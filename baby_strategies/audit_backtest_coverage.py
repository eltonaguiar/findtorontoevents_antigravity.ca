"""
Audit backtest coverage across baby_strategies/.

Scans every .py file in baby_strategies/ and reports which ones lack backtest
metadata. Babies without .meta.json + backtest_metrics are effectively stuck
in the pipeline — they cannot graduate to the main pipeline because there is
no record of forward-test performance.

Usage:
    python baby_strategies/audit_backtest_coverage.py
    python baby_strategies/audit_backtest_coverage.py --json  # machine-readable
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import Counter
from pathlib import Path


# Harnesses/utilities/docs — not strategies, no backtest expected.
NON_STRATEGY_PATTERNS = (
    "backtest_", "__init__", "discord_", "_gen", "presentation", "tracker",
    "check_", "runner", "batch_", "suite", "generator", "audit_",
)


def is_strategy_file(path: Path) -> bool:
    name = path.name
    if name.startswith("_"):
        return False
    for pat in NON_STRATEGY_PATTERNS:
        if name.startswith(pat):
            return False
    return True


def audit(root: str = "baby_strategies") -> dict:
    root_p = Path(root)
    py_files = sorted(root_p.glob("*.py"))
    strategies = [f for f in py_files if is_strategy_file(f)]
    non_strat = [f for f in py_files if not is_strategy_file(f)]

    buckets: dict[str, list[str]] = {
        "no_meta": [],
        "meta_no_metrics": [],
        "backtest_passed": [],
        "backtest_failed": [],
        "ready_for_forward_test": [],
        "awaiting_backtest": [],
        "backtested_synthetic": [],
        "other_status": [],
    }
    statuses = Counter()

    for f in strategies:
        meta_path = f.with_suffix(f.suffix + ".meta.json")
        if not meta_path.exists():
            buckets["no_meta"].append(f.name)
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            buckets["meta_no_metrics"].append(f"{f.name} [parse error]")
            continue
        status = meta.get("status", "unknown")
        statuses[status] += 1
        metrics = meta.get("backtest_metrics", {})
        if not metrics or metrics.get("total_trades", 0) == 0:
            buckets["meta_no_metrics"].append(f.name)
        elif status in buckets:
            buckets[status].append(f.name)
        else:
            buckets["other_status"].append(f"{f.name} [{status}]")

    return {
        "totals": {
            "strategy_files": len(strategies),
            "non_strategy_files": len(non_strat),
            "no_meta": len(buckets["no_meta"]),
            "meta_no_metrics": len(buckets["meta_no_metrics"]),
            "with_valid_metrics": (
                len(strategies) - len(buckets["no_meta"]) - len(buckets["meta_no_metrics"])
            ),
        },
        "coverage_pct": round(
            100
            * (len(strategies) - len(buckets["no_meta"]) - len(buckets["meta_no_metrics"]))
            / max(len(strategies), 1),
            1,
        ),
        "buckets": buckets,
        "status_counts": dict(statuses),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="Emit JSON only")
    ap.add_argument("--show-missing", type=int, default=20,
                    help="How many missing names to print")
    args = ap.parse_args()

    report = audit()
    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print("Baby Strategies — Backtest Coverage Audit")
    print("=" * 60)
    t = report["totals"]
    print(f"Strategy .py files:       {t['strategy_files']}")
    print(f"  With valid metrics:     {t['with_valid_metrics']} ({report['coverage_pct']}%)")
    print(f"  Missing .meta.json:     {t['no_meta']}  <-- STUCK IN PIPELINE")
    print(f"  Meta but no metrics:    {t['meta_no_metrics']}")
    print(f"Non-strategy files (harnesses/etc): {t['non_strategy_files']}")
    print()
    print("Status distribution (of backtested):")
    for s, n in sorted(report["status_counts"].items(), key=lambda x: -x[1]):
        print(f"  {s:30s} {n}")
    print()
    print(f"First {args.show_missing} strategies WITHOUT .meta.json:")
    for name in report["buckets"]["no_meta"][: args.show_missing]:
        print(f"  - {name}")

    if t["no_meta"] > 0:
        print()
        print("ACTION: these strategies cannot graduate until they have")
        print("backtest_metrics in their .meta.json. Options:")
        print("  1. Run baby_strategies_backtest.py if they fit its single-symbol API")
        print("  2. Write a purpose-specific harness (see backtest_cross_sectional_carry.py)")
        print("  3. Archive obsolete babies to STRATEGY_GRAVEYARD.md")

    return 0 if t["no_meta"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
