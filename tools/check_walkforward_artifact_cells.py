#!/usr/bin/env python3
"""P1-1 standing CI check: fail when the walk-forward evaluation report contains
frozen-exit artifact cells.

Background
----------
The frozen-exit resolver bug (audit_trail/universal_pick_resolver.py) used to
fetch prices once per run and stamp the same snapshot onto every unresolved pick
of a symbol, manufacturing fake clustered "wins" (a cluster of N wins sharing one
exit date). The walk-forward harness flags these via `detect_artifact_cells`
(wins > 2 x distinct exit dates) and reports them under `artifact_cells`.

This script is the guardian: if the LATEST walk-forward report still contains any
artifact cells, the CI gate fails, so a stale or regressed resolver can never
silently poison downstream rankings.

Exit codes:
  0 - no artifact cells in the latest report (clean)
  1 - artifact cells found (CI must fail)
  2 - usage / report-not-found error
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
DEFAULT_GLOB = "walkforward_strategy_eval_*.json"


def _latest_report(glob_pattern: str = DEFAULT_GLOB) -> pathlib.Path:
    """Return the most recently modified walk-forward report."""
    matches = sorted(REPORTS_DIR.glob(glob_pattern), key=lambda p: p.stat().st_mtime)
    if not matches:
        raise FileNotFoundError(f"no reports matching {REPORTS_DIR / glob_pattern}")
    return matches[-1]


def _display_path(path: pathlib.Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def check_report(path: pathlib.Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    artifact_cells = list(payload.get("artifact_cells") or [])
    n_cleaned = payload.get("n_cleaned")
    n_test = payload.get("n_test")
    return {
        "path": _display_path(path),
        "n_cleaned": n_cleaned,
        "n_test": n_test,
        "artifact_cells": artifact_cells,
        "n_artifact_cells": len(artifact_cells),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--report",
        default=None,
        help="Path to a specific walk-forward report JSON (default: latest in reports/).",
    )
    args = ap.parse_args(argv)

    try:
        report_path = pathlib.Path(args.report) if args.report else _latest_report()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not report_path.exists():
        print(f"ERROR: report not found: {report_path}", file=sys.stderr)
        return 2

    res = check_report(report_path)
    print(f"walk-forward report: {res['path']}")
    print(f"  n_cleaned = {res['n_cleaned']}")
    print(f"  n_test     = {res['n_test']}")
    print(f"  artifact_cells = {res['n_artifact_cells']}")

    if res["n_artifact_cells"]:
        print(
            "\nFAIL: frozen-exit artifact cells detected in latest report. "
            "The resolver or report is stale/regressed. List:",
            file=sys.stderr,
        )
        for cell in res["artifact_cells"]:
            print(f"  - {cell}", file=sys.stderr)
        return 1

    print("OK: no artifact cells. Clean resolution.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
