#!/usr/bin/env python3
"""
Update account_snapshot in audit_dashboard/data/hyrotrader_picks.json from the CLI.

  python tools/hyrotrader_update_snapshot.py --equity 4929.34 --pnl -70.66 --day-start 5000 --high-water 5070.3

Does not touch picks[] or challenge blocks. Writes JSON with stable key order via round-trip.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
JSON_PATH = WORKSPACE / "audit_dashboard" / "data" / "hyrotrader_picks.json"


def main() -> None:
    p = argparse.ArgumentParser(description="Update Hyro account_snapshot in hyrotrader_picks.json")
    p.add_argument("--equity", type=float, help="equity_usdt (current balance)")
    p.add_argument("--day-start", type=float, dest="day_start", help="day_start_equity_usdt")
    p.add_argument("--pnl", type=float, dest="cumulative_pnl", help="cumulative_pnl_usdt")
    p.add_argument("--high-water", type=float, dest="high_water", help="high_water_equity_usdt (session/eval peak)")
    p.add_argument("--challenge-start", type=float, dest="challenge_start", help="challenge_start_equity_usdt")
    p.add_argument("--trading-days", type=int, dest="trading_days", help="trading_days_logged")
    p.add_argument("--phase", type=int, dest="eval_phase", help="eval_phase (1 or 2)")
    p.add_argument("--phase-label", dest="phase_label", help='hyro_phase_label e.g. "2-Step · Phase 1"')
    p.add_argument("--best-day", type=float, dest="best_day", help="largest_single_day_profit_usdt (green day)")
    args = p.parse_args()

    if not JSON_PATH.is_file():
        raise SystemExit(f"Missing {JSON_PATH}")

    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    snap = data.get("account_snapshot")
    if not isinstance(snap, dict):
        raise SystemExit("account_snapshot missing or not an object")

    if args.equity is not None:
        snap["equity_usdt"] = args.equity
    if args.day_start is not None:
        snap["day_start_equity_usdt"] = args.day_start
    if args.cumulative_pnl is not None:
        snap["cumulative_pnl_usdt"] = args.cumulative_pnl
    if args.high_water is not None:
        snap["high_water_equity_usdt"] = args.high_water
    if args.challenge_start is not None:
        snap["challenge_start_equity_usdt"] = args.challenge_start
    if args.trading_days is not None:
        snap["trading_days_logged"] = args.trading_days
    if args.eval_phase is not None:
        snap["eval_phase"] = args.eval_phase
    if args.phase_label is not None:
        snap["hyro_phase_label"] = args.phase_label
    if args.best_day is not None:
        snap["largest_single_day_profit_usdt"] = args.best_day

    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated account_snapshot in {JSON_PATH}")


if __name__ == "__main__":
    main()
