"""Regression: entry_time/exit_time fallback in mysql_trading_sync.

battleground/data/closed_picks.json + alpha_engine/data/active_picks.json
emit `entry_time` and `exit_time` keys (not created_at / closed_at). Without
fallback support, 115 battleground closed picks per file land in MySQL with
NULL timestamps. Confirmed dry-run: 76 of 115 had matching DB rows missing
the timestamp; would all be repaired by the writer fix on next sync.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alpha_engine.mysql_trading_sync import pick_to_row


def _base(**kw):
    p = {"id": "test", "symbol": "BTCUSDT", "direction": "LONG", "status": "ACTIVE"}
    p.update(kw)
    return p


def test_entry_time_fills_created_at():
    """battleground closed_picks.json case: entry_time only."""
    r = pick_to_row(_base(entry_time="2026-02-24T06:00:00+00:00"))
    assert r["created_at"] is not None
    assert "2026-02-24" in r["created_at"]


def test_exit_time_fills_closed_at():
    """battleground closed_picks.json case: exit_time only, on closed pick."""
    r = pick_to_row(_base(
        status="WIN", exit_reason="TP",
        exit_time="2026-02-24T18:00:00+00:00",
        entry_time="2026-02-24T06:00:00+00:00",
    ))
    assert r["closed_at"] is not None
    assert "2026-02-24 18:00:00" in r["closed_at"]


def test_created_at_takes_precedence_over_entry_time():
    """If both present, created_at wins (legacy field is canonical)."""
    r = pick_to_row(_base(
        created_at="2026-05-10T10:00:00Z",
        entry_time="2026-02-24T06:00:00+00:00",
    ))
    assert r["created_at"] is not None
    assert "2026-05-10" in r["created_at"]


def test_closed_at_takes_precedence_over_exit_time():
    r = pick_to_row(_base(
        status="WIN", exit_reason="TP",
        closed_at="2026-05-10T20:00:00Z",
        exit_time="2026-02-24T18:00:00+00:00",
    ))
    assert "2026-05-10 20:00:00" in r["closed_at"]


def test_no_fields_present_stays_none():
    """Pick with neither created_at nor entry_time → DB NULL preserved."""
    r = pick_to_row(_base())
    assert r["created_at"] is None
    assert r["closed_at"] is None


def test_battleground_realistic_row():
    """Replays a real battleground/data/closed_picks.json shape."""
    bg = {
        "id": "bg_001",
        "symbol": "ETHUSDT",
        "direction": "LONG",
        "strategy": "drawdown_recovery_rsi_eth",
        "entry_price": 2300.0,
        "take_profit": 2369.0,
        "stop_loss": 2240.0,
        "confidence": 0.65,
        "status": "WIN",
        "exit_reason": "TP_HIT",
        "pnl_pct": 3.0,
        "entry_time": "2026-02-24T06:00:00+00:00",
        "exit_time": "2026-02-24T18:00:00+00:00",
        "source_system": "battleground",
    }
    r = pick_to_row(bg)
    assert r["created_at"] is not None
    assert r["closed_at"] is not None
    assert r["pnl_pct"] == 3.0
    assert r["source_system"] == "battleground"


def test_active_pick_with_entry_time_only():
    """ACTIVE picks shouldn't get a closed_at even if exit_time is mistakenly set."""
    r = pick_to_row(_base(
        status="ACTIVE",
        entry_time="2026-05-10T10:00:00Z",
    ))
    assert r["created_at"] is not None
    assert r["closed_at"] is None  # ACTIVE → closed_at always None
