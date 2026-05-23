"""Final review of action plan v2 — single reviewer (DeepSeek)."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLAN_V1 = REPO / "reports" / "ACTION_PLAN_2026_05_01_DRAFT.md"
PLAN_V2 = REPO / "reports" / "ACTION_PLAN_2026_05_01_V2.md"
OUT = REPO / "reports" / "feedback" / "deepseek-action-plan-v2-FINAL.md"


SYSTEM = """You are the final reviewer of action plan v2 for a multi-asset hedge-fund alpha pipeline. v2 was rewritten after 5 AI reviewers flagged issues with v1 (B9 dependency error, B25 missing diagnostic, 14-day shadow rule, B7 wire-up rule). Your job: confirm v2 closes the consensus blockers AND that no new contradictions were introduced.

Reply in 3 short sections, total <300 words:
1. CONSENSUS-BLOCKER STATUS: For each of the 4 consensus blockers (B9, B25, 14-day shadow, B7 wire-up), state PASS / FAIL / PARTIAL with one sentence why.
2. NEW CONTRADICTIONS INTRODUCED: List anything v2 broke that v1 had right, OR anything still inconsistent.
3. FINAL VERDICT: SHIP-AS-IS / SHIP-WITH-MINOR-EDITS / NEEDS-REVISION-V3."""


def main():
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API")
    if not key:
        print("ERROR: no DeepSeek key")
        sys.exit(1)
    v2 = PLAN_V2.read_text(encoding="utf-8")
    body = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Review this v2:\n\n" + v2},
        ],
        "max_tokens": 600,
        "temperature": 0.1,
    }
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key.strip()}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        d = json.loads(resp.read().decode("utf-8", errors="replace"))
    msg = d["choices"][0]["message"]
    content = msg.get("content", "") or msg.get("reasoning_content", "")
    OUT.write_text(content, encoding="utf-8")
    print(content)


if __name__ == "__main__":
    main()
