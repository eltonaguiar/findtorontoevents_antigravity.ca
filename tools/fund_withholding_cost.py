#!/usr/bin/env python3
"""US withholding cost for a Canadian holder, to size it against the fee edge.

The report debates a 0.0795pp/yr fee difference for most of its length while the
withholding question was left as an unverified paragraph. It is arithmetic, so
size it.

Scope of the tax, stated carefully
---------------------------------
* US-source DIVIDENDS paid to a Canadian resident: 30% statutory, 15% under the
  Canada-US treaty with a valid W-8BEN; an RRSP is generally exempt.
* US-source INTEREST (portfolio interest) paid to a non-resident: generally
  exempt from US withholding. So bond and T-bill distributions are mostly NOT
  hit, which means quoting a single "withholding cost" for a 60/40 is wrong --
  it depends on the sleeve's income character.

Everything below is an ESTIMATE built from each fund's trailing distribution
yield, applied only to the equity sleeves. It is not tax advice and the tax
treatment is flagged unverified; the point is the ORDER OF MAGNITUDE relative to
a 0.0795pp fee edge, which is what the decision turns on.

    python3 tools/fund_withholding_cost.py --json reports/fund_withholding.json
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# income character decides whether withholding applies at all
CHARACTER = {
    "SPY": "equity_dividend",
    "VTI": "equity_dividend",
    "VEA": "equity_dividend",
    "BND": "bond_interest",
    "SGOV": "tbill_interest",
}
TICKERS = list(CHARACTER)
STATUTORY = 0.30
TREATY = 0.15          # Canada-US, with W-8BEN
FEE_EDGE_PP = 0.0795   # FXAIX vs SPY, from the report


def fetch_yields():
    import yfinance as yf  # noqa: PLC0415

    out = {}
    for t in TICKERS:
        try:
            info = yf.Ticker(t).info or {}
        except Exception:  # noqa: BLE001
            continue
        y = info.get("dividendYield") or info.get("yield")
        if y:
            try:
                out[t] = float(y)          # already a percentage here
            except (TypeError, ValueError):
                pass
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)

    yields = fetch_yields()
    if not yields:
        print("  yield data unavailable; refusing to estimate")
        return 1

    # withholdable yield = distribution yield, but ONLY for equity dividends
    rows = []
    for t in TICKERS:
        if t not in yields:
            continue
        y = yields[t]
        kind = CHARACTER[t]
        withholdable = kind == "equity_dividend"
        drag_treaty = (TREATY * y) if withholdable else 0.0
        drag_stat = (STATUTORY * y) if withholdable else 0.0
        rows.append({
            "ticker": t, "income_character": kind,
            "distribution_yield_pct": round(y, 3),
            "withholdable": withholdable,
            "tfsa_or_taxable_drag_pp_treaty": round(drag_treaty, 4),
            "no_treaty_drag_pp": round(drag_stat, 4),
            "rrsp_drag_pp": 0.0,
            "multiple_of_fee_edge_treaty": (round(drag_treaty / FEE_EDGE_PP, 2)
                                            if drag_treaty else 0.0),
        })

    print(f"  {'ticker':7s}{'character':16s}{'yield':>8s}{'15% drag':>10s}"
          f"{'x fee edge':>12s}{'30% drag':>10s}")
    for r in rows:
        print(f"  {r['ticker']:7s}{r['income_character']:16s}"
              f"{r['distribution_yield_pct']:8.2f}{r['tfsa_or_taxable_drag_pp_treaty']:10.3f}"
              f"{r['multiple_of_fee_edge_treaty']:12.1f}{r['no_treaty_drag_pp']:10.3f}")

    eq = [r for r in rows if r["withholdable"]]
    best = max(eq, key=lambda r: r["tfsa_or_taxable_drag_pp_treaty"]) if eq else None
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "fee_edge_pp": FEE_EDGE_PP,
        # store as percentages so the report's table header is traceable
        "statutory_rate_pct": round(STATUTORY * 100, 2),
        "treaty_rate_pct": round(TREATY * 100, 2),
        "rows": rows,
        "equity_drag_range_pp": [
            min(r["tfsa_or_taxable_drag_pp_treaty"] for r in eq),
            max(r["tfsa_or_taxable_drag_pp_treaty"] for r in eq),
        ] if eq else None,
        "max_multiple_of_fee_edge": best["multiple_of_fee_edge_treaty"] if best else None,
        "tax_treatment_verified": False,
        "caveat": ("estimate from trailing distribution yield; tax treatment NOT "
                   "verified in this session; bond/t-bill interest generally "
                   "exempt as portfolio interest"),
    }

    if eq:
        lo, hi = payload["equity_drag_range_pp"]
        print(f"\n  Equity withholding drag: {lo:.3f} .. {hi:.3f} pp/yr")
        print(f"  Fee edge under debate  : {FEE_EDGE_PP:.4f} pp/yr")
        print(f"  Ratio                  : {lo/FEE_EDGE_PP:.1f}x .. {hi/FEE_EDGE_PP:.1f}x")
        print("\n  Bond/T-bill distributions are mostly portfolio interest and are")
        print("  generally NOT withheld, so the cost lands on the equity sleeve only.")

    if args.json:
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
