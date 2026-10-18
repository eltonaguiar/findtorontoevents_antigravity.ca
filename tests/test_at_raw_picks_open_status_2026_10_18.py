"""Regression tests for the 2026-10-18 at_raw_picks integrity fixes.

Background (see updates/2026-10-18-audit-picks-quality-per-class-review.md):

1. ``at_raw_picks.status`` was never written by ``record_raw_pick()`` — all 3,126
   NULL-status rows have ``closed_at IS NULL`` (verified 100% against production),
   yet the recency sidecar only counted ``status IN ('OPEN','ACTIVE')`` as active.
   Result: every asset class reported ``n_active=0`` while the dashboard showed
   live actives.

2. 38 TIME_EXIT rows reached ``picks.recent_closed`` with ``exit_price=0.0`` and
   ``pnl_pct=0.0`` — arithmetic performed on a failed price fetch, published as if
   it were a flat trade.

These tests pin both behaviours so neither can silently regress.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from tools.audit_pick_funnel.build_recency_summary import _classify_rows
from audit_trail.universal_pick_resolver import _priceless_close, _compute_pnl
import audit_trail.mysql_client as mysql_client

NOW = datetime(2026, 10, 18, 4, 0, 0)
CUTOFF = NOW - timedelta(hours=48)


def _row(symbol, asset_class, status, closed_at=None, pnl=None):
    return {
        "symbol": symbol,
        "asset_class": asset_class,
        "direction": "LONG",
        "source_system": "AlphaEngine",
        "strategy": "test_strategy",
        "confidence": 0.5,
        "signal_timestamp": NOW - timedelta(hours=1),
        "closed_at": closed_at,
        "status": status,
        "pnl_pct": pnl,
    }


# ── 1. NULL status must be treated as an open pick ───────────────────────────

def test_null_status_unclosed_counts_as_active():
    rows = [_row("EURUSD=X", "FOREX", None)]
    out = _classify_rows(rows, "last_48_hours", CUTOFF, False)
    assert out["FOREX"]["n_active"] == 1
    assert out["FOREX"]["n_closed"] == 0


def test_null_status_with_closed_at_is_not_active():
    """A row that is already closed must not be resurrected as active just
    because a writer set closed_at without setting status."""
    rows = [_row("V", "EQUITY", None, closed_at=NOW)]
    out = _classify_rows(rows, "last_48_hours", CUTOFF, False)
    assert out["EQUITY"]["n_active"] == 0


def test_explicit_open_still_counts_as_active():
    rows = [_row("BTCUSDT", "CRYPTO", "OPEN"), _row("ETHUSDT", "CRYPTO", "ACTIVE")]
    out = _classify_rows(rows, "last_48_hours", CUTOFF, False)
    assert out["CRYPTO"]["n_active"] == 2


def test_terminal_statuses_are_not_active():
    rows = [
        _row("SOLUSDT", "CRYPTO", "WON", closed_at=NOW, pnl=1.5),
        _row("XRPUSDT", "CRYPTO", "LOST", closed_at=NOW, pnl=-1.5),
        _row("BNBUSDT", "CRYPTO", "EXPIRED", closed_at=NOW, pnl=0.0),
    ]
    out = _classify_rows(rows, "last_48_hours", CUTOFF, False)
    assert out["CRYPTO"]["n_active"] == 0
    assert out["CRYPTO"]["n_closed"] == 3


def test_mixed_cohort_counts_active_and_closed_independently():
    rows = [
        _row("EURUSD=X", "FOREX", None),              # open via NULL
        _row("GBPUSD=X", "FOREX", "OPEN"),            # open via explicit
        _row("AUDUSD=X", "FOREX", "LOST", closed_at=NOW, pnl=-2.0),  # closed
    ]
    out = _classify_rows(rows, "last_48_hours", CUTOFF, False)
    assert out["FOREX"]["n_active"] == 2
    assert out["FOREX"]["n_closed"] == 1
    assert out["FOREX"]["n_touched"] == 3


# ── 2. A priceless close must not be published as a flat 0% ─────────────────

def test_priceless_close_rejects_zero_exit_price():
    """The exact defect: exit_price=0.0 with a real entry."""
    assert _priceless_close(0.0, 383.9) is True


def test_priceless_close_rejects_missing_entry():
    """entry missing -> _compute_pnl returns 0.0, which would fabricate a flat."""
    assert _priceless_close(100.0, None) is True
    assert _priceless_close(100.0, 0) is True


def test_priceless_close_rejects_none_or_negative_price():
    assert _priceless_close(None, 383.9) is True
    assert _priceless_close(-5.0, 383.9) is True
    assert _priceless_close("not-a-price", 383.9) is True


def test_priceless_close_accepts_a_real_price():
    assert _priceless_close(383.9, 380.0) is False
    assert _priceless_close(1.1234, 1.1000) is False


def test_zero_exit_price_would_have_produced_the_published_38():
    """Reproduces the numbers seen on production: entry 383.9, exit 0.0.

    Without the guard this computes a confident -100%, and with a missing entry
    it computes exactly 0.0 — either way it is fabricated, so the guard must fire.
    """
    assert _priceless_close(0.0, 383.9) is True          # fabricated -100% case
    assert _priceless_close(0.0, None) is True           # fabricated 0.0 case
    # the honest computation is only used when a real price exists
    assert _compute_pnl(383.9, 385.0, "LONG") != 0.0


# ── 3. The INSERT must declare status, or the NULL marker comes back ────────

def test_record_raw_pick_sql_declares_status_open():
    src = open(mysql_client.__file__, encoding="utf-8", errors="replace").read()
    assert "INSERT IGNORE INTO at_raw_picks" in src
    # column list must include status, and the value list must pin 'OPEN'
    assert "'aggregator','OPEN')" in src.replace(" ", "").replace("\r", ""), (
        "record_raw_pick() no longer declares status='OPEN' — NULL status will "
        "re-appear in at_raw_picks and every DB-backed active counter will "
        "read 0 again"
    )
