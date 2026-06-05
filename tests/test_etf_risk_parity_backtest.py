"""ETF inverse-vol (risk-parity-lite) backtest — offline tests on synthetic frames."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verified_strategies"))
import etf_risk_parity_backtest as rp  # noqa: E402


def _vol_df(start, daily_vol, n_days=900, drift=0.0003, seed=0):
    """Daily close frame with a controllable noise level (=> realized vol)."""
    rng = np.random.RandomState(seed)
    idx = pd.date_range("2021-01-01", periods=n_days, freq="D")
    rets = drift + rng.normal(0, daily_vol, n_days)
    close = start * np.cumprod(1 + rets)
    return pd.DataFrame({"close": close}, index=idx)


def test_inverse_vol_weights_sum_to_one():
    w = rp.inverse_vol_weights({"SPY": 0.01, "TLT": 0.02, "GLD": 0.015, "DBC": 0.025})
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert all(0.0 < v < 1.0 for v in w.values())
    assert set(w) == {"SPY", "TLT", "GLD", "DBC"}


def test_lower_vol_asset_gets_higher_weight():
    # SPY has the lowest vol -> must receive the largest weight; DBC highest vol -> smallest.
    w = rp.inverse_vol_weights({"SPY": 0.008, "TLT": 0.016, "GLD": 0.012, "DBC": 0.040})
    assert w["SPY"] == max(w.values())
    assert w["DBC"] == min(w.values())
    assert w["SPY"] > w["TLT"] > w["DBC"]


def test_weights_drop_unusable_vol():
    # None / non-positive vols are dropped; remaining weights still sum to 1.
    w = rp.inverse_vol_weights({"SPY": 0.01, "TLT": None, "GLD": 0.0, "DBC": 0.02})
    assert set(w) == {"SPY", "DBC"}
    assert abs(sum(w.values()) - 1.0) < 1e-9
    # empty / all-unusable -> {}
    assert rp.inverse_vol_weights({"SPY": None, "TLT": 0.0}) == {}


def test_trailing_vol_is_walk_forward():
    df = _vol_df(100, 0.01, n_days=400, seed=3)
    s = df["close"]
    asof = s.index[200]
    v = rp.trailing_vol(s, asof, lookback_days=63)
    assert v is not None and v > 0.0
    # uses only data <= asof: truncating the series after asof must not change it
    v_trunc = rp.trailing_vol(s[s.index <= asof], asof, lookback_days=63)
    assert abs(v - v_trunc) < 1e-12
    # too little history -> None
    assert rp.trailing_vol(s.iloc[:10], s.index[9], lookback_days=63) is None


def test_backtest_runs_and_reports_metrics():
    price = {
        "SPY": _vol_df(100, 0.008, seed=1, drift=0.0006),
        "TLT": _vol_df(100, 0.012, seed=2, drift=0.0001),
        "GLD": _vol_df(100, 0.010, seed=3, drift=0.0003),
        "DBC": _vol_df(100, 0.020, seed=4, drift=0.0002),
    }
    res = rp.backtest_risk_parity(price)
    assert res["n_months"] > 0
    for k in ("profit_factor", "win_rate", "sharpe_annual", "max_drawdown", "cagr"):
        assert k in res
    assert -1.0 <= res["max_drawdown"] <= 0.0
    assert 0.0 <= res["win_rate"] <= 1.0


def test_cost_drag_reduces_returns():
    price = {
        "SPY": _vol_df(100, 0.008, seed=1, drift=0.0006),
        "TLT": _vol_df(100, 0.012, seed=2, drift=0.0001),
        "GLD": _vol_df(100, 0.010, seed=3, drift=0.0003),
        "DBC": _vol_df(100, 0.020, seed=4, drift=0.0002),
    }
    base = rp.backtest_risk_parity(price, cost_bps=0.0)
    drag = rp.backtest_risk_parity(price, cost_bps=20.0)
    assert drag["total_return"] < base["total_return"]


def test_bootstrap_pf_ci_is_seeded_and_ordered():
    rng = np.random.RandomState(7)
    rets = (0.004 + rng.normal(0, 0.02, 80)).tolist()
    a = rp.bootstrap_pf_ci(rets, n_resamples=1000, seed=42)
    b = rp.bootstrap_pf_ci(rets, n_resamples=1000, seed=42)
    assert a == b  # deterministic for a fixed seed
    assert a["pf_lower"] <= a["pf_median"] <= a["pf_upper"]
    # too few months -> graceful None
    assert rp.bootstrap_pf_ci([0.01, 0.02], n_resamples=100)["pf_lower"] is None


def test_insufficient_data_errors_cleanly():
    res = rp.backtest_risk_parity({"SPY": _vol_df(100, 0.01, n_days=60)})
    assert res.get("n_months") == 0
