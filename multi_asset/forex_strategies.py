#!/usr/bin/env python3
"""
FOREX-SPECIFIC STRATEGIES v1.0
================================
Purpose-built forex strategies that exploit forex-specific edges:
  1. Session Overlap — momentum in London-NY overlap, mean reversion in Asian
  2. Carry Trade Scanner — interest rate differential + trend alignment
  3. Connors RSI-2 Forex-Tuned — wider thresholds, ATR-based exits, no SMA200 filter
  4. Keltner Compression Forex — longer lookback, wider KC multiplier for lower vol
  5. DXY Macro Filter — dollar index correlation filter for all USD pairs

Data source: yfinance (EURUSD=X format)
Output: same signal dict format as multi_asset/scanner.py for seamless integration.

All strategies return list[dict] matching the scanner.py pick format.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Forex pair universe — 8 major pairs + DXY proxy
# ---------------------------------------------------------------------------
FOREX_PAIRS = {
    "EURUSD=X": {"name": "EUR/USD", "cat": "forex", "carry_yield_diff": -0.5,
                 "dxy_correlation": -0.95, "session_bias": "london"},
    "USDJPY=X": {"name": "USD/JPY", "cat": "forex", "carry_yield_diff": 4.5,
                 "dxy_correlation": 0.60, "session_bias": "asian"},
    "GBPUSD=X": {"name": "GBP/USD", "cat": "forex", "carry_yield_diff": 0.25,
                 "dxy_correlation": -0.85, "session_bias": "london"},
    "AUDUSD=X": {"name": "AUD/USD", "cat": "forex", "carry_yield_diff": 0.75,
                 "dxy_correlation": -0.70, "session_bias": "asian"},
    "NZDUSD=X": {"name": "NZD/USD", "cat": "forex", "carry_yield_diff": 1.0,
                 "dxy_correlation": -0.65, "session_bias": "asian"},
    "USDCAD=X": {"name": "USD/CAD", "cat": "forex", "carry_yield_diff": 0.5,
                 "dxy_correlation": 0.75, "session_bias": "newyork"},
    "USDCHF=X": {"name": "USD/CHF", "cat": "forex", "carry_yield_diff": 2.0,
                 "dxy_correlation": 0.90, "session_bias": "london"},
    "EURJPY=X": {"name": "EUR/JPY", "cat": "forex", "carry_yield_diff": 4.0,
                 "dxy_correlation": -0.20, "session_bias": "london"},
}

# DXY proxy ticker on yfinance
DXY_TICKER = "DX-Y.NYB"

# Interest rate differentials (annualized, approximate as of 2026-Q1)
# Positive = base currency yields more than quote currency
# Updated quarterly — these drive carry trade direction
RATE_DIFFERENTIALS = {
    "EURUSD=X": -0.50,   # EUR 3.75% - USD 4.25%
    "USDJPY=X":  4.50,   # USD 4.25% - JPY -0.25% (classic carry)
    "GBPUSD=X":  0.25,   # GBP 4.50% - USD 4.25%
    "AUDUSD=X":  0.75,   # AUD 5.00% - USD 4.25%
    "NZDUSD=X":  1.00,   # NZD 5.25% - USD 4.25%
    "USDCAD=X":  0.50,   # USD 4.25% - CAD 3.75%
    "USDCHF=X":  2.00,   # USD 4.25% - CHF 2.25%
    "EURJPY=X":  4.00,   # EUR 3.75% - JPY -0.25%
}

# Risk parameters: (stop_loss_pct, take_profit_pct, max_hold_days)
# Forex-specific: tighter stops, modest targets, longer hold for carry
FOREX_RISK = {
    "session_overlap":     (-0.020, 0.030, 5),
    "carry_trade":         (-0.025, 0.040, 21),
    "connors_rsi2_forex":  (-0.015, 0.025, 7),
    "keltner_forex":       (-0.020, 0.035, 10),
    "dxy_trend_filter":    (-0.020, 0.030, 10),
}

# Session time windows (UTC hours)
SESSIONS = {
    "asian":     (0, 8),     # Tokyo/Sydney: 00:00-08:00 UTC
    "london":    (8, 16),    # London: 08:00-16:00 UTC
    "newyork":   (13, 21),   # New York: 13:00-21:00 UTC
    "overlap":   (13, 17),   # London-NY overlap: 13:00-17:00 UTC (highest volatility)
}


# ---------------------------------------------------------------------------
# Technical indicators (self-contained, matching scanner.py conventions)
# ---------------------------------------------------------------------------

def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def bollinger_bands(series: pd.Series, period: int = 20, std_mult: float = 2.0):
    mid = sma(series, period)
    std = series.rolling(period).std()
    return mid, mid + std_mult * std, mid - std_mult * std


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    atr_val = atr(high, low, close, period)
    plus_di = 100 * ema(plus_dm, period) / atr_val.replace(0, np.nan)
    minus_di = 100 * ema(minus_dm, period) / atr_val.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return ema(dx, period)


def _hma(series: pd.Series, period: int = 21) -> pd.Series:
    """Hull Moving Average -- lag-reduced trend filter."""
    half = max(1, period // 2)
    sqrt_n = max(1, int(period ** 0.5))
    wma_half = series.ewm(span=half, adjust=False).mean()
    wma_full = series.ewm(span=period, adjust=False).mean()
    raw = 2 * wma_half - wma_full
    return raw.ewm(span=sqrt_n, adjust=False).mean()


def _sanitize_float(val) -> float:
    """Safely convert to float, handling numpy scalars."""
    if hasattr(val, "item"):
        val = val.item()
    val = float(val)
    if not np.isfinite(val):
        return float("nan")
    return val


def _pick_id(strategy: str, symbol: str, dt: str) -> str:
    return f"{strategy}::{symbol}::{dt}"


# ---------------------------------------------------------------------------
# STRATEGY 1: Session Overlap (Momentum + Mean Reversion Switch)
# ---------------------------------------------------------------------------
# Edge: London-NY overlap (13:00-17:00 UTC) = highest FX volatility = momentum.
#        Asian session (00:00-08:00 UTC) = range-bound = mean reversion.
# This strategy checks the current UTC hour and applies the appropriate mode.
# On daily bars it uses recent volatility regime as a proxy for session behavior.

def session_overlap(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    Session-aware forex strategy:
    - During high-volatility regime (proxy for London-NY overlap): breakout/momentum.
    - During low-volatility regime (proxy for Asian session): mean reversion.

    On daily data, we approximate session behavior by measuring recent ATR
    relative to its 20-day average:
    - ATR expanding (> 1.2x avg) => momentum mode
    - ATR contracting (< 0.8x avg) => mean reversion mode
    """
    signals = []
    cat = info.get("cat", "forex")
    if cat != "forex":
        return signals

    if len(df) < 50:
        return signals

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    price = _sanitize_float(close.iloc[-1])
    if not np.isfinite(price) or price <= 0:
        return signals

    # ATR regime detection
    atr_14 = atr(high, low, close, 14)
    atr_now = _sanitize_float(atr_14.iloc[-1])
    atr_avg = _sanitize_float(atr_14.rolling(20).mean().iloc[-1])

    if not np.isfinite(atr_now) or not np.isfinite(atr_avg) or atr_avg <= 0:
        return signals

    atr_ratio = atr_now / atr_avg
    rsi_14 = _sanitize_float(rsi(close, 14).iloc[-1])
    if not np.isfinite(rsi_14):
        return signals

    sl_pct, tp_pct, max_hold = FOREX_RISK["session_overlap"]

    # Also check current hour for live session detection
    now_utc = datetime.now(timezone.utc)
    hour = now_utc.hour
    in_overlap = 13 <= hour <= 17
    in_asian = 0 <= hour <= 8

    # --- MOMENTUM MODE: high volatility / London-NY overlap ---
    # ATR expanding + trending (ADX > 20) + session overlap bonus
    if atr_ratio > 1.15:
        adx_val = _sanitize_float(adx(high, low, close, 14).iloc[-1])
        if not np.isfinite(adx_val):
            adx_val = 15.0

        ema_20 = _sanitize_float(ema(close, 20).iloc[-1])
        ema_50 = _sanitize_float(ema(close, 50).iloc[-1])

        if adx_val > 20 and np.isfinite(ema_20) and np.isfinite(ema_50):
            # Bullish momentum: price > EMA20 > EMA50
            if price > ema_20 > ema_50 and rsi_14 > 50 and rsi_14 < 75:
                conf = min(0.90, 0.55 + (adx_val - 20) * 0.005 + (atr_ratio - 1.0) * 0.15)
                if in_overlap:
                    conf = min(0.90, conf + 0.05)
                tp_price = price + 1.5 * atr_now
                sl_price = price - 1.0 * atr_now

                signals.append({
                    "strategy": "session_overlap_momentum",
                    "symbol": symbol,
                    "category": cat,
                    "direction": "LONG",
                    "signal_type": "BUY",
                    "entry_price": price,
                    "take_profit": round(tp_price, 6),
                    "stop_loss": round(sl_price, 6),
                    "confidence": round(conf, 3),
                    "risk_reward": 1.5,
                    "reason": (f"Session momentum LONG: ATR ratio {atr_ratio:.2f}x, "
                               f"ADX={adx_val:.1f}, RSI={rsi_14:.1f}, "
                               f"EMA20>{ema_20:.5f} > EMA50>{ema_50:.5f}"
                               f"{' [OVERLAP]' if in_overlap else ''}"),
                    "atr_at_entry": round(atr_now, 6),
                    "session_mode": "momentum",
                    "max_hold_days": max_hold,
                })

            # Bearish momentum: price < EMA20 < EMA50
            elif price < ema_20 < ema_50 and rsi_14 < 50 and rsi_14 > 25:
                conf = min(0.90, 0.55 + (adx_val - 20) * 0.005 + (atr_ratio - 1.0) * 0.15)
                if in_overlap:
                    conf = min(0.90, conf + 0.05)
                tp_price = price - 1.5 * atr_now
                sl_price = price + 1.0 * atr_now

                signals.append({
                    "strategy": "session_overlap_momentum",
                    "symbol": symbol,
                    "category": cat,
                    "direction": "SHORT",
                    "signal_type": "SELL",
                    "entry_price": price,
                    "take_profit": round(tp_price, 6),
                    "stop_loss": round(sl_price, 6),
                    "confidence": round(conf, 3),
                    "risk_reward": 1.5,
                    "reason": (f"Session momentum SHORT: ATR ratio {atr_ratio:.2f}x, "
                               f"ADX={adx_val:.1f}, RSI={rsi_14:.1f}"
                               f"{' [OVERLAP]' if in_overlap else ''}"),
                    "atr_at_entry": round(atr_now, 6),
                    "session_mode": "momentum",
                    "max_hold_days": max_hold,
                })

    # --- MEAN REVERSION MODE: low volatility / Asian session ---
    # ATR contracting + RSI extreme = fading range extremes
    if atr_ratio < 0.85:
        bb_mid, bb_upper, bb_lower = bollinger_bands(close, 20, 2.0)
        bb_mid_val = _sanitize_float(bb_mid.iloc[-1])
        bb_upper_val = _sanitize_float(bb_upper.iloc[-1])
        bb_lower_val = _sanitize_float(bb_lower.iloc[-1])

        if not all(np.isfinite([bb_mid_val, bb_upper_val, bb_lower_val])):
            return signals

        # Buy at lower band in quiet market
        if price <= bb_lower_val and rsi_14 < 35:
            conf = min(0.85, 0.55 + (35 - rsi_14) * 0.01 + (0.85 - atr_ratio) * 0.2)
            if in_asian:
                conf = min(0.85, conf + 0.05)

            signals.append({
                "strategy": "session_overlap_mr",
                "symbol": symbol,
                "category": cat,
                "direction": "LONG",
                "signal_type": "BUY",
                "entry_price": price,
                "take_profit": round(bb_mid_val, 6),
                "stop_loss": round(price - 1.5 * atr_now, 6),
                "confidence": round(conf, 3),
                "risk_reward": round(abs(bb_mid_val - price) / (1.5 * atr_now), 2) if atr_now > 0 else 1.0,
                "reason": (f"Session MR LONG: quiet market ATR ratio {atr_ratio:.2f}x, "
                           f"price at lower BB, RSI={rsi_14:.1f}"
                           f"{' [ASIAN]' if in_asian else ''}"),
                "atr_at_entry": round(atr_now, 6),
                "session_mode": "mean_reversion",
                "max_hold_days": max_hold,
            })

        # Sell at upper band in quiet market
        if price >= bb_upper_val and rsi_14 > 65:
            conf = min(0.85, 0.55 + (rsi_14 - 65) * 0.01 + (0.85 - atr_ratio) * 0.2)
            if in_asian:
                conf = min(0.85, conf + 0.05)

            signals.append({
                "strategy": "session_overlap_mr",
                "symbol": symbol,
                "category": cat,
                "direction": "SHORT",
                "signal_type": "SELL",
                "entry_price": price,
                "take_profit": round(bb_mid_val, 6),
                "stop_loss": round(price + 1.5 * atr_now, 6),
                "confidence": round(conf, 3),
                "risk_reward": round(abs(price - bb_mid_val) / (1.5 * atr_now), 2) if atr_now > 0 else 1.0,
                "reason": (f"Session MR SHORT: quiet market ATR ratio {atr_ratio:.2f}x, "
                           f"price at upper BB, RSI={rsi_14:.1f}"
                           f"{' [ASIAN]' if in_asian else ''}"),
                "atr_at_entry": round(atr_now, 6),
                "session_mode": "mean_reversion",
                "max_hold_days": max_hold,
            })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 2: Carry Trade Scanner
# ---------------------------------------------------------------------------
# Edge: Pairs with high interest rate differentials tend to trend in the carry
# direction. Long the high-yielding currency, short the low-yielding one.
# Filter: only enter when price trend aligns with carry direction (EMA 50/200).
# This prevents catching falling knives in risk-off environments.

def carry_trade(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    Carry Trade Scanner:
    - Identifies pairs with significant interest rate differentials
    - Enters only when price trend aligns with carry direction
    - Uses EMA(50)/EMA(200) trend filter + ADX for trend strength
    - Higher confidence for classic carry pairs (USDJPY, EURJPY, AUDUSD)

    Carry direction logic:
    - Positive rate diff = base yields more => LONG (buy base, sell quote)
    - Negative rate diff = quote yields more => SHORT (sell base, buy quote)
    """
    signals = []
    cat = info.get("cat", "forex")
    if cat != "forex":
        return signals

    if len(df) < 200:
        return signals

    rate_diff = RATE_DIFFERENTIALS.get(symbol, 0.0)
    # Only trade pairs with meaningful rate differential (> 0.5%)
    if abs(rate_diff) < 0.5:
        return signals

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    price = _sanitize_float(close.iloc[-1])
    if not np.isfinite(price) or price <= 0:
        return signals

    # Trend filters
    ema_50 = _sanitize_float(ema(close, 50).iloc[-1])
    ema_200 = _sanitize_float(ema(close, 200).iloc[-1])
    adx_val = _sanitize_float(adx(high, low, close, 14).iloc[-1])
    atr_now = _sanitize_float(atr(high, low, close, 14).iloc[-1])

    if not all(np.isfinite([ema_50, ema_200, adx_val, atr_now])) or atr_now <= 0:
        return signals

    # Need a minimum trend strength
    if adx_val < 18:
        return signals

    sl_pct, tp_pct, max_hold = FOREX_RISK["carry_trade"]

    # Carry direction: positive diff = LONG, negative = SHORT
    carry_direction = "LONG" if rate_diff > 0 else "SHORT"

    # Trend alignment check
    if carry_direction == "LONG":
        trend_aligned = price > ema_50 > ema_200
    else:
        trend_aligned = price < ema_50 < ema_200

    if not trend_aligned:
        return signals

    # Confidence: base + rate diff magnitude + ADX strength
    conf = min(0.90, 0.50 + abs(rate_diff) * 0.04 + (adx_val - 18) * 0.005)

    # Classic carry pairs get a bonus (deeper liquidity, more reliable carry)
    classic_carry = symbol in ("USDJPY=X", "EURJPY=X", "AUDUSD=X", "NZDUSD=X")
    if classic_carry:
        conf = min(0.90, conf + 0.05)

    # RSI sanity check: don't enter overbought/oversold extremes
    rsi_14 = _sanitize_float(rsi(close, 14).iloc[-1])
    if np.isfinite(rsi_14):
        if carry_direction == "LONG" and rsi_14 > 72:
            return signals
        if carry_direction == "SHORT" and rsi_14 < 28:
            return signals

    if carry_direction == "LONG":
        tp_price = price + 2.0 * atr_now
        sl_price = price - 1.2 * atr_now
        signal_type = "BUY"
    else:
        tp_price = price - 2.0 * atr_now
        sl_price = price + 1.2 * atr_now
        signal_type = "SELL"

    rr = 2.0 / 1.2  # ~1.67:1

    signals.append({
        "strategy": "carry_trade",
        "symbol": symbol,
        "category": cat,
        "direction": carry_direction,
        "signal_type": signal_type,
        "entry_price": price,
        "take_profit": round(tp_price, 6),
        "stop_loss": round(sl_price, 6),
        "confidence": round(conf, 3),
        "risk_reward": round(rr, 2),
        "reason": (f"Carry trade {carry_direction}: rate diff {rate_diff:+.2f}%, "
                   f"trend aligned (EMA50/200), ADX={adx_val:.1f}"
                   f"{', classic carry' if classic_carry else ''}"),
        "rate_differential": rate_diff,
        "adx_at_entry": round(adx_val, 2),
        "atr_at_entry": round(atr_now, 6),
        "max_hold_days": max_hold,
    })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 3: Connors RSI-2 Forex-Tuned
# ---------------------------------------------------------------------------
# The original connors_rsi2 has 12% WR on forex. Root causes:
# 1. RSI(2) < 10 threshold is too aggressive for forex (lower volatility)
# 2. SMA(200) uptrend filter doesn't work for ranging forex pairs
# 3. Fixed % stops don't account for forex's tighter price ranges
#
# Fixes:
# - Widen RSI thresholds: buy < 15, sell > 85 (forex needs less extreme)
# - Replace SMA(200) with EMA(50) + price above EMA(20) (shorter trend)
# - ATR-based stops instead of fixed % (adapts to forex volatility)
# - Add confirmation: require 2 consecutive oversold/overbought bars

def connors_rsi2_forex(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    Connors RSI-2 adapted for forex:
    - RSI(2) thresholds widened to 15/85 (vs 10/90 for equities)
    - EMA(50) trend filter instead of SMA(200)
    - ATR-based exits (1.5x TP, 0.8x SL)
    - Requires 2 consecutive oversold/overbought bars for confirmation
    - Exit target: EMA(5) mean reversion (Connors original exit)
    """
    signals = []
    cat = info.get("cat", "forex")
    if cat != "forex":
        return signals

    if len(df) < 60:
        return signals

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    price = _sanitize_float(close.iloc[-1])
    if not np.isfinite(price) or price <= 0:
        return signals

    rsi_2 = rsi(close, 2)
    rsi_now = _sanitize_float(rsi_2.iloc[-1])
    rsi_prev = _sanitize_float(rsi_2.iloc[-2])

    if not all(np.isfinite([rsi_now, rsi_prev])):
        return signals

    ema_20 = _sanitize_float(ema(close, 20).iloc[-1])
    ema_50 = _sanitize_float(ema(close, 50).iloc[-1])
    ema_5 = _sanitize_float(ema(close, 5).iloc[-1])
    atr_now = _sanitize_float(atr(high, low, close, 14).iloc[-1])

    if not all(np.isfinite([ema_20, ema_50, ema_5, atr_now])) or atr_now <= 0:
        return signals

    sl_pct, tp_pct, max_hold = FOREX_RISK["connors_rsi2_forex"]

    # BUY: RSI(2) < 15 for 2 bars + price above EMA(50) + above EMA(20)
    if rsi_now < 15 and rsi_prev < 15 and price > ema_50 and price > ema_20 * 0.998:
        conf = min(0.88, 0.60 + (15 - rsi_now) * 0.02)
        # Target: EMA(5) -- Connors' original exit signal
        tp_price = ema_5 if ema_5 > price else price + 1.5 * atr_now
        sl_price = price - 0.8 * atr_now

        rr = abs(tp_price - price) / (0.8 * atr_now) if atr_now > 0 else 1.0

        signals.append({
            "strategy": "connors_rsi2_forex",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "STRONG_BUY",
            "entry_price": price,
            "take_profit": round(tp_price, 6),
            "stop_loss": round(sl_price, 6),
            "confidence": round(conf, 3),
            "risk_reward": round(rr, 2),
            "reason": (f"Connors RSI2 Forex LONG: RSI(2)={rsi_now:.1f} (prev {rsi_prev:.1f}), "
                       f"2-bar oversold, price above EMA50, target EMA5={ema_5:.5f}"),
            "rsi_at_entry": round(rsi_now, 2),
            "atr_at_entry": round(atr_now, 6),
            "max_hold_days": max_hold,
        })

    # SELL: RSI(2) > 85 for 2 bars + price below EMA(50) + below EMA(20)
    if rsi_now > 85 and rsi_prev > 85 and price < ema_50 and price < ema_20 * 1.002:
        conf = min(0.88, 0.60 + (rsi_now - 85) * 0.02)
        tp_price = ema_5 if ema_5 < price else price - 1.5 * atr_now
        sl_price = price + 0.8 * atr_now

        rr = abs(price - tp_price) / (0.8 * atr_now) if atr_now > 0 else 1.0

        signals.append({
            "strategy": "connors_rsi2_forex",
            "symbol": symbol,
            "category": cat,
            "direction": "SHORT",
            "signal_type": "STRONG_SELL",
            "entry_price": price,
            "take_profit": round(tp_price, 6),
            "stop_loss": round(sl_price, 6),
            "confidence": round(conf, 3),
            "risk_reward": round(rr, 2),
            "reason": (f"Connors RSI2 Forex SHORT: RSI(2)={rsi_now:.1f} (prev {rsi_prev:.1f}), "
                       f"2-bar overbought, price below EMA50, target EMA5={ema_5:.5f}"),
            "rsi_at_entry": round(rsi_now, 2),
            "atr_at_entry": round(atr_now, 6),
            "max_hold_days": max_hold,
        })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 4: Keltner Compression Forex
# ---------------------------------------------------------------------------
# The crypto keltner_compression_expansion has 72.9% WR on BTC.
# Forex adaptation needs:
# - Longer KC lookback: EMA(30) instead of EMA(20) -- forex trends are slower
# - Wider KC multiplier: 2.0x ATR instead of 1.5x -- forex is less volatile
# - Longer BB period: 30 instead of 20 -- reduces false squeezes
# - Volume filter removed (forex has no reliable volume via yfinance)
# - HMA trend filter kept but with longer period (30 vs 21)

def keltner_compression_forex(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    Keltner Compression adapted for forex:
    - KC: EMA(30), ATR(14) x 2.0 (wider for lower forex volatility)
    - BB: SMA(30), StdDev(2.0) (longer period for forex)
    - No volume filter (forex volume unreliable via yfinance)
    - HMA(30) trend filter (slower for forex trend speed)
    - TP: 2.0x ATR, SL: 1.0x ATR (wider targets for forex)
    """
    signals = []
    cat = info.get("cat", "forex")
    if cat != "forex":
        return signals

    if len(df) < 100:
        return signals

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    price = _sanitize_float(close.iloc[-1])
    if not np.isfinite(price) or price <= 0:
        return signals

    # Keltner Channel: EMA(30) +/- 2.0 * ATR(14)
    kc_ema = ema(close, 30)
    atr_14 = atr(high, low, close, 14)
    kc_upper = kc_ema + 2.0 * atr_14
    kc_lower = kc_ema - 2.0 * atr_14

    # Bollinger Bands: SMA(30), StdDev(2.0)
    bb_mid, bb_upper, bb_lower = bollinger_bands(close, 30, 2.0)

    # Check squeeze on previous bar (squeeze must exist before breakout)
    bb_up_prev = _sanitize_float(bb_upper.iloc[-2])
    bb_lo_prev = _sanitize_float(bb_lower.iloc[-2])
    kc_up_prev = _sanitize_float(kc_upper.iloc[-2])
    kc_lo_prev = _sanitize_float(kc_lower.iloc[-2])

    if not all(np.isfinite([bb_up_prev, bb_lo_prev, kc_up_prev, kc_lo_prev])):
        return signals

    squeeze = bb_up_prev < kc_up_prev and bb_lo_prev > kc_lo_prev
    if not squeeze:
        return signals

    kc_up_now = _sanitize_float(kc_upper.iloc[-1])
    kc_lo_now = _sanitize_float(kc_lower.iloc[-1])
    atr_now = _sanitize_float(atr_14.iloc[-1])

    if not all(np.isfinite([kc_up_now, kc_lo_now, atr_now])) or atr_now <= 0:
        return signals

    # HMA trend filter (period 30 for forex)
    hma_val = _hma(close, 30)
    hma_now = _sanitize_float(hma_val.iloc[-1])
    hma_prev = _sanitize_float(hma_val.iloc[-2])
    if not all(np.isfinite([hma_now, hma_prev])):
        return signals
    hma_rising = hma_now > hma_prev

    # Squeeze duration bonus: longer squeeze = more explosive breakout
    squeeze_bars = 0
    for i in range(2, min(20, len(df))):
        bb_u = _sanitize_float(bb_upper.iloc[-i])
        bb_l = _sanitize_float(bb_lower.iloc[-i])
        kc_u = _sanitize_float(kc_upper.iloc[-i])
        kc_l = _sanitize_float(kc_lower.iloc[-i])
        if np.isfinite(bb_u) and np.isfinite(kc_u) and bb_u < kc_u and bb_l > kc_l:
            squeeze_bars += 1
        else:
            break
    squeeze_bonus = min(0.10, squeeze_bars * 0.015)

    sl_pct, tp_pct, max_hold = FOREX_RISK["keltner_forex"]

    # LONG: price breaks above KC upper + HMA rising
    if price > kc_up_now and hma_rising:
        conf = min(0.92, 0.58 + (price - kc_up_now) / (atr_now + 1e-12) * 0.12 + squeeze_bonus)
        tp_price = price + 2.0 * atr_now
        sl_price = price - 1.0 * atr_now

        signals.append({
            "strategy": "keltner_compression_forex",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "BUY",
            "entry_price": price,
            "take_profit": round(tp_price, 6),
            "stop_loss": round(sl_price, 6),
            "confidence": round(conf, 3),
            "risk_reward": 2.0,
            "reason": (f"Keltner Forex squeeze breakout UP: price > KC upper "
                       f"{kc_up_now:.5f}, HMA rising, squeeze {squeeze_bars} bars, "
                       f"ATR={atr_now:.6f}"),
            "atr_at_entry": round(atr_now, 6),
            "squeeze_bars": squeeze_bars,
            "max_hold_days": max_hold,
        })

    # SHORT: price breaks below KC lower + HMA falling
    elif price < kc_lo_now and not hma_rising:
        conf = min(0.92, 0.58 + (kc_lo_now - price) / (atr_now + 1e-12) * 0.12 + squeeze_bonus)
        tp_price = price - 2.0 * atr_now
        sl_price = price + 1.0 * atr_now

        signals.append({
            "strategy": "keltner_compression_forex",
            "symbol": symbol,
            "category": cat,
            "direction": "SHORT",
            "signal_type": "SELL",
            "entry_price": price,
            "take_profit": round(tp_price, 6),
            "stop_loss": round(sl_price, 6),
            "confidence": round(conf, 3),
            "risk_reward": 2.0,
            "reason": (f"Keltner Forex squeeze breakdown: price < KC lower "
                       f"{kc_lo_now:.5f}, HMA falling, squeeze {squeeze_bars} bars, "
                       f"ATR={atr_now:.6f}"),
            "atr_at_entry": round(atr_now, 6),
            "squeeze_bars": squeeze_bars,
            "max_hold_days": max_hold,
        })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 5: DXY (Dollar Index) Correlation Filter
# ---------------------------------------------------------------------------
# Edge: DXY trends predict USD pair movements with high correlation.
# - DXY up => short EURUSD, GBPUSD, AUDUSD / long USDCAD, USDCHF, USDJPY
# - DXY down => long EURUSD, GBPUSD, AUDUSD / short USDCAD, USDCHF, USDJPY
#
# This is both a standalone strategy AND a macro filter for other forex strategies.
# Standalone: enters when DXY trend is strong + RSI confirms direction.

def dxy_trend_filter(df: pd.DataFrame, symbol: str, info: dict,
                     dxy_df: Optional[pd.DataFrame] = None) -> list[dict]:
    """
    DXY Correlation Strategy:
    - Tracks DXY (Dollar Index) trend via EMA(20)/EMA(50) crossover
    - Enters trades aligned with DXY direction and pair correlation
    - EURUSD has -0.95 correlation with DXY (strongest)
    - Uses ADX on DXY for trend strength confirmation

    Can also be used as a filter: call dxy_macro_check() separately.
    """
    signals = []
    cat = info.get("cat", "forex")
    if cat != "forex":
        return signals

    if dxy_df is None or len(dxy_df) < 60:
        return signals

    if len(df) < 60:
        return signals

    # DXY analysis
    dxy_close = dxy_df["Close"]
    dxy_price = _sanitize_float(dxy_close.iloc[-1])
    dxy_ema20 = _sanitize_float(ema(dxy_close, 20).iloc[-1])
    dxy_ema50 = _sanitize_float(ema(dxy_close, 50).iloc[-1])

    if not all(np.isfinite([dxy_price, dxy_ema20, dxy_ema50])):
        return signals

    # DXY trend direction
    dxy_bullish = dxy_price > dxy_ema20 > dxy_ema50
    dxy_bearish = dxy_price < dxy_ema20 < dxy_ema50

    if not dxy_bullish and not dxy_bearish:
        return signals  # No clear DXY trend

    # DXY ADX for trend strength
    if "High" in dxy_df.columns and "Low" in dxy_df.columns:
        dxy_adx = _sanitize_float(adx(dxy_df["High"], dxy_df["Low"], dxy_close, 14).iloc[-1])
    else:
        dxy_adx = 25.0  # Default if no H/L data

    if not np.isfinite(dxy_adx) or dxy_adx < 20:
        return signals  # DXY trend not strong enough

    # Pair analysis
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    price = _sanitize_float(close.iloc[-1])
    atr_now = _sanitize_float(atr(high, low, close, 14).iloc[-1])
    rsi_14 = _sanitize_float(rsi(close, 14).iloc[-1])

    if not all(np.isfinite([price, atr_now, rsi_14])) or atr_now <= 0 or price <= 0:
        return signals

    # Correlation lookup
    pair_info = FOREX_PAIRS.get(symbol, {})
    correlation = pair_info.get("dxy_correlation", 0.0)

    if abs(correlation) < 0.50:
        return signals  # Correlation too weak

    sl_pct, tp_pct, max_hold = FOREX_RISK["dxy_trend_filter"]

    # Determine trade direction based on DXY trend and correlation
    # DXY bullish + negative correlation (e.g., EURUSD) => SHORT the pair
    # DXY bullish + positive correlation (e.g., USDCHF) => LONG the pair
    # DXY bearish + negative correlation => LONG the pair
    # DXY bearish + positive correlation => SHORT the pair
    if dxy_bullish:
        trade_direction = "SHORT" if correlation < 0 else "LONG"
    else:  # dxy_bearish
        trade_direction = "LONG" if correlation < 0 else "SHORT"

    # RSI confirmation: don't enter against extreme RSI
    if trade_direction == "LONG" and rsi_14 > 70:
        return signals
    if trade_direction == "SHORT" and rsi_14 < 30:
        return signals

    # Confidence: based on DXY ADX strength + correlation magnitude
    conf = min(0.90, 0.50 + dxy_adx * 0.005 + abs(correlation) * 0.15)

    if trade_direction == "LONG":
        tp_price = price + 1.8 * atr_now
        sl_price = price - 1.0 * atr_now
        signal_type = "BUY"
    else:
        tp_price = price - 1.8 * atr_now
        sl_price = price + 1.0 * atr_now
        signal_type = "SELL"

    rr = 1.8  # 1.8:1

    dxy_direction = "BULLISH" if dxy_bullish else "BEARISH"

    signals.append({
        "strategy": "dxy_trend_filter",
        "symbol": symbol,
        "category": cat,
        "direction": trade_direction,
        "signal_type": signal_type,
        "entry_price": price,
        "take_profit": round(tp_price, 6),
        "stop_loss": round(sl_price, 6),
        "confidence": round(conf, 3),
        "risk_reward": rr,
        "reason": (f"DXY {dxy_direction} (ADX={dxy_adx:.1f}), "
                   f"{symbol} corr={correlation:.2f} => {trade_direction}, "
                   f"RSI={rsi_14:.1f}"),
        "dxy_direction": dxy_direction,
        "dxy_adx": round(dxy_adx, 2),
        "dxy_correlation": correlation,
        "atr_at_entry": round(atr_now, 6),
        "max_hold_days": max_hold,
    })

    return signals


# ---------------------------------------------------------------------------
# DXY Macro Filter (for use by other strategies)
# ---------------------------------------------------------------------------

def dxy_macro_check(dxy_df: Optional[pd.DataFrame], symbol: str,
                    direction: str) -> tuple[bool, str]:
    """
    Check if a proposed trade direction aligns with DXY trend.
    Returns (aligned: bool, reason: str).

    Usage: call before accepting any forex signal to filter against DXY.
    """
    if dxy_df is None or len(dxy_df) < 60:
        return True, "DXY data unavailable, passing"

    dxy_close = dxy_df["Close"]
    dxy_price = _sanitize_float(dxy_close.iloc[-1])
    dxy_ema20 = _sanitize_float(ema(dxy_close, 20).iloc[-1])
    dxy_ema50 = _sanitize_float(ema(dxy_close, 50).iloc[-1])

    if not all(np.isfinite([dxy_price, dxy_ema20, dxy_ema50])):
        return True, "DXY data invalid, passing"

    dxy_bullish = dxy_price > dxy_ema20 > dxy_ema50
    dxy_bearish = dxy_price < dxy_ema20 < dxy_ema50

    if not dxy_bullish and not dxy_bearish:
        return True, "DXY no clear trend, passing"

    pair_info = FOREX_PAIRS.get(symbol, {})
    correlation = pair_info.get("dxy_correlation", 0.0)

    if abs(correlation) < 0.50:
        return True, f"Weak DXY correlation ({correlation:.2f}), passing"

    # Expected direction given DXY trend
    if dxy_bullish:
        expected = "SHORT" if correlation < 0 else "LONG"
    else:
        expected = "LONG" if correlation < 0 else "SHORT"

    if direction == expected:
        return True, f"DXY {'BULL' if dxy_bullish else 'BEAR'} aligns with {direction}"
    else:
        return False, (f"DXY {'BULL' if dxy_bullish else 'BEAR'} conflicts: "
                       f"expected {expected}, got {direction}")


# ---------------------------------------------------------------------------
# Strategy registry + aggregated scan function
# ---------------------------------------------------------------------------

# All forex strategies (name -> function)
FOREX_STRATEGIES = {
    "session_overlap":         session_overlap,       # Session-aware momentum + MR
    "carry_trade":             carry_trade,            # Interest rate differential
    # KILLED 2026-04-12: connors_rsi2_forex — 61.75% WR, PF 0.68, -20.6% return.
    # Classic high-WR-negative-economics trap (losses pay too much vs wins).
    # Function retained for backtest / inverse experiments; removed from live
    # registry. See multi_asset/FOCUSED_NONCRYPTO_BACKTEST_REPORT_2026-04-07.md.
    # "connors_rsi2_forex":      connors_rsi2_forex,     # RSI-2 forex-tuned
    "keltner_compression_forex": keltner_compression_forex,  # Keltner squeeze forex
    "dxy_trend_filter":        dxy_trend_filter,       # DXY correlation
}


def scan_forex(symbols: dict, data: dict[str, pd.DataFrame],
               dxy_df: Optional[pd.DataFrame] = None,
               killed_strategies: Optional[set] = None,
               use_dxy_filter: bool = True) -> list[dict]:
    """
    Run all forex-specific strategies on the given forex pairs.

    Args:
        symbols: dict of {ticker: info_dict} for forex pairs
        data: dict of {ticker: DataFrame} with OHLCV data
        dxy_df: Optional DataFrame for DXY (Dollar Index) -- used by dxy_trend_filter
                and as a macro filter for all strategies
        killed_strategies: set of strategy names to skip
        use_dxy_filter: if True, apply DXY macro filter to all signals

    Returns:
        list of signal dicts in scanner.py pick format
    """
    # Defensive import of pre-emission policy gates.
    # Fail-open if the policy module is missing/broken.
    try:
        from alpha_engine.non_crypto_policy import passes_non_crypto_policy
        _policy_available = True
    except Exception:
        _policy_available = False

    all_signals = []
    now_iso = datetime.now(timezone.utc).isoformat()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    killed = killed_strategies or set()

    for symbol, info in symbols.items():
        df = data.get(symbol)
        if df is None or df.empty:
            continue

        cat = info.get("cat", "forex")
        if cat != "forex":
            continue

        for strat_name, strat_fn in FOREX_STRATEGIES.items():
            if strat_name in killed:
                continue

            try:
                # dxy_trend_filter needs dxy_df as extra argument
                if strat_name == "dxy_trend_filter":
                    raw_signals = strat_fn(df, symbol, info, dxy_df=dxy_df)
                else:
                    raw_signals = strat_fn(df, symbol, info)

                for sig in raw_signals:
                    # Apply DXY macro filter to non-DXY strategies
                    if (use_dxy_filter and strat_name != "dxy_trend_filter"
                            and dxy_df is not None):
                        aligned, reason = dxy_macro_check(
                            dxy_df, symbol, sig.get("direction", "LONG"))
                        if not aligned:
                            print(f"    [DXY FILTER] Blocked {symbol} "
                                  f"{sig.get('direction')} via {strat_name}: {reason}")
                            continue
                        sig["dxy_filter"] = reason

                    sig["id"] = _pick_id(sig["strategy"], symbol, today)
                    sig["timestamp"] = now_iso
                    sig["created_at"] = now_iso
                    sig["status"] = "OPEN"
                    sig["source_system"] = "multi_asset_scanner"
                    sig["asset_class"] = "FOREX"

                    # Ensure risk_reward is set
                    if "risk_reward" not in sig and sig.get("take_profit") and sig.get("stop_loss"):
                        tp_dist = abs(sig["take_profit"] - sig["entry_price"])
                        sl_dist = abs(sig["stop_loss"] - sig["entry_price"])
                        sig["risk_reward"] = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 1.0

                    # Pre-emission policy gates (FX session / ATR reachability).
                    if _policy_available:
                        try:
                            ok, reason = passes_non_crypto_policy(sig)
                            if not ok:
                                print(f"    [POLICY] Blocked {symbol} {sig.get('direction')} "
                                      f"via {strat_name}: {reason}")
                                continue
                        except Exception:
                            pass

                    all_signals.append(sig)

            except Exception as e:
                print(f"  ERROR: {strat_name} on {symbol}: {e}")

    return all_signals


# ---------------------------------------------------------------------------
# CLI entry point for standalone testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance required. pip install yfinance")
        sys.exit(1)

    print("=" * 70)
    print("FOREX STRATEGIES v1.0 -- Standalone Scan")
    print("=" * 70)

    # Fetch data for all forex pairs + DXY
    all_tickers = list(FOREX_PAIRS.keys()) + [DXY_TICKER]
    print(f"\nFetching data for {len(all_tickers)} tickers...")

    raw = yf.download(" ".join(all_tickers), period="1y", interval="1d",
                       group_by="ticker", auto_adjust=True, threads=True,
                       progress=False)

    data = {}
    dxy_data = None
    for ticker in all_tickers:
        try:
            if ticker in raw.columns.get_level_values(0):
                df = raw[ticker].dropna()
                if len(df) > 20:
                    if ticker == DXY_TICKER:
                        dxy_data = df
                    else:
                        data[ticker] = df
        except (KeyError, TypeError):
            pass

    print(f"  Loaded: {len(data)} forex pairs, DXY: {'YES' if dxy_data is not None else 'NO'}")

    # Run scan
    signals = scan_forex(FOREX_PAIRS, data, dxy_df=dxy_data)

    print(f"\n{'=' * 70}")
    print(f"RESULTS: {len(signals)} signals")
    print(f"{'=' * 70}")

    for sig in signals:
        direction_icon = "^" if sig["direction"] == "LONG" else "v"
        print(f"  {direction_icon} {sig['symbol']:12s} | {sig['strategy']:30s} | "
              f"{sig['direction']:5s} | conf={sig['confidence']:.2f} | "
              f"R:R={sig.get('risk_reward', 0):.2f}")
        print(f"    {sig['reason']}")
        print()
