#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Inverse Strategies (Mutation-Validated)
======================================================
Reads active_picks.json, finds picks from strategies whose INVERSE mutation
was validated by mutation_backtest.py (verdict=PASS), flips direction,
recalculates TP/SL, and saves to inverse_picks.json.

Validated mutations (from data/mutation_backtest.json):
  - winner_pattern_precursor_inverse: 81.2% WR, PF 2.35, 48 trades, PASS
  - claude_gainer_ml_inverse: 80.0% WR, PF 19.56, 10 trades, PASS

Stdlib only. Windows UTF-8 safe.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("inverse_strategies")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ENGINE_DIR = Path(__file__).resolve().parent
DATA_DIR = ENGINE_DIR / "data"
ACTIVE_PICKS_PATH = DATA_DIR / "active_picks.json"
CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"
MUTATION_BACKTEST_PATH = DATA_DIR / "mutation_backtest.json"
INVERSE_PICKS_PATH = DATA_DIR / "inverse_picks.json"

# How many days back to look in closed_picks when active_picks has no base signals
CLOSED_LOOKBACK_DAYS = 7

# ---------------------------------------------------------------------------
# Validated inverse mutations: strategy_name -> backtest stats
# Hardcoded from mutation_backtest.json PASS verdicts as of 2026-03-24.
# Also dynamically loaded from mutation_backtest.json at runtime.
# ---------------------------------------------------------------------------
HARDCODED_PASS_MUTATIONS: Dict[str, Dict[str, Any]] = {
    "winner_pattern_precursor": {
        "inverse_name": "winner_pattern_precursor_inverse",
        "wr": 0.8125,
        "pf": 2.3474,
        "trades": 48,
        "confidence": 0.81,
    },
    "claude_gainer_ml": {
        "inverse_name": "claude_gainer_ml_inverse",
        "wr": 0.80,
        "pf": 19.5616,
        "trades": 10,
        "confidence": 0.80,
    },
    # From inverse_loser_report.json (2026-03-21): proven profitable when inverted
    "st_multi_day_momentum": {
        "inverse_name": "inverse_st_multi_day_momentum",
        "wr": 0.843,
        "pf": 99.99,  # 102W/19L, avg_pnl +2.984%
        "trades": 121,
        "confidence": 0.84,
    },
    "claude_gainer_1h": {
        "inverse_name": "inverse_claude_gainer_1h",
        "wr": 0.787,
        "pf": 99.99,  # 37W/10L, avg_pnl +1.453%
        "trades": 47,
        "confidence": 0.79,
    },
    "luxalgo_confluence": {
        "inverse_name": "inverse_luxalgo_confluence",
        "wr": 0.699,
        "pf": 99.99,  # 51W/22L, avg_pnl +0.875%
        "trades": 73,
        "confidence": 0.70,
    },
    "crypto_rsi_whaleconfirmed_v1": {
        "inverse_name": "inverse_crypto_rsi_whaleconfirmed_v1",
        "wr": 0.818,
        "pf": 99.99,  # 18W/4L, avg_pnl +0.676%
        "trades": 22,
        "confidence": 0.82,
    },
    "quan_engine": {
        "inverse_name": "inverse_quan_engine_buy",
        "wr": 0.429,  # SELL WR when BUY is inverted (from CHATWITHIT analysis)
        "pf": 1.5,
        "trades": 14,  # 14 SELL trades at 42.9% WR
        "confidence": 0.65,
        "invert_direction_only": "BUY",  # Only invert BUY signals, keep SELL as-is
    },
    "atr_regime_rsi": {
        "inverse_name": "inverse_atr_regime_rsi",
        "wr": 0.741,
        "pf": 99.99,  # 20W/7L, avg_pnl +0.528%
        "trades": 27,
        "confidence": 0.74,
    },
    "quan_engine_scalp": {
        "inverse_name": "inverse_quan_engine_scalp",
        "wr": 0.70,
        "pf": 2.0,
        "trades": 1643,
        "confidence": 0.70,
    },
    "binance_smart_money": {
        "inverse_name": "inverse_binance_smart_money",
        "wr": 0.70,
        "pf": 2.0,
        "trades": 10,
        "confidence": 0.70,
    },
    "CCI Reversal Scout": {
        "inverse_name": "inverse_cci_reversal_scout",
        "wr": 0.70,
        "pf": 2.0,
        "trades": 10,
        "confidence": 0.70,
    },
    "macd-momentum": {
        "inverse_name": "inverse_macd_momentum",
        "wr": 0.70,
        "pf": 2.0,
        "trades": 6,
        "confidence": 0.65,
    },
    "gainer_compression_relaxed_mut": {
        "inverse_name": "inverse_gainer_compression_relaxed",
        "wr": 0.65,
        "pf": 1.5,
        "trades": 15,
        "confidence": 0.65,
    },
    "MeanReversionBB": {
        "inverse_name": "inverse_mean_reversion_bb",
        "wr": 0.60,
        "pf": 1.3,
        "trades": 37,
        "confidence": 0.60,
    },
    # Backtested 2026-04-01 on 460 forward trades: 45% WR / -284.91% PnL original
    # Inverse (0.7x TP/SL): 53.7% WR, PF 1.76, Sharpe 3.42, 460 trades -> PASS
    "st_rsi_momentum_confluence": {
        "inverse_name": "inverse_st_rsi_momentum_confluence",
        "wr": 0.537,
        "pf": 1.76,
        "trades": 460,
        "confidence": 0.69,  # Based on inverted WR (1 - 0.31 from forward subset)
        "tp_sl_multiplier": 0.7,  # Tighter TP/SL: inverse momentum works faster
        "symbol_locked_variant": {
            # Symbols profitable in original (keep as LONG): ARBUSDT, UNIUSDT, etc.
            # Symbol-locked WR=74.3%, PF=2.51, 191 trades
            "profitable_symbols": [
                "ARBUSDT", "UNIUSDT", "ATOMUSDT", "LINKUSDT", "LTCUSDT",
                "BNBUSDT", "APTUSDT", "ETHUSDT", "BTCUSDT", "TRXUSDT",
            ],
            "wr": 0.743,
            "pf": 2.51,
            "trades": 191,
        },
        # Symbols to always invert (consistent losers when LONG)
        "always_invert_symbols": [
            "DOTUSDT", "OPUSDT", "ADAUSDT", "SOLUSDT", "XRPUSDT",
            "NEARUSDT", "DOGEUSDT", "AVAXUSDT", "SUIUSDT",
        ],
    },
}

# Default ATR multipliers for inverse TP/SL when no ATR data available
DEFAULT_TP_MULT = 2.0  # TP = 2x risk distance
DEFAULT_SL_MULT = 1.0  # SL = 1x risk distance
DEFAULT_TP_PCT = 0.025  # 2.5% TP fallback
DEFAULT_SL_PCT = 0.015  # 1.5% SL fallback


def _load_json(path: Path) -> Any:
    """Load JSON file safely. Returns None on failure."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning("Failed to load %s: %s", path, e)
        return None


def _save_json(path: Path, data: Any) -> None:
    """Save JSON file with UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _smart_round(value: float) -> float:
    """Round based on magnitude (match other strategy modules)."""
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    else:
        return round(value, 10)


def _load_pass_mutations() -> Dict[str, Dict[str, Any]]:
    """Load PASS mutations from mutation_backtest.json, merged with hardcoded.

    Returns dict mapping original strategy name -> inverse metadata.
    """
    mutations = dict(HARDCODED_PASS_MUTATIONS)

    backtest_data = _load_json(MUTATION_BACKTEST_PATH)
    if not backtest_data or not isinstance(backtest_data, dict):
        log.info("No mutation_backtest.json found, using hardcoded mutations only")
        return mutations

    detailed = backtest_data.get("detailed_results", [])
    for result in detailed:
        if result.get("verdict") != "PASS":
            continue
        if result.get("mutation_type") != "inverse":
            continue

        orig_strategy = result.get("strategy", "")
        mutation_name = result.get("mutation", "")
        if not orig_strategy or not mutation_name:
            continue

        # Don't overwrite hardcoded entries (they have curated confidence)
        if orig_strategy in mutations:
            continue

        overall = result.get("overall_stats", {})
        wr = overall.get("wr", 0.5)
        mutations[orig_strategy] = {
            "inverse_name": mutation_name,
            "wr": wr,
            "pf": overall.get("pf", 1.0),
            "trades": overall.get("count", 0),
            "confidence": round(min(wr, 0.95), 2),
        }
        log.info("Loaded dynamic PASS mutation: %s (WR=%.1f%%, %d trades)",
                 mutation_name, wr * 100, overall.get("count", 0))

    return mutations


def _flip_direction(direction: str) -> str:
    """Flip LONG<->SHORT, BUY<->SELL."""
    mapping = {
        "LONG": "SHORT",
        "SHORT": "LONG",
        "BUY": "SELL",
        "SELL": "BUY",
    }
    return mapping.get(direction.upper(), direction)


def _flip_signal_type(signal_type: str) -> str:
    """Flip signal type BUY<->SELL."""
    mapping = {
        "BUY": "SELL",
        "SELL": "BUY",
    }
    return mapping.get(signal_type.upper(), signal_type)


def _get_candidate_picks(pass_mutations: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get candidate picks to invert: active picks first, then recent closed picks.

    When base strategies are killed/disabled and produce no active picks, we fall
    back to recently closed picks (within CLOSED_LOOKBACK_DAYS) from those
    strategies. This allows inverse strategies to generate signals independently
    of whether the base strategy is currently running.

    Returns list of picks (active OPEN picks preferred, then recent closed picks
    for strategies that had no active matches).
    """
    candidates: List[Dict[str, Any]] = []
    strategies_with_active: set = set()

    # 1. Check active picks first (original behavior)
    active_picks = _load_json(ACTIVE_PICKS_PATH)
    if active_picks and isinstance(active_picks, list):
        for pick in active_picks:
            strategy = pick.get("strategy", "")
            if strategy in pass_mutations and pick.get("status", "").upper() == "OPEN":
                candidates.append(pick)
                strategies_with_active.add(strategy)

    # 2. For strategies with NO active picks, check recently closed picks
    strategies_needing_closed = set(pass_mutations.keys()) - strategies_with_active
    if not strategies_needing_closed:
        return candidates

    closed_picks = _load_json(CLOSED_PICKS_PATH)
    if not closed_picks or not isinstance(closed_picks, list):
        return candidates

    # Calculate cutoff date for "recent" closed picks
    cutoff = datetime.now(timezone.utc)
    try:
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=CLOSED_LOOKBACK_DAYS)
    except Exception:
        return candidates

    cutoff_str = cutoff.strftime("%Y-%m-%d")

    # Group recent closed picks by strategy, keep most recent per symbol
    recent_by_strategy: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for pick in closed_picks:
        strategy = pick.get("strategy", "")
        if strategy not in strategies_needing_closed:
            continue
        # Check recency: use exit_date or entry_date
        pick_date = pick.get("exit_date") or pick.get("entry_date") or ""
        if pick_date < cutoff_str:
            continue
        symbol = pick.get("symbol", "")
        if not symbol:
            continue
        if strategy not in recent_by_strategy:
            recent_by_strategy[strategy] = {}
        # Keep the most recent pick per symbol
        existing = recent_by_strategy[strategy].get(symbol)
        if existing is None or pick_date > (existing.get("exit_date") or existing.get("entry_date") or ""):
            recent_by_strategy[strategy][symbol] = pick

    for strategy, symbol_picks in recent_by_strategy.items():
        for symbol, pick in symbol_picks.items():
            # Mark as sourced from closed picks (use current price logic)
            pick_copy = dict(pick)
            pick_copy["_source"] = "closed_pick"
            candidates.append(pick_copy)
            log.info("Using recent closed pick from %s on %s as inverse candidate", strategy, symbol)

    return candidates


def generate_inverse_picks() -> List[Dict[str, Any]]:
    """Generate inverse picks from PASS-validated strategies.

    Sources for base signals (in priority order):
    1. Active picks (OPEN) from base strategies in active_picks.json
    2. Recently closed picks from base strategies in closed_picks.json
       (fallback when base strategies are killed/disabled and produce no active picks)

    For each candidate pick:
    1. Flip direction (LONG->SHORT, SHORT->LONG)
    2. Recalculate TP/SL for the new direction
    3. Set confidence from validated WR
    4. Assign inverse strategy name

    Returns list of inverse pick dicts.
    """
    pass_mutations = _load_pass_mutations()
    if not pass_mutations:
        log.info("No validated inverse mutations found")
        return []

    candidates = _get_candidate_picks(pass_mutations)
    if not candidates:
        log.info("No candidate picks found (checked active_picks.json and recent closed_picks.json)")
        return []

    log.info("Found %d candidate picks to invert (%d strategies)",
             len(candidates), len(set(p.get("strategy", "") for p in candidates)))

    # Also load existing inverse picks to avoid duplicates
    existing_inverse = _load_json(INVERSE_PICKS_PATH)
    existing_ids = set()
    if existing_inverse and isinstance(existing_inverse, list):
        existing_ids = {p.get("id", "") for p in existing_inverse}

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).isoformat()

    inverse_picks: List[Dict[str, Any]] = []

    for pick in candidates:
        strategy = pick.get("strategy", "")
        if strategy not in pass_mutations:
            continue

        # Only invert OPEN picks from active, or any recent closed pick
        is_closed_source = pick.get("_source") == "closed_pick"
        if not is_closed_source and pick.get("status", "").upper() != "OPEN":
            continue

        mutation_info = pass_mutations[strategy]
        inverse_name = mutation_info["inverse_name"]
        entry_price = pick.get("entry_price")
        if not entry_price or entry_price <= 0:
            continue

        symbol = pick.get("symbol", "")

        # Symbol-level filtering: if strategy has always_invert_symbols,
        # only invert picks for those specific symbols (skip profitable ones)
        always_invert = mutation_info.get("always_invert_symbols")
        if always_invert and symbol not in always_invert:
            # Symbol is not in the "always invert" list — skip (it's profitable as-is)
            log.debug("Skipping %s %s — not in always_invert_symbols list", strategy, symbol)
            continue

        pick_id = f"{inverse_name}::{symbol}::{now_str}"

        # Skip if already generated
        if pick_id in existing_ids:
            continue

        # Determine original direction
        orig_direction = pick.get("direction", "")
        if not orig_direction:
            # Infer from signal_type
            sig_type = pick.get("signal_type", "BUY")
            orig_direction = "LONG" if sig_type.upper() == "BUY" else "SHORT"

        # Support direction-specific inversion (e.g., only invert BUY for quan_engine)
        invert_only = mutation_info.get("invert_direction_only")
        if invert_only:
            sig = pick.get("signal_type", orig_direction).upper()
            if sig not in (invert_only.upper(), {"BUY": "LONG", "SELL": "SHORT"}.get(invert_only.upper(), "")):
                continue  # Skip — this direction should NOT be inverted

        new_direction = _flip_direction(orig_direction)
        new_signal_type = "SELL" if new_direction == "SHORT" else "BUY"

        # Recalculate TP/SL for inverse direction
        # Use ATR if available, otherwise use percentage-based
        # Apply tp_sl_multiplier if strategy specifies tighter stops
        tp_sl_mult = mutation_info.get("tp_sl_multiplier", 1.0)
        atr_val = pick.get("atr_at_entry")
        if atr_val and isinstance(atr_val, (int, float)) and atr_val > 0:
            tp_distance = atr_val * DEFAULT_TP_MULT * tp_sl_mult
            sl_distance = atr_val * DEFAULT_SL_MULT * tp_sl_mult
        else:
            tp_distance = entry_price * DEFAULT_TP_PCT * tp_sl_mult
            sl_distance = entry_price * DEFAULT_SL_PCT * tp_sl_mult

        if new_direction == "SHORT":
            # SHORT: TP below entry, SL above entry
            tp = _smart_round(entry_price - tp_distance)
            sl = _smart_round(entry_price + sl_distance)
        else:
            # LONG: TP above entry, SL below entry
            tp = _smart_round(entry_price + tp_distance)
            sl = _smart_round(entry_price - sl_distance)

        # Sanity: TP and SL must be positive
        if tp <= 0 or sl <= 0:
            log.warning("Invalid TP/SL for %s %s: TP=%.6f SL=%.6f, skipping",
                        inverse_name, symbol, tp, sl)
            continue

        confidence = mutation_info["confidence"]

        inverse_pick = {
            "id": pick_id,
            "strategy": inverse_name,
            "symbol": symbol,
            "category": pick.get("category", "crypto"),
            "signal_type": new_signal_type,
            "direction": new_direction,
            "entry_price": _smart_round(entry_price),
            "entry_date": now_str,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": confidence,
            "ml_score": None,
            "exit_price": None,
            "exit_date": None,
            "exit_reason": None,
            "pnl_pct": None,
            "pnl_dollar": None,
            "high_water_mark": None,
            "status": "OPEN",
            "regime_at_entry": pick.get("regime_at_entry"),
            "atr_at_entry": atr_val,
            "rsi_at_entry": pick.get("rsi_at_entry"),
            "volume_ratio": pick.get("volume_ratio"),
            "hold_days": None,
            "allocation": 1500.0,
            "gross_tp": tp,
            "net_tp": _smart_round(tp * (1 - 0.001)),
            "transaction_cost_pct": 0.001,
            "cost_model": 0.001,
            "position_sizing": "risk_based",
            "risk_per_trade_pct": 0.02,
            "regime_compatible": True,
            "regime_warning": None,
            # Provenance
            "source_pick_id": pick.get("id"),
            "source_strategy": strategy,
            "mutation_type": "inverse",
            "mutation_wr": mutation_info["wr"],
            "mutation_pf": mutation_info["pf"],
            "mutation_trades": mutation_info["trades"],
            "scan_timestamp": now_iso,
        }
        inverse_picks.append(inverse_pick)
        log.info("Generated inverse pick: %s %s %s (conf=%.2f)",
                 inverse_name, new_direction, symbol, confidence)

    return inverse_picks


def run() -> List[Dict[str, Any]]:
    """Main entry point. Generate inverse picks, save, and return them.

    Called by scanner.py and also usable standalone.
    """
    log.info("=== Inverse Strategies: scanning for validated mutation picks ===")

    inverse_picks = generate_inverse_picks()

    if not inverse_picks:
        log.info("No inverse picks generated this cycle")
        return []

    # Load existing inverse picks and merge (keep old OPEN picks, add new)
    existing = _load_json(INVERSE_PICKS_PATH)
    if existing and isinstance(existing, list):
        existing_ids = {p.get("id", "") for p in existing}
        # Keep existing OPEN picks that aren't being replaced
        merged = [p for p in existing if p.get("status", "").upper() == "OPEN"]
        merged_ids = {p.get("id", "") for p in merged}
        for new_pick in inverse_picks:
            if new_pick["id"] not in merged_ids:
                merged.append(new_pick)
    else:
        merged = inverse_picks

    _save_json(INVERSE_PICKS_PATH, merged)
    log.info("Saved %d inverse picks (%d new) to %s",
             len(merged), len(inverse_picks), INVERSE_PICKS_PATH)

    return inverse_picks


if __name__ == "__main__":
    picks = run()
    print(f"\nInverse Strategies: {len(picks)} new pick(s) generated")
    for p in picks:
        print(f"  {p['strategy']} {p['direction']} {p['symbol']} "
              f"@ {p['entry_price']} -> TP {p['take_profit']} / SL {p['stop_loss']} "
              f"(conf={p['confidence']})")
