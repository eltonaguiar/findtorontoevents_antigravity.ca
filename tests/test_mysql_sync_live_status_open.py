"""Live pick status normalization in mysql_trading_sync.pick_to_row."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alpha_engine.mysql_trading_sync import pick_to_row


def test_missing_status_defaults_to_open():
    row = pick_to_row({"id": "t1", "symbol": "BTCUSDT", "direction": "LONG"})
    assert row["status"] == "OPEN"


def test_active_live_pick_maps_to_open():
    row = pick_to_row(
        {
            "id": "t2",
            "symbol": "ETHUSDT",
            "direction": "LONG",
            "status": "ACTIVE",
        }
    )
    assert row["status"] == "OPEN"


def test_active_with_exit_reason_not_mapped_to_open():
    row = pick_to_row(
        {
            "id": "t3",
            "symbol": "SPY",
            "direction": "LONG",
            "status": "ACTIVE",
            "exit_reason": "TIME_EXIT",
            "pnl_pct": 0.0,
        }
    )
    assert row["status"] == "ACTIVE"
