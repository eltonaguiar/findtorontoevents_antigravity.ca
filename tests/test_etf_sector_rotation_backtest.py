"""ETF sector-rotation backtest — offline tests on synthetic price frames."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verified_strategies"))
import etf_sector_rotation_backtest as sr  # noqa: E402


def _ramp_df(start, daily_drift, n_days=900, seed=0):
    rng = np.random.RandomState(seed)
    idx = pd.date_range("2022-01-01", periods=n_days, freq="D")
    rets = daily_drift + rng.normal(0, 0.002, n_days)
    close = start * np.cumprod(1 + rets)
    return pd.DataFrame({"close": close}, index=idx)


def _synth_universe(drifts, seed0=1):
    """Build a sector + SHY price dict from a {sector: drift} mapping."""
    price = {}
    for i, (sym, drift) in enumerate(drifts.items()):
        price[sym] = _ramp_df(100, drift, seed=seed0 + i)
    return price


def test_picks_top3_sectors_by_momentum():
    # XLK > XLY > XLF fastest; rest flat; SHY ~flat -> top-3 = those three.
    drifts = {
        "XLK": 0.0012, "XLY": 0.0010, "XLF": 0.0009,
        "XLE": 0.0001, "XLV": 0.0001, "XLP": 0.00005,
        "XLU": 0.00005, "XLI": 0.0001, "XLB": 0.00008,
        "XLRE": 0.00006, "XLC": 0.00007, "SHY": 0.00003,
    }
    closes = {s: sr.monthly_closes(df) for s, df in _synth_universe(drifts).items()}
    asof = sorted(closes["XLK"].index)[-1]
    pick = sr.dual_momentum_pick(closes, asof, lookback=12, top_k=3, cash="SHY")
    assert set(pick) == {"XLK", "XLY", "XLF"}
    assert len(pick) == 3


def test_risk_off_goes_to_cash():
    # All sectors falling, SHY rising -> absolute filter empties -> hold SHY.
    drifts = {s: -0.0010 for s in sr.SECTOR_ETFS}
    drifts["SHY"] = 0.0003
    closes = {s: sr.monthly_closes(df) for s, df in _synth_universe(drifts).items()}
    asof = sorted(closes["XLK"].index)[-1]
    assert sr.dual_momentum_pick(closes, asof, lookback=12, top_k=3, cash="SHY") == ["SHY"]


def test_backtest_runs_and_reports_metrics():
    drifts = {
        "XLK": 0.0010, "XLY": 0.0009, "XLF": 0.0008,
        "XLE": 0.0003, "XLV": 0.0004, "XLP": 0.0002,
        "XLU": 0.0002, "XLI": 0.0005, "XLB": 0.0003,
        "XLRE": 0.0002, "XLC": 0.0004, "SHY": 0.00004,
    }
    res = sr.backtest_sector_rotation(_synth_universe(drifts))
    assert res["n_months"] > 0
    for k in ("profit_factor", "win_rate", "sharpe_annual", "max_drawdown", "cagr"):
        assert k in res
    assert -1.0 <= res["max_drawdown"] <= 0.0


def test_bootstrap_and_cost_drag_and_verdict():
    rets = [0.03, -0.01, 0.02, 0.04, -0.02, 0.01, 0.03, -0.015,
            0.025, 0.01, -0.005, 0.02, 0.015, -0.01, 0.03, 0.02,
            -0.02, 0.01, 0.025, 0.005, 0.03, -0.01, 0.02, 0.015]
    boot = sr.bootstrap_pf_ci(rets, n_resamples=1000, seed=42)
    assert boot["pf_lower"] <= boot["pf_median"] <= boot["pf_upper"]
    assert boot["n_resamples"] == 1000

    base = sr.cost_drag_metrics(rets, 0.0)
    drag = sr.cost_drag_metrics(rets, 20.0)
    # Costs only reduce profit factor.
    assert drag["profit_factor"] <= base["profit_factor"]

    v = sr.verdict({
        "attribution_vs_spy": {"alpha_t": 3.0, "alpha_ir": 0.2},
        "bootstrap_pf_ci": {"pf_lower": 1.5},
        "sharpe_annual": 1.4, "max_drawdown": -0.15,
    })
    assert v["verdict"] == "VALIDATED"
    v2 = sr.verdict({
        "attribution_vs_spy": {"alpha_t": 0.5, "alpha_ir": 0.01},
        "bootstrap_pf_ci": {"pf_lower": 0.8},
        "sharpe_annual": 0.3, "max_drawdown": -0.35,
    })
    assert v2["verdict"] == "REJECTED"
