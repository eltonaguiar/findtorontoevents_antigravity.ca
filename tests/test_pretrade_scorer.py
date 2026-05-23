"""Test pre-trade signal scorer."""
import numpy as np
import pytest
import sys
sys.path.insert(0, '.')


def test_good_signal_passes():
    """A signal with good RR and moderate vol should grade A or B."""
    from risk_management.pretrade_scorer import score_signal

    result = score_signal(
        symbol="BTCUSDT",
        entry_price=60000,
        target_price=63000,  # +5%
        stop_price=58800,    # -2%
        direction="BUY",
        vol_override=0.015,  # 1.5% per bar — moderate
        n_sims=1000,
    )
    assert result["pass_filter"], f"Good signal should pass, got grade={result['grade']}"
    assert result["prob_tp"] > 0.2  # Monte Carlo is stochastic; 20% is the floor for grade A/B
    assert result["rr_ratio"] >= 2.0


def test_bad_rr_fails():
    """A signal with terrible RR should fail."""
    from risk_management.pretrade_scorer import score_signal

    result = score_signal(
        symbol="BTCUSDT",
        entry_price=60000,
        target_price=60300,  # +0.5% tiny target
        stop_price=54000,    # -10% huge stop
        direction="BUY",
        vol_override=0.02,
        n_sims=500,
    )
    assert result["grade"] == "F" or not result["pass_filter"]
    assert result["rr_ratio"] < 0.1


def test_invalid_tpsl():
    """Invalid TP/SL should return F grade."""
    from risk_management.pretrade_scorer import score_signal

    result = score_signal(
        symbol="BTCUSDT",
        entry_price=60000,
        target_price=59000,  # target below entry for BUY = invalid
        stop_price=58000,
        direction="BUY",
        vol_override=0.02,
    )
    assert result["grade"] == "F"
    assert not result["pass_filter"]


def test_cost_deducted():
    """Expected P&L should account for transaction costs."""
    from risk_management.pretrade_scorer import score_signal

    result = score_signal(
        symbol="BTCUSDT",
        entry_price=60000,
        target_price=63000,
        stop_price=58800,
        direction="BUY",
        vol_override=0.015,
        n_sims=500,
    )
    assert result["cost_pct"] > 0, "Cost should be positive"


def test_sell_direction():
    """SHORT signals should work correctly."""
    from risk_management.pretrade_scorer import score_signal

    result = score_signal(
        symbol="ETHUSDT",
        entry_price=3000,
        target_price=2850,   # -5% target
        stop_price=3060,     # +2% stop
        direction="SELL",
        vol_override=0.02,
        n_sims=500,
    )
    assert "prob_tp" in result
    assert result["rr_ratio"] >= 2.0
