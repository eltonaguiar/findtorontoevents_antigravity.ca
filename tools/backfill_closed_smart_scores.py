#!/usr/bin/env python3
"""One-time / periodic backfill: add smart_score + quality_tier to closed picks JSON.

Reads ``audit_dashboard/data/dashboard_data.json`` (or ``--input``), recomputes
fields the same way as ``audit_trail.dashboard_generator._closed_pick_with_quality_fields``,
writes ``--output`` (default: overwrite input with ``.bak`` backup).

Usage:
  python tools/backfill_closed_smart_scores.py
  python tools/backfill_closed_smart_scores.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from audit_trail.quality_gates import (  # noqa: E402
    calculate_smart_score,
    classify_pick_quality,
    passes_smart_gate,
)


def _tier_if_still_active(p: dict) -> str:
    p2 = dict(p)
    p2["status"] = "OPEN"
    try:
        return classify_pick_quality(p2)
    except Exception:
        return "ACTIVE"


def _enrich_closed(p: dict) -> dict:
    out = dict(p)
    try:
        out["smart_score"] = float(calculate_smart_score(out))
    except Exception:
        out["smart_score"] = None
    p_open = dict(out)
    p_open["status"] = "OPEN"
    try:
        out["quality_tier"] = classify_pick_quality(p_open)
        out["smart_gate_passed"] = bool(passes_smart_gate(p_open))
    except Exception:
        out["quality_tier"] = _tier_if_still_active(out)
        out["smart_gate_passed"] = False
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input",
        type=Path,
        default=REPO / "audit_dashboard" / "data" / "dashboard_data.json",
    )
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    inp = args.input
    if not inp.exists():
        print(f"Missing input: {inp}", file=sys.stderr)
        return 1
    data = json.loads(inp.read_text(encoding="utf-8", errors="replace"))
    picks = (data.get("picks") or {}).get("recent_closed")
    if not isinstance(picks, list):
        print("No picks.recent_closed array found", file=sys.stderr)
        return 1
    n = len(picks)
    enriched = [_enrich_closed(p) if isinstance(p, dict) else p for p in picks]
    if "picks" not in data:
        data["picks"] = {}
    data["picks"]["recent_closed"] = enriched
    smart_n = sum(1 for p in enriched if isinstance(p, dict) and p.get("smart_gate_passed"))
    print(f"Enriched {n} closed picks; smart_gate_passed count: {smart_n}")
    if args.dry_run:
        return 0
    out = args.output or inp
    if out == inp:
        bak = inp.with_suffix(inp.suffix + ".bak")
        shutil.copy2(inp, bak)
        print(f"Backup: {bak}")
    out.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
