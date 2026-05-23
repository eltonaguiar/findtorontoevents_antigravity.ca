"""
Scalp Session Timing Breakout Strategy
-----------------------------------------
Trades ONLY the first 30 minutes of London open (08:00 UTC) and
US open (13:30 UTC) -- the highest-liquidity windows where
institutional order flow creates reliable breakouts.

Requires Asian session range > 1.0 ATR (significant compression),
volume > 2.0x average, ADX > 25, and price breaking the Asian
high/low with momentum.

TP: 3.0 ATR | SL: 0.8 ATR  =>  R:R ~3.75:1
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


NAME = "scalp_session_timing_breakout"
DESCRIPTION = "Session breakout: London/US first 30min + Asian compression + vol 2x + ADX>25 (5/5)"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# ---------- tunables ----------
# Asian session: 00:00-08:00 UTC (hours 0-7)
ASIAN_START_HOUR = 0
ASIAN_END_HOUR = 8

# London open window: 08:00-08:30 UTC
LONDON_START = 8
LONDON_END_MIN = 30

# US open window: 13:30-14:00 UTC
US_START_HOUR = 13
US_START_MIN = 30
US_END_HOUR = 14

ATR_PERIOD = 14
ADX_PERIOD = 14
ADX_THRESHOLD = 25
VOL_SPIKE_MULT = 2.0
ASIAN_RANGE_MIN_ATR = 1.0   # Asian range must be >= 1.0 ATR

EMA_TREND = 50               # overall trend filter

TP_ATR_MULT = 3.0
SL_ATR_MULT = 0.8
CONF_FLOOR = 0.80


def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    plus_dm[plus_dm < minus_dm] = 0
    minus_dm[minus_dm < plus_dm] = 0

    tr_h = high - low
    tr_hc = (high - close.shift(1)).abs()
    tr_lc = (low - close.shift(1)).abs()
    tr = pd.concat([tr_h, tr_hc, tr_lc], axis=1).max(axis=1)

    atr_s = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr_s)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr_s)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.rolling(period).mean()


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # ATR
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(ATR_PERIOD).mean()

    # ADX
    df["adx"] = _adx(df, ADX_PERIOD)

    # EMA trend
    df["ema_trend"] = df["close"].ewm(span=EMA_TREND, adjust=False).mean()

    # Volume
    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["vol_spike"] = df["volume"] / df["vol_ma"]

    # Extract hour/minute if timestamp column exists
    if "timestamp" in df.columns:
        ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df["hour"] = ts.dt.hour
        df["minute"] = ts.dt.minute
    elif isinstance(df.index, pd.DatetimeIndex):
        df["hour"] = df.index.hour
        df["minute"] = df.index.minute
    else:
        # Fallback: create synthetic hours based on bar count
        # This allows backtesting without real timestamps
        total_bars = len(df)
        df["hour"] = [(i // 60) % 24 for i in range(total_bars)]
        df["minute"] = [i % 60 for i in range(total_bars)]

    # Asian session range (rolling computation)
    # For each bar, compute the high-low range of the last ~480 1-min bars (8 hours)
    asian_bars = 480  # 8 hours * 60 min
    if len(df) > asian_bars:
        df["asian_high"] = df["high"].rolling(asian_bars).max()
        df["asian_low"] = df["low"].rolling(asian_bars).min()
        df["asian_range"] = df["asian_high"] - df["asian_low"]
    else:
        df["asian_high"] = df["high"].rolling(min(len(df), 100)).max()
        df["asian_low"] = df["low"].rolling(min(len(df), 100)).min()
        df["asian_range"] = df["asian_high"] - df["asian_low"]

    return df


def _in_session_window(hour: int, minute: int) -> str:
    """Return 'london', 'us', or '' depending on whether we're in a valid window."""
    # London: 08:00-08:30
    if hour == LONDON_START and minute < LONDON_END_MIN:
        return "london"
    # US: 13:30-14:00
    if hour == US_START_HOUR and minute >= US_START_MIN:
        return "us"
    if hour == US_END_HOUR and minute == 0:
        return "us"
    return ""


def generate_signals(data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
    df = compute_indicators(data)
    signals: List[Signal] = []

    if len(df) < EMA_TREND + 20:
        return signals

    curr = df.iloc[-2]

    if pd.isna(curr["atr"]) or curr["atr"] <= 0:
        return signals

    atr = curr["atr"]
    price = curr["close"]

    # ---- SESSION GATE ----
    session = _in_session_window(int(curr["hour"]), int(curr["minute"]))
    if not session:
        return signals  # outside trading windows

    # ---- C1: Asian range compression (significant, not tiny) ----
    if pd.isna(curr["asian_range"]) or curr["asian_range"] < ASIAN_RANGE_MIN_ATR * atr:
        return signals

    # ---- C2: ADX trend strength ----
    if pd.isna(curr["adx"]) or curr["adx"] < ADX_THRESHOLD:
        return signals

    # ---- C3: Volume spike ----
    if curr["vol_spike"] < VOL_SPIKE_MULT:
        return signals

    # ---- C4 + C5: Breakout direction + trend alignment ----
    asian_high = curr["asian_high"]
    asian_low = curr["asian_low"]

    # LONG: price breaking above Asian high + above EMA trend
    if price > asian_high and price > curr["ema_trend"]:
        conf = 0.82
        if curr["vol_spike"] > 2.5:
            conf += 0.04
        if curr["adx"] > 30:
            conf += 0.04
        if curr["asian_range"] > 1.5 * atr:
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
                    f"Session LONG ({session}): broke Asian high {asian_high:.2f}, "
                    f"ADX={curr['adx']:.0f}, vol={curr['vol_spike']:.1f}x, "
                    f"range={curr['asian_range']/atr:.1f}ATR"
                ),
            ))

    # SHORT: price breaking below Asian low + below EMA trend
    elif price < asian_low and price < curr["ema_trend"]:
        conf = 0.82
        if curr["vol_spike"] > 2.5:
            conf += 0.04
        if curr["adx"] > 30:
            conf += 0.04
        if curr["asian_range"] > 1.5 * atr:
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
                    f"Session SHORT ({session}): broke Asian low {asian_low:.2f}, "
                    f"ADX={curr['adx']:.0f}, vol={curr['vol_spike']:.1f}x, "
                    f"range={curr['asian_range']/atr:.1f}ATR"
                ),
            ))

    return signals
