#!/usr/bin/env python3
"""
Derive pair-level exception candidates from recent_closed pick data (B19).

Scans the dashboard's recent_closed pool for (strategy, symbol, direction)
combinations that meet the registry admission criteria:
  - Wilson 95% lower bound >= 60%
  - n >= 20 closed picks

Usage:
    python tools/derive_pair_exceptions.py [--min-n N] [--min-wilson-lb LB]
    python tools/derive_pair_exceptions.py --check-current

The tool PROPOSES candidates; it does NOT auto-write to pair_exceptions.py.
New entries require a code-change PR with operator sign-off per B19 protocol.

Output: prints a table of candidates to stdout and writes a machine-readable
JSON to reports/pair_exception_candidates_<date>.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from math import sqrt
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_DATA = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
REPORTS_DIR = REPO_ROOT / "reports"

# Ensure repo root is importable regardless of working directory
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def wilson_lower_bound(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    lb = (p + z * z / (2 * n) - z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (
        1 + z * z / n
    )
    return round(lb * 100, 1)


def load_recent_closed() -> list[dict]:
    data = json.loads(DASHBOARD_DATA.read_text(encoding="utf-8"))
    return data.get("picks", {}).get("recent_closed", [])


def compute_candidates(
    picks: list[dict],
    min_n: int = 20,
    min_wilson_lb: float = 60.0,
) -> list[dict]:
    stats: dict[tuple, dict] = defaultdict(lambda: {"wins": 0, "total": 0})
    for p in picks:
        strat = str(p.get("strategy") or "").strip()
        sym = str(p.get("symbol") or "").upper().strip()
        dirn = str(p.get("direction") or p.get("signal_type") or "").upper().strip()
        if not strat or not sym or not dirn:
            continue
        key = (strat, sym, dirn)
        stats[key]["total"] += 1
        if str(p.get("status") or "").upper() == "WON":
            stats[key]["wins"] += 1

    candidates = []
    for (strat, sym, dirn), s in stats.items():
        n = s["total"]
        wins = s["wins"]
        if n < min_n:
            continue
        wr = 100.0 * wins / n
        lb = wilson_lower_bound(wins, n)
        if lb < min_wilson_lb:
            continue
        candidates.append(
            {
                "strategy": strat,
                "symbol": sym,
                "direction": dirn,
                "n": n,
                "wr_pct": round(wr, 1),
                "wilson_lb_pct": lb,
            }
        )

    candidates.sort(key=lambda x: (-x["wilson_lb_pct"], -x["n"]))
    return candidates


def check_current_registry(candidates: list[dict]) -> None:
    try:
        from alpha_engine.pair_exceptions import PAIR_EXCEPTIONS
        existing = {
            (e.strategy.lower(), e.symbol.upper(), e.direction.upper())
            for e in PAIR_EXCEPTIONS
        }
    except ImportError:
        existing = set()

    print("\n=== Registry membership ===")
    for c in candidates:
        key = (c["strategy"].lower(), c["symbol"].upper(), c["direction"].upper())
        status = "IN REGISTRY" if key in existing else "NOT IN REGISTRY"
        print(f"  {status}: {c['strategy']} {c['symbol']} {c['direction']} "
              f"n={c['n']} WR={c['wr_pct']}% lb={c['wilson_lb_pct']}%")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-n", type=int, default=20,
                        help="Minimum closed picks per pair (default: 20)")
    parser.add_argument("--min-wilson-lb", type=float, default=60.0,
                        help="Minimum Wilson 95%% lower bound %% (default: 60.0)")
    parser.add_argument("--check-current", action="store_true",
                        help="Also show registry membership for each candidate")
    args = parser.parse_args()

    if not DASHBOARD_DATA.exists():
        print(f"ERROR: {DASHBOARD_DATA} not found", file=sys.stderr)
        sys.exit(1)

    picks = load_recent_closed()
    candidates = compute_candidates(picks, min_n=args.min_n, min_wilson_lb=args.min_wilson_lb)

    if not candidates:
        print(f"No candidates found (min_n={args.min_n}, min_wilson_lb={args.min_wilson_lb}%)")
        return

    print(f"\n{'Strategy':<30} {'Symbol':<12} {'Dir':<5} {'n':>5} {'WR%':>6} {'lb%':>6}")
    print("-" * 68)
    for c in candidates:
        print(
            f"{c['strategy']:<30} {c['symbol']:<12} {c['direction']:<5} "
            f"{c['n']:>5} {c['wr_pct']:>6.1f} {c['wilson_lb_pct']:>6.1f}"
        )

    if args.check_current:
        check_current_registry(candidates)

    # Write JSON artifact
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = REPORTS_DIR / f"pair_exception_candidates_{date_str}.json"
    out_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "min_n": args.min_n,
                "min_wilson_lb_pct": args.min_wilson_lb,
                "candidates": candidates,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nArtifact written: {out_path}")
    print(
        "\nNOTE: These are PROPOSALS only. To add an entry, open a code-change PR "
        "modifying alpha_engine/pair_exceptions.py — operator sign-off required."
    )


if __name__ == "__main__":
    main()
