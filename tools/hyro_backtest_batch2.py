#!/usr/bin/env python3
"""
hyro_backtest_batch2.py
Batch 2 — 30+ additional strategies from ALL_STRATEGIES.md catalog.
All use OHLCV data only (Binance 1h candles).

Usage (from repo root):
  python tools/hyro_backtest_batch2.py --symbols BTCUSDT ETHUSDT SOLUSDT --months 6 --save
  python tools/hyro_backtest_batch2.py --strategy cci_divergence --symbol BTCUSDT --months 6
"""

import json, sys, os, math, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from hyro_backtest import (
    fetch_candles, parse_candles, calc_sma, calc_std, calc_rsi, calc_atr,
    HyroSimulator, HYRO
)
from hyro_backtest_extended import (
    calc_ema,
    calc_stochastic,
    calc_macd,
    calc_donchian,
    calc_adx,
    calc_vwap_proxy,
)

WORKSPACE = _TOOLS.parent
DEFAULT_BATCH2_OUTPUT = (
    WORKSPACE / "audit_dashboard" / "data" / "hyro_batch2_results.json"
)


# ── New Indicators ─────────────────────────────────────────────────────────

def calc_cci(candles, period=20):
    """Commodity Channel Index."""
    n = len(candles)
    result = [None] * n
    for i in range(period - 1, n):
        window = candles[i - period + 1:i + 1]
        tp = [(c["high"] + c["low"] + c["close"]) / 3 for c in window]
        sma_tp = sum(tp) / period
        mad = sum(abs(t - sma_tp) for t in tp) / period
        if mad == 0:
            result[i] = 0
        else:
            result[i] = (tp[-1] - sma_tp) / (0.015 * mad)
    return result

def calc_dema(values, period):
    """Double Exponential Moving Average."""
    ema1 = [None] * len(values)
    ema2 = [None] * len(values)
    result = [None] * len(values)
    k = 2 / (period + 1)
    if len(values) < period * 2:
        return result
    # First EMA
    ema1[period - 1] = sum(values[:period]) / period
    for i in range(period, len(values)):
        ema1[i] = values[i] * k + ema1[i - 1] * (1 - k)
    # Second EMA
    first_valid = next(i for i, v in enumerate(ema1) if v is not None)
    start = first_valid + period - 1
    if start >= len(values):
        return result
    valid_ema1 = [v for v in ema1 if v is not None]
    if len(valid_ema1) < period:
        return result
    ema2[start] = sum(valid_ema1[:period]) / period
    for i in range(start + 1, len(values)):
        if ema1[i] is not None:
            ema2[i] = ema1[i] * k + ema2[i - 1] * (1 - k)
    for i in range(len(values)):
        if ema1[i] is not None and ema2[i] is not None:
            result[i] = 2 * ema1[i] - ema2[i]
    return result

def calc_fisher_transform(candles, period=9):
    """Ehlers Fisher Transform."""
    n = len(candles)
    result = [None] * n
    fish = [0] * n
    if n < period + 1:
        return result
    for i in range(period, n):
        window = candles[i - period + 1:i + 1]
        hh = max(c["high"] for c in window)
        ll = min(c["low"] for c in window)
        if hh == ll:
            value = 0
        else:
            value = 0.33 * 2 * ((candles[i]["close"] - ll) / (hh - ll) - 0.5) + 0.67 * fish[i - 1]
        value = max(min(value, 0.999), -0.999)
        fish[i] = value
        result[i] = 0.5 * math.log((1 + value) / (1 - value)) if abs(value) < 1 else 0
    return result

def calc_obv(candles):
    """On Balance Volume."""
    n = len(candles)
    obv = [0] * n
    for i in range(1, n):
        if candles[i]["close"] > candles[i - 1]["close"]:
            obv[i] = obv[i - 1] + candles[i]["volume"]
        elif candles[i]["close"] < candles[i - 1]["close"]:
            obv[i] = obv[i - 1] - candles[i]["volume"]
        else:
            obv[i] = obv[i - 1]
    return obv

def calc_cmf(candles, period=20):
    """Chaikin Money Flow."""
    n = len(candles)
    result = [None] * n
    for i in range(period - 1, n):
        window = candles[i - period + 1:i + 1]
        mf_vol = 0
        vol_sum = 0
        for c in window:
            rng = c["high"] - c["low"]
            if rng == 0:
                mfm = 0
            else:
                mfm = ((c["close"] - c["low"]) - (c["high"] - c["close"])) / rng
            mf_vol += mfm * c["volume"]
            vol_sum += c["volume"]
        result[i] = mf_vol / vol_sum if vol_sum > 0 else 0
    return result

def calc_mfi(candles, period=14):
    """Money Flow Index."""
    n = len(candles)
    result = [None] * n
    for i in range(period, n):
        pos_flow = 0
        neg_flow = 0
        for j in range(i - period + 1, i + 1):
            tp = (candles[j]["high"] + candles[j]["low"] + candles[j]["close"]) / 3
            prev_tp = (candles[j - 1]["high"] + candles[j - 1]["low"] + candles[j - 1]["close"]) / 3
            mf = tp * candles[j]["volume"]
            if tp > prev_tp:
                pos_flow += mf
            elif tp < prev_tp:
                neg_flow += mf
        if neg_flow == 0:
            result[i] = 100
        else:
            result[i] = 100 - 100 / (1 + pos_flow / neg_flow)
    return result

def calc_tsi(candles, long=25, short=13):
    """True Strength Index."""
    n = len(candles)
    closes = [c["close"] for c in candles]
    pc = [0] * n
    for i in range(1, n):
        pc[i] = closes[i] - closes[i - 1]
    
    # Double smoothed momentum
    k1 = 2 / (long + 1)
    k2 = 2 / (short + 1)
    
    ema1_m = [0] * n
    ema1_a = [0] * n
    for i in range(1, n):
        ema1_m[i] = pc[i] * k1 + ema1_m[i - 1] * (1 - k1)
        ema1_a[i] = abs(pc[i]) * k1 + ema1_a[i - 1] * (1 - k1)
    
    ema2_m = [0] * n
    ema2_a = [0] * n
    for i in range(1, n):
        ema2_m[i] = ema1_m[i] * k2 + ema2_m[i - 1] * (1 - k2)
        ema2_a[i] = ema1_a[i] * k2 + ema2_a[i - 1] * (1 - k2)
    
    result = [None] * n
    for i in range(long + short, n):
        if ema2_a[i] == 0:
            result[i] = 0
        else:
            result[i] = 100 * ema2_m[i] / ema2_a[i]
    return result

def calc_hma(values, period):
    """Hull Moving Average."""
    half = int(period / 2)
    sqrt_p = int(math.sqrt(period))
    wma_half = calc_wma_list(values, half)
    wma_full = calc_wma_list(values, period)
    
    n = len(values)
    diff = [None] * n
    for i in range(n):
        if wma_half[i] is not None and wma_full[i] is not None:
            diff[i] = 2 * wma_half[i] - wma_full[i]
    
    valid_diff = [(i, v) for i, v in enumerate(diff) if v is not None]
    if len(valid_diff) < sqrt_p:
        return [None] * n
    
    hma = [None] * n
    start_idx = valid_diff[sqrt_p - 1][0]
    # WMA of diff with period sqrt_p
    valid_vals = [v for _, v in valid_diff]
    for k in range(sqrt_p - 1, len(valid_vals)):
        chunk = valid_vals[k - sqrt_p + 1:k + 1]
        denom = sqrt_p * (sqrt_p + 1) / 2
        weighted = sum((j + 1) * v for j, v in enumerate(chunk))
        orig_idx = valid_diff[k][0]
        hma[orig_idx] = weighted / denom
    return hma

def calc_wma_list(values, period):
    """WMA from a list of values."""
    n = len(values)
    result = [None] * n
    denom = period * (period + 1) / 2
    for i in range(period - 1, n):
        chunk = values[i - period + 1:i + 1]
        result[i] = sum((j + 1) * v for j, v in enumerate(chunk)) / denom
    return result


# ── Batch 2 Strategies ─────────────────────────────────────────────────────

def strategy_fisher_transform(candles, params=None):
    """Ehlers Fisher Transform. Signal on zero-line cross + direction change."""
    p = params or {}
    period = p.get("period", 9)
    atr_p = p.get("atr_period", 14)
    
    fisher = calc_fisher_transform(candles, period)
    atr = calc_atr(candles, atr_p)
    signals = []
    for i in range(2, len(candles)):
        if fisher[i] is None or fisher[i-1] is None or fisher[i-2] is None or atr[i] is None:
            continue
        c = candles[i]
        # Bullish: fisher crosses above 0 and is rising
        if fisher[i] > 0 and fisher[i-1] <= 0:
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "fisher"})
        # Bearish: fisher crosses below 0
        if fisher[i] < 0 and fisher[i-1] >= 0:
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "fisher"})
    return signals

def strategy_dema_crossover(candles, params=None):
    """DEMA Crossover Momentum. Fast DEMA crosses slow DEMA."""
    p = params or {}
    fast_p = p.get("fast", 9)
    slow_p = p.get("slow", 21)
    
    closes = [c["close"] for c in candles]
    dema_fast = calc_dema(closes, fast_p)
    dema_slow = calc_dema(closes, slow_p)
    atr = calc_atr(candles, 14)
    rsi = calc_rsi(candles, 14)
    
    signals = []
    for i in range(2, len(candles)):
        if (dema_fast[i] is None or dema_slow[i] is None or 
            dema_fast[i-1] is None or dema_slow[i-1] is None or atr[i] is None):
            continue
        c = candles[i]
        if dema_fast[i] > dema_slow[i] and dema_fast[i-1] <= dema_slow[i-1] and (rsi[i] is None or rsi[i] > 50):
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "dema_crossover"})
        if dema_fast[i] < dema_slow[i] and dema_fast[i-1] >= dema_slow[i-1] and (rsi[i] is None or rsi[i] < 50):
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "dema_crossover"})
    return signals

def strategy_elder_ray(candles, params=None):
    """Elder Ray Bull/Bear Power. Bull power > 0 + EMA rising = LONG."""
    p = params or {}
    ema_p = p.get("ema_period", 13)
    
    closes = [c["close"] for c in candles]
    ema = calc_ema(closes, ema_p)
    atr = calc_atr(candles, 14)
    
    signals = []
    for i in range(2, len(candles)):
        if ema[i] is None or ema[i-1] is None or atr[i] is None:
            continue
        c = candles[i]
        bull = c["high"] - ema[i]
        bear = c["low"] - ema[i]
        
        if bull > 0 and bear > -atr[i] and ema[i] > ema[i-1]:
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "elder_ray"})
        if bear < 0 and bull < atr[i] and ema[i] < ema[i-1]:
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "elder_ray"})
    return signals

def strategy_cci_divergence(candles, params=None):
    """CCI Divergence. CCI < -100 with bullish divergence."""
    p = params or {}
    period = p.get("period", 20)
    
    cci = calc_cci(candles, period)
    atr = calc_atr(candles, 14)
    sma50 = calc_sma(candles, 50)
    
    signals = []
    for i in range(2, len(candles)):
        if cci[i] is None or cci[i-1] is None or atr[i] is None or sma50[i] is None:
            continue
        c = candles[i]
        # Bullish: CCI crosses above -100 from below
        if cci[i-1] < -100 and cci[i] >= -100 and c["close"] > sma50[i]:
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "cci_divergence"})
        # Bearish: CCI crosses below 100 from above
        if cci[i-1] > 100 and cci[i] <= 100 and c["close"] < sma50[i]:
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "cci_divergence"})
    return signals

def strategy_atr_volatility_breakout(candles, params=None):
    """ATR Volatility Breakout (Connors & Raschke). Entry on range expansion."""
    p = params or {}
    atr_p = p.get("atr_period", 14)
    mult = p.get("breakout_mult", 1.5)
    
    atr = calc_atr(candles, atr_p)
    signals = []
    for i in range(atr_p + 1, len(candles)):
        if atr[i] is None or atr[i-1] is None:
            continue
        c = candles[i]
        prev_range = candles[i-1]["high"] - candles[i-1]["low"]
        # Bullish: current range > 1.5x ATR AND close > prev high
        if c["high"] - c["low"] > mult * atr[i] and c["close"] > candles[i-1]["high"]:
            entry = c["close"]
            sl = entry - atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "atr_vol_breakout"})
        if c["high"] - c["low"] > mult * atr[i] and c["close"] < candles[i-1]["low"]:
            entry = c["close"]
            sl = entry + atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "atr_vol_breakout"})
    return signals

def strategy_obv_divergence(candles, params=None):
    """OBV Divergence Breakout. OBV making higher lows while price makes lower lows."""
    p = params or {}
    lookback = p.get("lookback", 20)
    
    obv = calc_obv(candles)
    atr = calc_atr(candles, 14)
    sma_obv = [None] * len(candles)
    for i in range(lookback - 1, len(candles)):
        sma_obv[i] = sum(obv[i - lookback + 1:i + 1]) / lookback
    
    signals = []
    for i in range(lookback + 2, len(candles)):
        if sma_obv[i] is None or sma_obv[i-1] is None or atr[i] is None:
            continue
        c = candles[i]
        # Bullish: OBV rising while price flat/down, OBV above its SMA
        obv_rising = obv[i] > obv[i-1] and obv[i-1] > obv[i-2]
        if obv_rising and sma_obv[i] > sma_obv[i-1] and obv[i] > sma_obv[i]:
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2.5 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.5, "strategy": "obv_divergence"})
        obv_falling = obv[i] < obv[i-1] and obv[i-1] < obv[i-2]
        if obv_falling and sma_obv[i] < sma_obv[i-1] and obv[i] < sma_obv[i]:
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2.5 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.5, "strategy": "obv_divergence"})
    return signals

def strategy_rsi_macd_confluence(candles, params=None):
    """RSI + MACD Confluence. Both must agree for entry."""
    rsi_vals = calc_rsi(candles, 14)
    macd_line, signal_line, hist = calc_macd(candles)
    atr = calc_atr(candles, 14)
    ema200 = calc_ema([c["close"] for c in candles], 200)
    
    signals = []
    for i in range(2, len(candles)):
        if (rsi_vals[i] is None or rsi_vals[i-1] is None or
            macd_line[i] is None or signal_line[i] is None or macd_line[i-1] is None or
            atr[i] is None or ema200[i] is None):
            continue
        c = candles[i]
        # LONG: RSI crosses above 30 + MACD crosses above signal + above EMA200
        if (rsi_vals[i-1] < 30 and rsi_vals[i] >= 30 and
            macd_line[i] > signal_line[i] and macd_line[i-1] <= signal_line[i-1] and
            c["close"] > ema200[i]):
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "rsi_macd_confluence"})
        # SHORT: RSI crosses below 70 + MACD crosses below signal + below EMA200
        if (rsi_vals[i-1] > 70 and rsi_vals[i] <= 70 and
            macd_line[i] < signal_line[i] and macd_line[i-1] >= signal_line[i-1] and
            c["close"] < ema200[i]):
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "rsi_macd_confluence"})
    return signals

def strategy_multi_ema_stack(candles, params=None):
    """Multi-Timeframe EMA Stack (EMA 9/21/55). All aligned = trend."""
    closes = [c["close"] for c in candles]
    e9 = calc_ema(closes, 9)
    e21 = calc_ema(closes, 21)
    e55 = calc_ema(closes, 55)
    atr = calc_atr(candles, 14)
    
    signals = []
    for i in range(2, len(candles)):
        if e9[i] is None or e21[i] is None or e55[i] is None or e9[i-1] is None or atr[i] is None:
            continue
        c = candles[i]
        # Bullish stack: 9 > 21 > 55 AND 9 just crossed above 21
        if e9[i] > e21[i] > e55[i] and e9[i-1] <= e21[i-1]:
            entry = c["close"]
            sl = entry - 2.5 * atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "multi_ema_stack"})
        # Bearish stack: 9 < 21 < 55 AND 9 just crossed below 21
        if e9[i] < e21[i] < e55[i] and e9[i-1] >= e21[i-1]:
            entry = c["close"]
            sl = entry + 2.5 * atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "multi_ema_stack"})
    return signals

def strategy_consecutive_down_rsi(candles, params=None):
    """Consecutive Down + RSI. 3 red candles with RSI oversold."""
    rsi_vals = calc_rsi(candles, 14)
    atr = calc_atr(candles, 14)
    sma50 = calc_sma(candles, 50)
    
    signals = []
    for i in range(3, len(candles)):
        if rsi_vals[i] is None or atr[i] is None or sma50[i] is None:
            continue
        c = candles[i]
        # 3 consecutive down candles
        down3 = (candles[i]["close"] < candles[i]["open"] and
                 candles[i-1]["close"] < candles[i-1]["open"] and
                 candles[i-2]["close"] < candles[i-2]["open"])
        if down3 and rsi_vals[i] < 30 and c["close"] > sma50[i]:
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "consecutive_down_rsi"})
        
        up3 = (candles[i]["close"] > candles[i]["open"] and
               candles[i-1]["close"] > candles[i-1]["open"] and
               candles[i-2]["close"] > candles[i-2]["open"])
        if up3 and rsi_vals[i] > 70 and c["close"] < sma50[i]:
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "consecutive_down_rsi"})
    return signals

def strategy_vwap_sd_reversion(candles, params=None):
    """VWAP Standard Deviation Mean Reversion (70-75% WR research)."""
    vwap = calc_vwap_proxy(candles)
    atr = calc_atr(candles, 14)
    
    # Calc VWAP std dev
    n = len(candles)
    vwap_std = [None] * n
    for i in range(20, n):
        if vwap[i] is None: continue
        window = candles[i-20:i]
        vals = []
        for c in window:
            tp = (c["high"] + c["low"] + c["close"]) / 3
            vals.append((tp - vwap[i]) ** 2)
        vwap_std[i] = math.sqrt(sum(vals) / len(vals)) if vals else None
    
    rsi_vals = calc_rsi(candles, 14)
    signals = []
    for i in range(21, n):
        if vwap[i] is None or vwap_std[i] is None or atr[i] is None or rsi_vals[i] is None:
            continue
        c = candles[i]
        # Price 2 std devs below VWAP
        if c["close"] < vwap[i] - 2 * vwap_std[i] and rsi_vals[i] < 35:
            entry = c["close"]
            sl = entry - 1.5 * atr[i]
            tp = vwap[i]
            if tp > entry:
                rr = (tp - entry) / (entry - sl) if entry != sl else 0
                if rr >= 1.0:
                    signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                                   "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                                   "rr": round(rr, 2), "strategy": "vwap_sd_reversion"})
        # Price 2 std devs above VWAP
        if c["close"] > vwap[i] + 2 * vwap_std[i] and rsi_vals[i] > 65:
            entry = c["close"]
            sl = entry + 1.5 * atr[i]
            tp = vwap[i]
            if tp < entry:
                rr = (entry - tp) / (sl - entry) if sl != entry else 0
                if rr >= 1.0:
                    signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                                   "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                                   "rr": round(rr, 2), "strategy": "vwap_sd_reversion"})
    return signals

def strategy_cmf_cross(candles, params=None):
    """Chaikin Money Flow zero-line cross."""
    cmf = calc_cmf(candles, 20)
    atr = calc_atr(candles, 14)
    ema50 = calc_ema([c["close"] for c in candles], 50)
    
    signals = []
    for i in range(2, len(candles)):
        if cmf[i] is None or cmf[i-1] is None or atr[i] is None or ema50[i] is None:
            continue
        c = candles[i]
        if cmf[i] > 0 and cmf[i-1] <= 0 and c["close"] > ema50[i]:
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "cmf_cross"})
        if cmf[i] < 0 and cmf[i-1] >= 0 and c["close"] < ema50[i]:
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "cmf_cross"})
    return signals

def strategy_mfi_reversion(candles, params=None):
    """MFI Smart Money Detection. MFI extreme with trend filter."""
    mfi = calc_mfi(candles, 14)
    atr = calc_atr(candles, 14)
    ema200 = calc_ema([c["close"] for c in candles], 200)
    
    signals = []
    for i in range(2, len(candles)):
        if mfi[i] is None or mfi[i-1] is None or atr[i] is None or ema200[i] is None:
            continue
        c = candles[i]
        if mfi[i-1] < 20 and mfi[i] >= 20 and c["close"] > ema200[i]:
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "mfi_reversion"})
        if mfi[i-1] > 80 and mfi[i] <= 80 and c["close"] < ema200[i]:
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "mfi_reversion"})
    return signals

def strategy_tsi_signal(candles, params=None):
    """True Strength Index. TSI cross above/below zero."""
    tsi = calc_tsi(candles)
    atr = calc_atr(candles, 14)
    
    signals = []
    for i in range(2, len(candles)):
        if tsi[i] is None or tsi[i-1] is None or atr[i] is None:
            continue
        c = candles[i]
        if tsi[i] > 0 and tsi[i-1] <= 0:
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2.5 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.5, "strategy": "tsi"})
        if tsi[i] < 0 and tsi[i-1] >= 0:
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2.5 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.5, "strategy": "tsi"})
    return signals

def strategy_hma_trend(candles, params=None):
    """Hull Moving Average Trend. Price crosses HMA."""
    p = params or {}
    period = p.get("period", 55)
    
    closes = [c["close"] for c in candles]
    hma = calc_hma(closes, period)
    atr = calc_atr(candles, 14)
    rsi = calc_rsi(candles, 14)
    
    signals = []
    for i in range(2, len(candles)):
        if hma[i] is None or hma[i-1] is None or atr[i] is None:
            continue
        c = candles[i]
        if c["close"] > hma[i] and candles[i - 1]["close"] <= hma[i - 1] and (rsi[i] is None or rsi[i] > 50):
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "hma_trend"})
        if c["close"] < hma[i] and candles[i - 1]["close"] >= hma[i - 1] and (rsi[i] is None or rsi[i] < 50):
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "hma_trend"})
    return signals

def strategy_bb_squeeze(candles, params=None):
    """Bollinger Band Squeeze Breakout. BB inside Keltner → breakout."""
    bb_sma = sma_list([c["close"] for c in candles], 20)
    bb_std_vals = std_list([c["close"] for c in candles], 20)
    atr_vals = calc_atr(candles, 14)
    ema20 = calc_ema([c["close"] for c in candles], 20)
    
    signals = []
    for i in range(21, len(candles)):
        if bb_sma[i] is None or bb_std_vals[i] is None or atr_vals[i] is None or ema20[i] is None:
            continue
        bb_width = 2 * bb_std_vals[i]
        keltner_width = 2 * atr_vals[i]
        c = candles[i]
        # Squeeze: BB inside Keltner
        if bb_width < keltner_width:
            # Breakout direction
            if c["close"] > bb_sma[i] + bb_std_vals[i] and c["close"] > candles[i-1]["high"]:
                entry = c["close"]
                sl = entry - 2 * atr_vals[i]
                risk = entry - sl
                tp = entry + 2 * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                               "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                               "rr": 2.0, "strategy": "bb_squeeze"})
            if c["close"] < bb_sma[i] - bb_std_vals[i] and c["close"] < candles[i-1]["low"]:
                entry = c["close"]
                sl = entry + 2 * atr_vals[i]
                risk = sl - entry
                tp = entry - 2 * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                               "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                               "rr": 2.0, "strategy": "bb_squeeze"})
    return signals

def strategy_three_white_soldiers(candles, params=None):
    """Three White Soldiers / Three Black Crows + RSI."""
    rsi_vals = calc_rsi(candles, 14)
    atr = calc_atr(candles, 14)
    sma50 = calc_sma(candles, 50)
    
    signals = []
    for i in range(3, len(candles)):
        if rsi_vals[i] is None or atr[i] is None or sma50[i] is None:
            continue
        c = candles[i]
        # Three white soldiers
        tws = (candles[i]["close"] > candles[i]["open"] and
               candles[i-1]["close"] > candles[i-1]["open"] and
               candles[i-2]["close"] > candles[i-2]["open"] and
               candles[i]["close"] > candles[i-1]["close"] > candles[i-2]["close"])
        if tws and rsi_vals[i] > 50 and rsi_vals[i] < 70:
            entry = c["close"]
            sl = candles[i-2]["low"]  # SL below first soldier
            risk = entry - sl
            if risk > 0:
                tp = entry + 2 * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                               "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                               "rr": 2.0, "strategy": "three_soldiers"})
        
        # Three black crows
        tbc = (candles[i]["close"] < candles[i]["open"] and
               candles[i-1]["close"] < candles[i-1]["open"] and
               candles[i-2]["close"] < candles[i-2]["open"] and
               candles[i]["close"] < candles[i-1]["close"] < candles[i-2]["close"])
        if tbc and rsi_vals[i] < 50 and rsi_vals[i] > 30:
            entry = c["close"]
            sl = candles[i-2]["high"]
            risk = sl - entry
            if risk > 0:
                tp = entry - 2 * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                               "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                               "rr": 2.0, "strategy": "three_soldiers"})
    return signals

def strategy_volume_climax(candles, params=None):
    """Volume Climax Reversal. Extreme volume + reversal candle."""
    atr = calc_atr(candles, 14)
    sma20_vol = [None] * len(candles)
    for i in range(19, len(candles)):
        sma20_vol[i] = sum(c["volume"] for c in candles[i-19:i+1]) / 20
    
    signals = []
    for i in range(20, len(candles)):
        if atr[i] is None or sma20_vol[i] is None or sma20_vol[i] == 0:
            continue
        c = candles[i]
        vol_ratio = c["volume"] / sma20_vol[i]
        body = abs(c["close"] - c["open"])
        full_range = c["high"] - c["low"]
        
        if vol_ratio > 3 and full_range > 0:
            lower_wick = min(c["close"], c["open"]) - c["low"]
            upper_wick = c["high"] - max(c["close"], c["open"])
            
            # Bullish climax: high vol, hammer, after decline
            if lower_wick > 2 * body and c["close"] > candles[i-1]["close"]:
                entry = c["close"]
                sl = entry - 1.5 * atr[i]
                risk = entry - sl
                tp = entry + 2 * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                               "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                               "rr": 2.0, "strategy": "volume_climax"})
            
            # Bearish climax: high vol, shooting star, after rally
            if upper_wick > 2 * body and c["close"] < candles[i-1]["close"]:
                entry = c["close"]
                sl = entry + 1.5 * atr[i]
                risk = sl - entry
                tp = entry - 2 * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                               "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                               "rr": 2.0, "strategy": "volume_climax"})
    return signals

def strategy_adx_vol_breakout(candles, params=None):
    """ADX Volatility Breakout. ADX rising above 25 + DI cross."""
    adx_vals, plus_di, minus_di = calc_adx(candles, 14)
    atr = calc_atr(candles, 14)
    
    signals = []
    for i in range(2, len(candles)):
        if adx_vals[i] is None or adx_vals[i-1] is None or plus_di[i] is None or minus_di[i] is None or atr[i] is None:
            continue
        c = candles[i]
        # ADX just crossed above 25 (trend starting)
        if adx_vals[i] > 25 and adx_vals[i-1] <= 25:
            if plus_di[i] > minus_di[i]:
                entry = c["close"]
                sl = entry - 2 * atr[i]
                risk = entry - sl
                tp = entry + 2.5 * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                               "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                               "rr": 2.5, "strategy": "adx_vol_breakout"})
            elif minus_di[i] > plus_di[i]:
                entry = c["close"]
                sl = entry + 2 * atr[i]
                risk = sl - entry
                tp = entry - 2.5 * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                               "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                               "rr": 2.5, "strategy": "adx_vol_breakout"})
    return signals

def strategy_rsi_divergence(candles, params=None):
    """RSI Hidden Divergence. Price higher low + RSI lower low = bullish."""
    rsi_vals = calc_rsi(candles, 14)
    atr = calc_atr(candles, 14)
    lookback = 10
    
    signals = []
    for i in range(lookback + 5, len(candles)):
        if rsi_vals[i] is None or atr[i] is None:
            continue
        c = candles[i]
        
        # Find recent swing low in price and RSI
        min_price = min(c["low"] for c in candles[i-lookback:i])
        min_rsi = min(rsi_vals[j] for j in range(i-lookback, i) if rsi_vals[j] is not None)
        
        # Bullish divergence: current price > prev swing low but RSI < prev swing RSI
        if (c["low"] > min_price and rsi_vals[i] < min_rsi and rsi_vals[i] < 40):
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "rsi_divergence"})
        
        max_price = max(c["high"] for c in candles[i-lookback:i])
        max_rsi = max(rsi_vals[j] for j in range(i-lookback, i) if rsi_vals[j] is not None)
        
        if (c["high"] < max_price and rsi_vals[i] > max_rsi and rsi_vals[i] > 60):
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "rsi_divergence"})
    return signals

def strategy_keltner_squeeze_breakout(candles, params=None):
    """Keltner Squeeze Breakout (Proven Scanner)."""
    ema20 = calc_ema([c["close"] for c in candles], 20)
    atr_vals = calc_atr(candles, 14)
    
    signals = []
    for i in range(21, len(candles)):
        if ema20[i] is None or atr_vals[i] is None:
            continue
        c = candles[i]
        upper = ema20[i] + 2 * atr_vals[i]
        lower = ema20[i] - 2 * atr_vals[i]
        
        # Check if was in squeeze (range < 1.5 ATR) then breaks out
        prev_range = candles[i-1]["high"] - candles[i-1]["low"]
        if prev_range < 1.5 * atr_vals[i-1] if atr_vals[i-1] else False:
            if c["close"] > upper:
                entry = c["close"]
                sl = ema20[i]
                risk = entry - sl
                tp = entry + 2 * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                               "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                               "rr": 2.0, "strategy": "keltner_squeeze"})
            if c["close"] < lower:
                entry = c["close"]
                sl = ema20[i]
                risk = sl - entry
                tp = entry - 2 * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                               "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                               "rr": 2.0, "strategy": "keltner_squeeze"})
    return signals

def strategy_justin_ema9(candles, params=None):
    """Justin Bravo EMA-9 Basic. Price touches EMA(9) in trend."""
    closes = [c["close"] for c in candles]
    e9 = calc_ema(closes, 9)
    e21 = calc_ema(closes, 21)
    rsi_vals = calc_rsi(candles, 14)
    atr = calc_atr(candles, 14)
    
    signals = []
    for i in range(2, len(candles)):
        if e9[i] is None or e21[i] is None or rsi_vals[i] is None or atr[i] is None:
            continue
        c = candles[i]
        # Uptrend pullback: EMA9 > EMA21, price touches EMA9 from above
        if e9[i] > e21[i] and c["low"] <= e9[i] * 1.002 and c["low"] >= e9[i] * 0.998 and c["close"] > e9[i]:
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "justin_ema9"})
        if e9[i] < e21[i] and c["high"] >= e9[i] * 0.998 and c["high"] <= e9[i] * 1.002 and c["close"] < e9[i]:
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "justin_ema9"})
    return signals

def strategy_wavetrend(candles, params=None):
    """WaveTrend Oscillator. WT1 crosses WT2."""
    n = len(candles)
    closes = [c["close"] for c in candles]
    
    # EMA of close
    esa = calc_ema(closes, 10)
    # D = EMA of |close - ESA|
    abs_diff = [abs(closes[i] - esa[i]) if esa[i] is not None else 0 for i in range(n)]
    d = calc_wma_list(abs_diff, 10)
    
    ci = [None] * n
    for i in range(n):
        if d[i] and d[i] > 0 and esa[i] is not None:
            ci[i] = (closes[i] - esa[i]) / (0.015 * d[i])
    
    wt1 = calc_wma_list([v if v is not None else 0 for v in ci], 21)
    wt2 = calc_wma_list([v if v is not None else 0 for v in wt1], 4)
    
    atr = calc_atr(candles, 14)
    signals = []
    for i in range(2, len(candles)):
        if wt1[i] is None or wt2[i] is None or wt1[i-1] is None or wt2[i-1] is None or atr[i] is None:
            continue
        c = candles[i]
        if wt1[i] > wt2[i] and wt1[i-1] <= wt2[i-1] and wt1[i] < -30:
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "wavetrend"})
        if wt1[i] < wt2[i] and wt1[i-1] >= wt2[i-1] and wt1[i] > 30:
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.0, "strategy": "wavetrend"})
    return signals

def strategy_ttm_squeeze(candles, params=None):
    """TTM Squeeze Momentum. BB inside Keltner + momentum histogram."""
    closes = [c["close"] for c in candles]
    bb_sma = sma_list(closes, 20)
    bb_std_vals = std_list(closes, 20)
    ema20 = calc_ema(closes, 20)
    atr_vals = calc_atr(candles, 14)
    
    # Momentum = close - SMA(close, 20)
    mom = [None] * len(candles)
    for i in range(19, len(candles)):
        mom[i] = closes[i] - bb_sma[i]
    
    signals = []
    for i in range(21, len(candles)):
        if bb_sma[i] is None or bb_std_vals[i] is None or atr_vals[i] is None or mom[i] is None or mom[i-1] is None:
            continue
        
        bb_width = 2 * bb_std_vals[i]
        keltner_width = 2 * atr_vals[i]
        c = candles[i]
        
        # Squeeze on = BB inside Keltner
        in_squeeze = bb_width < keltner_width
        
        # Squeeze fires (was in squeeze, now out) + momentum direction
        if not in_squeeze and i > 0:
            prev_bb = 2 * bb_std_vals[i-1] if bb_std_vals[i-1] else 0
            prev_kelt = 2 * atr_vals[i-1] if atr_vals[i-1] else 0
            was_squeeze = prev_bb < prev_kelt
            
            if was_squeeze and mom[i] > 0 and mom[i] > mom[i-1]:
                entry = c["close"]
                sl = entry - 2 * atr_vals[i]
                risk = entry - sl
                tp = entry + 2 * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                               "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                               "rr": 2.0, "strategy": "ttm_squeeze"})
            if was_squeeze and mom[i] < 0 and mom[i] < mom[i-1]:
                entry = c["close"]
                sl = entry + 2 * atr_vals[i]
                risk = sl - entry
                tp = entry - 2 * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                               "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                               "rr": 2.0, "strategy": "ttm_squeeze"})
    return signals

def strategy_multi_sigma_reversal(candles, params=None):
    """Multi-Sigma Extreme Reversion. Price > 3 std devs from mean."""
    closes = [c["close"] for c in candles]
    sma20 = sma_list(closes, 20)
    std20 = std_list(closes, 20)
    atr = calc_atr(candles, 14)
    rsi_vals = calc_rsi(candles, 14)
    
    signals = []
    for i in range(20, len(candles)):
        if sma20[i] is None or std20[i] is None or std20[i] == 0 or atr[i] is None or rsi_vals[i] is None:
            continue
        c = candles[i]
        z = (c["close"] - sma20[i]) / std20[i]
        
        if z < -2.5 and rsi_vals[i] < 25:
            entry = c["close"]
            sl = entry - 1.5 * atr[i]
            tp = sma20[i]
            if tp > entry:
                rr = (tp - entry) / (entry - sl) if entry != sl else 0
                if rr >= 1.0:
                    signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                                   "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                                   "rr": round(rr, 2), "strategy": "multi_sigma"})
        if z > 2.5 and rsi_vals[i] > 75:
            entry = c["close"]
            sl = entry + 1.5 * atr[i]
            tp = sma20[i]
            if tp < entry:
                rr = (entry - tp) / (sl - entry) if sl != entry else 0
                if rr >= 1.0:
                    signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                                   "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                                   "rr": round(rr, 2), "strategy": "multi_sigma"})
    return signals

def strategy_vwap_bounce(candles, params=None):
    """VWAP Bounce (Community). Price bounces off VWAP with volume."""
    vwap = calc_vwap_proxy(candles)
    atr = calc_atr(candles, 14)
    
    signals = []
    lookback = 20
    for i in range(lookback + 1, len(candles)):
        if vwap[i] is None or vwap[i-1] is None or atr[i] is None:
            continue
        c = candles[i]
        avg_vol = sum(cc["volume"] for cc in candles[i-lookback:i]) / lookback
        
        # Price touches VWAP from above and bounces (LONG)
        if c["low"] <= vwap[i] * 1.005 and c["close"] > vwap[i] and c["close"] > c["open"] and c["volume"] > avg_vol:
            entry = c["close"]
            sl = vwap[i] * 0.99
            risk = entry - sl
            if risk > 0:
                tp = entry + 2 * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                               "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                               "rr": 2.0, "strategy": "vwap_bounce"})
        
        # Price touches VWAP from below and rejects (SHORT)
        if c["high"] >= vwap[i] * 0.995 and c["close"] < vwap[i] and c["close"] < c["open"] and c["volume"] > avg_vol:
            entry = c["close"]
            sl = vwap[i] * 1.01
            risk = sl - entry
            if risk > 0:
                tp = entry - 2 * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                               "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                               "rr": 2.0, "strategy": "vwap_bounce"})
    return signals

def strategy_failed_breakout_reversal(candles, params=None):
    """Failed Breakout Reversal. Breakout fails → reverse."""
    atr = calc_atr(candles, 14)
    lookback = 20
    
    signals = []
    for i in range(lookback + 2, len(candles)):
        if atr[i] is None:
            continue
        c = candles[i]
        prev_high = max(cc["high"] for cc in candles[i-lookback:i])
        prev_low = min(cc["low"] for cc in candles[i-lookback:i])
        
        # Failed upside breakout: prev candle broke above, current closes back below
        if candles[i-1]["high"] > prev_high and candles[i-1]["close"] > prev_high:
            if c["close"] < prev_high and c["close"] < c["open"]:
                entry = c["close"]
                sl = candles[i-1]["high"] + atr[i]
                risk = sl - entry
                tp = entry - 2 * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                               "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                               "rr": 2.0, "strategy": "failed_breakout"})
        
        # Failed downside breakout
        if candles[i-1]["low"] < prev_low and candles[i-1]["close"] < prev_low:
            if c["close"] > prev_low and c["close"] > c["open"]:
                entry = c["close"]
                sl = candles[i-1]["low"] - atr[i]
                risk = entry - sl
                tp = entry + 2 * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                               "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                               "rr": 2.0, "strategy": "failed_breakout"})
    return signals

def strategy_vol_scaled_momentum(candles, params=None):
    """Volatility-Scaled Momentum. Momentum / ATR for risk-adjusted entry."""
    closes = [c["close"] for c in candles]
    ema21 = calc_ema(closes, 21)
    atr = calc_atr(candles, 14)
    
    signals = []
    for i in range(22, len(candles)):
        if ema21[i] is None or ema21[i-1] is None or atr[i] is None or atr[i] == 0:
            continue
        c = candles[i]
        momentum = (c["close"] - candles[i-5]["close"]) / candles[i-5]["close"] * 100
        vol_scaled = momentum / (atr[i] / c["close"] * 100)
        
        if vol_scaled > 2 and ema21[i] > ema21[i-1]:
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2.5 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.5, "strategy": "vol_scaled_mom"})
        if vol_scaled < -2 and ema21[i] < ema21[i-1]:
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2.5 * risk
            signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                           "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                           "rr": 2.5, "strategy": "vol_scaled_mom"})
    return signals

def strategy_bb_rsi_reversion(candles, params=None):
    """BB + RSI Mean Reversion (NextGen #12). BB touch + RSI confirmation."""
    closes = [c["close"] for c in candles]
    sma20 = sma_list(closes, 20)
    std20 = std_list(closes, 20)
    rsi_vals = calc_rsi(candles, 14)
    atr = calc_atr(candles, 14)
    
    signals = []
    for i in range(20, len(candles)):
        if sma20[i] is None or std20[i] is None or rsi_vals[i] is None or atr[i] is None:
            continue
        c = candles[i]
        upper = sma20[i] + 2 * std20[i]
        lower = sma20[i] - 2 * std20[i]
        
        if c["low"] <= lower and rsi_vals[i] < 30 and c["close"] > lower:
            entry = c["close"]
            sl = lower - atr[i]
            tp = sma20[i]
            if tp > entry:
                rr = (tp - entry) / (entry - sl) if entry != sl else 0
                if rr >= 1.0:
                    signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                                   "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                                   "rr": round(rr, 2), "strategy": "bb_rsi_reversion"})
        if c["high"] >= upper and rsi_vals[i] > 70 and c["close"] < upper:
            entry = c["close"]
            sl = upper + atr[i]
            tp = sma20[i]
            if tp < entry:
                rr = (entry - tp) / (sl - entry) if sl != entry else 0
                if rr >= 1.0:
                    signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                                   "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                                   "rr": round(rr, 2), "strategy": "bb_rsi_reversion"})
    return signals


# ── Helpers ────────────────────────────────────────────────────────────────

def sma_list(values, period):
    result = [None] * len(values)
    for i in range(period - 1, len(values)):
        result[i] = sum(values[i - period + 1:i + 1]) / period
    return result

def std_list(values, period):
    result = [None] * len(values)
    for i in range(period - 1, len(values)):
        chunk = values[i - period + 1:i + 1]
        mean = sum(chunk) / period
        result[i] = math.sqrt(sum((x - mean) ** 2 for x in chunk) / period)
    return result


# ── Registry ───────────────────────────────────────────────────────────────

BATCH2_STRATEGIES = {
    "fisher": ("Ehlers Fisher Transform", strategy_fisher_transform),
    "dema_crossover": ("DEMA Crossover", strategy_dema_crossover),
    "elder_ray": ("Elder Ray Bull/Bear", strategy_elder_ray),
    "cci_divergence": ("CCI Divergence", strategy_cci_divergence),
    "atr_vol_breakout": ("ATR Volatility Breakout", strategy_atr_volatility_breakout),
    "obv_divergence": ("OBV Divergence Breakout", strategy_obv_divergence),
    "rsi_macd_confluence": ("RSI + MACD Confluence [65% WR]", strategy_rsi_macd_confluence),
    "multi_ema_stack": ("Multi-EMA Stack (9/21/55) [65-72% WR]", strategy_multi_ema_stack),
    "consecutive_down_rsi": ("Consecutive Down + RSI", strategy_consecutive_down_rsi),
    "vwap_sd_reversion": ("VWAP SD Mean Reversion [70-75% WR]", strategy_vwap_sd_reversion),
    "cmf_cross": ("Chaikin Money Flow Cross", strategy_cmf_cross),
    "mfi_reversion": ("MFI Smart Money Reversion", strategy_mfi_reversion),
    "tsi": ("True Strength Index", strategy_tsi_signal),
    "hma_trend": ("Hull MA Trend", strategy_hma_trend),
    "bb_squeeze": ("BB Squeeze Breakout", strategy_bb_squeeze),
    "three_soldiers": ("Three White Soldiers / Black Crows", strategy_three_white_soldiers),
    "volume_climax": ("Volume Climax Reversal [60-70% WR]", strategy_volume_climax),
    "adx_vol_breakout": ("ADX Volatility Breakout", strategy_adx_vol_breakout),
    "rsi_divergence": ("RSI Hidden Divergence", strategy_rsi_divergence),
    "keltner_squeeze": ("Keltner Squeeze Breakout (Proven)", strategy_keltner_squeeze_breakout),
    "justin_ema9": ("Justin Bravo EMA-9", strategy_justin_ema9),
    "wavetrend": ("WaveTrend Oscillator", strategy_wavetrend),
    "ttm_squeeze": ("TTM Squeeze Momentum", strategy_ttm_squeeze),
    "multi_sigma": ("Multi-Sigma Extreme Reversion", strategy_multi_sigma_reversal),
    "vwap_bounce": ("VWAP Bounce (Community)", strategy_vwap_bounce),
    "failed_breakout": ("Failed Breakout Reversal", strategy_failed_breakout_reversal),
    "vol_scaled_mom": ("Volatility-Scaled Momentum", strategy_vol_scaled_momentum),
    "bb_rsi_reversion": ("BB + RSI Mean Reversion", strategy_bb_rsi_reversion),
}


def run_single(symbol, strategy_key, months=6, risk_pct=0.75):
    name, fn = BATCH2_STRATEGIES[strategy_key]
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=months * 30)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(now.timestamp() * 1000)
    
    raw = fetch_candles(symbol, "1h", start_ms, end_ms)
    candles = parse_candles(raw)
    signals = fn(candles)
    if not signals:
        return None
    
    signals.sort(key=lambda s: s["index"])
    sim = HyroSimulator(account_size=5000, risk_pct=risk_pct)
    last_exit_idx = -1
    
    for signal in signals:
        if signal["index"] <= last_exit_idx:
            continue
        if sim.failed:
            break
        if sim.daily_profit >= HYRO["consistency_max_daily_phase1"]:
            continue
        result = sim.simulate_trade(signal, candles)
        if result:
            last_exit_idx = signal["index"] + result.get("bars_held", 0)
    
    if sim.failed:
        sim.passed = False
    
    wins = [t for t in sim.trades if t["pnl"] > 0]
    losses = [t for t in sim.trades if t["pnl"] <= 0]
    total = len(sim.trades)
    if total == 0:
        return None
    
    total_profit = sum(t["pnl"] for t in wins)
    total_loss = sum(t["pnl"] for t in losses)
    
    return {
        "symbol": symbol, "strategy": strategy_key, "strategy_name": name,
        "months": months, "risk_pct": risk_pct,
        "passed": sim.passed, "failed": sim.failed, "fail_reason": sim.fail_reason,
        "total_trades": total, "wins": len(wins), "losses": len(losses),
        "win_rate": round(len(wins) / total * 100, 1),
        "profit_factor": round(abs(total_profit / total_loss), 2) if total_loss != 0 else 999,
        "total_pnl": round(sim.total_pnl, 2),
        "pnl_pct": round(sim.total_pnl / sim.account_size * 100, 1),
        "final_equity": round(sim.equity, 2),
        "peak_equity": round(sim.high_water_equity, 2),
        "max_dd": round(sim.max_drawdown_from_peak, 2),
        "trading_days": len(sim.trading_days),
        "avg_win": round(total_profit / len(wins), 2) if wins else 0,
        "avg_loss": round(total_loss / len(losses), 2) if losses else 0,
        "signals_generated": len(signals),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Batch 2 HyroTrader backtester")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    parser.add_argument(
        "--symbol",
        default=None,
        help="Single symbol (overrides --symbols when set)",
    )
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--risk", type=float, default=0.75)
    parser.add_argument("--strategy", default=None)
    parser.add_argument("--save", action="store_true")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_BATCH2_OUTPUT),
        help="JSON path when using --save",
    )
    args = parser.parse_args()

    symbols = [args.symbol] if args.symbol else args.symbols

    strats = [args.strategy] if args.strategy else list(BATCH2_STRATEGIES.keys())
    all_results = []

    for symbol in symbols:
        for strat_key in strats:
            name = BATCH2_STRATEGIES[strat_key][0]
            print(f"  {symbol} × {name} ...", end=" ", flush=True)
            try:
                result = run_single(symbol, strat_key, args.months, args.risk)
                if result:
                    all_results.append(result)
                    status = "PASS" if result["passed"] else "FAIL" if result["failed"] else "INCOMPLETE"
                    print(f"{status} | {result['total_trades']}t | WR {result['win_rate']}% | PF {result['profit_factor']} | ${result['total_pnl']} ({result['pnl_pct']}%) | DD ${result['max_dd']}")
                else:
                    print("NO SIGNALS")
            except Exception as e:
                print(f"ERROR: {e}")
            time.sleep(0.3)
    
    # Summary
    all_results.sort(key=lambda r: r["total_pnl"], reverse=True)
    passed = [r for r in all_results if r["passed"]]
    
    print(f"\n{'='*120}")
    print(f"  BATCH 2 RESULTS — {len(all_results)} runs, {len(passed)} PASSED")
    print(f"{'='*120}")
    print(f"  {'Symbol':<10} {'Strategy':<35} {'Result':<12} {'Trades':<8} {'WR%':<8} {'PF':<8} {'PnL%':<8} {'MaxDD$':<10}")
    print(f"  {'-'*10} {'-'*35} {'-'*12} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")
    for r in all_results:
        status = "PASS" if r["passed"] else "FAIL" if r["failed"] else "INCOMPLETE"
        print(f"  {r['symbol']:<10} {r['strategy_name']:<35} {status:<12} {r['total_trades']:<8} {r['win_rate']:<8} {r['profit_factor']:<8} {r['pnl_pct']:<8} {r['max_dd']:<10}")
    
    if passed:
        print(f"\n  PASSING:")
        for r in passed:
            print(f"    {r['symbol']} × {r['strategy_name']}: +{r['pnl_pct']}%, PF {r['profit_factor']}, WR {r['win_rate']}%")
    
    if args.save and all_results:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "months": args.months,
            "risk_pct": args.risk,
            "symbols": symbols,
            "challenge_params": {k: v for k, v in HYRO.items()},
            "results": all_results,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"\n  Saved to {out_path}")
    elif args.save and not all_results:
        print("\n  --save skipped (no results)")


if __name__ == "__main__":
    main()
