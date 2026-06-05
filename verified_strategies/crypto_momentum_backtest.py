#!/usr/bin/env python3
"""CRYPTO momentum (dual-momentum) backtest on CLEAN DAILY BARS.

New per-class archetype on the swarm-endorsed clean-bar track (sibling of
verified_strategies/etf_dual_momentum_backtest.py). Same textbook dual-momentum
mechanic (Antonacci), tuned for crypto:

  - lookback = 6 months (crypto trends faster than equities/ETFs)
  - top_k = 2 (hold the two strongest names that beat cash)
  - cash = BIL (risk-off T-bill proxy; crypto risk-off = exit to cash)
  - monthly rebalance, walk-forward by construction

We REUSE the proven engine from etf_dual_momentum_backtest:
  backtest_dual_momentum(price_data, lookback, top_k, cash)
  monthly_closes(df), dual_momentum_pick(...)

`run()` fetches the liquid-crypto USD universe + cash + benchmark via
data_fetcher.fetch_ohlcv, runs the backtest, computes #111 return-attribution
vs BTC monthly returns, a 5000-resample bootstrap PF 95% CI (seed 42), and a
cost-drag sensitivity at 0/10/20 bps per monthly rebalance. Prints a JSON
summary. Honest verdict gate is applied at the end.

NOTE on scale: these are yfinance USD spot closes (BTC-USD etc.), auto-adjusted.
Returns are monthly fractional returns of an equal-weight top-2 sleeve; PnL is
expressed as fractional/percentage of sleeve equity, NOT raw coin price.
"""
from __future__ import annotations

import os
import sys
from typing import Dict, List

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import etf_dual_momentum_backtest as dm  # reuse proven engine

# Liquid crypto USD universe (yfinance tickers)
CRYPTO_UNIVERSE: List[str] = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD",
    "XRP-USD", "ADA-USD", "AVAX-USD", "LINK-USD",
]
CASH = "BIL"
BENCHMARK = "BTC-USD"
LOOKBACK_M = 6
TOP_K = 2


def backtest_crypto_momentum(price_data: Dict, lookback: int = LOOKBACK_M,
                             top_k: int = TOP_K, cash: str = CASH) -> Dict:
    """Thin wrapper over the proven dual-momentum engine, crypto defaults."""
    return dm.backtest_dual_momentum(price_data, lookback=lookback,
                                     top_k=top_k, cash=cash)


def _bootstrap_pf_ci(monthly_returns: List[float], n_resamples: int = 5000,
                     seed: int = 42, alpha: float = 0.05) -> Dict:
    """Bootstrap 95% CI of monthly profit factor (resample-with-replacement)."""
    arr = np.asarray(monthly_returns, dtype=float)
    if arr.size < 2:
        return {"lower": None, "median": None, "upper": None,
                "n_resamples": 0, "note": "too few months"}
    rng = np.random.RandomState(seed)
    n = arr.size
    pfs = []
    for _ in range(n_resamples):
        sample = arr[rng.randint(0, n, n)]
        gains = sample[sample > 0].sum()
        losses = -sample[sample < 0].sum()
        if losses > 0:
            pf = gains / losses
        elif gains > 0:
            pf = 999.0
        else:
            pf = 0.0
        pfs.append(pf)
    pfs = np.array(pfs)
    return {
        "lower": round(float(np.percentile(pfs, 100 * alpha / 2)), 3),
        "median": round(float(np.percentile(pfs, 50)), 3),
        "upper": round(float(np.percentile(pfs, 100 * (1 - alpha / 2))), 3),
        "n_resamples": int(n_resamples),
        "note": "",
    }


def _cost_drag_check(monthly_returns: List[float],
                     bps_levels=(0, 10, 20)) -> Dict:
    """Apply a per-rebalance cost (bps of equity) each month; report net PF/Sharpe.

    A monthly-rebalanced sleeve pays roughly one round of turnover cost per month.
    We model cost as a flat deduction of `bps` from each monthly return.
    """
    import math
    arr = np.asarray(monthly_returns, dtype=float)
    out = {}
    for bps in bps_levels:
        cost = bps / 10000.0
        net = arr - cost
        gains = net[net > 0].sum()
        losses = -net[net < 0].sum()
        pf = float(gains / losses) if losses > 0 else (999.0 if gains > 0 else 0.0)
        sd = net.std(ddof=1)
        sharpe = float(net.mean() / sd * math.sqrt(12)) if sd > 0 else 0.0
        equity = np.cumprod(1 + net)
        peak = np.maximum.accumulate(equity)
        mdd = float(((equity - peak) / peak).min())
        out[f"{bps}bps"] = {
            "profit_factor": round(pf, 3),
            "sharpe_annual": round(sharpe, 3),
            "max_drawdown": round(mdd, 4),
            "total_return": round(float(equity[-1] - 1.0), 4),
        }
    return out


def _verdict(res: Dict) -> Dict:
    """Apply the honest gate. VALIDATED needs ALL of:
      attribution alpha_t >= 2.0 AND alpha_ir >= 0.10
      bootstrap PF lower > 1.0
      Sharpe >= 1.0
      MDD >= -0.20 (i.e. drawdown shallower than -20%)
    """
    reasons = []
    attr = res.get("attribution_vs_btc") or {}
    boot = res.get("bootstrap_pf_ci") or {}
    at = attr.get("alpha_t")
    ir = attr.get("alpha_ir")
    pf_lo = boot.get("lower")
    sharpe = res.get("sharpe_annual")
    mdd = res.get("max_drawdown")

    def _ge(v, t):
        return v is not None and v != float("inf") and v >= t

    pass_t = _ge(at, 2.0) or at == float("inf")
    pass_ir = _ge(ir, 0.10)
    pass_pf = pf_lo is not None and pf_lo > 1.0
    pass_sharpe = _ge(sharpe, 1.0)
    pass_mdd = mdd is not None and mdd >= -0.20

    if not pass_t:
        reasons.append(f"alpha_t={at} < 2.0 (no significant skill vs BTC beta)")
    if not pass_ir:
        reasons.append(f"alpha_ir={ir} < 0.10 (economically negligible alpha)")
    if not pass_pf:
        reasons.append(f"bootstrap PF lower={pf_lo} not > 1.0 (PF CI straddles loss)")
    if not pass_sharpe:
        reasons.append(f"sharpe={sharpe} < 1.0")
    if not pass_mdd:
        reasons.append(f"max_drawdown={mdd} worse than -0.20")

    all_pass = pass_t and pass_ir and pass_pf and pass_sharpe and pass_mdd
    n_pass = sum([pass_t, pass_ir, pass_pf, pass_sharpe, pass_mdd])
    if all_pass:
        verdict = "VALIDATED"
    elif n_pass == 0:
        verdict = "REJECTED"
    else:
        verdict = "MIXED"
    return {
        "verdict": verdict,
        "gates_passed": f"{n_pass}/5",
        "checks": {
            "alpha_t>=2.0": pass_t,
            "alpha_ir>=0.10": pass_ir,
            "bootstrap_pf_lower>1.0": pass_pf,
            "sharpe>=1.0": pass_sharpe,
            "mdd>=-0.20": pass_mdd,
        },
        "reasons": reasons,
    }


def run():  # pragma: no cover — live network
    import json
    import data_fetcher

    price = {}
    fetch_failures = []
    for a in CRYPTO_UNIVERSE + [CASH]:
        df, prov = data_fetcher.fetch_ohlcv(a, period_days=2600)
        price[a] = df
        if df is None:
            fetch_failures.append(a)
            print(f"  {a}: FETCH FAIL")
        else:
            print(f"  {a}: {len(df)} rows ({prov})")

    res = backtest_crypto_momentum(price)

    # attribution vs BTC monthly returns (real crypto-market benchmark)
    btc_df = price.get(BENCHMARK)
    rets = res.get("monthly_returns", [])
    if btc_df is not None and rets:
        btc_m = dm.monthly_closes(btc_df).pct_change().dropna()
        if len(btc_m) >= len(rets):
            import return_attribution as ra
            bench = btc_m.iloc[-len(rets):].tolist()
            res["attribution_vs_btc"] = ra.attribution_gate(rets, bench)
        else:
            res["attribution_vs_btc"] = {"ok": None, "note": "benchmark shorter than sleeve"}

    if rets:
        res["bootstrap_pf_ci"] = _bootstrap_pf_ci(rets, n_resamples=5000, seed=42)
        res["cost_drag"] = _cost_drag_check(rets, bps_levels=(0, 10, 20))

    res["fetch_failures"] = fetch_failures
    res["verdict_block"] = _verdict(res)

    summary = {k: v for k, v in res.items()
               if k not in ("monthly_returns", "holdings_tail")}
    print(json.dumps(summary, indent=2, default=str))
    return res


if __name__ == "__main__":  # pragma: no cover
    run()
