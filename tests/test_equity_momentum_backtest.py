"""EQUITY cross-sectional momentum — smoke tests (reuses ETF engine, offline)."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verified_strategies"))
import equity_momentum_backtest as eq  # noqa: E402
from etf_dual_momentum_backtest import backtest_dual_momentum  # noqa: E402


def _ramp(start, drift, n=900, seed=0):
    rng = np.random.RandomState(seed)
    idx = pd.date_range("2022-01-01", periods=n, freq="D")
    close = start * np.cumprod(1 + drift + rng.normal(0, 0.003, n))
    return pd.DataFrame({"close": close}, index=idx)


def test_universe_constants():
    assert "NVDA" in eq.UNIVERSE and "AAPL" in eq.UNIVERSE
    assert eq.BENCHMARK == "SPY" and eq.TOP_K == 3


def test_engine_runs_on_equity_universe():
    price = {s: _ramp(100, 0.0003 + 0.0001 * i, seed=i)
             for i, s in enumerate(eq.UNIVERSE)}
    price["BIL"] = _ramp(100, 0.00004, seed=99)
    res = backtest_dual_momentum(price, lookback=eq.LOOKBACK_M, top_k=eq.TOP_K, cash="BIL")
    assert res["n_months"] > 0
    for k in ("profit_factor", "sharpe_annual", "max_drawdown"):
        assert k in res
