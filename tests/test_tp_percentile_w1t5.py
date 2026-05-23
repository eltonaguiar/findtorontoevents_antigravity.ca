"""
Regression tests for the TP_PERCENTILE wiring (W1-T5).

Background
----------
Kimi audit 2026-04-25 found that adaptive TP was set at the 75th percentile
of winner MFE. Winners reached that level only ~25% of the time before
reversing, leaving the rest to decay into TIME_EXIT. The fix lowers the
default to 60 and makes the percentile a single named constant
(`TP_PERCENTILE`) instead of magic literals scattered across
`_compute_strategy_levels` and `_compute_symbol_levels`.

These tests:
  1. Pin the new constant value so an accidental revert is loud.
  2. Pin the SL_PERCENTILE value (unchanged at 90) so we don't drift
     symmetrically by mistake.
  3. Build small synthetic distributions and assert the recomputed TP
     equals the p60 of winner MFE (not p75), proving the constant is
     actually plumbed into the operative code path.
"""
from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from alpha_engine import adaptive_tp_sl as ats


def test_tp_percentile_constant_is_60():
    """An accidental bump back to 75 must fail loudly."""
    assert ats.TP_PERCENTILE == 60.0


def test_sl_percentile_constant_is_90():
    """SL_PERCENTILE must remain at 90 (W1-T5 only changed TP)."""
    assert ats.SL_PERCENTILE == 90.0


def test_strategy_levels_use_p60_winner_mfe():
    """
    Build a strategy with winners whose MFEs are 1..10 and losers with
    MAEs of 5..14, exceed MIN_TRADES_STRATEGY, and assert the recomputed
    TP equals p60 of winner MFE (= 5.5%, /100 = 0.055), NOT the old
    p75 value (= 7.0%, /100 = 0.07). SL stays at p90 of loser MAE.

    Picks layout follows what _compute_strategy_levels reads:
      - status WON/LOST drives is_winner
      - mfe_pct / mae_pct extracted from extra dict (or root)
      - strategy is the bucket key
    """
    # 10 winners with MFEs 1..10 (in percent units)
    winners = [
        {
            "strategy": "W1T5_TEST",
            "status": "WON",
            "pnl_pct": 0.05,
            "category": "equity",
            "extra": {"mfe_pct": float(i), "mae_pct": 1.0},
            "symbol": "AAPL",
            "entry_price": 100.0,
        }
        for i in range(1, 11)
    ]
    # 10 losers with MAEs 5..14
    losers = [
        {
            "strategy": "W1T5_TEST",
            "status": "LOST",
            "pnl_pct": -0.04,
            "category": "equity",
            "extra": {"mfe_pct": 0.5, "mae_pct": float(i)},
            "symbol": "AAPL",
            "entry_price": 100.0,
        }
        for i in range(5, 15)
    ]
    picks = winners + losers

    levels = ats._compute_strategy_levels(picks)
    assert "W1T5_TEST" in levels, f"strategy bucket not produced; got {list(levels)[:5]}"

    bucket = levels["W1T5_TEST"]

    # p60 of winner MFE [1..10] is 5.5; / 100 => 0.055
    expected_tp = ats._percentile([float(i) for i in range(1, 11)], 60.0) / 100.0
    expected_tp = max(ats.MIN_TP_PCT, min(expected_tp, ats.MAX_TP_PCT))

    # p90 of loser MAE [5..14] is 13.1; / 100 => 0.131 -> clamped to 0.10
    expected_sl = ats._percentile([float(i) for i in range(5, 15)], 90.0) / 100.0
    expected_sl = max(ats.MIN_SL_PCT, min(expected_sl, ats.MAX_SL_PCT))

    # Old behaviour (must NOT match): p75 of [1..10] = 7.75 -> 0.0775
    pre_fix_tp = ats._percentile([float(i) for i in range(1, 11)], 75.0) / 100.0
    pre_fix_tp = max(ats.MIN_TP_PCT, min(pre_fix_tp, ats.MAX_TP_PCT))

    assert bucket["optimal_tp_pct"] == pytest.approx(round(expected_tp, 6)), (
        f"TP={bucket['optimal_tp_pct']} != expected p60 {expected_tp}"
    )
    assert bucket["optimal_sl_pct"] == pytest.approx(round(expected_sl, 6))
    assert bucket["optimal_tp_pct"] != pytest.approx(round(pre_fix_tp, 6)), (
        "TP unchanged from old p75 value -- W1-T5 not actually wired in"
    )


def test_diagnostic_p75_winner_mfe_still_emitted():
    """
    The dump still records p75 winner MFE alongside the operative p60
    level so operators can see the gap between 'where we set TP' and
    'where p75 actually was'. This test catches accidental removal of
    the diagnostic field.
    """
    winners = [
        {
            "strategy": "W1T5_DIAG",
            "status": "WON",
            "pnl_pct": 0.05,
            "category": "equity",
            "extra": {"mfe_pct": float(i), "mae_pct": 1.0},
            "symbol": "AAPL",
            "entry_price": 100.0,
        }
        for i in range(1, 11)
    ]
    losers = [
        {
            "strategy": "W1T5_DIAG",
            "status": "LOST",
            "pnl_pct": -0.04,
            "category": "equity",
            "extra": {"mfe_pct": 0.5, "mae_pct": float(i)},
            "symbol": "AAPL",
            "entry_price": 100.0,
        }
        for i in range(5, 15)
    ]
    levels = ats._compute_strategy_levels(winners + losers)
    bucket = levels["W1T5_DIAG"]
    assert bucket["p75_winner_mfe_pct"] is not None, (
        "diagnostic p75_winner_mfe_pct field disappeared"
    )
    # p75 of [1..10] = 7.75
    assert bucket["p75_winner_mfe_pct"] == pytest.approx(7.75, abs=0.01)
