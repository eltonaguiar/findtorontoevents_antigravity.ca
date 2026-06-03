"""ETF dual-momentum backtest — offline tests on synthetic price frames."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verified_strategies"))
import etf_dual_momentum_backtest as dm  # noqa: E402


def _ramp_df(start, daily_drift, n_days=900, seed=0):
    rng = np.random.RandomState(seed)
    idx = pd.date_range("2022-01-01", periods=n_days, freq="D")
    rets = daily_drift + rng.normal(0, 0.002, n_days)
    close = start * np.cumprod(1 + rets)
    return pd.DataFrame({"close": close}, index=idx)


def test_picks_top_momentum_asset():
    # SPY trending up fastest, AGG flat, BIL ~flat -> dual momentum picks SPY
    data = {
        "SPY": dm.monthly_closes(_ramp_df(100, 0.0010, seed=1)),
        "QQQ": dm.monthly_closes(_ramp_df(100, 0.0006, seed=2)),
        "AGG": dm.monthly_closes(_ramp_df(100, 0.00005, seed=3)),
        "GLD": dm.monthly_closes(_ramp_df(100, 0.0002, seed=4)),
        "EFA": dm.monthly_closes(_ramp_df(100, 0.0003, seed=5)),
        "BIL": dm.monthly_closes(_ramp_df(100, 0.00004, seed=6)),
    }
    asof = sorted(data["SPY"].index)[-1]
    pick = dm.dual_momentum_pick(data, asof)
    assert pick == ["SPY"]


def test_risk_off_goes_to_cash():
    # all risk assets falling, cash rising -> hold cash
    data = {
        "SPY": dm.monthly_closes(_ramp_df(100, -0.0010, seed=1)),
        "QQQ": dm.monthly_closes(_ramp_df(100, -0.0012, seed=2)),
        "AGG": dm.monthly_closes(_ramp_df(100, -0.0008, seed=3)),
        "BIL": dm.monthly_closes(_ramp_df(100, 0.0002, seed=6)),
    }
    asof = sorted(data["SPY"].index)[-1]
    assert dm.dual_momentum_pick(data, asof) == ["BIL"]


def test_backtest_runs_and_reports_metrics():
    price = {
        "SPY": _ramp_df(100, 0.0008, seed=1),
        "QQQ": _ramp_df(100, 0.0009, seed=2),
        "AGG": _ramp_df(100, 0.0001, seed=3),
        "GLD": _ramp_df(100, 0.0003, seed=4),
        "EFA": _ramp_df(100, 0.0004, seed=5),
        "BIL": _ramp_df(100, 0.00004, seed=6),
    }
    res = dm.backtest_dual_momentum(price)
    assert res["n_months"] > 0
    for k in ("profit_factor", "win_rate", "sharpe_annual", "max_drawdown", "cagr"):
        assert k in res
    assert -1.0 <= res["max_drawdown"] <= 0.0


def test_insufficient_data_errors_cleanly():
    res = dm.backtest_dual_momentum({"SPY": _ramp_df(100, 0.001, n_days=60)})
    assert res.get("n_months") == 0
