#!/usr/bin/env python3
"""Per-asset-class realised risk, measured from our own cached bars.

Backs the numbers broadcast on COMS topic
`notes/asset-class-risk-edge-copilot-20261123` (2026-11-23). The point of this
file is that a broadcast claim should be reproducible from the repo, not live
only in a shell history.

Reports, per class, the MEDIAN over member symbols of:
  * annualised volatility (daily log returns, x sqrt(252))
  * max drawdown (peak-to-trough on close)
  * annualised return over the sample
  * Sharpe (annual return / annual vol, zero risk-free -- it is a ranking aid,
    not a claim of excess return)

WHAT THIS IS NOT
    These are NOT strategy results and NOT net of cost. They are buy-and-hold
    risk characteristics of the instruments, which is what "how risky is this
    asset class" means. A strategy's risk is a different question.

    Sample depth is small per class (n=10..24 symbols). The medians are stable
    enough to RANK classes but individual members vary widely -- the worst
    member of each class is printed for that reason.

Read-only. Not investment advice.

Usage:
    python3 tools/asset_class_risk.py
"""
from __future__ import annotations

import csv
import glob
import json
import math
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache" / "asset_class_review"
OUT = ROOT / "reports" / "asset_class_risk.json"

ETFS = {"AGG", "ARKK", "BND", "DIA", "EEM", "EFA", "GLD", "HYG", "IEF", "IWM",
        "JNK", "LQD", "QQQ", "SHY", "SLV", "SOXX", "SPY", "TIP", "TLH", "TLT",
        "XLE", "XLF", "XLK", "XLV"}


def classify(sym: str) -> str:
    if sym.endswith("-USD"):
        return "CRYPTO"
    if sym.endswith("_X"):
        return "FOREX"
    if sym.endswith("_F"):
        return "COMMODITY/FUTURES"
    return "ETF" if sym in ETFS else "EQUITY"


def stats_for(path: str) -> dict | None:
    closes = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                v = float(r["Close"])
            except Exception:                              # noqa: BLE001
                continue
            if v > 0:
                closes.append(v)
    if len(closes) < 250:
        return None
    rets = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    if len(rets) < 200:
        return None
    vol = statistics.stdev(rets) * math.sqrt(252)
    peak, mdd = closes[0], 0.0
    for p in closes:
        peak = max(peak, p)
        mdd = min(mdd, p / peak - 1)
    ann = (closes[-1] / closes[0]) ** (252 / len(closes)) - 1
    return {"vol": vol, "mdd": mdd, "ann": ann,
            "sharpe": ann / vol if vol > 0 else 0.0,
            "first": None, "last": None}


def main() -> int:
    files = sorted(glob.glob(str(CACHE / "*_5y.csv")))
    if not files:
        print(f"::error:: no cached bars under {CACHE}")
        return 2
    by_class: dict[str, list] = {}
    for f in files:
        sym = os.path.basename(f).replace("_5y.csv", "")
        s = stats_for(f)
        if s:
            s["symbol"] = sym
            by_class.setdefault(classify(sym), []).append(s)

    rows = []
    for cls, members in by_class.items():
        rows.append({
            "asset_class": cls,
            "n": len(members),
            "median_vol": round(statistics.median([m["vol"] for m in members]), 4),
            "median_mdd": round(statistics.median([m["mdd"] for m in members]), 4),
            "median_ann": round(statistics.median([m["ann"] for m in members]), 4),
            "median_sharpe": round(statistics.median([m["sharpe"] for m in members]), 4),
            "worst_vol_member": max(members, key=lambda m: m["vol"])["symbol"],
            "members": [m["symbol"] for m in members],
        })
    rows.sort(key=lambda r: -r["median_vol"])

    out = {"generated_utc": datetime.now(timezone.utc).isoformat(),
           "sample": "data/cache/asset_class_review/*_5y.csv, 5y daily closes",
           "not_a_strategy_result": True,
           "note": "buy-and-hold risk characteristics, gross, medians per class",
           "classes": rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))

    print(f"{'CLASS':18} {'n':>3} {'medVol':>8} {'medMDD':>8} {'medAnn':>8} "
          f"{'medSR':>7}  worst-vol")
    for r in rows:
        print(f"{r['asset_class']:18} {r['n']:>3} {r['median_vol']:>7.1%} "
              f"{r['median_mdd']:>7.1%} {r['median_ann']:>7.1%} "
              f"{r['median_sharpe']:>7.2f}  {r['worst_vol_member']}")
    print(f"\nwritten: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
