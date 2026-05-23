#!/usr/bin/env python3
"""
Rescore All Picks — standalone script to score every active pick with elite_scorer.

Problem: 64% of active picks have elite_score=0 (unscored) because the ELITE SAFETY NET
in production_scanner.py doesn't always run in the workflow.

Usage:
    python alpha_engine/rescore_all_picks.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# Ensure alpha_engine is importable
_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_DIR))

from elite_scorer import enrich_picks_with_elite_score


def _sanitize(obj):
    """Recursively replace NaN/Infinity with None so json.dump never fails."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if hasattr(obj, "item"):
        v = obj.item()
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    return obj


def main():
    data_dir = _DIR / "data"
    picks_path = data_dir / "active_picks.json"

    if not picks_path.exists():
        print(f"ERROR: {picks_path} not found")
        return 1

    # Load picks
    with open(picks_path, "r", encoding="utf-8") as f:
        picks = json.load(f)

    if not isinstance(picks, list):
        print(f"ERROR: active_picks.json is not a list (got {type(picks).__name__})")
        return 1

    total = len(picks)
    unscored_before = sum(1 for p in picks if not p.get("elite_score"))
    print(f"Loaded {total} active picks ({unscored_before} unscored / elite_score=0)")

    # Score all picks using elite_scorer
    picks = enrich_picks_with_elite_score(picks, data_dir=data_dir)

    # Report results
    unscored_after = sum(1 for p in picks if not p.get("elite_score"))
    scores = [p.get("elite_score", 0) for p in picks]
    max_score = max(scores) if scores else 0
    avg_score = sum(scores) / len(scores) if scores else 0
    nonzero = [s for s in scores if s > 0]

    print(f"\nRescoring complete:")
    print(f"  Total picks:    {total}")
    print(f"  Scored (>0):    {len(nonzero)}")
    print(f"  Still zero:     {unscored_after}")
    print(f"  Max score:      {max_score}")
    print(f"  Avg score:      {avg_score:.1f}")
    if nonzero:
        print(f"  Avg (nonzero):  {sum(nonzero)/len(nonzero):.1f}")
    else:
        print(f"  Avg (nonzero):  N/A")

    # Grade distribution
    grades = {}
    for p in picks:
        g = p.get("elite_grade", "?")
        grades[g] = grades.get(g, 0) + 1
    print(f"  Grades:         {dict(sorted(grades.items()))}")

    # Top 11 picks (ASCII-safe for Windows console)
    picks_sorted = sorted(picks, key=lambda p: p.get("elite_score", 0), reverse=True)
    print("\nTop 11 picks:")
    for i, p in enumerate(picks_sorted[:11], 1):
        sym = str(p.get("symbol", "?")).encode("ascii", "replace").decode("ascii")
        strat = str(p.get("strategy", "?"))[:40].encode("ascii", "replace").decode("ascii")
        print(f"  #{i:2d}  {sym:15s}  score={p.get('elite_score', 0):3d}  "
              f"grade={p.get('elite_grade', '?')}  strategy={strat}")

    # Save back
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(_sanitize(picks), f, indent=2, ensure_ascii=False)

    print(f"\nSaved rescored picks to {picks_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
