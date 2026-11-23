"""How much cost can each class bear, and can this sample even detect the effect it claims?

Three questions, one artifact, because they share the same algebra and answering them apart is
how a programme talks itself into a false positive.

1. COST FLOOR. Each cell has a CI lower bound at 1x cost and at 2x cost. Treating CI-LB as
   locally linear in cost, the multiple k at which it hits zero is

       k* = 1 + CI_LB(1x) / (CI_LB(1x) - CI_LB(2x))

   and the cost floor is base_cost * k*. A cell that only survives because cost is assumed
   away has k* barely above 1; a cell where cost is irrelevant has a delta near zero and k*
   blows up, which is reported as UNBOUNDED rather than as a number.

2. MDE. Minimum detectable effect on the daily mean, at 95% confidence and 80% power:

       MDE = (z95 + z80) * sigma_daily / sqrt(n_days)

   with sigma_daily recovered from the cell's annualised strategy vol. This is the smallest
   true daily edge the sample could have distinguished from zero.

3. REQUIRED N. Inverting (2): how many days would be needed to detect an effect of a given
   size at the same power. Reported for the effect the cell actually claims, and for the
   smallest effect worth trading (one that clears the cash hurdle at 2x cost).

The comparison that matters is MDE against the cell's own CI-LB. When they are the same order,
the "result" is at the detection limit and the honest label is UNDERPOWERED, not significant.

Reads reports/per_class_edge_2026-11-22.json. Writes a JSON artifact and prints a table.

Usage
  python3 tools/per_class_cost_floor.py --out reports/per_class_cost_floor_2026-11-22.json
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

Z_95 = 1.959964
Z_80 = 0.841621
POWER_FACTOR = Z_95 + Z_80          # 2.8016
TRADING_DAYS = 252
TBILL_PCT = 3.5
HURDLE_BP_DAY = TBILL_PCT / 365.0 * 100.0


def cost_floor(ci_lb_1x: float | None, ci_lb_2x: float | None, base_cost: float) -> dict:
    if ci_lb_1x is None or ci_lb_2x is None:
        return {"state": "NO_DATA"}
    delta = ci_lb_1x - ci_lb_2x
    if ci_lb_1x <= 0:
        return {"state": "ALREADY_BELOW_FLOOR", "ci_lb_1x_bps": ci_lb_1x,
                "base_cost_bps": base_cost,
                "reading": "negative at the assumed cost, so no cost floor exists to report"}
    if delta <= 1e-9:
        return {"state": "UNBOUNDED", "ci_lb_1x_bps": ci_lb_1x, "base_cost_bps": base_cost,
                "reading": "doubling cost barely moved the CI lower bound: this cell is not "
                           "paying for its turnover, so it is a hold, not a strategy"}
    k_star = 1.0 + ci_lb_1x / delta
    return {
        "state": "BOUNDED",
        "ci_lb_1x_bps": ci_lb_1x,
        "ci_lb_2x_bps": ci_lb_2x,
        "cost_elasticity_bps_per_x": round(delta, 3),
        "max_cost_multiple": round(k_star, 2),
        "max_roundtrip_bps": round(base_cost * k_star, 1),
        "base_cost_bps": base_cost,
    }


def mde_and_power(strategy_vol_pct: float | None, n_days: int | None,
                  observed_bp_day: float | None) -> dict:
    if not strategy_vol_pct or not n_days or n_days < 2:
        return {"state": "NO_DATA"}
    sigma_daily = (strategy_vol_pct / 100.0) / math.sqrt(TRADING_DAYS)
    mde_bp_day = POWER_FACTOR * sigma_daily / math.sqrt(n_days) * 1e4
    out = {
        "state": "OK",
        "sigma_daily_pct": round(sigma_daily * 100, 4),
        "n_days": int(n_days),
        "mde_bp_day": round(mde_bp_day, 3),
        "yield_required_days": None,
        "yield_required_days_note": None,
    }
    if observed_bp_day is not None:
        # days needed to detect an effect the size of this cell's point estimate
        days_observed = (POWER_FACTOR * sigma_daily * 1e4 / observed_bp_day) ** 2 \
            if observed_bp_day > 0 else None
        out["days_to_detect_observed_effect"] = (
            int(math.ceil(days_observed)) if days_observed else None)
        # days needed to detect a tradable effect: hurdle + 2x cost drag is unavailable here,
        # so the conservative target is twice the cash hurdle
        tradable = 2.0 * HURDLE_BP_DAY
        out["tradable_effect_bp_day"] = round(tradable, 4)
        out["days_to_detect_tradable_effect"] = int(math.ceil(
            (POWER_FACTOR * sigma_daily * 1e4 / tradable) ** 2))
        out["years_to_detect_tradable_effect"] = round(
            out["days_to_detect_tradable_effect"] / TRADING_DAYS, 1)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default="reports/per_class_edge_2026-11-22.json")
    ap.add_argument("--out", default="reports/per_class_cost_floor_2026-11-22.json")
    args = ap.parse_args()

    sweep = json.loads(Path(args.sweep).read_text())
    cost_map = sweep.get("cost_model_bps_round_trip") or {}
    cells = sweep["cells"]

    rows = []
    for c in cells:
        base = cost_map.get(c["asset_class"])
        if base is None:
            base = 10.0
        cf = cost_floor(c.get("boot_ci_lb_bps"), c.get("boot_ci_lb_2x_cost_bps"), float(base))
        mp = mde_and_power(c.get("strategy_vol_pct"), c.get("n_days"), c.get("mean_daily_bps"))
        ci = c.get("boot_ci_lb_bps")
        underpowered = (mp.get("state") == "OK" and ci is not None
                        and ci > 0 and ci < mp["mde_bp_day"])
        rows.append({
            "id": c["id"], "asset_class": c["asset_class"], "name": c["name"],
            "status": c.get("final_status") or c.get("status"),
            "traceable": underpowered,
            "cost_floor": cf,
            "power": mp,
        })

    # per class: the best cell by CI lower bound, and the class-level cost floor.
    # Inadmissible cells are excluded from the "best" vote - picking the highest CI-LB
    # regardless of status would elect a n=13 cell as the class representative, which is the
    # same selection trap the whole programme exists to catch. If nothing admissible remains,
    # the class reports NO_ADMISSIBLE_CELL rather than promoting a cell on a technicality.
    INADMISSIBLE = {"INSUFFICIENT_N", "DATA_INTEGRITY_FAIL"}
    by_class: dict[str, dict] = {}
    seen: dict[str, dict] = {}
    for r in rows:
        cls = r["asset_class"]
        ci = r["cost_floor"].get("ci_lb_1x_bps")
        if ci is None:
            continue
        seen.setdefault(cls, r)
        if r["status"] in INADMISSIBLE:
            continue
        best = by_class.get(cls)
        if best is None or ci > best["cost_floor"]["ci_lb_1x_bps"]:
            by_class[cls] = r
    for cls, r in seen.items():
        if cls not in by_class:
            by_class[cls] = {
                **r,
                "id": f"{r['id']} (no admissible cell)",
                "status": "NO_ADMISSIBLE_CELL",
            }

    class_summary = []
    for cls, r in sorted(by_class.items()):
        class_summary.append({
            "asset_class": cls,
            "best_cell": r["id"],
            "best_status": r["status"],
            "ci_lb_1x_bps": r["cost_floor"]["ci_lb_1x_bps"],
            "cost_floor": r["cost_floor"],
            "admissible_cell": r["status"] != "NO_ADMISSIBLE_CELL",
            "mde_bp_day": r["power"].get("mde_bp_day"),
            "years_to_detect_tradable_effect": r["power"].get(
                "years_to_detect_tradable_effect"),
            "at_detection_limit": r["traceable"],
        })

    out = {
        "generated_by": "tools/per_class_cost_floor.py",
        "question": "how much cost can each class bear, and could this sample have detected "
                    "the effect it claims?",
        "source_sweep": args.sweep,
        "assumptions": {
            "power": "95% confidence, 80% power",
            "power_factor": round(POWER_FACTOR, 4),
            "cost_linearity": "CI-LB treated as locally linear in cost between 1x and 2x",
            "tbill_pct": TBILL_PCT,
            "hurdle_bp_day": round(HURDLE_BP_DAY, 4),
            "tradable_effect_rule": "twice the cash hurdle per day",
        },
        "class_summary": class_summary,
        "cells": rows,
        "headline": {
            "classes_bounded": sum(1 for c in class_summary
                                   if c["cost_floor"].get("state") == "BOUNDED"),
            "classes_unbounded": sum(1 for c in class_summary
                                     if c["cost_floor"].get("state") == "UNBOUNDED"),
            "classes_already_below_floor": sum(
                1 for c in class_summary
                if c["cost_floor"].get("state") == "ALREADY_BELOW_FLOOR"),
            "cells_at_detection_limit": sum(1 for r in rows if r["traceable"]),
            "classes_without_admissible_cell": [c["asset_class"] for c in class_summary
                                                if not c["admissible_cell"]],
        },
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")

    print(f"{'class':<12}{'best cell':<22}{'CI-LB':>8}{'cost floor':>22}{'MDE':>8}"
          f"{'yrs@tradable':>14}")
    for c in class_summary:
        cf = c["cost_floor"]
        floor = (f"{cf['max_roundtrip_bps']:.0f} bp ({cf['max_cost_multiple']:.1f}x)"
                 if cf.get("state") == "BOUNDED" else cf.get("state", "?"))
        mde = f"{c['mde_bp_day']:.2f}" if c["mde_bp_day"] is not None else "n/a"
        yrs = c["years_to_detect_tradable_effect"]
        print(f"{c['asset_class']:<12}{c['best_cell']:<22}{c['ci_lb_1x_bps']:>8.3f}"
              f"{floor:>22}{mde:>8}{str(yrs) if yrs is not None else 'n/a':>14}")

    h = out["headline"]
    print(f"\nclasses: {h['classes_bounded']} bounded, {h['classes_unbounded']} unbounded, "
          f"{h['classes_already_below_floor']} already below floor")
    print(f"cells whose CI-LB is below their own MDE (at detection limit): "
          f"{h['cells_at_detection_limit']}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
