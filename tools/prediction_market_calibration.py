#!/usr/bin/env python3
"""Prediction-market calibration: do Polymarket prices equal realised frequencies?

TODO 41.

The question that matters for a trading programme is not "are markets efficient"
but "is there a bucket of contracts where price and outcome systematically
disagree by more than the cost of trading it". This measures exactly that.

Method
  1. Pull resolved binary markets from the public Gamma API.
  2. For each, take the price at a FIXED LEAD TIME before resolution (default 7
     days). The final price is ~0 or ~1 by construction and carries no signal;
     using it would be circular.
  3. Bucket by that price and compare the bucket's mean price to its realised YES
     frequency. That difference is the edge before cost.
  4. Score with Brier against a 0.5-climatology baseline, and report n per bucket
     so a 3-market bucket cannot masquerade as a finding.

Cost model
  Polymarket charges no trading fee on most markets, but there is a spread. The
  spread is NOT measured here (would need the book per market) -> UNMEASURED, and
  no bucket is labelled tradable without it. The edge is reported gross with that
  stated.

Read-only, public endpoints, no keys, no orders. Not investment advice.

Usage:
    python3 tools/prediction_market_calibration.py
    python3 tools/prediction_market_calibration.py --max 500 --lead-days 7
"""
from __future__ import annotations

import argparse
import json
import math
import statistics as st
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "reports/prediction_market_calibration"
GAMMA = "https://gamma-api.polymarket.com/markets"
CLOB = "https://clob.polymarket.com/prices-history"
UA = {"User-Agent": "antigravity-research/1.0"}


def get(url, timeout=25, retries=2):
    for k in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as f:
                return json.loads(f.read())
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                json.JSONDecodeError):
            if k == retries:
                return None
    return None


def list_markets(want):
    """Page the Gamma API until we have `want` closed binary markets."""
    out, offset, page = [], 0, 100
    while len(out) < want and offset < 12000:
        url = (f"{GAMMA}?closed=true&limit={page}&offset={offset}"
               f"&order=endDate&ascending=false")
        batch = get(url)
        if not batch:
            break
        for m in batch:
            ct = m.get("clobTokenIds")
            op = m.get("outcomePrices")
            if not ct or not op:
                continue
            try:
                ctl = json.loads(ct) if isinstance(ct, str) else ct
                opl = json.loads(op) if isinstance(op, str) else op
            except (json.JSONDecodeError, TypeError):
                continue
            if len(ctl) < 1 or len(opl) < 2:
                continue
            try:
                p0, p1 = float(opl[0]), float(opl[1])
            except (TypeError, ValueError):
                continue
            # resolved iff the prices are a 0/1 pair
            if not (abs(p0 + p1 - 1.0) < 0.02 and (p0 in (0.0, 1.0) or p1 in (0.0, 1.0))):
                continue
            out.append({"q": (m.get("question") or "")[:80],
                        "token": ctl[0], "yes_won": int(round(p0)) == 1,
                        "end": m.get("endDate"), "vol": m.get("volumeNum") or 0})
            if len(out) >= want:
                break
        offset += page
    return out


def price_at_lead(m, lead_days):
    """Price `lead_days` before the LAST observation in the market's history."""
    h = get(f"{CLOB}?market={m['token']}&interval=max&fidelity=1440")
    if not h:
        return None
    pts = h.get("history") or []
    if len(pts) < 3:
        return None
    last_t = pts[-1]["t"]
    target = last_t - lead_days * 86400
    best = None
    for p in pts:
        if p["t"] <= target:
            best = p
        else:
            break
    if best is None:
        best = pts[0]
    return float(best["p"]), len(pts)


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=500)
    ap.add_argument("--lead-days", type=int, default=7)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    print("=" * 78)
    print("SECTION 41 -- PREDICTION MARKET CALIBRATION (Polymarket, resolved)")
    print("=" * 78)
    print(f"source: public Gamma + CLOB endpoints; lead time {a.lead_days}d before "
          f"resolution")
    markets = list_markets(a.max)
    print(f"resolved binary markets collected: {len(markets):,}")
    if len(markets) < 80:
        print("BLOCKED: fewer than 80 usable resolved markets. Nothing measured.")
        return 3

    rows, miss = [], 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(price_at_lead, m, a.lead_days): m for m in markets}
        for f, m in futs.items():
            try:
                r = f.result()
            except Exception:  # noqa: BLE001
                r = None
            if r is None:
                miss += 1
                continue
            px, npts = r
            rows.append({"p": px, "y": 1 if m["yes_won"] else 0,
                         "npts": npts, "q": m["q"]})
    print(f"with a usable price history:       {len(rows):,}  "
          f"(dropped {miss:,} for missing/short history)")
    if len(rows) < 80:
        print("BLOCKED: too few markets with history.")
        return 3

    base = sum(r["y"] for r in rows) / len(rows)
    print(f"base rate (YES frequency):         {100*base:.2f}%")

    # Brier against climatology
    brier = sum((r["p"] - r["y"]) ** 2 for r in rows) / len(rows)
    brier_climo = sum((base - r["y"]) ** 2 for r in rows) / len(rows)
    print(f"Brier score (market):              {brier:.4f}")
    print(f"Brier score (0.5-climatology):     {0.25:.4f}")
    print(f"Brier score (base-rate climatology): {brier_climo:.4f}")
    skill = 1 - brier / brier_climo if brier_climo else float("nan")
    print(f"Brier skill vs base rate:          {skill:+.4f}  "
          f"({'beats' if skill > 0 else 'FAILS TO BEAT'} the naive base rate)")

    # Calibration curve
    edges = [0.0, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.0001]
    buckets = defaultdict(list)
    for r in rows:
        for i in range(len(edges) - 1):
            if edges[i] <= r["p"] < edges[i + 1]:
                buckets[(edges[i], edges[i + 1])].append(r)
                break
    print(f"\ncalibration curve (price bucket -> realised YES rate)")
    hdr = (f"    {'bucket':<12}{'n':>6}{'mean px':>9}{'YES rate':>10}"
           f"{'gap':>9}{'95% CI':>18}  reading")
    print(hdr)
    print("    " + "-" * (len(hdr) - 4))
    calib = {}
    for lo, hi in sorted(buckets):
        v = buckets[(lo, hi)]
        if len(v) < 10:
            continue
        mp = sum(r["p"] for r in v) / len(v)
        yr = sum(r["y"] for r in v) / len(v)
        clo, chi = wilson(sum(r["y"] for r in v), len(v))
        gap = yr - mp
        sig = not (clo <= mp <= chi)
        reading = ("price INSIDE outcome CI -> calibrated"
                   if not sig else
                   ("outcomes BETTER than price (price too low)" if gap > 0
                    else "outcomes WORSE than price (price too high)"))
        print(f"    {lo:.2f}-{hi if hi<=1 else 1.0:.2f}  {len(v):>6}{mp:>9.3f}"
              f"{yr:>10.3f}{gap:>+9.3f}   [{clo:.3f},{chi:.3f}]  {reading}")
        calib[f"{lo:.1f}-{min(hi,1.0):.1f}"] = {
            "n": len(v), "mean_price": mp, "yes_rate": yr, "gap": gap,
            "ci": [clo, chi], "significant": sig}

    # Bounded n_trials: 10 buckets tested.
    n_trials = len(calib)
    sig_buckets = [k for k, v in calib.items() if v["significant"]]
    print(f"\n    n_trials = {n_trials} price buckets")
    print(f"    buckets whose outcome CI excludes their mean price: "
          f"{len(sig_buckets)}/{n_trials}")
    print(f"    expected false positives at alpha=.05: {0.05*n_trials:.1f}")
    if len(sig_buckets) <= 0.05 * n_trials:
        print("    -> no bucket shows a price/outcome disagreement beyond what")
        print("       multiple testing would produce. The market is calibrated at")
        print("       this lead time and there is nothing here to trade.")

    # Costs
    print(f"\ncost of acting on any gap")
    print("    Polymarket trading fee:        0 on most markets")
    print("    spread / slippage:             UNMEASURED (needs per-market book)")
    print("    -> because the spread is unmeasured, NO bucket can be labelled")
    print("       tradable, however large its gross gap. The gate is")
    print("       docs/PROMOTION_GATE_2026-11-22.md gate 1: unmeasured cost cannot")
    print("       support a promotion, only a rejection.")

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "calibration.json").write_text(json.dumps(
        {"n_markets": len(rows), "lead_days": a.lead_days,
         "base_rate": base, "brier": brier, "brier_climo": brier_climo,
         "brier_skill": skill, "buckets": calib,
         "n_trials": n_trials, "significant_buckets": sig_buckets},
        indent=1))
    print(f"\nwrote {out/'calibration.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
