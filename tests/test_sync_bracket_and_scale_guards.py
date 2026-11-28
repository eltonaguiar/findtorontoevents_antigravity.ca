"""Ingest-time guards added 2026-11-28.

`mysql_trading_sync` is the single production INSERT path into `trading_picks`.
A data-only repair regrows on the next sync, so the guards that motivated the
2026-11-28 cleanup live here:

  * bracket geometry — a take_profit/stop_loss on the wrong side of its own
    entry, or more than 100x away (the audit found 2,283 such rows)
  * price scale now also covers CRYPTO/MEMECOIN, which used to be bypassed
    (ARBUSDT entry 0.000629 vs a real 0.1148 = 182x)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.mysql_trading_sync import (  # noqa: E402
    _ENTRY_SCALE_THRESHOLD_BY_CLASS,
    _validate_bracket_geometry,
    _validate_entry_price_scale,
    _validate_exit_price_scale,
)


# ── bracket geometry ────────────────────────────────────────────────────────

@pytest.mark.parametrize("direction", ["LONG", "BUY", "long", " BUY_LONG "])
def test_long_with_stop_above_entry_is_rejected(direction):
    ok, reason = _validate_bracket_geometry(100.0, 120.0, 105.0, direction)
    assert ok is False
    assert "wrong side" in reason


@pytest.mark.parametrize("direction", ["LONG", "BUY"])
def test_long_with_take_profit_below_entry_is_rejected(direction):
    ok, reason = _validate_bracket_geometry(100.0, 90.0, 95.0, direction)
    assert ok is False
    assert "take_profit" in reason


@pytest.mark.parametrize("direction", ["SHORT", "SELL", "short"])
def test_short_with_take_profit_above_entry_is_rejected(direction):
    ok, reason = _validate_bracket_geometry(100.0, 110.0, 105.0, direction)
    assert ok is False
    assert "wrong side" in reason


@pytest.mark.parametrize("direction", ["SHORT", "SELL"])
def test_short_with_stop_below_entry_is_rejected(direction):
    ok, reason = _validate_bracket_geometry(100.0, 90.0, 95.0, direction)
    assert ok is False
    assert "stop_loss" in reason


def test_correct_long_bracket_passes():
    ok, reason = _validate_bracket_geometry(100.0, 110.0, 95.0, "LONG")
    assert ok is True, reason


def test_correct_short_bracket_passes():
    ok, reason = _validate_bracket_geometry(100.0, 90.0, 105.0, "SHORT")
    assert ok is True, reason


def test_missing_bracket_levels_pass():
    """Open picks without a bracket are not this guard's business."""
    assert _validate_bracket_geometry(100.0, None, None, "LONG")[0] is True
    assert _validate_bracket_geometry(100.0, None, 95.0, "LONG")[0] is True


def test_absurd_bracket_multiple_is_rejected():
    # The real row: take_profit 4433.71 on a token priced 0.00000475.
    ok, reason = _validate_bracket_geometry(0.00000475, 4433.70614375, None, "LONG")
    assert ok is False
    assert "x from entry" in reason


def test_nonpositive_bracket_level_is_rejected():
    ok, reason = _validate_bracket_geometry(100.0, 0.0, 95.0, "LONG")
    assert ok is False
    assert "<=" in reason


def test_no_entry_means_no_verdict():
    assert _validate_bracket_geometry(None, 1.0, 2.0, "LONG")[0] is True
    assert _validate_bracket_geometry(0, 1.0, 2.0, "LONG")[0] is True


def test_unknown_direction_still_enforces_multiple():
    ok, reason = _validate_bracket_geometry(100.0, 20000.0, None, "")
    assert ok is False
    assert "x from entry" in reason


# ── price scale, now covering crypto ────────────────────────────────────────

def test_crypto_threshold_exists():
    """Crypto used to short-circuit the scale guard entirely."""
    assert "CRYPTO" in _ENTRY_SCALE_THRESHOLD_BY_CLASS
    assert "MEMECOIN" in _ENTRY_SCALE_THRESHOLD_BY_CLASS
    assert _ENTRY_SCALE_THRESHOLD_BY_CLASS["CRYPTO"] == 20.0


def test_off_scale_crypto_entry_is_rejected():
    # ARBUSDT: entry recorded at the wrong decimal scale (182x from real).
    ok, reason = _validate_entry_price_scale(
        "ARBUSDT", 0.000629, "CRYPTO", {"ARBUSDT": 0.1148}
    )
    assert ok is False
    assert "ratio" in reason


def test_plausible_crypto_entry_passes():
    ok, reason = _validate_entry_price_scale(
        "ARBUSDT", 0.1120, "CRYPTO", {"ARBUSDT": 0.1148}
    )
    assert ok is True, reason


def test_crypto_entry_within_threshold_but_displaced_passes():
    """A 10x drift is below the 20x crypto threshold — deliberately lenient."""
    ok, reason = _validate_entry_price_scale(
        "SOMECOIN", 1.0, "CRYPTO", {"SOMECOIN": 10.0}
    )
    assert ok is True, reason


def test_off_scale_crypto_exit_is_rejected():
    ok, reason = _validate_exit_price_scale(
        "SHIBUSDT", 4016.41, "CRYPTO", {"SHIBUSDT": 0.00000475}
    )
    assert ok is False
    assert "ratio" in reason


def test_missing_ohlcv_passes_gracefully():
    """No bar for the symbol must never block a pick."""
    assert _validate_entry_price_scale("NODATA", 1.0, "CRYPTO", {})[0] is True
    assert _validate_exit_price_scale("NODATA", 1.0, "CRYPTO", {})[0] is True
