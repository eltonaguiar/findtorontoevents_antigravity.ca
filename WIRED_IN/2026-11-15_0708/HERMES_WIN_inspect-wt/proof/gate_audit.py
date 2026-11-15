"""Gate audit — are the repo's promotion gates actually enforced?

The audit found two promotion gates shipping disabled
(`MONEY_READY_FDR_GATE=0`, `MONEY_READY_SINGLE_SOURCE_GATE=0`). A "money-ready"
verdict reached with them off is not a promotion. This script makes that
checkable in CI instead of a footnote in a markdown file.

Usage:
    python proof/gate_audit.py [--repo-root PATH]
Exit code 0 = all gates enforced, 1 = at least one gate off/missing.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CHECKS = [
    {
        "name": "cost_gate_multiple",
        "file": "tools/per_class_cost_gate.py",
        "pattern": r"REQUIRED_COST_MULTIPLE\s*=\s*([0-9.]+)",
        "expect": lambda v: float(v) >= 3.0,
        "why": "edge/cost multiple must be >= 3x before a class is tradeable",
    },
    {
        "name": "fdr_gate",
        "file": "alpha_engine/money_ready_verdict.py",
        "pattern": r'MONEY_READY_FDR_GATE",\s*"([01])"',
        "expect": lambda v: v == "1",
        "why": "false-discovery-rate gate must be ON or promotions are uncorrected",
    },
    {
        "name": "single_source_gate",
        "file": "alpha_engine/money_ready_verdict.py",
        "pattern": r'MONEY_READY_SINGLE_SOURCE_GATE",\s*"([01])"',
        "expect": lambda v: v == "1",
        "why": "single-source gate must be ON or one feed can promote a class alone",
    },
    {
        "name": "walk_forward_consistency",
        "file": "walk_forward_validator.py",
        "pattern": r"min_consistency[^=\n]*=\s*([0-9.]+)",
        "expect": lambda v: float(v) >= 0.5,
        "why": "walk-forward consistency threshold must be >= 0.5",
    },
    {
        "name": "walk_forward_min_trades",
        "file": "walk_forward_validator.py",
        "pattern": r"min_train_trades[\"']?\s*[:=]\s*([0-9]+)",
        "expect": lambda v: int(v) >= 10,
        "why": "each window needs enough trades to be meaningful",
    },
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()
    root = Path(args.repo_root).resolve()

    failures = 0
    print(f"Gate audit — repo root: {root}\n")
    print(f"{'gate':28} {'value':8} {'status':8} why")
    print("-" * 96)
    for c in CHECKS:
        path = root / c["file"]
        if not path.exists():
            print(f"{c['name']:28} {'-':8} {'MISSING':8} {c['file']} not found")
            failures += 1
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        m = re.search(c["pattern"], text)
        if not m:
            print(f"{c['name']:28} {'?':8} {'UNKNOWN':8} pattern not matched in {c['file']}")
            failures += 1
            continue
        val = m.group(1)
        ok = False
        try:
            ok = bool(c["expect"](val))
        except Exception:
            ok = False
        print(f"{c['name']:28} {val:8} {'OK' if ok else 'OFF/FAIL':8} {c['why']}")
        failures += 0 if ok else 1

    print("-" * 96)
    if failures:
        print(f"\n{failures} gate(s) not enforced. Do NOT promote any candidate until they are.")
        return 1
    print("\nAll gates enforced.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
