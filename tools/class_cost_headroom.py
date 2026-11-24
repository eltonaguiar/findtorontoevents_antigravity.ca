#!/usr/bin/env python3
"""How much cost a class can absorb before its measured edge reaches zero.

Reads only stored ledger statistics: ``net_ci_pct`` (already net of cost) and
``pf_cost_pct`` (the cost actually charged). The headroom is how far the CI's
lower bound sits above zero; if the measured cost already exceeds that headroom,
the class dies under any wider spread.

Usage:
    python3 tools/class_cost_headroom.py
    python3 tools/class_cost_headroom.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = (ROOT / "docs" / "audit_review_2026-11-22" / "_raw"
          / "audit3_audit3_ledger.json")


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def headroom(row: dict) -> dict:
    ci = row.get("net_ci_pct") or []
    lo = _num(ci[0]) if isinstance(ci, (list, tuple)) and ci else 0.0
    cost = _num(row.get("pf_cost_pct"))
    h = round(lo, 4) if lo > 0 else 0.0
    return {
        "headroom_pct": h,
        "cost_pct": round(cost, 4),
        "cost_exceeds_headroom": cost > h,
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
    out = [dict(asset_class=r.get("asset_class"), **headroom(r)) for r in rows]
    if args.json:
        print(json.dumps(out, indent=1))
        return 0
    for r in out:
        flag = " DIES" if r["cost_exceeds_headroom"] else ""
        print(f"{r['asset_class']:<12}headroom={r['headroom_pct']:<9}"
              f"cost={r['cost_pct']}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
