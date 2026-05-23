#!/usr/bin/env python3
"""Backtest ETF sector-rotation (Edge — DAILY_IDEAS B-ETF + PyPortfolioOpt).

Per github research consensus (3/4 engines): PyPortfolioOpt is the
ETF-class go-live candidate. Test the simplest variant first — monthly
sector-momentum rotation across SPDRs — before introducing Black-Litterman
machinery.

Universe: 11 SPDR sector ETFs (XLF financial, XLE energy, XLK tech,
XLV health, XLI industrial, XLY consumer-disc, XLP staples, XLU
utilities, XLB materials, XLRE real-estate, XLC comms)

Signal: rank by 12-1m total return; long top-3 / short bottom-3
(or top-3 long-only); rebalance monthly.

Benchmarks vs current /audit ETF class: PF 1.34 / WR 56.1% / n=107.

Data: yfinance only (no PyPortfolioOpt for v1 — start with naive
ranking, add Black-Litterman in v2).

NFA — academic backtest only.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
    import yfinance as yf
except ImportError as exc:
    print(f"ERROR: missing dependency: {exc}", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent

SECTOR_ETFS = ["XLF", "XLE", "XLK", "XLV", "XLI", "XLY", "XLP",
               "XLU", "XLB", "XLRE", "XLC"]


def fetch_monthly_returns(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    df = yf.download(tickers, start=start, end=end, interval="1mo",
                     progress=False, auto_adjust=True)
    closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df
    if isinstance(closes, pd.Series):
        closes = closes.to_frame()
    returns = closes.pct_change().dropna(how="all")
    return returns


def momentum_score(returns: pd.DataFrame, lookback: int = 12,
                   skip: int = 1) -> pd.Series:
    """12-1m total return per ticker (skip most recent month)."""
    if len(returns) < lookback + skip + 1:
        return pd.Series(dtype=float)
    window = returns.iloc[-(lookback + skip):-skip] if skip > 0 else returns.iloc[-lookback:]
    return (1 + window).prod() - 1


def run_backtest(returns: pd.DataFrame, n_long: int = 3, n_short: int = 0,
                 lookback: int = 12, skip: int = 1) -> dict:
    """Walk-forward monthly rebalance. Returns per-period + summary."""
    trades = []
    equity = 1.0
    equity_curve = []
    win_count = 0
    loss_count = 0
    win_pnl_sum = 0.0
    loss_pnl_sum = 0.0
    peak = 1.0
    max_dd = 0.0
    for i in range(lookback + skip, len(returns)):
        # Build score from returns up to i (exclusive)
        sub = returns.iloc[:i]
        scores = momentum_score(sub, lookback=lookback, skip=skip).dropna()
        if scores.empty:
            continue
        ranked = scores.sort_values(ascending=False)
        longs = ranked.head(n_long).index.tolist()
        shorts = ranked.tail(n_short).index.tolist() if n_short > 0 else []
        # Next-period return for each leg
        next_period = returns.iloc[i]
        long_ret = next_period[longs].mean() if longs else 0.0
        short_ret = -next_period[shorts].mean() if shorts else 0.0
        # Equal-weight long+short
        if n_short > 0:
            period_ret = (long_ret + short_ret) / 2
        else:
            period_ret = long_ret
        if pd.isna(period_ret):
            continue
        equity *= 1 + period_ret
        equity_curve.append({
            "period": str(returns.index[i].date()),
            "longs": longs,
            "shorts": shorts,
            "long_ret_pct": round(float(long_ret * 100), 3),
            "short_ret_pct": round(float(short_ret * 100), 3),
            "period_ret_pct": round(float(period_ret * 100), 3),
            "equity": round(float(equity), 5),
        })
        trades.append(period_ret)
        if period_ret > 0:
            win_count += 1
            win_pnl_sum += period_ret
        elif period_ret < 0:
            loss_count += 1
            loss_pnl_sum += abs(period_ret)
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    n = len(trades)
    wr = (win_count / n * 100) if n else 0
    pf = (win_pnl_sum / loss_pnl_sum) if loss_pnl_sum > 0 else (
        float("inf") if win_pnl_sum > 0 else 0.0
    )
    mean_ret = float(np.mean(trades)) if trades else 0
    std_ret = float(np.std(trades, ddof=1)) if len(trades) > 1 else 0
    sharpe_annual = (mean_ret / std_ret * np.sqrt(12)) if std_ret > 0 else 0
    total_return = (equity - 1) * 100
    return {
        "n_periods": n,
        "win_rate_pct": round(wr, 2),
        "profit_factor": round(pf, 4) if pf != float("inf") else None,
        "sharpe_annualized": round(float(sharpe_annual), 4),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "total_return_pct": round(total_return, 2),
        "final_equity": round(equity, 4),
        "trades": equity_curve[-12:],  # last 12 periods only for payload
        "wins": win_count,
        "losses": loss_count,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2015-01-01",
                   help="Backtest start (default 2015-01-01)")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--n-long", type=int, default=3)
    p.add_argument("--n-short", type=int, default=0,
                   help="0=long-only; 3=top3-long / bottom3-short")
    p.add_argument("--lookback", type=int, default=12)
    p.add_argument("--skip", type=int, default=1)
    p.add_argument("--out", default="audit_dashboard/data/etf_sector_rotation_backtest.json")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print(f"# fetching monthly closes for {len(SECTOR_ETFS)} ETFs "
          f"{args.start} -> {args.end}", file=sys.stderr)
    returns = fetch_monthly_returns(SECTOR_ETFS, args.start, args.end)
    print(f"# returns shape: {returns.shape}", file=sys.stderr)

    if len(returns) < args.lookback + args.skip + 12:
        print(f"WARN: only {len(returns)} months; need >= {args.lookback + args.skip + 12}",
              file=sys.stderr)

    print(f"# backtesting n_long={args.n_long} n_short={args.n_short} "
          f"lookback={args.lookback} skip={args.skip}", file=sys.stderr)
    result = run_backtest(
        returns,
        n_long=args.n_long,
        n_short=args.n_short,
        lookback=args.lookback,
        skip=args.skip,
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "ETF sector-rotation backtest — DAILY_IDEAS B-ETF + 4-engine github research consensus",
        "universe": SECTOR_ETFS,
        "config": {
            "start": args.start,
            "end": args.end,
            "n_long": args.n_long,
            "n_short": args.n_short,
            "lookback_months": args.lookback,
            "skip_months": args.skip,
        },
        "results": result,
        "benchmark_audit_etf_class": {
            "n": 107,
            "wr_pct": 56.1,
            "pf": 1.34,
            "verdict": "sub-T2 (PF<1.5)",
        },
        "tier_comparison": _classify(result),
        "nfa": "Hindsight backtest. No real-money sizing.",
    }

    if args.dry_run:
        print(json.dumps(payload, indent=2, default=str))
        return

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"# wrote {out_path} ({out_path.stat().st_size:,} bytes)",
          file=sys.stderr)
    print(f"# Results: PF={result['profit_factor']} WR={result['win_rate_pct']}% "
          f"Sharpe={result['sharpe_annualized']} MDD={result['max_drawdown_pct']}% "
          f"Total={result['total_return_pct']}% (n={result['n_periods']} periods)",
          file=sys.stderr)


def _classify(r: dict) -> str:
    pf = r.get("profit_factor") or 0
    wr = r.get("win_rate_pct") or 0
    n = r.get("n_periods") or 0
    mdd = r.get("max_drawdown_pct") or 999
    if pf >= 2 and wr >= 55 and mdd <= 10 and n >= 200:
        return "TIER_1"
    if pf >= 1.5 and wr >= 50 and mdd <= 20 and n >= 100:
        return "TIER_2"
    if pf >= 1.2 and wr >= 45 and mdd <= 25 and n >= 100:
        return "TIER_3"
    return "BELOW_T3"


if __name__ == "__main__":
    main()
