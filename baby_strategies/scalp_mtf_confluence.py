"""
Scalp Multi-Timeframe Confluence Strategy
-------------------------------------------
Requires alignment across THREE simulated time-frames built from
a single bar series (15-min trend, 5-min momentum, 1-min entry)
plus RSI in the 55-70 "sweet spot" and a volume spike.

All 5 conditions must agree before a signal fires.

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


NAME = "scalp_mtf_confluence"
DESCRIPTION = "Multi-TF confluence: 15m trend + 5m momentum + 1m cross + RSI sweet-spot + vol spike (5/5)"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# ---------- tunables ----------
# "15-min trend" simulated via longer EMA on 1-min bars
EMA_HTF = 21 * 15        # ~315 bars on 1-min ≈ 21-bar on 15-min
EMA_HTF_SLOPE_LB = 15    # bars to measure HTF EMA slope

# "5-min momentum" simulated via medium EMA
EMA_MTF = 21 * 5         # ~105 bars on 1-min ≈ 21-bar on 5-min
MOMENTUM_LB = 10         # bars to measure momentum direction

# "1-min entry" fast cross
EMA_ENTRY_FAST = 5
EMA_ENTRY_SLOW = 13

# RSI
RSI_PERIOD = 14
RSI_LONG_LOW = 55
RSI_LONG_HIGH = 70
RSI_SHORT_LOW = 30
RSI_SHORT_HIGH = 45

# Volume
VOL_SPIKE_MULT = 2.0

# ATR / Risk
ATR_PERIOD = 14
TP_ATR_MULT = 2.5
SL_ATR_MULT = 0.6
CONF_FLOOR = 0.80


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Higher-TF trend EMA (simulated 15-min)
    df["ema_htf"] = df["close"].ewm(span=EMA_HTF, adjust=False).mean()
    df["ema_htf_slope"] = df["ema_htf"] - df["ema_htf"].shift(EMA_HTF_SLOPE_LB)

    # Mid-TF momentum EMA (simulated 5-min)
    df["ema_mtf"] = df["close"].ewm(span=EMA_MTF, adjust=False).mean()
    df["mtf_momentum"] = df["close"] - df["ema_mtf"]
    df["mtf_mom_slope"] = df["mtf_momentum"] - df["mtf_momentum"].shift(MOMENTUM_LB)

    # Entry-TF fast / slow EMAs (1-min)
    df["ema_entry_fast"] = df["close"].ewm(span=EMA_ENTRY_FAST, adjust=False).mean()
    df["ema_entry_slow"] = df["close"].ewm(span=EMA_ENTRY_SLOW, adjust=False).mean()

    # RSI
    df["rsi"] = _rsi(df["close"], RSI_PERIOD)

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

    if len(df) < EMA_HTF + 20:
        return signals

    curr = df.iloc[-2]
    prev = df.iloc[-3]

    if pd.isna(curr["atr"]) or curr["atr"] <= 0:
        return signals

    atr = curr["atr"]
    price = curr["close"]

    # ===================== LONG =====================
    # C1 - 15-min trend: HTF EMA slope positive
    htf_up = curr["ema_htf_slope"] > 0

    # C2 - 5-min momentum: price above MTF EMA and momentum rising
    mtf_bull = curr["mtf_momentum"] > 0 and curr["mtf_mom_slope"] > 0

    # C3 - 1-min entry: fresh fast-over-slow cross
    entry_cross_long = (
        curr["ema_entry_fast"] > curr["ema_entry_slow"]
        and prev["ema_entry_fast"] <= prev["ema_entry_slow"]
    )

    # C4 - RSI in sweet spot (momentum present, not overbought)
    rsi_ok_long = RSI_LONG_LOW <= curr["rsi"] <= RSI_LONG_HIGH

    # C5 - Volume confirmation
    vol_ok = curr["vol_spike"] >= VOL_SPIKE_MULT

    if all([htf_up, mtf_bull, entry_cross_long, rsi_ok_long, vol_ok]):
        conf = 0.82
        if curr["vol_spike"] > 2.5:
            conf += 0.04
        if curr["rsi"] > 60:
            conf += 0.03
        if curr["mtf_mom_slope"] > 0.001 * price:
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
                    f"MTF LONG: HTF_slope={curr['ema_htf_slope']:.2f}, "
                    f"MTF_mom={curr['mtf_momentum']:.2f}, "
                    f"RSI={curr['rsi']:.1f}, vol={curr['vol_spike']:.1f}x"
                ),
            ))

    # ===================== SHORT =====================
    htf_down = curr["ema_htf_slope"] < 0
    mtf_bear = curr["mtf_momentum"] < 0 and curr["mtf_mom_slope"] < 0
    entry_cross_short = (
        curr["ema_entry_fast"] < curr["ema_entry_slow"]
        and prev["ema_entry_fast"] >= prev["ema_entry_slow"]
    )
    rsi_ok_short = RSI_SHORT_LOW <= curr["rsi"] <= RSI_SHORT_HIGH

    if all([htf_down, mtf_bear, entry_cross_short, rsi_ok_short, vol_ok]):
        conf = 0.82
        if curr["vol_spike"] > 2.5:
            conf += 0.04
        if curr["rsi"] < 40:
            conf += 0.03
        if curr["mtf_mom_slope"] < -0.001 * price:
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
                    f"MTF SHORT: HTF_slope={curr['ema_htf_slope']:.2f}, "
                    f"MTF_mom={curr['mtf_momentum']:.2f}, "
                    f"RSI={curr['rsi']:.1f}, vol={curr['vol_spike']:.1f}x"
                ),
            ))

    return signals
