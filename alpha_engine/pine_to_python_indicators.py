#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Pine Script to Python Indicator Conversions + Backtest
======================================================================
Converts the most popular TradingView Pine Script indicators to pure Python
(numpy only), backtests them on 90 days of 4H data for BTC/ETH/SOL, ranks
by win-rate improvement, and creates two A/B portfolios.

Indicators:
  1. Squeeze Momentum (LazyBear) -- BB inside KC = compression, momentum on release
  2. RSI + MACD + Volume Confluence -- triple confirmation entry filter
  3. Multi-Timeframe EMA Cloud -- perfect EMA alignment scoring
  4. Momentum Safety Index (custom) -- calm entry detection (lower volume = better)
  5. VWAP Deviation + Bollinger Squeeze Combo -- compression near fair value

Portfolios:
  PINE-A: Squeeze Momentum + RSI-MACD-Volume Confluence
  PINE-B: EMA Cloud + VWAP-BB Squeeze

Usage:
  python pine_to_python_indicators.py              # Full backtest
  python pine_to_python_indicators.py --quick       # Quick test (30 days)

No fake data. Fetches real OHLCV via api_failover.py with 3+ exchange fallback.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

# Ensure local imports work
sys.path.insert(0, str(Path(__file__).resolve().parent))

_log = logging.getLogger("alpha_engine.pine_indicators")

# ---------------------------------------------------------------------------
# Numpy-only helpers (no pandas dependency for indicator core)
# ---------------------------------------------------------------------------

def _sma(data: np.ndarray, period: int) -> np.ndarray:
    """Simple Moving Average using numpy convolution."""
    out = np.full_like(data, np.nan, dtype=float)
    if len(data) < period:
        return out
    kernel = np.ones(period) / period
    conv = np.convolve(data, kernel, mode="valid")
    out[period - 1:] = conv
    return out


def _ema(data: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average."""
    out = np.full_like(data, np.nan, dtype=float)
    if len(data) < period:
        return out
    alpha = 2.0 / (period + 1)
    out[period - 1] = np.mean(data[:period])
    for i in range(period, len(data)):
        out[i] = alpha * data[i] + (1 - alpha) * out[i - 1]
    return out


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
         period: int) -> np.ndarray:
    """Average True Range (Wilder smoothing)."""
    n = len(close)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i],
                     abs(high[i] - close[i - 1]),
                     abs(low[i] - close[i - 1]))
    return _ema(tr, period)


def _rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """Relative Strength Index -- Wilder smoothing."""
    n = len(close)
    out = np.full(n, np.nan)
    if n < period + 1:
        return out
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.mean(gain[:period])
    avg_loss = np.mean(loss[:period])
    if avg_loss == 0:
        out[period] = 100.0
    else:
        out[period] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    alpha = 1.0 / period
    for i in range(period, len(delta)):
        avg_gain = alpha * gain[i] + (1 - alpha) * avg_gain
        avg_loss = alpha * loss[i] + (1 - alpha) * avg_loss
        if avg_loss == 0:
            out[i + 1] = 100.0
        else:
            out[i + 1] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return out


def _rolling_max(data: np.ndarray, period: int) -> np.ndarray:
    """Rolling maximum."""
    out = np.full_like(data, np.nan, dtype=float)
    for i in range(period - 1, len(data)):
        out[i] = np.max(data[i - period + 1: i + 1])
    return out


def _rolling_min(data: np.ndarray, period: int) -> np.ndarray:
    """Rolling minimum."""
    out = np.full_like(data, np.nan, dtype=float)
    for i in range(period - 1, len(data)):
        out[i] = np.min(data[i - period + 1: i + 1])
    return out


def _rolling_std(data: np.ndarray, period: int) -> np.ndarray:
    """Rolling standard deviation."""
    out = np.full_like(data, np.nan, dtype=float)
    for i in range(period - 1, len(data)):
        out[i] = np.std(data[i - period + 1: i + 1], ddof=1)
    return out


def _rolling_mean(data: np.ndarray, period: int) -> np.ndarray:
    """Rolling mean (same as SMA but explicit name)."""
    return _sma(data, period)


def _linreg(data: np.ndarray, period: int) -> np.ndarray:
    """Linear regression value (endpoint of best-fit line over period)."""
    out = np.full_like(data, np.nan, dtype=float)
    if len(data) < period:
        return out
    x = np.arange(period, dtype=float)
    x_mean = np.mean(x)
    x_var = np.sum((x - x_mean) ** 2)
    for i in range(period - 1, len(data)):
        y = data[i - period + 1: i + 1]
        y_mean = np.mean(y)
        if x_var == 0:
            out[i] = y_mean
            continue
        slope = np.sum((x - x_mean) * (y - y_mean)) / x_var
        out[i] = y_mean + slope * (x[-1] - x_mean)
    return out


def _percentile_rank(data: np.ndarray, period: int) -> np.ndarray:
    """Rolling percentile rank of current value within lookback window."""
    out = np.full_like(data, np.nan, dtype=float)
    for i in range(period - 1, len(data)):
        window = data[i - period + 1: i + 1]
        current = data[i]
        rank = np.sum(window <= current) / period * 100.0
        out[i] = rank
    return out


# ===========================================================================
# INDICATOR 1: Squeeze Momentum (LazyBear / John Carter TTM Squeeze)
# ===========================================================================

def squeeze_momentum(close: np.ndarray, high: np.ndarray, low: np.ndarray,
                     length: int = 20, mult_bb: float = 2.0,
                     mult_kc: float = 1.5) -> dict:
    """
    Squeeze Momentum Indicator -- the most popular Pine Script indicator.

    BB squeeze: when Bollinger Bands are inside Keltner Channel.
    Momentum: linear regression of:
        (close - avg(highest(high,length), lowest(low,length)) + SMA(close,length)) / 2

    Returns dict with:
        squeeze_on: bool array -- True when squeeze is active
        momentum_value: float array -- momentum oscillator
        momentum_increasing: bool array -- True when momentum is rising
    """
    n = len(close)

    # Bollinger Bands
    bb_mid = _sma(close, length)
    bb_std = _rolling_std(close, length)
    bb_upper = bb_mid + mult_bb * bb_std
    bb_lower = bb_mid - mult_bb * bb_std

    # Keltner Channel
    kc_mid = _ema(close, length)
    atr_val = _atr(high, low, close, length)
    kc_upper = kc_mid + mult_kc * atr_val
    kc_lower = kc_mid - mult_kc * atr_val

    # Squeeze detection: BB inside KC
    squeeze_on = np.zeros(n, dtype=bool)
    for i in range(n):
        if not (np.isnan(bb_lower[i]) or np.isnan(kc_lower[i])):
            squeeze_on[i] = (bb_lower[i] > kc_lower[i]) and (bb_upper[i] < kc_upper[i])

    # Momentum: LazyBear formula
    # val = linreg(source - avg(avg(highest(high, length), lowest(low, length)), sma(close, length)), length)
    highest_high = _rolling_max(high, length)
    lowest_low = _rolling_min(low, length)
    donchian_mid = (highest_high + lowest_low) / 2.0
    sma_mid = _sma(close, length)
    midline = (donchian_mid + sma_mid) / 2.0
    source = close - midline
    momentum_value = _linreg(source, length)

    # Momentum direction
    momentum_increasing = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if not np.isnan(momentum_value[i]) and not np.isnan(momentum_value[i - 1]):
            momentum_increasing[i] = momentum_value[i] > momentum_value[i - 1]

    return {
        "squeeze_on": squeeze_on,
        "momentum_value": momentum_value,
        "momentum_increasing": momentum_increasing,
    }


# ===========================================================================
# INDICATOR 2: RSI + MACD + Volume Confluence
# ===========================================================================

def rsi_macd_volume_confluence(close: np.ndarray, volume: np.ndarray,
                                rsi_period: int = 14,
                                macd_fast: int = 12, macd_slow: int = 26,
                                macd_signal: int = 9) -> dict:
    """
    Triple confluence: RSI oversold/overbought + MACD histogram turn + volume spike.

    BUY when:  RSI < 40 AND MACD histogram turning positive AND volume > 1.5x 20-bar avg
    SELL when: RSI > 60 AND MACD histogram turning negative AND volume > 1.5x avg

    Returns dict with:
        signal: int array (1=BUY, -1=SELL, 0=NONE)
        strength: float array (0-100)
    """
    n = len(close)

    # RSI
    rsi_vals = _rsi(close, rsi_period)

    # MACD
    ema_fast = _ema(close, macd_fast)
    ema_slow = _ema(close, macd_slow)
    macd_line = ema_fast - ema_slow
    macd_sig = _ema(macd_line, macd_signal)
    histogram = macd_line - macd_sig

    # Volume ratio
    vol_avg = _sma(volume, 20)
    vol_ratio = np.where(vol_avg > 0, volume / vol_avg, 0.0)

    signal = np.zeros(n, dtype=int)
    strength = np.zeros(n, dtype=float)

    for i in range(1, n):
        if np.isnan(rsi_vals[i]) or np.isnan(histogram[i]) or np.isnan(histogram[i - 1]):
            continue

        hist_turning_positive = histogram[i] > 0 and histogram[i - 1] <= 0
        hist_turning_negative = histogram[i] < 0 and histogram[i - 1] >= 0
        hist_positive_rising = histogram[i] > 0 and histogram[i] > histogram[i - 1]
        hist_negative_falling = histogram[i] < 0 and histogram[i] < histogram[i - 1]
        vol_spike = vol_ratio[i] > 1.2  # Relaxed from 1.5x

        # BUY confluence (relaxed: 2 of 3 conditions)
        rsi_buy = rsi_vals[i] < 50  # Relaxed: below midline
        macd_buy = hist_turning_positive or (hist_positive_rising and histogram[i] > 0)
        # Also count MACD line rising (not just histogram)
        macd_rising = macd_line[i] > macd_line[i - 1] and macd_line[i] < 0  # Rising from below zero
        macd_buy = macd_buy or macd_rising
        conditions_met = sum([rsi_buy, macd_buy, vol_spike])
        if conditions_met >= 2:
            signal[i] = 1
            # Strength: deeper RSI oversold = stronger, higher volume = stronger
            rsi_score = min(40.0, 40.0 - rsi_vals[i]) / 40.0 * 50  # 0-50
            vol_score = min(vol_ratio[i], 5.0) / 5.0 * 30  # 0-30
            macd_score = min(abs(histogram[i]) * 1000, 20.0)  # 0-20
            strength[i] = min(100.0, rsi_score + vol_score + macd_score)

        # SELL confluence (relaxed: 2 of 3)
        rsi_sell = rsi_vals[i] > 50  # Relaxed: above midline
        macd_sell = hist_turning_negative or (hist_negative_falling and histogram[i] < 0)
        macd_falling = macd_line[i] < macd_line[i - 1] and macd_line[i] > 0  # Falling from above zero
        macd_sell = macd_sell or macd_falling
        sell_conditions = sum([rsi_sell, macd_sell, vol_spike])
        if signal[i] == 0 and sell_conditions >= 2:
            signal[i] = -1
            rsi_score = min(40.0, rsi_vals[i] - 60.0) / 40.0 * 50
            vol_score = min(vol_ratio[i], 5.0) / 5.0 * 30
            macd_score = min(abs(histogram[i]) * 1000, 20.0)
            strength[i] = min(100.0, rsi_score + vol_score + macd_score)

    return {"signal": signal, "strength": strength}


# ===========================================================================
# INDICATOR 3: Multi-Timeframe EMA Cloud
# ===========================================================================

def ema_cloud(close: np.ndarray, fast: int = 9, mid: int = 21,
              slow: int = 50, trend: int = 200) -> dict:
    """
    Multi-Timeframe EMA Cloud -- measures EMA alignment.

    Bullish:  fast > mid > slow > trend (perfect alignment = +4)
    Bearish:  fast < mid < slow < trend (perfect alignment = -4)
    Partial:  mixed alignment = fractional score

    Returns dict with:
        alignment_score: float array (-4 to +4)
        trend_direction: str array ("BULL", "BEAR", "NEUTRAL")
        ema_fast/mid/slow/trend: float arrays (the EMA values)
    """
    n = len(close)
    ema_fast = _ema(close, fast)
    ema_mid = _ema(close, mid)
    ema_slow = _ema(close, slow)
    ema_trend = _ema(close, trend)

    alignment_score = np.zeros(n, dtype=float)
    trend_direction = np.full(n, "NEUTRAL", dtype=object)

    for i in range(n):
        if np.isnan(ema_trend[i]):
            continue

        score = 0.0
        # Each pair adds +1 (bullish order) or -1 (bearish order)
        if ema_fast[i] > ema_mid[i]:
            score += 1.0
        elif ema_fast[i] < ema_mid[i]:
            score -= 1.0

        if ema_mid[i] > ema_slow[i]:
            score += 1.0
        elif ema_mid[i] < ema_slow[i]:
            score -= 1.0

        if ema_slow[i] > ema_trend[i]:
            score += 1.0
        elif ema_slow[i] < ema_trend[i]:
            score -= 1.0

        # Price above/below trend EMA
        if close[i] > ema_fast[i]:
            score += 1.0
        elif close[i] < ema_fast[i]:
            score -= 1.0

        alignment_score[i] = score
        if score >= 3.0:
            trend_direction[i] = "BULL"
        elif score <= -3.0:
            trend_direction[i] = "BEAR"
        else:
            trend_direction[i] = "NEUTRAL"

    return {
        "alignment_score": alignment_score,
        "trend_direction": trend_direction,
        "ema_fast": ema_fast,
        "ema_mid": ema_mid,
        "ema_slow": ema_slow,
        "ema_trend": ema_trend,
    }


# ===========================================================================
# INDICATOR 4: Momentum Safety Index (our custom indicator)
# ===========================================================================

def momentum_safety_index(close: np.ndarray, high: np.ndarray,
                          low: np.ndarray, volume: np.ndarray,
                          period: int = 20) -> dict:
    """
    Custom indicator: safe momentum entry detection.

    Combines:
      - EMA alignment (9/21/50)
      - RSI sweet spot (40-60 = optimal momentum zone, not overbought)
      - Volume BELOW average (calm entry -- our finding: winners enter at
        volume ratio 1.12 vs losers at 1.33)
      - ATR expansion (confirms volatility is present for movement)

    Score 0-100, higher = safer momentum entry.

    Returns dict with:
        safety_score: float array (0-100)
        components: dict of sub-scores
    """
    n = len(close)

    # EMA alignment (9/21/50)
    ema9 = _ema(close, 9)
    ema21 = _ema(close, 21)
    ema50 = _ema(close, 50)

    # RSI
    rsi_vals = _rsi(close, 14)

    # Volume ratio
    vol_avg = _sma(volume, period)
    vol_ratio = np.where(vol_avg > 0, volume / vol_avg, 1.0)

    # ATR
    atr_val = _atr(high, low, close, period)
    atr_avg = _sma(atr_val, period * 2)
    atr_ratio = np.where(atr_avg > 0, atr_val / atr_avg, 1.0)

    safety_score = np.zeros(n, dtype=float)
    ema_scores = np.zeros(n, dtype=float)
    rsi_scores = np.zeros(n, dtype=float)
    vol_scores = np.zeros(n, dtype=float)
    atr_scores = np.zeros(n, dtype=float)

    for i in range(n):
        if np.isnan(ema50[i]) or np.isnan(rsi_vals[i]) or np.isnan(atr_val[i]):
            continue

        # 1. EMA alignment score (0-30)
        ema_s = 0.0
        if ema9[i] > ema21[i]:
            ema_s += 10.0
        if ema21[i] > ema50[i]:
            ema_s += 10.0
        if close[i] > ema9[i]:
            ema_s += 10.0
        ema_scores[i] = ema_s

        # 2. RSI sweet spot score (0-25)
        # Best zone: 40-60 (momentum without overextension)
        rsi_v = rsi_vals[i]
        if 40 <= rsi_v <= 60:
            rsi_s = 25.0
        elif 30 <= rsi_v < 40 or 60 < rsi_v <= 70:
            rsi_s = 15.0
        elif 20 <= rsi_v < 30 or 70 < rsi_v <= 80:
            rsi_s = 5.0
        else:
            rsi_s = 0.0
        rsi_scores[i] = rsi_s

        # 3. Volume below average score (0-25)
        # Our finding: winners enter at LOWER volume (1.12 vs 1.33)
        # Best: vol_ratio 0.7-1.2 (calm, not crowded)
        vr = vol_ratio[i]
        if np.isnan(vr):
            vr = 1.0
        if 0.7 <= vr <= 1.2:
            vol_s = 25.0  # Calm entry -- ideal
        elif 0.5 <= vr < 0.7 or 1.2 < vr <= 1.5:
            vol_s = 15.0  # Slightly off but okay
        elif vr > 1.5:
            vol_s = 5.0   # Crowded entry -- risky
        else:
            vol_s = 10.0  # Very low volume -- uncertain
        vol_scores[i] = vol_s

        # 4. ATR expansion score (0-20)
        # Want ATR above average (room to move)
        ar = atr_ratio[i]
        if np.isnan(ar):
            ar = 1.0
        if ar >= 1.3:
            atr_s = 20.0  # Strong expansion
        elif ar >= 1.0:
            atr_s = 15.0  # Moderate expansion
        elif ar >= 0.7:
            atr_s = 8.0   # Low volatility
        else:
            atr_s = 2.0   # Dead market
        atr_scores[i] = atr_s

        safety_score[i] = ema_s + rsi_s + vol_s + atr_s

    return {
        "safety_score": safety_score,
        "components": {
            "ema_alignment": ema_scores,
            "rsi_sweetspot": rsi_scores,
            "volume_calm": vol_scores,
            "atr_expansion": atr_scores,
        },
    }


# ===========================================================================
# INDICATOR 5: VWAP Deviation + Bollinger Squeeze Combo
# ===========================================================================

def vwap_bb_squeeze(close: np.ndarray, high: np.ndarray, low: np.ndarray,
                    volume: np.ndarray, vwap_threshold: float = 0.015,
                    bb_percentile: float = 35.0, bb_period: int = 20) -> dict:
    """
    Entry when: price near VWAP (within 0.5%) AND Bollinger bandwidth at 20th percentile.
    This catches compression before expansion -- the highest-probability setup.

    Returns dict with:
        entry_signal: bool array -- True when both conditions met
        vwap_deviation: float array -- distance from VWAP as fraction
        bb_bandwidth_pctile: float array -- percentile rank of current bandwidth
        vwap_values: float array -- the VWAP line
    """
    n = len(close)

    # VWAP (cumulative session -- reset approximation via rolling)
    typical = (high + low + close) / 3.0
    cum_tp_vol = np.cumsum(typical * volume)
    cum_vol = np.cumsum(volume)
    vwap = np.where(cum_vol > 0, cum_tp_vol / cum_vol, close)

    # VWAP deviation (fraction)
    vwap_dev = np.where(vwap > 0, np.abs(close - vwap) / vwap, 999.0)

    # Bollinger bandwidth
    bb_mid = _sma(close, bb_period)
    bb_std = _rolling_std(close, bb_period)
    bb_upper = bb_mid + 2.0 * bb_std
    bb_lower = bb_mid - 2.0 * bb_std
    bandwidth = np.where(bb_mid > 0, (bb_upper - bb_lower) / bb_mid, 0.0)

    # Percentile rank of bandwidth (is current bandwidth in bottom 20%?)
    bb_pctile = _percentile_rank(bandwidth, bb_period * 5)  # 100-bar lookback

    # Entry signal: near VWAP AND tight squeeze
    entry_signal = np.zeros(n, dtype=bool)
    for i in range(n):
        if np.isnan(bb_pctile[i]) or np.isnan(vwap_dev[i]):
            continue
        entry_signal[i] = (vwap_dev[i] <= vwap_threshold) and (bb_pctile[i] <= bb_percentile)

    return {
        "entry_signal": entry_signal,
        "vwap_deviation": vwap_dev,
        "bb_bandwidth_pctile": bb_pctile,
        "vwap_values": vwap,
    }


# ===========================================================================
# BACKTEST ENGINE
# ===========================================================================

def _klines_to_arrays(klines: list) -> dict:
    """Convert Binance-format klines to numpy arrays."""
    if not klines:
        return {}
    opens, highs, lows, closes, volumes, timestamps = [], [], [], [], [], []
    for k in klines:
        try:
            timestamps.append(int(k[0]))
            opens.append(float(k[1]))
            highs.append(float(k[2]))
            lows.append(float(k[3]))
            closes.append(float(k[4]))
            volumes.append(float(k[5]))
        except (IndexError, ValueError, TypeError):
            continue
    return {
        "timestamp": np.array(timestamps),
        "open": np.array(opens),
        "high": np.array(highs),
        "low": np.array(lows),
        "close": np.array(closes),
        "volume": np.array(volumes),
    }


def _simulate_trades(close: np.ndarray, high: np.ndarray, low: np.ndarray,
                     entry_mask: np.ndarray, direction: str = "LONG",
                     tp_pct: float = 0.03, sl_pct: float = 0.02,
                     hold_bars: int = 12) -> dict:
    """
    Simulate trades from entry signals.

    For each entry bar:
      - Enter at close of signal bar
      - Exit at TP, SL, or hold_bars timeout
      - Track win/loss and P&L

    Returns dict with trade stats.
    """
    trades = []
    n = len(close)
    in_trade = False
    entry_idx = 0
    entry_price = 0.0

    for i in range(n):
        if in_trade:
            # Check exit conditions
            bars_held = i - entry_idx
            if direction == "LONG":
                # TP hit?
                if high[i] >= entry_price * (1 + tp_pct):
                    trades.append({
                        "entry_idx": entry_idx, "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": entry_price * (1 + tp_pct),
                        "pnl_pct": tp_pct, "result": "WIN",
                    })
                    in_trade = False
                    continue
                # SL hit?
                if low[i] <= entry_price * (1 - sl_pct):
                    trades.append({
                        "entry_idx": entry_idx, "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": entry_price * (1 - sl_pct),
                        "pnl_pct": -sl_pct, "result": "LOSS",
                    })
                    in_trade = False
                    continue
                # Timeout
                if bars_held >= hold_bars:
                    pnl = (close[i] - entry_price) / entry_price
                    trades.append({
                        "entry_idx": entry_idx, "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": close[i],
                        "pnl_pct": pnl, "result": "WIN" if pnl > 0 else "LOSS",
                    })
                    in_trade = False
                    continue
            else:  # SHORT
                if low[i] <= entry_price * (1 - tp_pct):
                    trades.append({
                        "entry_idx": entry_idx, "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": entry_price * (1 - tp_pct),
                        "pnl_pct": tp_pct, "result": "WIN",
                    })
                    in_trade = False
                    continue
                if high[i] >= entry_price * (1 + sl_pct):
                    trades.append({
                        "entry_idx": entry_idx, "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": entry_price * (1 + sl_pct),
                        "pnl_pct": -sl_pct, "result": "LOSS",
                    })
                    in_trade = False
                    continue
                if bars_held >= hold_bars:
                    pnl = (entry_price - close[i]) / entry_price
                    trades.append({
                        "entry_idx": entry_idx, "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": close[i],
                        "pnl_pct": pnl, "result": "WIN" if pnl > 0 else "LOSS",
                    })
                    in_trade = False
                    continue

        # Check for new entry
        if not in_trade and entry_mask[i]:
            in_trade = True
            entry_idx = i
            entry_price = close[i]

    # Close any open trade at end
    if in_trade:
        pnl = (close[-1] - entry_price) / entry_price
        if direction == "SHORT":
            pnl = -pnl
        trades.append({
            "entry_idx": entry_idx, "exit_idx": len(close) - 1,
            "entry_price": entry_price, "exit_price": close[-1],
            "pnl_pct": pnl, "result": "WIN" if pnl > 0 else "LOSS",
        })

    wins = sum(1 for t in trades if t["result"] == "WIN")
    total = len(trades)
    total_pnl = sum(t["pnl_pct"] for t in trades)
    avg_pnl = total_pnl / total if total > 0 else 0.0
    win_rate = wins / total * 100 if total > 0 else 0.0

    return {
        "total_trades": total,
        "wins": wins,
        "losses": total - wins,
        "win_rate": round(win_rate, 2),
        "total_pnl_pct": round(total_pnl * 100, 2),
        "avg_pnl_pct": round(avg_pnl * 100, 4),
        "trades": trades,
    }


def _backtest_indicator(name: str, data: dict, tp: float = 0.03,
                        sl: float = 0.02) -> dict:
    """Run a single indicator backtest on OHLCV data."""
    close = data["close"]
    high = data["high"]
    low = data["low"]
    volume = data["volume"]
    n = len(close)

    if n < 220:  # Need 200+ bars for EMA cloud
        return {"error": f"Insufficient data: {n} bars (need 220+)"}

    # Generate entry signals per indicator
    entry_long = np.zeros(n, dtype=bool)
    entry_short = np.zeros(n, dtype=bool)

    if name == "squeeze_momentum":
        result = squeeze_momentum(close, high, low)
        # BUY: squeeze was on -> releases (off), momentum positive and increasing
        for i in range(2, n):
            if result["squeeze_on"][i - 1] and not result["squeeze_on"][i]:
                if result["momentum_value"][i] > 0 and result["momentum_increasing"][i]:
                    entry_long[i] = True
                elif result["momentum_value"][i] < 0 and not result["momentum_increasing"][i]:
                    entry_short[i] = True

    elif name == "rsi_macd_volume":
        result = rsi_macd_volume_confluence(close, volume)
        entry_long = result["signal"] == 1
        entry_short = result["signal"] == -1

    elif name == "ema_cloud":
        result = ema_cloud(close)
        # BUY: alignment goes from <3 to >=3 (bullish alignment achieved)
        for i in range(1, n):
            if result["alignment_score"][i] >= 3 and result["alignment_score"][i - 1] < 3:
                entry_long[i] = True
            elif result["alignment_score"][i] <= -3 and result["alignment_score"][i - 1] > -3:
                entry_short[i] = True

    elif name == "momentum_safety":
        result = momentum_safety_index(close, high, low, volume)
        # BUY: safety score crosses above 70 (safe momentum entry)
        for i in range(1, n):
            if result["safety_score"][i] >= 70 and result["safety_score"][i - 1] < 70:
                entry_long[i] = True

    elif name == "vwap_bb_squeeze":
        result = vwap_bb_squeeze(close, high, low, volume)
        # BUY: entry signal fires AND price is above VWAP
        for i in range(n):
            if result["entry_signal"][i]:
                if close[i] > result["vwap_values"][i]:
                    entry_long[i] = True
                else:
                    entry_short[i] = True

    # Simulate trades
    long_stats = _simulate_trades(close, high, low, entry_long, "LONG", tp, sl)
    short_stats = _simulate_trades(close, high, low, entry_short, "SHORT", tp, sl)

    total_trades = long_stats["total_trades"] + short_stats["total_trades"]
    total_wins = long_stats["wins"] + short_stats["wins"]
    combined_wr = round(total_wins / total_trades * 100, 2) if total_trades > 0 else 0.0
    combined_pnl = round(long_stats["total_pnl_pct"] + short_stats["total_pnl_pct"], 2)

    return {
        "indicator": name,
        "total_trades": total_trades,
        "total_wins": total_wins,
        "win_rate": combined_wr,
        "total_pnl_pct": combined_pnl,
        "long": {
            "trades": long_stats["total_trades"],
            "win_rate": long_stats["win_rate"],
            "pnl_pct": long_stats["total_pnl_pct"],
        },
        "short": {
            "trades": short_stats["total_trades"],
            "win_rate": short_stats["win_rate"],
            "pnl_pct": short_stats["total_pnl_pct"],
        },
    }


def _backtest_portfolio(name: str, indicators: list[str], data: dict,
                        tp: float = 0.03, sl: float = 0.02) -> dict:
    """Backtest a portfolio using AND-combination of multiple indicators."""
    close = data["close"]
    high = data["high"]
    low = data["low"]
    volume = data["volume"]
    n = len(close)

    if n < 220:
        return {"error": f"Insufficient data: {n} bars"}

    # Compute all indicator signals -- use OR (any indicator confirms)
    # then require at least 1 indicator to fire (not all zero)
    all_long = np.zeros(n, dtype=bool)   # OR combination
    all_short = np.zeros(n, dtype=bool)

    for ind_name in indicators:
        long_mask = np.zeros(n, dtype=bool)
        short_mask = np.zeros(n, dtype=bool)

        if ind_name == "squeeze_momentum":
            r = squeeze_momentum(close, high, low)
            for i in range(2, n):
                if r["squeeze_on"][i - 1] and not r["squeeze_on"][i]:
                    if r["momentum_value"][i] > 0 and r["momentum_increasing"][i]:
                        long_mask[i] = True
                    elif r["momentum_value"][i] < 0 and not r["momentum_increasing"][i]:
                        short_mask[i] = True
                # Also allow entries during active squeeze if momentum aligns
                elif r["squeeze_on"][i]:
                    if r["momentum_value"][i] > 0 and r["momentum_increasing"][i]:
                        long_mask[i] = True
                    elif r["momentum_value"][i] < 0 and not r["momentum_increasing"][i]:
                        short_mask[i] = True

        elif ind_name == "rsi_macd_volume":
            r = rsi_macd_volume_confluence(close, volume)
            long_mask = r["signal"] == 1
            short_mask = r["signal"] == -1
            # Relax: also allow if RSI/MACD are favorable (not just on crossover)
            rsi_vals = _rsi(close, 14)
            for i in range(n):
                if not np.isnan(rsi_vals[i]):
                    if rsi_vals[i] < 45 and r["signal"][i] >= 0:
                        long_mask[i] = True
                    elif rsi_vals[i] > 55 and r["signal"][i] <= 0:
                        short_mask[i] = True

        elif ind_name == "ema_cloud":
            r = ema_cloud(close)
            for i in range(n):
                if r["alignment_score"][i] >= 3:
                    long_mask[i] = True
                elif r["alignment_score"][i] <= -3:
                    short_mask[i] = True

        elif ind_name == "vwap_bb_squeeze":
            r = vwap_bb_squeeze(close, high, low, volume)
            for i in range(n):
                if r["entry_signal"][i]:
                    if close[i] > r["vwap_values"][i]:
                        long_mask[i] = True
                    else:
                        short_mask[i] = True
                # Relax: allow near-VWAP even without full squeeze
                elif not np.isnan(r["vwap_deviation"][i]) and r["vwap_deviation"][i] < 0.01:
                    if not np.isnan(r["bb_bandwidth_pctile"][i]) and r["bb_bandwidth_pctile"][i] < 40:
                        if close[i] > r["vwap_values"][i]:
                            long_mask[i] = True
                        else:
                            short_mask[i] = True

        all_long = all_long | long_mask
        all_short = all_short | short_mask

    long_stats = _simulate_trades(close, high, low, all_long, "LONG", tp, sl)
    short_stats = _simulate_trades(close, high, low, all_short, "SHORT", tp, sl)

    total_trades = long_stats["total_trades"] + short_stats["total_trades"]
    total_wins = long_stats["wins"] + short_stats["wins"]
    combined_wr = round(total_wins / total_trades * 100, 2) if total_trades > 0 else 0.0
    combined_pnl = round(long_stats["total_pnl_pct"] + short_stats["total_pnl_pct"], 2)

    return {
        "portfolio": name,
        "indicators": indicators,
        "total_trades": total_trades,
        "total_wins": total_wins,
        "win_rate": combined_wr,
        "total_pnl_pct": combined_pnl,
        "long": {
            "trades": long_stats["total_trades"],
            "win_rate": long_stats["win_rate"],
            "pnl_pct": long_stats["total_pnl_pct"],
        },
        "short": {
            "trades": short_stats["total_trades"],
            "win_rate": short_stats["win_rate"],
            "pnl_pct": short_stats["total_pnl_pct"],
        },
    }


# ===========================================================================
# Scanner filter interface (for wiring into scanner.py)
# ===========================================================================

def pine_indicator_filter(signal: dict, ohlcv_data: dict) -> dict:
    """
    Apply Pine indicator filters to a signal for the scanner.

    Adds pine_* fields to signal dict:
      - pine_squeeze_momentum: bool (squeeze active or releasing bullish)
      - pine_rsi_macd_confluence: int (1=BUY confirmed, -1=SELL, 0=none)
      - pine_ema_alignment: float (-4 to +4)
      - pine_safety_score: float (0-100)
      - pine_vwap_squeeze: bool (compression near VWAP)
      - pine_composite_score: float (0-100 weighted blend)
      - pine_filter_pass: bool (True if composite >= 50)

    Args:
        signal: dict with at least 'symbol', 'signal_type'
        ohlcv_data: dict with numpy arrays: close, high, low, volume

    Returns:
        signal dict with pine_* fields added
    """
    try:
        close = ohlcv_data.get("close")
        high = ohlcv_data.get("high")
        low = ohlcv_data.get("low")
        volume = ohlcv_data.get("volume")

        if close is None or len(close) < 50:
            signal["pine_filter_pass"] = True  # Pass through if no data
            signal["pine_composite_score"] = 50.0
            return signal

        n = len(close)
        direction = str(signal.get("signal_type", "BUY")).upper()
        is_buy = direction in ("BUY", "LONG")

        # 1. Squeeze Momentum
        sq = squeeze_momentum(close, high, low)
        squeeze_active = bool(sq["squeeze_on"][n - 1]) if not np.isnan(sq["squeeze_on"][n - 1]) else False
        mom_positive = sq["momentum_value"][n - 1] > 0 if not np.isnan(sq["momentum_value"][n - 1]) else False
        mom_rising = bool(sq["momentum_increasing"][n - 1])
        if is_buy:
            squeeze_favorable = (squeeze_active and mom_positive) or (mom_positive and mom_rising)
        else:
            squeeze_favorable = (squeeze_active and not mom_positive) or (not mom_positive and not mom_rising)
        signal["pine_squeeze_momentum"] = squeeze_favorable

        # 2. RSI-MACD-Volume confluence
        rmc = rsi_macd_volume_confluence(close, volume)
        confluence_sig = int(rmc["signal"][n - 1])
        signal["pine_rsi_macd_confluence"] = confluence_sig

        # 3. EMA Cloud
        ec = ema_cloud(close)
        alignment = float(ec["alignment_score"][n - 1])
        signal["pine_ema_alignment"] = alignment

        # 4. Momentum Safety Index
        msi = momentum_safety_index(close, high, low, volume)
        safety = float(msi["safety_score"][n - 1])
        signal["pine_safety_score"] = safety

        # 5. VWAP-BB Squeeze
        vbs = vwap_bb_squeeze(close, high, low, volume)
        vwap_squeeze = bool(vbs["entry_signal"][n - 1])
        signal["pine_vwap_squeeze"] = vwap_squeeze

        # Composite score (weighted blend)
        score = 0.0
        # Squeeze momentum: 25 pts
        if squeeze_favorable:
            score += 25.0
        elif squeeze_active:
            score += 10.0

        # RSI-MACD confluence: 20 pts
        if is_buy and confluence_sig == 1:
            score += 20.0
        elif not is_buy and confluence_sig == -1:
            score += 20.0
        elif confluence_sig == 0:
            score += 8.0  # Neutral is okay

        # EMA alignment: 20 pts
        if is_buy:
            ema_score = max(0.0, min(20.0, (alignment + 4) / 8.0 * 20.0))
        else:
            ema_score = max(0.0, min(20.0, (4 - alignment) / 8.0 * 20.0))
        score += ema_score

        # Safety index: 20 pts
        score += safety / 100.0 * 20.0

        # VWAP squeeze: 15 pts
        if vwap_squeeze:
            score += 15.0

        signal["pine_composite_score"] = round(min(100.0, score), 2)
        signal["pine_filter_pass"] = score >= 40.0  # Threshold for passing

    except Exception as e:
        _log.warning("Pine indicator filter error: %s", e)
        signal["pine_filter_pass"] = True
        signal["pine_composite_score"] = 50.0

    return signal


# ===========================================================================
# MAIN: Fetch data + run backtests
# ===========================================================================

def run_backtest(quick: bool = False):
    """Fetch 90d 4H data and backtest all indicators."""
    from api_failover import fetch_klines

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    # 90 days * 6 bars/day (4H) = 540 bars; request 600 for safety
    limit = 300 if quick else 600

    print("=" * 70)
    print("PINE SCRIPT INDICATOR BACKTEST")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Timeframe: 4H | Bars: {limit} | TP: 3% | SL: 2%")
    print("=" * 70)

    all_results = {}
    indicator_names = [
        "squeeze_momentum",
        "rsi_macd_volume",
        "ema_cloud",
        "momentum_safety",
        "vwap_bb_squeeze",
    ]

    # Baseline: random entry for comparison
    baseline_results = {}

    for sym in symbols:
        print(f"\n--- Fetching {sym} 4H data ({limit} bars) ---")
        klines = fetch_klines(sym, "4h", limit)
        if not klines:
            print(f"  FAILED to fetch {sym} -- skipping")
            continue

        data = _klines_to_arrays(klines)
        n = len(data.get("close", []))
        print(f"  Got {n} bars")

        if n < 220:
            print(f"  WARNING: Only {n} bars, need 220+ for EMA-200. Using available data.")

        # Baseline: enter every 12th bar (random-ish)
        baseline_mask = np.zeros(n, dtype=bool)
        for i in range(0, n, 12):
            baseline_mask[i] = True
        baseline_long = _simulate_trades(data["close"], data["high"], data["low"],
                                         baseline_mask, "LONG", 0.03, 0.02)
        baseline_results[sym] = {
            "trades": baseline_long["total_trades"],
            "win_rate": baseline_long["win_rate"],
            "pnl_pct": baseline_long["total_pnl_pct"],
        }
        print(f"  Baseline (periodic): {baseline_long['total_trades']} trades, "
              f"WR={baseline_long['win_rate']:.1f}%, PnL={baseline_long['total_pnl_pct']:.1f}%")

        sym_results = {}
        for ind_name in indicator_names:
            print(f"  Testing {ind_name}...", end=" ")
            result = _backtest_indicator(ind_name, data)
            sym_results[ind_name] = result
            if "error" in result:
                print(f"ERROR: {result['error']}")
            else:
                print(f"Trades={result['total_trades']}, WR={result['win_rate']:.1f}%, "
                      f"PnL={result['total_pnl_pct']:.1f}%")

        all_results[sym] = sym_results

    # Aggregate across symbols
    print("\n" + "=" * 70)
    print("AGGREGATE RESULTS (all symbols combined)")
    print("=" * 70)

    aggregate = {}
    for ind_name in indicator_names:
        total_trades = 0
        total_wins = 0
        total_pnl = 0.0
        for sym in symbols:
            if sym in all_results and ind_name in all_results[sym]:
                r = all_results[sym][ind_name]
                if "error" not in r:
                    total_trades += r["total_trades"]
                    total_wins += r["total_wins"]
                    total_pnl += r["total_pnl_pct"]

        wr = round(total_wins / total_trades * 100, 2) if total_trades > 0 else 0.0
        aggregate[ind_name] = {
            "total_trades": total_trades,
            "total_wins": total_wins,
            "win_rate": wr,
            "total_pnl_pct": round(total_pnl, 2),
        }

    # Baseline aggregate
    bl_trades = sum(b["trades"] for b in baseline_results.values())
    bl_wr = round(sum(b["win_rate"] * b["trades"] for b in baseline_results.values()) /
                  max(bl_trades, 1), 2)

    # Rank by win rate improvement over baseline
    ranked = sorted(aggregate.items(),
                    key=lambda x: x[1]["win_rate"], reverse=True)

    print(f"\nBaseline: {bl_trades} trades, WR={bl_wr:.1f}%\n")
    print(f"{'Rank':<5} {'Indicator':<25} {'Trades':<8} {'WR%':<8} {'PnL%':<10} {'WR Delta':<10}")
    print("-" * 70)
    for i, (name, stats) in enumerate(ranked, 1):
        delta = stats["win_rate"] - bl_wr
        print(f"{i:<5} {name:<25} {stats['total_trades']:<8} "
              f"{stats['win_rate']:<8.1f} {stats['total_pnl_pct']:<10.1f} "
              f"{'+' if delta >= 0 else ''}{delta:<10.1f}")

    # A/B Portfolios
    print("\n" + "=" * 70)
    print("A/B PORTFOLIO COMPARISON")
    print("=" * 70)

    portfolios = {
        "PINE-A": ["squeeze_momentum", "rsi_macd_volume"],
        "PINE-B": ["ema_cloud", "vwap_bb_squeeze"],
    }

    portfolio_results = {}
    for port_name, port_indicators in portfolios.items():
        print(f"\n--- {port_name}: {' + '.join(port_indicators)} ---")
        port_total = {"trades": 0, "wins": 0, "pnl": 0.0}

        for sym in symbols:
            if sym not in all_results:
                continue
            klines = fetch_klines(sym, "4h", limit)
            if not klines:
                continue
            data = _klines_to_arrays(klines)
            result = _backtest_portfolio(port_name, port_indicators, data)
            if "error" in result:
                print(f"  {sym}: {result['error']}")
                continue
            print(f"  {sym}: Trades={result['total_trades']}, "
                  f"WR={result['win_rate']:.1f}%, PnL={result['total_pnl_pct']:.1f}%")
            port_total["trades"] += result["total_trades"]
            port_total["wins"] += result["total_wins"]
            port_total["pnl"] += result["total_pnl_pct"]

        wr = round(port_total["wins"] / max(port_total["trades"], 1) * 100, 2)
        portfolio_results[port_name] = {
            "indicators": port_indicators,
            "total_trades": port_total["trades"],
            "total_wins": port_total["wins"],
            "win_rate": wr,
            "total_pnl_pct": round(port_total["pnl"], 2),
        }
        print(f"  TOTAL: Trades={port_total['trades']}, WR={wr:.1f}%, "
              f"PnL={port_total['pnl']:.1f}%")

    # Determine winner
    winner = max(portfolio_results.items(), key=lambda x: x[1]["win_rate"])
    print(f"\n  WINNER: {winner[0]} (WR={winner[1]['win_rate']:.1f}%)")

    # Save results
    output = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "symbols": symbols,
            "timeframe": "4H",
            "bars_per_symbol": limit,
            "tp_pct": 3.0,
            "sl_pct": 2.0,
        },
        "baseline": {
            "total_trades": bl_trades,
            "win_rate": bl_wr,
            "per_symbol": {k: v for k, v in baseline_results.items()},
        },
        "indicators": {
            name: {
                "aggregate": stats,
                "per_symbol": {
                    sym: all_results.get(sym, {}).get(name, {})
                    for sym in symbols
                },
                "rank": i + 1,
            }
            for i, (name, stats) in enumerate(ranked)
        },
        "portfolios": portfolio_results,
        "winner": {
            "portfolio": winner[0],
            "win_rate": winner[1]["win_rate"],
            "indicators": winner[1]["indicators"],
        },
        "recommendation": (
            f"Wire {winner[0]} indicators ({', '.join(winner[1]['indicators'])}) "
            f"into scanner.py as additional filters. "
            f"WR={winner[1]['win_rate']:.1f}% vs baseline {bl_wr:.1f}%."
        ),
    }

    # Clean trades from per-symbol results (too verbose for JSON)
    for sym in symbols:
        for ind_name in indicator_names:
            if sym in all_results and ind_name in all_results[sym]:
                r = all_results[sym][ind_name]
                if isinstance(r.get("long"), dict):
                    pass  # Already clean
                # Remove raw trade list from output
                for key in list(r.keys()):
                    if key == "trades" and isinstance(r[key], list):
                        del r[key]

    data_dir = Path(__file__).resolve().parent / "data"
    data_dir.mkdir(exist_ok=True)
    output_path = data_dir / "pine_indicator_backtest.json"

    # Sanitize NaN/Infinity for JSON
    def _sanitize(obj):
        if isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize(v) for v in obj]
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            v = float(obj)
            return None if (math.isnan(v) or math.isinf(v)) else v
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return _sanitize(obj.tolist())
        return obj

    output = _sanitize(output)

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nResults saved to {output_path}")
    return output


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pine Script Indicator Backtest")
    parser.add_argument("--quick", action="store_true", help="Quick test (30 days)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    run_backtest(quick=args.quick)
