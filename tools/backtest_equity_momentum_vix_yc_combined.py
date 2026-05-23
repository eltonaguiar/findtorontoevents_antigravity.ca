#!/usr/bin/env python3
"""EQUITY top-5 momentum + VIX + yield-curve 2-of-2 regime overlay.

Per equity_yc_regime_breakthrough_20260513.md recommendation:
Combine VIX gate (proven TIER-1) + YC gate (3rd TIER-1) into 2-of-2 filter.
Trade only when BOTH regime conditions clean: VIX < threshold AND 10y-5y > 0.

Expected: tighter MDD via 2 independent regime checks. PF should remain TIER-1.

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


def run_combined(returns, vix, yc_spread, n_long=5, lookback=12, skip=1,
                 vix_max=None, yc_min=None, mode="AND"):
    """Top-N momentum with VIX and/or YC filters. mode = AND | OR | VIX_ONLY | YC_ONLY."""
    trades = []; eq = 1.0; peak = 1.0; max_dd = 0
    w = lo = 0; w_pnl = lo_pnl = 0.0
    skipped = 0; active = 0
    skip_reasons = {"vix": 0, "yc": 0, "both": 0, "missing_data": 0}
    for i in range(lookback + skip, len(returns)):
        sub = returns.iloc[:i]
        scores = momentum_score(sub, lookback=lookback, skip=skip).dropna()
        if scores.empty: continue
        signal_date = returns.index[i]

        # Regime checks
        vix_bad = False
        yc_bad = False
        if vix_max is not None and vix is not None:
            vix_prior = vix[vix.index <= signal_date]
            if vix_prior.empty:
                skip_reasons["missing_data"] += 1; skipped += 1; continue
            vix_now = float(vix_prior.iloc[-1])
            if vix_now > vix_max: vix_bad = True
        if yc_min is not None and yc_spread is not None:
            yc_prior = yc_spread[yc_spread.index <= signal_date]
            if yc_prior.empty:
                skip_reasons["missing_data"] += 1; skipped += 1; continue
            yc_now = float(yc_prior.iloc[-1])
            if yc_now < yc_min: yc_bad = True

        # Skip decision
        if mode == "AND":
            # Skip if EITHER bad (both gates must pass)
            if vix_bad and yc_bad:
                skip_reasons["both"] += 1; skipped += 1; continue
            elif vix_bad:
                skip_reasons["vix"] += 1; skipped += 1; continue
            elif yc_bad:
                skip_reasons["yc"] += 1; skipped += 1; continue
        elif mode == "OR":
            # Skip only if BOTH bad (any one gate passes)
            if vix_bad and yc_bad:
                skip_reasons["both"] += 1; skipped += 1; continue

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
        "skipped_total": skipped, "active": active,
        "skip_pct": round(skipped/(skipped+active)*100,2) if (skipped+active)>0 else 0,
        "skip_reasons": skip_reasons,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2015-01-01")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--out", default="audit_dashboard/data/equity_momentum_vix_yc_combined_backtest.json")
    args = p.parse_args()

    print(f"# fetching universe + VIX + YC", file=sys.stderr)
    eq = fetch_monthly(UNIVERSE, args.start, args.end)
    rets = eq.pct_change().dropna(how="all")
    vix = fetch_monthly(["^VIX"], args.start, args.end).iloc[:, 0]
    yields = fetch_monthly(["^TNX", "^FVX"], args.start, args.end).ffill()
    yc_spread = (yields["^TNX"] - yields["^FVX"]).dropna() if "^TNX" in yields.columns and "^FVX" in yields.columns else None

    results = {}

    # Baseline
    print(f"\n## Baseline (no filter)", file=sys.stderr)
    base = run_combined(rets, vix, yc_spread, vix_max=None, yc_min=None)
    if base:
        results["baseline"] = base
        print(f"  PF={base['profit_factor']:>5.2f} Sharpe={base['sharpe_annualized']:>5.2f} MDD={base['max_drawdown_pct']:>5.1f}% Total={base['total_return_pct']:>+7.1f}% n={base['n_periods']}", file=sys.stderr)

    # VIX-only references
    print(f"\n## VIX-only (reference)", file=sys.stderr)
    for vt in [20.0, 22.0]:
        r = run_combined(rets, vix, yc_spread, vix_max=vt, yc_min=None)
        if r:
            results[f"vix_only_{vt}"] = r
            print(f"  VIX<{vt}: PF={r['profit_factor']:>5.2f} Sharpe={r['sharpe_annualized']:>5.2f} MDD={r['max_drawdown_pct']:>5.1f}% Total={r['total_return_pct']:>+7.1f}% n={r['n_periods']}", file=sys.stderr)

    # YC-only references
    print(f"\n## YC-only (reference)", file=sys.stderr)
    for yc in [0.0, 0.25]:
        r = run_combined(rets, vix, yc_spread, vix_max=None, yc_min=yc)
        if r:
            results[f"yc_only_{yc}"] = r
            print(f"  YC>{yc}: PF={r['profit_factor']:>5.2f} Sharpe={r['sharpe_annualized']:>5.2f} MDD={r['max_drawdown_pct']:>5.1f}% Total={r['total_return_pct']:>+7.1f}% n={r['n_periods']}", file=sys.stderr)

    # Combined AND (most conservative)
    print(f"\n## Combined AND (skip if EITHER bad)", file=sys.stderr)
    for vt in [20.0, 22.0, 25.0]:
        for yc in [0.0, 0.25]:
            r = run_combined(rets, vix, yc_spread, vix_max=vt, yc_min=yc, mode="AND")
            if r:
                results[f"AND_vix{vt}_yc{yc}"] = r
                print(f"  VIX<{vt} AND YC>{yc}: PF={r['profit_factor']:>5.2f} Sharpe={r['sharpe_annualized']:>5.2f} "
                      f"MDD={r['max_drawdown_pct']:>5.1f}% Total={r['total_return_pct']:>+7.1f}% "
                      f"n={r['n_periods']} skip={r['skip_pct']:.1f}%", file=sys.stderr)

    # Combined OR (most permissive — skip only if BOTH bad)
    print(f"\n## Combined OR (skip only if BOTH bad)", file=sys.stderr)
    for vt in [22.0, 25.0]:
        for yc in [0.0]:
            r = run_combined(rets, vix, yc_spread, vix_max=vt, yc_min=yc, mode="OR")
            if r:
                results[f"OR_vix{vt}_yc{yc}"] = r
                print(f"  VIX<{vt} OR YC>{yc}: PF={r['profit_factor']:>5.2f} Sharpe={r['sharpe_annualized']:>5.2f} "
                      f"MDD={r['max_drawdown_pct']:>5.1f}% Total={r['total_return_pct']:>+7.1f}% "
                      f"n={r['n_periods']}", file=sys.stderr)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "EQUITY top-5 12-1m momentum + VIX + YC (10y-5y) combined regime overlay",
        "universe": UNIVERSE,
        "config": {"start": args.start, "end": args.end},
        "results": results,
        "nfa": "Hindsight backtest.",
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\n# wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
