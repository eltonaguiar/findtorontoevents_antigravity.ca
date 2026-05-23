#!/usr/bin/env python3
"""Consult multiple Cerebras models for a second opinion.

Usage:
    # Read prompt from stdin (heredoc / pipe):
    py -3.14 tools/consult_cerebras.py < prompt.txt

    # Or pass path:
    py -3.14 tools/consult_cerebras.py path/to/prompt.md

    # Output: writes reports/consult_cerebras_<UTCstamp>.md with all responses.

Models queried (all free-tier friendly on Cerebras):
    - gpt-oss-120b      (largest, most capable)
    - llama-3.3-70b     (Meta, strong reasoning)
    - llama3.1-8b       (fast sanity-check)

Requires env var CEREBRAS_API (set on this box).
"""
from __future__ import annotations

import concurrent.futures
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from cerebras.cloud.sdk import Cerebras
except ImportError:
    print("Install the SDK:  py -3.14 -m pip install cerebras-cloud-sdk", file=sys.stderr)
    sys.exit(1)

REPO = Path(__file__).resolve().parent.parent
# Model IDs verified working on Cerebras on 2026-04-22.
# `llama-3.3-70b` (with dashes) returns 404 on the standard key; drop it.
MODELS = ["gpt-oss-120b", "llama3.1-8b"]

# Key preference order (first non-empty wins).
# Both env names observed: CEREBRAS_API (paid) + CERBRAS_FREE_ITHINK (free tier, user's spelling).
KEY_ENV_NAMES = ("CEREBRAS_API", "CEREBRAS_API_KEY", "CERBRAS_FREE_ITHINK")

# Senior-quant-researcher persona. Blunt, specific, skeptical — no generic
# advice. Modeled on the SYSTEM string in tools/no_edge_cloud_consult.py so
# the one-off consult scripts match the better-engineered fan-out scripts.
SYSTEM = (
    "You are a senior quantitative researcher giving a second opinion to a "
    "small quant team. You are blunt, specific, and skeptical. You do NOT "
    "give generic trading-blog or generic-engineering advice (no 'open a "
    "broker account', no 'add unit tests', no 'consider edge cases' filler). "
    "Every point must be concrete, falsifiable, and directly actionable. If "
    "the plan or a stated fact looks wrong, stale, or unverifiable, say so "
    "and explain why before building on it. If multiple options exist, rank "
    "them. 'No edge / insufficient data / stop' is a fully valid answer and "
    "must be stated plainly if true — never manufacture a positive finding "
    "to seem useful."
)


def query(client: Cerebras, model: str, prompt: str, timeout: int = 90) -> dict:
    t0 = time.time()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_completion_tokens=1800,
        )
        return {
            "model": model,
            "ok": True,
            "elapsed_s": round(time.time() - t0, 2),
            "content": resp.choices[0].message.content,
            "usage": {
                "prompt_tokens": resp.usage.prompt_tokens,
                "completion_tokens": resp.usage.completion_tokens,
            },
        }
    except Exception as exc:
        return {"model": model, "ok": False, "elapsed_s": round(time.time() - t0, 2), "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    key = None
    key_source = None
    for name in KEY_ENV_NAMES:
        if os.environ.get(name):
            key = os.environ[name]
            key_source = name
            break
    if not key:
        print(f"ERROR: no Cerebras key in env (checked {KEY_ENV_NAMES})", file=sys.stderr)
        return 1
    print(f"Using key from ${key_source}")

    if len(sys.argv) > 1:
        prompt = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        prompt = sys.stdin.read()

    if not prompt.strip():
        print("ERROR: empty prompt", file=sys.stderr)
        return 1

    print(f"Consulting {len(MODELS)} Cerebras models on a {len(prompt)}-char prompt...")
    client = Cerebras(api_key=key)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(MODELS)) as ex:
        futs = [ex.submit(query, client, m, prompt) for m in MODELS]
        results = [f.result() for f in futs]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = REPO / "reports" / f"consult_cerebras_{stamp}.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [f"# Cerebras Multi-Model Consultation\n\n**Run:** {stamp}\n"]
    lines.append("## Prompt\n")
    lines.append("```")
    lines.append(prompt.rstrip())
    lines.append("```\n")
    for r in results:
        lines.append(f"\n---\n\n## {r['model']}  ({'OK' if r['ok'] else 'FAILED'}, {r['elapsed_s']}s)\n")
        if r["ok"]:
            lines.append(f"_tokens: prompt={r['usage']['prompt_tokens']} / completion={r['usage']['completion_tokens']}_\n")
            lines.append(r["content"])
        else:
            lines.append(f"**error:** `{r['error']}`")
    out.write_text("\n".join(lines), encoding="utf-8")

    print(f"\nReport -> {out.relative_to(REPO)}")
    for r in results:
        tag = "OK" if r["ok"] else "FAIL"
        tok = r["usage"]["completion_tokens"] if r["ok"] else 0
        print(f"  [{tag}] {r['model']:18s}  {r['elapsed_s']:>5.1f}s  {tok} completion tokens")
    return 0


if __name__ == "__main__":
    sys.exit(main())
