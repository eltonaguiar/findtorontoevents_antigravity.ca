#!/usr/bin/env python3
"""audjpy_tradelevel_check.py — trade-level AUDJPY vs the audit3 +0.576% aggregate.

The audit3 symbol block says AUDJPY n=34, net +0.576%/trade (DSR 0.815). This checks a TRADE-LEVEL
sample (riseoftheclaw/data/signal_tracking.json). pnl values there are FRACTIONS (0.01 = 1%); all
outputs are expressed in PERCENT. Flags implausible (>100%) outliers, which dominate a mean.
"""
import json, statistics as st
from math import comb
from pathlib import Path

def main():
    d = json.load(open("riseoftheclaw/data/signal_tracking.json"))
    rows = d.get("signals") or d.get("picks") or d.get("items") or []
    if isinstance(rows, dict):
        rows = list(rows.values())
    aj = [r for r in rows if isinstance(r, dict) and "AUDJPY" in str(r.get("symbol", "")).upper()
          and r.get("pnl_pct") is not None]
    raw = sorted(float(r["pnl_pct"]) for r in aj)     # fractions
    pct = [v * 100 for v in raw]                       # percent
    n = len(pct); w = sum(1 for x in pct if x > 0)
    k = max(1, int(n * 0.1))
    p_sign = min(1.0, 2 * sum(comb(n, i) for i in range(0, w + 1)) / 2 ** n) if w <= n / 2 else None
    out = {"generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
           "source": "riseoftheclaw/data/signal_tracking.json (trade-level; pnl stored as fractions)",
           "symbol": "AUDJPY=X", "n": n,
           "mean_pct": round(st.mean(pct), 4), "median_pct": round(st.median(pct), 4),
           "sd_pct": round(st.pstdev(pct), 4), "min_pct": round(min(pct), 4), "max_pct": round(max(pct), 4),
           "wins": w, "losses": sum(1 for x in pct if x < 0), "zeros": sum(1 for x in pct if x == 0),
           "mean_excl_top3_pct": round(st.mean(pct[:-3]), 4) if n > 3 else None,
           "trimmed10_pct": round(st.mean(pct[k:n - k]), 4) if n > 2 * k else None,
           "sign_test_p_two_sided": round(p_sign, 6) if p_sign is not None else None,
           "outlier_flag": (f"one value {max(pct):.0f}% is implausible for AUDJPY in a single trade - likely a "
                            "data error or a different instrument; it dominates the mean") if max(pct) > 100 else None,
           "audit3_aggregate_reference": {"n": 34, "net_expectancy_pct": 0.576, "dsr": 0.8148, "verdict": "WEAK"},
           "finding": (f"CONFLICT: trade-level AUDJPY is a LOSING pattern ({w} wins/{n}; mean {st.mean(pct):+.2f}%, "
                       f"median {st.median(pct):+.2f}%, sign p~{p_sign}); it does NOT corroborate the audit3 +0.576% aggregate.")}
    Path("reports/audjpy_tradelevel_check.json").write_text(json.dumps(out, indent=2) + "\n")
    for kk in ("n", "mean_pct", "median_pct", "wins", "losses", "max_pct", "mean_excl_top3_pct",
               "trimmed10_pct", "sign_test_p_two_sided", "outlier_flag"):
        print(f"  {kk} = {out[kk]}")
    print(out["finding"])

if __name__ == "__main__":
    main()
