#!/usr/bin/env python3
"""Append one canonical verdict row per asset class.

The schema is frozen so rows are comparable across the 12 class phases:

    class, mechanism, n, ci_low, halves_ok, cost_2x_pf, verdict, blocking_gate

verdict is one of:
    PROVEN CANDIDATE WEAK KILL INSUFFICIENT_N NO_ROWS BLOCKED_DATA

PROVEN is only reachable from forward rows dated after registration, so a
backtest phase can never legitimately emit it. See
docs/audit_review_2026-11-22/PROOF_METHODOLOGY.md section 4.

Usage:
    python3 tools/publish_class_verdict.py '{"class":"ETF","mechanism":"...","n":79,
        "ci_low":-0.266,"halves_ok":false,"cost_2x_pf":1.4256,
        "verdict":"INSUFFICIENT_N","blocking_gate":"n<100"}'
    python3 tools/publish_class_verdict.py --show
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "per_class_edge_verdicts_20261122.json"

VERDICTS = {"PROVEN", "CANDIDATE", "WEAK", "KILL",
            "INSUFFICIENT_N", "NO_ROWS", "BLOCKED_DATA"}
FIELDS = ("class", "mechanism", "n", "ci_low", "halves_ok",
          "cost_2x_pf", "verdict", "blocking_gate")


def add(row: dict) -> dict:
    if row.get("verdict") not in VERDICTS:
        raise ValueError(f"bad verdict {row.get('verdict')!r}; allowed {sorted(VERDICTS)}")
    missing = [f for f in FIELDS if f not in row]
    if missing:
        raise ValueError(f"missing fields {missing}")
    cur = json.loads(OUT.read_text()) if OUT.exists() else {"rows": []}
    cur["rows"] = [r for r in cur["rows"] if r["class"] != row["class"]]
    cur["rows"].append({k: row[k] for k in FIELDS})
    cur["rows"].sort(key=lambda r: r["class"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cur, indent=2) + "\n")
    return cur


def _render(cur: dict) -> None:
    if not cur["rows"]:
        print("(no rows)")
        return
    for r in cur["rows"]:
        print(f"{r['class']:<14}{r['verdict']:<16}"
              f"n={str(r['n']):<7}{r['mechanism'][:40]:<42}{r['blocking_gate'][:50]}")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    arg = sys.argv[1]
    if arg == "--show":
        cur = json.loads(OUT.read_text()) if OUT.exists() else {"rows": []}
        _render(cur)
        return 0
    try:
        row = json.loads(arg)
    except json.JSONDecodeError as exc:
        print(f"argument must be a JSON object: {exc}", file=sys.stderr)
        return 2
    _render(add(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
