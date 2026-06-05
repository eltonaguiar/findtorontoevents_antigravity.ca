"""CRYPTO momentum backtest — offline tests on synthetic price frames."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verified_strategies"))
import crypto_momentum_backtest as cm  # noqa: E402
import etf_dual_momentum_backtest as dm  # noqa: E402


def _ramp_df(start, daily_drift, n_days=900, seed=0, vol=0.02):
    """Crypto-scale synthetic daily closes (higher vol than ETFs)."""
    rng = np.random.RandomState(seed)
    idx = pd.date_range("2021-01-01", periods=n_days, freq="D")
    rets = daily_drift + rng.normal(0, vol, n_days)
    close = start * np.cumprod(1 + rets)
    return pd.DataFrame({"close": close}, index=idx)


def test_engine_runs_on_crypto_universe():
    # Build a full crypto universe + cash; engine should produce metrics.
    price = {
        "BTC-USD": _ramp_df(30000, 0.0012, seed=1),
        "ETH-USD": _ramp_df(2000, 0.0014, seed=2),
        "SOL-USD": _ramp_df(100, 0.0016, seed=3),
        "BNB-USD": _ramp_df(300, 0.0008, seed=4),
        "XRP-USD": _ramp_df(0.5, 0.0005, seed=5),
        "ADA-USD": _ramp_df(0.4, 0.0006, seed=6),
        "AVAX-USD": _ramp_df(20, 0.0010, seed=7),
        "LINK-USD": _ramp_df(15, 0.0009, seed=8),
        "BIL": _ramp_df(91, 0.00004, seed=9, vol=0.0005),
    }
    res = cm.backtest_crypto_momentum(price)
    assert res["n_months"] > 0
    for k in ("profit_factor", "win_rate", "sharpe_annual", "max_drawdown", "cagr"):
        assert k in res
    assert -1.0 <= res["max_drawdown"] <= 0.0


def test_risk_off_goes_to_cash():
    # All crypto names crashing, cash drifting up -> dual momentum holds cash.
    data = {
        "BTC-USD": dm.monthly_closes(_ramp_df(30000, -0.0015, seed=1, vol=0.005)),
        "ETH-USD": dm.monthly_closes(_ramp_df(2000, -0.0018, seed=2, vol=0.005)),
        "SOL-USD": dm.monthly_closes(_ramp_df(100, -0.0020, seed=3, vol=0.005)),
        "BIL": dm.monthly_closes(_ramp_df(91, 0.0003, seed=9, vol=0.0005)),
    }
    asof = sorted(data["BTC-USD"].index)[-1]
    assert dm.dual_momentum_pick(data, asof, lookback=cm.LOOKBACK_M,
                                 top_k=cm.TOP_K, cash=cm.CASH) == ["BIL"]


def test_top_k_picks_two_strongest():
    # SOL + ETH the two fastest movers -> top_k=2 holds exactly those.
    data = {
        "BTC-USD": dm.monthly_closes(_ramp_df(30000, 0.0005, seed=1, vol=0.004)),
        "ETH-USD": dm.monthly_closes(_ramp_df(2000, 0.0018, seed=2, vol=0.004)),
        "SOL-USD": dm.monthly_closes(_ramp_df(100, 0.0022, seed=3, vol=0.004)),
        "BNB-USD": dm.monthly_closes(_ramp_df(300, 0.0007, seed=4, vol=0.004)),
        "BIL": dm.monthly_closes(_ramp_df(91, 0.00004, seed=9, vol=0.0005)),
    }
    asof = sorted(data["BTC-USD"].index)[-1]
    pick = dm.dual_momentum_pick(data, asof, lookback=cm.LOOKBACK_M,
                                 top_k=cm.TOP_K, cash=cm.CASH)
    assert len(pick) == 2
    assert set(pick) == {"SOL-USD", "ETH-USD"}


def test_bootstrap_ci_deterministic_with_seed():
    rets = [0.05, -0.03, 0.08, -0.02, 0.04, -0.06, 0.10, 0.01, -0.04, 0.03,
            0.07, -0.05, 0.02, 0.06, -0.01]
    a = cm._bootstrap_pf_ci(rets, n_resamples=1000, seed=42)
    b = cm._bootstrap_pf_ci(rets, n_resamples=1000, seed=42)
    assert a == b
    assert a["lower"] <= a["median"] <= a["upper"]
