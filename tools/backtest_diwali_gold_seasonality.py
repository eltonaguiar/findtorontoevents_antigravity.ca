#!/usr/bin/env python3
"""Diwali → GLD 60-day forward return backtest.

Per opencode (Grok-4.x) altdata swarm 2026-05-13:
"India Diwali calendar ±30d window vs GLD 60-day forward excess return, 2005-2025"

Hypothesis: India accounts for ~25% of global gold demand. Diwali (Oct-Nov)
+ wedding-season buying drives physical gold consumption that historically
leads GLD price moves. Test: enter GLD-L 30d before Diwali, exit 60d after.

Free data: yfinance for GLD + SPY (benchmark). Diwali dates hard-coded
2005-2026 (lunar calendar, public).

NFA — hindsight backtest.
"""
from __future__ import annotations
import sys
from datetime import datetime, timedelta, timezone
try:
    import numpy as np
    import pandas as pd
    import yfinance as yf
except ImportError as exc:
    print(f"ERROR: {exc}", file=sys.stderr); sys.exit(2)

# Diwali dates (5-day festival, primary day = Lakshmi Puja)
DIWALI = [
    "2005-11-01","2006-10-21","2007-11-09","2008-10-28","2009-10-17",
    "2010-11-05","2011-10-26","2012-11-13","2013-11-03","2014-10-23",
    "2015-11-11","2016-10-30","2017-10-19","2018-11-07","2019-10-27",
    "2020-11-14","2021-11-04","2022-10-24","2023-11-12","2024-10-31",
    "2025-10-20","2026-11-08",
]


def fetch_daily(ticker, start, end):
    df = yf.download(ticker, start=start, end=end, interval="1d",
                     progress=False, auto_adjust=True)
    if df.empty: return None
    close = df["Close"] if "Close" in df.columns else df.iloc[:, 0]
    if isinstance(close, pd.DataFrame): close = close.iloc[:, 0]
    return close


def main():
    gld = fetch_daily("GLD", "2004-11-18", "2026-12-31")
    spy = fetch_daily("SPY", "2004-11-18", "2026-12-31")
    if gld is None or spy is None:
        print("ERROR: data fetch failed", file=sys.stderr); sys.exit(1)

    print(f"# GLD bars: {len(gld)}  SPY bars: {len(spy)}", file=sys.stderr)
    diwali = pd.to_datetime(DIWALI)

    trades = []
    for d in diwali:
        # Skip if no prior data (e.g., 2005 with too-short lookback)
        entry = d - pd.Timedelta(days=30)
        exit_ = d + pd.Timedelta(days=60)
        # Find nearest trading days
        gld_window = gld[(gld.index >= entry) & (gld.index <= exit_)]
        spy_window = spy[(spy.index >= entry) & (spy.index <= exit_)]
        if len(gld_window) < 30 or len(spy_window) < 30: continue
        gld_ret = (gld_window.iloc[-1] / gld_window.iloc[0]) - 1
        spy_ret = (spy_window.iloc[-1] / spy_window.iloc[0]) - 1
        excess = gld_ret - spy_ret
        trades.append({
            "diwali": d.strftime("%Y-%m-%d"),
            "entry": gld_window.index[0].strftime("%Y-%m-%d"),
            "exit": gld_window.index[-1].strftime("%Y-%m-%d"),
            "gld_ret_pct": float(gld_ret) * 100,
            "spy_ret_pct": float(spy_ret) * 100,
            "excess_pct": float(excess) * 100,
        })

    if not trades:
        print("ERROR: no trades")
        return

    print(f"\n## Diwali GLD seasonality backtest (n={len(trades)})\n")
    print(f"{'diwali':<12} {'gld%':>8} {'spy%':>8} {'excess%':>8}")
    for t in trades:
        print(f"{t['diwali']:<12} {t['gld_ret_pct']:>+8.2f} {t['spy_ret_pct']:>+8.2f} {t['excess_pct']:>+8.2f}")

    gld_returns = [t['gld_ret_pct']/100 for t in trades]
    spy_returns = [t['spy_ret_pct']/100 for t in trades]
    excess_returns = [t['excess_pct']/100 for t in trades]

    print(f"\n## GLD long-only stats")
    w = sum(1 for r in gld_returns if r > 0)
    l = sum(1 for r in gld_returns if r < 0)
    wr = w/(w+l)*100 if (w+l) else 0
    wins = [r for r in gld_returns if r > 0]
    losses = [abs(r) for r in gld_returns if r < 0]
    pf = sum(wins)/sum(losses) if losses else 999
    mean_r = np.mean(gld_returns)
    std_r = np.std(gld_returns, ddof=1) if len(gld_returns)>1 else 0
    sharpe_per_trade = (mean_r/std_r) if std_r>0 else 0
    print(f"  n={len(gld_returns)} WR={wr:.1f}% PF={pf:.2f}")
    print(f"  mean={mean_r*100:+.2f}% std={std_r*100:.2f}% Sharpe/trade={sharpe_per_trade:.2f}")
    print(f"  total compounded: {(np.prod([1+r for r in gld_returns]) - 1)*100:+.2f}%")

    print(f"\n## GLD long vs SPY excess (alpha test)")
    w2 = sum(1 for r in excess_returns if r > 0)
    l2 = sum(1 for r in excess_returns if r < 0)
    wr2 = w2/(w2+l2)*100 if (w2+l2) else 0
    wins2 = [r for r in excess_returns if r > 0]
    losses2 = [abs(r) for r in excess_returns if r < 0]
    pf2 = sum(wins2)/sum(losses2) if losses2 else 999
    mean_e = np.mean(excess_returns)
    std_e = np.std(excess_returns, ddof=1) if len(excess_returns)>1 else 0
    print(f"  n={len(excess_returns)} alpha-WR={wr2:.1f}% PF(alpha)={pf2:.2f}")
    print(f"  mean_alpha={mean_e*100:+.2f}% std={std_e*100:.2f}%")
    if std_e > 0:
        info_ratio = mean_e/std_e
        print(f"  information_ratio={info_ratio:.3f}")


if __name__ == "__main__":
    main()
