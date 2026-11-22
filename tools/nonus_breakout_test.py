"""Is the daily-breakout edge a ZIRP artefact or a family effect?

Mercury3's own numbers: US daily breakout continuation is his one Gate-C-positive
family (+12 to +15 bp/trade across a look=10..40 plateau), but it is POST-2010 ONLY
(SPY first half +5.49 bp, t=0.47; second half +40.70 bp, t=3.91). He cannot tell
whether that is the ZIRP era or sample luck, and he asked for exactly one test:

    "run the same daily-breakout rule with a 10m-SMA regime filter on a NON-US market
     with a pre-2010 history -- FTSE, DAX, N225, or TSX. If the edge is absent pre-2010
     everywhere, it is a ZIRP artefact and should be sized accordingly. If it appears
     pre-2010 in another market, it is a family effect and my US window is just unlucky."

That is the question this answers. ^GSPC is included as the control so the non-US rows
can be compared against the US result on the SAME code path, costs and split dates.

Rule (frozen before the run, no per-market tuning):
  regime  : month-end close > 10-month SMA of month-end closes, value applied to the
            FOLLOWING month (no lookahead -- the last completed month decides).
  entry   : close > highest close of the prior N days, and regime on.
  exit    : close < lowest close of the prior N days, or regime off.
  fill    : NEXT session's open. Never the signal bar's close (that is the lag-0 defect
            both desks caught in other harnesses).
  cost    : two sides x COST_BPS per side, charged on every round trip.

Usage:
  python3 tools/nonus_breakout_test.py --out reports/nonus_breakout_2026-11-22.json
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd
import yfinance as yf

MARKETS = {
    "^GSPC": "US S&P 500 (control)",
    "^FTSE": "UK FTSE 100",
    "^GDAXI": "Germany DAX",
    "^N225": "Japan Nikkei 225",
    "^GSPTSE": "Canada TSX Composite",
}
LOOKS = (10, 20, 30, 40)
COST_BPS = 10.0
SPLITS = ("pre_2010", "post_2010")


def load(sym: str) -> pd.DataFrame:
    df = yf.download(sym, start="1980-01-01", progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df[["Open", "High", "Low", "Close"]].dropna()
    return df


def regime_series(closes: pd.Series, sma_months: int = 10) -> pd.Series:
    """month-end regime shifted one month forward, then reindexed onto daily bars."""
    # groupby period end, not resample("ME"): the "ME" alias only exists in
    # pandas >= 2.2 and raises "Invalid frequency: ME" on the older pandas CI
    # installs. to_timestamp(how="end") gives the same month-end stamps.
    me = closes.groupby(closes.index.to_period("M")).last()
    me.index = me.index.to_timestamp(how="end")
    on = (me > me.rolling(sma_months).mean()).astype(float)
    # shift(1) => the month that has just CLOSED decides the next month's permission
    return on.shift(1).reindex(closes.index, method="ffill").fillna(0.0)


def run(df: pd.DataFrame, look: int, use_regime: bool, cost_bps: float) -> list[dict]:
    close, openp = df["Close"], df["Open"]
    hi = close.rolling(look).max().shift(1)
    lo = close.rolling(look).min().shift(1)
    reg = regime_series(close) if use_regime else pd.Series(1.0, index=close.index)

    trades: list[dict] = []
    pos = 0.0
    entry_px = entry_dt = None
    idx = df.index
    for i in range(1, len(df)):
        c = float(close.iloc[i])
        # exits are decided on today's close, filled at tomorrow's open
        if pos and (c < float(lo.iloc[i]) or float(reg.iloc[i]) == 0.0):
            if i + 1 < len(df):
                px = float(openp.iloc[i + 1])
                ret = (px / entry_px - 1.0) * 1e4 - 2 * cost_bps
                trades.append({"entry": entry_dt, "exit": idx[i + 1],
                               "days": (idx[i + 1] - entry_dt).days, "bps": ret})
                pos = 0.0
                entry_px = None
        if not pos and float(reg.iloc[i]) > 0 and c > float(hi.iloc[i]) and i + 1 < len(df):
            pos = 1.0
            entry_px = float(openp.iloc[i + 1])
            entry_dt = idx[i + 1]
    return trades


def stats(trades: list[dict]) -> dict:
    xs = [t["bps"] for t in trades]
    n = len(xs)
    if n == 0:
        return {"n": 0}
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1)) if n > 1 else 0.0
    t = m / (sd / math.sqrt(n)) if sd > 0 else 0.0
    wins = sum(1 for x in xs if x > 0)
    return {
        "n": n,
        "mean_bp": round(m, 3),
        "median_bp": round(sorted(xs)[n // 2], 3),
        "t_stat": round(t, 2),
        "win_rate_pct": round(100.0 * wins / n, 1),
        "avg_days": round(sum(t["days"] for t in trades) / n, 1),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/nonus_breakout_2026-11-22.json")
    args = ap.parse_args()

    out: dict = {
        "generated_by": "tools/nonus_breakout_test.py",
        "question": "is the US post-2010 daily-breakout edge a ZIRP artefact or a family effect?",
        "rule": {
            "regime": "month-end close > 10-month SMA, applied to the following month",
            "entry": "close > prior-N-day high, next-open fill",
            "exit": "close < prior-N-day low or regime off, next-open fill",
            "cost_bps_per_side": COST_BPS,
            "looks": list(LOOKS),
        },
        "markets": {},
    }

    for sym, name in MARKETS.items():
        df = load(sym)
        row = {"name": name, "first": str(df.index.min().date()), "last": str(df.index.max().date()),
               "n_bars": int(len(df)), "cells": {}}
        for look in LOOKS:
            for use_reg, tag in ((True, "breakout+10m_regime"), (False, "breakout_only")):
                tr = run(df, look, use_reg, COST_BPS)
                pre = [t for t in tr if t["exit"] < pd.Timestamp("2010-01-01")]
                post = [t for t in tr if t["exit"] >= pd.Timestamp("2010-01-01")]
                row["cells"][f"look{look}|{tag}"] = {
                    "all": stats(tr), "pre_2010": stats(pre), "post_2010": stats(post),
                }
        out["markets"][sym] = row

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")

    # compact table: the 10m-regime variant at the middle look, pre vs post
    print(f"{'market':<26}{'look':>5}{'n_pre':>7}{'pre_bp':>8}{'pre_t':>7}"
          f"{'n_post':>7}{'post_bp':>9}{'post_t':>7}")
    for sym, row in out["markets"].items():
        for look in LOOKS:
            c = row["cells"][f"look{look}|breakout+10m_regime"]
            a, b = c["pre_2010"], c["post_2010"]
            print(f"{row['name'][:25]:<26}{look:>5}{a.get('n',0):>7}{a.get('mean_bp',0):>8.2f}"
                  f"{a.get('t_stat',0):>7.2f}{b.get('n',0):>7}{b.get('mean_bp',0):>9.2f}"
                  f"{b.get('t_stat',0):>7.2f}")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
