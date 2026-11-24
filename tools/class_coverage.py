#!/usr/bin/env python3
"""Report per-class alpha coverage against the 50% floor.

A class verdict is only as trustworthy as the fraction of the class it was
measured on. CRYPTO is the case that matters: it is the bulk of the ledger and
the least covered. This tool reports coverage per class and flags any class
below the floor, keeping the ledger's own flag visible next to the arithmetic
so a disagreement between them cannot hide.

Usage:
    python3 tools/class_coverage.py
    python3 tools/class_coverage.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = (ROOT / "docs" / "audit_review_2026-11-22" / "_raw"
          / "audit3_audit3_ledger.json")

COVERAGE_FLOOR_PCT = 50.0


def coverage(row: dict) -> dict:
    """Coverage for one class row, or None-percent when the gate is absent."""
    gate = row.get("alpha_gate")
    if not isinstance(gate, dict):
        return {"coverage_pct": None, "ledger_says_ok": None,
                "below_floor": None}
    try:
        n = int(row.get("n") or 0)
        alpha_n = int(gate.get("alpha_n") or 0)
    except (TypeError, ValueError):
        return {"coverage_pct": None, "ledger_says_ok": gate.get("alpha_coverage_ok"),
                "below_floor": None}
    pct = round(alpha_n / n * 100, 2) if n else 0.0
    return {
        "coverage_pct": pct,
        "ledger_says_ok": gate.get("alpha_coverage_ok"),
        "below_floor": pct < COVERAGE_FLOOR_PCT,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.ledger)
    if not path.exists():
        print(f"ledger not found: {path}", file=sys.stderr)
        return 2
    rows = json.loads(path.read_text(encoding="utf-8")).get("classes") or []
    out = [dict(asset_class=r.get("asset_class"), n=r.get("n"), **coverage(r))
           for r in rows]

    if args.json:
        print(json.dumps(out, indent=1))
        return 0
    print(f"{'class':<12}{'n':>7}{'coverage%':>11}{'below 50%':>11}{'ledger ok':>11}")
    for r in out:
        print(f"{r['asset_class']:<12}{str(r['n']):>7}"
              f"{str(r['coverage_pct']):>11}{str(r['below_floor']):>11}"
              f"{str(r['ledger_says_ok']):>11}")
    bad = [r["asset_class"] for r in out if r["below_floor"]]
    print(f"\nbelow the {COVERAGE_FLOOR_PCT}% floor: {bad or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
