#!/usr/bin/env python3
"""cost_horizon_ladder.py — where does edge beat cost?

The binding constraint established in PART13 is COST, not signal quality: gross
edge is real and 6-9x smaller than the fee needed to capture it at 5-minute
horizons. So the question this answers is not "is there edge" but:

    At which (strategy x horizon x instrument) does gross edge per trade
    exceed the round-trip cost by the Gate-C factor of 3?

Method
------
Instead of assuming a fee and computing a net number, measure the GROSS edge per
trade and derive the MAXIMUM AFFORDABLE round-trip cost:

    max_affordable_rt_cost_bp = gross_bp_per_trade / GATE_C_FACTOR

Then compare that against what the venue actually charges. This inverts the
usual presentation because the usual presentation hides the answer inside the
fee assumption — the exact failure buffy flagged ("a rule that is +0.3%/trade at
4bps and -0.2% at 24bps is a fee disagreement, not a market disagreement").

Honesty rules
  * Signal at bar close i, fill at the OPEN of bar i+1 (no same-bar look-ahead).
  * Stop checked on the entry bar too (conservative).
  * If a bar's range covers both stop and target, the STOP is assumed first.
  * Every cell reports its own n and its own data window. Intraday history is
    short on free data; that is disclosed per row, never averaged over.
  * gross is reported even when negative; no cell is omitted.

Usage: python3 tools/cost_horizon_ladder.py [--quick]
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "cost_horizon"

GATE_C_FACTOR = 3.0      # Gate C: gross edge must be >= 3x round-trip cost

# instrument -> realistic round-trip cost in bp at TAKER, and at MAKER
VENUE_COST_BP = {
    "BTC-USD": (20.0, 4.0),    # spot taker 10bp/side; maker ~2bp/side
    "ETH-USD": (20.0, 4.0),
    "SPY":     (4.0, -1.0),    # commission-free-ish + spread; no maker rebate
    "GLD":     (4.0, -1.0),
}

HORIZONS = ["15m", "1h", "4h", "1D"]
INSTRUMENTS = ["BTC-USD", "ETH-USD", "SPY", "GLD"]
PERIOD = {"15m": "60d", "1h": "730d", "4h": "730d", "1D": "max"}

SL_ATR = 1.0
TP_ATR = 2.0
ATR_N = 14


def fetch(sym: str, interval: str) -> pd.DataFrame | None:
    import yfinance as yf
    try:
        d = yf.download(sym, period=PERIOD[interval], interval=interval,
                        auto_adjust=True, progress=False, threads=False)
        if d is None or len(d) == 0:
            return None
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        d = d.rename(columns=str.lower)
        need = {"open", "high", "low", "close"}
        if not need.issubset(d.columns):
            return None
        d = d[list(need)].dropna()
        return d if len(d) > ATR_N + 30 else None
    except Exception:
        return None


def atr_series(df: pd.DataFrame, n: int = ATR_N) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def sig_donchian(df: pd.DataFrame, look: int = 20) -> pd.Series:
    hi = df["high"].rolling(look).max().shift(1)
    return (df["close"] > hi).astype(int)


def sig_rsi2(df: pd.DataFrame, n: int = 2, thresh: float = 10.0) -> pd.Series:
    delta = df["close"].diff()
    up = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    return (rsi < thresh).astype(int)


def sig_ema(df: pd.DataFrame, fast: int = 9, slow: int = 21) -> pd.Series:
    f = df["close"].ewm(span=fast, adjust=False).mean()
    s = df["close"].ewm(span=slow, adjust=False).mean()
    return ((f > s) & (f.shift(1) <= s.shift(1))).astype(int)


SIGNALS = {"donchian": sig_donchian, "rsi2": sig_rsi2, "emacross": sig_ema}


def simulate(df: pd.DataFrame, sig: pd.Series, a: pd.Series, max_hold: int) -> list[float]:
    """Gross fractional returns per trade. Entry at NEXT bar open.

    ONE POSITION AT A TIME. A Donchian breakout emits a signal on every bar of a
    sustained move; entering all of them counts the same move many times and
    inflates both n and the t-statistic. We therefore skip any signal that fires
    while a position is already open. (Caught in review of this file's first
    run: BTC 1D listed n=379 with heavy clustering, which overstated the
    evidence.)
    """
    o, h, l, c = (df[k].values for k in ("open", "high", "low", "close"))
    sv, av = sig.values, a.values
    out = []
    busy_until = -1
    for i in range(ATR_N + 2, len(df) - 2):
        if i <= busy_until:            # still in a trade — ignore this signal
            continue
        if sv[i] != 1 or not np.isfinite(av[i]) or av[i] <= 0:
            continue
        entry = o[i + 1]
        if not np.isfinite(entry) or entry <= 0:
            continue
        tp, sl = entry + TP_ATR * av[i], entry - SL_ATR * av[i]
        exitp = None
        exit_bar = min(i + max_hold, len(df) - 1)
        for j in range(i + 1, min(i + 1 + max_hold, len(df))):
            if l[j] <= sl:                 # pessimistic: stop wins ties
                exitp, exit_bar = sl, j
                break
            if h[j] >= tp:
                exitp, exit_bar = tp, j
                break
        if exitp is None:
            exitp = c[exit_bar]
        busy_until = exit_bar
        out.append((exitp - entry) / entry)
    return out


def max_hold_for(interval: str) -> int:
    return {"15m": 24, "1h": 24, "4h": 12, "1D": 10}[interval]


def cells(quick: bool) -> list[dict]:
    rows = []
    for inst in INSTRUMENTS:
        for iv in HORIZONS:
            df = fetch(inst, iv)
            if df is None:
                rows.append({"instrument": inst, "horizon": iv, "status": "NO_DATA"})
                continue
            a = atr_series(df)
            mh = max_hold_for(iv)
            for sname, fn in SIGNALS.items():
                if quick and sname != "donchian":
                    continue
                try:
                    tr = simulate(df, fn(df), a, mh)
                except Exception as e:
                    rows.append({"instrument": inst, "horizon": iv, "strategy": sname,
                                 "status": f"ERR {type(e).__name__}"})
                    continue
                if len(tr) < 20:
                    rows.append({"instrument": inst, "horizon": iv, "strategy": sname,
                                 "status": "INSUFFICIENT_N", "n": len(tr)})
                    continue
                gross_bp = statistics.mean(tr) * 1e4
                sd = statistics.stdev(tr) * 1e4 if len(tr) > 1 else 0.0
                tstat = (gross_bp / (sd / math.sqrt(len(tr)))) if sd else float("nan")
                taker, maker = VENUE_COST_BP[inst]
                max_aff = gross_bp / GATE_C_FACTOR
                rows.append({
                    "instrument": inst, "horizon": iv, "strategy": sname,
                    "status": "OK", "n": len(tr),
                    "window": f"{df.index[0].date()}..{df.index[-1].date()}",
                    "bars": len(df),
                    "gross_bp": round(gross_bp, 3),
                    "sd_bp": round(sd, 2),
                    "t": round(tstat, 2),
                    "max_affordable_rt_bp": round(max_aff, 2),
                    "venue_taker_bp": taker, "venue_maker_bp": maker,
                    "passes_gate_on_taker": bool(gross_bp >= GATE_C_FACTOR * taker),
                    "passes_gate_on_maker": bool(gross_bp >= GATE_C_FACTOR * maker),
                })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    print(f"cost-horizon ladder — Gate C factor {GATE_C_FACTOR}x, "
          f"{'quick (donchian only)' if a.quick else 'full (3 strategies)'}")
    rows = cells(a.quick)
    ok = [r for r in rows if r.get("status") == "OK"]

    print(f"\n=== GROSS EDGE PER TRADE AND MAX AFFORDABLE COST ===")
    print(f"{'inst':<8} {'horizon':<8} {'strategy':<10} {'n':>5} {'gross bp':>10} {'t':>7} "
          f"{'maxCost':>8} {'taker':>7} {'maker':>7} {'GATE C':>10}  window")
    print("-" * 118)
    for r in sorted(ok, key=lambda x: -x["gross_bp"]):
        verdict = ("PASS taker" if r["passes_gate_on_taker"] else
                   ("PASS maker" if r["passes_gate_on_maker"] else "FAIL"))
        print(f"{r['instrument']:<8} {r['horizon']:<8} {r['strategy']:<10} {r['n']:>5} "
              f"{r['gross_bp']:>10.2f} {r['t']:>7.2f} {r['max_affordable_rt_bp']:>8.2f} "
              f"{r['venue_taker_bp']:>7.1f} {r['venue_maker_bp']:>7.1f} {verdict:>10}  {r['window']}")

    skipped = [r for r in rows if r.get("status") != "OK"]
    if skipped:
        print(f"\n=== NOT MEASURABLE ({len(skipped)} cells) ===")
        for r in skipped[:12]:
            print(f"  {r['instrument']:<8} {r['horizon']:<8} {r.get('strategy','-'):<10} "
                  f"{r['status']}" + (f" (n={r.get('n')})" if 'n' in r else ""))

    n_pass = sum(1 for r in ok if r["passes_gate_on_taker"] or r["passes_gate_on_maker"])
    print(f"\n=== SUMMARY ===")
    print(f"  cells measured      : {len(ok)}")
    print(f"  cells not measurable: {len(skipped)}")
    print(f"  pass Gate C         : {n_pass}")
    if ok:
        pos = [r for r in ok if r["gross_bp"] > 0]
        print(f"  gross positive      : {len(pos)}/{len(ok)}")
        if pos:
            by_h = {}
            for r in pos:
                by_h.setdefault(r["horizon"], []).append(r["gross_bp"])
            print("  median gross bp by horizon (positive cells only):")
            for h in HORIZONS:
                if h in by_h:
                    print(f"    {h:<5} n={len(by_h[h]):>2}  median {statistics.median(by_h[h]):>+8.2f} bp")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cost_horizon_ladder.json").write_text(json.dumps(
        {"generated_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
         "gate_c_factor": GATE_C_FACTOR, "venue_costs_bp": VENUE_COST_BP,
         "signals": list(SIGNALS), "rows": rows}, indent=1, default=str))
    print(f"\nwrote {OUT/'cost_horizon_ladder.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
