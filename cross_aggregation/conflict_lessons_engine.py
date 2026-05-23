#!/usr/bin/env python3
"""
Conflict Lessons Engine — Application layer for historical conflict resolution rules.

Loads conflict_lessons_learned.json and exposes functions that any trading system
can call to apply proven conflict resolution rules before making decisions.

Consumers:
  - super_signal.py     (trust-weighted voting + conflict rules)
  - dashboard_generator (conflict annotations on audit dashboard)
  - discord_notify.py   (suppress BANNED signals)
  - contested_pick_checker.py (legacy — rules originated here)

Functions:
  apply_conflict_rules(symbol, signals_dict) -> structured result
  get_trust_weight(system_name) -> float multiplier
  should_suppress_signal(system_name) -> bool
  annotate_pick(pick_dict) -> pick_dict with annotations
  check_stale_signals(signals, max_age_hours) -> filtered list
"""

from __future__ import annotations

import json
import os
import math
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Load lessons at import time
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_LESSONS_PATH = os.path.join(_SCRIPT_DIR, "data", "conflict_lessons_learned.json")

_LESSONS: Dict[str, Any] = {}
_TRUST_HIERARCHY: List[Dict[str, Any]] = []
_NEVER_TRUST: List[Dict[str, Any]] = []
_CONFLICT_RULES: List[Dict[str, Any]] = []

# System name aliases — maps various naming conventions to canonical keys
_SYSTEM_ALIASES: Dict[str, str] = {
    # Battleground DNA variants
    "battleground": "battleground",
    "battleground_dna": "battleground",
    "bg_dna": "battleground",
    "Battleground DNA (6 forward strategies)": "battleground",
    # Cross-Agg SUPER
    "cross_agg_super": "cross_agg_super",
    "super_signal": "cross_agg_super",
    "cross_aggregation": "cross_agg_super",
    "Cross-Aggregation SUPER (4+ systems agree)": "cross_agg_super",
    # Mega Mutation
    "mega_mutation_macd_rsi": "mega_mutation_macd_rsi",
    "mega_mutation": "mega_mutation_macd_rsi",
    "tournament": "mega_mutation_macd_rsi",
    "Mega Mutation MACD_RSI": "mega_mutation_macd_rsi",
    # System F / Claws of Doom
    "system_f": "system_f",
    "claws_of_doom": "system_f",
    "fear_contrarian": "system_f",
    "System F Claws of Doom (Fear Contrarian)": "system_f",
    # LuxAlgo
    "luxalgo_sell": "luxalgo_sell",
    "luxalgo": "luxalgo_sell",
    "LuxAlgo SELL (RSI overbought)": "luxalgo_sell",
    # Alpha Engine
    "alpha_engine_short": "alpha_engine_short",
    "alpha_engine": "alpha_engine_short",
    "alpha": "alpha_engine_short",
    "Alpha Engine SHORT signals": "alpha_engine_short",
    # BANNED / Never-trust systems
    "system_a": "system_a",
    "ml_bg_a": "system_a",
    "System A/B (ml_battleground)": "system_a",
    "system_b": "system_b",
    "ml_bg_b": "system_b",
    "ml_bg_c": "system_a",
    "ml_bg_ensemble": "system_a",
    "predictions_stale": "predictions_stale",
    "predictions": "predictions_stale",
    "Stale predictions system": "predictions_stale",
    "kimi_standalone": "kimi_standalone",
    "kimi": "kimi_standalone",
    "KIMI standalone": "kimi_standalone",
    "paper_trading": "paper_trading",
    "Paper Trading": "paper_trading",
}

# Trust weights derived from lessons (rank 1 = highest weight)
_TRUST_WEIGHTS: Dict[str, float] = {
    "battleground": 2.0,
    "cross_agg_super": 1.8,
    "mega_mutation_macd_rsi": 1.6,
    "system_f": 1.3,
    "luxalgo_sell": 1.0,
    "alpha_engine_short": 1.1,
}

# Never-trust systems get suppressed or near-zero weight
_BANNED_SYSTEMS: Dict[str, Dict[str, Any]] = {
    "system_a": {"wr": 0.053, "pnl": -62.49, "reason": "5.3% WR, fired SELL at extreme fear"},
    "system_b": {"wr": 0.053, "pnl": -64.15, "reason": "5.3% WR, same as System A"},
    "predictions_stale": {"wr": None, "pnl": None, "reason": "324 stale picks, inflates BUY counts"},
    "kimi_standalone": {"wr": 0.200, "pnl": -125.38, "reason": "20% WR solo, only useful as confirmer"},
    "paper_trading": {"wr": 0.382, "pnl": -124.45, "reason": "Heavy losses across 34 trades"},
}

# Large-cap symbols where LuxAlgo SELL is valid (Rule 3 exception)
_LARGE_CAPS = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"}

# Altcoins where Mega Mutation MACD_RSI historically overrides LuxAlgo
_MEGA_MUTATION_ALTS = {"ENAUSDT", "JUPUSDT", "STXUSDT", "WIFUSDT"}

# EMA_CROSS exceptions — LuxAlgo was right on these
_EMA_CROSS_EXCEPTIONS = {"AVAXUSDT", "DOTUSDT"}


def _load_lessons():
    """Load lessons from JSON file. Called once at import."""
    global _LESSONS, _TRUST_HIERARCHY, _NEVER_TRUST, _CONFLICT_RULES
    try:
        with open(_LESSONS_PATH, "r", encoding="utf-8") as f:
            _LESSONS = json.load(f)
        _TRUST_HIERARCHY = _LESSONS.get("trust_hierarchy", [])
        _NEVER_TRUST = _LESSONS.get("never_trust_in_conflicts", [])
        _CONFLICT_RULES = _LESSONS.get("conflict_resolution_rules", [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[conflict_lessons_engine] WARNING: Could not load lessons: {e}")
        _LESSONS = {}
        _TRUST_HIERARCHY = []
        _NEVER_TRUST = []
        _CONFLICT_RULES = []


# Load on import
_load_lessons()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _canonical_name(system_name: str) -> str:
    """Resolve a system name to its canonical key."""
    if system_name in _SYSTEM_ALIASES:
        return _SYSTEM_ALIASES[system_name]
    # Try lowercase
    low = system_name.lower().strip()
    if low in _SYSTEM_ALIASES:
        return _SYSTEM_ALIASES[low]
    # Try partial match
    for alias, canonical in _SYSTEM_ALIASES.items():
        if alias.lower() in low or low in alias.lower():
            return canonical
    return low


def get_trust_weight(system_name: str) -> float:
    """
    Returns the trust multiplier for a system based on historical performance.

    Returns:
        float: Weight from 0.0 (banned) to 2.0 (battleground).
               Unknown systems default to 0.8 (slight penalty for unproven).
    """
    canonical = _canonical_name(system_name)
    if canonical in _BANNED_SYSTEMS:
        return 0.0
    return _TRUST_WEIGHTS.get(canonical, 0.8)


def should_suppress_signal(system_name: str) -> bool:
    """
    Returns True if the system is BANNED or UNTRUSTED and its signals
    should be suppressed from consensus voting and notifications.

    Use this in discord_notify.py to skip sending alerts for known-bad systems.
    """
    canonical = _canonical_name(system_name)
    return canonical in _BANNED_SYSTEMS


def get_system_info(system_name: str) -> Dict[str, Any]:
    """
    Returns full info about a system: trust weight, banned status, reason.
    Useful for dashboard annotations.
    """
    canonical = _canonical_name(system_name)
    if canonical in _BANNED_SYSTEMS:
        info = _BANNED_SYSTEMS[canonical]
        return {
            "canonical_name": canonical,
            "trust_weight": 0.0,
            "status": "BANNED",
            "win_rate": info.get("wr"),
            "total_pnl": info.get("pnl"),
            "reason": info.get("reason", "Historical underperformance"),
        }
    weight = _TRUST_WEIGHTS.get(canonical, 0.8)
    # Find rank from hierarchy
    rank = None
    wr = None
    for entry in _TRUST_HIERARCHY:
        if _canonical_name(entry.get("system", "")) == canonical:
            rank = entry.get("rank")
            wr = entry.get("win_rate")
            break
    return {
        "canonical_name": canonical,
        "trust_weight": weight,
        "status": "TRUSTED" if weight >= 1.0 else "WATCH",
        "rank": rank,
        "win_rate": wr,
    }


def _recency_decay(signal_age_hours: float, half_life_hours: float = 48.0) -> float:
    """
    Exponential decay factor for signal recency.
    Rule 1: A fresh signal is worth more than a stale one.

    At 0h: returns 1.0
    At 48h (half-life): returns 0.5
    At 96h: returns 0.25
    """
    if signal_age_hours <= 0:
        return 1.0
    return math.pow(0.5, signal_age_hours / half_life_hours)


def check_stale_signals(
    signals: List[Dict[str, Any]],
    max_age_hours: float = 48.0,
    time_field: str = "generated_at",
) -> List[Dict[str, Any]]:
    """
    Filter out stale signals that are older than max_age_hours.
    Implements Rule 1: "Recency beats count."

    Args:
        signals: List of signal dicts, each with a timestamp field.
        max_age_hours: Maximum age before a signal is considered stale.
        time_field: The key in each signal dict that holds the ISO timestamp.

    Returns:
        List of fresh signals (those younger than max_age_hours).
        Each returned signal gets a "_recency_decay" field added.
    """
    now = datetime.now(timezone.utc)
    fresh = []
    for sig in signals:
        ts_str = sig.get(time_field) or sig.get("timestamp") or sig.get("created_at")
        if not ts_str:
            # No timestamp = suspect; apply heavy penalty but don't discard
            sig["_recency_decay"] = 0.25
            sig["_stale_warning"] = "No timestamp found — treated as old"
            fresh.append(sig)
            continue

        try:
            if isinstance(ts_str, str):
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            else:
                ts = ts_str
            age_hours = (now - ts).total_seconds() / 3600
        except (ValueError, TypeError):
            sig["_recency_decay"] = 0.25
            sig["_stale_warning"] = f"Unparseable timestamp: {ts_str}"
            fresh.append(sig)
            continue

        if age_hours > max_age_hours:
            # Stale — skip it (Rule 1)
            continue

        sig["_recency_decay"] = round(_recency_decay(age_hours), 4)
        sig["_age_hours"] = round(age_hours, 1)
        fresh.append(sig)

    return fresh


def apply_conflict_rules(
    symbol: str,
    signals_dict: Dict[str, str],
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Apply all 6 conflict resolution rules to determine the recommended direction.

    Args:
        symbol: Trading symbol (e.g., "BTCUSDT")
        signals_dict: {system_name: direction} e.g. {"battleground": "LONG", "luxalgo": "SELL"}
        context: Optional extra context:
            - "fear_greed_index": int (0-100)
            - "strategy_type": str (e.g., "MACD_RSI", "EMA_CROSS")
            - "signal_ages": {system_name: hours_since_signal}

    Returns:
        {
            "recommended_direction": "LONG" | "SHORT" | "NEUTRAL",
            "confidence": float (0-1),
            "rules_applied": [{"rule_id": 1, "rule": "...", "effect": "..."}],
            "overrides": [{"overrider": "battleground", "overridden": "luxalgo", "reason": "..."}],
            "warnings": ["..."],
            "trust_breakdown": {system: weight},
            "suppressed_systems": [system_names],
        }
    """
    context = context or {}
    symbol_upper = symbol.strip().upper().replace("-", "").replace("/", "")
    if symbol_upper.endswith("USD") and not symbol_upper.endswith("USDT"):
        symbol_upper += "T"

    rules_applied: List[Dict[str, Any]] = []
    overrides: List[Dict[str, Any]] = []
    warnings: List[str] = []
    suppressed: List[str] = []

    # Normalize all system names and filter out banned
    normalized_signals: Dict[str, str] = {}
    trust_breakdown: Dict[str, float] = {}

    for sys_name, direction in signals_dict.items():
        canonical = _canonical_name(sys_name)
        direction_upper = direction.strip().upper()

        # Normalize direction
        if direction_upper in ("BUY", "LONG", "LEAN_BUY"):
            direction_upper = "LONG"
        elif direction_upper in ("SELL", "SHORT", "LEAN_SELL"):
            direction_upper = "SHORT"
        else:
            direction_upper = "NEUTRAL"

        # Check if system should be suppressed
        if should_suppress_signal(sys_name):
            suppressed.append(sys_name)
            trust_breakdown[sys_name] = 0.0
            warnings.append(
                f"{sys_name} ({canonical}) is BANNED — signal suppressed "
                f"({_BANNED_SYSTEMS.get(canonical, {}).get('reason', 'historical underperformance')})"
            )
            continue

        weight = get_trust_weight(sys_name)

        # Apply recency decay if signal ages provided (Rule 1)
        signal_ages = context.get("signal_ages", {})
        if sys_name in signal_ages:
            age_hours = signal_ages[sys_name]
            decay = _recency_decay(age_hours)
            weight *= decay
            if age_hours > 48:
                warnings.append(
                    f"{sys_name} signal is {age_hours:.0f}h old — "
                    f"recency decay applied ({decay:.2f}x)"
                )

        normalized_signals[sys_name] = direction_upper
        trust_breakdown[sys_name] = round(weight, 3)

    # If nothing left after suppression, return neutral
    if not normalized_signals:
        return {
            "recommended_direction": "NEUTRAL",
            "confidence": 0.0,
            "rules_applied": [],
            "overrides": [],
            "warnings": warnings + ["All signals were from suppressed/banned systems"],
            "trust_breakdown": trust_breakdown,
            "suppressed_systems": suppressed,
        }

    # -----------------------------------------------------------------------
    # RULE 1: Recency beats count (48h half-life decay)
    # Already applied above via recency decay on weights.
    # Log if stale signals were penalized.
    # -----------------------------------------------------------------------
    signal_ages = context.get("signal_ages", {})
    stale_systems = [s for s, age in signal_ages.items() if age > 48 and s in normalized_signals]
    if stale_systems:
        rules_applied.append({
            "rule_id": 1,
            "rule": "Recency beats count",
            "effect": f"Penalized stale signals from: {', '.join(stale_systems)}",
        })

    # -----------------------------------------------------------------------
    # Trust-weighted vote tally
    # -----------------------------------------------------------------------
    weighted_long = 0.0
    weighted_short = 0.0
    raw_long = 0
    raw_short = 0

    for sys_name, direction in normalized_signals.items():
        w = trust_breakdown[sys_name]
        if direction == "LONG":
            weighted_long += w
            raw_long += 1
        elif direction == "SHORT":
            weighted_short += w
            raw_short += 1

    total_weight = weighted_long + weighted_short
    if total_weight == 0:
        total_weight = 1.0  # prevent division by zero

    # Base direction from weighted votes
    if weighted_long > weighted_short:
        base_direction = "LONG"
        base_confidence = weighted_long / total_weight
    elif weighted_short > weighted_long:
        base_direction = "SHORT"
        base_confidence = weighted_short / total_weight
    else:
        base_direction = "NEUTRAL"
        base_confidence = 0.5

    recommended = base_direction
    confidence = base_confidence

    # -----------------------------------------------------------------------
    # RULE 2: SUPER consensus (4+ systems) beats any individual signal
    # -----------------------------------------------------------------------
    agreeing_count = raw_long if recommended == "LONG" else raw_short
    if agreeing_count >= 4:
        confidence = min(confidence + 0.10, 0.99)
        rules_applied.append({
            "rule_id": 2,
            "rule": "SUPER consensus (4+ systems) beats any individual signal",
            "effect": f"{agreeing_count} systems agree on {recommended} — confidence boosted to {confidence:.2f}",
        })

    # -----------------------------------------------------------------------
    # RULE 3: Mega Mutation MACD_RSI > LuxAlgo SELL on altcoins
    # -----------------------------------------------------------------------
    has_mega_mutation = any(
        _canonical_name(s) == "mega_mutation_macd_rsi" for s in normalized_signals
    )
    has_luxalgo = any(
        _canonical_name(s) == "luxalgo_sell" for s in normalized_signals
    )
    strategy_type = context.get("strategy_type", "MACD_RSI")

    if has_mega_mutation and has_luxalgo:
        mega_dir = None
        lux_dir = None
        mega_sys = None
        lux_sys = None
        for s, d in normalized_signals.items():
            if _canonical_name(s) == "mega_mutation_macd_rsi":
                mega_dir = d
                mega_sys = s
            if _canonical_name(s) == "luxalgo_sell":
                lux_dir = d
                lux_sys = s

        if mega_dir and lux_dir and mega_dir != lux_dir:
            if symbol_upper in _EMA_CROSS_EXCEPTIONS or strategy_type == "EMA_CROSS":
                # Exception: LuxAlgo wins on EMA_CROSS picks
                overrides.append({
                    "overrider": lux_sys,
                    "overridden": mega_sys,
                    "reason": f"EMA_CROSS exception on {symbol_upper} — LuxAlgo historically correct here",
                })
                rules_applied.append({
                    "rule_id": 3,
                    "rule": "Mega Mutation MACD_RSI > LuxAlgo SELL on altcoins (EXCEPTION: EMA_CROSS)",
                    "effect": f"LuxAlgo overrides Mega Mutation on {symbol_upper} (EMA_CROSS exception)",
                })
            elif symbol_upper not in _LARGE_CAPS:
                # Mega Mutation wins on altcoins
                overrides.append({
                    "overrider": mega_sys,
                    "overridden": lux_sys,
                    "reason": f"Mega Mutation MACD_RSI (77-88% WR, Sharpe 5-8) overrides LuxAlgo SELL on {symbol_upper}",
                })
                recommended = mega_dir
                confidence = max(confidence, 0.80)
                rules_applied.append({
                    "rule_id": 3,
                    "rule": "Mega Mutation MACD_RSI > LuxAlgo SELL on altcoins",
                    "effect": f"Mega Mutation LONG overrides LuxAlgo SELL on altcoin {symbol_upper}",
                })
            else:
                # Large-cap: LuxAlgo SELL is valid short-term
                warnings.append(
                    f"LuxAlgo SELL vs Mega Mutation conflict on large-cap {symbol_upper} — "
                    f"LuxAlgo valid for 24-48h scalp, Mega Mutation for swing"
                )

    # -----------------------------------------------------------------------
    # RULE 4: Hayes Liquidity Index = direction only, NOT entry signal
    # -----------------------------------------------------------------------
    has_hayes = any("hayes" in s.lower() for s in normalized_signals)
    if has_hayes:
        rules_applied.append({
            "rule_id": 4,
            "rule": "Hayes Liquidity Index = direction only, NOT entry signal",
            "effect": "Hayes used for LONG/SHORT bias. Wait for RSI < 50 before entry.",
        })
        warnings.append(
            "Hayes signal present — good for direction bias, "
            "but do NOT enter on Hayes alone. Wait for RSI cooling."
        )

    # -----------------------------------------------------------------------
    # RULE 5: Extreme Fear (F&G < 15) invalidates SELL signals
    # -----------------------------------------------------------------------
    fear_greed = context.get("fear_greed_index")
    if fear_greed is not None and fear_greed < 15:
        if recommended == "SHORT":
            warnings.append(
                f"Fear & Greed = {fear_greed} (extreme fear) — "
                f"SELL signals historically fail at F&G < 15. "
                f"Market bounces from extreme fear."
            )
            # Flip to LONG with lower confidence
            recommended = "LONG"
            confidence = 0.60
            overrides.append({
                "overrider": "Rule5_ExtremeFear",
                "overridden": "weighted_vote",
                "reason": f"F&G={fear_greed} < 15 invalidates SELL — System A lost -62.49% selling at F&G=11",
            })
            rules_applied.append({
                "rule_id": 5,
                "rule": "Extreme Fear (F&G<15) invalidates SELL signals",
                "effect": f"F&G={fear_greed}: flipped SHORT -> LONG (extreme fear bounce pattern)",
            })
        else:
            rules_applied.append({
                "rule_id": 5,
                "rule": "Extreme Fear (F&G<15) invalidates SELL signals",
                "effect": f"F&G={fear_greed}: already LONG — rule confirms direction",
            })

    # -----------------------------------------------------------------------
    # RULE 6: Entry timing matters more than direction
    # -----------------------------------------------------------------------
    entry_price = context.get("entry_price")
    resistance_level = context.get("resistance_level")
    if entry_price and resistance_level:
        if entry_price > resistance_level * 0.97:
            warnings.append(
                f"Entry price ${entry_price} is within 3% of resistance ${resistance_level} — "
                f"historically, entries at resistance lose even with correct direction."
            )
            confidence *= 0.85  # Reduce confidence near resistance
            rules_applied.append({
                "rule_id": 6,
                "rule": "Entry timing matters more than direction",
                "effect": f"Entry near resistance — confidence reduced by 15%",
            })

    # -----------------------------------------------------------------------
    # RULE 7: RSI>70 across multiple large-caps = broad reversal override
    # Added 2026-03-13 after Antigravity SELL beat Claude LONG on all 5 picks.
    # When RSI is overbought across BTC+ETH+SOL simultaneously, LONG consensus
    # becomes unreliable regardless of system count or trust hierarchy.
    # -----------------------------------------------------------------------
    multi_rsi_overbought = context.get("multi_asset_rsi_overbought", False)
    rsi_values = context.get("rsi_values", {})
    overbought_count = sum(1 for v in rsi_values.values() if v and v > 70)

    if multi_rsi_overbought or overbought_count >= 3:
        if recommended == "LONG":
            warnings.append(
                f"RSI>70 on {overbought_count} large-caps simultaneously — "
                f"broad reversal signal. LONG consensus unreliable. "
                f"Validated 2026-03-13: all 5 LONG calls lost 3-4%."
            )
            confidence *= 0.50  # Halve confidence on LONG during multi-asset overbought
            rules_applied.append({
                "rule_id": 7,
                "rule": "RSI>70 multi-asset reversal override",
                "effect": f"RSI overbought on {overbought_count} large-caps — LONG confidence halved to {confidence:.2f}",
            })

    # -----------------------------------------------------------------------
    # Battleground override check (Rank 1 always wins conflicts)
    # -----------------------------------------------------------------------
    bg_systems = [
        s for s in normalized_signals
        if _canonical_name(s) == "battleground"
    ]
    if bg_systems:
        bg_dir = normalized_signals[bg_systems[0]]
        if bg_dir != recommended and agreeing_count < 4:
            # Battleground overrides unless SUPER consensus (4+)
            overrides.append({
                "overrider": bg_systems[0],
                "overridden": "weighted_vote",
                "reason": "Battleground DNA (65.2% WR, +105% PnL, 210 trades) overrides non-SUPER consensus",
            })
            recommended = bg_dir
            confidence = max(confidence, 0.75)
            rules_applied.append({
                "rule_id": 0,
                "rule": "Battleground DNA (Rank 1) always wins unless SUPER 4+ consensus",
                "effect": f"Battleground {bg_dir} overrides {base_direction} consensus",
            })

    # -----------------------------------------------------------------------
    # KIMI-as-confirmer check
    # -----------------------------------------------------------------------
    kimi_systems = [
        s for s in normalized_signals
        if _canonical_name(s) == "kimi_standalone"
    ]
    if kimi_systems:
        # KIMI should have been suppressed, but if someone passes it through
        # with a non-standard name, at least warn
        kimi_dir = normalized_signals[kimi_systems[0]]
        if kimi_dir == recommended and len(normalized_signals) >= 3:
            # KIMI confirms 3+ system consensus — this is the good case
            confidence = min(confidence + 0.03, 0.99)
            warnings.append(
                f"KIMI confirms {recommended} with {len(normalized_signals)} other systems — "
                f"KIMI is profitable ONLY as a confirmer in 3+ system consensus"
            )

    return {
        "recommended_direction": recommended,
        "confidence": round(confidence, 4),
        "rules_applied": rules_applied,
        "overrides": overrides,
        "warnings": warnings,
        "trust_breakdown": trust_breakdown,
        "suppressed_systems": suppressed,
        "weighted_long": round(weighted_long, 3),
        "weighted_short": round(weighted_short, 3),
        "raw_long": raw_long,
        "raw_short": raw_short,
    }


def annotate_pick(pick_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add conflict lesson annotations to any pick object.
    This non-destructively adds a "_conflict_lessons" sub-dict.

    Works with picks from any system — just needs "symbol" and
    a system identifier (checks "system", "source_system", "strategy" fields).

    Args:
        pick_dict: A pick dict from any trading system.

    Returns:
        The same dict with "_conflict_lessons" added.
    """
    symbol = pick_dict.get("symbol") or pick_dict.get("pair") or ""
    system_name = (
        pick_dict.get("system")
        or pick_dict.get("source_system")
        or pick_dict.get("strategy")
        or pick_dict.get("strategy_name")
        or "unknown"
    )
    direction = (
        pick_dict.get("direction")
        or pick_dict.get("signal_type")
        or pick_dict.get("signal")
        or ""
    ).upper()

    canonical = _canonical_name(system_name)
    weight = get_trust_weight(system_name)
    suppressed = should_suppress_signal(system_name)

    annotations: Dict[str, Any] = {
        "system_canonical": canonical,
        "trust_weight": weight,
        "is_suppressed": suppressed,
    }

    if suppressed:
        info = _BANNED_SYSTEMS.get(canonical, {})
        annotations["suppression_reason"] = info.get("reason", "Historical underperformance")
        annotations["historical_wr"] = info.get("wr")
        annotations["historical_pnl"] = info.get("pnl")

    # Check for applicable rules
    applicable_rules: List[str] = []

    # Rule 1: Check recency
    ts_str = (
        pick_dict.get("generated_at")
        or pick_dict.get("timestamp")
        or pick_dict.get("created_at")
    )
    if ts_str:
        try:
            if isinstance(ts_str, str):
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            else:
                ts = ts_str
            age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            annotations["age_hours"] = round(age_hours, 1)
            if age_hours > 48:
                applicable_rules.append(
                    f"RULE1: Signal is {age_hours:.0f}h old — recency decay = {_recency_decay(age_hours):.2f}x"
                )
                annotations["recency_decay"] = round(_recency_decay(age_hours), 4)
        except (ValueError, TypeError):
            pass

    # Rule 3: Mega Mutation vs LuxAlgo on altcoins
    sym_upper = symbol.upper().replace("-", "").replace("/", "")
    if sym_upper.endswith("USD") and not sym_upper.endswith("USDT"):
        sym_upper += "T"

    if canonical == "mega_mutation_macd_rsi" and sym_upper in _MEGA_MUTATION_ALTS:
        applicable_rules.append(
            f"RULE3: Mega Mutation on {sym_upper} — historically overrides LuxAlgo SELL (77-88% WR)"
        )
    elif canonical == "luxalgo_sell" and sym_upper in _MEGA_MUTATION_ALTS:
        applicable_rules.append(
            f"RULE3: LuxAlgo SELL on {sym_upper} — historically overridden by Mega Mutation on alts"
        )

    # Rule 4: Hayes
    if "hayes" in canonical or "hayes" in system_name.lower():
        applicable_rules.append(
            "RULE4: Hayes Liquidity = direction only, wait for RSI < 50 before entry"
        )

    # Rule 5: Extreme fear (we note it but can't check F&G without context)
    if canonical == "system_f":
        applicable_rules.append(
            "RULE5 note: System F valid ONLY at initial F&G extreme (<15). "
            "Second bounce at same F&G level has no edge."
        )

    annotations["applicable_rules"] = applicable_rules

    pick_dict["_conflict_lessons"] = annotations
    return pick_dict


def get_all_rules() -> List[Dict[str, Any]]:
    """Return all conflict resolution rules for display purposes."""
    return list(_CONFLICT_RULES)


def get_trust_hierarchy() -> List[Dict[str, Any]]:
    """Return the full trust hierarchy for display purposes."""
    return list(_TRUST_HIERARCHY)


def reload_lessons():
    """
    Force-reload the lessons JSON (e.g., after the file has been updated
    by contested_pick_checker.py).
    """
    _load_lessons()


# ---------------------------------------------------------------------------
# Convenience: CLI self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  CONFLICT LESSONS ENGINE — Self-Test")
    print("=" * 60)

    # Test 1: Trust weights
    print("\n--- Trust Weights ---")
    for name in ["battleground", "luxalgo", "system_a", "kimi", "unknown_system"]:
        w = get_trust_weight(name)
        s = should_suppress_signal(name)
        print(f"  {name:<25} weight={w:.1f}  suppressed={s}")

    # Test 2: Apply rules to a conflicted symbol
    print("\n--- Conflict Resolution: BTCUSDT ---")
    result = apply_conflict_rules("BTCUSDT", {
        "battleground": "LONG",
        "luxalgo": "SELL",
        "system_a": "SELL",
        "mega_mutation": "LONG",
    })
    print(f"  Recommended: {result['recommended_direction']}")
    print(f"  Confidence:  {result['confidence']}")
    print(f"  Suppressed:  {result['suppressed_systems']}")
    for r in result["rules_applied"]:
        print(f"  Rule {r['rule_id']}: {r['effect']}")
    for o in result["overrides"]:
        print(f"  Override: {o['overrider']} > {o['overridden']} — {o['reason']}")
    for w in result["warnings"]:
        print(f"  Warning: {w}")

    # Test 3: Extreme fear override
    print("\n--- Conflict Resolution: ETHUSDT at F&G=10 ---")
    result2 = apply_conflict_rules("ETHUSDT", {
        "system_f": "LONG",
        "alpha_engine": "SHORT",
    }, context={"fear_greed_index": 10})
    print(f"  Recommended: {result2['recommended_direction']}")
    print(f"  Confidence:  {result2['confidence']}")
    for r in result2["rules_applied"]:
        print(f"  Rule {r['rule_id']}: {r['effect']}")

    # Test 4: Annotate a pick
    print("\n--- Pick Annotation ---")
    test_pick = {
        "symbol": "WIFUSDT",
        "direction": "LONG",
        "system": "mega_mutation",
        "generated_at": "2026-03-13T10:00:00Z",
    }
    annotated = annotate_pick(test_pick)
    lessons = annotated["_conflict_lessons"]
    print(f"  System: {lessons['system_canonical']}")
    print(f"  Weight: {lessons['trust_weight']}")
    print(f"  Suppressed: {lessons['is_suppressed']}")
    for rule in lessons["applicable_rules"]:
        print(f"  Rule: {rule}")

    # Test 5: Stale signal filtering
    print("\n--- Stale Signal Filtering ---")
    now_iso = datetime.now(timezone.utc).isoformat()
    old_iso = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
    test_signals = [
        {"symbol": "BTCUSDT", "generated_at": now_iso, "direction": "LONG"},
        {"symbol": "ETHUSDT", "generated_at": old_iso, "direction": "LONG"},
        {"symbol": "SOLUSDT", "direction": "LONG"},  # no timestamp
    ]
    fresh = check_stale_signals(test_signals, max_age_hours=48)
    print(f"  Input: {len(test_signals)} signals")
    print(f"  Fresh: {len(fresh)} signals (after 48h filter)")
    for s in fresh:
        print(f"    {s['symbol']}: decay={s.get('_recency_decay', 'N/A')}")

    print(f"\n{'=' * 60}")
    print(f"  Lessons loaded: {len(_CONFLICT_RULES)} rules, "
          f"{len(_TRUST_HIERARCHY)} trusted systems, "
          f"{len(_BANNED_SYSTEMS)} banned systems")
    print(f"{'=' * 60}")
