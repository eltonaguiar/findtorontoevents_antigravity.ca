#!/usr/bin/env python3
"""ETF inverse-volatility (risk-parity-lite) rotation backtest on CLEAN DAILY BARS.

Clean-bar track (swarm-endorsed 2026-06-03): build NEW per-class archetypes on real
daily ETF closes with proper walk-forward + #111 attribution, instead of re-auditing
the temporally-broken pick ledger.

This is the canonical RISK-PARITY-LITE sleeve: hold a multi-asset basket
(equity / long-bond / gold / commodity) every month, weighting each asset
INVERSELY to its trailing realized volatility so each contributes a more equal
share of portfolio risk. No leverage, no covariance term (that's the "-lite"):

  vol_i   = std of trailing 63-trading-day (≈3mo) daily returns of asset i
  w_i     = (1 / vol_i) / sum_j (1 / vol_j)            (weights sum to 1, long-only)
  r_port  = sum_i w_i * (next-month return of asset i)

Walk-forward by construction: each month's weights use only trailing data, and the
realized return is the FOLLOWING month. Monthly rebalance.

Pure functions are unit-tested offline; `run()` fetches live daily closes via
data_fetcher and reports PF / Sharpe / WR / MDD / CAGR + #111 attribution vs SPY +
5000-resample bootstrap PF 95% CI + cost-drag sensitivity (0/10/20 bps per rebalance).

Honest expectation: a diversified risk-parity sleeve typically has LOW drawdown and a
respectable Sharpe, but its alpha vs SPY is often small/insignificant (it IS largely
beta to a balanced-fund factor). The attribution gate is expected to be the binding
constraint — report it honestly.
"""
from __future__ import annotations

import math
import os
import sys
from typing import Dict, List

import numpy as np
import pandas as pd

# Reuse the verified month-end helper from the dual-momentum sleeve.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etf_dual_momentum_backtest import monthly_closes  # noqa: E402

UNIVERSE = ["SPY", "TLT", "GLD", "DBC"]   # equity / long-bond / gold / commodity
BENCHMARK = "SPY"
VOL_LOOKBACK_DAYS = 63                    # ≈3 trading months of daily returns
MIN_VOL = 1e-6                            # floor to avoid div-by-zero on a flat asset


def inverse_vol_weights(vols: Dict[str, float]) -> Dict[str, float]:
    """Inverse-volatility weights that sum to 1 (long-only, no leverage).

    w_i = (1 / vol_i) / sum_j (1 / vol_j). Assets with None/<=0 vol are dropped.
    Returns {} when no asset has a usable vol.
    """
    inv = {a: 1.0 / max(float(v), MIN_VOL)
           for a, v in vols.items()
           if v is not None and np.isfinite(v) and float(v) > 0.0}
    total = sum(inv.values())
    if total <= 0.0:
        return {}
    return {a: iv / total for a, iv in inv.items()}


def trailing_vol(daily_closes: pd.Series, asof: pd.Timestamp,
                 lookback_days: int = VOL_LOOKBACK_DAYS):
    """Std of the trailing `lookback_days` daily returns as of (and including) asof.

    Returns None when there isn't enough trailing history. Uses ONLY data at or
    before `asof` (walk-forward / no look-ahead).
    """
    hist = daily_closes[daily_closes.index <= asof]
    if len(hist) < lookback_days + 2:
        return None
    rets = hist.iloc[-(lookback_days + 1):].pct_change().dropna()
    if len(rets) < lookback_days // 2:
        return None
    v = float(rets.std(ddof=1))
    return v if np.isfinite(v) and v > 0.0 else None


def _metrics(arr: np.ndarray) -> Dict:
    gains = arr[arr > 0].sum()
    losses = -arr[arr < 0].sum()
    pf = float(gains / losses) if losses > 0 else (999.0 if gains > 0 else 0.0)
    wr = float((arr > 0).mean())
    sd = arr.std(ddof=1)
    sharpe = float(arr.mean() / sd * math.sqrt(12)) if sd > 0 else 0.0
    eq = np.cumprod(1 + arr)
    peak = np.maximum.accumulate(eq)
    mdd = float(((eq - peak) / peak).min())
    cagr = float(eq[-1] ** (12 / len(arr)) - 1.0)
    return {
        "n_months": int(len(arr)),
        "total_return": round(float(eq[-1] - 1.0), 4),
        "cagr": round(cagr, 4),
        "profit_factor": round(pf, 3),
        "win_rate": round(wr, 4),
        "sharpe_annual": round(sharpe, 3),
        "max_drawdown": round(mdd, 4),
    }


def backtest_risk_parity(price_data: Dict[str, pd.DataFrame],
                         lookback_days: int = VOL_LOOKBACK_DAYS,
                         cost_bps: float = 0.0) -> Dict:
    """Walk-forward monthly inverse-vol backtest.

    For each month boundary, compute inverse-vol weights from trailing daily vol
    (data <= asof), then realize the NEXT month's weighted return. `cost_bps` is a
    flat per-rebalance drag (basis points) subtracted from each monthly return.
    """
    daily = {a: df["close"].copy() for a, df in price_data.items() if df is not None}
    for a, s in daily.items():
        s.index = pd.to_datetime(s.index)
    monthly = {a: monthly_closes(df) for a, df in price_data.items() if df is not None}
    if len([a for a in UNIVERSE if a in monthly]) < 2:
        return {"error": "insufficient price data", "n_months": 0}

    assets = [a for a in UNIVERSE if a in monthly]
    months = sorted(set().union(*[set(monthly[a].index) for a in assets]))
    cost = cost_bps / 10_000.0

    rets: List[float] = []
    holdings: List = []
    # Need enough leading daily history for the first vol estimate; the monthly
    # loop naturally skips early months where trailing_vol returns None.
    for i in range(len(months) - 1):
        asof, nxt = months[i], months[i + 1]
        vols = {a: trailing_vol(daily[a], asof, lookback_days) for a in assets}
        w = inverse_vol_weights(vols)
        if not w:
            continue
        # realized next-month return at those (trailing-derived) weights
        port = 0.0
        wsum = 0.0
        for a, wi in w.items():
            s = monthly[a]
            if asof in s.index and nxt in s.index:
                port += wi * float(s.loc[nxt] / s.loc[asof] - 1.0)
                wsum += wi
        if wsum <= 0.0:
            continue
        # renormalize if some asset lacked a monthly print at this boundary
        if wsum < 0.999:
            port = port / wsum
        port -= cost
        rets.append(port)
        holdings.append((str(nxt.date()),
                         {a: round(wi, 3) for a, wi in sorted(w.items())},
                         round(port, 4)))

    if not rets:
        return {"error": "no realized months", "n_months": 0}
    arr = np.array(rets, dtype=float)
    out = _metrics(arr)
    out["monthly_returns"] = arr.tolist()
    out["holdings_tail"] = holdings[-12:]
    out["cost_bps"] = cost_bps
    return out


def bootstrap_pf_ci(monthly_returns: List[float], n_resamples: int = 5000,
                    seed: int = 42, ci: float = 0.95) -> Dict:
    """Resample monthly returns with replacement; report PF distribution CI."""
    arr = np.asarray(monthly_returns, dtype=float)
    if len(arr) < 5:
        return {"pf_lower": None, "pf_median": None, "pf_upper": None,
                "n_resamples": 0, "note": "too few months for bootstrap"}
    rng = np.random.RandomState(seed)
    n = len(arr)
    pfs = np.empty(n_resamples, dtype=float)
    for k in range(n_resamples):
        sample = arr[rng.randint(0, n, size=n)]
        gains = sample[sample > 0].sum()
        losses = -sample[sample < 0].sum()
        pfs[k] = (gains / losses) if losses > 0 else (999.0 if gains > 0 else 0.0)
    lo_q = (1.0 - ci) / 2.0
    hi_q = 1.0 - lo_q
    return {
        "pf_lower": round(float(np.quantile(pfs, lo_q)), 3),
        "pf_median": round(float(np.quantile(pfs, 0.5)), 3),
        "pf_upper": round(float(np.quantile(pfs, hi_q)), 3),
        "n_resamples": int(n_resamples),
        "seed": seed,
        "note": "",
    }


def run():  # pragma: no cover — live network
    import json
    import data_fetcher
    import return_attribution as ra

    price = {}
    fetch_status = {}
    for a in UNIVERSE:
        df, prov = data_fetcher.fetch_ohlcv(a, period_days=2600)
        price[a] = df
        ok = df is not None
        fetch_status[a] = (f"{len(df)} rows ({prov})" if ok else "FETCH FAIL")
        print(f"  {a}: {fetch_status[a]}")

    res = backtest_risk_parity(price)
    rets = res.get("monthly_returns", [])

    # #111 attribution vs SPY monthly returns (real market benchmark)
    if rets and price.get(BENCHMARK) is not None:
        spy_m = monthly_closes(price[BENCHMARK]).pct_change().dropna()
        if len(spy_m) >= len(rets):
            res["attribution_vs_spy"] = ra.attribution_gate(
                rets, spy_m.iloc[-len(rets):].tolist())

    # bootstrap PF 95% CI
    if rets:
        res["bootstrap_pf_ci"] = bootstrap_pf_ci(rets, n_resamples=5000, seed=42)

    # cost-drag sensitivity (re-run the full backtest with the drag baked in)
    cost_drag = {}
    for bps in (0, 10, 20):
        r = backtest_risk_parity(price, cost_bps=float(bps))
        cost_drag[f"{bps}bps"] = {
            "profit_factor": r.get("profit_factor"),
            "sharpe_annual": r.get("sharpe_annual"),
            "cagr": r.get("cagr"),
            "win_rate": r.get("win_rate"),
        }
    res["cost_drag"] = cost_drag
    res["fetch_status"] = fetch_status

    print(json.dumps({k: v for k, v in res.items()
                      if k not in ("monthly_returns", "holdings_tail")},
                     indent=2, default=str))
    return res


if __name__ == "__main__":  # pragma: no cover
    run()
