#!/usr/bin/env python3
"""ETF sector-rotation top-3 + VIX regime overlay.

Same pattern as EQUITY VIX overlay (TIER-1 breakthrough this session):
  Baseline ETF top-3 12-1m momentum: PF 2.05, Sharpe 0.97, MDD 16.1%
  Test: skip rebalance month when VIX > threshold.

Hypothesis: regime-gate pattern transfers from EQUITY to ETF class.

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
SECTORS = ["XLF","XLE","XLK","XLV","XLI","XLY","XLP","XLU","XLB","XLRE","XLC"]


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


def run_with_vix(returns, vix, n_long=3, lookback=12, skip=1,
                 vix_threshold=None):
    """Top-N momentum gated on current VIX < threshold (None = no filter)."""
    trades = []; eq = 1.0; peak = 1.0; max_dd = 0
    w = lo = 0; w_pnl = lo_pnl = 0.0
    skipped = 0; active = 0
    for i in range(lookback + skip, len(returns)):
        sub = returns.iloc[:i]
        scores = momentum_score(sub, lookback=lookback, skip=skip).dropna()
        if scores.empty: continue
        signal_date = returns.index[i]
        if vix_threshold is not None:
            vix_prior = vix[vix.index <= signal_date]
            if vix_prior.empty: skipped += 1; continue
            vix_now = float(vix_prior.iloc[-1])
            if vix_now > vix_threshold: skipped += 1; continue
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
    p.add_argument("--out", default="audit_dashboard/data/etf_rotation_vix_regime_backtest.json")
    args = p.parse_args()

    print(f"# fetching {len(SECTORS)} sector ETFs + ^VIX monthly", file=sys.stderr)
    sectors = fetch_monthly(SECTORS, args.start, args.end)
    sector_rets = sectors.pct_change().dropna(how="all")
    vix = fetch_monthly(["^VIX"], args.start, args.end)
    if vix.empty:
        print("ERROR: VIX missing", file=sys.stderr); sys.exit(1)
    vix_close = vix.iloc[:, 0]
    print(f"# sector_rets shape: {sector_rets.shape}, VIX bars: {len(vix_close)}",
          file=sys.stderr)

    baseline = run_with_vix(sector_rets, vix_close, vix_threshold=None)
    print(f"\n## Baseline (no VIX filter)", file=sys.stderr)
    if baseline:
        print(f"  PF={baseline['profit_factor']} Sharpe={baseline['sharpe_annualized']} "
              f"MDD={baseline['max_drawdown_pct']}% Total={baseline['total_return_pct']}% "
              f"n={baseline['n_periods']}", file=sys.stderr)

    variants = []
    for vt in [18.0, 20.0, 22.0, 25.0, 28.0, 30.0]:
        r = run_with_vix(sector_rets, vix_close, vix_threshold=vt)
        if not r: continue
        r["vix_threshold"] = vt
        variants.append(r)
        print(f"  VIX<{vt:>5.1f}: PF={r['profit_factor']:>5.2f} Sharpe={r['sharpe_annualized']:>5.2f} "
              f"MDD={r['max_drawdown_pct']:>5.1f}% Total={r['total_return_pct']:>+7.1f}% "
              f"skip={r['skip_pct']:>5.1f}% n={r['n_periods']}", file=sys.stderr)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "ETF sector top-3 12-1m momentum + VIX regime overlay",
        "universe": SECTORS,
        "config": {"start": args.start, "end": args.end,
                   "n_long": 3, "lookback_months": 12, "skip_months": 1},
        "baseline_no_filter": baseline,
        "vix_variants": variants,
        "nfa": "Hindsight backtest.",
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\n# wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
