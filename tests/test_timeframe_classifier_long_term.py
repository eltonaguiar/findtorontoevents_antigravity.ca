"""Tests for the equity/bond POSITION wireup of cross_aggregation/timeframe_classifier.py
(2026-04-30).

Background: live audit had **0 EQUITY × POSITION** picks despite having 281
closed equity rows, because the classifier had zero equity strategies in
its STRATEGY_TIMEFRAME map. Picks fell through to the system default
(``alpha_engine`` → SWING) and were never tagged POSITION.

This file pins:
  1. Each newly-mapped equity strategy classifies as POSITION.
  2. ``bond_credit_spread_mean_reversion`` classifies as SWING.
  3. ``time_horizon_days`` (the field set by the TradingAgents emitter,
     PR #544) is honored alongside ``max_hold_days`` / ``hold_days``.
  4. The non-crypto system defaults (tradingagents / value_screener /
     bond_agent) classify correctly when strategy is unknown.
"""
from __future__ import annotations

import pytest

from cross_aggregation.timeframe_classifier import (
    SYSTEM_TIMEFRAME_DEFAULT,
    classify_timeframe,
)


# ────────────────────────────────────────────────────────────────────────
# Strategy → timeframe mappings (equity + bond, added 2026-04-30)
# ────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "strategy,expected_tf",
    [
        # Equity long-term (POSITION = 7d+ hold)
        ("vt_earnings_pead",                       "POSITION"),
        ("magic_formula_x_piotroski_x_acquirers",  "POSITION"),
        ("tradingagents_consensus",                "POSITION"),
        ("stocks_ema_golden_cross",                "POSITION"),
        ("smart_money_accumulation",               "POSITION"),
        # Bond mean-reversion is intentionally SWING (3-10d), not POSITION.
        ("bond_credit_spread_mean_reversion",      "SWING"),
    ],
)
def test_long_term_equity_and_bond_strategies_classified(strategy, expected_tf):
    """Every newly-added strategy in STRATEGY_TIMEFRAME resolves correctly."""
    assert classify_timeframe({"strategy": strategy}) == expected_tf


# ────────────────────────────────────────────────────────────────────────
# System defaults (non-crypto POSITION lane)
# ────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "system_name,expected_tf",
    [
        ("tradingagents",  "POSITION"),  # PR #544 emitter (5-90d horizon)
        ("value_screener", "POSITION"),  # UEPS magic-formula (3y+ holding)
        ("bond_agent",     "SWING"),     # bond-agent.yml emitter
    ],
)
def test_non_crypto_system_defaults(system_name, expected_tf):
    """When strategy is not in the map, system default takes over."""
    # Use a known-unmapped strategy so the system default actually applies.
    pick = {"strategy": "definitely_not_a_real_strategy_xyz"}
    assert classify_timeframe(pick, system_name) == expected_tf
    # Also pin the constant so a future refactor can't silently move them.
    assert SYSTEM_TIMEFRAME_DEFAULT.get(system_name) == expected_tf


def test_existing_alpha_engine_default_unchanged():
    """Regression guard: alpha_engine remains SWING (the other ~50 system
    defaults must not have been disturbed by the 2026-04-30 patch)."""
    assert SYSTEM_TIMEFRAME_DEFAULT.get("alpha_engine") == "SWING"
    assert SYSTEM_TIMEFRAME_DEFAULT.get("battleground") == "INTRADAY"
    assert SYSTEM_TIMEFRAME_DEFAULT.get("rapid_fire") == "SCALP"


# ────────────────────────────────────────────────────────────────────────
# time_horizon_days field check (added 2026-04-30 for PR #544 emitter)
# ────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "horizon_days,expected_tf",
    [
        (0.1,  "SCALP"),     # < 4h
        (0.5,  "INTRADAY"),  # 4-24h (0.17 < d <= 1.0)
        (1.0,  "INTRADAY"),  # boundary: <= 1.0 day
        (1.01, "SWING"),     # > 1.0 day
        (5,    "SWING"),     # mid-range swing
        (7,    "SWING"),     # boundary: <= 7 days
        (8,    "POSITION"),  # > 7 days
        (21,   "POSITION"),  # default TradingAgents horizon
        (90,   "POSITION"),  # max TradingAgents horizon
    ],
)
def test_time_horizon_days_field_drives_classification(horizon_days, expected_tf):
    """Picks with no strategy match but a time_horizon_days hint must
    classify by that hint, not fall through to the system default."""
    pick = {"strategy": "unknown_strategy_xyz", "time_horizon_days": horizon_days}
    # Empty system_name to skip the system-default fallback.
    assert classify_timeframe(pick, "") == expected_tf


def test_max_hold_days_wins_over_time_horizon_days():
    """If both are present, max_hold_days takes precedence (the existing
    field used by the rest of the pipeline)."""
    pick = {
        "strategy": "unknown_strategy_xyz",
        "max_hold_days": 0.1,        # SCALP
        "time_horizon_days": 30,     # POSITION
    }
    assert classify_timeframe(pick, "") == "SCALP"


def test_unknown_strategy_with_no_hints_falls_back_to_swing():
    """Pin the documented fallback so a future refactor can't silently
    change the classification of unknown picks."""
    pick = {"strategy": "completely_unknown_xyz"}
    assert classify_timeframe(pick, "") == "SWING"


# ────────────────────────────────────────────────────────────────────────
# Strategy match wins over system default
# ────────────────────────────────────────────────────────────────────────

def test_strategy_match_wins_over_system_default():
    """An EQUITY strategy mapped to POSITION must classify as POSITION even
    when the source system's default is SWING (the case for picks emitted
    by ``alpha_engine`` running ``vt_earnings_pead``)."""
    pick = {"strategy": "vt_earnings_pead"}
    assert classify_timeframe(pick, "alpha_engine") == "POSITION"
