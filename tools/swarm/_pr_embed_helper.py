"""Internal helper used by swarm_dispatch.ps1 to embed a captured PR
artifact JSON into a prompt template via _pr_capture.embed_into_prompt.

Standalone so PowerShell does not need to inline a multi-line `python -c`
(fragile under PSv7 quoting rules) and so the embed step can be smoke-
tested independently of a full dispatch run.

Usage:
    python tools/swarm/_pr_embed_helper.py \\
        --template tools/swarm/prompts/pr_review_inline.md \\
        --capture  swarm_runs/<TS>/pr_<n>_capture.json \\
        --out      swarm_runs/<TS>/pr_<n>_prompt.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _pr_capture import embed_into_prompt  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--capture", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    template = Path(args.template).read_text(encoding="utf-8")
    capture = json.loads(Path(args.capture).read_text(encoding="utf-8"))
    body = embed_into_prompt(template, capture)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
