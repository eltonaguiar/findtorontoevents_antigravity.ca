#!/usr/bin/env python3
"""Cost-sensitivity analysis: does the cost assumption decide the verdict?

WHY THIS EXISTS
---------------
``tools/equity_cost_hml.py`` measured a **0.98 bp** round-trip cost for liquid US
equities (Corwin-Schultz spread 0.77 bp + SEC 0.21 bp, zero commission/ECN, FX
avoided, 191 names, $20k notional = 0.008% of median ADV). The rest of the repo
charges **5.0 bp** (``alpha_engine/cost_model.py``) or **25.0 bp**
(``pod_equity_breakout_backtest``) — 5x to 25x the measurement.

That raises an uncomfortable question about every KILL verdict in the estate:
were strategies killed by their lack of edge, or by an inflated cost constant?

This module answers it arithmetically instead of by assertion.

THE FLIP BAND
-------------
For a strategy with gross annual edge ``g`` and annual turnover ``T`` (in
round trips per year), the cost drag at ``c`` bp per round trip is::

    drag(c) = T * c / 10000        (as a fraction of capital per year)

So the verdict is cost-SENSITIVE exactly when ``g`` falls between ``drag(c_low)``
and ``drag(c_high)``: below the low assumption the strategy looks profitable,
above the high assumption it looks unprofitable.

Two different questions get conflated in most discussions, so this tool reports
them separately:

  * **sign flip**  -- does ``g - drag(c)`` change sign between c_low and c_high?
  * **verdict flip** -- does the decision against a hurdle change?

A strategy can flip sign and still be killed at both ends. That distinction is
the whole point: it shows whether the cost model is doing the killing.

HONEST READING OF THE MEASUREMENT
---------------------------------
0.98 bp is an optimistic FLOOR, not a universal truth: it assumes patient
execution at the quoted spread, small size, and liquid names. The Roll estimator
on the same data gives 4.77 bp and the high-low bound 209 bp; Corwin-Schultz and
Roll differ by 6x on the same bars. So the defensible position is to treat cost
as an INTERVAL and require an edge to survive the top of it — not to adopt the
lowest estimate and declare the estate profitable.

Paper only, zero capital, not investment advice.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Measured, from reports/equity_cost_hml.json (2026-11-23)
COST_LOW_BP = 0.9756
# Largest constant currently used by a backtest in this repo
COST_HIGH_BP = 25.0


def drag_fraction(turnover_per_year: float, cost_bp: float) -> float:
    """Annual cost drag as a fraction of capital."""
    return turnover_per_year * cost_bp / 10000.0


#: A strategy earns a cost-headroom pass only when the cost at which its net
#: return reaches zero is above the worst cost constant any backtest in this repo
#: charges. Otherwise the downside cost case can still kill it.
COST_HEADROOM_RULE = "breakeven_cost_bp > cost_high_bp"


def cost_headroom_gate(breakeven_cost_bp, cost_high_bp: float = COST_HIGH_BP) -> dict:
    """Evaluate ``breakeven_cost_bp > cost_high_bp`` as a gate.

    Returns a dict with ``status`` in {PASS, FAIL, UNKNOWN}. The comparison is
    strict, so a breakeven exactly equal to the high constant FAILS: it survives
    only by assuming the pessimistic case is never reached.

    ``UNKNOWN`` is returned when breakeven is undefined (zero turnover). That is
    not a pass and not a fail -- with no turnover there is no cost drag, so the
    cost constant cannot bind and the rule has nothing to say.

    NOTE: this gate is deliberately *not* wired into pick promotion. Turning a
    FAIL into an automatic demotion would silently reclassify live strategies, so
    that step is left to an explicit owner decision. The gate is exposed as a
    computed field and as `--gate` (non-zero exit) so it can be enforced where
    somebody chooses to enforce it.
    """
    if breakeven_cost_bp is None:
        return {
            "rule": COST_HEADROOM_RULE,
            "status": "UNKNOWN",
            "breakeven_cost_bp": None,
            "cost_high_bp": round(cost_high_bp, 4),
            "headroom_bp": None,
            "reason": ("breakeven cost is undefined (zero turnover); with no turnover "
                       "there is no cost drag, so the cost constant cannot bind"),
        }

    headroom = float(breakeven_cost_bp) - float(cost_high_bp)
    passed = float(breakeven_cost_bp) > float(cost_high_bp)
    return {
        "rule": COST_HEADROOM_RULE,
        "status": "PASS" if passed else "FAIL",
        "breakeven_cost_bp": round(float(breakeven_cost_bp), 4),
        "cost_high_bp": round(float(cost_high_bp), 4),
        "headroom_bp": round(headroom, 4),
        "reason": (
            f"breakeven {breakeven_cost_bp:.4f} bp is above the worst cost assumption "
            f"{cost_high_bp:.4f} bp, so even the pessimistic case leaves net positive"
            if passed else
            f"breakeven {breakeven_cost_bp:.4f} bp is at or below the worst cost "
            f"assumption {cost_high_bp:.4f} bp, so that case can wipe out the edge"
        ),
    }


def analyse(gross_ann: float, turnover_per_year: float, hurdle_ann: float,
            cost_low_bp: float = COST_LOW_BP, cost_high_bp: float = COST_HIGH_BP) -> dict:
    """Compare a strategy's verdict under the measured cost and the repo constant."""
    lo_drag = drag_fraction(turnover_per_year, cost_low_bp)
    hi_drag = drag_fraction(turnover_per_year, cost_high_bp)

    lo_net = gross_ann - lo_drag
    hi_net = gross_ann - hi_drag

    sign_flip = (lo_net > 0) != (hi_net > 0)
    verdict_low = "PASS" if lo_net > hurdle_ann else "KILL"
    verdict_high = "PASS" if hi_net > hurdle_ann else "KILL"
    verdict_flip = verdict_low != verdict_high

    # cost at which net flips sign (breakeven cost)
    breakeven_bp = (gross_ann * 10000.0 / turnover_per_year) if turnover_per_year else None
    # cost at which the hurdle is exactly met
    hurdle_cost_bp = ((gross_ann - hurdle_ann) * 10000.0 / turnover_per_year) \
        if turnover_per_year else None

    if verdict_flip:
        assessment = "COST-DECIDED"
    elif verdict_low == "KILL":
        # killed even at the optimistic cost -> the cost model is NOT the killer
        assessment = "ROBUSTLY-KILLED"
    else:
        assessment = "ROBUSTLY-PASSES"

    return {
        "inputs": {
            "gross_ann": gross_ann,
            "turnover_per_year": turnover_per_year,
            "hurdle_ann": hurdle_ann,
            "cost_low_bp": cost_low_bp,
            "cost_high_bp": cost_high_bp,
        },
        "at_measured_cost": {
            "cost_bp": round(cost_low_bp, 4),
            "drag_ann": round(lo_drag, 8),
            "net_ann": round(lo_net, 8),
            "verdict": verdict_low,
        },
        "at_repo_constant": {
            "cost_bp": round(cost_high_bp, 4),
            "drag_ann": round(hi_drag, 8),
            "net_ann": round(hi_net, 8),
            "verdict": verdict_high,
        },
        "sign_flip": sign_flip,
        "verdict_flip": verdict_flip,
        "breakeven_cost_bp": None if breakeven_bp is None else round(breakeven_bp, 4),
        "breakeven_vs_hurdle_cost_bp": None if hurdle_cost_bp is None else round(hurdle_cost_bp, 4),
        "cost_headroom_gate": cost_headroom_gate(breakeven_bp, cost_high_bp),
        "assessment": assessment,
        "interpretation": _interpret(assessment, sign_flip, gross_ann, hurdle_ann,
                                     breakeven_bp, cost_low_bp, cost_high_bp),
    }


def _interpret(assessment: str, sign_flip: bool, gross_ann: float, hurdle_ann: float,
               breakeven_bp, cost_low_bp: float, cost_high_bp: float) -> str:
    if assessment == "ROBUSTLY-KILLED":
        return ("Killed at BOTH cost levels, so the inflated cost constant is not what "
                f"rejected this. At the measured {cost_low_bp:.2f} bp it still falls short of "
                f"the {hurdle_ann:.2%} hurdle. The cost finding does not reopen this verdict.")
    if assessment == "COST-DECIDED":
        return ("The verdict FLIPS between the cost assumptions, so the cost constant is "
                "doing the deciding. Neither answer can be trusted until the execution "
                "assumption is pinned down.")
    if sign_flip:
        return ("The SIGN of net return flips between cost assumptions, but the verdict does "
                "not, because the hurdle is far away. Report the interval, not a point.")
    return "Passes at both cost levels with margin; not cost-sensitive."


def hml_case() -> dict:
    """Run the analysis on the HML record from reports/hml_result.json."""
    path = REPO_ROOT / "reports/hml_result.json"
    if not path.exists():
        raise SystemExit("reports/hml_result.json missing; run tools/hml_pit_backtest.py first")
    d = json.loads(path.read_text())
    res, cost, rule = d["result"], d["cost"], d["rule"]
    turnover_per_year = res["avg_turnover"] * 12.0  # monthly rebalance
    # The measured total is the Corwin-Schultz spread PLUS the SEC fee; using the
    # spread alone would understate the low arm and flatter the strategy.
    measured_total_bp = COST_LOW_BP
    if cost.get("cs"):
        measured_total_bp = float(cost["cs"]) + float(cost.get("sec_bp") or 0.0)
    out = analyse(
        gross_ann=res["gross_ann"],
        turnover_per_year=turnover_per_year,
        hurdle_ann=rule["hurdle_annual"],
        cost_low_bp=measured_total_bp,
        cost_high_bp=COST_HIGH_BP,
    )
    out["source"] = "reports/hml_result.json"
    out["recorded_cost_bp"] = cost["round_trip_bp_used"]
    out["recorded_verdict"] = rule["verdict"]
    out["low_arm_definition"] = (f"Corwin-Schultz spread {cost.get('cs')} bp + SEC "
                                 f"{cost.get('sec_bp')} bp = {measured_total_bp:.4f} bp")
    out["note"] = ("The HML backtest used the Roll estimator (4.97 bp). Here the low arm "
                   "switches to the measured Corwin-Schultz spread + SEC fee to show what "
                   "the cheapest defensible assumption would do.")
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hml", action="store_true", help="analyse the recorded HML result")
    ap.add_argument("--gross-ann", type=float, help="gross annual return, e.g. 0.00109")
    ap.add_argument("--turnover-per-year", type=float,
                    help="round trips per year, e.g. 1.77 (0.1475 turnover x 12 rebalances)")
    ap.add_argument("--hurdle-ann", type=float, default=0.0432)
    ap.add_argument("--cost-low-bp", type=float, default=COST_LOW_BP)
    ap.add_argument("--cost-high-bp", type=float, default=COST_HIGH_BP)
    ap.add_argument("--out", default="reports/cost_sensitivity_2026-11-23.json")
    ap.add_argument("--gate", action="store_true",
                    help="exit non-zero when the cost-headroom gate does not PASS")
    args = ap.parse_args(argv[1:])

    if args.hml:
        out = hml_case()
    elif args.gross_ann is not None and args.turnover_per_year is not None:
        out = analyse(args.gross_ann, args.turnover_per_year, args.hurdle_ann,
                      args.cost_low_bp, args.cost_high_bp)
    else:
        ap.error("give --hml, or both --gross-ann and --turnover-per-year")

    dest = REPO_ROOT / args.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1) + "\n")

    i = out["inputs"]
    print(f"gross {i['gross_ann']:.5f}/yr · turnover {i['turnover_per_year']:.3f} RT/yr "
          f"· hurdle {i['hurdle_ann']:.2%}")
    for label, arm in (("measured cost", out["at_measured_cost"]),
                       ("repo constant", out["at_repo_constant"])):
        print(f"  {label:<16} {arm['cost_bp']:>7.4f} bp  drag {arm['drag_ann']:.5f}  "
              f"net {arm['net_ann']:+.5f}  -> {arm['verdict']}")
    print(f"  sign flip        {out['sign_flip']}")
    print(f"  verdict flip     {out['verdict_flip']}")
    print(f"  breakeven cost   {out['breakeven_cost_bp']} bp")
    gate = out.get("cost_headroom_gate") or {}
    if gate:
        print(f"  cost headroom    {gate['status']}  ({gate['rule']})")
        print(f"                   {gate['reason']}")
    print(f"  ASSESSMENT       {out['assessment']}")
    print(f"  {out['interpretation']}")
    print(f"  written          {args.out}")
    if args.gate and gate.get("status") != "PASS":
        print(f"  GATE FAILED      {gate.get('status')}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
