#!/usr/bin/env python3
"""Ask AI chat sites that have no API, by teaching api-anything their own request.

Why this exists
---------------
notegpt.io/ai-chat, notrack.ai/chat and duck.ai are browser-only: no API key, no
documented endpoint. Driving a browser for each question is slow and
token-expensive; `api-anything` (github.com/goodnight000/api-anything) instead
watches the site's own page make its request once, turns that into a template
with the prompt as a parameter, and afterwards answers with one plain HTTP call.

Hard truth found while building this (2026-11-18, api-anything 0.4.0)
----------------------------------------------------------------------
An AI chat answer is not a read. On all three sites the answer arrives from a
POST, so api-anything's read-learning path refuses it by design:

    {"ok":false,"class":"refused","error":"request 22 (POST https://notrack.ai/api/dispatch)
     is not a read: a POST that is not a GraphQL query may change something.
     learn_site learns reads only, and sent nothing", ...}

What each site's own page actually does:

  duckai   GET  /?q=<prompt>                 carries the prompt (HTML shell)
           POST /duckchat/v1/chat            the answer, gated by
           GET  /duckchat/v1/auth/token      a token fetched first
  notrack  GET  /chat?q=<prompt>             carries the prompt (HTML shell)
           POST /api/dispatch                the answer, text/event-stream
  notegpt  not probed yet

So there are two paths, and this tool is explicit about which one it is on:

  learn            read path. Works for sites whose answer is a GET. It will
                   refuse these three, and say so instead of failing obscurely.
  learn --write    write path (`api-anything add --write`). This is the one that
                   can learn a POST. api-anything intercepts the request and
                   aborts it while learning, so learning itself sends nothing —
                   but the later `ask --allow-writes` DOES send the prompt to
                   the site, which is a post leaving this machine. That is why
                   it is a separate flag the user has to approve, not a default.

Usage
-----
    python3 tools/consult_webchat.py doctor
    python3 tools/consult_webchat.py learn --site notrack --write   # asks once, sends nothing
    python3 tools/consult_webchat.py ask "prompt" --allow-writes    # this DOES post
    python3 tools/consult_webchat.py ask "prompt" --site duckai --json
    python3 tools/consult_webchat.py sites

Design notes
------------
* Nothing here reimplements api-anything; it shells out to the CLI and handles
  only the two things the CLI does not: the per-site trigger table and pulling
  the readable answer out of the JSON result.
* A site that is not learned is reported as such, never guessed at. `ask` on a
  half-learned set would otherwise look like a silent failure.
* State lives in ~/.api-anything (API_ANYTHING_HOME overrides), so this script
  is stateless and learning persists across sessions.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import textwrap

API_ANYTHING = os.environ.get("API_ANYTHING_PKG", "api-anything@0.4.0")

# trigger: the page URL whose own request carries the prompt, as a template.
# param:   the parameter name api-anything interpolates.
# answer:  how that site delivers the answer — the reason it needs --write.
# verified: only set after `ask` returned a real answer; a learned-but-wrong
#   trigger happily replays the example text, so a successful `learn` is not proof.
SITES: dict[str, dict[str, str]] = {
    "duckai": {
        "slug": "duckai",
        "label": "Duck.ai (DuckDuckGo AI Chat)",
        "url": "https://duck.ai/",
        "trigger": "https://duck.ai/?q={prompt}",
        "param": "prompt",
        "op": "chat",
        "answer": "POST /duckchat/v1/chat (token from /duckchat/v1/auth/token)",
        "verified": "",
    },
    "notegpt": {
        "slug": "notegpt",
        "label": "NoteGPT AI Chat",
        "url": "https://notegpt.io/ai-chat",
        "trigger": "https://notegpt.io/ai-chat?q={prompt}",
        "param": "prompt",
        "op": "chat",
        "answer": "not probed yet",
        "verified": "",
    },
    "notrack": {
        "slug": "notrack",
        "label": "NoTrack AI Chat",
        "url": "https://notrack.ai/chat",
        "trigger": "https://notrack.ai/chat?q={prompt}",
        "param": "prompt",
        "op": "chat",
        "answer": "POST /api/dispatch (text/event-stream)",
        "verified": "",
    },
}

# Two values to learn from; the third is kept as the operation's holdout check.
# Keep the answers stable over time — the check replays its question and compares.
LEARN_ARGS = ("What is 2+2?", "Name one prime number.", "What colour is the sky?")


def _run(cmd: list[str], timeout: int = 600) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, f"{cmd[0]} not found on PATH"
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s: {' '.join(cmd[:4])} ..."
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def aa(*args: str, timeout: int = 600) -> tuple[int, str]:
    return _run(["npx", "-y", API_ANYTHING, *args], timeout=timeout)


def _json_error(out: str) -> dict[str, object] | None:
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{") and '"ok"' in line:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get("ok") is False:
                return obj
    return None


def _post_answer_request(err: dict[str, object], param: str) -> str | None:
    """The request that looks like the answer: a POST that carries the prompt.

    Read-learning reports a plain "no request carries the example values" when the
    answer is a POST it will not touch. Naming that request turns a vague failure
    into the one instruction that resolves it.
    """
    alts = err.get("alternatives") or []
    if isinstance(alts, list):
        for a in alts:
            if not isinstance(a, dict) or a.get("method") != "POST":
                continue
            carries = a.get("carries") or []
            if isinstance(carries, list) and param in carries:
                return f"{a.get('method')} {a.get('url')}"
    return None


def cmd_doctor(_: argparse.Namespace) -> int:
    """Check the pieces a learn needs. Cheap, and the first thing to run."""
    ok = True

    def line(label: str, good: bool, detail: str) -> None:
        nonlocal ok
        ok = ok and good
        print(f"{'OK  ' if good else 'FAIL'}  {label:14} {detail}")

    node = shutil.which("node")
    version = ""
    if node:
        _, out = _run([node, "--version"], timeout=30)
        version = out.strip()
    major_minor = tuple(int(x) for x in version.lstrip("v").split(".")[:2]) if version else (0, 0)
    line("node", bool(node) and major_minor >= (22, 13), version or "missing (need >= 22.13)")

    browsers = [b for b in ("google-chrome", "chromium", "chromium-browser", "brave-browser") if shutil.which(b)]
    line("chromium", bool(browsers), ", ".join(browsers) or "none found (learning needs one)")

    rc, out = aa("--version", timeout=300)
    line("api-anything", rc == 0, out.strip().splitlines()[0] if out.strip() else "not reachable")

    rc, out = aa("sites", timeout=300)
    learned = out if rc == 0 else ""
    for key, site in SITES.items():
        hit = site["slug"] in learned
        mark = f"  verified {site['verified']}" if site["verified"] else ""
        print(f"{'OK  ' if hit else '--  '}  {key:14} {'learned' if hit else 'not learned yet'}{mark}")
        if not hit:
            print(f"      answers via {site['answer']} -> learn needs --write")
    return 0 if ok else 1


def cmd_learn(ns: argparse.Namespace) -> int:
    site = SITES[ns.site]
    p = site["param"]
    if ns.write:
        cmd = [
            "add", site["slug"], site["op"],
            "--trigger", site["trigger"],
            "--example", f"{p}={LEARN_ARGS[0]}",
            "--example2", f"{p}={LEARN_ARGS[1]}",
            "--write",
        ]
        print(f"learning {site['label']} over the WRITE path from {site['trigger']}", file=sys.stderr)
        print("api-anything intercepts and aborts the request while learning, so nothing is sent now;\n"
              "`ask --allow-writes` is what actually sends the prompt.", file=sys.stderr)
    else:
        cmd = [
            "learn", site["trigger"],
            "--args", f"{p}={LEARN_ARGS[0]}",
            "--args2", f"{p}={LEARN_ARGS[1]}",
            "--args3", f"{p}={LEARN_ARGS[2]}",
            "--site", site["slug"], "--op", site["op"],
        ]
        print(f"learning {site['label']} over the READ path from {site['trigger']}", file=sys.stderr)
        print(f"note: this site answers via {site['answer']} — if learn refuses with class=refused,\n"
              f"re-run with --write", file=sys.stderr)

    rc, out = aa(*cmd, timeout=ns.timeout)
    print(out.rstrip())
    err = _json_error(out)
    if rc != 0 or err:
        cls = (err or {}).get("class")
        post = _post_answer_request(err, site["param"]) if err else None
        if cls == "refused":
            print(
                f"\nrefused: {site['label']} answers with a POST, and read-learning is read-only by design.\n"
                f"The sanctioned path is the write path, which this tool will not run for you unprompted:\n\n"
                f"  python3 tools/consult_webchat.py learn --site {ns.site} --write\n\n"
                f"(api-anything's own words: {err.get('error')})",
                file=sys.stderr,
            )
        elif post:
            print(
                f"\n{site['label']} answers via {post} — a POST. Read-learning is read-only by\n"
                f"design, which is why nothing here could be read. The sanctioned path is the write\n"
                f"path, and this tool will not run it unprompted:\n\n"
                f"  python3 tools/consult_webchat.py learn --site {ns.site} --write\n",
                file=sys.stderr,
            )
        else:
            print(
                "\nlearn failed. Usual causes, in order:\n"
                "  1. the page takes the prompt from a click/typing step, not the URL ->\n"
                "     api-anything capture <url>, then add --trigger ... --steps '<json>'\n"
                "  2. the site needs a session -> api-anything login <site>\n"
                "  3. the request is signed per session -> it cannot be replayed over plain HTTP.",
                file=sys.stderr,
            )
        return rc or 1
    print(
        f"\nlearned. Only after `ask --site {ns.site}` returns a real answer, set\n"
        f"SITES['{ns.site}']['verified'] to today's date in {os.path.abspath(__file__)}.",
        file=sys.stderr,
    )
    return 0


def _answer_text(payload: object) -> str:
    """Pull the readable answer out of whatever shape the site returned."""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        for key in ("answer", "text", "response", "content", "message", "output", "reply"):
            v = payload.get(key)
            if isinstance(v, str) and v.strip():
                return v
            if isinstance(v, dict):
                nested = _answer_text(v)
                if nested:
                    return nested
        for key in ("data", "result", "messages", "choices", "events"):
            if key in payload:
                nested = _answer_text(payload[key])
                if nested:
                    return nested
        if len(payload) == 1:
            return _answer_text(next(iter(payload.values())))
    if isinstance(payload, list):
        for item in reversed(payload):
            nested = _answer_text(item)
            if nested:
                return nested
    return ""


def _ask_one(ns: argparse.Namespace, site: dict[str, str]) -> dict[str, object]:
    cmd = ["call", site["slug"], site["op"], f"{site['param']}={ns.prompt}"]
    if ns.allow_writes:
        cmd.append("--allow-writes")
    rc, out = aa(*cmd, timeout=ns.timeout)
    result: dict[str, object] = {"site": site["slug"], "label": site["label"], "ok": False, "raw": out}
    err = _json_error(out)
    if err:
        result.update(error=f"{err.get('class')}: {err.get('error') or err.get('reason')}", next=err.get("next"))
        return result
    if rc != 0:
        result["error"] = f"api-anything exited {rc}"
        return result
    try:
        parsed = json.loads(out)
    except json.JSONDecodeError:
        text = _answer_text(out.strip())
        result.update(ok=bool(text), answer=text or out.strip()[:4000])
        return result
    data = parsed.get("data") if isinstance(parsed, dict) else parsed
    text = _answer_text(data)
    result.update(
        ok=bool(text),
        answer=text or "(no answer field found — see raw)",
        tier=parsed.get("tier") if isinstance(parsed, dict) else None,
    )
    return result


def cmd_ask(ns: argparse.Namespace) -> int:
    if ns.prompt == "-":
        ns.prompt = sys.stdin.read().strip()
    if not ns.prompt:
        print("empty prompt", file=sys.stderr)
        return 2
    targets = [SITES[ns.site]] if ns.site else list(SITES.values())

    rc, learned = aa("sites", timeout=300)
    blob = learned if rc == 0 else ""
    usable = [s for s in targets if s["slug"] in blob]
    skipped = [s["slug"] for s in targets if s not in usable]
    if not usable:
        first = targets[0]
        print(
            f"none of {[s['slug'] for s in targets]} is learned yet.\n"
            f"their answers arrive by POST, so the step that can learn them is the write path:\n"
            f"  python3 tools/consult_webchat.py learn --site {first['slug']} --write",
            file=sys.stderr,
        )
        return 3

    results = [_ask_one(ns, s) for s in usable]
    if ns.json:
        print(json.dumps({"prompt": ns.prompt, "skipped": skipped, "results": results}, indent=2))
        return 0 if any(r["ok"] for r in results) else 1

    for r in results:
        print(f"\n===== {r['label']} =====")
        if r["ok"]:
            print(textwrap.fill(str(r["answer"]), width=100))
        else:
            print(f"[failed] {r.get('error')}")
            if r.get("next"):
                print(f"[next] {r['next']}")
    if skipped:
        print(f"\n(skipped, not learned: {', '.join(skipped)})", file=sys.stderr)
    return 0 if any(r["ok"] for r in results) else 1


def cmd_sites(_: argparse.Namespace) -> int:
    rc, out = aa("sites", timeout=300)
    if rc != 0:
        print(out.rstrip(), file=sys.stderr)
        return rc
    print(f"{'key':10} {'slug':10} {'learned':8} {'verified':10} answers-via")
    for key, s in SITES.items():
        print(f"{key:10} {s['slug']:10} {str(s['slug'] in out):8} {s['verified'] or '-':10} {s['answer']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("doctor", help="check node/chromium/api-anything and what is already learned")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("learn", help="teach api-anything one site's own chat request (once per site)")
    p.add_argument("--site", required=True, choices=sorted(SITES))
    p.add_argument("--write", action="store_true",
                   help="use the write path (api-anything add --write); required when the answer is a POST")
    p.add_argument("--timeout", type=int, default=900)
    p.set_defaults(func=cmd_learn)

    p = sub.add_parser("ask", help="ask one or all learned sites")
    p.add_argument("prompt", help="the question, or - to read stdin")
    p.add_argument("--site", choices=sorted(SITES))
    p.add_argument("--json", action="store_true")
    p.add_argument("--allow-writes", action="store_true",
                   help="actually send the prompt to the site (required for POST-answer ops)")
    p.add_argument("--timeout", type=int, default=300)
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("sites", help="which of the three are learned, and how each answers")
    p.set_defaults(func=cmd_sites)

    ns = ap.parse_args(argv)
    return ns.func(ns)


if __name__ == "__main__":
    sys.exit(main())
