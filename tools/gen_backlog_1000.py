#!/usr/bin/env python3
"""Generate the 1000-item backlog for the fund-report programme.

Why generated
-------------
A hand-written 1000-item list would be either fabricated or 900 duplicates. So
the list is composed from the REAL entities in this work - the funds, metrics,
artifacts, tools, tests, document sections, tax dimensions and asset classes -
crossed with real check types. Every item names a concrete object that exists in
the repo, which makes it triageable rather than decorative.

The first 60 items are hand-specified and prioritised; the remainder is the
systematic sweep. Nothing here claims to be planned work until it is triaged.

    python3 tools/gen_backlog_1000.py --out docs/edge_research/BACKLOG_1000_2026-11-24.md
"""
import argparse
import sys
from pathlib import Path

# ---- real entities from the fund programme --------------------------------
FUNDS = ["FXAIX", "SPY", "FZROX", "VTI", "VTSAX", "BND", "SGOV"]
METRICS = ["gross CAGR", "net CAGR", "volatility", "Sharpe", "Sortino",
           "max drawdown", "turnover", "bootstrap CI", "rf hurdle", "n_days"]
ARTIFACTS = ["fund_deep_dive.json", "fund_forward_anchors.json",
             "fund_glide_path.json", "fund_block_sensitivity.json",
             "fund_cad_view.json", "fund_withholding.json"]
TOOLS = ["fund_deep_dive.py", "fund_glide_path.py", "fund_block_sensitivity.py",
         "fund_cad_view.py", "fund_withholding_cost.py", "fund_doc_lint.py",
         "check_fund_schema.py", "gen_corrected_table.py"]
TESTS = ["test_fund_metrics.py", "test_fund_glide_path.py",
         "test_check_fund_schema.py", "test_fund_doc_lint.py",
         "test_fund_block_sensitivity.py", "test_fund_cad_view.py",
         "test_fund_jurisdiction_and_withholding.py"]
SECTIONS = ["Errata", "Step 0 wrapper", "Step 1 vehicle", "measured table",
            "CAD view", "Precision", "paired diffs", "rebalancing",
            "glide path", "forward anchors", "futures scope", "decision table",
            "bottom line"]
TAX = ["PFIC", "US estate tax", "TFSA withholding", "RRSP withholding",
       "W-8BEN", "capital-gains distributions", "portfolio interest",
       "currency hedging", "FX conversion cost", "withholding reclaim"]
CLASSES = ["CRYPTO", "EQUITY", "COMMODITY", "ETF", "FOREX", "BOND",
           "PREDICTION", "OPTIONS", "FUTURES", "FX-CARRY", "MACRO", "CASH"]

# ---- real check types -----------------------------------------------------
CHECKS = [
    ("verify against an independent source", "cross-source"),
    ("prove the computation on synthetic data with a known answer", "unit"),
    ("state the assumption it depends on, next to the number", "documentation"),
    ("record provenance (source, as-of date, fetch method)", "provenance"),
    ("test the failure mode, not just the happy path", "negative"),
]

HAND = [
    ("Establish a canonical price dataset with a hash recorded in the payload", "P0"),
    ("Fetch a TSX-listed total-market ETF series so the Canadian answer is testable", "P0"),
    ("Fetch a TSX-listed S&P 500 ETF series (VFV/ZSP/XUS) with CAD prices", "P0"),
    ("Fetch a TSX-listed aggregate bond ETF series (ZAG/VAB) with CAD prices", "P0"),
    ("Fetch a TSX-listed cash ETF series (CASH.TO/PSA) as the CAD cash hurdle", "P0"),
    ("Replace the assumed hedging carry with a measured forward curve", "P0"),
    ("Quantify US estate-tax exposure for a non-resident at several portfolio sizes", "P0"),
    ("Compute the PFIC cost of holding a US mutual fund as a Canadian resident", "P0"),
    ("Model the TFSA-vs-RRSP domicile flip as an explicit decision table", "P0"),
    ("Measure the FX conversion cost a Canadian broker actually charges", "P1"),
    ("Model Norbert's Gambit as an alternative to broker FX spread", "P1"),
    ("Add a CAD-basis Sharpe using a CAD cash hurdle throughout the report", "P1"),
    ("Test whether the CAD conclusion survives a 2015-2021 window (CAD strengthened)", "P1"),
    ("Add a regime table: rate-hike vs rate-cut windows, per sleeve", "P1"),
    ("Test whether BND duration risk is properly reflected in the forward claim", "P1"),
    ("Replace the 5bp spread assumption with observed ETF bid-ask data", "P1"),
    ("Model the withholding reclaim process and its cost in effort", "P1"),
    ("Verify the 15% treaty rate against current CRA/IRS guidance", "P1"),
    ("Verify whether portfolio-interest exemption applies to BND's distributions", "P1"),
    ("Confirm FZROX availability constraints in writing", "P1"),
    ("Check whether the price CSV is dividend-adjusted for every ticker, not just SGOV", "P0"),
    ("Add a per-ticker dividend-reinvestment control test like the SGOV one", "P0"),
    ("Recompute all CAGRs from raw unadjusted prices to cross-check", "P0"),
    ("Test survivorship: are these funds still open and was any delisted", "P1"),
    ("Document why SPY was chosen over IVV/VOO as the ETF comparator", "P1"),
    ("Add VOO/IVV so the 0.0945% SPY fee is not the only ETF datapoint", "P1"),
    ("Reconcile the report's USD numbers against the audit dashboard's ETF class", "P1"),
    ("Decide whether this report should live under /audit or standalone", "P1"),
    ("Add a machine-readable claims register alongside the prose", "P1"),
    ("Extend the provenance lint to cover prose numbers, not just tables", "P1"),
    ("Make the lint fail on any number lacking a source in the same sentence", "P1"),
    ("Add a CI job asserting the report renders and links resolve", "P2"),
    ("Add a scheduled refresh for anchors with staleness alerting", "P2"),
    ("Add a diff summary when the regenerated payload changes materially", "P2"),
    ("Record why the 21-day bootstrap block was chosen, in the methods section", "P2"),
    ("Add a permutation test alongside the paired bootstrap", "P2"),
    ("Add a stationary bootstrap (Politis-Romano) as a robustness check", "P2"),
    ("Test the paired difference under a block=63 default", "P2"),
    ("Add the sub-period test for every paired comparison, not just FXAIX-SPY", "P2"),
    ("Model a 3-sleeve portfolio (equity/bond/cash) on the glide path", "P2"),
    ("Add a rebalancing bonus/cost decomposition", "P2"),
    ("Test whether buy-and-hold dominance holds with wider spreads", "P2"),
    ("Add a tax-aware rebalancing view (only rebalance with new money)", "P2"),
    ("Model sequence-of-returns risk for a decumulation phase", "P2"),
    ("Add a Monte Carlo of terminal wealth for each glide-path point", "P2"),
    ("State the report's horizon assumption explicitly (5y is not a plan)", "P1"),
    ("Add a 'what we would need to believe' section per recommendation", "P1"),
    ("Add the inverse of each finding: when is the opposite true", "P1"),
    ("Get one independent external review of the corrected document", "P1"),
    ("Fix the stale /consult-multi model IDs so fan-out works", "P2"),
    ("Add a local-review harness that feeds the doc verbatim and captures objections", "P2"),
    ("Turn each past review objection into a permanent regression test", "P1"),
    ("Record review objections that were REFUTED, with the refuting evidence", "P2"),
    ("Publish a corrections log with dates and reasons", "P2"),
    ("Decide the merge path for this branch (PR vs fold into the existing one)", "P0"),
    ("Confirm the branch contains no foreign files before any merge", "P0"),
    ("Add a pre-push check that the branch diff is a subset of an allowlist", "P0"),
    ("Add a guard so a masked gate failure cannot be committed again", "P0"),
    ("Extend the CI workflow to run the full fund suite on every push", "P1"),
]


def build():
    items = []
    for i, (text, prio) in enumerate(HAND, 1):
        items.append((f"H{i:03d}", "PRIORITISED", prio, text))

    # systematic sweep: real entity x real check type
    n = len(items)
    for cat, entities in (("FUND", FUNDS), ("METRIC", METRICS),
                          ("ARTIFACT", ARTIFACTS), ("TOOL", TOOLS),
                          ("TEST", TESTS), ("SECTION", SECTIONS),
                          ("TAX", TAX), ("CLASS", CLASSES)):
        for ent in entities:
            for check, kind in CHECKS:
                n += 1
                prefix = {"FUND": "FD", "METRIC": "MT", "ARTIFACT": "AR",
                          "TOOL": "TL", "TEST": "TS", "SECTION": "SC",
                          "TAX": "TX", "CLASS": "CL"}[cat]
                items.append((f"{prefix}{n:04d}", cat, kind,
                              f"{ent}: {check}"))
    return items


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    items = build()
    # top up to exactly 1000 with named cross-entity combinations
    idx = 0
    while len(items) < 1000:
        f = FUNDS[idx % len(FUNDS)]
        m = METRICS[(idx // len(FUNDS)) % len(METRICS)]
        c = CLASSES[idx % len(CLASSES)]
        idx += 1
        items.append((f"XX{len(items):04d}", "CROSS", "cross-check",
                      f"{f}: {m} vs the {c} class baseline in the audit dashboard"))
    items = items[:1000]

    lines = [
        "# Backlog: 1000 items for the fund-report programme",
        "",
        "**Date:** 2026-11-24 · **Status:** scaffold, not a plan",
        "",
        f"The first {len(HAND)} are hand-specified and prioritised. The remainder is a",
        "systematic sweep across the real entities in this work (funds, metrics,",
        "artifacts, tools, tests, document sections, tax dimensions, asset classes)",
        "crossed with real check types, so every item names something that exists.",
        "",
        f"**Nothing below item {len(HAND)} should be treated as planned.** Triage before",
        "working: most sweeps will be either already-done or not worth doing, and",
        "saying so is a valid outcome for an item.",
        "",
        f"Total items: {len(items)}",
        "",
        "## Prioritised",
        "",
        "| id | prio | item |",
        "|---|---|---|",
    ]
    for iid, cat, prio, text in items[:len(HAND)]:
        lines.append(f"| {iid} | {prio} | {text} |")

    lines += ["", "## Sweep", "", "| id | group | kind | item |", "|---|---|---|---|"]
    for iid, cat, kind, text in items[len(HAND):]:
        lines.append(f"| {iid} | {cat} | {kind} | {text} |")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines) + "\n")
    print(f"  wrote {args.out} with {len(items)} items")
    print(f"  prioritised: {len(HAND)}   sweep: {len(items) - len(HAND)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
