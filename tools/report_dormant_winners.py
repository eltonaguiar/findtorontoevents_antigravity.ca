#!/usr/bin/env python3
"""List leaderboard strategies with strong forward stats but few/no active picks.

Run from repo root:
  python tools/report_dormant_winners.py
  python tools/report_dormant_winners.py --min-trades 20 --min-wr 55
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_PAYLOAD = REPO / "audit_trail" / "data" / "dashboard_payload.json"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--payload", type=pathlib.Path, default=DEFAULT_PAYLOAD)
    p.add_argument("--min-trades", type=int, default=15)
    p.add_argument("--min-wr", type=float, default=55.0)
    p.add_argument("--max-active", type=int, default=1)
    args = p.parse_args()

    if not args.payload.is_file():
        print(f"Missing {args.payload}", file=sys.stderr)
        return 2

    data = json.loads(args.payload.read_text(encoding="utf-8"))
    lb = data.get("leaderboard") or []
    rows = []
    for r in lb:
        trades = int(r.get("fwd_trades") or 0)
        wr = float(r.get("fwd_wr") or 0)
        ap = int(r.get("active_picks") or 0)
        if trades < args.min_trades or wr < args.min_wr:
            continue
        if ap > args.max_active:
            continue
        rows.append(
            {
                "strategy": r.get("strategy"),
                "fwd_wr": wr,
                "fwd_trades": trades,
                "fwd_total_pnl": r.get("fwd_total_pnl"),
                "active_picks": ap,
                "systems": r.get("systems") or [],
            }
        )
    rows.sort(key=lambda x: (-x["fwd_wr"], -x["fwd_trades"]))
    print(f"Dormant high-performers (active_picks<={args.max_active}, trades>={args.min_trades}, wr>={args.min_wr}): {len(rows)}\n")
    for r in rows[:40]:
        print(
            f"{r['strategy'][:72]:72} | WR {r['fwd_wr']:.1f}% | n={r['fwd_trades']} | "
            f"pnl={r['fwd_total_pnl']} | act={r['active_picks']} | ROOT={r['systems']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
