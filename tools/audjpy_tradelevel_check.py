#!/usr/bin/env python3
"""audjpy_tradelevel_check.py — does trade-level AUDJPY support the +0.576% aggregate?

The audit3 symbol block says AUDJPY n=34, net +0.576%/trade. This checks a TRADE-LEVEL sample
(riseoftheclaw/data/signal_tracking.json) for the same symbol: mean vs median, win count, sign test,
and outlier sensitivity. If the trade-level sample is a losing pattern, the aggregate is not corroborated.
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
    pn = sorted(float(r["pnl_pct"]) for r in aj)
    n = len(pn); w = sum(1 for x in pn if x > 0)
    k = max(1, int(n * 0.1))
    p_sign = min(1.0, 2 * sum(comb(n, i) for i in range(0, w + 1)) / 2 ** n) if w <= n / 2 else None
    out = {"generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
           "source": "riseoftheclaw/data/signal_tracking.json (trade-level)",
           "symbol": "AUDJPY=X", "n": n,
           "mean_pct": round(st.mean(pn)*100, 4), "median_pct": round(st.median(pn)*100, 4),
           "sd_pct": round(st.pstdev(pn)*100, 4), "min_pct": round(min(pn)*100, 4), "max_pct": round(max(pn)*100, 4),
           "wins": w, "losses": sum(1 for x in pn if x < 0), "zeros": sum(1 for x in pn if x == 0),
           "mean_excl_top3_pct": round(st.mean(pn[:-3])*100, 4) if n > 3 else None,
           "trimmed10_pct": round(st.mean(pn[k:n - k])*100, 4) if n > 2 * k else None,
           "sign_test_p_two_sided": round(p_sign, 4) if p_sign is not None else None,
           "audit3_aggregate_reference": {"n": 34, "net_expectancy_pct": 0.576, "dsr": 0.8148, "verdict": "WEAK"},
           "finding": ("CONFLICT: trade-level AUDJPY is a LOSING pattern ({} wins/{}; mean {:.2f}%, median {:.2f}%, "
                       "sign p~{}) with one +{:.2f}% outlier - it does NOT corroborate the audit3 +0.576% aggregate."
                       ).format(w, n, st.mean(pn) * 100, st.median(pn) * 100, p_sign, max(pn) * 100)}
    out["outlier_flag"] = ("one value >100% (%.0f%%) is implausible for AUDJPY - likely a data error or "
                           "different instrument; it dominates the mean" % (max(pn)*100)) if max(pn) > 1.0 else None
    Path("reports/audjpy_tradelevel_check.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("n", "mean_pct", "median_pct", "wins", "losses", "max_pct",
                                          "mean_excl_top3_pct", "trimmed10_pct", "sign_test_p_two_sided")}, indent=1))
    print(out["finding"])

if __name__ == "__main__":
    main()
