#!/usr/bin/env python3
"""shrinkage_estimator.py — James-Stein shrinkage on per-strategy/per-symbol means.

The operator's top-gainers brief: "symbol-level ranking is noise at our sample sizes
(50,000 tests -> 2,500 false positives); the escape route is nested/hierarchical
modelling WITH SHRINKAGE, not independent per-symbol searches."

This applies a James-Stein estimator to the REAL dated trades only (entry_date set):
  shrunk_i = grand_mean + (1 - B) * (raw_i - grand_mean)
  B = (k-3) * sigma^2 / sum_i (raw_i - grand_mean)^2      (0<B<1; B=1 = shrink all to mean)
Effect: names with few trades / extreme means are pulled toward the pool mean, so a
'lucky' small-sample winner stops looking like a winner. Reports raw vs shrunk ranks and
how many of the raw top-5 survive.
"""
import argparse, json, statistics as st
from collections import defaultdict
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

COST = {"EQUITY": 0.120749, "ETF": 0.067122, "BOND": 0.006144,
        "FOREX": 0.07533, "CRYPTO": 0.52, "COMMODITY": 0.20}


def load_real(src):
    picks = json.load(open(src))
    return [r for r in picks if r.get("entry_date") and r.get("pnl_pct") is not None]


def group(rows, key):
    g = defaultdict(list)
    for r in rows:
        k = r.get(key)
        if k is None:
            continue
        g[k].append(float(r["pnl_pct"]))
    return g


def shrink(groups):
    items = []
    for k, v in groups.items():
        if len(v) < 3:
            continue
        items.append({"key": k, "n": len(v), "raw_mean": st.mean(v),
                      "sd": st.pstdev(v)})
    if len(items) < 4:
        return items, None
    k = len(items)
    grand = st.mean(it["raw_mean"] for it in items)
    # pooled variance estimate (equal-variance JS); use mean of within-variances
    sigma2 = st.mean((it["sd"] ** 2) / max(1, it["n"]) for it in items)  # var of each mean
    num = (k - 3) * sigma2
    den = sum((it["raw_mean"] - grand) ** 2 for it in items)
    B = min(0.999, max(0.0, num / den)) if den > 0 else 0.999
    for it in items:
        it["shrunk_mean"] = grand + (1 - B) * (it["raw_mean"] - grand)
        it["shrinkage_pct"] = round(100 * B, 2)
    return items, {"k": k, "grand_mean_pct": round(grand, 4), "B": round(B, 4),
                   "shrink_pct": round(100 * B, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="alpha_engine/data/closed_picks.json")
    ap.add_argument("--out", default="reports/shrinkage_estimator.json")
    a = ap.parse_args()
    rows = load_real(a.src)
    out = {"generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
           "source": a.src, "real_dated_rows": len(rows),
           "note": "James-Stein shrinkage on REAL dated trades; raw vs shrunk ranking", "dimensions": {}}
    for dim in ("strategy", "symbol"):
        items, meta = shrink(group(rows, dim))
        items.sort(key=lambda x: -x["raw_mean"])
        raw_top = [it["key"] for it in items[:5]]
        shr = sorted(items, key=lambda x: -x["shrunk_mean"])
        shrunk_top = [it["key"] for it in shr[:5]]
        survived = [t for t in raw_top if t in shrunk_top]
        out["dimensions"][dim] = {"meta": meta, "raw_top5": raw_top, "shrunk_top5": shrunk_top,
                                  "raw_top5_surviving_shrinkage": survived,
                                  "top": [{"key": it["key"], "n": it["n"],
                                           "raw_mean_pct": round(it["raw_mean"], 4),
                                           "shrunk_mean_pct": round(it["shrunk_mean"], 4)} for it in shr[:6]]}
        print(f"=== by {dim} === meta={meta}")
        print("  raw top5:   ", raw_top)
        print("  shrunk top5:", shrunk_top)
        print(f"  raw top5 surviving: {len(survived)}/5 -> {survived}")
        for t in out["dimensions"][dim]["top"]:
            print(f"    {str(t['key'])[:30]:32s} n={t['n']:3d} raw={t['raw_mean_pct']:+.4f}% shrunk={t['shrunk_mean_pct']:+.4f}%")
    Path(a.out).write_text(json.dumps(out, indent=2) + "\n")
    print("\nwrote", a.out)


if __name__ == "__main__":
    main()
