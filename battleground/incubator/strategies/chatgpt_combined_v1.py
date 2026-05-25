#!/usr/bin/env python3
"""
ChatGPT Combined Strategy v1 — MavilimW + Range Filter + Cyberpunk Analyzer + Volume

Inspired by: "I gave ChatGPT 4.5 every free TradingView indicator...
              The Strategy it Built was Insane" (YouTube)

Implements 4 indicators as Python filters and combines them into a
single consensus signal:

  1. MavilimW — Fibonacci-weighted moving average trend filter
     (6-layer smoothed WMA using Fib numbers: 3,5,8,13,21,34,55,89)
     Signal: price above MavilimW = LONG, below = SHORT

  2. Range Filter — DonovanWall noise filter
     Smooth average range gating: only moves when price exceeds
     the smoothed range × multiplier. Filters out noise.
     Signal: filter direction change = trend confirmation

  3. Cyberpunk Value Trend Analyzer — momentum oscillator
     Normalized price deviation from WMA with overbought/oversold levels.
     Signal: cross above entry_level = BUY, cross below exit_level = SELL

  4. Volume Confirmation — relative volume spike detection
     Signal: current volume > 1.5x 20-period SMA = confirmed

  COMBINED SIGNAL:
     3+ of 4 indicators agree → HIGH confidence
     2 of 4 agree → MEDIUM confidence
     <2 agree → NO SIGNAL

Data: Binance klines API (free, no key required)
"""
from __future__ import annotations

import json
import datetime as dt
import pathlib
import urllib.request
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT",
    "DOGEUSDT", "AVAXUSDT", "ADAUSDT", "LINKUSDT", "DOTUSDT",
    "NEARUSDT", "TRXUSDT", "MATICUSDT",
]
INTERVAL = "4h"
LIMIT = 200  # candles to fetch
OUTPUT_PATH = pathlib.Path("battleground/data/chatgpt_combined_signals.json")

# MavilimW parameters (Fibonacci layers)
MAVW_FIBS = [3, 5, 8, 13, 21, 34, 55, 89]

# Range Filter parameters
RF_PERIOD = 20
RF_MULTIPLIER = 2.6

# Cyberpunk parameters
CYBER_LENGTH = 28
CYBER_ENTRY_LEVEL = 30
CYBER_EXIT_LEVEL = 75

# Volume parameters
VOL_SMA_PERIOD = 20
VOL_SPIKE_MULT = 1.5


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------
def fetch_klines(symbol: str, interval: str = INTERVAL, limit: int = LIMIT) -> List[dict]:
    """Fetch OHLCV klines from Binance."""
    url = (
        f"https://api.binance.com/api/v3/klines"
        f"?symbol={symbol}&interval={interval}&limit={limit}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "ChatGPTCombined/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = json.loads(resp.read())
    candles = []
    for k in raw:
        candles.append({
            "ts": k[0],
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        })
    return candles


# ---------------------------------------------------------------------------
# Indicator 1: MavilimW — Fibonacci Weighted Moving Average
# ---------------------------------------------------------------------------
def _wma(data: List[float], period: int) -> List[float]:
    """Weighted Moving Average."""
    result = [None] * len(data)
    if len(data) < period:
        return result
    for i in range(period - 1, len(data)):
        window = data[i - period + 1: i + 1]
        # Skip if any values are None
        if any(v is None for v in window):
            continue
        weights = list(range(1, period + 1))
        wsum = sum(w * v for w, v in zip(weights, window))
        result[i] = wsum / sum(weights)
    return result


def calc_mavilimw(closes: List[float]) -> List[Optional[float]]:
    """Calculate MavilimW: cascading WMAs using Fibonacci periods.

    MavilimW = WMA(WMA(WMA(WMA(WMA(WMA(close, f1), f2), f3), f4), f5), f6)
    where f1-f6 are Fibonacci numbers.
    """
    # Use first 6 Fibonacci numbers from our list
    fibs = MAVW_FIBS[:6]  # [3, 5, 8, 13, 21, 34]

    # Cascade WMAs
    layer = closes[:]
    for fib_period in fibs:
        layer = _wma(layer, fib_period)
        # Replace Nones with previous values for next cascade
        cleaned = []
        last = None
        for v in layer:
            if v is not None:
                last = v
            cleaned.append(last)
        layer = cleaned

    return layer


def mavilimw_signal(closes: List[float]) -> Tuple[str, float]:
    """Return (direction, confidence) based on MavilimW.

    LONG if price > MavilimW and MavilimW rising
    SHORT if price < MavilimW and MavilimW falling
    """
    mavw = calc_mavilimw(closes)
    if mavw[-1] is None:
        return "NEUTRAL", 0.0

    current_price = closes[-1]
    mavw_val = mavw[-1]
    mavw_prev = mavw[-2] if mavw[-2] is not None else mavw_val

    # Distance from MavilimW as confidence proxy
    distance_pct = abs(current_price - mavw_val) / mavw_val * 100
    conf = min(0.95, 0.5 + distance_pct * 0.05)

    if current_price > mavw_val and mavw_val > mavw_prev:
        return "LONG", round(conf, 3)
    elif current_price < mavw_val and mavw_val < mavw_prev:
        return "SHORT", round(conf, 3)
    elif current_price > mavw_val:
        return "LONG", round(conf * 0.7, 3)
    elif current_price < mavw_val:
        return "SHORT", round(conf * 0.7, 3)
    return "NEUTRAL", 0.0


# ---------------------------------------------------------------------------
# Indicator 2: Range Filter (DonovanWall)
# ---------------------------------------------------------------------------
def calc_range_filter(closes: List[float], highs: List[float], lows: List[float]) -> Tuple[List[float], List[int]]:
    """Calculate Range Filter.

    Returns (filter_values, directions) where direction is 1=LONG, -1=SHORT.
    """
    n = len(closes)
    if n < RF_PERIOD:
        return closes[:], [0] * n

    # Step 1: Calculate smooth average range
    ranges = [highs[i] - lows[i] for i in range(n)]

    # EMA of ranges
    alpha = 2.0 / (RF_PERIOD + 1)
    smooth_range = [0.0] * n
    smooth_range[0] = ranges[0]
    for i in range(1, n):
        smooth_range[i] = alpha * ranges[i] + (1 - alpha) * smooth_range[i - 1]

    # Multiply by range multiplier
    scaled_range = [sr * RF_MULTIPLIER for sr in smooth_range]

    # Step 2: Apply filter
    filt = [0.0] * n
    filt[0] = closes[0]
    direction = [0] * n

    for i in range(1, n):
        if closes[i] > filt[i - 1] + scaled_range[i]:
            filt[i] = closes[i] - scaled_range[i]
        elif closes[i] < filt[i - 1] - scaled_range[i]:
            filt[i] = closes[i] + scaled_range[i]
        else:
            filt[i] = filt[i - 1]

        if filt[i] > filt[i - 1]:
            direction[i] = 1  # LONG
        elif filt[i] < filt[i - 1]:
            direction[i] = -1  # SHORT
        else:
            direction[i] = direction[i - 1]

    return filt, direction


def range_filter_signal(closes: List[float], highs: List[float], lows: List[float]) -> Tuple[str, float]:
    """Return (direction, confidence) based on Range Filter."""
    filt, directions = calc_range_filter(closes, highs, lows)

    curr_dir = directions[-1]
    prev_dir = directions[-2] if len(directions) > 1 else 0

    # Confidence based on how far price is from filter
    if filt[-1] > 0:
        dist = abs(closes[-1] - filt[-1]) / filt[-1] * 100
        conf = min(0.95, 0.5 + dist * 0.1)
    else:
        conf = 0.5

    # Recent direction change = higher confidence
    if curr_dir != prev_dir and curr_dir != 0:
        conf = min(0.95, conf + 0.15)

    if curr_dir == 1:
        return "LONG", round(conf, 3)
    elif curr_dir == -1:
        return "SHORT", round(conf, 3)
    return "NEUTRAL", 0.0


# ---------------------------------------------------------------------------
# Indicator 3: Cyberpunk Value Trend Analyzer
# ---------------------------------------------------------------------------
def calc_cyberpunk(closes: List[float]) -> List[float]:
    """Calculate Cyberpunk Value Trend oscillator.

    Based on normalized price deviation from WMA, scaled 0-100.
    """
    n = len(closes)
    if n < CYBER_LENGTH:
        return [50.0] * n

    # Step 1: Calculate WMA
    wma_vals = _wma(closes, CYBER_LENGTH)

    # Step 2: Price deviation from WMA
    deviation = [0.0] * n
    for i in range(n):
        if wma_vals[i] is not None and wma_vals[i] > 0:
            deviation[i] = (closes[i] - wma_vals[i]) / wma_vals[i] * 100
        else:
            deviation[i] = 0.0

    # Step 3: Normalize to 0-100 range using rolling min/max
    lookback = CYBER_LENGTH * 2
    normalized = [50.0] * n
    for i in range(lookback, n):
        window = deviation[i - lookback: i + 1]
        mn = min(window)
        mx = max(window)
        rng = mx - mn
        if rng > 0:
            normalized[i] = (deviation[i] - mn) / rng * 100
        else:
            normalized[i] = 50.0

    return normalized


def cyberpunk_signal(closes: List[float]) -> Tuple[str, float]:
    """Return (direction, confidence) based on Cyberpunk analyzer.

    BUY when oscillator crosses above entry_level (30) from below.
    SELL when oscillator crosses below exit_level (75) from above.
    """
    cyber = calc_cyberpunk(closes)
    if len(cyber) < 3:
        return "NEUTRAL", 0.0

    curr = cyber[-1]
    prev = cyber[-2]

    # Determine signal based on level crossings and current zone
    if curr > CYBER_EXIT_LEVEL:
        # In overbought zone
        if prev > curr:  # Turning down from overbought
            conf = min(0.95, 0.6 + (curr - CYBER_EXIT_LEVEL) * 0.005)
            return "SHORT", round(conf, 3)
        else:
            return "LONG", 0.55  # Still bullish momentum
    elif curr < CYBER_ENTRY_LEVEL:
        # In oversold zone
        if prev < curr:  # Turning up from oversold
            conf = min(0.95, 0.6 + (CYBER_ENTRY_LEVEL - curr) * 0.01)
            return "LONG", round(conf, 3)
        else:
            return "SHORT", 0.55  # Still bearish momentum
    else:
        # Middle zone — use slope
        if curr > prev and curr > 50:
            return "LONG", 0.5
        elif curr < prev and curr < 50:
            return "SHORT", 0.5
        return "NEUTRAL", 0.0


# ---------------------------------------------------------------------------
# Indicator 4: Volume Confirmation
# ---------------------------------------------------------------------------
def volume_signal(volumes: List[float]) -> Tuple[str, float]:
    """Return (confirmed, spike_ratio) based on volume analysis.

    Checks if current volume is a spike relative to 20-period SMA.
    Returns direction="CONFIRM" if volume spike, "WEAK" otherwise.
    """
    if len(volumes) < VOL_SMA_PERIOD:
        return "WEAK", 0.0

    sma = sum(volumes[-VOL_SMA_PERIOD:]) / VOL_SMA_PERIOD
    current = volumes[-1]

    if sma > 0:
        ratio = current / sma
    else:
        ratio = 1.0

    if ratio >= VOL_SPIKE_MULT:
        return "CONFIRM", round(min(0.95, 0.5 + (ratio - 1) * 0.2), 3)
    elif ratio >= 1.2:
        return "MODERATE", round(0.5, 3)
    else:
        return "WEAK", round(max(0.2, ratio * 0.4), 3)


# ---------------------------------------------------------------------------
# Combined Signal Logic
# ---------------------------------------------------------------------------
def analyze_symbol(symbol: str) -> Optional[dict]:
    """Run all 4 indicators on a symbol and combine into consensus."""
    try:
        candles = fetch_klines(symbol)
    except Exception as e:
        print(f"  [SKIP] {symbol}: {e}")
        return None

    if len(candles) < 100:
        return None

    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    volumes = [c["volume"] for c in candles]

    # Run each indicator
    mav_dir, mav_conf = mavilimw_signal(closes)
    rf_dir, rf_conf = range_filter_signal(closes, highs, lows)
    cyber_dir, cyber_conf = cyberpunk_signal(closes)
    vol_status, vol_conf = volume_signal(volumes)

    # Count agreements
    directional_signals = [
        ("MavilimW", mav_dir, mav_conf),
        ("RangeFilter", rf_dir, rf_conf),
        ("Cyberpunk", cyber_dir, cyber_conf),
    ]

    long_count = sum(1 for _, d, _ in directional_signals if d == "LONG")
    short_count = sum(1 for _, d, _ in directional_signals if d == "SHORT")

    # Determine consensus direction
    if long_count >= 2:
        consensus = "LONG"
        agree_count = long_count
    elif short_count >= 2:
        consensus = "SHORT"
        agree_count = short_count
    else:
        consensus = "NEUTRAL"
        agree_count = max(long_count, short_count)

    # Volume confirmation bonus
    vol_bonus = 0.10 if vol_status == "CONFIRM" else (0.05 if vol_status == "MODERATE" else 0.0)

    # Calculate combined confidence
    agreeing_confs = [c for _, d, c in directional_signals if d == consensus]
    if agreeing_confs:
        avg_conf = sum(agreeing_confs) / len(agreeing_confs)
    else:
        avg_conf = 0.0

    # Scale confidence by agreement level
    if agree_count == 3:
        combined_conf = min(0.98, avg_conf + 0.15 + vol_bonus)
        signal_tier = "SUPER"
    elif agree_count == 2:
        combined_conf = min(0.90, avg_conf + 0.05 + vol_bonus)
        signal_tier = "STRONG"
    else:
        combined_conf = avg_conf * 0.5
        signal_tier = "WEAK"

    if consensus == "NEUTRAL":
        combined_conf = 0.0
        signal_tier = "NONE"

    # Calculate TP/SL based on ATR
    atr_values = []
    for i in range(1, min(15, len(candles))):
        tr = max(
            highs[-i] - lows[-i],
            abs(highs[-i] - closes[-i - 1]),
            abs(lows[-i] - closes[-i - 1]),
        )
        atr_values.append(tr)
    atr = sum(atr_values) / len(atr_values) if atr_values else closes[-1] * 0.02

    current_price = closes[-1]
    if consensus == "LONG":
        tp = round(current_price + atr * 2.5, 6)
        sl = round(current_price - atr * 1.5, 6)
    elif consensus == "SHORT":
        tp = round(current_price - atr * 2.5, 6)
        sl = round(current_price + atr * 1.5, 6)
    else:
        tp = 0
        sl = 0

    return {
        "symbol": symbol,
        "direction": consensus,
        "confidence": round(combined_conf, 3),
        "signal_tier": signal_tier,
        "entry_price": current_price,
        "take_profit": tp,
        "stop_loss": sl,
        "strategy": f"chatgpt_combined_v1 ({signal_tier.lower()})",
        "generated_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "indicators": {
            "mavilimw": {"direction": mav_dir, "confidence": mav_conf},
            "range_filter": {"direction": rf_dir, "confidence": rf_conf},
            "cyberpunk": {"direction": cyber_dir, "confidence": cyber_conf},
            "volume": {"status": vol_status, "confidence": vol_conf},
        },
        "agreement_count": agree_count,
        "volume_confirmed": vol_status in ("CONFIRM", "MODERATE"),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run() -> dict:
    """Run the combined strategy across all symbols."""
    print(f"\n{'=' * 70}")
    print(f"  CHATGPT COMBINED STRATEGY v1")
    print(f"  MavilimW + Range Filter + Cyberpunk Analyzer + Volume")
    print(f"  Interval: {INTERVAL} | Symbols: {len(SYMBOLS)}")
    print(f"{'=' * 70}\n")

    signals = []
    for sym in SYMBOLS:
        result = analyze_symbol(sym)
        if result and result["direction"] != "NEUTRAL":
            signals.append(result)
            tier_icon = {"SUPER": "***", "STRONG": "**", "WEAK": "*"}.get(result["signal_tier"], "")
            print(
                f"  {result['symbol']:12s} {result['direction']:6s} "
                f"conf={result['confidence']:.3f} "
                f"tier={result['signal_tier']:6s} {tier_icon}"
            )
            for name, ind in result["indicators"].items():
                d = ind.get("direction", ind.get("status", "?"))
                c = ind.get("confidence", 0)
                print(f"    {name:15s}: {d:8s} ({c:.3f})")
            print()
        elif result:
            print(f"  {sym:12s} NEUTRAL (no consensus)")

    # Sort by confidence descending
    signals.sort(key=lambda s: (
        {"SUPER": 3, "STRONG": 2, "WEAK": 1}.get(s["signal_tier"], 0),
        s["confidence"],
    ), reverse=True)

    now_iso = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    output = {
        "generated_at": now_iso,
        "strategy": "chatgpt_combined_v1",
        "description": "MavilimW + Range Filter + Cyberpunk Analyzer + Volume consensus",
        "source_video": "I gave chatgpt 4.5 every free tradingview indicator... The Strategy it Built was Insane",
        "interval": INTERVAL,
        "symbols_scanned": len(SYMBOLS),
        "active_signals": len(signals),
        "active_picks": signals,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")

    print(f"\n{'=' * 70}")
    print(f"  RESULTS: {len(signals)} signals from {len(SYMBOLS)} symbols")
    if signals:
        print(f"\n  {'Symbol':12s} {'Dir':6s} {'Conf':>6s} {'Tier':6s} {'Entry':>12s} {'TP':>12s} {'SL':>12s}")
        print(f"  {'-' * 12} {'-' * 6} {'-' * 6} {'-' * 6} {'-' * 12} {'-' * 12} {'-' * 12}")
        for s in signals:
            print(
                f"  {s['symbol']:12s} {s['direction']:6s} "
                f"{s['confidence']:>6.3f} {s['signal_tier']:6s} "
                f"{s['entry_price']:>12.4f} {s['take_profit']:>12.4f} {s['stop_loss']:>12.4f}"
            )
    print(f"\n  Output: {OUTPUT_PATH}")
    print(f"{'=' * 70}\n")

    return output


if __name__ == "__main__":
    run()
