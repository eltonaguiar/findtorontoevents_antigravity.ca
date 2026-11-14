#!/usr/bin/env python3
"""
daily_forward_tracker.py — Daily runner for mega_mutation forward validation.

Combines:
  1. Gated scanner — emits paper picks when entry conditions + regime gates pass
  2. Forward pilot — queries MySQL trading_picks for closed picks since pilot start,
     updates state.json with rolling 30d stats, checks promotion gates

Usage:
    python3 quick_wins/shared/daily_forward_tracker.py --once    # single daily run
    # Add to crontab: 0 9 * * * /path/to/python3 /path/to/daily_forward_tracker.py --once

Output:
    quick_wins/shared/daily_tracker_log.jsonl — one JSON line per run
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOG_PATH = Path(__file__).resolve().parent / "daily_tracker_log.jsonl"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_gated_scanner() -> dict:
    """Run the gated scanner once; return emit count and picks."""
    from quick_wins.shared.gated_scanner import scan, WINNING_COMBOS
    picks = scan(WINNING_COMBOS, existing_positions=[])
    seen = set()
    unique = []
    for p in picks:
        if p["pick_id"] not in seen:
            seen.add(p["pick_id"])
            unique.append(p)
    return {"emitted": len(unique), "picks": unique}


def run_forward_pilot() -> dict:
    """Run the forward pilot one-shot; return state summary."""
    from verified_strategies.paper_pilot.mega_mutation_forward_pilot import run_daily_tick
    state = run_daily_tick()
    return {
        "strategy": state["strategy_id"],
        "day_count": state["day_count"],
        "n_closed": state["rolling_30d_n_closed"],
        "wr": state["rolling_30d_wr"],
        "pf": state["rolling_30d_pf"],
        "promotion_ready": state["promotion_ready"],
        "production_enable": state["production_enable"],
        "blockers": state["blockers"],
        "last_tick_utc": state["last_tick_utc"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Daily forward tracker for mega_mutation")
    ap.add_argument("--once", action="store_true", help="Run one daily cycle and exit")
    args = ap.parse_args()

    result = {
        "ts": _utc_iso(),
        "scanner": None,
        "pilot": None,
    }

    try:
        result["scanner"] = run_gated_scanner()
    except Exception as exc:
        result["scanner"] = {"error": str(exc)}

    try:
        result["pilot"] = run_forward_pilot()
    except Exception as exc:
        result["pilot"] = {"error": str(exc)}

    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result, default=str) + "\n")

    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
