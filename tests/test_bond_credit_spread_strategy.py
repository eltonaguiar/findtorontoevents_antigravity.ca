import numpy as np
import pandas as pd

from alpha_engine.bond_strategies import bond_credit_spread_mean_reversion


def _mk_df(close_vals):
    idx = pd.date_range("2026-01-01", periods=len(close_vals), freq="D")
    close = pd.Series(close_vals, index=idx, dtype=float)
    return pd.DataFrame(
        {
            "Close": close,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Volume": np.full(len(close_vals), 1_000_000.0),
        },
        index=idx,
    )


def test_credit_spread_strategy_disabled_by_default(monkeypatch):
    monkeypatch.setenv("BOND_ENABLE_CREDIT_SPREAD", "0")
    hyg = _mk_df(np.linspace(80, 81, 90))
    lqd = _mk_df(np.linspace(100, 101, 90))
    out = bond_credit_spread_mean_reversion({"HYG": hyg, "LQD": lqd})
    assert out == []


def test_credit_spread_strategy_emits_buy_when_spread_oversold(monkeypatch):
    monkeypatch.setenv("BOND_ENABLE_CREDIT_SPREAD", "1")
    lqd_vals = np.full(100, 100.0)
    hyg_vals = np.full(100, 90.0)
    hyg_vals[-1] = 70.0  # force deeply negative spread z-score
    out = bond_credit_spread_mean_reversion({"HYG": _mk_df(hyg_vals), "LQD": _mk_df(lqd_vals)})
    assert out and out[0]["signal_type"] == "BUY"
    assert out[0]["strategy"] == "bond_credit_spread_mean_reversion"
    assert out[0]["extra"]["pair"] == "HYG/LQD"


def test_credit_spread_strategy_emits_sell_when_spread_overbought(monkeypatch):
    monkeypatch.setenv("BOND_ENABLE_CREDIT_SPREAD", "1")
    lqd_vals = np.full(100, 100.0)
    hyg_vals = np.full(100, 90.0)
    hyg_vals[-1] = 120.0  # force positive spread z-score
    out = bond_credit_spread_mean_reversion({"HYG": _mk_df(hyg_vals), "LQD": _mk_df(lqd_vals)})
    assert out and out[0]["signal_type"] == "SELL"

