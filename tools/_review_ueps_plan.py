"""Final review of UEPS gate fix plan — single reviewer (DeepSeek)."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLAN = REPO / "reports" / "UEPS_GATE_FIX_PLAN_2026_05_01.md"
OUT = REPO / "reports" / "feedback" / "deepseek-ueps-plan-FINAL.md"


SYSTEM = """You are the final reviewer of a small, focused gate-fix plan for a
multi-asset alpha pipeline. The plan was written after a 3-AI panel (DeepSeek,
Cerebras Qwen, xAI Grok) unanimously selected Option B (env-flag-gated long-
horizon bypass for source=ueps + TF=POSITION). Your job:

1. CONSENSUS-FAITHFULNESS: does the plan correctly implement Option B as the panel meant it?
2. TEST COVERAGE: are the 6 tests sufficient? anything missing?
3. RISK FOOTGUNS: anything in the implementation guard logic that could leak into non-UEPS picks?
4. CLAUDE.md COMPLIANCE: default-OFF, 14d shadow, Wire-Up Rule, single-file scope?
5. FINAL VERDICT: SHIP-AS-IS / SHIP-WITH-MINOR-EDITS / NEEDS-REVISION.

<300 words total."""


def main():
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API")
    if not key:
        print("ERROR: no DeepSeek key")
        sys.exit(1)
    plan = PLAN.read_text(encoding="utf-8")
    body = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Review plan:\n\n" + plan},
        ],
        "max_tokens": 700,
        "temperature": 0.1,
    }
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key.strip()}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        d = json.loads(resp.read().decode("utf-8", errors="replace"))
    msg = d["choices"][0]["message"]
    content = msg.get("content", "") or msg.get("reasoning_content", "")
    OUT.write_text(content, encoding="utf-8")
    try:
        print(content)
    except Exception:
        print(f"OK ({len(content)} chars)")


if __name__ == "__main__":
    main()
