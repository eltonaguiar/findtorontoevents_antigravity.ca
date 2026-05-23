#!/usr/bin/env python3
"""SPY 50d/200d moving-average crossover + VIX regime overlay.

Per cerebras (next-harvest swarm 2026-05-13, rank 2): "Moving-average
crossovers have underperformed recently; VIX filter can prune false signals."

Spec:
  Base signal: SPY golden cross (50d MA > 200d MA = LONG) / death cross (LONG -> CASH)
  Overlay: skip new LONG entry when VIX > threshold (don't chase golden cross
  during high-vol regimes).

Hypothesis: regime-gate pattern (4/5 hit rate this session) extends to
event-based MA crossover. Or fails like Donchian+VIX (event already implies
regime).

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


def fetch_daily(tickers, start, end):
    df = yf.download(tickers, start=start, end=end, interval="1d",
                     progress=False, auto_adjust=True)
    closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df
    if isinstance(closes, pd.Series): closes = closes.to_frame()
    return closes


def run_crossover(closes_spy, closes_vix=None, vix_threshold=None):
    """Golden cross long / death cross flat. Optional VIX gate on entries."""
    ma50 = closes_spy.rolling(50).mean()
    ma200 = closes_spy.rolling(200).mean()
    above = ma50 > ma200
    # Entry/exit signals
    entry_signal = above & ~above.shift(1).fillna(False)
    exit_signal = ~above & above.shift(1).fillna(False)

    trades = []
    in_position = False
    entry_idx = None
    entry_price = None
    skipped_by_vix = 0
    for i in range(200, len(closes_spy)):
        date = closes_spy.index[i]
        if not in_position and entry_signal.iloc[i]:
            # Optional VIX gate
            if vix_threshold is not None and closes_vix is not None:
                vix_prior = closes_vix[closes_vix.index <= date]
                if not vix_prior.empty:
                    vix_now = float(vix_prior.iloc[-1])
                    if vix_now > vix_threshold:
                        skipped_by_vix += 1
                        continue
            in_position = True
            entry_idx = i
            entry_price = closes_spy.iloc[i]
        elif in_position and exit_signal.iloc[i]:
            exit_price = closes_spy.iloc[i]
            ret = (exit_price / entry_price - 1) * 100
            trades.append({
                "entry_date": closes_spy.index[entry_idx].strftime("%Y-%m-%d"),
                "exit_date": date.strftime("%Y-%m-%d"),
                "ret_pct": float(ret),
                "days_held": i - entry_idx,
            })
            in_position = False
            entry_idx = None
    if in_position:
        ret = (closes_spy.iloc[-1] / entry_price - 1) * 100
        trades.append({
            "entry_date": closes_spy.index[entry_idx].strftime("%Y-%m-%d"),
            "exit_date": closes_spy.index[-1].strftime("%Y-%m-%d"),
            "ret_pct": float(ret),
            "days_held": len(closes_spy)-1-entry_idx,
        })
    return trades, skipped_by_vix


def aggregate(trades):
    if not trades: return None
    pnls = [t["ret_pct"]/100 for t in trades]
    n = len(pnls)
    w = sum(1 for p in pnls if p > 0); l = sum(1 for p in pnls if p < 0)
    wr = w/(w+l)*100 if (w+l) else 0
    wins = [p for p in pnls if p > 0]
    losses = [abs(p) for p in pnls if p < 0]
    pf = sum(wins)/sum(losses) if losses else 999
    mean = float(np.mean(pnls))
    std = float(np.std(pnls, ddof=1)) if n > 1 else 0
    avg_days = float(np.mean([t["days_held"] for t in trades]))
    trades_per_year = 252/max(avg_days, 1)
    sharpe = (mean/std * np.sqrt(trades_per_year)) if std > 0 else 0
    # Cumulative equity
    eq = 1.0; peak = 1.0; max_dd = 0
    for p in pnls:
        eq *= 1 + p; peak = max(peak, eq); max_dd = max(max_dd, (peak-eq)/peak)
    return {
        "n_trades": n, "win_rate_pct": round(wr,2),
        "profit_factor": round(pf,4),
        "sharpe_annualized": round(float(sharpe),4),
        "mean_ret_pct": round(mean*100,3),
        "max_dd_pct": round(float(max_dd)*100,2),
        "total_return_pct": round(float(eq-1)*100,2),
        "avg_days_held": round(avg_days,1),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2005-01-01")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--out", default="audit_dashboard/data/ma_crossover_vix_regime_backtest.json")
    args = p.parse_args()

    print(f"# fetching SPY + ^VIX daily 2005-now", file=sys.stderr)
    df = fetch_daily(["SPY", "^VIX"], args.start, args.end)
    spy = df["SPY"] if "SPY" in df.columns else None
    vix = df["^VIX"] if "^VIX" in df.columns else None
    if spy is None or vix is None:
        print("ERROR: data fetch", file=sys.stderr); sys.exit(1)

    results = {}

    # Baseline (no VIX gate)
    trades_base, _ = run_crossover(spy, vix, vix_threshold=None)
    base = aggregate(trades_base)
    results["baseline"] = base
    print(f"\n## Baseline SPY 50/200 crossover (no VIX gate)", file=sys.stderr)
    if base:
        print(f"  n={base['n_trades']} WR={base['win_rate_pct']}% PF={base['profit_factor']} "
              f"Sharpe={base['sharpe_annualized']} MDD={base['max_dd_pct']}% "
              f"Total={base['total_return_pct']}% avg_days={base['avg_days_held']}", file=sys.stderr)

    # VIX variants
    print(f"\n## With VIX threshold filter on entries", file=sys.stderr)
    for vt in [18.0, 20.0, 22.0, 25.0, 30.0]:
        trades_vt, skipped = run_crossover(spy, vix, vix_threshold=vt)
        agg = aggregate(trades_vt)
        if not agg: continue
        agg["vix_threshold"] = vt
        agg["entries_skipped"] = skipped
        results[f"vix_{vt}"] = agg
        print(f"  VIX<{vt}: n={agg['n_trades']:>3} WR={agg['win_rate_pct']:>5.1f}% "
              f"PF={agg['profit_factor']:>5.2f} Sharpe={agg['sharpe_annualized']:>5.2f} "
              f"MDD={agg['max_dd_pct']:>5.1f}% Total={agg['total_return_pct']:>+8.1f}% "
              f"skipped={skipped}", file=sys.stderr)

    # Buy-and-hold SPY benchmark
    spy_clean = spy.dropna()
    bh_total = (spy_clean.iloc[-1]/spy_clean.iloc[0] - 1) * 100
    spy_rets = spy_clean.pct_change().dropna()
    bh_sharpe = (spy_rets.mean()/spy_rets.std() * np.sqrt(252)) if spy_rets.std() > 0 else 0
    peak_spy = spy_clean.cummax()
    bh_mdd = ((peak_spy - spy_clean)/peak_spy).max() * 100
    print(f"\n## Buy-and-hold SPY (benchmark)", file=sys.stderr)
    print(f"  Total={bh_total:+.1f}% Sharpe={bh_sharpe:.2f} MDD={bh_mdd:.1f}%", file=sys.stderr)
    results["bh_spy"] = {
        "total_return_pct": round(float(bh_total), 2),
        "sharpe_annualized": round(float(bh_sharpe), 4),
        "max_dd_pct": round(float(bh_mdd), 2),
    }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "SPY 50/200 MA crossover + VIX regime overlay",
        "config": {"start": args.start, "end": args.end,
                   "ma_short": 50, "ma_long": 200},
        "results": results,
        "nfa": "Hindsight backtest.",
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\n# wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
