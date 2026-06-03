#!/usr/bin/env python3
"""ETF dual-momentum backtest on CLEAN DAILY BARS (swarm-endorsed track, 2026-06-03).

The cross-review (reports/APPROACH_strategy_attribution_edge_hunt_2026-06-03.md)
rejected re-auditing the temporally-broken pick ledger and endorsed building NEW
per-class archetypes on clean daily bars with proper walk-forward + attribution.
This is that: a textbook **dual-momentum** sleeve (Antonacci) on liquid ETFs.

Dual momentum, monthly rebalance:
  - ABSOLUTE filter: an asset is eligible only if its lookback return > cash (BIL/SHY).
  - RELATIVE rank: among eligible risk assets, hold the top-k by lookback return.
  - If nothing is eligible (risk-off), hold cash.

Returns are REAL daily ETF closes (clean timestamps, no batch-stamp problem), and
the test is walk-forward by construction (each month uses only trailing data).

Pure functions are unit-tested offline; `run()` fetches live data via data_fetcher
and reports PF / Sharpe / MDD + #111 attribution vs SPY + bootstrap-CI of monthly PF.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

RISK_ASSETS = ["SPY", "QQQ", "EFA", "AGG", "GLD"]   # equity/intl/bond/gold
CASH = "BIL"                                          # T-bill proxy (risk-off)
LOOKBACK_M = 12
TOP_K = 1


def monthly_closes(daily: pd.DataFrame) -> pd.Series:
    """Month-end close series from a daily OHLC frame (index=date, col 'close')."""
    s = daily["close"].copy()
    s.index = pd.to_datetime(s.index)
    # "ME" (month-end) is the pandas >=2.2 alias; fall back to "M" on older
    # pandas (CI runs an unpinned, sometimes <2.2 pandas) — matches the
    # try/except pattern in tools/backtest_etf_economic.py.
    try:
        return s.resample("ME").last().dropna()
    except ValueError:
        return s.resample("M").last().dropna()


def _lookback_return(closes: pd.Series, asof: pd.Timestamp, months: int) -> Optional[float]:
    hist = closes[closes.index <= asof]
    if len(hist) < months + 1:
        return None
    return float(hist.iloc[-1] / hist.iloc[-1 - months] - 1.0)


def dual_momentum_pick(closes_by_asset: Dict[str, pd.Series], asof: pd.Timestamp,
                       lookback: int = LOOKBACK_M, top_k: int = TOP_K,
                       cash: str = CASH) -> List[str]:
    """Return the asset(s) to hold for the month starting at `asof`."""
    cash_ret = _lookback_return(closes_by_asset.get(cash, pd.Series(dtype=float)),
                                asof, lookback)
    cash_ret = 0.0 if cash_ret is None else cash_ret
    ranked = []
    for a, closes in closes_by_asset.items():
        if a == cash:
            continue
        r = _lookback_return(closes, asof, lookback)
        if r is None:
            continue
        ranked.append((a, r))
    # absolute filter: beat cash; relative: top-k by return
    eligible = [(a, r) for a, r in ranked if r > cash_ret]
    if not eligible:
        return [cash]
    eligible.sort(key=lambda x: -x[1])
    return [a for a, _ in eligible[:top_k]]


def backtest_dual_momentum(price_data: Dict[str, pd.DataFrame],
                           lookback: int = LOOKBACK_M, top_k: int = TOP_K,
                           cash: str = CASH) -> Dict:
    """Walk-forward monthly dual-momentum backtest. Returns metrics + monthly rets."""
    closes = {a: monthly_closes(df) for a, df in price_data.items() if df is not None}
    if cash not in closes or len([a for a in closes if a != cash]) < 2:
        return {"error": "insufficient price data", "n_months": 0}

    # common monthly index
    all_idx = sorted(set().union(*[set(s.index) for s in closes.values()]))
    months = [m for m in all_idx]
    strat_rets: List[float] = []
    holdings: List[Tuple] = []
    for i in range(lookback, len(months) - 1):
        asof = months[i]
        nxt = months[i + 1]
        pick = dual_momentum_pick(closes, asof, lookback, top_k, cash)
        # realized next-month return = equal-weight of picks
        rets = []
        for a in pick:
            s = closes[a]
            if asof in s.index and nxt in s.index:
                rets.append(float(s.loc[nxt] / s.loc[asof] - 1.0))
        if rets:
            r = sum(rets) / len(rets)
            strat_rets.append(r)
            holdings.append((str(nxt.date()), pick, round(r, 4)))

    if not strat_rets:
        return {"error": "no realized months", "n_months": 0}
    arr = np.array(strat_rets)
    gains = arr[arr > 0].sum()
    losses = -arr[arr < 0].sum()
    pf = float(gains / losses) if losses > 0 else (999.0 if gains > 0 else 0.0)
    wr = float((arr > 0).mean())
    sharpe = float(arr.mean() / arr.std(ddof=1) * math.sqrt(12)) if arr.std(ddof=1) > 0 else 0.0
    equity = np.cumprod(1 + arr)
    peak = np.maximum.accumulate(equity)
    mdd = float(((equity - peak) / peak).min())
    cagr = float(equity[-1] ** (12 / len(arr)) - 1.0)
    return {
        "n_months": len(arr),
        "monthly_returns": arr.tolist(),
        "total_return": round(float(equity[-1] - 1.0), 4),
        "cagr": round(cagr, 4),
        "profit_factor": round(pf, 3),
        "win_rate": round(wr, 4),
        "sharpe_annual": round(sharpe, 3),
        "max_drawdown": round(mdd, 4),
        "holdings_tail": holdings[-12:],
    }


def run():  # pragma: no cover — live network
    import json
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import data_fetcher
    import return_attribution as ra

    price = {}
    for a in RISK_ASSETS + [CASH]:
        df, prov = data_fetcher.fetch_ohlcv(a, period_days=2600)
        price[a] = df
        print(f"  {a}: {'%d rows (%s)' % (len(df), prov) if df is not None else 'FETCH FAIL'}")
    res = backtest_dual_momentum(price)
    # attribution vs SPY monthly returns (real market benchmark)
    spy_m = monthly_closes(price["SPY"]).pct_change().dropna()
    rets = res.get("monthly_returns", [])
    if rets and len(spy_m) >= len(rets):
        bench = spy_m.iloc[-len(rets):].tolist()
        res["attribution_vs_spy"] = ra.attribution_gate(rets, bench)
    print(json.dumps({k: v for k, v in res.items()
                      if k not in ("monthly_returns", "holdings_tail")}, indent=2, default=str))
    return res


if __name__ == "__main__":  # pragma: no cover
    run()
