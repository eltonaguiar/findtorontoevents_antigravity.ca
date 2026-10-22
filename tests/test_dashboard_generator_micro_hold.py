"""Regression tests for the micro-hold (instant/synthetic fill) rejection fix.

Closes the "ultimate bug" class from reports/2026-10-22-forward-data-quality-audit.md
and the hold-time anomaly scan (tools/hold_time_anomaly_scan.py).

Background:
The dashboard counts resolved "closed" rows as performance even when the trade was
opened and closed within seconds at synthetic/same-tick prices. These instant/synthetic
fills pass every price-based impossibility check (prices are "plausible", direction is
consistent, pnl is a small positive number) so they inflate win rate, profit factor and
total PnL with phantom trades. Evidence: genome/data/closed_picks.json has 955 rows with
hold < 60s (mega_mutation_* family), 583 of them recorded as WON/TP_HIT, contributing
~+2200% phantom PnL to the aggregate.

The fix adds a minimum-hold-duration gate to `_is_valid_resolved_pick()`: when BOTH
entry and exit timestamps are present and the elapsed hold is below the floor, the row
is rejected from performance metrics. Rows missing either timestamp are NOT gated
(we never over-reject when we cannot compute a duration).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from audit_trail import dashboard_generator as dg  # noqa: E402


def _base_pick(**overrides) -> dict:
    """A minimal *genuine* resolved pick that MUST pass validity."""
    pick = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "asset_class": "CRYPTO",
        "strategy": "signal_validation",
        "entry_price": 30000.0,
        "exit_price": 31500.0,
        "pnl_pct": 5.0,
        "status": "WON",
        "exit_reason": "TP_HIT",
        "outcome": "WON",
    }
    pick.update(overrides)
    return pick


# ---------------------------------------------------------------------------
# Minimum-hold-duration gate
# ---------------------------------------------------------------------------

def test_rejects_instant_fill_subsecond_hold():
    """A TP_HIT winner opened/closed <1s apart is a synthetic fill, not a trade."""
    pick = _base_pick(
        entry_time="2026-10-22T10:00:00Z",
        exit_time="2026-10-22T10:00:00.500Z",
    )
    assert dg._is_valid_resolved_pick(pick) is False


def test_rejects_30s_hold_below_floor():
    pick = _base_pick(
        entry_time="2026-10-22T10:00:00Z",
        exit_time="2026-10-22T10:00:30Z",
    )
    assert dg._is_valid_resolved_pick(pick) is False


def test_accepts_genuine_hold_above_floor():
    """A real multi-minute/hour hold remains valid."""
    pick = _base_pick(
        entry_time="2026-10-22T10:00:00Z",
        exit_time="2026-10-22T12:30:00Z",
    )
    assert dg._is_valid_resolved_pick(pick) is True


def test_accepts_when_exit_timestamp_missing():
    """Cannot compute duration -> do NOT gate (never over-reject)."""
    pick = _base_pick(entry_time="2026-10-22T10:00:00Z")
    assert dg._is_valid_resolved_pick(pick) is True


def test_accepts_when_entry_timestamp_missing():
    pick = _base_pick(exit_time="2026-10-22T10:00:00Z")
    assert dg._is_valid_resolved_pick(pick) is True


def test_accepts_when_neither_timestamp_present():
    assert dg._is_valid_resolved_pick(_base_pick()) is True


def test_genome_mega_mutation_instant_row_rejected():
    """Reproduce the exact genome mega_mutation artifact signature."""
    pick = _base_pick(
        symbol="STXUSDT",
        strategy="mega_mutation_macd_rsi_m048",
        entry_price=0.2174,
        exit_price=0.222973,
        pnl_pct=-2.763,
        status="LOST",
        exit_reason="SL_HIT",
        outcome="LOST",
        entry_time="2026-10-22T00:00:00.100Z",
        exit_time="2026-10-22T00:00:00.640Z",
    )
    assert dg._is_valid_resolved_pick(pick) is False


def test_genome_uses_timestamp_key_as_entry():
    """Real genome rows stamp entry under `timestamp`, exit under `closed_at`.

    The fix must scan `timestamp`/`created_at` as entry candidates or it silently
    misses the exact mega_mutation micro-hold rows it was written to catch.
    """
    pick = _base_pick(
        symbol="STXUSDT",
        strategy="mega_mutation_macd_rsi_m048",
        entry_price=0.2174,
        exit_price=0.222973,
        pnl_pct=-2.763,
        status="LOST",
        exit_reason="SL_HIT",
        outcome="LOST",
        timestamp="2026-10-22T20:08:26.969578+00:00",
        closed_at="2026-10-22T20:08:27.513671+00:00",
    )
    assert dg._is_valid_resolved_pick(pick) is False
