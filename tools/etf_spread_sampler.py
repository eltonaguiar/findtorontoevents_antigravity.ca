#!/usr/bin/env python3
"""ETF effective-spread measurement: a live-quote sampler, NOT a guessed estimator.

WHY THIS IS A SAMPLER AND NOT AN ESTIMATOR
    The breakout family is the only strategy in this programme with a real gross
    edge: +22.43 bp/trade at t = +7.32 (tools/execution_sensitivity.py,
    section2_maker_taker). Breakeven sits between 20 and 24 bp round trip. The
    single number that decides whether that edge is investable is therefore the
    realised ETF round-trip spread, and it has been UNMEASURED for the whole
    programme.

    Three attempts to infer it from daily OHLC:

    1. Corwin-Schultz   -> returned 0.00 on all SPY pairs. Degenerate.
    2. Roll             -> returned 34.76 bp, but 2*sqrt(-autocov) scales with
                           return volatility, not with the spread. Structurally
                           invalid for this purpose.
    3. Abdi-Ranaldo     -> I implemented it and it returned ~100,000 bp on SPY.
                           The control check caught it immediately: the estimator
                           is supposed to recover a single-digit-bp spread on the
                           most liquid ETF in the world.

    On (3) I looked for the exact formula and could not confirm the algebra from a
    source I trusted. Rather than tune a variant until it produces a plausible
    number -- which is fitting to the answer -- the implementation was DELETED.
    A spread estimator whose only validation is "it agrees with what I wanted" is
    not a measurement.

    So this measures the spread directly instead: sample the live NBBO from IEX
    during market hours, repeatedly, and report the distribution. That is slower
    and needs many sessions, but every number it produces is an observed quote.

WHAT IT REFUSES TO DO
    * Refuse to emit anything when the quote is stale or empty (outside regular
      trading hours IEX returns null bid/ask -- that is a BLOCKED state, not a
      zero).
    * Refuse to report a single snapshot as the spread. One quote is a sample, not
      a distribution, exactly as with the carry cost series.

Read-only. No orders. Not investment advice.

Usage:
    python3 tools/etf_spread_sampler.py                 # one sample now
    python3 tools/etf_spread_sampler.py --record        # append to the series
    python3 tools/etf_spread_sampler.py --series        # report the series
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "reports/etf_spread"
SERIES = OUT / "etf_spread_series.jsonl"
TICKERS = ["SPY", "QQQ", "GLD"]

# The breakout family's gross edge and the breakeven band (todo 5).
GROSS_EDGE_BP = 22.43
BREAKEVEN_HI = 24.0
INVESTABLE_BELOW = 18.0
MIN_GAP_MINUTES = 20          # one sample per ticker per 20 min


def token():
    t = os.environ.get("TIINGO_API_KEY")
    if not t:
        print("BLOCKED: TIINGO_API_KEY not set. Cannot quote.", file=sys.stderr)
    return t


def quotes(tk, tickers):
    """Live IEX top-of-book. Returns list of dicts, or [] if unavailable."""
    url = ("https://api.tiingo.com/iex/?tickers=" + ",".join(tickers))
    req = urllib.request.Request(url, headers={
        "Content-Type": "application/json", "Authorization": f"Token {tk}"})
    with urllib.request.urlopen(req, timeout=25) as f:
        data = json.loads(f.read())
    return data if isinstance(data, list) else [data]


def build(rows):
    now = datetime.now(timezone.utc)
    out = []
    for r in rows:
        sym = r.get("ticker")
        bid, ask = r.get("bidPrice"), r.get("askPrice")
        if bid in (None, 0) or ask in (None, 0) or ask < bid:
            out.append({"ticker": sym, "ok": False,
                        "reason": "null/stale quote (market closed?)",
                        "quote_timestamp": r.get("quoteTimestamp")})
            continue
        mid = (bid + ask) / 2.0
        spread_bp = (ask - bid) / mid * 1e4
        out.append({"ticker": sym, "ok": True, "bid": bid, "ask": ask,
                    "mid": mid, "spread_bp": spread_bp,
                    "quote_timestamp": r.get("quoteTimestamp"),
                    "utc": now.isoformat(timespec="seconds")})
    return out


def cmd_series():
    if not SERIES.exists():
        print(f"BLOCKED: no series at {SERIES.relative_to(REPO)}")
        return 3
    rows = [json.loads(l) for l in SERIES.open() if l.strip()]
    by = {}
    for r in rows:
        if r.get("ok"):
            by.setdefault(r["ticker"], []).append(r["spread_bp"])
    print(f"series: {len(rows)} sample rows, {len(by)} tickers")
    if not by:
        print("all samples were BLOCKED (never quote during market hours?)")
        return 3
    print(f"\n{'ticker':<7}{'n':>5}{'median':>9}{'p75':>8}{'p95':>8}{'min':>8}"
          f"{'net @med':>10}  verdict")
    for t, v in sorted(by.items()):
        v.sort()
        med = v[len(v) // 2]
        p75 = v[int(0.75 * (len(v) - 1))]
        p95 = v[int(0.95 * (len(v) - 1))]
        net = GROSS_EDGE_BP - med
        verdict = ("INVESTABLE" if med < INVESTABLE_BELOW else
                   "MARGINAL" if med < BREAKEVEN_HI else "DEAD")
        print(f"{t:<7}{len(v):>5}{med:>9.2f}{p75:>8.2f}{p95:>8.2f}{v[0]:>8.2f}"
              f"{net:>+10.2f}  {verdict}")
    print(f"\ngross edge {GROSS_EDGE_BP:+.2f} bp; breakeven band "
          f"{INVESTABLE_BELOW:.0f}-{BREAKEVEN_HI:.0f} bp round trip")
    print("n<10 anywhere -> the distribution is not established yet; the median is")
    print("a point, not a spread, and the deciding parameter is the TAIL.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--series", action="store_true")
    ap.add_argument("--tickers", default=",".join(TICKERS))
    a = ap.parse_args()

    if a.series:
        return cmd_series()

    print("=" * 78)
    print("ETF EFFECTIVE SPREAD -- live NBBO sampler (not an estimator)")
    print("=" * 78)
    tk = token()
    if not tk:
        return 3
    tickers = [t.strip().upper() for t in a.tickers.split(",") if t.strip()]
    try:
        raw = quotes(tk, tickers)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        print(f"BLOCKED: quote request failed: {type(exc).__name__}: {str(exc)[:90]}")
        return 3

    res = build(raw)
    good = [r for r in res if r["ok"]]
    print(f"requested {len(tickers)}, quoted OK {len(good)}")
    print(f"\n{'ticker':<7}{'bid':>11}{'ask':>11}{'spread bp':>11}  quote ts")
    for r in res:
        if r["ok"]:
            print(f"{r['ticker']:<7}{r['bid']:>11.2f}{r['ask']:>11.2f}"
                  f"{r['spread_bp']:>11.2f}  {r['quote_timestamp']}")
        else:
            print(f"{r['ticker']:<7}{'—':>11}{'—':>11}{'BLOCKED':>11}  "
                  f"{r['reason']}")

    if not good:
        print("\nBLOCKED: no live quote. IEX returns null bid/ask outside regular")
        print("trading hours, so this must run 09:30-16:00 America/New_York on a")
        print("trading day. Recording nothing is the correct outcome -- a zero or")
        print("a previous close would be a fabricated spread.")
        return 3

    med = sorted(r["spread_bp"] for r in good)[len(good) // 2]
    print(f"\nthis sample: median {med:.2f} bp one-way"
          f"  -> round trip {2*med:.2f} bp")
    print(f"gross edge {GROSS_EDGE_BP:+.2f} bp  ->  net at this sample "
          f"{GROSS_EDGE_BP - 2*med:+.2f} bp")
    print("\nCAVEAT: this is ONE snapshot. Spreads widen in stress and stress is")
    print("when you enter. Treat it as a floor, not the round-trip cost. That is")
    print("why --record exists and why the verdict comes from --series.")

    if a.record:
        # enforce the minimum gap so a burst cannot inflate n
        prev = []
        if SERIES.exists():
            prev = [json.loads(l) for l in SERIES.open() if l.strip()]
        now = datetime.now(timezone.utc)
        recent = False
        for p in prev[-12:]:
            try:
                dt = datetime.fromisoformat(p["utc"])
            except (KeyError, ValueError):
                continue
            if p.get("ticker") in tickers and (now - dt).total_seconds() < MIN_GAP_MINUTES * 60:
                recent = True
                break
        if recent:
            print(f"\nnot recorded: another sample within {MIN_GAP_MINUTES} min")
            return 0
        SERIES.parent.mkdir(parents=True, exist_ok=True)
        with SERIES.open("a") as f:
            for r in good:
                f.write(json.dumps(r) + "\n")
        n = sum(1 for l in SERIES.open() if l.strip())
        print(f"\nrecorded -> {SERIES.relative_to(REPO)} (series rows: {n})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
