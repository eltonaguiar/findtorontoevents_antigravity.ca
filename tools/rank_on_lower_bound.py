#!/usr/bin/env python3
"""rank_on_lower_bound.py — rank strategies on the 95% LOWER BOUND of net return.

The operator requires ranking on the CI lower bound, not the point estimate. This
bootstrap-resamples each strategy's per-trade pnl from the closed-picks corpus,
subtracts the class round-trip cost (COST_OF_RECORD), and reports the 5th-percentile
(lower-bound) mean. A strategy with LB <= 0 is not rankable for real money.

Source: alpha_engine/data/closed_picks.json (2,204 resolved picks, 61 strategies).
"""
import argparse, json, random, statistics as st
from collections import defaultdict
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.pick_gate import cod_cost_bp  # class-aware COST_OF_RECORD

COST_PCT = {  # round trip in PERCENT (bp/100) by class
    "EQUITY": 0.120749, "ETF": 0.067122, "BOND": 0.006144,
    "FOREX": 0.07533, "CRYPTO": 0.52, "COMMODITY": 0.20,
}


def boot_lb(x, n_boot=4000, seed=7, q=0.025):
    if len(x) < 10:
        return None
    rng = random.Random(seed)
    n = len(x)
    means = []
    for _ in range(n_boot):
        means.append(sum(x[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return means[int(q * n_boot)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="alpha_engine/data/closed_picks.json")
    ap.add_argument("--out", default="reports/lower_bound_ranking.json")
    a = ap.parse_args()
    picks = json.load(open(a.src))
    by = defaultdict(lambda: {"pnl": [], "cls": None, "symbols": set()})
    for r in picks:
        if r.get("pnl_pct") is None:
            continue
        s = r.get("strategy")
        by[s]["pnl"].append(float(r["pnl_pct"]))
        by[s]["cls"] = by[s]["cls"] or r.get("asset_class")
        by[s]["symbols"].add(r.get("symbol"))
    rows = []
    for s, d in by.items():
        x = d["pnl"]
        if len(x) < 10:
            continue
        cost = COST_PCT.get((d["cls"] or "").upper(), 0.52)
        net = [v - cost for v in x]
        lb = boot_lb(net)
        rows.append({"strategy": s, "class": d["cls"], "n": len(x),
                     "n_symbols": len(d["symbols"]),
                     "mean_net_pct": round(st.mean(net), 5),
                     "lb95_net_pct": round(lb, 5) if lb is not None else None,
                     "cost_pct": cost,
                     "rankable": bool(lb is not None and lb > 0)})
    rows.sort(key=lambda r: -(r["lb95_net_pct"] if r["lb95_net_pct"] is not None else -1e9))
    out = {"generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
           "source": a.src, "rule": "rank on 95% bootstrap lower bound of NET return; LB>0 required to rank",
           "n_strategies": len(rows), "n_rankable_lb_positive": sum(1 for r in rows if r["rankable"]),
           "ranking": rows}
    Path(a.out).write_text(json.dumps(out, indent=2) + "\n")
    print(f"{'strategy':38s}{'cls':9s}{'n':>5s}{'meanNet%':>10s}{'LB95%':>10s}{'rank?':>7s}")
    for r in rows[:12]:
        print(f"{str(r['strategy'])[:37]:38s}{str(r['class'])[:8]:9s}{r['n']:5d}{r['mean_net_pct']:10.4f}"
              f"{r['lb95_net_pct'] if r['lb95_net_pct'] is not None else 0:10.4f}{str(r['rankable']):>7s}")
    print(f"\nLB>0 rankable: {out['n_rankable_lb_positive']}/{out['n_strategies']}")
    return 0


if __name__ == "__main__":
    main()
