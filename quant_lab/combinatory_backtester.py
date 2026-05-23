#!/usr/bin/env python3
"""
Combinatory Backtester — Tests failing strategies with regime filters,
inverse logic, and winner+loser ensembles.

Theory: Strategies that CONSISTENTLY lose may be valuable as:
  1. Pure inverse signals (flip BUY→SELL)
  2. Confirmation filters (only enter when a loser DISAGREES)
  3. Regime-gated signals (loser works in specific regimes)
  4. Ensemble components (combine multiple weak signals)

Outputs a portfolio of hypothetical positions with:
  - Entry/exit prices, TP/SL
  - Entry/exit date+time (EST)
  - PnL per trade
  - Strategy combination that generated it

Usage:
    py quant_lab/combinatory_backtester.py
    py quant_lab/combinatory_backtester.py --symbols BTC/USDT ETH/USDT
    py quant_lab/combinatory_backtester.py --export results.json
"""

import sqlite3
import json
import sys
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "crypto_data.db"
OUTPUT_DIR = ROOT / "quant_lab" / "combo_results"

# ─────────────────────────────────────────────────────────────────
# Technical Indicators
# ─────────────────────────────────────────────────────────────────

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False).mean()


def sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(period).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def bollinger_bands(close: pd.Series, period: int = 20, num_std: float = 2.0):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    return mid + num_std * std, mid, mid - num_std * std


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr_s = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr_s)
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr_s)
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    return dx.ewm(span=period, adjust=False).mean()


def hurst_exponent(close: pd.Series, max_lag: int = 20) -> float:
    """Simplified R/S Hurst exponent."""
    returns = np.log(close / close.shift(1)).dropna().values
    if len(returns) < 100:
        return 0.5
    lags = [2, 4, 8, 16, 32, 64]
    lags = [l for l in lags if l < len(returns) // 2]
    if len(lags) < 3:
        return 0.5
    rs_values = []
    for lag in lags:
        rs_list = []
        n_chunks = len(returns) // lag
        for i in range(n_chunks):
            chunk = returns[i*lag:(i+1)*lag]
            mean_r = np.mean(chunk)
            dev = np.cumsum(chunk - mean_r)
            R = np.max(dev) - np.min(dev)
            S = np.std(chunk, ddof=1) if np.std(chunk, ddof=1) > 0 else 1e-10
            rs_list.append(R / S)
        rs_values.append(np.mean(rs_list))
    log_lags = np.log(lags)
    log_rs = np.log(np.array(rs_values) + 1e-10)
    slope, _ = np.polyfit(log_lags, log_rs, 1)
    return max(0.0, min(1.0, slope))


def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
    return volume / volume.rolling(period).mean()


# ─────────────────────────────────────────────────────────────────
# Regime Detection
# ─────────────────────────────────────────────────────────────────

def detect_regime(close: pd.Series, high: pd.Series, low: pd.Series,
                  volume: pd.Series) -> dict:
    """Detect current market regime from price data."""
    if len(close) < 200:
        return {"regime": "UNKNOWN", "hurst": 0.5, "adx": 20, "vol_regime": "NORMAL"}

    h = hurst_exponent(close.tail(200))
    adx_val = float(adx(high, low, close, 14).iloc[-1]) if not np.isnan(adx(high, low, close, 14).iloc[-1]) else 20

    # Trend detection
    roc_20d = (float(close.iloc[-1]) / float(close.iloc[-21]) - 1) * 100 if len(close) > 21 else 0

    # Volatility regime
    atr_val = atr(high, low, close, 14)
    atr_ratio = float(atr_val.iloc[-1] / atr_val.rolling(60).mean().iloc[-1]) if len(atr_val) > 60 else 1.0

    # Drawdown from peak
    peak = float(close.rolling(30).max().iloc[-1])
    dd = (float(close.iloc[-1]) / peak - 1) * 100

    if dd < -15:
        regime = "CRISIS"
    elif atr_ratio > 2.0:
        regime = "HIGH_VOLATILITY"
    elif atr_ratio < 0.5:
        regime = "LOW_VOLATILITY"
    elif h > 0.65 and adx_val > 25:
        regime = "TRENDING_UP" if roc_20d > 0 else "TRENDING_DOWN"
    elif h < 0.40:
        regime = "MEAN_REVERTING"
    else:
        regime = "NEUTRAL"

    vol_regime = "HIGH" if atr_ratio > 1.5 else "LOW" if atr_ratio < 0.7 else "NORMAL"

    return {
        "regime": regime,
        "hurst": round(h, 4),
        "adx": round(adx_val, 2),
        "roc_20d": round(roc_20d, 2),
        "atr_ratio": round(atr_ratio, 4),
        "drawdown": round(dd, 2),
        "vol_regime": vol_regime,
    }


# ─────────────────────────────────────────────────────────────────
# Failing Strategy Signal Generators (Reimplemented for backtest)
# ─────────────────────────────────────────────────────────────────

def sig_halloween_effect(close, high, low, volume, i):
    """Halloween: BUY Nov-Apr, SELL May-Oct."""
    if i < 50:
        return 0
    # In backtest we use bar index as proxy for month
    # We'll use actual timestamp if available, fallback to index
    return 0  # Will be set from timestamp


def sig_monthly_seasonality(close, high, low, volume, i, month):
    """Monthly seasonality scores for crypto."""
    scores = {1:0.40, 2:0.25, 3:-0.10, 4:0.50, 5:-0.20, 6:-0.30,
              7:0.15, 8:-0.15, 9:-0.60, 10:0.85, 11:0.70, 12:0.55}
    score = scores.get(month, 0)
    rsi_val = rsi(close[:i+1], 14).iloc[-1]
    if np.isnan(rsi_val):
        return 0
    if score >= 0.25 and rsi_val <= 72:
        return 1  # BUY
    elif score <= -0.25 and rsi_val >= 28:
        return -1  # SELL
    return 0


def sig_fourier_cycle(close, high, low, volume, i):
    """FFT cycle detector — phase-based entry."""
    if i < 120:
        return 0
    window = close[i-120:i+1].values
    # Detrend
    x = np.arange(len(window))
    coeffs = np.polyfit(x, window, 1)
    detrended = window - np.polyval(coeffs, x)
    # Window
    hann = np.hanning(len(detrended))
    windowed = detrended * hann
    # FFT
    fft_vals = np.fft.rfft(windowed)
    power = np.abs(fft_vals) ** 2
    freqs = np.fft.rfftfreq(len(windowed))
    # Find dominant cycle (5-90 bars)
    valid = (freqs > 1/90) & (freqs < 1/5) & (np.arange(len(freqs)) > 0)
    if not valid.any():
        return 0
    valid_power = power.copy()
    valid_power[~valid] = 0
    dom_idx = np.argmax(valid_power)
    if valid_power[dom_idx] < 1.5 * np.mean(power[1:]):
        return 0
    period = 1 / freqs[dom_idx] if freqs[dom_idx] > 0 else 60
    phase = (i % period) / period
    # Adjust by FFT angle
    angle = np.angle(fft_vals[dom_idx])
    phase = (phase + angle / (2 * np.pi)) % 1.0
    # BUY at trough, SELL at peak
    if 0.7 <= phase or phase <= 0.1:
        return 1
    elif 0.4 <= phase <= 0.6:
        return -1
    return 0


def sig_smart_money_fvg(close, high, low, volume, i):
    """Fair Value Gap detection — bullish FVG fill bounce."""
    if i < 20:
        return 0
    # Find FVGs in last 20 bars
    price = float(close.iloc[i])
    for j in range(max(1, i-20), i-1):
        # Bullish FVG: gap between bar[j-1] high and bar[j+1] low
        gap_low = float(high.iloc[j-1])
        gap_high = float(low.iloc[j+1])
        if gap_high <= gap_low:
            continue
        gap_pct = (gap_high - gap_low) / gap_low
        if gap_pct < 0.005:
            continue
        # Price in FVG zone?
        if gap_low * 0.98 <= price <= gap_high * 1.02:
            # Bullish candle
            if float(close.iloc[i]) > float(close.iloc[i-1]):
                rsi_val = rsi(close[:i+1], 14).iloc[-1]
                if not np.isnan(rsi_val) and rsi_val <= 70:
                    return 1
    return 0


def sig_exchange_netflow(close, high, low, volume, i):
    """BB squeeze + declining volume proxy for accumulation."""
    if i < 50:
        return 0
    bb_upper, bb_mid, bb_lower = bollinger_bands(close[:i+1], 20, 2.0)
    bw = float((bb_upper.iloc[-1] - bb_lower.iloc[-1]) / bb_mid.iloc[-1]) if float(bb_mid.iloc[-1]) > 0 else 0
    avg_bw = float(((bb_upper - bb_lower) / bb_mid).rolling(50).mean().iloc[-1])
    if np.isnan(avg_bw) or avg_bw == 0:
        return 0
    # Squeeze: bandwidth < 70% of average
    if bw >= avg_bw * 0.70:
        return 0
    # Volume declining
    vol_sma = float(volume[:i+1].rolling(20).mean().iloc[-1])
    if vol_sma == 0:
        return 0
    vol_trend = float(volume.iloc[i]) / vol_sma
    if vol_trend > 1.1:
        return 0
    # RSI neutral
    rsi_val = rsi(close[:i+1], 14).iloc[-1]
    if np.isnan(rsi_val) or not (35 <= rsi_val <= 65):
        return 0
    # Price above 20d SMA support
    sma20 = float(sma(close[:i+1], 20).iloc[-1])
    if float(close.iloc[i]) < sma20 * 0.98:
        return 0
    return 1  # BUY


def sig_price_touch_recurrence(close, high, low, volume, i):
    """Price level magnet — S/R touch detection."""
    if i < 30:
        return 0
    window = 30
    price = float(close.iloc[i])
    # Find candidate levels (round numbers + local extremes)
    levels = []
    step = price * 0.005
    if step > 0:
        rounded = round(price / step) * step
        levels.extend([rounded - step, rounded, rounded + step])
    # Local highs/lows
    for j in range(max(1, i-window), i-1):
        if float(high.iloc[j]) > float(high.iloc[j-1]) and float(high.iloc[j]) > float(high.iloc[j+1]):
            levels.append(float(high.iloc[j]))
        if float(low.iloc[j]) < float(low.iloc[j-1]) and float(low.iloc[j]) < float(low.iloc[j+1]):
            levels.append(float(low.iloc[j]))
    # Count touches
    tolerance = price * 0.005
    for level in levels:
        touches = 0
        for j in range(max(0, i-window), i+1):
            if abs(float(high.iloc[j]) - level) < tolerance or abs(float(low.iloc[j]) - level) < tolerance:
                touches += 1
        if touches >= 3:
            distance = abs(price - level)
            if distance < price * 0.02:
                if price > level:  # Support magnet
                    return 1
                else:  # Resistance magnet
                    return -1
    return 0


def sig_momentum_mean_rev_blend(close, high, low, volume, i):
    """Momentum + BTC-neutral mean reversion blend."""
    if i < 60:
        return 0
    returns = close[:i+1].pct_change().dropna()
    if len(returns) < 28:
        return 0
    ret_7d = float(close.iloc[i] / close.iloc[max(0,i-7)] - 1)
    returns_28 = returns.tail(28)
    mean_r = float(returns_28.mean())
    std_r = float(returns_28.std())
    if std_r == 0:
        return 0
    momentum_z = (ret_7d - mean_r) / std_r
    # Momentum leg: z > 1.0 = bullish
    momentum_bull = momentum_z > 1.0
    momentum_bear = momentum_z < -1.0
    # Mean reversion leg (simplified — no BTC beta in backtest)
    rsi_val = rsi(close[:i+1], 14).iloc[-1]
    if np.isnan(rsi_val):
        return 0
    mr_bull = rsi_val < 30  # oversold
    mr_bear = rsi_val > 70  # overbought
    if momentum_bull or mr_bull:
        return 1
    elif momentum_bear or mr_bear:
        return -1
    return 0


def sig_altcoin_season(close, high, low, volume, i, btc_close=None):
    """Altcoin season rotation — alt outperformance."""
    if i < 10 or btc_close is None or len(btc_close) <= i:
        return 0
    alt_7d = float(close.iloc[i] / close.iloc[max(0,i-7)] - 1)
    btc_7d = float(btc_close.iloc[i] / btc_close.iloc[max(0,i-7)] - 1)
    outperformance = alt_7d - btc_7d
    if outperformance >= 0.04:
        rsi_val = rsi(close[:i+1], 14).iloc[-1]
        if not np.isnan(rsi_val) and rsi_val <= 75:
            return 1
    return 0


def sig_ict_fvg_selective(close, high, low, volume, i):
    """ICT FVG in discount zone with ADX filter."""
    if i < 20:
        return 0
    price = float(close.iloc[i])
    # Discount zone: below 50% of 20-bar range
    range_high = float(high[max(0,i-20):i].max())
    range_low = float(low[max(0,i-20):i].min())
    mid = (range_high + range_low) / 2
    if price >= mid:  # Not in discount
        return 0
    # ADX > 20
    adx_val = adx(high[:i+1], low[:i+1], close[:i+1], 14).iloc[-1]
    if np.isnan(adx_val) or adx_val <= 20:
        return 0
    # RSI < 45
    rsi_val = rsi(close[:i+1], 14).iloc[-1]
    if np.isnan(rsi_val) or rsi_val >= 45:
        return 0
    # Look for FVG
    for j in range(max(1, i-10), i-1):
        gap_low = float(high.iloc[j-1])
        gap_high = float(low.iloc[j+1])
        if gap_high <= gap_low:
            continue
        gap_pct = (gap_high - gap_low) / gap_low
        if gap_pct < 0.005:
            continue
        age = i - j
        if age < 5:
            continue
        if gap_low * 0.98 <= price <= gap_high * 1.02:
            if float(close.iloc[i]) > float(close.iloc[i-1]):
                return 1
    return 0


# ─────────────────────────────────────────────────────────────────
# Winning Strategy Signal Generators
# ─────────────────────────────────────────────────────────────────

def sig_autocorrelation(close, high, low, volume, i):
    """Autocorrelation exploiter — momentum/reversal at significant lags."""
    if i < 120:
        return 0
    returns = np.log(close[i-120:i+1] / close[i-120:i+1].shift(1)).dropna().values
    if len(returns) < 100:
        return 0
    threshold = 1.96 / np.sqrt(len(returns))
    best_ac = 0
    best_lag = 1
    for lag in [1, 2, 3, 5, 10]:
        if lag >= len(returns):
            continue
        r1 = returns[lag:]
        r2 = returns[:-lag]
        if len(r1) < 10:
            continue
        ac = np.corrcoef(r1, r2)[0, 1]
        if abs(ac) > abs(best_ac) and abs(ac) > threshold:
            best_ac = ac
            best_lag = lag
    if best_ac == 0:
        return 0
    lag_return = float(close.iloc[i] / close.iloc[max(0, i-best_lag)] - 1)
    if best_ac > 0:  # Momentum
        return 1 if lag_return > 0 else -1
    else:  # Reversal
        return -1 if lag_return > 0 else 1


def sig_multi_sigma_reversal(close, high, low, volume, i):
    """Multi-sigma reversal — Z > 2.5 mean reversion."""
    if i < 100:
        return 0
    returns = close[:i+1].pct_change().dropna()
    if len(returns) < 50:
        return 0
    tail = returns.tail(100)
    mean_r = float(tail.mean())
    std_r = float(tail.std())
    if std_r == 0:
        return 0
    z = (float(returns.iloc[-1]) - mean_r) / std_r
    if z < -2.5:
        return 1  # Extreme selloff → BUY
    elif z > 2.5:
        return -1  # Extreme rally → SELL
    return 0


def sig_hurst_regime(close, high, low, volume, i):
    """Hurst regime adaptive — RSI-2 in MR, EMA cross in trending."""
    if i < 200:
        return 0
    h = hurst_exponent(close[i-200:i+1])
    if h < 0.40:  # Mean reverting
        r2 = rsi(close[:i+1], 2).iloc[-1]
        if np.isnan(r2):
            return 0
        if r2 < 10:
            return 1
        elif r2 > 90:
            return -1
    elif h > 0.65:  # Trending
        ema9 = ema(close[:i+1], 9).iloc[-1]
        ema21 = ema(close[:i+1], 21).iloc[-1]
        ema9_prev = ema(close[:i], 9).iloc[-1]
        ema21_prev = ema(close[:i], 21).iloc[-1]
        if ema9 > ema21 and ema9_prev <= ema21_prev:
            return 1
        elif ema9 < ema21 and ema9_prev >= ema21_prev:
            return -1
    return 0


def sig_volume_profile(close, high, low, volume, i):
    """Volume profile value area — trade at VAL/VAH extremes."""
    if i < 30:
        return 0
    lookback = min(30, i)
    c_slice = close[i-lookback:i+1].values
    h_slice = high[i-lookback:i+1].values
    l_slice = low[i-lookback:i+1].values
    v_slice = volume[i-lookback:i+1].values
    price_min = l_slice.min()
    price_max = h_slice.max()
    if price_max <= price_min:
        return 0
    n_bins = 50
    bin_edges = np.linspace(price_min, price_max, n_bins + 1)
    bin_vol = np.zeros(n_bins)
    for j in range(len(c_slice)):
        bar_lo = l_slice[j]
        bar_hi = h_slice[j]
        bar_vol = v_slice[j]
        bar_height = bar_hi - bar_lo if bar_hi > bar_lo else 0.001
        for b in range(n_bins):
            overlap = max(0, min(bar_hi, bin_edges[b+1]) - max(bar_lo, bin_edges[b]))
            if overlap > 0:
                bin_vol[b] += bar_vol * (overlap / bar_height)
    poc_idx = np.argmax(bin_vol)
    total_vol = bin_vol.sum()
    if total_vol == 0:
        return 0
    # Expand from POC for 70% value area
    va_vol = bin_vol[poc_idx]
    lo_idx = poc_idx
    hi_idx = poc_idx
    while va_vol < 0.70 * total_vol:
        expand_lo = bin_vol[lo_idx - 1] if lo_idx > 0 else 0
        expand_hi = bin_vol[hi_idx + 1] if hi_idx < n_bins - 1 else 0
        if expand_lo >= expand_hi and lo_idx > 0:
            lo_idx -= 1
            va_vol += bin_vol[lo_idx]
        elif hi_idx < n_bins - 1:
            hi_idx += 1
            va_vol += bin_vol[hi_idx]
        else:
            break
    val = bin_edges[lo_idx]
    vah = bin_edges[hi_idx + 1]
    atr_val = float(atr(high[:i+1], low[:i+1], close[:i+1], 14).iloc[-1])
    price = float(close.iloc[i])
    if price < val - atr_val:
        return 1  # Below value area → BUY
    elif price > vah + atr_val:
        return -1  # Above value area → SELL
    return 0


# ─────────────────────────────────────────────────────────────────
# Regime Filters (applied ON TOP of signals)
# ─────────────────────────────────────────────────────────────────

REGIME_FILTERS = {
    "no_filter": lambda sig, regime: sig,
    "crisis_only": lambda sig, regime: sig if regime["regime"] == "CRISIS" else 0,
    "trending_only": lambda sig, regime: sig if regime["regime"].startswith("TRENDING") else 0,
    "mean_rev_only": lambda sig, regime: sig if regime["regime"] == "MEAN_REVERTING" else 0,
    "high_vol_only": lambda sig, regime: sig if regime["vol_regime"] == "HIGH" else 0,
    "low_vol_only": lambda sig, regime: sig if regime["vol_regime"] == "LOW" else 0,
    "not_crisis": lambda sig, regime: sig if regime["regime"] != "CRISIS" else 0,
    "hurst_trending": lambda sig, regime: sig if regime["hurst"] > 0.60 else 0,
    "hurst_mr": lambda sig, regime: sig if regime["hurst"] < 0.40 else 0,
    "strong_trend": lambda sig, regime: sig if regime["adx"] > 30 else 0,
    "weak_trend": lambda sig, regime: sig if regime["adx"] < 20 else 0,
}


# ─────────────────────────────────────────────────────────────────
# Trade Simulation
# ─────────────────────────────────────────────────────────────────

@dataclass
class Trade:
    symbol: str
    strategy: str
    combo_name: str
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    take_profit: float
    stop_loss: float
    entry_time: str  # EST
    exit_time: str   # EST
    exit_price: float
    pnl_pct: float
    exit_reason: str  # "TP", "SL", "TIME_EXIT"
    regime_at_entry: str
    bars_held: int


def simulate_trades(close, high, low, volume, timestamps, signals,
                    symbol, strategy_name, combo_name,
                    tp_mult=2.5, sl_mult=1.5, max_hold=48,
                    commission=0.001) -> list[Trade]:
    """Walk-forward trade simulation with TP/SL/time exit."""
    trades = []
    pos = 0
    entry_price = 0.0
    entry_tp = 0.0
    entry_sl = 0.0
    entry_time = None
    entry_dir = ""
    entry_regime = ""
    bars_held = 0

    atr_series = atr(high, low, close, 14)

    for i in range(len(close)):
        if pos != 0:
            bars_held += 1
            current_price = float(close.iloc[i])
            current_high = float(high.iloc[i])
            current_low = float(low.iloc[i])
            ts = timestamps.iloc[i] if i < len(timestamps) else ""

            hit_tp = False
            hit_sl = False
            exit_price = current_price
            exit_reason = ""

            if pos == 1:  # LONG
                if current_high >= entry_tp:
                    hit_tp = True
                    exit_price = entry_tp
                    exit_reason = "TP"
                elif current_low <= entry_sl:
                    hit_sl = True
                    exit_price = entry_sl
                    exit_reason = "SL"
            else:  # SHORT
                if current_low <= entry_tp:
                    hit_tp = True
                    exit_price = entry_tp
                    exit_reason = "TP"
                elif current_high >= entry_sl:
                    hit_sl = True
                    exit_price = entry_sl
                    exit_reason = "SL"

            if bars_held >= max_hold and not (hit_tp or hit_sl):
                exit_reason = "TIME_EXIT"

            if hit_tp or hit_sl or bars_held >= max_hold:
                if pos == 1:
                    pnl = (exit_price / entry_price - 1) - 2 * commission
                else:
                    pnl = (1 - exit_price / entry_price) - 2 * commission

                # Convert timestamp to EST
                exit_est = _to_est(ts)
                trades.append(Trade(
                    symbol=symbol,
                    strategy=strategy_name,
                    combo_name=combo_name,
                    direction=entry_dir,
                    entry_price=round(entry_price, 6),
                    take_profit=round(entry_tp, 6),
                    stop_loss=round(entry_sl, 6),
                    entry_time=_to_est(entry_time),
                    exit_time=exit_est,
                    exit_price=round(exit_price, 6),
                    pnl_pct=round(pnl * 100, 4),
                    exit_reason=exit_reason,
                    regime_at_entry=entry_regime,
                    bars_held=bars_held,
                ))
                pos = 0
                bars_held = 0

        # New entry
        if pos == 0 and i < len(signals) and signals[i] != 0 and i > 0:
            atr_val = float(atr_series.iloc[i]) if not np.isnan(atr_series.iloc[i]) else 0
            if atr_val <= 0:
                continue
            entry_price = float(close.iloc[i])
            entry_time = timestamps.iloc[i] if i < len(timestamps) else ""

            if signals[i] == 1:  # BUY
                pos = 1
                entry_dir = "LONG"
                entry_tp = entry_price + tp_mult * atr_val
                entry_sl = entry_price - sl_mult * atr_val
            elif signals[i] == -1:  # SELL
                pos = -1
                entry_dir = "SHORT"
                entry_tp = entry_price - tp_mult * atr_val
                entry_sl = entry_price + sl_mult * atr_val

            regime = detect_regime(close[:i+1], high[:i+1], low[:i+1], volume[:i+1])
            entry_regime = regime["regime"]

    return trades


def _to_est(ts):
    """Convert timestamp to EST string."""
    if isinstance(ts, str):
        try:
            dt = pd.Timestamp(ts)
            if dt.tzinfo is None:
                dt = dt.tz_localize("UTC")
            return dt.tz_convert("US/Eastern").strftime("%Y-%m-%d %H:%M EST")
        except Exception:
            return str(ts)
    if isinstance(ts, (pd.Timestamp, datetime)):
        try:
            if ts.tzinfo is None:
                ts = ts.tz_localize("UTC")
            return ts.tz_convert("US/Eastern").strftime("%Y-%m-%d %H:%M EST")
        except Exception:
            return str(ts)
    return str(ts)


# ─────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────

def compute_metrics(trades: list[Trade]) -> dict:
    if not trades:
        return {"win_rate": 0, "sharpe": 0, "profit_factor": 0,
                "total_pnl": 0, "max_dd": 0, "trades": 0, "avg_pnl": 0}
    pnls = [t.pnl_pct for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    wr = len(wins) / len(pnls) * 100
    gp = sum(wins) if wins else 0
    gl = abs(sum(losses)) if losses else 0
    pf = gp / gl if gl > 0 else 999
    avg = np.mean(pnls)
    std = np.std(pnls) if len(pnls) > 1 else 1
    sharpe = (avg / std) * np.sqrt(252) if std > 0 else 0
    # Max drawdown
    equity = 10000
    peak = equity
    max_dd = 0
    for p in pnls:
        equity += equity * p / 100
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak
        if dd > max_dd:
            max_dd = dd

    return {
        "win_rate": round(wr, 2),
        "sharpe": round(sharpe, 4),
        "profit_factor": round(pf, 4),
        "total_pnl": round(sum(pnls), 4),
        "max_dd": round(max_dd * 100, 2),
        "trades": len(pnls),
        "avg_pnl": round(avg, 4),
    }


# ─────────────────────────────────────────────────────────────────
# Main Backtester
# ─────────────────────────────────────────────────────────────────

FAILING_STRATEGIES = {
    "monthly_seasonality": sig_monthly_seasonality,
    "fourier_cycle": sig_fourier_cycle,
    "smart_money_fvg": sig_smart_money_fvg,
    "exchange_netflow": sig_exchange_netflow,
    "price_touch_recurrence": sig_price_touch_recurrence,
    "momentum_mean_rev_blend": sig_momentum_mean_rev_blend,
    "ict_fvg_selective": sig_ict_fvg_selective,
}

WINNING_STRATEGIES = {
    "autocorrelation": sig_autocorrelation,
    "multi_sigma_reversal": sig_multi_sigma_reversal,
    "hurst_regime": sig_hurst_regime,
    "volume_profile": sig_volume_profile,
}

NEEDS_MONTH = {"monthly_seasonality"}
NEEDS_BTC = {"altcoin_season"}


def run_strategy_on_symbol(strat_name, strat_fn, close, high, low, volume,
                           timestamps, symbol, btc_close=None):
    """Generate signal array for a strategy."""
    signals = np.zeros(len(close), dtype=int)
    for i in range(len(close)):
        try:
            if strat_name in NEEDS_MONTH:
                ts = pd.Timestamp(timestamps.iloc[i])
                month = ts.month
                signals[i] = strat_fn(close, high, low, volume, i, month)
            elif strat_name == "altcoin_season":
                signals[i] = strat_fn(close, high, low, volume, i, btc_close)
            else:
                signals[i] = strat_fn(close, high, low, volume, i)
        except Exception:
            signals[i] = 0
    return signals


def precompute_regime_series(close, high_s, low_s, vol, step=12):
    """Precompute regime at regular intervals (every `step` bars) for speed.
    Interpolate between. This avoids O(N*N) indicator recomputation."""
    n = len(close)
    regimes = [None] * n
    # Full series indicators (computed ONCE)
    atr_full = atr(high_s, low_s, close, 14)
    atr_ma60 = atr_full.rolling(60).mean()
    adx_full = adx(high_s, low_s, close, 14)
    roc_full = close.pct_change(20) * 100

    for i in range(200, n, step):
        atr_val = float(atr_full.iloc[i]) if not np.isnan(atr_full.iloc[i]) else 0
        atr_ma = float(atr_ma60.iloc[i]) if not np.isnan(atr_ma60.iloc[i]) else atr_val
        atr_ratio = atr_val / atr_ma if atr_ma > 0 else 1.0
        adx_val = float(adx_full.iloc[i]) if not np.isnan(adx_full.iloc[i]) else 20
        roc_20d = float(roc_full.iloc[i]) if not np.isnan(roc_full.iloc[i]) else 0
        peak = float(close[max(0,i-30):i+1].max())
        dd = (float(close.iloc[i]) / peak - 1) * 100 if peak > 0 else 0
        # Hurst only every 48 bars (expensive)
        h = 0.5
        if i % 48 == 0:
            h = hurst_exponent(close[max(0,i-200):i+1])

        if dd < -15:
            regime = "CRISIS"
        elif atr_ratio > 2.0:
            regime = "HIGH_VOLATILITY"
        elif atr_ratio < 0.5:
            regime = "LOW_VOLATILITY"
        elif h > 0.65 and adx_val > 25:
            regime = "TRENDING_UP" if roc_20d > 0 else "TRENDING_DOWN"
        elif h < 0.40:
            regime = "MEAN_REVERTING"
        else:
            regime = "NEUTRAL"

        vol_regime = "HIGH" if atr_ratio > 1.5 else "LOW" if atr_ratio < 0.7 else "NORMAL"
        r = {"regime": regime, "hurst": round(h, 4), "adx": round(adx_val, 2),
             "roc_20d": round(roc_20d, 2), "atr_ratio": round(atr_ratio, 4),
             "drawdown": round(dd, 2), "vol_regime": vol_regime}
        # Fill forward
        for j in range(i, min(i + step, n)):
            regimes[j] = r

    # Fill any remaining None at start
    default = {"regime": "NEUTRAL", "hurst": 0.5, "adx": 20, "roc_20d": 0,
               "atr_ratio": 1.0, "drawdown": 0, "vol_regime": "NORMAL"}
    for i in range(n):
        if regimes[i] is None:
            regimes[i] = default
    return regimes


def run_backtest(symbols=None, export_path=None):
    """Main backtest runner."""
    if symbols is None:
        symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "XRP/USDT"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    btc_df = pd.read_sql_query(
        "SELECT * FROM klines WHERE pair='BTC/USDT' ORDER BY timestamp", conn
    )
    btc_close = pd.to_numeric(btc_df["close"], errors="coerce")

    all_results = []
    all_trades = []

    for symbol in symbols:
        print(f"\n{'='*80}")
        print(f"  SYMBOL: {symbol}")
        print(f"{'='*80}")

        df = pd.read_sql_query(
            "SELECT * FROM klines WHERE pair=? ORDER BY timestamp",
            conn, params=[symbol]
        )
        if df.empty:
            print(f"  No data for {symbol}")
            continue

        close = pd.to_numeric(df["close"], errors="coerce")
        high_s = pd.to_numeric(df["high"], errors="coerce")
        low_s = pd.to_numeric(df["low"], errors="coerce")
        vol = pd.to_numeric(df["volume"], errors="coerce")
        timestamps = df["timestamp"]

        print(f"  {len(close)} bars | Precomputing regime series...")
        regime_series = precompute_regime_series(close, high_s, low_s, vol)
        print(f"  Regime series ready. Running strategies...")

        # ── Test each FAILING strategy in 3 modes ──
        for strat_name, strat_fn in FAILING_STRATEGIES.items():
            print(f"    {strat_name}...", end=" ", flush=True)
            raw_signals = run_strategy_on_symbol(
                strat_name, strat_fn, close, high_s, low_s, vol,
                timestamps, symbol, btc_close
            )
            n_raw = np.count_nonzero(raw_signals)
            print(f"{n_raw} signals", flush=True)

            for mode_name, mode_signals in [("ORIGINAL", raw_signals), ("INVERSE", -raw_signals)]:
                for filter_name, filter_fn in REGIME_FILTERS.items():
                    filtered = np.zeros_like(mode_signals)
                    for i in range(len(mode_signals)):
                        if mode_signals[i] != 0:
                            if i >= 200:
                                filtered[i] = filter_fn(mode_signals[i], regime_series[i])
                            elif filter_name == "no_filter":
                                filtered[i] = mode_signals[i]

                    combo = f"{mode_name}({strat_name})+{filter_name}"
                    trades = simulate_trades(close, high_s, low_s, vol, timestamps,
                                           filtered, symbol, strat_name, combo)
                    if trades:
                        metrics = compute_metrics(trades)
                        all_results.append({
                            "symbol": symbol, "strategy": strat_name,
                            "mode": mode_name, "filter": filter_name,
                            "combo": combo, **metrics
                        })
                        all_trades.extend(trades)

        # ── Test WINNING strategies (baseline) ──
        for strat_name, strat_fn in WINNING_STRATEGIES.items():
            print(f"    WINNER: {strat_name}...", end=" ", flush=True)
            raw_signals = run_strategy_on_symbol(
                strat_name, strat_fn, close, high_s, low_s, vol,
                timestamps, symbol, btc_close
            )
            print(f"{np.count_nonzero(raw_signals)} signals", flush=True)
            combo = f"WINNER({strat_name})"
            trades = simulate_trades(close, high_s, low_s, vol, timestamps,
                                   raw_signals, symbol, strat_name, combo)
            if trades:
                metrics = compute_metrics(trades)
                all_results.append({
                    "symbol": symbol, "strategy": strat_name,
                    "mode": "WINNER", "filter": "none",
                    "combo": combo, **metrics
                })
                all_trades.extend(trades)

        # ── ENSEMBLE combos ──
        print(f"    Building ensembles...", flush=True)
        winner_signals = {}
        for strat_name, strat_fn in WINNING_STRATEGIES.items():
            winner_signals[strat_name] = run_strategy_on_symbol(
                strat_name, strat_fn, close, high_s, low_s, vol,
                timestamps, symbol, btc_close
            )

        inv_loser_signals = {}
        original_loser_signals = {}
        for strat_name, strat_fn in FAILING_STRATEGIES.items():
            raw = run_strategy_on_symbol(
                strat_name, strat_fn, close, high_s, low_s, vol,
                timestamps, symbol, btc_close
            )
            inv_loser_signals[f"INV_{strat_name}"] = -raw
            original_loser_signals[strat_name] = raw

        # Ensemble A: 2+ winners agree
        ensemble_a = np.zeros(len(close), dtype=int)
        for i in range(len(close)):
            votes = sum(winner_signals[s][i] for s in winner_signals)
            if votes >= 2:
                ensemble_a[i] = 1
            elif votes <= -2:
                ensemble_a[i] = -1
        combo = "ENSEMBLE_WINNERS_2+"
        trades = simulate_trades(close, high_s, low_s, vol, timestamps,
                               ensemble_a, symbol, "ensemble_winners", combo)
        if trades:
            metrics = compute_metrics(trades)
            all_results.append({"symbol": symbol, "strategy": "ensemble_winners",
                "mode": "ENSEMBLE", "filter": "consensus_2+", "combo": combo, **metrics})
            all_trades.extend(trades)

        # Ensemble B: 3+ inverse losers agree
        ensemble_b = np.zeros(len(close), dtype=int)
        for i in range(len(close)):
            votes = sum(inv_loser_signals[s][i] for s in inv_loser_signals)
            if votes >= 3:
                ensemble_b[i] = 1
            elif votes <= -3:
                ensemble_b[i] = -1
        combo = "ENSEMBLE_INV_LOSERS_3+"
        trades = simulate_trades(close, high_s, low_s, vol, timestamps,
                               ensemble_b, symbol, "ensemble_inv_losers", combo)
        if trades:
            metrics = compute_metrics(trades)
            all_results.append({"symbol": symbol, "strategy": "ensemble_inv_losers",
                "mode": "ENSEMBLE", "filter": "consensus_3+", "combo": combo, **metrics})
            all_trades.extend(trades)

        # Ensemble C: 1+ winner AND 2+ inverse losers agree (THE THEORY)
        ensemble_c = np.zeros(len(close), dtype=int)
        for i in range(len(close)):
            w_buys = sum(1 for s in winner_signals if winner_signals[s][i] == 1)
            w_sells = sum(1 for s in winner_signals if winner_signals[s][i] == -1)
            l_buys = sum(1 for s in inv_loser_signals if inv_loser_signals[s][i] == 1)
            l_sells = sum(1 for s in inv_loser_signals if inv_loser_signals[s][i] == -1)
            if w_buys >= 1 and l_buys >= 2:
                ensemble_c[i] = 1
            elif w_sells >= 1 and l_sells >= 2:
                ensemble_c[i] = -1
        combo = "ENSEMBLE_WINNER+INV_LOSER"
        trades = simulate_trades(close, high_s, low_s, vol, timestamps,
                               ensemble_c, symbol, "winner_plus_inv_loser", combo)
        if trades:
            metrics = compute_metrics(trades)
            all_results.append({"symbol": symbol, "strategy": "winner_plus_inv_loser",
                "mode": "ENSEMBLE", "filter": "1W+2IL", "combo": combo, **metrics})
            all_trades.extend(trades)

        # Ensemble D: Winner CONFIRMED by loser DISAGREEMENT
        ensemble_d = np.zeros(len(close), dtype=int)
        for i in range(len(close)):
            for ws_name in winner_signals:
                w_sig = winner_signals[ws_name][i]
                if w_sig == 0:
                    continue
                agrees = sum(1 for ls in original_loser_signals
                           if original_loser_signals[ls][i] == w_sig)
                disagrees = sum(1 for ls in original_loser_signals
                              if original_loser_signals[ls][i] == -w_sig)
                if disagrees > agrees and disagrees >= 1:
                    ensemble_d[i] = w_sig
                    break
        combo = "ENSEMBLE_WINNER_LOSER_DISAGREE"
        trades = simulate_trades(close, high_s, low_s, vol, timestamps,
                               ensemble_d, symbol, "winner_loser_disagree", combo)
        if trades:
            metrics = compute_metrics(trades)
            all_results.append({"symbol": symbol, "strategy": "winner_loser_disagree",
                "mode": "ENSEMBLE", "filter": "W+L_disagree", "combo": combo, **metrics})
            all_trades.extend(trades)

        # Ensemble E: ANY winner + regime gate (only trade in mean-reverting or crisis)
        ensemble_e = np.zeros(len(close), dtype=int)
        for i in range(len(close)):
            if regime_series[i]["regime"] not in ("MEAN_REVERTING", "CRISIS", "HIGH_VOLATILITY"):
                continue
            for ws_name in winner_signals:
                if winner_signals[ws_name][i] != 0:
                    ensemble_e[i] = winner_signals[ws_name][i]
                    break
        combo = "ENSEMBLE_WINNER_MR_CRISIS_ONLY"
        trades = simulate_trades(close, high_s, low_s, vol, timestamps,
                               ensemble_e, symbol, "winner_mr_crisis", combo)
        if trades:
            metrics = compute_metrics(trades)
            all_results.append({"symbol": symbol, "strategy": "winner_mr_crisis",
                "mode": "ENSEMBLE", "filter": "MR+CRISIS", "combo": combo, **metrics})
            all_trades.extend(trades)

        # Ensemble F: Inverse losers BUT only in their WORST regime (where they fail most)
        ensemble_f = np.zeros(len(close), dtype=int)
        for i in range(len(close)):
            # Inverse losers are most reliable in trending markets (losers fail at trends)
            if regime_series[i]["regime"] not in ("TRENDING_UP", "TRENDING_DOWN"):
                continue
            votes = sum(inv_loser_signals[s][i] for s in inv_loser_signals)
            if votes >= 2:
                ensemble_f[i] = 1
            elif votes <= -2:
                ensemble_f[i] = -1
        combo = "ENSEMBLE_INV_LOSERS_TRENDING"
        trades = simulate_trades(close, high_s, low_s, vol, timestamps,
                               ensemble_f, symbol, "inv_losers_trending", combo)
        if trades:
            metrics = compute_metrics(trades)
            all_results.append({"symbol": symbol, "strategy": "inv_losers_trending",
                "mode": "ENSEMBLE", "filter": "trending_only", "combo": combo, **metrics})
            all_trades.extend(trades)

        print(f"    Done: {len([r for r in all_results if r['symbol']==symbol])} combos tested")

    conn.close()

    # ── Print Results ──
    print("\n\n" + "=" * 120)
    print("  COMBINATORY BACKTEST RESULTS — RANKED BY SHARPE RATIO")
    print("=" * 120)

    results_df = pd.DataFrame(all_results)
    if results_df.empty:
        print("  No results generated!")
        return

    # Group by combo, average across symbols
    agg = results_df.groupby("combo").agg({
        "win_rate": "mean", "sharpe": "mean", "profit_factor": "mean",
        "total_pnl": "sum", "max_dd": "max", "trades": "sum", "avg_pnl": "mean",
    }).round(4)
    agg = agg[agg["trades"] >= 3]  # Min 3 trades
    agg = agg.sort_values("sharpe", ascending=False)

    print(f"\n{'Combo':<45} {'Sharpe':>8} {'WR%':>7} {'PF':>7} {'TotalPnL':>10} {'MaxDD%':>8} {'Trades':>7} {'AvgPnL':>8}")
    print("-" * 105)
    for combo, row in agg.head(40).iterrows():
        marker = "*" if row["sharpe"] > 1.0 and row["win_rate"] > 50 else " "
        print(f"{marker}{combo:<44} {row['sharpe']:>8.4f} {row['win_rate']:>6.2f}% "
              f"{row['profit_factor']:>7.4f} {row['total_pnl']:>+10.4f} "
              f"{row['max_dd']:>7.2f}% {row['trades']:>7.0f} {row['avg_pnl']:>+8.4f}")

    # ── Print Top Trade Portfolio ──
    print(f"\n\n{'='*120}")
    print("  HYPOTHETICAL PORTFOLIO — TOP COMBO TRADES")
    print(f"{'='*120}")

    # Get best combo
    if len(agg) > 0:
        best_combo = agg.index[0]
        best_trades = [t for t in all_trades if t.combo_name == best_combo]
        print(f"\n  Best combo: {best_combo} (Sharpe {agg.iloc[0]['sharpe']:.4f})")
        print(f"\n{'Symbol':<12} {'Dir':<6} {'Entry$':>10} {'TP$':>10} {'SL$':>10} {'Exit$':>10} "
              f"{'PnL%':>8} {'Reason':<10} {'Entry Time':<22} {'Exit Time':<22} {'Regime':<15} {'Bars':>5}")
        print("-" * 145)
        for t in best_trades[:50]:
            print(f"{t.symbol:<12} {t.direction:<6} {t.entry_price:>10.2f} {t.take_profit:>10.2f} "
                  f"{t.stop_loss:>10.2f} {t.exit_price:>10.2f} {t.pnl_pct:>+8.4f} "
                  f"{t.exit_reason:<10} {t.entry_time:<22} {t.exit_time:<22} "
                  f"{t.regime_at_entry:<15} {t.bars_held:>5}")

    # ── Save results ──
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = OUTPUT_DIR / f"combo_results_{ts}.json"
    trades_path = OUTPUT_DIR / f"combo_trades_{ts}.json"

    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2)
    with open(trades_path, "w") as f:
        json.dump([asdict(t) for t in all_trades], f, indent=2, default=str)

    print(f"\n\n  Results saved to: {results_path}")
    print(f"  Trades saved to:  {trades_path}")
    print(f"  Total combos tested: {len(agg)}")
    print(f"  Total trades generated: {len(all_trades)}")

    # Export if requested
    if export_path:
        with open(export_path, "w") as f:
            json.dump({
                "summary": agg.reset_index().to_dict(orient="records"),
                "trades": [asdict(t) for t in all_trades],
                "generated": datetime.now(timezone.utc).isoformat(),
            }, f, indent=2, default=str)
        print(f"  Exported to: {export_path}")

    return agg, all_trades


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Combinatory Strategy Backtester")
    parser.add_argument("--symbols", nargs="+", default=None,
                       help="Symbols to test (e.g., BTC/USDT ETH/USDT)")
    parser.add_argument("--export", type=str, default=None,
                       help="Export results to JSON file")
    args = parser.parse_args()

    run_backtest(symbols=args.symbols, export_path=args.export)
