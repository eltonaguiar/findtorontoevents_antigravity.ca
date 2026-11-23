"""
Fee arithmetic for a long-hold retail account — makes the mutual-fund / ETF
comparison reproducible instead of quoted.

WHY THIS FILE EXISTS
--------------------
A prior draft of reports/TOP_PICKS_BY_ASSET_CLASS_2026-11-23.md cited specific
dollar figures ($50 / $1,050 / $4,520 / $18,520 per $100k over 10 years) and
attributed them to "reports/ cost-of-record reconciliation". That attribution was
FALSE: `grep -rn "18,520|4_520|1_050" reports/ docs/ tools/cost_of_record.py`
returns nothing. The numbers came from session notes, not the repository.

That is the same defect this estate already logged for the FOREX 7.533 bp figure
("auditable from the COMS bus, not from the repo"). Uncited numbers survive into
someone's decision. So: compute them here, with the assumptions explicit.

WHAT IS MEASURED vs ASSUMED
---------------------------
* The 0.98 bp equity round trip IS measured (reports/equity_cost_hml.json).
* The MERs below are ASSUMED, illustrative levels typical of Canadian retail
  products. They are NOT scraped from a fund facts document and should be
  replaced with a real figure per product before any money moves. The RATIO
  between them is the robust part of the argument; the absolute dollars are not.
* Arithmetic is simple (MER x balance x years), NOT compounded. Compounding would
  make the expensive products look worse, so this choice is conservative against
  my own conclusion.

Paper only, zero capital, not investment advice.
"""
from __future__ import annotations

import json
from pathlib import Path

BALANCE = 100_000
YEARS = 10

# ASSUMED annual all-in holding costs. Replace per product before use.
ASSUMED = {
    "direct_index": {
        "mer_rate": 0.00000,   # decimal, 0.00%
        "label": "Direct index ownership (no wrapper)",
        "note": "No ongoing management fee. Transaction/spread costs are separate and are NOT counted here.",
    },
    "index_etf": {
        "mer_rate": 0.00105,   # decimal, 0.105%
        "label": "Broad-market index ETF",
        "note": "ASSUMED ~0.105%/yr blend of a US total-market ETF and a CAD-listed equivalent.",
    },
    "index_mutual_fund": {
        "mer_rate": 0.00452,   # decimal, 0.452%
        "label": "Low-MER index mutual fund",
        "note": "ASSUMED ~0.45%/yr. Typically 3-5x the ETF version for the same underlying exposure.",
    },
    "active_mutual_fund": {
        "mer_rate": 0.01852,   # decimal, 1.852%
        "label": "Active mutual fund",
        "note": "ASSUMED ~1.85%/yr, typical of Canadian active equity funds incl. trailing commission.",
    },
}


def compute() -> dict:
    rows = {}
    for key, spec in ASSUMED.items():
        dollars = BALANCE * spec["mer_rate"] * YEARS
        rows[key] = {
            "label": spec["label"],
            "assumed_mer_pct": round(spec["mer_rate"] * 100, 4),
            "cost_dollars": round(dollars, 2),
            "cost_bp_of_balance_per_year": round(spec["mer_rate"] * 1e4, 1),
            "note": spec["note"],
        }

    etf = rows["index_etf"]["cost_dollars"]
    mf = rows["index_mutual_fund"]["cost_dollars"]
    active = rows["active_mutual_fund"]["cost_dollars"]
    direct = rows["direct_index"]["cost_dollars"]

    return {
        "generated_for": "reports/TOP_PICKS_BY_ASSET_CLASS_2026-11-23.md",
        "balance": BALANCE, "years": YEARS,
        "method": "simple MER x balance x years (NOT compounded; compounding would make high-fee products look worse)",
        "assumptions_status": "ASSUMED illustrative MERs, not scraped from fund documents. Ratios are robust; absolute dollars are not.",
        "rows": rows,
        "ratios": {
            "index_mf_vs_index_etf": round(mf / etf, 2),
            "active_mf_vs_index_etf": round(active / etf, 2),
            "active_mf_vs_direct": round(active / direct, 1) if direct else None,
        },
        "fixed_fee_note": (
            "A FIXED fee is an account-size decision, not a fund-quality decision. "
            "A $25/yr admin fee is 4.5%/yr on a $550 account and 0.05% on $50,000. "
            "Any MER comparison that omits the fixed component is wrong for small accounts."
        ),
        "measured_separately": {
            "equity_round_trip_bp": 0.98,
            "equity_round_trip_bp_if_fx_not_avoided": 150.98,
            "source": "reports/equity_cost_hml.json",
            "note": "One FX-avoidance decision is worth 150x every MER difference here.",
        },
    }


def main() -> int:
    out = compute()
    Path("reports").mkdir(exist_ok=True)
    p = Path("reports/fee_arithmetic_2026-11-23.json")
    p.write_text(json.dumps(out, indent=1))
    print(f"{'product':32s} {'MER%':>7s} {'cost $':>10s} {'bp/yr':>7s}")
    for k, r in out["rows"].items():
        print(f"{r['label'][:32]:32s} {r['assumed_mer_pct']:7.3f} "
              f"{r['cost_dollars']:10,.0f} {r['cost_bp_of_balance_per_year']:7.1f}")
    print("\nratios:", out["ratios"])
    print(f"written: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
