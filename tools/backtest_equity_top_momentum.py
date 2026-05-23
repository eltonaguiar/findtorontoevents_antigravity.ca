#!/usr/bin/env python3
"""Backtest EQUITY top-N momentum (DAILY_IDEAS B-EQUITY).

Cross-sectional 12-1m momentum on a 30-stock liquid US universe.
Monthly rebalance, long top-N equal-weight.

Universe: 30 large-cap US (mostly S&P 100 components) — broad enough
to test cross-sectional momentum without S&P 500 data download.

Benchmark vs current /audit EQUITY class: PF 1.55 / WR 53.2% / n=447
(T2 confirmed).

Data: yfinance free tier.
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

UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ORCL",
    "JPM", "BAC", "WFC", "GS", "MS", "BLK",
    "JNJ", "PFE", "UNH", "ABBV", "LLY",
    "WMT", "HD", "COST", "KO", "MCD",
    "XOM", "CVX",
    "PG", "PEP", "TMO",
]


def fetch_monthly_returns(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    df = yf.download(tickers, start=start, end=end, interval="1mo",
                     progress=False, auto_adjust=True)
    closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df
    if isinstance(closes, pd.Series):
        closes = closes.to_frame()
    return closes.pct_change().dropna(how="all")


def momentum_score(returns: pd.DataFrame, lookback: int, skip: int) -> pd.Series:
    if len(returns) < lookback + skip + 1:
        return pd.Series(dtype=float)
    window = returns.iloc[-(lookback + skip):-skip] if skip > 0 else returns.iloc[-lookback:]
    return (1 + window).prod() - 1


def run_backtest(returns: pd.DataFrame, n_long: int, n_short: int,
                 lookback: int, skip: int) -> dict:
    trades = []
    equity = 1.0
    win = loss = 0
    win_pnl = loss_pnl = 0.0
    peak = 1.0
    max_dd = 0.0
    history = []
    for i in range(lookback + skip, len(returns)):
        sub = returns.iloc[:i]
        scores = momentum_score(sub, lookback, skip).dropna()
        if scores.empty:
            continue
        ranked = scores.sort_values(ascending=False)
        longs = ranked.head(n_long).index.tolist()
        shorts = ranked.tail(n_short).index.tolist() if n_short > 0 else []
        nxt = returns.iloc[i]
        long_ret = nxt[longs].mean() if longs else 0.0
        short_ret = -nxt[shorts].mean() if shorts else 0.0
        period_ret = (long_ret + short_ret) / 2 if n_short > 0 else long_ret
        if pd.isna(period_ret):
            continue
        equity *= 1 + period_ret
        history.append({
            "period": str(returns.index[i].date()),
            "longs": longs,
            "period_ret_pct": round(float(period_ret) * 100, 3),
        })
        trades.append(period_ret)
        if period_ret > 0:
            win += 1; win_pnl += period_ret
        elif period_ret < 0:
            loss += 1; loss_pnl += abs(period_ret)
        peak = max(peak, equity)
        dd = (peak - equity) / peak
        max_dd = max(max_dd, dd)
    n = len(trades)
    wr = (win / n * 100) if n else 0
    pf = (win_pnl / loss_pnl) if loss_pnl > 0 else (float("inf") if win_pnl > 0 else 0.0)
    mean_r = float(np.mean(trades)) if trades else 0
    std_r = float(np.std(trades, ddof=1)) if len(trades) > 1 else 0
    sharpe = (mean_r / std_r * np.sqrt(12)) if std_r > 0 else 0
    return {
        "n_periods": n, "win_rate_pct": round(wr, 2),
        "profit_factor": round(pf, 4) if pf != float("inf") else None,
        "sharpe_annualized": round(float(sharpe), 4),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "total_return_pct": round((equity - 1) * 100, 2),
        "wins": win, "losses": loss,
        "history_tail": history[-12:],
    }


def _classify(r):
    pf = r.get("profit_factor") or 0
    wr = r.get("win_rate_pct") or 0
    n = r.get("n_periods") or 0
    mdd = r.get("max_drawdown_pct") or 999
    if pf >= 2 and wr >= 55 and mdd <= 10 and n >= 200: return "TIER_1"
    if pf >= 1.5 and wr >= 50 and mdd <= 20 and n >= 100: return "TIER_2"
    if pf >= 1.2 and wr >= 45 and mdd <= 25 and n >= 100: return "TIER_3"
    return "BELOW_T3"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2015-01-01")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--n-long", type=int, default=5)
    p.add_argument("--n-short", type=int, default=0)
    p.add_argument("--lookback", type=int, default=12)
    p.add_argument("--skip", type=int, default=1)
    p.add_argument("--out", default="audit_dashboard/data/equity_top_momentum_backtest.json")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print(f"# fetching {len(UNIVERSE)} large-cap equities", file=sys.stderr)
    returns = fetch_monthly_returns(UNIVERSE, args.start, args.end)
    print(f"# returns shape: {returns.shape}", file=sys.stderr)

    result = run_backtest(returns, args.n_long, args.n_short, args.lookback, args.skip)

    # Benchmark vs SPY
    spy = fetch_monthly_returns(["SPY"], args.start, args.end)
    spy_col = spy.columns[0] if not spy.empty else None
    if spy_col:
        spy_r = spy[spy_col].dropna()
        spy_eq = (1 + spy_r).cumprod()
        spy_total = (spy_eq.iloc[-1] - 1) * 100
        spy_peak = spy_eq.cummax()
        spy_mdd = ((spy_peak - spy_eq) / spy_peak).max() * 100
        spy_sharpe = (spy_r.mean() / spy_r.std() * np.sqrt(12)) if spy_r.std() > 0 else 0
        bh_spy = {
            "total_return_pct": round(spy_total, 2),
            "max_drawdown_pct": round(spy_mdd, 2),
            "sharpe_annualized": round(float(spy_sharpe), 4),
        }
    else:
        bh_spy = None

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "EQUITY top-N 12-1m momentum — DAILY_IDEAS B-EQUITY",
        "universe": UNIVERSE,
        "config": {
            "start": args.start, "end": args.end,
            "n_long": args.n_long, "n_short": args.n_short,
            "lookback_months": args.lookback, "skip_months": args.skip,
        },
        "results": result,
        "buy_and_hold_spy": bh_spy,
        "benchmark_audit_equity": {
            "n": 447, "wr_pct": 53.2, "pf": 1.55, "verdict": "T2 confirmed",
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
    print(f"# wrote {out_path}", file=sys.stderr)
    print(f"# strategy: PF={result['profit_factor']} WR={result['win_rate_pct']}% "
          f"Sharpe={result['sharpe_annualized']} MDD={result['max_drawdown_pct']}% "
          f"Total={result['total_return_pct']}% (n={result['n_periods']})",
          file=sys.stderr)
    if bh_spy:
        print(f"# B&H SPY: Sharpe={bh_spy['sharpe_annualized']} "
              f"MDD={bh_spy['max_drawdown_pct']}% Total={bh_spy['total_return_pct']}%",
              file=sys.stderr)


if __name__ == "__main__":
    main()
