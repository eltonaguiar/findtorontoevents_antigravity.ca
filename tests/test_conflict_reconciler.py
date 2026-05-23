"""Network-free unit tests for the book-level direction-conflict reconciler.

Covers: conflict detection, higher-conviction-side kept, tie-band drops-both,
non-conflicted passthrough, fail-open on bad data, and confirmation that the
function never mutates its input. The shadow/enforce env flag is exercised
indirectly here via DEFAULT_TIE_BAND / CONFLICT_TIE_BAND; the scanner.py
wiring (DIRECTION_CONFLICT_RECONCILER default OFF) is a thin caller and is
asserted by inspection of the import block.

Run: python -m pytest tests/test_conflict_reconciler.py -q
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine.conflict_reconciler import (  # noqa: E402
    DEFAULT_TIE_BAND,
    reconcile_direction_conflicts,
)


def _pick(symbol, direction, confidence=None, **extra):
    p = {"symbol": symbol, "direction": direction}
    if confidence is not None:
        p["confidence"] = confidence
    p.update(extra)
    return p


# --------------------------------------------------------------------------
# Conflict detection + higher-conviction-side kept
# --------------------------------------------------------------------------

def test_higher_conviction_side_kept():
    """Conflicted symbol: keep the higher-conviction side, drop the other."""
    picks = [
        _pick("BTCUSDT", "LONG", 0.50),
        _pick("BTCUSDT", "SHORT", 0.79),  # short side wins (0.79 vs 0.50)
    ]
    kept, dropped = reconcile_direction_conflicts(picks)
    assert len(kept) == 1 and len(dropped) == 1
    assert kept[0]["direction"] == "SHORT"
    assert dropped[0]["direction"] == "LONG"


def test_higher_conviction_uses_sum_across_multiple_picks():
    """Aggregate conviction is the SUM per side."""
    picks = [
        _pick("ETHUSDT", "LONG", 0.50),
        _pick("ETHUSDT", "SHORT", 0.40),
        _pick("ETHUSDT", "SHORT", 0.45),  # short sum 0.85 > long 0.50
    ]
    kept, dropped = reconcile_direction_conflicts(picks)
    assert {p["direction"] for p in kept} == {"SHORT"}
    assert len(kept) == 2 and len(dropped) == 1
    assert dropped[0]["direction"] == "LONG"


def test_buy_sell_aliases_count_as_long_short():
    """BUY/SELL are treated as LONG/SHORT for conflict detection."""
    picks = [
        _pick("XRPUSDT", "BUY", 0.30),
        _pick("XRPUSDT", "SELL", 0.90),
    ]
    kept, dropped = reconcile_direction_conflicts(picks)
    assert len(kept) == 1
    assert kept[0]["direction"] == "SELL"


# --------------------------------------------------------------------------
# Tie band -> drop both
# --------------------------------------------------------------------------

def test_tie_band_drops_both_sides():
    """Within the tie band (default 0.10) -> conflict = no edge -> drop both."""
    picks = [
        _pick("DOGEUSDT", "LONG", 0.55),
        _pick("DOGEUSDT", "SHORT", 0.50),  # gap 0.05 <= 0.10
    ]
    kept, dropped = reconcile_direction_conflicts(picks)
    assert kept == []
    assert len(dropped) == 2


def test_gap_exactly_at_band_is_a_tie():
    """Gap exactly equal to the band is treated as a tie (<=)."""
    picks = [
        _pick("BNBUSDT", "LONG", 0.60),
        _pick("BNBUSDT", "SHORT", 0.50),  # gap exactly 0.10
    ]
    assert DEFAULT_TIE_BAND == 0.10
    kept, dropped = reconcile_direction_conflicts(picks)
    assert kept == []
    assert len(dropped) == 2


def test_gap_just_above_band_keeps_winner():
    """Gap just above the band -> keep the winning side."""
    picks = [
        _pick("BNBUSDT", "LONG", 0.61),
        _pick("BNBUSDT", "SHORT", 0.50),  # gap 0.11 > 0.10
    ]
    kept, dropped = reconcile_direction_conflicts(picks)
    assert len(kept) == 1 and kept[0]["direction"] == "LONG"
    assert len(dropped) == 1


def test_env_override_widens_tie_band(monkeypatch):
    """CONFLICT_TIE_BAND env widens the tie band."""
    picks = [
        _pick("BNBUSDT", "LONG", 0.70),
        _pick("BNBUSDT", "SHORT", 0.50),  # gap 0.20
    ]
    # Default band 0.10 -> winner kept.
    kept, _ = reconcile_direction_conflicts(picks)
    assert len(kept) == 1
    # Widened band 0.25 -> treated as tie -> both dropped.
    monkeypatch.setenv("CONFLICT_TIE_BAND", "0.25")
    kept2, dropped2 = reconcile_direction_conflicts(picks)
    assert kept2 == [] and len(dropped2) == 2


# --------------------------------------------------------------------------
# Non-conflicted passthrough
# --------------------------------------------------------------------------

def test_non_conflicted_passthrough():
    """Single-direction symbols pass through untouched."""
    picks = [
        _pick("BTCUSDT", "LONG", 0.50),
        _pick("BTCUSDT", "LONG", 0.60),
        _pick("ETHUSDT", "SHORT", 0.70),
        _pick("SOLUSDT", "LONG", 0.40),
    ]
    kept, dropped = reconcile_direction_conflicts(picks)
    assert dropped == []
    assert kept == picks  # same order, same objects


def test_mixed_book_only_conflicted_symbol_touched():
    """In a mixed book only the conflicted symbol is reconciled."""
    picks = [
        _pick("BTCUSDT", "LONG", 0.90),   # conflicted -> wins
        _pick("BTCUSDT", "SHORT", 0.20),  # conflicted -> dropped
        _pick("ETHUSDT", "LONG", 0.50),   # clean
        _pick("SOLUSDT", "SHORT", 0.50),  # clean
    ]
    kept, dropped = reconcile_direction_conflicts(picks)
    assert len(dropped) == 1 and dropped[0]["symbol"] == "BTCUSDT"
    assert {p["symbol"] for p in kept} == {"BTCUSDT", "ETHUSDT", "SOLUSDT"}


def test_symbol_normalization_groups_dash_and_usdt_forms():
    """BTC-USD and BTCUSDT normalize to the same symbol for conflict grouping."""
    picks = [
        _pick("BTC-USD", "LONG", 0.30),
        _pick("BTCUSDT", "SHORT", 0.90),
    ]
    kept, dropped = reconcile_direction_conflicts(picks)
    assert len(kept) == 1 and kept[0]["direction"] == "SHORT"


# --------------------------------------------------------------------------
# Fail-open / robustness on bad data
# --------------------------------------------------------------------------

def test_empty_book():
    kept, dropped = reconcile_direction_conflicts([])
    assert kept == [] and dropped == []


def test_non_dict_rows_pass_through():
    """Non-dict rows are treated as non-conflicting passthrough, not errors."""
    picks = [None, "garbage", 42, _pick("BTCUSDT", "LONG", 0.5)]
    kept, dropped = reconcile_direction_conflicts(picks)
    assert dropped == []
    assert len(kept) == 4


def test_missing_direction_is_passthrough():
    """Picks with no resolvable direction never count toward a conflict."""
    picks = [
        {"symbol": "BTCUSDT"},                       # no direction
        {"symbol": "BTCUSDT", "direction": "LONG", "confidence": 0.5},
    ]
    kept, dropped = reconcile_direction_conflicts(picks)
    assert dropped == []
    assert len(kept) == 2


def test_missing_confidence_falls_back_to_elite_score():
    """When confidence is absent, elite_score is used as conviction."""
    picks = [
        _pick("BTCUSDT", "LONG", confidence=None, elite_score=80.0),
        _pick("BTCUSDT", "SHORT", confidence=None, elite_score=10.0),
    ]
    kept, dropped = reconcile_direction_conflicts(picks)
    assert len(kept) == 1 and kept[0]["direction"] == "LONG"


def test_no_conviction_fields_treated_as_zero_tie():
    """No conviction fields on either side -> 0 vs 0 -> tie -> drop both."""
    picks = [
        {"symbol": "BTCUSDT", "direction": "LONG"},
        {"symbol": "BTCUSDT", "direction": "SHORT"},
    ]
    kept, dropped = reconcile_direction_conflicts(picks)
    assert kept == [] and len(dropped) == 2


def test_bad_confidence_value_does_not_raise():
    """Unparseable confidence is ignored (treated as 0), no exception."""
    picks = [
        _pick("BTCUSDT", "LONG", confidence="not-a-number"),
        _pick("BTCUSDT", "SHORT", confidence=0.5),
    ]
    kept, dropped = reconcile_direction_conflicts(picks)
    # long conviction 0 vs short 0.5 -> gap 0.5 > band -> short wins
    assert len(kept) == 1 and kept[0]["direction"] == "SHORT"


def test_input_is_not_mutated():
    """Pure function: neither the list nor the dicts are mutated."""
    picks = [
        _pick("BTCUSDT", "LONG", 0.50),
        _pick("BTCUSDT", "SHORT", 0.79),
    ]
    import copy
    snapshot = copy.deepcopy(picks)
    reconcile_direction_conflicts(picks)
    assert picks == snapshot  # caller's list and dicts untouched


def test_partition_property():
    """kept + dropped is always a partition of the input."""
    picks = [
        _pick("BTCUSDT", "LONG", 0.90),
        _pick("BTCUSDT", "SHORT", 0.20),
        _pick("ETHUSDT", "LONG", 0.55),
        _pick("ETHUSDT", "SHORT", 0.50),  # tie -> both dropped
        _pick("SOLUSDT", "LONG", 0.40),
    ]
    kept, dropped = reconcile_direction_conflicts(picks)
    assert len(kept) + len(dropped) == len(picks)


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
