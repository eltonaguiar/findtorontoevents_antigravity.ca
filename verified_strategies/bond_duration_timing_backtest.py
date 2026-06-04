#!/usr/bin/env python3
"""BOND duration-timing backtest on CLEAN DAILY BARS (2026-06-03).

Same clean-bar method as ETF (#502 PASS) / commodity (#506 REJECT) / FX (#508) /
EQUITY (#517). Canonical BOND archetype: duration timing via dual-momentum across
the duration spectrum — hold the bond ETF with the strongest trailing 12m return
that also beats short-duration cash (absolute filter), monthly; else short cash.
This rotates long-duration (TLT) in falling-rate regimes and short-duration (SHY)
in rising-rate regimes. Reuses the generic dual-momentum engine.

Universe: TLT (20y+), IEF (7-10y), AGG (agg), LQD (IG corp) vs SHY (1-3y cash).
Benchmark for attribution: AGG (the aggregate-bond beta). Real yfinance daily,
walk-forward, fixed textbook params (no fitting). Addresses BOND n=0 (BONDS#7).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etf_dual_momentum_backtest import backtest_dual_momentum, monthly_closes  # reuse engine

UNIVERSE = ["TLT", "IEF", "AGG", "LQD"]   # long / intermediate / agg / IG-corp
CASH = "SHY"                               # short-duration treasuries = risk-off
BENCHMARK = "AGG"
LOOKBACK_M = 12
TOP_K = 1


def run():  # pragma: no cover — live network
    import json
    import numpy as np
    import data_fetcher
    import return_attribution as ra

    price = {}
    for a in UNIVERSE + [CASH, BENCHMARK]:
        df, prov = data_fetcher.fetch_ohlcv(a, period_days=2600)
        price[a] = df
        print(f"  {a}: {'%d rows' % len(df) if df is not None else 'FETCH FAIL'}")
    bt_price = {a: price[a] for a in UNIVERSE + [CASH] if price.get(a) is not None}
    res = backtest_dual_momentum(bt_price, lookback=LOOKBACK_M, top_k=TOP_K, cash=CASH)
    rets = res.get("monthly_returns", [])
    if rets and price.get(BENCHMARK) is not None:
        bench = monthly_closes(price[BENCHMARK]).pct_change().dropna()
        if len(bench) >= len(rets):
            res["attribution_vs_agg"] = ra.attribution_gate(rets, bench.iloc[-len(rets):].tolist())
    if rets:
        arr = np.array(rets)
        rng = np.random.RandomState(42)
        pfs = []
        for _ in range(5000):
            s = rng.choice(arr, len(arr), replace=True)
            gp, gl = s[s > 0].sum(), -s[s < 0].sum()
            pfs.append(gp / gl if gl > 0 else 0.0)
        res["bootstrap_pf_ci"] = [round(float(np.percentile(pfs, 2.5)), 2),
                                  round(float(np.percentile(pfs, 97.5)), 2)]
    print(json.dumps({k: v for k, v in res.items()
                      if k not in ("monthly_returns", "holdings_tail")}, indent=2, default=str))
    return res


if __name__ == "__main__":  # pragma: no cover
    run()
