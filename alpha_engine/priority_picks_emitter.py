"""Priority Picks Emitter — Layer 2.5 emission point for flagship picks.

Re-created 2026-06-01 after silent file revert (P0 §15 Trap #2 dedup + Trap #3
forward_test shim fixes in flight).

Usage:
    python -m alpha_engine.priority_picks_emitter --dry-run
    python -m alpha_engine.priority_picks_emitter --output alpha_engine/data/priority_picks.json

Wire-Up:
    Called by alpha-engine-daily-picks.yml (indirect via alpha_engine.main)
    and can be invoked standalone for the 13:30 UTC emission window.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alpha_engine.eight_class_flagship_strategies import generate_all_flagship_picks
from alpha_engine.academic_strategies_emitter import generate_academic_picks

try:
    from alpha_engine.june2026_research_candidates import generate_forward_observation_picks
except ImportError:
    generate_forward_observation_picks = None  # type: ignore

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "data" / "priority_picks.json"


def _filter_protocol(picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Final Layer 2.5 gate before emission (redundant safety)."""
    kept: list[dict[str, Any]] = []
    for p in picks:
        score = int(p.get("score", 0))
        trust = int(p.get("trust", 0))
        conf = float(p.get("confidence", 0))
        direction = str(p.get("direction", "LONG")).upper()
        if score < 40:
            continue
        if trust < 4:
            continue
        if direction in ("LONG", "BUY", "YES") and conf >= 0.90:
            continue
        kept.append(p)
    return kept


def _deduplicate_across_sources(picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep highest-confidence pick per (symbol, direction, strategy).

    2026-06-01 fix: key was previously (symbol, direction) which collapsed
    every academic strategy emitting the same symbol/direction into a single
    pick, destroying per-strategy attribution before the picks reached the
    DB writer. Including `strategy` preserves per-strategy diversity so each
    of the 30+ academic strategies can be measured independently in pf_registry.
    """
    best: dict[tuple[str, str, str], dict[str, Any]] = {}
    for p in picks:
        sym = str(p.get("symbol", "")).strip().upper()
        direction = str(p.get("direction") or p.get("signal_type") or "LONG").strip().upper()
        direction = "SHORT" if direction in ("SELL", "SHORT") else "LONG"
        strategy = str(p.get("strategy", "")).strip()
        key = (sym, direction, strategy)
        conf = float(p.get("confidence") or 0)
        if key not in best or conf > float(best[key].get("confidence") or 0):
            best[key] = p
    return list(best.values())


def emit_picks(
    output_path: Path | None = None,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """Generate, dedup, gate, and optionally write priority picks."""
    logger.info("PriorityPicksEmitter starting...")
    flagship = generate_all_flagship_picks()
    academic = generate_academic_picks()
    forward_obs: list[dict[str, Any]] = []
    if generate_forward_observation_picks is not None:
        import os
        if os.environ.get("JUNE2026_FORWARD_OBSERVATION", "1").strip().lower() not in (
            "0", "false", "off",
        ):
            forward_obs = generate_forward_observation_picks()
            logger.info("June2026 forward observation picks: %d", len(forward_obs))
    combined = flagship + academic + forward_obs
    deduped = _deduplicate_across_sources(combined)
    picks = _filter_protocol(deduped)

    if not picks:
        logger.warning("Zero picks survived gating.")
        return []

    # Enrich with emission metadata
    for p in picks:
        p.setdefault("emitted_at", datetime.now(timezone.utc).isoformat())
        p.setdefault("emitter", "priority_picks_emitter_v1")
        # P0 §15 dedup harmonization (TON-validated 2026-06-01): inject canonical ID at emission
        # so downstream writers (and at_pick_outcomes) receive the unified key by construction.
        from alpha_engine.dedup import build_canonical_outcomes_pick_id
        p.setdefault("id", build_canonical_outcomes_pick_id(p))

    if dry_run:
        logger.info("DRY-RUN: would emit %d picks", len(picks))
        for p in picks[:10]:
            logger.info(
                "  %-10s %-6s score=%d trust=%d conf=%.2f strat=%s",
                p.get("symbol", ""),
                p.get("direction", ""),
                p.get("score", 0),
                p.get("trust", 0),
                p.get("confidence", 0),
                p.get("strategy", ""),
            )
        if len(picks) > 10:
            logger.info("  ... and %d more", len(picks) - 10)
        return picks

    out = output_path or DEFAULT_OUTPUT
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)
    logger.info("Wrote %d picks to %s", len(picks), out)
    return picks


def main() -> int:
    parser = argparse.ArgumentParser(description="Priority Picks Emitter")
    parser.add_argument("--dry-run", action="store_true", help="Print picks, do not write")
    parser.add_argument("--output", type=Path, default=None, help="Output JSON path")
    parser.add_argument("--verbose", action="store_true", help="DEBUG logging")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    picks = emit_picks(output_path=args.output, dry_run=args.dry_run)
    if not picks:
        print("\nZero priority picks emitted.")
        return 1

    print(f"\n{'Symbol':<10} {'Dir':<6} {'Score':<6} {'Trust':<6} {'Conf':<6} {'Strategy':<30}")
    print("-" * 70)
    for p in picks[:20]:
        print(
            f"{p.get('symbol',''):<10} "
            f"{p.get('direction',''):<6} "
            f"{p.get('score',0):<6} "
            f"{p.get('trust',0):<6} "
            f"{p.get('confidence',0):<6.2f} "
            f"{p.get('strategy','')[:28]:<30}"
        )
    if len(picks) > 20:
        print(f"... and {len(picks)-20} more")
    print(f"\nTotal: {len(picks)} picks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
