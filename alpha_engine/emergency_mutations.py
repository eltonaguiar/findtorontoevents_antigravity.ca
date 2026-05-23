"""
EMERGENCY MUTATIONS -- Mutate-Before-Kill Strategy Variants
============================================================
Per the Mutate-Before-Kill rule: never kill a strategy without first trying
3 mutation approaches. This module generates 15 variants (5 strategies x 3
mutations each) and tracks them in a 48-hour forward test.

The 5 worst strategies (WR < 35%, significant trade count):
1. winner_pattern_precursor  -- 96+ trades, 17% WR, BUY-biased
2. volume_spike_backfill     -- 50 trades, 30% WR, BUY-biased
3. hl_funding_fade           -- 20 trades, 20% WR, bidirectional
4. momentum_catcher          -- 20 trades, 15% WR, BUY-biased
5. ml_enhanced_BTCUSDT_15m_D_ensemble_stack -- 10 trades, 0% WR, SHORT-biased

Mutation Types:
  A) INVERSE -- flip direction (BUY->SELL, LONG->SHORT)
  B) TIGHTER -- raise confidence +0.10, TP=1.0x ATR, SL=0.75x ATR, vol>1.5x avg
  C) REGIME_GATED -- only fire when market regime matches strategy edge

Usage:
    from emergency_mutations import EMERGENCY_MUTATION_STRATEGIES, get_mutation_variants
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
MUTATION_FORWARD_TEST_PATH = DATA_DIR / "mutation_forward_test.json"
MUTATION_CANDIDATES_PATH = DATA_DIR / "mutation_candidates.json"

# ---------------------------------------------------------------------------
# Regime detection (lazy import to avoid circular deps)
# ---------------------------------------------------------------------------
_cached_regime = None
_cached_regime_ts = 0.0


def _get_current_regime() -> str:
    """Get current market regime with 5-min cache."""
    global _cached_regime, _cached_regime_ts
    if _cached_regime and (time.time() - _cached_regime_ts) < 300:
        return _cached_regime
    try:
        from fast_regime_detector import get_regime_for_symbol
        _cached_regime = get_regime_for_symbol("BTCUSDT")
        _cached_regime_ts = time.time()
        return _cached_regime
    except Exception:
        return "UNKNOWN"


# ---------------------------------------------------------------------------
# Strategy classification for regime gating
# ---------------------------------------------------------------------------
STRATEGY_EDGE_TYPE = {
    "winner_pattern_precursor": "momentum",
    "volume_spike_backfill": "momentum",
    "hl_funding_fade": "mean_reversion",
    "momentum_catcher": "momentum",
    "ml_enhanced_BTCUSDT_15m_D_ensemble_stack": "momentum",
    "ml_enhanced_RENDERUSDT_1h_D_ensemble_stack": "momentum",
    "ml_enhanced_RENDERUSDT_4h_D_ensemble_stack": "momentum",
    "kimi_signal_tracking": "momentum",
    "macd_rsi_confluence": "momentum",
    "st_multi_day_momentum": "momentum",
    "lower_wick_absorption": "mean_reversion",
    "hh-hl-scout": "momentum",
    "macd-momentum": "momentum",
    "intermarket-flow-scout": "momentum",
    "binance_smart_money": "momentum",
}

# Which regimes each edge type is allowed in
REGIME_ALLOWLIST = {
    "momentum": {"STRONG_BULL", "BULL", "STRONG_BEAR", "BEAR"},
    "mean_reversion": {"RANGING", "CHOPPY"},
}


# ---------------------------------------------------------------------------
# Core mutation logic
# ---------------------------------------------------------------------------

def _mutate_inverse(pick: dict, parent_strategy: str) -> dict | None:
    """Mutation A: INVERSE -- flip direction entirely."""
    mutated = deepcopy(pick)
    variant_name = f"INV_{parent_strategy}"

    # Flip direction
    orig_signal = str(mutated.get("signal_type", "")).upper()
    orig_direction = str(mutated.get("direction", "")).upper()

    if orig_signal in ("BUY", "LONG"):
        mutated["signal_type"] = "SELL"
        mutated["direction"] = "SHORT"
    elif orig_signal in ("SELL", "SHORT"):
        mutated["signal_type"] = "BUY"
        mutated["direction"] = "LONG"
    else:
        return None  # Can't invert unknown direction

    # Swap TP and SL (inverted trade)
    entry = mutated.get("entry_price", 0)
    if entry <= 0:
        return None

    orig_tp = mutated.get("take_profit", entry)
    orig_sl = mutated.get("stop_loss", entry)

    # Calculate original TP/SL distances
    tp_dist = abs(orig_tp - entry)
    sl_dist = abs(orig_sl - entry)

    if mutated["direction"] == "SHORT":
        mutated["take_profit"] = round(entry - tp_dist, 8)
        mutated["stop_loss"] = round(entry + sl_dist, 8)
    else:
        mutated["take_profit"] = round(entry + tp_dist, 8)
        mutated["stop_loss"] = round(entry - sl_dist, 8)

    mutated["gross_tp"] = mutated["take_profit"]
    cost = mutated.get("transaction_cost_pct", 0.001)
    if mutated["direction"] == "SHORT":
        mutated["net_tp"] = round(mutated["take_profit"] * (1 + cost), 8)
    else:
        mutated["net_tp"] = round(mutated["take_profit"] * (1 - cost), 8)

    # Reduce confidence (inverse is experimental)
    conf = mutated.get("confidence", 0.5)
    mutated["confidence"] = round(conf * 0.6, 3)

    # Tag
    mutated["strategy"] = variant_name
    mutated["mutation_type"] = "INVERSE"
    mutated["parent_strategy"] = parent_strategy
    mutated["id"] = mutated.get("id", "") + "_INV"

    return mutated


def _mutate_tighter(pick: dict, parent_strategy: str) -> dict | None:
    """Mutation B: TIGHTER parameters -- higher confidence, tighter TP/SL, volume filter."""
    mutated = deepcopy(pick)
    variant_name = f"TIGHT_{parent_strategy}"

    entry = mutated.get("entry_price", 0)
    if entry <= 0:
        return None

    direction = str(mutated.get("direction", "LONG")).upper()

    # Raise confidence threshold by 0.10
    conf = mutated.get("confidence", 0.5)
    new_conf = conf + 0.10
    if new_conf > 1.0:
        new_conf = 0.95
    mutated["confidence"] = round(new_conf, 3)

    # Tighter TP: 1.0x ATR (use 2% as proxy if no ATR available)
    atr = mutated.get("atr_at_entry")
    if atr and atr > 0:
        tp_distance = atr * 1.0
        sl_distance = atr * 0.75
    else:
        # Use 2% TP, 1.5% SL as default tight parameters
        tp_distance = entry * 0.02
        sl_distance = entry * 0.015

    if direction in ("LONG", "BUY"):
        mutated["take_profit"] = round(entry + tp_distance, 8)
        mutated["stop_loss"] = round(entry - sl_distance, 8)
    else:
        mutated["take_profit"] = round(entry - tp_distance, 8)
        mutated["stop_loss"] = round(entry + sl_distance, 8)

    mutated["gross_tp"] = mutated["take_profit"]
    cost = mutated.get("transaction_cost_pct", 0.001)
    if direction in ("SHORT", "SELL"):
        mutated["net_tp"] = round(mutated["take_profit"] * (1 + cost), 8)
    else:
        mutated["net_tp"] = round(mutated["take_profit"] * (1 - cost), 8)

    # Volume filter: require volume_ratio > 1.5
    vol_ratio = mutated.get("volume_ratio")
    if vol_ratio is not None and vol_ratio < 1.5:
        return None  # Filtered out -- volume too low

    # Tag
    mutated["strategy"] = variant_name
    mutated["mutation_type"] = "TIGHTER"
    mutated["parent_strategy"] = parent_strategy
    mutated["id"] = mutated.get("id", "") + "_TIGHT"

    return mutated


def _mutate_regime_gated(pick: dict, parent_strategy: str) -> dict | None:
    """Mutation C: REGIME-GATED -- only allow strategy in compatible regime."""
    edge_type = STRATEGY_EDGE_TYPE.get(parent_strategy, "momentum")
    allowed_regimes = REGIME_ALLOWLIST.get(edge_type, {"BULL", "STRONG_BULL"})

    current_regime = _get_current_regime()

    if current_regime not in allowed_regimes and current_regime != "UNKNOWN":
        # Block this pick -- regime mismatch
        log.info(
            f"[REGIME_GATE] Blocking {parent_strategy} pick: "
            f"regime={current_regime}, allowed={allowed_regimes}"
        )
        return None

    mutated = deepcopy(pick)
    variant_name = f"RG_{parent_strategy}"

    # Boost confidence slightly when regime is compatible
    conf = mutated.get("confidence", 0.5)
    mutated["confidence"] = round(min(conf * 1.15, 0.95), 3)

    # Tag
    mutated["strategy"] = variant_name
    mutated["mutation_type"] = "REGIME_GATED"
    mutated["parent_strategy"] = parent_strategy
    mutated["regime_at_mutation"] = current_regime
    mutated["allowed_regimes"] = list(allowed_regimes)
    mutated["id"] = mutated.get("id", "") + "_RG"

    return mutated


# ---------------------------------------------------------------------------
# Strategy-as-callable wrappers
# ---------------------------------------------------------------------------

# The target strategies for mutation
MUTATION_TARGETS = [
    "winner_pattern_precursor",
    "volume_spike_backfill",
    "hl_funding_fade",
    "momentum_catcher",
    "ml_enhanced_BTCUSDT_15m_D_ensemble_stack",
    "ml_enhanced_RENDERUSDT_1h_D_ensemble_stack",
    "ml_enhanced_RENDERUSDT_4h_D_ensemble_stack",
    "kimi_signal_tracking",
    "macd_rsi_confluence",
    "st_multi_day_momentum",
    "lower_wick_absorption",
    "hh-hl-scout",
    "macd-momentum",
    "intermarket-flow-scout",
    "binance_smart_money",
    "macd_crossover",
    "volume_spike_breakout",
    "stochrsi_macd_combo",
]


def _make_mutation_strategy(parent_name: str, mutation_type: str):
    """Factory: create a callable strategy function that wraps a parent strategy
    and applies the specified mutation to every pick it generates."""

    mutation_fn = {
        "INVERSE": _mutate_inverse,
        "TIGHTER": _mutate_tighter,
        "REGIME_GATED": _mutate_regime_gated,
    }[mutation_type]

    variant_name = {
        "INVERSE": f"INV_{parent_name}",
        "TIGHTER": f"TIGHT_{parent_name}",
        "REGIME_GATED": f"RG_{parent_name}",
    }[mutation_type]

    def mutated_strategy(df, context=None, **kwargs):
        """Run parent strategy, then mutate every pick."""
        # Lazy import the parent strategy
        parent_fn = _resolve_parent_strategy(parent_name)
        if parent_fn is None:
            return []

        try:
            raw_picks = parent_fn(df, context=context, **kwargs) if context else parent_fn(df, **kwargs)
        except Exception as e:
            log.warning(f"[MUTATION] Parent {parent_name} failed: {e}")
            return []

        if not raw_picks:
            return []

        mutated_picks = []
        for pick in raw_picks:
            mutated = mutation_fn(pick, parent_name)
            if mutated is not None:
                mutated_picks.append(mutated)

        if mutated_picks:
            log.info(
                f"[MUTATION] {variant_name}: {len(mutated_picks)} picks "
                f"from {len(raw_picks)} parent picks"
            )

        return mutated_picks

    mutated_strategy.__name__ = variant_name
    mutated_strategy.__doc__ = (
        f"Emergency mutation ({mutation_type}) of {parent_name}. "
        f"Auto-generated by emergency_mutations.py for 48h forward test."
    )

    return mutated_strategy


def _resolve_parent_strategy(name: str):
    """Resolve a parent strategy name to its callable function."""
    # Try each known strategy registry
    _registries = []

    try:
        from crypto_strategies import CRYPTO_STRATEGIES
        _registries.append(CRYPTO_STRATEGIES)
    except ImportError:
        pass

    try:
        from advanced_strategies import ADVANCED_STRATEGIES
        _registries.append(ADVANCED_STRATEGIES)
    except ImportError:
        pass

    try:
        from survivor_strategies import SURVIVOR_STRATEGIES
        _registries.append(SURVIVOR_STRATEGIES)
    except ImportError:
        pass

    try:
        from high_accuracy_strategies import HIGH_ACCURACY_STRATEGIES
        _registries.append(HIGH_ACCURACY_STRATEGIES)
    except ImportError:
        pass

    try:
        from novel_strategies import NOVEL_STRATEGIES
        _registries.append(NOVEL_STRATEGIES)
    except ImportError:
        pass

    for reg in _registries:
        if name in reg:
            return reg[name]

    # Special cases: standalone modules
    if name == "momentum_catcher":
        try:
            from momentum_catcher import scan_momentum
            return scan_momentum
        except ImportError:
            pass

    if name == "winner_pattern_precursor":
        try:
            from winner_pattern_strategy import scan_winner_patterns
            return scan_winner_patterns
        except ImportError:
            pass

    if name == "volume_spike_backfill":
        try:
            from crypto_strategies import CRYPTO_STRATEGIES as cs
            return cs.get("volume_spike_backfill")
        except ImportError:
            pass

    if name.startswith("ml_enhanced_"):
        # ML strategies are dynamically generated; we can't easily import them.
        # For the inverse mutation, we just need to flip existing picks.
        return None

    log.warning(f"[MUTATION] Cannot resolve parent strategy: {name}")
    return None


# ---------------------------------------------------------------------------
# Build the EMERGENCY_MUTATION_STRATEGIES dict
# ---------------------------------------------------------------------------

EMERGENCY_MUTATION_STRATEGIES = {}

for _parent in MUTATION_TARGETS:
    for _mut_type in ("INVERSE", "TIGHTER", "REGIME_GATED"):
        _key = {
            "INVERSE": f"INV_{_parent}",
            "TIGHTER": f"TIGHT_{_parent}",
            "REGIME_GATED": f"RG_{_parent}",
        }[_mut_type]

        EMERGENCY_MUTATION_STRATEGIES[_key] = _make_mutation_strategy(_parent, _mut_type)

log.info(f"[MUTATION] Loaded {len(EMERGENCY_MUTATION_STRATEGIES)} emergency mutation variants")


# ---------------------------------------------------------------------------
# Forward-test tracking
# ---------------------------------------------------------------------------

def load_forward_test() -> dict:
    """Load the forward test tracking file."""
    if MUTATION_FORWARD_TEST_PATH.exists():
        try:
            with open(MUTATION_FORWARD_TEST_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"variants": {}, "created": datetime.now(timezone.utc).isoformat()}


def save_forward_test(data: dict):
    """Save the forward test tracking file."""
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(MUTATION_FORWARD_TEST_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def register_mutation_pick(variant_name: str, pick: dict, won: bool | None = None):
    """Track a mutation variant pick in the forward test."""
    ft = load_forward_test()
    if variant_name not in ft["variants"]:
        # Determine parent and mutation type from variant name
        parent = variant_name
        mut_type = "UNKNOWN"
        for prefix, mtype in [("INV_", "INVERSE"), ("TIGHT_", "TIGHTER"), ("RG_", "REGIME_GATED")]:
            if variant_name.startswith(prefix):
                parent = variant_name[len(prefix):]
                mut_type = mtype
                break

        ft["variants"][variant_name] = {
            "parent_strategy": parent,
            "mutation_type": mut_type,
            "start_date": datetime.now(timezone.utc).isoformat(),
            "picks": 0,
            "wins": 0,
            "losses": 0,
            "pending": 0,
            "total_pnl_pct": 0.0,
            "pick_ids": [],
        }

    v = ft["variants"][variant_name]
    v["picks"] += 1
    v["pick_ids"].append(pick.get("id", "unknown"))

    if won is True:
        v["wins"] += 1
    elif won is False:
        v["losses"] += 1
    else:
        v["pending"] += 1

    if pick.get("pnl_pct") is not None:
        pnl = pick["pnl_pct"]
        if isinstance(pnl, (int, float)) and not math.isnan(pnl):
            v["total_pnl_pct"] += pnl

    save_forward_test(ft)


def get_mutation_report() -> dict:
    """Get a summary of all mutation variant performance."""
    ft = load_forward_test()
    report = {}
    for name, v in ft.get("variants", {}).items():
        total_decided = v["wins"] + v["losses"]
        wr = v["wins"] / total_decided if total_decided > 0 else None
        report[name] = {
            "parent": v["parent_strategy"],
            "mutation_type": v["mutation_type"],
            "picks": v["picks"],
            "wins": v["wins"],
            "losses": v["losses"],
            "pending": v["pending"],
            "win_rate": round(wr, 4) if wr is not None else None,
            "total_pnl_pct": round(v["total_pnl_pct"], 4),
            "verdict": _verdict(wr, total_decided),
        }
    return report


def _verdict(wr, total_decided):
    """Determine if a mutation should be promoted, killed, or needs more data."""
    if total_decided < 5:
        return "NEEDS_DATA"
    if wr is not None and wr >= 0.50:
        return "PROMOTE"
    if wr is not None and wr >= 0.35:
        return "KEEP_TESTING"
    return "KILL"


# ---------------------------------------------------------------------------
# Utility: get all variant names for a parent strategy
# ---------------------------------------------------------------------------

def get_mutation_variants(parent_name: str) -> list[str]:
    """Return all variant names for a parent strategy."""
    return [
        k for k in EMERGENCY_MUTATION_STRATEGIES
        if k.endswith(parent_name) or k.endswith(f"_{parent_name}")
    ]


# ---------------------------------------------------------------------------
# Initialize forward test tracking if not exists
# ---------------------------------------------------------------------------

def initialize_forward_test():
    """Create the forward test file with all 15 variants registered."""
    ft = load_forward_test()
    now = datetime.now(timezone.utc).isoformat()

    for parent in MUTATION_TARGETS:
        for mut_type, prefix in [("INVERSE", "INV_"), ("TIGHTER", "TIGHT_"), ("REGIME_GATED", "RG_")]:
            variant_name = f"{prefix}{parent}"
            if variant_name not in ft["variants"]:
                ft["variants"][variant_name] = {
                    "parent_strategy": parent,
                    "mutation_type": mut_type,
                    "start_date": now,
                    "picks": 0,
                    "wins": 0,
                    "losses": 0,
                    "pending": 0,
                    "total_pnl_pct": 0.0,
                    "pick_ids": [],
                    "original_wr": _get_original_wr(parent),
                    "original_pf": _get_original_pf(parent),
                }

    save_forward_test(ft)
    log.info(f"[MUTATION] Forward test initialized with {len(ft['variants'])} variants")
    return ft


def _get_original_wr(parent: str) -> float:
    """Look up original win rate from strategy_mutations.json."""
    wr_map = {
        "winner_pattern_precursor": 0.1635,
        "volume_spike_backfill": 0.30,
        "ml_enhanced_BTCUSDT_15m_D_ensemble_stack": 0.0,
        "ml_enhanced_RENDERUSDT_1h_D_ensemble_stack": 0.20,
        "ml_enhanced_RENDERUSDT_4h_D_ensemble_stack": 0.0,
        "kimi_signal_tracking": 0.13,
        "macd_rsi_confluence": 0.12,
        "lower_wick_absorption": 0.08,
        "st_multi_day_momentum": 0.0,
        "hh-hl-scout": 0.0,
        "macd-momentum": 0.0,
        "intermarket-flow-scout": 0.0,
        "binance_smart_money": 0.25,
    }
    return wr_map.get(parent, 0.0)


def _get_original_pf(parent: str) -> float:
    """Look up original profit factor from strategy_mutations.json."""
    pf_map = {
        "winner_pattern_precursor": 0.325,
        "volume_spike_backfill": 0.777,
        "ml_enhanced_BTCUSDT_15m_D_ensemble_stack": 0.0,
        "ml_enhanced_RENDERUSDT_1h_D_ensemble_stack": 0.25,
        "ml_enhanced_RENDERUSDT_4h_D_ensemble_stack": 0.0,
    }
    return pf_map.get(parent, 0.0)


# Auto-initialize on import
if not MUTATION_FORWARD_TEST_PATH.exists():
    try:
        initialize_forward_test()
    except Exception as e:
        log.warning(f"[MUTATION] Could not initialize forward test: {e}")
