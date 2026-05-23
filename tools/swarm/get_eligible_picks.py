#!/usr/bin/env python3
"""M-010 Phase 2: Filter swarm_picks.json by tier gate before TV paper trading.

Reads ``audit_dashboard/data/swarm_picks.json``, applies
``passes_tier_gate()`` (M-010 Phase 1), and writes the eligible subset to
stdout (JSON array) or ``--out-file``.

Usage:
  # Print eligible picks (strong+ tier, default):
  python tools/swarm/get_eligible_picks.py

  # Change minimum tier:
  python tools/swarm/get_eligible_picks.py --min-tier moderate

  # Filter to open picks only (no outcome yet):
  python tools/swarm/get_eligible_picks.py --open-only

  # Write to file instead of stdout:
  python tools/swarm/get_eligible_picks.py --out-file /tmp/eligible.json

  # Show summary stats (no JSON output):
  python tools/swarm/get_eligible_picks.py --summary

Kill-switch: SWARM_TIER_GATE_ENABLED=0 → all picks pass (fail-open for testing).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.swarm.swarm_pick_schema import (  # noqa: E402
    load_store,
    passes_tier_gate,
)

DEFAULT_PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "swarm_picks.json"


def filter_picks(
    picks: list[dict],
    *,
    min_tier: str = "strong",
    open_only: bool = False,
) -> tuple[list[dict], list[dict]]:
    """Split picks into (eligible, blocked) lists.

    Args:
        picks: Full pick list from swarm_picks.json.
        min_tier: Minimum consensus_tier required to pass.
        open_only: When True, only consider picks with no resolved outcome.

    Returns:
        (eligible, blocked) tuple.
    """
    eligible: list[dict] = []
    blocked: list[dict] = []
    for p in picks:
        if open_only and p.get("outcome") is not None:
            continue
        if passes_tier_gate(p, min_tier=min_tier):
            eligible.append(p)
        else:
            blocked.append(p)
    return eligible, blocked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--picks-path", type=Path, default=DEFAULT_PICKS_PATH,
        help="Path to swarm_picks.json (default: audit_dashboard/data/swarm_picks.json)",
    )
    parser.add_argument(
        "--min-tier", default="strong",
        choices=["control", "single", "moderate", "strong", "unanimous"],
        help="Minimum consensus_tier to pass the gate (default: strong)",
    )
    parser.add_argument(
        "--open-only", action="store_true",
        help="Only include picks with no resolved outcome (outcome=null)",
    )
    parser.add_argument(
        "--out-file", type=Path, default=None,
        help="Write eligible picks JSON to this path instead of stdout",
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="Print summary stats only (no JSON output)",
    )
    args = parser.parse_args()

    picks = load_store(args.picks_path)
    if not picks:
        print(f"# no picks found at {args.picks_path}", file=sys.stderr)
        if not args.summary:
            print("[]")
        return 0

    eligible, blocked = filter_picks(
        picks,
        min_tier=args.min_tier,
        open_only=args.open_only,
    )

    print(
        f"# tier gate (min={args.min_tier}): {len(picks)} total → "
        f"{len(eligible)} eligible, {len(blocked)} blocked",
        file=sys.stderr,
    )
    if args.open_only:
        print(
            f"# (open-only mode: resolved picks excluded from filter scope)",
            file=sys.stderr,
        )

    if args.summary:
        by_tier: dict[str, int] = {}
        for p in picks:
            t = str(p.get("consensus_tier", "unknown"))
            by_tier[t] = by_tier.get(t, 0) + 1
        tier_order = ["unanimous", "strong", "moderate", "single", "control", "unknown"]
        print(f"total picks : {len(picks)}")
        print(f"eligible    : {len(eligible)}")
        print(f"blocked     : {len(blocked)}")
        print(f"min_tier    : {args.min_tier}")
        print()
        print("by tier:")
        for t in tier_order:
            if t in by_tier:
                print(f"  {t:12s} {by_tier[t]:5d}")
        for t in sorted(by_tier):
            if t not in tier_order:
                print(f"  {t:12s} {by_tier[t]:5d}")
        return 0

    out = json.dumps(eligible, indent=2, ensure_ascii=False)
    if args.out_file:
        args.out_file.write_text(out, encoding="utf-8")
        print(f"# wrote {len(eligible)} eligible picks to {args.out_file}", file=sys.stderr)
    else:
        print(out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
