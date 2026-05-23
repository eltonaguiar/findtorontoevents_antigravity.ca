#!/usr/bin/env python3
"""
CONSENSUS TIER — High Conviction System-Level Agreement Detector
================================================================
Key insight from workflow audit: when 5+ INDEPENDENT SYSTEMS agree on a
symbol+direction, win rate is 82-100% across 25 closed trades. This is the
GOLDEN SIGNAL.

The critical distinction: SYSTEM-level agreement (alpha_engine, battleground,
copy_trader, kimi, cta_replicator, etc.) is predictive at 82-100% WR.
Strategy-level agreement within one system is ANTI-predictive (herding).

This module:
  1. Reads active picks (or accepts them as argument)
  2. Groups by symbol + direction
  3. Counts UNIQUE source_system agreements
  4. Tags each pick with consensus_count, consensus_tier, consensus_strategies
  5. Writes consensus data to data/consensus_tier_picks.json

Tiers:
  ULTRA    = 5+ unique systems agree  → +15 elite_score, +3 trust_score
  STRONG   = 4 unique systems agree   → +10 elite_score, +2 trust_score
  MODERATE = 3 unique systems agree   → +5 elite_score, +1 trust_score
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"

# ── Tier definitions ──
TIER_ULTRA_MIN = 5
TIER_STRONG_MIN = 4
TIER_MODERATE_MIN = 3

TIER_BONUSES = {
    "ULTRA":    {"elite_score": 15, "trust_score": 3},
    "STRONG":   {"elite_score": 10, "trust_score": 2},
    "MODERATE": {"elite_score": 5,  "trust_score": 1},
}

# ── Normalize system names to root system for dedup ──
# e.g. "multi_asset_copytrader" and "multi_asset_cot" are both "multi_asset"
# but we want to count them as SEPARATE systems since they use different signals.
# Only truly duplicate pipelines should merge.
_SYSTEM_ALIASES = {
    # Add aliases here if two source_systems are truly the same pipeline
    # "multi_asset_copytrader_v2": "multi_asset_copytrader",
}


def _normalize_system(source_system: str) -> str:
    """Return the canonical system name for dedup purposes."""
    s = str(source_system or "").strip()
    return _SYSTEM_ALIASES.get(s, s)


def _normalize_direction(pick: dict) -> str:
    """Extract normalized direction from a pick."""
    d = (pick.get("direction") or pick.get("signal_type") or "").upper()
    if "LONG" in d or "BUY" in d:
        return "LONG"
    if "SHORT" in d or "SELL" in d:
        return "SHORT"
    return d


def _load_consensus_matrix() -> dict | None:
    """Try to load pre-computed consensus matrix if available."""
    path = DATA_DIR / "strategy_consensus_matrix.json"
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def compute_consensus_tiers(picks: list[dict]) -> dict[str, Any]:
    """
    Analyze picks for system-level consensus.

    Returns:
        {
            "consensus_picks": [
                {
                    "symbol": "BTCUSDT",
                    "direction": "LONG",
                    "consensus_count": 5,
                    "consensus_tier": "ULTRA",
                    "consensus_systems": ["alpha_engine", "kimi", ...],
                    "consensus_strategies": ["rsi_macd_4h", "btc_momentum", ...],
                    "consensus_confidence": 0.72,
                    "consensus_avg_pnl": 1.23,
                    "pick_ids": ["id1", "id2", ...],
                }
            ],
            "generated_at": "...",
            "total_picks_analyzed": 87,
            "ultra_count": 1,
            "strong_count": 2,
            "moderate_count": 5,
        }
    """
    # Group picks by (symbol, direction)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for p in picks:
        sym = (p.get("symbol") or "").strip().upper()
        direction = _normalize_direction(p)
        if sym and direction:
            groups[(sym, direction)].append(p)

    consensus_picks = []

    for (sym, direction), group_picks in sorted(groups.items()):
        # Count UNIQUE systems
        system_map: dict[str, list[dict]] = defaultdict(list)
        for p in group_picks:
            source = _normalize_system(p.get("source_system", "unknown"))
            if source and source != "0":  # Skip zeroed source_system
                system_map[source].append(p)

        unique_system_count = len(system_map)

        if unique_system_count < TIER_MODERATE_MIN:
            continue

        # Determine tier
        if unique_system_count >= TIER_ULTRA_MIN:
            tier = "ULTRA"
        elif unique_system_count >= TIER_STRONG_MIN:
            tier = "STRONG"
        else:
            tier = "MODERATE"

        # Collect strategy names (unique)
        strategies = []
        for p in group_picks:
            strat = p.get("strategy", "")
            if strat and strat not in strategies:
                strategies.append(strat)

        # Weighted average confidence (by system, not pick, to avoid one system dominating)
        system_confs = []
        for sys_name, sys_picks in system_map.items():
            avg_conf = sum(float(p.get("confidence", 0) or 0) for p in sys_picks) / len(sys_picks)
            system_confs.append(avg_conf)
        consensus_confidence = sum(system_confs) / len(system_confs) if system_confs else 0

        # Average unrealized PnL
        pnls = [float(p.get("pnl_pct", 0) or 0) for p in group_picks]
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0

        # Pick IDs
        pick_ids = [p.get("id", "") for p in group_picks if p.get("id")]

        # Best entry from group
        entry_prices = [float(p.get("entry_price", 0) or 0) for p in group_picks if p.get("entry_price")]
        avg_entry = sum(entry_prices) / len(entry_prices) if entry_prices else 0

        consensus_picks.append({
            "symbol": sym,
            "direction": direction,
            "consensus_count": unique_system_count,
            "consensus_tier": tier,
            "consensus_systems": sorted(system_map.keys()),
            "consensus_strategies": strategies,
            "consensus_confidence": round(consensus_confidence, 4),
            "consensus_avg_pnl": round(avg_pnl, 3),
            "avg_entry_price": round(avg_entry, 6),
            "num_picks": len(group_picks),
            "pick_ids": pick_ids,
        })

    # Sort: ULTRA first, then STRONG, then MODERATE, then by count desc
    tier_order = {"ULTRA": 0, "STRONG": 1, "MODERATE": 2}
    consensus_picks.sort(key=lambda x: (tier_order.get(x["consensus_tier"], 9), -x["consensus_count"]))

    ultra = sum(1 for c in consensus_picks if c["consensus_tier"] == "ULTRA")
    strong = sum(1 for c in consensus_picks if c["consensus_tier"] == "STRONG")
    moderate = sum(1 for c in consensus_picks if c["consensus_tier"] == "MODERATE")

    return {
        "consensus_picks": consensus_picks,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_picks_analyzed": len(picks),
        "ultra_count": ultra,
        "strong_count": strong,
        "moderate_count": moderate,
    }


def enrich_picks_with_consensus(picks: list[dict]) -> list[dict]:
    """
    Tag each pick with its consensus_count, consensus_tier, and apply bonuses.

    Modifies picks in-place and returns them.
    """
    result = compute_consensus_tiers(picks)
    consensus_picks = result["consensus_picks"]

    # Build lookup: (symbol, direction) -> consensus info
    consensus_lookup: dict[tuple[str, str], dict] = {}
    for cp in consensus_picks:
        key = (cp["symbol"], cp["direction"])
        consensus_lookup[key] = cp

    tagged = 0
    for p in picks:
        sym = (p.get("symbol") or "").strip().upper()
        direction = _normalize_direction(p)
        key = (sym, direction)

        cp = consensus_lookup.get(key)
        if cp:
            p["consensus_count"] = cp["consensus_count"]
            p["consensus_tier"] = cp["consensus_tier"]
            p["consensus_systems"] = cp["consensus_systems"]

            # Apply tier bonuses
            bonuses = TIER_BONUSES.get(cp["consensus_tier"], {})

            # Elite score bonus
            elite_bonus = bonuses.get("elite_score", 0)
            if elite_bonus:
                cur_elite = float(p.get("elite_score", 0) or 0)
                p["elite_score"] = round(cur_elite + elite_bonus, 2)
                p["_consensus_elite_bonus"] = elite_bonus

            # Trust score bonus
            trust_bonus = bonuses.get("trust_score", 0)
            if trust_bonus:
                cur_trust = float(p.get("trust_score", 0) or 0)
                p["trust_score"] = round(cur_trust + trust_bonus, 2)
                p["_consensus_trust_bonus"] = trust_bonus

            tagged += 1
        else:
            p["consensus_count"] = 0
            p["consensus_tier"] = None

    # Save consensus data for dashboard consumption
    try:
        out_path = DATA_DIR / "consensus_tier_picks.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2, default=str)
    except Exception as e:
        print(f"  [CONSENSUS TIER] Warning: could not write {out_path}: {e}")

    print(f"  [CONSENSUS TIER] Analyzed {len(picks)} picks: "
          f"ULTRA={result['ultra_count']}, STRONG={result['strong_count']}, "
          f"MODERATE={result['moderate_count']} | Tagged {tagged} picks with bonuses")

    return picks


def main():
    """Standalone mode: read active_picks.json and compute consensus."""
    picks_path = DATA_DIR / "active_picks.json"
    if not picks_path.exists():
        print(f"No active picks found at {picks_path}")
        return

    with open(picks_path) as f:
        picks = json.load(f)

    result = compute_consensus_tiers(picks)

    print(f"\n{'='*60}")
    print(f"HIGH CONVICTION CONSENSUS TIER ANALYSIS")
    print(f"{'='*60}")
    print(f"Picks analyzed: {result['total_picks_analyzed']}")
    print(f"ULTRA (5+ systems):  {result['ultra_count']}")
    print(f"STRONG (4 systems):  {result['strong_count']}")
    print(f"MODERATE (3 systems): {result['moderate_count']}")
    print()

    for cp in result["consensus_picks"]:
        tier_emoji = {"ULTRA": "***", "STRONG": "**", "MODERATE": "*"}.get(cp["consensus_tier"], "")
        print(f"  {tier_emoji} {cp['symbol']} {cp['direction']} "
              f"[{cp['consensus_tier']}] "
              f"({cp['consensus_count']} systems: {', '.join(cp['consensus_systems'])})")
        print(f"    Strategies: {', '.join(cp['consensus_strategies'][:5])}"
              f"{'...' if len(cp['consensus_strategies']) > 5 else ''}")
        print(f"    Avg Confidence: {cp['consensus_confidence']:.1%} | "
              f"Avg PnL: {cp['consensus_avg_pnl']:+.2f}%")
        print()


if __name__ == "__main__":
    main()
