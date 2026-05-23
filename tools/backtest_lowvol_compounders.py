#!/usr/bin/env python3
"""Low-Volatility Compounders backtest.

4/4-engine swarm consensus + academic: Haugen-Baker 1996, Baker-Bradley-Wurgler
2011, Ang-Hodrick-Xing-Zhang 2006. Expected highest Sharpe (1.10-1.30) of
all categories.

Spec:
  Each month, rank universe by 252-day realized volatility (rolling).
  Select bottom-quintile (low-vol) tickers with 252-day return > 0.
  Equal-weight hold for 21 trading days (1 month), rebalance.

Universe: 50 large-cap US stable companies (consumer staples, utilities,
healthcare, blue-chip industrials — bias toward low-vol candidates).

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

# Bias toward stable/defensive names to make the low-vol bucket meaningful
UNIVERSE = [
    "JNJ","PFE","UNH","ABBV","LLY","MRK","ABT","BMY","CVS","TMO",
    "WMT","HD","COST","KO","MCD","PG","PEP","CL","KMB","MO",
    "JPM","BAC","WFC","GS","MS","BLK","V","MA","AXP","C",
    "XOM","CVX","COP","SLB","MPC",
    "BRK-B","SO","DUK","NEE","D","AEP","XEL","SRE",
    "AAPL","MSFT","GOOGL","ORCL","CSCO","IBM","INTC",
]


def fetch_daily(tickers, start, end):
    df = yf.download(tickers, start=start, end=end, interval="1d",
                     progress=False, auto_adjust=True)
    closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df
    if isinstance(closes, pd.Series): closes = closes.to_frame()
    return closes


def backtest(closes, vol_lookback=252, ret_lookback=252,
             rebalance_days=21, bottom_quintile_frac=0.2):
    returns = closes.pct_change()
    vol = returns.rolling(vol_lookback).std()
    cum_ret = closes.pct_change(ret_lookback)
    trades_per_period = []
    equity = 1.0; peak = 1.0; max_dd = 0
    wins = losses = 0
    win_pnl = loss_pnl = 0.0
    period_returns = []
    history = []
    n_per_period_avg = []
    for i in range(max(vol_lookback, ret_lookback), len(closes) - rebalance_days, rebalance_days):
        # As-of date i: compute vol + 252d return
        as_of = closes.index[i]
        vol_now = vol.iloc[i].dropna()
        ret_now = cum_ret.iloc[i].dropna()
        # Universe with positive 252d return only
        valid = ret_now[ret_now > 0].index.tolist()
        if not valid: continue
        vol_valid = vol_now.loc[[v for v in valid if v in vol_now.index]].dropna()
        if vol_valid.empty: continue
        n_pick = max(1, int(len(vol_valid) * bottom_quintile_frac))
        picks = vol_valid.sort_values().head(n_pick).index.tolist()
        n_per_period_avg.append(len(picks))
        # Forward return for next rebalance_days
        end_i = min(i + rebalance_days, len(closes) - 1)
        forward = closes.iloc[end_i] / closes.iloc[i] - 1
        period_ret = forward[picks].mean()
        if pd.isna(period_ret): continue
        period_returns.append(period_ret)
        equity *= 1 + period_ret
        peak = max(peak, equity)
        dd = (peak-equity)/peak
        max_dd = max(max_dd, dd)
        if period_ret > 0: wins += 1; win_pnl += period_ret
        elif period_ret < 0: losses += 1; loss_pnl += abs(period_ret)
        history.append({"as_of": as_of.strftime("%Y-%m-%d"),
                        "picks": picks[:5],
                        "n_picks": len(picks),
                        "period_ret_pct": round(float(period_ret)*100, 3)})
    n = len(period_returns)
    if n == 0: return None
    wr = wins/(wins+losses)*100 if (wins+losses) else 0
    pf = win_pnl/loss_pnl if loss_pnl > 0 else 999
    mean = float(np.mean(period_returns))
    std = float(np.std(period_returns, ddof=1)) if len(period_returns)>1 else 0
    sharpe = (mean/std*np.sqrt(252/rebalance_days)) if std>0 else 0
    return {
        "n_periods": n,
        "win_rate_pct": round(wr, 2),
        "profit_factor": round(pf, 4),
        "sharpe_annualized": round(float(sharpe), 4),
        "max_drawdown_pct": round(float(max_dd)*100, 2),
        "total_return_pct": round(float(equity-1)*100, 2),
        "mean_period_ret_pct": round(mean*100, 3),
        "std_period_ret_pct": round(std*100, 3),
        "avg_picks_per_period": round(float(np.mean(n_per_period_avg)), 1) if n_per_period_avg else 0,
        "history_tail": history[-6:],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2010-01-01")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--out", default="audit_dashboard/data/lowvol_compounders_backtest.json")
    args = p.parse_args()

    print(f"# fetching {len(UNIVERSE)} stable-bias tickers", file=sys.stderr)
    closes = fetch_daily(UNIVERSE, args.start, args.end)
    print(f"# closes shape: {closes.shape}", file=sys.stderr)

    result = backtest(closes)
    if not result:
        print("ERROR: no trades"); return

    # SPY benchmark for context
    spy = fetch_daily(["SPY"], args.start, args.end)
    if not spy.empty:
        spy_close = spy.iloc[:, 0]
        spy_total = (spy_close.iloc[-1]/spy_close.iloc[0] - 1) * 100
        spy_daily = spy_close.pct_change().dropna()
        spy_mean = spy_daily.mean()
        spy_std = spy_daily.std()
        spy_sharpe = (spy_mean/spy_std * np.sqrt(252)) if spy_std > 0 else 0
        result["benchmark_spy_total_pct"] = round(float(spy_total), 2)
        result["benchmark_spy_sharpe"] = round(float(spy_sharpe), 4)

    print(f"\n## Low-vol compounders backtest")
    print(f"n={result['n_periods']} periods (rebal=21d)")
    print(f"WR={result['win_rate_pct']}%  PF={result['profit_factor']}  Sharpe={result['sharpe_annualized']}")
    print(f"MDD={result['max_drawdown_pct']}%  Total={result['total_return_pct']}%")
    print(f"avg_picks_per_period={result['avg_picks_per_period']}")
    if 'benchmark_spy_total_pct' in result:
        print(f"\n## Benchmark SPY")
        print(f"Total={result['benchmark_spy_total_pct']}%  Sharpe={result['benchmark_spy_sharpe']}")
        # Alpha
        excess = result['total_return_pct'] - result['benchmark_spy_total_pct']
        print(f"\n## Alpha vs SPY")
        print(f"Excess total return = {excess:+.2f}%")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "Low-Vol Compounders — Haugen-Baker 1996 / Baker-Wurgler 2011",
        "universe": UNIVERSE,
        "config": {"start": args.start, "end": args.end,
                   "vol_lookback_days": 252, "ret_lookback_days": 252,
                   "rebalance_days": 21, "bottom_quintile_frac": 0.2},
        "results": result,
        "expected_per_swarm": {"pf": 2.5, "sharpe": 1.20, "mdd_pct": 14.5},
        "nfa": "Hindsight backtest. No real-money sizing.",
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\n# wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
