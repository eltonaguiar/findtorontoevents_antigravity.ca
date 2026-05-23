"""
ALPHA_ENGINE -- Micro-Breakout Detector
========================================
Identifies early-stage momentum moves (0.5-1% moves that could become 5%+).

Scoring components (total 0-100):
  - Price velocity z-score   (30%) -- last 3 candles vs previous 10
  - Volume spike             (30%) -- current vs 20-period average
  - RSI momentum alignment   (20%) -- RSI(14) crossing 50 threshold
  - BB squeeze release        (20%) -- bandwidth expanding after contraction

Usage:
  from alpha_engine.micro_breakout_detector import detect_breakouts
  breakouts = detect_breakouts(["BTCUSDT", "ETHUSDT", "SOLUSDT"])
  for b in breakouts:
      print(f"{b['symbol']} {b['direction']} score={b['score']} entry={b['entry_price']}")
"""
from __future__ import annotations

import json
import logging
import math
import sys
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)

# -- API endpoints with 3+ fallback chain ------------------------------

_BINANCE_KLINE_BASES = [
    "https://api.binance.com/api/v3/klines",
    "https://api1.binance.com/api/v3/klines",
    "https://api2.binance.com/api/v3/klines",
]

_COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# -- Thresholds --------------------------------------------------------

BREAKOUT_THRESHOLD = 60       # Minimum score to report
VELOCITY_ZSCORE_MIN = 2.0     # Minimum z-score for velocity signal
VOLUME_SPIKE_RATIO = 2.0      # Volume must be 2x 20-period avg
RSI_PERIOD = 14
BB_PERIOD = 20


# -- Data fetching -----------------------------------------------------

def _fetch_json(url: str, timeout: int = 10) -> Optional[list | dict]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaMicroBreakout/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.debug(f"Fetch failed: {url}: {e}")
        return None


def _fetch_klines(symbol: str, interval: str, limit: int) -> Optional[list]:
    """
    Fetch OHLCV with Binance 3-mirror + CoinGecko fallback.
    Returns list of [open, high, low, close, volume].
    """
    for base in _BINANCE_KLINE_BASES:
        url = f"{base}?symbol={symbol}&interval={interval}&limit={limit}"
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) > 5:
            return [
                [float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])]
                for k in data
            ]

    # CoinGecko fallback
    cg_id = _symbol_to_coingecko(symbol)
    if cg_id:
        days_map = {"15m": 1, "1h": 2, "4h": 10}
        days = days_map.get(interval, 2)
        url = f"{_COINGECKO_BASE}/coins/{cg_id}/ohlc?vs_currency=usd&days={days}"
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) > 5:
            return [
                [float(k[1]), float(k[2]), float(k[3]), float(k[4]), 0.0]
                for k in data
            ]

    return None


def _symbol_to_coingecko(symbol: str) -> Optional[str]:
    mapping = {
        "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "BNBUSDT": "binancecoin",
        "SOLUSDT": "solana", "ADAUSDT": "cardano", "DOGEUSDT": "dogecoin",
        "XRPUSDT": "ripple", "AVAXUSDT": "avalanche-2", "DOTUSDT": "polkadot",
        "LINKUSDT": "chainlink", "MATICUSDT": "matic-network", "LTCUSDT": "litecoin",
        "ATOMUSDT": "cosmos", "NEARUSDT": "near", "ARBUSDT": "arbitrum",
        "OPUSDT": "optimism", "APTUSDT": "aptos", "SUIUSDT": "sui",
        "PEPEUSDT": "pepe", "WIFUSDT": "dogwifcoin",
    }
    return mapping.get(symbol.upper())


# -- Technical indicators ----------------------------------------------

def _compute_rsi(closes: list, period: int = 14) -> list:
    """Compute RSI series. Returns list same length as closes (NaN-padded at start)."""
    if len(closes) < period + 1:
        return [50.0] * len(closes)

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    rsi_values = [50.0] * (period + 1)  # pad initial values

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100.0 - 100.0 / (1.0 + rs))

    return rsi_values


def _compute_bb_width_series(closes: list, period: int = 20) -> list:
    """Compute BB width series (normalized). Returns list same length as closes."""
    widths = [0.0] * min(period - 1, len(closes))
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1: i + 1]
        sma = sum(window) / period
        if sma == 0:
            widths.append(0.0)
            continue
        variance = sum((x - sma) ** 2 for x in window) / period
        std = math.sqrt(variance)
        widths.append((4 * std) / sma)
    return widths


def _compute_atr(highs: list, lows: list, closes: list, period: int = 14) -> float:
    """Compute current ATR value."""
    if len(highs) < period + 1:
        return 0.0

    tr = [highs[0] - lows[0]]
    for i in range(1, len(highs)):
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))

    # Wilder smooth
    atr = sum(tr[:period]) / period
    for i in range(period, len(tr)):
        atr = (atr * (period - 1) + tr[i]) / period
    return atr


def _z_score(value: float, series: list) -> float:
    """Compute z-score of value relative to series."""
    if len(series) < 2:
        return 0.0
    mean = sum(series) / len(series)
    variance = sum((x - mean) ** 2 for x in series) / len(series)
    std = math.sqrt(variance) if variance > 0 else 0.0
    if std < 1e-12:
        return 0.0
    return (value - mean) / std


# -- Breakout Detection ------------------------------------------------

def _analyze_symbol(symbol: str) -> Optional[dict]:
    """
    Analyze a single symbol for micro-breakout conditions.
    Uses 1h candles (24h) for main analysis and 15m candles (4h) for velocity.
    """
    # Fetch 1h candles (last 30 for RSI/BB calculations)
    klines_1h = _fetch_klines(symbol, "1h", 30)
    if not klines_1h or len(klines_1h) < 20:
        return None

    # Fetch 15m candles (last 16 = 4h of data)
    klines_15m = _fetch_klines(symbol, "15m", 20)

    closes_1h = [k[3] for k in klines_1h]
    highs_1h = [k[1] for k in klines_1h]
    lows_1h = [k[2] for k in klines_1h]
    volumes_1h = [k[4] for k in klines_1h]

    current_price = closes_1h[-1]
    if current_price <= 0:
        return None

    # -- 1. Price Velocity (30%) ---------------------------------------
    # Compare last 3 candle moves vs previous 10
    velocity_score = 0.0

    if klines_15m and len(klines_15m) >= 15:
        closes_15m = [k[3] for k in klines_15m]
        # Candle-to-candle % changes
        pct_changes = []
        for i in range(1, len(closes_15m)):
            if closes_15m[i - 1] > 0:
                pct_changes.append((closes_15m[i] - closes_15m[i - 1]) / closes_15m[i - 1] * 100)

        if len(pct_changes) >= 13:
            recent_velocity = sum(abs(c) for c in pct_changes[-3:]) / 3
            historical = pct_changes[:-3]
            z = _z_score(recent_velocity, [abs(c) for c in historical])

            if z >= 3.0:
                velocity_score = 30.0
            elif z >= 2.0:
                velocity_score = 20.0
            elif z >= 1.5:
                velocity_score = 10.0
    else:
        # Fallback: use 1h candles
        pct_changes = []
        for i in range(1, len(closes_1h)):
            if closes_1h[i - 1] > 0:
                pct_changes.append((closes_1h[i] - closes_1h[i - 1]) / closes_1h[i - 1] * 100)

        if len(pct_changes) >= 13:
            recent_velocity = sum(abs(c) for c in pct_changes[-3:]) / 3
            historical = pct_changes[:-3]
            z = _z_score(recent_velocity, [abs(c) for c in historical])

            if z >= 3.0:
                velocity_score = 30.0
            elif z >= 2.0:
                velocity_score = 20.0
            elif z >= 1.5:
                velocity_score = 10.0

    # -- 2. Volume Spike (30%) -----------------------------------------
    volume_score = 0.0

    if volumes_1h[-1] > 0:  # Skip if CoinGecko fallback (no volume)
        vol_20_avg = sum(volumes_1h[-20:]) / min(len(volumes_1h), 20) if volumes_1h else 0
        if vol_20_avg > 0:
            vol_ratio = volumes_1h[-1] / vol_20_avg
            if vol_ratio >= 3.0:
                volume_score = 30.0
            elif vol_ratio >= 2.0:
                volume_score = 22.0
            elif vol_ratio >= 1.5:
                volume_score = 12.0
            elif vol_ratio >= 1.2:
                volume_score = 5.0

    # -- 3. RSI Momentum (20%) -----------------------------------------
    rsi_score = 0.0
    direction = "LONG"

    rsi_values = _compute_rsi(closes_1h, period=RSI_PERIOD)

    if len(rsi_values) >= 3:
        rsi_now = rsi_values[-1]
        rsi_prev = rsi_values[-2]
        rsi_prev2 = rsi_values[-3]

        # LONG: RSI crossing above 50 from below
        if rsi_now > 50 and rsi_prev <= 50:
            rsi_score = 20.0
            direction = "LONG"
        elif rsi_now > 50 and rsi_prev2 <= 50:
            rsi_score = 15.0
            direction = "LONG"
        # SHORT: RSI crossing below 50 from above
        elif rsi_now < 50 and rsi_prev >= 50:
            rsi_score = 20.0
            direction = "SHORT"
        elif rsi_now < 50 and rsi_prev2 >= 50:
            rsi_score = 15.0
            direction = "SHORT"
        # Momentum continuation
        elif rsi_now > 55 and rsi_now > rsi_prev:
            rsi_score = 10.0
            direction = "LONG"
        elif rsi_now < 45 and rsi_now < rsi_prev:
            rsi_score = 10.0
            direction = "SHORT"

    # -- 4. BB Squeeze Release (20%) -----------------------------------
    bb_score = 0.0
    bb_widths = _compute_bb_width_series(closes_1h, period=BB_PERIOD)

    if len(bb_widths) >= 10:
        current_bw = bb_widths[-1]
        recent_avg = sum(bb_widths[-5:]) / 5
        older_avg = sum(bb_widths[-10:-5]) / 5

        # Squeeze release: current expanding after contraction
        if older_avg > 0 and recent_avg > 0:
            # Was contracting (older > recent average of previous) and now expanding
            if current_bw > recent_avg * 1.2 and older_avg > recent_avg * 0.9:
                bb_score = 20.0
            elif current_bw > recent_avg * 1.1:
                bb_score = 12.0
            elif current_bw > recent_avg:
                bb_score = 5.0

    # -- Aggregate Score -----------------------------------------------
    total_score = velocity_score + volume_score + rsi_score + bb_score

    # Compute ATR for TP/SL
    atr = _compute_atr(highs_1h, lows_1h, closes_1h, period=14)

    if direction == "LONG":
        suggested_tp = current_price + 2 * atr
        suggested_sl = current_price - 1 * atr
    else:
        suggested_tp = current_price - 2 * atr
        suggested_sl = current_price + 1 * atr

    return {
        "symbol": symbol,
        "direction": direction,
        "score": round(total_score, 1),
        "entry_price": round(current_price, 6),
        "suggested_tp": round(suggested_tp, 6),
        "suggested_sl": round(suggested_sl, 6),
        "atr": round(atr, 6),
        "components": {
            "velocity": round(velocity_score, 1),
            "volume": round(volume_score, 1),
            "rsi": round(rsi_score, 1),
            "bb_expansion": round(bb_score, 1),
        },
        "rsi_current": round(rsi_values[-1], 1) if rsi_values else 50.0,
    }


def detect_breakouts(symbols: list[str], threshold: int = BREAKOUT_THRESHOLD) -> list[dict]:
    """
    Scan multiple symbols for micro-breakout conditions.

    Args:
        symbols: List of trading pairs (e.g. ["BTCUSDT", "ETHUSDT"])
        threshold: Minimum score (0-100) to include in results. Default 60.

    Returns:
        List of breakout signals sorted by score descending.
        Each dict: symbol, direction, score, entry_price, suggested_tp, suggested_sl, components
    """
    results = []

    for sym in symbols:
        try:
            analysis = _analyze_symbol(sym)
            if analysis and analysis["score"] >= threshold:
                results.append(analysis)
            elif analysis:
                logger.debug(f"{sym}: score {analysis['score']:.0f} below threshold {threshold}")
        except Exception as e:
            logger.warning(f"Error analyzing {sym}: {e}")
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


# -- Standalone execution ----------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "ADAUSDT", "DOTUSDT",
        "ARBUSDT", "OPUSDT", "APTUSDT", "SUIUSDT", "NEARUSDT",
    ]

    print("=" * 70)
    print("ALPHA ENGINE -- Micro-Breakout Detector v1.0")
    print(f"Scanning {len(symbols)} symbols (threshold: {BREAKOUT_THRESHOLD})")
    print("=" * 70)

    # Also show all scores even below threshold
    all_results = []
    for sym in symbols:
        try:
            analysis = _analyze_symbol(sym)
            if analysis:
                all_results.append(analysis)
        except Exception as e:
            print(f"  ERROR {sym}: {e}")

    all_results.sort(key=lambda x: x["score"], reverse=True)

    # Print all scores
    print(f"\n{'Symbol':<12} {'Dir':<6} {'Score':>5}  {'Vel':>4} {'Vol':>4} {'RSI':>4} {'BB':>4}  {'Price':>12}  {'TP':>12}  {'SL':>12}")
    print("-" * 95)

    for r in all_results:
        c = r["components"]
        marker = " ***" if r["score"] >= BREAKOUT_THRESHOLD else ""
        print(
            f"{r['symbol']:<12} {r['direction']:<6} {r['score']:>5.0f}  "
            f"{c['velocity']:>4.0f} {c['volume']:>4.0f} {c['rsi']:>4.0f} {c['bb_expansion']:>4.0f}  "
            f"{r['entry_price']:>12.2f}  {r['suggested_tp']:>12.2f}  {r['suggested_sl']:>12.2f}"
            f"{marker}"
        )

    # Show breakouts only
    breakouts = [r for r in all_results if r["score"] >= BREAKOUT_THRESHOLD]

    print(f"\n{'=' * 70}")
    if breakouts:
        print(f"BREAKOUTS DETECTED: {len(breakouts)}")
        for b in breakouts:
            print(f"  >>> {b['symbol']} {b['direction']} score={b['score']:.0f} "
                  f"entry={b['entry_price']:.2f} TP={b['suggested_tp']:.2f} SL={b['suggested_sl']:.2f}")
    else:
        print("No breakouts above threshold. Market is quiet.")

    print("\nDone.")
