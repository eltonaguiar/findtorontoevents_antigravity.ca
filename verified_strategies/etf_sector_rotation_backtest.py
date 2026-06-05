#!/usr/bin/env python3
"""ETF SECTOR-ROTATION archetype backtest on CLEAN DAILY BARS (2026-06-04).

Sibling of `etf_dual_momentum_backtest.py`. Same walk-forward dual-momentum
engine, but the universe is the 11 SPDR **sector** ETFs instead of the
asset-class sleeve. This is the textbook "sector rotation" archetype:

  - Universe: 11 GICS sectors via SPDR Select Sector funds (XLK ... XLC).
  - Cash/risk-off proxy: SHY (1-3yr Treasury).
  - Benchmark for attribution: SPY (the cap-weighted market).
  - Monthly rebalance, lookback=12m, hold the top-3 sectors by 12m momentum
    that also beat cash (absolute filter). If none beat cash, hold SHY.

We reuse `backtest_dual_momentum` / `monthly_closes` / `dual_momentum_pick`
verbatim from the dual-momentum module so the engine is identical and already
unit-tested; only the universe + parameters differ.

`run()` fetches live daily closes, backtests, runs the #111 attribution gate
vs SPY, a 5000-resample bootstrap PF 95% CI (seed 42), and a cost-drag
sensitivity (0/10/20 bps per monthly rebalance). Prints a JSON summary and a
VALIDATED / MIXED / REJECTED verdict.
"""
from __future__ import annotations

import math
import os
import sys
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from etf_dual_momentum_backtest import (  # noqa: E402
    backtest_dual_momentum,
    dual_momentum_pick,
    monthly_closes,
)

# 11 SPDR Select Sector ETFs (GICS sectors). XLRE (real estate, 2015) and
# XLC (comm. services, 2018) inception-date later than the others, so the
# common monthly index is bounded by the shortest series.
SECTOR_ETFS = ["XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLU", "XLI", "XLB", "XLRE", "XLC"]
CASH = "SHY"
BENCHMARK = "SPY"
LOOKBACK_M = 12
TOP_K = 3


def backtest_sector_rotation(price_data: Dict[str, pd.DataFrame],
                             lookback: int = LOOKBACK_M, top_k: int = TOP_K,
                             cash: str = CASH) -> Dict:
    """Walk-forward monthly sector rotation. Thin wrapper over the shared engine."""
    return backtest_dual_momentum(price_data, lookback=lookback, top_k=top_k, cash=cash)


def bootstrap_pf_ci(monthly_returns: List[float], n_resamples: int = 5000,
                    seed: int = 42, ci: float = 0.95) -> Dict[str, float]:
    """Resample monthly returns with replacement; report PF distribution CI."""
    arr = np.asarray(monthly_returns, dtype=float)
    n = len(arr)
    if n < 2:
        return {"pf_lower": 0.0, "pf_median": 0.0, "pf_upper": 0.0, "n_resamples": 0}
    rng = np.random.RandomState(seed)
    pfs = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        sample = arr[rng.randint(0, n, size=n)]
        gains = sample[sample > 0].sum()
        losses = -sample[sample < 0].sum()
        if losses > 0:
            pfs[i] = gains / losses
        else:
            pfs[i] = 999.0 if gains > 0 else 0.0
    lo = (1.0 - ci) / 2.0
    return {
        "pf_lower": round(float(np.quantile(pfs, lo)), 3),
        "pf_median": round(float(np.quantile(pfs, 0.5)), 3),
        "pf_upper": round(float(np.quantile(pfs, 1.0 - lo)), 3),
        "n_resamples": n_resamples,
    }


def cost_drag_metrics(monthly_returns: List[float], cost_bps: float) -> Dict[str, float]:
    """Re-derive PF/Sharpe/MDD/CAGR after subtracting a per-month cost (bps)."""
    arr = np.asarray(monthly_returns, dtype=float) - (cost_bps / 1e4)
    if len(arr) == 0:
        return {}
    gains = arr[arr > 0].sum()
    losses = -arr[arr < 0].sum()
    pf = float(gains / losses) if losses > 0 else (999.0 if gains > 0 else 0.0)
    std = arr.std(ddof=1) if len(arr) > 1 else 0.0
    sharpe = float(arr.mean() / std * math.sqrt(12)) if std > 0 else 0.0
    equity = np.cumprod(1 + arr)
    peak = np.maximum.accumulate(equity)
    mdd = float(((equity - peak) / peak).min())
    cagr = float(equity[-1] ** (12 / len(arr)) - 1.0)
    return {
        "cost_bps": cost_bps,
        "profit_factor": round(pf, 3),
        "win_rate": round(float((arr > 0).mean()), 4),
        "sharpe_annual": round(sharpe, 3),
        "max_drawdown": round(mdd, 4),
        "cagr": round(cagr, 4),
    }


def verdict(res: Dict) -> Dict:
    """VALIDATED only if attr t>=2.0 AND ir>=0.10 AND boot PF lower>1.0
    AND Sharpe>=1.0 AND MDD>=-0.20. Else MIXED/REJECTED with reasons."""
    attr = res.get("attribution_vs_spy") or {}
    boot = res.get("bootstrap_pf_ci") or {}
    sharpe = res.get("sharpe_annual")
    mdd = res.get("max_drawdown")
    t = attr.get("alpha_t")
    ir = attr.get("alpha_ir")
    pf_lower = boot.get("pf_lower")

    checks = {
        "attr_t_ge_2.0": (t is not None and t != float("-inf")
                          and (t == float("inf") or t >= 2.0)),
        "attr_ir_ge_0.10": (ir is not None and ir >= 0.10),
        "bootstrap_pf_lower_gt_1.0": (pf_lower is not None and pf_lower > 1.0),
        "sharpe_ge_1.0": (sharpe is not None and sharpe >= 1.0),
        "mdd_ge_-0.20": (mdd is not None and mdd >= -0.20),
    }
    failed = [k for k, ok in checks.items() if not ok]
    n_pass = sum(1 for ok in checks.values() if ok)
    if not failed:
        label = "VALIDATED"
    elif n_pass >= 3:
        label = "MIXED"
    else:
        label = "REJECTED"
    return {"verdict": label, "checks": checks, "failed": failed,
            "n_pass": n_pass, "n_total": len(checks)}


def run():  # pragma: no cover — live network
    import json

    import data_fetcher
    import return_attribution as ra

    price: Dict[str, Optional[pd.DataFrame]] = {}
    fetch_report: Dict[str, str] = {}
    for a in SECTOR_ETFS + [CASH, BENCHMARK]:
        df, prov = data_fetcher.fetch_ohlcv(a, period_days=2600)
        price[a] = df
        status = ("%d rows (%s)" % (len(df), prov)) if df is not None else "FETCH FAIL"
        fetch_report[a] = status
        print(f"  {a}: {status}")

    # Engine ignores benchmark — pass only sectors + cash.
    engine_price = {a: price[a] for a in SECTOR_ETFS + [CASH] if price.get(a) is not None}
    res = backtest_sector_rotation(engine_price)

    rets = res.get("monthly_returns", [])

    # Attribution vs SPY monthly returns (real market benchmark).
    if rets and price.get(BENCHMARK) is not None:
        spy_m = monthly_closes(price[BENCHMARK]).pct_change().dropna()
        if len(spy_m) >= len(rets):
            bench = spy_m.iloc[-len(rets):].tolist()
            res["attribution_vs_spy"] = ra.attribution_gate(rets, bench)
        else:
            res["attribution_vs_spy"] = {"ok": None,
                                         "note": f"SPY months {len(spy_m)} < strat months {len(rets)}"}

    if rets:
        res["bootstrap_pf_ci"] = bootstrap_pf_ci(rets, n_resamples=5000, seed=42)
        res["cost_drag"] = [cost_drag_metrics(rets, c) for c in (0.0, 10.0, 20.0)]

    res["fetch_report"] = fetch_report
    res["verdict_detail"] = verdict(res)

    summary = {k: v for k, v in res.items()
               if k not in ("monthly_returns", "holdings_tail")}
    print(json.dumps(summary, indent=2, default=str))
    return res


if __name__ == "__main__":  # pragma: no cover
    run()
