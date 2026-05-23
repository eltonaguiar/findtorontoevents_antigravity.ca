#!/usr/bin/env python3
"""
Strategy Variation Engine
==========================
Generates 5-8 strategy variations (mutations) per learned strategy profile.
Reads learned strategies from copy_trader_intel/data/learned_strategies.json
and produces concrete, testable parameter sets for forward testing.

Each variation mutates TP/SL/hold-time multipliers and optionally flips
direction, creating a family of related strategies from a single trader's
proven edge.

Output: copy_trader_intel/data/strategy_variations.json
"""

import sys
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

import json
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

LEARNED_STRATEGIES_FILE = DATA_DIR / "learned_strategies.json"
VARIATIONS_OUTPUT_FILE = DATA_DIR / "strategy_variations.json"

# ─── Variation Templates ─────────────────────────────────────────────────────

VARIATION_TEMPLATES = [
    {"name": "base",       "tp_mult": 1.0, "sl_mult": 1.0, "hold_mult": 1.0,  "dir": "same"},
    {"name": "tight",      "tp_mult": 0.7, "sl_mult": 0.7, "hold_mult": 0.75, "dir": "same"},
    {"name": "wide",       "tp_mult": 1.5, "sl_mult": 1.5, "hold_mult": 2.0,  "dir": "same"},
    {"name": "scalp",      "tp_mult": 0.5, "sl_mult": 0.5, "hold_mult": 0.25, "dir": "same"},
    {"name": "swing",      "tp_mult": 2.0, "sl_mult": 1.8, "hold_mult": 4.0,  "dir": "same"},
    {"name": "inverse",    "tp_mult": 1.0, "sl_mult": 1.0, "hold_mult": 1.0,  "dir": "flip"},
    {"name": "asymmetric", "tp_mult": 2.0, "sl_mult": 0.8, "hold_mult": 1.0,  "dir": "same"},
]

# Sessions mapped to entry hour ranges (UTC)
SESSIONS = {
    "ASIA_SESSION":   list(range(0, 8)),
    "LONDON_SESSION": list(range(8, 14)),
    "US_SESSION":     list(range(14, 21)),
    "LATE_US":        list(range(21, 24)),
}

# Default TP/SL percentages when learned strategy doesn't provide them
DEFAULT_TP_PCT = 3.0
DEFAULT_SL_PCT = 1.5
DEFAULT_HOLD_HOURS = 6.0
DEFAULT_LEVERAGE = 20


def _normalize_tradeable_coin(raw_coin: str) -> str | None:
    """Normalize learned strategy coin labels to tradeable Binance-style symbols."""
    coin = str(raw_coin or "").strip().upper().replace("/", "").replace("-", "")
    if not coin:
        return None

    # Learned-strategy files can include commodities/equities like XYZ:GOLD, XYZ:CL.
    # Those are not tradeable in the crypto forward tester and would dead-end.
    if ":" in coin or coin.startswith("@") or coin.startswith("KM:") or coin.startswith("HYNA:"):
        return None

    # Hyperliquid uses k-prefixed memecoins for some symbols.
    if coin.startswith("K") and len(coin) > 5:
        coin = coin[1:]

    if coin.endswith("USDT"):
        return coin
    if coin.endswith("USD"):
        return coin + "T"
    return coin + "USDT"


def _sanitize_label(label: str) -> str:
    """Create a filesystem/ID-safe label from a trader label."""
    safe = label.replace(" ", "_").replace("/", "_").replace(".", "")
    # Truncate long labels
    if len(safe) > 20:
        safe = safe[:20]
    return safe


def _flip_direction(direction: str) -> str:
    """Flip LONG to SHORT and vice versa."""
    if direction.upper() == "LONG":
        return "SHORT"
    elif direction.upper() == "SHORT":
        return "LONG"
    return direction


def _direction_from_bias(coin_info: dict, patterns: dict) -> str:
    bias = str(coin_info.get("direction_bias", "") or patterns.get("direction_bias", "")).upper()
    better_direction = str(patterns.get("better_direction", "")).upper()
    if bias in ("LONG_ONLY", "LONG_BIASED") or better_direction == "LONG":
        return "LONG"
    if bias in ("SHORT_ONLY", "SHORT_BIASED") or better_direction == "SHORT":
        return "SHORT"

    long_wr = coin_info.get("long_wr", patterns.get("long_win_rate", 0.5))
    short_wr = coin_info.get("short_wr", patterns.get("short_win_rate", 0.5))
    return "LONG" if long_wr >= short_wr else "SHORT"


def _extract_coin_strategies(strategy: dict) -> list:
    """Extract per-coin strategy profiles from a learned strategy.

    Returns a list of dicts with coin, direction, tp_pct, sl_pct,
    max_hold_hours, leverage, entry_hours, session.
    """
    patterns = strategy.get("learned_patterns", {})
    metrics = strategy.get("overall_metrics", {})
    trader_label = strategy.get("trader_label", "unknown")

    best_coin_lookup = {
        str(coin.get("coin", "")).upper(): coin
        for coin in patterns.get("best_coins", [])
        if isinstance(coin, dict)
    }
    coin_profiles = strategy.get("coin_strategies", {})
    if not coin_profiles:
        return []

    preferred_session = patterns.get("preferred_session", "US_SESSION")
    default_entry_hours = patterns.get("entry_hours_utc", SESSIONS.get(preferred_session, [14, 15, 16]))
    default_hold = patterns.get("median_hold_hours", DEFAULT_HOLD_HOURS) or DEFAULT_HOLD_HOURS
    leverage_map = patterns.get("leverage_per_coin", {}) or {}
    overall_wr = metrics.get("win_rate", 0.5)

    coin_strategies = []
    for coin_key, coin_info in coin_profiles.items():
        if not isinstance(coin_info, dict):
            continue

        coin = coin_info.get("coin", coin_key)
        coin_symbol = _normalize_tradeable_coin(str(coin))
        if not coin_symbol:
            continue

        coin_base = coin_symbol.replace("USDT", "")
        best_coin = best_coin_lookup.get(str(coin).upper(), best_coin_lookup.get(coin_base, {}))
        coin_trades = int(
            coin_info.get("sample_size")
            or best_coin.get("trades")
            or 0
        )
        if coin_trades < 3:
            continue

        coin_wr = float(
            coin_info.get("win_rate")
            or best_coin.get("wr")
            or overall_wr
            or 0.0
        )
        direction = _direction_from_bias(coin_info, patterns)

        tp_pct = float(coin_info.get("median_tp_pct") or 0)
        sl_pct = float(coin_info.get("median_sl_pct") or 0)
        if tp_pct <= 0:
            tp_pct = DEFAULT_TP_PCT
        if sl_pct <= 0:
            # Learned files often have zero recorded stop-loss for trader fills.
            # Use a conservative fallback rather than generating impossible 0-stop setups.
            sl_pct = max(DEFAULT_SL_PCT, round(tp_pct * 0.45, 2))

        hold_hours = float(
            coin_info.get("median_hold_hours")
            or best_coin.get("avg_hold_h")
            or default_hold
            or DEFAULT_HOLD_HOURS
        )
        entry_hours = coin_info.get("preferred_entry_hours_utc") or default_entry_hours
        session = coin_info.get("best_session") or patterns.get("best_session_by_wr") or preferred_session
        leverage = float(
            coin_info.get("leverage")
            or leverage_map.get(coin_base, DEFAULT_LEVERAGE)
            or DEFAULT_LEVERAGE
        )

        coin_strategies.append({
            "coin": coin_symbol,
            "direction": direction,
            "tp_pct": round(max(0.3, min(tp_pct, 20.0)), 2),
            "sl_pct": round(max(0.2, min(sl_pct, 10.0)), 2),
            "max_hold_hours": round(max(0.25, min(hold_hours, 168.0)), 2),
            "leverage": round(max(1.0, min(leverage, 50.0)), 2),
            "entry_hours_utc": list(entry_hours[:4]) if entry_hours else default_entry_hours[:4],
            "session": session,
            "coin_wr": round(coin_wr, 3),
            "coin_trades": coin_trades,
        })

    return coin_strategies


def generate_variations_for_trader(strategy: dict) -> list:
    """Generate all variations for a single trader's learned strategy.

    Returns a list of variation dicts ready for forward testing.
    """
    trader_label = strategy.get("trader_label", "unknown")
    trader_address = strategy.get("trader_address", "")
    safe_label = _sanitize_label(trader_label)
    confidence = strategy.get("confidence", 0.5)

    coin_strategies = _extract_coin_strategies(strategy)
    if not coin_strategies:
        return []

    variations = []

    for coin_strat in coin_strategies:
        coin = coin_strat["coin"]
        # Short coin name for ID (e.g., ETHUSDT -> ETH)
        coin_short = coin.replace("USDT", "")

        for template in VARIATION_TEMPLATES:
            var_name = template["name"]

            # Determine direction
            if template["dir"] == "flip":
                direction = _flip_direction(coin_strat["direction"])
            else:
                direction = coin_strat["direction"]

            # Apply multipliers
            tp_pct = round(coin_strat["tp_pct"] * template["tp_mult"], 2)
            sl_pct = round(coin_strat["sl_pct"] * template["sl_mult"], 2)
            max_hold = round(coin_strat["max_hold_hours"] * template["hold_mult"], 2)

            # Sanity bounds
            tp_pct = max(0.3, min(tp_pct, 20.0))   # 0.3% - 20%
            sl_pct = max(0.2, min(sl_pct, 10.0))    # 0.2% - 10%
            max_hold = max(0.25, min(max_hold, 168)) # 15 min - 1 week

            variation_id = f"{safe_label}_{coin_short}_{var_name}"

            variations.append({
                "variation_id": variation_id,
                "source_trader": trader_label,
                "source_address": trader_address,
                "coin": coin,
                "direction": direction,
                "tp_pct": tp_pct,
                "sl_pct": sl_pct,
                "max_hold_hours": max_hold,
                "leverage": coin_strat["leverage"],
                "entry_hours_utc": coin_strat["entry_hours_utc"],
                "session": coin_strat["session"],
                "starting_capital": 1000,
                "status": "ACTIVE",
                "variation_type": var_name,
                "source_confidence": confidence,
                "source_coin_wr": coin_strat.get("coin_wr", 0),
                "source_coin_trades": coin_strat.get("coin_trades", 0),
            })

    return variations


def generate_variations() -> list:
    """Main entry point: read learned strategies and generate all variations.

    Returns list of all variation dicts and saves to strategy_variations.json.
    """
    print("=" * 70)
    print("  STRATEGY VARIATION ENGINE v1.0")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # Load learned strategies
    if not LEARNED_STRATEGIES_FILE.exists():
        print(f"  [ERROR] {LEARNED_STRATEGIES_FILE} not found.")
        print("  Run strategy_learner.py first (--learn flag).")
        return []

    with open(LEARNED_STRATEGIES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    strategies = data.get("strategies", [])
    if not strategies:
        print("  [WARN] No strategies found in learned_strategies.json")
        return []

    print(f"  Loaded {len(strategies)} learned strategies")

    all_variations = []
    trader_counts = {}

    for strategy in strategies:
        label = strategy.get("trader_label", "unknown")
        variations = generate_variations_for_trader(strategy)
        trader_counts[label] = len(variations)
        all_variations.extend(variations)

        if variations:
            print(f"  {label}: {len(variations)} variations generated")
        else:
            print(f"  {label}: SKIPPED (insufficient coin data)")

    # Save output
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_version": "1.0",
        "template_count": len(VARIATION_TEMPLATES),
        "total_variations": len(all_variations),
        "traders_with_variations": sum(1 for c in trader_counts.values() if c > 0),
        "per_trader_counts": trader_counts,
        "variations": all_variations,
    }

    with open(VARIATIONS_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  VARIATION GENERATION COMPLETE")
    print(f"  Total variations: {len(all_variations)}")
    print(f"  Traders with variations: {output['traders_with_variations']}/{len(strategies)}")
    print(f"  Templates per coin: {len(VARIATION_TEMPLATES)}")
    print(f"  Output: {VARIATIONS_OUTPUT_FILE}")

    # Breakdown by variation type
    type_counts = {}
    for v in all_variations:
        vt = v["variation_type"]
        type_counts[vt] = type_counts.get(vt, 0) + 1

    print(f"\n  Variation Type Breakdown:")
    for vt, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    {vt:<12s}: {count:>4d}")

    # Breakdown by coin
    coin_counts = {}
    for v in all_variations:
        c = v["coin"]
        coin_counts[c] = coin_counts.get(c, 0) + 1

    print(f"\n  Coin Breakdown (top 10):")
    for c, count in sorted(coin_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"    {c:<12s}: {count:>4d}")

    print(f"{'=' * 70}\n")

    return all_variations


if __name__ == "__main__":
    generate_variations()
