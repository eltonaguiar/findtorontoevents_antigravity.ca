#!/usr/bin/env python3
"""Multi-host local LLM consult: LM Studio + Ollama + local vLLM, in parallel.

Engines are discovered, not configured: every (engine, host) pair in --target is
probed, its model list read, and each request routed to the engine that owns the
model. A reply is written to disk as soon as it lands, so a slow or hung model
never costs the answers of the fast ones.

The interesting mode is --check-claims. Models are asked for findings in a strict
one-line format that must cite file:line and quote the code they object to. The
checker then opens that file and verifies the quote is really at that line. Models
that invent line numbers, or describe code that is not there, get UNVERIFIED --
which is what happened to every specific claim two local models made about
tools/h150_gpa_backtest.py on 2026-11-22 (see reports/lms_review_2026-11-22/).

Usage:
    python3 tools/fleet_consult.py --list
    python3 tools/fleet_consult.py --model ollama:qwen3:32b --prompt "..." 
    python3 tools/fleet_consult.py --fanout 6 --prompt-file /tmp/p.md --check-claims
    python3 tools/fleet_consult.py --self-check
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_TARGETS = [
    ("lmstudio", "http://192.168.2.32:1234"),
    ("ollama", "http://192.168.2.32:11434"),
    ("ollama", "http://127.0.0.1:11434"),
    # vLLM on this box: 35B MoE (Qwen3.6-35B-A3B-NVFP4), reasoning-parser on.
    # Added 2026-11-22 — it is the fastest capable engine on the LAN, ~80 tok/s.
    ("vllm", "http://127.0.0.1:8000"),
]

# Below this many tokens a reasoning model spends the whole budget inside
# reasoning_content and answers with content="". See call_model().
THINK_MIN_TOKENS = 1500

FINDING_RE = re.compile(
    r"^FINDING\s+(?P<sev>CRITICAL|MAJOR|MINOR)\s+(?P<file>[\w./-]+):(?P<line>\d+)\s*\|"
    r"\s*(?P<claim>[^|]+?)\s*\|\s*(?P<quote>[^|]*?)\s*$",
    re.MULTILINE,
)

CLAIM_PROTOCOL = """
Report only defects you can point at. Use exactly one line per finding, no prose:

FINDING <CRITICAL|MAJOR|MINOR> <path>:<line> | what is wrong | the exact code you are objecting to

The quote must be copied verbatim from the file, character for character. A finding whose quote
is not found at the cited line is discarded as UNVERIFIED, so do not guess line numbers and do
not paraphrase the code. If you find nothing that meets this bar, reply NO_FINDINGS.
"""


def http_json(url, payload=None, timeout=180):
    """POST/GET JSON. Returns (status, body_text). Never raises on HTTP error."""
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST" if data else "GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # connection refused, timeout, DNS
        return 0, f"{type(e).__name__}: {e}"


def discover(targets, timeout=10):
    """Probe every (engine, host) and return {ref: (engine, host, model)}."""
    found = {}
    report = []
    for engine, host in targets:
        if engine in ("lmstudio", "vllm"):
            st, body = http_json(f"{host}/v1/models", timeout=timeout)
            ids = [m["id"] for m in json.loads(body).get("data", [])] if st == 200 else []
        else:
            st, body = http_json(f"{host}/api/tags", timeout=timeout)
            ids = [m["name"] for m in json.loads(body).get("models", [])] if st == 200 else []
        report.append({"engine": engine, "host": host, "http": st, "n_models": len(ids)})
        for m in ids:
            # first engine that has a model owns it; ollama/ollama need host disambiguation
            if engine in ("lmstudio", "vllm"):
                ref = f"{engine}:{m}"
            else:
                ref = f"ollama:{m}@{host.split('//')[1]}"
            found.setdefault(ref, (engine, host, m))
    return found, report


def call_model(engine, host, model, messages, max_tokens, temperature, timeout):
    t0 = time.time()
    text, err, payload = "", None, {}
    if engine in ("lmstudio", "vllm"):
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        if engine == "vllm":
            # 2026-11-22: Qwen3.6 on :8000 answers HTTP 200 with content="" when
            # max_tokens is small — every token went to reasoning_content. Ask for
            # thinking only when the budget can pay for it; never flip it silently
            # for the caller, record it below.
            payload["chat_template_kwargs"] = {"enable_thinking": max_tokens >= THINK_MIN_TOKENS}
        st, body = http_json(f"{host}/v1/chat/completions", payload, timeout=timeout)
        if st == 200:
            try:
                text = json.loads(body)["choices"][0]["message"].get("content") or ""
            except Exception as e:
                err = f"unparsable body: {e}: {body[:200]}"
        else:
            err = f"http {st}: {body[:300]}"
    else:
        st, body = http_json(
            f"{host}/api/chat",
            {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": temperature},
            },
            timeout=timeout,
        )
        text, err = "", None
        if st == 200:
            try:
                text = json.loads(body).get("message", {}).get("content") or ""
            except Exception as e:
                err = f"unparsable body: {e}: {body[:200]}"
        else:
            err = f"http {st}: {body[:300]}"
    if (engine == "vllm" and not text.strip() and err is None
            and payload.get("chat_template_kwargs", {}).get("enable_thinking")):
        # Reasoning still ate the answer: retry once with thinking disabled rather
        # than returning an empty reply the caller has to debug.
        retry = dict(payload, chat_template_kwargs={"enable_thinking": False})
        st2, body2 = http_json(f"{host}/v1/chat/completions", retry, timeout=timeout)
        if st2 == 200:
            try:
                text = json.loads(body2)["choices"][0]["message"].get("content") or ""
            except Exception as e:
                err = f"unparsable body (retry, thinking off): {e}: {body2[:200]}"
        else:
            err = f"retry(thinking off) http {st2}: {body2[:300]}"
    if not text.strip() and err is None:
        err = "empty content (model probably spent the whole token budget on reasoning)"
    return {
        "engine": engine,
        "host": host,
        "model": model,
        "http": st,
        "chars": len(text),
        "elapsed_s": round(time.time() - t0, 1),
        "error": err,
        "text": text,
    }


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def check_claim(file_rel, line, quote):
    """Is the quoted code actually at (or within 2 lines of) the cited line?"""
    p = (REPO_ROOT / file_rel).resolve()
    if REPO_ROOT not in p.parents and p != REPO_ROOT:
        return {"verdict": "PATH_OUTSIDE_REPO", "found": None}
    if not p.exists():
        return {"verdict": "NO_SUCH_FILE", "found": None}
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as e:
        return {"verdict": f"UNREADABLE: {e}", "found": None}
    if not 1 <= line <= len(lines):
        return {"verdict": "LINE_OUT_OF_RANGE", "found": None, "n_lines": len(lines)}
    lo, hi = max(0, line - 3), min(len(lines), line + 2)
    window = "\n".join(lines[lo:hi])
    q = norm(quote)
    if q and q in norm(window):
        return {"verdict": "VERIFIED", "found": lines[line - 1].strip()}
    # A quote spanning several lines (a comment block, a docstring) will not fit a 5-line
    # window even when the cite is exactly right. Search the whole file before rejecting.
    if q and q in norm("\n".join(lines)):
        for k in range(len(lines)):
            probe = norm("\n".join(lines[k:k + 8]))
            if q in probe:
                return {"verdict": "VERIFIED_ELSEWHERE", "found": lines[k].strip(),
                        "cited_line": line, "actual_line": k + 1}
    return {"verdict": "UNVERIFIED", "found": lines[line - 1].strip()}


def extract_claims(text):
    out = []
    for m in FINDING_RE.finditer(text or ""):
        c = {
            "severity": m.group("sev"),
            "file": m.group("file"),
            "line": int(m.group("line")),
            "claim": m.group("claim").strip(),
            "quote": m.group("quote").strip(),
        }
        c.update(check_claim(c["file"], c["line"], c["quote"]))
        out.append(c)
    return out


def self_check():
    """The checker must reject the false claims local models actually made."""
    fx = Path(REPO_ROOT / "tools" / "fleet_consult.py")
    real = fx.read_text().splitlines()[0]  # a line that definitely exists
    cases = [
        # (file, line, quote, expected)
        ("tools/fleet_consult.py", 1, real, "VERIFIED"),
        # invented line number
        ("tools/fleet_consult.py", 999999, real, "LINE_OUT_OF_RANGE"),
        # multi-line quote cited at its first line must not be rejected
        ("tools/fleet_consult.py", 1, fx.read_text().splitlines()[0], "VERIFIED"),
        # real file, quote that is not there (the llama-3.1-8b "fix")
        ("tools/h150_gpa_backtest.py", 1, "if not (p0 == p0) and p0 <= 0:", "UNVERIFIED"),
        # file that does not exist
        ("tools/does_not_exist_xyz.py", 1, "x", "NO_SUCH_FILE"),
        # path traversal must be refused
        ("../../etc/passwd", 1, "root", "PATH_OUTSIDE_REPO"),
    ]
    bad = 0
    for f, ln, q, want in cases:
        got = check_claim(f, ln, q)["verdict"]
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {f}:{ln} -> {got} (want {want})")
    # a model reply in the protocol format, one true and one fabricated
    reply = (
        f"FINDING MINOR tools/fleet_consult.py:1 | real line | {real}\n"
        "FINDING CRITICAL tools/h150_gpa_backtest.py:245 | ZeroDivisionError | "
        "if not (p0 == p0) and p0 <= 0:\n"
        "NO_FINDINGS\n"
    )
    claims = extract_claims(reply)
    verdicts = [c["verdict"] for c in claims]
    print(f"  parsed {len(claims)} findings -> {verdicts}")
    # VERIFIED_ELSEWHERE counts as a pass: a legitimately multi-line quote cannot sit inside
    # a 5-line window, and rejecting it would punish accurate citations.
    ok_verdicts = {"VERIFIED", "VERIFIED_ELSEWHERE"}
    if not (verdicts[0] in ok_verdicts and len(verdicts) == 2 and verdicts[1] == "UNVERIFIED"):
        bad += 1
        print("  FAIL expected the real quote to verify and the fabricated one to be rejected")
    print(("SELF-CHECK PASSED" if not bad else f"SELF-CHECK FAILED ({bad})"))
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--target", action="append", default=[],
                    help="engine:base_url, e.g. ollama:http://127.0.0.1:11434 "
                         "or vllm:http://127.0.0.1:8000")
    ap.add_argument("--model", action="append", default=[],
                    help="repeatable; 'engine:model' or a discovered ref")
    ap.add_argument("--fanout", type=int, default=0, help="call N discovered models")
    ap.add_argument("--engine", default="", help="restrict fanout to one engine")
    ap.add_argument("--prompt", default="")
    ap.add_argument("--prompt-file", default="")
    ap.add_argument("--max-tokens", type=int, default=1200)
    ap.add_argument("--temperature", type=float, default=0.4)
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--out-dir", default="/tmp/fleet_consult")
    ap.add_argument("--check-claims", action="store_true")
    ap.add_argument("--claim-protocol", action="store_true",
                    help="append the strict FINDING format to the prompt")
    a = ap.parse_args()

    if a.self_check:
        return self_check()

    targets = DEFAULT_TARGETS[:]
    for t in a.target:
        eng, _, host = t.partition(":")
        targets.append((eng, host))

    found, report = discover(targets)
    if a.list:
        for r in report:
            print(f"{r['engine']:9s} {r['host']:28s} http {r['http']} models {r['n_models']}")
        print()
        for ref in sorted(found):
            print(" ", ref)
        return 0

    prompt = a.prompt
    if a.prompt_file:
        prompt = Path(a.prompt_file).read_text()
    if not prompt:
        ap.error("--prompt or --prompt-file required")
    if a.claim_protocol:
        prompt = prompt.rstrip() + "\n\n" + CLAIM_PROTOCOL

    refs = list(a.model)
    if a.fanout or (not refs and not a.model):
        pool = [r for r in sorted(found) if not a.engine or found[r][0] == a.engine]
        refs.extend(pool[: a.fanout] if a.fanout else pool)
    if not refs:
        ap.error("nothing to call; see --list")

    jobs = []
    for ref in refs:
        if ref in found:
            jobs.append(found[ref])
        else:  # allow ad-hoc "engine:model" or "engine:model@host:port"
            eng, _, rest = ref.partition(":")
            if "@" in rest:
                model, _, hostport = rest.rpartition("@")
                host = f"http://{hostport}" if not hostport.startswith("http") else hostport
            else:
                model = rest
                host = next((h for e, h in targets if e == eng), None)
            if host is None:
                print(f"skip {ref}: unknown engine", file=sys.stderr)
                continue
            jobs.append((eng, host, model))

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    messages = [{"role": "user", "content": prompt}]

    def run(job):
        eng, host, model = job
        res = call_model(eng, host, model, messages, a.max_tokens, a.temperature, a.timeout)
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", f"{eng}-{host.split('//')[1]}-{model}")[:120]
        claims = extract_claims(res["text"]) if a.check_claims else []
        res["claims"] = claims
        (out_dir / f"{slug}.md").write_text(
            f"<!-- engine={eng} host={host} model={model} http={res['http']} "
            f"chars={res['chars']} elapsed={res['elapsed_s']}s error={res['error']} -->\n\n"
            + (res["text"] or f"[no content: {res['error']}]"),
            encoding="utf-8",
        )
        v = {}
        for c in claims:
            v[c["verdict"]] = v.get(c["verdict"], 0) + 1
        print(f"  {res['http']} {res['chars']:6d}ch {res['elapsed_s']:6.1f}s {ref_summary(job)}"
              + (f" claims={v}" if claims else "") + (f" ERR {res['error'][:80]}" if res["error"] else ""))
        return res

    print(f"calling {len(jobs)} model(s), parallel={a.parallel}, out={out_dir}")
    with ThreadPoolExecutor(max_workers=a.parallel) as ex:
        results = list(ex.map(run, jobs))

    index = {
        "prompt_chars": len(prompt),
        "when": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "models": [{k: v for k, v in r.items() if k != "text"} for r in results],
    }
    (out_dir / "index.json").write_text(json.dumps(index, indent=2))
    ok = sum(1 for r in results if r["text"].strip())
    print(f"\n{ok}/{len(results)} replied; index at {out_dir/'index.json'}")
    if a.check_claims:
        allc = [c for r in results for c in r["claims"]]
        ver = sum(1 for c in allc if c["verdict"] == "VERIFIED")
        print(f"claims: {len(allc)} total, {ver} VERIFIED, {len(allc)-ver} rejected")
    return 0 if ok else 1


def ref_summary(job):
    eng, host, model = job
    return f"{eng}:{model}@{host.split('//')[1]}"


if __name__ == "__main__":
    sys.exit(main())
