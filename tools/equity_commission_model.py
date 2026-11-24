"""Equity commission is modelled from published schedules, NOT measured.

The fleet labels equity commission `COMMISSION_UNKNOWN` and the H-201 pod charges
`commission_bp_per_side: 1` as an assumption. This tool does not turn that assumption into a
measurement -- nothing in this repo has broker fills, and no fill has a commission field to
read. What it does is make the assumption *checkable*: it computes commission in basis points
from published per-share schedules across the ticket sizes a 3-name pod actually trades, so a
reader can see where 1 bp/side is adequate and where it is not.

The answer is not uniform, which is the point. Per-share pricing has a MINIMUM ticket fee, and a
minimum fee is not scale-invariant: on a $1,000 ticket the floor alone can be 10 bp, while on a
$25,000 ticket the same floor is 0.4 bp. A single scalar "1 bp" is therefore either conservative
or materially optimistic depending on position size -- and the pod never states its position
size, so the assumption is unfalsifiable as written. That is the finding.

Schedules are the published retail tiers; they are inputs, not observations. Every output is
labelled `MODEL` and must never be reported as a measured cost.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "equity_commission_model_20261123.json"

# Published retail schedules, per share, with the ticket floor and the 1%-of-trade cap that both
# bind at the small and large ends respectively.
SCHEDULES = {
    "IBKR_FIXED": {"per_share": 0.005, "min_ticket": 1.00, "max_pct_of_trade": 0.01,
                   "note": "flat $0.005/share, $1.00 minimum, 1% maximum"},
    "IBKR_TIERED": {"per_share": 0.0035, "min_ticket": 0.35, "max_pct_of_trade": 0.01,
                    "note": "$0.0035/share + exchange fees, $0.35 minimum"},
    "ZERO_COMMISSION_RETAIL": {"per_share": 0.0, "min_ticket": 0.0, "max_pct_of_trade": 0.0,
                               "note": "advertised $0; payment-for-order-flow cost arrives as "
                                       "spread/price improvement, i.e. inside the measured "
                                       "spread, not as a line item"},
}

NOTIONALS = [1_000, 2_500, 5_000, 10_000, 25_000]
PRICES = [10.0, 25.0, 50.0, 100.0, 250.0, 500.0]


def commission_bp(schedule: dict, notional: float, price: float) -> float:
    """Commission in bp of notional for one side of one ticket."""
    shares = notional / price
    fee = shares * schedule["per_share"]
    if schedule["min_ticket"]:
        fee = max(fee, schedule["min_ticket"])
    if schedule["max_pct_of_trade"]:
        fee = min(fee, notional * schedule["max_pct_of_trade"])
    return 1e4 * fee / notional


def main() -> int:
    cells = []
    for name, sch in SCHEDULES.items():
        for n in NOTIONALS:
            for p in PRICES:
                cells.append({"schedule": name, "notional_usd": n, "price_usd": p,
                              "shares": round(n / p, 4),
                              "commission_bp_per_side": round(commission_bp(sch, n, p), 4)})

    # Where does the pod's own 1 bp/side assumption sit?
    assumed = 1.0
    by_sched = {}
    for name in SCHEDULES:
        vals = [c["commission_bp_per_side"] for c in cells if c["schedule"] == name]
        by_sched[name] = {
            "min_bp": min(vals), "max_bp": max(vals),
            "median_bp": round(sorted(vals)[len(vals) // 2], 4),
            "cells_at_or_below_1bp": sum(1 for v in vals if v <= assumed),
            "cells_above_1bp": sum(1 for v in vals if v > assumed),
            "n_cells": len(vals),
        }

    # The floor alone, which is what actually binds on small tickets.
    floor_bp = {}
    for name, sch in SCHEDULES.items():
        if sch["min_ticket"]:
            floor_bp[name] = {f"{n}": round(1e4 * sch["min_ticket"] / n, 3) for n in NOTIONALS}

    verdicts = {
        "is_this_a_measurement": False,
        "what_it_is": "MODEL built from published per-share schedules",
        "assumption_under_test_bp_per_side": assumed,
        "finding": (
            "1 bp/side is adequate only on larger tickets and only for per-share pricing above "
            "its floor: at $10,000 the IBKR_FIXED floor is 1.0 bp and at $25,000 it is 0.4 bp, "
            "but at $1,000 the floor alone is 10 bp and at $2,500 it is 4 bp. A single scalar "
            "cannot describe all of those, so the pod's cost basis is broker- and "
            "ticket-size-dependent rather than unknown."
        ),
        "consequence_for_the_pod": (
            "On a $1,000-$2,500 ticket the 11 bp/side assumption (10 slip + 1 commission) may "
            "UNDERSTATE commission by 3-9 bp. On $10,000+ tickets it holds. Since the pod has no "
            "declared position size, its cost basis must state the ticket size assumption or the "
            "figure is not reproducible."
        ),
        "what_would_make_it_a_measurement": (
            "Broker fills with a commission field, or a statement reconciliation. Neither exists "
            "in this repo; the paper-trading surfaces record prices, not fees."
        ),
        "do_not_report_as": "measured equity cost",
    }

    payload = {
        "generated_utc": "2026-11-23",
        "tool": "tools/equity_commission_model.py",
        "label": "MODEL_NOT_MEASURED",
        "schedules": SCHEDULES,
        "notionals_usd": NOTIONALS,
        "prices_usd": PRICES,
        "summary_by_schedule": by_sched,
        "minimum_ticket_floor_bp": floor_bp,
        "verdicts": verdicts,
        "cells": cells,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1))

    print(f"{len(cells)} cells -> {OUT.relative_to(ROOT)}")
    for name, s in by_sched.items():
        print(f"  {name:24s} bp/side {s['min_bp']:.3f}..{s['max_bp']:.3f} "
              f"median {s['median_bp']:.3f}  <=1bp: {s['cells_at_or_below_1bp']}/{s['n_cells']}")
    print("\nminimum ticket floor, bp of notional:")
    for name, d in floor_bp.items():
        print(f"  {name:24s} " + "  ".join(f"${k}:{v}bp" for k, v in d.items()))
    print(f"\nverdict: {verdicts['finding']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
