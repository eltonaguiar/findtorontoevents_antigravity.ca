"""
Hoffman IRB Combination Backtester — Exhaustive Search
========================================================

Systematically combines Hoffman IRB detection with 25+ filters/indicators
to find winning combinations that push WR above 50%.

Filters tested:
  1.  RSI(14) oversold/overbought filter
  2.  RSI(2) Connors-style extreme filter
  3.  Volume confirmation (>1.2x, >1.5x, >2.0x avg)
  4.  ADX regime filter (trending only / ranging only)
  5.  Hurst exponent regime filter
  6.  Bollinger Band position filter
  7.  MACD histogram confirmation
  8.  EMA stack alignment (9/21/50)
  9.  Support/resistance (swing high/low proximity)
  10. Consecutive candle pattern ("yesterday predicts today")
  11. Autocorrelation filter (negative lag-1)
  12. ATR percentile volatility filter
  13. VWAP deviation filter
  14. Day-of-week seasonality
  15. Higher-timeframe EMA trend
  16. Wider stops (2x ATR SL, 3x ATR TP)
  17. Wider R:R (1:2, 1:3)
  18. Combined: RSI + Volume + Regime
  19. Combined: Autocorr + S/R + Volume
  20. Combined: Consecutive + RSI2 + Volume
  21. Smart Money SFP + IRB confluence
  22. MACD + Volume + Regime triple filter
  23. BB Squeeze + IRB breakout
  24. Funding rate contrarian (if available)
  25. Multi-filter best-of combos

Usage:
    python backtest_hoffman_combos.py
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Callable

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

# ══════════════════════════════════════════════════════════════════════
# Data structures
# ══════════════════════════════════════════════════════════════════════

@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT",
           "XRPUSDT", "LTCUSDT", "ADAUSDT", "LINKUSDT", "AVAXUSDT"]

KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "qav", "trades", "tbbav", "tbqav", "ignore",
]


# ══════════════════════════════════════════════════════════════════════
# Indicator Library (vectorized numpy)
# ══════════════════════════════════════════════════════════════════════

def ema(arr, period):
    out = np.full_like(arr, np.nan, dtype=float)
    if len(arr) < period:
        return out
    out[period - 1] = np.mean(arr[:period])
    k = 2.0 / (period + 1)
    for i in range(period, len(arr)):
        out[i] = arr[i] * k + out[i - 1] * (1 - k)
    return out


def sma(arr, period):
    out = np.full_like(arr, np.nan, dtype=float)
    cs = np.nancumsum(arr)
    out[period - 1:] = (cs[period - 1:] - np.concatenate([[0], cs[:-period]])) / period
    return out


def atr(high, low, close, period=14):
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


def rsi(close, period=14):
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


def adx(high, low, close, period=14):
    n = len(high)
    out = np.full(n, np.nan)
    if n < period * 2 + 1:
        return out
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    for i in range(1, n):
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        plus_dm[i] = up if (up > down and up > 0) else 0
        minus_dm[i] = down if (down > up and down > 0) else 0
    atr_v = atr(high, low, close, period)
    sm_p = np.sum(plus_dm[1:period + 1])
    sm_m = np.sum(minus_dm[1:period + 1])
    dx = np.full(n, np.nan)
    for i in range(period, n):
        if i == period:
            sm_p = np.sum(plus_dm[1:period + 1])
            sm_m = np.sum(minus_dm[1:period + 1])
        else:
            sm_p = sm_p - sm_p / period + plus_dm[i]
            sm_m = sm_m - sm_m / period + minus_dm[i]
        if not np.isnan(atr_v[i]) and atr_v[i] > 0:
            pdi = 100 * sm_p / (atr_v[i] * period)
            mdi = 100 * sm_m / (atr_v[i] * period)
            if (pdi + mdi) > 0:
                dx[i] = 100 * abs(pdi - mdi) / (pdi + mdi)
    first = next((i for i in range(n) if not np.isnan(dx[i])), None)
    if first is not None and first + period <= n:
        out[first + period - 1] = np.nanmean(dx[first:first + period])
        for i in range(first + period, n):
            if not np.isnan(dx[i]) and not np.isnan(out[i - 1]):
                out[i] = (out[i - 1] * (period - 1) + dx[i]) / period
    return out


def macd(close, fast=12, slow=26, signal=9):
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line[~np.isnan(macd_line)], signal)
    # Pad signal_line to match length
    full_signal = np.full_like(close, np.nan)
    valid_idx = np.where(~np.isnan(macd_line))[0]
    if len(valid_idx) >= signal:
        start = valid_idx[signal - 1]
        full_signal[start:start + len(signal_line)] = signal_line[:len(full_signal) - start]
    histogram = macd_line - full_signal
    return macd_line, full_signal, histogram


def bollinger_bands(close, period=20, num_std=2.0):
    mid = sma(close, period)
    n = len(close)
    upper = np.full(n, np.nan)
    lower = np.full(n, np.nan)
    for i in range(period - 1, n):
        std = np.std(close[i - period + 1:i + 1], ddof=1)
        upper[i] = mid[i] + num_std * std
        lower[i] = mid[i] - num_std * std
    return upper, mid, lower


def vwap_rolling(high, low, close, volume, period=20):
    typical = (high + low + close) / 3.0
    n = len(close)
    out = np.full(n, np.nan)
    for i in range(period - 1, n):
        s = slice(i - period + 1, i + 1)
        tv = np.sum(typical[s] * volume[s])
        vol_sum = np.sum(volume[s])
        if vol_sum > 0:
            out[i] = tv / vol_sum
    return out


def hurst_exponent(close, max_lag=100):
    if len(close) < max_lag:
        return 0.5
    lags = range(10, min(max_lag, len(close) // 2), 5)
    rs_vals, lag_vals = [], []
    for lag in lags:
        segs = len(close) // lag
        if segs < 1:
            continue
        rs_seg = []
        for s in range(segs):
            subset = close[s * lag:(s + 1) * lag]
            dev = subset - np.mean(subset)
            cum = np.cumsum(dev)
            r = np.max(cum) - np.min(cum)
            sd = np.std(subset, ddof=1)
            if sd > 0:
                rs_seg.append(r / sd)
        if rs_seg:
            rs_vals.append(np.mean(rs_seg))
            lag_vals.append(lag)
    if len(rs_vals) < 3:
        return 0.5
    try:
        c = np.polyfit(np.log(lag_vals), np.log(rs_vals), 1)
        return float(np.clip(c[0], 0.0, 1.0))
    except:
        return 0.5


def autocorrelation_lag1(close, window=60):
    """Rolling lag-1 autocorrelation."""
    n = len(close)
    out = np.full(n, np.nan)
    for i in range(window, n):
        seg = close[i - window:i]
        if np.std(seg) == 0:
            out[i] = 0
        else:
            out[i] = np.corrcoef(seg[:-1], seg[1:])[0, 1]
    return out


def consecutive_candles(close, open_arr):
    """Count consecutive same-direction candles. Positive = bullish streak, negative = bearish."""
    n = len(close)
    out = np.zeros(n, dtype=int)
    for i in range(1, n):
        bullish = close[i] > open_arr[i]
        if i == 0:
            out[i] = 1 if bullish else -1
        else:
            prev_bullish = out[i - 1] > 0
            if bullish and prev_bullish:
                out[i] = out[i - 1] + 1
            elif not bullish and not prev_bullish:
                out[i] = out[i - 1] - 1
            else:
                out[i] = 1 if bullish else -1
    return out


def swing_levels(high, low, lookback=20):
    """Find nearest swing high/low."""
    n = len(high)
    swing_highs = np.full(n, np.nan)
    swing_lows = np.full(n, np.nan)
    for i in range(lookback, n):
        swing_highs[i] = np.max(high[i - lookback:i])
        swing_lows[i] = np.min(low[i - lookback:i])
    return swing_highs, swing_lows


def atr_percentile(atr_arr, window=100):
    n = len(atr_arr)
    out = np.full(n, np.nan)
    for i in range(window - 1, n):
        if np.isnan(atr_arr[i]):
            continue
        seg = atr_arr[max(0, i - window + 1):i + 1]
        valid = seg[~np.isnan(seg)]
        if len(valid) >= 10:
            out[i] = np.sum(valid <= atr_arr[i]) / len(valid)
    return out


# ══════════════════════════════════════════════════════════════════════
# Core IRB Detection
# ══════════════════════════════════════════════════════════════════════

def detect_irb(o, h, l, c, retrace_pct=45):
    """Detect Hoffman Inventory Retracement Bars.
    Returns (bearish_irb, bullish_irb) boolean arrays.
    bearish_irb = long upper wick (potential sell/short signal)
    bullish_irb = long lower wick (potential buy/long signal)
    """
    n = len(c)
    bearish = np.zeros(n, dtype=bool)
    bullish = np.zeros(n, dtype=bool)

    for i in range(n):
        bar_range = h[i] - l[i]
        if bar_range <= 0:
            continue
        body = abs(c[i] - o[i])
        # Range verification: body < retrace_pct% of range
        if body >= (retrace_pct / 100.0) * bar_range:
            continue

        upper_retrace = h[i] - (retrace_pct / 100.0) * bar_range
        lower_retrace = l[i] + (retrace_pct / 100.0) * bar_range

        # Bearish IRB: price action in upper portion (red candle with long upper wick)
        if h[i] > upper_retrace and c[i] < upper_retrace and o[i] < upper_retrace:
            bearish[i] = True

        # Bullish IRB: price action in lower portion (green candle with long lower wick)
        if l[i] < lower_retrace and c[i] > lower_retrace and o[i] > lower_retrace:
            bullish[i] = True

    return bearish, bullish


# ══════════════════════════════════════════════════════════════════════
# Precompute all indicators for a DataFrame
# ══════════════════════════════════════════════════════════════════════

class IndicatorCache:
    """Precompute all indicators once for efficient combination testing."""

    def __init__(self, df):
        o = df["open"].values.astype(float)
        h = df["high"].values.astype(float)
        l = df["low"].values.astype(float)
        c = df["close"].values.astype(float)
        v = df["volume"].values.astype(float)
        n = len(c)

        self.o, self.h, self.l, self.c, self.v = o, h, l, c, v
        self.n = n

        # IRB detection with different thresholds
        self.irb_bear_45, self.irb_bull_45 = detect_irb(o, h, l, c, 45)
        self.irb_bear_50, self.irb_bull_50 = detect_irb(o, h, l, c, 50)
        self.irb_bear_55, self.irb_bull_55 = detect_irb(o, h, l, c, 55)
        self.irb_bear_40, self.irb_bull_40 = detect_irb(o, h, l, c, 40)

        # Moving averages
        self.ema5 = ema(c, 5)
        self.ema8 = ema(c, 8)
        self.ema9 = ema(c, 9)
        self.ema20 = ema(c, 20)
        self.ema21 = ema(c, 21)
        self.ema50 = ema(c, 50)
        self.sma50 = sma(c, 50)
        self.sma200 = sma(c, 200)

        # EMA slope (angle proxy)
        self.ema20_slope = np.full(n, np.nan)
        for i in range(4, n):
            if not np.isnan(self.ema20[i]) and not np.isnan(self.ema20[i - 4]):
                pct_change = (self.ema20[i] - self.ema20[i - 4]) / self.ema20[i - 4]
                self.ema20_slope[i] = np.degrees(np.arctan(pct_change * 1000))

        # Volatility
        self.atr14 = atr(h, l, c, 14)
        self.atr_pct = atr_percentile(self.atr14, 100)

        # Momentum
        self.rsi14 = rsi(c, 14)
        self.rsi2 = rsi(c, 2)
        self.macd_line, self.macd_signal, self.macd_hist = macd(c)

        # Bollinger Bands
        self.bb_upper, self.bb_mid, self.bb_lower = bollinger_bands(c, 20, 2.0)

        # Volume
        self.vol_sma20 = sma(v, 20)
        self.vol_ratio = np.where(self.vol_sma20 > 0, v / self.vol_sma20, 1.0)

        # Trend strength
        self.adx14 = adx(h, l, c, 14)

        # VWAP
        self.vwap20 = vwap_rolling(h, l, c, v, 20)

        # Support/Resistance
        self.swing_high, self.swing_low = swing_levels(h, l, 20)

        # Consecutive candles
        self.consec = consecutive_candles(c, o)

        # Autocorrelation
        self.acf1 = autocorrelation_lag1(c, 60)

        # Higher-TF EMA (4x = 1H from 15m)
        htf_close = np.full(n, np.nan)
        for i in range(0, n, 4):
            end = min(i + 4, n)
            htf_close[i:end] = c[end - 1]
        self.htf_ema20 = ema(htf_close, 20)

        # Hurst (computed per-bar would be too slow, compute for last bar)
        self.hurst_100 = hurst_exponent(c[-100:]) if n >= 100 else 0.5


# ══════════════════════════════════════════════════════════════════════
# Combination Strategy Definitions
# ══════════════════════════════════════════════════════════════════════

def _base_irb_signal(ic: IndicatorCache, i: int, irb_pct: int = 45,
                     tp_mult: float = 1.5, sl_mult: float = 1.0,
                     min_angle: float = 0.0):
    """Base IRB signal generator. Returns Signal or None."""
    if i < 60 or np.isnan(ic.atr14[i]) or ic.atr14[i] <= 0:
        return None

    # Select IRB arrays based on threshold
    if irb_pct == 40:
        bear, bull = ic.irb_bear_40, ic.irb_bull_40
    elif irb_pct == 50:
        bear, bull = ic.irb_bear_50, ic.irb_bull_50
    elif irb_pct == 55:
        bear, bull = ic.irb_bear_55, ic.irb_bull_55
    else:
        bear, bull = ic.irb_bear_45, ic.irb_bull_45

    entry = ic.c[i]
    atr_val = ic.atr14[i]

    # Check EMA angle
    angle = ic.ema20_slope[i] if not np.isnan(ic.ema20_slope[i]) else 0

    # BUY: bearish IRB in uptrend (buy the dip) — or bullish IRB
    # Original Hoffman: bearish IRB (red candle) in uptrend = buy the dip
    if bear[i] and angle >= min_angle:
        tp = entry + tp_mult * atr_val
        sl = entry - sl_mult * atr_val
        return Signal("", "BUY", 0.6, entry, tp, sl, "IRB-BUY")

    # SELL: bullish IRB in downtrend (sell the rally)
    if bull[i] and angle <= -min_angle:
        tp = entry - tp_mult * atr_val
        sl = entry + sl_mult * atr_val
        return Signal("", "SELL", 0.6, entry, tp, sl, "IRB-SELL")

    return None


def make_combo(name: str, description: str,
               irb_pct: int = 45,
               tp_mult: float = 1.5, sl_mult: float = 1.0,
               min_angle: float = 15.0,
               filter_fn: Optional[Callable] = None):
    """Factory to create a combination strategy."""

    def generate(ic: IndicatorCache, i: int, symbol: str) -> Optional[Signal]:
        sig = _base_irb_signal(ic, i, irb_pct, tp_mult, sl_mult, min_angle)
        if sig is None:
            return None

        # Apply filter
        if filter_fn is not None:
            if not filter_fn(ic, i, sig.direction):
                return None

        sig.symbol = symbol
        sig.reason = f"{name}: {sig.reason}"
        return sig

    return {"name": name, "description": description, "generate": generate}


# ═══ Filter functions ═══

def f_rsi14_moderate(ic, i, direction):
    """RSI(14) not extreme — between 30-70."""
    if np.isnan(ic.rsi14[i]):
        return False
    if direction == "BUY":
        return 25 < ic.rsi14[i] < 60
    else:
        return 40 < ic.rsi14[i] < 75

def f_rsi14_oversold(ic, i, direction):
    """RSI(14) must be oversold for BUY, overbought for SELL."""
    if np.isnan(ic.rsi14[i]):
        return False
    if direction == "BUY":
        return ic.rsi14[i] < 35
    else:
        return ic.rsi14[i] > 65

def f_rsi2_extreme(ic, i, direction):
    """Connors RSI(2) extreme — <10 for BUY, >90 for SELL."""
    if np.isnan(ic.rsi2[i]):
        return False
    if direction == "BUY":
        return ic.rsi2[i] < 10
    else:
        return ic.rsi2[i] > 90

def f_rsi2_moderate(ic, i, direction):
    """RSI(2) < 25 for BUY, > 75 for SELL."""
    if np.isnan(ic.rsi2[i]):
        return False
    if direction == "BUY":
        return ic.rsi2[i] < 25
    else:
        return ic.rsi2[i] > 75

def f_volume_1_2x(ic, i, direction):
    """Volume > 1.2x average."""
    return ic.vol_ratio[i] >= 1.2

def f_volume_1_5x(ic, i, direction):
    """Volume > 1.5x average."""
    return ic.vol_ratio[i] >= 1.5

def f_volume_2x(ic, i, direction):
    """Volume > 2.0x average."""
    return ic.vol_ratio[i] >= 2.0

def f_adx_trending(ic, i, direction):
    """ADX > 25 = trending market only."""
    return not np.isnan(ic.adx14[i]) and ic.adx14[i] > 25

def f_adx_ranging(ic, i, direction):
    """ADX < 20 = ranging market only."""
    return not np.isnan(ic.adx14[i]) and ic.adx14[i] < 20

def f_adx_moderate(ic, i, direction):
    """ADX > 20 = some trend."""
    return not np.isnan(ic.adx14[i]) and ic.adx14[i] > 20

def f_bb_extreme(ic, i, direction):
    """Near Bollinger Band extreme."""
    if np.isnan(ic.bb_lower[i]) or np.isnan(ic.bb_upper[i]):
        return False
    if direction == "BUY":
        return ic.c[i] <= ic.bb_lower[i] * 1.01
    else:
        return ic.c[i] >= ic.bb_upper[i] * 0.99

def f_bb_within(ic, i, direction):
    """Within Bollinger Bands (not extreme)."""
    if np.isnan(ic.bb_lower[i]) or np.isnan(ic.bb_upper[i]):
        return False
    return ic.bb_lower[i] < ic.c[i] < ic.bb_upper[i]

def f_macd_confirm(ic, i, direction):
    """MACD histogram confirms direction."""
    if np.isnan(ic.macd_hist[i]):
        return False
    if direction == "BUY":
        return ic.macd_hist[i] > 0 or (i > 0 and not np.isnan(ic.macd_hist[i-1])
                                         and ic.macd_hist[i] > ic.macd_hist[i-1])
    else:
        return ic.macd_hist[i] < 0 or (i > 0 and not np.isnan(ic.macd_hist[i-1])
                                         and ic.macd_hist[i] < ic.macd_hist[i-1])

def f_macd_crossover(ic, i, direction):
    """MACD recently crossed signal (within 3 bars)."""
    if i < 3 or np.isnan(ic.macd_hist[i]):
        return False
    for j in range(max(0, i - 3), i):
        if np.isnan(ic.macd_hist[j]):
            continue
        if direction == "BUY" and ic.macd_hist[j] < 0 and ic.macd_hist[i] > 0:
            return True
        if direction == "SELL" and ic.macd_hist[j] > 0 and ic.macd_hist[i] < 0:
            return True
    return False

def f_ema_stack(ic, i, direction):
    """EMA 9 > 21 > 50 alignment for BUY."""
    if np.isnan(ic.ema9[i]) or np.isnan(ic.ema21[i]) or np.isnan(ic.ema50[i]):
        return False
    if direction == "BUY":
        return ic.ema9[i] > ic.ema21[i] > ic.ema50[i]
    else:
        return ic.ema9[i] < ic.ema21[i] < ic.ema50[i]

def f_ema_ribbon(ic, i, direction):
    """EMA 5 > 20 > SMA 50 ribbon."""
    if np.isnan(ic.ema5[i]) or np.isnan(ic.ema20[i]) or np.isnan(ic.sma50[i]):
        return False
    if direction == "BUY":
        return ic.ema5[i] > ic.ema20[i] > ic.sma50[i]
    else:
        return ic.ema5[i] < ic.ema20[i] < ic.sma50[i]

def f_near_support(ic, i, direction):
    """Near swing support (for BUY) or resistance (for SELL)."""
    if np.isnan(ic.swing_low[i]) or np.isnan(ic.atr14[i]):
        return False
    if direction == "BUY":
        return abs(ic.c[i] - ic.swing_low[i]) < 1.0 * ic.atr14[i]
    else:
        return abs(ic.c[i] - ic.swing_high[i]) < 1.0 * ic.atr14[i]

def f_consecutive_reversal(ic, i, direction):
    """After consecutive candles in opposite direction (yesterday predicts today)."""
    if direction == "BUY":
        return ic.consec[i] <= -2  # 2+ consecutive red candles = buy reversal
    else:
        return ic.consec[i] >= 2   # 2+ consecutive green candles = sell reversal

def f_consecutive_3(ic, i, direction):
    """After 3+ consecutive candles in opposite direction."""
    if direction == "BUY":
        return ic.consec[i] <= -3
    else:
        return ic.consec[i] >= 3

def f_autocorr_negative(ic, i, direction):
    """Negative lag-1 autocorrelation (mean-reverting regime)."""
    if np.isnan(ic.acf1[i]):
        return False
    return ic.acf1[i] < -0.1

def f_autocorr_strong(ic, i, direction):
    """Strongly negative autocorrelation."""
    if np.isnan(ic.acf1[i]):
        return False
    return ic.acf1[i] < -0.2

def f_atr_not_extreme(ic, i, direction):
    """ATR not at extreme (avoid spiky volatility)."""
    if np.isnan(ic.atr_pct[i]):
        return True  # allow if not computed
    return ic.atr_pct[i] < 0.85

def f_atr_compressed(ic, i, direction):
    """ATR compressed — low volatility (potential breakout)."""
    if np.isnan(ic.atr_pct[i]):
        return False
    return ic.atr_pct[i] < 0.30

def f_vwap_confirm(ic, i, direction):
    """Price relative to VWAP."""
    if np.isnan(ic.vwap20[i]):
        return True
    if direction == "BUY":
        return ic.c[i] <= ic.vwap20[i] * 1.005  # at or below VWAP
    else:
        return ic.c[i] >= ic.vwap20[i] * 0.995  # at or above VWAP

def f_htf_trend(ic, i, direction):
    """Higher-timeframe EMA trend alignment."""
    if np.isnan(ic.htf_ema20[i]) or i < 1 or np.isnan(ic.htf_ema20[i - 1]):
        return True
    if direction == "BUY":
        return ic.htf_ema20[i] > ic.htf_ema20[i - 1]
    else:
        return ic.htf_ema20[i] < ic.htf_ema20[i - 1]

def f_above_sma200(ic, i, direction):
    """Above SMA200 for buys, below for sells (major trend)."""
    if np.isnan(ic.sma200[i]):
        return True
    if direction == "BUY":
        return ic.c[i] > ic.sma200[i]
    else:
        return ic.c[i] < ic.sma200[i]


# ═══ Combined filter functions ═══

def f_rsi_vol_regime(ic, i, direction):
    return f_rsi14_moderate(ic, i, direction) and f_volume_1_2x(ic, i, direction) and f_adx_moderate(ic, i, direction)

def f_autocorr_sr_vol(ic, i, direction):
    return f_autocorr_negative(ic, i, direction) and f_near_support(ic, i, direction) and f_volume_1_2x(ic, i, direction)

def f_consec_rsi2_vol(ic, i, direction):
    return f_consecutive_reversal(ic, i, direction) and f_rsi2_moderate(ic, i, direction) and f_volume_1_2x(ic, i, direction)

def f_macd_vol_regime(ic, i, direction):
    return f_macd_confirm(ic, i, direction) and f_volume_1_2x(ic, i, direction) and f_adx_moderate(ic, i, direction)

def f_rsi2_vol_ema(ic, i, direction):
    return f_rsi2_moderate(ic, i, direction) and f_volume_1_2x(ic, i, direction) and f_ema_ribbon(ic, i, direction)

def f_consec_autocorr(ic, i, direction):
    return f_consecutive_reversal(ic, i, direction) and f_autocorr_negative(ic, i, direction)

def f_bb_rsi_vol(ic, i, direction):
    return f_bb_extreme(ic, i, direction) and f_rsi14_oversold(ic, i, direction) and f_volume_1_2x(ic, i, direction)

def f_support_rsi_consec(ic, i, direction):
    return f_near_support(ic, i, direction) and f_rsi14_oversold(ic, i, direction) and f_consecutive_reversal(ic, i, direction)

def f_htf_vol_rsi(ic, i, direction):
    return f_htf_trend(ic, i, direction) and f_volume_1_2x(ic, i, direction) and f_rsi14_moderate(ic, i, direction)

def f_kitchen_sink(ic, i, direction):
    """Everything: RSI + Vol + Regime + HTF + VWAP."""
    return (f_rsi14_moderate(ic, i, direction) and f_volume_1_2x(ic, i, direction)
            and f_adx_moderate(ic, i, direction) and f_htf_trend(ic, i, direction))


# ══════════════════════════════════════════════════════════════════════
# Build all combinations
# ══════════════════════════════════════════════════════════════════════

COMBOS = [
    # === Baseline (no filter) ===
    make_combo("hoffman_baseline_45pct", "Baseline IRB 45% no filter", 45, 1.5, 1.0, 15.0, None),
    make_combo("hoffman_baseline_wider_rr", "Baseline with 2:1 R:R", 45, 2.0, 1.0, 15.0, None),
    make_combo("hoffman_baseline_3x_rr", "Baseline with 3:1 R:R", 45, 3.0, 1.0, 15.0, None),
    make_combo("hoffman_wider_stops", "Wider stops 2x ATR SL", 45, 3.0, 2.0, 15.0, None),
    make_combo("hoffman_no_angle", "No angle requirement", 45, 1.5, 1.0, 0.0, None),

    # === Single indicator filters ===
    make_combo("irb+rsi14_moderate", "IRB + RSI(14) 30-70 zone", 45, 1.5, 1.0, 15.0, f_rsi14_moderate),
    make_combo("irb+rsi14_oversold", "IRB + RSI(14) oversold/overbought", 45, 1.5, 1.0, 15.0, f_rsi14_oversold),
    make_combo("irb+rsi2_extreme", "IRB + Connors RSI(2) <10/>90", 45, 2.0, 1.0, 0.0, f_rsi2_extreme),
    make_combo("irb+rsi2_moderate", "IRB + RSI(2) <25/>75", 45, 2.0, 1.0, 0.0, f_rsi2_moderate),
    make_combo("irb+vol_1.2x", "IRB + Volume >1.2x avg", 45, 1.5, 1.0, 15.0, f_volume_1_2x),
    make_combo("irb+vol_1.5x", "IRB + Volume >1.5x avg", 45, 1.5, 1.0, 15.0, f_volume_1_5x),
    make_combo("irb+vol_2x", "IRB + Volume >2x avg", 45, 2.0, 1.0, 15.0, f_volume_2x),
    make_combo("irb+adx_trending", "IRB + ADX>25 trending", 45, 1.5, 1.0, 15.0, f_adx_trending),
    make_combo("irb+adx_ranging", "IRB + ADX<20 ranging", 45, 1.5, 1.0, 0.0, f_adx_ranging),
    make_combo("irb+bb_extreme", "IRB + at Bollinger Band extreme", 45, 2.0, 1.0, 0.0, f_bb_extreme),
    make_combo("irb+macd_confirm", "IRB + MACD histogram confirms", 45, 1.5, 1.0, 15.0, f_macd_confirm),
    make_combo("irb+macd_crossover", "IRB + recent MACD crossover", 45, 2.0, 1.0, 0.0, f_macd_crossover),
    make_combo("irb+ema_stack", "IRB + EMA 9>21>50 stack", 45, 1.5, 1.0, 0.0, f_ema_stack),
    make_combo("irb+ema_ribbon", "IRB + EMA 5>20>SMA50 ribbon", 45, 1.5, 1.0, 0.0, f_ema_ribbon),
    make_combo("irb+near_support", "IRB + near S/R level", 45, 2.0, 1.0, 0.0, f_near_support),
    make_combo("irb+consec_reversal", "IRB + 2+ consecutive opposite candles", 45, 1.5, 1.0, 0.0, f_consecutive_reversal),
    make_combo("irb+consec_3", "IRB + 3+ consecutive opposite candles", 45, 2.0, 1.0, 0.0, f_consecutive_3),
    make_combo("irb+autocorr_neg", "IRB + negative autocorrelation", 45, 2.0, 1.0, 0.0, f_autocorr_negative),
    make_combo("irb+autocorr_strong", "IRB + strongly negative autocorrelation", 45, 2.0, 1.0, 0.0, f_autocorr_strong),
    make_combo("irb+atr_not_extreme", "IRB + ATR not spiking", 45, 1.5, 1.0, 15.0, f_atr_not_extreme),
    make_combo("irb+atr_compressed", "IRB + ATR compressed (breakout setup)", 45, 2.5, 1.0, 0.0, f_atr_compressed),
    make_combo("irb+vwap_confirm", "IRB + at/below VWAP for buys", 45, 1.5, 1.0, 15.0, f_vwap_confirm),
    make_combo("irb+htf_trend", "IRB + HTF EMA trend alignment", 45, 1.5, 1.0, 15.0, f_htf_trend),
    make_combo("irb+sma200", "IRB + above SMA200 for buys", 45, 1.5, 1.0, 15.0, f_above_sma200),

    # === Different IRB thresholds ===
    make_combo("irb40+vol+rsi", "IRB 40% + Vol + RSI moderate", 40, 1.5, 1.0, 10.0, f_rsi_vol_regime),
    make_combo("irb50+vol+rsi", "IRB 50% + Vol + RSI moderate", 50, 1.5, 1.0, 10.0, f_rsi_vol_regime),
    make_combo("irb55+vol+rsi", "IRB 55% + Vol + RSI moderate (stricter wick)", 55, 2.0, 1.0, 0.0, f_rsi_vol_regime),

    # === R:R variations with best filters ===
    make_combo("irb+rsi14+2rr", "IRB + RSI moderate + 2:1 R:R", 45, 2.0, 1.0, 15.0, f_rsi14_moderate),
    make_combo("irb+rsi14+3rr", "IRB + RSI moderate + 3:1 R:R", 45, 3.0, 1.0, 15.0, f_rsi14_moderate),
    make_combo("irb+vol+2rr", "IRB + Volume + 2:1 R:R", 45, 2.0, 1.0, 15.0, f_volume_1_2x),
    make_combo("irb+vol+wide_sl", "IRB + Volume + 2x ATR SL", 45, 3.0, 2.0, 15.0, f_volume_1_2x),

    # === Multi-filter combinations ===
    make_combo("irb+rsi+vol+regime", "RSI + Volume + ADX regime", 45, 1.5, 1.0, 10.0, f_rsi_vol_regime),
    make_combo("irb+autocorr+sr+vol", "Autocorr + S/R + Volume", 45, 2.0, 1.0, 0.0, f_autocorr_sr_vol),
    make_combo("irb+consec+rsi2+vol", "Consecutive + RSI(2) + Volume", 45, 2.0, 1.0, 0.0, f_consec_rsi2_vol),
    make_combo("irb+macd+vol+regime", "MACD + Volume + ADX regime", 45, 1.5, 1.0, 10.0, f_macd_vol_regime),
    make_combo("irb+rsi2+vol+ema", "RSI(2) + Volume + EMA ribbon", 45, 2.0, 1.0, 0.0, f_rsi2_vol_ema),
    make_combo("irb+consec+autocorr", "Consecutive candles + Autocorrelation", 45, 2.0, 1.0, 0.0, f_consec_autocorr),
    make_combo("irb+bb+rsi+vol", "BB extreme + RSI oversold + Volume", 45, 2.5, 1.0, 0.0, f_bb_rsi_vol),
    make_combo("irb+support+rsi+consec", "S/R + RSI oversold + Consecutive", 45, 2.0, 1.0, 0.0, f_support_rsi_consec),
    make_combo("irb+htf+vol+rsi", "HTF trend + Volume + RSI", 45, 1.5, 1.0, 10.0, f_htf_vol_rsi),
    make_combo("irb+kitchen_sink", "Everything: RSI+Vol+ADX+HTF", 45, 2.0, 1.0, 10.0, f_kitchen_sink),

    # === Wider stops with multi-filters ===
    make_combo("irb+rsi+vol+regime+wide", "RSI+Vol+Regime + wide stops", 45, 3.0, 2.0, 10.0, f_rsi_vol_regime),
    make_combo("irb+consec+rsi2+vol+wide", "Consec+RSI2+Vol + wide stops", 45, 3.0, 2.0, 0.0, f_consec_rsi2_vol),
    make_combo("irb+bb+rsi+vol+wide", "BB+RSI+Vol + wide stops", 45, 4.0, 2.0, 0.0, f_bb_rsi_vol),
]


# ══════════════════════════════════════════════════════════════════════
# Backtesting Engine
# ══════════════════════════════════════════════════════════════════════

def fetch_historical(symbol, interval="15m", limit=1000):
    url = "https://api.binance.com/api/v3/klines"
    resp = requests.get(url, params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=15)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json(), columns=KLINE_COLUMNS)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    return df


def simulate_trades(signals_by_bar, df, max_hold_bars=16):
    trades = []
    position = None

    for bar_idx in range(len(df)):
        h_val = df["high"].iloc[bar_idx]
        l_val = df["low"].iloc[bar_idx]
        c_val = df["close"].iloc[bar_idx]

        if position is not None:
            entry = position["entry_price"]
            hold = bar_idx - position["entry_bar"]

            if position["direction"] == "BUY":
                if l_val <= position["sl"]:
                    pnl = (position["sl"] - entry) / entry * 100
                    trades.append({"pnl_pct": pnl, "exit_reason": "SL", "hold_bars": hold})
                    position = None; continue
                if h_val >= position["tp"]:
                    pnl = (position["tp"] - entry) / entry * 100
                    trades.append({"pnl_pct": pnl, "exit_reason": "TP", "hold_bars": hold})
                    position = None; continue
            else:
                if h_val >= position["sl"]:
                    pnl = (entry - position["sl"]) / entry * 100
                    trades.append({"pnl_pct": pnl, "exit_reason": "SL", "hold_bars": hold})
                    position = None; continue
                if l_val <= position["tp"]:
                    pnl = (entry - position["tp"]) / entry * 100
                    trades.append({"pnl_pct": pnl, "exit_reason": "TP", "hold_bars": hold})
                    position = None; continue

            if hold >= max_hold_bars:
                if position["direction"] == "BUY":
                    pnl = (c_val - entry) / entry * 100
                else:
                    pnl = (entry - c_val) / entry * 100
                trades.append({"pnl_pct": pnl, "exit_reason": "TIME", "hold_bars": hold})
                position = None; continue

        if position is None and bar_idx in signals_by_bar:
            sig = signals_by_bar[bar_idx]
            position = {
                "entry_bar": bar_idx, "entry_price": sig.entry_price,
                "tp": sig.take_profit, "sl": sig.stop_loss,
                "direction": sig.direction,
            }

    return trades


def compute_metrics(trades):
    if not trades:
        return {"total_trades": 0, "win_rate": 0, "avg_pnl": 0, "total_pnl": 0,
                "profit_factor": 0, "max_dd": 0, "tp_exits": 0, "sl_exits": 0,
                "sharpe": 0, "avg_hold": 0}

    wins = [t for t in trades if t["pnl_pct"] > 0]
    total_pnl = sum(t["pnl_pct"] for t in trades)
    gross_profit = sum(t["pnl_pct"] for t in wins) if wins else 0
    gross_loss = abs(sum(t["pnl_pct"] for t in trades if t["pnl_pct"] <= 0)) or 0.001

    pnls = [t["pnl_pct"] for t in trades]
    sharpe = (np.mean(pnls) / np.std(pnls) * np.sqrt(252)) if np.std(pnls) > 0 else 0

    equity = [0]
    for t in trades:
        equity.append(equity[-1] + t["pnl_pct"])
    peak = equity[0]
    max_dd = 0
    for e in equity:
        peak = max(peak, e)
        max_dd = max(max_dd, peak - e)

    return {
        "total_trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_pnl": round(total_pnl / len(trades), 3),
        "total_pnl": round(total_pnl, 2),
        "profit_factor": round(gross_profit / gross_loss, 2),
        "max_dd": round(max_dd, 2),
        "tp_exits": sum(1 for t in trades if t["exit_reason"] == "TP"),
        "sl_exits": sum(1 for t in trades if t["exit_reason"] == "SL"),
        "sharpe": round(sharpe, 2),
        "avg_hold": round(np.mean([t["hold_bars"] for t in trades]), 1),
    }


def run_combo(combo, all_caches, max_hold=16):
    """Run a single combo across all symbols."""
    all_trades = []
    total_signals = 0

    for symbol, ic in all_caches.items():
        signals_by_bar = {}
        for i in range(60, ic.n):
            sig = combo["generate"](ic, i, symbol)
            if sig is not None:
                signals_by_bar[i] = sig
                total_signals += 1

        # Build a minimal DF for simulation
        df_sim = pd.DataFrame({
            "high": ic.h, "low": ic.l, "close": ic.c
        })
        trades = simulate_trades(signals_by_bar, df_sim, max_hold)
        all_trades.extend(trades)

    return all_trades, total_signals


def main():
    print("=" * 80)
    print("  Hoffman IRB Combination Backtester — Exhaustive Search")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Testing {len(COMBOS)} combinations × {len(SYMBOLS)} symbols")
    print("=" * 80)

    # Fetch data
    all_data = {}
    for sym in SYMBOLS:
        print(f"  Fetching {sym} 15m (1000 bars)...", end=" ", flush=True)
        try:
            all_data[sym] = fetch_historical(sym, "15m", 1000)
            print(f"OK ({len(all_data[sym])} bars)")
        except Exception as e:
            print(f"FAIL: {e}")
        time.sleep(0.3)

    if not all_data:
        print("No data — aborting")
        return

    # Precompute indicators
    print("\n  Precomputing indicators...", flush=True)
    all_caches = {}
    for sym, df in all_data.items():
        all_caches[sym] = IndicatorCache(df)
    print(f"  Done — {len(all_caches)} symbol caches built\n")

    # Run all combos
    results = []
    print(f"  {'#':>3} {'Strategy':<40} {'Trades':>6} {'WR%':>6} {'PnL%':>8} {'PF':>5} {'Sharpe':>7} {'DD%':>6} {'Sigs':>5}")
    print("  " + "-" * 88)

    for idx, combo in enumerate(COMBOS, 1):
        trades, n_signals = run_combo(combo, all_caches, max_hold=16)
        metrics = compute_metrics(trades)

        results.append({
            "name": combo["name"],
            "description": combo["description"],
            "metrics": metrics,
            "signals": n_signals,
        })

        wr = metrics["win_rate"]
        icon = "*" if wr >= 55 else "+" if wr >= 50 else "o" if wr >= 45 else "."
        print(f"  {idx:>3} {icon} {combo['name']:<38} "
              f"{metrics['total_trades']:>6} {wr:>5.1f}% "
              f"{metrics['total_pnl']:>+7.2f}% {metrics['profit_factor']:>5.2f} "
              f"{metrics['sharpe']:>+6.2f} {metrics['max_dd']:>5.2f}% {n_signals:>5}")

    # Sort and display top performers
    ranked = sorted(results, key=lambda r: (r["metrics"]["win_rate"], r["metrics"]["total_pnl"]), reverse=True)

    print("\n" + "=" * 80)
    print("  TOP 15 COMBINATIONS BY WIN RATE")
    print("=" * 80)
    for i, r in enumerate(ranked[:15], 1):
        m = r["metrics"]
        print(f"  {i:>2}. {r['name']:<40} WR={m['win_rate']:>5.1f}% PnL={m['total_pnl']:>+7.2f}% "
              f"PF={m['profit_factor']:>5.2f} Sharpe={m['sharpe']:>+6.2f} Trades={m['total_trades']:>4}")

    # Top by PnL
    ranked_pnl = sorted(results, key=lambda r: r["metrics"]["total_pnl"], reverse=True)
    print("\n" + "=" * 80)
    print("  TOP 15 COMBINATIONS BY TOTAL PnL")
    print("=" * 80)
    for i, r in enumerate(ranked_pnl[:15], 1):
        m = r["metrics"]
        print(f"  {i:>2}. {r['name']:<40} PnL={m['total_pnl']:>+7.2f}% WR={m['win_rate']:>5.1f}% "
              f"PF={m['profit_factor']:>5.2f} Sharpe={m['sharpe']:>+6.2f} Trades={m['total_trades']:>4}")

    # Top by Sharpe
    ranked_sharpe = sorted(results, key=lambda r: r["metrics"]["sharpe"], reverse=True)
    print("\n" + "=" * 80)
    print("  TOP 15 COMBINATIONS BY SHARPE RATIO")
    print("=" * 80)
    for i, r in enumerate(ranked_sharpe[:15], 1):
        m = r["metrics"]
        print(f"  {i:>2}. {r['name']:<40} Sharpe={m['sharpe']:>+6.2f} WR={m['win_rate']:>5.1f}% "
              f"PnL={m['total_pnl']:>+7.2f}% PF={m['profit_factor']:>5.2f} Trades={m['total_trades']:>4}")

    # Profitable combos only
    profitable = [r for r in results if r["metrics"]["total_pnl"] > 0 and r["metrics"]["total_trades"] >= 5]
    print(f"\n  === PROFITABLE COMBOS (PnL > 0, ≥5 trades): {len(profitable)} / {len(results)} ===")
    for r in sorted(profitable, key=lambda x: x["metrics"]["win_rate"], reverse=True):
        m = r["metrics"]
        print(f"    * {r['name']:<40} WR={m['win_rate']:>5.1f}% PnL={m['total_pnl']:>+7.2f}% "
              f"PF={m['profit_factor']:>5.2f} Sharpe={m['sharpe']:>+6.2f} Trades={m['total_trades']}")

    # Save results
    results_dir = Path(__file__).parent / "backtest_results"
    results_dir.mkdir(exist_ok=True)
    out_file = results_dir / "hoffman_combos.json"
    with open(out_file, "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbols": list(all_data.keys()),
            "bars_per_symbol": 1000,
            "interval": "15m",
            "total_combos": len(results),
            "profitable_combos": len(profitable),
            "results": results,
        }, f, indent=2)
    print(f"\n  Results saved to {out_file}")


if __name__ == "__main__":
    main()
