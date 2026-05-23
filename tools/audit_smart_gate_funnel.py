#!/usr/bin/env python3
"""Histogram first-failure reasons for ``passes_smart_gate`` on dashboard active picks.

Loads ``picks.active`` from a dashboard JSON (live export or snapshot), runs
``evaluate_smart_gate_funnel`` per row (deepcopy to avoid mutating file-backed data),
and prints counts by reason code.

Usage:
  python tools/audit_smart_gate_funnel.py
  python tools/audit_smart_gate_funnel.py tools/data/snapshots/dashboard_data_2026-04-07T000149Z.json
"""
from __future__ import annotations

import argparse
import copy
import json
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

for _lg in ("audit_trail.quality_gates", "audit_trail.forward_degradation_tracker"):
    logging.getLogger(_lg).setLevel(logging.CRITICAL)

from audit_trail.quality_gates import evaluate_smart_gate_funnel  # noqa: E402

DEFAULT_DASH = REPO / "audit_dashboard" / "data" / "dashboard_data.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "dashboard",
        nargs="?",
        default=str(DEFAULT_DASH),
        help="Path to dashboard_data.json (default: audit_dashboard/data/dashboard_data.json)",
    )
    ap.add_argument("--out", default="", help="Optional path to write JSON histogram")
    args = ap.parse_args()

    path = Path(args.dashboard)
    if not path.is_file():
        print("missing %s" % path, file=sys.stderr)
        return 1

    with open(path, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    picks = data.get("picks") or {}
    active = picks.get("active") or []
    summary = data.get("summary") or {}

    ctr: Counter[str] = Counter()
    passed = 0
    for raw in active:
        pick = copy.deepcopy(raw)
        ok, reason = evaluate_smart_gate_funnel(pick)
        if ok:
            passed += 1
            ctr["passed"] += 1
        else:
            ctr[reason or "unknown"] += 1

    lines = [
        "dashboard_path: %s" % path,
        "dashboard_generated_at: %s" % (summary.get("generated_at") or data.get("generated_at") or ""),
        "active_count: %d" % len(active),
        "smart_gate_passed: %d" % passed,
        "",
        "first_failure_counts:",
    ]
    for code, n in ctr.most_common():
        lines.append("  %s: %d" % (code, n))
    print("\n".join(lines))

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "dashboard_path": str(path),
            "dashboard_generated_at": summary.get("generated_at") or data.get("generated_at"),
            "active_count": len(active),
            "passed": passed,
            "counts": dict(ctr.most_common()),
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print("wrote %s" % out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
