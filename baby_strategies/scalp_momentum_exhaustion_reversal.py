"""
Scalp Momentum Exhaustion Reversal Strategy
----------------------------------------------
Counter-trend reversal that waits for EXTREME exhaustion signals
before fading a move.  Requires 4 of 5 exhaustion conditions PLUS
a mandatory consecutive-bars filter (3+ bars in one direction).

This is the ONLY strategy that trades counter-trend, but it does so
only at genuine exhaustion points where mean-reversion is near-certain.

TP: 1.0 ATR (tight -- mean reversion target, not trend continuation)
SL: 0.5 ATR (very tight -- if it doesn't snap back fast, we're wrong)
=> R:R 2.0:1
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


NAME = "scalp_momentum_exhaustion_reversal"
DESCRIPTION = "Exhaustion reversal: 4/5 conditions + 3-bar consecutive run + volume climax (ultra selective)"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# ---------- tunables ----------
RSI_PERIOD = 14
RSI_OB = 80          # extreme overbought (not 70)
RSI_OS = 20          # extreme oversold (not 30)

BB_PERIOD = 20
BB_STD = 2.0

ATR_PERIOD = 14
VOL_SPIKE_MULT = 2.0    # volume climax required

CONSEC_BARS_MIN = 3      # minimum consecutive same-direction bars
MIN_EXHAUSTION = 4       # need 4 of 5 conditions

TP_ATR_MULT = 1.0        # tight TP -- mean reversion target
SL_ATR_MULT = 0.5        # very tight SL
CONF_FLOOR = 0.80


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # RSI
    df["rsi"] = _rsi(df["close"], RSI_PERIOD)

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

    # Consecutive bars in same direction
    df["bar_dir"] = np.sign(df["close"] - df["open"])
    consec = []
    count = 0
    prev_dir = 0
    for d in df["bar_dir"]:
        if d == prev_dir and d != 0:
            count += 1
        else:
            count = 1
        consec.append(count)
        prev_dir = d
    df["consec_bars"] = consec

    # Price rate of change (for deceleration check)
    df["roc_1"] = df["close"].pct_change(1)
    df["roc_3"] = df["close"].pct_change(3)

    # Wick ratio (rejection candle detection)
    body = (df["close"] - df["open"]).abs()
    full_range = (df["high"] - df["low"]).replace(0, np.nan)
    df["body_ratio"] = body / full_range
    # Upper wick for bearish rejection
    df["upper_wick"] = (df["high"] - df[["close", "open"]].max(axis=1)) / full_range
    # Lower wick for bullish rejection
    df["lower_wick"] = (df[["close", "open"]].min(axis=1) - df["low"]) / full_range

    return df


def generate_signals(data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
    df = compute_indicators(data)
    signals: List[Signal] = []

    if len(df) < BB_PERIOD + 20:
        return signals

    curr = df.iloc[-2]
    prev = df.iloc[-3]

    if pd.isna(curr["atr"]) or curr["atr"] <= 0:
        return signals

    atr = curr["atr"]
    price = curr["close"]

    # ===================== BEARISH EXHAUSTION (go SHORT) =====================
    # MANDATORY: 3+ consecutive up bars
    consec_up = curr["consec_bars"] >= CONSEC_BARS_MIN and curr["bar_dir"] > 0

    if consec_up:
        exhaust_count = 0
        details = []

        # E1 - RSI extreme overbought
        if curr["rsi"] >= RSI_OB:
            exhaust_count += 1
            details.append(f"RSI={curr['rsi']:.0f}")

        # E2 - Price at or above upper Bollinger Band
        if curr["close"] >= curr["bb_upper"]:
            exhaust_count += 1
            details.append("above_BB_upper")

        # E3 - Volume climax (spike on exhaustion bar)
        if curr["vol_spike"] >= VOL_SPIKE_MULT:
            exhaust_count += 1
            details.append(f"vol={curr['vol_spike']:.1f}x")

        # E4 - Deceleration: ROC_1 < ROC_3 / 3 (momentum fading)
        if abs(curr["roc_1"]) < abs(curr["roc_3"]) / 3:
            exhaust_count += 1
            details.append("deceleration")

        # E5 - Rejection wick (long upper wick > 40% of bar)
        if curr["upper_wick"] > 0.40:
            exhaust_count += 1
            details.append(f"wick={curr['upper_wick']:.0%}")

        if exhaust_count >= MIN_EXHAUSTION:
            conf = 0.80 + 0.04 * (exhaust_count - MIN_EXHAUSTION)
            if curr["consec_bars"] >= 5:
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
                        f"Exhaustion SHORT: {exhaust_count}/5 signals "
                        f"[{', '.join(details)}], "
                        f"consec_up={curr['consec_bars']:.0f}"
                    ),
                ))

    # ===================== BULLISH EXHAUSTION (go LONG) =====================
    consec_down = curr["consec_bars"] >= CONSEC_BARS_MIN and curr["bar_dir"] < 0

    if consec_down:
        exhaust_count = 0
        details = []

        if curr["rsi"] <= RSI_OS:
            exhaust_count += 1
            details.append(f"RSI={curr['rsi']:.0f}")

        if curr["close"] <= curr["bb_lower"]:
            exhaust_count += 1
            details.append("below_BB_lower")

        if curr["vol_spike"] >= VOL_SPIKE_MULT:
            exhaust_count += 1
            details.append(f"vol={curr['vol_spike']:.1f}x")

        if abs(curr["roc_1"]) < abs(curr["roc_3"]) / 3:
            exhaust_count += 1
            details.append("deceleration")

        if curr["lower_wick"] > 0.40:
            exhaust_count += 1
            details.append(f"wick={curr['lower_wick']:.0%}")

        if exhaust_count >= MIN_EXHAUSTION:
            conf = 0.80 + 0.04 * (exhaust_count - MIN_EXHAUSTION)
            if curr["consec_bars"] >= 5:
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
                        f"Exhaustion LONG: {exhaust_count}/5 signals "
                        f"[{', '.join(details)}], "
                        f"consec_down={curr['consec_bars']:.0f}"
                    ),
                ))

    return signals
