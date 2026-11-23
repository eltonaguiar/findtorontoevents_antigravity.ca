#!/usr/bin/env python3
"""Turnover-cost consequence per class, from MEASURED turnover x MEASURED cost.

Feeds the final ranked list (block 1 of the ranked-pick objective).

WHY A SCRIPT AND NOT A TABLE TYPED INTO A DOC
    "Turnover matters" is an assertion. "7.6 round trips/year at 7.53bp = 57bp/yr,
    which is 13% of the 432bp hurdle" is a number somebody can check. Both inputs
    here are measured in this repo:

      turnover/yr  <- reports/cross_class_backtest.json (block 2, identical-criteria
                      grid, top pick per class)
      cost bp      <- reports/equity_cost_hml.json (EQUITY/ETF, n=191) and
                      measured_cost_recost (CRYPTO 12.60, FOREX 7.53 upper bound)
                      COMMODITY/BOND are PROXIES and flagged.

WHAT IT DOES NOT DO
    It does not invent MERs. Mutual-fund/ETF expense ratios are published industry
    figures we have not verified; they are left to the doc, labelled INFO.

Read-only. Not investment advice.

Usage:
    python3 tools/turnover_cost_consequence.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BT = ROOT / "reports" / "cross_class_backtest.json"
OUT = ROOT / "reports" / "turnover_cost_consequence.json"
HURDLE_BP = 432.0


def main() -> int:
    if not BT.exists():
        print(f"::error:: {BT} missing -- run tools/cross_class_momentum_backtest.py")
        return 2
    bt = json.loads(BT.read_text())
    rows = []
    for cls, r in bt.get("classes", {}).items():
        if "turnover_per_year" not in r:
            continue
        cost_bp = r["cost_bp"]
        turn = r["turnover_per_year"]
        drag_bp = turn * cost_bp                 # round trips/yr x bp per round trip
        rows.append({
            "class": cls,
            "instrument": r["instrument"],
            "turnover_round_trips_per_year": turn,
            "cost_bp_per_round_trip": cost_bp,
            "cost_provenance": r["cost_provenance"],
            "annual_drag_bp": round(drag_bp, 2),
            "pct_of_hurdle": round(drag_bp / HURDLE_BP * 100, 2),
            "oos_net_ann": r["oos"].get("ann_return"),
            "net_after_drag_bp": round(
                (r["oos"].get("ann_return") or 0) * 1e4 - 0, 1),
        })
    rows.sort(key=lambda x: -x["annual_drag_bp"])

    out = {"hurdle_bp": HURDLE_BP,
           "note": "drag = turnover(round trips/yr) x round-trip cost(bp); both "
                   "inputs measured, COMMODITY/BOND cost is a flagged PROXY",
           "rows": rows}
    OUT.write_text(json.dumps(out, indent=2))

    print(f"{'CLASS':10} {'turn/yr':>8} {'bp/trip':>8} {'drag bp/yr':>11} "
          f"{'% hurdle':>9}  cost provenance")
    for r in rows:
        print(f"{r['class']:10} {r['turnover_round_trips_per_year']:>8.1f} "
              f"{r['cost_bp_per_round_trip']:>8.2f} {r['annual_drag_bp']:>11.2f} "
              f"{r['pct_of_hurdle']:>8.1f}%  {r['cost_provenance']}")
    print(f"\nwritten: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
