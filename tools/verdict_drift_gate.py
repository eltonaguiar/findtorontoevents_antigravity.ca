#!/usr/bin/env python3
"""Fail when a class verdict changes without the change being announced.

The programme has had verdicts move when the ledger refreshed. This gate pins
the stored verdicts to a baseline file and fails on any change to a class that
already existed. A newly appearing class, or one that disappears, is reported
as a note so a scope change does not masquerade as a verdict flip.

Usage:
    python3 tools/verdict_drift_gate.py --baseline reports/verdict_baseline.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.class_verdict_audit import LEDGER  # noqa: E402


def compare(baseline: dict, current: dict) -> tuple[bool, str]:
    problems, notes = [], []
    for cls, was in baseline.items():
        now = current.get(cls)
        if now is None:
            notes.append(f"{cls} disappeared")
        elif now != was:
            problems.append(f"{cls}: {was} -> {now}")
    for cls in current:
        if cls not in baseline:
            notes.append(f"{cls} is new ({current[cls]})")
    if problems:
        return False, "verdict changed: " + "; ".join(problems)
    return True, " ".join(notes) if notes else "no drift"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--ledger", default=str(LEDGER))
    args = ap.parse_args(argv)

    base_path, ledger_path = Path(args.baseline), Path(args.ledger)
    for p in (base_path, ledger_path):
        if not p.exists():
            print(f"missing input: {p}", file=sys.stderr)
            return 2

    baseline = json.loads(base_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    current = {r.get("asset_class"): r.get("verdict")
               for r in ledger.get("classes") or []}
    ok, msg = compare(baseline, current)
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
