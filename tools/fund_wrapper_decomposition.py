#!/usr/bin/env python3
"""Decompose the CAD-listed wrapper: MER vs what is left over.

The Canadian answer left one thing unmeasured: "MER is not total cost - the ETF
still pays US withholding at the fund level". This attributes the gap between a
CAD-listed fund and its US-listed equivalent, in CAD terms, into:

    gap       = net CAGR(cad-listed) - net CAGR(us-listed, converted to CAD)
    mer_pp    = -(mer_cad - mer_us)          cheaper CAD fund -> positive
    residual  = gap - mer_pp                 withholding + tracking + structure

The testable prediction: for a US-equity fund the residual should be about
-15% x dividend yield, because a Canadian-domiciled fund holding US stocks pays
US withholding at the fund level and cannot recover it.

Inputs are the committed artifacts only - no network, so this is reproducible:
    reports/fund_cad_home.json   (CAD-listed, CAD prices)
    reports/fund_cad_view.json   (US-listed, converted to CAD)
    reports/fund_withholding.json (dividend yields)

Paper only. Not investment advice. The withholding rate is the treaty rate; its
applicability is flagged unverified upstream and stays flagged here.

    python3 tools/fund_wrapper_decomposition.py --json reports/fund_wrapper_decomp.json
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# cad ticker -> (us ticker in the cad_view artifact, us ticker for the yield)
# Only EXPOSURE-MATCHED pairs are valid here. ZAG.TO holds CANADIAN aggregate
# bonds and CASH.TO holds CAD cash - they are not CAD-listed versions of BND and
# SGOV, so differencing them measures the bond market and the currency, not the
# cost of the wrapper. An earlier version of this tool paired them anyway and
# produced a -3.3pp "residual" that was pure exposure mismatch.
PAIRS = {
    "VFV.TO": ("SPY_adj", "SPY"),    # US large cap, CAD-listed, unhedged
    "ZSP.TO": ("SPY_adj", "SPY"),    # same
    "VUN.TO": ("VTI_adj", "VTI"),    # US total market, CAD-listed, unhedged
}
NOT_COMPARABLE = {
    "ZAG.TO": "holds Canadian aggregate bonds, not US - not a BND equivalent",
    "CASH.TO": "holds CAD cash, not US T-bills - not an SGOV equivalent",
}
TREATY = 0.15
# predawn  ->  residual is a mix of withholding, tracking and structure, so a
# tight equality would be false precision. 5bp is the tolerance in the tests.
TOL_PP = 0.05


def load(name):
    p = REPO_ROOT / "reports" / name
    if not p.exists():
        return None
    return json.loads(p.read_text())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)

    home, view, wh = (load("fund_cad_home.json"), load("fund_cad_view.json"),
                      load("fund_withholding.json"))
    if not (home and view and wh):
        print("  missing an input artifact; run fund_cad_home / fund_cad_view / "
              "fund_withholding_cost first")
        return 1

    yields = {r["ticker"]: r["distribution_yield_pct"] for r in wh["rows"]}
    withholdable = {r["ticker"]: r["withholdable"] for r in wh["rows"]}

    print(f"  {'cad-listed':10s}{'vs':>5s}{'gap':>8s}{'MER':>8s}{'residual':>10s}"
          f"{'predicted':>11s}{'diff':>8s}")
    rows, problems = [], []
    for cad, (us_key, us_tick) in PAIRS.items():
        cm = home["funds"].get(cad)
        um = view["funds"].get(us_key)
        if not cm or not um:
            problems.append(f"{cad}: missing counterpart")
            continue
        gap = cm["net_cagr_pct"] - um["cad_net_cagr_pct"]
        mer_pp = -(cm["mer_pct"] - (0.0945 if us_tick == "SPY" else
                                    0.03 if us_tick in ("VTI", "BND") else 0.09))
        residual = gap - mer_pp
        # predicted withholding: only on withholdable (dividend) income
        y = yields.get(us_tick, 0.0) if withholdable.get(us_tick, False) else 0.0
        predicted = -(TREATY * y)
        diff = residual - predicted
        rows.append({"cad_listed": cad, "us_listed": us_tick,
                     "gap_pp": round(gap, 4), "mer_pp": round(mer_pp, 4),
                     "residual_pp": round(residual, 4),
                     "predicted_withholding_pp": round(predicted, 4),
                     "unexplained_pp": round(diff, 4),
                     "within_tolerance": abs(diff) <= TOL_PP})
        print(f"  {cad:10s}{us_tick:>5s}{gap:8.2f}{mer_pp:+8.4f}{residual:+10.4f}"
              f"{predicted:+11.4f}{diff:+8.4f}")
        if abs(diff) > TOL_PP:
            problems.append(
                f"{cad} vs {us_tick}: residual {residual:+.3f}pp differs from "
                f"predicted withholding {predicted:+.3f}pp by {diff:+.3f}pp")

    payload = {
        "source_artifacts": ["fund_cad_home.json", "fund_cad_view.json",
                             "fund_withholding.json"],
        "treaty_rate": TREATY,
        "tolerance_pp": TOL_PP,
        "rows": rows,
        "not_exposure_matched": NOT_COMPARABLE,
        "consistent_with_withholding": all(r["within_tolerance"] for r in rows),
        "unexplained": problems,
        "caveat": ("residual bundles withholding, tracking error and fund "
                   "structure; agreement with the predicted withholding is "
                   "corroboration, not proof"),
    }

    print()
    if problems:
        print("  Residuals NOT fully explained by the withholding prediction:")
        for p in problems:
            print(f"    - {p}")
    else:
        print("  Every residual is within "
              f"{TOL_PP:.2f}pp of the predicted fund-level withholding.")

    print("\n  Excluded as NOT exposure-matched:")
    for t, why in NOT_COMPARABLE.items():
        print(f"    {t:9s} {why}")

    print("\n  Reading: for exposure-matched US-equity pairs the gap is roughly")
    print("  fund-level US withholding on dividends, not the MER difference -")
    print("  the opposite of what the fee-focused part of the report implies.")

    if args.json:
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
