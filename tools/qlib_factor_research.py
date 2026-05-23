#!/usr/bin/env python3
"""qlib-factor edge research — do the volume / price-volume / volatility
factors predict forward returns, walk-forward?

The last in-house edge candidate (per reports/EDGE_VERDICT_2026-05-18.md). The
qlib Alpha158-family factors added in PR #1178 (pv_corr30, vol_ratio,
realized_vol30) were never tested for predictive power — only that they compute.
This is the test, on a CLEAN controlled universe of liquid ETFs (no dependency
on the noise pick-ledger).

Method (no look-ahead): for each symbol, weekly OHLCV; at each week compute the
factor from strictly-past bars; bucket weeks into factor terciles; measure the
forward N-week return spread top-tercile minus bottom-tercile; require the
spread to hold the same sign across years to count as an edge.

    python tools/qlib_factor_research.py [--fwd-weeks 4] [--out report.md]
"""
from __future__ import annotations

import argparse
import math
import statistics
import sys
from pathlib import Path

# Liquid, deep-history ETFs — reliable yfinance OHLCV+volume.
UNIVERSE = ("SPY", "QQQ", "IWM", "GLD", "SLV", "XLK", "XLE", "EEM", "TLT", "HYG")
WARMUP = 35   # weeks of history needed before the first factor value


def pv_corr(closes, volumes, period=30):
    if len(closes) < period:
        return None
    c, v = closes[-period:], volumes[-period:]
    mc, mv = sum(c) / period, sum(v) / period
    cov = sum((c[i] - mc) * (v[i] - mv) for i in range(period))
    vc = sum((x - mc) ** 2 for x in c)
    vv = sum((x - mv) ** 2 for x in v)
    d = math.sqrt(vc * vv)
    return None if d == 0 else max(-1.0, min(1.0, cov / d))


def vol_ratio(volumes, short=5, long=30):
    if len(volumes) < long:
        return None
    sa = sum(volumes[-short:]) / short
    la = sum(volumes[-long:]) / long
    if la <= 0:
        return None
    r = sa / la
    return max(-1.0, min(1.0, math.log(r))) if r > 0 else None


def realized_vol(closes, period=30):
    if len(closes) < period + 1:
        return None
    rets = [closes[i] / closes[i - 1] - 1.0
            for i in range(len(closes) - period, len(closes))
            if closes[i - 1] > 0]
    if len(rets) < 2:
        return None
    return statistics.pstdev(rets)


FACTORS = {"pv_corr30": pv_corr, "vol_ratio": vol_ratio, "realized_vol30": realized_vol}


def fetch_ohlcv(ticker):
    import time
    import warnings
    warnings.filterwarnings("ignore")
    import yfinance as yf
    for _ in range(3):
        df = yf.download(ticker, period="max", interval="1wk",
                         progress=False, auto_adjust=True)
        if df is not None and len(df) >= 80:
            break
        time.sleep(5)
    else:
        return []
    close, vol = df["Close"], df["Volume"]
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]
    if hasattr(vol, "columns"):
        vol = vol.iloc[:, 0]
    rows = []
    for idx in close.index:
        try:
            c, v = float(close.loc[idx]), float(vol.loc[idx])
        except (TypeError, ValueError):
            continue
        d = idx.date() if hasattr(idx, "date") else None
        if d is not None and c > 0:
            rows.append((str(d), c, v))
    return rows


def research(fwd_weeks: int) -> dict:
    # per factor: list of (year, factor_value, forward_return)
    obs = {f: [] for f in FACTORS}
    per_symbol = {}
    for sym in UNIVERSE:
        rows = fetch_ohlcv(sym)
        if len(rows) < WARMUP + fwd_weeks + 10:
            per_symbol[sym] = {"skip": f"only {len(rows)} bars"}
            continue
        closes = [r[1] for r in rows]
        vols = [r[2] for r in rows]
        n_sig = 0
        for i in range(WARMUP, len(rows) - fwd_weeks):
            fwd = closes[i + fwd_weeks] / closes[i] - 1.0
            yr = rows[i][0][:4]
            for fname, fn in FACTORS.items():
                if fname == "vol_ratio":
                    val = fn(vols[:i + 1])
                elif fname == "pv_corr30":
                    val = fn(closes[:i + 1], vols[:i + 1])
                else:  # realized_vol30
                    val = fn(closes[:i + 1])
                if val is not None:
                    obs[fname].append((yr, val, fwd))
            n_sig += 1
        per_symbol[sym] = {"bars": len(rows), "weeks_scored": n_sig}
    return {"obs": obs, "per_symbol": per_symbol}


def _tercile_spread(triples):
    """Forward-return spread: top-tercile-by-factor minus bottom-tercile."""
    if len(triples) < 30:
        return None
    s = sorted(triples, key=lambda x: x[1])
    k = len(s) // 3
    bot = [t[2] for t in s[:k]]
    top = [t[2] for t in s[-k:]]
    return statistics.fmean(top) - statistics.fmean(bot)


def render(r: dict, fwd_weeks: int) -> str:
    out = ["# qlib-Factor Edge Research — pv_corr30 / vol_ratio / realized_vol30",
           "",
           f"Universe: {', '.join(UNIVERSE)}. Weekly bars. Forward return = "
           f"{fwd_weeks} weeks. Edge = top-tercile-minus-bottom-tercile forward-"
           f"return spread, **year-stable** (consistent sign).", ""]
    skipped = [s for s, v in r["per_symbol"].items() if "skip" in v]
    if skipped:
        out.append(f"Skipped (thin data): {', '.join(skipped)}")
        out.append("")
    any_edge = False
    for fname, triples in r["obs"].items():
        out += [f"## {fname}", ""]
        if len(triples) < 60:
            out += [f"insufficient observations (n={len(triples)})", ""]
            continue
        overall = _tercile_spread(triples)
        out.append(f"- pooled top-minus-bottom tercile {fwd_weeks}w return spread: "
                    f"**{overall*100:+.2f}%**  (n={len(triples)})")
        years = sorted({t[0] for t in triples})
        pos = neg = 0
        ylines = []
        for y in years:
            yt = [t for t in triples if t[0] == y]
            sp = _tercile_spread(yt)
            if sp is None:
                continue
            pos += sp > 0
            neg += sp <= 0
            ylines.append(f"  - {y}: {sp*100:+.2f}%  (n={len(yt)})")
        out.append(f"- year sign-split: {pos} positive / {neg} non-positive")
        out += ylines
        stable = (pos >= 3 * max(neg, 1) and abs(overall) > 0.005)
        any_edge |= stable
        out.append("")
        out.append(f"**Verdict: {'STABLE — candidate, run through harness' if stable else 'NOT an edge — spread is not year-stable or near-zero'}.**")
        out.append("")
    out.append("---")
    out.append("**Overall: " + ("at least one qlib factor shows a year-stable "
               "forward-return spread — promote to the harness."
               if any_edge else
               "no qlib factor shows a year-stable forward-return spread. The "
               "in-house edge-candidate queue is now exhausted — every testable "
               "candidate (scores, COT, qlib factors) has been falsified. The "
               "path forward is new signal sources, not the existing pipeline.")
               + "**")
    return "\n".join(out)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fwd-weeks", type=int, default=4)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    r = research(args.fwd_weeks)
    report = render(r, args.fwd_weeks)
    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"# wrote {args.out}", file=sys.stderr)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
