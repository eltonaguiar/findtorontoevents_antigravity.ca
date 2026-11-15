#!/usr/bin/env python3
"""
Mutual Fund Passive Allocation Screener
=======================================

Screens mutual funds against hard gates for passive core allocation.
NOT an active pick system — mutual funds are structurally incompatible
with intraday TP/SL picking (daily NAV only).

Hard gates (ALL must pass):
  - Expense ratio ≤ 0.09% (index) / ≤ 0.20% (active)
  - No load, no 12b-1
  - Min initial investment ≤ $3,000 (Admiral shares are eligible)
  - AUM ≥ $1B
  - Turnover ≤ 20%
  - Tracking error ≤ 0.25% vs benchmark
  - Track record ≥ 10 years
  - NAV freshness ≤ 24h

Usage:
  python3 mf_screener.py --input <mf_metadata.json|csv> --output <screening_results.json>
"""

import json
import csv
import os
import sys
import argparse
from datetime import datetime, timezone

HARD_GATES = {
    "expense_ratio_index": 0.0009,   # 0.09%
    "expense_ratio_active": 0.0020,  # 0.20%
    "max_load": 0.0,
    "max_12b1": 0.0,
    "max_min_initial": 3000.0,  # Admiral share class, not a defect
    "min_aum": 1_000_000_000,        # $1B
    "max_turnover": 0.20,            # 20%
    "max_tracking_error": 0.0025,    # 0.25%
    "min_track_record_years": 10,
    "max_nav_freshness_hours": 24,
}

STARTER_UNIVERSE = ["VFIAX", "VTSAX", "FXAIX", "SWTSX", "VBTLX", "VWELX", "VGSLX", "VTIAX"]



def _num_gate(actual, ok, threshold):
    if actual is None or actual == "":
        return {"pass": False, "status": "insufficient", "threshold": threshold, "actual": None}
    try:
        value = float(actual)
    except (TypeError, ValueError):
        return {"pass": False, "status": "insufficient", "threshold": threshold, "actual": actual}
    passed = bool(ok(value))
    return {"pass": passed, "status": "pass" if passed else "fail", "threshold": threshold, "actual": value}


def screen_fund(fund):
    """Screen a single mutual fund against hard gates. Returns pass/fail + details."""
    is_index = fund.get("index_fund", True)
    er_threshold = HARD_GATES["expense_ratio_index"] if is_index else HARD_GATES["expense_ratio_active"]

    gates = {
        "expense_ratio": {
            "pass": fund.get("expense_ratio", 999) <= er_threshold,
            "threshold": f"≤ {er_threshold:.4f} ({er_threshold*100:.2f}%)",
            "actual": fund.get("expense_ratio"),
        },
        "no_load": {
            "pass": fund.get("load", 1) == 0,
            "threshold": "None",
            "actual": fund.get("load"),
        },
        "no_12b1": {
            "pass": fund.get("b_12b1", 1) == 0,
            "threshold": "None",
            "actual": fund.get("b_12b1"),
        },
        "min_initial": _num_gate(fund.get("min_initial"), lambda v: v <= HARD_GATES["max_min_initial"], f"≤ ${HARD_GATES['max_min_initial']:,.0f}"),
        "aum": _num_gate(fund.get("aum"), lambda v: v >= HARD_GATES["min_aum"], f"≥ ${HARD_GATES['min_aum']:,.0f}"),
        "turnover": {
            "pass": fund.get("turnover", 999) <= HARD_GATES["max_turnover"],
            "threshold": f"≤ {HARD_GATES['max_turnover']:.0%}",
            "actual": fund.get("turnover"),
        },
        "tracking_error": {
            "pass": fund.get("tracking_error", 999) <= HARD_GATES["max_tracking_error"],
            "threshold": f"≤ {HARD_GATES['max_tracking_error']:.4f}",
            "actual": fund.get("tracking_error"),
        },
        "track_record_years": {
            "pass": fund.get("track_record_years", 0) >= HARD_GATES["min_track_record_years"],
            "threshold": f"≥ {HARD_GATES['min_track_record_years']} years",
            "actual": fund.get("track_record_years"),
        },
        "nav_freshness": {
            "pass": fund.get("nav_freshness_hours", 999) <= HARD_GATES["max_nav_freshness_hours"],
            "threshold": f"≤ {HARD_GATES['max_nav_freshness_hours']} hours",
            "actual": fund.get("nav_freshness_hours"),
        },
    }

    failed = [k for k, v in gates.items() if v.get("status") == "fail" or (v.get("status") is None and not v["pass"])]
    insufficient = [k for k, v in gates.items() if v.get("status") == "insufficient"]
    passed = not failed and not insufficient
    return {
        "symbol": fund.get("symbol"),
        "name": fund.get("name"),
        "passed": passed,
        "status": "pass" if passed else ("insufficient" if insufficient and not failed else "fail"),
        "failed_gates": failed,
        "insufficient_gates": insufficient,
        "gates": gates,
    }


def screen_all(funds):
    """Screen all funds and return aggregate results."""
    results = [screen_fund(f) for f in funds]
    passed = [r for r in results if r["passed"]]
    failed = [r for r in results if not r["passed"]]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_funds": len(results),
        "passed": len(passed),
        "failed": len(failed),
        "passing_funds": passed,
        "failing_funds": failed,
        "hard_gates": HARD_GATES,
    }


def generate_html(result):
    """Generate HTML screening report."""
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Mutual Fund Screener</title>
<style>
body {{ font-family: monospace; margin: 20px; }}
.pass {{ color: green; }}
.fail {{ color: red; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
th {{ background: #f4f4f4; }}
</style>
</head>
<body>
<h1>Mutual Fund Passive Allocation Screener</h1>
<p>Generated: {result['generated_at']}</p>
<p>Total funds: {result['total_funds']} | Passing: <span class="pass">{result['passed']}</span> | Failing: <span class="fail">{result['failed']}</span></p>

<h2>Hard Gates</h2>
<ul>
<li>Expense ratio ≤ 0.09% (index) / 0.20% (active)</li>
<li>No load, no 12b-1</li>
<li>Min initial ≤ $3,000 (Admiral eligible; missing field = insufficient)</li>
<li>AUM ≥ $1B</li>
<li>Turnover ≤ 20%</li>
<li>Tracking error ≤ 0.25%</li>
<li>Track record ≥ 10 years</li>
<li>NAV freshness ≤ 24h</li>
</ul>

<h2>Passing Funds (eligible for passive core allocation)</h2>
<table>
<tr><th>Symbol</th><th>Name</th><th>Failed Gates</th></tr>
"""
    for r in result["passing_funds"]:
        html += f"<tr><td>{r['symbol']}</td><td>{r['name']}</td><td>None</td></tr>"

    html += """</table>

<h2>Failing Funds</h2>
<table>
<tr><th>Symbol</th><th>Name</th><th>Failed Gates</th></tr>
"""
    for r in result["failing_funds"]:
        html += f"<tr><td>{r['symbol']}</td><td>{r['name']}</td><td>{', '.join(r['failed_gates'])}</td></tr>"

    html += """
<p><em>Note: Mutual funds are NOT active picks. These are screened for passive core allocation only.</em></p>
</body></html>"""
    return html


def main():
    parser = argparse.ArgumentParser(description="Mutual Fund Passive Allocation Screener")
    parser.add_argument("--input", required=True, help="Path to mutual fund metadata JSON or CSV")
    parser.add_argument("--output", help="Output JSON path")
    parser.add_argument("--html", help="Output HTML path")
    args = parser.parse_args()

    # Load funds
    funds = []
    if args.input.endswith(".csv"):
        with open(args.input) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric fields
                for k in ["expense_ratio", "load", "b_12b1", "min_initial", "aum", "turnover", "tracking_error", "track_record_years", "nav_freshness_hours"]:
                    if k in row and row[k]:
                        try:
                            row[k] = float(row[k])
                        except ValueError:
                            pass
                funds.append(row)
    else:
        data = json.load(open(args.input))
        if isinstance(data, dict):
            funds = data.get("funds", data.get("mutual_funds", [data]))
        else:
            funds = data

    result = screen_all(funds)

    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True) if os.path.dirname(args.output) else None
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"Screening results saved to {args.output}")

    if args.html:
        html = generate_html(result)
        with open(args.html, "w") as f:
            f.write(html)
        print(f"HTML report saved to {args.html}")

    print(f"\nScreened {result['total_funds']} funds: {result['passed']} passing, {result['failed']} failing")
    print("\nPassing funds (eligible for passive core allocation):")
    for r in result["passing_funds"]:
        print(f"  {r['symbol']:<10s} {r['name']}")
    print("\nFailing funds:")
    for r in result["failing_funds"]:
        print(f"  {r['symbol']:<10s} {r['name']} — {', '.join(r['failed_gates'])}")


if __name__ == "__main__":
    main()
