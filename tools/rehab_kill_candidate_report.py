#!/usr/bin/env python3
"""Print rehabilitation hints for degraded strategies (real closed picks from payload).

Usage (repo root):
  python tools/rehab_kill_candidate_report.py
  python tools/rehab_kill_candidate_report.py --payload path/to/dashboard_data.json

Requires picks.recent_closed (or picks.closed list) with strategy, pnl_pct, symbol, direction.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from audit_trail.forward_degradation_tracker import (  # noqa: E402
    REHAB_CONFLUENCE_PARENT_STRATEGIES,
    compute_rehabilitation_hints,
)


def _load_closed(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        print("Failed to read JSON:", e, file=sys.stderr)
        return []
    picks = data.get("picks") or {}
    for key in ("recent_closed", "closed", "recent_resolved"):
        block = picks.get(key)
        if isinstance(block, list):
            return [p for p in block if isinstance(p, dict)]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--payload",
        type=Path,
        default=ROOT / "audit_dashboard" / "data" / "dashboard_data.json",
    )
    args = ap.parse_args()
    closed = _load_closed(args.payload)
    if not closed:
        print("No closed picks found. Pass --payload to dashboard_data.json")
        return 1
    print("Payload:", args.payload)
    print("Closed rows:", len(closed))
    print()
    for strat in sorted(REHAB_CONFLUENCE_PARENT_STRATEGIES):
        hints = compute_rehabilitation_hints(closed, strat)
        print("=" * 72)
        print(strat)
        print("=" * 72)
        for r in hints.get("recommendations") or []:
            print(" ", r)
        for wc in hints.get("winning_combos") or []:
            print(
                "  WIN_COMBO",
                wc.get("symbol"),
                wc.get("direction"),
                "n=%s wr=%s%% pnl=%s%%"
                % (wc.get("trades"), wc.get("win_rate"), wc.get("pnl_pct")),
            )
        if hints.get("inverse_candidate"):
            print("  inverse_candidate: True")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
