"""
Scalp Price Action Pattern Strategy
--------------------------------------
Only two high-probability patterns: engulfing and pin bar (dropped
noisy inside-bar and 3-bar patterns).

EVERY pattern must occur AT a key level (EMA proximity AND Bollinger
Band proximity).  Volume must be > 1.5x average.

TP: 2.0 ATR | SL: 0.6 ATR  =>  R:R ~3.3:1
Confidence floor: 0.80
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


NAME = "scalp_price_action_pattern"
DESCRIPTION = "Price action: engulfing/pin bar AT key level (EMA+BB proximity) + vol 1.5x (all required)"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# ---------- tunables ----------
EMA_FAST = 9
EMA_SLOW = 21
EMA_TREND = 50

BB_PERIOD = 20
BB_STD = 2.0
BB_PROXIMITY_ATR = 0.5     # must be within 0.5 ATR of a BB band

EMA_PROXIMITY_ATR = 0.6    # must be within 0.6 ATR of EMA

ATR_PERIOD = 14
VOL_SPIKE_MULT = 1.5

# Pin bar thresholds
PIN_WICK_MIN = 0.60         # wick must be >= 60% of total range
PIN_BODY_MAX = 0.25         # body must be <= 25% of total range

TP_ATR_MULT = 2.0
SL_ATR_MULT = 0.6
CONF_FLOOR = 0.80


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # EMAs
    df["ema_fast"] = df["close"].ewm(span=EMA_FAST, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=EMA_SLOW, adjust=False).mean()
    df["ema_trend"] = df["close"].ewm(span=EMA_TREND, adjust=False).mean()

    # Bollinger Bands
    df["bb_mid"] = df["close"].rolling(BB_PERIOD).mean()
    bb_std = df["close"].rolling(BB_PERIOD).std()
    df["bb_upper"] = df["bb_mid"] + BB_STD * bb_std
    df["bb_lower"] = df["bb_mid"] - BB_STD * bb_std

    # ATR
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(ATR_PERIOD).mean()

    # Volume
    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["vol_spike"] = df["volume"] / df["vol_ma"]

    # Candle components
    df["body"] = (df["close"] - df["open"]).abs()
    df["full_range"] = (df["high"] - df["low"]).replace(0, np.nan)
    df["body_ratio"] = df["body"] / df["full_range"]
    df["upper_wick"] = df["high"] - df[["close", "open"]].max(axis=1)
    df["lower_wick"] = df[["close", "open"]].min(axis=1) - df["low"]
    df["upper_wick_ratio"] = df["upper_wick"] / df["full_range"]
    df["lower_wick_ratio"] = df["lower_wick"] / df["full_range"]

    return df


def _is_bullish_engulfing(curr, prev) -> bool:
    """Current bar fully engulfs previous bar's body, bullish close."""
    prev_body_low = min(prev["open"], prev["close"])
    prev_body_high = max(prev["open"], prev["close"])
    curr_open = curr["open"]
    curr_close = curr["close"]
    return (
        curr_close > curr_open  # bullish bar
        and prev["close"] < prev["open"]  # previous was bearish
        and curr_open <= prev_body_low
        and curr_close >= prev_body_high
        and curr["body_ratio"] > 0.50  # substantial body
    )


def _is_bearish_engulfing(curr, prev) -> bool:
    prev_body_low = min(prev["open"], prev["close"])
    prev_body_high = max(prev["open"], prev["close"])
    curr_open = curr["open"]
    curr_close = curr["close"]
    return (
        curr_close < curr_open  # bearish bar
        and prev["close"] > prev["open"]  # previous was bullish
        and curr_open >= prev_body_high
        and curr_close <= prev_body_low
        and curr["body_ratio"] > 0.50
    )


def _is_bullish_pin_bar(curr) -> bool:
    """Long lower wick, tiny body at top -- hammer pattern."""
    return (
        curr["lower_wick_ratio"] >= PIN_WICK_MIN
        and curr["body_ratio"] <= PIN_BODY_MAX
    )


def _is_bearish_pin_bar(curr) -> bool:
    """Long upper wick, tiny body at bottom -- shooting star."""
    return (
        curr["upper_wick_ratio"] >= PIN_WICK_MIN
        and curr["body_ratio"] <= PIN_BODY_MAX
    )


def generate_signals(data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
    df = compute_indicators(data)
    signals: List[Signal] = []

    if len(df) < EMA_TREND + 10:
        return signals

    curr = df.iloc[-2]
    prev = df.iloc[-3]

    if pd.isna(curr["atr"]) or curr["atr"] <= 0:
        return signals

    atr = curr["atr"]
    price = curr["close"]

    # ---- KEY LEVEL CHECKS (both required) ----
    # EMA proximity: price within EMA_PROXIMITY_ATR of any EMA
    near_ema = (
        abs(price - curr["ema_fast"]) < EMA_PROXIMITY_ATR * atr
        or abs(price - curr["ema_slow"]) < EMA_PROXIMITY_ATR * atr
        or abs(price - curr["ema_trend"]) < EMA_PROXIMITY_ATR * atr
    )

    # BB proximity: price within BB_PROXIMITY_ATR of upper or lower band
    near_bb_lower = abs(price - curr["bb_lower"]) < BB_PROXIMITY_ATR * atr
    near_bb_upper = abs(price - curr["bb_upper"]) < BB_PROXIMITY_ATR * atr
    near_bb = near_bb_lower or near_bb_upper

    if not (near_ema and near_bb):
        return signals  # NOT at a key level -- skip

    # ---- VOLUME GATE ----
    if curr["vol_spike"] < VOL_SPIKE_MULT:
        return signals

    # ---- TREND FILTER ----
    trend_up = curr["ema_fast"] > curr["ema_slow"] > curr["ema_trend"]
    trend_down = curr["ema_fast"] < curr["ema_slow"] < curr["ema_trend"]

    # ===================== BULLISH PATTERNS =====================
    bull_engulf = _is_bullish_engulfing(curr, prev)
    bull_pin = _is_bullish_pin_bar(curr)

    if (bull_engulf or bull_pin) and near_bb_lower:
        pattern_name = "engulfing" if bull_engulf else "pin_bar"
        conf = 0.81
        if bull_engulf and bull_pin:
            conf += 0.05  # both patterns = extra conviction
        if trend_up:
            conf += 0.05  # with trend bonus
        if curr["vol_spike"] > 2.0:
            conf += 0.03
        conf = min(conf, 0.97)

        if conf >= CONF_FLOOR:
            signals.append(Signal(
                symbol=symbol,
                direction="LONG",
                confidence=round(conf, 3),
                entry_price=round(price, 6),
                take_profit=round(price + TP_ATR_MULT * atr, 6),
                stop_loss=round(price - SL_ATR_MULT * atr, 6),
                reason=(
                    f"PA LONG: {pattern_name} at BB_lower+EMA, "
                    f"vol={curr['vol_spike']:.1f}x, "
                    f"trend={'UP' if trend_up else 'neutral'}"
                ),
            ))

    # ===================== BEARISH PATTERNS =====================
    bear_engulf = _is_bearish_engulfing(curr, prev)
    bear_pin = _is_bearish_pin_bar(curr)

    if (bear_engulf or bear_pin) and near_bb_upper:
        pattern_name = "engulfing" if bear_engulf else "pin_bar"
        conf = 0.81
        if bear_engulf and bear_pin:
            conf += 0.05
        if trend_down:
            conf += 0.05
        if curr["vol_spike"] > 2.0:
            conf += 0.03
        conf = min(conf, 0.97)

        if conf >= CONF_FLOOR:
            signals.append(Signal(
                symbol=symbol,
                direction="SHORT",
                confidence=round(conf, 3),
                entry_price=round(price, 6),
                take_profit=round(price - TP_ATR_MULT * atr, 6),
                stop_loss=round(price + SL_ATR_MULT * atr, 6),
                reason=(
                    f"PA SHORT: {pattern_name} at BB_upper+EMA, "
                    f"vol={curr['vol_spike']:.1f}x, "
                    f"trend={'DOWN' if trend_down else 'neutral'}"
                ),
            ))

    return signals
