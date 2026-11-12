#!/usr/bin/env python3
"""Ask several independent LLM providers the same question, in parallel.

Keys come from the environment only; nothing is read from disk and nothing is printed.
Missing keys simply skip that provider, so the script is safe to run anywhere.

Local endpoints (vLLM :8000, Ollama :11434, LiteLLM :4000) and keyless endpoints
(Pollinations, Hack Club AI) are first-class providers: they need no key at all.

    python3 ask.py "is this diagnosis right?"
    python3 ask.py --context notes.md "review this plan"
    python3 ask.py --only groq,gemini,vllm --model vllm=@discover "quick check"
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import os
import sys
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (compatible; second-opinion/1.1)"
TIMEOUT = 120
DISCOVER = "@discover"

# (name, base endpoint, env var or None for keyless, model IDs to try, extra body)
PROVIDERS = [
    # --- local, zero latency, zero key -------------------------------------
    ("vllm", "http://localhost:8000/v1", None, [DISCOVER], {}),
    ("ollama", "http://localhost:11434/v1", None, [DISCOVER], {}),
    ("litellm", "http://localhost:4000/v1", None, [DISCOVER], {}),
    # --- keyless public endpoints ------------------------------------------
    ("pollinations", "https://text.pollinations.ai/openai", None, ["openai"], {}),
    ("hackclub", "https://ai.hackclub.com", None, ["llama-3.3-70b-versatile"], {}),
    # --- keyed free tiers ---------------------------------------------------
    ("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY",
     ["openai/gpt-oss-120b", "llama-3.3-70b-versatile"], {}),
    ("gemini", "https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY",
     ["gemini-2.5-flash"], {}),
    ("mistral", "https://api.mistral.ai/v1", "MISTRAL_API_KEY",
     ["mistral-small-latest", "ministral-8b-2512"], {}),
    ("openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY",
     ["meta-llama/llama-3.3-70b-instruct:free", "nvidia/nemotron-3.5-lightning:free"], {}),
    # Inception Mercury retired 2026-12-28 (service sunset). Cerebras replaces it
    # as the fastest third-party peer (~600 tok/s on gpt-oss-120b).
    ("cerebras", "https://api.cerebras.ai/v1", "CEREBRAS_API_KEY",
     ["gpt-oss-120b", "llama-3.3-70b"], {}),
]

SYSTEM = (
    "You are a blunt senior reviewer. Answer the question directly, in the length asked for. "
    "Say what you would do differently and name the failure mode you expect if this goes wrong. "
    "Do not restate the question, do not hedge, do not pad with praise."
)


def _headers(key: str | None) -> dict:
    h = {"Content-Type": "application/json", "User-Agent": UA}
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h


def discover(base: str, key: str | None) -> list[str]:
    """Model IDs a provider advertises; empty when the endpoint has no /models."""
    req = urllib.request.Request(f"{base}/models", headers=_headers(key))
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception:
        return []
    items = data.get("data", data if isinstance(data, list) else [])
    return [m.get("id") for m in items if isinstance(m, dict) and m.get("id")]


def call(base: str, key: str | None, model: str, question: str, extra: dict) -> tuple[str, str]:
    body = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}],
        "temperature": 0.3,
        "max_tokens": 700,
        **extra,
    }
    req = urllib.request.Request(f"{base}/chat/completions",
                                 data=json.dumps(body).encode(), headers=_headers(key))
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read())
    return model, (data["choices"][0]["message"].get("content") or "").strip()


def ask(provider, question: str, overrides: dict) -> dict:
    name, base, env, models, extra = provider
    key = os.environ.get(env) if env else None
    if env and not key:
        return {"provider": name, "error": f"{env} not set"}
    models = [overrides[name]] if name in overrides else list(models)
    if models == [DISCOVER]:
        found = [m for m in discover(base, key) if not any(x in m.lower() for x in ("embed", "rerank"))]
        models = found[:2]
        if not models:
            return {"provider": name, "error": "endpoint unreachable or advertises no models"}
    last = ""
    for model in models:
        try:
            used, text = call(base, key, model, question, extra)
            if not text:
                last = f"{model}: empty content"
                continue
            return {"provider": name, "model": used, "text": text}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:160]
            last = f"{model}: HTTP {e.code} {detail}"
            if e.code in (400, 404):      # model id not valid for this account
                continue
            break
        except Exception as e:            # noqa: BLE001 - report, don't crash the fan-out
            last = f"{model}: {type(e).__name__} {str(e)[:120]}"
            break
    return {"provider": name, "error": last}


def main() -> int:
    ap = argparse.ArgumentParser(description="fan a question out to independent LLM providers")
    ap.add_argument("question", nargs="+")
    ap.add_argument("--context", help="file whose contents are prepended to the question")
    ap.add_argument("--only", help="comma-separated provider names to use")
    ap.add_argument("--model", action="append", default=[],
                    help="provider=model override, repeatable")
    ap.add_argument("--json", action="store_true", help="emit raw JSON instead of markdown")
    args = ap.parse_args()

    question = " ".join(args.question)
    if args.context:
        with open(args.context, encoding="utf-8") as fh:
            question = f"{fh.read().strip()}\n\n---\n\n{question}"

    wanted = {p.strip() for p in args.only.split(",")} if args.only else None
    overrides = dict(m.split("=", 1) for m in args.model if "=" in m)
    pool = [p for p in PROVIDERS if wanted is None or p[0] in wanted]

    with futures.ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(lambda p: ask(p, question, overrides), pool))

    if args.json:
        print(json.dumps(results, indent=1))
        return 0 if any("text" in r for r in results) else 1

    answered = 0
    for r in results:
        if "text" in r:
            answered += 1
            print(f"\n## {r['provider']} ({r['model']})\n\n{r['text']}")
        else:
            print(f"\n## {r['provider']} — SKIPPED/FAILED\n\n{r['error']}")
    print(f"\n---\n{answered}/{len(results)} providers answered")
    return 0 if answered else 1


if __name__ == "__main__":
    sys.exit(main())
