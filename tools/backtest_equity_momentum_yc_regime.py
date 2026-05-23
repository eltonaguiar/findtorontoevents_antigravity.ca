#!/usr/bin/env python3
"""EQUITY top-5 momentum + yield-curve (10y-2y proxy) regime overlay.

Per swarm consensus 2026-05-13 (top pick, 8 weighted votes): apply yield-
curve-inversion filter to existing EQUITY top-5 12-1m momentum.

Tests three yield-curve proxies (yfinance free-tier):
  - ^TNX - ^IRX (10y - 13w)  — closest to canonical 10y-2y
  - ^TNX - ^FVX (10y - 5y)   — used in BOND duration rotation backtest
  - ^TNX only level (recession when yields > X%)

Rule: skip rebalance month when yield curve INVERTED (spread < 0) or near-inverted.

Expected per swarm consensus: TIER-1 outcome, Sharpe lift ~0.25-0.40 over baseline.
Baseline EQUITY top-5 momentum: PF 2.82 / Sharpe 1.34 / MDD 24.18%.

NFA - hindsight backtest.
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path
try:
    import numpy as np
    import pandas as pd
    import yfinance as yf
except ImportError as exc:
    print(f"ERROR: {exc}", file=sys.stderr); sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent

UNIVERSE = [
    "AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","AVGO","ORCL",
    "JPM","BAC","WFC","GS","MS","BLK",
    "JNJ","PFE","UNH","ABBV","LLY",
    "WMT","HD","COST","KO","MCD",
    "XOM","CVX","PG","PEP","TMO",
]


def fetch_monthly(tickers, start, end):
    df = yf.download(tickers, start=start, end=end, interval="1mo",
                     progress=False, auto_adjust=True)
    closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df
    if isinstance(closes, pd.Series): closes = closes.to_frame()
    return closes


def momentum_score(returns, lookback=12, skip=1):
    if len(returns) < lookback + skip + 1: return pd.Series(dtype=float)
    window = returns.iloc[-(lookback+skip):-skip] if skip > 0 else returns.iloc[-lookback:]
    return (1 + window).prod() - 1


def run_with_yc(returns, spread_series, n_long=5, lookback=12, skip=1,
                min_spread=None):
    """Top-N momentum; skip when spread < min_spread (None = no filter)."""
    trades = []; eq = 1.0; peak = 1.0; max_dd = 0
    w = lo = 0; w_pnl = lo_pnl = 0.0
    skipped = 0; active = 0
    for i in range(lookback + skip, len(returns)):
        sub = returns.iloc[:i]
        scores = momentum_score(sub, lookback=lookback, skip=skip).dropna()
        if scores.empty: continue
        signal_date = returns.index[i]
        if min_spread is not None:
            spread_prior = spread_series[spread_series.index <= signal_date]
            if spread_prior.empty: skipped += 1; continue
            spread_now = float(spread_prior.iloc[-1])
            if spread_now < min_spread: skipped += 1; continue
        active += 1
        longs = scores.sort_values(ascending=False).head(n_long).index.tolist()
        nxt = returns.iloc[i]
        period_ret = nxt[longs].mean()
        if pd.isna(period_ret): continue
        eq *= 1 + period_ret
        if period_ret > 0: w += 1; w_pnl += period_ret
        elif period_ret < 0: lo += 1; lo_pnl += abs(period_ret)
        peak = max(peak, eq); max_dd = max(max_dd, (peak-eq)/peak)
        trades.append(period_ret)
    n = len(trades)
    if n == 0: return None
    wr = w/(w+lo)*100 if (w+lo) else 0
    pf = w_pnl/lo_pnl if lo_pnl > 0 else 999
    mean = float(np.mean(trades))
    std = float(np.std(trades, ddof=1)) if n > 1 else 0
    sharpe = (mean/std*np.sqrt(12)) if std > 0 else 0
    return {
        "n_periods": n, "win_rate_pct": round(wr,2),
        "profit_factor": round(pf,4),
        "sharpe_annualized": round(float(sharpe),4),
        "max_drawdown_pct": round(float(max_dd)*100,2),
        "total_return_pct": round(float(eq-1)*100,2),
        "skipped_months": skipped, "active_months": active,
        "skip_pct": round(skipped/(skipped+active)*100,2) if (skipped+active)>0 else 0,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2015-01-01")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--out", default="audit_dashboard/data/equity_momentum_yc_regime_backtest.json")
    args = p.parse_args()

    print(f"# fetching equity universe + yield-curve series", file=sys.stderr)
    equity = fetch_monthly(UNIVERSE, args.start, args.end)
    equity_rets = equity.pct_change().dropna(how="all")

    yields = fetch_monthly(["^TNX", "^IRX", "^FVX"], args.start, args.end).ffill()
    if yields.empty or "^TNX" not in yields.columns:
        print("ERROR: yield series missing", file=sys.stderr); sys.exit(1)
    print(f"# yields shape: {yields.shape}", file=sys.stderr)

    spreads = {}
    if "^IRX" in yields.columns:
        spreads["10y_minus_13w"] = (yields["^TNX"] - yields["^IRX"]).dropna()
        print(f"# 10y-13w spread range: {spreads['10y_minus_13w'].min():.2f} to {spreads['10y_minus_13w'].max():.2f}", file=sys.stderr)
    if "^FVX" in yields.columns:
        spreads["10y_minus_5y"] = (yields["^TNX"] - yields["^FVX"]).dropna()
        print(f"# 10y-5y spread range: {spreads['10y_minus_5y'].min():.2f} to {spreads['10y_minus_5y'].max():.2f}", file=sys.stderr)

    baseline = run_with_yc(equity_rets, list(spreads.values())[0], min_spread=None)
    print(f"\n## Baseline (no YC filter)", file=sys.stderr)
    if baseline:
        print(f"  PF={baseline['profit_factor']} Sharpe={baseline['sharpe_annualized']} "
              f"MDD={baseline['max_drawdown_pct']}% Total={baseline['total_return_pct']}% "
              f"n={baseline['n_periods']}", file=sys.stderr)

    results = {"baseline": baseline}

    for spread_name, spread_series in spreads.items():
        print(f"\n## Using {spread_name}", file=sys.stderr)
        for ms in [0.0, 0.25, 0.5, 0.75, 1.0]:
            r = run_with_yc(equity_rets, spread_series, min_spread=ms)
            if not r: continue
            r["spread"] = spread_name
            r["min_spread"] = ms
            key = f"{spread_name}_min{ms}"
            results[key] = r
            print(f"  min_spread>{ms:.2f}: PF={r['profit_factor']:>5.2f} Sharpe={r['sharpe_annualized']:>5.2f} "
                  f"MDD={r['max_drawdown_pct']:>5.1f}% Total={r['total_return_pct']:>+7.1f}% "
                  f"skip={r['skip_pct']:>5.1f}% n={r['n_periods']}", file=sys.stderr)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "EQUITY top-5 12-1m momentum + yield-curve regime overlay (skip when YC inverted)",
        "universe": UNIVERSE,
        "config": {"start": args.start, "end": args.end,
                   "n_long": 5, "lookback_months": 12, "skip_months": 1,
                   "spreads_tested": list(spreads.keys())},
        "results": results,
        "expected_per_swarm": {"sharpe_lift": "0.25-0.40", "tier": "TIER-1"},
        "nfa": "Hindsight backtest.",
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\n# wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
