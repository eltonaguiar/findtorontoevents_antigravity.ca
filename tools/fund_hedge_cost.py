#!/usr/bin/env python3
"""Measure the CAD-hedging carry instead of assuming it (backlog H006).

Elsewhere the cost of hedging USD exposure to CAD was an ASSUMED carry parameter
(-1.0%/yr). The assumption is removable: hold the SAME index in a hedged and an
unhedged TSX-listed wrapper and difference them. Both are CAD-priced and both
hold the same underlying, so the gap isolates what the hedge did.

    gap        = unhedged net CAGR - hedged net CAGR
    fx_effect  = measured USD/CAD effect on an unhedged USD asset (from
                 fund_cad_view.json: +2.59%/yr over this window)
    residual   = gap - fx_effect
               = cost of hedging + the fee differential between the two wrappers

The residual is NOT purely hedging cost, because the hedged wrappers also charge
more (VSP ~0.39%, XSP ~0.42% against VFV/ZSP ~0.09%). Those MERs are QUOTED, not
fetched, so they are separated out and labelled rather than folded in silently.

One window, one rate path. CAD weakened over it, which flatters the unhedged
side; a reversal would flatter the hedged side by a similar amount. Nothing here
predicts FX.

    python3 tools/fund_hedge_cost.py --json reports/fund_hedge_cost.json
"""
import argparse
import json
import math
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
START, END = "2021-11-15", "2026-11-15"
ANN = 252

# ticker -> (label, quoted MER%, kind)
FUNDS = {
    "VFV.TO": ("Vanguard S&P 500 CAD unhedged", 0.09, "unhedged"),
    "ZSP.TO": ("BMO S&P 500 CAD unhedged", 0.09, "unhedged"),
    "VSP.TO": ("Vanguard S&P 500 CAD HEDGED", 0.39, "hedged"),
    "XSP.TO": ("iShares S&P 500 CAD HEDGED", 0.42, "hedged"),
}
PRIOR_ASSUMPTION_PP = 1.0   # the -1.0%/yr carry the report previously assumed


def stats(ret, mer_pct):
    n = len(ret)
    nav = 1.0
    for r in ret:
        nav *= 1 + r
    gross = nav ** (ANN / n) - 1
    net = (1 + gross) * (1 - mer_pct / 100.0) - 1
    vol = st.stdev(ret) * math.sqrt(ANN)
    return {"gross_cagr_pct": round(gross * 100, 3),
            "net_cagr_pct": round(net * 100, 3),
            "vol_pct": round(vol * 100, 3), "n": n}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)

    import yfinance as yf  # noqa: PLC0415

    rows = {}
    for t in FUNDS:
        h = yf.Ticker(t).history(start=START, end=END)
        if not len(h):
            print(f"  {t}: no data, aborting")
            return 1
        s = [float(v) for v in h["Close"]]
        rows[t] = stats([s[i] / s[i - 1] - 1 for i in range(1, len(s))], FUNDS[t][1])

    cv = REPO_ROOT / "reports" / "fund_cad_view.json"
    fx_effect = None
    if cv.exists():
        fx_effect = json.loads(cv.read_text())["fx_cagr_pct"]

    print(f"  {'ticker':8s}{'kind':10s}{'MER':>7s}{'gross':>9s}{'net':>9s}{'vol':>8s}")
    for t, m in rows.items():
        print(f"  {t:8s}{FUNDS[t][2]:10s}{FUNDS[t][1]:7.2f}"
              f"{m['gross_cagr_pct']:9.2f}{m['net_cagr_pct']:9.2f}{m['vol_pct']:8.2f}")

    payload = {"fetched_at": datetime.now(timezone.utc).isoformat(),
               "period": [START, END], "source": "yfinance (TSX-listed, CAD)",
               "quoted_mers_pct": {t: FUNDS[t][1] for t in FUNDS},
               "mers_verified": False, "funds": rows,
               "measured_fx_effect_pct": fx_effect,
               "prior_assumption_pct": PRIOR_ASSUMPTION_PP,
               "pairs": {}}

    print()
    for un, hd in (("VFV.TO", "VSP.TO"), ("ZSP.TO", "XSP.TO")):
        gap = rows[un]["net_cagr_pct"] - rows[hd]["net_cagr_pct"]
        mer_diff = FUNDS[hd][1] - FUNDS[un][1]
        hedge = gap - (fx_effect or 0.0) - mer_diff
        payload["pairs"][f"{un} vs {hd}"] = {
            "gap_pp": round(gap, 3), "fx_effect_pp": fx_effect,
            "mer_diff_pp": round(mer_diff, 3),
            "hedge_cost_pp": round(hedge, 3),
            "prior_assumption_pp": PRIOR_ASSUMPTION_PP,
            "understated_by_pp": round(hedge - PRIOR_ASSUMPTION_PP, 3),
        }
        print(f"  {un} - {hd}: gap {gap:+.2f}pp  - fx {fx_effect:+.2f}  "
              f"- MER diff {mer_diff:+.2f}  => hedge cost {hedge:.2f}pp/yr")
        print(f"    prior assumption was {PRIOR_ASSUMPTION_PP:.2f}pp/yr "
              f"-> understated by {hedge - PRIOR_ASSUMPTION_PP:+.2f}pp")

    print("\n  Caveat: one window with a falling CAD favours the unhedged side.")
    print("  A reversal would favour the hedged side by a comparable amount.")
    print("  MERs are QUOTED, not fetched (mers_verified=false).")

    if args.json:
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
