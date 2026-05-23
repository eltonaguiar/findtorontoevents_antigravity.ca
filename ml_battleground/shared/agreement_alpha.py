#!/usr/bin/env python3
"""
Agreement Alpha: System A (XGBoost) + System C (GRU-Attention) consensus filter.
When both systems agree on direction for the same symbol, confidence is boosted.
When they disagree, the pick is suppressed.

Based on ML Audit recommendation: "Agreement Alpha filters 60-70% noise"
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
SYSTEM_A_DASHBOARD = BASE_DIR / "system_a_filter" / "data" / "dashboard.json"
SYSTEM_C_DASHBOARD = BASE_DIR / "system_c_deeplearn" / "data" / "dashboard.json"
OUTPUT_DIR = BASE_DIR / "ensemble_data"
OUTPUT_FILE = OUTPUT_DIR / "agreement_alpha_picks.json"

# ── Configuration ─────────────────────────────────────────────────────
CONFIDENCE_BOOST = 0.15  # +15% when both systems agree


def _load_dashboard(path: Path) -> Optional[Dict[str, Any]]:
    """Load a dashboard.json file, returning None on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("Dashboard not found: %s", path)
        return None
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in %s: %s", path, e)
        return None


def _extract_picks(dashboard: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract active picks from a dashboard.

    Checks for 'active_picks' key (the standard field in both System A and C).
    Falls back to 'picks' or 'active' if present.
    """
    for key in ("active_picks", "picks", "active"):
        picks = dashboard.get(key)
        if picks is not None:
            return picks if isinstance(picks, list) else []
    return []


def _normalize_symbol(symbol: str) -> str:
    """Normalize symbol name for matching (uppercase, strip whitespace)."""
    return symbol.strip().upper()


def _get_direction(pick: Dict[str, Any]) -> Optional[str]:
    """
    Extract direction from a pick dict.

    System A uses 'signal_type' (BUY/SELL).
    System C also uses 'signal_type'.
    Fallback to 'direction'.
    """
    direction = pick.get("signal_type") or pick.get("direction")
    if direction:
        return direction.strip().upper()
    return None


def _get_confidence(pick: Dict[str, Any]) -> float:
    """Extract confidence from a pick, checking multiple field names."""
    for key in ("confidence", "ml_score", "meta_confidence"):
        val = pick.get(key)
        if val is not None:
            return float(val)
    return 0.5  # default


def run_agreement_filter() -> List[Dict[str, Any]]:
    """
    Run the Agreement Alpha consensus filter.

    1. Load System A and System C active picks.
    2. For matching symbols:
       - AGREE on direction: boost confidence +15%, tag agreement_alpha=true
       - DISAGREE on direction: suppress (exclude from output)
    3. For symbols only in one system: pass through with agreement_alpha="single"
    4. Save results to ensemble_data/agreement_alpha_picks.json

    Returns
    -------
    List of consensus picks (dicts).
    """
    # Load dashboards
    dashboard_a = _load_dashboard(SYSTEM_A_DASHBOARD)
    dashboard_c = _load_dashboard(SYSTEM_C_DASHBOARD)

    picks_a = _extract_picks(dashboard_a) if dashboard_a else []
    picks_c = _extract_picks(dashboard_c) if dashboard_c else []

    logger.info(
        "Agreement Alpha: System A has %d active picks, System C has %d active picks",
        len(picks_a), len(picks_c),
    )

    # Index System C picks by normalized symbol for O(1) lookup
    c_by_symbol: Dict[str, Dict[str, Any]] = {}
    for pick in picks_c:
        sym = _normalize_symbol(pick.get("symbol", ""))
        if sym:
            c_by_symbol[sym] = pick

    # Track which System C symbols were matched (to find C-only picks later)
    matched_c_symbols = set()

    consensus_picks: List[Dict[str, Any]] = []

    # Process System A picks
    for pick_a in picks_a:
        sym = _normalize_symbol(pick_a.get("symbol", ""))
        if not sym:
            continue

        dir_a = _get_direction(pick_a)
        conf_a = _get_confidence(pick_a)

        if sym in c_by_symbol:
            # Both systems have a pick for this symbol
            pick_c = c_by_symbol[sym]
            dir_c = _get_direction(pick_c)
            conf_c = _get_confidence(pick_c)
            matched_c_symbols.add(sym)

            if dir_a and dir_c and dir_a == dir_c:
                # AGREE: boost confidence, merge into consensus pick
                boosted_confidence = min(0.99, max(conf_a, conf_c) + CONFIDENCE_BOOST)
                consensus_pick = {
                    **pick_a,
                    "confidence": round(boosted_confidence, 4),
                    "agreement_alpha": True,
                    "agreement_detail": {
                        "system_a_confidence": conf_a,
                        "system_c_confidence": conf_c,
                        "original_max_confidence": max(conf_a, conf_c),
                        "boost_applied": CONFIDENCE_BOOST,
                        "agreed_direction": dir_a,
                    },
                    "source_systems": ["system_a_filter", "system_c_deeplearn"],
                }
                consensus_picks.append(consensus_pick)
                logger.info(
                    "AGREE %s %s: A=%.2f C=%.2f -> boosted=%.4f",
                    sym, dir_a, conf_a, conf_c, boosted_confidence,
                )
            else:
                # DISAGREE: suppress
                logger.info(
                    "DISAGREE %s: A=%s(%.2f) vs C=%s(%.2f) -> SUPPRESSED",
                    sym, dir_a, conf_a, dir_c, conf_c,
                )
        else:
            # Only System A has this pick — pass through
            single_pick = {
                **pick_a,
                "agreement_alpha": "single",
                "source_systems": ["system_a_filter"],
            }
            consensus_picks.append(single_pick)
            logger.info("SINGLE-A %s %s: conf=%.2f (no System C pick)", sym, dir_a, conf_a)

    # Process System C picks that weren't matched
    for pick_c in picks_c:
        sym = _normalize_symbol(pick_c.get("symbol", ""))
        if not sym or sym in matched_c_symbols:
            continue

        dir_c = _get_direction(pick_c)
        conf_c = _get_confidence(pick_c)

        single_pick = {
            **pick_c,
            "agreement_alpha": "single",
            "source_systems": ["system_c_deeplearn"],
        }
        consensus_picks.append(single_pick)
        logger.info("SINGLE-C %s %s: conf=%.2f (no System A pick)", sym, dir_c, conf_c)

    # Build output payload
    output = {
        "filter": "agreement_alpha",
        "description": "System A (XGBoost) + System C (GRU-Attention) consensus filter",
        "updated": datetime.now(timezone.utc).isoformat(),
        "system_a_picks_count": len(picks_a),
        "system_c_picks_count": len(picks_c),
        "consensus_picks_count": len(consensus_picks),
        "agreed_count": sum(1 for p in consensus_picks if p.get("agreement_alpha") is True),
        "single_count": sum(1 for p in consensus_picks if p.get("agreement_alpha") == "single"),
        "suppressed_count": (
            len(picks_a) + len(picks_c)
            - len(consensus_picks)
            - sum(1 for s in matched_c_symbols)  # matched C symbols counted in A loop
        ),
        "consensus_picks": consensus_picks,
    }

    # Save to disk
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, default=str)
        logger.info("Saved %d consensus picks to %s", len(consensus_picks), OUTPUT_FILE)
    except Exception as e:
        logger.error("Failed to save consensus picks: %s", e)

    return consensus_picks


# ── Standalone Runner ────────────────────────────────────────────────
def main():
    """Run agreement filter and print summary."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    picks = run_agreement_filter()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n{'='*70}")
    print(f"  AGREEMENT ALPHA — A+C Consensus Filter  |  {ts}")
    print(f"  'Filters 60-70% noise' — ML Audit recommendation")
    print(f"{'='*70}")

    if not picks:
        print("\n  No consensus picks (both systems have empty active_picks).")
    else:
        for p in picks:
            sym = p.get("symbol", "?")
            direction = _get_direction(p) or "?"
            conf = p.get("confidence", 0)
            tag = p.get("agreement_alpha", "?")
            sources = p.get("source_systems", [])

            if tag is True:
                detail = p.get("agreement_detail", {})
                print(f"\n  {sym} — {direction} — AGREED")
                print(f"    Boosted confidence: {conf:.1%}")
                print(f"    System A: {detail.get('system_a_confidence', 0):.1%}")
                print(f"    System C: {detail.get('system_c_confidence', 0):.1%}")
            else:
                print(f"\n  {sym} — {direction} — SINGLE ({', '.join(sources)})")
                print(f"    Confidence: {conf:.1%}")

    print(f"\n{'='*70}")
    print(f"  Total consensus picks: {len(picks)}")
    print(f"  Output: {OUTPUT_FILE}")
    print(f"{'='*70}\n")

    return picks


if __name__ == "__main__":
    main()
