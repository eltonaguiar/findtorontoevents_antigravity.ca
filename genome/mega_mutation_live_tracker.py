#!/usr/bin/env python3
"""
MEGA MUTATION LIVE TRACKER
===========================
Two modes:
  1. GENERATE: Run the tournament's winning DNA mutations against live Binance
     data and output paper-trade picks with exact TP/SL levels.
  2. CHECK: Fetch current prices and resolve open picks (TP hit / SL hit / still open).

All picks tagged as "Mega Mutation" with the exact mutation name + symbol documented.

Usage:
    python genome/mega_mutation_live_tracker.py generate   # Generate new picks
    python genome/mega_mutation_live_tracker.py check      # Check open picks
    python genome/mega_mutation_live_tracker.py report     # Print summary

Output:
    genome/data/mega_mutation_picks.json  — All picks (open + closed)
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
import random
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PICKS_FILE = DATA_DIR / "mega_mutation_picks.json"
RESULTS_FILE = DATA_DIR / "mega_mutation_results.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [MegaMutation] %(message)s")
logger = logging.getLogger("MegaMutationTracker")

# ============================================================================
# WINNING MUTATIONS from tournament (top combos with clean overfit status)
# These are the exact mutations + symbols that won the tournament
# ============================================================================
WINNING_COMBOS = [
    {
        "mutation_name": "ema_momentum_m006",
        "symbol": "AVAXUSDT",
        "primary": "EMA_CROSS",
        "genes": {
            "primary": "EMA_CROSS",
            "ema_fast": 9, "ema_slow": 21,
            "rsi_period": 14, "rsi_filter_low": 40, "rsi_filter_high": 60,
            "tp_atr": 1.1429, "sl_atr": 1.2,
            "direction_bias": "both",
        },
        "tournament_sharpe": 5.77,
        "tournament_wr": 0.875,
        "tournament_pf": 4.66,
        "overfit": "clean",
    },
    {
        "mutation_name": "macd_rsi_m048",
        "symbol": "JUPUSDT",
        "primary": "MACD_RSI",
        "genes": {
            "primary": "MACD_RSI",
            "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
            "rsi_period": 14, "rsi_buy": 35, "rsi_sell": 65,
            "tp_atr": 2.2, "sl_atr": 1.2,
            "direction_bias": "both",
        },
        "tournament_sharpe": 7.52,
        "tournament_wr": 0.857,
        "tournament_pf": 6.44,
        "overfit": "clean",
    },
    {
        "mutation_name": "macd_rsi_m084",
        "symbol": "ENAUSDT",
        "primary": "MACD_RSI",
        "genes": {
            "primary": "MACD_RSI",
            "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
            "rsi_period": 14, "rsi_buy": 35, "rsi_sell": 65,
            "tp_atr": 2.2, "sl_atr": 1.4527,
            "direction_bias": "both",
        },
        "tournament_sharpe": 8.38,
        "tournament_wr": 0.833,
        "tournament_pf": 8.28,
        "overfit": "clean",
    },
    {
        "mutation_name": "ema_momentum_m006",
        "symbol": "DOTUSDT",
        "primary": "EMA_CROSS",
        "genes": {
            "primary": "EMA_CROSS",
            "ema_fast": 9, "ema_slow": 21,
            "rsi_period": 14, "rsi_filter_low": 40, "rsi_filter_high": 60,
            "tp_atr": 1.1429, "sl_atr": 1.2,
            "direction_bias": "both",
        },
        "tournament_sharpe": 4.79,
        "tournament_wr": 0.857,
        "tournament_pf": 3.75,
        "overfit": "clean",
    },
    {
        "mutation_name": "macd_rsi_m017",
        "symbol": "ADAUSDT",
        "primary": "MACD_RSI",
        "genes": {
            "primary": "MACD_RSI",
            "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
            "rsi_period": 14, "rsi_buy": 35, "rsi_sell": 65,
            "tp_atr": 2.2, "sl_atr": 1.2,
            "direction_bias": "both",
        },
        "tournament_sharpe": 4.94,
        "tournament_wr": 0.778,
        "tournament_pf": 3.72,
        "overfit": "clean",
    },
    # Additional predictable symbols with MACD_RSI (top family)
    {
        "mutation_name": "macd_rsi_m048",
        "symbol": "WIFUSDT",
        "primary": "MACD_RSI",
        "genes": {
            "primary": "MACD_RSI",
            "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
            "rsi_period": 14, "rsi_buy": 35, "rsi_sell": 65,
            "tp_atr": 2.2, "sl_atr": 1.2,
            "direction_bias": "both",
        },
        "tournament_sharpe": 5.0,
        "tournament_wr": 0.80,
        "tournament_pf": 4.0,
        "overfit": "clean",
    },
    {
        "mutation_name": "macd_rsi_m048",
        "symbol": "STXUSDT",
        "primary": "MACD_RSI",
        "genes": {
            "primary": "MACD_RSI",
            "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
            "rsi_period": 14, "rsi_buy": 35, "rsi_sell": 65,
            "tp_atr": 2.2, "sl_atr": 1.2,
            "direction_bias": "both",
        },
        "tournament_sharpe": 6.13,
        "tournament_wr": 0.833,
        "tournament_pf": 4.88,
        "overfit": "clean",
    },
    {
        "mutation_name": "macd_rsi_m048",
        "symbol": "RENDERUSDT",
        "primary": "MACD_RSI",
        "genes": {
            "primary": "MACD_RSI",
            "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
            "rsi_period": 14, "rsi_buy": 35, "rsi_sell": 65,
            "tp_atr": 2.2, "sl_atr": 1.2,
            "direction_bias": "both",
        },
        "tournament_sharpe": 5.10,
        "tournament_wr": 0.875,
        "tournament_pf": 4.08,
        "overfit": "clean",
    },
]

# ============================================================================
# Technical indicators (same as tournament)
# ============================================================================
def _ema(data, period):
    out = np.empty_like(data, dtype=float)
    out[0] = data[0]
    mult = 2.0 / (period + 1)
    for i in range(1, len(data)):
        out[i] = data[i] * mult + out[i - 1] * (1 - mult)
    return out

def _rsi(closes, period):
    deltas = np.diff(closes, prepend=closes[0])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.zeros_like(closes)
    avg_loss = np.zeros_like(closes)
    if len(gains) < period + 1:
        return np.full_like(closes, 50.0)
    avg_gain[period] = np.mean(gains[1:period + 1])
    avg_loss[period] = np.mean(losses[1:period + 1])
    for i in range(period + 1, len(closes)):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i]) / period
    rs = np.divide(avg_gain, avg_loss, out=np.full_like(avg_gain, 100.0, dtype=float), where=avg_loss > 0)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi[:period] = 50.0
    return rsi

def _atr(highs, lows, closes, period=14):
    tr = np.zeros(len(closes))
    tr[0] = highs[0] - lows[0]
    for i in range(1, len(closes)):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
    atr = np.zeros_like(closes)
    if len(tr) < period:
        return atr
    atr[period - 1] = np.mean(tr[:period])
    for i in range(period, len(closes)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr

def _macd(closes, fast, slow, signal):
    ema_f = _ema(closes, fast)
    ema_s = _ema(closes, slow)
    macd_line = ema_f - ema_s
    sig_line = _ema(macd_line, signal)
    hist = macd_line - sig_line
    return macd_line, sig_line, hist


# ============================================================================
# Binance API helpers
# ============================================================================
def _klines_from_raw(raw: list) -> Optional[dict]:
    """Convert raw Binance-style kline list to OHLCV dict."""
    if not raw:
        return None
    return {
        "open": np.array([float(k[1]) for k in raw]),
        "high": np.array([float(k[2]) for k in raw]),
        "low": np.array([float(k[3]) for k in raw]),
        "close": np.array([float(k[4]) for k in raw]),
        "volume": np.array([float(k[5]) for k in raw]),
        "timestamp": [int(k[0]) for k in raw],
    }


def fetch_klines(symbol: str, interval: str = "4h", limit: int = 100) -> Optional[dict]:
    """Fetch OHLCV with multi-source failover: Binance mirrors → Bybit → KuCoin."""
    # 1. Binance mirror failover (using shared helper)
    try:
        from shared.binance_api import binance_get
        data = binance_get(
            "/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": str(limit)},
        )
        if data and isinstance(data, list):
            return _klines_from_raw(data)
    except ImportError:
        pass

    # 2. Bybit v5 fallback (no geo-block, public)
    _BYBIT_INTERVAL_MAP = {"1h": "60", "4h": "240", "1d": "D", "5m": "5", "15m": "15"}
    bybit_interval = _BYBIT_INTERVAL_MAP.get(interval, "240")
    try:
        import urllib.request
        url = f"https://api.bybit.com/v5/market/kline?category=spot&symbol={symbol.upper()}&interval={bybit_interval}&limit={min(limit, 200)}"
        req = urllib.request.Request(url, headers={"User-Agent": "MegaMutation/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if payload.get("retCode") == 0 and payload["result"]["list"]:
            rows = []
            for item in payload["result"]["list"]:
                rows.append([int(item[0]), item[1], item[2], item[3], item[4], item[5]])
            return _klines_from_raw(rows)
    except Exception:
        pass

    # 3. KuCoin fallback
    _KC_INTERVAL_MAP = {"1h": "1hour", "4h": "4hour", "1d": "1day"}
    kc_interval = _KC_INTERVAL_MAP.get(interval, "4hour")
    base_sym = symbol.upper().replace("USDT", "-USDT")
    if "-" not in base_sym:
        base_sym = f"{base_sym}-USDT"
    try:
        import urllib.request
        import time as _time_mod
        end_at = int(_time_mod.time())
        start_at = end_at - (limit * 3600 * (4 if interval == "4h" else 24 if interval == "1d" else 1))
        url = f"https://api.kucoin.com/api/v1/market/candles?type={kc_interval}&symbol={base_sym}&startAt={start_at}&endAt={end_at}"
        req = urllib.request.Request(url, headers={"User-Agent": "MegaMutation/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if payload.get("code") == "200000" and payload.get("data"):
            rows = []
            for item in payload["data"]:
                # KuCoin: [time, open, close, high, low, volume, turnover]
                rows.append([int(item[0]) * 1000, item[1], item[3], item[4], item[2], item[5]])
            return _klines_from_raw(rows)
    except Exception:
        pass

    return None


def fetch_current_price(symbol: str) -> Optional[float]:
    """Get current price with multi-source failover: Binance → Bybit → KuCoin."""
    # 1. Binance mirror failover (using shared helper)
    try:
        from shared.binance_api import binance_get
        data = binance_get(
            "/api/v3/ticker/price",
            params={"symbol": symbol},
        )
        if data and isinstance(data, dict) and "price" in data:
            return float(data["price"])
    except ImportError:
        pass

    # 2. Bybit v5 fallback
    try:
        import urllib.request
        url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol.upper()}"
        req = urllib.request.Request(url, headers={"User-Agent": "MegaMutation/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if payload.get("retCode") == 0 and payload["result"]["list"]:
            return float(payload["result"]["list"][0]["lastPrice"])
    except Exception:
        pass

    # 3. KuCoin fallback
    try:
        import urllib.request
        base_sym = symbol.upper().replace("USDT", "-USDT")
        if "-" not in base_sym:
            base_sym = f"{base_sym}-USDT"
        url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={base_sym}"
        req = urllib.request.Request(url, headers={"User-Agent": "MegaMutation/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if payload.get("code") == "200000" and payload.get("data"):
            return float(payload["data"]["price"])
    except Exception:
        pass

    return None


# ============================================================================
# Signal generation for live picks
# ============================================================================
def check_signal(data: dict, genes: dict) -> Optional[dict]:
    """Check if the latest bar triggers a signal. Returns signal dict or None."""
    closes = data["close"]
    highs = data["high"]
    lows = data["low"]
    n = len(closes)
    if n < 60:
        return None

    primary = genes.get("primary", "MACD_RSI")
    rsi_p = genes.get("rsi_period", 14)
    rsi_vals = _rsi(closes, rsi_p)
    atr_vals = _atr(highs, lows, closes, 14)

    current_atr = atr_vals[-1]
    current_price = closes[-1]
    current_rsi = rsi_vals[-1]

    if current_atr <= 0:
        return None

    signal = None
    reason = ""

    if primary == "EMA_CROSS":
        ef = _ema(closes, genes.get("ema_fast", 9))
        es = _ema(closes, genes.get("ema_slow", 21))
        rsi_lo = genes.get("rsi_filter_low", 40)
        rsi_hi = genes.get("rsi_filter_high", 60)

        # Cross happened on latest bar
        if ef[-1] > es[-1] and ef[-2] <= es[-2] and rsi_vals[-1] > rsi_lo:
            signal = "LONG"
            reason = f"EMA {genes.get('ema_fast')}/{genes.get('ema_slow')} bullish cross, RSI={current_rsi:.1f}"
        elif ef[-1] < es[-1] and ef[-2] >= es[-2] and rsi_vals[-1] < rsi_hi:
            signal = "SHORT"
            reason = f"EMA {genes.get('ema_fast')}/{genes.get('ema_slow')} bearish cross, RSI={current_rsi:.1f}"

    elif primary == "MACD_RSI":
        macd_l, macd_s, macd_h = _macd(closes,
                                         genes.get("macd_fast", 12),
                                         genes.get("macd_slow", 26),
                                         genes.get("macd_signal", 9))
        buy_rsi = genes.get("rsi_buy", 35)
        sell_rsi = genes.get("rsi_sell", 65)

        if macd_h[-1] > 0 and macd_h[-2] <= 0 and rsi_vals[-1] < buy_rsi + 20:
            signal = "LONG"
            reason = f"MACD histogram crossed positive, RSI={current_rsi:.1f} (< {buy_rsi + 20})"
        elif macd_h[-1] < 0 and macd_h[-2] >= 0 and rsi_vals[-1] > sell_rsi - 20:
            signal = "SHORT"
            reason = f"MACD histogram crossed negative, RSI={current_rsi:.1f} (> {sell_rsi - 20})"

    if signal is None:
        return None

    # Apply direction bias
    bias = genes.get("direction_bias", "both")
    if bias == "long" and signal == "SHORT":
        return None
    if bias == "short" and signal == "LONG":
        return None

    # Calculate TP/SL
    tp_mult = genes.get("tp_atr", 2.0)
    sl_mult = genes.get("sl_atr", 1.0)

    if signal == "LONG":
        tp_price = current_price + tp_mult * current_atr
        sl_price = current_price - sl_mult * current_atr
    else:
        tp_price = current_price - tp_mult * current_atr
        sl_price = current_price + sl_mult * current_atr

    tp_pct = abs(tp_price - current_price) / current_price * 100
    sl_pct = abs(sl_price - current_price) / current_price * 100
    rr_ratio = tp_pct / sl_pct if sl_pct > 0 else 0

    return {
        "signal": signal,
        "entry_price": round(current_price, 6),
        "tp_price": round(tp_price, 6),
        "sl_price": round(sl_price, 6),
        "tp_pct": round(tp_pct, 2),
        "sl_pct": round(sl_pct, 2),
        "rr_ratio": round(rr_ratio, 2),
        "atr": round(current_atr, 6),
        "rsi": round(current_rsi, 1),
        "reason": reason,
    }


# ============================================================================
# Pick management
# ============================================================================
def load_picks() -> dict:
    """Load existing picks from file."""
    if PICKS_FILE.exists():
        with open(str(PICKS_FILE)) as f:
            return json.load(f)
    return {"open_picks": [], "closed_picks": [], "stats": {}, "updated_at": None}


def save_picks(picks: dict):
    """Save picks to file."""
    picks["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(str(PICKS_FILE), "w") as f:
        json.dump(picks, f, indent=2, default=str)
    # Also export in standard active/closed format for MySQL sync + audit page
    export_standard_format(picks)


def export_standard_format(picks: dict):
    """
    Export picks as genome/data/active_picks.json and genome/data/closed_picks.json.
    These files are picked up by sync_all_picks_to_mysql.py (source: mega_mutation)
    and synced to ejaguiar1_stocks.at_raw_picks → visible on findtorontoevents.ca/audit.
    """
    # active_picks.json — standard format for MySQL sync
    active = []
    for p in picks.get("open_picks", []):
        active.append({
            "symbol": p["symbol"],
            "direction": p["signal"],
            "signal_type": p["signal"],
            "entry_price": p["entry_price"],
            "take_profit": p["tp_price"],
            "stop_loss": p["sl_price"],
            "confidence": p.get("tournament_wr", 0.8),
            "strategy": f"mega_mutation_{p['mutation_name']}",
            "strategy_name": f"Mega Mutation: {p['mutation_name']}",
            "algorithm": f"mega_mutation_{p['primary_strategy']}",
            "timestamp": p["opened_at"],
            "generated_at": p["opened_at"],
            "tag": "Mega Mutation",
            "status": "OPEN",
            "asset_class": "CRYPTO",
            "category": "crypto",
            "source_system": "mega_mutation",
            "mutation_name": p["mutation_name"],
            "primary_strategy": p["primary_strategy"],
            "tournament_sharpe": p.get("tournament_sharpe"),
            "tournament_wr": p.get("tournament_wr"),
            "tournament_pf": p.get("tournament_pf"),
            "rsi_at_entry": p.get("entry_rsi"),
            "atr_at_entry": p.get("entry_atr"),
            "reason": p.get("reason", ""),
        })

    try:
        from alpha_engine.feed_hygiene import sanitize_active_picks
    except ImportError:
        sanitize_active_picks = lambda picks, label="": picks
    active = sanitize_active_picks(active, "genome_mega_mutation")

    active_path = DATA_DIR / "active_picks.json"
    with open(str(active_path), "w") as f:
        json.dump(active, f, indent=2, default=str)

    # closed_picks.json — standard format for MySQL sync
    closed = []
    for p in picks.get("closed_picks", []):
        closed.append({
            "symbol": p["symbol"],
            "direction": p["signal"],
            "signal_type": p["signal"],
            "entry_price": p["entry_price"],
            "exit_price": p.get("exit_price", p["entry_price"]),
            "take_profit": p["tp_price"],
            "stop_loss": p["sl_price"],
            "confidence": p.get("tournament_wr", 0.8),
            "strategy": f"mega_mutation_{p['mutation_name']}",
            "strategy_name": f"Mega Mutation: {p['mutation_name']}",
            "algorithm": f"mega_mutation_{p['primary_strategy']}",
            "timestamp": p["opened_at"],
            "generated_at": p["opened_at"],
            "closed_at": p.get("closed_at", ""),
            "tag": "Mega Mutation",
            "status": p.get("status", "CLOSED"),
            "exit_reason": p.get("exit_reason", ""),
            "pnl_pct": float(p.get("pnl_pct", 0) or 0),
            "realized_pnl_pct": float(p.get("pnl_pct", 0) or 0),
            "pnl_usd": p.get("pnl_usd", 0),
            "asset_class": "CRYPTO",
            "category": "crypto",
            "source_system": "mega_mutation",
            "mutation_name": p["mutation_name"],
            "primary_strategy": p["primary_strategy"],
            "tournament_sharpe": p.get("tournament_sharpe"),
            "tournament_wr": p.get("tournament_wr"),
            "tournament_pf": p.get("tournament_pf"),
            "reason": p.get("reason", ""),
        })

    closed_path = DATA_DIR / "closed_picks.json"
    with open(str(closed_path), "w") as f:
        json.dump(closed, f, indent=2, default=str)

    logger.info(f"  📤 Exported {len(active)} active + {len(closed)} closed picks "
                f"to standard format (for MySQL sync → audit page)")


def generate_picks():
    """Generate new picks from winning combos against live data."""
    logger.info("=" * 60)
    logger.info("  MEGA MUTATION LIVE PICK GENERATOR")
    logger.info("=" * 60)

    picks = load_picks()
    # Track which combos already have open picks to avoid duplicates
    open_keys = {(p["symbol"], p["mutation_name"]) for p in picks["open_picks"]}

    new_picks = 0
    scanned = 0

    for combo in WINNING_COMBOS:
        symbol = combo["symbol"]
        mut_name = combo["mutation_name"]

        # Skip if already has open pick for this combo
        if (symbol, mut_name) in open_keys:
            logger.info(f"  ⏭ {symbol} / {mut_name} — already has open pick")
            continue

        scanned += 1
        data = fetch_klines(symbol, "4h", 100)
        if data is None or len(data["close"]) < 60:
            logger.warning(f"  ✗ {symbol}: No data")
            continue

        sig = check_signal(data, combo["genes"])
        if sig is None:
            logger.info(f"  · {symbol} / {mut_name}: No signal right now")
            continue

        # Create pick
        pick = {
            "id": hashlib.md5(f"{symbol}_{mut_name}_{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:12],
            "symbol": symbol,
            "mutation_name": mut_name,
            "primary_strategy": combo["primary"],
            "tag": "Mega Mutation",
            "signal": sig["signal"],
            "entry_price": sig["entry_price"],
            "tp_price": sig["tp_price"],
            "sl_price": sig["sl_price"],
            "tp_pct": sig["tp_pct"],
            "sl_pct": sig["sl_pct"],
            "rr_ratio": sig["rr_ratio"],
            "entry_atr": sig["atr"],
            "entry_rsi": sig["rsi"],
            "reason": sig["reason"],
            "tournament_sharpe": combo["tournament_sharpe"],
            "tournament_wr": combo["tournament_wr"],
            "tournament_pf": combo["tournament_pf"],
            "overfit_status": combo["overfit"],
            "genes": combo["genes"],
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "status": "OPEN",
            "max_hold_hours": 120,  # 5 days max
            "paper_position_size_usd": 100,
        }

        picks["open_picks"].append(pick)
        new_picks += 1
        logger.info(f"  🎯 NEW PICK: {sig['signal']} {symbol} @ {sig['entry_price']}")
        logger.info(f"     TP: {sig['tp_price']} (+{sig['tp_pct']}%) | SL: {sig['sl_price']} (-{sig['sl_pct']}%)")
        logger.info(f"     R:R = {sig['rr_ratio']} | Strategy: {mut_name} ({combo['primary']})")
        logger.info(f"     Tournament: Sharpe={combo['tournament_sharpe']}, WR={combo['tournament_wr']*100:.1f}%")

    save_picks(picks)
    logger.info(f"\n  Scanned: {scanned} combos | New picks: {new_picks}")
    logger.info(f"  Total open: {len(picks['open_picks'])} | Total closed: {len(picks['closed_picks'])}")
    return new_picks


def check_picks():
    """Check all open picks against current prices. Resolve TP/SL hits."""
    logger.info("=" * 60)
    logger.info("  MEGA MUTATION HOURLY CHECK")
    logger.info("=" * 60)

    picks = load_picks()
    if not picks["open_picks"]:
        logger.info("  No open picks to check")
        return

    resolved = 0
    still_open = 0
    now = datetime.now(timezone.utc)

    for pick in list(picks["open_picks"]):
        symbol = pick["symbol"]
        current_price = fetch_current_price(symbol)

        if current_price is None:
            logger.warning(f"  ✗ {symbol}: Can't fetch price")
            still_open += 1
            continue

        entry = pick["entry_price"]
        tp = pick["tp_price"]
        sl = pick["sl_price"]
        signal = pick["signal"]
        opened = datetime.fromisoformat(pick["opened_at"])
        hours_held = (now - opened).total_seconds() / 3600

        # Check expiry
        max_hold = pick.get("max_hold_hours", 120)
        expired = hours_held >= max_hold

        # Check TP/SL
        hit_tp = False
        hit_sl = False

        if signal == "LONG":
            hit_tp = current_price >= tp
            hit_sl = current_price <= sl
        else:  # SHORT
            hit_tp = current_price <= tp
            hit_sl = current_price >= sl

        if hit_tp or hit_sl or expired:
            # Resolve pick
            if hit_tp:
                exit_reason = "TP_HIT"
                exit_price = tp
            elif hit_sl:
                exit_reason = "SL_HIT"
                exit_price = sl
            else:
                exit_reason = "EXPIRED"
                exit_price = current_price

            if signal == "LONG":
                pnl_pct = (exit_price - entry) / entry * 100
            else:
                pnl_pct = (entry - exit_price) / entry * 100

            pnl_pct -= 0.2  # 0.2% commission round-trip
            position_size = pick.get("paper_position_size_usd", 100)
            pnl_usd = position_size * pnl_pct / 100

            pick["status"] = "WON" if pnl_pct > 0 else "LOST"
            pick["exit_price"] = round(exit_price, 6)
            pick["exit_reason"] = exit_reason
            pick["pnl_pct"] = round(pnl_pct, 3)
            pick["pnl_usd"] = round(pnl_usd, 2)
            pick["hours_held"] = round(hours_held, 1)
            pick["closed_at"] = now.isoformat()
            pick["price_at_check"] = round(current_price, 6)

            picks["open_picks"].remove(pick)
            picks["closed_picks"].append(pick)
            resolved += 1

            emoji = "✅" if pnl_pct > 0 else "❌"
            logger.info(f"  {emoji} {symbol} / {pick['mutation_name']}: {exit_reason} "
                        f"PnL={pnl_pct:+.2f}% (${pnl_usd:+.2f}) after {hours_held:.1f}h")
        else:
            # Update current price and unrealized PnL
            if signal == "LONG":
                unrealized = (current_price - entry) / entry * 100
            else:
                unrealized = (entry - current_price) / entry * 100

            pick["current_price"] = round(current_price, 6)
            pick["unrealized_pnl_pct"] = round(unrealized, 3)
            pick["last_checked"] = now.isoformat()
            pick["hours_held"] = round(hours_held, 1)

            still_open += 1
            emoji = "📈" if unrealized > 0 else "📉"
            logger.info(f"  {emoji} {symbol} / {pick['mutation_name']}: "
                        f"price={current_price:.4f} ({unrealized:+.2f}%) | {hours_held:.1f}h held")

    # Update stats
    closed = picks["closed_picks"]
    if closed:
        wins = [p for p in closed if p["status"] == "WON"]
        losses = [p for p in closed if p["status"] == "LOST"]
        total_pnl = sum(p["pnl_pct"] for p in closed)
        total_usd = sum(p["pnl_usd"] for p in closed)
        avg_win = np.mean([p["pnl_pct"] for p in wins]) if wins else 0
        avg_loss = np.mean([p["pnl_pct"] for p in losses]) if losses else 0
        gross_w = sum(p["pnl_pct"] for p in wins) if wins else 0
        gross_l = abs(sum(p["pnl_pct"] for p in losses)) if losses else 0.01

        picks["stats"] = {
            "total_picks": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0,
            "total_pnl_pct": round(total_pnl, 2),
            "total_pnl_usd": round(total_usd, 2),
            "avg_win_pct": round(float(avg_win), 3),
            "avg_loss_pct": round(float(avg_loss), 3),
            "profit_factor": round(gross_w / gross_l, 2) if gross_l > 0 else 0,
            "best_trade": max(closed, key=lambda x: x["pnl_pct"])["pnl_pct"] if closed else 0,
            "worst_trade": min(closed, key=lambda x: x["pnl_pct"])["pnl_pct"] if closed else 0,
            "open_picks": len(picks["open_picks"]),
        }

    save_picks(picks)

    logger.info(f"\n  Resolved: {resolved} | Still open: {still_open}")
    if picks.get("stats"):
        s = picks["stats"]
        logger.info(f"  📊 RUNNING TOTAL: {s['wins']}W / {s['losses']}L "
                    f"({s['win_rate']}% WR) | PnL: {s['total_pnl_pct']:+.2f}% "
                    f"(${s['total_pnl_usd']:+.2f}) | PF: {s['profit_factor']}")


def print_report():
    """Print a detailed report of all picks."""
    picks = load_picks()

    print("\n" + "=" * 70)
    print("  🏆 MEGA MUTATION PAPER TRADING REPORT")
    print("=" * 70)

    # Open picks
    if picks["open_picks"]:
        print(f"\n  📂 OPEN PICKS ({len(picks['open_picks'])})")
        print("-" * 70)
        for p in picks["open_picks"]:
            unr = p.get("unrealized_pnl_pct", 0)
            emoji = "📈" if unr > 0 else "📉"
            print(f"  {emoji} {p['signal']} {p['symbol']} | {p['mutation_name']} ({p['primary_strategy']})")
            print(f"     Entry: {p['entry_price']} → TP: {p['tp_price']} (+{p['tp_pct']}%) / "
                  f"SL: {p['sl_price']} (-{p['sl_pct']}%)")
            if "current_price" in p:
                print(f"     Current: {p['current_price']} ({unr:+.2f}%) | {p.get('hours_held', 0):.1f}h held")
            print()

    # Closed picks
    if picks["closed_picks"]:
        print(f"\n  📋 CLOSED PICKS ({len(picks['closed_picks'])})")
        print("-" * 70)
        for p in picks["closed_picks"]:
            emoji = "✅" if p["status"] == "WON" else "❌"
            print(f"  {emoji} {p['signal']} {p['symbol']} | {p['mutation_name']} | "
                  f"{p['exit_reason']} | PnL: {p['pnl_pct']:+.2f}% (${p['pnl_usd']:+.2f}) | "
                  f"{p['hours_held']:.1f}h held")
        print()

    # Stats
    s = picks.get("stats", {})
    if s:
        print(f"\n  📊 LIFETIME STATS")
        print("-" * 70)
        print(f"  Total: {s.get('total_picks', 0)} trades | "
              f"{s.get('wins', 0)}W / {s.get('losses', 0)}L = {s.get('win_rate', 0)}% WR")
        print(f"  PnL: {s.get('total_pnl_pct', 0):+.2f}% (${s.get('total_pnl_usd', 0):+.2f} on $100/trade)")
        print(f"  PF: {s.get('profit_factor', 0)} | Best: {s.get('best_trade', 0):+.2f}% | "
              f"Worst: {s.get('worst_trade', 0):+.2f}%")

    print("\n" + "=" * 70)


# Also update the incubator_ledger.json for visibility on the Battleground dashboard
def sync_to_incubator_ledger():
    """Sync Mega Mutation picks to the incubator ledger for dashboard visibility."""
    picks = load_picks()
    ledger_file = PROJECT_ROOT / "battleground" / "data" / "incubator_ledger.json"

    if not ledger_file.exists():
        return

    try:
        with open(str(ledger_file)) as f:
            ledger = json.load(f)
    except Exception:
        return

    # Add/update Mega Mutation strategy entry
    ledger["strategies"]["mega_mutation_tournament"] = {
        "open_picks": [
            {
                "symbol": p["symbol"],
                "direction": p["signal"],
                "entry_price": p["entry_price"],
                "tp_price": p["tp_price"],
                "sl_price": p["sl_price"],
                "strategy": f"mega_mutation_{p['mutation_name']}",
                "confidence": p.get("tournament_wr", 0.8),
                "timestamp": p["opened_at"],
            }
            for p in picks["open_picks"]
        ],
        "closed_trades": [
            {
                "symbol": p["symbol"],
                "direction": p["signal"],
                "entry_price": p["entry_price"],
                "exit_price": p.get("exit_price", p["entry_price"]),
                "pnl_pct": float(p.get("pnl_pct", 0) or 0),
                "result": p.get("status", "UNKNOWN"),
                "exit_reason": p.get("exit_reason", ""),
                "strategy": f"mega_mutation_{p['mutation_name']}",
                "opened_at": p["opened_at"],
                "closed_at": p.get("closed_at", ""),
            }
            for p in picks["closed_picks"]
        ],
        "total_signals_generated": len(picks["open_picks"]) + len(picks["closed_picks"]),
        "first_seen": picks["open_picks"][0]["opened_at"] if picks["open_picks"] else
                      (picks["closed_picks"][0]["opened_at"] if picks["closed_picks"] else
                       datetime.now(timezone.utc).isoformat()),
        "stats": picks.get("stats", {}),
    }

    ledger["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(str(ledger_file), "w") as f:
        json.dump(ledger, f, indent=2, default=str)

    logger.info(f"  📋 Synced to incubator ledger: {ledger_file}")


# ============================================================================
# Main
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="Mega Mutation Live Tracker")
    parser.add_argument("mode", choices=["generate", "check", "report", "full"],
                        help="generate=new picks, check=resolve TP/SL, report=print summary, full=generate+check")
    args = parser.parse_args()

    if args.mode == "generate":
        generate_picks()
        sync_to_incubator_ledger()
    elif args.mode == "check":
        check_picks()
        sync_to_incubator_ledger()
    elif args.mode == "report":
        print_report()
    elif args.mode == "full":
        generate_picks()
        check_picks()
        sync_to_incubator_ledger()
        print_report()


if __name__ == "__main__":
    main()
