#!/usr/bin/env python3
"""
CBC Flip — Candle By Candle Flip State Machine
================================================
Strategy credit: MapleStax Trades (@MapleStaxTrades on X/Twitter)
Pine Script indicator: "CBC Flip" by friksa & AsiaRoo (TradingView)

Rules (from MapleStax, updated Jan 2024 — strict inequality, no fakeouts):
  - Bulls in control: close > previous candle HIGH (strict, not >=)
  - Bears in control: close < previous candle LOW (strict, not <=)
  - No flip: neither met → previous state persists
  - Best on 5-10 min timeframes (use 10m for trend, 2m for entry)

Risk management (Dec 2023 update):
  - CBC flips long → SL = candle low
  - CBC flips short → SL = candle high

MapleStax usage tips (Jul 2025):
  - Longs: CBC bullish + price above VWAP + coming out of demand zone
  - Shorts: CBC bearish + price below VWAP + coming out of supply zone
  - Avoid: longs into overhead supply, shorts into demand below
  - Higher TF CBC (10m) on lower TF chart (2m) for stronger trend alignment

Combined with 9/20 EMA for additional trend confirmation:
  - LONG: CBC bullish + price > VWAP + 9 EMA > 20 EMA
  - SHORT: CBC bearish + price < VWAP + 9 EMA < 20 EMA
"""

from __future__ import annotations

import json
import math
import os
import ssl
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# -- Windows UTF-8 fix --
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_PATH = DATA_DIR / "maplestax_picks.json"

# 5+ API failover chain (NEVER single Binance endpoint)
BINANCE_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

# Top symbols to scan
SCAN_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "MATICUSDT", "NEARUSDT", "SUIUSDT", "APTUSDT", "RENDERUSDT",
    "FETUSDT", "AAVEUSDT", "LTCUSDT", "UNIUSDT", "ATOMUSDT",
]

# Use 5-minute candles (MapleStax recommended: 5 or 10 min)
KLINE_INTERVAL = "5m"
KLINE_LIMIT = 100  # enough for VWAP + EMAs + CBC state

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _fetch_json(url: str, timeout: int = 15):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=_ssl_ctx, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Fetch klines with failover
# ---------------------------------------------------------------------------

def fetch_klines(symbol: str, interval: str = KLINE_INTERVAL, limit: int = KLINE_LIMIT) -> list[dict]:
    """Fetch OHLCV candles from Binance with 5-mirror failover."""
    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) >= 30:
            candles = []
            for k in data:
                candles.append({
                    "time": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                })
            return candles
    return []


# ---------------------------------------------------------------------------
# VWAP calculation (daily session reset at 00:00 UTC)
# ---------------------------------------------------------------------------

def compute_vwap(candles: list[dict]) -> float | None:
    """Compute session VWAP. Resets at 00:00 UTC daily."""
    if not candles:
        return None

    # Find today's session start (00:00 UTC)
    now_ms = candles[-1]["time"]
    today_start_ms = (now_ms // 86400000) * 86400000  # floor to day

    cum_tp_vol = 0.0
    cum_vol = 0.0
    for c in candles:
        if c["time"] >= today_start_ms:
            typical_price = (c["high"] + c["low"] + c["close"]) / 3
            cum_tp_vol += typical_price * c["volume"]
            cum_vol += c["volume"]

    if cum_vol == 0:
        return None
    return cum_tp_vol / cum_vol


# ---------------------------------------------------------------------------
# EMA calculation
# ---------------------------------------------------------------------------

def compute_ema(closes: list[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    k = 2.0 / (period + 1)
    ema = sum(closes[:period]) / period
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
    return ema


# ---------------------------------------------------------------------------
# CBC Flip State Machine (MapleStax, Jan 2024 update — strict inequality)
# ---------------------------------------------------------------------------

def compute_cbc_state(candles: list[dict]) -> dict:
    """
    Run the CBC Flip state machine over candle history.

    Returns dict with:
      - state: 'BULL' or 'BEAR'
      - flipped: True if state just changed on the last candle
      - flip_type: 'BULL_FLIP' or 'BEAR_FLIP' or None
      - signal_candle: the candle that caused the flip (for SL placement)
    """
    if len(candles) < 3:
        return {"state": "BEAR", "flipped": False, "flip_type": None, "signal_candle": None}

    # Initialize state as BEAR (conservative)
    cbc = False  # False = bears, True = bulls

    # Walk through all candles to build state history
    prev_cbc = cbc
    signal_candle = None

    for i in range(1, len(candles)):
        prev = candles[i - 1]
        curr = candles[i]
        prev_cbc = cbc

        # Jan 2024 update: strict inequality (> not >=, < not <=)
        # "close above (not on) the high" / "close below (not on) the low"
        if cbc and curr["close"] < prev["low"]:
            # Was bullish, now bearish flip
            cbc = False
        if not cbc and curr["close"] > prev["high"]:
            # Was bearish, now bullish flip
            cbc = True

    # Check if the LAST candle caused a flip
    last = candles[-1]
    second_last = candles[-2]
    flipped = False
    flip_type = None

    # Re-check the final transition
    if prev_cbc and not cbc:
        flipped = True
        flip_type = "BEAR_FLIP"
        signal_candle = last
    elif not prev_cbc and cbc:
        # Need to recompute: walk again to get the state before last candle
        cbc2 = False
        for i in range(1, len(candles) - 1):
            prev = candles[i - 1]
            curr = candles[i]
            if cbc2 and curr["close"] < prev["low"]:
                cbc2 = False
            if not cbc2 and curr["close"] > prev["high"]:
                cbc2 = True
        # Now check last candle
        if not cbc2 and last["close"] > second_last["high"]:
            flipped = True
            flip_type = "BULL_FLIP"
            signal_candle = last

    return {
        "state": "BULL" if cbc else "BEAR",
        "flipped": flipped,
        "flip_type": flip_type,
        "signal_candle": signal_candle,
    }


# ---------------------------------------------------------------------------
# Analyze a single symbol
# ---------------------------------------------------------------------------

def analyze_symbol(symbol: str) -> dict | None:
    """Analyze a symbol for MapleStax VWAP + EMA + CBC Flip signals."""
    candles = fetch_klines(symbol)
    if len(candles) < 30:
        return None

    closes = [c["close"] for c in candles]
    current_price = closes[-1]

    # 1. VWAP
    vwap = compute_vwap(candles)
    if vwap is None:
        return None

    # 2. EMAs (9 and 20 period)
    ema9 = compute_ema(closes, 9)
    ema20 = compute_ema(closes, 20)
    if ema9 is None or ema20 is None:
        return None

    # 3. CBC Flip state
    cbc = compute_cbc_state(candles)

    # 4. Determine signal
    price_above_vwap = current_price > vwap
    price_below_vwap = current_price < vwap
    ema_bullish = ema9 > ema20
    ema_bearish = ema9 < ema20
    cbc_bull = cbc["state"] == "BULL"
    cbc_bear = cbc["state"] == "BEAR"
    cbc_flipped = cbc["flipped"]

    signal = None
    direction = None

    # LONG: CBC bullish (or just flipped bullish) + price > VWAP + 9 EMA > 20 EMA
    if cbc_bull and price_above_vwap and ema_bullish:
        signal = "LONG"
        direction = "LONG"

    # SHORT: CBC bearish (or just flipped bearish) + price < VWAP + 9 EMA < 20 EMA
    elif cbc_bear and price_below_vwap and ema_bearish:
        signal = "SHORT"
        direction = "SHORT"

    if signal is None:
        return None

    # 5. Calculate TP/SL
    signal_candle = cbc.get("signal_candle") or candles[-1]

    if direction == "LONG":
        # SL = candle low (MapleStax Dec 2023 risk rule)
        sl = signal_candle["low"] * 0.999  # tiny buffer
        risk = current_price - sl
        if risk <= 0:
            return None
        tp = current_price + risk * 1.8  # 1.8:1 R:R
    else:  # SHORT
        # SL = candle high (MapleStax Dec 2023 risk rule)
        sl = signal_candle["high"] * 1.001  # tiny buffer
        risk = sl - current_price
        if risk <= 0:
            return None
        tp = current_price - risk * 1.8  # 1.8:1 R:R

    # 6. Confidence scaling
    confidence = 0.70

    # Price distance from VWAP (further = stronger signal)
    vwap_dist_pct = abs(current_price - vwap) / vwap * 100
    if vwap_dist_pct > 1.0:
        confidence += 0.05

    # EMA gap widening
    ema_gap_pct = abs(ema9 - ema20) / ema20 * 100
    if ema_gap_pct > 0.3:
        confidence += 0.05

    # Fresh CBC flip (just happened) = stronger signal
    if cbc_flipped:
        confidence += 0.10

    confidence = min(0.95, confidence)

    # R:R check
    rr = abs(tp - current_price) / abs(current_price - sl) if abs(current_price - sl) > 0 else 0
    if rr < 1.2:
        return None

    return {
        "symbol": symbol,
        "direction": direction,
        "entry_price": round(current_price, 6),
        "take_profit": round(tp, 6),
        "stop_loss": round(sl, 6),
        "confidence": round(confidence, 2),
        "risk_reward": round(rr, 2),
        "vwap": round(vwap, 6),
        "ema9": round(ema9, 6),
        "ema20": round(ema20, 6),
        "cbc_state": cbc["state"],
        "cbc_flipped": cbc_flipped,
        "cbc_flip_type": cbc.get("flip_type"),
        "vwap_distance_pct": round(vwap_dist_pct, 2),
        "ema_gap_pct": round(ema_gap_pct, 3),
        "timeframe": KLINE_INTERVAL,
    }


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run() -> list[dict]:
    """Scan all symbols and generate MapleStax VWAP + CBC Flip picks."""
    print("=" * 70)
    print("  MAPLESTAX VWAP + CBC FLIP STRATEGY")
    print("  Strategy credit: MapleStax Trades (@MapleStaxTrades)")
    print(f"  Timeframe: {KLINE_INTERVAL} | Symbols: {len(SCAN_SYMBOLS)}")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    picks = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for sym in SCAN_SYMBOLS:
        try:
            result = analyze_symbol(sym)
            if result is None:
                print(f"  {sym:<14} -- no signal")
                continue

            pick = {
                "id": f"maplestax_cbc::{sym}::{now_iso[:10]}",
                "strategy": "maplestax_vwap_cbc_flip",
                "symbol": sym,
                "category": "crypto",
                "asset_class": "CRYPTO",
                "signal_type": "CBC_FLIP",
                "direction": result["direction"],
                "entry_price": result["entry_price"],
                "take_profit": result["take_profit"],
                "stop_loss": result["stop_loss"],
                "confidence": result["confidence"],
                "risk_reward": result["risk_reward"],
                "ml_score": result["confidence"],
                "status": "OPEN",
                "reason": (
                    f"CBC {result['cbc_state']} {'(FRESH FLIP)' if result['cbc_flipped'] else ''} "
                    f"| Price {'>' if result['direction'] == 'LONG' else '<'} VWAP "
                    f"| EMA9 {'>' if result['direction'] == 'LONG' else '<'} EMA20 "
                    f"| VWAP dist {result['vwap_distance_pct']:.1f}%"
                ),
                "source_system": "alpha_engine",
                "timestamp": now_iso,
                "timeframe": KLINE_INTERVAL,
                "vwap": result["vwap"],
                "ema9": result["ema9"],
                "ema20": result["ema20"],
                "cbc_state": result["cbc_state"],
                "cbc_flipped": result["cbc_flipped"],
            }
            picks.append(pick)

            flip_tag = " ** FRESH FLIP **" if result["cbc_flipped"] else ""
            print(
                f"  {sym:<14} {result['direction']:<6} "
                f"CBC={result['cbc_state']} "
                f"VWAP_dist={result['vwap_distance_pct']:+.1f}% "
                f"EMA_gap={result['ema_gap_pct']:.2f}% "
                f"R:R={result['risk_reward']:.1f} "
                f"conf={result['confidence']:.0%}"
                f"{flip_tag}"
            )
        except Exception as e:
            print(f"  {sym:<14} ERROR: {e}")

    # Save picks
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2)

    print()
    print(f"  Total signals: {len(picks)}")
    longs = sum(1 for p in picks if p["direction"] == "LONG")
    shorts = len(picks) - longs
    print(f"  LONG: {longs} | SHORT: {shorts}")
    flips = sum(1 for p in picks if p.get("cbc_flipped"))
    print(f"  Fresh CBC flips: {flips}")
    print(f"  Saved to: {OUTPUT_PATH}")
    print("=" * 70)

    return picks


if __name__ == "__main__":
    run()
