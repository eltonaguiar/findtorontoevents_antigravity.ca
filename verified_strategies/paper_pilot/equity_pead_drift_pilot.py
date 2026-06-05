#!/usr/bin/env python3
"""PEAD drift-lane paper pilot — repo earnings cache + extended window."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT_DIR = Path(__file__).resolve().parent
LOG_PATH = PILOT_DIR / "equity_pead_drift_paper_log.jsonl"
STATE_PATH = PILOT_DIR / "equity_pead_drift_state.json"
STRATEGY_ID = "equity_pead_drift"
DRIFT_UNIVERSE = ["GOOGL", "MSFT", "AAPL", "XYZ", "NVDA", "META", "AMZN"]


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"strategy_id": STRATEGY_ID, "started_at": _utc_today(), "last_run": None}


def _save_state(state: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _append_log(row: dict) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def run_one_shot() -> dict:
    os.environ.setdefault("EQUITY_PEAD_ENABLED", "1")
    os.environ.setdefault("PEAD_DRIFT_MAX_DAYS", "30")
    from alpha_engine.equity_pead_strategy import equity_pead_signals

    today = _utc_today()
    signals = equity_pead_signals(DRIFT_UNIVERSE)
    state = _load_state()
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    state["last_signals"] = signals
    state["drift_max_days"] = int(os.environ.get("PEAD_DRIFT_MAX_DAYS", "30"))
    _save_state(state)
    for s in signals:
        s["source_system"] = "equity_pead_drift_pilot"
        s["strategy"] = STRATEGY_ID
        _append_log({"date": today, "event": "SIGNAL", **s})
    return {
        "date": today,
        "strategy": STRATEGY_ID,
        "drift_max_days": state["drift_max_days"],
        "signals": len(signals),
        "picks": [
            {"symbol": s.get("symbol"), "surprise_pct": s.get("earnings_surprise_pct"),
             "days_since": s.get("days_since_earnings")}
            for s in signals
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--one-shot", action="store_true")
    args = ap.parse_args(argv)
    if not args.one_shot:
        ap.print_help()
        return 0
    print(json.dumps(run_one_shot(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
