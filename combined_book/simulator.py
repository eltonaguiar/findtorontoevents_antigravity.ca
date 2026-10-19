"""Month-end engine: combine sleeve returns into a book series + equity curve."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from combined_book.combiner import (
    apply_per_sleeve_cap,
    inverse_vol_weights,
    max_drawdown,
)
from combined_book.fetch import UNIVERSE, monthly_returns
from combined_book.gates import (
    annualized_sharpe,
    bootstrapped_pf,
    profit_factor,
    sharpe,
)
from combined_book.put_sleeve import put_monthly_returns
from combined_book.quality_sleeve import QUALITY_UNIVERSE, quality_monthly_returns
from combined_book.trend_sleeve import trend_target_weights


def combine_sleeves(sleeve_returns, weights):
    frame = pd.DataFrame(sleeve_returns).fillna(0.0)
    ordered = [k for k in weights if k in frame.columns]
    return frame[ordered].dot(
        pd.Series({k: weights[k] for k in ordered})
    )


def book_return_series(sleeve_returns, vols, vol_cap):
    w = apply_per_sleeve_cap(inverse_vol_weights(vols))
    r = combine_sleeves(sleeve_returns, w)
    annual = r.std(ddof=0) * math.sqrt(12)
    if annual > 0:
        r = r * (vol_cap / annual)
    return r, w


def equity_curve(monthly_returns):
    return (1.0 + monthly_returns).cumprod()


def max_drawdown_from_returns(monthly_returns):
    return max_drawdown(equity_curve(monthly_returns).values)


def compute_stats(monthly_returns, n_variants=1):
    r = monthly_returns.dropna()
    n = len(r)
    wins = int((r > 0).sum())
    eq = equity_curve(r)
    span_years = max(n / 12.0, 1e-9)
    cagr = float((eq.iloc[-1] ** (1.0 / span_years)) - 1.0) if n > 0 else 0.0
    pfs = bootstrapped_pf(r.tolist())
    boot_p_over_1 = float(np.mean(np.asarray(pfs) <= 1.0))
    return {
        "n_months": n,
        "cagr": cagr,
        "sharpe": sharpe(r.tolist()),
        "annualized_sharpe": annualized_sharpe(r.tolist()),
        "max_dd": max_drawdown_from_returns(r),
        "pf": profit_factor(r.tolist()),
        "win_rate": wins / n if n > 0 else 0.0,
        "wins": wins,
        "bootstrap_p_over_1": boot_p_over_1,
        "n_variants": n_variants,
    }


def run_backtest(fetch_func, vol_cap=0.05, start=None, end=None):
    closes = fetch_func()
    monthly = {
        sym: monthly_returns(c)
        for sym, c in closes.items()
        if not c.empty
    }
    trend_symbols = {
        s for s, kind in UNIVERSE.items() if kind.startswith("trend")
    }
    trend_closes = {s: c for s, c in closes.items() if s in trend_symbols}
    w_trend = trend_target_weights(trend_closes, cap_fraction=1.0)
    if w_trend:
        trend_ret = combine_sleeves(
            {s: monthly[s] for s in w_trend if s in monthly}, w_trend
        ).fillna(0.0)
    else:
        trend_ret = pd.Series(dtype=float)
    qual_ret = quality_monthly_returns(
        {s: monthly[s] for s in QUALITY_UNIVERSE if s in monthly}
    )
    put_ret = put_monthly_returns(monthly, use_index=True)
    sleeve = {"trend": trend_ret, "quality": qual_ret, "put": put_ret}
    vols = {
        k: float(v.std(ddof=0)) if len(v) > 1 else 0.0
        for k, v in sleeve.items()
    }
    r, w = book_return_series(sleeve, vols, vol_cap)
    if start:
        r = r.loc[start:]
    if end:
        r = r.loc[:end]
    r = r.dropna()
    return {"returns": r, "weights": w, "stats": compute_stats(r)}
