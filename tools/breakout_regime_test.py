#!/usr/bin/env python3
"""breakout_regime_test.py — is the daily-breakout edge real, or a ZIRP artefact?

THE PROBLEM THIS SOLVES
-----------------------
My cost-horizon ladder found daily breakout continuation to be the only
Gate-C-positive family. But SPY's edge is almost entirely POST-2010: first half
+5.49 bp/trade (t=0.47), second half +40.70 bp (t=3.91). Two explanations:

  (a) REGIME — the 2010-2026 era (ZIRP, buybacks, passive inflows) created an
      edge that did not exist before. Then the edge is conditional and should be
      sized as such.
  (b) SAMPLE — the US simply had an unlucky first half and the family effect is
      real everywhere.

The test that separates them: run the SAME rule on markets that are NOT the US
and have long pre-2010 history. If pre-2010 is negative in every market, it is
(a). If pre-2010 is positive somewhere, it is (b).

Rule held fixed everywhere (no per-market tuning):
  Donchian breakout, close > prior 20-bar high, long only, one position at a
  time, entry at NEXT bar open, TP 2xATR(14), SL 1xATR(14), max hold 10 bars,
  stop assumed first when a bar covers both.
  Costs charged both legs at 10 bp per side (equity-index ETF-ish).

Usage: python3 tools/breakout_regime_test.py
"""
from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "breakout_regime"

MARKETS = {
    "^GSPC": "US S&P 500",
    "^FTSE": "UK FTSE 100",
    "^GDAXI": "Germany DAX",
    "^N225": "Japan Nikkei 225",
    "^GSPTSE": "Canada TSX",
    "^AXJO": "Australia ASX 200",
    "^HSI": "Hong Kong HSI",
}
SPLIT = pd.Timestamp("2010-01-01")
LOOK = 20
ATR_N = 14
SL_ATR, TP_ATR = 1.0, 2.0
MAX_HOLD = 10
COST_BP = 10.0


def fetch(sym: str) -> pd.DataFrame | None:
    import yfinance as yf
    try:
        d = yf.download(sym, period="max", interval="1d", auto_adjust=True,
                        progress=False, threads=False)
        if d is None or len(d) == 0:
            return None
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        d = d.rename(columns=str.lower)
        if not {"open", "high", "low", "close"}.issubset(d.columns):
            return None
        d.index = pd.to_datetime(d.index).tz_localize(None)
        return d[["open", "high", "low", "close"]].dropna()
    except Exception:
        return None


def atr(df: pd.DataFrame, n: int = ATR_N) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def trades(df: pd.DataFrame, cost_bp: float = COST_BP) -> list[dict]:
    a = atr(df)
    hi = df["high"].rolling(LOOK).max().shift(1)
    sig = (df["close"] > hi).values
    av = a.values
    o, h, l, c = (df[k].values for k in ("open", "high", "low", "close"))
    idx = df.index
    out, busy = [], -1
    for i in range(ATR_N + LOOK + 2, len(df) - 2):
        if i <= busy or not sig[i] or not np.isfinite(av[i]) or av[i] <= 0:
            continue
        entry = o[i + 1]
        if not np.isfinite(entry) or entry <= 0:
            continue
        tp, sl = entry + TP_ATR * av[i], entry - SL_ATR * av[i]
        exitp = exit_bar = None
        for j in range(i + 1, min(i + 1 + MAX_HOLD, len(df))):
            if l[j] <= sl:
                exitp, exit_bar = sl, j
                break
            if h[j] >= tp:
                exitp, exit_bar = tp, j
                break
        if exitp is None:
            exit_bar = min(i + MAX_HOLD, len(df) - 1)
            exitp = c[exit_bar]
        busy = exit_bar
        out.append({"date": idx[i + 1], "net": (exitp - entry) / entry - 2 * cost_bp / 1e4})
    return out


def stat(tr: list[dict]) -> dict:
    if len(tr) < 5:
        return {"n": len(tr)}
    v = np.array([t["net"] for t in tr])
    sd = v.std(ddof=1)
    return {"n": len(v), "mean_bp": float(v.mean() * 1e4),
            "wr": float(100 * (v > 0).mean()),
            "t": float(v.mean() / (sd / math.sqrt(len(v)))) if sd else float("nan")}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--cost", type=float, default=COST_BP,
                    help="one-way cost in bp per side (4 = commission-free ETF, 10 = conservative)")
    args = ap.parse_args()
    cost_bp = args.cost
    print("=== BREAKOUT REGIME TEST — same rule, 7 markets, split at 2010 ===")
    print(f"    Donchian {LOOK} / TP {TP_ATR}xATR / SL {SL_ATR}xATR / hold {MAX_HOLD} / "
          f"{cost_bp:.0f}bp per side / next-bar-open\n")
    print(f"{'market':<18} {'bars':>6} {'from':>11} {'pre-2010 n':>11} {'pre bp':>8} {'pre t':>7} "
          f"{'post-2010 n':>12} {'post bp':>8} {'post t':>7}  verdict")
    print("-" * 118)
    rows = []
    for sym, label in MARKETS.items():
        df = fetch(sym)
        if df is None or len(df) < 800:
            print(f"{label:<18} NO DATA"); continue
        tr = trades(df, cost_bp)
        pre = stat([t for t in tr if t["date"] < SPLIT])
        post = stat([t for t in tr if t["date"] >= SPLIT])
        if pre.get("n", 0) < 5 or post.get("n", 0) < 5:
            print(f"{label:<18} {len(df):>6} {df.index[0].date()} insufficient sample")
            continue
        both = pre["mean_bp"] > 0 and post["mean_bp"] > 0
        verdict = "REAL (both halves +)" if both else (
            "POST-ONLY" if post["mean_bp"] > 0 else "NEGATIVE")
        print(f"{label:<18} {len(df):>6} {df.index[0].date()} {pre['n']:>11} "
              f"{pre['mean_bp']:>+8.1f} {pre['t']:>+7.2f} {post['n']:>12} "
              f"{post['mean_bp']:>+8.1f} {post['t']:>+7.2f}  {verdict}")
        rows.append({"market": label, "symbol": sym, "bars": len(df),
                     "start": df.index[0].strftime("%Y-%m-%d"),
                     "pre_2010": pre, "post_2010": post, "verdict": verdict})

    print("\n=== VERDICT ===")
    pre_pos = [r for r in rows if r["pre_2010"]["mean_bp"] > 0]
    both_pos = [r for r in rows if r["pre_2010"]["mean_bp"] > 0 and r["post_2010"]["mean_bp"] > 0]
    print(f"  markets measured            : {len(rows)}")
    print(f"  pre-2010 mean POSITIVE      : {len(pre_pos)}/{len(rows)}")
    print(f"  positive in BOTH halves     : {len(both_pos)}/{len(rows)}")
    if len(both_pos) >= max(2, len(rows) // 2):
        print("  => FAMILY EFFECT. The edge exists pre-2010 in multiple non-US markets;")
        print("     the US post-2010 concentration is sample, not regime.")
    elif len(pre_pos) == 0:
        print("  => REGIME ARTEFACT. No market shows a positive pre-2010 edge at this")
        print("     specification, so the family should be treated as conditional on the")
        print("     2010+ era (ZIRP / buybacks / passive inflows), not as a durable edge.")
    else:
        print("  => MIXED. Some markets show pre-2010 edge, most do not. Treat as")
        print("     weak evidence for the family and size it as conditional.")
    print("\n  Note: pre-2010 samples include 2000-2002 and 2008 drawdowns, which is")
    print("  exactly the regime a breakout rule is supposed to survive. A rule that only")
    print("  works after 2010 has not been tested against a sustained bear.")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "breakout_regime_test.json").write_text(json.dumps({
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rule": {"donchian": LOOK, "tp_atr": TP_ATR, "sl_atr": SL_ATR,
                 "max_hold": MAX_HOLD, "cost_bp_per_side": cost_bp,
                 "fill": "next bar open", "tie_break": "stop first"},
        "split": SPLIT.strftime("%Y-%m-%d"), "markets": rows}, indent=1))
    print(f"\nwrote {OUT/'breakout_regime_test.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
