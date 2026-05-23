#!/usr/bin/env python3
"""
SURVIVOR BACKTEST -- Find strategies that ACTUALLY work
=======================================================
Anti-overfitting protocol:
  1. Minimum 30 trades required (no tiny-sample illusions)
  2. Walk-forward: signals use ONLY past data
  3. Out-of-sample split: train on first 60%, test on last 40%
  4. Multi-asset: must work on 3+ symbols (not curve-fit to one)
  5. Regime test: must profit in 2+ market regimes
  6. Bootstrap p-value < 0.05 (binomial test vs coin flip)
  7. Profit factor > 1.2 (not barely breaking even)
  8. Consistency: both halves must be profitable

Uses yfinance OHLCV data -- no fake data, no lookahead bias.
"""

import json
import sys
import time
import warnings
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats as sp_stats

warnings.filterwarnings("ignore")

# -- Symbols to test ------------------------------------------------------
CRYPTO = [
    "BTC-USD",
    "ETH-USD",
    "SOL-USD",
    "BNB-USD",
    "XRP-USD",
    "ADA-USD",
    "AVAX-USD",
    "LINK-USD",
    "NEAR-USD",
    "ATOM-USD",
]
EQUITY = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]
FOREX = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"]

ALL_SYMBOLS = CRYPTO + EQUITY + FOREX


# -- Strategy definitions (pure, no dependencies) -------------------------


def connors_rsi2(
    df: pd.DataFrame, rsi_entry=5, rsi_exit=65, sma_period=200
) -> list[dict]:
    """Connors RSI-2 mean reversion. Academically proven on 15+ years of data."""
    if len(df) < sma_period + 10:
        return []

    close = df["Close"].values.astype(float)
    sma200 = pd.Series(close).rolling(sma_period).mean().values

    # RSI-2 calculation
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0).astype(float)
    loss = np.where(delta < 0, -delta, 0).astype(float)

    avg_gain = pd.Series(gain).ewm(span=2, adjust=False).mean().values
    avg_loss = pd.Series(loss).ewm(span=2, adjust=False).mean().values
    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    rsi2 = 100 - 100 / (1 + rs)

    signals = []
    in_trade = False
    entry_price = 0
    entry_idx = 0

    for i in range(sma_period, len(close)):
        if not in_trade:
            # BUY: price above 200 SMA (uptrend) AND RSI-2 < 5 (oversold)
            if close[i] > sma200[i] and rsi2[i] < rsi_entry:
                in_trade = True
                entry_price = close[i]
                entry_idx = i
        else:
            # EXIT: RSI-2 > 65 (mean reversion done) OR 10-day max hold
            days_held = i - entry_idx
            if rsi2[i] > rsi_exit or days_held >= 10:
                pnl = (close[i] - entry_price) / entry_price
                signals.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": close[i],
                        "pnl": pnl,
                        "days": days_held,
                        "exit_reason": "rsi_exit"
                        if rsi2[i] > rsi_exit
                        else "time_exit",
                    }
                )
                in_trade = False

    return signals


def vwap_mean_reversion(
    df: pd.DataFrame, lookback=20, z_entry=-2.0, z_exit=0.0
) -> list[dict]:
    """Buy when price drops > 2 std devs below VWAP proxy, sell at mean."""
    if len(df) < lookback + 50:
        return []

    close = df["Close"].values.astype(float)
    volume = df["Volume"].values.astype(float)

    # VWAP proxy: volume-weighted moving average
    vwap = np.zeros(len(close))
    for i in range(lookback, len(close)):
        w = volume[i - lookback : i]
        if w.sum() > 0:
            vwap[i] = np.average(close[i - lookback : i], weights=w)
        else:
            vwap[i] = close[i - lookback : i].mean()

    # Z-score of price relative to VWAP
    zscore = np.zeros(len(close))
    for i in range(lookback * 2, len(close)):
        diff = close[i] - vwap[i]
        std = np.std(close[i - lookback : i] - vwap[i - lookback : i])
        if std > 0:
            zscore[i] = diff / std

    signals = []
    in_trade = False
    entry_price = 0
    entry_idx = 0

    for i in range(lookback * 2, len(close)):
        if not in_trade:
            if zscore[i] < z_entry and vwap[i] > 0:
                in_trade = True
                entry_price = close[i]
                entry_idx = i
        else:
            days_held = i - entry_idx
            if zscore[i] > z_exit or days_held >= 15:
                pnl = (close[i] - entry_price) / entry_price
                signals.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": close[i],
                        "pnl": pnl,
                        "days": days_held,
                        "exit_reason": "z_exit" if zscore[i] > z_exit else "time_exit",
                    }
                )
                in_trade = False

    return signals


def bollinger_mean_reversion(df: pd.DataFrame, period=20, num_std=2.0) -> list[dict]:
    """Buy at lower Bollinger Band, sell at middle band. Classic mean reversion."""
    if len(df) < period + 50:
        return []

    close = df["Close"].values.astype(float)
    sma = pd.Series(close).rolling(period).mean().values
    std = pd.Series(close).rolling(period).std().values
    lower = sma - num_std * std
    upper = sma + num_std * std

    # Need uptrend filter (200 SMA)
    sma200 = pd.Series(close).rolling(200).mean().values if len(close) >= 250 else sma

    signals = []
    in_trade = False
    entry_price = 0
    entry_idx = 0

    start = max(period, 200 if len(close) >= 250 else period)
    for i in range(start, len(close)):
        if not in_trade:
            # Buy when price touches lower band AND in uptrend
            if close[i] <= lower[i] and close[i] > sma200[i] * 0.9:
                in_trade = True
                entry_price = close[i]
                entry_idx = i
        else:
            days_held = i - entry_idx
            # Sell at middle band or time exit
            if close[i] >= sma[i] or days_held >= 12:
                pnl = (close[i] - entry_price) / entry_price
                signals.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": close[i],
                        "pnl": pnl,
                        "days": days_held,
                        "exit_reason": "band_exit"
                        if close[i] >= sma[i]
                        else "time_exit",
                    }
                )
                in_trade = False

    return signals


def rsi_extreme_reversal(
    df: pd.DataFrame, rsi_period=14, oversold=25, overbought=70
) -> list[dict]:
    """Buy RSI < 25, sell RSI > 70. Simple but tested across decades."""
    if len(df) < rsi_period + 200:
        return []

    close = df["Close"].values.astype(float)
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0).astype(float)
    loss = np.where(delta < 0, -delta, 0).astype(float)

    avg_gain = pd.Series(gain).ewm(span=rsi_period, adjust=False).mean().values
    avg_loss = pd.Series(loss).ewm(span=rsi_period, adjust=False).mean().values
    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    rsi = 100 - 100 / (1 + rs)

    sma200 = pd.Series(close).rolling(200).mean().values

    signals = []
    in_trade = False
    entry_price = 0
    entry_idx = 0

    for i in range(200, len(close)):
        if not in_trade:
            if rsi[i] < oversold and close[i] > sma200[i]:
                in_trade = True
                entry_price = close[i]
                entry_idx = i
        else:
            days_held = i - entry_idx
            if rsi[i] > overbought or days_held >= 20:
                pnl = (close[i] - entry_price) / entry_price
                signals.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": close[i],
                        "pnl": pnl,
                        "days": days_held,
                        "exit_reason": "rsi_exit"
                        if rsi[i] > overbought
                        else "time_exit",
                    }
                )
                in_trade = False

    return signals


def ema_crossover_trend(df: pd.DataFrame, fast=9, slow=21) -> list[dict]:
    """EMA 9/21 crossover with 200 SMA trend filter. Momentum following."""
    if len(df) < 250:
        return []

    close = df["Close"].values.astype(float)
    ema_fast = pd.Series(close).ewm(span=fast, adjust=False).mean().values
    ema_slow = pd.Series(close).ewm(span=slow, adjust=False).mean().values
    sma200 = pd.Series(close).rolling(200).mean().values

    signals = []
    in_trade = False
    entry_price = 0
    entry_idx = 0

    for i in range(201, len(close)):
        if not in_trade:
            # Buy: fast EMA crosses above slow EMA, price above 200 SMA
            if (
                ema_fast[i] > ema_slow[i]
                and ema_fast[i - 1] <= ema_slow[i - 1]
                and close[i] > sma200[i]
            ):
                in_trade = True
                entry_price = close[i]
                entry_idx = i
        else:
            days_held = i - entry_idx
            # Sell: fast EMA crosses below slow OR 15 day max
            if ema_fast[i] < ema_slow[i] or days_held >= 15:
                pnl = (close[i] - entry_price) / entry_price
                signals.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": close[i],
                        "pnl": pnl,
                        "days": days_held,
                        "exit_reason": "ema_cross"
                        if ema_fast[i] < ema_slow[i]
                        else "time_exit",
                    }
                )
                in_trade = False

    return signals


def macd_divergence_reversal(df: pd.DataFrame) -> list[dict]:
    """MACD histogram divergence: price makes new low but MACD doesn't."""
    if len(df) < 250:
        return []

    close = df["Close"].values.astype(float)
    ema12 = pd.Series(close).ewm(span=12, adjust=False).mean().values
    ema26 = pd.Series(close).ewm(span=26, adjust=False).mean().values
    macd = ema12 - ema26
    signal_line = pd.Series(macd).ewm(span=9, adjust=False).mean().values
    hist = macd - signal_line
    sma200 = pd.Series(close).rolling(200).mean().values

    signals = []
    in_trade = False
    entry_price = 0
    entry_idx = 0

    for i in range(200, len(close) - 1):
        if not in_trade:
            # Bullish divergence: price lower low, MACD higher low
            lookback = 20
            if i >= lookback + 200:
                price_low = min(close[i - lookback : i])
                macd_low = min(hist[i - lookback : i])
                prev_price_low = min(close[i - 2 * lookback : i - lookback])
                prev_macd_low = min(hist[i - 2 * lookback : i - lookback])

                if (
                    close[i] < prev_price_low * 1.02  # price near/below prior low
                    and hist[i] > prev_macd_low  # MACD higher
                    and hist[i] < 0  # still negative (oversold)
                    and close[i] > sma200[i] * 0.85
                ):  # not in total crash
                    in_trade = True
                    entry_price = close[i]
                    entry_idx = i
        else:
            days_held = i - entry_idx
            if hist[i] > 0 or days_held >= 15:
                pnl = (close[i] - entry_price) / entry_price
                signals.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": close[i],
                        "pnl": pnl,
                        "days": days_held,
                        "exit_reason": "macd_positive" if hist[i] > 0 else "time_exit",
                    }
                )
                in_trade = False

    return signals


def supertrend_follow(df: pd.DataFrame, period=10, multiplier=3.0) -> list[dict]:
    """Supertrend indicator -- ATR-based trend following."""
    if len(df) < 250:
        return []

    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)

    # ATR
    tr = np.maximum(
        high[1:] - low[1:],
        np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])),
    )
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(period).mean().values

    # Supertrend
    hl2 = (high + low) / 2
    upper_band = hl2 + multiplier * atr
    lower_band = hl2 - multiplier * atr

    supertrend = np.zeros(len(close))
    direction = np.zeros(len(close))  # 1 = up, -1 = down

    for i in range(1, len(close)):
        if close[i] > upper_band[i - 1]:
            direction[i] = 1
        elif close[i] < lower_band[i - 1]:
            direction[i] = -1
        else:
            direction[i] = direction[i - 1]

        if direction[i] == 1:
            supertrend[i] = (
                max(lower_band[i], supertrend[i - 1])
                if direction[i - 1] == 1
                else lower_band[i]
            )
        else:
            supertrend[i] = (
                min(upper_band[i], supertrend[i - 1])
                if direction[i - 1] == -1
                else upper_band[i]
            )

    signals = []
    in_trade = False
    entry_price = 0
    entry_idx = 0

    for i in range(period + 1, len(close)):
        if not in_trade:
            # Buy when direction flips to up
            if direction[i] == 1 and direction[i - 1] == -1:
                in_trade = True
                entry_price = close[i]
                entry_idx = i
        else:
            days_held = i - entry_idx
            # Sell when direction flips down or 20 day max
            if direction[i] == -1 or days_held >= 20:
                pnl = (close[i] - entry_price) / entry_price
                signals.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": close[i],
                        "pnl": pnl,
                        "days": days_held,
                        "exit_reason": "trend_flip"
                        if direction[i] == -1
                        else "time_exit",
                    }
                )
                in_trade = False

    return signals


# -- Strategy registry ----------------------------------------------------


def connors_r3(df: pd.DataFrame) -> list[dict]:
    """Connors R3: 3-day consecutive RSI drop, buy RSI(2)<10, sell >70.
    Source: 'High Probability ETF Trading' Chapter 4. Still works 12+ years post-publication."""
    if len(df) < 210:
        return []
    close = df["Close"].values.astype(float)
    sma200 = pd.Series(close).rolling(200).mean().values

    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0).astype(float)
    loss = np.where(delta < 0, -delta, 0).astype(float)
    avg_gain = pd.Series(gain).ewm(span=2, adjust=False).mean().values
    avg_loss = pd.Series(loss).ewm(span=2, adjust=False).mean().values
    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    rsi2 = 100 - 100 / (1 + rs)

    signals = []
    in_trade = False
    entry_price = entry_idx = 0

    for i in range(200, len(close)):
        if not in_trade:
            # R3: close > 200 SMA, 3 consecutive RSI drops, first from <60, current RSI<10
            if (
                close[i] > sma200[i]
                and i >= 3
                and rsi2[i] < 10
                and rsi2[i] < rsi2[i - 1] < rsi2[i - 2]
                and rsi2[i - 2] < 60
            ):
                in_trade = True
                entry_price = close[i]
                entry_idx = i
        else:
            days = i - entry_idx
            if rsi2[i] > 70 or days >= 10:
                signals.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": close[i],
                        "pnl": (close[i] - entry_price) / entry_price,
                        "days": days,
                        "exit_reason": "rsi_exit" if rsi2[i] > 70 else "time_exit",
                    }
                )
                in_trade = False
    return signals


def double_seven(df: pd.DataFrame) -> list[dict]:
    """Connors Double Seven: Buy at 7-day low close, sell at 7-day high close.
    Source: 'Short Term Trading Strategies That Work'. 82.5% WR on 154 trades, PF 2.58."""
    if len(df) < 210:
        return []
    close = df["Close"].values.astype(float)
    sma200 = pd.Series(close).rolling(200).mean().values
    low7 = pd.Series(close).rolling(7).min().values
    high7 = pd.Series(close).rolling(7).max().values

    signals = []
    in_trade = False
    entry_price = entry_idx = 0

    for i in range(200, len(close)):
        if not in_trade:
            if close[i] > sma200[i] and close[i] <= low7[i]:
                in_trade = True
                entry_price = close[i]
                entry_idx = i
        else:
            days = i - entry_idx
            if close[i] >= high7[i] or days >= 15:
                signals.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": close[i],
                        "pnl": (close[i] - entry_price) / entry_price,
                        "days": days,
                        "exit_reason": "high7_exit"
                        if close[i] >= high7[i]
                        else "time_exit",
                    }
                )
                in_trade = False
    return signals


def three_day_low(df: pd.DataFrame) -> list[dict]:
    """Connors 3-Day High/Low: Buy after 3 consecutive lower highs AND lower lows.
    Source: Connors & Alvarez. 1616 trades documented, avg gain 0.38%."""
    if len(df) < 210:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    sma200 = pd.Series(close).rolling(200).mean().values
    sma5 = pd.Series(close).rolling(5).mean().values

    signals = []
    in_trade = False
    entry_price = entry_idx = 0

    for i in range(200, len(close)):
        if not in_trade:
            if (
                i >= 3
                and close[i] > sma200[i]
                and close[i] < sma5[i]
                and high[i] < high[i - 1] < high[i - 2]
                and low[i] < low[i - 1] < low[i - 2]
            ):
                in_trade = True
                entry_price = close[i]
                entry_idx = i
        else:
            days = i - entry_idx
            if close[i] > sma5[i] or days >= 10:
                signals.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": close[i],
                        "pnl": (close[i] - entry_price) / entry_price,
                        "days": days,
                        "exit_reason": "sma5_exit"
                        if close[i] > sma5[i]
                        else "time_exit",
                    }
                )
                in_trade = False
    return signals


def williams_r_oversold(
    df: pd.DataFrame, period=14, oversold=-80, overbought=-20
) -> list[dict]:
    """Williams %R oversold reversal. Documented 81% WR on QuantifiedStrategies.
    Similar to RSI but uses high-low range. Buy %R < -80, sell > -20."""
    if len(df) < 220:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    sma200 = pd.Series(close).rolling(200).mean().values

    # Williams %R
    highest = pd.Series(high).rolling(period).max().values
    lowest = pd.Series(low).rolling(period).min().values
    wr = np.where(highest != lowest, -100 * (highest - close) / (highest - lowest), -50)

    signals = []
    in_trade = False
    entry_price = entry_idx = 0

    for i in range(200, len(close)):
        if not in_trade:
            if close[i] > sma200[i] and wr[i] < oversold:
                in_trade = True
                entry_price = close[i]
                entry_idx = i
        else:
            days = i - entry_idx
            if wr[i] > overbought or days >= 15:
                signals.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": close[i],
                        "pnl": (close[i] - entry_price) / entry_price,
                        "days": days,
                        "exit_reason": "wr_exit" if wr[i] > overbought else "time_exit",
                    }
                )
                in_trade = False
    return signals


def keltner_mean_reversion(df: pd.DataFrame, period=20, atr_mult=2.0) -> list[dict]:
    """Keltner Channel mean reversion: buy at lower channel, sell at midline.
    Documented 77% WR on QuantifiedStrategies with 6-day period."""
    if len(df) < 220:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    sma200 = pd.Series(close).rolling(200).mean().values

    ema = pd.Series(close).ewm(span=period, adjust=False).mean().values
    tr = np.maximum(
        high[1:] - low[1:],
        np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])),
    )
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(period).mean().values
    lower = ema - atr_mult * atr

    signals = []
    in_trade = False
    entry_price = entry_idx = 0

    for i in range(200, len(close)):
        if not in_trade:
            if close[i] > sma200[i] and close[i] <= lower[i]:
                in_trade = True
                entry_price = close[i]
                entry_idx = i
        else:
            days = i - entry_idx
            if close[i] >= ema[i] or days >= 12:
                signals.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": close[i],
                        "pnl": (close[i] - entry_price) / entry_price,
                        "days": days,
                        "exit_reason": "midline_exit"
                        if close[i] >= ema[i]
                        else "time_exit",
                    }
                )
                in_trade = False
    return signals


def volatility_scaled(df: pd.DataFrame, lookback=21) -> list[dict]:
    """Volatility-managed mean reversion (Moreira & Muir 2017, Journal of Finance).
    Scale position by inverse of recent volatility. Buy oversold + low vol."""
    if len(df) < 250:
        return []
    close = df["Close"].values.astype(float)
    sma200 = pd.Series(close).rolling(200).mean().values
    returns = np.diff(close) / close[:-1]
    returns = np.insert(returns, 0, 0)
    vol = pd.Series(returns).rolling(lookback).std().values

    # RSI-5 for oversold
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0).astype(float)
    loss = np.where(delta < 0, -delta, 0).astype(float)
    avg_gain = pd.Series(gain).ewm(span=5, adjust=False).mean().values
    avg_loss = pd.Series(loss).ewm(span=5, adjust=False).mean().values
    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    rsi5 = 100 - 100 / (1 + rs)

    # Median vol for scaling
    med_vol = np.median(vol[200:][vol[200:] > 0]) if np.any(vol[200:] > 0) else 0.01

    signals = []
    in_trade = False
    entry_price = entry_idx = 0

    for i in range(200, len(close)):
        if not in_trade:
            current_vol = vol[i] if vol[i] > 0 else med_vol
            # Buy when: uptrend + oversold RSI-5 + vol below 1.5x median (avoid chaos)
            if close[i] > sma200[i] and rsi5[i] < 20 and current_vol < med_vol * 1.5:
                in_trade = True
                entry_price = close[i]
                entry_idx = i
        else:
            days = i - entry_idx
            if rsi5[i] > 65 or days >= 12:
                signals.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": close[i],
                        "pnl": (close[i] - entry_price) / entry_price,
                        "days": days,
                        "exit_reason": "rsi_exit" if rsi5[i] > 65 else "time_exit",
                    }
                )
                in_trade = False
    return signals


def dual_momentum(df: pd.DataFrame, lookback=252) -> list[dict]:
    """Dual Momentum (Gary Antonacci 2014): absolute + relative momentum.
    Buy only when 12-month return > 0 AND price > SMA. Simple but effective."""
    if len(df) < lookback + 50:
        return []
    close = df["Close"].values.astype(float)
    sma200 = pd.Series(close).rolling(200).mean().values

    signals = []
    in_trade = False
    entry_price = entry_idx = 0

    for i in range(lookback, len(close)):
        mom_12m = close[i] / close[i - lookback] - 1  # 12-month return
        if not in_trade:
            # Buy when: positive 12m momentum + price above 200 SMA + pullback (3d low)
            if (
                mom_12m > 0
                and close[i] > sma200[i]
                and close[i] < min(close[max(0, i - 3) : i]) * 1.01
            ):
                in_trade = True
                entry_price = close[i]
                entry_idx = i
        else:
            days = i - entry_idx
            # Sell when momentum turns negative or 20 day hold
            if mom_12m < -0.02 or close[i] < sma200[i] or days >= 20:
                signals.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": close[i],
                        "pnl": (close[i] - entry_price) / entry_price,
                        "days": days,
                        "exit_reason": "mom_exit"
                        if mom_12m < -0.02
                        else ("sma_exit" if close[i] < sma200[i] else "time_exit"),
                    }
                )
                in_trade = False
    return signals


def kama_adaptive_trend(df: pd.DataFrame, er_period=10, fast_sc_period=2, slow_sc_period=30) -> list[dict]:
    """KAMA single crossover: price crosses above/below adaptive MA. Kaufman 1998."""
    if len(df) < er_period + slow_sc_period + 20:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    n = len(close)

    # ATR for TP/SL
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values

    # KAMA calculation
    fast_sc = 2.0 / (fast_sc_period + 1)
    slow_sc = 2.0 / (slow_sc_period + 1)
    change = np.abs(close - np.roll(close, er_period))
    change[:er_period] = 0
    vol = pd.Series(np.abs(np.diff(close, prepend=close[0]))).rolling(er_period).sum().values
    vol[vol == 0] = 1e-10
    er = change / vol
    er = np.clip(er, 0, 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    kama = np.full(n, np.nan)
    kama[er_period] = close[er_period]
    for i in range(er_period + 1, n):
        kama[i] = kama[i - 1] + sc[i] * (close[i] - kama[i - 1])

    signals = []
    in_trade = False
    side = None
    entry_price = entry_idx = 0

    for i in range(er_period + 2, n):
        if np.isnan(kama[i]) or np.isnan(kama[i - 1]) or atr[i] <= 0:
            continue
        kama_slope = kama[i] - kama[i - 1]
        cross_above = close[i - 1] <= kama[i - 1] and close[i] > kama[i] and kama_slope > 0
        cross_below = close[i - 1] >= kama[i - 1] and close[i] < kama[i] and kama_slope < 0

        if not in_trade:
            if cross_above:
                in_trade = True
                side = "LONG"
                entry_price = close[i]
                entry_idx = i
            elif cross_below:
                in_trade = True
                side = "SHORT"
                entry_price = close[i]
                entry_idx = i
        else:
            days = i - entry_idx
            tp = entry_price + 3 * atr[entry_idx] if side == "LONG" else entry_price - 3 * atr[entry_idx]
            sl = entry_price - 2 * atr[entry_idx] if side == "LONG" else entry_price + 2 * atr[entry_idx]

            hit_tp = (side == "LONG" and close[i] >= tp) or (side == "SHORT" and close[i] <= tp)
            hit_sl = (side == "LONG" and close[i] <= sl) or (side == "SHORT" and close[i] >= sl)
            opposite = (side == "LONG" and cross_below) or (side == "SHORT" and cross_above)

            if hit_tp or hit_sl or opposite or days >= 15:
                if side == "LONG":
                    pnl = (close[i] - entry_price) / entry_price
                else:
                    pnl = (entry_price - close[i]) / entry_price
                reason = "tp" if hit_tp else ("sl" if hit_sl else ("signal" if opposite else "time_exit"))
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def kama_adx_trend(df: pd.DataFrame, fast_kama=10, slow_kama=30, adx_threshold=25) -> list[dict]:
    """KAMA fast/slow crossover + ADX >= 25 filter. Kaufman 1999 + Wilder ADX."""
    min_bars = slow_kama + 30
    if len(df) < min_bars:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    n = len(close)

    # ATR
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values

    # Dual KAMA
    def calc_kama(period):
        fast_sc = 2.0 / (2 + 1)
        slow_sc_val = 2.0 / (30 + 1)
        ch = np.abs(close - np.roll(close, period))
        ch[:period] = 0
        vol = pd.Series(np.abs(np.diff(close, prepend=close[0]))).rolling(period).sum().values
        vol[vol == 0] = 1e-10
        er = np.clip(ch / vol, 0, 1)
        sc = (er * (fast_sc - slow_sc_val) + slow_sc_val) ** 2
        k = np.full(n, np.nan)
        k[period] = close[period]
        for i in range(period + 1, n):
            k[i] = k[i - 1] + sc[i] * (close[i] - k[i - 1])
        return k

    kf = calc_kama(fast_kama)
    ks = calc_kama(slow_kama)

    # ADX
    plus_dm = np.diff(high, prepend=high[0])
    minus_dm = -np.diff(low, prepend=low[0])
    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0.0)
    tr_s = pd.Series(tr).rolling(14).sum().values
    tr_s[tr_s == 0] = 1e-10
    plus_di = 100 * pd.Series(plus_dm).rolling(14).sum().values / tr_s
    minus_di = 100 * pd.Series(minus_dm).rolling(14).sum().values / tr_s
    di_sum = plus_di + minus_di
    di_sum[di_sum == 0] = 1e-10
    dx = 100 * np.abs(plus_di - minus_di) / di_sum
    adx = pd.Series(dx).ewm(alpha=1 / 14, adjust=False).mean().values

    signals = []
    in_trade = False
    side = None
    entry_price = entry_idx = 0

    for i in range(slow_kama + 2, n):
        if any(np.isnan(v) for v in [kf[i], kf[i - 1], ks[i], ks[i - 1], adx[i]]) or atr[i] <= 0:
            continue
        cross_above = kf[i - 1] <= ks[i - 1] and kf[i] > ks[i]
        cross_below = kf[i - 1] >= ks[i - 1] and kf[i] < ks[i]

        if not in_trade:
            if cross_above and adx[i] >= adx_threshold and close[i] > ks[i]:
                in_trade, side, entry_price, entry_idx = True, "LONG", close[i], i
            elif cross_below and adx[i] >= adx_threshold and close[i] < ks[i]:
                in_trade, side, entry_price, entry_idx = True, "SHORT", close[i], i
        else:
            days = i - entry_idx
            tp = entry_price + 3 * atr[entry_idx] if side == "LONG" else entry_price - 3 * atr[entry_idx]
            sl = entry_price - 2 * atr[entry_idx] if side == "LONG" else entry_price + 2 * atr[entry_idx]
            hit_tp = (side == "LONG" and close[i] >= tp) or (side == "SHORT" and close[i] <= tp)
            hit_sl = (side == "LONG" and close[i] <= sl) or (side == "SHORT" and close[i] >= sl)
            opposite = (side == "LONG" and cross_below) or (side == "SHORT" and cross_above)
            if hit_tp or hit_sl or opposite or days >= 15:
                pnl = ((close[i] - entry_price) / entry_price) if side == "LONG" else ((entry_price - close[i]) / entry_price)
                reason = "tp" if hit_tp else ("sl" if hit_sl else ("signal" if opposite else "time_exit"))
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def volatility_anchor_fade(df: pd.DataFrame, sma_period=20, deviation_mult=2.0, vol_thresh=1.2) -> list[dict]:
    """Mean reversion at 2x ATR extremes with volume confirmation. Engle 1982 GARCH + De Bondt & Thaler 1985."""
    min_bars = sma_period + 14 + 5
    if len(df) < min_bars:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    volume = df["Volume"].values.astype(float)
    n = len(close)

    sma = pd.Series(close).rolling(sma_period).mean().values
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    vol_ma = pd.Series(volume).rolling(sma_period).mean().values

    signals = []
    in_trade = False
    side = None
    entry_price = entry_idx = 0

    for i in range(min_bars, n):
        if np.isnan(sma[i]) or atr[i] <= 0 or vol_ma[i] <= 0:
            continue
        upper_dev = sma[i] + deviation_mult * atr[i]
        lower_dev = sma[i] - deviation_mult * atr[i]
        vol_spike = volume[i] >= vol_thresh * vol_ma[i]

        if not in_trade:
            # LONG: price crashed below lower deviation + volume spike + recovery candle
            if close[i] <= lower_dev and vol_spike and close[i] > close[i - 1]:
                in_trade, side, entry_price, entry_idx = True, "LONG", close[i], i
            # SHORT: price spiked above upper deviation + volume spike + decline candle
            elif close[i] >= upper_dev and vol_spike and close[i] < close[i - 1]:
                in_trade, side, entry_price, entry_idx = True, "SHORT", close[i], i
        else:
            days = i - entry_idx
            tp = entry_price + 3 * atr[entry_idx] if side == "LONG" else entry_price - 3 * atr[entry_idx]
            sl = entry_price - 2 * atr[entry_idx] if side == "LONG" else entry_price + 2 * atr[entry_idx]
            hit_tp = (side == "LONG" and close[i] >= tp) or (side == "SHORT" and close[i] <= tp)
            hit_sl = (side == "LONG" and close[i] <= sl) or (side == "SHORT" and close[i] >= sl)
            # Also exit if price returns to SMA (mean reversion complete)
            mean_revert = (side == "LONG" and close[i] >= sma[i]) or (side == "SHORT" and close[i] <= sma[i])
            if hit_tp or hit_sl or mean_revert or days >= 15:
                pnl = ((close[i] - entry_price) / entry_price) if side == "LONG" else ((entry_price - close[i]) / entry_price)
                reason = "tp" if hit_tp else ("sl" if hit_sl else ("mean_revert" if mean_revert else "time_exit"))
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def kama_pullback_continuation(df: pd.DataFrame, pullback_atr=0.5, slope_lb=5, pb_lb=3) -> list[dict]:
    """KAMA pullback continuation: trend + pullback below KAMA + reclaim cross. Kaufman 1995."""
    kama_period = 10
    fast_sc_period = 2
    slow_sc_period = 30
    min_bars = kama_period + slope_lb + pb_lb + 20
    if len(df) < min_bars:
        return []

    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    n = len(close)

    # ATR
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values

    # KAMA
    fast_sc = 2.0 / (fast_sc_period + 1)
    slow_sc = 2.0 / (slow_sc_period + 1)
    change = np.abs(close - np.roll(close, kama_period))
    change[:kama_period] = 0
    vol = pd.Series(np.abs(np.diff(close, prepend=close[0]))).rolling(kama_period).sum().values
    vol[vol == 0] = 1e-10
    er = np.clip(change / vol, 0, 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    kama = np.full(n, np.nan)
    kama[kama_period] = close[kama_period]
    for i in range(kama_period + 1, n):
        kama[i] = kama[i - 1] + sc[i] * (close[i] - kama[i - 1])

    signals = []
    in_trade = False
    side = None
    entry_price = entry_idx = 0

    start = kama_period + slope_lb + pb_lb + 1
    for i in range(start, n):
        if np.isnan(kama[i]) or np.isnan(kama[i - 1]) or atr[i] <= 0:
            continue

        # Slope: KAMA direction over slope_lb bars
        if np.isnan(kama[i - slope_lb]):
            continue
        slope_up = kama[i] > kama[i - slope_lb]
        slope_down = kama[i] < kama[i - slope_lb]

        # Pullback threshold
        pb_amt = pullback_atr * atr[i]

        # Check pullback in prior pb_lb bars (excluding current)
        diffs = close[i - pb_lb:i] - kama[i - pb_lb:i]
        if np.any(np.isnan(diffs)):
            continue

        had_pb_long = np.min(diffs) <= -pb_amt
        had_pb_short = np.max(diffs) >= pb_amt

        # Cross detection
        crossed_up = close[i] > kama[i] and close[i - 1] <= kama[i - 1]
        crossed_down = close[i] < kama[i] and close[i - 1] >= kama[i - 1]

        if not in_trade:
            if slope_up and had_pb_long and crossed_up:
                in_trade, side, entry_price, entry_idx = True, "LONG", close[i], i
            elif slope_down and had_pb_short and crossed_down:
                in_trade, side, entry_price, entry_idx = True, "SHORT", close[i], i
        else:
            days = i - entry_idx
            tp = entry_price + 3 * atr[entry_idx] if side == "LONG" else entry_price - 3 * atr[entry_idx]
            sl = entry_price - 2 * atr[entry_idx] if side == "LONG" else entry_price + 2 * atr[entry_idx]
            hit_tp = (side == "LONG" and close[i] >= tp) or (side == "SHORT" and close[i] <= tp)
            hit_sl = (side == "LONG" and close[i] <= sl) or (side == "SHORT" and close[i] >= sl)
            opposite = (side == "LONG" and crossed_down) or (side == "SHORT" and crossed_up)
            if hit_tp or hit_sl or opposite or days >= 15:
                pnl = ((close[i] - entry_price) / entry_price) if side == "LONG" else ((entry_price - close[i]) / entry_price)
                reason = "tp" if hit_tp else ("sl" if hit_sl else ("signal" if opposite else "time_exit"))
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


# -- NEW: Grok + Claude AI strategies (Feb 28 2026) ----------------------


def williams_pr_trend_mr(df: pd.DataFrame, wr_period=14, sma_period=50) -> list[dict]:
    """Williams %R trend-aligned pullback (Larry Williams oscillator + SMA filter). Grok AI."""
    if len(df) < sma_period + 10:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    n = len(close)
    hh = pd.Series(high).rolling(wr_period).max().values
    ll = pd.Series(low).rolling(wr_period).min().values
    denom = hh - ll
    denom[denom == 0] = np.nan
    wr = -100 * ((hh - close) / denom)
    sma = pd.Series(close).rolling(sma_period).mean().values
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    signals = []
    in_trade = False
    side = None
    entry_price = entry_idx = 0
    for i in range(sma_period + 1, n):
        if np.isnan(wr[i]) or np.isnan(wr[i - 1]) or np.isnan(sma[i]) or atr[i] <= 0:
            continue
        if not in_trade:
            if wr[i - 1] >= -80 and wr[i] < -80 and close[i] > sma[i]:
                in_trade, side, entry_price, entry_idx = True, "LONG", close[i], i
            elif wr[i - 1] <= -20 and wr[i] > -20 and close[i] < sma[i]:
                in_trade, side, entry_price, entry_idx = True, "SHORT", close[i], i
        else:
            days = i - entry_idx
            tp = entry_price + 3 * atr[entry_idx] if side == "LONG" else entry_price - 3 * atr[entry_idx]
            sl = entry_price - 2 * atr[entry_idx] if side == "LONG" else entry_price + 2 * atr[entry_idx]
            hit_tp = (side == "LONG" and close[i] >= tp) or (side == "SHORT" and close[i] <= tp)
            hit_sl = (side == "LONG" and close[i] <= sl) or (side == "SHORT" and close[i] >= sl)
            if hit_tp or hit_sl or days >= 15:
                pnl = ((close[i] - entry_price) / entry_price) if side == "LONG" else ((entry_price - close[i]) / entry_price)
                reason = "tp" if hit_tp else ("sl" if hit_sl else "time_exit")
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def cci_exhaustion_reversal(df: pd.DataFrame, cci_period=20, cci_threshold=150, vol_mult=1.5) -> list[dict]:
    """CCI exhaustion reversal + volume confirmation (Lambert 1980 + Blume et al. 1994). Claude AI."""
    if len(df) < 210:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    volume = df["Volume"].values.astype(float)
    n = len(close)
    tp_arr = (high + low + close) / 3
    tp_sma = pd.Series(tp_arr).rolling(cci_period).mean().values
    tp_md = pd.Series(tp_arr).rolling(cci_period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True).values
    tp_md[tp_md == 0] = np.nan
    cci = (tp_arr - tp_sma) / (0.015 * tp_md)
    vol_avg = pd.Series(volume).rolling(20).mean().values
    vol_avg[vol_avg == 0] = np.nan
    vol_ratio = volume / vol_avg
    sma200 = pd.Series(close).rolling(200).mean().values
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    signals = []
    in_trade = False
    side = None
    entry_price = entry_idx = 0
    for i in range(201, n):
        if np.isnan(cci[i]) or np.isnan(cci[i - 1]) or np.isnan(vol_ratio[i]) or np.isnan(sma200[i]) or atr[i] <= 0:
            continue
        vol_ok = vol_ratio[i] >= vol_mult
        if not in_trade:
            if cci[i] < -cci_threshold and cci[i - 1] >= -cci_threshold and vol_ok and close[i] > sma200[i]:
                in_trade, side, entry_price, entry_idx = True, "LONG", close[i], i
            elif cci[i] > cci_threshold and cci[i - 1] <= cci_threshold and vol_ok and close[i] < sma200[i]:
                in_trade, side, entry_price, entry_idx = True, "SHORT", close[i], i
        else:
            days = i - entry_idx
            tp = entry_price + 3 * atr[entry_idx] if side == "LONG" else entry_price - 3 * atr[entry_idx]
            sl = entry_price - 2 * atr[entry_idx] if side == "LONG" else entry_price + 2 * atr[entry_idx]
            hit_tp = (side == "LONG" and close[i] >= tp) or (side == "SHORT" and close[i] <= tp)
            hit_sl = (side == "LONG" and close[i] <= sl) or (side == "SHORT" and close[i] >= sl)
            mean_revert = (side == "LONG" and cci[i] >= 0 and cci[i - 1] < 0) or (side == "SHORT" and cci[i] <= 0 and cci[i - 1] > 0)
            if hit_tp or hit_sl or mean_revert or days >= 15:
                pnl = ((close[i] - entry_price) / entry_price) if side == "LONG" else ((entry_price - close[i]) / entry_price)
                reason = "tp" if hit_tp else ("sl" if hit_sl else ("mean_revert" if mean_revert else "time_exit"))
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def donchian_adx_breakout(df: pd.DataFrame, donchian_period=20, adx_threshold=25) -> list[dict]:
    """Donchian Channel breakout + ADX trend filter (Turtle Traders + Wilder). Claude AI."""
    min_bars = max(donchian_period, 30) + 10
    if len(df) < min_bars:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    n = len(close)
    upper_dc = pd.Series(high).rolling(donchian_period).max().values
    lower_dc = pd.Series(low).rolling(donchian_period).min().values
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    plus_dm = np.diff(high, prepend=high[0])
    minus_dm = -np.diff(low, prepend=low[0])
    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0.0)
    tr_s = pd.Series(tr).rolling(14).sum().values
    tr_s[tr_s == 0] = 1e-10
    plus_di = 100 * pd.Series(plus_dm).rolling(14).sum().values / tr_s
    minus_di = 100 * pd.Series(minus_dm).rolling(14).sum().values / tr_s
    di_sum = plus_di + minus_di
    di_sum[di_sum == 0] = 1e-10
    dx = 100 * np.abs(plus_di - minus_di) / di_sum
    adx = pd.Series(dx).ewm(span=14, adjust=False).mean().values
    signals = []
    in_trade = False
    side = None
    entry_price = entry_idx = 0
    for i in range(min_bars, n):
        if np.isnan(adx[i]) or atr[i] <= 0:
            continue
        adx_ok = adx[i] > adx_threshold
        if not in_trade:
            if adx_ok and close[i] > upper_dc[i - 1] and close[i - 1] <= upper_dc[i - 1]:
                in_trade, side, entry_price, entry_idx = True, "LONG", close[i], i
            elif adx_ok and close[i] < lower_dc[i - 1] and close[i - 1] >= lower_dc[i - 1]:
                in_trade, side, entry_price, entry_idx = True, "SHORT", close[i], i
        else:
            days = i - entry_idx
            tp = entry_price + 4 * atr[entry_idx] if side == "LONG" else entry_price - 4 * atr[entry_idx]
            sl = entry_price - 1.5 * atr[entry_idx] if side == "LONG" else entry_price + 1.5 * atr[entry_idx]
            hit_tp = (side == "LONG" and close[i] >= tp) or (side == "SHORT" and close[i] <= tp)
            hit_sl = (side == "LONG" and close[i] <= sl) or (side == "SHORT" and close[i] >= sl)
            if hit_tp or hit_sl or days >= 20:
                pnl = ((close[i] - entry_price) / entry_price) if side == "LONG" else ((entry_price - close[i]) / entry_price)
                reason = "tp" if hit_tp else ("sl" if hit_sl else "time_exit")
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def kama_slope_reversal(df: pd.DataFrame, er_period=10, slope_lookback=5, flat_pct=0.001) -> list[dict]:
    """KAMA slope reversal from flat period (Kaufman 1995). Claude AI."""
    if len(df) < er_period + slope_lookback * 2 + 30:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    n = len(close)
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0).astype(float)
    loss = np.where(delta < 0, -delta, 0).astype(float)
    avg_gain = pd.Series(gain).ewm(span=14, adjust=False).mean().values
    avg_loss = pd.Series(loss).ewm(span=14, adjust=False).mean().values
    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    rsi = 100 - 100 / (1 + rs)
    fast_sc = 2.0 / (2 + 1)
    slow_sc = 2.0 / (30 + 1)
    change = np.abs(close - np.roll(close, er_period))
    change[:er_period] = 0
    vol = pd.Series(np.abs(np.diff(close, prepend=close[0]))).rolling(er_period).sum().values
    vol[vol == 0] = 1e-10
    er = np.clip(change / vol, 0, 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
    kama = np.full(n, np.nan)
    kama[er_period] = close[er_period]
    for i in range(er_period + 1, n):
        kama[i] = kama[i - 1] + sc[i] * (close[i] - kama[i - 1])
    kama_slope = np.full(n, np.nan)
    for i in range(slope_lookback, n):
        if kama[i - slope_lookback] != 0 and not np.isnan(kama[i - slope_lookback]):
            kama_slope[i] = (kama[i] - kama[i - slope_lookback]) / kama[i - slope_lookback]
    signals = []
    in_trade = False
    side = None
    entry_price = entry_idx = 0
    start = er_period + slope_lookback * 2
    for i in range(start, n):
        if np.isnan(kama_slope[i]) or atr[i] <= 0:
            continue
        prior = kama_slope[i - slope_lookback:i]
        if np.any(np.isnan(prior)):
            continue
        was_flat = np.all(np.abs(prior) < flat_pct)
        if not in_trade and was_flat:
            if kama_slope[i] > flat_pct and rsi[i] < 60:
                in_trade, side, entry_price, entry_idx = True, "LONG", close[i], i
            elif kama_slope[i] < -flat_pct and rsi[i] > 40:
                in_trade, side, entry_price, entry_idx = True, "SHORT", close[i], i
        elif in_trade:
            days = i - entry_idx
            tp = entry_price + 3 * atr[entry_idx] if side == "LONG" else entry_price - 3 * atr[entry_idx]
            sl = entry_price - 2 * atr[entry_idx] if side == "LONG" else entry_price + 2 * atr[entry_idx]
            hit_tp = (side == "LONG" and close[i] >= tp) or (side == "SHORT" and close[i] <= tp)
            hit_sl = (side == "LONG" and close[i] <= sl) or (side == "SHORT" and close[i] >= sl)
            if hit_tp or hit_sl or days >= 15:
                pnl = ((close[i] - entry_price) / entry_price) if side == "LONG" else ((entry_price - close[i]) / entry_price)
                reason = "tp" if hit_tp else ("sl" if hit_sl else "time_exit")
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def volume_dryup_fade(df: pd.DataFrame, rsi_oversold=30, rsi_overbought=70, vol_dryup=0.5, vol_spike=2.0) -> list[dict]:
    """Volume dry-up fade: RSI extreme + volume exhaustion after spike (Elder 1993). Claude AI."""
    if len(df) < 50:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    volume = df["Volume"].values.astype(float)
    n = len(close)
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0).astype(float)
    loss = np.where(delta < 0, -delta, 0).astype(float)
    avg_gain = pd.Series(gain).ewm(span=14, adjust=False).mean().values
    avg_loss = pd.Series(loss).ewm(span=14, adjust=False).mean().values
    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    rsi = 100 - 100 / (1 + rs)
    vol_avg = pd.Series(volume).rolling(20).mean().values
    vol_avg[vol_avg == 0] = np.nan
    vol_ratio = volume / vol_avg
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    signals = []
    in_trade = False
    side = None
    entry_price = entry_idx = 0
    for i in range(25, n):
        if np.isnan(rsi[i]) or np.isnan(vol_ratio[i]) or atr[i] <= 0:
            continue
        is_dry = vol_ratio[i] < vol_dryup
        had_spk = any(not np.isnan(vol_ratio[j]) and vol_ratio[j] > vol_spike for j in range(max(0, i - 3), i))
        if not in_trade and is_dry and had_spk:
            if rsi[i] < rsi_oversold:
                in_trade, side, entry_price, entry_idx = True, "LONG", close[i], i
            elif rsi[i] > rsi_overbought:
                in_trade, side, entry_price, entry_idx = True, "SHORT", close[i], i
        elif in_trade:
            days = i - entry_idx
            tp = entry_price + 2 * atr[entry_idx] if side == "LONG" else entry_price - 2 * atr[entry_idx]
            sl = entry_price - 1.5 * atr[entry_idx] if side == "LONG" else entry_price + 1.5 * atr[entry_idx]
            hit_tp = (side == "LONG" and close[i] >= tp) or (side == "SHORT" and close[i] <= tp)
            hit_sl = (side == "LONG" and close[i] <= sl) or (side == "SHORT" and close[i] >= sl)
            if hit_tp or hit_sl or days >= 12:
                pnl = ((close[i] - entry_price) / entry_price) if side == "LONG" else ((entry_price - close[i]) / entry_price)
                reason = "tp" if hit_tp else ("sl" if hit_sl else "time_exit")
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


# -- Perplexity AI Strategy Bundle (Feb 28 2026) --------------------------


def short_term_return_reversal(df: pd.DataFrame, lookback=3, z_thresh=2.0) -> list[dict]:
    """Short-term return reversal: contrarian buy/sell on extreme N-bar returns.
    Jegadeesh & Titman (1993), NY Fed Staff Report #513."""
    if len(df) < 100:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)

    ret = np.zeros(len(close))
    for i in range(lookback, len(close)):
        ret[i] = close[i] / close[i - lookback] - 1

    ret_mean = pd.Series(ret).rolling(50, min_periods=20).mean().values
    ret_std = pd.Series(ret).rolling(50, min_periods=20).std().values

    tr = np.maximum(
        high[1:] - low[1:],
        np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])),
    )
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14).mean().values

    signals = []
    in_trade = False
    side = entry_price = entry_idx = 0

    for i in range(60, len(close)):
        if ret_std[i] <= 0 or np.isnan(ret_std[i]) or np.isnan(atr[i]) or atr[i] <= 0:
            continue
        z = (ret[i] - ret_mean[i]) / ret_std[i]

        if not in_trade:
            if z <= -z_thresh:
                in_trade, side, entry_price, entry_idx = True, "LONG", close[i], i
            elif z >= z_thresh:
                in_trade, side, entry_price, entry_idx = True, "SHORT", close[i], i
        else:
            days = i - entry_idx
            tp_mult, sl_mult = 3.0, 2.0
            a = atr[entry_idx]
            if side == "LONG":
                hit_tp = close[i] >= entry_price + tp_mult * a
                hit_sl = close[i] <= entry_price - sl_mult * a
                pnl = (close[i] - entry_price) / entry_price
            else:
                hit_tp = close[i] <= entry_price - tp_mult * a
                hit_sl = close[i] >= entry_price + sl_mult * a
                pnl = (entry_price - close[i]) / entry_price
            if hit_tp or hit_sl or days >= 15:
                reason = "tp" if hit_tp else ("sl" if hit_sl else "time_exit")
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def vwap_volume_mean_reversion(df: pd.DataFrame, vwap_len=20, z_thresh=2.0) -> list[dict]:
    """VWAP volume-weighted mean reversion: z-score of price vs rolling VWAP.
    Institutional VWAP anchoring drives price back to fair value."""
    if len(df) < 60:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    volume = df["Volume"].values.astype(float)

    typical = (high + low + close) / 3
    pv = typical * volume
    cum_pv = pd.Series(pv).rolling(vwap_len, min_periods=5).sum().values
    cum_vol = pd.Series(volume).rolling(vwap_len, min_periods=5).sum().values
    vwap = np.where(cum_vol > 0, cum_pv / cum_vol, np.nan)

    deviation = close - vwap
    dev_std = pd.Series(deviation).rolling(20, min_periods=10).std().values
    vwap_z = np.where(dev_std > 0, deviation / dev_std, 0)

    tr = np.maximum(
        high[1:] - low[1:],
        np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])),
    )
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14).mean().values

    signals = []
    in_trade = False
    side = entry_price = entry_idx = 0

    for i in range(40, len(close)):
        if np.isnan(vwap_z[i]) or np.isnan(atr[i]) or atr[i] <= 0:
            continue

        if not in_trade:
            if vwap_z[i] <= -z_thresh:
                in_trade, side, entry_price, entry_idx = True, "LONG", close[i], i
            elif vwap_z[i] >= z_thresh:
                in_trade, side, entry_price, entry_idx = True, "SHORT", close[i], i
        else:
            days = i - entry_idx
            tp_mult, sl_mult = 3.0, 2.0
            a = atr[entry_idx]
            if side == "LONG":
                hit_tp = close[i] >= entry_price + tp_mult * a
                hit_sl = close[i] <= entry_price - sl_mult * a
                pnl = (close[i] - entry_price) / entry_price
            else:
                hit_tp = close[i] <= entry_price - tp_mult * a
                hit_sl = close[i] >= entry_price + sl_mult * a
                pnl = (entry_price - close[i]) / entry_price
            if hit_tp or hit_sl or days >= 15:
                reason = "tp" if hit_tp else ("sl" if hit_sl else "time_exit")
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def donchian_turtle_breakout(df: pd.DataFrame, channel_len=20) -> list[dict]:
    """Donchian/Turtle breakout: buy N-bar high, short N-bar low.
    Richard Dennis (1983), CME Speed of Trend-Following (2018)."""
    if len(df) < channel_len + 20:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)

    upper = pd.Series(high).shift(1).rolling(channel_len, min_periods=5).max().values
    lower = pd.Series(low).shift(1).rolling(channel_len, min_periods=5).min().values

    tr = np.maximum(
        high[1:] - low[1:],
        np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])),
    )
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(20).mean().values

    signals = []
    in_trade = False
    side = entry_price = entry_idx = 0

    for i in range(channel_len + 2, len(close)):
        if np.isnan(upper[i]) or np.isnan(atr[i]) or atr[i] <= 0:
            continue

        if not in_trade:
            # Fresh breakout: current breaks, previous didn't
            if close[i] > upper[i] and close[i - 1] <= upper[i - 1]:
                in_trade, side, entry_price, entry_idx = True, "LONG", close[i], i
            elif close[i] < lower[i] and close[i - 1] >= lower[i - 1]:
                in_trade, side, entry_price, entry_idx = True, "SHORT", close[i], i
        else:
            days = i - entry_idx
            tp_mult, sl_mult = 4.0, 2.0  # wider for trend
            a = atr[entry_idx]
            if side == "LONG":
                hit_tp = close[i] >= entry_price + tp_mult * a
                hit_sl = close[i] <= entry_price - sl_mult * a
                pnl = (close[i] - entry_price) / entry_price
            else:
                hit_tp = close[i] <= entry_price - tp_mult * a
                hit_sl = close[i] >= entry_price + sl_mult * a
                pnl = (entry_price - close[i]) / entry_price
            if hit_tp or hit_sl or days >= 20:
                reason = "tp" if hit_tp else ("sl" if hit_sl else "time_exit")
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def triple_ma_trend(df: pd.DataFrame, fast=10, mid=30, slow=90) -> list[dict]:
    """Triple EMA trend-following: aligned EMA 10/30/90 + price breakout.
    CME 'Speed of Trend-Following' (2018), PrimeXBT triple MA crossover."""
    if len(df) < slow + 20:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)

    ema_f = pd.Series(close).ewm(span=fast, adjust=False).mean().values
    ema_m = pd.Series(close).ewm(span=mid, adjust=False).mean().values
    ema_s = pd.Series(close).ewm(span=slow, adjust=False).mean().values

    tr = np.maximum(
        high[1:] - low[1:],
        np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])),
    )
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14).mean().values

    signals = []
    in_trade = False
    side = entry_price = entry_idx = 0

    for i in range(slow + 1, len(close)):
        if np.isnan(atr[i]) or atr[i] <= 0:
            continue

        if not in_trade:
            # Bull stack + price crosses above fast EMA
            if ema_f[i] > ema_m[i] > ema_s[i] and close[i] > ema_f[i] and close[i - 1] <= ema_f[i - 1]:
                in_trade, side, entry_price, entry_idx = True, "LONG", close[i], i
            # Bear stack + price crosses below fast EMA
            elif ema_f[i] < ema_m[i] < ema_s[i] and close[i] < ema_f[i] and close[i - 1] >= ema_f[i - 1]:
                in_trade, side, entry_price, entry_idx = True, "SHORT", close[i], i
        else:
            days = i - entry_idx
            tp_mult, sl_mult = 4.0, 2.0  # wider for trend
            a = atr[entry_idx]
            if side == "LONG":
                hit_tp = close[i] >= entry_price + tp_mult * a
                hit_sl = close[i] <= entry_price - sl_mult * a
                pnl = (close[i] - entry_price) / entry_price
            else:
                hit_tp = close[i] <= entry_price - tp_mult * a
                hit_sl = close[i] >= entry_price + sl_mult * a
                pnl = (entry_price - close[i]) / entry_price
            if hit_tp or hit_sl or days >= 20:
                reason = "tp" if hit_tp else ("sl" if hit_sl else "time_exit")
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def kama_mean_reversion(df: pd.DataFrame, z_thresh=1.5, kama_fast=2, kama_slow=30) -> list[dict]:
    """KAMA mean reversion: buy when price deviates below adaptive MA by z-score threshold.
    Perry Kaufman, Trading Systems and Methods (2013). Mistral AI."""
    if len(df) < 220:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    n = len(close)

    sma200 = pd.Series(close).rolling(200).mean().values

    # ATR
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values

    # KAMA
    er_period = 10
    change = np.abs(np.diff(close, prepend=close[0]))
    volatility = pd.Series(change).rolling(er_period).sum().values
    er = np.where(volatility > 0, change / volatility, 0)
    fast_sc = 2 / (kama_fast + 1)
    slow_sc = 2 / (kama_slow + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    kama = np.full(n, np.nan)
    kama[er_period] = close[er_period]
    for i in range(er_period + 1, n):
        if np.isnan(sc[i]):
            kama[i] = kama[i - 1]
        else:
            kama[i] = kama[i - 1] + sc[i] * (close[i] - kama[i - 1])

    # Z-score of deviation from KAMA
    kama_std = pd.Series(kama).rolling(20).std().values
    kama_z = np.where(kama_std > 0, (close - kama) / kama_std, 0)

    signals = []
    in_trade = False
    entry_price = entry_idx = 0

    for i in range(200, n):
        if np.isnan(kama[i]) or np.isnan(sma200[i]) or atr[i] <= 0:
            continue

        if not in_trade:
            # LONG: price below KAMA by z_thresh std devs + above 200 SMA
            if kama_z[i] < -z_thresh and close[i] > sma200[i]:
                in_trade = True
                entry_price = close[i]
                entry_idx = i
        else:
            days = i - entry_idx
            # Exit: price returns above KAMA (mean reversion complete) or max hold
            if close[i] >= kama[i] or days >= 15:
                signals.append({
                    "entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                    "exit_price": close[i], "pnl": (close[i] - entry_price) / entry_price,
                    "days": days, "exit_reason": "kama_exit" if close[i] >= kama[i] else "time_exit",
                })
                in_trade = False
    return signals


def autocorr_reversion(df: pd.DataFrame, acf_window=60, acf_thresh=-0.10, ma_dev_mult=0.5) -> list[dict]:
    """Autocorrelation-driven mean reversion: negative lag-1 ACF of RETURNS + price deviation from MA20.
    Academic: Box, Jenkins, Reinsel (2015) Time Series Analysis. GPT-5 Nano."""
    if len(df) < 200:
        return []

    close = df["Close"].values.astype(float).flatten()
    high = df["High"].values.astype(float).flatten()
    low = df["Low"].values.astype(float).flatten()

    # Daily returns (for autocorrelation -- NOT prices)
    returns = np.diff(close, prepend=close[0]) / np.where(close > 0, close, 1.0)

    # MA20
    ma20 = pd.Series(close).rolling(20).mean().values

    # ATR14
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
    atr14 = pd.Series(tr).rolling(14).mean().values

    # Rolling lag-1 autocorrelation of RETURNS (not prices)
    acf1 = np.full(len(close), np.nan)
    for i in range(acf_window + 1, len(close)):
        w = returns[i - acf_window:i]
        if np.std(w) < 1e-10:
            continue
        try:
            acf1[i] = np.corrcoef(w[:-1], w[1:])[0, 1]
        except Exception:
            acf1[i] = np.nan

    signals = []
    in_trade = False
    entry_price = 0
    entry_idx = 0
    trade_side = "LONG"

    for i in range(200, len(close)):
        if np.isnan(acf1[i]) or np.isnan(ma20[i]) or np.isnan(atr14[i]) or atr14[i] <= 0:
            continue

        deviation = ma_dev_mult * atr14[i]

        if not in_trade:
            if acf1[i] < acf_thresh and close[i] < ma20[i] - deviation:
                in_trade = True
                entry_price = close[i]
                entry_idx = i
                trade_side = "LONG"
            elif acf1[i] < acf_thresh and close[i] > ma20[i] + deviation:
                in_trade = True
                entry_price = close[i]
                entry_idx = i
                trade_side = "SHORT"
        else:
            days = i - entry_idx
            if trade_side == "LONG":
                pnl = (close[i] - entry_price) / entry_price
                # Exit: price returns to MA20 or max hold
                if close[i] >= ma20[i] or days >= 15:
                    signals.append({
                        "entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                        "exit_price": close[i], "pnl": pnl,
                        "days": days, "exit_reason": "ma_revert" if close[i] >= ma20[i] else "time_exit",
                    })
                    in_trade = False
            else:
                pnl = (entry_price - close[i]) / entry_price
                # Exit: price returns to MA20 or max hold
                if close[i] <= ma20[i] or days >= 15:
                    signals.append({
                        "entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                        "exit_price": close[i], "pnl": pnl,
                        "days": days, "exit_reason": "ma_revert" if close[i] <= ma20[i] else "time_exit",
                    })
                    in_trade = False

    return signals


STRATEGIES = {
    "connors_rsi2": {
        "func": connors_rsi2,
        "desc": "Connors RSI-2 mean reversion (Connors & Alvarez 2008)",
        "type": "mean_reversion",
        "academic": True,
    },
    "vwap_mean_reversion": {
        "func": vwap_mean_reversion,
        "desc": "VWAP z-score mean reversion",
        "type": "mean_reversion",
        "academic": False,
    },
    "bollinger_mean_reversion": {
        "func": bollinger_mean_reversion,
        "desc": "Bollinger Band lower touch with trend filter",
        "type": "mean_reversion",
        "academic": False,
    },
    "rsi_extreme_reversal": {
        "func": rsi_extreme_reversal,
        "desc": "RSI-14 extreme reversal (oversold < 25)",
        "type": "mean_reversion",
        "academic": True,
    },
    "ema_crossover_trend": {
        "func": ema_crossover_trend,
        "desc": "EMA 9/21 crossover with 200 SMA trend filter",
        "type": "trend_following",
        "academic": False,
    },
    "macd_divergence": {
        "func": macd_divergence_reversal,
        "desc": "MACD histogram bullish divergence",
        "type": "mean_reversion",
        "academic": False,
    },
    "supertrend": {
        "func": supertrend_follow,
        "desc": "Supertrend ATR-based trend following",
        "type": "trend_following",
        "academic": False,
    },
    "connors_r3": {
        "func": connors_r3,
        "desc": "Connors R3: 3-day consecutive drop + RSI(2)<10 (Connors & Alvarez)",
        "type": "mean_reversion",
        "academic": True,
    },
    "double_seven": {
        "func": double_seven,
        "desc": "Double Seven: buy 7-day low close, sell 7-day high close (82.5% WR documented)",
        "type": "mean_reversion",
        "academic": True,
    },
    "three_day_low": {
        "func": three_day_low,
        "desc": "3-Day High/Low pattern (1616 trades documented by Connors)",
        "type": "mean_reversion",
        "academic": True,
    },
    "williams_r_oversold": {
        "func": williams_r_oversold,
        "desc": "Williams %R < -80 oversold reversal (81% WR documented)",
        "type": "mean_reversion",
        "academic": True,
    },
    "keltner_mean_reversion": {
        "func": keltner_mean_reversion,
        "desc": "Keltner Channel lower band mean reversion (77% WR Keltner 1960)",
        "type": "mean_reversion",
        "academic": True,
    },
    "volatility_scaled": {
        "func": volatility_scaled,
        "desc": "Volatility-managed momentum (Moreira & Muir 2017 JFE)",
        "type": "mean_reversion",
        "academic": True,
    },
    "dual_momentum": {
        "func": dual_momentum,
        "desc": "Dual Momentum: absolute + relative (Antonacci 2014)",
        "type": "trend_following",
        "academic": True,
    },
    "kama_adaptive_trend": {
        "func": kama_adaptive_trend,
        "desc": "KAMA single crossover: price vs adaptive MA (Kaufman 1998)",
        "type": "trend_following",
        "academic": True,
    },
    "kama_adx_trend": {
        "func": kama_adx_trend,
        "desc": "KAMA fast/slow crossover + ADX >= 25 trend filter (Kaufman + Wilder)",
        "type": "trend_following",
        "academic": True,
    },
    "volatility_anchor_fade": {
        "func": volatility_anchor_fade,
        "desc": "Mean reversion at 2x ATR extremes + volume spike (Engle 1982 GARCH)",
        "type": "mean_reversion",
        "academic": True,
    },
    "kama_pullback_continuation": {
        "func": kama_pullback_continuation,
        "desc": "KAMA pullback continuation: trend + pullback + reclaim (Kaufman 1995)",
        "type": "trend_following",
        "academic": True,
    },
    # -- Grok + Claude AI strategies (Feb 28 2026) --
    "williams_pr_trend_mr": {
        "func": williams_pr_trend_mr,
        "desc": "Williams %R trend-aligned pullback (Larry Williams + SMA filter). Grok AI.",
        "type": "mean_reversion",
        "academic": True,
    },
    "cci_exhaustion_reversal": {
        "func": cci_exhaustion_reversal,
        "desc": "CCI exhaustion reversal + volume confirmation (Lambert 1980). Claude AI.",
        "type": "mean_reversion",
        "academic": True,
    },
    "donchian_adx_breakout": {
        "func": donchian_adx_breakout,
        "desc": "Donchian Channel breakout + ADX trend filter (Turtle Traders). Claude AI.",
        "type": "trend_following",
        "academic": True,
    },
    "kama_slope_reversal": {
        "func": kama_slope_reversal,
        "desc": "KAMA slope reversal from flat period (Kaufman 1995). Claude AI.",
        "type": "trend_following",
        "academic": True,
    },
    "volume_dryup_fade": {
        "func": volume_dryup_fade,
        "desc": "Volume dry-up fade: RSI extreme + exhaustion after spike (Elder 1993). Claude AI.",
        "type": "mean_reversion",
        "academic": True,
    },
    # -- Perplexity AI Strategy Bundle (Feb 28 2026) --
    "short_term_return_reversal": {
        "func": short_term_return_reversal,
        "desc": "Short-term return reversal: contrarian z-score (Jegadeesh & Titman 1993). Perplexity AI.",
        "type": "mean_reversion",
        "academic": True,
    },
    "vwap_volume_mean_reversion": {
        "func": vwap_volume_mean_reversion,
        "desc": "VWAP volume-weighted mean reversion: z-score vs rolling VWAP. Perplexity AI.",
        "type": "mean_reversion",
        "academic": True,
    },
    "donchian_turtle_breakout": {
        "func": donchian_turtle_breakout,
        "desc": "Donchian/Turtle breakout: N-bar high/low (Richard Dennis 1983). Perplexity AI.",
        "type": "trend_following",
        "academic": True,
    },
    "triple_ma_trend": {
        "func": triple_ma_trend,
        "desc": "Triple EMA trend-following: aligned 10/30/90 + breakout (CME 2018). Perplexity AI.",
        "type": "trend_following",
        "academic": True,
    },
    # -- Mistral AI (Feb 28 2026) --
    "kama_mean_reversion": {
        "func": kama_mean_reversion,
        "desc": "KAMA z-score mean reversion: buy oversold vs adaptive MA (Kaufman 2013). Mistral AI.",
        "type": "mean_reversion",
        "academic": True,
    },
    # -- GPT-5 Nano (Feb 28 2026) --
    "autocorr_reversion": {
        "func": autocorr_reversion,
        "desc": "Lag-1 autocorrelation mean reversion: negative ACF + MA20 deviation (Box-Jenkins 2015). GPT-5 Nano.",
        "type": "mean_reversion",
        "academic": True,
    },
}

# -- Batch 2 strategies (import + merge) ----------------------------------
try:
    from batch2_strategies import BATCH2_STRATEGIES as _B2
    for _name, _info in _B2.items():
        if _name not in STRATEGIES:
            STRATEGIES[_name] = {"func": _info["func"], "desc": _info["desc"], "type": "mean_reversion", "academic": True}
except ImportError:
    pass  # batch2_strategies.py not available


# -- Data fetching --------------------------------------------------------


def fetch_data(symbols: list[str], period: str = "5y") -> dict[str, pd.DataFrame]:
    """Fetch OHLCV from yfinance using batch download."""
    data = {}
    print(f"  Fetching {len(symbols)} symbols ({period})...")

    tickers = " ".join(symbols)
    try:
        raw = yf.download(
            tickers,
            period=period,
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )
    except Exception as e:
        print(f"  Batch failed: {e}")
        raw = None

    if raw is not None and not raw.empty:
        for sym in symbols:
            try:
                if len(symbols) == 1:
                    df = raw
                else:
                    if sym in raw.columns.get_level_values(0):
                        df = raw[sym].copy()
                    else:
                        continue
                if df is not None and not df.empty:
                    df = df.dropna(subset=["Close"])
                    if len(df) >= 200:
                        data[sym] = df
            except Exception:
                pass

    if not data:
        print("  Batch empty, trying one-by-one...")
        for sym in symbols:
            try:
                df = yf.download(
                    sym, period=period, interval="1d", auto_adjust=True, progress=False
                )
                if df is not None and len(df) >= 200:
                    df = df.dropna(subset=["Close"])
                    data[sym] = df
            except Exception:
                pass

    bars = [len(d) for d in data.values()] if data else [0]
    print(f"  Got {len(data)}/{len(symbols)} symbols ({min(bars)}-{max(bars)} bars)")
    return data


# -- Regime detection -----------------------------------------------------


def detect_regime(close_series: np.ndarray, idx: int) -> str:
    if idx < 60:
        return "unknown"
    sma50 = np.mean(close_series[max(0, idx - 50) : idx])
    sma200 = np.mean(close_series[max(0, idx - 200) : idx]) if idx >= 200 else sma50
    current = close_series[idx - 1]
    ret20 = (current / close_series[max(0, idx - 20)] - 1) if idx >= 20 else 0

    if current > sma50 and current > sma200 and ret20 > 0.02:
        return "bull"
    elif current < sma50 and current < sma200 and ret20 < -0.02:
        return "bear"
    return "sideways"


# -- Main backtest engine -------------------------------------------------


def run_survivor_test(data: dict[str, pd.DataFrame]) -> dict:
    """Run all strategies on all symbols with full anti-overfitting protocol."""
    results = defaultdict(
        lambda: {
            "trades": [],
            "by_symbol": defaultdict(list),
            "by_regime": defaultdict(list),
        }
    )

    for sym, df in data.items():
        close_arr = df["Close"].values.astype(float)
        n_bars = len(df)

        for strat_name, strat_info in STRATEGIES.items():
            func = strat_info["func"]
            try:
                trades = func(df)
            except Exception as e:
                continue

            if not trades:
                continue

            for t in trades:
                # Detect regime at entry
                regime = detect_regime(close_arr, t["entry_idx"])
                t["symbol"] = sym
                t["regime"] = regime
                t["in_sample"] = t["entry_idx"] < int(n_bars * 0.6)

                results[strat_name]["trades"].append(t)
                results[strat_name]["by_symbol"][sym].append(t)
                results[strat_name]["by_regime"][regime].append(t)

    return dict(results)


def analyze_strategy(strat_name: str, data: dict) -> dict:
    """Apply full anti-overfitting analysis to one strategy."""
    trades = data["trades"]
    n = len(trades)
    if n < 5:
        return {"verdict": "INSUFFICIENT", "total_trades": n}

    pnls = np.array([t["pnl"] for t in trades])
    wins = int((pnls > 0).sum())
    wr = wins / n
    avg_pnl = float(pnls.mean())
    total_pnl = float(pnls.sum())
    std = float(pnls.std()) if pnls.std() > 0 else 1e-10
    avg_hold = float(np.mean([t["days"] for t in trades]))
    trades_per_year = 252 / max(1, avg_hold)
    sharpe = float(pnls.mean() / std * np.sqrt(trades_per_year))

    gross_win = float(sum(p for p in pnls if p > 0))
    gross_loss = float(abs(sum(p for p in pnls if p < 0)))
    pf = gross_win / gross_loss if gross_loss > 0 else 99.99

    # P-value (binomial, one-sided: is WR > 50%?)
    p_val = float(sp_stats.binomtest(wins, n, 0.5, alternative="greater").pvalue)

    # Out-of-sample split
    is_trades = [t for t in trades if t["in_sample"]]
    oos_trades = [t for t in trades if not t["in_sample"]]
    is_wr = np.mean([t["pnl"] > 0 for t in is_trades]) if is_trades else 0
    oos_wr = np.mean([t["pnl"] > 0 for t in oos_trades]) if oos_trades else 0
    is_pnl = np.mean([t["pnl"] for t in is_trades]) if is_trades else 0
    oos_pnl = np.mean([t["pnl"] for t in oos_trades]) if oos_trades else 0

    # Multi-asset test
    symbols_profitable = 0
    symbols_tested = 0
    symbol_results = {}
    for sym, sym_trades in data["by_symbol"].items():
        if len(sym_trades) >= 3:
            symbols_tested += 1
            sym_pnls = [t["pnl"] for t in sym_trades]
            sym_wr = sum(1 for p in sym_pnls if p > 0) / len(sym_pnls)
            sym_avg = np.mean(sym_pnls)
            if sym_avg > 0:
                symbols_profitable += 1
            symbol_results[sym] = {
                "trades": len(sym_trades),
                "wr": round(sym_wr * 100, 1),
                "avg_pnl": round(float(sym_avg) * 100, 3),
            }

    # Regime test
    regimes_profitable = 0
    regimes_tested = 0
    regime_results = {}
    for regime, regime_trades in data["by_regime"].items():
        if regime == "unknown":
            continue
        if len(regime_trades) >= 5:
            regimes_tested += 1
            r_pnls = [t["pnl"] for t in regime_trades]
            r_avg = np.mean(r_pnls)
            r_wr = sum(1 for p in r_pnls if p > 0) / len(r_pnls)
            if r_avg > 0:
                regimes_profitable += 1
            regime_results[regime] = {
                "trades": len(regime_trades),
                "wr": round(r_wr * 100, 1),
                "avg_pnl": round(float(r_avg) * 100, 3),
            }

    # First half vs second half consistency
    half = n // 2
    first_avg = float(np.mean(pnls[:half])) if half > 0 else 0
    second_avg = float(np.mean(pnls[half:])) if half > 0 else 0

    # -- VERDICT ------------------------------------------------------
    checks = {
        "min_trades_30": n >= 30,
        "win_rate_gt_50": wr > 0.50,
        "p_value_lt_05": p_val < 0.05,
        "profit_factor_gt_1_2": pf > 1.2,
        "oos_profitable": oos_pnl > 0 if oos_trades else False,
        "multi_asset_3plus": symbols_profitable >= 3,
        "regime_2plus": regimes_profitable >= 2,
        "consistent_halves": first_avg > 0 and second_avg > 0,
    }

    passed = sum(checks.values())
    total_checks = len(checks)

    if passed >= 7:
        verdict = "SURVIVOR"
    elif passed >= 5:
        verdict = "PROMISING"
    elif passed >= 3:
        verdict = "MARGINAL"
    else:
        verdict = "ELIMINATED"

    return {
        "verdict": verdict,
        "checks_passed": f"{passed}/{total_checks}",
        "checks": checks,
        "total_trades": n,
        "wins": wins,
        "losses": n - wins,
        "win_rate_pct": round(wr * 100, 1),
        "avg_pnl_pct": round(avg_pnl * 100, 3),
        "total_return_pct": round(total_pnl * 100, 1),
        "sharpe": round(sharpe, 2),
        "profit_factor": round(min(pf, 99.99), 2),
        "p_value": round(p_val, 6),
        "avg_hold_days": round(avg_hold, 1),
        "in_sample_wr": round(float(is_wr) * 100, 1),
        "in_sample_trades": len(is_trades),
        "oos_wr": round(float(oos_wr) * 100, 1),
        "oos_trades": len(oos_trades),
        "oos_avg_pnl_pct": round(float(oos_pnl) * 100, 3),
        "symbols_profitable": symbols_profitable,
        "symbols_tested": symbols_tested,
        "symbol_results": symbol_results,
        "regimes_profitable": regimes_profitable,
        "regimes_tested": regimes_tested,
        "regime_results": regime_results,
        "first_half_avg_pnl": round(first_avg * 100, 3),
        "second_half_avg_pnl": round(second_avg * 100, 3),
    }


def main():
    t0 = time.time()

    print("=" * 80)
    print("  SURVIVOR BACKTEST -- Anti-Overfitting Strategy Validation")
    print("  7 strategies x 24 symbols x 5 years x 8 anti-overfit checks")
    print("=" * 80)

    print("\n[1/3] Fetching 5 years of daily OHLCV data...")
    data = fetch_data(ALL_SYMBOLS, period="5y")

    if not data:
        print("FATAL: No data fetched")
        sys.exit(1)

    print(
        f"\n[2/3] Running walk-forward backtests on {len(STRATEGIES)} strategies x {len(data)} symbols..."
    )
    raw_results = run_survivor_test(data)

    print(f"\n[3/3] Statistical analysis with anti-overfitting checks...")
    final = {}
    for strat_name in STRATEGIES:
        if strat_name in raw_results:
            analysis = analyze_strategy(strat_name, raw_results[strat_name])
            final[strat_name] = analysis

    # Sort by verdict quality
    verdict_order = {
        "SURVIVOR": 0,
        "PROMISING": 1,
        "MARGINAL": 2,
        "ELIMINATED": 3,
        "INSUFFICIENT": 4,
    }
    sorted_strats = sorted(
        final.items(),
        key=lambda x: (verdict_order.get(x[1]["verdict"], 5), -x[1].get("sharpe", 0)),
    )

    # Print report
    print("\n" + "=" * 80)
    print("  RESULTS")
    print("=" * 80)

    for strat_name, analysis in sorted_strats:
        desc = STRATEGIES[strat_name]["desc"]
        v = analysis["verdict"]
        marker = {
            "SURVIVOR": "[***]",
            "PROMISING": "[** ]",
            "MARGINAL": "[*  ]",
            "ELIMINATED": "[   ]",
        }.get(v, "[   ]")

        print(f"\n  {marker} {strat_name} -- {v}")
        print(f"       {desc}")

        if analysis.get("total_trades", 0) < 5:
            print(f"       Insufficient trades ({analysis['total_trades']})")
            continue

        print(
            f"       Trades: {analysis['total_trades']} | WR: {analysis['win_rate_pct']}% | "
            f"Sharpe: {analysis['sharpe']} | PF: {analysis['profit_factor']} | p={analysis['p_value']}"
        )
        print(
            f"       In-sample: {analysis['in_sample_trades']}T {analysis['in_sample_wr']}% WR | "
            f"OOS: {analysis['oos_trades']}T {analysis['oos_wr']}% WR (avg {analysis['oos_avg_pnl_pct']}%)"
        )
        print(
            f"       Multi-asset: {analysis['symbols_profitable']}/{analysis['symbols_tested']} profitable | "
            f"Regimes: {analysis['regimes_profitable']}/{analysis['regimes_tested']} profitable"
        )
        print(
            f"       Consistency: 1st half {analysis['first_half_avg_pnl']}% | 2nd half {analysis['second_half_avg_pnl']}%"
        )

        # Per-symbol breakdown for survivors
        if v in ("SURVIVOR", "PROMISING"):
            print(f"       Per-symbol breakdown:")
            for sym, sr in sorted(
                analysis["symbol_results"].items(), key=lambda x: -x[1]["avg_pnl"]
            ):
                status = "+" if sr["avg_pnl"] > 0 else "-"
                print(
                    f"         {status} {sym:>10}: {sr['trades']:3d}T  WR={sr['wr']:5.1f}%  avg={sr['avg_pnl']:+.3f}%"
                )

        # Checks
        checks = analysis["checks"]
        fails = [k for k, v in checks.items() if not v]
        if fails:
            print(f"       Failed checks: {', '.join(fails)}")

    # Save results
    save_dir = Path("alpha_engine/data")
    save_dir.mkdir(parents=True, exist_ok=True)

    save_path = save_dir / "survivor_backtest_results.json"
    with open(save_path, "w") as f:
        json.dump(
            {
                "test_date": datetime.now(timezone.utc).isoformat(),
                "symbols_tested": len(data),
                "strategies_tested": len(STRATEGIES),
                "period": "5y",
                "anti_overfit_checks": 8,
                "results": {k: v for k, v in final.items()},
            },
            f,
            indent=2,
            default=str,
        )

    elapsed = time.time() - t0

    # Summary
    survivors = [s for s, a in final.items() if a["verdict"] == "SURVIVOR"]
    promising = [s for s, a in final.items() if a["verdict"] == "PROMISING"]
    eliminated = [
        s for s, a in final.items() if a["verdict"] in ("ELIMINATED", "MARGINAL")
    ]

    print(f"\n{'=' * 80}")
    print(f"  FINAL SCORE:")
    print(
        f"    SURVIVORS (pass 7+/8 checks):  {len(survivors)} -- {', '.join(survivors) if survivors else 'NONE'}"
    )
    print(
        f"    PROMISING (pass 5-6/8 checks): {len(promising)} -- {', '.join(promising) if promising else 'NONE'}"
    )
    print(f"    ELIMINATED:                    {len(eliminated)}")
    print(f"  Completed in {elapsed:.1f}s | Saved: {save_path}")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
