"""
ALPHA ENGINE - Winner Reverse Engineer v1.0
=============================================
Every hour, finds the TOP WINNING crypto and reverse-engineers what the ideal
entry would have been. Creates training data for ML and reveals what we're missing.

Key insight: Instead of predicting winners, study ACTUAL winners and figure out
what the entry signals looked like BEFORE the pump. Over time this builds a
massive dataset of "what winning entries look like" for ML training.

Output files:
  - data/winner_analysis.json    (latest hourly analysis)
  - data/winner_history.json     (rolling 1-week history, max 168 entries)
  - data/winner_patterns.json    (aggregate pattern stats from 24+ entries)

Usage:
  python winner_reverse_engineer.py              # Run full analysis
  python winner_reverse_engineer.py --patterns   # Only recompute patterns from history
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Shared multi-source failover (Binance mirrors -> CoinGecko -> KuCoin ->
# CryptoCompare). REQUIRED by project rule (CLAUDE.md / feedback_api_failover).
# Uses centralized failover_imports.py to avoid triple duplicate import blocks.
# ---------------------------------------------------------------------------
try:
    from alpha_engine.failover_imports import (
        fetch_tickers_24h as _shared_fetch_tickers_24h,
        fetch_klines as _shared_fetch_klines,
        HAS_SHARED_FAILOVER as _HAS_SHARED_FAILOVER,
    )
except ImportError:
    _HAS_SHARED_FAILOVER = False
    _shared_fetch_tickers_24h = None  # type: ignore[assignment]
    _shared_fetch_klines = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"
ACTIVE_PICKS_PATH = DATA_DIR / "active_picks.json"
WINNER_ANALYSIS_PATH = DATA_DIR / "winner_analysis.json"
WINNER_HISTORY_PATH = DATA_DIR / "winner_history.json"
WINNER_PATTERNS_PATH = DATA_DIR / "winner_patterns.json"

HISTORY_MAX_ENTRIES = 168  # 1 week of hourly snapshots

# ---------------------------------------------------------------------------
# API endpoints (with failover per project rules: 3+ fallback chain)
# ---------------------------------------------------------------------------
BINANCE_FUTURES_TICKER = "https://fapi.binance.com/fapi/v1/ticker/24hr"
BINANCE_FUTURES_KLINES = "https://fapi.binance.com/fapi/v1/klines"
BINANCE_SPOT_TICKER = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_SPOT_KLINES = "https://api.binance.com/api/v3/klines"
BINANCE_MIRROR_TICKER = "https://api1.binance.com/api/v3/ticker/24hr"
BINANCE_MIRROR_KLINES = "https://api1.binance.com/api/v3/klines"

REQUEST_TIMEOUT = 15
TOP_N_WINNERS = 10


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _smart_round(v, precision=6):
    if v == 0:
        return 0.0
    a = abs(v)
    if a >= 1000:
        return round(v, 2)
    elif a >= 1:
        return round(v, 4)
    elif a >= 0.01:
        return round(v, 6)
    return round(v, 8)


# ---------------------------------------------------------------------------
# API helpers with failover
# ---------------------------------------------------------------------------
def _api_get(url, params=None, timeout=REQUEST_TIMEOUT):
    """GET with basic retry."""
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def fetch_all_tickers():
    """Fetch 24h ticker data for all USDT pairs (Binance schema).

    Uses the shared multi-source failover module — Binance mirrors then
    CoinGecko / KuCoin / CryptoCompare per project rule (CLAUDE.md).

    Returns ``(tickers, source_name)``.
    """
    if _HAS_SHARED_FAILOVER:
        tickers, source = _shared_fetch_tickers_24h()
        if tickers:
            return tickers, source

    # Local fallback (kept only for environments where the shared module
    # cannot be imported — should never trigger in production).
    data = _api_get(BINANCE_FUTURES_TICKER)
    if data and isinstance(data, list) and len(data) > 10:
        return data, "futures_local"
    data = _api_get(BINANCE_SPOT_TICKER)
    if data and isinstance(data, list) and len(data) > 10:
        return data, "spot_local"
    data = _api_get(BINANCE_MIRROR_TICKER)
    if data and isinstance(data, list) and len(data) > 10:
        return data, "mirror_local"
    return [], "none"


def fetch_klines(symbol, interval="1h", limit=24, source="futures"):
    """Fetch kline/candlestick data via shared multi-source failover.

    The ``source`` arg is retained for backward-compat but no longer routes
    requests; the shared module always tries the full Binance fapi -> spot
    mirrors -> KuCoin -> CoinGecko -> CryptoCompare chain.
    """
    if _HAS_SHARED_FAILOVER:
        bars = _shared_fetch_klines(symbol, interval, limit)
        if bars:
            return bars

    # Local fallback (best-effort, single-binance only)
    endpoints = []
    if source == "futures":
        endpoints = [BINANCE_FUTURES_KLINES, BINANCE_SPOT_KLINES, BINANCE_MIRROR_KLINES]
    else:
        endpoints = [BINANCE_SPOT_KLINES, BINANCE_MIRROR_KLINES, BINANCE_FUTURES_KLINES]
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    for url in endpoints:
        data = _api_get(url, params=params)
        if data and isinstance(data, list) and len(data) > 0:
            return data
    return []


# ---------------------------------------------------------------------------
# Technical indicator computations (pure Python, no pandas dependency)
# ---------------------------------------------------------------------------
def compute_rsi(closes, period=14):
    """Compute RSI from a list of close prices. Returns latest RSI or None."""
    if len(closes) < period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))

    if len(gains) < period:
        return None

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def compute_bollinger_width(closes, period=20, std_mult=2.0):
    """Compute Bollinger Band width (squeeze indicator). Lower = more squeeze."""
    if len(closes) < period:
        return None
    window = closes[-period:]
    mean = sum(window) / period
    variance = sum((x - mean) ** 2 for x in window) / period
    std = math.sqrt(variance)
    if mean == 0:
        return None
    width = (std_mult * std * 2) / mean
    return round(width, 6)


def compute_volume_ratio(volumes, lookback=6):
    """Ratio of latest volume to average of prior `lookback` candles."""
    if len(volumes) < lookback + 1:
        return None
    recent = volumes[-1]
    avg_prior = sum(volumes[-(lookback + 1):-1]) / lookback
    if avg_prior == 0:
        return None
    return round(recent / avg_prior, 2)


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------
def find_hourly_winners(tickers, source):
    """From ticker data, find top N USDT gainers by 1h price change.

    Returns list of dicts with symbol, change_1h, change_4h, change_24h.
    """
    candidates = []

    for t in tickers:
        symbol = t.get("symbol", "")
        if not symbol.endswith("USDT"):
            continue

        # Skip stablecoins and leveraged tokens
        base = symbol.replace("USDT", "")
        if base in ("USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP", "PYUSD",
                     "GUSD", "FRAX", "USDE", "XUSD", "RLUSD", "BFUSD", "USD1",
                     "U", "STABLE"):
            continue
        # Pattern heuristic: *USDUSDT or *USDTUSDT = stablecoin
        if symbol.endswith("USDUSDT") or symbol.endswith("USDTUSDT"):
            continue
        if any(x in base for x in ("UP", "DOWN", "BULL", "BEAR", "3L", "3S")):
            continue

        # For futures ticker: priceChangePercent is 24h
        # We need to compute 1h change from klines later
        # For now, sort by 24h change as initial filter, then refine
        pct_24h = _safe_float(t.get("priceChangePercent", 0))
        last_price = _safe_float(t.get("lastPrice", 0))
        volume_usd = _safe_float(t.get("quoteVolume", 0))

        # Skip low-volume dust
        if volume_usd < 500_000 or last_price <= 0:
            continue
        # Price heuristic: $0.99-$1.01 = stablecoin peg
        if 0.99 <= last_price <= 1.01:
            continue

        candidates.append({
            "symbol": symbol,
            "last_price": last_price,
            "change_24h": round(pct_24h, 2),
            "volume_usd": volume_usd,
        })

    # Sort by 24h change descending, take top 30 for deeper analysis
    candidates.sort(key=lambda x: x["change_24h"], reverse=True)
    top_candidates = candidates[:30]

    # Now fetch 1h and 4h klines for each to get actual 1h/4h changes
    winners = []
    for c in top_candidates:
        sym = c["symbol"]

        # Fetch 4h klines (last 7 candles = 28h of data)
        klines_4h = fetch_klines(sym, interval="4h", limit=7, source=source)
        # Fetch 1h klines (last 25 candles for analysis)
        klines_1h = fetch_klines(sym, interval="1h", limit=25, source=source)

        change_1h = 0.0
        change_4h = 0.0

        if klines_1h and len(klines_1h) >= 2:
            prev_close = _safe_float(klines_1h[-2][4])
            curr_close = _safe_float(klines_1h[-1][4])
            if prev_close > 0:
                change_1h = round(((curr_close - prev_close) / prev_close) * 100, 2)

        if klines_4h and len(klines_4h) >= 2:
            prev_close_4h = _safe_float(klines_4h[-2][4])
            curr_close_4h = _safe_float(klines_4h[-1][4])
            if prev_close_4h > 0:
                change_4h = round(((curr_close_4h - prev_close_4h) / prev_close_4h) * 100, 2)

        c["change_1h"] = change_1h
        c["change_4h"] = change_4h
        c["klines_1h"] = klines_1h  # keep for reverse engineering
        winners.append(c)

        # Rate limit: be gentle with API
        time.sleep(0.15)

    # Re-sort by 1h change and take top N
    winners.sort(key=lambda x: x["change_1h"], reverse=True)
    return winners[:TOP_N_WINNERS]


def reverse_engineer_entry(winner):
    """For a single winner, reverse-engineer the ideal entry from 1h klines.

    Looks at last 24 1h candles to find:
    - Ideal entry: lowest price in the 6 hours before the pump started
    - Ideal TP: the actual high reached during/after the pump
    - Ideal SL: the MAE (maximum adverse excursion) after ideal entry
    - R:R ratio
    - RSI at ideal entry
    - Volume spike before pump
    - Bollinger squeeze before pump
    """
    klines = winner.get("klines_1h", [])
    if not klines or len(klines) < 10:
        return None

    # Parse klines into structured data
    # Kline format: [open_time, open, high, low, close, volume, close_time, ...]
    candles = []
    for k in klines:
        candles.append({
            "time": int(k[0]),
            "open": _safe_float(k[1]),
            "high": _safe_float(k[2]),
            "low": _safe_float(k[3]),
            "close": _safe_float(k[4]),
            "volume": _safe_float(k[5]),
        })

    if len(candles) < 3:
        return None

    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    volumes = [c["volume"] for c in candles]

    # The pump is the most recent candle(s)
    # Find the pump start: where price started rising significantly
    # Look at last 6-8 candles for the "pre-pump" zone
    current_price = closes[-1]
    current_high = max(highs[-3:]) if len(highs) >= 3 else highs[-1]

    # Ideal entry: lowest low in the 6 candles before the last 2 (pre-pump zone)
    pre_pump_start = max(0, len(candles) - 8)
    pre_pump_end = max(1, len(candles) - 2)
    pre_pump_lows = lows[pre_pump_start:pre_pump_end]

    if not pre_pump_lows:
        return None

    ideal_entry = min(pre_pump_lows)
    ideal_entry_idx = pre_pump_start + pre_pump_lows.index(ideal_entry)

    # Ideal TP: highest high from entry point onward
    post_entry_highs = highs[ideal_entry_idx:]
    ideal_tp = max(post_entry_highs) if post_entry_highs else current_high

    # Ideal SL (MAE): lowest low after entry (how much it dipped before hitting TP)
    post_entry_lows = lows[ideal_entry_idx:]
    ideal_sl = min(post_entry_lows) if post_entry_lows else ideal_entry

    # R:R ratio
    risk = abs(ideal_entry - ideal_sl) if ideal_entry != ideal_sl else ideal_entry * 0.005
    reward = abs(ideal_tp - ideal_entry)
    rr_ratio = round(reward / risk, 2) if risk > 0 else 0.0

    # RSI at ideal entry point
    entry_closes = closes[:ideal_entry_idx + 1]
    rsi_at_entry = compute_rsi(entry_closes) if len(entry_closes) >= 15 else None

    # Volume analysis: was there a spike in the 2 candles before pump?
    vol_ratio = compute_volume_ratio(volumes[:pre_pump_end], lookback=6)
    volume_spike_before = vol_ratio is not None and vol_ratio >= 2.0

    # Bollinger squeeze before pump
    bb_width = compute_bollinger_width(closes[:pre_pump_end])
    bb_squeeze = bb_width is not None and bb_width < 0.04

    # Pump time of day (UTC hour)
    pump_time = candles[-1]["time"]
    pump_hour = datetime.fromtimestamp(pump_time / 1000, tz=timezone.utc).hour

    return {
        "ideal_entry": _smart_round(ideal_entry),
        "ideal_tp": _smart_round(ideal_tp),
        "ideal_sl": _smart_round(ideal_sl),
        "ideal_rr": rr_ratio,
        "ideal_profit_pct": round(((ideal_tp - ideal_entry) / ideal_entry) * 100, 2) if ideal_entry > 0 else 0,
        "rsi_at_entry": rsi_at_entry,
        "volume_spike_before": volume_spike_before,
        "volume_ratio": vol_ratio or 0.0,
        "bb_squeeze_before": bb_squeeze,
        "bb_width": bb_width,
        "pump_hour_utc": pump_hour,
        "candle_count": len(candles),
        "entry_candle_idx": ideal_entry_idx,
    }


# ---------------------------------------------------------------------------
# Compare vs our active picks
# ---------------------------------------------------------------------------
def load_active_picks():
    """Load our active picks from JSON."""
    try:
        if ACTIVE_PICKS_PATH.exists():
            with open(ACTIVE_PICKS_PATH, "r") as f:
                picks = json.load(f)
            return picks if isinstance(picks, list) else []
    except Exception as e:
        print(f"  [WARN] Could not load active picks: {e}")
    return []


def get_our_symbol_universe():
    """Get the set of symbols we track (from active picks + known universe)."""
    picks = load_active_picks()
    symbols = set()
    for p in picks:
        sym = p.get("symbol", "")
        if sym:
            # Normalize: ensure USDT suffix
            if not sym.endswith("USDT"):
                sym = sym.replace("-USD", "USDT").replace("USD", "USDT")
            symbols.add(sym)
    return symbols, picks


def compare_our_picks(winners):
    """Compare our active picks against the hourly winners.

    Returns enriched winner list and summary stats.
    """
    our_symbols, our_picks = get_our_symbol_universe()

    # Build lookup: symbol -> list of our picks
    picks_by_symbol = defaultdict(list)
    for p in our_picks:
        sym = p.get("symbol", "")
        if not sym.endswith("USDT"):
            sym = sym.replace("-USD", "USDT").replace("USD", "USDT")
        picks_by_symbol[sym].append(p)

    overlap_count = 0

    for w in winners:
        sym = w["symbol"]
        in_universe = sym in our_symbols
        our_match = picks_by_symbol.get(sym, [])

        w["our_pick_exists"] = len(our_match) > 0
        w["our_pick_symbol_in_universe"] = in_universe

        if our_match:
            overlap_count += 1
            # Compare our entry vs ideal
            best_pick = our_match[0]
            our_entry = _safe_float(best_pick.get("entry_price", 0))
            our_tp = _safe_float(best_pick.get("take_profit", 0))
            our_sl = _safe_float(best_pick.get("stop_loss", 0))
            ideal_entry = w.get("ideal_entry", 0)
            ideal_tp = w.get("ideal_tp", 0)

            entry_diff_pct = 0.0
            if ideal_entry > 0 and our_entry > 0:
                entry_diff_pct = round(((our_entry - ideal_entry) / ideal_entry) * 100, 2)

            w["our_entry_price"] = our_entry
            w["our_tp"] = our_tp
            w["our_sl"] = our_sl
            w["our_entry_vs_ideal_pct"] = entry_diff_pct
            w["our_strategy"] = best_pick.get("strategy", "unknown")
            w["miss_reason"] = None
        else:
            w["our_entry_price"] = None
            w["our_tp"] = None
            w["our_sl"] = None
            w["our_entry_vs_ideal_pct"] = None
            w["our_strategy"] = None

            if in_universe:
                w["miss_reason"] = "symbol in universe but no strategy fired"
            else:
                w["miss_reason"] = "symbol not in our universe"

    total = len(winners)
    catch_rate = f"{round((overlap_count / total) * 100)}%" if total > 0 else "0%"

    summary = {
        "overlap": overlap_count,
        "total_winners": total,
        "catch_rate": catch_rate,
    }

    return winners, summary


# ---------------------------------------------------------------------------
# Lesson extraction from a single analysis
# ---------------------------------------------------------------------------
def extract_lessons_single(winners):
    """Extract quick lessons from a single hourly run."""
    lessons = []
    if not winners:
        return lessons

    n = len(winners)

    # Volume spike before pump
    vol_spike_count = sum(1 for w in winners if w.get("volume_spike_before"))
    if vol_spike_count > 0:
        lessons.append(f"{vol_spike_count}/{n} winners had volume spike >2x before pump")

    # RSI at entry
    rsi_vals = [w["rsi_at_entry"] for w in winners if w.get("rsi_at_entry") is not None]
    if rsi_vals:
        low_rsi = sum(1 for r in rsi_vals if r < 35)
        avg_rsi = round(sum(rsi_vals) / len(rsi_vals), 1)
        lessons.append(f"{low_rsi}/{len(rsi_vals)} had RSI < 35 at ideal entry (avg RSI: {avg_rsi})")

    # BB squeeze
    squeeze_count = sum(1 for w in winners if w.get("bb_squeeze_before"))
    if squeeze_count > 0:
        lessons.append(f"{squeeze_count}/{n} had Bollinger squeeze before pump")

    # R:R
    rr_vals = [w["ideal_rr"] for w in winners if w.get("ideal_rr", 0) > 0]
    if rr_vals:
        avg_rr = round(sum(rr_vals) / len(rr_vals), 2)
        lessons.append(f"Average ideal R:R ratio: {avg_rr}")

    # Sustained vs noise
    sustained = sum(1 for w in winners if w.get("change_4h", 0) > w.get("change_1h", 0) * 0.5)
    lessons.append(f"{sustained}/{n} winners showed sustained move (4h confirms 1h)")

    return lessons


# ---------------------------------------------------------------------------
# Pattern extraction from history
# ---------------------------------------------------------------------------
def extract_patterns(history):
    """Build aggregate pattern stats from 24+ history entries.

    Analyzes: average RSI at entry, volume ratios, pump times, frequent symbols, R:R.
    """
    if len(history) < 24:
        return {
            "status": "insufficient_data",
            "entries_available": len(history),
            "entries_needed": 24,
            "message": f"Need {24 - len(history)} more hourly scans to extract patterns",
        }

    all_winners = []
    for entry in history:
        for w in entry.get("hourly_winners", []):
            all_winners.append(w)

    if not all_winners:
        return {"status": "no_winners", "message": "No winner data in history"}

    n = len(all_winners)

    # RSI stats
    rsi_vals = [w["rsi_at_entry"] for w in all_winners if w.get("rsi_at_entry") is not None]
    rsi_stats = {}
    if rsi_vals:
        rsi_stats = {
            "avg": round(sum(rsi_vals) / len(rsi_vals), 1),
            "median": round(sorted(rsi_vals)[len(rsi_vals) // 2], 1),
            "pct_below_30": round(sum(1 for r in rsi_vals if r < 30) / len(rsi_vals) * 100, 1),
            "pct_below_40": round(sum(1 for r in rsi_vals if r < 40) / len(rsi_vals) * 100, 1),
            "sample_size": len(rsi_vals),
        }

    # Volume ratio stats
    vol_vals = [w["volume_ratio"] for w in all_winners if w.get("volume_ratio", 0) > 0]
    vol_stats = {}
    if vol_vals:
        vol_stats = {
            "avg": round(sum(vol_vals) / len(vol_vals), 2),
            "pct_above_2x": round(sum(1 for v in vol_vals if v >= 2.0) / len(vol_vals) * 100, 1),
            "pct_above_3x": round(sum(1 for v in vol_vals if v >= 3.0) / len(vol_vals) * 100, 1),
            "sample_size": len(vol_vals),
        }

    # Pump hour distribution
    pump_hours = [w["pump_hour_utc"] for w in all_winners if "pump_hour_utc" in w]
    hour_counts = Counter(pump_hours)
    top_hours = hour_counts.most_common(5)

    # Most frequent winning symbols
    sym_counts = Counter(w["symbol"] for w in all_winners)
    top_symbols = sym_counts.most_common(15)

    # R:R stats
    rr_vals = [w["ideal_rr"] for w in all_winners if w.get("ideal_rr", 0) > 0]
    rr_stats = {}
    if rr_vals:
        rr_stats = {
            "avg": round(sum(rr_vals) / len(rr_vals), 2),
            "median": round(sorted(rr_vals)[len(rr_vals) // 2], 2),
            "pct_above_3": round(sum(1 for r in rr_vals if r >= 3) / len(rr_vals) * 100, 1),
            "sample_size": len(rr_vals),
        }

    # Catch rate over time
    catch_rates = []
    for entry in history:
        picks_vs = entry.get("our_picks_vs_winners", {})
        if picks_vs.get("total_winners", 0) > 0:
            rate = picks_vs["overlap"] / picks_vs["total_winners"]
            catch_rates.append(rate)

    catch_stats = {}
    if catch_rates:
        catch_stats = {
            "avg_catch_rate_pct": round(sum(catch_rates) / len(catch_rates) * 100, 1),
            "best_catch_rate_pct": round(max(catch_rates) * 100, 1),
            "worst_catch_rate_pct": round(min(catch_rates) * 100, 1),
        }

    # 1h change stats of winners
    change_vals = [w["change_1h"] for w in all_winners if "change_1h" in w]
    change_stats = {}
    if change_vals:
        change_stats = {
            "avg_1h_change": round(sum(change_vals) / len(change_vals), 2),
            "median_1h_change": round(sorted(change_vals)[len(change_vals) // 2], 2),
            "max_1h_change": round(max(change_vals), 2),
        }

    # BB squeeze prevalence
    squeeze_count = sum(1 for w in all_winners if w.get("bb_squeeze_before"))
    squeeze_pct = round(squeeze_count / n * 100, 1) if n > 0 else 0

    patterns = {
        "status": "active",
        "last_updated": _now_iso(),
        "total_winner_samples": n,
        "history_entries": len(history),
        "rsi_at_ideal_entry": rsi_stats,
        "volume_before_pump": vol_stats,
        "ideal_risk_reward": rr_stats,
        "pump_time_distribution_utc": {str(h): c for h, c in top_hours},
        "most_frequent_winners": {s: c for s, c in top_symbols},
        "bb_squeeze_prevalence_pct": squeeze_pct,
        "winner_change_stats": change_stats,
        "our_catch_rate": catch_stats,
        "ml_training_insights": {
            "recommended_rsi_entry_zone": f"<{rsi_stats.get('avg', 40):.0f}" if rsi_stats else "<40",
            "recommended_vol_threshold": f">{vol_stats.get('avg', 2.0):.1f}x" if vol_stats else ">2.0x",
            "most_active_hours_utc": [h for h, _ in top_hours[:3]] if top_hours else [],
            "top_recurring_symbols": [s for s, _ in top_symbols[:10]] if top_symbols else [],
        },
    }

    return patterns


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------
def _safe_write_json(path, data):
    """Atomic-ish JSON write."""
    tmp_path = str(path) + ".tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        # Rename into place
        if os.path.exists(str(path)):
            os.replace(tmp_path, str(path))
        else:
            os.rename(tmp_path, str(path))
    except Exception as e:
        print(f"  [ERROR] Failed to write {path}: {e}")
        # Clean up temp file
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def load_history():
    """Load winner history from disk."""
    try:
        if WINNER_HISTORY_PATH.exists():
            with open(WINNER_HISTORY_PATH, "r") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"  [WARN] Could not load history: {e}")
    return []


def append_to_history(analysis):
    """Append analysis to rolling history, capped at HISTORY_MAX_ENTRIES."""
    history = load_history()
    history.append(analysis)

    # Keep only the most recent entries
    if len(history) > HISTORY_MAX_ENTRIES:
        history = history[-HISTORY_MAX_ENTRIES:]

    _safe_write_json(WINNER_HISTORY_PATH, history)
    return history


# ---------------------------------------------------------------------------
# Main analysis pipeline
# ---------------------------------------------------------------------------
def analyze_hourly_winners():
    """Run the full hourly winner analysis pipeline.

    1. Fetch top crypto gainers
    2. Reverse-engineer ideal entries
    3. Compare vs our picks
    4. Save analysis + append history
    5. Extract patterns if enough data

    Returns the analysis dict.
    """
    timestamp = _now_iso()
    print(f"\n{'='*60}")
    print(f"  WINNER REVERSE ENGINEER - {timestamp}")
    print(f"{'='*60}")

    # Step 1: Fetch tickers
    print("\n[1/6] Fetching all USDT tickers...")
    tickers, source = fetch_all_tickers()
    if not tickers:
        print("  [ERROR] Could not fetch tickers from any API endpoint")
        return None
    print(f"  Got {len(tickers)} tickers from {source} API")

    # Step 2: Find hourly winners
    print("\n[2/6] Finding top {TOP_N_WINNERS} hourly winners...")
    winners = find_hourly_winners(tickers, source)
    if not winners:
        print("  [WARN] No winners found")
        return None
    print(f"  Top winners:")
    for i, w in enumerate(winners, 1):
        print(f"    {i}. {w['symbol']:12s} | 1h: {w['change_1h']:+.2f}% | 4h: {w['change_4h']:+.2f}% | 24h: {w['change_24h']:+.2f}%")

    # Step 3: Reverse-engineer entries
    print(f"\n[3/6] Reverse-engineering ideal entries...")
    for w in winners:
        entry_data = reverse_engineer_entry(w)
        if entry_data:
            w.update(entry_data)
        else:
            w["ideal_entry"] = None
            w["ideal_tp"] = None
            w["ideal_sl"] = None
            w["ideal_rr"] = 0
            w["rsi_at_entry"] = None
            w["volume_spike_before"] = False
            w["volume_ratio"] = 0
            w["bb_squeeze_before"] = False

        # Remove raw klines from output
        w.pop("klines_1h", None)
        w.pop("volume_usd", None)
        w.pop("last_price", None)

    for w in winners:
        if w.get("ideal_entry"):
            rsi_str = f"RSI:{w['rsi_at_entry']}" if w.get("rsi_at_entry") else "RSI:N/A"
            print(f"    {w['symbol']:12s} | entry:{w['ideal_entry']} -> TP:{w['ideal_tp']} | R:R:{w['ideal_rr']} | {rsi_str} | vol:{w['volume_ratio']}x")

    # Step 4: Compare vs our picks
    print(f"\n[4/6] Comparing vs our active picks...")
    winners, pick_summary = compare_our_picks(winners)
    print(f"  Overlap: {pick_summary['overlap']}/{pick_summary['total_winners']} ({pick_summary['catch_rate']})")

    for w in winners:
        if w.get("our_pick_exists"):
            diff = w.get("our_entry_vs_ideal_pct", 0)
            print(f"    HIT  {w['symbol']:12s} | our entry {diff:+.1f}% from ideal | strategy: {w.get('our_strategy', '?')}")
        else:
            print(f"    MISS {w['symbol']:12s} | reason: {w.get('miss_reason', 'unknown')}")

    # Step 5: Extract lessons
    print(f"\n[5/6] Extracting lessons...")
    lessons = extract_lessons_single(winners)
    for lesson in lessons:
        print(f"    - {lesson}")

    # Build analysis object
    analysis = {
        "timestamp": timestamp,
        "source_api": source,
        "hourly_winners": winners,
        "our_picks_vs_winners": pick_summary,
        "lessons": lessons,
    }

    # Save latest analysis
    _safe_write_json(WINNER_ANALYSIS_PATH, analysis)
    print(f"\n  Saved analysis to {WINNER_ANALYSIS_PATH}")

    # Append to history
    history = append_to_history(analysis)
    print(f"  History now has {len(history)} entries (max {HISTORY_MAX_ENTRIES})")

    # Step 6: Extract patterns if enough data
    print(f"\n[6/6] Extracting aggregate patterns...")
    patterns = extract_patterns(history)
    _safe_write_json(WINNER_PATTERNS_PATH, patterns)

    if patterns.get("status") == "active":
        print(f"  Patterns updated ({patterns['total_winner_samples']} winner samples)")
        rsi_info = patterns.get("rsi_at_ideal_entry", {})
        vol_info = patterns.get("volume_before_pump", {})
        rr_info = patterns.get("ideal_risk_reward", {})
        if rsi_info:
            print(f"    Avg RSI at ideal entry: {rsi_info.get('avg', 'N/A')}")
        if vol_info:
            print(f"    Avg volume ratio before pump: {vol_info.get('avg', 'N/A')}x")
        if rr_info:
            print(f"    Avg ideal R:R: {rr_info.get('avg', 'N/A')}")
        catch_info = patterns.get("our_catch_rate", {})
        if catch_info:
            print(f"    Our catch rate: {catch_info.get('avg_catch_rate_pct', 'N/A')}%")
    else:
        print(f"  {patterns.get('message', 'Waiting for more data...')}")

    print(f"\n{'='*60}")
    print(f"  ANALYSIS COMPLETE")
    print(f"{'='*60}\n")

    return analysis


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Winner Reverse Engineer - Study hourly crypto winners to build ML training data"
    )
    parser.add_argument(
        "--patterns", action="store_true",
        help="Only recompute patterns from existing history (no API calls)"
    )
    parser.add_argument(
        "--history-stats", action="store_true",
        help="Print summary stats from history"
    )

    args = parser.parse_args()

    if args.patterns:
        print("Recomputing patterns from history...")
        history = load_history()
        if not history:
            print("No history found. Run a full analysis first.")
            sys.exit(1)
        patterns = extract_patterns(history)
        _safe_write_json(WINNER_PATTERNS_PATH, patterns)
        print(json.dumps(patterns, indent=2, default=str))
        return

    if args.history_stats:
        history = load_history()
        if not history:
            print("No history found.")
            sys.exit(1)
        print(f"History entries: {len(history)}")
        print(f"First entry: {history[0].get('timestamp', 'N/A')}")
        print(f"Last entry: {history[-1].get('timestamp', 'N/A')}")
        total_winners = sum(len(e.get("hourly_winners", [])) for e in history)
        print(f"Total winner samples: {total_winners}")
        return

    # Full analysis
    try:
        result = analyze_hourly_winners()
        if result is None:
            print("[ERROR] Analysis failed - no data returned")
            sys.exit(1)
    except Exception as e:
        print(f"[FATAL] {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
