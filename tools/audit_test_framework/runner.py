#!/usr/bin/env python3
"""Executable test runner for the audit test framework.

Usage:
    python3 tools/audit_test_framework/runner.py --tests all
    python3 tools/audit_test_framework/runner.py --tests critical
    python3 -m tools.audit_test_framework.runner --tests all
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Support both direct execution and module execution
try:
    from .base import AuditTest
    from .tests import (
        AssetClassificationCheck,
        BacktestTableCheck,
        DataFreshnessCheck,
        DbHealthCheck,
        GhostRowCount,
        OpenBloatCheck,
        PnLIntegrityCheck,
        SignalOutcomesCheck,
        WonPnlContradiction,
    )
except ImportError:
    # Direct script execution — add parent to path and use absolute imports
    _here = os.path.dirname(os.path.abspath(__file__))
    _root = os.path.dirname(os.path.dirname(_here))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from tools.audit_test_framework.base import AuditTest
    from tools.audit_test_framework.tests import (
        AssetClassificationCheck,
        BacktestTableCheck,
        DataFreshnessCheck,
        DbHealthCheck,
        GhostRowCount,
        OpenBloatCheck,
        PnLIntegrityCheck,
        SignalOutcomesCheck,
        WonPnlContradiction,
    )

# Discovery registry — all AuditTest subclasses
ALL_TESTS = [
    DbHealthCheck,
    GhostRowCount,
    OpenBloatCheck,
    PnLIntegrityCheck,
    WonPnlContradiction,
    DataFreshnessCheck,
    AssetClassificationCheck,
    SignalOutcomesCheck,
    BacktestTableCheck,
]

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
_REPORTS_DIR = os.path.join(_PROJECT_ROOT, "reports")


def _discover_tests(filter_severities: list | None = None) -> list[AuditTest]:
    """Instantiate tests, optionally filtered by severity.

    Critical tests are always included first, then the rest in severity order.
    """
    instances = []
    for cls in ALL_TESTS:
        test = cls()
        if filter_severities is None or test.severity in filter_severities:
            instances.append(test)

    # Sort: critical first, then by severity order
    instances.sort(key=lambda t: SEVERITY_ORDER.get(t.severity, 99))
    return instances


def run_audit_tests(mode: str = "all") -> dict:
    """Run audit tests and return results + summary.

    Parameters
    ----------
    mode : str
        "all" — run every test
        "critical" — run only critical-severity tests
        "critical,high" — comma-separated severity list

    Returns
    -------
    dict with keys: summary, results, timestamp
    """
    if mode == "all":
        filter_severities = None
    else:
        filter_severities = [s.strip() for s in mode.split(",")]

    tests = _discover_tests(filter_severities)

    results = []
    critical_failed = False

    for test in tests:
        result = test.run()
        result["name"] = test.name
        result["severity"] = test.severity

        if not result["passed"] and test.severity == "critical":
            critical_failed = True

        results.append(result)

    # Build summary
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = sum(1 for r in results if not r["passed"])
    by_severity = {}
    for r in results:
        sev = r["severity"]
        by_severity.setdefault(sev, {"passed": 0, "failed": 0})
        if r["passed"]:
            by_severity[sev]["passed"] += 1
        else:
            by_severity[sev]["failed"] += 1

    summary = {
        "total": len(results),
        "passed": passed_count,
        "failed": failed_count,
        "critical_failed": critical_failed,
        "by_severity": by_severity,
    }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "summary": summary,
        "results": results,
    }


def _write_report(report: dict) -> str:
    """Write report JSON to reports/audit_test_results_YYYY-MM-DD.json."""
    os.makedirs(_REPORTS_DIR, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"audit_test_results_{date_str}.json"
    filepath = os.path.join(_REPORTS_DIR, filename)

    with open(filepath, "w") as f:
        json.dump(report, f, indent=2, default=str)

    return filepath


def _format_result(result: dict) -> str:
    """Format a single test result for console output."""
    status = "PASS" if result["passed"] else "FAIL"
    severity_tag = result["severity"].upper()
    return f"  [{severity_tag:8s}] {status:4s}  {result['name']}: {result['message']}"


def main():
    parser = argparse.ArgumentParser(description="Audit test framework runner")
    parser.add_argument(
        "--tests",
        choices=["all", "critical"],
        default="all",
        help="Which tests to run (default: all)",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip writing the JSON report file",
    )
    args = parser.parse_args()

    report = run_audit_tests(mode=args.tests)

    # Console output
    print(f"\n{'='*70}")
    print(f"Audit Test Results  ({report['timestamp']})")
    print(f"Mode: {args.tests}")
    print(f"{'='*70}")

    for result in report["results"]:
        print(_format_result(result))

    s = report["summary"]
    print(f"\n{'─'*70}")
    print(f"  Total: {s['total']}  |  Passed: {s['passed']}  |  Failed: {s['failed']}")
    if s["critical_failed"]:
        print(f"  *** CRITICAL TESTS FAILED ***")
    print(f"{'='*70}\n")

    # Write report
    if not args.no_report:
        report_path = _write_report(report)
        print(f"Report saved to: {report_path}")

    # Exit code: 1 if any critical test failed
    sys.exit(1 if s["critical_failed"] else 0)


if __name__ == "__main__":
    main()
