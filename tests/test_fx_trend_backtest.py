"""FX trend-following backtest — smoke tests (reuses ETF engine, offline)."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verified_strategies"))
import fx_trend_backtest as fx  # noqa: E402
from etf_dual_momentum_backtest import backtest_dual_momentum  # noqa: E402


def _ramp(start, drift, n=900, seed=0):
    rng = np.random.RandomState(seed)
    idx = pd.date_range("2022-01-01", periods=n, freq="D")
    close = start * np.cumprod(1 + drift + rng.normal(0, 0.002, n))
    return pd.DataFrame({"close": close}, index=idx)


def test_universe_constants():
    assert "FXE" in fx.FX_ETFS and "FXY" in fx.FX_ETFS
    assert fx.BENCHMARK == "UUP" and fx.CASH == "BIL"


def test_engine_runs_on_fx_universe():
    price = {s: _ramp(100, d, seed=i) for i, (s, d) in enumerate(
        [("FXE", 0.0005), ("FXY", -0.0003), ("FXB", 0.0004),
         ("FXA", 0.0006), ("FXF", 0.0002), ("BIL", 0.00004)])}
    res = backtest_dual_momentum(price, lookback=fx.LOOKBACK_M, top_k=fx.TOP_K, cash=fx.CASH)
    assert res["n_months"] > 0
    for k in ("profit_factor", "sharpe_annual", "max_drawdown"):
        assert k in res
