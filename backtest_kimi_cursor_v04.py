#!/usr/bin/env python3
"""
Kimi_Cursor v0.04 Backtesting Validator
========================================
Mirrors the Pine Script Simpletonv0.04_Kimi_Cursor.pine logic in Python.
9 indicators, ADX regime gating, timeframe-adaptive ATR TP/SL, Dynamic voting.

Compares v0.04 (Dynamic) vs KIMI v0.01 baseline (5-indicator Multi) on every timeframe.

Usage:
    python backtest_kimi_cursor_v04.py                     # All timeframes
    python backtest_kimi_cursor_v04.py --timeframe 4h      # Single TF
    python backtest_kimi_cursor_v04.py --mode Dynamic       # Dynamic only
    python backtest_kimi_cursor_v04.py --mode Multi         # Multi only
"""

import argparse
import json
import warnings
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Timeframe profile mapping (mirrors Pine tf_secs logic)
# ---------------------------------------------------------------------------
TF_PROFILES = {
    "5m":  {"secs": 300,   "label": "SCALP",     "tp_mult": 1.25, "sl_mult": 0.75, "max_hold": 8},
    "15m": {"secs": 900,   "label": "INTRADAY",  "tp_mult": 1.5,  "sl_mult": 0.75, "max_hold": 12},
    "30m": {"secs": 1800,  "label": "SWING-ID",  "tp_mult": 2.0,  "sl_mult": 1.0,  "max_hold": 15},
    "45m": {"secs": 2700,  "label": "SWING-ID",  "tp_mult": 2.0,  "sl_mult": 1.0,  "max_hold": 15},
    "1h":  {"secs": 3600,  "label": "SWING-ID",  "tp_mult": 2.0,  "sl_mult": 1.0,  "max_hold": 15},
    "4h":  {"secs": 14400, "label": "SWING",     "tp_mult": 2.5,  "sl_mult": 1.25, "max_hold": 20},
    "1d":  {"secs": 86400, "label": "POSITION",  "tp_mult": 3.5,  "sl_mult": 1.75, "max_hold": 12},
    "2d":  {"secs": 172800,"label": "MACRO",     "tp_mult": 4.5,  "sl_mult": 2.0,  "max_hold": 8},
    "1wk": {"secs": 604800,"label": "MACRO",     "tp_mult": 4.5,  "sl_mult": 2.0,  "max_hold": 8},
    "1mo": {"secs":2592000,"label": "MACRO",     "tp_mult": 4.5,  "sl_mult": 2.0,  "max_hold": 8},
}

TESTABLE_TFS = ["15m", "30m", "45m", "1h", "4h", "1d"]

# ---------------------------------------------------------------------------
# Indicator calculations
# ---------------------------------------------------------------------------

def calc_rsi(close: pd.Series, period: int = 2) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def calc_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def calc_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    plus_dm = h.diff()
    minus_dm = -l.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    atr_val = calc_atr(df, period)
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr_val.replace(0, np.nan))
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr_val.replace(0, np.nan))
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx = dx.rolling(period).mean()
    return adx


def calc_wma(series: pd.Series, period: int) -> pd.Series:
    weights = np.arange(1, period + 1, dtype=float)
    return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)


def calc_supertrend(df: pd.DataFrame, factor: float = 3.0, period: int = 10) -> Tuple[pd.Series, pd.Series]:
    atr_val = calc_atr(df, period)
    hl2 = (df["high"] + df["low"]) / 2
    upper = hl2 + factor * atr_val
    lower = hl2 - factor * atr_val

    direction = pd.Series(1, index=df.index, dtype=int)
    st_line = pd.Series(np.nan, index=df.index)

    for i in range(1, len(df)):
        if df["close"].iloc[i] > upper.iloc[i - 1]:
            direction.iloc[i] = -1
        elif df["close"].iloc[i] < lower.iloc[i - 1]:
            direction.iloc[i] = 1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

        if direction.iloc[i] == -1:
            st_line.iloc[i] = max(lower.iloc[i], st_line.iloc[i - 1] if not np.isnan(st_line.iloc[i - 1]) else lower.iloc[i])
        else:
            st_line.iloc[i] = min(upper.iloc[i], st_line.iloc[i - 1] if not np.isnan(st_line.iloc[i - 1]) else upper.iloc[i])

    return st_line, direction


# ---------------------------------------------------------------------------
# Signal generators (mirrors Pine v0.04 logic)
# ---------------------------------------------------------------------------

def signals_rsi2(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    rsi_val = calc_rsi(df["close"], 2)
    ema200 = calc_ema(df["close"], 200)
    buy = (rsi_val < 30) & (rsi_val.shift(1) <= 30) & (df["close"] > ema200)
    sell = (rsi_val > 70) & (rsi_val.shift(1) >= 70) & (df["close"] < ema200)
    return buy, sell


def signals_supertrend(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    _, direction = calc_supertrend(df, 3.0, 10)
    buy = (direction < 0) & (direction.shift(1) > 0)
    sell = (direction > 0) & (direction.shift(1) < 0)
    return buy, sell


def signals_macd(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    fast_e = calc_ema(df["close"], 12)
    slow_e = calc_ema(df["close"], 26)
    macd_line = fast_e - slow_e
    signal_line = calc_ema(macd_line, 9)
    buy = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
    sell = (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))
    return buy, sell


def signals_triple_ema(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    f = calc_ema(df["close"], 9)
    m = calc_ema(df["close"], 21)
    s = calc_ema(df["close"], 50)
    bullish = (f > m) & (m > s)
    bearish = (f < m) & (m < s)
    buy = bullish & (~bullish.shift(1).fillna(False) | ~bullish.shift(2).fillna(False))
    sell = bearish & (~bearish.shift(1).fillna(False) | ~bearish.shift(2).fillna(False))
    return buy, sell


def signals_bb(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    basis = calc_sma(df["close"], 20)
    dev = df["close"].rolling(20).std() * 2.0
    upper = basis + dev
    lower = basis - dev
    buy = (df["close"] < lower) & (df["close"].shift(1) <= lower.shift(1))
    sell = (df["close"] > upper) & (df["close"].shift(1) >= upper.shift(1))
    return buy, sell


def signals_ichimoku(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    tenkan = (df["high"].rolling(9).max() + df["low"].rolling(9).min()) / 2
    kijun = (df["high"].rolling(26).max() + df["low"].rolling(26).min()) / 2
    span_a = ((tenkan + kijun) / 2).shift(26)
    span_b = ((df["high"].rolling(52).max() + df["low"].rolling(52).min()) / 2).shift(26)
    cloud_top = pd.concat([span_a, span_b], axis=1).max(axis=1)
    cloud_bot = pd.concat([span_a, span_b], axis=1).min(axis=1)

    tk_cross_up = (tenkan > kijun) & (tenkan.shift(1) <= kijun.shift(1))
    tk_cross_dn = (tenkan < kijun) & (tenkan.shift(1) >= kijun.shift(1))
    buy = tk_cross_up & (df["close"] > cloud_top) & (span_a > span_b)
    sell = tk_cross_dn & (df["close"] < cloud_bot) & (span_a < span_b)
    return buy, sell


def signals_hma(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    n = 50
    hma_half = calc_wma(df["close"], n // 2)
    hma_full = calc_wma(df["close"], n)
    hma_diff = 2 * hma_half - hma_full
    hma_val = calc_wma(hma_diff, int(np.floor(np.sqrt(n))))
    sma50 = calc_sma(df["close"], 50)
    rsi14 = calc_rsi(df["close"], 14)

    turn_up = (hma_val > hma_val.shift(1)) & (hma_val.shift(1) <= hma_val.shift(2))
    turn_dn = (hma_val < hma_val.shift(1)) & (hma_val.shift(1) >= hma_val.shift(2))
    buy = turn_up & (df["close"] > sma50) & (rsi14 < 75)
    sell = turn_dn & (df["close"] < sma50) & (rsi14 > 25)
    return buy, sell


def signals_sfp(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    swing_hi = df["high"].rolling(20).max().shift(1)
    swing_lo = df["low"].rolling(20).min().shift(1)
    bar_range = df["high"] - df["low"]
    wick_below = (swing_lo - df["low"]).clip(lower=0)
    wick_above = (df["high"] - swing_hi).clip(lower=0)

    buy = (df["low"] < swing_lo) & (df["close"] > swing_lo) & (df["close"] > df["open"]) & (bar_range > 0) & (wick_below / bar_range >= 0.25)
    sell = (df["high"] > swing_hi) & (df["close"] < swing_hi) & (df["close"] < df["open"]) & (bar_range > 0) & (wick_above / bar_range >= 0.25)
    return buy, sell


def signals_zscore(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    mean = calc_sma(df["close"], 20)
    std = df["close"].rolling(20).std()
    z = (df["close"] - mean) / std.replace(0, np.nan)
    buy = z < -2.0
    sell = z > 2.0
    return buy, sell


# ---------------------------------------------------------------------------
# Composite signal generators
# ---------------------------------------------------------------------------

def compute_all_signals(df: pd.DataFrame) -> Dict[str, Tuple[pd.Series, pd.Series]]:
    return {
        "RSI-2":       signals_rsi2(df),
        "SuperTrend":  signals_supertrend(df),
        "MACD":        signals_macd(df),
        "TripleEMA":   signals_triple_ema(df),
        "BB":          signals_bb(df),
        "Ichimoku":    signals_ichimoku(df),
        "HMA":         signals_hma(df),
        "SFP":         signals_sfp(df),
        "ZScore":      signals_zscore(df),
    }


TREND_STRATS = {"SuperTrend", "MACD", "TripleEMA", "Ichimoku", "HMA"}
MR_STRATS = {"RSI-2", "BB", "ZScore"}
UNIVERSAL_STRATS = {"SFP"}


def kimi_v01_multi(all_sigs: Dict, min_confirm: int = 2) -> Tuple[pd.Series, pd.Series]:
    """KIMI v0.01 baseline: 5 indicators, static voting, min 2 confirmations."""
    kimi_strats = ["RSI-2", "SuperTrend", "MACD", "TripleEMA", "BB"]
    long_sum = None
    short_sum = None
    for name in kimi_strats:
        b, s = all_sigs[name]
        if long_sum is None:
            long_sum = b.astype(int)
            short_sum = s.astype(int)
        else:
            long_sum = long_sum + b.astype(int)
            short_sum = short_sum + s.astype(int)
    return long_sum >= min_confirm, short_sum >= min_confirm


def v04_multi(all_sigs: Dict, min_confirm: int = 2) -> Tuple[pd.Series, pd.Series]:
    """v0.04 Multi: 9 indicators, static voting."""
    long_sum = None
    short_sum = None
    for name, (b, s) in all_sigs.items():
        if long_sum is None:
            long_sum = b.astype(int)
            short_sum = s.astype(int)
        else:
            long_sum = long_sum + b.astype(int)
            short_sum = short_sum + s.astype(int)
    return long_sum >= min_confirm, short_sum >= min_confirm


def v04_dynamic(df: pd.DataFrame, all_sigs: Dict) -> Tuple[pd.Series, pd.Series]:
    """v0.04 Dynamic: soft-weighted regime voting.
    TREND: trend-following 2x, MR 1x. RANGE: MR 2x, TF 1x. MIXED: all 1x.
    Threshold: 4 in TREND/RANGE (max 14/12), 3 in MIXED (max 9)."""
    adx = calc_adx(df, 14)
    is_trend = adx >= 25
    is_range = adx < 15
    is_mixed = ~is_trend & ~is_range

    long_sum = pd.Series(0, index=df.index)
    short_sum = pd.Series(0, index=df.index)

    for name, (b, s) in all_sigs.items():
        if name in TREND_STRATS:
            weight = is_trend.astype(int) * 2 + (~is_trend).astype(int) * 1
        elif name in MR_STRATS:
            weight = is_range.astype(int) * 2 + (~is_range).astype(int) * 1
        else:
            weight = pd.Series(1, index=df.index)
        long_sum = long_sum + b.astype(int) * weight
        short_sum = short_sum + s.astype(int) * weight

    threshold = pd.Series(4, index=df.index)
    threshold[is_mixed] = 3

    buy = long_sum >= threshold
    sell = short_sum >= threshold
    return buy, sell


# ---------------------------------------------------------------------------
# Backtesting engine with ATR-based TP/SL
# ---------------------------------------------------------------------------

@dataclass
class BacktestResult:
    mode: str
    timeframe: str
    num_trades: int
    win_rate: float
    profit_factor: float
    total_return: float
    max_drawdown: float
    sharpe: float
    avg_bars_held: float
    tp_sl_mode: str


def backtest_atr(df: pd.DataFrame, buy_sig: pd.Series, sell_sig: pd.Series,
                 tp_mult: float, sl_mult: float, max_hold: int,
                 commission_pct: float = 0.1) -> Dict:
    atr_val = calc_atr(df, 14)
    trades = []
    position = 0
    entry_price = 0.0
    entry_bar = 0
    entry_atr = 0.0

    for i in range(len(df)):
        c = df["close"].iloc[i]
        h = df["high"].iloc[i]
        l = df["low"].iloc[i]
        a = atr_val.iloc[i] if not np.isnan(atr_val.iloc[i]) else 0.0

        if position != 0:
            bars_held = i - entry_bar
            tp_price = entry_price + entry_atr * tp_mult * position
            sl_price = entry_price - entry_atr * sl_mult * position

            hit_tp = (position == 1 and h >= tp_price) or (position == -1 and l <= tp_price)
            hit_sl = (position == 1 and l <= sl_price) or (position == -1 and h >= sl_price)
            hit_timeout = bars_held >= max_hold
            flip = (position == 1 and sell_sig.iloc[i]) or (position == -1 and buy_sig.iloc[i])

            if hit_tp or hit_sl or hit_timeout or flip:
                if hit_tp:
                    exit_price = tp_price
                    reason = "TP"
                elif hit_sl:
                    exit_price = sl_price
                    reason = "SL"
                elif hit_timeout:
                    exit_price = c
                    reason = "TIMEOUT"
                else:
                    exit_price = c
                    reason = "FLIP"

                pnl_pct = (exit_price / entry_price - 1) * position * 100 - commission_pct * 2
                trades.append({"pnl": pnl_pct, "bars": bars_held, "reason": reason})
                position = 0

        if position == 0:
            if buy_sig.iloc[i]:
                position = 1
                entry_price = c
                entry_bar = i
                entry_atr = a
            elif sell_sig.iloc[i]:
                position = -1
                entry_price = c
                entry_bar = i
                entry_atr = a

    if not trades:
        return {"num_trades": 0, "win_rate": 0.0, "profit_factor": 0.0,
                "total_return": 0.0, "max_drawdown": 0.0, "sharpe": 0.0, "avg_bars": 0.0}

    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_win = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.001
    equity = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    max_dd = abs(dd.min()) if len(dd) > 0 else 0.0
    pnl_arr = np.array(pnls)
    sharpe = (pnl_arr.mean() / pnl_arr.std() * np.sqrt(252)) if pnl_arr.std() > 0 else 0.0

    return {
        "num_trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 2),
        "profit_factor": round(gross_win / gross_loss, 3),
        "total_return": round(float(sum(pnls)), 2),
        "max_drawdown": round(float(max_dd), 2),
        "sharpe": round(float(sharpe), 3),
        "avg_bars": round(float(np.mean([t["bars"] for t in trades])), 1),
    }


def backtest_smart_pct(df: pd.DataFrame, buy_sig: pd.Series, sell_sig: pd.Series,
                       tp_mult: float = 1.5, sl_mult: float = 1.0,
                       commission_pct: float = 0.1) -> Dict:
    """Smart TP/SL: per-bar ATR% * tp_mult / sl_mult. atrPct = ATR(14)/close*100."""
    atr14 = calc_atr(df, 14)
    atr_pct = (atr14 / df["close"].replace(0, np.nan) * 100).fillna(2.0)  # fallback 2% -> 3%/2% equiv
    tp_pct_series = atr_pct * tp_mult
    sl_pct_series = atr_pct * sl_mult

    trades = []
    position = 0
    entry_price = 0.0
    entry_bar = 0

    for i in range(len(df)):
        c = df["close"].iloc[i]
        tp_pct = float(tp_pct_series.iloc[i])
        sl_pct = float(sl_pct_series.iloc[i])
        if position != 0:
            bars_held = i - entry_bar
            pnl = (c / entry_price - 1) * position * 100
            hit_tp = pnl >= tp_pct
            hit_sl = pnl <= -sl_pct
            flip = (position == 1 and sell_sig.iloc[i]) or (position == -1 and buy_sig.iloc[i])
            if hit_tp or hit_sl or flip:
                net = pnl - commission_pct * 2
                trades.append({"pnl": net, "bars": bars_held,
                               "reason": "TP" if hit_tp else "SL" if hit_sl else "FLIP"})
                position = 0
        if position == 0:
            if buy_sig.iloc[i]:
                position = 1
                entry_price = c
                entry_bar = i
            elif sell_sig.iloc[i]:
                position = -1
                entry_price = c
                entry_bar = i

    if not trades:
        return {"num_trades": 0, "win_rate": 0.0, "profit_factor": 0.0,
                "total_return": 0.0, "max_drawdown": 0.0, "sharpe": 0.0, "avg_bars": 0.0}
    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_win = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.001
    equity = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    max_dd = abs(dd.min()) if len(dd) > 0 else 0.0
    pnl_arr = np.array(pnls)
    sharpe = (pnl_arr.mean() / pnl_arr.std() * np.sqrt(252)) if pnl_arr.std() > 0 else 0.0
    return {
        "num_trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 2),
        "profit_factor": round(gross_win / gross_loss, 3),
        "total_return": round(float(sum(pnls)), 2),
        "max_drawdown": round(float(max_dd), 2),
        "sharpe": round(float(sharpe), 3),
        "avg_bars": round(float(np.mean([t["bars"] for t in trades])), 1),
    }


def backtest_fixed_pct(df: pd.DataFrame, buy_sig: pd.Series, sell_sig: pd.Series,
                       tp_pct: float = 3.0, sl_pct: float = 2.0,
                       commission_pct: float = 0.1) -> Dict:
    """KIMI v0.01 style: fixed percentage TP/SL, no max hold."""
    trades = []
    position = 0
    entry_price = 0.0
    entry_bar = 0

    for i in range(len(df)):
        c = df["close"].iloc[i]
        if position != 0:
            bars_held = i - entry_bar
            pnl = (c / entry_price - 1) * position * 100

            hit_tp = pnl >= tp_pct
            hit_sl = pnl <= -sl_pct
            flip = (position == 1 and sell_sig.iloc[i]) or (position == -1 and buy_sig.iloc[i])

            if hit_tp or hit_sl or flip:
                net = pnl - commission_pct * 2
                trades.append({"pnl": net, "bars": bars_held,
                               "reason": "TP" if hit_tp else "SL" if hit_sl else "FLIP"})
                position = 0

        if position == 0:
            if buy_sig.iloc[i]:
                position = 1
                entry_price = c
                entry_bar = i
            elif sell_sig.iloc[i]:
                position = -1
                entry_price = c
                entry_bar = i

    if not trades:
        return {"num_trades": 0, "win_rate": 0.0, "profit_factor": 0.0,
                "total_return": 0.0, "max_drawdown": 0.0, "sharpe": 0.0, "avg_bars": 0.0}

    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_win = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.001
    equity = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    max_dd = abs(dd.min()) if len(dd) > 0 else 0.0
    pnl_arr = np.array(pnls)
    sharpe = (pnl_arr.mean() / pnl_arr.std() * np.sqrt(252)) if pnl_arr.std() > 0 else 0.0

    return {
        "num_trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 2),
        "profit_factor": round(gross_win / gross_loss, 3),
        "total_return": round(float(sum(pnls)), 2),
        "max_drawdown": round(float(max_dd), 2),
        "sharpe": round(float(sharpe), 3),
        "avg_bars": round(float(np.mean([t["bars"] for t in trades])), 1),
    }


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_ohlc(symbol: str, tf: str, days: int = 729) -> Optional[pd.DataFrame]:
    """Fetch OHLC for any symbol. tf in 5m,15m,30m,45m,1h,4h,1d,1wk,1mo."""
    interval_map = {
        "5m": "5m", "15m": "15m", "30m": "30m", "45m": "1h",
        "1h": "1h", "4h": "1h", "1d": "1d", "1wk": "1wk", "1mo": "1mo",
    }
    raw_interval = interval_map.get(tf, "1d")
    max_days = {"5m": 59, "15m": 59, "30m": 59, "1h": 729, "1d": 3650, "1wk": 3650, "1mo": 3650}
    limit = min(days, max_days.get(raw_interval, days))
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=f"{limit}d", interval=raw_interval)
    if df is None or len(df) == 0:
        return None
    df.columns = [c.lower() for c in df.columns]
    df.drop(columns=["stock splits", "dividends"], errors="ignore", inplace=True)
    if tf == "4h" and raw_interval == "1h":
        df = df.resample("4h").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    elif tf == "45m" and raw_interval == "1h":
        df = df.resample("45min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    elif tf == "2d" and raw_interval == "1d":
        df = df.resample("2D").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    df = df.dropna(subset=["close"])
    return df


def fetch_btcusd(tf: str, days: int = 700) -> Optional[pd.DataFrame]:
    interval_map = {
        "5m": "5m", "15m": "15m", "30m": "30m", "45m": "1h",
        "1h": "1h", "4h": "1h", "1d": "1d", "1wk": "1wk", "1mo": "1mo",
    }
    raw_interval = interval_map.get(tf, "1d")

    max_days = {"5m": 59, "15m": 59, "30m": 59, "1h": 729, "1d": 3650, "1wk": 3650, "1mo": 3650}
    limit = min(days, max_days.get(raw_interval, days))

    ticker = yf.Ticker("BTC-USD")
    df = ticker.history(period=f"{limit}d", interval=raw_interval)

    if df is None or len(df) == 0:
        return None

    df.columns = [c.lower() for c in df.columns]
    if "stock splits" in df.columns:
        df.drop(columns=["stock splits", "dividends"], errors="ignore", inplace=True)

    if tf == "4h" and raw_interval == "1h":
        df = df.resample("4h").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    elif tf == "45m" and raw_interval == "1h":
        df = df.resample("45min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    elif tf == "2d" and raw_interval == "1d":
        df = df.resample("2D").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()

    df = df.dropna(subset=["close"])
    return df


# ---------------------------------------------------------------------------
# Main comparison engine
# ---------------------------------------------------------------------------

def run_comparison(tf: str, verbose: bool = False) -> Optional[Dict]:
    print(f"\n{'='*60}")
    print(f"  BTCUSD {tf.upper()} — Kimi_Cursor v0.04 Validator")
    print(f"{'='*60}")

    df = fetch_btcusd(tf)
    if df is None or len(df) < 200:
        print(f"  [!] Insufficient data for {tf} ({len(df) if df is not None else 0} bars)")
        return None

    print(f"  Data: {len(df)} bars, {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")

    all_sigs = compute_all_signals(df)
    profile = TF_PROFILES.get(tf, TF_PROFILES["1d"])

    results = {}

    # 1. KIMI v0.01 baseline (5-indicator, fixed 3%/2% TP/SL)
    kimi_buy, kimi_sell = kimi_v01_multi(all_sigs, min_confirm=2)
    kimi_res = backtest_fixed_pct(df, kimi_buy, kimi_sell, tp_pct=3.0, sl_pct=2.0)
    kimi_res["tp_sl_mode"] = "Fixed 3%/2%"
    results["KIMI v0.01 Multi"] = kimi_res

    # 2. v0.04 Hybrid: 9-indicator Multi(3) + Hybrid TP/SL (fixed <=1H, ATR 4H+)
    multi_buy, multi_sell = v04_multi(all_sigs, min_confirm=3)
    tf_secs = profile["secs"]
    if tf_secs > 3600:
        hybrid_res = backtest_atr(df, multi_buy, multi_sell, profile["tp_mult"], profile["sl_mult"], profile["max_hold"])
        hybrid_res["tp_sl_mode"] = f"ATR {profile['tp_mult']}x/{profile['sl_mult']}x"
    else:
        hybrid_res = backtest_fixed_pct(df, multi_buy, multi_sell, tp_pct=3.0, sl_pct=2.0)
        hybrid_res["tp_sl_mode"] = "Fixed 3%/2%"
    results["v0.04 Hybrid"] = hybrid_res

    # 3. v0.04 Dynamic (soft-weighted, same Hybrid TP/SL)
    dyn_buy, dyn_sell = v04_dynamic(df, all_sigs)
    if tf_secs > 3600:
        dyn_res = backtest_atr(df, dyn_buy, dyn_sell, profile["tp_mult"], profile["sl_mult"], profile["max_hold"])
        dyn_res["tp_sl_mode"] = f"ATR {profile['tp_mult']}x/{profile['sl_mult']}x + Regime"
    else:
        dyn_res = backtest_fixed_pct(df, dyn_buy, dyn_sell, tp_pct=3.0, sl_pct=2.0)
        dyn_res["tp_sl_mode"] = "Fixed 3%/2% + Regime"
    results["v0.04 Dynamic"] = dyn_res

    # 4. Individual strategies (v0.04 ATR TP/SL)
    if verbose:
        for name, (b, s) in all_sigs.items():
            r = backtest_atr(df, b, s, profile["tp_mult"], profile["sl_mult"], profile["max_hold"])
            results[f"  {name}"] = r

    # Print results
    print(f"\n  {'Mode':<22} {'Trades':>7} {'WR%':>7} {'PF':>7} {'Return%':>9} {'MaxDD%':>8} {'Sharpe':>7} {'TP/SL'}")
    print(f"  {'-'*90}")
    for mode, r in results.items():
        wr_color = r["win_rate"]
        pf = r["profit_factor"]
        ret = r["total_return"]
        indicator = "+" if ret > 0 else ""
        print(f"  {mode:<22} {r['num_trades']:>7} {wr_color:>6.1f}% {pf:>7.3f} {indicator}{ret:>8.2f}% {r['max_drawdown']:>7.2f}% {r['sharpe']:>7.3f}  {r.get('tp_sl_mode', '')}")

    return {"timeframe": tf, "profile": profile["label"], "bars": len(df), "results": results}


def main():
    parser = argparse.ArgumentParser(description="Kimi_Cursor v0.04 Backtesting Validator")
    parser.add_argument("--timeframe", type=str, help="Single timeframe (e.g. 4h)")
    parser.add_argument("--verbose", action="store_true", help="Show individual strategy results")
    parser.add_argument("--save", action="store_true", help="Save results to JSON")
    args = parser.parse_args()

    print("=" * 70)
    print("  KIMI_CURSOR v0.04 BACKTESTING VALIDATOR")
    print("  Comparing: KIMI v0.01 (baseline) vs v0.04 Multi vs v0.04 Dynamic")
    print("=" * 70)

    tfs = [args.timeframe] if args.timeframe else TESTABLE_TFS
    all_results = []

    for tf in tfs:
        r = run_comparison(tf, verbose=args.verbose)
        if r:
            all_results.append(r)

    # Final summary
    print(f"\n\n{'='*70}")
    print("  SUMMARY: v0.04 Dynamic vs KIMI v0.01 Baseline")
    print(f"{'='*70}")
    print(f"\n  {'TF':<6} {'Profile':<12} | {'KIMI v0.01':^30} | {'v0.04 Dynamic':^30} | {'Delta'}")
    print(f"  {'':6} {'':12} | {'Trades WR%    PF   Return%':^30} | {'Trades WR%    PF   Return%':^30} |")
    print(f"  {'-'*100}")

    v04_wins = 0
    kimi_wins = 0
    for r in all_results:
        tf = r["timeframe"]
        prof = r["profile"]
        kimi = r["results"].get("KIMI v0.01 Multi", {})
        dyn = r["results"].get("v0.04 Dynamic", {})
        if not kimi or not dyn:
            continue

        k_str = f"{kimi['num_trades']:>4} {kimi['win_rate']:>5.1f}% {kimi['profit_factor']:>5.3f} {kimi['total_return']:>+8.2f}%"
        d_str = f"{dyn['num_trades']:>4} {dyn['win_rate']:>5.1f}% {dyn['profit_factor']:>5.3f} {dyn['total_return']:>+8.2f}%"

        pf_delta = dyn["profit_factor"] - kimi["profit_factor"]
        ret_delta = dyn["total_return"] - kimi["total_return"]
        winner = "v0.04" if dyn["profit_factor"] > kimi["profit_factor"] else "KIMI"
        if dyn["profit_factor"] > kimi["profit_factor"]:
            v04_wins += 1
        else:
            kimi_wins += 1

        print(f"  {tf:<6} {prof:<12} | {k_str} | {d_str} | PF {pf_delta:>+.3f} ({winner})")

    total = v04_wins + kimi_wins
    if total > 0:
        print(f"\n  v0.04 Dynamic wins: {v04_wins}/{total} timeframes ({v04_wins/total*100:.0f}%)")
        print(f"  KIMI v0.01 wins:   {kimi_wins}/{total} timeframes ({kimi_wins/total*100:.0f}%)")

    if args.save and all_results:
        out = Path("backtest_results/kimi_cursor_v04_comparison.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        serializable = []
        for r in all_results:
            entry = {"timeframe": r["timeframe"], "profile": r["profile"], "bars": r["bars"]}
            for mode, metrics in r["results"].items():
                entry[mode.strip()] = metrics
            serializable.append(entry)
        out.write_text(json.dumps(serializable, indent=2))
        print(f"\n  Results saved to {out}")


if __name__ == "__main__":
    main()
