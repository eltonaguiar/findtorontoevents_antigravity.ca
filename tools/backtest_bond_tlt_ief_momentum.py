#!/usr/bin/env python3
"""Backtest BOND TLT/IEF momentum (Edge — DAILY_IDEAS B-BOND + pmorissette/bt
consensus pick from 4-engine github research).

Strategy: monthly switch between TLT (long-duration treasuries) and IEF
(7-10y treasuries) based on 12-1m momentum. Conservative duration-rotation
that historically scored Sharpe 1.2-1.5 per academic literature
(Daniel-Moskowitz Time Series Momentum 2012).

Universe: TLT, IEF (+ optional SHY cash-equivalent).

Signal: rank by 12-1m total return; long top-1; rebalance monthly.

Benchmarks vs current /audit BOND class: PF 0.66 / WR 54.5% / n=11
(thin sample, sub-T2).

Data: yfinance free tier.

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

DEFAULT_UNIVERSE = ["TLT", "IEF", "SHY"]


def fetch_monthly_returns(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    df = yf.download(tickers, start=start, end=end, interval="1mo",
                     progress=False, auto_adjust=True)
    closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df
    if isinstance(closes, pd.Series):
        closes = closes.to_frame()
    return closes.pct_change().dropna(how="all")


def momentum_score(returns: pd.DataFrame, lookback: int = 12,
                   skip: int = 1) -> pd.Series:
    if len(returns) < lookback + skip + 1:
        return pd.Series(dtype=float)
    window = returns.iloc[-(lookback + skip):-skip] if skip > 0 else returns.iloc[-lookback:]
    return (1 + window).prod() - 1


def run_backtest(returns: pd.DataFrame, n_long: int = 1,
                 lookback: int = 12, skip: int = 1) -> dict:
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
        sub = returns.iloc[:i]
        scores = momentum_score(sub, lookback=lookback, skip=skip).dropna()
        if scores.empty:
            continue
        ranked = scores.sort_values(ascending=False)
        longs = ranked.head(n_long).index.tolist()
        next_period = returns.iloc[i]
        long_ret = next_period[longs].mean()
        if pd.isna(long_ret):
            continue
        period_ret = float(long_ret)
        equity *= 1 + period_ret
        equity_curve.append({
            "period": str(returns.index[i].date()),
            "longs": longs,
            "period_ret_pct": round(period_ret * 100, 3),
            "equity": round(equity, 5),
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
    sharpe_ann = (mean_ret / std_ret * np.sqrt(12)) if std_ret > 0 else 0
    return {
        "n_periods": n,
        "win_rate_pct": round(wr, 2),
        "profit_factor": round(pf, 4) if pf != float("inf") else None,
        "sharpe_annualized": round(float(sharpe_ann), 4),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "total_return_pct": round((equity - 1) * 100, 2),
        "final_equity": round(equity, 4),
        "trades": equity_curve[-12:],
        "wins": win_count,
        "losses": loss_count,
    }


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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2003-01-01",
                   help="Backtest start (default 2003-01-01 - TLT inception)")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--universe", nargs="*", default=DEFAULT_UNIVERSE)
    p.add_argument("--n-long", type=int, default=1)
    p.add_argument("--lookback", type=int, default=12)
    p.add_argument("--skip", type=int, default=1)
    p.add_argument("--out", default="audit_dashboard/data/bond_tlt_ief_backtest.json")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print(f"# fetching {len(args.universe)} bond ETFs {args.start} -> {args.end}",
          file=sys.stderr)
    returns = fetch_monthly_returns(args.universe, args.start, args.end)
    print(f"# returns shape: {returns.shape}", file=sys.stderr)

    print(f"# backtesting n_long={args.n_long} lookback={args.lookback} "
          f"skip={args.skip}", file=sys.stderr)
    result = run_backtest(returns, n_long=args.n_long,
                          lookback=args.lookback, skip=args.skip)

    # Buy-and-hold TLT comparison
    tlt_only = returns["TLT"].dropna() if "TLT" in returns.columns else pd.Series()
    if not tlt_only.empty:
        tlt_eq = (1 + tlt_only).cumprod()
        tlt_total = (tlt_eq.iloc[-1] - 1) * 100
        tlt_peak = tlt_eq.cummax()
        tlt_mdd = ((tlt_peak - tlt_eq) / tlt_peak).max() * 100
        tlt_mean = tlt_only.mean()
        tlt_std = tlt_only.std()
        tlt_sharpe = (tlt_mean / tlt_std * np.sqrt(12)) if tlt_std > 0 else 0
        bh_tlt = {
            "total_return_pct": round(tlt_total, 2),
            "max_drawdown_pct": round(tlt_mdd, 2),
            "sharpe_annualized": round(float(tlt_sharpe), 4),
        }
    else:
        bh_tlt = None

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "BOND TLT/IEF momentum rotation — pmorissette/bt consensus pick",
        "universe": args.universe,
        "config": {
            "start": args.start,
            "end": args.end,
            "n_long": args.n_long,
            "lookback_months": args.lookback,
            "skip_months": args.skip,
        },
        "results": result,
        "buy_and_hold_tlt": bh_tlt,
        "benchmark_audit_bond_class": {
            "n": 11,
            "wr_pct": 54.5,
            "pf": 0.66,
            "verdict": "sub-floor (PF<1) + thin sample (n<<100)",
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
    print(f"# strategy: PF={result['profit_factor']} WR={result['win_rate_pct']}% "
          f"Sharpe={result['sharpe_annualized']} MDD={result['max_drawdown_pct']}% "
          f"Total={result['total_return_pct']}% (n={result['n_periods']} periods)",
          file=sys.stderr)
    if bh_tlt:
        print(f"# B&H TLT: Sharpe={bh_tlt['sharpe_annualized']} "
              f"MDD={bh_tlt['max_drawdown_pct']}% Total={bh_tlt['total_return_pct']}%",
              file=sys.stderr)


if __name__ == "__main__":
    main()
