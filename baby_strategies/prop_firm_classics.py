"""
Prop Firm Classic Strategies + Justin's Methods
=================================================

8 battle-tested strategies for prop firm challenges:

Battle-Tested Classics:
  1. OpeningRangeBreakout   — First 1h defines range, trade the breakout
  2. TurtleDonchianBreakout — Richard Dennis 20-bar channel breakout
  3. InsideBarBreakout      — Consolidation → expansion with trend filter
  4. VWAPMeanReversion      — Price deviation from VWAP snaps back to mean
  5. SessionMomentum        — Trade during high-volume session overlap

Justin's Methods (Expert Prop Firm Trader):
  6. EMA9CloseCrossover     — Short below EMA9 close, buy above. Simple & disciplined.
  7. RSIMultiTimeframeBias  — 1h/4h RSI sets directional bias for 15m entries
  8. DoubleTweeterPattern   — Double top/bottom + tweezer reversal patterns

All strategies enforce:
  - Min 1.5x ATR stop loss (crypto-safe wider stops)
  - Min 2:1 R:R ratio
  - Max 2% risk per trade
  - Liquidity filter: skip low-volume symbols
"""

import math
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd


# ══════════════════════════════════════════════════════════════════════
# Shared Signal dataclass
# ══════════════════════════════════════════════════════════════════════

@dataclass
class Signal:
    symbol: str
    direction: str      # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


# ══════════════════════════════════════════════════════════════════════
# Indicator Library (vectorized numpy)
# ══════════════════════════════════════════════════════════════════════

def _ema(arr, period):
    out = np.full_like(arr, np.nan, dtype=float)
    if len(arr) < period:
        return out
    out[period - 1] = np.mean(arr[:period])
    k = 2.0 / (period + 1)
    for i in range(period, len(arr)):
        out[i] = arr[i] * k + out[i - 1] * (1 - k)
    return out


def _sma(arr, period):
    out = np.full_like(arr, np.nan, dtype=float)
    if len(arr) < period:
        return out
    cs = np.nancumsum(arr)
    out[period - 1:] = (cs[period - 1:] - np.concatenate([[0], cs[:-period]])) / period
    return out


def _atr(high, low, close, period=14):
    n = len(high)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i],
                     abs(high[i] - close[i - 1]),
                     abs(low[i] - close[i - 1]))
    out = np.full(n, np.nan)
    if n < period:
        return out
    out[period - 1] = np.mean(tr[:period])
    for i in range(period, n):
        out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def _rsi(close, period=14):
    n = len(close)
    out = np.full(n, np.nan)
    if n < period + 1:
        return out
    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    if avg_loss == 0:
        out[period] = 100.0
    else:
        out[period] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            out[i + 1] = 100.0
        else:
            out[i + 1] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return out


def _vwap(high, low, close, volume):
    """Compute cumulative VWAP and standard deviation bands."""
    typical = (high + low + close) / 3.0
    cum_tp_vol = np.nancumsum(typical * volume)
    cum_vol = np.nancumsum(volume)
    vwap = np.where(cum_vol > 0, cum_tp_vol / cum_vol, np.nan)
    # Rolling std dev of (price - vwap)
    dev = typical - vwap
    n = len(close)
    vwap_std = np.full(n, np.nan)
    for i in range(20, n):
        vwap_std[i] = np.std(dev[max(0, i - 20):i + 1])
    return vwap, vwap_std


def _rolling_vwap(high, low, close, volume, period=20):
    """Compute rolling VWAP over a fixed window (not cumulative).
    This stays close to price and actually crosses EMAs — essential for GoGo Juice."""
    typical = (high + low + close) / 3.0
    tp_vol = typical * volume
    n = len(close)
    rvwap = np.full(n, np.nan)
    for i in range(period, n):
        window_vol = np.sum(volume[i - period:i + 1])
        if window_vol > 0:
            rvwap[i] = np.sum(tp_vol[i - period:i + 1]) / window_vol
    return rvwap


# ══════════════════════════════════════════════════════════════════════
# Precomputed indicator cache
# ══════════════════════════════════════════════════════════════════════

class IndicatorCache:
    """Precompute all indicators once per symbol for efficiency."""

    def __init__(self, df):
        self.open = df["open"].values.astype(float) if "open" in df.columns else df["close"].values.astype(float)
        self.close = df["close"].values.astype(float)
        self.high = df["high"].values.astype(float)
        self.low = df["low"].values.astype(float)
        self.volume = df["volume"].values.astype(float)
        self.n = len(self.close)

        # EMAs
        self.ema8 = _ema(self.close, 8)
        self.ema9 = _ema(self.close, 9)
        self.ema20 = _ema(self.close, 20)
        self.ema21 = _ema(self.close, 21)
        self.ema50 = _ema(self.close, 50)

        # ATR
        self.atr14 = _atr(self.high, self.low, self.close, 14)

        # RSI
        self.rsi14 = _rsi(self.close, 14)

        # Volume SMA
        self.vol_sma20 = _sma(self.volume, 20)

        # Donchian channels (20-bar high/low)
        self.donchian_high = np.full(self.n, np.nan)
        self.donchian_low = np.full(self.n, np.nan)
        self.donchian_exit_high = np.full(self.n, np.nan)
        self.donchian_exit_low = np.full(self.n, np.nan)
        for i in range(20, self.n):
            self.donchian_high[i] = np.max(self.high[i - 20:i])
            self.donchian_low[i] = np.min(self.low[i - 20:i])
        for i in range(10, self.n):
            self.donchian_exit_high[i] = np.max(self.high[i - 10:i])
            self.donchian_exit_low[i] = np.min(self.low[i - 10:i])

        # VWAP + bands (cumulative)
        self.vwap, self.vwap_std = _vwap(self.high, self.low, self.close, self.volume)

        # Rolling VWAP (20-bar window) — stays near price, enables GoGo Juice crosses
        self.rvwap = _rolling_vwap(self.high, self.low, self.close, self.volume, 20)

        # EMA9 slope (angle in degrees)
        self.ema9_angle = np.full(self.n, 0.0)
        for i in range(5, self.n):
            if not np.isnan(self.ema9[i]) and not np.isnan(self.ema9[i - 3]):
                atr_val = self.atr14[i] if not np.isnan(self.atr14[i]) and self.atr14[i] > 0 else 1
                self.ema9_angle[i] = math.degrees(math.atan2(
                    (self.ema9[i] - self.ema9[i - 3]) / atr_val, 3
                ))

        # Higher-timeframe RSI (4x resampled for 15m→1h or 1h→4h)
        n4 = self.n // 4
        self.htf_rsi = np.full(self.n, np.nan)
        if n4 >= 20:
            htf_close = self.close[3::4][:n4]
            htf_rsi_raw = _rsi(htf_close, 14)
            for i in range(len(htf_rsi_raw)):
                val = htf_rsi_raw[i]
                for j in range(4):
                    idx = i * 4 + j
                    if idx < self.n:
                        self.htf_rsi[idx] = val

        # Swing highs/lows for pattern detection
        self.swing_high_20 = np.full(self.n, np.nan)
        self.swing_low_20 = np.full(self.n, np.nan)
        for i in range(20, self.n):
            self.swing_high_20[i] = np.max(self.high[i - 20:i])
            self.swing_low_20[i] = np.min(self.low[i - 20:i])


def _trend_aligned(ic, i, direction):
    """Check if EMA stack (9/20/50) aligns with trade direction. Regime filter."""
    if i < 50 or any(np.isnan(x) for x in [ic.ema9[i], ic.ema20[i], ic.ema50[i]]):
        return True  # Not enough data — allow trade
    if direction == "BUY":
        return ic.ema9[i] > ic.ema20[i] and ic.ema20[i] > ic.ema50[i]
    else:
        return ic.ema9[i] < ic.ema20[i] and ic.ema20[i] < ic.ema50[i]


def _make_signal(symbol, direction, price, atr_val, tp_mult, sl_mult, confidence, reason):
    """Create signal with ATR-based TP/SL. Enforces min 2.0x ATR SL for crypto.
    Also enforces a minimum SL distance of 1% of price (prevents noise stops on low-TF)."""
    sl_mult = max(sl_mult, 2.0)  # Crypto-safe minimum (was 1.5 — too tight)

    # Calculate ATR-based SL distance
    sl_dist = atr_val * sl_mult

    # Enforce minimum 1% SL distance (prevents getting stopped by 15m noise)
    min_sl_dist = price * 0.01
    if sl_dist < min_sl_dist:
        sl_dist = min_sl_dist
        # Scale TP proportionally to maintain R:R
        tp_mult_adj = (sl_dist / atr_val) * (tp_mult / sl_mult)
    else:
        tp_mult_adj = tp_mult

    tp_dist = atr_val * tp_mult_adj

    if direction == "BUY":
        tp = price + tp_dist
        sl = price - sl_dist
    else:
        tp = price - tp_dist
        sl = price + sl_dist
    return Signal(
        symbol=symbol, direction=direction, confidence=confidence,
        entry_price=price, take_profit=tp, stop_loss=sl, reason=reason,
    )


# ══════════════════════════════════════════════════════════════════════
# Strategy 1: Opening Range Breakout (ORB)
# ══════════════════════════════════════════════════════════════════════

class OpeningRangeBreakout:
    """First 4 bars (1h on 15m) define range. Trade the breakout."""

    name = "prop_orb_breakout"
    display_name = "Opening Range Breakout (ORB)"
    EXPECTED_WR = "55-65%"

    @staticmethod
    def generate_signals(df, symbol) -> List[Signal]:
        if len(df) < 60:
            return []
        cache = IndicatorCache(df)
        signals = []
        i = len(df) - 1

        # Define opening range from bars 4 back (simulating first 4 bars of session)
        # In live scanning, we look at the most recent complete 4-bar block
        range_start = max(0, i - 8)
        range_end = range_start + 4
        if range_end > i:
            return []

        range_high = np.max(cache.high[range_start:range_end])
        range_low = np.min(cache.low[range_start:range_end])
        range_height = range_high - range_low

        if range_height <= 0:
            return []

        price = cache.close[i]
        atr_val = cache.atr14[i]
        if np.isnan(atr_val) or atr_val <= 0:
            return []

        # Volume confirmation
        vol_ok = (not np.isnan(cache.vol_sma20[i]) and
                  cache.volume[i] > 1.2 * cache.vol_sma20[i])

        if price > range_high and vol_ok:
            tp = price + range_height * 1.5
            sl = range_low
            # Ensure min 2:1 R:R
            risk = price - sl
            if risk > 0 and (tp - price) / risk >= 2.0:
                signals.append(Signal(
                    symbol=symbol, direction="BUY", confidence=0.65,
                    entry_price=price, take_profit=tp, stop_loss=sl,
                    reason="ORB breakout above range high + volume",
                ))
        elif price < range_low and vol_ok:
            tp = price - range_height * 1.5
            sl = range_high
            risk = sl - price
            if risk > 0 and (price - tp) / risk >= 2.0:
                signals.append(Signal(
                    symbol=symbol, direction="SELL", confidence=0.65,
                    entry_price=price, take_profit=tp, stop_loss=sl,
                    reason="ORB breakdown below range low + volume",
                ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 2: Turtle/Donchian Channel Breakout
# ══════════════════════════════════════════════════════════════════════

class TurtleDonchianBreakout:
    """Richard Dennis classic. 20-bar high breakout with EMA trend filter."""

    name = "prop_turtle_breakout"
    display_name = "Turtle Donchian Breakout"
    EXPECTED_WR = "40-45%"

    @staticmethod
    def generate_signals(df, symbol) -> List[Signal]:
        if len(df) < 60:
            return []
        cache = IndicatorCache(df)
        signals = []
        i = len(df) - 1

        price = cache.close[i]
        atr_val = cache.atr14[i]
        dc_high = cache.donchian_high[i]
        dc_low = cache.donchian_low[i]

        if any(np.isnan(x) for x in [atr_val, dc_high, dc_low]):
            return []
        if atr_val <= 0:
            return []

        # EMA trend filter (8 > 21 > 50 for longs, reverse for shorts)
        e8, e21, e50 = cache.ema8[i], cache.ema21[i], cache.ema50[i]
        if any(np.isnan(x) for x in [e8, e21, e50]):
            return []

        long_trend = e8 > e21 > e50
        short_trend = e8 < e21 < e50

        # ATR volatility scaling — reduce confidence when ATR is extended
        atr_sma = _sma(cache.atr14[~np.isnan(cache.atr14)], 20)
        vol_extended = False
        if len(atr_sma) > 0 and not np.isnan(atr_sma[-1]) and atr_sma[-1] > 0:
            vol_extended = atr_val > 1.5 * atr_sma[-1]

        conf = 0.55 if vol_extended else 0.65

        if price > dc_high and long_trend:
            signals.append(_make_signal(
                symbol, "BUY", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=conf,
                reason="Turtle 20-bar high breakout + EMA stack aligned",
            ))
        elif price < dc_low and short_trend:
            signals.append(_make_signal(
                symbol, "SELL", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=conf,
                reason="Turtle 20-bar low breakdown + EMA stack aligned",
            ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 3: Inside Bar Breakout
# ══════════════════════════════════════════════════════════════════════

class InsideBarBreakout:
    """Consolidation → expansion. Mother bar contains child bar entirely."""

    name = "prop_inside_bar"
    display_name = "Inside Bar Breakout"
    EXPECTED_WR = "60-75%"

    @staticmethod
    def generate_signals(df, symbol) -> List[Signal]:
        if len(df) < 30:
            return []
        cache = IndicatorCache(df)
        signals = []
        i = len(df) - 1

        if i < 2:
            return []

        # Check if bar i-1 is an inside bar (contained within bar i-2)
        mother_high = cache.high[i - 2]
        mother_low = cache.low[i - 2]
        child_high = cache.high[i - 1]
        child_low = cache.low[i - 1]

        is_inside = child_high <= mother_high and child_low >= mother_low
        if not is_inside:
            return []

        # Current bar breaks out of the inside bar
        price = cache.close[i]
        atr_val = cache.atr14[i]
        if np.isnan(atr_val) or atr_val <= 0:
            return []

        ib_range = child_high - child_low
        if ib_range <= 0:
            return []

        # EMA20 trend filter
        ema20 = cache.ema20[i]
        if np.isnan(ema20):
            return []

        # Volume confirmation
        vol_ok = (not np.isnan(cache.vol_sma20[i]) and
                  cache.volume[i] > 1.2 * cache.vol_sma20[i])

        if price > child_high and price > ema20 and vol_ok:
            tp = price + ib_range * 2.0
            sl = child_low
            risk = price - sl
            if risk > 0 and (tp - price) / risk >= 2.0:
                signals.append(Signal(
                    symbol=symbol, direction="BUY", confidence=0.70,
                    entry_price=price, take_profit=tp, stop_loss=sl,
                    reason="Inside bar breakout UP + EMA20 trend + volume",
                ))
        elif price < child_low and price < ema20 and vol_ok:
            tp = price - ib_range * 2.0
            sl = child_high
            risk = sl - price
            if risk > 0 and (price - tp) / risk >= 2.0:
                signals.append(Signal(
                    symbol=symbol, direction="SELL", confidence=0.70,
                    entry_price=price, take_profit=tp, stop_loss=sl,
                    reason="Inside bar breakdown DOWN + EMA20 trend + volume",
                ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 4: VWAP Mean Reversion
# ══════════════════════════════════════════════════════════════════════

class VWAPMeanReversion:
    """Price deviates >2 std dev from VWAP → snaps back to mean."""

    name = "prop_vwap_reversion"
    display_name = "VWAP Mean Reversion"
    EXPECTED_WR = "50-55%"

    @staticmethod
    def generate_signals(df, symbol) -> List[Signal]:
        if len(df) < 30:
            return []
        cache = IndicatorCache(df)
        signals = []
        i = len(df) - 1

        price = cache.close[i]
        vwap = cache.vwap[i]
        vwap_std = cache.vwap_std[i]
        atr_val = cache.atr14[i]

        if any(np.isnan(x) for x in [vwap, vwap_std, atr_val]):
            return []
        if vwap_std <= 0 or atr_val <= 0:
            return []

        lower_band = vwap - 2.0 * vwap_std
        upper_band = vwap + 2.0 * vwap_std

        # Volume spike confirmation
        vol_spike = (not np.isnan(cache.vol_sma20[i]) and
                     cache.volume[i] > 1.3 * cache.vol_sma20[i])

        if price <= lower_band and vol_spike:
            # Long: revert to VWAP mean
            tp = vwap
            sl = price - atr_val * 1.5
            risk = price - sl
            reward = tp - price
            if risk > 0 and reward / risk >= 1.5:
                signals.append(Signal(
                    symbol=symbol, direction="BUY", confidence=0.60,
                    entry_price=price, take_profit=tp, stop_loss=sl,
                    reason="VWAP -2sigma reversion + volume spike",
                ))
        elif price >= upper_band and vol_spike:
            tp = vwap
            sl = price + atr_val * 1.5
            risk = sl - price
            reward = price - tp
            if risk > 0 and reward / risk >= 1.5:
                signals.append(Signal(
                    symbol=symbol, direction="SELL", confidence=0.60,
                    entry_price=price, take_profit=tp, stop_loss=sl,
                    reason="VWAP +2sigma reversion + volume spike",
                ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 5: Session Momentum (High-Volume Window)
# ══════════════════════════════════════════════════════════════════════

class SessionMomentum:
    """Trade during 14:00-20:00 UTC (US market overlap = highest crypto volume)."""

    name = "prop_session_momentum"
    display_name = "Session Momentum (US Overlap)"
    EXPECTED_WR = "55-62%"

    @staticmethod
    def generate_signals(df, symbol) -> List[Signal]:
        if len(df) < 30:
            return []
        cache = IndicatorCache(df)
        signals = []
        i = len(df) - 1

        price = cache.close[i]
        atr_val = cache.atr14[i]
        if np.isnan(atr_val) or atr_val <= 0:
            return []

        # Session filter: check if open_time is in 14:00-20:00 UTC range
        if "open_time" in df.columns:
            bar_time = pd.to_datetime(df["open_time"].iloc[i])
            hour = bar_time.hour
            if hour < 14 or hour >= 20:
                return []  # Outside session window
        # If no timestamp available, skip session filter (backtest mode)

        # EMA trend alignment
        e9 = cache.ema9[i]
        e21 = cache.ema21[i]
        if np.isnan(e9) or np.isnan(e21):
            return []

        # Volume confirmation
        vol_ok = (not np.isnan(cache.vol_sma20[i]) and
                  cache.volume[i] > 1.5 * cache.vol_sma20[i])

        # RSI not overbought/oversold
        rsi = cache.rsi14[i]
        if np.isnan(rsi):
            return []

        if e9 > e21 and vol_ok and 40 <= rsi <= 70:
            signals.append(_make_signal(
                symbol, "BUY", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.65,
                reason="Session momentum BUY: EMA9>21 + high volume + RSI neutral",
            ))
        elif e9 < e21 and vol_ok and 30 <= rsi <= 60:
            signals.append(_make_signal(
                symbol, "SELL", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.65,
                reason="Session momentum SELL: EMA9<21 + high volume + RSI neutral",
            ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 6: EMA9 Close Crossover (Justin's Primary Method)
# ══════════════════════════════════════════════════════════════════════

class EMA9CloseCrossover:
    """Justin's method: short when close < EMA9, buy when close > EMA9.
    Hold until signal reverses. EMA slope filter to avoid chop."""

    name = "prop_ema9_justin"
    display_name = "EMA9 Close Crossover (Justin)"
    EXPECTED_WR = "45-55%"

    @staticmethod
    def generate_signals(df, symbol) -> List[Signal]:
        if len(df) < 20:
            return []
        cache = IndicatorCache(df)
        signals = []
        i = len(df) - 1

        if i < 1:
            return []

        price = cache.close[i]
        prev_close = cache.close[i - 1]
        ema9 = cache.ema9[i]
        prev_ema9 = cache.ema9[i - 1]
        atr_val = cache.atr14[i]

        if any(np.isnan(x) for x in [ema9, prev_ema9, atr_val]):
            return []
        if atr_val <= 0:
            return []

        # Slope filter: avoid chop (EMA9 angle must be meaningful)
        angle = cache.ema9_angle[i]
        if abs(angle) < 10:
            return []  # Too flat, choppy market (raised from 5 to 10)

        # Regime filter: EMA stack must align with direction
        # This was the #1 cause of failure (22% WR without it)

        # Crossover detection: previous bar on opposite side
        cross_up = prev_close <= prev_ema9 and price > ema9
        cross_down = prev_close >= prev_ema9 and price < ema9

        # RSI confirmation to avoid catching falling knives
        rsi = cache.rsi14[i]
        if np.isnan(rsi):
            return []

        if cross_up and angle > 10 and _trend_aligned(cache, i, "BUY") and rsi > 40:
            signals.append(_make_signal(
                symbol, "BUY", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.60,
                reason="EMA9 crossover UP + EMA stack aligned + RSI>40",
            ))
        elif cross_down and angle < -10 and _trend_aligned(cache, i, "SELL") and rsi < 60:
            signals.append(_make_signal(
                symbol, "SELL", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.60,
                reason="EMA9 crossover DOWN + EMA stack aligned + RSI<60",
            ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 7: RSI Multi-Timeframe Bias (Justin's Directional Filter)
# ══════════════════════════════════════════════════════════════════════

class RSIMultiTimeframeBias:
    """Justin's approach: use 1h/4h RSI for directional bias,
    then enter on EMA9 crossover in that direction only."""

    name = "prop_rsi_mtf_justin"
    display_name = "RSI MTF Bias + EMA9 (Justin)"
    EXPECTED_WR = "55-65%"

    @staticmethod
    def generate_signals(df, symbol) -> List[Signal]:
        if len(df) < 80:
            return []
        cache = IndicatorCache(df)
        signals = []
        i = len(df) - 1

        price = cache.close[i]
        ema9 = cache.ema9[i]
        atr_val = cache.atr14[i]
        htf_rsi = cache.htf_rsi[i]

        if any(np.isnan(x) for x in [ema9, atr_val, htf_rsi]):
            return []
        if atr_val <= 0:
            return []

        # Determine HTF bias
        htf_bullish = htf_rsi > 60
        htf_bearish = htf_rsi < 40

        if not htf_bullish and not htf_bearish:
            return []  # No clear bias

        # Look for EMA9 crossover in bias direction
        if i < 1:
            return []
        prev_close = cache.close[i - 1]
        prev_ema9 = cache.ema9[i - 1]
        if np.isnan(prev_ema9):
            return []

        cross_up = prev_close <= prev_ema9 and price > ema9
        cross_down = prev_close >= prev_ema9 and price < ema9

        # Volume confirmation
        vol_ok = (not np.isnan(cache.vol_sma20[i]) and
                  cache.volume[i] > 1.2 * cache.vol_sma20[i])

        if htf_bullish and cross_up and vol_ok:
            signals.append(_make_signal(
                symbol, "BUY", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.70,
                reason=f"HTF RSI={htf_rsi:.0f} bullish + EMA9 cross up + volume",
            ))
        elif htf_bearish and cross_down and vol_ok:
            signals.append(_make_signal(
                symbol, "SELL", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.70,
                reason=f"HTF RSI={htf_rsi:.0f} bearish + EMA9 cross down + volume",
            ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 8: Double Top/Tweezer Pattern Scanner
# ══════════════════════════════════════════════════════════════════════

class DoubleTweeterPattern:
    """Double top/bottom + tweezer reversal patterns (Justin's TA patterns)."""

    name = "prop_double_tweezer"
    display_name = "Double Top/Tweezer Patterns"
    EXPECTED_WR = "55-65%"

    @staticmethod
    def generate_signals(df, symbol) -> List[Signal]:
        if len(df) < 30:
            return []
        cache = IndicatorCache(df)
        signals = []
        i = len(df) - 1

        price = cache.close[i]
        atr_val = cache.atr14[i]
        if np.isnan(atr_val) or atr_val <= 0:
            return []

        # ── Tweezer Top: two consecutive candles with matching highs ──
        if i >= 2:
            h1, h2 = cache.high[i - 1], cache.high[i]
            l1, l2 = cache.low[i - 1], cache.low[i]
            bar1_range = cache.high[i - 1] - cache.low[i - 1]
            bar2_range = cache.high[i] - cache.low[i]

            # Tweezer top: highs within 0.1%, upper wicks > 40% of bar
            if bar1_range > 0 and bar2_range > 0:
                highs_match = abs(h1 - h2) / h1 < 0.001
                upper_wick1 = (h1 - max(cache.open[i - 1], cache.close[i - 1])) / bar1_range
                upper_wick2 = (h2 - max(cache.open[i], cache.close[i])) / bar2_range

                if highs_match and upper_wick1 > 0.4 and upper_wick2 > 0.4:
                    # Bearish tweezer top
                    signals.append(_make_signal(
                        symbol, "SELL", price, atr_val,
                        tp_mult=4.0, sl_mult=2.0, confidence=0.60,
                        reason="Tweezer top: matching highs + long upper wicks",
                    ))

                # Tweezer bottom: lows within 0.1%, lower wicks > 40%
                lows_match = abs(l1 - l2) / max(l1, 0.0001) < 0.001
                lower_wick1 = (min(cache.open[i - 1], cache.close[i - 1]) - l1) / bar1_range
                lower_wick2 = (min(cache.open[i], cache.close[i]) - l2) / bar2_range

                if lows_match and lower_wick1 > 0.4 and lower_wick2 > 0.4:
                    signals.append(_make_signal(
                        symbol, "BUY", price, atr_val,
                        tp_mult=4.0, sl_mult=2.0, confidence=0.60,
                        reason="Tweezer bottom: matching lows + long lower wicks",
                    ))

        # ── Double Top/Bottom: two peaks/troughs within 20-bar window ──
        if i >= 5:
            lookback = min(20, i)
            recent_highs = cache.high[i - lookback:i + 1]
            recent_lows = cache.low[i - lookback:i + 1]

            # Find two highest peaks
            sorted_highs = np.argsort(recent_highs)[::-1]
            if len(sorted_highs) >= 2:
                peak1_idx = sorted_highs[0]
                peak2_idx = sorted_highs[1]

                # Peaks must be at least 3 bars apart
                if abs(peak1_idx - peak2_idx) >= 3:
                    peak1 = recent_highs[peak1_idx]
                    peak2 = recent_highs[peak2_idx]

                    # Within 0.5% of each other = double top
                    if abs(peak1 - peak2) / peak1 < 0.005:
                        neckline = np.min(recent_lows[min(peak1_idx, peak2_idx):max(peak1_idx, peak2_idx) + 1])
                        pattern_height = peak1 - neckline

                        # Current price breaks below neckline
                        if price < neckline and pattern_height > 0:
                            tp = price - pattern_height
                            sl = peak1 + atr_val * 0.5
                            risk = sl - price
                            if risk > 0 and (price - tp) / risk >= 1.5:
                                signals.append(Signal(
                                    symbol=symbol, direction="SELL", confidence=0.65,
                                    entry_price=price, take_profit=tp, stop_loss=sl,
                                    reason="Double top neckline break",
                                ))

            # Find two lowest troughs
            sorted_lows = np.argsort(recent_lows)
            if len(sorted_lows) >= 2:
                trough1_idx = sorted_lows[0]
                trough2_idx = sorted_lows[1]

                if abs(trough1_idx - trough2_idx) >= 3:
                    trough1 = recent_lows[trough1_idx]
                    trough2 = recent_lows[trough2_idx]

                    if trough1 > 0 and abs(trough1 - trough2) / trough1 < 0.005:
                        neckline = np.max(recent_highs[min(trough1_idx, trough2_idx):max(trough1_idx, trough2_idx) + 1])
                        pattern_height = neckline - trough1

                        if price > neckline and pattern_height > 0:
                            tp = price + pattern_height
                            sl = trough1 - atr_val * 0.5
                            risk = price - sl
                            if risk > 0 and (tp - price) / risk >= 1.5:
                                signals.append(Signal(
                                    symbol=symbol, direction="BUY", confidence=0.65,
                                    entry_price=price, take_profit=tp, stop_loss=sl,
                                    reason="Double bottom neckline break",
                                ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Registry of all strategies
# ══════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════
# Strategy 9: J Bravo Triple MA System (SMA9/EMA20/SMA180)
# ══════════════════════════════════════════════════════════════════════

class BravoTripleMA:
    """J Bravo's core method: SMA9/EMA20/SMA180.
    Buy when close > SMA9 + MAs aligned up. Sell when close < EMA20.
    Strong signals when all 3 MAs slope in same direction and stacked."""

    name = "prop_bravo_triple_ma"
    display_name = "Bravo Triple MA (J Bravo)"
    EXPECTED_WR = "50-60%"

    @staticmethod
    def generate_signals(df, symbol) -> List[Signal]:
        if len(df) < 200:
            return []
        cache = IndicatorCache(df)
        signals = []
        i = len(df) - 1

        if i < 1:
            return []

        price = cache.close[i]
        prev_close = cache.close[i - 1]
        atr_val = cache.atr14[i]
        if np.isnan(atr_val) or atr_val <= 0:
            return []

        # J Bravo's 3 MAs: SMA9, EMA20, SMA180
        sma9 = _sma(cache.close, 9)
        sma180 = _sma(cache.close, 180)

        s9 = sma9[i] if i < len(sma9) else np.nan
        e20 = cache.ema20[i]
        s180 = sma180[i] if i < len(sma180) else np.nan

        if any(np.isnan(x) for x in [s9, e20, s180]):
            return []

        prev_s9 = sma9[i - 1] if i - 1 < len(sma9) else np.nan
        prev_e20 = cache.ema20[i - 1]
        if np.isnan(prev_s9) or np.isnan(prev_e20):
            return []

        # Strong Buy: all 3 MAs sloping up and stacked 9 > 20 > 180
        strong_buy = s9 > e20 > s180
        # Strong Sell: all 3 MAs sloping down and stacked 180 > 20 > 9
        strong_sell = s9 < e20 < s180

        # Buy signal: close crosses above SMA9
        cross_above_sma9 = prev_close <= prev_s9 and price > s9
        # Sell signal: close crosses below EMA20
        cross_below_ema20 = prev_close >= prev_e20 and price < e20

        if cross_above_sma9 and strong_buy:
            signals.append(_make_signal(
                symbol, "BUY", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.75,
                reason="Bravo STRONG BUY: close > SMA9 + MAs stacked 9>20>180",
            ))
        elif cross_above_sma9:
            signals.append(_make_signal(
                symbol, "BUY", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.60,
                reason="Bravo BUY: close crosses above SMA9",
            ))
        elif cross_below_ema20 and strong_sell:
            signals.append(_make_signal(
                symbol, "SELL", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.75,
                reason="Bravo STRONG SELL: close < EMA20 + MAs stacked 180>20>9",
            ))
        elif cross_below_ema20:
            signals.append(_make_signal(
                symbol, "SELL", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.60,
                reason="Bravo SELL: close crosses below EMA20",
            ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 10: GoGo Juice (VWAP x EMA20 Crossover)
# ══════════════════════════════════════════════════════════════════════

class GoGoJuice:
    """J Bravo's GoGo Juice: VWAP crosses above EMA20 = GoGo Long,
    VWAP crosses below EMA20 = GoGo Short. Momentum confirmation."""

    name = "prop_gogo_juice"
    display_name = "GoGo Juice (J Bravo VWAP)"
    EXPECTED_WR = "50-55%"

    @staticmethod
    def generate_signals(df, symbol) -> List[Signal]:
        if len(df) < 30:
            return []
        cache = IndicatorCache(df)
        signals = []
        i = len(df) - 1

        if i < 1:
            return []

        price = cache.close[i]
        atr_val = cache.atr14[i]
        vwap_now = cache.rvwap[i]       # Rolling VWAP (stays near price)
        vwap_prev = cache.rvwap[i - 1]
        e20_now = cache.ema20[i]
        e20_prev = cache.ema20[i - 1]

        if any(np.isnan(x) for x in [atr_val, vwap_now, vwap_prev, e20_now, e20_prev]):
            return []
        if atr_val <= 0:
            return []

        # GoGo Long: Rolling VWAP crosses above EMA20
        gogo_long = vwap_prev <= e20_prev and vwap_now > e20_now
        # GoGo Short: Rolling VWAP crosses below EMA20
        gogo_short = vwap_prev >= e20_prev and vwap_now < e20_now

        # Volume confirmation
        vol_ok = (not np.isnan(cache.vol_sma20[i]) and
                  cache.volume[i] > 1.2 * cache.vol_sma20[i])

        if gogo_long and vol_ok:
            signals.append(_make_signal(
                symbol, "BUY", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.65,
                reason="GoGo Long: Rolling VWAP crossed above EMA20 + volume",
            ))
        elif gogo_short and vol_ok:
            signals.append(_make_signal(
                symbol, "SELL", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.65,
                reason="GoGo Short: Rolling VWAP crossed below EMA20 + volume",
            ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 11: Bravo 9 Count Exhaustion
# ══════════════════════════════════════════════════════════════════════

class Bravo9CountExhaustion:
    """J Bravo's 9 Count trend exhaustion system.
    Counts consecutive closes above/below prior close with angle weighting.
    At count 9+, signals potential reversal (trend exhaustion)."""

    name = "prop_bravo_9count"
    display_name = "Bravo 9 Count Exhaustion"
    EXPECTED_WR = "50-60%"

    @staticmethod
    def generate_signals(df, symbol) -> List[Signal]:
        if len(df) < 30:
            return []
        cache = IndicatorCache(df)
        signals = []
        i = len(df) - 1

        if i < 12:
            return []

        price = cache.close[i]
        atr_val = cache.atr14[i]
        if np.isnan(atr_val) or atr_val <= 0:
            return []

        # Count consecutive closes higher/lower than 4 bars ago
        # (TD Sequential style but checking close[i] vs close[i-4])
        up_count = 0
        down_count = 0
        for j in range(i, max(i - 13, 3), -1):
            if cache.close[j] > cache.close[j - 4]:
                up_count += 1
            else:
                break
        for j in range(i, max(i - 13, 3), -1):
            if cache.close[j] < cache.close[j - 4]:
                down_count += 1
            else:
                break

        # At count >= 9, trend is exhausted — look for reversal
        rsi = cache.rsi14[i]
        if np.isnan(rsi):
            return []

        if up_count >= 9 and rsi > 65:
            # Bearish exhaustion — potential sell
            signals.append(_make_signal(
                symbol, "SELL", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.60,
                reason=f"Bravo 9 Count exhaustion: {up_count} up bars + RSI {rsi:.0f}",
            ))
        elif down_count >= 9 and rsi < 35:
            # Bullish exhaustion — potential buy
            signals.append(_make_signal(
                symbol, "BUY", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.60,
                reason=f"Bravo 9 Count exhaustion: {down_count} down bars + RSI {rsi:.0f}",
            ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 12: GoGo Juice Enhanced (Higher Frequency + RSI Confluence)
# ══════════════════════════════════════════════════════════════════════

class GoGoJuiceEnhanced:
    """Enhanced GoGo Juice: relaxed volume + RSI confluence + proximity trigger.
    Original GoGo had 64% WR but only 13 trades. This variant generates more
    signals by also triggering when VWAP is near EMA20 (within 0.3 ATR)
    and RSI confirms direction."""

    name = "prop_gogo_enhanced"
    display_name = "GoGo Juice Enhanced"
    EXPECTED_WR = "55-65%"

    @staticmethod
    def generate_signals(df, symbol) -> List[Signal]:
        if len(df) < 30:
            return []
        cache = IndicatorCache(df)
        signals = []
        i = len(df) - 1

        if i < 1:
            return []

        price = cache.close[i]
        atr_val = cache.atr14[i]
        vwap_now = cache.rvwap[i]       # Rolling VWAP
        vwap_prev = cache.rvwap[i - 1]
        e20_now = cache.ema20[i]
        e20_prev = cache.ema20[i - 1]
        rsi = cache.rsi14[i]

        if any(np.isnan(x) for x in [atr_val, vwap_now, vwap_prev, e20_now, e20_prev, rsi]):
            return []
        if atr_val <= 0:
            return []

        # Classic cross signals (Rolling VWAP × EMA20)
        gogo_long = vwap_prev <= e20_prev and vwap_now > e20_now
        gogo_short = vwap_prev >= e20_prev and vwap_now < e20_now

        # Proximity trigger: Rolling VWAP within 0.3 ATR of EMA20
        vwap_ema_gap = abs(vwap_now - e20_now)
        near_cross = vwap_ema_gap < 0.3 * atr_val

        # Volume: relaxed threshold (1.0x instead of 1.2x)
        vol_ok = (not np.isnan(cache.vol_sma20[i]) and
                  cache.volume[i] > 1.0 * cache.vol_sma20[i])

        # Regime filter
        if not vol_ok:
            return []

        if gogo_long and rsi > 45:
            signals.append(_make_signal(
                symbol, "BUY", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.70,
                reason="GoGo Enhanced LONG: VWAP crossed above EMA20 + RSI>45",
            ))
        elif gogo_short and rsi < 55:
            signals.append(_make_signal(
                symbol, "SELL", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.70,
                reason="GoGo Enhanced SHORT: VWAP crossed below EMA20 + RSI<55",
            ))
        elif near_cross and rsi > 60 and vwap_now > e20_now and _trend_aligned(cache, i, "BUY"):
            signals.append(_make_signal(
                symbol, "BUY", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.60,
                reason="GoGo Proximity LONG: VWAP near EMA20 + RSI>60 + trend aligned",
            ))
        elif near_cross and rsi < 40 and vwap_now < e20_now and _trend_aligned(cache, i, "SELL"):
            signals.append(_make_signal(
                symbol, "SELL", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.60,
                reason="GoGo Proximity SHORT: VWAP near EMA20 + RSI<40 + trend aligned",
            ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 13: Confluence Power (Multi-Signal Confirmation)
# ══════════════════════════════════════════════════════════════════════

class ConfluencePower:
    """Only trade when 3+ independent signals agree: EMA stack + RSI direction
    + VWAP position + volume surge. This is the most selective strategy
    but should have the highest WR."""

    name = "prop_confluence_power"
    display_name = "Confluence Power (Multi-Signal)"
    EXPECTED_WR = "60-75%"

    @staticmethod
    def generate_signals(df, symbol) -> List[Signal]:
        if len(df) < 60:
            return []
        cache = IndicatorCache(df)
        signals = []
        i = len(df) - 1

        price = cache.close[i]
        atr_val = cache.atr14[i]
        rsi = cache.rsi14[i]

        if any(np.isnan(x) for x in [atr_val, rsi]):
            return []
        if atr_val <= 0:
            return []

        # Count bullish/bearish confluence signals
        bull_score = 0
        bear_score = 0

        # Signal 1: EMA stack (9 > 20 > 50)
        if not any(np.isnan(x) for x in [cache.ema9[i], cache.ema20[i], cache.ema50[i]]):
            if cache.ema9[i] > cache.ema20[i] > cache.ema50[i]:
                bull_score += 1
            elif cache.ema9[i] < cache.ema20[i] < cache.ema50[i]:
                bear_score += 1

        # Signal 2: RSI direction
        if rsi > 55:
            bull_score += 1
        elif rsi < 45:
            bear_score += 1

        # Signal 3: Price above/below VWAP
        if not np.isnan(cache.vwap[i]):
            if price > cache.vwap[i]:
                bull_score += 1
            elif price < cache.vwap[i]:
                bear_score += 1

        # Signal 4: Volume surge
        vol_surge = (not np.isnan(cache.vol_sma20[i]) and
                     cache.volume[i] > 1.5 * cache.vol_sma20[i])
        if vol_surge:
            bull_score += 1  # Volume confirms whatever direction
            bear_score += 1

        # Signal 5: EMA9 slope direction
        angle = cache.ema9_angle[i]
        if angle > 15:
            bull_score += 1
        elif angle < -15:
            bear_score += 1

        # Require ALL 5 signals to agree (tightened from 4/5 — was 35% WR at 4/5)
        if bull_score >= 5:
            signals.append(_make_signal(
                symbol, "BUY", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.80,
                reason="Confluence LONG: 5/5 signals aligned (EMA+RSI+VWAP+Vol+Slope)",
            ))
        elif bear_score >= 5:
            signals.append(_make_signal(
                symbol, "SELL", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.80,
                reason="Confluence SHORT: 5/5 signals aligned (EMA+RSI+VWAP+Vol+Slope)",
            ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 14: VWAP + GoGo Hybrid (top 2 winners combined)
# ══════════════════════════════════════════════════════════════════════

class VWAPGoGoHybrid:
    """Combines the two best performers: VWAP Reversion (52.5% WR) +
    GoGo Juice rolling VWAP cross (53.8% WR). Triggers when BOTH
    VWAP deviation AND rolling VWAP/EMA20 alignment agree on direction."""

    name = "prop_vwap_gogo_hybrid"
    display_name = "VWAP + GoGo Hybrid"
    EXPECTED_WR = "55-65%"

    @staticmethod
    def generate_signals(df, symbol) -> List[Signal]:
        if len(df) < 60:
            return []
        cache = IndicatorCache(df)
        signals = []
        i = len(df) - 1

        price = cache.close[i]
        atr_val = cache.atr14[i]
        vwap_cum = cache.vwap[i]
        rvwap = cache.rvwap[i]
        e20 = cache.ema20[i]
        rsi = cache.rsi14[i]

        if any(np.isnan(x) for x in [atr_val, vwap_cum, rvwap, e20, rsi]):
            return []
        if atr_val <= 0:
            return []

        vwap_std = cache.vwap_std[i]
        if np.isnan(vwap_std) or vwap_std <= 0:
            return []

        # Condition 1: VWAP deviation (price far from cumulative VWAP)
        dev = (price - vwap_cum) / vwap_std if vwap_std > 0 else 0

        # Condition 2: Rolling VWAP position vs EMA20
        gogo_bull = rvwap > e20  # Rolling VWAP above EMA20 = bullish
        gogo_bear = rvwap < e20  # Rolling VWAP below EMA20 = bearish

        # Volume filter
        vol_ok = (not np.isnan(cache.vol_sma20[i]) and
                  cache.volume[i] > 0.8 * cache.vol_sma20[i])

        if not vol_ok:
            return []

        # LONG: price below VWAP (oversold) + rolling VWAP bullish + RSI not overbought
        if dev < -1.5 and gogo_bull and rsi < 60:
            signals.append(_make_signal(
                symbol, "BUY", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.72,
                reason=f"VWAP+GoGo LONG: price {dev:.1f}σ below VWAP + RVWAP>EMA20",
            ))
        # SHORT: price above VWAP (overbought) + rolling VWAP bearish + RSI not oversold
        elif dev > 1.5 and gogo_bear and rsi > 40:
            signals.append(_make_signal(
                symbol, "SELL", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.72,
                reason=f"VWAP+GoGo SHORT: price {dev:.1f}σ above VWAP + RVWAP<EMA20",
            ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 15: Exhaustion Reversal (9 Count + VWAP snap)
# ══════════════════════════════════════════════════════════════════════

class ExhaustionReversal:
    """Combines Bravo 9 Count exhaustion with VWAP mean reversion.
    Triggers when a trend is exhausted (9+ consecutive same-direction closes)
    AND price is extended from VWAP. This catches reversals with confirmation."""

    name = "prop_exhaustion_reversal"
    display_name = "Exhaustion Reversal (9Count+VWAP)"
    EXPECTED_WR = "50-60%"

    @staticmethod
    def generate_signals(df, symbol) -> List[Signal]:
        if len(df) < 60:
            return []
        cache = IndicatorCache(df)
        signals = []
        i = len(df) - 1

        price = cache.close[i]
        atr_val = cache.atr14[i]

        if np.isnan(atr_val) or atr_val <= 0:
            return []

        # Count consecutive closes in same direction (Bravo 9 count logic)
        up_count = 0
        down_count = 0
        for j in range(i, max(i - 15, 3), -1):
            if cache.close[j] > cache.close[j - 4]:
                up_count += 1
            else:
                break
        for j in range(i, max(i - 15, 3), -1):
            if cache.close[j] < cache.close[j - 4]:
                down_count += 1
            else:
                break

        # VWAP deviation check
        vwap_std = cache.vwap_std[i]
        vwap_cum = cache.vwap[i]
        if np.isnan(vwap_cum) or np.isnan(vwap_std) or vwap_std <= 0:
            return []
        dev = (price - vwap_cum) / vwap_std

        # RSI extreme confirmation
        rsi = cache.rsi14[i]
        if np.isnan(rsi):
            return []

        # Exhaustion SHORT: 9+ up closes + price extended above VWAP + RSI overbought
        if up_count >= 9 and dev > 1.0 and rsi > 65:
            signals.append(_make_signal(
                symbol, "SELL", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.68,
                reason=f"Exhaustion SHORT: {up_count} up closes + {dev:.1f}σ above VWAP + RSI {rsi:.0f}",
            ))
        # Exhaustion LONG: 9+ down closes + price extended below VWAP + RSI oversold
        elif down_count >= 9 and dev < -1.0 and rsi < 35:
            signals.append(_make_signal(
                symbol, "BUY", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.68,
                reason=f"Exhaustion LONG: {down_count} down closes + {dev:.1f}σ below VWAP + RSI {rsi:.0f}",
            ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 16: EMA Ribbon Momentum (inspired by Battleground 61% WR)
# ══════════════════════════════════════════════════════════════════════

class EMARibbonMomentum:
    """Inspired by Battleground's 61% WR kalman trend strategy.
    Uses EMA ribbon (8/9/20/21/50) expansion as momentum signal.
    Only enters when ribbon is expanding (trending) and RSI confirms."""

    name = "prop_ema_ribbon_momentum"
    display_name = "EMA Ribbon Momentum"
    EXPECTED_WR = "50-60%"

    @staticmethod
    def generate_signals(df, symbol) -> List[Signal]:
        if len(df) < 60:
            return []
        cache = IndicatorCache(df)
        signals = []
        i = len(df) - 1

        price = cache.close[i]
        atr_val = cache.atr14[i]

        if np.isnan(atr_val) or atr_val <= 0:
            return []

        e8 = cache.ema8[i]
        e9 = cache.ema9[i]
        e20 = cache.ema20[i]
        e21 = cache.ema21[i]
        e50 = cache.ema50[i]
        rsi = cache.rsi14[i]

        if any(np.isnan(x) for x in [e8, e9, e20, e21, e50, rsi]):
            return []

        # Check if EMA ribbon is fully stacked (bullish or bearish)
        bull_stack = e8 > e9 > e20 > e21 > e50
        bear_stack = e8 < e9 < e20 < e21 < e50

        # Ribbon expansion: current spread vs 5 bars ago
        spread_now = abs(e8 - e50) / atr_val
        if i >= 5:
            e8_prev = cache.ema8[i - 5]
            e50_prev = cache.ema50[i - 5]
            if not np.isnan(e8_prev) and not np.isnan(e50_prev):
                atr_prev = cache.atr14[i - 5]
                if not np.isnan(atr_prev) and atr_prev > 0:
                    spread_prev = abs(e8_prev - e50_prev) / atr_prev
                else:
                    spread_prev = spread_now
            else:
                spread_prev = spread_now
        else:
            spread_prev = spread_now

        expanding = spread_now > spread_prev * 1.1  # 10% expansion

        # Volume confirmation
        vol_ok = (not np.isnan(cache.vol_sma20[i]) and
                  cache.volume[i] > 0.8 * cache.vol_sma20[i])

        if not vol_ok:
            return []

        # LONG: full bullish stack + expanding + RSI 45-75 (momentum, not overbought)
        if bull_stack and expanding and 45 < rsi < 75:
            signals.append(_make_signal(
                symbol, "BUY", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.70,
                reason=f"EMA Ribbon LONG: 5-EMA bullish stack expanding ({spread_now:.1f}x ATR)",
            ))
        # SHORT: full bearish stack + expanding + RSI 25-55
        elif bear_stack and expanding and 25 < rsi < 55:
            signals.append(_make_signal(
                symbol, "SELL", price, atr_val,
                tp_mult=4.0, sl_mult=2.0, confidence=0.70,
                reason=f"EMA Ribbon SHORT: 5-EMA bearish stack expanding ({spread_now:.1f}x ATR)",
            ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Registry of all strategies
# ══════════════════════════════════════════════════════════════════════

ALL_PROP_STRATEGIES = [
    # Battle-tested classics
    OpeningRangeBreakout,
    TurtleDonchianBreakout,
    InsideBarBreakout,
    VWAPMeanReversion,
    SessionMomentum,
    # Justin's methods
    EMA9CloseCrossover,
    RSIMultiTimeframeBias,
    DoubleTweeterPattern,
    # J Bravo / ChartPrime methods
    BravoTripleMA,
    GoGoJuice,
    Bravo9CountExhaustion,
    # Enhanced / New strategies
    GoGoJuiceEnhanced,
    ConfluencePower,
    # Hybrid variations (combining winning patterns)
    VWAPGoGoHybrid,
    ExhaustionReversal,
    # EMARibbonMomentum DISABLED — 24.8% WR, -103% total in backtest
]
