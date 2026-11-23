#!/usr/bin/env python3
"""rank_picks_lower_bound.py — per-INSTRUMENT 95% lower bound, the operator's ranking basis.

Groups the closed-picks corpus by SYMBOL (not strategy), bootstraps the mean net return
(net of the class COST_OF_RECORD), and reports the 2.5th percentile. A symbol is only
'rankable' for real money if its LB > 0. Also cross-references the 69 audit3 ledger
symbols so we can see whether any ranked pick has a positive LB.
"""
import argparse, json, random, statistics as st
from collections import defaultdict
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.pick_gate import cod_cost_bp

COST_PCT = {"EQUITY": 0.120749, "ETF": 0.067122, "BOND": 0.006144,
            "FOREX": 0.07533, "CRYPTO": 0.52, "COMMODITY": 0.20}


def boot_lb(x, n_boot=4000, seed=7, q=0.025):
    if len(x) < 10:
        return None
    rng = random.Random(seed); n = len(x)
    m = sorted(sum(x[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    return m[int(q * n_boot)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="alpha_engine/data/closed_picks.json")
    ap.add_argument("--ledger", default="audit_dashboard/data/audit3_ledger.json")
    ap.add_argument("--out", default="reports/picks_lower_bound_ranking.json")
    a = ap.parse_args()
    picks = json.load(open(a.src))
    by = defaultdict(lambda: {"pnl": [], "cls": None})
    for r in picks:
        if r.get("pnl_pct") is None:
            continue
        s = r.get("symbol")
        by[s]["pnl"].append(float(r["pnl_pct"]))
        by[s]["cls"] = by[s]["cls"] or r.get("asset_class")
    rows = []
    for s, d in by.items():
        x = d["pnl"]
        if len(x) < 10:
            continue
        cls = (d["cls"] or "").upper()
        cost = COST_PCT.get(cls, 0.52)
        net = [v - cost for v in x]
        lb = boot_lb(net)
        rows.append({"symbol": s, "class": d["cls"], "n": len(x),
                     "mean_net_pct": round(st.mean(net), 5),
                     "lb95_net_pct": round(lb, 5) if lb is not None else None,
                     "rankable": bool(lb is not None and lb > 0)})
    rows.sort(key=lambda r: -(r["lb95_net_pct"] if r["lb95_net_pct"] is not None else -1e9))
    # cross-ref ledger symbols
    led = json.load(open(a.ledger))
    led_syms = {s.get("symbol") for s in led.get("symbols", []) if isinstance(s, dict)}
    ranked_syms = {r["symbol"] for r in rows if r["rankable"]}
    overlap_rankable = sorted(ranked_syms & led_syms)
    out = {"generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
           "source": a.src, "rule": "LB95 of net return per SYMBOL; LB>0 required to rank",
           "n_symbols_with_n>=10": len(rows),
           "n_rankable_lb_positive": sum(1 for r in rows if r["rankable"]),
           "ledger_symbols": len(led_syms),
           "ledger_symbols_with_lb_positive": overlap_rankable,
           "ranking": rows}
    Path(a.out).write_text(json.dumps(out, indent=2) + "\n")
    print(f"{'symbol':10s}{'cls':9s}{'n':>5s}{'meanNet%':>10s}{'LB95%':>10s}rank?")
    for r in rows[:12]:
        print(f"{str(r['symbol'])[:9]:10s}{str(r['class'])[:8]:9s}{r['n']:5d}{r['mean_net_pct']:10.4f}"
              f"{r['lb95_net_pct'] if r['lb95_net_pct'] is not None else 0:10.4f}{str(r['rankable']):>6s}")
    print(f"\nLB>0 rankable symbols: {out['n_rankable_lb_positive']}/{out['n_symbols_with_n>=10']}")
    print(f"of the 69 ledger symbols, LB>0: {len(overlap_rankable)} -> {overlap_rankable[:8]}")


if __name__ == "__main__":
    main()
