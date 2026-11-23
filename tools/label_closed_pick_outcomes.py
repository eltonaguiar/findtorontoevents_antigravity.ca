#!/usr/bin/env python3
"""label_closed_pick_outcomes.py — classify every closed pick REALISED vs WOULD_HIT.

Defect (2026-11-23): alpha_engine/data/closed_picks.json mixes real fills with placeholder
rows whose pnl_pct is quantised to the take-profit/stop-loss barrier and whose entry_date
is null. Downstream DSR/edge must use REALISED rows only.

A row is REALISED when it has an entry_date (a dated trade). Otherwise it is WOULD_HIT
(placeholder). Emits counts per strategy and per symbol so callers can filter, and the
list of TP-like values observed among WOULD_HIT rows.
"""
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path

BARRIER_VALUES = (-5.0, -3.75, -3.0, -2.7, -2.5, -2.0, 2.0, 2.5, 2.7, 3.0, 3.75, 5.0)  # observed exact TP/SL quantisations


def basis(r):
    return "REALISED" if r.get("entry_date") else "WOULD_HIT"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="alpha_engine/data/closed_picks.json")
    ap.add_argument("--out", default="reports/closed_picks_outcome_basis.json")
    a = ap.parse_args()
    picks = json.load(open(a.src))
    per_strategy = defaultdict(lambda: Counter())
    per_symbol = defaultdict(lambda: Counter())
    wh_vals = Counter()
    for r in picks:
        b = basis(r)
        per_strategy[r.get("strategy")][b] += 1
        per_symbol[r.get("symbol")][b] += 1
        if b == "WOULD_HIT" and r.get("pnl_pct") is not None:
            wh_vals[round(float(r["pnl_pct"]), 2)] += 1
    tot = Counter(basis(r) for r in picks)
    on_barrier = sum(v for k, v in wh_vals.items() if k in BARRIER_VALUES)
    out = {"generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
           "source": a.src, "total": len(picks),
           "REALISED": tot["REALISED"], "WOULD_HIT": tot["WOULD_HIT"],
           "would_hit_on_barrier": on_barrier,
           "would_hit_pct_on_barrier": round(100.0 * on_barrier / max(1, tot["WOULD_HIT"]), 2),
           "would_hit_top_values": dict(wh_vals.most_common(8)),
           "per_strategy": {k: dict(v) for k, v in per_strategy.items()},
           "per_symbol": {k: dict(v) for k, v in per_symbol.items()},
           "usage": "FILTER to REALISED (entry_date non-null) before any DSR/edge/hit-rate computation"}
    Path(a.out).write_text(json.dumps(out, indent=2) + "\n")
    print(f"total {out['total']} | REALISED {out['REALISED']} | WOULD_HIT {out['WOULD_HIT']} "
          f"({out['would_hit_pct_on_barrier']}% of WOULD_HIT sit on an exact barrier)")
    print("top WOULD_HIT values:", out["would_hit_top_values"])
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
