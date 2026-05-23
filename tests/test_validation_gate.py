"""Tests for BundleBabySystem.evaluate_gate validation gate."""

import sys
import types
from unittest.mock import MagicMock

# Stub out heavy dependencies so bundle_baby_system can import without pandas/etc.
_incubator_testing = types.ModuleType("incubator.testing")
_incubator_testing.run_tier1_backtest = MagicMock()
_incubator_testing.run_tier2_backtest = MagicMock()
_incubator_testing.run_full_backtest = MagicMock()
_incubator_testing.check_pass_criteria = MagicMock()
sys.modules.setdefault("incubator.testing", _incubator_testing)

from bundle_baby_system import BundleBabySystem


def test_gate_proven_status():
    stats = {
        "forward_win_rate": 60,
        "forward_sharpe": 1.5,
        "forward_max_dd": -12,
        "forward_trades": 25,
        "forward_realized_pnl": 15.0,
    }
    gate = BundleBabySystem.evaluate_gate(stats)
    assert gate["status"] in ("PROVEN", "ELITE")
    assert gate["checks_passed"] >= 5


def test_gate_collecting_status():
    stats = {
        "forward_win_rate": 0,
        "forward_sharpe": 0,
        "forward_max_dd": 0,
        "forward_trades": 2,
        "forward_realized_pnl": 0,
    }
    gate = BundleBabySystem.evaluate_gate(stats)
    assert gate["status"] == "COLLECTING"
    assert gate["checks_passed"] < 4


def test_gate_marginal_status():
    stats = {
        "forward_win_rate": 48,
        "forward_sharpe": 0.5,
        "forward_max_dd": -25,
        "forward_trades": 15,
        "forward_realized_pnl": 3.0,
    }
    gate = BundleBabySystem.evaluate_gate(stats)
    assert gate["status"] in ("TESTING", "MARGINAL")


def test_gate_elite_status():
    stats = {
        "forward_win_rate": 70,
        "forward_sharpe": 2.0,
        "forward_max_dd": -5,
        "forward_trades": 50,
        "forward_realized_pnl": 40.0,
    }
    gate = BundleBabySystem.evaluate_gate(stats)
    assert gate["status"] == "ELITE"
    assert gate["checks_passed"] == 8
