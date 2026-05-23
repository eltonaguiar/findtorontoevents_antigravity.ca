#!/usr/bin/env python3
"""
Backtest: equity catalyst + relative volume surge (daily bars).

Motivation: SIDU (Sidus Space) spiked 2026-04-02 after FY2025 earnings (2026-04-01)
with massive RVOL — pattern = speculative small-cap continuation after catalyst + flow.

Data: yfinance only (no placeholder prices).

Usage (from repo root):
  python scripts/backtest_equity_catalyst_momentum.py
  python scripts/backtest_equity_catalyst_momentum.py --symbols SIDU,RKLB,ASTR
"""
from __future__ import annotations

import argparse
import statistics
import sys
from dataclasses import dataclass

try:
    import yfinance as yf
except ImportError:
    print("pip install yfinance", file=sys.stderr)
    sys.exit(1)

# ASTR may be delisted on Yahoo; keep liquid/spec names only
DEFAULT_SYMBOLS = ("SIDU", "RKLB", "LUNR", "PLTR", "SOFI", "GME", "AMC", "RIVN")


@dataclass
class Trade:
    symbol: str
    date: str
    ret_day: float
    rvol: float
    fwd1: float | None
    fwd3: float | None
    fwd5: float | None


def load_df(symbol: str, period: str):
    t = yf.Ticker(symbol)
    df = t.history(period=period, interval="1d", auto_adjust=True)
    if df is None or len(df) < 30:
        return None
    df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
    return df


def backtest_symbol(
    symbol: str,
    period: str,
    min_rvol: float,
    min_abs_ret: float,
    require_bull_bar: bool,
) -> list[Trade]:
    df = load_df(symbol, period)
    if df is None:
        return []
    trades: list[Trade] = []
    closes = df["Close"].values
    opens = df["Open"].values
    vols = df["Volume"].values
    idx = df.index
    n = len(df)
    # Include latest bars; forward returns are None when not enough future days
    for i in range(21, n):
        avg_vol = float(vols[i - 20 : i].mean())
        if avg_vol <= 0:
            continue
        rvol = float(vols[i]) / avg_vol
        ret = float(closes[i] / closes[i - 1] - 1.0)
        if require_bull_bar and closes[i] < opens[i]:
            continue
        if rvol < min_rvol or ret < min_abs_ret:
            continue
        d = idx[i]
        date_s = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
        c0 = float(closes[i])
        fwd1 = float(closes[i + 1] / c0 - 1.0) if i + 1 < n else None
        fwd3 = float(closes[i + 3] / c0 - 1.0) if i + 3 < n else None
        fwd5 = float(closes[i + 5] / c0 - 1.0) if i + 5 < n else None
        trades.append(
            Trade(symbol, date_s, ret, rvol, fwd1, fwd3, fwd5)
        )
    return trades


def summarize(name: str, xs: list[float]) -> str:
    if not xs:
        return f"{name}: n=0"
    return (
        f"{name}: n={len(xs)} mean={statistics.mean(xs)*100:.2f}% "
        f"median={statistics.median(xs)*100:.2f}% win%={100*sum(1 for x in xs if x>0)/len(xs):.1f}"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", type=str, default=",".join(DEFAULT_SYMBOLS))
    ap.add_argument("--period", type=str, default="2y")
    ap.add_argument("--min-rvol", type=float, default=2.2)
    ap.add_argument("--min-ret", type=float, default=0.06)
    ap.add_argument("--no-bull-bar", action="store_true")
    args = ap.parse_args()
    syms = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    all_trades: list[Trade] = []
    for sym in syms:
        all_trades.extend(
            backtest_symbol(
                sym,
                args.period,
                args.min_rvol,
                args.min_ret,
                require_bull_bar=not args.no_bull_bar,
            )
        )

    print("Equity catalyst momentum backtest (yfinance daily)")
    print("Rule: RVOL>=%.2f, day return>=%.1f%%, %s"
          % (args.min_rvol, args.min_ret * 100, "bull bar" if not args.no_bull_bar else "any close"))
    print("Period:", args.period, "Symbols:", ", ".join(syms))
    print("Total signals:", len(all_trades))
    sidu_hits = [t for t in all_trades if t.symbol == "SIDU"]
    for t in sidu_hits[-5:]:
        print(
            "  SIDU", t.date, "day_ret=%.1f%% rvol=%.1f fwd1=%s fwd3=%s"
            % (
                t.ret_day * 100,
                t.rvol,
                "n/a" if t.fwd1 is None else "%.1f%%" % (t.fwd1 * 100),
                "n/a" if t.fwd3 is None else "%.1f%%" % (t.fwd3 * 100),
            )
        )

    f1 = [t.fwd1 for t in all_trades if t.fwd1 is not None]
    f3 = [t.fwd3 for t in all_trades if t.fwd3 is not None]
    f5 = [t.fwd5 for t in all_trades if t.fwd5 is not None]
    print(summarize("fwd+1d", f1))
    print(summarize("fwd+3d", f3))
    print(summarize("fwd+5d", f5))


if __name__ == "__main__":
    main()
