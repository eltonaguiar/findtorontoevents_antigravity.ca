#!/usr/bin/env python3
"""
Template ↔ Index drift detector for audit_dashboard.

Checks that critical features in index.html also exist in template.html.
The automated audit-dashboard.yml workflow regenerates index.html from
template.html, so any feature ONLY in index.html gets wiped on the next run.

Run: python audit_dashboard/check_template_sync.py
Exit code 0 = in sync, 1 = drift detected.

Add to pre-commit hook or CI to prevent this from happening again.
"""

import re
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
INDEX = DIR / "index.html"
TEMPLATE = DIR / "template.html"

# Critical elements that MUST exist in both files
REQUIRED_ELEMENTS = [
    # HTML elements
    ("btn-export-excel", "Excel export button"),
    ("btn-export-closed", "Closed picks export button"),
    ("btn-clear-filters", "Clear filters button"),
    ("btn-best-fresh", "Best Picks button"),
    ("btn-proven-picks", "Proven Only button"),
    ("btn-strong-picks", "In Profit button"),
    # Age filter options
    ('value="2"', "≤2h age filter option"),
    # JS handlers
    ("btn-export-excel", "Excel export click handler"),
    ("btn-export-closed", "Closed export click handler"),
    ("downloadCSV", "CSV download helper function"),
    ("csvEscape", "CSV escape helper function"),
    # Scoring components
    ("_TRUST_PROVEN_STRATEGIES", "Trust proven strategies map"),
    ("_TRUST_DEMOTED", "Trust demoted strategies map"),
    ("_TRUST_PROBATION", "Trust probation systems map"),
    ("computeScore", "Score computation function"),
    ("livePnlScore", "Live PnL scoring component (v97)"),
    # Key scoring logic
    ("UNPROVEN", "Unproven trust tier"),
    ("score_multiplier", "Allocation tier multipliers"),
    # Persistent enhancements (external JS — survives generator overwrites)
    ("dashboard_enhancements.js", "Dashboard enhancements script tag"),
]

# Patterns that should have similar counts in both files (within tolerance)
COUNT_CHECKS = [
    ("addEventListener", 3),  # tolerance: template can have up to 3 fewer
    ("btn-export", 0),  # must have exact same count
]


def check_sync():
    if not INDEX.exists():
        print(f"SKIP: {INDEX} not found")
        return 0
    if not TEMPLATE.exists():
        print(f"SKIP: {TEMPLATE} not found")
        return 0

    idx = INDEX.read_text(encoding="utf-8", errors="replace")
    tpl = TEMPLATE.read_text(encoding="utf-8", errors="replace")

    issues = []

    # Check required elements
    for pattern, desc in REQUIRED_ELEMENTS:
        in_idx = pattern in idx
        in_tpl = pattern in tpl
        if in_idx and not in_tpl:
            issues.append(f"  MISSING from template.html: {desc} ({pattern!r})")
        elif not in_idx and in_tpl:
            issues.append(f"  MISSING from index.html: {desc} ({pattern!r})")

    # Check count parity
    for pattern, tolerance in COUNT_CHECKS:
        idx_count = idx.count(pattern)
        tpl_count = tpl.count(pattern)
        if abs(idx_count - tpl_count) > tolerance:
            issues.append(
                f"  COUNT MISMATCH: {pattern!r} — index={idx_count}, template={tpl_count} "
                f"(tolerance={tolerance})"
            )

    if issues:
        print(f"DRIFT DETECTED between index.html and template.html:")
        print(f"  The automated workflow will overwrite index.html from template.html!")
        print(f"  Features only in index.html will be LOST on the next workflow run.\n")
        for issue in issues:
            print(issue)
        print(f"\n  Total issues: {len(issues)}")
        print(f"  Fix: Add missing elements to template.html, not just index.html.")
        return 1
    else:
        print("OK: index.html and template.html are in sync (all critical elements present in both)")
        return 0


if __name__ == "__main__":
    sys.exit(check_sync())
