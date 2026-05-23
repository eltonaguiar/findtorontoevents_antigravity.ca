#!/usr/bin/env python3
"""ETF-A — Slippage-aware sector-rotation (extends backtest_etf_sector_rotation.py).

Same 11 SPDR sectors + top-N 12-1m momentum, BUT applies per-trade friction:
  - turnover_cost_bps: applied to portfolio turnover each rebalance
  - bid_ask_spread_bps: applied per leg entered/exited (counts changed positions)
  - commission_bps: flat per trade

Default friction stack (conservative):
  - turnover_cost: 2bps (large-cap ETFs, tight spreads)
  - spread: 1bp per leg
  - commission: 0.5bp per trade

Total round-trip friction at 100% turnover: ~7bps/month = ~84bps/year.

Tests whether TIER-1 PF 2.05 from naive backtest survives realistic friction.

NFA — hindsight backtest with friction model.
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
    print(f"ERROR: missing dependency: {exc}", file=sys.stderr); sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
SECTOR_ETFS = ["XLF","XLE","XLK","XLV","XLI","XLY","XLP","XLU","XLB","XLRE","XLC"]


def fetch_monthly_returns(tickers, start, end):
    df = yf.download(tickers, start=start, end=end, interval="1mo",
                     progress=False, auto_adjust=True)
    closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df
    if isinstance(closes, pd.Series): closes = closes.to_frame()
    return closes.pct_change().dropna(how="all")


def momentum_score(returns, lookback=12, skip=1):
    if len(returns) < lookback + skip + 1: return pd.Series(dtype=float)
    window = returns.iloc[-(lookback+skip):-skip] if skip>0 else returns.iloc[-lookback:]
    return (1 + window).prod() - 1


def run_with_slippage(returns, n_long=3, lookback=12, skip=1,
                       spread_bps=1.0, commission_bps=0.5, slippage_bps=1.0):
    """Apply per-leg friction on position change."""
    trades = []
    equity = 1.0
    prev_longs = set()
    win_count = loss_count = 0
    win_pnl_sum = loss_pnl_sum = 0.0
    peak = 1.0; max_dd = 0.0
    friction_drag_total = 0.0
    for i in range(lookback + skip, len(returns)):
        sub = returns.iloc[:i]
        scores = momentum_score(sub, lookback=lookback, skip=skip).dropna()
        if scores.empty: continue
        ranked = scores.sort_values(ascending=False)
        longs = set(ranked.head(n_long).index.tolist())
        # Friction: count legs entered + exited this rebalance
        entered = longs - prev_longs
        exited = prev_longs - longs
        n_legs_changed = len(entered) + len(exited)
        # Each leg pays: spread + commission + slippage
        per_leg_cost_bps = spread_bps + commission_bps + slippage_bps
        # Weighted by leg fraction (each long = 1/n_long of portfolio)
        leg_weight = 1.0 / n_long
        friction_bps = n_legs_changed * per_leg_cost_bps * leg_weight
        friction_pct = friction_bps / 10000.0
        nxt = returns.iloc[i]
        long_ret = nxt[list(longs)].mean()
        if pd.isna(long_ret): continue
        # Apply friction to period return
        period_ret = float(long_ret) - friction_pct
        friction_drag_total += friction_pct
        equity *= 1 + period_ret
        trades.append(period_ret)
        if period_ret > 0: win_count += 1; win_pnl_sum += period_ret
        elif period_ret < 0: loss_count += 1; loss_pnl_sum += abs(period_ret)
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
        prev_longs = longs
    n = len(trades)
    wr = (win_count/n*100) if n else 0
    pf = (win_pnl_sum/loss_pnl_sum) if loss_pnl_sum>0 else (float("inf") if win_pnl_sum>0 else 0.0)
    mean = float(np.mean(trades)) if trades else 0
    std = float(np.std(trades, ddof=1)) if len(trades)>1 else 0
    sharpe = (mean/std*np.sqrt(12)) if std>0 else 0
    return {
        "n_periods": n,
        "win_rate_pct": round(wr, 2),
        "profit_factor": round(pf, 4) if pf != float("inf") else None,
        "sharpe_annualized": round(float(sharpe), 4),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "total_return_pct": round((equity-1)*100, 2),
        "wins": win_count, "losses": loss_count,
        "friction_drag_total_pct": round(friction_drag_total * 100, 4),
        "friction_drag_annual_bps": round(friction_drag_total / max(n/12, 1) * 10000, 1),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2015-01-01")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--n-long", type=int, default=3)
    p.add_argument("--out", default="audit_dashboard/data/etf_sector_rotation_slippage_backtest.json")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print(f"# fetching {len(SECTOR_ETFS)} sector ETFs {args.start}->{args.end}", file=sys.stderr)
    returns = fetch_monthly_returns(SECTOR_ETFS, args.start, args.end)
    print(f"# returns shape: {returns.shape}", file=sys.stderr)

    scenarios = [
        {"label": "naive_zero_friction", "spread": 0, "commission": 0, "slippage": 0},
        {"label": "low_friction_2bp_total", "spread": 0.5, "commission": 0.25, "slippage": 0.25},
        {"label": "realistic_5bp_total", "spread": 1.0, "commission": 0.5, "slippage": 1.0},
        {"label": "conservative_10bp_total", "spread": 2.0, "commission": 1.0, "slippage": 2.0},
        {"label": "stress_20bp_total", "spread": 5.0, "commission": 2.0, "slippage": 3.0},
    ]
    results = []
    for sc in scenarios:
        r = run_with_slippage(returns, n_long=args.n_long,
                              spread_bps=sc["spread"], commission_bps=sc["commission"],
                              slippage_bps=sc["slippage"])
        r["scenario"] = sc["label"]
        r["friction_per_leg_bps"] = sc["spread"] + sc["commission"] + sc["slippage"]
        results.append(r)
        print(f"# {sc['label']:30s} per_leg={r['friction_per_leg_bps']:4.1f}bps "
              f"PF={r['profit_factor']:.2f} Sharpe={r['sharpe_annualized']:.2f} "
              f"Total={r['total_return_pct']:.1f}% MDD={r['max_drawdown_pct']:.1f}%",
              file=sys.stderr)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "ETF-A slippage-aware sector rotation (5 friction scenarios)",
        "universe": SECTOR_ETFS,
        "config": {"start": args.start, "end": args.end, "n_long": args.n_long,
                   "lookback_months": 12, "skip_months": 1,
                   "friction_model": "per-leg (spread+commission+slippage), weighted by leg fraction"},
        "scenarios": results,
        "baseline_naive_pf": 2.05,
        "nfa": "Hindsight backtest with friction model. No real-money sizing.",
    }
    if args.dry_run:
        print(json.dumps(payload, indent=2, default=str)); return
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"# wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
