"""Tests for alpha_engine.auto_retire — quarantine threshold logic."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alpha_engine.auto_retire import (
    FWD_BT_DIVERGENCE_PP,
    MAX_DRAWDOWN_PCT,
    MIN_TRADES_FOR_EVAL,
    PF_FLOOR,
    WR_FLOOR,
    evaluate_strategy,
)


def test_pf_below_floor_after_min_trades_quarantines():
    reason = evaluate_strategy("strat_a", {
        "n_resolved": 60, "profit_factor": 0.3, "win_rate": 50,
    })
    assert reason is not None
    assert "PF 0.30" in reason


def test_wr_below_floor_quarantines():
    reason = evaluate_strategy("strat_b", {
        "n_resolved": 60, "profit_factor": 0.6, "win_rate": 30,
    })
    assert reason is not None
    assert "WR 30.0%" in reason


def test_max_dd_breach_quarantines():
    reason = evaluate_strategy("strat_c", {
        "n_resolved": 60, "profit_factor": 1.2, "win_rate": 55,
        "max_drawdown_pct": -25.0,
    })
    assert reason is not None
    assert "DD" in reason


def test_fwd_bt_divergence_quarantines_when_fwd_sample_sufficient():
    reason = evaluate_strategy("strat_d", {
        "n_resolved": 60, "profit_factor": 1.5, "win_rate": 60,
        "max_drawdown_pct": -10.0,
        "forward_trades": 25, "forward_win_rate": 0.35,
        "backtest_win_rate": 0.70,
    })
    assert reason is not None
    assert "divergence" in reason


def test_insufficient_trades_no_action():
    reason = evaluate_strategy("strat_e", {
        "n_resolved": 10, "profit_factor": 0.1, "win_rate": 10,
    })
    assert reason is None


def test_healthy_strategy_no_action():
    reason = evaluate_strategy("strat_f", {
        "n_resolved": 100, "profit_factor": 1.8, "win_rate": 58,
        "max_drawdown_pct": -8.0,
    })
    assert reason is None


def test_wr_handled_as_percentage_or_fraction():
    # WR 30 (percentage form)
    r1 = evaluate_strategy("a", {"n_resolved": 60, "profit_factor": 0.6, "win_rate": 30})
    # WR 0.30 (fraction form)
    r2 = evaluate_strategy("b", {"n_resolved": 60, "profit_factor": 0.6, "win_rate": 0.30})
    assert r1 is not None
    assert r2 is not None


def test_thresholds_exposed_as_module_constants():
    # ensure constants are present for monitoring/test parity
    assert PF_FLOOR > 0
    assert WR_FLOOR > 0
    assert MAX_DRAWDOWN_PCT < 0
    assert MIN_TRADES_FOR_EVAL >= 30
    assert FWD_BT_DIVERGENCE_PP > 0
