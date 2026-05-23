"""
HoffmanIRBEmaAngle - Baby Strat
================================

Created by: Claude AI
Date: 2026-03-05

Source: Rob Hoffman's Inventory Retracement Bar (IRB) system
  Combined with EMA(20) slope angle confirmation and higher-TF EMA filter.

Symbols: BTCUSDT, DOGEUSDT, LTCUSDT, SOLUSDT, XRPUSDT
  (mapped from Coinbase perps: BTCUSDC.P, DOGEUSDC.P, LTCUSDC.P, SOLUSDC.P, XRPUSDC.P)

Strategy Logic:
  1. IRB Detection (from Pine Script UCS_Rob Hoffman_Inventory Retracement Bar):
     - Inventory Retracement % = 45%
     - Range = |high - low|, Body = |close - open|
     - Range Verification: body < 45% of range (small body = retracement bar)
     - Bearish IRB (red down arrow): RV true, high > upper_retrace, close < upper_retrace, open < upper_retrace
     - Bullish IRB (green up arrow): RV true, low < lower_retrace, close > lower_retrace, open > lower_retrace

  2. EMA(20) on close, same timeframe (15min):
     - "45-degree angle" = EMA slope steep enough (> threshold per bar)
     - Rising EMA = uptrend confirmation
     - Falling EMA = downtrend confirmation

  3. Higher-timeframe EMA(20) for trend alignment (1H for 15min chart)

  4. Entry Rules (contrarian IRB + trend confirmation):
     - BUY:  EMA(20) rising at 45° angle + bearish IRB (red down) = buy the dip in uptrend
             + Higher TF EMA also rising
     - SELL: EMA(20) falling at 45° angle + bullish IRB (green up) = sell the rally in downtrend
             + Higher TF EMA also falling

  5. Hold time variants: 1hr, 2hr, 4hr max hold
     - TP: 1.5x ATR(14)
     - SL: 1x ATR(14)
     - Time stop: exit at max hold regardless

Why it works:
  - IRB detects where institutions retrace inventory (temporary counter-trend bars)
  - EMA angle confirms strong trend momentum
  - Buying bearish IRBs in uptrends = buying institutional dips
  - Selling bullish IRBs in downtrends = selling institutional bounces
  - Higher TF filter prevents counter-trend entries
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import math

import numpy as np
import pandas as pd


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


NAME = "hoffman_irb_ema_angle"
DESCRIPTION = "Hoffman IRB + EMA(20) 45° angle + higher-TF EMA confirmation"

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]

IRB_RETRACE_PCT = 45  # Inventory Retracement percentage


# ── Indicators ─────────────────────────────────────────────────────

def _ema(series, period):
    """EMA as numpy array."""
    if len(series) < period:
        return np.full(len(series), np.nan)
    k = 2 / (period + 1)
    result = np.empty(len(series))
    result[:period - 1] = np.nan
    result[period - 1] = np.mean(series[:period])
    for i in range(period, len(series)):
        result[i] = series[i] * k + result[i - 1] * (1 - k)
    return result


def _atr(high, low, close, period=14):
    """ATR as numpy array."""
    n = len(close)
    tr = np.empty(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    atr = np.empty(n)
    atr[:period - 1] = np.nan
    atr[period - 1] = np.mean(tr[:period])
    for i in range(period, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def _detect_irb(open_arr, high, low, close, retrace_pct=45):
    """
    Detect Hoffman Inventory Retracement Bars.

    Returns (bearish_irb, bullish_irb) boolean arrays.
    - bearish_irb (red down arrow / "Long Bar"): wick above, close below retracement
    - bullish_irb (green up arrow / "Short Bar"): wick below, close above retracement
    """
    n = len(close)
    c = retrace_pct / 100.0

    candle_range = np.abs(high - low)
    candle_body = np.abs(close - open_arr)

    # Range verification: small body relative to range
    rv = candle_body < c * candle_range

    # Retracement levels
    x = low + c * candle_range   # lower retracement
    y = high - c * candle_range  # upper retracement

    # Bearish IRB (sl): high punched above upper retrace, but close & open stayed below
    bearish = rv & (high > y) & (close < y) & (open_arr < y)

    # Bullish IRB (ss): low punched below lower retrace, but close & open stayed above
    bullish = rv & (low < x) & (close > x) & (open_arr > x)

    return bearish, bullish


def _ema_slope_degrees(ema_vals, lookback=4):
    """
    Approximate EMA "angle" in degrees using slope over lookback bars.
    Normalized by price level so it's comparable across symbols.

    Returns array of angles in degrees. Positive = rising, negative = falling.
    """
    n = len(ema_vals)
    angles = np.full(n, np.nan)
    for i in range(lookback, n):
        if np.isnan(ema_vals[i]) or np.isnan(ema_vals[i - lookback]):
            continue
        if ema_vals[i - lookback] == 0:
            continue
        # Slope as percentage change per bar
        pct_per_bar = (ema_vals[i] - ema_vals[i - lookback]) / ema_vals[i - lookback] / lookback
        # Convert to approximate degrees (atan of pct * scale_factor)
        # Scale factor makes typical crypto moves map to meaningful angles
        # 0.1% per bar ≈ 45° for 15min crypto
        angles[i] = math.degrees(math.atan(pct_per_bar * 1000))
    return angles


def _resample_to_higher_tf(open_arr, high, low, close, volume, factor=4):
    """
    Resample bars to a higher timeframe by grouping every `factor` bars.
    15min * 4 = 1H, etc.
    Returns (htf_open, htf_high, htf_low, htf_close, htf_volume) with same length
    (forward-filled to align with lower TF).
    """
    n = len(close)
    n_htf = n // factor
    htf_close = np.full(n, np.nan)

    for i in range(n_htf):
        start = i * factor
        end = start + factor
        htf_c = close[end - 1]
        # Forward-fill: assign HTF value to all bars in this group
        htf_close[start:end] = htf_c

    # Fill remaining bars
    remainder = n % factor
    if remainder > 0:
        htf_close[n - remainder:] = close[-1]

    return htf_close


# ── Signal Generator ──────────────────────────────────────────────

def generate_signals(data: pd.DataFrame, symbol: str,
                     max_hold_hours: int = 4) -> List[Signal]:
    """
    Generate Hoffman IRB + EMA angle signals.

    Args:
        data: DataFrame with open, high, low, close, volume (15min bars)
        symbol: Trading symbol
        max_hold_hours: Maximum hold time in hours (1, 2, or 4)
    """
    if len(data) < 100:
        return []

    open_arr = data["open"].values.astype(float)
    high = data["high"].values.astype(float)
    low = data["low"].values.astype(float)
    close = data["close"].values.astype(float)
    volume = data["volume"].values.astype(float)

    # 1. EMA(20) on close — same timeframe (15min)
    ema20 = _ema(close, 20)

    # 2. EMA slope angle
    angles = _ema_slope_degrees(ema20, lookback=4)

    # 3. Higher TF EMA(20) — resample 15min to 1H (factor=4)
    htf_close = _resample_to_higher_tf(open_arr, high, low, close, volume, factor=4)
    htf_ema20 = _ema(htf_close, 20)

    # 4. IRB detection
    bearish_irb, bullish_irb = _detect_irb(open_arr, high, low, close, IRB_RETRACE_PCT)

    # 5. ATR for TP/SL
    atr = _atr(high, low, close, 14)

    # Check last bar
    i = len(close) - 1
    if np.isnan(ema20[i]) or np.isnan(angles[i]) or np.isnan(atr[i]):
        return []
    if np.isnan(htf_ema20[i]):
        return []

    price = close[i]
    atr_now = atr[i]
    angle_now = angles[i]

    # Higher TF trend: compare current HTF EMA to 4 bars ago
    htf_rising = not np.isnan(htf_ema20[i - 4]) and htf_ema20[i] > htf_ema20[i - 4]
    htf_falling = not np.isnan(htf_ema20[i - 4]) and htf_ema20[i] < htf_ema20[i - 4]

    signals = []

    # BUY: EMA rising at ~45° + bearish IRB (red down = buy the dip) + HTF rising
    if bearish_irb[i] and angle_now >= 30 and htf_rising:
        # Confidence based on angle steepness
        angle_conf = min(angle_now / 60, 1.0)
        conf = 0.55 + 0.30 * angle_conf
        tp = price + 1.5 * atr_now
        sl = price - 1.0 * atr_now
        signals.append(Signal(
            symbol=symbol, direction="BUY", confidence=round(conf, 2),
            entry_price=price, take_profit=tp, stop_loss=sl,
            reason=(f"IRB bearish dip-buy | EMA20 angle={angle_now:.0f}° "
                    f"HTF=rising ATR={atr_now:.2f} hold≤{max_hold_hours}h"),
        ))

    # SELL: EMA falling at ~-45° + bullish IRB (green up = sell the rally) + HTF falling
    if bullish_irb[i] and angle_now <= -30 and htf_falling:
        angle_conf = min(abs(angle_now) / 60, 1.0)
        conf = 0.55 + 0.30 * angle_conf
        tp = price - 1.5 * atr_now
        sl = price + 1.0 * atr_now
        signals.append(Signal(
            symbol=symbol, direction="SELL", confidence=round(conf, 2),
            entry_price=price, take_profit=tp, stop_loss=sl,
            reason=(f"IRB bullish rally-sell | EMA20 angle={angle_now:.0f}° "
                    f"HTF=falling ATR={atr_now:.2f} hold≤{max_hold_hours}h"),
        ))

    return signals


# ── CLI Test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Strategy: {NAME}")
    print(f"Description: {DESCRIPTION}")
    print(f"Symbols: {SYMBOLS}")
    print()

    try:
        import requests
        for sym in SYMBOLS:
            # 15min bars, 200 bars
            url = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=15m&limit=200"
            resp = requests.get(url, timeout=10)
            rows = resp.json()
            df = pd.DataFrame(rows, columns=[
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "qav", "trades", "tbbav", "tbqav", "ignore",
            ])
            for c in ["open", "high", "low", "close", "volume"]:
                df[c] = df[c].astype(float)

            for hold in [1, 2, 4]:
                sigs = generate_signals(df, sym, max_hold_hours=hold)
                if sigs:
                    for s in sigs:
                        print(f"  [{hold}h] {s.symbol} {s.direction} conf={s.confidence} "
                              f"entry={s.entry_price:.4f} tp={s.take_profit:.4f} "
                              f"sl={s.stop_loss:.4f} | {s.reason}")
                else:
                    print(f"  [{hold}h] {sym}: no signal")
    except Exception as e:
        print(f"  Test error: {e}")
