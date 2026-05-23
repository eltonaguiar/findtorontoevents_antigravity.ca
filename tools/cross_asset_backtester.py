#!/usr/bin/env python3
"""
cross_asset_backtester.py — Validate strategies across all crypto pairs
======================================================================
Tests the top forward-proven strategies + inverse money-losers across the
full QuanEngine symbol universe. Outputs edge metrics per strategy/symbol.

Usage:
  python tools/cross_asset_backtester.py                          # All symbols, all strategies
  python tools/cross_asset_backtester.py --symbols BTCUSDT ETHUSDT --months 12
  python tools/cross_asset_backtester.py --save                   # Write results JSON
  python tools/cross_asset_backtester.py --inverse-only           # Only test inverse losers
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))

from hyro_backtest import fetch_candles, parse_candles, calc_sma, calc_std, calc_rsi, HYRO

# ── Symbol Universe ────────────────────────────────────────────────────────

SYMBOLS_CORE = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT",
    "XRPUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT",
]

SYMBOLS_EXTENDED = [
    "LINKUSDT", "UNIUSDT", "AAVEUSDT", "NEARUSDT", "APTUSDT",
    "SUIUSDT", "ARBUSDT", "INJUSDT", "FETUSDT", "PEPEUSDT",
    "LTCUSDT",
]

# ── Indicator helpers ──────────────────────────────────────────────────────

def calc_atr(candles: list[dict], period: int = 14) -> list:
    result = [None] * len(candles)
    if len(candles) < 2:
        return result
    trs = [candles[0]["high"] - candles[0]["low"]]
    for i in range(1, len(candles)):
        h, l, pc = candles[i]["high"], candles[i]["low"], candles[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    for i in range(period - 1, len(candles)):
        result[i] = sum(trs[i - period + 1 : i + 1]) / period
    return result


def calc_bb(candles: list[dict], period: int = 20, mult: float = 2.0):
    sma = calc_sma(candles, period)
    std = calc_std(candles, period)
    upper = [None] * len(candles)
    lower = [None] * len(candles)
    for i in range(len(candles)):
        if sma[i] is not None and std[i] is not None:
            upper[i] = sma[i] + mult * std[i]
            lower[i] = sma[i] - mult * std[i]
    return sma, upper, lower


def calc_adx(candles: list[dict], period: int = 14) -> list:
    result = [None] * len(candles)
    if len(candles) < period * 2:
        return result
    plus_dm = []
    minus_dm = []
    trs = []
    for i in range(1, len(candles)):
        h, l = candles[i]["high"], candles[i]["low"]
        ph, pl = candles[i - 1]["high"], candles[i - 1]["low"]
        pc = candles[i - 1]["close"]
        up = h - ph
        dn = pl - l
        plus_dm.append(up if up > dn and up > 0 else 0)
        minus_dm.append(dn if dn > up and dn > 0 else 0)
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))

    # Wilder smoothing
    def smooth(arr, p):
        out = [sum(arr[:p])]
        for v in arr[p:]:
            out.append(out[-1] - out[-1] / p + v)
        return out

    if len(trs) < period:
        return result
    sm_tr = smooth(trs, period)
    sm_pdm = smooth(plus_dm, period)
    sm_mdm = smooth(minus_dm, period)

    dx_vals = []
    for i in range(len(sm_tr)):
        tr = sm_tr[i]
        if tr == 0:
            dx_vals.append(0)
            continue
        pdi = 100 * sm_pdm[i] / tr
        mdi = 100 * sm_mdm[i] / tr
        s = pdi + mdi
        dx_vals.append(abs(pdi - mdi) / s * 100 if s > 0 else 0)

    if len(dx_vals) < period:
        return result
    adx = [sum(dx_vals[:period]) / period]
    for v in dx_vals[period:]:
        adx.append((adx[-1] * (period - 1) + v) / period)

    offset = 2 * period
    for i in range(len(adx)):
        idx = offset + i
        if idx < len(result):
            result[idx] = adx[i]
    return result


def calc_zscore(candles: list[dict], period: int = 50) -> list:
    sma = calc_sma(candles, period)
    std = calc_std(candles, period)
    result = [None] * len(candles)
    for i in range(len(candles)):
        if sma[i] is not None and std[i] is not None and std[i] > 0:
            result[i] = (candles[i]["close"] - sma[i]) / std[i]
    return result


def calc_hma(candles: list[dict], period: int = 20) -> list:
    """Hull Moving Average."""
    half = max(2, period // 2)
    sqrt_p = max(2, int(math.sqrt(period)))
    sma_half = calc_sma(candles, half)
    sma_full = calc_sma(candles, period)
    # 2*WMA(half) - WMA(full)
    diff = [None] * len(candles)
    for i in range(len(candles)):
        if sma_half[i] is not None and sma_full[i] is not None:
            diff[i] = 2 * sma_half[i] - sma_full[i]
    # SMA of diff over sqrt(period)
    result = [None] * len(candles)
    for i in range(sqrt_p - 1, len(candles)):
        vals = [diff[j] for j in range(i - sqrt_p + 1, i + 1) if diff[j] is not None]
        if len(vals) == sqrt_p:
            result[i] = sum(vals) / sqrt_p
    return result


# ── Strategy Implementations ──────────────────────────────────────────────


def strategy_luxalgo_breakout(candles, i, atr, rsi, sma50, bb_upper, bb_lower):
    """LuxAlgo-inspired probabilistic breakout.
    Uses z-score of price vs range + squeeze detection."""
    if i < 50 or atr[i] is None or rsi[i] is None:
        return None
    # Range (20-bar)
    highs_20 = max(c["high"] for c in candles[i - 19 : i + 1])
    lows_20 = min(c["low"] for c in candles[i - 19 : i + 1])
    price = candles[i]["close"]
    rng = highs_20 - lows_20
    if rng <= 0:
        return None

    # Volatility squeeze: ATR vs 50-bar avg ATR
    atr_vals = [atr[j] for j in range(max(0, i - 49), i + 1) if atr[j] is not None]
    if len(atr_vals) < 20:
        return None
    avg_atr = sum(atr_vals) / len(atr_vals)
    squeeze = max(0, 1 - atr[i] / avg_atr) if avg_atr > 0 else 0

    # Bull/bear probability approximation
    dist_to_high = (highs_20 - price) / rng
    dist_to_low = (price - lows_20) / rng
    bull_prob = (1 - dist_to_high) * 100  # Higher when price is near range high => breakout likely
    bear_prob = (1 - dist_to_low) * 100

    # RSI filter (avoid overbought/oversold counter-trend entries)
    if bull_prob > 55 and bull_prob > bear_prob and rsi[i] < 70 and squeeze < 0.6:
        return "LONG"
    if bear_prob > 55 and bear_prob > bull_prob and rsi[i] > 30 and squeeze < 0.6:
        return "SHORT"
    return None


def strategy_zscore_mr(candles, i, atr, rsi, zscore, adx, bb_upper, bb_lower):
    """Z-Score Mean Reversion (Kimi Claw best module, 76.9% WR p=0.015).
    LONG when z < -2.0 in ranging market, SHORT when z > 2.0."""
    if i < 50 or zscore[i] is None or atr[i] is None:
        return None
    adx_val = adx[i] if adx[i] is not None else 50  # default to trending if unknown
    # Only in ranging markets (ADX < 25)
    if adx_val > 25:
        return None
    # BB width check — squeeze condition
    if bb_upper[i] is not None and bb_lower[i] is not None:
        bb_width = bb_upper[i] - bb_lower[i]
        price = candles[i]["close"]
        if price > 0 and bb_width / price > 0.08:  # Too wide = trending
            return None
    if zscore[i] < -2.0:
        return "LONG"
    if zscore[i] > 2.0:
        return "SHORT"
    return None


def strategy_rsi_mr(candles, i, atr, rsi, sma50):
    """RSI Mean Reversion — top backtest performer (63% WR on BTC).
    Modified: RSI(14) extreme with SMA trend filter."""
    if i < 50 or rsi[i] is None or sma50[i] is None or atr[i] is None:
        return None
    price = candles[i]["close"]
    # RSI extreme + trend alignment
    if rsi[i] < 30 and price > sma50[i]:  # Oversold in uptrend
        return "LONG"
    if rsi[i] > 80 and price < sma50[i]:  # Overbought in downtrend
        return "SHORT"
    return None


def strategy_supertrend(candles, i, atr, factor=3.0, atr_period=10):
    """Supertrend indicator (ATR-based trend follower).
    Component of Kimi Claw, widely validated."""
    if i < atr_period + 1 or atr[i] is None:
        return None
    hl2 = (candles[i]["high"] + candles[i]["low"]) / 2
    upper = hl2 + factor * atr[i]
    lower = hl2 - factor * atr[i]
    # Simple directional check: close vs bands
    price = candles[i]["close"]
    prev_price = candles[i - 1]["close"]
    if price > upper and prev_price <= upper:
        return None  # band just breached — wait for confirmation
    if price > lower and candles[i - 1]["close"] > lower:
        return "LONG"
    if price < upper and candles[i - 1]["close"] < upper:
        return "SHORT"
    return None


def strategy_hma_trend(candles, i, hma):
    """HMA trend inflection — fires when Hull MA turns direction."""
    if i < 3 or hma[i] is None or hma[i - 1] is None or hma[i - 2] is None:
        return None
    if hma[i] > hma[i - 1] and hma[i - 1] <= hma[i - 2]:
        return "LONG"
    if hma[i] < hma[i - 1] and hma[i - 1] >= hma[i - 2]:
        return "SHORT"
    return None


def strategy_bb_squeeze_breakout(candles, i, atr, rsi, bb_mid, bb_upper, bb_lower):
    """Bollinger Band squeeze breakout — fires when BB compresses then price breaks out."""
    if i < 100 or atr[i] is None or bb_upper[i] is None or bb_lower[i] is None:
        return None
    price = candles[i]["close"]
    bb_width = bb_upper[i] - bb_lower[i]
    if bb_mid[i] is None or bb_mid[i] == 0:
        return None
    norm_width = bb_width / bb_mid[i]
    # Check if BB width is at 40-bar low (squeeze)
    widths = []
    for j in range(i - 39, i + 1):
        if bb_upper[j] is not None and bb_lower[j] is not None and bb_mid[j] is not None and bb_mid[j] > 0:
            widths.append((bb_upper[j] - bb_lower[j]) / bb_mid[j])
    if len(widths) < 30:
        return None
    min_width = min(widths)
    if norm_width > min_width * 1.2:  # Not in squeeze
        return None
    # Breakout direction
    vol = candles[i]["volume"]
    vol_sma = sum(c["volume"] for c in candles[i - 19 : i + 1]) / 20
    if vol < vol_sma * 1.5:  # Need volume confirmation
        return None
    if price > bb_upper[i]:
        return "LONG"
    if price < bb_lower[i]:
        return "SHORT"
    return None


def strategy_cci_divergence(candles, i, atr, cci_period=20):
    """CCI Divergence — top Hyro backtest passer (PF 2.15, 52% WR)."""
    if i < cci_period + 5 or atr[i] is None:
        return None
    # CCI = (typical - SMA) / (0.015 * mean_deviation)
    typical = [(c["high"] + c["low"] + c["close"]) / 3 for c in candles[i - cci_period + 1 : i + 1]]
    mean_tp = sum(typical) / cci_period
    mean_dev = sum(abs(t - mean_tp) for t in typical) / cci_period
    if mean_dev == 0:
        return None
    cci_now = (typical[-1] - mean_tp) / (0.015 * mean_dev)
    # Previous bar CCI
    typical_prev = [(c["high"] + c["low"] + c["close"]) / 3 for c in candles[i - cci_period : i]]
    mean_tp_prev = sum(typical_prev) / cci_period
    mean_dev_prev = sum(abs(t - mean_tp_prev) for t in typical_prev) / cci_period
    if mean_dev_prev == 0:
        return None
    cci_prev = (typical_prev[-1] - mean_tp_prev) / (0.015 * mean_dev_prev)
    # CCI cross signals
    if cci_prev < -100 and cci_now >= -100:  # Cross above -100 = long
        return "LONG"
    if cci_prev > 100 and cci_now <= 100:  # Cross below +100 = short
        return "SHORT"
    return None


def strategy_volume_breakout(candles, i, atr, rsi):
    """Volume breakout with trend confirmation."""
    if i < 50 or atr[i] is None or rsi[i] is None:
        return None
    vol = candles[i]["volume"]
    vol_sma = sum(c["volume"] for c in candles[i - 19 : i + 1]) / 20
    if vol < vol_sma * 2.0:  # Need 2x volume surge
        return None
    price = candles[i]["close"]
    prev_close = candles[i - 1]["close"]
    # Direction from price action + RSI
    if price > prev_close and rsi[i] > 50 and rsi[i] < 75:
        return "LONG"
    if price < prev_close and rsi[i] < 50 and rsi[i] > 25:
        return "SHORT"
    return None


# ── NEW STRATEGIES (Wave 2) ───────────────────────────────────────────────


def calc_rsi2(candles: list[dict]) -> list:
    """RSI with period=2 for extreme mean reversion signals."""
    return calc_rsi(candles, 2)


def calc_ema(candles: list[dict], period: int) -> list:
    """Exponential Moving Average."""
    result = [None] * len(candles)
    if len(candles) < period:
        return result
    # Seed with SMA
    s = sum(c["close"] for c in candles[:period]) / period
    result[period - 1] = s
    mult = 2.0 / (period + 1)
    for i in range(period, len(candles)):
        result[i] = candles[i]["close"] * mult + result[i - 1] * (1 - mult)
    return result


def calc_sma200(candles: list[dict]) -> list:
    return calc_sma(candles, 200)


def calc_williams_r(candles: list[dict], period: int = 14) -> list:
    """Williams %R oscillator."""
    result = [None] * len(candles)
    for i in range(period - 1, len(candles)):
        hh = max(c["high"] for c in candles[i - period + 1 : i + 1])
        ll = min(c["low"] for c in candles[i - period + 1 : i + 1])
        if hh == ll:
            result[i] = -50
        else:
            result[i] = -100 * (hh - candles[i]["close"]) / (hh - ll)
    return result


def calc_keltner(candles: list[dict], ema_period: int = 20, atr_mult: float = 2.5):
    """Keltner Channel: EMA +/- mult*ATR."""
    ema_vals = calc_ema(candles, ema_period)
    atr_vals = calc_atr(candles, ema_period)
    upper = [None] * len(candles)
    lower = [None] * len(candles)
    for i in range(len(candles)):
        if ema_vals[i] is not None and atr_vals[i] is not None:
            upper[i] = ema_vals[i] + atr_mult * atr_vals[i]
            lower[i] = ema_vals[i] - atr_mult * atr_vals[i]
    return ema_vals, upper, lower


def calc_stoch_rsi(candles: list[dict], rsi_period: int = 14, stoch_period: int = 14,
                    k_smooth: int = 3, d_smooth: int = 3):
    """Stochastic RSI: %K and %D."""
    rsi_vals = calc_rsi(candles, rsi_period)
    n = len(candles)
    stoch_k = [None] * n
    stoch_d = [None] * n
    for i in range(stoch_period - 1, n):
        window = [rsi_vals[j] for j in range(i - stoch_period + 1, i + 1) if rsi_vals[j] is not None]
        if len(window) < stoch_period:
            continue
        mn, mx = min(window), max(window)
        if mx == mn:
            stoch_k[i] = 50
        else:
            stoch_k[i] = (rsi_vals[i] - mn) / (mx - mn) * 100
    # Smooth %K
    for i in range(k_smooth - 1, n):
        vals = [stoch_k[j] for j in range(i - k_smooth + 1, i + 1) if stoch_k[j] is not None]
        if len(vals) == k_smooth:
            stoch_k[i] = sum(vals) / k_smooth
    # %D = SMA of %K
    for i in range(d_smooth - 1, n):
        vals = [stoch_k[j] for j in range(i - d_smooth + 1, i + 1) if stoch_k[j] is not None]
        if len(vals) == d_smooth:
            stoch_d[i] = sum(vals) / d_smooth
    return stoch_k, stoch_d


def calc_macd(candles: list[dict], fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD line, signal line, histogram."""
    ema_fast = calc_ema(candles, fast)
    ema_slow = calc_ema(candles, slow)
    n = len(candles)
    macd_line = [None] * n
    for i in range(n):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line[i] = ema_fast[i] - ema_slow[i]
    # Signal line = EMA of MACD line
    signal_line = [None] * n
    # Find first valid MACD
    start = None
    for i in range(n):
        if macd_line[i] is not None:
            start = i
            break
    if start is not None and start + signal <= n:
        s = sum(macd_line[i] for i in range(start, start + signal) if macd_line[i] is not None) / signal
        signal_line[start + signal - 1] = s
        mult = 2.0 / (signal + 1)
        for i in range(start + signal, n):
            if macd_line[i] is not None and signal_line[i - 1] is not None:
                signal_line[i] = macd_line[i] * mult + signal_line[i - 1] * (1 - mult)
    hist = [None] * n
    for i in range(n):
        if macd_line[i] is not None and signal_line[i] is not None:
            hist[i] = macd_line[i] - signal_line[i]
    return macd_line, signal_line, hist


def calc_consecutive_down(candles: list[dict]) -> list:
    """Count consecutive down closes."""
    result = [0] * len(candles)
    for i in range(1, len(candles)):
        if candles[i]["close"] < candles[i - 1]["close"]:
            result[i] = result[i - 1] + 1
        else:
            result[i] = 0
    return result


def calc_vci(candles: list[dict]) -> list:
    """Volatility Compression Index: std20 / std50."""
    std20 = calc_std(candles, 20)
    std50 = calc_std(candles, 50)
    result = [None] * len(candles)
    for i in range(len(candles)):
        if std20[i] is not None and std50[i] is not None and std50[i] > 0:
            result[i] = std20[i] / std50[i]
    return result


# ── Strategy 9: Connors RSI-2 Mean Reversion ─────────────────────────────

def strategy_connors_rsi2(candles, i, atr, rsi2, sma200):
    """LONG when RSI(2) < 5 and price > SMA200. 68.4% WR, Sharpe 1.17."""
    if i < 200 or rsi2[i] is None or sma200[i] is None or atr[i] is None:
        return None
    price = candles[i]["close"]
    if rsi2[i] < 5 and price > sma200[i]:
        return "LONG"
    if rsi2[i] > 95 and price < sma200[i]:
        return "SHORT"
    return None


# ── Strategy 10: Consecutive Down RSI ────────────────────────────────────

def strategy_consecutive_down(candles, i, atr, rsi, sma200, consec_down):
    """LONG on 4+ consecutive down days + RSI < 35 + above SMA200. 74.3% WR."""
    if i < 200 or rsi[i] is None or sma200[i] is None or atr[i] is None:
        return None
    price = candles[i]["close"]
    if consec_down[i] >= 4 and rsi[i] < 35 and price > sma200[i]:
        return "LONG"
    # Mirror: 4+ consecutive up + RSI > 65 + below SMA200
    if consec_down[i] == 0:
        up_count = 0
        for j in range(i, max(i - 6, 0), -1):
            if candles[j]["close"] > candles[j - 1]["close"]:
                up_count += 1
            else:
                break
        if up_count >= 4 and rsi[i] > 65 and price < sma200[i]:
            return "SHORT"
    return None


# ── Strategy 11: RSI-2 + Bollinger Squeeze ───────────────────────────────

def strategy_rsi2_bb(candles, i, atr, rsi2, sma200, bb_lower, bb_upper):
    """RSI(2) < 10 + at lower BB + above SMA200. 67.1% WR."""
    if i < 200 or rsi2[i] is None or sma200[i] is None or bb_lower[i] is None:
        return None
    price = candles[i]["close"]
    if rsi2[i] < 10 and price <= bb_lower[i] and price > sma200[i]:
        return "LONG"
    if rsi2[i] > 90 and price >= bb_upper[i] and price < sma200[i]:
        return "SHORT"
    return None


# ── Strategy 12: Williams %R Mean Reversion ──────────────────────────────

def strategy_williams_r(candles, i, atr, williams_r, sma200):
    """LONG when %R < -80 + above SMA200. 59.8% WR."""
    if i < 200 or williams_r[i] is None or sma200[i] is None or atr[i] is None:
        return None
    price = candles[i]["close"]
    if williams_r[i] < -80 and price > sma200[i]:
        return "LONG"
    if williams_r[i] > -20 and price < sma200[i]:
        return "SHORT"
    return None


# ── Strategy 13: Keltner Channel Mean Reversion ──────────────────────────

def strategy_keltner_mr(candles, i, atr, rsi, sma200, kelt_upper, kelt_lower):
    """Close at/below lower Keltner + RSI < 40 + above SMA200. 58-65% WR."""
    if i < 200 or kelt_lower[i] is None or rsi[i] is None or sma200[i] is None:
        return None
    price = candles[i]["close"]
    if price <= kelt_lower[i] and rsi[i] < 40 and price > sma200[i]:
        return "LONG"
    if price >= kelt_upper[i] and rsi[i] > 60 and price < sma200[i]:
        return "SHORT"
    return None


# ── Strategy 14: Stochastic RSI Divergence ───────────────────────────────

def strategy_stoch_rsi(candles, i, atr, rsi, sma200, stoch_k, stoch_d):
    """StochRSI %K crosses %D in oversold/overbought zones + trend filter."""
    if i < 200 or stoch_k[i] is None or stoch_d[i] is None or stoch_k[i - 1] is None:
        return None
    if rsi[i] is None or sma200[i] is None:
        return None
    price = candles[i]["close"]
    # LONG: K crosses above D, both < 20, RSI < 35, price > SMA100
    if stoch_k[i - 1] < stoch_d[i - 1] and stoch_k[i] > stoch_d[i]:
        if stoch_k[i] < 25 and rsi[i] < 40 and price > sma200[i]:
            return "LONG"
    # SHORT: K crosses below D, both > 80, RSI > 65, price < SMA100
    if stoch_k[i - 1] > stoch_d[i - 1] and stoch_k[i] < stoch_d[i]:
        if stoch_k[i] > 75 and rsi[i] > 60 and price < sma200[i]:
            return "SHORT"
    return None


# ── Strategy 15: MACD Trend Momentum ─────────────────────────────────────

def strategy_macd_trend(candles, i, atr, macd_line, macd_signal, macd_hist, ema50):
    """MACD crosses signal + EMA50 slope confirms trend."""
    if i < 60 or macd_line[i] is None or macd_signal[i] is None or ema50[i] is None:
        return None
    if macd_line[i - 1] is None or macd_signal[i - 1] is None or ema50[i - 5] is None:
        return None
    ema50_slope = (ema50[i] - ema50[i - 5]) / ema50[i - 5] if ema50[i - 5] > 0 else 0
    # LONG: MACD crosses above signal + EMA50 rising
    if macd_line[i - 1] <= macd_signal[i - 1] and macd_line[i] > macd_signal[i]:
        if ema50_slope > 0:
            return "LONG"
    # SHORT: MACD crosses below signal + EMA50 falling
    if macd_line[i - 1] >= macd_signal[i - 1] and macd_line[i] < macd_signal[i]:
        if ema50_slope < 0:
            return "SHORT"
    return None


# ── Strategy 16: ADX Range Mean Reversion ────────────────────────────────

def strategy_adx_range_mr(candles, i, atr, rsi, adx, bb_lower, bb_upper):
    """Only trade when ADX < 20 (ranging). RSI extreme + BB touch."""
    if i < 50 or adx[i] is None or rsi[i] is None or bb_lower[i] is None:
        return None
    if adx[i] >= 20:  # Only trade ranges
        return None
    price = candles[i]["close"]
    if rsi[i] < 30 and price <= bb_lower[i] * 1.005:
        return "LONG"
    if rsi[i] > 70 and price >= bb_upper[i] * 0.995:
        return "SHORT"
    return None


# ── Strategy 17: Volatility Compression Breakout (VRB from Elite v4) ────

def strategy_vol_compression(candles, i, atr, vci):
    """Volatility compression then expansion. VCI < 0.8 for 3+ bars, then breakout."""
    if i < 55 or vci[i] is None or atr[i] is None:
        return None
    # Check 3+ consecutive compressed bars before current
    compressed_count = 0
    for j in range(i - 1, max(i - 10, 0), -1):
        if vci[j] is not None and vci[j] < 0.8:
            compressed_count += 1
        else:
            break
    if compressed_count < 3:
        return None
    # Current bar should be expanding
    if vci[i] < 0.8:
        return None
    # Check for large range bar (normalized range > 1.5x ATR)
    bar_range = candles[i]["high"] - candles[i]["low"]
    if atr[i] > 0 and bar_range / atr[i] > 1.5:
        if candles[i]["close"] > candles[i]["open"]:
            return "LONG"
        elif candles[i]["close"] < candles[i]["open"]:
            return "SHORT"
    return None


# ── Strategy 18: Liquidity Sweep Reversal ────────────────────────────────

def strategy_liquidity_sweep(candles, i, atr):
    """Price sweeps swing high/low (stop hunt), then reverses."""
    if i < 25 or atr[i] is None:
        return None
    PIVOT_LEN = 10
    SWEEP_THRESH = 0.003  # 0.3%
    WICK_BODY_RATIO = 2.0

    price = candles[i]["close"]
    h, l, o = candles[i]["high"], candles[i]["low"], candles[i]["open"]
    body = abs(price - o) or 0.0001
    lower_wick = min(o, price) - l
    upper_wick = h - max(o, price)

    # Find recent swing low (within 60 bars)
    swing_low = None
    for j in range(max(PIVOT_LEN, i - 60), i - PIVOT_LEN):
        is_pivot = True
        for k in range(1, min(PIVOT_LEN + 1, j + 1)):
            if j - k < 0 or j + k >= i:
                is_pivot = False
                break
            if candles[j]["low"] > candles[j - k]["low"] or candles[j]["low"] > candles[j + k]["low"]:
                is_pivot = False
                break
        if is_pivot:
            swing_low = candles[j]["low"]

    # Find recent swing high
    swing_high = None
    for j in range(max(PIVOT_LEN, i - 60), i - PIVOT_LEN):
        is_pivot = True
        for k in range(1, min(PIVOT_LEN + 1, j + 1)):
            if j - k < 0 or j + k >= i:
                is_pivot = False
                break
            if candles[j]["high"] < candles[j - k]["high"] or candles[j]["high"] < candles[j + k]["high"]:
                is_pivot = False
                break
        if is_pivot:
            swing_high = candles[j]["high"]

    # LONG: swept below swing low, closed above, long lower wick
    if swing_low is not None:
        swept = l < swing_low * (1 - SWEEP_THRESH)
        closed_above = price > swing_low
        wick_ok = lower_wick > WICK_BODY_RATIO * body
        if swept and closed_above and wick_ok and price > o:
            return "LONG"

    # SHORT: swept above swing high, closed below, long upper wick
    if swing_high is not None:
        swept = h > swing_high * (1 + SWEEP_THRESH)
        closed_below = price < swing_high
        wick_ok = upper_wick > WICK_BODY_RATIO * body
        if swept and closed_below and wick_ok and price < o:
            return "SHORT"
    return None


# ── Strategy 19: Support/Resistance Bounce ───────────────────────────────

def strategy_sr_bounce(candles, i, atr):
    """Bounce off S/R levels identified by pivot highs/lows."""
    if i < 60 or atr[i] is None:
        return None
    tolerance = 0.5 * atr[i]
    # Find supports/resistances in last 50 bars
    supports = []
    resistances = []
    for j in range(max(5, i - 50), i - 5):
        # Pivot low
        if all(candles[j]["low"] <= candles[j + k]["low"] and
               candles[j]["low"] <= candles[j - k]["low"]
               for k in range(1, min(6, j + 1, i - j))):
            supports.append(candles[j]["low"])
        # Pivot high
        if all(candles[j]["high"] >= candles[j + k]["high"] and
               candles[j]["high"] >= candles[j - k]["high"]
               for k in range(1, min(6, j + 1, i - j))):
            resistances.append(candles[j]["high"])

    price = candles[i]["close"]
    # LONG: bouncing off support
    for sup in supports:
        if abs(candles[i]["low"] - sup) < tolerance and price > sup:
            # Check there's resistance above for target
            res_above = [r for r in resistances if r > price]
            if res_above:
                return "LONG"
    # SHORT: rejection off resistance
    for res in resistances:
        if abs(candles[i]["high"] - res) < tolerance and price < res:
            sup_below = [s for s in supports if s < price]
            if sup_below:
                return "SHORT"
    return None


# ── Strategy 20: TSMOM (Time-Series Momentum) ───────────────────────────

def strategy_tsmom(candles, i, atr, sma200):
    """Moskowitz-Grinblatt TSMOM: risk-adjusted 252-bar momentum.
    Long if score > 0.5, short if < -0.5."""
    lookback = 252
    if i < lookback + 10 or atr[i] is None:
        return None
    # 252-bar log return
    p_now = candles[i]["close"]
    p_past = candles[i - lookback]["close"]
    if p_past <= 0 or p_now <= 0:
        return None
    ret = math.log(p_now / p_past)
    # 252-bar realized vol
    log_rets = []
    for j in range(i - lookback + 1, i + 1):
        pr = candles[j - 1]["close"]
        if pr > 0:
            log_rets.append(math.log(candles[j]["close"] / pr))
    if len(log_rets) < lookback // 2:
        return None
    mean_r = sum(log_rets) / len(log_rets)
    var_r = sum((r - mean_r) ** 2 for r in log_rets) / len(log_rets)
    vol = math.sqrt(var_r * 365) if var_r > 0 else 0.001
    score = ret / vol
    if score > 0.5:
        return "LONG"
    if score < -0.5:
        return "SHORT"
    return None


# ── Strategy 21: Multi-TF Z-Score Mean Reversion (Elite v4) ──────────────

def strategy_multitf_zscore(candles, i, atr, sma200):
    """Composite Z-score from 4 simulated timeframes. Long if z < -2, short if z > 2."""
    if i < 200 or atr[i] is None or sma200[i] is None:
        return None
    price = candles[i]["close"]
    tf_params = [(5, 0.10), (10, 0.25), (20, 0.35), (40, 0.30)]
    composite_z = 0.0
    for window, weight in tf_params:
        if i < window:
            continue
        vals = [c["close"] for c in candles[i - window + 1 : i + 1]]
        mean_v = sum(vals) / window
        var_v = sum((v - mean_v) ** 2 for v in vals) / window
        std_v = math.sqrt(var_v) if var_v > 0 else 0.001
        z = (price - mean_v) / std_v
        composite_z += weight * z
    # Trend filter
    if composite_z < -2.0 and price > sma200[i]:
        return "LONG"
    if composite_z > 2.0 and price < sma200[i]:
        return "SHORT"
    return None


# ── ATR Stop Width Configurations (fix the 78.9% SL hit rate) ─────────────

SL_TP_CONFIGS = {
    "tight": {"sl_mult": 1.0, "tp_mult": 2.0},       # Original (broken)
    "normal": {"sl_mult": 1.5, "tp_mult": 2.5},       # 50% wider SL
    "wide": {"sl_mult": 2.0, "tp_mult": 3.0},         # 100% wider SL
    "ultra_wide": {"sl_mult": 2.5, "tp_mult": 4.0},   # For volatile alts
}


# ── Backtest Engine ──────────────────────────────────────────────────────

def run_backtest(
    candles: list[dict],
    strategy_fn,
    sl_mult: float = 1.5,
    tp_mult: float = 2.5,
    max_hold_bars: int = 48,
    indicators: dict | None = None,
    inverse: bool = False,
) -> dict:
    """Run a single strategy on candle data. Returns trade stats."""
    if indicators is None:
        indicators = {}
    atr = indicators.get("atr") or calc_atr(candles)
    rsi = indicators.get("rsi") or calc_rsi(candles)

    trades = []
    position = None  # {"dir", "entry", "sl", "tp", "bar_idx", "entry_bar"}

    for i in range(100, len(candles)):
        price = candles[i]["close"]

        # Check exit first
        if position is not None:
            h, l = candles[i]["high"], candles[i]["low"]
            bars_held = i - position["entry_bar"]

            # SL hit
            if position["dir"] == "LONG" and l <= position["sl"]:
                pnl_pct = (position["sl"] - position["entry"]) / position["entry"] * 100
                trades.append({"dir": position["dir"], "pnl_pct": pnl_pct, "exit": "SL",
                               "bars": bars_held, "entry_price": position["entry"]})
                position = None
            elif position["dir"] == "SHORT" and h >= position["sl"]:
                pnl_pct = (position["entry"] - position["sl"]) / position["entry"] * 100
                trades.append({"dir": position["dir"], "pnl_pct": pnl_pct, "exit": "SL",
                               "bars": bars_held, "entry_price": position["entry"]})
                position = None
            # TP hit
            elif position["dir"] == "LONG" and h >= position["tp"]:
                pnl_pct = (position["tp"] - position["entry"]) / position["entry"] * 100
                trades.append({"dir": position["dir"], "pnl_pct": pnl_pct, "exit": "TP",
                               "bars": bars_held, "entry_price": position["entry"]})
                position = None
            elif position["dir"] == "SHORT" and l <= position["tp"]:
                pnl_pct = (position["entry"] - position["tp"]) / position["entry"] * 100
                trades.append({"dir": position["dir"], "pnl_pct": pnl_pct, "exit": "TP",
                               "bars": bars_held, "entry_price": position["entry"]})
                position = None
            # Time exit
            elif bars_held >= max_hold_bars:
                if position["dir"] == "LONG":
                    pnl_pct = (price - position["entry"]) / position["entry"] * 100
                else:
                    pnl_pct = (position["entry"] - price) / position["entry"] * 100
                trades.append({"dir": position["dir"], "pnl_pct": pnl_pct, "exit": "TIME",
                               "bars": bars_held, "entry_price": position["entry"]})
                position = None

        # Check entry (only when flat)
        if position is None and atr[i] is not None and atr[i] > 0:
            signal = strategy_fn(candles, i, indicators)
            if inverse and signal is not None:
                signal = "SHORT" if signal == "LONG" else "LONG"
            if signal is not None:
                entry = price
                if signal == "LONG":
                    sl = entry - atr[i] * sl_mult
                    tp = entry + atr[i] * tp_mult
                else:
                    sl = entry + atr[i] * sl_mult
                    tp = entry - atr[i] * tp_mult
                position = {
                    "dir": signal, "entry": entry, "sl": sl, "tp": tp,
                    "entry_bar": i,
                }

    # Compute stats
    if not trades:
        return {"trades": 0, "wr": 0, "pf": 0, "avg_pnl": 0, "total_pnl": 0,
                "sl_rate": 0, "tp_rate": 0, "max_dd": 0, "trades_list": []}

    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    sl_exits = [t for t in trades if t["exit"] == "SL"]
    tp_exits = [t for t in trades if t["exit"] == "TP"]
    gross_profit = sum(t["pnl_pct"] for t in wins) if wins else 0
    gross_loss = abs(sum(t["pnl_pct"] for t in losses)) if losses else 0.001

    # Max drawdown
    equity = [0]
    for t in trades:
        equity.append(equity[-1] + t["pnl_pct"])
    peak = 0
    max_dd = 0
    for e in equity:
        peak = max(peak, e)
        max_dd = min(max_dd, e - peak)

    return {
        "trades": len(trades),
        "wr": len(wins) / len(trades) * 100,
        "pf": gross_profit / gross_loss if gross_loss > 0 else 0,
        "avg_pnl": sum(t["pnl_pct"] for t in trades) / len(trades),
        "total_pnl": sum(t["pnl_pct"] for t in trades),
        "avg_win": sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0,
        "avg_loss": sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0,
        "sl_rate": len(sl_exits) / len(trades) * 100,
        "tp_rate": len(tp_exits) / len(trades) * 100,
        "max_dd": max_dd,
        "trades_list": trades,
    }


# ── Strategy Wrapper Functions (uniform interface for backtest engine) ────

def make_luxalgo(candles, i, ind):
    return strategy_luxalgo_breakout(
        candles, i, ind["atr"], ind["rsi"], ind["sma50"],
        ind["bb_upper"], ind["bb_lower"])

def make_zscore_mr(candles, i, ind):
    return strategy_zscore_mr(
        candles, i, ind["atr"], ind["rsi"], ind["zscore"],
        ind["adx"], ind["bb_upper"], ind["bb_lower"])

def make_rsi_mr(candles, i, ind):
    return strategy_rsi_mr(candles, i, ind["atr"], ind["rsi"], ind["sma50"])

def make_supertrend(candles, i, ind):
    return strategy_supertrend(candles, i, ind["atr"])

def make_hma_trend(candles, i, ind):
    return strategy_hma_trend(candles, i, ind["hma"])

def make_bb_squeeze(candles, i, ind):
    return strategy_bb_squeeze_breakout(
        candles, i, ind["atr"], ind["rsi"],
        ind["bb_mid"], ind["bb_upper"], ind["bb_lower"])

def make_cci_div(candles, i, ind):
    return strategy_cci_divergence(candles, i, ind["atr"])

def make_vol_breakout(candles, i, ind):
    return strategy_volume_breakout(candles, i, ind["atr"], ind["rsi"])


# ── Wave 2 wrappers ──────────────────────────────────────────────────────

def make_connors_rsi2(candles, i, ind):
    return strategy_connors_rsi2(candles, i, ind["atr"], ind["rsi2"], ind["sma200"])

def make_consec_down(candles, i, ind):
    return strategy_consecutive_down(candles, i, ind["atr"], ind["rsi"], ind["sma200"], ind["consec_down"])

def make_rsi2_bb(candles, i, ind):
    return strategy_rsi2_bb(candles, i, ind["atr"], ind["rsi2"], ind["sma200"], ind["bb_lower"], ind["bb_upper"])

def make_williams_r(candles, i, ind):
    return strategy_williams_r(candles, i, ind["atr"], ind["williams_r"], ind["sma200"])

def make_keltner_mr(candles, i, ind):
    return strategy_keltner_mr(candles, i, ind["atr"], ind["rsi"], ind["sma200"], ind["kelt_upper"], ind["kelt_lower"])

def make_stoch_rsi(candles, i, ind):
    return strategy_stoch_rsi(candles, i, ind["atr"], ind["rsi"], ind["sma200"], ind["stoch_k"], ind["stoch_d"])

def make_macd_trend(candles, i, ind):
    return strategy_macd_trend(candles, i, ind["atr"], ind["macd_line"], ind["macd_signal"], ind["macd_hist"], ind["ema50"])

def make_adx_range_mr(candles, i, ind):
    return strategy_adx_range_mr(candles, i, ind["atr"], ind["rsi"], ind["adx"], ind["bb_lower"], ind["bb_upper"])

def make_vol_compression(candles, i, ind):
    return strategy_vol_compression(candles, i, ind["atr"], ind["vci"])

def make_liq_sweep(candles, i, ind):
    return strategy_liquidity_sweep(candles, i, ind["atr"])

def make_sr_bounce(candles, i, ind):
    return strategy_sr_bounce(candles, i, ind["atr"])

def make_tsmom(candles, i, ind):
    return strategy_tsmom(candles, i, ind["atr"], ind["sma200"])

def make_multitf_z(candles, i, ind):
    return strategy_multitf_zscore(candles, i, ind["atr"], ind["sma200"])


STRATEGIES = {
    # Forward-proven winners (extract core logic)
    "luxalgo_breakout": {"fn": make_luxalgo, "sl": 1.5, "tp": 2.5, "hold": 24, "category": "winner"},
    "zscore_mr": {"fn": make_zscore_mr, "sl": 1.5, "tp": 2.0, "hold": 12, "category": "winner"},
    "rsi_mr": {"fn": make_rsi_mr, "sl": 1.5, "tp": 2.5, "hold": 48, "category": "winner"},

    # Kimi Claw modules (validated components)
    "supertrend": {"fn": make_supertrend, "sl": 1.5, "tp": 2.5, "hold": 48, "category": "component"},
    "hma_trend": {"fn": make_hma_trend, "sl": 1.5, "tp": 2.5, "hold": 24, "category": "component"},

    # Hyro backtest passers
    "cci_divergence": {"fn": make_cci_div, "sl": 1.5, "tp": 2.5, "hold": 24, "category": "passer"},
    "bb_squeeze_breakout": {"fn": make_bb_squeeze, "sl": 1.5, "tp": 2.5, "hold": 24, "category": "passer"},
    "volume_breakout": {"fn": make_vol_breakout, "sl": 1.5, "tp": 2.5, "hold": 24, "category": "passer"},

    # Wave 2: Academic / baby_strategies — mean reversion focused
    "connors_rsi2": {"fn": make_connors_rsi2, "sl": 2.0, "tp": 3.0, "hold": 10, "category": "academic_mr"},
    "consecutive_down": {"fn": make_consec_down, "sl": 2.0, "tp": 3.0, "hold": 10, "category": "academic_mr"},
    "rsi2_bb_squeeze": {"fn": make_rsi2_bb, "sl": 2.0, "tp": 3.0, "hold": 10, "category": "academic_mr"},
    "williams_r_mr": {"fn": make_williams_r, "sl": 2.0, "tp": 3.0, "hold": 10, "category": "academic_mr"},
    "keltner_mr": {"fn": make_keltner_mr, "sl": 1.5, "tp": 2.0, "hold": 24, "category": "academic_mr"},
    "stoch_rsi_div": {"fn": make_stoch_rsi, "sl": 1.2, "tp": 2.5, "hold": 24, "category": "academic_mr"},

    # Wave 2: Momentum / trend
    "macd_trend": {"fn": make_macd_trend, "sl": 1.5, "tp": 2.5, "hold": 48, "category": "momentum"},
    "tsmom": {"fn": make_tsmom, "sl": 2.0, "tp": 3.0, "hold": 48, "category": "momentum"},

    # Wave 2: Structural / volatility
    "adx_range_mr": {"fn": make_adx_range_mr, "sl": 1.5, "tp": 2.0, "hold": 24, "category": "structural"},
    "vol_compression": {"fn": make_vol_compression, "sl": 1.5, "tp": 2.5, "hold": 24, "category": "structural"},
    "liquidity_sweep": {"fn": make_liq_sweep, "sl": 1.5, "tp": 2.5, "hold": 30, "category": "structural"},
    "sr_bounce": {"fn": make_sr_bounce, "sl": 1.5, "tp": 2.0, "hold": 24, "category": "structural"},
    "multitf_zscore": {"fn": make_multitf_z, "sl": 2.0, "tp": 3.0, "hold": 48, "category": "academic_mr"},
}

# Inverse candidates — strategies known to lose money in forward test
INVERSE_CANDIDATES = {
    "INV_luxalgo_breakout": {"fn": make_luxalgo, "sl": 1.5, "tp": 2.5, "hold": 24, "category": "inverse"},
    "INV_zscore_mr": {"fn": make_zscore_mr, "sl": 1.5, "tp": 2.0, "hold": 12, "category": "inverse"},
    "INV_rsi_mr": {"fn": make_rsi_mr, "sl": 1.5, "tp": 2.5, "hold": 48, "category": "inverse"},
    "INV_supertrend": {"fn": make_supertrend, "sl": 1.5, "tp": 2.5, "hold": 48, "category": "inverse"},
    "INV_hma_trend": {"fn": make_hma_trend, "sl": 1.5, "tp": 2.5, "hold": 24, "category": "inverse"},
    "INV_cci_divergence": {"fn": make_cci_div, "sl": 1.5, "tp": 2.5, "hold": 24, "category": "inverse"},
    "INV_bb_squeeze_breakout": {"fn": make_bb_squeeze, "sl": 1.5, "tp": 2.5, "hold": 24, "category": "inverse"},
    "INV_volume_breakout": {"fn": make_vol_breakout, "sl": 1.5, "tp": 2.5, "hold": 24, "category": "inverse"},
    # Wave 2 inverses
    "INV_connors_rsi2": {"fn": make_connors_rsi2, "sl": 2.0, "tp": 3.0, "hold": 10, "category": "inverse"},
    "INV_consecutive_down": {"fn": make_consec_down, "sl": 2.0, "tp": 3.0, "hold": 10, "category": "inverse"},
    "INV_rsi2_bb_squeeze": {"fn": make_rsi2_bb, "sl": 2.0, "tp": 3.0, "hold": 10, "category": "inverse"},
    "INV_williams_r_mr": {"fn": make_williams_r, "sl": 2.0, "tp": 3.0, "hold": 10, "category": "inverse"},
    "INV_keltner_mr": {"fn": make_keltner_mr, "sl": 1.5, "tp": 2.0, "hold": 24, "category": "inverse"},
    "INV_stoch_rsi_div": {"fn": make_stoch_rsi, "sl": 1.2, "tp": 2.5, "hold": 24, "category": "inverse"},
    "INV_macd_trend": {"fn": make_macd_trend, "sl": 1.5, "tp": 2.5, "hold": 48, "category": "inverse"},
    "INV_tsmom": {"fn": make_tsmom, "sl": 2.0, "tp": 3.0, "hold": 48, "category": "inverse"},
    "INV_adx_range_mr": {"fn": make_adx_range_mr, "sl": 1.5, "tp": 2.0, "hold": 24, "category": "inverse"},
    "INV_vol_compression": {"fn": make_vol_compression, "sl": 1.5, "tp": 2.5, "hold": 24, "category": "inverse"},
    "INV_liquidity_sweep": {"fn": make_liq_sweep, "sl": 1.5, "tp": 2.5, "hold": 30, "category": "inverse"},
    "INV_sr_bounce": {"fn": make_sr_bounce, "sl": 1.5, "tp": 2.0, "hold": 24, "category": "inverse"},
    "INV_multitf_zscore": {"fn": make_multitf_z, "sl": 2.0, "tp": 3.0, "hold": 48, "category": "inverse"},
}


def compute_indicators(candles: list[dict]) -> dict:
    """Precompute all indicators once per symbol."""
    macd_l, macd_s, macd_h = calc_macd(candles)
    stoch_k, stoch_d = calc_stoch_rsi(candles)
    kelt_ema, kelt_upper, kelt_lower = calc_keltner(candles)
    return {
        "atr": calc_atr(candles, 14),
        "rsi": calc_rsi(candles, 14),
        "rsi2": calc_rsi2(candles),
        "sma50": calc_sma(candles, 50),
        "sma200": calc_sma200(candles),
        "ema50": calc_ema(candles, 50),
        "bb_mid": calc_sma(candles, 20),
        "bb_upper": calc_bb(candles, 20, 2.0)[1],
        "bb_lower": calc_bb(candles, 20, 2.0)[2],
        "adx": calc_adx(candles, 14),
        "zscore": calc_zscore(candles, 50),
        "hma": calc_hma(candles, 20),
        "williams_r": calc_williams_r(candles),
        "kelt_upper": kelt_upper,
        "kelt_lower": kelt_lower,
        "stoch_k": stoch_k,
        "stoch_d": stoch_d,
        "macd_line": macd_l,
        "macd_signal": macd_s,
        "macd_hist": macd_h,
        "consec_down": calc_consecutive_down(candles),
        "vci": calc_vci(candles),
    }


def fetch_symbol_candles(symbol: str, months: int, interval: str = "1h") -> list[dict]:
    """Fetch and parse candles for a symbol."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=months * 30)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(now.timestamp() * 1000)
    raw = fetch_candles(symbol, interval, start_ms, end_ms)
    return parse_candles(raw)


def test_sl_widths(candles, strategy_fn, indicators, hold_bars):
    """Test a strategy with multiple SL widths to find optimal."""
    results = {}
    for name, cfg in SL_TP_CONFIGS.items():
        r = run_backtest(candles, strategy_fn, cfg["sl_mult"], cfg["tp_mult"],
                         hold_bars, indicators)
        results[name] = r
    return results


def main():
    ap = argparse.ArgumentParser(description="Cross-asset strategy backtester")
    ap.add_argument("--symbols", nargs="+", default=None,
                    help="Symbols to test (default: CORE + EXTENDED)")
    ap.add_argument("--months", type=int, default=6, help="Lookback months")
    ap.add_argument("--interval", default="1h")
    ap.add_argument("--save", action="store_true", help="Write results JSON")
    ap.add_argument("--inverse-only", action="store_true", help="Only test inverse strategies")
    ap.add_argument("--test-sl-widths", action="store_true", help="Test multiple SL widths")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    symbols = args.symbols or (SYMBOLS_CORE + SYMBOLS_EXTENDED)
    strategies_to_test = {}
    if not args.inverse_only:
        strategies_to_test.update(STRATEGIES)
    strategies_to_test.update(INVERSE_CANDIDATES)

    all_results = {}
    symbol_data = {}

    print(f"=== Cross-Asset Backtester ===")
    print(f"Symbols: {len(symbols)} | Strategies: {len(strategies_to_test)} | Months: {args.months}")
    print(f"Interval: {args.interval} | SL width test: {args.test_sl_widths}")
    print()

    # Fetch all candle data first
    for sym in symbols:
        print(f"Fetching {sym}...", end=" ", flush=True)
        try:
            candles = fetch_symbol_candles(sym, args.months, args.interval)
            if len(candles) < 200:
                print(f"SKIP (only {len(candles)} bars)")
                continue
            indicators = compute_indicators(candles)
            symbol_data[sym] = {"candles": candles, "indicators": indicators}
            print(f"OK ({len(candles)} bars)")
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(0.2)

    print(f"\nLoaded {len(symbol_data)}/{len(symbols)} symbols. Running backtests...\n")

    # Run all strategies × symbols
    for strat_name, strat_cfg in strategies_to_test.items():
        is_inverse = strat_name.startswith("INV_")
        strat_results = {}

        for sym, data in symbol_data.items():
            if args.test_sl_widths and not is_inverse:
                width_results = test_sl_widths(
                    data["candles"], strat_cfg["fn"], data["indicators"], strat_cfg["hold"])
                # Pick best SL width by PF
                best_width = max(width_results.items(), key=lambda x: x[1].get("pf", 0))
                r = best_width[1]
                r["best_sl_config"] = best_width[0]
                r["sl_width_comparison"] = {
                    k: {"wr": v["wr"], "pf": v["pf"], "trades": v["trades"],
                         "sl_rate": v["sl_rate"], "avg_pnl": v["avg_pnl"]}
                    for k, v in width_results.items()
                }
            else:
                r = run_backtest(
                    data["candles"], strat_cfg["fn"],
                    strat_cfg["sl"], strat_cfg["tp"], strat_cfg["hold"],
                    data["indicators"], inverse=is_inverse)

            # Remove trade list from output (too large)
            r.pop("trades_list", None)
            strat_results[sym] = r

            if args.verbose and r["trades"] > 0:
                tag = "INV" if is_inverse else "   "
                edge = "EDGE" if r["pf"] > 1.2 and r["wr"] > 40 else "    "
                print(f"  {tag} {strat_name:<25} {sym:<10} T={r['trades']:>4} "
                      f"WR={r['wr']:>5.1f}% PF={r['pf']:>5.2f} "
                      f"avg={r['avg_pnl']:>+6.2f}% SL%={r['sl_rate']:>5.1f}% {edge}")

        # Aggregate across symbols
        total_trades = sum(r["trades"] for r in strat_results.values())
        if total_trades > 0:
            agg_pnl = sum(r["total_pnl"] for r in strat_results.values())
            agg_wins = sum(r["trades"] * r["wr"] / 100 for r in strat_results.values())
            agg_wr = agg_wins / total_trades * 100
            # PF from per-symbol avg_win * wins vs avg_loss * losses (more accurate)
            gross_p = sum(r.get("avg_win", 0) * r["trades"] * r["wr"] / 100
                          for r in strat_results.values())
            gross_l = abs(sum(r.get("avg_loss", 0) * r["trades"] * (100 - r["wr"]) / 100
                              for r in strat_results.values())) or 0.001
            agg_pf = gross_p / gross_l

            all_results[strat_name] = {
                "category": strat_cfg["category"],
                "agg_trades": total_trades,
                "agg_wr": round(agg_wr, 1),
                "agg_pf": round(agg_pf, 2),
                "agg_avg_pnl": round(agg_pnl / total_trades, 3),
                "agg_total_pnl": round(agg_pnl, 2),
                "symbols_tested": len(strat_results),
                "symbols_with_edge": sum(1 for r in strat_results.values() if r["pf"] > 1.2 and r["wr"] > 40),
                "per_symbol": {k: {kk: round(vv, 3) if isinstance(vv, float) else vv
                                    for kk, vv in v.items()} for k, v in strat_results.items()},
            }

    # Print summary
    print("\n" + "=" * 90)
    print(f"{'STRATEGY':<28} {'CAT':<10} {'TRADES':>7} {'WR%':>6} {'PF':>6} "
          f"{'AVG PNL':>8} {'TOTAL':>8} {'EDGE SYM':>8}")
    print("=" * 90)

    sorted_results = sorted(all_results.items(), key=lambda x: x[1]["agg_pf"], reverse=True)
    for name, r in sorted_results:
        edge_marker = " ***" if r["agg_pf"] > 1.3 and r["agg_wr"] > 45 else ""
        inv_marker = " [INVERSE EDGE!]" if name.startswith("INV_") and r["agg_pf"] > 1.3 else ""
        print(f"{name:<28} {r['category']:<10} {r['agg_trades']:>7} {r['agg_wr']:>5.1f}% "
              f"{r['agg_pf']:>6.2f} {r['agg_avg_pnl']:>+7.3f}% {r['agg_total_pnl']:>+8.1f}% "
              f"{r['symbols_with_edge']:>3}/{r['symbols_tested']}{edge_marker}{inv_marker}")

    # DNA Mutation suggestions
    print("\n--- DNA MUTATION CANDIDATES ---")
    for name, r in sorted_results:
        if r["agg_pf"] < 0.8 and r["agg_trades"] > 30 and not name.startswith("INV_"):
            inv_name = f"INV_{name}"
            inv_r = all_results.get(inv_name)
            if inv_r and inv_r["agg_pf"] > 1.0:
                print(f"  {name}: PF={r['agg_pf']:.2f} -> INVERSE PF={inv_r['agg_pf']:.2f} "
                      f"WR={inv_r['agg_wr']:.1f}% *** RECOMMEND INVERSE ***")
            else:
                print(f"  {name}: PF={r['agg_pf']:.2f} — inverse not profitable either. "
                      f"Consider parameter mutation or retirement.")

    # Optimal SL width recommendations
    if args.test_sl_widths:
        print("\n--- SL WIDTH OPTIMIZATION ---")
        for name, r in sorted_results:
            if name.startswith("INV_"):
                continue
            for sym, sym_r in r.get("per_symbol", {}).items():
                if "sl_width_comparison" in sym_r:
                    print(f"  {name} × {sym}: best={sym_r.get('best_sl_config','?')}")
                    for w, wr in sym_r["sl_width_comparison"].items():
                        print(f"    {w}: WR={wr['wr']:.1f}% PF={wr['pf']:.2f} "
                              f"SL%={wr['sl_rate']:.0f}% T={wr['trades']}")

    if args.save:
        out_path = _ROOT / "backtest_results" / "cross_asset_validation.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "config": {
                "symbols": list(symbol_data.keys()),
                "months": args.months,
                "interval": args.interval,
                "test_sl_widths": args.test_sl_widths,
            },
            "results": all_results,
        }
        with open(out_path, "w") as f:
            json.dump(payload, f, indent=2, default=str)
        print(f"\nWrote {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
