#!/usr/bin/env python3
"""
Run HC Filter Rewrite v2 validation stack + summarize Cursor plan YAML status.

  python tools/run_hc_plan_validation.py
  python tools/run_hc_plan_validation.py --plan "C:\\Users\\you\\.cursor\\plans\\hc_filter_rewrite_v2_945ff086.plan.md"

Does not auto-watch the plan file; re-run after Cursor todos change or before merge.
See docs/HC_FILTER_REWRITE_V2_VALIDATION.md
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def _plan_summary(plan_path: Path) -> None:
    if not plan_path.is_file():
        print("Plan file not found:", plan_path)
        return
    text = plan_path.read_text(encoding="utf-8", errors="replace")
    pending = len(re.findall(r"status:\s*pending", text, re.I))
    done = len(re.findall(r"status:\s*completed", text, re.I))
    print("=== Cursor plan:", plan_path)
    print("   todos completed:", done, " pending:", pending)
    if pending and not done:
        print("   (All steps still pending in YAML — or plan file not updated.)")
    print()


def _run(name: str, cmd: list[str]) -> bool:
    print("---", name)
    try:
        r = subprocess.run(cmd, cwd=_REPO, check=False)
        ok = r.returncode == 0
        if not ok:
            print("FAILED:", name, "exit", r.returncode)
        return ok
    except OSError as e:
        print("FAILED:", name, e)
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--plan",
        type=Path,
        default=Path.home() / ".cursor" / "plans" / "hc_filter_rewrite_v2_945ff086.plan.md",
        help="Path to hc_filter_rewrite_v2 Cursor plan (optional)",
    )
    ap.add_argument("--skip-plan-read", action="store_true")
    args = ap.parse_args()

    if not args.skip_plan_read:
        _plan_summary(args.plan)

    py = sys.executable
    steps: list[tuple[str, list[str]]] = [
        ("py_compile conviction_stack_patch", [py, "-m", "py_compile", "alpha_engine/conviction_stack_patch.py"]),
        ("pytest dashboard_hc_rules", [py, "-m", "pytest", "tests/test_dashboard_hc_rules.py", "-q", "--tb=short"]),
        ("backtest_hc_filter", [py, "tools/backtest_hc_filter.py"]),
        ("validate_dashboard_parity", [py, "tools/validate_dashboard_parity.py"]),
        (
            "validate_hf_by_asset_class",
            [py, "tools/validate_hf_by_asset_class.py", "--json-out", "audit_trail/data/hf_asset_class_report.json"],
        ),
        ("node test_hc_filter.js", ["node", "tests/test_hc_filter.js"]),
    ]

    ok_all = True
    for name, cmd in steps:
        if not _run(name, cmd):
            ok_all = False

    print()
    if ok_all:
        print("=== All automated checks passed. Run LAYER NC manual rows in docs/HC_FILTER_REWRITE_V2_VALIDATION.md if needed.")
        return 0
    print("=== One or more checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
