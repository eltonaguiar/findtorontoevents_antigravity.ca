#!/usr/bin/env python3
"""Reconcile every round-trip cost in flight and name ONE cost of record.

Backlog items A1-A4 (docs/BACKLOG_100_2026-11-23.md).

The programme currently carries at least five different equity round-trip costs
simultaneously. A verdict computed at 50bp and a verdict computed at 4.98bp are
not comparable, so "0 of 6 classes survive" is not one statement, it is five
statements wearing one sentence. This tool prints them side by side, marks each
as measured or assumed, and computes which published verdicts would FLIP if the
cost of record changed.

Read-only. Emits reports/cost_of_record_2026-11-23.json + stdout table.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "cost_of_record_2026-11-23.json"

HURDLE_TBILL_BP = 432.0  # 4.32%/yr, tools/capacity_model.py:49

# ---------------------------------------------------------------------------
# Every cost currently used to make a decision, with its provenance.
# verdict_grade=True means a published DEAD/ALIVE was computed with it.
# ---------------------------------------------------------------------------
COSTS_IN_FLIGHT = [
    {
        "id": "questrade_measured",
        "bp_round_trip": 4.98,
        "provenance": "MEASURED (spread only) — tools/equity_cost_hml.py, n=191 names, "
                      "238,810 daily + 356,271 minute bars, Corwin-Schultz 65/191 usable. "
                      "LOWER BOUND: commission/ECN/exchange fields are 0 by construction, "
                      "so 4.98bp excludes any per-trade commission",
        "verdict_grade": False,
        "used_by": "nothing (questrade_canada() has ZERO call sites)",
    },
    {
        "id": "ib_default",
        "bp_round_trip": None,  # computed at runtime
        "provenance": "ASSUMED — CostModel.interactive_brokers() "
                      "(slippage_bps=5, spread_bps=3, exchange_fee_per_share=0.003, "
                      "ecn_fee=0.0035, commission_per_share=0.005); no measurement, no source cited",
        "verdict_grade": True,
        "used_by": "alpha_engine/backtest/engine.py:115 — the PRODUCTION DEFAULT",
    },
    {
        "id": "freebuff_upper_bound",
        "bp_round_trip": 12.0749,
        "provenance": "UPPER BOUND — freebuff, 13 symbols, 1-min bars; author states it is "
                      "superseded for EQUITY by the 191-name measurement",
        "verdict_grade": True,
        "used_by": "zoo notes/zoo-final-2026-11-23 EQUITY DEAD-NOT-REOPENED",
    },
    {
        "id": "zoo_breakout_25bp_per_side",
        "bp_round_trip": 50.0,
        "provenance": "ASSUMED — 'PF 0.9917 @25bp/side' stress case, not a measured cost",
        "verdict_grade": True,
        "used_by": "zoo EQUITY breakout verdict",
    },
    {
        "id": "subq_forex",
        "bp_round_trip": 7.533,
        "provenance": "CLAIMED — reports/fx_meanrev_cost_sweep/sweep.json; not reproduced in "
                      "this session",
        "verdict_grade": True,
        "used_by": "zoo FOREX NOT_INVESTABLE (break-even 4.3038 < cost 7.533)",
    },
]

# Published verdicts whose deciding margin is smaller than the spread between
# the costs above — i.e. verdicts that are COST-SENSITIVE and therefore
# provisional until the cost of record is fixed.
VERDICTS_AT_RISK = [
    {
        "class": "FOREX",
        "strategy": "mean reversion",
        "gross_bp": 4.3038,
        "cost_bp_used": 7.533,
        "published": "NOT_INVESTABLE",
        "source": "reports/fx_meanrev_cost_sweep/sweep.json",
        "note": "break-even cost is 4.3038bp RT; verdict flips to positive if true cost "
                "< 4.3038bp. Cost of record for FX is UNVERIFIED, so this is a "
                "cost-margin kill, not a signal kill.",
    },
    {
        "class": "ETF",
        "strategy": "breakout",
        "gross_bp": 4.7,
        "cost_bp_used": 5.1,
        "published": "no edge found",
        "source": "notes/investment-decision-framework-and-assignments-2026-11-23",
        "note": "margin is 0.4bp — inside the measurement error of any cost estimate.",
    },
    {
        "class": "EQUITY",
        "strategy": "breakout",
        "gross_bp": None,
        "cost_bp_used": 50.0,
        "published": "PF 0.9917 -> DEAD",
        "source": "notes/zoo-final-2026-11-23",
        "note": "PF<1 is a SIGNAL failure and survives any cost change; listed to show "
                "the verdict is cost-robust even though the cost is 10x the measurement.",
    },
]


def _load_costs():
    spec = importlib.util.spec_from_file_location(
        "costs", ROOT / "alpha_engine" / "backtest" / "costs.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["costs"] = m
    spec.loader.exec_module(m)
    return m


def _rt_bp(cm, price: float, shares: int) -> float:
    notional = price * shares
    return cm.compute_round_trip_cost(price, price, shares) / notional * 1e4


def factory_provenance() -> list[dict]:
    """Classify every scalar on every CostModel factory as measured or assumed."""
    m = _load_costs()
    measured_fields = {
        # things this programme actually measured, with the artifact
        "spread_bps": "partly — Questrade 2.385bp from Corwin-Schultz/Roll on 191 names",
        "sec_fee_rate": "yes — SEC statutory 0.0000206",
        "slippage_bps": "partly — Questrade set to 0.0 because spread covers it",
    }
    rows = []
    for name in dir(m.CostModel):
        if name.startswith("_") or not callable(getattr(m.CostModel, name)):
            continue
        try:
            cm = getattr(m.CostModel, name)()
        except TypeError:
            continue
        if not isinstance(cm, m.CostModel):
            continue
        fields = {}
        for f in ("commission_per_share", "min_commission", "slippage_bps",
                  "spread_bps", "exchange_fee_per_share", "ecn_fee", "sec_fee_rate"):
            if hasattr(cm, f):
                fields[f] = {"value": getattr(cm, f),
                             "status": measured_fields.get(f, "ASSUMED")}
        rows.append({"factory": name, "fields": fields,
                     "rt_bp_at_500x100": round(_rt_bp(cm, 500.0, 100), 2)})
    return rows


def main() -> int:
    m = _load_costs()
    ib = m.CostModel.interactive_brokers()

    for c in COSTS_IN_FLIGHT:
        if c["bp_round_trip"] is None:
            c["bp_round_trip"] = round(_rt_bp(ib, 500.0, 100), 2)

    facs = factory_provenance()

    # A3: cost of record. Pick the MEASURED one, and say so out loud.
    measured = [c for c in COSTS_IN_FLIGHT if c["provenance"].startswith("MEASURED")]
    assumed_verdict_grade = [c for c in COSTS_IN_FLIGHT
                             if c["verdict_grade"] and not c["provenance"].startswith("MEASURED")]

    print("=" * 96)
    print("COSTS IN FLIGHT")
    print("=" * 96)
    print(f"{'id':32} {'RT bp':>8} {'verdict-grade':>14}  provenance")
    for c in COSTS_IN_FLIGHT:
        print(f"{c['id']:32} {c['bp_round_trip']:>8.2f} "
              f"{str(c['verdict_grade']):>14}  {c['provenance'][:52]}")

    lo = min(c["bp_round_trip"] for c in COSTS_IN_FLIGHT)
    hi = max(c["bp_round_trip"] for c in COSTS_IN_FLIGHT)
    print(f"\nspread between lowest and highest cost used: {lo:.2f} .. {hi:.2f} bp "
          f"= {hi / lo:.2f}x")

    print("\n" + "=" * 96)
    print("A3 — COST OF RECORD")
    print("=" * 96)
    if measured:
        cor = min(measured, key=lambda c: c["bp_round_trip"])
        print(f"cost of record = {cor['bp_round_trip']:.2f} bp round trip ({cor['id']})")
        print(f"  basis: {cor['provenance']}")
        print(f"  caveat: {cor['used_by']}")
        print("  caveat 2: this is a LOWER BOUND — commission/ECN/exchange fields are 0")
        print("            by construction, so true cost is 4.98bp PLUS any commission")
        # 2x-cost survival must be checked against it
        print(f"  2x-cost stress  = {cor['bp_round_trip'] * 2:.2f} bp")
    print(f"\nverdict-grade costs that are NOT measured: "
          f"{[c['id'] for c in assumed_verdict_grade]}")

    print("\n" + "=" * 96)
    print("A4 — VERDICTS AT RISK (deciding margin < cost uncertainty)")
    print("=" * 96)
    flips = []
    for v in VERDICTS_AT_RISK:
        g, c = v["gross_bp"], v["cost_bp_used"]
        if g is None:
            print(f"{v['class']:9} {v['strategy']:16} {v['published']:14} "
                  f"— not cost-computable: {v['note'][:46]}")
            continue
        net = g - c
        # would it flip if the measured cost of record applied?
        net_at_cor = g - (measured[0]["bp_round_trip"] if measured else c)
        flip = net < 0 < net_at_cor
        if flip:
            flips.append(v["class"])
        print(f"{v['class']:9} {v['strategy']:16} gross {g:6.2f} cost {c:6.2f} "
              f"net {net:+7.2f} | at cost-of-record net {net_at_cor:+7.2f} "
              f"{'<< FLIPS' if flip else ''}")

    print("\n" + "=" * 96)
    print("FACTORY PROVENANCE")
    print("=" * 96)
    for f in facs:
        assumed = sum(1 for v in f["fields"].values() if v["status"] == "ASSUMED")
        print(f"{f['factory']:24} RT {f['rt_bp_at_500x100']:>7.2f} bp  "
              f"{assumed}/{len(f['fields'])} fields ASSUMED")

    payload = {
        "generated": "2026-11-23",
        "hurdle_tbill_bp_per_yr": HURDLE_TBILL_BP,
        "costs_in_flight": COSTS_IN_FLIGHT,
        "cost_spread_ratio": round(hi / lo, 3),
        "cost_of_record": {
            "id": measured[0]["id"] if measured else None,
            "bp_round_trip": measured[0]["bp_round_trip"] if measured else None,
            "two_x_cost_bp": (measured[0]["bp_round_trip"] * 2) if measured else None,
            "reason": "it is the only MEASURED round-trip cost in the programme",
            "caveat": "spread-only measurement; commission/ECN/exchange fields are 0 by "
                      "construction, so 4.98bp is a LOWER bound on true round-trip cost",
        },
        "verdict_grade_costs_not_measured": [c["id"] for c in assumed_verdict_grade],
        "verdicts_at_risk": VERDICTS_AT_RISK,
        "classes_that_flip_at_cost_of_record": flips,
        "factory_provenance": facs,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2))
    print(f"\nwritten: {OUT.relative_to(ROOT)}")
    if flips:
        print(f"\n!! {len(flips)} class(es) flip at the cost of record: {flips}")
        print("   Those verdicts are COST-MARGIN kills, not signal kills, and must be")
        print("   reclassified CANDIDATE-CONDITIONAL until the cost is verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
