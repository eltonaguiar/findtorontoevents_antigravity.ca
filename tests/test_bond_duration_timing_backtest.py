"""BOND duration-timing — smoke tests (reuses ETF engine, offline)."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verified_strategies"))
import bond_duration_timing_backtest as bd  # noqa: E402
from etf_dual_momentum_backtest import backtest_dual_momentum, dual_momentum_pick, monthly_closes  # noqa: E402


def _ramp(start, drift, n=900, seed=0):
    rng = np.random.RandomState(seed)
    idx = pd.date_range("2022-01-01", periods=n, freq="D")
    close = start * np.cumprod(1 + drift + rng.normal(0, 0.0015, n))
    return pd.DataFrame({"close": close}, index=idx)


def test_universe_constants():
    assert "TLT" in bd.UNIVERSE and bd.CASH == "SHY" and bd.BENCHMARK == "AGG"


def test_rising_rates_rotates_to_short_cash():
    # all longer-duration falling, SHY (cash) rising -> hold SHY
    data = {
        "TLT": monthly_closes(_ramp(100, -0.0010, seed=1)),
        "IEF": monthly_closes(_ramp(100, -0.0006, seed=2)),
        "AGG": monthly_closes(_ramp(100, -0.0004, seed=3)),
        "LQD": monthly_closes(_ramp(100, -0.0005, seed=4)),
        "SHY": monthly_closes(_ramp(100, 0.0002, seed=5)),
    }
    asof = sorted(data["TLT"].index)[-1]
    assert dual_momentum_pick(data, asof, cash="SHY") == ["SHY"]


def test_engine_runs_on_bond_universe():
    price = {s: _ramp(100, d, seed=i) for i, (s, d) in enumerate(
        [("TLT", 0.0004), ("IEF", 0.0003), ("AGG", 0.0002), ("LQD", 0.00025),
         ("SHY", 0.00005)])}
    res = backtest_dual_momentum(price, lookback=bd.LOOKBACK_M, top_k=bd.TOP_K, cash="SHY")
    assert res["n_months"] > 0 and "profit_factor" in res
