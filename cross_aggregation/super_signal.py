#!/usr/bin/env python3
"""
Super Signal Engine — Cross-Pair / Cross-System Consensus Detector

A "Super Signal" fires when multiple crypto pairs AND multiple systems
all agree on the same market direction. When this happens, the trade
has historically had a much higher probability of success.

Conditions for a SUPER signal:
  1. Cross-pair consensus:  >= 60% of tracked symbols lean same direction
  2. Cross-system consensus: >= 2 independent systems agree on at least 1 symbol
  3. Optional: cross-timeframe (future - needs multi-TF data)

Output: super_signals.json with high-conviction picks + market-wide direction.
"""

from __future__ import annotations

import json
import pathlib
import datetime as dt
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CROSS_PAIR_THRESHOLD = 0.60    # 60% of symbols must lean same direction
MIN_SYSTEM_AGREEMENT = 2       # At least 2 systems must agree per symbol
MIN_SYMBOLS_FOR_SIGNAL = 4     # Need at least 4 symbols with active picks
OUTPUT_PATH = pathlib.Path("cross_aggregation/data/super_signals.json")

# Reuse the aggregator's system paths
try:
    from cross_aggregation.aggregator import SYSTEMS as AGG_SYSTEMS, DEMOTED_SYSTEMS
except ImportError:
    AGG_SYSTEMS = {}
    DEMOTED_SYSTEMS = set()

try:
    from cross_aggregation.system_trust_registry import get_vote_weight, get_tier, TIER_BANNED
except ImportError:
    def get_vote_weight(s): return 1.0
    def get_tier(s): return "WATCH"
    TIER_BANNED = "BANNED"

# Conflict lessons engine — applies historical resolution rules
try:
    from cross_aggregation.conflict_lessons_engine import (
        apply_conflict_rules,
        annotate_pick,
        should_suppress_signal as lessons_should_suppress,
        get_trust_weight as lessons_trust_weight,
        check_stale_signals,
    )
    _LESSONS_AVAILABLE = True
except ImportError:
    _LESSONS_AVAILABLE = False


def _normalize_symbol(s: str) -> str:
    """Normalize symbol to XXXUSDT format."""
    s = s.strip().upper().replace("-", "").replace("/", "")
    if s.endswith("USD") and not s.endswith("USDT"):
        s += "T"
    return s


def _load_all_active_picks(root: pathlib.Path) -> Dict[str, List[dict]]:
    """Load active picks from all systems. Returns {system_id: [picks]}."""
    results = {}
    for sys_id, rel_path in AGG_SYSTEMS.items():
        if sys_id in DEMOTED_SYSTEMS:
            continue
        fpath = root / rel_path
        if not fpath.exists():
            continue
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            picks = data if isinstance(data, list) else data.get("active_picks", data.get("activePicks", []))
            if picks:
                results[sys_id] = picks
        except (json.JSONDecodeError, OSError):
            continue
    return results


def _extract_direction(pick: dict) -> Optional[str]:
    """Extract normalized direction (LONG/SHORT) from a pick."""
    d = (pick.get("direction") or pick.get("signal_type") or
         pick.get("signal") or "").upper()
    if "LONG" in d or "BUY" in d:
        return "LONG"
    elif "SHORT" in d or "SELL" in d:
        return "SHORT"
    return None


def _pick_confidence_static(pick: dict) -> float:
    """Extract confidence from a pick dict, handling None values."""
    for key in ("confidence", "ml_score", "sentiment_score"):
        val = pick.get(key)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                continue
    return 0.5


def _extract_symbol(pick: dict) -> Optional[str]:
    """Extract normalized symbol from a pick."""
    s = pick.get("symbol") or pick.get("pair") or pick.get("name") or ""
    if not s:
        return None
    return _normalize_symbol(s)


def detect_super_signals(root: pathlib.Path) -> dict:
    """
    Main detection logic. Returns a dict with:
      - market_direction: overall bias (LONG/SHORT/NEUTRAL)
      - cross_pair_ratio: % of symbols leaning in the dominant direction
      - super_signals: list of high-conviction individual picks
      - symbol_breakdown: per-symbol system agreement details
    """
    all_picks = _load_all_active_picks(root)

    if not all_picks:
        return _empty_result("No active picks found across any system")

    # Build symbol -> [(system_id, direction, pick)] map
    symbol_map: Dict[str, List[Tuple[str, str, dict]]] = defaultdict(list)

    for sys_id, picks in all_picks.items():
        for pick in picks:
            sym = _extract_symbol(pick)
            direction = _extract_direction(pick)
            if sym and direction:
                symbol_map[sym].append((sys_id, direction, pick))

    active_symbols = len(symbol_map)
    if active_symbols < MIN_SYMBOLS_FOR_SIGNAL:
        return _empty_result(
            f"Only {active_symbols} symbols have active picks "
            f"(need {MIN_SYMBOLS_FOR_SIGNAL})"
        )

    # Count dominant direction per symbol — DEDUPLICATED by system
    # Each system gets exactly ONE vote per symbol (highest confidence wins)
    symbol_directions = {}
    for sym, entries in symbol_map.items():
        # Deduplicate: keep best entry per (system, direction) pair
        best_per_system: Dict[str, Tuple[str, str, dict]] = {}
        for e in entries:
            sys_id = e[0]
            # Skip BANNED systems entirely (predictions, system A/B/C, ensemble)
            if get_tier(sys_id) == TIER_BANNED:
                continue
            if sys_id not in best_per_system:
                best_per_system[sys_id] = e
            else:
                # Keep the one with higher confidence
                old_conf = _pick_confidence_static(best_per_system[sys_id][2])
                new_conf = _pick_confidence_static(e[2])
                if new_conf > old_conf:
                    best_per_system[sys_id] = e

        unique_entries = list(best_per_system.values())
        if not unique_entries:
            continue  # All systems were BANNED

        # Trust-weighted vote counting (replaces raw Counter)
        # PROVEN systems get 2.0 votes, RELIABLE 1.5, WATCH 1.0, UNTRUSTED 0.3
        weighted_long = 0.0
        weighted_short = 0.0
        raw_long = 0
        raw_short = 0
        for e in unique_entries:
            sys_id, direction = e[0], e[1]
            weight = get_vote_weight(sys_id)
            if direction == "LONG":
                weighted_long += weight
                raw_long += 1
            else:
                weighted_short += weight
                raw_short += 1

        if weighted_long >= weighted_short:
            dominant_dir = ("LONG", raw_long)
        else:
            dominant_dir = ("SHORT", raw_short)

        # Extract per-system strategy names, directions, and trust tiers
        system_details = []
        for sys_id, entry in best_per_system.items():
            strat = entry[2].get("strategy") or entry[2].get("strategy_name") or ""
            system_details.append({
                "system": sys_id,
                "direction": entry[1],
                "strategy": strat,
                "trust_tier": get_tier(sys_id),
                "vote_weight": get_vote_weight(sys_id),
            })

        symbol_directions[sym] = {
            "dominant": dominant_dir[0],
            "count": dominant_dir[1],
            "total_systems": len(unique_entries),
            "long_count": raw_long,
            "short_count": raw_short,
            "weighted_long": round(weighted_long, 1),
            "weighted_short": round(weighted_short, 1),
            "systems": list(best_per_system.keys()),
            "system_details": system_details,
        }

    # Replace symbol_map entries with deduplicated versions for downstream use
    for sym, entries in symbol_map.items():
        best_per_system = {}
        for e in entries:
            sys_id = e[0]
            if sys_id not in best_per_system:
                best_per_system[sys_id] = e
            else:
                old_conf = _pick_confidence_static(best_per_system[sys_id][2])
                new_conf = _pick_confidence_static(e[2])
                if new_conf > old_conf:
                    best_per_system[sys_id] = e
        symbol_map[sym] = list(best_per_system.values())

    # Cross-pair consensus: what % of symbols lean in the same direction?
    overall_dir_counter = Counter(
        v["dominant"] for v in symbol_directions.values()
    )
    market_dominant = overall_dir_counter.most_common(1)[0]
    market_direction = market_dominant[0]
    market_count = market_dominant[1]
    cross_pair_ratio = market_count / active_symbols

    # Find symbols where multiple systems agree (super signal candidates)
    super_signals = []
    for sym, info in symbol_directions.items():
        agree_count = info["long_count"] if info["dominant"] == "LONG" else info["short_count"]
        if agree_count >= MIN_SYSTEM_AGREEMENT and info["dominant"] == market_direction:
            # Get the best pick (highest confidence) from agreeing systems
            # symbol_map is already deduplicated — one entry per system
            agreeing_entries = [
                e for e in symbol_map[sym] if e[1] == market_direction
            ]

            best_pick = max(
                agreeing_entries,
                key=lambda e: _pick_confidence_static(e[2]),
            )

            confidence = _pick_confidence_static(best_pick[2])

            # Boost confidence based on agreement breadth
            boost = 0.05 * (agree_count - 1) + 0.10 * (cross_pair_ratio - 0.5)
            boosted = min(confidence + boost, 0.99)

            entry_price = (
                best_pick[2].get("entry_price") or
                best_pick[2].get("entryPrice") or
                best_pick[2].get("entry") or
                best_pick[2].get("price", 0)
            )
            tp = (
                best_pick[2].get("take_profit") or
                best_pick[2].get("targetPrice") or
                best_pick[2].get("tp_price") or
                best_pick[2].get("tp", 0)
            )
            sl = (
                best_pick[2].get("stop_loss") or
                best_pick[2].get("stopPrice") or
                best_pick[2].get("sl_price") or
                best_pick[2].get("sl", 0)
            )

            super_signals.append({
                "symbol": sym,
                "direction": market_direction,
                "confidence": round(boosted, 3),
                "raw_confidence": round(confidence, 3),
                "entry_price": entry_price,
                "take_profit": tp,
                "stop_loss": sl,
                "agreeing_systems": sorted(set(e[0] for e in agreeing_entries)),
                "agreement_count": agree_count,
                "cross_pair_ratio": round(cross_pair_ratio, 3),
                "signal_tier": "SUPER" if cross_pair_ratio >= 0.70 and agree_count >= 3 else "STRONG",
                "source_system": best_pick[0],
            })

    # Sort by agreement count, then confidence
    super_signals.sort(
        key=lambda s: (s["agreement_count"], s["confidence"]),
        reverse=True,
    )

    now_iso = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    # Stamp each pick with generated_at and a descriptive strategy name
    for sig in super_signals:
        sig["generated_at"] = now_iso
        tier = sig.get("signal_tier", "consensus").lower()
        src = sig.get("source_system", "")
        sig["strategy"] = f"super signal ({tier})" + (f" via {src}" if src else "")

    # -----------------------------------------------------------------------
    # Conflict Lessons Engine: annotate each super signal with resolution data
    # -----------------------------------------------------------------------
    conflict_summary = {}
    if _LESSONS_AVAILABLE:
        for sig in super_signals:
            sym = sig["symbol"]
            # Build signals_dict from the per-symbol breakdown
            sym_info = symbol_directions.get(sym, {})
            sys_details = sym_info.get("system_details", [])
            if not sys_details:
                continue

            signals_for_rules = {
                d["system"]: d["direction"] for d in sys_details
            }

            # Apply conflict resolution rules
            conflict_result = apply_conflict_rules(sym, signals_for_rules)

            # Attach conflict resolution data to the signal
            sig["conflict_resolution"] = {
                "recommended_direction": conflict_result["recommended_direction"],
                "conflict_confidence": conflict_result["confidence"],
                "rules_applied": conflict_result["rules_applied"],
                "overrides": conflict_result["overrides"],
                "warnings": conflict_result["warnings"],
                "suppressed_systems": conflict_result["suppressed_systems"],
            }

            # If conflict resolution disagrees with the consensus, flag it
            if conflict_result["recommended_direction"] != sig["direction"]:
                sig["conflict_resolution"]["direction_conflict"] = True
                sig["conflict_resolution"]["conflict_note"] = (
                    f"Consensus says {sig['direction']} but conflict rules "
                    f"recommend {conflict_result['recommended_direction']}"
                )

            # Also annotate the pick itself
            annotate_pick(sig)

            conflict_summary[sym] = {
                "consensus_dir": sig["direction"],
                "lessons_dir": conflict_result["recommended_direction"],
                "aligned": conflict_result["recommended_direction"] == sig["direction"],
                "rules_count": len(conflict_result["rules_applied"]),
                "warnings_count": len(conflict_result["warnings"]),
            }

    result = {
        "generated_at": now_iso,
        "market_direction": market_direction if cross_pair_ratio >= CROSS_PAIR_THRESHOLD else "NEUTRAL",
        "cross_pair_ratio": round(cross_pair_ratio, 3),
        "active_symbols": active_symbols,
        "systems_reporting": len(all_picks),
        "super_signals": super_signals,
        "symbol_breakdown": {
            sym: {
                "dominant_direction": info["dominant"],
                "system_agreement": info["total_systems"],
                "long": info["long_count"],
                "short": info["short_count"],
                "systems": info["systems"],
                "system_details": info.get("system_details", []),
            }
            for sym, info in sorted(
                symbol_directions.items(),
                key=lambda x: x[1]["total_systems"],
                reverse=True,
            )
        },
        "thresholds": {
            "cross_pair_threshold": CROSS_PAIR_THRESHOLD,
            "min_system_agreement": MIN_SYSTEM_AGREEMENT,
            "min_symbols": MIN_SYMBOLS_FOR_SIGNAL,
        },
        "conflict_lessons": {
            "engine_available": _LESSONS_AVAILABLE,
            "symbols_analyzed": len(conflict_summary),
            "all_aligned": all(v["aligned"] for v in conflict_summary.values()) if conflict_summary else True,
            "summary": conflict_summary,
        },
    }

    return result


def _empty_result(reason: str) -> dict:
    return {
        "generated_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "market_direction": "NEUTRAL",
        "cross_pair_ratio": 0.0,
        "active_symbols": 0,
        "systems_reporting": 0,
        "super_signals": [],
        "symbol_breakdown": {},
        "reason": reason,
        "thresholds": {
            "cross_pair_threshold": CROSS_PAIR_THRESHOLD,
            "min_system_agreement": MIN_SYSTEM_AGREEMENT,
            "min_symbols": MIN_SYMBOLS_FOR_SIGNAL,
        },
    }


def run(root: pathlib.Path | None = None) -> dict:
    """Entry point. Detect super signals and write output."""
    if root is None:
        root = pathlib.Path(__file__).resolve().parent.parent

    result = detect_super_signals(root)

    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(result, indent=2, default=str),
        encoding="utf-8",
    )

    # Print summary
    n_super = len(result["super_signals"])
    mkt = result["market_direction"]
    ratio = result["cross_pair_ratio"]
    syms = result["active_symbols"]
    systems = result["systems_reporting"]

    print(f"\n{'='*60}")
    print(f"  SUPER SIGNAL ENGINE")
    print(f"{'='*60}")
    print(f"  Systems reporting:  {systems}")
    print(f"  Active symbols:     {syms}")
    print(f"  Market direction:   {mkt}")
    print(f"  Cross-pair ratio:   {ratio:.1%}")
    print(f"  Super signals:      {n_super}")

    if n_super > 0:
        print(f"\n  {'Symbol':<12} {'Dir':<6} {'Conf':>6} {'Systems':>8} {'Tier':<8}")
        print(f"  {'-'*12} {'-'*6} {'-'*6} {'-'*8} {'-'*8}")
        for sig in result["super_signals"]:
            print(
                f"  {sig['symbol']:<12} {sig['direction']:<6} "
                f"{sig['confidence']:>6.3f} {sig['agreement_count']:>8} "
                f"{sig['signal_tier']:<8}"
            )
    elif "reason" in result:
        print(f"\n  No super signals: {result['reason']}")
    else:
        print(f"\n  No symbols met the cross-pair + system agreement thresholds")

    print(f"\n  Output: {OUTPUT_PATH}")
    print(f"{'='*60}\n")

    return result


if __name__ == "__main__":
    run()
