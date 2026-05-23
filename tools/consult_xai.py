#!/usr/bin/env python3
"""Consult xAI Grok for a second opinion. Mirrors tools/consult_deepseek.py.

Reads prompt from stdin or a single positional path arg, POSTs to
https://api.x.ai/v1/chat/completions with model=grok-2-latest, writes
reports/consult_xai_<UTC>_<slug>.md.

Requires env X_AI (or GROK_SUPER, XAI_API_KEY).
"""
from __future__ import annotations
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
URL = "https://api.x.ai/v1/chat/completions"
MODEL = os.environ.get("XAI_MODEL", "grok-3-latest")

# Senior-quant-researcher persona. Blunt, specific, skeptical — no generic
# advice. Modeled on the SYSTEM string in tools/no_edge_cloud_consult.py so
# the one-off consult scripts match the better-engineered fan-out scripts.
SYSTEM = (
    "You are a senior quantitative researcher giving a second opinion to a "
    "small quant team. You are blunt, specific, and skeptical. You do NOT "
    "give generic trading-blog or generic-engineering advice (no 'open a "
    "broker account', no 'add unit tests', no 'consider edge cases' filler). "
    "Every point must be concrete, falsifiable, and directly actionable. If a "
    "fact in the prompt looks wrong, stale, or unverifiable, flag it before "
    "building on it. 'No edge / insufficient data / stop' is a fully valid "
    "answer and must be stated plainly if true — never manufacture a positive "
    "finding to seem useful."
)


def _read_prompt() -> tuple[str, str]:
    if len(sys.argv) > 1 and sys.argv[1] not in ("-", "--stdin"):
        p = Path(sys.argv[1])
        slug = re.sub(r"[^a-z0-9]+", "_", p.stem.lower()).strip("_")[:48]
        return p.read_text(encoding="utf-8"), slug or "prompt"
    return sys.stdin.read(), "stdin"


def main() -> int:
    key = (
        os.environ.get("X_AI")
        or os.environ.get("XAI_API_KEY")
        or os.environ.get("GROK_SUPER")
    )
    if not key:
        print("X_AI / XAI_API_KEY / GROK_SUPER not set in env", file=sys.stderr)
        return 1
    prompt, slug = _read_prompt()
    if not prompt.strip():
        print("empty prompt", file=sys.stderr)
        return 1
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 2000,
    }).encode("utf-8")
    req = urllib.request.Request(
        URL,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"xai error: {e}", file=sys.stderr)
        return 2
    elapsed = time.time() - t0
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = data.get("usage", {})
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = REPO / "reports"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"consult_xai_{ts}_{slug}.md"
    md = [
        f"# xAI Grok consult — {slug} ({ts})\n",
        f"Model: {MODEL}. Tokens: {usage}. Elapsed: {elapsed:.1f}s.\n",
        "## Prompt\n", "```", prompt[:8000], "```\n",
        "## Response\n", content, "\n",
    ]
    out_path.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
