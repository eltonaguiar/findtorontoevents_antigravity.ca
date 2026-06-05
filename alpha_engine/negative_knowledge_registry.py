#!/usr/bin/env python3
"""
Negative Knowledge Registry (IDEA 6 from data audit)

Blocks known losing patterns based on historical data analysis:
- Symbol-level: TRXUSDT, AMZN, MSFT, PG with documented losses
- Strategy-level: ml_bg_system_a/b/c/ensemble with PF 0.00-0.14
- Combo-level: Keltner × any_altcoin with 0-2% WR
- Time-level: UTC 02,08,13,20 with <35% WR
- Direction-level: SHORT without PROVEN tier = 34.6% WR
- Confidence-level: 0.85+ with 33.9% WR (overconfidence trap)
- R:R: 2.5+ with 30.6% WR (anti-predictive)
"""
from __future__ import annotations
import json
import os
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"

# Static blocked patterns from audit data
BLOCKED_SYMBOLS = {
    "TRXUSDT": {"wr": 33, "total_pnl": -81.76, "n": 132},
    "AMZN": {"wr": 0, "total_pnl": -13.31, "n": 15},
    "MSFT": {"wr": 0, "total_pnl": -39.62, "n": 22},
    "PG": {"wr": 0, "total_pnl": -38.73, "n": 14},
    "MATICUSDT": {"wr": 0, "total_pnl": 0, "n": 553},  # Already in SYMBOL_BLOCKLIST
    "UUSDT": {"wr": 0, "total_pnl": -2.26, "n": 23},
    "JTOUSDT": {"wr": 0, "total_pnl": 0, "n": 15},
}

# Strategy systems with documented PF < 1.0 (losing strategies)
BLOCKED_STRATEGY_SYSTEMS = {
    "ml_bg_system_a": {"pf": 0.14, "wr": 10.5, "n": 19},
    "ml_bg_system_b": {"pf": 0.02, "wr": 5.3, "n": 19},
    "ml_bg_system_c": {"pf": 0.00, "wr": 0, "n": 5},
    "ml_bg_ensemble": {"pf": 0.00, "wr": 0, "n": 8},
    # mega_mutation REMOVED from block: stale n=7/14.3% entry was wrong.
    # Current live DB (2026-06-05): n=296, WR=63.9%, PF=3.12 — GENUINE T2+ edge.
    # 39 distinct close dates, 8 symbols, HHI=0.128. See reports/wr_scrutiny_honest_2026-06-05.md
    "momentum_evolver": {"pf": 0.00, "wr": 0, "n": 8},
    "contrarian_evolver": {"pf": 0.00, "wr": 0, "n": 5},
    "st_rsi_momentum_confluence": {"pf": 0.20, "wr": 12.0, "n": 108},
    "enhanced_ml_A_xgboost": {"pf": 0.50, "wr": 29.3, "n": 123},
    "proven_triple_ema_prop": {"pf": 0.30, "wr": 14.0, "n": 980},
    "proven_propfirm_cons_prop": {"pf": 0.25, "wr": 17.0, "n": 1088},
    # --- Added 2026-06-05: live DB verified 0% WR, near-100% null-close picks ---
    # Source: reports/wr_scrutiny_honest_2026-06-05.md (queries against live trading_picks)
    "polymarket_whale_tracker": {"pf": 0.00, "wr": 0.0, "n": 1582, "null_close_pct": 100},
    "short_dominant_engine": {"pf": 0.00, "wr": 0.0, "n": 1840, "null_close_pct": 99.9},
    "polymarket_momentum": {"pf": 0.00, "wr": 0.0, "n": 389, "null_close_pct": 100},
    "copy_trader_polymarket": {"pf": 0.00, "wr": 0.1, "n": 1183, "null_close_pct": 99.9},
    "luxalgo_filters": {"pf": 0.00, "wr": 0.0, "n": 2121, "null_close_pct": 3.8},
    # signal_validation: creates stale ghost picks (322/353 open picks >7d old)
    "signal_validation": {"pf": None, "wr": None, "n": 353, "reason": "ghost_picks_stale"},
    # --- Added 2026-06-05 Session 2: confirmed bleeders across all classes ---
    # multi_asset_copytrader: FOREX WR=45.7% PF=1.02 (true, post-outlier-removal);
    #   COMMODITY WR=34.4% PF=0.81 (n=677). Also caused 3,495 extreme-pnl FOREX
    #   rows (CADJPY +427%, NZDUSD +7955%) = price-feed unit-mismatch bugs.
    "multi_asset_copytrader": {"pf": 0.91, "wr": 44.8, "n": 1971, "reason": "consistent_loser_all_classes+price_feed_bugs"},
    # forex_copy_trader: WR=39.7% PF=0.84 on n=63 — persistent losing FOREX source
    "forex_copy_trader": {"pf": 0.84, "wr": 39.7, "n": 63, "reason": "consistent_loser_forex"},
}

# Time-of-day blocks (UTC hours with <35% WR)
BLOCKED_HOURS_UTC = {2, 8, 13, 20}

# Confidence overconfidence trap (0.85+ = 33.9% WR)
HIGH_CONF_THRESHOLD = 0.85

# R:R anti-predictive threshold (>2.5 = 30.6% WR)
RR_BLOCK_THRESHOLD = 2.5

# Direction blocks
SHORT_BLOCK_THRESHOLD = 40  # Block SHORTs below this WR threshold for the strategy


def load_strategy_performance() -> dict:
    """Load strategy performance data to dynamically identify losing strategies."""
    perf_path = _DATA_DIR / "strategy_performance.json"
    if perf_path.exists():
        try:
            with open(perf_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def check_symbol_block(pick: dict) -> str | None:
    """Check if symbol is blocked. Returns reason if blocked, None if OK."""
    symbol = pick.get("symbol", "").upper()
    if symbol in BLOCKED_SYMBOLS:
        block_info = BLOCKED_SYMBOLS[symbol]
        return f"SYMBOL_BLOCK:{symbol} (WR {block_info['wr']}%, n={block_info['n']})"
    return None


def check_strategy_block(pick: dict) -> str | None:
    """Check if strategy system is blocked."""
    strategy = pick.get("strategy", "").lower()
    source_system = pick.get("source_system", "").lower()
    
    # Check exact match
    if strategy in BLOCKED_STRATEGY_SYSTEMS:
        info = BLOCKED_STRATEGY_SYSTEMS[strategy]
        return f"STRATEGY_BLOCK:{strategy} (PF {info['pf']:.2f}, WR {info['wr']}%)"
    
    if source_system in BLOCKED_STRATEGY_SYSTEMS:
        info = BLOCKED_STRATEGY_SYSTEMS[source_system]
        return f"STRATEGY_BLOCK:{source_system} (PF {info['pf']:.2f}, WR {info['wr']}%)"
    
    # Check prefix matches (ml_bg_system_a, ml_bg_system_b, etc.)
    for blocked, info in BLOCKED_STRATEGY_SYSTEMS.items():
        if strategy.startswith(blocked) or source_system.startswith(blocked):
            return f"STRATEGY_PREFIX_BLOCK:{blocked} (PF {info['pf']:.2f})"
    
    return None


def check_time_block(pick: dict) -> str | None:
    """Check if pick was created during blocked UTC hours."""
    from datetime import datetime, timezone
    
    # Get pick creation time
    entry_date = pick.get("entry_date") or pick.get("open_time") or pick.get("timestamp")
    if not entry_date:
        return None
    
    try:
        if isinstance(entry_date, str):
            dt = datetime.fromisoformat(entry_date.replace("Z", "+00:00"))
        else:
            dt = entry_date
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        hour = dt.hour
        if hour in BLOCKED_HOURS_UTC:
            return f"TIME_BLOCK:UTC {hour} (<35% WR historically)"
    except Exception:
        pass
    
    return None


def check_confidence_block(pick: dict) -> str | None:
    """Check if confidence is in overconfidence trap range."""
    conf = pick.get("confidence")
    if conf is None:
        return None
    
    try:
        conf_val = float(conf)
        if conf_val >= HIGH_CONF_THRESHOLD:
            return f"CONF_BLOCK:confidence {conf_val:.2f} >= {HIGH_CONF_THRESHOLD} (33.9% WR trap)"
    except (ValueError, TypeError):
        pass
    
    return None


def check_rr_block(pick: dict, live_price: float, entry: float, tp: float, sl: float) -> str | None:
    """Check if R:R is in anti-predictive range."""
    if not all([live_price, entry, tp, sl]):
        return None
    
    direction = pick.get("direction", "LONG").upper()
    try:
        if direction in ("LONG", "BUY"):
            risk = abs(live_price - sl)
            reward = abs(tp - live_price)
        else:
            risk = abs(sl - live_price)
            reward = abs(live_price - tp)
        
        if risk > 0:
            rr = reward / risk
            if rr > RR_BLOCK_THRESHOLD:
                return f"RR_BLOCK:R:R {rr:.2f} > {RR_BLOCK_THRESHOLD} (30.6% WR)"
    except Exception:
        pass
    
    return None


def check_direction_block(pick: dict, strategy_perf: dict) -> str | None:
    """Check if SHORT direction is blocked (low WR for strategy)."""
    direction = pick.get("direction", "LONG").upper()
    if direction not in ("SHORT", "SELL"):
        return None
    
    strategy = pick.get("strategy", "").lower()
    
    # Get strategy performance - check both overall and SHORT-specific WR
    perf = strategy_perf.get(strategy, {})
    wr = perf.get("win_rate", perf.get("wr", 0))
    
    # If we have performance data and SHORT WR is below threshold
    if wr and wr < SHORT_BLOCK_THRESHOLD:
        # Exception: allow if strategy is in PROVEN_WINNERS
        from alpha_engine.smart_picks_engine import PROVEN_WINNERS
        if strategy in PROVEN_WINNERS or strategy.startswith("copy_hl_"):
            return None
        return f"DIRECTION_BLOCK:SHORT WR {wr:.1f}% < {SHORT_BLOCK_THRESHOLD}%"
    
    return None


def check_negative_knowledge(pick: dict, live_price: float = None, entry: float = None, 
                             tp: float = None, sl: float = None) -> str | None:
    """Main function: Check pick against all negative knowledge blocks.
    
    Returns:
        str (blocking reason) or None (pick passes all blocks)
    """
    # 1. Symbol block
    reason = check_symbol_block(pick)
    if reason:
        return reason
    
    # 2. Strategy system block
    reason = check_strategy_block(pick)
    if reason:
        return reason
    
    # 3. Time-of-day block
    reason = check_time_block(pick)
    if reason:
        return reason
    
    # 4. Confidence overconfidence block
    reason = check_confidence_block(pick)
    if reason:
        return reason
    
    # 5. R:R anti-predictive block
    if all([live_price, entry, tp, sl]):
        reason = check_rr_block(pick, live_price, entry, tp, sl)
        if reason:
            return reason
    
    # 6. Direction block (SHORT with low WR)
    strategy_perf = load_strategy_performance()
    reason = check_direction_block(pick, strategy_perf)
    if reason:
        return reason
    
    return None


def get_blocked_patterns_summary() -> dict:
    """Get summary of all blocked patterns for audit/logging."""
    return {
        "blocked_symbols": list(BLOCKED_SYMBOLS.keys()),
        "blocked_strategies": list(BLOCKED_STRATEGY_SYSTEMS.keys()),
        "blocked_hours_utc": list(BLOCKED_HOURS_UTC),
        "high_conf_threshold": HIGH_CONF_THRESHOLD,
        "rr_block_threshold": RR_BLOCK_THRESHOLD,
        "short_wr_threshold": SHORT_BLOCK_THRESHOLD,
    }


if __name__ == "__main__":
    import pprint
    pprint.pprint(get_blocked_patterns_summary())