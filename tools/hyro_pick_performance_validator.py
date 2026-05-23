#!/usr/bin/env python3
"""
HyroTrader Pick Performance Validator
======================================
Validates whether signals from hyro_signal_history.json and hyro_quan_bridge.json
actually performed as predicted by checking real price action from Binance.

For each historical signal with entry/TP/SL:
  - Fetches 1h klines starting from signal time
  - Checks if TP or SL was hit first within the max_hold_bars window
  - Records outcome: WIN (TP hit), LOSS (SL hit), EXPIRED (neither hit in time)
  - Computes per-strategy and per-symbol strength scores

Output: audit_dashboard/data/hyro_pick_performance.json
  Consumed by the HyroTrader dashboard (Table 4 — Signal Strength & Performance).

Usage:
  python tools/hyro_pick_performance_validator.py [--save] [--lookback-days 14]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "audit_dashboard" / "data"
ALPHA_DATA_DIR = REPO / "alpha_engine" / "data"
SIGNAL_HISTORY_PATH = DATA_DIR / "hyro_signal_history.json"
QUAN_BRIDGE_PATH = DATA_DIR / "hyro_quan_bridge.json"
CLOSED_PICKS_PATH = ALPHA_DATA_DIR / "closed_picks.json"
DASHBOARD_PAYLOAD_PATH = ALPHA_DATA_DIR / "dashboard_payload.json"
OUTPUT_PATH = DATA_DIR / "hyro_pick_performance.json"

BINANCE_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

# Max bars to check forward for TP/SL hit (default SCALP=8h, SWING=24h)
DEFAULT_MAX_HOLD_BARS = 24
# Binance API retry count per mirror
MAX_RETRIES_PER_MIRROR = 2


def fetch_klines(symbol: str, interval: str, start_ms: int, limit: int = 500) -> list:
    """Fetch klines with Binance mirror failover + retry."""
    for attempt in range(MAX_RETRIES_PER_MIRROR):
        for base in BINANCE_MIRRORS:
            url = (
                f"{base}/api/v3/klines?"
                f"symbol={symbol}&interval={interval}"
                f"&startTime={start_ms}&limit={limit}"
            )
            try:
                req = Request(url, headers={"User-Agent": "HyroValidator/1.0"})
                with urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read())
                    if data:
                        return data
            except (URLError, OSError, json.JSONDecodeError) as e:
                log.debug(f"Mirror {base} failed for {symbol} (attempt {attempt+1}): {e}")
                continue
        if attempt < MAX_RETRIES_PER_MIRROR - 1:
            log.info(f"  Retrying klines for {symbol} (attempt {attempt+2})...")
            time.sleep(1.0)
    log.warning(f"All Binance mirrors failed for {symbol} after {MAX_RETRIES_PER_MIRROR} retries")
    return []


def check_signal_outcome(
    symbol: str,
    direction: str,
    entry: float,
    tp: float,
    sl: float,
    signal_time_ms: int,
    max_hold_bars: int = DEFAULT_MAX_HOLD_BARS,
) -> dict:
    """
    Check if a signal hit TP or SL first by fetching klines from signal time.
    Returns outcome dict with result, bars_to_result, max_favorable_excursion, etc.
    """
    # Guard: if signal is younger than one 1h bar (3600000 ms), no closed candle
    # exists yet for validation. Mark PENDING so the next workflow run retries,
    # instead of poisoning the W/L stats with NO_DATA (bug: bridge writes signals
    # with signal_time=now, validator runs seconds later and gets empty klines).
    now_ms = int(time.time() * 1000)
    if now_ms - signal_time_ms < 3_600_000:
        return {"result": "PENDING", "bars_checked": 0,
                "reason": "signal younger than 1h — awaiting closed candle"}
    klines = fetch_klines(symbol, "1h", signal_time_ms, limit=max_hold_bars + 5)
    if not klines:
        return {"result": "NO_DATA", "bars_checked": 0}

    is_long = direction.upper() in ("BUY", "LONG")
    bars_checked = 0
    mfe = 0.0  # max favorable excursion
    mae = 0.0  # max adverse excursion

    for k in klines:
        close_time_ms = k[6]
        if close_time_ms <= signal_time_ms:
            continue
        bars_checked += 1
        if bars_checked > max_hold_bars:
            break

        high = float(k[2])
        low = float(k[3])
        close = float(k[4])

        if is_long:
            favorable = (high - entry) / entry * 100
            adverse = (entry - low) / entry * 100
            mfe = max(mfe, favorable)
            mae = max(mae, adverse)

            if high >= tp:
                return {
                    "result": "WIN",
                    "bars_to_result": bars_checked,
                    "hit_price": tp,
                    "mfe_pct": round(mfe, 3),
                    "mae_pct": round(mae, 3),
                    "pnl_pct": round((tp - entry) / entry * 100, 3),
                }
            if low <= sl:
                return {
                    "result": "LOSS",
                    "bars_to_result": bars_checked,
                    "hit_price": sl,
                    "mfe_pct": round(mfe, 3),
                    "mae_pct": round(mae, 3),
                    "pnl_pct": round((sl - entry) / entry * 100, 3),
                }
        else:
            favorable = (entry - low) / entry * 100
            adverse = (high - entry) / entry * 100
            mfe = max(mfe, favorable)
            mae = max(mae, adverse)

            if low <= tp:
                return {
                    "result": "WIN",
                    "bars_to_result": bars_checked,
                    "hit_price": tp,
                    "mfe_pct": round(mfe, 3),
                    "mae_pct": round(mae, 3),
                    "pnl_pct": round((entry - tp) / entry * 100, 3),
                }
            if high >= sl:
                return {
                    "result": "LOSS",
                    "bars_to_result": bars_checked,
                    "hit_price": sl,
                    "mfe_pct": round(mfe, 3),
                    "mae_pct": round(mae, 3),
                    "pnl_pct": round((entry - sl) / entry * 100, 3),
                }

    # Expired — compute unrealized PnL at last bar
    if klines and bars_checked > 0:
        last_close = float(klines[-1][4])
        if is_long:
            unrealized_pct = round((last_close - entry) / entry * 100, 3)
        else:
            unrealized_pct = round((entry - last_close) / entry * 100, 3)
    else:
        unrealized_pct = 0.0

    return {
        "result": "EXPIRED",
        "bars_checked": bars_checked,
        "mfe_pct": round(mfe, 3),
        "mae_pct": round(mae, 3),
        "unrealized_pnl_pct": unrealized_pct,
    }


def extract_signals_from_history(lookback_days: int = 14) -> list[dict]:
    """Extract testable signals from hyro_signal_history.json."""
    if not SIGNAL_HISTORY_PATH.exists():
        log.warning(f"Signal history not found: {SIGNAL_HISTORY_PATH}")
        return []

    with open(SIGNAL_HISTORY_PATH, "r", encoding="utf-8") as f:
        history = json.load(f)

    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    signals = []

    for scan in history:
        scan_time_str = scan.get("scan_time", "")
        try:
            scan_dt = datetime.fromisoformat(scan_time_str)
        except (ValueError, TypeError):
            continue

        if scan_dt < cutoff:
            continue

        scan_time_ms = int(scan_dt.timestamp() * 1000)

        for sig in scan.get("active_signals", []):
            s = sig.get("signal", {})
            if not s or not s.get("entry") or not s.get("tp") or not s.get("sl"):
                continue
            signals.append({
                "symbol": sig["symbol"],
                "strategy": sig.get("strategy", "unknown"),
                "strategy_label": sig.get("strategy_label", ""),
                "tier": sig.get("tier", "unknown"),
                "direction": s["direction"],
                "entry": s["entry"],
                "tp": s["tp"],
                "sl": s["sl"],
                "rr": s.get("rr", 0),
                "trigger": s.get("trigger", ""),
                "signal_time": scan_time_str,
                "signal_time_ms": scan_time_ms,
                "bar_time": sig.get("bar_time", scan_time_str),
            })

    return signals


def _normalize_symbol_for_binance(symbol: str) -> str:
    """Convert various symbol formats to Binance-compatible USDT pairs."""
    s = symbol.upper().replace("-", "").replace("/", "").replace(" ", "")
    # Handle formats like BTC-USDT, BTC/USDT, BTCUSDT
    if s.endswith("USDT"):
        return s
    if s.endswith("USD") and not s.endswith("USDT"):
        return s + "T"
    if s.endswith("PERP"):
        return s.replace("PERP", "USDT")
    return s + "USDT"


def extract_signals_from_closed_picks(lookback_days: int = 30) -> list[dict]:
    """Extract testable signals from closed_picks.json / dashboard_payload.json.
    
    Closed picks already have a recorded outcome (exit_reason), so we can
    build validated signals directly without re-fetching Binance klines.
    This is the richest data source — typically thousands of entries.
    """
    # Try closed_picks.json first, then dashboard_payload.json
    picks_data = None
    source = "closed_picks"
    
    if CLOSED_PICKS_PATH.exists():
        try:
            with open(CLOSED_PICKS_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, list):
                picks_data = raw
            elif isinstance(raw, dict):
                picks_data = raw.get("picks", raw.get("closed_picks", []))
        except (json.JSONDecodeError, OSError) as e:
            log.warning(f"Failed to load closed_picks.json: {e}")
    
    if not picks_data and DASHBOARD_PAYLOAD_PATH.exists():
        try:
            with open(DASHBOARD_PAYLOAD_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            recent = raw.get("picks", {}).get("recent_closed", [])
            if recent:
                picks_data = recent
                source = "dashboard_payload"
        except (json.JSONDecodeError, OSError) as e:
            log.warning(f"Failed to load dashboard_payload.json: {e}")
    
    if not picks_data:
        log.warning("No closed picks data found")
        return []
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    signals = []
    
    for p in picks_data:
        # Filter to crypto only (HyroTrader is crypto perps)
        asset_class = (p.get("asset_class") or "").upper()
        if asset_class and asset_class not in ("CRYPTO", ""):
            continue
        
        symbol = p.get("symbol", "")
        if not symbol:
            continue
        symbol = _normalize_symbol_for_binance(symbol)
        
        # Need entry/TP/SL for validation
        entry = p.get("entry_price") or p.get("entry")
        tp = p.get("take_profit") or p.get("tp")
        sl = p.get("stop_loss") or p.get("sl")
        if not entry or not tp or not sl:
            continue
        try:
            entry = float(entry)
            tp = float(tp)
            sl = float(sl)
        except (ValueError, TypeError):
            continue
        if entry <= 0 or tp <= 0 or sl <= 0:
            continue
        
        # Parse signal time
        time_str = p.get("entry_time") or p.get("created_at") or p.get("timestamp") or ""
        try:
            sig_dt = datetime.fromisoformat(time_str)
        except (ValueError, TypeError):
            continue
        if sig_dt < cutoff:
            continue
        
        direction = (p.get("signal_type") or p.get("direction") or "BUY").upper()
        if direction in ("SELL", "SHORT"):
            direction = "SELL"
        else:
            direction = "BUY"
        
        strategy = p.get("strategy", "unknown")
        
        # For closed picks, we already know the outcome
        exit_reason = (p.get("exit_reason") or p.get("status") or "").upper()
        pnl_pct = p.get("pnl_pct") or p.get("pnl_percent") or 0
        try:
            pnl_pct = float(pnl_pct)
        except (ValueError, TypeError):
            pnl_pct = 0
        
        # Map exit_reason to WIN/LOSS/EXPIRED
        is_win = exit_reason in ("TP_HIT", "TP", "WON", "TAKE_PROFIT") or pnl_pct > 0
        is_loss = exit_reason in ("SL_HIT", "SL", "LOST", "STOP_LOSS", "FORCE_CLOSED_TOXIC") or (pnl_pct < 0 and not is_win)
        is_expired = exit_reason in ("TIME_EXPIRY", "EXPIRED", "MAX_HOLD", "STALE_DATA")
        
        if is_win:
            result = "WIN"
        elif is_expired:
            result = "EXPIRED"
        elif is_loss:
            result = "LOSS"
        else:
            result = "UNKNOWN"
        
        # Only include signals with clear outcomes
        if result == "UNKNOWN":
            continue
        
        # Estimate bars based on timeframe + hold duration
        timeframe = p.get("timeframe", "1d")
        tf_hours = {"15m": 0.25, "1h": 1, "4h": 4, "1d": 24}.get(timeframe, 24)
        exit_time_str = p.get("exit_time") or p.get("closed_at") or ""
        bars = 24  # default estimate
        if exit_time_str:
            try:
                exit_dt = datetime.fromisoformat(exit_time_str)
                hold_hours = max(1, (exit_dt - sig_dt).total_seconds() / 3600)
                bars = max(1, int(hold_hours / tf_hours))
            except (ValueError, TypeError):
                pass
        
        # Build the signal with pre-validated outcome
        signals.append({
            "symbol": symbol,
            "strategy": strategy,
            "strategy_label": strategy.replace("_", " "),
            "tier": p.get("trust_tier", "unknown"),
            "direction": direction,
            "entry": entry,
            "tp": tp,
            "sl": sl,
            "rr": p.get("risk_reward", round((tp - entry) / (entry - sl), 2) if direction == "BUY" and entry > sl else 0),
            "trigger": f"closed_pick:{exit_reason}",
            "signal_time": time_str,
            "signal_time_ms": int(sig_dt.timestamp() * 1000),
            "bar_time": time_str,
            "regime": p.get("regime", ""),
            "max_hold_bars": bars + 5,
            # Pre-validated outcome from closed pick record
            "_prevalidated_outcome": {
                "result": result,
                "bars_to_result": bars,
                "pnl_pct": pnl_pct,
                "mfe_pct": abs(pnl_pct) * 1.2 if pnl_pct > 0 else 0,  # estimate
                "mae_pct": abs(pnl_pct) * 0.8 if pnl_pct < 0 else 0,  # estimate
            },
            "_source": source,
        })
    
    log.info(f"Extracted {len(signals)} crypto closed-pick signals from {source}")
    return signals


def extract_signals_from_quan_bridge() -> list[dict]:
    """Extract testable signals from hyro_quan_bridge.json (most recent run)."""
    if not QUAN_BRIDGE_PATH.exists():
        log.warning(f"Quan bridge not found: {QUAN_BRIDGE_PATH}")
        return []

    with open(QUAN_BRIDGE_PATH, "r", encoding="utf-8") as f:
        qb = json.load(f)

    gen_at = qb.get("generated_at", "")
    try:
        gen_dt = datetime.fromisoformat(gen_at)
        gen_ms = int(gen_dt.timestamp() * 1000)
    except (ValueError, TypeError):
        gen_ms = int(time.time() * 1000) - 86400000  # fallback 1 day ago

    signals = []
    symbols = qb.get("symbols", {})
    for sym, data in symbols.items():
        ts = data.get("trade_setup")
        ens = data.get("ensemble")
        if not ts or not ens:
            continue
        if not ts.get("entry_price") or not ts.get("take_profit") or not ts.get("stop_loss"):
            continue

        strategies = ens.get("strategies_agreed", [])
        signals.append({
            "symbol": sym,
            "strategy": "quan_ensemble",
            "strategy_label": f"QuanEngine {ens.get('direction', '?')} ({', '.join(strategies)})",
            "tier": "ensemble",
            "direction": ts["direction"],
            "entry": ts["entry_price"],
            "tp": ts["take_profit"],
            "sl": ts["stop_loss"],
            "rr": ts.get("rr_ratio", 0),
            "trigger": f"consensus={ens.get('consensus_pct', 0):.0%} conf={ens.get('avg_confidence', 0):.0%}",
            "signal_time": gen_at,
            "signal_time_ms": gen_ms,
            "bar_time": gen_at,
            "regime": data.get("regime", "UNKNOWN"),
            "hurst": data.get("hurst", 0),
            "max_hold_bars": ts.get("max_hold_bars", DEFAULT_MAX_HOLD_BARS),
        })

    return signals


def compute_strategy_scores(validated: list[dict]) -> dict:
    """Compute per-strategy performance metrics from validated signals."""
    by_strategy = {}
    for v in validated:
        key = v["strategy"]
        if key not in by_strategy:
            by_strategy[key] = {"wins": 0, "losses": 0, "expired": 0, "signals": [],
                                "total_pnl_pct": 0.0, "mfe_sum": 0.0, "mae_sum": 0.0}
        bucket = by_strategy[key]
        outcome = v.get("outcome", {})
        result = outcome.get("result", "NO_DATA")

        if result == "WIN":
            bucket["wins"] += 1
            bucket["total_pnl_pct"] += outcome.get("pnl_pct", 0)
        elif result == "LOSS":
            bucket["losses"] += 1
            bucket["total_pnl_pct"] += outcome.get("pnl_pct", 0)
        elif result == "EXPIRED":
            bucket["expired"] += 1

        bucket["mfe_sum"] += outcome.get("mfe_pct", 0)
        bucket["mae_sum"] += outcome.get("mae_pct", 0)
        bucket["signals"].append(v)

    scores = {}
    for strat, b in by_strategy.items():
        total = b["wins"] + b["losses"] + b["expired"]
        decided = b["wins"] + b["losses"]
        win_rate = b["wins"] / decided if decided > 0 else 0.0
        avg_mfe = b["mfe_sum"] / total if total > 0 else 0.0
        avg_mae = b["mae_sum"] / total if total > 0 else 0.0

        # Signal Strength Score (0-100):
        # - Win rate contributes 40%
        # - Sample size confidence (log scale) contributes 20%
        # - MFE/MAE ratio (edge quality) contributes 25%
        # - Low expiry rate contributes 15%
        wr_score = win_rate * 40

        import math
        sample_score = min(20, math.log2(max(1, decided)) * 5)

        edge_ratio = (avg_mfe / avg_mae) if avg_mae > 0 else 2.0
        edge_score = min(25, edge_ratio * 8.33)

        expiry_rate = b["expired"] / total if total > 0 else 1.0
        expiry_score = (1 - expiry_rate) * 15

        strength_score = round(wr_score + sample_score + edge_score + expiry_score, 1)
        strength_score = max(0, min(100, strength_score))

        # Profit factor
        gross_profit = sum(
            s["outcome"].get("pnl_pct", 0) for s in b["signals"]
            if s.get("outcome", {}).get("result") == "WIN"
        )
        gross_loss = abs(sum(
            s["outcome"].get("pnl_pct", 0) for s in b["signals"]
            if s.get("outcome", {}).get("result") == "LOSS"
        ))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (
            999.0 if gross_profit > 0 else 0.0
        )

        # Grade
        if strength_score >= 75:
            grade = "A"
        elif strength_score >= 60:
            grade = "B"
        elif strength_score >= 45:
            grade = "C"
        elif strength_score >= 30:
            grade = "D"
        else:
            grade = "F"

        if decided >= 5 and win_rate >= 0.6:
            grade += "+"

        scores[strat] = {
            "strength_score": strength_score,
            "grade": grade,
            "win_rate": round(win_rate, 3),
            "wins": b["wins"],
            "losses": b["losses"],
            "expired": b["expired"],
            "total_signals": total,
            "profit_factor": profit_factor,
            "avg_mfe_pct": round(avg_mfe, 3),
            "avg_mae_pct": round(avg_mae, 3),
            "total_pnl_pct": round(b["total_pnl_pct"], 3),
            "edge_ratio": round(edge_ratio, 2),
        }

    return scores


def compute_symbol_scores(validated: list[dict]) -> dict:
    """Compute per-symbol performance metrics."""
    by_symbol = {}
    for v in validated:
        sym = v["symbol"]
        if sym not in by_symbol:
            by_symbol[sym] = {"wins": 0, "losses": 0, "expired": 0, "total_pnl_pct": 0.0}
        outcome = v.get("outcome", {})
        result = outcome.get("result", "NO_DATA")
        if result == "WIN":
            by_symbol[sym]["wins"] += 1
            by_symbol[sym]["total_pnl_pct"] += outcome.get("pnl_pct", 0)
        elif result == "LOSS":
            by_symbol[sym]["losses"] += 1
            by_symbol[sym]["total_pnl_pct"] += outcome.get("pnl_pct", 0)
        elif result == "EXPIRED":
            by_symbol[sym]["expired"] += 1

    scores = {}
    for sym, b in by_symbol.items():
        decided = b["wins"] + b["losses"]
        wr = b["wins"] / decided if decided > 0 else 0.0
        scores[sym] = {
            "win_rate": round(wr, 3),
            "wins": b["wins"],
            "losses": b["losses"],
            "expired": b["expired"],
            "total_pnl_pct": round(b["total_pnl_pct"], 3),
        }
    return scores


def run(lookback_days: int = 30, save: bool = False) -> dict:
    """Main validator loop."""
    log.info(f"Extracting signals (lookback={lookback_days}d)...")

    # Gather signals from ALL sources (closed picks is richest)
    cp_signals = extract_signals_from_closed_picks(lookback_days)
    hist_signals = extract_signals_from_history(lookback_days)
    qb_signals = extract_signals_from_quan_bridge()
    all_signals = cp_signals + hist_signals + qb_signals

    log.info(f"Found {len(cp_signals)} closed-pick + {len(hist_signals)} history + {len(qb_signals)} QuanEngine = {len(all_signals)} total")

    if not all_signals:
        log.warning("No signals to validate")
        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "lookback_days": lookback_days,
            "total_signals": 0,
            "validated_signals": [],
            "strategy_scores": {},
            "symbol_scores": {},
            "summary": {"message": "No signals found to validate"},
        }
        if save:
            OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            log.info(f"Saved empty result to {OUTPUT_PATH}")
        return result

    # Deduplicate (same symbol + strategy + signal_time + rounded entry)
    # Round entry to 4 decimal places to avoid false uniqueness from rounding drift
    seen = set()
    unique_signals = []
    for s in all_signals:
        entry_rounded = round(s.get("entry", 0), 4)
        key = (s["symbol"], s["strategy"], s["signal_time"], entry_rounded)
        if key not in seen:
            seen.add(key)
            unique_signals.append(s)
    log.info(f"After dedup: {len(unique_signals)} unique signals")

    # Cap at 500 signals to avoid massive output / slow dashboard rendering
    MAX_SIGNALS = 500
    if len(unique_signals) > MAX_SIGNALS:
        log.info(f"Capping at {MAX_SIGNALS} most recent signals (from {len(unique_signals)})")
        unique_signals.sort(key=lambda s: s.get("signal_time", ""), reverse=True)
        unique_signals = unique_signals[:MAX_SIGNALS]

    # Validate each signal against actual price action
    #   - Pre-validated signals (from closed_picks.json) skip Binance API
    #   - Live signals fetch klines for validation
    validated = []
    n_prevalidated = 0
    n_fetched = 0
    n_no_data = 0
    for i, sig in enumerate(unique_signals):
        # Use pre-validated outcome if available (from closed picks)
        if "_prevalidated_outcome" in sig:
            outcome = sig["_prevalidated_outcome"]
            n_prevalidated += 1
            log.info(f"[{i+1}/{len(unique_signals)}] Pre-validated {sig['symbol']} {sig['strategy']} → {outcome['result']}")
        else:
            max_hold = sig.get("max_hold_bars", DEFAULT_MAX_HOLD_BARS)
            log.info(f"[{i+1}/{len(unique_signals)}] Checking {sig['symbol']} {sig['strategy']} {sig['direction']} @ {sig['entry']}")
            outcome = check_signal_outcome(
                symbol=sig["symbol"],
                direction=sig["direction"],
                entry=sig["entry"],
                tp=sig["tp"],
                sl=sig["sl"],
                signal_time_ms=sig["signal_time_ms"],
                max_hold_bars=max_hold,
            )
            n_fetched += 1
            if outcome.get("result") == "NO_DATA":
                n_no_data += 1
            # Rate limiting between API calls
            time.sleep(0.15)

        validated_entry = {**sig, "outcome": outcome}
        # Remove internal fields from output
        validated_entry.pop("signal_time_ms", None)
        validated_entry.pop("_prevalidated_outcome", None)
        validated_entry.pop("_source", None)
        validated.append(validated_entry)

    log.info(f"Validation: {n_prevalidated} pre-validated, {n_fetched} fetched, {n_no_data} NO_DATA")

    # Compute scores
    strategy_scores = compute_strategy_scores(validated)
    symbol_scores = compute_symbol_scores(validated)

    # Summary stats
    wins = sum(1 for v in validated if v["outcome"].get("result") == "WIN")
    losses = sum(1 for v in validated if v["outcome"].get("result") == "LOSS")
    expired = sum(1 for v in validated if v["outcome"].get("result") == "EXPIRED")
    no_data = sum(1 for v in validated if v["outcome"].get("result") == "NO_DATA")
    pending = sum(1 for v in validated if v["outcome"].get("result") == "PENDING")

    decided = wins + losses
    overall_wr = round(wins / decided, 3) if decided > 0 else 0.0

    # Best and worst strategies
    ranked = sorted(strategy_scores.items(), key=lambda x: x[1]["strength_score"], reverse=True)
    best = ranked[0] if ranked else ("none", {})
    worst = ranked[-1] if ranked else ("none", {})

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lookback_days": lookback_days,
        "total_signals": len(validated),
        "summary": {
            "wins": wins,
            "losses": losses,
            "expired": expired,
            "no_data": no_data,
            "pending": pending,
            "overall_win_rate": overall_wr,
            "best_strategy": best[0],
            "best_strategy_score": best[1].get("strength_score", 0) if isinstance(best[1], dict) else 0,
            "worst_strategy": worst[0],
            "worst_strategy_score": worst[1].get("strength_score", 0) if isinstance(worst[1], dict) else 0,
        },
        "strategy_scores": strategy_scores,
        "symbol_scores": symbol_scores,
        "validated_signals": [
            {
                "symbol": v["symbol"],
                "strategy": v["strategy"],
                "strategy_label": v.get("strategy_label", ""),
                "tier": v.get("tier", "unknown"),
                "direction": v["direction"],
                "entry": v["entry"],
                "tp": v["tp"],
                "sl": v["sl"],
                "rr": v.get("rr", 0),
                "trigger": v.get("trigger", ""),
                "signal_time": v.get("signal_time", ""),
                "regime": v.get("regime", ""),
                "outcome": v["outcome"],
            }
            for v in validated
        ],
    }

    if save:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        log.info(f"Saved {len(validated)} validated signals to {OUTPUT_PATH}")
        log.info(f"Overall: {wins}W/{losses}L/{expired}E — WR {overall_wr:.1%}")
        for name, sc in ranked:
            log.info(f"  {name}: {sc['grade']} ({sc['strength_score']}) — {sc['wins']}W/{sc['losses']}L WR={sc['win_rate']:.0%} PF={sc['profit_factor']}")

    return result


def main():
    parser = argparse.ArgumentParser(description="HyroTrader Pick Performance Validator")
    parser.add_argument("--save", action="store_true", help="Save results to JSON")
    parser.add_argument("--lookback-days", type=int, default=30, help="How many days of signal history to check (default 30)")
    args = parser.parse_args()

    result = run(lookback_days=args.lookback_days, save=args.save)

    if not args.save:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
