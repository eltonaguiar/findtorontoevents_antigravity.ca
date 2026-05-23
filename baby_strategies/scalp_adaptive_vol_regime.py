"""
Scalp Adaptive Volatility Regime Strategy
-------------------------------------------
Only trades when ATR percentile is in the 50-85 "sweet spot" --
enough volatility to profit but not so much that stops get blown.

Uses Donchian channel breakout + pullback to EMA + RSI divergence
+ volume confirmation.  Waits for RETEST of the breakout level,
not the initial break (avoids fakeouts).

TP: 2.0 ATR | SL: 0.7 ATR  =>  R:R ~2.9:1
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


NAME = "scalp_adaptive_vol_regime"
DESCRIPTION = "Vol-regime filtered: ATR pctile 50-85 + Donchian retest + EMA pullback + RSI div + volume (5/5)"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# ---------- tunables ----------
ATR_PERIOD = 14
ATR_RANK_LOOKBACK = 100      # rolling window for ATR percentile
ATR_PCTILE_LOW = 50
ATR_PCTILE_HIGH = 85

DONCHIAN_PERIOD = 20
EMA_TREND = 21
RSI_PERIOD = 14
VOL_SPIKE_MULT = 1.5         # moderate vol confirmation

TP_ATR_MULT = 2.0
SL_ATR_MULT = 0.7
CONF_FLOOR = 0.80


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # ATR + percentile rank
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(ATR_PERIOD).mean()
    df["atr_pctile"] = df["atr"].rolling(ATR_RANK_LOOKBACK).apply(
        lambda x: (x.values[-1] > x.values[:-1]).sum() / (len(x) - 1) * 100
        if len(x) > 1 else 50.0,
        raw=False,
    )

    # Donchian channel
    df["dc_high"] = df["high"].rolling(DONCHIAN_PERIOD).max()
    df["dc_low"] = df["low"].rolling(DONCHIAN_PERIOD).min()

    # Track if price PREVIOUSLY broke Donchian (within last 5 bars)
    df["broke_dc_high"] = (df["high"].shift(1).rolling(5).max() >= df["dc_high"].shift(1))
    df["broke_dc_low"] = (df["low"].shift(1).rolling(5).min() <= df["dc_low"].shift(1))

    # Price has now pulled back to EMA (retest)
    df["ema_trend"] = df["close"].ewm(span=EMA_TREND, adjust=False).mean()
    df["near_ema"] = (
        (df["close"] - df["ema_trend"]).abs() / df["atr"]
    )  # distance in ATR units

    # RSI + divergence detection
    df["rsi"] = _rsi(df["close"], RSI_PERIOD)
    # Bullish divergence: price made lower low but RSI made higher low
    df["price_ll"] = df["low"] < df["low"].shift(3)
    df["rsi_hl"] = df["rsi"] > df["rsi"].shift(3)
    df["bull_div"] = df["price_ll"] & df["rsi_hl"]
    # Bearish divergence: price made higher high but RSI made lower high
    df["price_hh"] = df["high"] > df["high"].shift(3)
    df["rsi_lh"] = df["rsi"] < df["rsi"].shift(3)
    df["bear_div"] = df["price_hh"] & df["rsi_lh"]

    # Volume
    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["vol_spike"] = df["volume"] / df["vol_ma"]

    return df


def generate_signals(data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
    df = compute_indicators(data)
    signals: List[Signal] = []

    if len(df) < ATR_RANK_LOOKBACK + 20:
        return signals

    curr = df.iloc[-2]

    if pd.isna(curr["atr"]) or curr["atr"] <= 0:
        return signals

    atr = curr["atr"]
    price = curr["close"]

    # ---- REGIME GATE: must be in volatility sweet spot ----
    if pd.isna(curr["atr_pctile"]):
        return signals
    if not (ATR_PCTILE_LOW <= curr["atr_pctile"] <= ATR_PCTILE_HIGH):
        return signals

    # ===================== LONG =====================
    # C1 - Volatility regime OK (already passed above)
    # C2 - Donchian breakout happened recently (retest setup)
    dc_broke_long = bool(curr["broke_dc_high"])

    # C3 - Price pulled back near EMA (within 0.8 ATR)
    pullback_to_ema_long = curr["near_ema"] < 0.8 and curr["close"] > curr["ema_trend"]

    # C4 - RSI divergence (bullish) or RSI recovering from dip
    rsi_ok_long = bool(curr["bull_div"]) or (40 < curr["rsi"] < 60)

    # C5 - Volume present
    vol_ok = curr["vol_spike"] >= VOL_SPIKE_MULT

    if all([dc_broke_long, pullback_to_ema_long, rsi_ok_long, vol_ok]):
        conf = 0.81
        if curr["bull_div"]:
            conf += 0.05
        if curr["vol_spike"] > 2.0:
            conf += 0.04
        if curr["near_ema"] < 0.3:
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
                    f"VolRegime LONG: ATR_pctile={curr['atr_pctile']:.0f}, "
                    f"DC_retest, EMA_dist={curr['near_ema']:.2f}ATR, "
                    f"RSI={curr['rsi']:.1f}, vol={curr['vol_spike']:.1f}x"
                ),
            ))

    # ===================== SHORT =====================
    dc_broke_short = bool(curr["broke_dc_low"])
    pullback_to_ema_short = curr["near_ema"] < 0.8 and curr["close"] < curr["ema_trend"]
    rsi_ok_short = bool(curr["bear_div"]) or (40 < curr["rsi"] < 60)

    if all([dc_broke_short, pullback_to_ema_short, rsi_ok_short, vol_ok]):
        conf = 0.81
        if curr["bear_div"]:
            conf += 0.05
        if curr["vol_spike"] > 2.0:
            conf += 0.04
        if curr["near_ema"] < 0.3:
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
                    f"VolRegime SHORT: ATR_pctile={curr['atr_pctile']:.0f}, "
                    f"DC_retest, EMA_dist={curr['near_ema']:.2f}ATR, "
                    f"RSI={curr['rsi']:.1f}, vol={curr['vol_spike']:.1f}x"
                ),
            ))

    return signals
