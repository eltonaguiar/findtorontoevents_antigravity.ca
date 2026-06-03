#!/usr/bin/env python3
"""FX trend-following backtest on CLEAN DAILY BARS (2026-06-03).

Same clean-bar method as ETF (PR #502, PASSED) / commodity (PR #506, REJECTED).
Canonical FX archetype: cross-sectional trend-following on liquid currency ETFs —
hold the top-k currencies by trailing 12m return (relative momentum) that also beat
cash (absolute filter); else cash. Reuses the generic dual-momentum engine.

Universe: FXE (EUR), FXY (JPY), FXB (GBP), FXA (AUD), FXF (CHF) vs BIL (cash).
Benchmark for attribution: UUP (US-dollar-bull index — the dominant FX beta).
Real yfinance daily, walk-forward, fixed textbook params (no fitting).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etf_dual_momentum_backtest import backtest_dual_momentum, monthly_closes  # reuse engine

FX_ETFS = ["FXE", "FXY", "FXB", "FXA", "FXF"]   # EUR/JPY/GBP/AUD/CHF
CASH = "BIL"
BENCHMARK = "UUP"
LOOKBACK_M = 12
TOP_K = 1


def run():  # pragma: no cover — live network
    import json
    import numpy as np
    import data_fetcher
    import return_attribution as ra

    price = {}
    for a in FX_ETFS + [CASH, BENCHMARK]:
        df, prov = data_fetcher.fetch_ohlcv(a, period_days=2600)
        price[a] = df
        print(f"  {a}: {'%d rows (%s)' % (len(df), prov) if df is not None else 'FETCH FAIL'}")
    # backtest universe excludes the benchmark
    bt_price = {a: price[a] for a in FX_ETFS + [CASH] if price.get(a) is not None}
    res = backtest_dual_momentum(bt_price, lookback=LOOKBACK_M, top_k=TOP_K, cash=CASH)
    rets = res.get("monthly_returns", [])
    if rets and price.get(BENCHMARK) is not None:
        bench = monthly_closes(price[BENCHMARK]).pct_change().dropna()
        if len(bench) >= len(rets):
            res["attribution_vs_uup"] = ra.attribution_gate(rets, bench.iloc[-len(rets):].tolist())
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
