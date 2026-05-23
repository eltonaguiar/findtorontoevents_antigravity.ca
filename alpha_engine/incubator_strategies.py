"""
ALPHA_ENGINE -- Incubator Strategies
=====================================
Five battle-tested strategies converted from top GitHub Pine Script repos
into pure Python (stdlib only).

Strategies:
  1. triple_supertrend     -- 3x Supertrend confirmation (keithorange, 75% WR)
  2. adx_momentum          -- ADX trend + DI momentum (keithorange, 60-85% WR)
  3. ttm_squeeze_carter    -- John Carter TTM Squeeze (hackingthemarkets, 70-80% WR)
  4. dual_thrust_orb       -- Opening Range Breakout (je-suis-tm/quant-trading, 65-72% WR)
  5. ict_fair_value_gap    -- ICT FVG displacement (ArunKBhaskar/PineScript, 65-75% WR)

Data sources:
  - Binance 5-mirror failover: data-api.binance.vision, api, api1, api2, api3

stdlib only (urllib.request, json, math, statistics, ssl, datetime).

References:
  - keithorange/HUGE_FreqTrade_Strategy_Collection (GitHub)
  - hackingthemarkets/ttm-squeeze (GitHub)
  - je-suis-tm/quant-trading (GitHub, 9.5k stars)
  - ArunKBhaskar/PineScript (GitHub, 354 stars)
"""

from __future__ import annotations

import json
import math
import os
import ssl
import statistics
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

try:
    _SSL_CTX = ssl.create_default_context()
except Exception:
    _SSL_CTX = ssl._create_unverified_context()

_REQUEST_TIMEOUT = 15

_BINANCE_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

_DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "MATICUSDT", "LTCUSDT", "NEARUSDT", "UNIUSDT", "ATOMUSDT",
    "APTUSDT", "SUIUSDT", "ARBUSDT", "OPUSDT", "INJUSDT",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_json(url: str, timeout: int = _REQUEST_TIMEOUT) -> Optional[Any]:
    """Fetch JSON from URL with error handling."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _fetch_klines(symbol: str, interval: str = "4h",
                  limit: int = 100) -> Optional[List[list]]:
    """Fetch klines from Binance with 5-mirror failover."""
    for mirror in _BINANCE_MIRRORS:
        url = (f"{mirror}/api/v3/klines"
               f"?symbol={symbol}&interval={interval}&limit={limit}")
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) > 10:
            return data
    return None


def _parse_ohlcv(klines: List[list]) -> Dict[str, List[float]]:
    """Parse Binance klines into OHLCV lists."""
    o, h, l, c, v = [], [], [], [], []
    for k in klines:
        o.append(float(k[1]))
        h.append(float(k[2]))
        l.append(float(k[3]))
        c.append(float(k[4]))
        v.append(float(k[5]))
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


def _smart_round(value: float) -> float:
    """Round to appropriate precision based on magnitude."""
    if value == 0:
        return 0.0
    if value >= 1000:
        return round(value, 2)
    if value >= 1:
        return round(value, 4)
    if value >= 0.01:
        return round(value, 6)
    return round(value, 8)


# ---------------------------------------------------------------------------
# Technical Indicators (stdlib only)
# ---------------------------------------------------------------------------

def _atr(high: List[float], low: List[float], close: List[float],
         period: int = 14) -> float:
    """Average True Range over last `period` bars."""
    trs: List[float] = []
    for i in range(1, len(high)):
        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
        trs.append(tr)
    if len(trs) < period:
        return statistics.mean(trs) if trs else 0.0
    return statistics.mean(trs[-period:])


def _atr_series(high: List[float], low: List[float], close: List[float],
                period: int = 14) -> List[float]:
    """ATR as a full series (for Supertrend etc.)."""
    n = len(high)
    trs: List[float] = [high[0] - low[0]]
    for i in range(1, n):
        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
        trs.append(tr)
    # RMA (Wilder smoothing)
    atr_vals: List[float] = [0.0] * n
    if n < period:
        return atr_vals
    atr_vals[period - 1] = statistics.mean(trs[:period])
    for i in range(period, n):
        atr_vals[i] = (atr_vals[i - 1] * (period - 1) + trs[i]) / period
    return atr_vals


def _sma(data: List[float], period: int) -> List[float]:
    """Simple Moving Average series."""
    result: List[float] = [0.0] * len(data)
    for i in range(period - 1, len(data)):
        result[i] = statistics.mean(data[i - period + 1: i + 1])
    return result


def _ema(data: List[float], period: int) -> List[float]:
    """Exponential Moving Average series."""
    result: List[float] = [0.0] * len(data)
    if len(data) < period:
        return result
    result[period - 1] = statistics.mean(data[:period])
    k = 2.0 / (period + 1)
    for i in range(period, len(data)):
        result[i] = data[i] * k + result[i - 1] * (1 - k)
    return result


def _adx(high: List[float], low: List[float], close: List[float],
         period: int = 14) -> Dict[str, float]:
    """Compute ADX, +DI, -DI (latest values)."""
    n = len(high)
    if n < period + 2:
        return {"adx": 0.0, "plus_di": 0.0, "minus_di": 0.0}

    plus_dm: List[float] = []
    minus_dm: List[float] = []
    tr_list: List[float] = []

    for i in range(1, n):
        up_move = high[i] - high[i - 1]
        down_move = low[i - 1] - low[i]
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)
        tr_list.append(max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        ))

    if len(tr_list) < period:
        return {"adx": 0.0, "plus_di": 0.0, "minus_di": 0.0}

    # Wilder smoothing
    sm_plus = statistics.mean(plus_dm[:period])
    sm_minus = statistics.mean(minus_dm[:period])
    sm_tr = statistics.mean(tr_list[:period])

    dx_list: List[float] = []
    for i in range(period, len(tr_list)):
        sm_plus = (sm_plus * (period - 1) + plus_dm[i]) / period
        sm_minus = (sm_minus * (period - 1) + minus_dm[i]) / period
        sm_tr = (sm_tr * (period - 1) + tr_list[i]) / period

        plus_di = 100.0 * sm_plus / sm_tr if sm_tr > 0 else 0.0
        minus_di = 100.0 * sm_minus / sm_tr if sm_tr > 0 else 0.0
        di_sum = plus_di + minus_di
        dx = 100.0 * abs(plus_di - minus_di) / di_sum if di_sum > 0 else 0.0
        dx_list.append(dx)

    if len(dx_list) < period:
        adx_val = statistics.mean(dx_list) if dx_list else 0.0
    else:
        adx_val = statistics.mean(dx_list[:period])
        for i in range(period, len(dx_list)):
            adx_val = (adx_val * (period - 1) + dx_list[i]) / period

    # Final +DI / -DI
    final_plus_di = 100.0 * sm_plus / sm_tr if sm_tr > 0 else 0.0
    final_minus_di = 100.0 * sm_minus / sm_tr if sm_tr > 0 else 0.0

    return {"adx": adx_val, "plus_di": final_plus_di, "minus_di": final_minus_di}


def _momentum(data: List[float], period: int = 10) -> float:
    """Simple momentum: close[now] - close[period ago]."""
    if len(data) <= period:
        return 0.0
    return data[-1] - data[-1 - period]


def _bollinger_bands(close: List[float], period: int = 20,
                     std_mult: float = 2.0) -> Dict[str, float]:
    """Bollinger Bands (latest upper, mid, lower)."""
    if len(close) < period:
        return {"upper": 0.0, "mid": 0.0, "lower": 0.0}
    window = close[-period:]
    mid = statistics.mean(window)
    std = statistics.stdev(window) if len(window) > 1 else 0.0
    return {
        "upper": mid + std_mult * std,
        "mid": mid,
        "lower": mid - std_mult * std,
    }


def _keltner_channels(high: List[float], low: List[float], close: List[float],
                      period: int = 20, atr_mult: float = 1.5) -> Dict[str, float]:
    """Keltner Channels (latest upper, mid, lower)."""
    if len(close) < period:
        return {"upper": 0.0, "mid": 0.0, "lower": 0.0}
    ema_vals = _ema(close, period)
    mid = ema_vals[-1]
    atr_val = _atr(high, low, close, period)
    return {
        "upper": mid + atr_mult * atr_val,
        "mid": mid,
        "lower": mid - atr_mult * atr_val,
    }


def _highest(data: List[float], period: int) -> float:
    """Highest value in last `period` bars."""
    if len(data) < period:
        return max(data) if data else 0.0
    return max(data[-period:])


def _lowest(data: List[float], period: int) -> float:
    """Lowest value in last `period` bars."""
    if len(data) < period:
        return min(data) if data else 0.0
    return min(data[-period:])


def _linreg_slope(data: List[float], period: int) -> float:
    """Linear regression slope over last `period` bars."""
    if len(data) < period:
        return 0.0
    y = data[-period:]
    n = len(y)
    x_mean = (n - 1) / 2.0
    y_mean = statistics.mean(y)
    num = sum((i - x_mean) * (y[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den != 0 else 0.0


# ---------------------------------------------------------------------------
# STRATEGY 1: Triple Supertrend Confirmation
# ---------------------------------------------------------------------------
# Source: keithorange/HUGE_FreqTrade_Strategy_Collection
# Logic: 3 Supertrend indicators with different ATR params must agree.
#   - ST1: period=10, multiplier=1.0
#   - ST2: period=11, multiplier=2.0
#   - ST3: period=12, multiplier=3.0
# LONG: all 3 show uptrend, SHORT: all 3 show downtrend
# WR: ~75% when all 3 agree (triple confirmation reduces false signals)
# ---------------------------------------------------------------------------

def _supertrend(high: List[float], low: List[float], close: List[float],
                atr_period: int, multiplier: float) -> List[int]:
    """Compute Supertrend direction series. +1 = uptrend, -1 = downtrend."""
    n = len(close)
    atr_vals = _atr_series(high, low, close, atr_period)
    direction = [1] * n  # 1 = up, -1 = down
    upper_band = [0.0] * n
    lower_band = [0.0] * n

    for i in range(n):
        hl2 = (high[i] + low[i]) / 2.0
        upper_band[i] = hl2 + multiplier * atr_vals[i]
        lower_band[i] = hl2 - multiplier * atr_vals[i]

    for i in range(1, n):
        # Lower band can only go up
        if lower_band[i] < lower_band[i - 1] and close[i - 1] > lower_band[i - 1]:
            lower_band[i] = lower_band[i - 1]
        # Upper band can only go down
        if upper_band[i] > upper_band[i - 1] and close[i - 1] < upper_band[i - 1]:
            upper_band[i] = upper_band[i - 1]

        # Direction logic
        prev_dir = direction[i - 1]
        if prev_dir == 1:
            # Was uptrend
            if close[i] < lower_band[i]:
                direction[i] = -1
            else:
                direction[i] = 1
        else:
            # Was downtrend
            if close[i] > upper_band[i]:
                direction[i] = 1
            else:
                direction[i] = -1

    return direction


def triple_supertrend(ohlcv: Dict[str, List[float]], symbol: str,
                      price: float, atr_val: float) -> Optional[Dict[str, Any]]:
    """Triple Supertrend Confirmation strategy."""
    o, h, l, c = ohlcv["open"], ohlcv["high"], ohlcv["low"], ohlcv["close"]
    n = len(c)
    if n < 20:
        return None

    st1 = _supertrend(h, l, c, 10, 1.0)
    st2 = _supertrend(h, l, c, 11, 2.0)
    st3 = _supertrend(h, l, c, 12, 3.0)

    d1, d2, d3 = st1[-1], st2[-1], st3[-1]

    if atr_val <= 0 or price <= 0:
        return None

    if d1 == 1 and d2 == 1 and d3 == 1:
        direction = "LONG"
        tp = price + 2.5 * atr_val
        sl = price - 1.5 * atr_val
    elif d1 == -1 and d2 == -1 and d3 == -1:
        direction = "SHORT"
        tp = price - 2.5 * atr_val
        sl = price + 1.5 * atr_val
    else:
        return None

    # Require fresh signal: at least one ST flipped in last 3 bars
    flipped = False
    for offset in range(1, min(4, n)):
        if st1[-offset] != st1[-offset - 1] if offset < n else False:
            flipped = True
            break
        if st2[-offset] != st2[-offset - 1] if offset < n else False:
            flipped = True
            break
        if st3[-offset] != st3[-offset - 1] if offset < n else False:
            flipped = True
            break
    if not flipped:
        return None

    rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0
    if rr < 1.3:
        return None

    return {
        "strategy": "triple_supertrend",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": _smart_round(price),
        "take_profit": _smart_round(tp),
        "stop_loss": _smart_round(sl),
        "confidence": 0.75,
        "risk_reward": round(rr, 2),
        "reason": (f"Triple Supertrend {direction}: ST1(10,1.0)={'+' if d1 > 0 else '-'}, "
                   f"ST2(11,2.0)={'+' if d2 > 0 else '-'}, "
                   f"ST3(12,3.0)={'+' if d3 > 0 else '-'}, "
                   f"ATR={atr_val:.4f}"),
        "source_system": "incubator",
        "tooltip": "keithorange/HUGE_FreqTrade_Strategy_Collection - Triple Supertrend",
        "timeframe": "4h",
        "timestamp": _now_iso(),
    }


# ---------------------------------------------------------------------------
# STRATEGY 2: ADX Momentum
# ---------------------------------------------------------------------------
# Source: keithorange/HUGE_FreqTrade_Strategy_Collection
# Logic: ADX(14) > 25 + Momentum(10) > 0 + DI crossover
# LONG: +DI > 25 AND +DI > -DI
# SHORT: -DI > 25 AND -DI > +DI
# Confidence scales with ADX: 25=0.60, 40+=0.85
# ---------------------------------------------------------------------------

def adx_momentum(ohlcv: Dict[str, List[float]], symbol: str,
                 price: float, atr_val: float) -> Optional[Dict[str, Any]]:
    """ADX Momentum strategy."""
    h, l, c = ohlcv["high"], ohlcv["low"], ohlcv["close"]
    if len(c) < 30:
        return None

    adx_data = _adx(h, l, c, 14)
    adx_val = adx_data["adx"]
    plus_di = adx_data["plus_di"]
    minus_di = adx_data["minus_di"]
    mom = _momentum(c, 10)

    if adx_val < 25:
        return None

    if atr_val <= 0 or price <= 0:
        return None

    direction = None
    if plus_di > 25 and plus_di > minus_di and mom > 0:
        direction = "LONG"
        tp = price + 3.0 * atr_val
        sl = price - 1.5 * atr_val
    elif minus_di > 25 and minus_di > plus_di and mom < 0:
        direction = "SHORT"
        tp = price - 3.0 * atr_val
        sl = price + 1.5 * atr_val
    else:
        return None

    # Confidence scales with ADX strength
    conf = min(0.85, 0.60 + (adx_val - 25) / 60.0)

    rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0
    if rr < 1.3:
        return None

    return {
        "strategy": "adx_momentum",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": _smart_round(price),
        "take_profit": _smart_round(tp),
        "stop_loss": _smart_round(sl),
        "confidence": round(conf, 2),
        "risk_reward": round(rr, 2),
        "reason": (f"ADX Momentum {direction}: ADX={adx_val:.1f}, "
                   f"+DI={plus_di:.1f}, -DI={minus_di:.1f}, "
                   f"Mom(10)={mom:.4f}"),
        "source_system": "incubator",
        "tooltip": "keithorange/HUGE_FreqTrade_Strategy_Collection - ADX Momentum",
        "timeframe": "4h",
        "timestamp": _now_iso(),
    }


# ---------------------------------------------------------------------------
# STRATEGY 3: TTM Squeeze (John Carter)
# ---------------------------------------------------------------------------
# Source: hackingthemarkets/ttm-squeeze
# Logic: BB(20,2.0) inside KC(20,1.5) = squeeze ON (compression)
#   Squeeze OFF + momentum direction = breakout signal
#   Momentum = close - midline of ((HH(20)+LL(20))/2 + SMA(20))/2
# LONG: squeeze fires OFF + momentum > 0 and rising
# SHORT: squeeze fires OFF + momentum < 0 and falling
# TP: 3x ATR, SL: 2x ATR (wider for breakout trades)
# Confidence: 0.70 base + 0.10 if squeeze held 6+ bars
# ---------------------------------------------------------------------------

def _squeeze_momentum(high: List[float], low: List[float], close: List[float],
                      period: int = 20) -> List[float]:
    """TTM Squeeze momentum oscillator series."""
    n = len(close)
    mom: List[float] = [0.0] * n
    sma_vals = _sma(close, period)

    for i in range(period - 1, n):
        hh = max(high[i - period + 1: i + 1])
        ll = min(low[i - period + 1: i + 1])
        midline = ((hh + ll) / 2.0 + sma_vals[i]) / 2.0
        mom[i] = close[i] - midline

    return mom


def ttm_squeeze_carter(ohlcv: Dict[str, List[float]], symbol: str,
                       price: float, atr_val: float) -> Optional[Dict[str, Any]]:
    """TTM Squeeze strategy (John Carter)."""
    h, l, c = ohlcv["high"], ohlcv["low"], ohlcv["close"]
    n = len(c)
    if n < 30:
        return None

    if atr_val <= 0 or price <= 0:
        return None

    # Detect squeeze state over recent bars
    squeeze_on_count = 0
    squeeze_was_on = False
    squeeze_just_off = False

    for i in range(max(0, n - 12), n):
        if i < 20:
            continue
        window = c[i - 20 + 1: i + 1]
        if len(window) < 20:
            continue
        bb_mid = statistics.mean(window)
        bb_std = statistics.stdev(window) if len(window) > 1 else 0.0
        bb_upper = bb_mid + 2.0 * bb_std
        bb_lower = bb_mid - 2.0 * bb_std

        # Keltner: EMA-based mid + ATR band
        ema_vals = _ema(c[:i + 1], 20)
        kc_mid = ema_vals[i]
        local_atr = _atr(h[:i + 1], l[:i + 1], c[:i + 1], 20)
        kc_upper = kc_mid + 1.5 * local_atr
        kc_lower = kc_mid - 1.5 * local_atr

        is_squeeze = bb_lower > kc_lower and bb_upper < kc_upper

        if is_squeeze:
            squeeze_on_count += 1
            squeeze_was_on = True
        elif squeeze_was_on and i >= n - 2:
            # Squeeze just released in last 2 bars
            squeeze_just_off = True

    if not squeeze_just_off:
        return None

    # Momentum direction
    mom = _squeeze_momentum(h, l, c, 20)
    current_mom = mom[-1]
    prev_mom = mom[-2] if n > 1 else 0.0
    mom_rising = current_mom > prev_mom

    direction = None
    if current_mom > 0 and mom_rising:
        direction = "LONG"
        tp = price + 3.0 * atr_val
        sl = price - 2.0 * atr_val
    elif current_mom < 0 and not mom_rising:
        direction = "SHORT"
        tp = price - 3.0 * atr_val
        sl = price + 2.0 * atr_val
    else:
        return None

    # Confidence: base 0.70, +0.10 if squeeze held 6+ bars
    conf = 0.70
    if squeeze_on_count >= 6:
        conf = 0.80

    rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0
    if rr < 1.2:
        return None

    return {
        "strategy": "ttm_squeeze_carter",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": _smart_round(price),
        "take_profit": _smart_round(tp),
        "stop_loss": _smart_round(sl),
        "confidence": round(conf, 2),
        "risk_reward": round(rr, 2),
        "reason": (f"TTM Squeeze {direction}: squeeze held {squeeze_on_count} bars, "
                   f"momentum={current_mom:.4f} ({'rising' if mom_rising else 'falling'}), "
                   f"ATR={atr_val:.4f}"),
        "source_system": "incubator",
        "tooltip": "hackingthemarkets/ttm-squeeze - John Carter TTM Squeeze",
        "timeframe": "4h",
        "timestamp": _now_iso(),
    }


# ---------------------------------------------------------------------------
# STRATEGY 4: Dual Thrust (Opening Range Breakout)
# ---------------------------------------------------------------------------
# Source: je-suis-tm/quant-trading (9.5k stars)
# Logic: range = max(HH-LC, HC-LL) from previous N bars (default 4)
#   Upper trigger = open + K1 * range (K1=0.5)
#   Lower trigger = open - K2 * range (K2=0.5)
#   LONG: close > upper trigger
#   SHORT: close < lower trigger
# TP: 2x ATR, SL: 1x ATR (tight -- range breakout has quick confirmation)
# ---------------------------------------------------------------------------

def dual_thrust_orb(ohlcv: Dict[str, List[float]], symbol: str,
                    price: float, atr_val: float) -> Optional[Dict[str, Any]]:
    """Dual Thrust Opening Range Breakout strategy."""
    o, h, l, c = ohlcv["open"], ohlcv["high"], ohlcv["low"], ohlcv["close"]
    n = len(c)
    lookback = 4
    k1, k2 = 0.5, 0.5

    if n < lookback + 2:
        return None

    if atr_val <= 0 or price <= 0:
        return None

    # Calculate range from previous N bars (excluding current)
    prev_h = h[-(lookback + 1):-1]
    prev_l = l[-(lookback + 1):-1]
    prev_c = c[-(lookback + 1):-1]

    hh = max(prev_h)
    ll = min(prev_l)
    hc = max(prev_c)
    lc = min(prev_c)

    range_val = max(hh - lc, hc - ll)
    if range_val <= 0:
        return None

    current_open = o[-1]
    upper_trigger = current_open + k1 * range_val
    lower_trigger = current_open - k2 * range_val

    direction = None
    if price > upper_trigger:
        direction = "LONG"
        tp = price + 2.0 * atr_val
        sl = price - 1.0 * atr_val
    elif price < lower_trigger:
        direction = "SHORT"
        tp = price - 2.0 * atr_val
        sl = price + 1.0 * atr_val
    else:
        return None

    # Ensure the breakout is meaningful (at least 0.3% beyond trigger)
    if direction == "LONG":
        breakout_pct = (price - upper_trigger) / upper_trigger
    else:
        breakout_pct = (lower_trigger - price) / lower_trigger
    if breakout_pct < 0.003:
        return None

    rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0
    if rr < 1.3:
        return None

    return {
        "strategy": "dual_thrust_orb",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": _smart_round(price),
        "take_profit": _smart_round(tp),
        "stop_loss": _smart_round(sl),
        "confidence": 0.68,
        "risk_reward": round(rr, 2),
        "reason": (f"Dual Thrust {direction}: range={range_val:.4f}, "
                   f"trigger={'upper' if direction == 'LONG' else 'lower'}="
                   f"{_smart_round(upper_trigger if direction == 'LONG' else lower_trigger)}, "
                   f"breakout={breakout_pct * 100:.2f}%"),
        "source_system": "incubator",
        "tooltip": "je-suis-tm/quant-trading (9.5k stars) - Dual Thrust ORB",
        "timeframe": "4h",
        "timestamp": _now_iso(),
    }


# ---------------------------------------------------------------------------
# STRATEGY 5: ICT Fair Value Gap (FVG)
# ---------------------------------------------------------------------------
# Source: ArunKBhaskar/PineScript (354 stars)
# Logic: Bullish FVG: candle[2].high < candle[0].low (3-bar gap)
#   Bearish FVG: candle[2].low > candle[0].high
#   Displacement: middle candle body > 1.5x ATR
#   LONG: price retraces into bullish FVG zone
#   SHORT: price retraces into bearish FVG zone
# TP: 3x ATR, SL: just beyond FVG zone
# Confidence: 0.65 base + 0.10 if FVG aligns with HTF trend (20-SMA)
# ---------------------------------------------------------------------------

def ict_fair_value_gap(ohlcv: Dict[str, List[float]], symbol: str,
                       price: float, atr_val: float) -> Optional[Dict[str, Any]]:
    """ICT Fair Value Gap (FVG) strategy."""
    o, h, l, c = ohlcv["open"], ohlcv["high"], ohlcv["low"], ohlcv["close"]
    n = len(c)
    if n < 25:
        return None

    if atr_val <= 0 or price <= 0:
        return None

    # HTF trend via SMA(20)
    sma20 = _sma(c, 20)
    htf_bullish = price > sma20[-1] if sma20[-1] > 0 else True

    # Scan last 10 bars for FVG formation
    best_fvg = None

    for i in range(n - 10, n - 2):
        if i < 2:
            continue

        # Middle candle (displacement candle)
        mid_body = abs(c[i] - o[i])

        # Bullish FVG: bar[i-2].high < bar[i].low (gap up)
        if h[i - 2] < l[i]:
            # Displacement check: middle candle body > 1.5x ATR
            if mid_body > 1.5 * atr_val:
                fvg_top = l[i]        # current bar low
                fvg_bottom = h[i - 2]  # 2-bars-ago high
                fvg_mid = (fvg_top + fvg_bottom) / 2.0

                # Price must retrace into the FVG zone
                if fvg_bottom <= price <= fvg_top:
                    best_fvg = {
                        "type": "bullish",
                        "top": fvg_top,
                        "bottom": fvg_bottom,
                        "mid": fvg_mid,
                        "displacement": mid_body,
                        "bar_idx": i,
                    }

        # Bearish FVG: bar[i-2].low > bar[i].high (gap down)
        if l[i - 2] > h[i]:
            if mid_body > 1.5 * atr_val:
                fvg_top = l[i - 2]  # 2-bars-ago low
                fvg_bottom = h[i]    # current bar high
                fvg_mid = (fvg_top + fvg_bottom) / 2.0

                if fvg_bottom <= price <= fvg_top:
                    best_fvg = {
                        "type": "bearish",
                        "top": fvg_top,
                        "bottom": fvg_bottom,
                        "mid": fvg_mid,
                        "displacement": mid_body,
                        "bar_idx": i,
                    }

    if best_fvg is None:
        return None

    direction = None
    if best_fvg["type"] == "bullish":
        direction = "LONG"
        tp = price + 3.0 * atr_val
        sl = best_fvg["bottom"] - 0.2 * atr_val  # just beyond FVG zone
    elif best_fvg["type"] == "bearish":
        direction = "SHORT"
        tp = price - 3.0 * atr_val
        sl = best_fvg["top"] + 0.2 * atr_val  # just beyond FVG zone
    else:
        return None

    # Confidence: 0.65 base + 0.10 if FVG aligns with HTF trend
    conf = 0.65
    if (direction == "LONG" and htf_bullish) or (direction == "SHORT" and not htf_bullish):
        conf = 0.75

    rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0
    if rr < 1.2:
        return None

    return {
        "strategy": "ict_fair_value_gap",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": _smart_round(price),
        "take_profit": _smart_round(tp),
        "stop_loss": _smart_round(sl),
        "confidence": round(conf, 2),
        "risk_reward": round(rr, 2),
        "reason": (f"ICT FVG {direction}: {best_fvg['type']} gap "
                   f"[{_smart_round(best_fvg['bottom'])}-{_smart_round(best_fvg['top'])}], "
                   f"displacement={best_fvg['displacement']:.4f} "
                   f"({'>{:.1f}x ATR'.format(best_fvg['displacement'] / atr_val)}), "
                   f"HTF={'bull' if htf_bullish else 'bear'}"),
        "source_system": "incubator",
        "tooltip": "ArunKBhaskar/PineScript (354 stars) - ICT Fair Value Gap",
        "timeframe": "4h",
        "timestamp": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Evaluator registry
# ---------------------------------------------------------------------------

_EVALUATORS = [
    triple_supertrend,
    adx_momentum,
    ttm_squeeze_carter,
    dual_thrust_orb,
    ict_fair_value_gap,
]


# ---------------------------------------------------------------------------
# Strategy registry (for scanner registration)
# ---------------------------------------------------------------------------

INCUBATOR_STRATEGIES: Dict[str, Dict[str, Any]] = {
    "triple_supertrend": {
        "name": "Triple Supertrend Confirmation",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "3x Supertrend (10/1.0, 11/2.0, 12/3.0) all agree on direction",
        "win_rate_est": "70-78%",
        "references": [
            "keithorange/HUGE_FreqTrade_Strategy_Collection (GitHub)",
        ],
    },
    "adx_momentum": {
        "name": "ADX Momentum",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "ADX(14) > 25 + DI crossover + Momentum(10) confirmation",
        "win_rate_est": "60-85%",
        "references": [
            "keithorange/HUGE_FreqTrade_Strategy_Collection (GitHub)",
            "Wilder, New Concepts in Technical Trading Systems (1978)",
        ],
    },
    "ttm_squeeze_carter": {
        "name": "TTM Squeeze (John Carter)",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "BB(20,2) inside KC(20,1.5) squeeze release + momentum direction",
        "win_rate_est": "70-80%",
        "references": [
            "John Carter, Mastering the Trade (2005) -- TTM Squeeze",
            "hackingthemarkets/ttm-squeeze (GitHub)",
        ],
    },
    "dual_thrust_orb": {
        "name": "Dual Thrust Opening Range Breakout",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "Open + K*range breakout (max(HH-LC, HC-LL), K=0.5)",
        "win_rate_est": "65-72%",
        "references": [
            "je-suis-tm/quant-trading (GitHub, 9.5k stars)",
            "Michael Harris, Short-Term Trading with Price Patterns (1999)",
        ],
    },
    "ict_fair_value_gap": {
        "name": "ICT Fair Value Gap",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "3-bar FVG with displacement (body > 1.5x ATR) + HTF trend filter",
        "win_rate_est": "65-75%",
        "references": [
            "ArunKBhaskar/PineScript (GitHub, 354 stars)",
            "ICT Inner Circle Trader -- Fair Value Gap concept",
        ],
    },
}


# ---------------------------------------------------------------------------
# Main pick generator
# ---------------------------------------------------------------------------

def generate_incubator_picks(symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Generate picks from all 5 incubator strategies.

    Args:
        symbols: List of trading pairs (default: top 20 crypto by volume).

    Returns:
        List of pick dicts with entry/TP/SL.
    """
    if symbols is None:
        symbols = _DEFAULT_SYMBOLS

    picks: List[Dict[str, Any]] = []

    for symbol in symbols:
        klines = _fetch_klines(symbol, interval="4h", limit=100)
        if not klines:
            continue

        ohlcv = _parse_ohlcv(klines)
        if len(ohlcv["close"]) < 20:
            continue

        price = ohlcv["close"][-1]
        atr_val = _atr(ohlcv["high"], ohlcv["low"], ohlcv["close"], 14)
        if atr_val <= 0 or price <= 0:
            continue

        for evaluator in _EVALUATORS:
            try:
                pick = evaluator(ohlcv, symbol, price, atr_val)
                if pick:
                    picks.append(pick)
            except Exception:
                continue

    return picks


# ---------------------------------------------------------------------------
# CLI entrypoint (for workflow / standalone testing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    print(f"Incubator Strategies v1.0 -- {len(INCUBATOR_STRATEGIES)} strategies")
    print(f"Scanning {len(_DEFAULT_SYMBOLS)} symbols...")
    results = generate_incubator_picks()
    print(f"Generated {len(results)} pick(s)")
    for p in results:
        print(f"  [{p['strategy']}] {p['symbol']} {p['direction']} "
              f"@ {p['entry_price']} -> TP {p['take_profit']} / SL {p['stop_loss']} "
              f"(conf={p['confidence']})")
    # Write results to data dir
    out_path = os.path.join(os.path.dirname(__file__), "data", "incubator_picks.json")
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Wrote {len(results)} picks to {out_path}")
    except Exception as e:
        print(f"Failed to write picks: {e}", file=sys.stderr)
