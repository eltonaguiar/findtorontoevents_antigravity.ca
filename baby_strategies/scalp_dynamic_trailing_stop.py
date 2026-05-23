"""
Scalp Dynamic Trailing Stop Strategy
---------------------------------------
Trend-following scalper that requires a STACKED EMA formation
(EMA5 > EMA13 > EMA34) for longs, plus RSI in the 55-70 momentum
window, volume > 1.5x, and ADX > 20 for trend strength.

All 4 conditions must be true.  The "dynamic trailing stop" name
reflects that the SL is placed at EMA13 (a tighter, adaptive level)
rather than a fixed ATR distance -- but we still use ATR for the
initial SL/TP computation.

TP: 2.5 ATR | SL: 0.5 ATR (tight -- EMA stack means strong trend support)
=> R:R ~5.0:1
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


NAME = "scalp_dynamic_trailing_stop"
DESCRIPTION = "Stacked EMA trend: EMA5>13>34 + RSI 55-70 + vol 1.5x + ADX>20 (all 4 required)"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# ---------- tunables ----------
EMA_FAST = 5
EMA_MID = 13
EMA_SLOW = 34

RSI_PERIOD = 14
RSI_LONG_LOW = 60
RSI_LONG_HIGH = 65
RSI_SHORT_LOW = 35
RSI_SHORT_HIGH = 40

ADX_PERIOD = 14
ADX_THRESHOLD = 40

ATR_PERIOD = 14
VOL_SPIKE_MULT = 3.0

TP_ATR_MULT = 2.5
SL_ATR_MULT = 0.5
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

    # Stacked EMAs
    df["ema_fast"] = df["close"].ewm(span=EMA_FAST, adjust=False).mean()
    df["ema_mid"] = df["close"].ewm(span=EMA_MID, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=EMA_SLOW, adjust=False).mean()

    # EMA slopes (for freshness check)
    df["ema_fast_slope"] = df["ema_fast"] - df["ema_fast"].shift(3)
    df["ema_mid_slope"] = df["ema_mid"] - df["ema_mid"].shift(3)

    # RSI
    df["rsi"] = _rsi(df["close"], RSI_PERIOD)

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

    # Price relative to EMA_mid (for trailing stop placement)
    df["dist_to_ema_mid"] = (df["close"] - df["ema_mid"]) / df["atr"]

    return df


def generate_signals(data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
    df = compute_indicators(data)
    signals: List[Signal] = []

    if len(df) < EMA_SLOW + ADX_PERIOD + 10:
        return signals

    curr = df.iloc[-2]
    prev = df.iloc[-3]

    if pd.isna(curr["atr"]) or curr["atr"] <= 0:
        return signals

    atr = curr["atr"]
    price = curr["close"]

    # ===================== LONG =====================
    # C1 - Stacked EMAs: fast > mid > slow
    ema_stacked_long = (
        curr["ema_fast"] > curr["ema_mid"] > curr["ema_slow"]
    )

    # C2 - RSI in momentum zone (not overbought)
    rsi_ok_long = RSI_LONG_LOW <= curr["rsi"] <= RSI_LONG_HIGH

    # C3 - Volume confirmation
    vol_ok = curr["vol_spike"] >= VOL_SPIKE_MULT

    # C4 - ADX trend strength
    adx_ok = not pd.isna(curr["adx"]) and curr["adx"] >= ADX_THRESHOLD

    if all([ema_stacked_long, rsi_ok_long, vol_ok, adx_ok]):
        # Extra quality: EMAs should be actively fanning out
        ema_fanning = curr["ema_fast_slope"] > 0 and curr["ema_mid_slope"] > 0

        conf = 0.81
        if ema_fanning:
            conf += 0.05
        if curr["adx"] > 30:
            conf += 0.04
        if curr["vol_spike"] > 2.0:
            conf += 0.03
        if curr["rsi"] > 60:
            conf += 0.02
        conf = min(conf, 0.97)

        # Use EMA_mid as dynamic SL if it's tighter than fixed ATR SL
        ema_mid_sl = curr["ema_mid"]
        fixed_sl = price - SL_ATR_MULT * atr
        sl = max(ema_mid_sl, fixed_sl)  # tighter of the two

        if conf >= CONF_FLOOR:
            signals.append(Signal(
                symbol=symbol,
                direction="LONG",
                confidence=round(conf, 3),
                entry_price=round(price, 6),
                take_profit=round(price + TP_ATR_MULT * atr, 6),
                stop_loss=round(sl, 6),
                reason=(
                    f"DynTrail LONG: EMA stack ({curr['ema_fast']:.1f}>"
                    f"{curr['ema_mid']:.1f}>{curr['ema_slow']:.1f}), "
                    f"RSI={curr['rsi']:.0f}, ADX={curr['adx']:.0f}, "
                    f"vol={curr['vol_spike']:.1f}x, "
                    f"{'fanning' if ema_fanning else 'flat'}"
                ),
            ))

    # ===================== SHORT =====================
    ema_stacked_short = (
        curr["ema_fast"] < curr["ema_mid"] < curr["ema_slow"]
    )
    rsi_ok_short = RSI_SHORT_LOW <= curr["rsi"] <= RSI_SHORT_HIGH

    if all([ema_stacked_short, rsi_ok_short, vol_ok, adx_ok]):
        ema_fanning = curr["ema_fast_slope"] < 0 and curr["ema_mid_slope"] < 0

        conf = 0.81
        if ema_fanning:
            conf += 0.05
        if curr["adx"] > 30:
            conf += 0.04
        if curr["vol_spike"] > 2.0:
            conf += 0.03
        if curr["rsi"] < 40:
            conf += 0.02
        conf = min(conf, 0.97)

        ema_mid_sl = curr["ema_mid"]
        fixed_sl = price + SL_ATR_MULT * atr
        sl = min(ema_mid_sl, fixed_sl)

        if conf >= CONF_FLOOR:
            signals.append(Signal(
                symbol=symbol,
                direction="SHORT",
                confidence=round(conf, 3),
                entry_price=round(price, 6),
                take_profit=round(price - TP_ATR_MULT * atr, 6),
                stop_loss=round(sl, 6),
                reason=(
                    f"DynTrail SHORT: EMA stack ({curr['ema_fast']:.1f}<"
                    f"{curr['ema_mid']:.1f}<{curr['ema_slow']:.1f}), "
                    f"RSI={curr['rsi']:.0f}, ADX={curr['adx']:.0f}, "
                    f"vol={curr['vol_spike']:.1f}x, "
                    f"{'fanning' if ema_fanning else 'flat'}"
                ),
            ))

    return signals
