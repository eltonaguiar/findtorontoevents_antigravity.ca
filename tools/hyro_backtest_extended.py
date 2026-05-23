#!/usr/bin/env python3
"""
Extended Hyro-style backtester: base strategies from hyro_backtest.py plus catalog-style setups.

Run from repo root:
  python tools/hyro_backtest_extended.py --months 6 --symbols BTCUSDT ETHUSDT SOLUSDT
  python tools/hyro_backtest_extended.py --strategy volume --long-only --save
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# tools/ on path when executed as python tools/hyro_backtest_extended.py
_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import hyro_backtest as hb

fetch_candles = hb.fetch_candles
parse_candles = hb.parse_candles
calc_sma = hb.calc_sma
calc_std = hb.calc_std
calc_rsi = hb.calc_rsi
calc_atr = hb.calc_atr
HyroSimulator = hb.HyroSimulator
HYRO = hb.HYRO
strategy_bollinger_reversion = hb.strategy_bollinger_reversion
strategy_rsi2_extreme = hb.strategy_rsi2_extreme
strategy_volume_breakout = hb.strategy_volume_breakout
strategy_sr_bounce = hb.strategy_sr_bounce

WORKSPACE = _TOOLS.parent
DEFAULT_OUTPUT = WORKSPACE / "audit_dashboard" / "data" / "hyro_backtest_extended_results.json"


def calc_ema(values: list[float], period: int) -> list:
    n = len(values)
    result = [None] * n
    if n < period:
        return result
    k = 2 / (period + 1)
    result[period - 1] = sum(values[:period]) / period
    for i in range(period, n):
        result[i] = values[i] * k + result[i - 1] * (1 - k)
    return result


def calc_macd(
    candles: list[dict], fast: int = 12, slow: int = 26, signal_n: int = 9
) -> tuple[list, list, list]:
    closes = [c["close"] for c in candles]
    ema_f = calc_ema(closes, fast)
    ema_s = calc_ema(closes, slow)
    n = len(closes)
    macd_line: list = [None] * n
    for i in range(n):
        if ema_f[i] is not None and ema_s[i] is not None:
            macd_line[i] = ema_f[i] - ema_s[i]
    macd_seq: list[float] = []
    idx_map: list[int] = []
    for i, v in enumerate(macd_line):
        if v is not None:
            macd_seq.append(v)
            idx_map.append(i)
    signal_line = [None] * n
    hist = [None] * n
    if len(macd_seq) < signal_n + 1:
        return macd_line, signal_line, hist
    sig_ema = calc_ema(macd_seq, signal_n)
    for j, orig_i in enumerate(idx_map):
        sv = sig_ema[j]
        if sv is None:
            continue
        signal_line[orig_i] = sv
        mv = macd_line[orig_i]
        if mv is not None:
            hist[orig_i] = mv - sv
    return macd_line, signal_line, hist


def calc_adx(candles: list[dict], period: int = 14) -> tuple[list, list, list]:
    """Rolling-mean style ADX / +DI / -DI (matches common pandas tutorials, no numpy)."""
    n = len(candles)
    adx = [None] * n
    plus_di = [None] * n
    minus_di = [None] * n
    if n < period * 3:
        return adx, plus_di, minus_di
    tr: list[float] = []
    p_dm: list[float] = []
    m_dm: list[float] = []
    for i in range(1, n):
        h, l = candles[i]["high"], candles[i]["low"]
        pc = candles[i - 1]["close"]
        h1, l1 = candles[i - 1]["high"], candles[i - 1]["low"]
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))
        up = h - h1
        dn = l1 - l
        p_dm.append(up if up > dn and up > 0 else 0.0)
        m_dm.append(dn if dn > up and dn > 0 else 0.0)
    dx_vals: list[float] = []
    dx_idx: list[int] = []
    for i in range(period - 1, len(tr)):
        i_c = i + 1
        tr_m = sum(tr[i - period + 1 : i + 1]) / period
        p_m = sum(p_dm[i - period + 1 : i + 1]) / period
        m_m = sum(m_dm[i - period + 1 : i + 1]) / period
        if tr_m <= 0:
            continue
        pp = 100.0 * p_m / tr_m
        mm = 100.0 * m_m / tr_m
        plus_di[i_c] = pp
        minus_di[i_c] = mm
        tot = pp + mm
        dx = 100.0 * abs(pp - mm) / tot if tot > 0 else 0.0
        dx_vals.append(dx)
        dx_idx.append(i_c)
    for j in range(period - 1, len(dx_vals)):
        adx_i = dx_idx[j]
        adx[adx_i] = sum(dx_vals[j - period + 1 : j + 1]) / period
    return adx, plus_di, minus_di


def calc_stochastic(candles: list[dict], k_period: int = 14, d_period: int = 3) -> tuple[list, list]:
    n = len(candles)
    k_vals = [None] * n
    d_vals = [None] * n
    for i in range(k_period - 1, n):
        window = candles[i - k_period + 1 : i + 1]
        hh = max(c["high"] for c in window)
        ll = min(c["low"] for c in window)
        if hh == ll:
            k_vals[i] = 50.0
        else:
            k_vals[i] = (candles[i]["close"] - ll) / (hh - ll) * 100
    for i in range(k_period - 1 + d_period - 1, n):
        chunk = [v for v in k_vals[i - d_period + 1 : i + 1] if v is not None]
        if len(chunk) == d_period:
            d_vals[i] = sum(chunk) / d_period
    return k_vals, d_vals


def calc_donchian(candles: list[dict], period: int = 20) -> tuple[list, list, list]:
    n = len(candles)
    upper = [None] * n
    lower = [None] * n
    mid = [None] * n
    for i in range(period - 1, n):
        window = candles[i - period + 1 : i + 1]
        u = max(c["high"] for c in window)
        lo = min(c["low"] for c in window)
        upper[i] = u
        lower[i] = lo
        mid[i] = (u + lo) / 2
    return upper, lower, mid


def calc_vwap_proxy(candles: list[dict]) -> list:
    n = len(candles)
    vwap = [None] * n
    cum_tp_vol = 0.0
    cum_vol = 0.0
    current_day = None
    for i, c in enumerate(candles):
        day = c["open_time"] // 86400000
        if day != current_day:
            cum_tp_vol = 0.0
            cum_vol = 0.0
            current_day = day
        tp = (c["high"] + c["low"] + c["close"]) / 3
        cum_tp_vol += tp * c["volume"]
        cum_vol += c["volume"]
        if cum_vol > 0:
            vwap[i] = cum_tp_vol / cum_vol
    return vwap


def strategy_connors_rsi2(candles: list[dict], params: dict | None = None) -> list[dict]:
    p = params or {}
    rsi_period = p.get("rsi_period", 2)
    sma_filter = p.get("sma_filter", 200)
    sma_tp = p.get("sma_tp", 5)
    atr_period = p.get("atr_period", 14)
    rsi_long = p.get("rsi_long", 10)
    rsi_short = p.get("rsi_short", 90)
    atr_sl_mult = p.get("atr_sl_mult", 2.0)
    rsi = calc_rsi(candles, rsi_period)
    sma200 = calc_sma(candles, sma_filter)
    sma5 = calc_sma(candles, sma_tp)
    atr = calc_atr(candles, atr_period)
    signals = []
    for i in range(max(sma_filter, atr_period) + 1, len(candles)):
        if rsi[i] is None or sma200[i] is None or sma5[i] is None or atr[i] is None:
            continue
        c = candles[i]
        if rsi[i] < rsi_long and c["close"] > sma200[i] and sma5[i] > c["close"]:
            entry = c["close"]
            sl = entry - atr_sl_mult * atr[i]
            tp = sma5[i]
            if tp > entry:
                rr = (tp - entry) / (entry - sl) if entry != sl else 0
                if rr >= 0.5:
                    signals.append(
                        {
                            "index": i,
                            "time": c["open_time"],
                            "direction": "LONG",
                            "entry": round(entry, 2),
                            "sl": round(sl, 2),
                            "tp": round(tp, 2),
                            "rr": round(rr, 2),
                            "strategy": "connors_rsi2",
                        }
                    )
        if rsi[i] > rsi_short and c["close"] < sma200[i] and sma5[i] < c["close"]:
            entry = c["close"]
            sl = entry + atr_sl_mult * atr[i]
            tp = sma5[i]
            if tp < entry:
                rr = (entry - tp) / (sl - entry) if sl != entry else 0
                if rr >= 0.5:
                    signals.append(
                        {
                            "index": i,
                            "time": c["open_time"],
                            "direction": "SHORT",
                            "entry": round(entry, 2),
                            "sl": round(sl, 2),
                            "tp": round(tp, 2),
                            "rr": round(rr, 2),
                            "strategy": "connors_rsi2",
                        }
                    )
    return signals


def strategy_ema_crossover(candles: list[dict], params: dict | None = None) -> list[dict]:
    p = params or {}
    fast = p.get("fast", 9)
    slow = p.get("slow", 21)
    atr_period = p.get("atr_period", 14)
    tp_r = p.get("tp_r", 2.0)
    sl_atr = p.get("sl_atr", 1.5)
    closes = [c["close"] for c in candles]
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    rsi = calc_rsi(candles, 14)
    atr = calc_atr(candles, atr_period)
    signals = []
    for i in range(2, len(candles)):
        if (
            ema_fast[i] is None
            or ema_slow[i] is None
            or ema_fast[i - 1] is None
            or ema_slow[i - 1] is None
            or rsi[i] is None
            or atr[i] is None
        ):
            continue
        c = candles[i]
        if ema_fast[i] > ema_slow[i] and ema_fast[i - 1] <= ema_slow[i - 1] and rsi[i] > 50:
            entry = c["close"]
            sl = entry - sl_atr * atr[i]
            risk = entry - sl
            tp = entry + tp_r * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "LONG",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": round(tp_r, 2),
                    "strategy": "ema_crossover",
                }
            )
        if ema_fast[i] < ema_slow[i] and ema_fast[i - 1] >= ema_slow[i - 1] and rsi[i] < 50:
            entry = c["close"]
            sl = entry + sl_atr * atr[i]
            risk = sl - entry
            tp = entry - tp_r * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "SHORT",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": round(tp_r, 2),
                    "strategy": "ema_crossover",
                }
            )
    return signals


def strategy_keltner_reversion(candles: list[dict], params: dict | None = None) -> list[dict]:
    p = params or {}
    ema_period = p.get("ema_period", 20)
    atr_period = p.get("atr_period", 14)
    atr_mult = p.get("atr_mult", 2.0)
    rsi_filter = p.get("rsi_filter", True)
    closes = [c["close"] for c in candles]
    ema = calc_ema(closes, ema_period)
    atr = calc_atr(candles, atr_period)
    rsi = calc_rsi(candles, 14)
    signals = []
    for i in range(max(ema_period, atr_period) + 1, len(candles)):
        if ema[i] is None or atr[i] is None or rsi[i] is None:
            continue
        c = candles[i]
        upper = ema[i] + atr_mult * atr[i]
        lower = ema[i] - atr_mult * atr[i]
        if c["close"] < lower and (not rsi_filter or rsi[i] < 35):
            entry = c["close"]
            sl = lower - atr[i]
            tp = ema[i]
            if tp > entry:
                rr = (tp - entry) / (entry - sl) if entry != sl else 0
                if rr >= 1.0:
                    signals.append(
                        {
                            "index": i,
                            "time": c["open_time"],
                            "direction": "LONG",
                            "entry": round(entry, 2),
                            "sl": round(sl, 2),
                            "tp": round(tp, 2),
                            "rr": round(rr, 2),
                            "strategy": "keltner_reversion",
                        }
                    )
        if c["close"] > upper and (not rsi_filter or rsi[i] > 65):
            entry = c["close"]
            sl = upper + atr[i]
            tp = ema[i]
            if tp < entry:
                rr = (entry - tp) / (sl - entry) if sl != entry else 0
                if rr >= 1.0:
                    signals.append(
                        {
                            "index": i,
                            "time": c["open_time"],
                            "direction": "SHORT",
                            "entry": round(entry, 2),
                            "sl": round(sl, 2),
                            "tp": round(tp, 2),
                            "rr": round(rr, 2),
                            "strategy": "keltner_reversion",
                        }
                    )
    return signals


def strategy_macd_trend(candles: list[dict], params: dict | None = None) -> list[dict]:
    p = params or {}
    tp_r = p.get("tp_r", 2.0)
    atr_sl = p.get("atr_sl", 2.0)
    macd_line, signal_line, hist = calc_macd(candles)
    atr = calc_atr(candles, 14)
    signals = []
    for i in range(2, len(candles)):
        if (
            macd_line[i] is None
            or signal_line[i] is None
            or hist[i] is None
            or macd_line[i - 1] is None
            or signal_line[i - 1] is None
            or hist[i - 1] is None
            or atr[i] is None
        ):
            continue
        c = candles[i]
        if (
            macd_line[i] > signal_line[i]
            and macd_line[i - 1] <= signal_line[i - 1]
            and hist[i] > 0
            and hist[i] > hist[i - 1]
        ):
            entry = c["close"]
            sl = entry - atr_sl * atr[i]
            risk = entry - sl
            tp = entry + tp_r * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "LONG",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": round(tp_r, 2),
                    "strategy": "macd_trend",
                }
            )
        if (
            macd_line[i] < signal_line[i]
            and macd_line[i - 1] >= signal_line[i - 1]
            and hist[i] < 0
            and hist[i] < hist[i - 1]
        ):
            entry = c["close"]
            sl = entry + atr_sl * atr[i]
            risk = sl - entry
            tp = entry - tp_r * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "SHORT",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": round(tp_r, 2),
                    "strategy": "macd_trend",
                }
            )
    return signals


def strategy_vwap_reversion(candles: list[dict], params: dict | None = None) -> list[dict]:
    p = params or {}
    dev_pct = p.get("dev_pct", 2.0)
    atr_period = p.get("atr_period", 14)
    vwap = calc_vwap_proxy(candles)
    rsi = calc_rsi(candles, 14)
    atr = calc_atr(candles, atr_period)
    signals = []
    for i in range(max(20, atr_period) + 1, len(candles)):
        if vwap[i] is None or rsi[i] is None or atr[i] is None:
            continue
        c = candles[i]
        dev = (c["close"] - vwap[i]) / vwap[i] * 100
        if dev < -dev_pct and rsi[i] < 30:
            entry = c["close"]
            sl = entry - 1.5 * atr[i]
            tp = vwap[i]
            if tp > entry:
                rr = (tp - entry) / (entry - sl) if entry != sl else 0
                if rr >= 1.0:
                    signals.append(
                        {
                            "index": i,
                            "time": c["open_time"],
                            "direction": "LONG",
                            "entry": round(entry, 2),
                            "sl": round(sl, 2),
                            "tp": round(tp, 2),
                            "rr": round(rr, 2),
                            "strategy": "vwap_reversion",
                        }
                    )
        if dev > dev_pct and rsi[i] > 70:
            entry = c["close"]
            sl = entry + 1.5 * atr[i]
            tp = vwap[i]
            if tp < entry:
                rr = (entry - tp) / (sl - entry) if sl != entry else 0
                if rr >= 1.0:
                    signals.append(
                        {
                            "index": i,
                            "time": c["open_time"],
                            "direction": "SHORT",
                            "entry": round(entry, 2),
                            "sl": round(sl, 2),
                            "tp": round(tp, 2),
                            "rr": round(rr, 2),
                            "strategy": "vwap_reversion",
                        }
                    )
    return signals


def strategy_donchian_breakout(candles: list[dict], params: dict | None = None) -> list[dict]:
    p = params or {}
    period = p.get("period", 20)
    tp_r = p.get("tp_r", 2.0)
    atr_sl = p.get("atr_sl", 1.5)
    upper, lower, _mid = calc_donchian(candles, period)
    atr = calc_atr(candles, 14)
    signals = []
    for i in range(period + 1, len(candles)):
        if upper[i] is None or lower[i] is None or atr[i] is None:
            continue
        if upper[i - 1] is None or lower[i - 1] is None:
            continue
        c = candles[i]
        if c["close"] > upper[i - 1] and candles[i - 1]["close"] <= upper[i - 1]:
            entry = c["close"]
            sl = entry - atr_sl * atr[i]
            risk = entry - sl
            tp = entry + tp_r * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "LONG",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": round(tp_r, 2),
                    "strategy": "donchian_breakout",
                }
            )
        if c["close"] < lower[i - 1] and candles[i - 1]["close"] >= lower[i - 1]:
            entry = c["close"]
            sl = entry + atr_sl * atr[i]
            risk = sl - entry
            tp = entry - tp_r * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "SHORT",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": round(tp_r, 2),
                    "strategy": "donchian_breakout",
                }
            )
    return signals


def strategy_stochastic_reversion(candles: list[dict], params: dict | None = None) -> list[dict]:
    p = params or {}
    k_period = p.get("k_period", 14)
    d_period = p.get("d_period", 3)
    oversold = p.get("oversold", 20)
    overbought = p.get("overbought", 80)
    k_vals, d_vals = calc_stochastic(candles, k_period, d_period)
    atr = calc_atr(candles, 14)
    sma200 = calc_sma(candles, 200)
    signals = []
    for i in range(2, len(candles)):
        if (
            k_vals[i] is None
            or d_vals[i] is None
            or k_vals[i - 1] is None
            or d_vals[i - 1] is None
            or atr[i] is None
            or sma200[i] is None
        ):
            continue
        c = candles[i]
        if k_vals[i] < oversold and k_vals[i] > d_vals[i] and k_vals[i - 1] <= d_vals[i - 1]:
            entry = c["close"]
            sl = entry - 1.5 * atr[i]
            risk = entry - sl
            tp = entry + 2.0 * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "LONG",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": 2.0,
                    "strategy": "stochastic_reversion",
                }
            )
        if k_vals[i] > overbought and k_vals[i] < d_vals[i] and k_vals[i - 1] >= d_vals[i - 1]:
            entry = c["close"]
            sl = entry + 1.5 * atr[i]
            risk = sl - entry
            tp = entry - 2.0 * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "SHORT",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": 2.0,
                    "strategy": "stochastic_reversion",
                }
            )
    return signals


def strategy_supertrend(candles: list[dict], params: dict | None = None) -> list[dict]:
    p = params or {}
    period = p.get("period", 10)
    multiplier = p.get("multiplier", 3.0)
    tp_r = p.get("tp_r", 2.5)
    atr = calc_atr(candles, period)
    n = len(candles)
    supertrend: list = [None] * n
    direction = [0] * n
    for i in range(period, n):
        if atr[i] is None:
            continue
        hl2 = (candles[i]["high"] + candles[i]["low"]) / 2
        upper_band = hl2 + multiplier * atr[i]
        lower_band = hl2 - multiplier * atr[i]
        if supertrend[i - 1] is None:
            supertrend[i] = lower_band
            direction[i] = 1
            continue
        if direction[i - 1] == 1:
            if candles[i]["close"] < lower_band:
                direction[i] = -1
                supertrend[i] = upper_band
            else:
                direction[i] = 1
                final_lower = lower_band
                if lower_band > supertrend[i - 1] or candles[i - 1]["close"] < supertrend[i - 1]:
                    pass
                else:
                    final_lower = max(lower_band, supertrend[i - 1])
                supertrend[i] = final_lower
        else:
            if candles[i]["close"] > upper_band:
                direction[i] = 1
                supertrend[i] = lower_band
            else:
                direction[i] = -1
                final_upper = upper_band
                if upper_band < supertrend[i - 1] or candles[i - 1]["close"] > supertrend[i - 1]:
                    pass
                else:
                    final_upper = min(upper_band, supertrend[i - 1])
                supertrend[i] = final_upper
    signals = []
    for i in range(period + 1, n):
        if supertrend[i] is None or supertrend[i - 1] is None or atr[i] is None:
            continue
        if direction[i] == direction[i - 1]:
            continue
        c = candles[i]
        if direction[i] == 1:
            entry = c["close"]
            sl = supertrend[i]
            risk = entry - sl
            if risk > 0:
                tp = entry + tp_r * risk
                signals.append(
                    {
                        "index": i,
                        "time": c["open_time"],
                        "direction": "LONG",
                        "entry": round(entry, 2),
                        "sl": round(sl, 2),
                        "tp": round(tp, 2),
                        "rr": round(tp_r, 2),
                        "strategy": "supertrend",
                    }
                )
        else:
            entry = c["close"]
            sl = supertrend[i]
            risk = sl - entry
            if risk > 0:
                tp = entry - tp_r * risk
                signals.append(
                    {
                        "index": i,
                        "time": c["open_time"],
                        "direction": "SHORT",
                        "entry": round(entry, 2),
                        "sl": round(sl, 2),
                        "tp": round(tp, 2),
                        "rr": round(tp_r, 2),
                        "strategy": "supertrend",
                    }
                )
    return signals


def strategy_rsi_volume(candles: list[dict], params: dict | None = None) -> list[dict]:
    p = params or {}
    rsi_period = p.get("rsi_period", 14)
    vol_lookback = p.get("vol_lookback", 20)
    vol_mult = p.get("vol_mult", 1.5)
    rsi = calc_rsi(candles, rsi_period)
    sma50 = calc_sma(candles, 50)
    atr = calc_atr(candles, 14)
    signals = []
    for i in range(max(50, vol_lookback) + 1, len(candles)):
        if rsi[i] is None or sma50[i] is None or atr[i] is None:
            continue
        c = candles[i]
        avg_vol = sum(cc["volume"] for cc in candles[i - vol_lookback : i]) / vol_lookback
        if avg_vol == 0:
            continue
        if rsi[i] < 30 and c["volume"] > vol_mult * avg_vol and c["close"] > sma50[i]:
            entry = c["close"]
            sl = entry - 1.5 * atr[i]
            risk = entry - sl
            tp = entry + 2.0 * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "LONG",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": 2.0,
                    "strategy": "rsi_volume",
                }
            )
        if rsi[i] > 70 and c["volume"] > vol_mult * avg_vol and c["close"] < sma50[i]:
            entry = c["close"]
            sl = entry + 1.5 * atr[i]
            risk = sl - entry
            tp = entry - 2.0 * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "SHORT",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": 2.0,
                    "strategy": "rsi_volume",
                }
            )
    return signals


def strategy_heikin_ashi_trend(candles: list[dict], params: dict | None = None) -> list[dict]:
    n = len(candles)
    ha = [{"open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0} for _ in range(n)]
    ha[0]["close"] = (
        candles[0]["open"] + candles[0]["high"] + candles[0]["low"] + candles[0]["close"]
    ) / 4
    ha[0]["open"] = (candles[0]["open"] + candles[0]["close"]) / 2
    ha[0]["high"] = max(candles[0]["high"], ha[0]["open"], ha[0]["close"])
    ha[0]["low"] = min(candles[0]["low"], ha[0]["open"], ha[0]["close"])
    for i in range(1, n):
        ha[i]["close"] = (
            candles[i]["open"] + candles[i]["high"] + candles[i]["low"] + candles[i]["close"]
        ) / 4
        ha[i]["open"] = (ha[i - 1]["open"] + ha[i - 1]["close"]) / 2
        ha[i]["high"] = max(candles[i]["high"], ha[i]["open"], ha[i]["close"])
        ha[i]["low"] = min(candles[i]["low"], ha[i]["open"], ha[i]["close"])
    closes = [c["close"] for c in candles]
    ema21 = calc_ema(closes, 21)
    atr = calc_atr(candles, 14)
    signals = []
    for i in range(3, n):
        if ema21[i] is None or ema21[i - 1] is None or atr[i] is None:
            continue
        c = candles[i]
        if (
            ha[i]["close"] > ha[i]["open"]
            and ha[i - 1]["close"] > ha[i - 1]["open"]
            and ha[i - 2]["close"] > ha[i - 2]["open"]
            and ha[i]["open"] == ha[i]["low"]
            and ha[i - 1]["open"] == ha[i - 1]["low"]
            and ema21[i] > ema21[i - 1]
        ):
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "LONG",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": 2.0,
                    "strategy": "heikin_ashi",
                }
            )
        if (
            ha[i]["close"] < ha[i]["open"]
            and ha[i - 1]["close"] < ha[i - 1]["open"]
            and ha[i - 2]["close"] < ha[i - 2]["open"]
            and ha[i]["open"] == ha[i]["high"]
            and ha[i - 1]["open"] == ha[i - 1]["high"]
            and ema21[i] < ema21[i - 1]
        ):
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "SHORT",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": 2.0,
                    "strategy": "heikin_ashi",
                }
            )
    return signals


def strategy_williams_r(candles: list[dict], params: dict | None = None) -> list[dict]:
    p = params or {}
    period = p.get("period", 14)
    n = len(candles)
    willr = [None] * n
    for i in range(period - 1, n):
        w = candles[i - period + 1 : i + 1]
        hh = max(cc["high"] for cc in w)
        ll = min(cc["low"] for cc in w)
        if hh == ll:
            willr[i] = -50.0
        else:
            willr[i] = (candles[i]["close"] - hh) / (hh - ll) * 100
    sma50 = calc_sma(candles, 50)
    atr = calc_atr(candles, 14)
    signals = []
    for i in range(max(period, 50) + 1, n):
        if willr[i] is None or sma50[i] is None or atr[i] is None:
            continue
        c = candles[i]
        if willr[i] < -90 and c["close"] > sma50[i]:
            entry = c["close"]
            sl = entry - 1.5 * atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "LONG",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": 2.0,
                    "strategy": "williams_r",
                }
            )
        if willr[i] > -10 and c["close"] < sma50[i]:
            entry = c["close"]
            sl = entry + 1.5 * atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "SHORT",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": 2.0,
                    "strategy": "williams_r",
                }
            )
    return signals


def strategy_ema_rsi_filtered(candles: list[dict], params: dict | None = None) -> list[dict]:
    closes = [c["close"] for c in candles]
    ema21 = calc_ema(closes, 21)
    ema55 = calc_ema(closes, 55)
    rsi = calc_rsi(candles, 14)
    atr = calc_atr(candles, 14)
    signals = []
    for i in range(2, len(candles)):
        if ema21[i] is None or ema55[i] is None or rsi[i] is None or rsi[i - 1] is None or atr[i] is None:
            continue
        c = candles[i]
        if ema21[i] > ema55[i] and rsi[i - 1] < 30 and rsi[i] >= 30:
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "LONG",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": 2.0,
                    "strategy": "ema_rsi_filtered",
                }
            )
        if ema21[i] < ema55[i] and rsi[i - 1] > 70 and rsi[i] <= 70:
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "SHORT",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": 2.0,
                    "strategy": "ema_rsi_filtered",
                }
            )
    return signals


def strategy_adx_trend(candles: list[dict], params: dict | None = None) -> list[dict]:
    adx_vals, plus_di, minus_di = calc_adx(candles, 14)
    rsi = calc_rsi(candles, 14)
    atr = calc_atr(candles, 14)
    signals = []
    for i in range(2, len(candles)):
        if (
            adx_vals[i] is None
            or plus_di[i] is None
            or minus_di[i] is None
            or adx_vals[i - 1] is None
            or rsi[i] is None
            or atr[i] is None
        ):
            continue
        c = candles[i]
        if adx_vals[i] < 25 or adx_vals[i] <= adx_vals[i - 1]:
            continue
        if plus_di[i] > minus_di[i] and rsi[i] > 50:
            entry = c["close"]
            sl = entry - 2 * atr[i]
            risk = entry - sl
            tp = entry + 2.5 * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "LONG",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": 2.5,
                    "strategy": "adx_trend",
                }
            )
        if minus_di[i] > plus_di[i] and rsi[i] < 50:
            entry = c["close"]
            sl = entry + 2 * atr[i]
            risk = sl - entry
            tp = entry - 2.5 * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "SHORT",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": 2.5,
                    "strategy": "adx_trend",
                }
            )
    return signals


def strategy_volume_surge_reversion(candles: list[dict], params: dict | None = None) -> list[dict]:
    atr = calc_atr(candles, 14)
    sma20 = calc_sma(candles, 20)
    signals = []
    lookback = 20
    for i in range(lookback + 1, len(candles)):
        if atr[i] is None or sma20[i] is None:
            continue
        c = candles[i]
        avg_vol = sum(cc["volume"] for cc in candles[i - lookback : i]) / lookback
        if avg_vol == 0:
            continue
        prev_low = min(cc["low"] for cc in candles[i - lookback : i])
        prev_high = max(cc["high"] for cc in candles[i - lookback : i])
        if c["volume"] <= 3 * avg_vol:
            continue
        body = abs(c["close"] - c["open"])
        lower_wick = min(c["close"], c["open"]) - c["low"]
        upper_wick = c["high"] - max(c["close"], c["open"])
        if c["low"] < prev_low and c["close"] > c["open"] and lower_wick > 2 * body:
            entry = c["close"]
            sl = entry - 1.5 * atr[i]
            risk = entry - sl
            tp = entry + 2 * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "LONG",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": 2.0,
                    "strategy": "volume_surge_rev",
                }
            )
        if c["high"] > prev_high and c["close"] < c["open"] and upper_wick > 2 * body:
            entry = c["close"]
            sl = entry + 1.5 * atr[i]
            risk = sl - entry
            tp = entry - 2 * risk
            signals.append(
                {
                    "index": i,
                    "time": c["open_time"],
                    "direction": "SHORT",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": 2.0,
                    "strategy": "volume_surge_rev",
                }
            )
    return signals


def strategy_macd_ema50_trend(candles: list[dict], params: dict | None = None) -> list[dict]:
    """MACD(12,26,9) crossover with EMA(50) directional filter.
    Blog-recommended: 'foundation for most profitable forex/crypto traders.'"""
    p = params or {}
    ema_filter = p.get("ema_filter", 50)
    tp_r = p.get("tp_r", 2.0)
    atr_sl = p.get("atr_sl", 1.5)
    macd_line, signal_line, hist = calc_macd(candles)
    closes = [c["close"] for c in candles]
    ema50 = calc_ema(closes, ema_filter)
    atr = calc_atr(candles, 14)
    signals = []
    for i in range(2, len(candles)):
        if (
            macd_line[i] is None or signal_line[i] is None
            or macd_line[i - 1] is None or signal_line[i - 1] is None
            or ema50[i] is None or atr[i] is None
        ):
            continue
        c = candles[i]
        if (
            macd_line[i] > signal_line[i]
            and macd_line[i - 1] <= signal_line[i - 1]
            and c["close"] > ema50[i]
        ):
            entry = c["close"]
            sl = entry - atr_sl * atr[i]
            risk = entry - sl
            tp = entry + tp_r * risk
            signals.append({
                "index": i, "time": c["open_time"], "direction": "LONG",
                "entry": round(entry, 2), "sl": round(sl, 2),
                "tp": round(tp, 2), "rr": round(tp_r, 2),
                "strategy": "macd_ema50_trend",
            })
        if (
            macd_line[i] < signal_line[i]
            and macd_line[i - 1] >= signal_line[i - 1]
            and c["close"] < ema50[i]
        ):
            entry = c["close"]
            sl = entry + atr_sl * atr[i]
            risk = sl - entry
            tp = entry - tp_r * risk
            signals.append({
                "index": i, "time": c["open_time"], "direction": "SHORT",
                "entry": round(entry, 2), "sl": round(sl, 2),
                "tp": round(tp, 2), "rr": round(tp_r, 2),
                "strategy": "macd_ema50_trend",
            })
    return signals


def strategy_rsi14_bb_dual(candles: list[dict], params: dict | None = None) -> list[dict]:
    """RSI(14) + Bollinger Band dual confirmation with ADX regime filter.
    Blog-cited: '71% win rate during ranging conditions.'
    Only fires when ADX < 25 (non-trending) to avoid catching falling knives."""
    p = params or {}
    bb_period = p.get("bb_period", 20)
    bb_std = p.get("bb_std_mult", 2.0)
    rsi_period = p.get("rsi_period", 14)
    adx_max = p.get("adx_max", 25)
    atr_period = p.get("atr_period", 14)
    sma = calc_sma(candles, bb_period)
    std = calc_std(candles, bb_period)
    rsi = calc_rsi(candles, rsi_period)
    atr = calc_atr(candles, atr_period)
    adx_vals, plus_di, minus_di = calc_adx(candles, 14)
    signals = []
    start = max(bb_period, rsi_period, atr_period, 42) + 1
    for i in range(start, len(candles)):
        if sma[i] is None or std[i] is None or rsi[i] is None or atr[i] is None or adx_vals[i] is None:
            continue
        if adx_vals[i] >= adx_max:
            continue
        c = candles[i]
        lower = sma[i] - bb_std * std[i]
        upper = sma[i] + bb_std * std[i]
        mid = sma[i]
        if c["low"] <= lower and rsi[i] < 30:
            entry = c["close"]
            sl = lower - atr[i]
            tp = mid
            if tp > entry and entry > sl:
                rr = (tp - entry) / (entry - sl)
                if rr >= 1.0:
                    signals.append({
                        "index": i, "time": c["open_time"], "direction": "LONG",
                        "entry": round(entry, 2), "sl": round(sl, 2),
                        "tp": round(tp, 2), "rr": round(rr, 2),
                        "strategy": "rsi14_bb_dual",
                    })
        if c["high"] >= upper and rsi[i] > 70:
            entry = c["close"]
            sl = upper + atr[i]
            tp = mid
            if tp < entry and sl > entry:
                rr = (entry - tp) / (sl - entry)
                if rr >= 1.0:
                    signals.append({
                        "index": i, "time": c["open_time"], "direction": "SHORT",
                        "entry": round(entry, 2), "sl": round(sl, 2),
                        "tp": round(tp, 2), "rr": round(rr, 2),
                        "strategy": "rsi14_bb_dual",
                    })
    return signals


def strategy_false_breakout(candles: list[dict], params: dict | None = None) -> list[dict]:
    """False breakout reversal — blog data: 62% success rate, 1:2.5 R:R.
    Price breaks 20-period high/low → fails within 3 bars → counter-entry."""
    p = params or {}
    lookback = p.get("lookback", 20)
    fail_bars = p.get("fail_bars", 3)
    tp_r = p.get("tp_r", 2.5)
    atr_sl = p.get("atr_sl", 1.5)
    atr_period = p.get("atr_period", 14)
    atr = calc_atr(candles, atr_period)
    signals = []
    for i in range(lookback + fail_bars + 1, len(candles)):
        if atr[i] is None:
            continue
        window = candles[i - lookback - fail_bars: i - fail_bars]
        hi_level = max(c["high"] for c in window)
        lo_level = min(c["low"] for c in window)
        breakout_bar = candles[i - fail_bars]
        bull_break = breakout_bar["close"] > hi_level
        bear_break = breakout_bar["close"] < lo_level
        if not bull_break and not bear_break:
            continue
        c = candles[i]
        if bull_break:
            failed = all(candles[i - j]["close"] < hi_level for j in range(fail_bars))
            if failed and c["close"] < hi_level:
                entry = c["close"]
                sl = entry + atr_sl * atr[i]
                risk = sl - entry
                tp = entry - tp_r * risk
                signals.append({
                    "index": i, "time": c["open_time"], "direction": "SHORT",
                    "entry": round(entry, 2), "sl": round(sl, 2),
                    "tp": round(tp, 2), "rr": round(tp_r, 2),
                    "strategy": "false_breakout",
                })
        if bear_break:
            failed = all(candles[i - j]["close"] > lo_level for j in range(fail_bars))
            if failed and c["close"] > lo_level:
                entry = c["close"]
                sl = entry - atr_sl * atr[i]
                risk = entry - sl
                tp = entry + tp_r * risk
                signals.append({
                    "index": i, "time": c["open_time"], "direction": "LONG",
                    "entry": round(entry, 2), "sl": round(sl, 2),
                    "tp": round(tp, 2), "rr": round(tp_r, 2),
                    "strategy": "false_breakout",
                })
    return signals


EXTENDED_STRATEGIES: dict[str, tuple[str, object]] = {
    "bollinger": ("Bollinger Band Reversion", strategy_bollinger_reversion),
    "rsi2": ("RSI(2) Extreme Reversion", strategy_rsi2_extreme),
    "volume": ("Volume Breakout", strategy_volume_breakout),
    "sr": ("S/R Bounce", strategy_sr_bounce),
    "connors_rsi2": ("Connors RSI(2) mean reversion", strategy_connors_rsi2),
    "ema_crossover": ("EMA 9/21 crossover", strategy_ema_crossover),
    "keltner": ("Keltner channel reversion", strategy_keltner_reversion),
    "macd_trend": ("MACD trend momentum", strategy_macd_trend),
    "vwap": ("VWAP deviation reversion", strategy_vwap_reversion),
    "donchian": ("Donchian breakout", strategy_donchian_breakout),
    "stochastic": ("Stochastic mean reversion", strategy_stochastic_reversion),
    "supertrend": ("Supertrend ATR flip", strategy_supertrend),
    "rsi_volume": ("RSI + volume reversion", strategy_rsi_volume),
    "heikin_ashi": ("Heikin-Ashi trend rider", strategy_heikin_ashi_trend),
    "williams_r": ("Williams %R reversion", strategy_williams_r),
    "ema_rsi_filtered": ("EMA + RSI filtered", strategy_ema_rsi_filtered),
    "adx_trend": ("ADX + DI trend", strategy_adx_trend),
    "volume_surge_rev": ("Volume surge reversal", strategy_volume_surge_reversion),
    "macd_ema50_trend": ("MACD + EMA50 trend filter", strategy_macd_ema50_trend),
    "rsi14_bb_dual": ("RSI(14) + BB dual confirm (ADX<25)", strategy_rsi14_bb_dual),
    "false_breakout": ("False breakout reversal (62% WR)", strategy_false_breakout),
}


def run_single(
    symbol: str,
    strategy_key: str,
    months: int = 6,
    risk_pct: float = 0.75,
    long_only: bool = False,
    strategy_params: dict | None = None,
) -> dict | None:
    name, fn = EXTENDED_STRATEGIES[strategy_key]
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=months * 30)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(now.timestamp() * 1000)
    raw = fetch_candles(symbol, "1h", start_ms, end_ms)
    candles = parse_candles(raw)
    if not candles:
        return None
    signals = fn(candles, strategy_params or {})
    if not signals:
        return None
    signals.sort(key=lambda s: s["index"])
    acct = float(HYRO["account_size"])
    sim = HyroSimulator(account_size=acct, risk_pct=risk_pct)
    last_exit_idx = -1
    for signal in signals:
        if signal["index"] <= last_exit_idx:
            continue
        if long_only and signal.get("direction") != "LONG":
            continue
        if sim.failed:
            break
        if sim.daily_profit >= sim._consistency_cap():
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
        "symbol": symbol,
        "strategy": strategy_key,
        "strategy_name": name,
        "months": months,
        "risk_pct": risk_pct,
        "long_only": long_only,
        "passed": sim.passed,
        "failed": sim.failed,
        "fail_reason": sim.fail_reason,
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / total * 100, 1),
        "profit_factor": round(abs(total_profit / total_loss), 2) if total_loss != 0 else 999.0,
        "total_pnl": round(sim.total_pnl, 2),
        "pnl_pct": round(sim.total_pnl / sim.account_size * 100, 1),
        "final_equity": round(sim.equity, 2),
        "peak_equity": round(sim.high_water_equity, 2),
        "max_dd": round(sim.max_drawdown_from_peak, 2),
        "trading_days": len(sim.trading_days),
        "avg_win": round(total_profit / len(wins), 2) if wins else 0.0,
        "avg_loss": round(total_loss / len(losses), 2) if losses else 0.0,
        "signals_generated": len(signals),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extended Hyro-style backtester")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--risk", type=float, default=0.75)
    parser.add_argument("--strategy", default=None, help="Single strategy key")
    parser.add_argument("--long-only", action="store_true")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    strats = [args.strategy] if args.strategy else list(EXTENDED_STRATEGIES.keys())
    all_results: list[dict] = []

    for symbol in args.symbols:
        for strat_key in strats:
            name = EXTENDED_STRATEGIES[strat_key][0]
            print(f"\n{'=' * 60}\n {symbol} x {name}\n{'=' * 60}")
            try:
                result = run_single(
                    symbol, strat_key, args.months, args.risk, long_only=args.long_only
                )
                if result:
                    all_results.append(result)
                    st = "PASS" if result["passed"] else ("FAIL" if result["failed"] else "INCOMPLETE")
                    print(
                        f" {st} | trades={result['total_trades']} WR={result['win_rate']}% "
                        f"PF={result['profit_factor']} PnL=${result['total_pnl']} ({result['pnl_pct']}%) "
                        f"maxDD=${result['max_dd']} days={result['trading_days']}"
                    )
                else:
                    print(" No trades / no signals")
            except Exception as e:
                print(f" ERROR: {e}")
            time.sleep(0.12)

    all_results.sort(key=lambda r: r["total_pnl"], reverse=True)
    print(f"\n{'=' * 100}\n SUMMARY ({len(all_results)} runs)\n{'=' * 100}")
    for r in all_results[:40]:
        st = "PASS" if r["passed"] else ("FAIL" if r["failed"] else "INC")
        print(
            f" {r['symbol']:<10} {r['strategy_name'][:28]:<30} {st:<5} "
            f"tr={r['total_trades']:<4} WR={r['win_rate']:<5} PnL={r['total_pnl']:<9} maxDD={r['max_dd']}"
        )
    passed = [r for r in all_results if r["passed"]]
    print(f"\n PASSED: {len(passed)} / {len(all_results)}")

    if args.save and all_results:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "challenge_params": {k: v for k, v in HYRO.items()},
                    "results": all_results,
                },
                f,
                indent=2,
            )
        print(f"\n Saved -> {out_path}")


if __name__ == "__main__":
    main()
