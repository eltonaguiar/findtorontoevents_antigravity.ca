"""
Scalp Ensemble Signal Combiner Strategy
-----------------------------------------
Combines 6 independent sub-signals with weighted voting.
Requires at least 5 of 6 to fire (was 3 -- that was far too loose).
Volume and MACD carry 1.5x weight.

Sub-signals:
  1. EMA cross (fast > slow)        weight 1.0
  2. MACD histogram positive         weight 1.5
  3. RSI in momentum zone            weight 1.0
  4. Volume spike                    weight 1.5
  5. Bollinger %B position           weight 1.0
  6. ADX trend strength              weight 1.0

TP: 2.5 ATR | SL: 0.6 ATR  =>  R:R ~4.2:1
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


NAME = "scalp_ensemble_signal_combiner"
DESCRIPTION = "Weighted ensemble: 6 sub-signals, need 5/6 active (vol+MACD weighted 1.5x)"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# ---------- tunables ----------
EMA_FAST = 9
EMA_SLOW = 21
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
RSI_PERIOD = 14
BB_PERIOD = 20
BB_STD = 2.0
ADX_PERIOD = 14
ATR_PERIOD = 14
VOL_SPIKE_MULT = 1.8
ADX_THRESHOLD = 25

# Voting
WEIGHT_EMA = 1.0
WEIGHT_MACD = 1.5
WEIGHT_RSI = 1.0
WEIGHT_VOL = 1.5
WEIGHT_BB = 1.0
WEIGHT_ADX = 1.0
TOTAL_WEIGHT = WEIGHT_EMA + WEIGHT_MACD + WEIGHT_RSI + WEIGHT_VOL + WEIGHT_BB + WEIGHT_ADX
MIN_SCORE_RATIO = 0.80   # need 80%+ of total weight (≈ 5 of 6)

TP_ATR_MULT = 2.5
SL_ATR_MULT = 0.6
CONF_FLOOR = 0.80


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    # Zero out where the other is larger
    plus_dm[plus_dm < minus_dm] = 0
    minus_dm[minus_dm < plus_dm] = 0

    tr_h = (high - low)
    tr_hc = (high - close.shift(1)).abs()
    tr_lc = (low - close.shift(1)).abs()
    tr = pd.concat([tr_h, tr_hc, tr_lc], axis=1).max(axis=1)

    atr_s = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr_s)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr_s)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.rolling(period).mean()
    return adx


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # EMAs
    df["ema_fast"] = df["close"].ewm(span=EMA_FAST, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=EMA_SLOW, adjust=False).mean()

    # MACD
    ema_f = df["close"].ewm(span=MACD_FAST, adjust=False).mean()
    ema_s = df["close"].ewm(span=MACD_SLOW, adjust=False).mean()
    df["macd_line"] = ema_f - ema_s
    df["macd_signal"] = df["macd_line"].ewm(span=MACD_SIGNAL, adjust=False).mean()
    df["macd_hist"] = df["macd_line"] - df["macd_signal"]

    # RSI
    df["rsi"] = _rsi(df["close"], RSI_PERIOD)

    # Bollinger Bands
    df["bb_mid"] = df["close"].rolling(BB_PERIOD).mean()
    bb_std = df["close"].rolling(BB_PERIOD).std()
    df["bb_upper"] = df["bb_mid"] + BB_STD * bb_std
    df["bb_lower"] = df["bb_mid"] - BB_STD * bb_std
    bb_range = (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
    df["bb_pctb"] = (df["close"] - df["bb_lower"]) / bb_range

    # ADX
    df["adx"] = _adx(df, ADX_PERIOD)

    # ATR
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(ATR_PERIOD).mean()

    # Volume
    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["vol_spike"] = df["volume"] / df["vol_ma"]

    return df


def generate_signals(data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
    df = compute_indicators(data)
    signals: List[Signal] = []

    if len(df) < max(EMA_SLOW, MACD_SLOW, BB_PERIOD, ADX_PERIOD * 2) + 10:
        return signals

    curr = df.iloc[-2]

    if pd.isna(curr["atr"]) or curr["atr"] <= 0:
        return signals

    atr = curr["atr"]
    price = curr["close"]

    # ===================== LONG sub-signals =====================
    long_score = 0.0
    active_long = []

    # S1 - EMA cross
    if curr["ema_fast"] > curr["ema_slow"]:
        long_score += WEIGHT_EMA
        active_long.append("EMA")

    # S2 - MACD histogram positive and rising
    if curr["macd_hist"] > 0:
        long_score += WEIGHT_MACD
        active_long.append("MACD")

    # S3 - RSI 55-70 (momentum without overbought)
    if 55 <= curr["rsi"] <= 70:
        long_score += WEIGHT_RSI
        active_long.append("RSI")

    # S4 - Volume spike
    if curr["vol_spike"] >= VOL_SPIKE_MULT:
        long_score += WEIGHT_VOL
        active_long.append("VOL")

    # S5 - BB %B between 0.5 and 0.85 (above mid, not at extreme)
    if 0.5 <= curr["bb_pctb"] <= 0.85:
        long_score += WEIGHT_BB
        active_long.append("BB")

    # S6 - ADX trend strength
    if curr["adx"] >= ADX_THRESHOLD:
        long_score += WEIGHT_ADX
        active_long.append("ADX")

    if long_score / TOTAL_WEIGHT >= MIN_SCORE_RATIO:
        conf = 0.78 + 0.15 * (long_score / TOTAL_WEIGHT)
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
                    f"Ensemble LONG: {len(active_long)}/6 active "
                    f"[{','.join(active_long)}], "
                    f"score={long_score:.1f}/{TOTAL_WEIGHT:.1f}"
                ),
            ))

    # ===================== SHORT sub-signals =====================
    short_score = 0.0
    active_short = []

    if curr["ema_fast"] < curr["ema_slow"]:
        short_score += WEIGHT_EMA
        active_short.append("EMA")

    if curr["macd_hist"] < 0:
        short_score += WEIGHT_MACD
        active_short.append("MACD")

    if 30 <= curr["rsi"] <= 45:
        short_score += WEIGHT_RSI
        active_short.append("RSI")

    if curr["vol_spike"] >= VOL_SPIKE_MULT:
        short_score += WEIGHT_VOL
        active_short.append("VOL")

    if 0.15 <= curr["bb_pctb"] <= 0.5:
        short_score += WEIGHT_BB
        active_short.append("BB")

    if curr["adx"] >= ADX_THRESHOLD:
        short_score += WEIGHT_ADX
        active_short.append("ADX")

    if short_score / TOTAL_WEIGHT >= MIN_SCORE_RATIO:
        conf = 0.78 + 0.15 * (short_score / TOTAL_WEIGHT)
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
                    f"Ensemble SHORT: {len(active_short)}/6 active "
                    f"[{','.join(active_short)}], "
                    f"score={short_score:.1f}/{TOTAL_WEIGHT:.1f}"
                ),
            ))

    return signals
