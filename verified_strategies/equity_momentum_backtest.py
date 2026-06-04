#!/usr/bin/env python3
"""EQUITY cross-sectional momentum backtest on CLEAN DAILY BARS (2026-06-03).

Same clean-bar method as the ETF sleeve (PR #502 PASS) / commodity (#506 REJECT) /
FX (#508 MIXED). Canonical EQUITY archetype: cross-sectional momentum — hold the
top-k mega-caps by trailing 12m return that also beat cash (absolute filter),
equal-weight, monthly rebalance; else cash. Reuses the generic dual-momentum engine.

Universe: liquid mega-caps (AAPL/MSFT/NVDA/GOOGL/AMZN/META/JPM/V/UNH/COST/LLY/AVGO)
vs BIL. Benchmark for attribution: SPY (the dominant equity beta). top_k=3.
Real yfinance daily, walk-forward, fixed textbook params (no fitting).

NOTE on survivorship: this fixed mega-cap list is chosen with hindsight (today's
winners) — a known upward bias. Treat any PASS as provisional; the binding test is
forward paper, not this backtest.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etf_dual_momentum_backtest import backtest_dual_momentum, monthly_closes  # reuse engine

UNIVERSE = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META",
            "JPM", "V", "UNH", "COST", "LLY", "AVGO"]
CASH = "BIL"
BENCHMARK = "SPY"
LOOKBACK_M = 12
TOP_K = 3


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
            res["attribution_vs_spy"] = ra.attribution_gate(rets, bench.iloc[-len(rets):].tolist())
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
