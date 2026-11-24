#!/usr/bin/env python3
"""Independently re-derive each class verdict stored in the audit3 ledger.

The ledger already records a ``verdict`` per class. This tool recomputes that
verdict from the stored statistics using a documented ladder and reports any
disagreement. It exists so the programme tally cannot silently drift: a stored
verdict that no longer follows from its own numbers is a defect, not a result.

This does NOT produce a new verdict for the programme. It audits the existing
one. Backtest statistics can at best justify CANDIDATE; nothing here can grant
INVESTABLE.

Usage:
    python3 tools/class_verdict_audit.py
    python3 tools/class_verdict_audit.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = (ROOT / "docs" / "audit_review_2026-11-22" / "_raw"
          / "audit3_audit3_ledger.json")

# The real gate is NOT required_n: that is a per-class power figure (COMMODITY
# 24, BOND 831, EQUITY 22,569) answering "how many rows to detect the declared
# floor", and only CRYPTO and COMMODITY clear it. The verdict gate is the flat
# WR_MIN_N in alpha_engine/audit3_tribunal.py:155, mirrored here because that
# module is heavy to import. tests/test_verdict_ladder_constants.py keeps them
# in lockstep, and tests/test_ledger_class_schema.py pins required_n as a field.
MIN_N = 20
PF_KILL_FLOOR = 0.8
CONCENTRATION_CAP = 0.60


def _num(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def rederive(row: dict) -> str:
    """Recompute the ladder verdict from a class row's own statistics."""
    n = int(_num(row.get("n"), 0) or 0)
    if n < MIN_N:
        return "INSUFFICIENT_N"

    ci = row.get("net_ci_pct") or []
    lo = _num(ci[0]) if isinstance(ci, (list, tuple)) and ci else None
    pf = _num(row.get("pf"))

    if lo is None:
        return "UNMEASURABLE"
    if lo <= 0:
        return "KILL" if (pf or 0) < PF_KILL_FLOOR else "WEAK"

    if not row.get("stress_2x_ok"):
        return "CANDIDATE_CAP_2X_COST"

    halves = row.get("split_half") or {}
    if not halves.get("stable"):
        return "CANDIDATE_CAP_HALVES"

    if (_num(row.get("top_symbol_share"), 0) or 0) >= CONCENTRATION_CAP:
        return "CANDIDATE_CAP_CONCENTRATION"

    return "CANDIDATE"


def audit(rows) -> list[dict]:
    """Return one record per class comparing stored vs re-derived verdicts."""
    out = []
    for row in rows:
        stored = row.get("verdict")
        derived = rederive(row)
        out.append({
            "asset_class": row.get("asset_class") or "?",
            "n": row.get("n"),
            "pf": row.get("pf"),
            "net_ci_lo": (row.get("net_ci_pct") or [None])[0],
            "coverage_ok": ((row.get("alpha_gate") or {})
                            .get("alpha_coverage_ok")),
            "stored": stored,
            "rederived": derived,
            "match": stored == derived,
        })
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.ledger)
    if not path.exists():
        print(f"ledger not found: {path}", file=sys.stderr)
        return 2
    ledger = json.loads(path.read_text(encoding="utf-8"))
    rows = audit(ledger.get("classes") or [])
    if args.json:
        print(json.dumps(rows, indent=1))
        return 0
    bad = 0
    for r in rows:
        flag = "OK " if r["match"] else "DRIFT"
        if not r["match"]:
            bad += 1
        print(f"{flag:<6}{r['asset_class']:<12}n={r['n']:<7}"
              f"stored={r['stored']:<14}rederived={r['rederived']}")
    print(f"\n{len(rows)} classes, {bad} mismatch")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
