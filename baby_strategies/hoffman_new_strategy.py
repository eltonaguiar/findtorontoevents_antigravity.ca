''' 
Hoffman New Strategy - Simple signal generator using EMA slope, ATR volatility, and funding rate.
''' 

from dataclasses import dataclass
from typing import List
import math
import numpy as np
import pandas as pd

# Import Signal dataclass from existing module
from baby_strategies.hoffman_irb_ema_angle import Signal
# Funding rate fetcher
from alpha_engine.next_gen_strategies import get_binance_funding_rate

NAME = "hoffman_new_strategy"
DESCRIPTION = "Hoffman IRB variation using EMA slope, ATR volatility rank, and Binance funding rate for crypto"

def hoffman_new_strategy_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    """
    Generate signals based on:
    - EMA20 slope angle (degrees)
    - ATR percentile rank (0.0-1.0)
    - Binance funding rate (most recent)
    BUY when angle > 5°, low volatility (<0.3) and strong negative funding (< -0.01).
    SELL when angle < -5°, high volatility (>0.7) and strong positive funding (> 0.01).
    TP = 2*ATR, SL = 1*ATR. Confidence scales with absolute angle magnitude.
    """
    if len(data) < 150:
        return []

    # Compute required indicators locally to avoid circular imports
    EMA_PERIOD = 20
    ATR_PERIOD = 14
    EMA_LOOKBACK = 4
    # Prepare arrays using local logic
    o = data["open"].values.astype(float)
    h = data["high"].values.astype(float)
    l = data["low"].values.astype(float)
    c = data["close"].values.astype(float)
    v = data["volume"].values.astype(float)
    ema20 = _ema(c, EMA_PERIOD)
    angles = _ema_slope_degrees(ema20, lookback=EMA_LOOKBACK)
    atr = _atr(h, l, c, ATR_PERIOD)
    # Compute ATR percentile rank
    def _atr_percentile_rank_local(atr_arr, lookback=100):
        n = len(atr_arr)
        rank = np.full(n, np.nan)
        for i in range(lookback, n):
            window = atr_arr[max(0, i - lookback):i + 1]
            valid = window[~np.isnan(window)]
            if len(valid) < 10:
                continue
            rank[i] = np.sum(valid <= atr_arr[i]) / len(valid)
        return rank
    atr_pct_rank = _atr_percentile_rank_local(atr)
    # Compute RSI
    def _rsi_local(close, period=14):
        n = len(close)
        rsi = np.full(n, np.nan)
        if n < period + 1:
            return rsi
        delta = np.diff(close)
        gain = np.where(delta > 0, delta, 0.0)
        loss = np.where(delta < 0, -delta, 0.0)
        avg_gain = np.mean(gain[:period])
        avg_loss = np.mean(loss[:period])
        if avg_loss == 0:
            rsi[period] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[period] = 100.0 - 100.0 / (1.0 + rs)
        for i in range(period, n - 1):
            avg_gain = (avg_gain * (period - 1) + gain[i]) / period
            avg_loss = (avg_loss * (period - 1) + loss[i]) / period
            if avg_loss == 0:
                rsi[i + 1] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi[i + 1] = 100.0 - 100.0 / (1.0 + rs)
        return rsi
    rsi = _rsi_local(c)

    # Prepare common arrays (open, high, low, close, volume, ema20, angles, atr, irb flags)
    o, h, l, c, v, ema20, angles, atr, _, _ = _prepare_arrays(data)
    # Compute ATR percentile rank
    atr_pct_rank = _atr_percentile_rank(atr)

    i = len(c) - 1
    # Ensure required values are present
    if any(np.isnan(x) for x in [ema20[i], angles[i], atr[i], atr_pct_rank[i]]):
        return []

    price = c[i]
    atr_now = atr[i]
    angle_now = angles[i]
    rank = atr_pct_rank[i]

    # Fetch latest funding rate from Binance (returns rate, avg, list)
    rate, _, _ = get_binance_funding_rate(symbol)
    funding = rate if rate is not None else 0.0

    signals: List[Signal] = []

    # BUY condition: positive angle, RSI oversold, and (funding negative or not available)
    if angle_now > 0 and rsi[i] < 40 and (funding < -0.01 or funding == 0.0):
        # Confidence: base 0.5 + up to 0.4 based on angle magnitude (capped at 60)
        conf = 0.5 + min(angle_now / 60.0, 1.0) * 0.4
        tp = price + 2.0 * atr_now
        sl = price - 0.5 * atr_now
        signals.append(Signal(
            symbol=symbol,
            direction="BUY",
            confidence=round(conf, 2),
            entry_price=price,
            take_profit=round(tp, 6),
            stop_loss=round(sl, 6),
            reason=(f"NewStrategy BUY | angle={angle_now:.0f}° RSI={rsi[i]:.1f} ATRpct={rank:.0%} funding={funding:.4f}")
        ))

    # SELL condition: negative angle, RSI overbought, and (funding positive or not available)
    if angle_now < 0 and rsi[i] > 60 and (funding > 0.01 or funding == 0.0):
        conf = 0.5 + min(abs(angle_now) / 60.0, 1.0) * 0.4
        tp = price - 2.0 * atr_now
        sl = price + 0.5 * atr_now
        signals.append(Signal(
            symbol=symbol,
            direction="SELL",
            confidence=round(conf, 2),
            entry_price=price,
            take_profit=round(tp, 6),
            stop_loss=round(sl, 6),
            reason=(f"NewStrategy SELL | angle={angle_now:.0f}° RSI={rsi[i]:.1f} ATRpct={rank:.0%} funding={funding:.4f}")
        ))

    return signals
