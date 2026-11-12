#!/usr/bin/env python3
"""free_model_discovery.py — pull every provider's live model catalog, keep only the
zero-cost ones, prove each with a real chat call, and emit a LiteLLM config fragment.

Why this exists
---------------
Hand-maintaining `:free` model IDs inside litellm_config.yaml rots within days:
providers retire IDs (nvidia llama-3.1-8b -> 410 Gone), reprice promos
(ring-2.6-1t -> paid), or rename (liquid/lfm-2.5-2.6b:free). This tool re-derives
the free set from each provider's own `/models` endpoint at run time, so a cron
job re-generates the fragment instead of a human `curl`-ing badges.

Free-detection strategies (per provider `kind`)
  pricing : entry.pricing.prompt == 0 AND completion == 0      (OpenRouter, Kilo)
  suffix  : id ends with ":free" / "-free"                      (OFOX, Zen, Nous)
  all     : provider's whole catalog is free-tier reachable      (Groq, Cerebras,
                                                                LLM7, Pollinations,
                                                                GitHub Models, CF)
  anon    : entry.tier == "anonymous"                            (Pollinations)

Every candidate is then LIVE-probed with a minimal chat call. Only HTTP 200 rows
are emitted, so a dead ID can never reach the router.

Usage
  python3 tools/free_model_discovery.py --probe --emit-yaml litellm_generated_free.yaml
  python3 tools/free_model_discovery.py --probe --out reports/free_model_discovery.json
  python3 tools/free_model_discovery.py --only groq,openrouter,kilo_gateway
  python3 tools/free_model_discovery.py --no-probe          # catalog only, fast

Generated groups
  DYNAMIC_FREE          every alive free model (weighted by context window)
  DYNAMIC_FREE_<PROV>   one group per provider
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
DEFAULT_TIMEOUT = 45

# ---------------------------------------------------------------------------
# Provider registry.
#   models : catalog URL (may use {account} for Cloudflare)
#   chat   : /chat/completions URL
#   kind   : free-detection strategy (see module docstring)
#   key    : env vars to try, in order (first non-empty wins); None = keyless
#   paid   : True -> never scanned (listed for completeness only)
# ---------------------------------------------------------------------------
PROVIDERS: list[dict[str, Any]] = [
    # ---- keyless, no account at all -------------------------------------
    dict(name="pollinations", models="https://text.pollinations.ai/models",
         chat="https://text.pollinations.ai/openai", kind="anon", key=None,
         note="~1 reply / 45 s per IP"),
    dict(name="llm7", models="https://api.llm7.io/v1/models",
         chat="https://api.llm7.io/v1/chat/completions", kind="all", key=None,
         bearer="unused", note="keyless; any non-empty bearer"),
    dict(name="ovh_anon", models="https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/models",
         chat="https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/chat/completions",
         kind="all", key=None, note="anon ~1-2 calls/IP"),
    # ---- key required, genuinely free tier ------------------------------
    dict(name="kilo_gateway", models="https://api.kilo.ai/api/gateway/models",
         chat="https://api.kilo.ai/api/gateway/v1/chat/completions", kind="pricing",
         key=["KILOCODE_API_KEY", "KILO_API_KEY"], note="383-model catalog, ~200 req/h"),
    dict(name="openrouter", models="https://openrouter.ai/api/v1/models",
         chat="https://openrouter.ai/api/v1/chat/completions", kind="pricing",
         key=["OPENROUTER", "OPENROUTER_API_KEY"], guard="openrouter"),
    dict(name="groq", models="https://api.groq.com/openai/v1/models",
         chat="https://api.groq.com/openai/v1/chat/completions", kind="all",
         key=["GROQ_API_KEY"]),
    dict(name="groq_alt", models="https://api.groq.com/openai/v1/models",
         chat="https://api.groq.com/openai/v1/chat/completions", kind="all",
         key=["GROQ_API_KEY_ALT"]),
    dict(name="cerebras", models="https://api.cerebras.ai/v1/models",
         chat="https://api.cerebras.ai/v1/chat/completions", kind="all",
         key=["CEREBRAS_API_KEY"]),
    dict(name="mistral", models="https://api.mistral.ai/v1/models",
         chat="https://api.mistral.ai/v1/chat/completions", kind="all",
         key=["MISTRAL_API_KEY"]),
    dict(name="cohere", models="https://api.cohere.ai/compatibility/v1/models",
         chat="https://api.cohere.ai/compatibility/v1/chat/completions", kind="all",
         key=["COHERE_API_KEY"], note="trial key"),
    dict(name="github_models", models="https://models.github.ai/catalog/models",
         chat="https://models.github.ai/inference/chat/completions", kind="all",
         key=["GITHUB_MODELS_KEY"]),
    dict(name="github_models_2", models="https://models.github.ai/catalog/models",
         chat="https://models.github.ai/inference/chat/completions", kind="all",
         key=["GITHUB_MODELS_KEY2"]),
    dict(name="cloudflare", models="https://api.cloudflare.com/client/v4/accounts/{account}/ai/models/search",
         chat="https://api.cloudflare.com/client/v4/accounts/{account}/ai/v1/chat/completions",
         kind="cf", key=["CF_API_TOKEN"], account="CF_ACCOUNT_ID",
         note="10k neurons/day free"),
    dict(name="nous", models="https://inference-api.nousresearch.com/v1/models",
         chat="https://inference-api.nousresearch.com/v1/chat/completions",
         kind="suffix", key=["NOUS_API_KEY"]),
    dict(name="ofox", models="https://api.ofox.ai/v1/models",
         chat="https://api.ofox.ai/v1/chat/completions", kind="suffix",
         key=["OFOX_API_KEY"]),
    dict(name="deepinfra", models="https://api.deepinfra.com/v1/openai/models",
         chat="https://api.deepinfra.com/v1/openai/chat/completions", kind="all",
         key=["DEEPINFRA_API_KEY_BEST", "DEEPINFRA_API_KEY_ALT"], slow=True),
    dict(name="together", models="https://api.together.xyz/v1/models",
         chat="https://api.together.xyz/v1/chat/completions", kind="all",
         key=["TOGETHER_API_KEY"]),
    dict(name="fireworks", models="https://api.fireworks.ai/inference/v1/models",
         chat="https://api.fireworks.ai/inference/v1/chat/completions", kind="all",
         key=["FIREWORKS_API_KEY"]),
    dict(name="bluesmind", models="https://api.bluesminds.com/v1/models",
         chat="https://api.bluesminds.com/v1/chat/completions", kind="all",
         key=["BLUESMIND_API_KEY"]),
    dict(name="nvidia_nim", models="https://integrate.api.nvidia.com/v1/models",
         chat="https://integrate.api.nvidia.com/v1/chat/completions", kind="all",
         key=["NVIDIA_API_KEY"]),
    dict(name="opencode_zen", models="https://opencode.ai/zen/v1/models",
         chat="https://opencode.ai/zen/v1/chat/completions", kind="suffix",
         key=["OPENCODE_API_KEY"], note="free IDs often 403 outside their client"),
    dict(name="sambanova", models="https://api.sambanova.ai/v1/models",
         chat="https://api.sambanova.ai/v1/chat/completions", kind="all",
         key=["SAMBANOVA_API_KEY"]),
    dict(name="qwen_dashscope", models="https://dashscope-intl.aliyuncs.com/compatible-mode/v1/models",
         chat="https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
         kind="all", key=["QWEN_API_KEY"]),
    # ---- paid / dead accounts: listed so the report shows we looked ------
    dict(name="xai", models="https://api.x.ai/v1/models", chat="https://api.x.ai/v1/chat/completions",
         kind="all", key=["XAI_API_KEY"], paid=True),
    dict(name="anthropic", models="https://api.anthropic.com/v1/models",
         chat="https://api.anthropic.com/v1/messages", kind="all",
         key=["ANTHROPIC_API_KEY"], paid=True),
    dict(name="openai", models="https://api.openai.com/v1/models",
         chat="https://api.openai.com/v1/chat/completions", kind="all",
         key=["OPENAI_API_KEY"], paid=True),
    dict(name="deepseek", models="https://api.deepseek.com/models",
         chat="https://api.deepseek.com/chat/completions", kind="all",
         key=["DEEPSEEK_API_KEY"], paid=True),
    dict(name="moonshot", models="https://api.moonshot.ai/v1/models",
         chat="https://api.moonshot.ai/v1/chat/completions", kind="all",
         key=["MOONSHOT_API_KEY"], paid=True),
    dict(name="hypereal", models="https://api.hypereal.cloud/v1/models",
         chat="https://api.hypereal.cloud/v1/chat/completions", kind="all",
         key=["HYPEREAL_API_KEY"], paid=True),
]


# ---------------------------------------------------------------------------
def env_of_proxy() -> dict[str, str]:
    """Read the live proxy's environment (the authoritative key source).

    Scans every /proc/<pid> whose cmdline mentions litellm and keeps the largest
    environment, so a stale/secondary process can't shadow the real proxy (the
    first version of this function silently returned {} and every provider then
    reported "no key": always fall through to the dbpasses.txt reader below.
    """
    pids: list[str] = []
    if os.environ.get("PROXY_PID"):
        pids.append(os.environ["PROXY_PID"])
    try:
        for p in Path("/proc").iterdir():
            if not p.name.isdigit():
                continue
            try:
                cmd = (p / "cmdline").read_bytes().decode("utf-8", "replace").replace("\0", " ")
            except Exception:
                continue
            if "litellm" in cmd:
                pids.append(p.name)
    except Exception:
        pass
    best: dict[str, str] = {}
    for pid in dict.fromkeys(pids):
        try:
            raw = Path(f"/proc/{pid}/environ").read_bytes().decode("utf-8", "replace")
        except Exception:
            continue
        d: dict[str, str] = {}
        for kv in raw.split("\0"):
            if "=" in kv:
                k, _, v = kv.partition("=")
                d[k] = v
        if len(d) > len(best):
            best = d
    return best


def dbpasses_values() -> dict[str, str]:
    """label -> value, for keys that exist in the file but were never exported."""
    f = Path(os.path.expanduser("~/dbpasses.txt"))
    if not f.exists():
        return {}
    lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
    out: dict[str, str] = {}
    for i, raw in enumerate(lines):
        s = raw.strip()
        if not s or s.startswith(("http", "#", "//")) or len(s) > 90:
            continue
        if not (s.endswith(":") or re.fullmatch(r"[A-Z0-9][A-Z0-9 _\.\(\)\-\*/]{2,}", s)):
            continue
        for j in range(i + 1, min(i + 4, len(lines))):
            cand = lines[j].strip()
            if not cand or len(cand) < 12 or cand.endswith(":"):
                continue
            if cand.startswith(("http", "==", "--")) or re.fullmatch(r"[A-Z0-9_ \-\.\(\)\*/,']+", cand):
                continue
            out.setdefault(s.rstrip(":"), cand)
            break
    return out


ENV = env_of_proxy()
DBV = dbpasses_values()


# dbpasses.txt labels whose wording doesn't match the env-var name. Without these
# the token-subset heuristic below misses CF/Groq-ALT/NVIDIA entirely and the
# provider is wrongly reported as "no key".
ALIASES: dict[str, list[str]] = {
    "CF_API_TOKEN": ["Cloudflare API key"],
    "CF_ACCOUNT_ID": ["Cloudflare account iD"],
    "GROQ_API_KEY_ALT": ["GROQ_API_KEY", "GROQ FREE KEY"],
    "GROQ_API_KEY": ["GROQ FREE KEY", "GROQ_API_KEY"],
    "NVIDIA_API_KEY": ["NVIDIA"],
    "NVIDIA_API_KEY_ALT": ["NVIDIA ALT KEY"],
    "OPENROUTER": ["OPEN ROUTER API KEY"],
    "OFOX_API_KEY": ["OFOX_API_KEY"],
    "LLM7_API_KEY": ["LLM7_API_KEY_FREE"],
}


def _dbpasses_lookup(envname: str) -> tuple[str | None, str]:
    """Find a key that lives in dbpasses.txt but was never exported to the proxy."""
    if not DBV:
        return None, ""
    if envname in DBV:
        return DBV[envname], f"dbpasses:{envname}"
    for lab in ALIASES.get(envname, []):
        for k, v in DBV.items():
            if k == lab or k.startswith(lab):
                return v, f"dbpasses:{k}"
    tokens = [t for t in re.split(r"[_\s\.]+", envname) if t and t not in ("API", "KEY")]
    if not tokens:
        return None, ""
    hits = []
    for label, val in DBV.items():
        up = label.upper()
        if all(t in up for t in tokens):
            hits.append((len(label), label, val))
    if not hits:
        return None, ""
    hits.sort()
    return hits[0][2], f"dbpasses:{hits[0][1]}"


def resolve_key(spec: dict) -> tuple[str | None, str]:
    for name in spec.get("key") or []:
        if ENV.get(name):
            return ENV[name], name
    for name in spec.get("key") or []:
        val, src = _dbpasses_lookup(name)
        if val:
            return val, src
    if spec.get("bearer"):
        return spec["bearer"], f"(literal {spec['bearer']})"
    return None, ""


def fmt(spec: dict) -> dict:
    out = dict(spec)
    acct = ENV.get(spec.get("account", ""), "") if spec.get("account") else ""
    if "{account}" in spec["models"]:
        out["models"] = spec["models"].replace("{account}", acct)
    if "{account}" in spec["chat"]:
        out["chat"] = spec["chat"].replace("{account}", acct)
    return out


S = requests.Session()
S.headers.update({"User-Agent": UA, "Content-Type": "application/json"})


def catalog(spec: dict, key: str | None, timeout: int = 40) -> tuple[int, list[dict], str]:
    h = {"Authorization": f"Bearer {key}"} if key else {}
    if spec["name"].startswith("anthropic"):
        h = {"x-api-key": key or "", "anthropic-version": "2023-06-01"}
    try:
        r = S.get(spec["models"], headers=h, timeout=timeout, allow_redirects=True)
        ct = r.headers.get("content-type", "")
        if "json" not in ct:
            return r.status_code, [], f"non-json ({r.text[:60]})"
        j = r.json()
    except Exception as e:
        return 0, [], f"{type(e).__name__}: {str(e)[:70]}"
    rows: list[dict] = []
    if isinstance(j, list):
        rows = [x for x in j if isinstance(x, dict)]
    elif isinstance(j, dict):
        for k in ("data", "models", "result", "response"):
            v = j.get(k)
            if isinstance(v, list):
                rows = [x for x in v if isinstance(x, dict)]
                break
            if isinstance(v, dict) and isinstance(v.get("models"), list):
                rows = [x for x in v["models"] if isinstance(x, dict)]
                break
    return r.status_code, rows, ""


def mid(m: dict) -> str:
    return str(m.get("id") or m.get("name") or m.get("model") or m.get("slug") or "")


def ctx_of(m: dict) -> int | None:
    for k in ("context_length", "context_window", "max_context_length", "max_context",
              "max_input_tokens", "max_model_len", "inputTokenLimit"):
        v = m.get(k)
        if isinstance(v, (int, float)) and v:
            return int(v)
    for k in ("top_provider", "limits"):
        d = m.get(k)
        if isinstance(d, dict):
            for kk in ("context_length", "max_context_length"):
                if isinstance(d.get(kk), (int, float)):
                    return int(d[kk])
    return None


def is_free(spec: dict, m: dict) -> tuple[bool, str]:
    kind = spec["kind"]
    _id = mid(m)
    pr = m.get("pricing") if isinstance(m.get("pricing"), dict) else {}
    if kind == "pricing":
        if not pr:
            return (":free" in _id or _id.endswith("-free")), "id-suffix"
        try:
            p = float(pr.get("prompt", 1))
            c = float(pr.get("completion", 1))
        except Exception:
            return False, ""
        return (p == 0 and c == 0), ("$0/0" if p == 0 and c == 0 else "")
    if kind == "suffix":
        low = _id.lower()
        return (low.endswith(":free") or low.endswith("-free")
                or low.endswith("-free:free") or ":free" in low), "id-suffix"
    if kind == "anon":
        tier = str(m.get("tier", "")).lower()
        if tier:
            return tier == "anonymous", f"tier:{tier}"
        return True, "default"
    if kind == "cf":
        return True, "neurons"
    return True, "free-tier"


def probe(spec: dict, model: str, key: str | None, timeout: int) -> tuple[int, float, str]:
    body = {"model": model, "messages": [{"role": "user", "content": "Reply with: ok"}],
            "max_tokens": 24, "temperature": 0}
    h = {"Authorization": f"Bearer {key}"} if key else {}
    t0 = time.time()
    try:
        r = S.post(spec["chat"], json=body, headers=h, timeout=timeout, allow_redirects=True)
        dt = time.time() - t0
        if r.status_code == 200:
            try:
                j = r.json()
            except Exception:
                return 200, dt, "non-json-200"
            ch = (j.get("choices") or [{}])[0]
            txt = ((ch.get("message") or {}).get("content") or "").strip().replace("\n", " ")[:30]
            if not txt:
                txt = f"finish={ch.get('finish_reason')}"
            return 200, dt, txt
        return r.status_code, dt, re.sub(r"\s+", " ", r.text)[:120]
    except Exception as e:
        return 0, time.time() - t0, f"{type(e).__name__}: {str(e)[:90]}"


def scan(spec: dict, probe_on: bool, max_per: int, workers: int) -> dict:
    spec = fmt(spec)
    rec: dict[str, Any] = {"provider": spec["name"], "models_url": spec["models"],
                           "chat_url": spec["chat"], "note": spec.get("note", ""),
                           "paid_skipped": bool(spec.get("paid")),
                           "alive": [], "dead": [], "catalog_status": None,
                           "catalog_error": "", "key_env": ""}
    if spec.get("paid"):
        rec["catalog_error"] = "paid provider — not scanned"
        return rec
    key, keyname = resolve_key(spec)
    rec["key_env"] = keyname
    # emit_yaml needs a REAL env-var name; a "dbpasses:<label>" source must be
    # translated back to the env var the launcher would have exported, otherwise
    # the YAML contains "api_key: os.environ/dbpasses:COHERE_TRIAL_API_KEY".
    rec["key_var"] = spec["key"][0] if keyname.startswith("dbpasses:") else keyname
    if not key and not spec.get("bearer"):
        rec["catalog_error"] = "no key in proxy env"
        return rec
    st, rows, err = catalog(spec, key)
    rec["catalog_status"] = st
    rec["catalog_error"] = err
    if not rows:
        return rec
    free = []
    for m in rows:
        ok, why = is_free(spec, m)
        if ok and mid(m):
            free.append({"id": mid(m), "ctx": ctx_of(m), "why": why, "row": m})
    rec["catalog_models"] = len(rows)
    rec["free_candidates"] = len(free)
    free.sort(key=lambda x: -(x["ctx"] or 0))
    free = free[:max_per]
    if not probe_on:
        rec["alive"] = [{"id": f["id"], "ctx": f["ctx"], "why": f["why"], "status": None} for f in free]
        return rec
    def work(f):
        stt, dt, note = probe(spec, f["id"], key, 90 if spec.get("slow") else DEFAULT_TIMEOUT)
        return {"id": f["id"], "ctx": f["ctx"], "why": f["why"], "status": stt,
                "sec": round(dt, 2), "note": note}
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(work, free):
            (rec["alive"] if r["status"] == 200 else rec["dead"]).append(r)
    return rec


def emit_yaml(recs: list[dict], path: Path, group: str = "DYNAMIC_FREE") -> int:
    """Write a LiteLLM model_list fragment: one group per provider + one combined."""
    lines = [f"# AUTO-GENERATED by tools/free_model_discovery.py — do not hand-edit.",
             f"# Regenerate: python3 tools/free_model_discovery.py --probe --emit-yaml {path.name}",
             f"# Verified free + HTTP 200 at generation time.", "",
             "model_list:"]
    total = 0
    for r in recs:
        alive = [a for a in r.get("alive") or [] if a.get("status") == 200]
        if not alive:
            continue
        envname = r.get("key_var") or r["key_env"]
        if envname.startswith("dbpasses:"):
            envname = ""
        pg = f"{group}_{re.sub(r'[^A-Z0-9]+', '_', r['provider'].upper())}"
        for a in alive:
            total += 1
            base = r["chat_url"].rsplit("/chat/completions", 1)[0]
            ctx = a.get("ctx")
            for gname in (pg, group):
                lines.append(f"  - model_name: {gname}")
                lines.append("    litellm_params:")
                lines.append(f"      model: openai/{a['id']}")
                if not envname or envname.startswith("(literal"):
                    lines.append("      api_key: unused")
                else:
                    lines.append(f"      api_key: os.environ/{envname}")
                lines.append(f"      api_base: {base}")
                if ctx:
                    lines.append(f"      weight: {max(1, min(10, ctx // 100_000 + 1))}")
                lines.append("    model_info:")
                lines.append("      mode: chat")
                if ctx:
                    lines.append(f"      max_input_tokens: {ctx}")
                lines.append("      input_cost_per_token: 0")
                lines.append("      output_cost_per_token: 0")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return total


def emit_env(path: Path) -> int:
    """Write KEY=VALUE lines for every provider whose key we could resolve.

    Lets a second LiteLLM instance be booted from the generated fragment without
    re-implementing the launcher's dbpasses parser:
        python3 tools/free_model_discovery.py --emit-env /tmp/free.env
        set -a; . /tmp/free.env; set +a
    """
    lines = ["# generated by tools/free_model_discovery.py --emit-env"]
    n = 0
    for spec in PROVIDERS:
        key, src = resolve_key(spec)
        if not key or src.startswith("(literal"):
            continue
        name = spec["key"][0] if src.startswith("dbpasses:") else src
        lines.append(f"{name}={key}")
        n += 1
        if spec.get("account"):
            acct = ENV.get(spec["account"], "")
            if acct:
                lines.append(f"{spec['account']}={acct}")
    path.write_text("\n".join(dict.fromkeys(lines)) + "\n", encoding="utf-8")
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="live chat-probe every free model")
    ap.add_argument("--no-probe", action="store_true", help="catalog only")
    ap.add_argument("--only", default="", help="comma-separated provider names")
    ap.add_argument("--max-per-provider", type=int, default=20)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default="")
    ap.add_argument("--emit-yaml", default="")
    ap.add_argument("--emit-env", default="")
    a = ap.parse_args()
    probe_on = a.probe and not a.no_probe
    only = {s.strip() for s in a.only.split(",") if s.strip()}
    specs = [p for p in PROVIDERS if not only or p["name"] in only]

    recs = []
    for spec in specs:
        rec = scan(spec, probe_on, a.max_per_provider, a.workers)
        recs.append(rec)
        nf = rec.get("free_candidates", 0)
        al = len(rec.get("alive") or [])
        dl = len(rec.get("dead") or [])
        bad = f" err={rec['catalog_error'][:40]}" if rec.get("catalog_error") else ""
        print(f"{rec['provider']:18} catalog={str(rec['catalog_status']):>4} "
              f"models={str(rec.get('catalog_models','-')):>4} free={nf:>3} "
              f"alive={al:>2} dead={dl:>2}{bad}")
        for x in (rec.get("alive") or [])[:6]:
            if x.get("status") == 200:
                print(f"    OK  {x['id'][:52]:54} ctx={str(x.get('ctx')):>8} {x.get('sec','')}s")

    if a.out:
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                   "probed": probe_on, "providers": recs}, indent=2), encoding="utf-8")
        print(f"\nreport -> {out}")
    if a.emit_yaml:
        n = emit_yaml(recs, Path(a.emit_yaml))
        print(f"yaml   -> {a.emit_yaml}  ({n} deployments)")
    if a.emit_env:
        n = emit_env(Path(a.emit_env))
        print(f"env    -> {a.emit_env}  ({n} keys)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
