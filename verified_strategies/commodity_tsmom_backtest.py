#!/usr/bin/env python3
"""Commodity time-series-momentum (TSMOM) backtest on CLEAN DAILY BARS (2026-06-03).

Same clean-bar method as the ETF dual-momentum sleeve (PR #502) but the canonical
COMMODITY archetype: TSMOM (Moskowitz-Ooi-Pedersen). Each commodity ETF is held
long for the next month iff its own trailing 12m return beats cash (absolute,
time-series momentum — each asset vs its OWN history, not cross-sectional rank);
the held set is equal-weighted; if nothing qualifies, hold cash.

Real daily closes via data_fetcher (yfinance), walk-forward (trailing-only),
fixed textbook params (no fitting). Gated via #111 attribution vs DBC (broad
commodity benchmark) + bootstrap PF CI + cost drag.
"""
from __future__ import annotations

import math
import os
import sys
from typing import Dict, List

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etf_dual_momentum_backtest import monthly_closes, _lookback_return  # reuse helpers

COMMODITIES = ["DBC", "GLD", "USO", "DBA", "SLV", "UNG"]   # broad/gold/oil/ag/silver/natgas
CASH = "BIL"
BENCHMARK = "DBC"
LOOKBACK_M = 12


def tsmom_longs(closes_by_asset: Dict[str, "object"], asof, lookback: int = LOOKBACK_M,
                cash: str = CASH) -> List[str]:
    """Assets whose OWN trailing return beats cash (time-series momentum)."""
    cash_ret = _lookback_return(closes_by_asset.get(cash), asof, lookback) if cash in closes_by_asset else 0.0
    cash_ret = 0.0 if cash_ret is None else cash_ret
    longs = []
    for a, closes in closes_by_asset.items():
        if a == cash:
            continue
        r = _lookback_return(closes, asof, lookback)
        if r is not None and r > cash_ret:
            longs.append(a)
    return longs if longs else [cash]


def backtest_tsmom(price_data: Dict, lookback: int = LOOKBACK_M, cash: str = CASH) -> Dict:
    closes = {a: monthly_closes(df) for a, df in price_data.items() if df is not None}
    if cash not in closes or len([a for a in closes if a != cash]) < 2:
        return {"error": "insufficient price data", "n_months": 0}
    months = sorted(set().union(*[set(s.index) for s in closes.values()]))
    rets = []
    holdings = []
    for i in range(lookback, len(months) - 1):
        asof, nxt = months[i], months[i + 1]
        longs = tsmom_longs(closes, asof, lookback, cash)
        month_rets = []
        for a in longs:
            s = closes[a]
            if asof in s.index and nxt in s.index:
                month_rets.append(float(s.loc[nxt] / s.loc[asof] - 1.0))
        if month_rets:
            r = sum(month_rets) / len(month_rets)
            rets.append(r)
            holdings.append((str(nxt.date()), longs, round(r, 4)))
    if not rets:
        return {"error": "no realized months", "n_months": 0}
    arr = np.array(rets)
    gains, losses = arr[arr > 0].sum(), -arr[arr < 0].sum()
    pf = float(gains / losses) if losses > 0 else (999.0 if gains > 0 else 0.0)
    eq = np.cumprod(1 + arr)
    peak = np.maximum.accumulate(eq)
    mdd = float(((eq - peak) / peak).min())
    sharpe = float(arr.mean() / arr.std(ddof=1) * math.sqrt(12)) if arr.std(ddof=1) > 0 else 0.0
    return {
        "n_months": len(arr), "monthly_returns": arr.tolist(),
        "total_return": round(float(eq[-1] - 1.0), 4),
        "cagr": round(float(eq[-1] ** (12 / len(arr)) - 1.0), 4),
        "profit_factor": round(pf, 3), "win_rate": round(float((arr > 0).mean()), 4),
        "sharpe_annual": round(sharpe, 3), "max_drawdown": round(mdd, 4),
        "holdings_tail": holdings[-12:],
    }


def run():  # pragma: no cover — live network
    import json
    import data_fetcher
    import return_attribution as ra
    price = {}
    for a in COMMODITIES + [CASH]:
        df, prov = data_fetcher.fetch_ohlcv(a, period_days=2600)
        price[a] = df
        print(f"  {a}: {'%d rows (%s)' % (len(df), prov) if df is not None else 'FETCH FAIL'}")
    res = backtest_tsmom(price)
    bench_m = monthly_closes(price[BENCHMARK]).pct_change().dropna()
    rets = res.get("monthly_returns", [])
    if rets and len(bench_m) >= len(rets):
        res["attribution_vs_dbc"] = ra.attribution_gate(rets, bench_m.iloc[-len(rets):].tolist())
    print(json.dumps({k: v for k, v in res.items()
                      if k not in ("monthly_returns", "holdings_tail")}, indent=2, default=str))
    return res


if __name__ == "__main__":  # pragma: no cover
    run()
