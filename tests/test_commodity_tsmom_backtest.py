"""Commodity TSMOM backtest — offline tests on synthetic price frames."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verified_strategies"))
import commodity_tsmom_backtest as ts  # noqa: E402
import etf_dual_momentum_backtest as dm  # noqa: E402


def _ramp(start, drift, n=900, seed=0):
    rng = np.random.RandomState(seed)
    idx = pd.date_range("2022-01-01", periods=n, freq="D")
    close = start * np.cumprod(1 + drift + rng.normal(0, 0.002, n))
    return pd.DataFrame({"close": close}, index=idx)


def test_longs_only_up_trending():
    data = {
        "DBC": dm.monthly_closes(_ramp(100, 0.0008, seed=1)),
        "GLD": dm.monthly_closes(_ramp(100, 0.0006, seed=2)),
        "USO": dm.monthly_closes(_ramp(100, -0.0010, seed=3)),   # falling -> excluded
        "BIL": dm.monthly_closes(_ramp(100, 0.00004, seed=6)),
    }
    asof = sorted(data["DBC"].index)[-1]
    longs = ts.tsmom_longs(data, asof)
    assert "DBC" in longs and "GLD" in longs
    assert "USO" not in longs


def test_all_falling_goes_cash():
    data = {
        "DBC": dm.monthly_closes(_ramp(100, -0.001, seed=1)),
        "GLD": dm.monthly_closes(_ramp(100, -0.0012, seed=2)),
        "BIL": dm.monthly_closes(_ramp(100, 0.0002, seed=6)),
    }
    asof = sorted(data["DBC"].index)[-1]
    assert ts.tsmom_longs(data, asof) == ["BIL"]


def test_backtest_reports_metrics():
    price = {s: _ramp(100, d, seed=i) for i, (s, d) in enumerate(
        [("DBC", 0.0006), ("GLD", 0.0007), ("USO", 0.0003), ("DBA", 0.0002),
         ("SLV", 0.0004), ("UNG", -0.0002), ("BIL", 0.00004)])}
    res = ts.backtest_tsmom(price)
    assert res["n_months"] > 0
    for k in ("profit_factor", "sharpe_annual", "max_drawdown", "win_rate"):
        assert k in res


def test_insufficient_data():
    assert ts.backtest_tsmom({"DBC": _ramp(100, 0.001, n=60)}).get("n_months") == 0
