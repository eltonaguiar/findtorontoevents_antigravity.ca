"""
Regression tests for the post-clamp R:R guard in alpha_engine/adaptive_tp_sl.py.

Background
----------
Kimi audit 2026-04-25 finding #1: `get_optimal_tp_sl()` applies floor/cap
clamps to tp_pct and sl_pct AFTER the per-strategy `has_edge` check.
Pathological inputs (tiny TP, large SL) could survive clamping and emit
picks at R:R as low as 0.05, well below break-even. The fix re-validates
ratio after the clamp and falls back to category defaults if it's below
MIN_TP_SL_RATIO.

These tests inject synthetic cache entries that exercise the path.
"""
from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from alpha_engine import adaptive_tp_sl as ats
from alpha_engine.tpsl_policy import get_tpsl_policy


@pytest.fixture(autouse=True)
def reset_cache():
    """Each test gets a clean in-memory cache."""
    saved = (ats._CACHE.copy() if ats._CACHE else {}, ats._CACHE_LOADED)
    ats._CACHE = {}
    ats._CACHE_LOADED = True  # bypass disk load
    yield
    ats._CACHE, ats._CACHE_LOADED = saved


def _expected_default_prices(category: str, entry: float, is_short: bool) -> tuple[float, float]:
    """Compute what the prices SHOULD be when the guard falls back to defaults."""
    pol = get_tpsl_policy(category)
    tp_pct = max(ats.MIN_TP_PCT, min(pol["tp_pct"], ats.MAX_TP_PCT))
    sl_pct = max(ats.MIN_SL_PCT, min(pol["sl_pct"], ats.MAX_SL_PCT))
    if is_short:
        return (round(entry * (1.0 - tp_pct), 8), round(entry * (1.0 + sl_pct), 8))
    return (round(entry * (1.0 + tp_pct), 8), round(entry * (1.0 - sl_pct), 8))


def test_degenerate_strategy_falls_back_to_default():
    """
    Per-strategy cache with tiny TP and large SL. After clamping the ratio
    is well below MIN_TP_SL_RATIO. Guard must fall back to category default.
    """
    ats._CACHE = {
        "per_strategy": {
            "BAD_STRAT": {
                "has_edge": True,           # pre-clamp the per-strategy code thought it was fine
                "sample_size": ats.MIN_TRADES_STRATEGY + 5,
                "optimal_tp_pct": 0.001,    # below MIN_TP_PCT -> clamps to 0.005
                "optimal_sl_pct": 0.50,     # above MAX_SL_PCT -> clamps to 0.10
            },
        },
        "per_symbol": {},
    }
    entry = 100.0
    tp_price, sl_price = ats.get_optimal_tp_sl(
        "BAD_STRAT", "AAPL", entry, category="equity", direction="LONG"
    )
    expected_tp, expected_sl = _expected_default_prices("equity", entry, is_short=False)
    assert tp_price == expected_tp, f"tp_price {tp_price} != default {expected_tp}"
    assert sl_price == expected_sl, f"sl_price {sl_price} != default {expected_sl}"


def test_healthy_strategy_keeps_its_levels():
    """
    Per-strategy cache with healthy TP/SL ratio. Guard MUST NOT fire and the
    picks should keep the cached optimal values.
    """
    tp_pct, sl_pct = 0.04, 0.025  # ratio 1.6, both well within clamps
    ats._CACHE = {
        "per_strategy": {
            "GOOD_STRAT": {
                "has_edge": True,
                "sample_size": ats.MIN_TRADES_STRATEGY + 5,
                "optimal_tp_pct": tp_pct,
                "optimal_sl_pct": sl_pct,
            },
        },
        "per_symbol": {},
    }
    entry = 100.0
    tp_price, sl_price = ats.get_optimal_tp_sl(
        "GOOD_STRAT", "AAPL", entry, category="equity", direction="LONG"
    )
    assert tp_price == round(entry * (1.0 + tp_pct), 8)
    assert sl_price == round(entry * (1.0 - sl_pct), 8)


def test_short_direction_degenerate_fallback():
    """SHORT direction must produce mirrored default prices on fallback."""
    ats._CACHE = {
        "per_strategy": {
            "BAD_STRAT": {
                "has_edge": True,
                "sample_size": ats.MIN_TRADES_STRATEGY + 5,
                "optimal_tp_pct": 0.001,
                "optimal_sl_pct": 0.50,
            },
        },
        "per_symbol": {},
    }
    entry = 100.0
    tp_price, sl_price = ats.get_optimal_tp_sl(
        "BAD_STRAT", "AAPL", entry, category="equity", direction="SHORT"
    )
    expected_tp, expected_sl = _expected_default_prices("equity", entry, is_short=True)
    assert tp_price == expected_tp
    assert sl_price == expected_sl


def test_no_cache_uses_defaults_directly():
    """When no per-strategy or per-symbol entry exists, defaults flow through
    cleanly (this exercises the path that the guard is also protecting)."""
    ats._CACHE = {"per_strategy": {}, "per_symbol": {}}
    entry = 100.0
    tp_price, sl_price = ats.get_optimal_tp_sl(
        "UNKNOWN_STRAT", "AAPL", entry, category="equity", direction="LONG"
    )
    expected_tp, expected_sl = _expected_default_prices("equity", entry, is_short=False)
    assert tp_price == expected_tp
    assert sl_price == expected_sl
