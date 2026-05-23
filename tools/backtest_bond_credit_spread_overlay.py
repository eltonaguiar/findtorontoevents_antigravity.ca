#!/usr/bin/env python3
"""BOND HYG/LQD momentum with credit-spread regime overlay.

Per BOND swarm 2026-05-13 (4/4 engines): add HYG-LQD price-spread filter
to existing 6m momentum on HYG/LQD pair. Expected Sharpe lift: 0.57 -> 1.0+.

Spec:
  Existing baseline: HYG/LQD top-1 6m momentum (PF 1.62, WR 62.7%, Sharpe 0.57).
  Overlay: skip rebalance month when credit spread is widening rapidly
  (HYG-LQD 1m return delta < -3%) — signals credit stress.

Universe: HYG (high-yield), LQD (investment-grade). Free yfinance data.

NFA — hindsight backtest.
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
UNIVERSE = ["HYG", "LQD"]


def fetch_monthly_returns(tickers, start, end):
    df = yf.download(tickers, start=start, end=end, interval="1mo",
                     progress=False, auto_adjust=True)
    closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df
    if isinstance(closes, pd.Series): closes = closes.to_frame()
    return closes.pct_change().dropna(how="all"), closes


def momentum_score(returns, lookback=6, skip=1):
    if len(returns) < lookback + skip + 1: return pd.Series(dtype=float)
    window = returns.iloc[-(lookback+skip):-skip] if skip > 0 else returns.iloc[-lookback:]
    return (1 + window).prod() - 1


def run_with_credit_spread(returns, closes,
                            lookback=6, skip=1,
                            spread_widening_threshold=-3.0,
                            apply_overlay=True):
    """HYG-LQD 6m momentum + optional credit-spread regime overlay."""
    trades = []; eq = 1.0; peak = 1.0; max_dd = 0
    w = lo = 0; w_pnl = lo_pnl = 0.0
    skipped = 0
    active = 0
    history = []
    for i in range(lookback + skip, len(returns)):
        sub = returns.iloc[:i]
        scores = momentum_score(sub, lookback=lookback, skip=skip).dropna()
        if scores.empty: continue

        # Credit-spread overlay: HYG-LQD 1m return delta
        if apply_overlay and i >= 1:
            hyg_1m = returns.iloc[i-1].get("HYG", 0)
            lqd_1m = returns.iloc[i-1].get("LQD", 0)
            if pd.isna(hyg_1m) or pd.isna(lqd_1m):
                hyg_1m = lqd_1m = 0
            spread_delta_pct = (hyg_1m - lqd_1m) * 100  # positive = HYG outperforming = risk-on
            if spread_delta_pct < spread_widening_threshold:
                skipped += 1
                continue
        active += 1

        longs = scores.sort_values(ascending=False).head(1).index.tolist()
        nxt = returns.iloc[i]
        period_ret = nxt[longs].mean()
        if pd.isna(period_ret): continue
        eq *= 1 + period_ret
        if period_ret > 0: w += 1; w_pnl += period_ret
        elif period_ret < 0: lo += 1; lo_pnl += abs(period_ret)
        peak = max(peak, eq)
        max_dd = max(max_dd, (peak-eq)/peak)
        trades.append(period_ret)
        history.append({"period": returns.index[i].strftime("%Y-%m-%d"),
                        "long": longs[0] if longs else "?",
                        "period_ret_pct": round(float(period_ret)*100, 3)})
    n = len(trades)
    if n == 0: return None
    wr = w/(w+lo)*100 if (w+lo) else 0
    pf = w_pnl/lo_pnl if lo_pnl > 0 else 999
    mean = float(np.mean(trades))
    std = float(np.std(trades, ddof=1)) if len(trades) > 1 else 0
    sharpe = (mean/std*np.sqrt(12)) if std > 0 else 0
    return {
        "n_periods": n,
        "win_rate_pct": round(wr, 2),
        "profit_factor": round(pf, 4),
        "sharpe_annualized": round(float(sharpe), 4),
        "max_drawdown_pct": round(float(max_dd)*100, 2),
        "total_return_pct": round(float(eq-1)*100, 2),
        "skipped_months": skipped,
        "active_months": active,
        "history_tail": history[-6:],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2007-01-01",
                   help="HYG inception ~April 2007")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--out", default="audit_dashboard/data/bond_credit_spread_overlay_backtest.json")
    args = p.parse_args()

    print(f"# fetching HYG + LQD monthly {args.start}->{args.end}", file=sys.stderr)
    returns, closes = fetch_monthly_returns(UNIVERSE, args.start, args.end)
    print(f"# returns shape: {returns.shape}", file=sys.stderr)

    print("\n## Baseline (no credit-spread filter)", file=sys.stderr)
    baseline = run_with_credit_spread(returns, closes, apply_overlay=False)
    if baseline:
        print(f"  PF={baseline['profit_factor']:>5.2f}  Sharpe={baseline['sharpe_annualized']:>5.2f}  "
              f"MDD={baseline['max_drawdown_pct']:>5.1f}%  Total={baseline['total_return_pct']:>+7.1f}%  "
              f"n={baseline['n_periods']}", file=sys.stderr)

    print("\n## Credit-spread thresholds", file=sys.stderr)
    variants = []
    for threshold in [-1.0, -2.0, -3.0, -4.0, -5.0]:
        r = run_with_credit_spread(returns, closes, spread_widening_threshold=threshold)
        if r:
            r["spread_threshold_pct"] = threshold
            variants.append(r)
            skipped_pct = r['skipped_months']/(r['skipped_months']+r['active_months'])*100 if (r['skipped_months']+r['active_months'])>0 else 0
            print(f"  HYG-LQD delta > {threshold:>+5.1f}%: "
                  f"PF={r['profit_factor']:>5.2f}  Sharpe={r['sharpe_annualized']:>5.2f}  "
                  f"MDD={r['max_drawdown_pct']:>5.1f}%  Total={r['total_return_pct']:>+7.1f}%  "
                  f"skipped={skipped_pct:>5.1f}%  n={r['n_periods']}", file=sys.stderr)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "HYG/LQD 6m momentum + credit-spread overlay (skip when HYG-LQD 1m delta < threshold)",
        "universe": UNIVERSE,
        "config": {"start": args.start, "end": args.end,
                   "lookback_months": 6, "skip_months": 1, "n_long": 1},
        "baseline_no_overlay": baseline,
        "credit_spread_variants": variants,
        "expected_per_swarm": {"sharpe_lift": "0.57 -> 1.0+", "pf": 1.8, "mdd_pct": 12},
        "nfa": "Hindsight backtest.",
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\n# wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
