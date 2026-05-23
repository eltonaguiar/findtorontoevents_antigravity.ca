"""
Regression test for the pnl_pct anomaly clamp added to
alpha_engine/mysql_trading_sync.py::pick_to_row 2026-05-09.

Reference: reports/db_query_bank_2026-05-07/FINDINGS.md Critical Finding #0
— forex pnl_pct ranged -106,700.679 to +95.58 across 2,071 rows in 90d,
swamping system-wide PF to 0.063.
"""
from __future__ import annotations

import logging

import pytest

from alpha_engine import mysql_trading_sync as m


def _base_pick(**overrides):
    pick = {
        "id": "p_test",
        "symbol": "EURUSD",
        "direction": "LONG",
        "category": "forex",
        "entry_price": 1.08,
        "status": "WON",
        "exit_reason": "TP_HIT",
        "created_at": None,
        "closed_at": None,
    }
    pick.update(overrides)
    return pick


def test_pnl_in_range_passes_through():
    row = m.pick_to_row(_base_pick(pnl_pct=-0.5))
    assert row["pnl_pct"] == -0.5


def test_pnl_at_lower_bound_passes():
    row = m.pick_to_row(_base_pick(pnl_pct=-100.0))
    assert row["pnl_pct"] == -100.0


def test_pnl_at_upper_bound_passes():
    row = m.pick_to_row(_base_pick(pnl_pct=200.0))
    assert row["pnl_pct"] == 200.0


def test_pnl_below_lower_bound_clamped_to_none(caplog):
    """The -106,700% forex anomaly must be dropped."""
    with caplog.at_level(logging.WARNING, logger="mysql_trading_sync"):
        row = m.pick_to_row(_base_pick(pnl_pct=-106700.679))
    assert row["pnl_pct"] is None
    assert any("anomaly clamp" in rec.message for rec in caplog.records)


def test_pnl_above_upper_bound_clamped_to_none(caplog):
    """A +201% pnl is unrealistic for our pick horizons — drop it."""
    with caplog.at_level(logging.WARNING, logger="mysql_trading_sync"):
        row = m.pick_to_row(_base_pick(pnl_pct=500.0, category="crypto", symbol="BTCUSDT"))
    assert row["pnl_pct"] is None
    assert any("anomaly clamp" in rec.message for rec in caplog.records)


def test_normal_winner_unchanged_with_warnings_off(caplog):
    """Sanity: a normal +5% TP_HIT shouldn't trigger any warning."""
    with caplog.at_level(logging.WARNING, logger="mysql_trading_sync"):
        row = m.pick_to_row(_base_pick(pnl_pct=5.0))
    assert row["pnl_pct"] == 5.0
    assert not any("anomaly clamp" in rec.message for rec in caplog.records)


def test_unrealized_pnl_field_also_clamped(caplog):
    """If pnl_pct is None but unrealized_pnl_pct is set, the same clamp applies."""
    pick = _base_pick(pnl_pct=None)
    pick["unrealized_pnl_pct"] = -50000.0
    with caplog.at_level(logging.WARNING, logger="mysql_trading_sync"):
        row = m.pick_to_row(pick)
    assert row["pnl_pct"] is None
    assert any("anomaly clamp" in rec.message for rec in caplog.records)


def test_none_pnl_stays_none():
    row = m.pick_to_row(_base_pick(pnl_pct=None))
    assert row["pnl_pct"] is None
