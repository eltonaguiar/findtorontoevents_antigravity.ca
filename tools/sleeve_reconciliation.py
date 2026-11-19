#!/usr/bin/env python3
"""Sleeve reconciliation: check if /audit top_sleeves exist in audit3 cells.

This script extracts top_sleeves from dashboard_data.json and checks whether
each sleeve strategy name appears in the audit3 ledger cells. If a sleeve
does not appear in audit3, it is flagged as UNVERIFIED (likely survivorship
or a naming/ingestion gap).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DASHBOARD = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
LEDGER = ROOT / "audit_dashboard" / "data" / "audit3_ledger.json"
OUT = ROOT / "reports" / "sleeve_reconciliation_2026-11-19.json"


def main():
    dashboard = json.load(open(DASHBOARD))
    ledger = json.load(open(LEDGER))

    # Extract top_sleeves from money_ready_verdicts
    mr = dashboard.get("money_ready_verdicts", {})
    sleeves = []
    for cls, info in mr.items():
        for s in (info.get("top_sleeves") or []):
            sleeves.append({
                "asset_class": cls,
                "strategy": s.get("strategy", "?"),
                "n": s.get("n", 0),
                "wr": s.get("wr", 0),
                "pf": s.get("pf", 0),
                "source": s.get("source", "?"),
                "is_single_source": s.get("is_single_source", False),
            })

    # Extract audit3 cell strategy names
    audit3_strategies = set()
    for cell in (ledger.get("cells") or []):
        audit3_strategies.add((cell.get("asset_class", ""), cell.get("strategy", "")))

    # Reconcile
    results = []
    for s in sleeves:
        key = (s["asset_class"], s["strategy"])
        in_audit3 = key in audit3_strategies
        # Also check case-insensitive
        if not in_audit3:
            for (ac, strat) in audit3_strategies:
                if ac == s["asset_class"] and strat.lower() == s["strategy"].lower():
                    in_audit3 = True
                    break
        results.append({
            **s,
            "in_audit3": in_audit3,
            "verdict": "VERIFIED" if in_audit3 else "UNVERIFIED",
            "single_source_warning": s["is_single_source"],
        })

    # Summary
    verified = [r for r in results if r["verdict"] == "VERIFIED"]
    unverified = [r for r in results if r["verdict"] == "UNVERIFIED"]
    single_source = [r for r in results if r["is_single_source"]]

    summary = {
        "total_sleeves": len(results),
        "verified": len(verified),
        "unverified": len(unverified),
        "single_source": len(single_source),
        "unverified_sleeves": [{"asset_class": r["asset_class"], "strategy": r["strategy"],
                                "pf": r["pf"], "n": r["n"]} for r in unverified],
    }

    output = {"summary": summary, "sleeves": results}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(f"Total sleeves: {len(results)}")
    print(f"Verified in audit3: {len(verified)}")
    print(f"UNVERIFIED (not in audit3): {len(unverified)}")
    print(f"Single-source: {len(single_source)}")
    print()
    print("UNVERIFIED sleeves:")
    for r in unverified:
        print(f"  {r['asset_class']:12s} {r['strategy'][:35]:35s} PF={r['pf']:8.2f} n={r['n']:4d} single={r['is_single_source']}")
    print()
    print(f"Output written to {OUT}")


if __name__ == "__main__":
    main()
