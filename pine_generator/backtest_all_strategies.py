#!/usr/bin/env python3
"""
PINE SCRIPT STRATEGY BACKTESTER -- All 14 Strategies
======================================================
Walk-forward backtest for every strategy in Elton's Predictions Pine Script.

Runs each strategy on multiple symbols with realistic transaction costs,
splits data into in-sample (70%) and out-of-sample (30%) periods,
and calculates full statistical validation (win rate, Sharpe, profit factor,
max drawdown, p-value).

Output:
  pine_generator/data/{strategy_name}_backtest.json  -- per-strategy results
  pine_generator/data/backtest_summary.json          -- combined summary

Usage:
  python pine_generator/backtest_all_strategies.py
  python pine_generator/backtest_all_strategies.py --strategies macd_momentum,ema_crossover
  python pine_generator/backtest_all_strategies.py --symbols SPY,QQQ
  python pine_generator/backtest_all_strategies.py --period 3y
"""

import json
import math
import sys
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Transaction Costs (realistic, per side)
# ---------------------------------------------------------------------------
TRANSACTION_COSTS = {
    "crypto": 0.001,    # 0.1% maker+taker combined
    "equity": 0.0005,   # 0.05% (commission + spread)
    "forex":  0.0003,   # 0.03% (spread cost)
}

# ---------------------------------------------------------------------------
# Test Symbols
# ---------------------------------------------------------------------------
DEFAULT_SYMBOLS = {
    # Crypto - majors
    "BTC-USD":   {"name": "Bitcoin",       "category": "crypto"},
    "ETH-USD":   {"name": "Ethereum",      "category": "crypto"},
    "SOL-USD":   {"name": "Solana",        "category": "crypto"},
    "DOGE-USD":  {"name": "Dogecoin",      "category": "crypto"},
    "XRP-USD":   {"name": "XRP",           "category": "crypto"},
    "ADA-USD":   {"name": "Cardano",       "category": "crypto"},
    "AVAX-USD":  {"name": "Avalanche",     "category": "crypto"},
    "LINK-USD":  {"name": "Chainlink",     "category": "crypto"},
    "MATIC-USD": {"name": "Polygon",       "category": "crypto"},
    "DOT-USD":   {"name": "Polkadot",      "category": "crypto"},
    # Equities
    "SPY":       {"name": "S&P 500 ETF",   "category": "equity"},
    "QQQ":       {"name": "Nasdaq 100",    "category": "equity"},
    "AAPL":      {"name": "Apple Inc",     "category": "equity"},
    # Forex
    "EURUSD=X":  {"name": "EUR/USD",       "category": "forex"},
    "GBPUSD=X":  {"name": "GBP/USD",       "category": "forex"},
    "USDJPY=X":  {"name": "USD/JPY",       "category": "forex"},
    "AUDUSD=X":  {"name": "AUD/USD",       "category": "forex"},
    "USDCAD=X":  {"name": "USD/CAD",       "category": "forex"},
    "NZDUSD=X":  {"name": "NZD/USD",       "category": "forex"},
    "USDCHF=X":  {"name": "USD/CHF",       "category": "forex"},
    "EURJPY=X":  {"name": "EUR/JPY",       "category": "forex"},
    "GBPJPY=X":  {"name": "GBP/JPY",       "category": "forex"},
    "EURGBP=X":  {"name": "EUR/GBP",       "category": "forex"},
}

# Which symbols each strategy should be tested on
STRATEGY_SYMBOLS = {
    "connors_rsi2":         ["SPY", "QQQ", "BTC-USD", "ETH-USD", "SOL-USD",
                             "DOGE-USD", "XRP-USD", "ADA-USD", "AVAX-USD",
                             "LINK-USD", "MATIC-USD", "DOT-USD",
                             "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"],
    "vix_spike_reversal":   ["SPY"],
    "macd_momentum":        ["BTC-USD", "ETH-USD", "SPY", "QQQ"],
    "ema_crossover":        ["BTC-USD", "ETH-USD", "SPY", "QQQ", "AAPL"],
    "ichimoku_cloud":       ["BTC-USD", "ETH-USD", "SPY"],
    "bollinger_squeeze":    ["BTC-USD", "ETH-USD", "SPY", "QQQ"],
    "vwap_reversion":       ["BTC-USD", "ETH-USD", "SPY", "QQQ"],
    "rsi_divergence":       ["BTC-USD", "ETH-USD", "SPY", "QQQ"],
    "supertrend":           ["BTC-USD", "ETH-USD", "SOL-USD", "SPY", "QQQ"],
    "sfp":                  ["BTC-USD", "ETH-USD", "SPY"],
    "bos":                  ["BTC-USD", "ETH-USD", "SPY", "QQQ"],
    "liquidation_cascade":  ["BTC-USD", "ETH-USD", "SOL-USD"],
    "momentum_crash_hedge": ["BTC-USD", "SPY", "QQQ"],
    "multi_strategy":       ["BTC-USD", "ETH-USD", "SPY", "QQQ"],
    "currency_momentum":    ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X",
                             "NZDUSD=X", "USDCHF=X", "EURJPY=X", "GBPJPY=X", "EURGBP=X",
                             "BTC-USD", "ETH-USD", "SOL-USD", "SPY", "QQQ"],
    "fx_value_ppp":         ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X",
                             "NZDUSD=X", "USDCHF=X"],
    "trend_following_vol":  ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X",
                             "NZDUSD=X", "USDCHF=X", "EURJPY=X", "GBPJPY=X", "EURGBP=X",
                             "BTC-USD", "ETH-USD", "SOL-USD", "SPY", "QQQ"],
}


# ===========================================================================
# INDICATORS
# ===========================================================================

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def bollinger_bands(close: pd.Series, period: int = 20, std_mult: float = 2.0):
    """Returns (upper, middle, lower, bandwidth)."""
    mid = sma(close, period)
    std = close.rolling(period).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    bandwidth = (upper - lower) / mid
    return upper, mid, lower, bandwidth


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Returns (macd_line, signal_line, histogram)."""
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.Series:
    """
    Supertrend indicator. Returns a Series of direction:
      1 = uptrend (bullish), -1 = downtrend (bearish)
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    atr_val = atr(df, period)

    hl2 = (high + low) / 2.0
    upper_band = hl2 + multiplier * atr_val
    lower_band = hl2 - multiplier * atr_val

    direction = pd.Series(1, index=df.index, dtype=float)
    final_upper = upper_band.copy()
    final_lower = lower_band.copy()

    for i in range(1, len(df)):
        if not np.isnan(final_lower.iloc[i - 1]):
            if lower_band.iloc[i] > final_lower.iloc[i - 1]:
                final_lower.iloc[i] = lower_band.iloc[i]
            else:
                final_lower.iloc[i] = final_lower.iloc[i - 1]

        if not np.isnan(final_upper.iloc[i - 1]):
            if upper_band.iloc[i] < final_upper.iloc[i - 1]:
                final_upper.iloc[i] = upper_band.iloc[i]
            else:
                final_upper.iloc[i] = final_upper.iloc[i - 1]

        if direction.iloc[i - 1] == 1:
            if close.iloc[i] < final_lower.iloc[i]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = 1
        else:
            if close.iloc[i] > final_upper.iloc[i]:
                direction.iloc[i] = 1
            else:
                direction.iloc[i] = -1

    return direction


def ichimoku(df: pd.DataFrame, tenkan_period: int = 9, kijun_period: int = 26,
             senkou_b_period: int = 52):
    """
    Returns (tenkan, kijun, senkou_a, senkou_b).
    senkou_a and senkou_b are NOT displaced (we compare to current price).
    """
    high = df["High"]
    low = df["Low"]

    tenkan = (high.rolling(tenkan_period).max() + low.rolling(tenkan_period).min()) / 2
    kijun = (high.rolling(kijun_period).max() + low.rolling(kijun_period).min()) / 2
    senkou_a = (tenkan + kijun) / 2
    senkou_b = (high.rolling(senkou_b_period).max() + low.rolling(senkou_b_period).min()) / 2

    return tenkan, kijun, senkou_a, senkou_b


def keltner_channels(df: pd.DataFrame, ema_period: int = 20, atr_period: int = 10,
                     multiplier: float = 1.5):
    """Returns (upper, middle, lower)."""
    mid = ema(df["Close"], ema_period)
    atr_val = atr(df, atr_period)
    upper = mid + multiplier * atr_val
    lower = mid - multiplier * atr_val
    return upper, mid, lower


def vwap(df: pd.DataFrame) -> pd.Series:
    """
    Cumulative VWAP (resets daily in real trading; here we use rolling 20-bar VWAP
    as a proxy for daily bars).
    """
    typical = (df["High"] + df["Low"] + df["Close"]) / 3.0
    volume = df["Volume"].replace(0, np.nan)
    cum_tp_vol = (typical * volume).rolling(20).sum()
    cum_vol = volume.rolling(20).sum()
    return cum_tp_vol / cum_vol


def ewma_volatility(returns: pd.Series, span: int = 60) -> pd.Series:
    """EWMA volatility (Daniel & Moskowitz 2016 style)."""
    return returns.ewm(span=span, adjust=False).std()


def find_swing_highs(high: pd.Series, lookback: int = 5) -> pd.Series:
    """Mark swing highs: higher than `lookback` bars on each side."""
    result = pd.Series(np.nan, index=high.index)
    for i in range(lookback, len(high) - lookback):
        window_left = high.iloc[i - lookback:i]
        window_right = high.iloc[i + 1:i + 1 + lookback]
        if high.iloc[i] >= window_left.max() and high.iloc[i] >= window_right.max():
            result.iloc[i] = high.iloc[i]
    return result


def find_swing_lows(low: pd.Series, lookback: int = 5) -> pd.Series:
    """Mark swing lows: lower than `lookback` bars on each side."""
    result = pd.Series(np.nan, index=low.index)
    for i in range(lookback, len(low) - lookback):
        window_left = low.iloc[i - lookback:i]
        window_right = low.iloc[i + 1:i + 1 + lookback]
        if low.iloc[i] <= window_left.min() and low.iloc[i] <= window_right.min():
            result.iloc[i] = low.iloc[i]
    return result


# ===========================================================================
# STRATEGY IMPLEMENTATIONS
# ===========================================================================
# Each strategy function takes a DataFrame and an index i, returns:
#   ("BUY", tp, sl)  or  ("SELL", tp, sl)  or  None
# All indicators should be pre-computed and passed via the df or a dict.

class StrategyRunner:
    """Holds pre-computed indicators and runs signal checks for each bar."""

    def __init__(self, df: pd.DataFrame, category: str = "crypto"):
        self.df = df
        self.category = category
        self.close = df["Close"]
        self.high = df["High"]
        self.low = df["Low"]
        self.volume = df["Volume"]
        self.n = len(df)

        # Pre-compute indicators
        self.sma200 = sma(self.close, 200)
        self.sma50 = sma(self.close, 50)
        self.ema9 = ema(self.close, 9)
        self.ema21 = ema(self.close, 21)
        self.ema50 = ema(self.close, 50)
        self.ema200 = ema(self.close, 200)
        self.rsi2 = rsi(self.close, 2)
        self.rsi14 = rsi(self.close, 14)
        self.atr14 = atr(df, 14)
        self.macd_line, self.macd_signal, self.macd_hist = macd(self.close)
        self.bb_upper, self.bb_mid, self.bb_lower, self.bb_width = bollinger_bands(self.close)
        self.kc_upper, self.kc_mid, self.kc_lower = keltner_channels(df)
        self.vwap_series = vwap(df)
        self.tenkan, self.kijun, self.senkou_a, self.senkou_b = ichimoku(df)
        self.supertrend_dir = supertrend(df, 10, 3.0)
        self.swing_highs = find_swing_highs(self.high, 5)
        self.swing_lows = find_swing_lows(self.low, 5)
        self.vol_sma20 = sma(self.volume.astype(float), 20)
        self.returns = self.close.pct_change()
        self.ewma_vol = ewma_volatility(self.returns, 60)
        self.vwap_std = (self.close - self.vwap_series).rolling(20).std()

    def get_atr(self, i: int) -> float:
        val = self.atr14.iloc[i]
        return float(val) if not np.isnan(val) else float(self.close.iloc[i]) * 0.02

    def _nan_safe(self, val) -> float:
        """Convert to float, return NaN if input is NaN."""
        if val is None:
            return np.nan
        f = float(val)
        return f

    # ------------------------------------------------------------------
    # 1. Connors RSI-2
    # ------------------------------------------------------------------
    def connors_rsi2(self, i: int):
        """BUY when RSI-2 < 5 and price > SMA200. EXIT when RSI-2 > 65 or 10 days."""
        price = float(self.close.iloc[i])
        rsi2_val = self._nan_safe(self.rsi2.iloc[i])
        sma200_val = self._nan_safe(self.sma200.iloc[i])
        if np.isnan(rsi2_val) or np.isnan(sma200_val):
            return None
        if rsi2_val < 5.0 and price > sma200_val:
            atr_val = self.get_atr(i)
            tp = price + 3.0 * atr_val
            sl = price - 1.5 * atr_val
            return ("BUY", tp, sl)
        return None

    def connors_rsi2_exit(self, i: int, entry_bar: int) -> bool:
        rsi2_val = self._nan_safe(self.rsi2.iloc[i])
        if np.isnan(rsi2_val):
            return (i - entry_bar) >= 10
        return rsi2_val > 65.0 or (i - entry_bar) >= 10

    # ------------------------------------------------------------------
    # 2. VIX Spike Reversal (equity only -- uses price drop as proxy)
    # ------------------------------------------------------------------
    def vix_spike_reversal(self, i: int):
        """
        Proxy for VIX spike: 3-day drawdown > 3% from recent high + RSI2 < 20.
        In production, this uses ^VIX data. For backtesting across symbols,
        we use a price-based fear proxy.
        """
        if i < 20:
            return None
        price = float(self.close.iloc[i])
        rsi2_val = self._nan_safe(self.rsi2.iloc[i])
        if np.isnan(rsi2_val):
            return None
        recent_high = float(self.high.iloc[i - 10:i].max())
        drawdown = (price - recent_high) / recent_high

        if drawdown < -0.03 and rsi2_val < 20.0:
            atr_val = self.get_atr(i)
            tp = price + 2.0 * atr_val
            sl = price - 1.5 * atr_val
            return ("BUY", tp, sl)
        return None

    def vix_spike_exit(self, i: int, entry_bar: int) -> bool:
        rsi2_val = self._nan_safe(self.rsi2.iloc[i])
        if np.isnan(rsi2_val):
            return (i - entry_bar) >= 10
        return rsi2_val > 65.0 or (i - entry_bar) >= 10

    # ------------------------------------------------------------------
    # 3. MACD Momentum
    # ------------------------------------------------------------------
    def macd_momentum(self, i: int):
        """
        BUY: MACD crosses above signal line AND RSI(14) > 40
        SELL: MACD crosses below signal line AND RSI(14) < 60
        """
        if i < 1:
            return None
        macd_now = self._nan_safe(self.macd_line.iloc[i])
        macd_prev = self._nan_safe(self.macd_line.iloc[i - 1])
        sig_now = self._nan_safe(self.macd_signal.iloc[i])
        sig_prev = self._nan_safe(self.macd_signal.iloc[i - 1])
        rsi_val = self._nan_safe(self.rsi14.iloc[i])
        if any(np.isnan(v) for v in [macd_now, macd_prev, sig_now, sig_prev, rsi_val]):
            return None

        price = float(self.close.iloc[i])
        atr_val = self.get_atr(i)

        # Bullish crossover
        if macd_prev <= sig_prev and macd_now > sig_now and rsi_val > 40:
            tp = price + 2.5 * atr_val
            sl = price - 1.5 * atr_val
            return ("BUY", tp, sl)

        # Bearish crossover
        if macd_prev >= sig_prev and macd_now < sig_now and rsi_val < 60:
            tp = price - 2.5 * atr_val
            sl = price + 1.5 * atr_val
            return ("SELL", tp, sl)

        return None

    def macd_exit(self, i: int, entry_bar: int) -> bool:
        return (i - entry_bar) >= 15

    # ------------------------------------------------------------------
    # 4. EMA Crossover
    # ------------------------------------------------------------------
    def ema_crossover(self, i: int):
        """
        BUY: EMA9 crosses above EMA21 AND price > EMA50
        SELL: EMA9 crosses below EMA21 AND price < EMA50
        """
        if i < 1:
            return None
        ema9_now = self._nan_safe(self.ema9.iloc[i])
        ema9_prev = self._nan_safe(self.ema9.iloc[i - 1])
        ema21_now = self._nan_safe(self.ema21.iloc[i])
        ema21_prev = self._nan_safe(self.ema21.iloc[i - 1])
        ema50_now = self._nan_safe(self.ema50.iloc[i])
        if any(np.isnan(v) for v in [ema9_now, ema9_prev, ema21_now, ema21_prev, ema50_now]):
            return None

        price = float(self.close.iloc[i])
        atr_val = self.get_atr(i)

        # Bullish crossover
        if ema9_prev <= ema21_prev and ema9_now > ema21_now and price > ema50_now:
            tp = price + 3.0 * atr_val
            sl = price - 1.5 * atr_val
            return ("BUY", tp, sl)

        # Bearish crossover
        if ema9_prev >= ema21_prev and ema9_now < ema21_now and price < ema50_now:
            tp = price - 3.0 * atr_val
            sl = price + 1.5 * atr_val
            return ("SELL", tp, sl)

        return None

    def ema_exit(self, i: int, entry_bar: int, direction: str) -> bool:
        """Exit on reverse cross or time."""
        if (i - entry_bar) >= 20:
            return True
        ema9_now = self._nan_safe(self.ema9.iloc[i])
        ema21_now = self._nan_safe(self.ema21.iloc[i])
        if np.isnan(ema9_now) or np.isnan(ema21_now):
            return False
        if direction == "BUY" and ema9_now < ema21_now:
            return True
        if direction == "SELL" and ema9_now > ema21_now:
            return True
        return False

    # ------------------------------------------------------------------
    # 5. Ichimoku Cloud
    # ------------------------------------------------------------------
    def ichimoku_cloud(self, i: int):
        """
        BUY: Tenkan crosses above Kijun AND price above cloud (both senkou_a and senkou_b)
              AND future cloud is green (senkou_a > senkou_b)
        """
        if i < 1:
            return None
        tenkan_now = self._nan_safe(self.tenkan.iloc[i])
        tenkan_prev = self._nan_safe(self.tenkan.iloc[i - 1])
        kijun_now = self._nan_safe(self.kijun.iloc[i])
        kijun_prev = self._nan_safe(self.kijun.iloc[i - 1])
        sa = self._nan_safe(self.senkou_a.iloc[i])
        sb = self._nan_safe(self.senkou_b.iloc[i])
        if any(np.isnan(v) for v in [tenkan_now, tenkan_prev, kijun_now, kijun_prev, sa, sb]):
            return None

        price = float(self.close.iloc[i])
        cloud_top = max(sa, sb)
        cloud_bottom = min(sa, sb)
        atr_val = self.get_atr(i)

        # Bullish: TK cross above cloud + future cloud green
        if (tenkan_prev <= kijun_prev and tenkan_now > kijun_now
                and price > cloud_top and sa > sb):
            tp = price + 3.0 * atr_val
            sl = price - 2.0 * atr_val
            return ("BUY", tp, sl)

        # Bearish: TK cross below cloud + future cloud red
        if (tenkan_prev >= kijun_prev and tenkan_now < kijun_now
                and price < cloud_bottom and sa < sb):
            tp = price - 3.0 * atr_val
            sl = price + 2.0 * atr_val
            return ("SELL", tp, sl)

        return None

    def ichimoku_exit(self, i: int, entry_bar: int, direction: str) -> bool:
        if (i - entry_bar) >= 25:
            return True
        tenkan_now = self._nan_safe(self.tenkan.iloc[i])
        kijun_now = self._nan_safe(self.kijun.iloc[i])
        if np.isnan(tenkan_now) or np.isnan(kijun_now):
            return False
        if direction == "BUY" and tenkan_now < kijun_now:
            return True
        if direction == "SELL" and tenkan_now > kijun_now:
            return True
        return False

    # ------------------------------------------------------------------
    # 6. Bollinger Squeeze
    # ------------------------------------------------------------------
    def bollinger_squeeze(self, i: int):
        """
        Squeeze: BB width < 20-day min BB width AND BB inside Keltner Channels.
        Breakout BUY: price closes above BB upper after squeeze.
        Breakout SELL: price closes below BB lower after squeeze.
        """
        if i < 21:
            return None
        bb_w = self._nan_safe(self.bb_width.iloc[i])
        bb_w_prev = self._nan_safe(self.bb_width.iloc[i - 1])
        if np.isnan(bb_w) or np.isnan(bb_w_prev):
            return None

        # Check if coming out of squeeze (min BB width over last 20 bars)
        bb_width_window = self.bb_width.iloc[max(0, i - 20):i]
        bb_width_window = bb_width_window.dropna()
        if len(bb_width_window) < 10:
            return None
        min_bw = float(bb_width_window.min())

        # Was in squeeze: previous BB width near the minimum
        in_squeeze = bb_w_prev <= min_bw * 1.05

        # Also check BB inside Keltner (squeeze condition)
        bb_u = self._nan_safe(self.bb_upper.iloc[i - 1])
        bb_l = self._nan_safe(self.bb_lower.iloc[i - 1])
        kc_u = self._nan_safe(self.kc_upper.iloc[i - 1])
        kc_l = self._nan_safe(self.kc_lower.iloc[i - 1])
        if any(np.isnan(v) for v in [bb_u, bb_l, kc_u, kc_l]):
            return None

        keltner_squeeze = bb_u < kc_u and bb_l > kc_l

        if not (in_squeeze or keltner_squeeze):
            return None

        # Now check breakout direction
        price = float(self.close.iloc[i])
        bb_upper_now = self._nan_safe(self.bb_upper.iloc[i])
        bb_lower_now = self._nan_safe(self.bb_lower.iloc[i])
        if np.isnan(bb_upper_now) or np.isnan(bb_lower_now):
            return None

        atr_val = self.get_atr(i)

        if price > bb_upper_now:
            tp = price + 2.5 * atr_val
            sl = price - 1.5 * atr_val
            return ("BUY", tp, sl)
        elif price < bb_lower_now:
            tp = price - 2.5 * atr_val
            sl = price + 1.5 * atr_val
            return ("SELL", tp, sl)

        return None

    def bollinger_exit(self, i: int, entry_bar: int, direction: str) -> bool:
        if (i - entry_bar) >= 15:
            return True
        price = float(self.close.iloc[i])
        bb_mid = self._nan_safe(self.bb_mid.iloc[i])
        if np.isnan(bb_mid):
            return False
        # Exit when price reverts to the mean (Bollinger midline)
        if direction == "BUY" and price < bb_mid:
            return True
        if direction == "SELL" and price > bb_mid:
            return True
        return False

    # ------------------------------------------------------------------
    # 7. VWAP Reversion
    # ------------------------------------------------------------------
    def vwap_reversion(self, i: int):
        """
        BUY: Price > 2 standard deviations below VWAP AND RSI(14) < 30
        SELL: Price > 2 standard deviations above VWAP AND RSI(14) > 70
        """
        vwap_val = self._nan_safe(self.vwap_series.iloc[i])
        vwap_sd = self._nan_safe(self.vwap_std.iloc[i])
        rsi_val = self._nan_safe(self.rsi14.iloc[i])
        if any(np.isnan(v) for v in [vwap_val, vwap_sd, rsi_val]):
            return None
        if vwap_sd <= 0:
            return None

        price = float(self.close.iloc[i])
        z_score = (price - vwap_val) / vwap_sd
        atr_val = self.get_atr(i)

        if z_score < -2.0 and rsi_val < 30:
            tp = vwap_val  # Target: revert to VWAP
            sl = price - 1.5 * atr_val
            return ("BUY", tp, sl)

        if z_score > 2.0 and rsi_val > 70:
            tp = vwap_val
            sl = price + 1.5 * atr_val
            return ("SELL", tp, sl)

        return None

    def vwap_exit(self, i: int, entry_bar: int) -> bool:
        if (i - entry_bar) >= 10:
            return True
        price = float(self.close.iloc[i])
        vwap_val = self._nan_safe(self.vwap_series.iloc[i])
        if np.isnan(vwap_val):
            return False
        # Reached VWAP (mean reversion complete)
        if abs(price - vwap_val) / vwap_val < 0.001:
            return True
        return False

    # ------------------------------------------------------------------
    # 8. RSI Divergence
    # ------------------------------------------------------------------
    def rsi_divergence(self, i: int):
        """
        Bullish divergence: Price makes lower low but RSI(14) makes higher low.
        Bearish divergence: Price makes higher high but RSI(14) makes lower high.
        Lookback window: 10-20 bars.
        """
        lookback = 14
        if i < lookback + 5:
            return None

        price = float(self.close.iloc[i])
        rsi_now = self._nan_safe(self.rsi14.iloc[i])
        if np.isnan(rsi_now):
            return None

        # Find prior low/high in lookback window
        window_close = self.close.iloc[i - lookback:i]
        window_rsi = self.rsi14.iloc[i - lookback:i].dropna()
        if len(window_rsi) < 5:
            return None

        prior_low_price = float(window_close.min())
        prior_low_idx = window_close.idxmin()
        prior_low_rsi = self._nan_safe(self.rsi14.loc[prior_low_idx]) if prior_low_idx in self.rsi14.index else np.nan

        prior_high_price = float(window_close.max())
        prior_high_idx = window_close.idxmax()
        prior_high_rsi = self._nan_safe(self.rsi14.loc[prior_high_idx]) if prior_high_idx in self.rsi14.index else np.nan

        atr_val = self.get_atr(i)

        # Bullish divergence: price lower low, RSI higher low
        if (not np.isnan(prior_low_rsi) and price < prior_low_price
                and rsi_now > prior_low_rsi and rsi_now < 40):
            tp = price + 2.5 * atr_val
            sl = price - 1.5 * atr_val
            return ("BUY", tp, sl)

        # Bearish divergence: price higher high, RSI lower high
        if (not np.isnan(prior_high_rsi) and price > prior_high_price
                and rsi_now < prior_high_rsi and rsi_now > 60):
            tp = price - 2.5 * atr_val
            sl = price + 1.5 * atr_val
            return ("SELL", tp, sl)

        return None

    def rsi_divergence_exit(self, i: int, entry_bar: int, direction: str) -> bool:
        if (i - entry_bar) >= 15:
            return True
        rsi_now = self._nan_safe(self.rsi14.iloc[i])
        if np.isnan(rsi_now):
            return False
        if direction == "BUY" and rsi_now > 60:
            return True
        if direction == "SELL" and rsi_now < 40:
            return True
        return False

    # ------------------------------------------------------------------
    # 9. Supertrend
    # ------------------------------------------------------------------
    def supertrend_signal(self, i: int):
        """
        BUY: Supertrend flips from -1 to 1 (down to up)
        SELL: Supertrend flips from 1 to -1 (up to down)
        """
        if i < 1:
            return None
        dir_now = self._nan_safe(self.supertrend_dir.iloc[i])
        dir_prev = self._nan_safe(self.supertrend_dir.iloc[i - 1])
        if np.isnan(dir_now) or np.isnan(dir_prev):
            return None

        price = float(self.close.iloc[i])
        atr_val = self.get_atr(i)

        if dir_prev == -1 and dir_now == 1:
            tp = price + 3.0 * atr_val
            sl = price - 2.0 * atr_val
            return ("BUY", tp, sl)
        if dir_prev == 1 and dir_now == -1:
            tp = price - 3.0 * atr_val
            sl = price + 2.0 * atr_val
            return ("SELL", tp, sl)

        return None

    def supertrend_exit(self, i: int, entry_bar: int, direction: str) -> bool:
        if (i - entry_bar) >= 25:
            return True
        dir_now = self._nan_safe(self.supertrend_dir.iloc[i])
        if np.isnan(dir_now):
            return False
        if direction == "BUY" and dir_now == -1:
            return True
        if direction == "SELL" and dir_now == 1:
            return True
        return False

    # ------------------------------------------------------------------
    # 10. Swing Failure Pattern (SFP)
    # ------------------------------------------------------------------
    def sfp_signal(self, i: int):
        """
        Bearish SFP: Wick goes above prior swing high but close is inside.
        Bullish SFP: Wick goes below prior swing low but close is inside.
        """
        price = float(self.close.iloc[i])
        high_now = float(self.high.iloc[i])
        low_now = float(self.low.iloc[i])
        atr_val = self.get_atr(i)

        # Find most recent swing high in last 30 bars
        lookback = min(30, i)
        recent_swing_highs = self.swing_highs.iloc[max(0, i - lookback):i].dropna()
        recent_swing_lows = self.swing_lows.iloc[max(0, i - lookback):i].dropna()

        # Bullish SFP: wick below prior swing low, close above it
        if len(recent_swing_lows) > 0:
            last_swing_low = float(recent_swing_lows.iloc[-1])
            if low_now < last_swing_low and price > last_swing_low:
                tp = price + 2.5 * atr_val
                sl = low_now - 0.5 * atr_val
                return ("BUY", tp, sl)

        # Bearish SFP: wick above prior swing high, close below it
        if len(recent_swing_highs) > 0:
            last_swing_high = float(recent_swing_highs.iloc[-1])
            if high_now > last_swing_high and price < last_swing_high:
                tp = price - 2.5 * atr_val
                sl = high_now + 0.5 * atr_val
                return ("SELL", tp, sl)

        return None

    def sfp_exit(self, i: int, entry_bar: int) -> bool:
        return (i - entry_bar) >= 10

    # ------------------------------------------------------------------
    # 11. Break of Structure (BOS)
    # ------------------------------------------------------------------
    def bos_signal(self, i: int):
        """
        Bullish BOS: Price breaks above the most recent swing high.
        Bearish BOS: Price breaks below the most recent swing low.
        """
        price = float(self.close.iloc[i])
        atr_val = self.get_atr(i)

        lookback = min(40, i)
        recent_swing_highs = self.swing_highs.iloc[max(0, i - lookback):i].dropna()
        recent_swing_lows = self.swing_lows.iloc[max(0, i - lookback):i].dropna()

        # Bullish BOS: close above prior swing high (continuation)
        if len(recent_swing_highs) > 0:
            last_sh = float(recent_swing_highs.iloc[-1])
            # Check previous bar was below
            if i > 0:
                prev_close = float(self.close.iloc[i - 1])
                if prev_close <= last_sh and price > last_sh:
                    tp = price + 3.0 * atr_val
                    sl = price - 1.5 * atr_val
                    return ("BUY", tp, sl)

        # Bearish BOS: close below prior swing low
        if len(recent_swing_lows) > 0:
            last_sl_price = float(recent_swing_lows.iloc[-1])
            if i > 0:
                prev_close = float(self.close.iloc[i - 1])
                if prev_close >= last_sl_price and price < last_sl_price:
                    tp = price - 3.0 * atr_val
                    sl = price + 1.5 * atr_val
                    return ("SELL", tp, sl)

        return None

    def bos_exit(self, i: int, entry_bar: int) -> bool:
        return (i - entry_bar) >= 15

    # ------------------------------------------------------------------
    # 12. Liquidation Cascade
    # ------------------------------------------------------------------
    def liquidation_cascade(self, i: int):
        """
        BUY after cascade: Volume > 5x 20-bar average + sharp price drop
        (>3% in 3 bars) + reversal candle (close > open on current bar).
        """
        if i < 5:
            return None
        vol_now = self._nan_safe(self.volume.iloc[i])
        vol_avg = self._nan_safe(self.vol_sma20.iloc[i])
        if np.isnan(vol_now) or np.isnan(vol_avg) or vol_avg <= 0:
            return None

        vol_ratio = vol_now / vol_avg
        if vol_ratio < 5.0:
            return None

        # Check for sharp drop in last 3 bars
        price_now = float(self.close.iloc[i])
        price_3ago = float(self.close.iloc[i - 3])
        drop_pct = (price_now - price_3ago) / price_3ago

        # Need a V-bounce: drop followed by recovery candle
        open_now = float(self.df["Open"].iloc[i])
        is_bullish_candle = price_now > open_now

        if drop_pct < -0.03 and is_bullish_candle:
            atr_val = self.get_atr(i)
            tp = price_now + 3.0 * atr_val
            sl = float(self.low.iloc[i]) - 0.5 * atr_val
            return ("BUY", tp, sl)

        return None

    def liquidation_cascade_exit(self, i: int, entry_bar: int) -> bool:
        return (i - entry_bar) >= 10

    # ------------------------------------------------------------------
    # 13. Momentum Crash Hedge (Daniel & Moskowitz 2016)
    # ------------------------------------------------------------------
    def momentum_crash_hedge(self, i: int):
        """
        EWMA vol scaling: when volatility spikes (>2x normal), reduce
        momentum exposure or go contrarian.

        Implementation: Monitor 12-month (252-day) momentum.
        If momentum is positive AND vol is low -> BUY (momentum).
        If momentum is negative AND vol is spiking -> BUY (contrarian bounce).
        """
        if i < 252:
            return None
        price = float(self.close.iloc[i])
        price_12m = float(self.close.iloc[i - 252])
        momentum_12m = (price - price_12m) / price_12m

        ewma_now = self._nan_safe(self.ewma_vol.iloc[i])
        if np.isnan(ewma_now) or ewma_now <= 0:
            return None

        # Median vol over last 252 days
        vol_window = self.ewma_vol.iloc[max(0, i - 252):i].dropna()
        if len(vol_window) < 60:
            return None
        median_vol = float(vol_window.median())
        if median_vol <= 0:
            return None
        vol_ratio = ewma_now / median_vol

        atr_val = self.get_atr(i)

        # High momentum + low volatility: trend continuation
        if momentum_12m > 0.10 and vol_ratio < 1.5:
            tp = price + 3.0 * atr_val
            sl = price - 2.0 * atr_val
            return ("BUY", tp, sl)

        # Momentum crash: negative momentum + vol spike = contrarian bounce
        if momentum_12m < -0.10 and vol_ratio > 2.0:
            tp = price + 2.5 * atr_val
            sl = price - 2.0 * atr_val
            return ("BUY", tp, sl)

        return None

    def momentum_crash_exit(self, i: int, entry_bar: int) -> bool:
        return (i - entry_bar) >= 20

    # ------------------------------------------------------------------
    # 14. Multi-Strategy Consensus
    # ------------------------------------------------------------------
    def multi_strategy_consensus(self, i: int):
        """
        BUY when 3+ strategies agree (same direction).
        This aggregates signals from strategies 3-12.
        """
        buy_count = 0
        sell_count = 0

        # Check each sub-strategy
        checks = [
            self.macd_momentum(i),
            self.ema_crossover(i),
            self.supertrend_signal(i),
            self.bollinger_squeeze(i),
            self.sfp_signal(i),
            self.bos_signal(i),
        ]

        for result in checks:
            if result is None:
                continue
            if result[0] == "BUY":
                buy_count += 1
            elif result[0] == "SELL":
                sell_count += 1

        # Also check RSI for overall bias
        rsi_val = self._nan_safe(self.rsi14.iloc[i])
        if not np.isnan(rsi_val):
            if rsi_val < 30:
                buy_count += 1
            elif rsi_val > 70:
                sell_count += 1

        price = float(self.close.iloc[i])
        atr_val = self.get_atr(i)

        if buy_count >= 3:
            tp = price + 3.0 * atr_val
            sl = price - 1.5 * atr_val
            return ("BUY", tp, sl)
        if sell_count >= 3:
            tp = price - 3.0 * atr_val
            sl = price + 1.5 * atr_val
            return ("SELL", tp, sl)

        return None

    def multi_strategy_exit(self, i: int, entry_bar: int) -> bool:
        return (i - entry_bar) >= 15

    # ------------------------------------------------------------------
    # 15. Currency Momentum (Menkhoff et al. 2012 JFE)
    # ------------------------------------------------------------------
    def currency_momentum(self, i: int):
        """
        Time-series momentum: if 3-month return > 0, go long; if < 0, go short.
        Blends 1-month (22d), 3-month (63d), and 12-month (252d) lookbacks.
        Moskowitz, Ooi & Pedersen (2012) JFE: Sharpe 0.40-0.80 across FX.
        """
        if i < 260:
            return None
        price = float(self.close.iloc[i])
        price_22 = float(self.close.iloc[i - 22])
        price_63 = float(self.close.iloc[i - 63])
        price_252 = float(self.close.iloc[i - 252])

        ret_1m = (price / price_22) - 1.0
        ret_3m = (price / price_63) - 1.0
        ret_12m = (price / price_252) - 1.0

        # Blended signal: count how many lookbacks agree
        bull_count = (1 if ret_1m > 0 else 0) + (1 if ret_3m > 0 else 0) + (1 if ret_12m > 0 else 0)

        atr_val = self.get_atr(i)

        if bull_count >= 2 and ret_3m > 0.005:  # Require at least 0.5% 3m return
            tp = price + 4.0 * atr_val   # Wide TP for trend following
            sl = price - 2.0 * atr_val   # Wide SL (trends need room)
            return ("BUY", tp, sl)
        elif bull_count <= 1 and ret_3m < -0.005:
            tp = price - 4.0 * atr_val
            sl = price + 2.0 * atr_val
            return ("SELL", tp, sl)
        return None

    def currency_momentum_exit(self, i: int, entry_bar: int, direction: str) -> bool:
        """Exit on momentum flip or after 30 bars (monthly rebalance)."""
        if (i - entry_bar) >= 30:
            return True
        if i < 63:
            return False
        price = float(self.close.iloc[i])
        price_63 = float(self.close.iloc[i - 63])
        ret_3m = (price / price_63) - 1.0
        # Exit if momentum has flipped against position
        if direction == "BUY" and ret_3m < -0.005:
            return True
        if direction == "SELL" and ret_3m > 0.005:
            return True
        return False

    # ------------------------------------------------------------------
    # 16. FX Value Mean Reversion (Asness et al. 2013 JF — PPP proxy)
    # ------------------------------------------------------------------
    def fx_value_ppp(self, i: int):
        """
        Buy currencies cheap vs 5-year SMA, sell expensive ones.
        Uses SMA(252*5=1260) as fair-value proxy for PPP.
        Combined with 1-month momentum filter to avoid catching falling knives.
        Asness, Moskowitz & Pedersen (2013) JF: Sharpe 0.35-0.50.
        """
        if i < 1260 + 22:
            return None
        price = float(self.close.iloc[i])

        # 5-year SMA as "fair value"
        fair_value = float(self.close.iloc[i - 1260:i + 1].mean())
        if fair_value == 0 or np.isnan(fair_value):
            return None

        deviation = (price - fair_value) / fair_value

        # Calculate std of deviation over trailing year
        dev_window = self.close.iloc[max(0, i - 252):i + 1]
        sma_5y_window = dev_window.rolling(min(1260, len(dev_window))).mean()
        if sma_5y_window.iloc[-1] is None or np.isnan(float(sma_5y_window.iloc[-1])):
            return None

        # Z-score approximation
        dev_std = float(dev_window.std() / fair_value) if fair_value != 0 else 0.01
        z_score = deviation / dev_std if dev_std > 0.001 else 0.0

        # 1-month momentum filter
        price_22 = float(self.close.iloc[i - 22])
        mom_1m = (price / price_22) - 1.0

        atr_val = self.get_atr(i)

        # Buy cheap currency + positive momentum (turning around)
        if z_score < -1.0 and mom_1m > 0:
            tp = price + 3.0 * atr_val
            sl = price - 2.0 * atr_val
            return ("BUY", tp, sl)
        # Sell expensive currency + negative momentum
        elif z_score > 1.0 and mom_1m < 0:
            tp = price - 3.0 * atr_val
            sl = price + 2.0 * atr_val
            return ("SELL", tp, sl)
        return None

    def fx_value_ppp_exit(self, i: int, entry_bar: int) -> bool:
        """Exit when price returns near fair value or after 40 bars."""
        if (i - entry_bar) >= 40:
            return True
        if i < 1260:
            return False
        price = float(self.close.iloc[i])
        fair_value = float(self.close.iloc[i - 1260:i + 1].mean())
        if fair_value == 0 or np.isnan(fair_value):
            return False
        deviation = abs((price - fair_value) / fair_value)
        # Exit when deviation shrinks to within 0.5 z-score equivalent
        return deviation < 0.005  # very close to fair value

    # ------------------------------------------------------------------
    # 17. Trend Following Vol-Scaled (Moskowitz, Ooi & Pedersen 2012 JFE)
    # ------------------------------------------------------------------
    def trend_following_vol(self, i: int):
        """
        Time-series momentum with volatility scaling.
        3-month return determines direction, position sized by inverse vol.
        Hurst, Ooi & Pedersen (2017): Sharpe 0.40-0.80 across 67 markets.
        Uses wider TP/SL than standard strategies to give trends room.
        """
        if i < 260:
            return None
        price = float(self.close.iloc[i])
        price_63 = float(self.close.iloc[i - 63])
        price_22 = float(self.close.iloc[i - 22])

        ret_3m = (price / price_63) - 1.0
        ret_1m = (price / price_22) - 1.0

        # Need momentum in same direction for both timeframes
        if ret_3m > 0.005 and ret_1m > 0:
            atr_val = self.get_atr(i)
            # Vol-scale: wider TP/SL for low-vol pairs, tighter for high-vol
            ewma_v = self._nan_safe(self.ewma_vol.iloc[i])
            vol_mult = 1.0
            if not np.isnan(ewma_v) and ewma_v > 0:
                vol_mult = max(0.5, min(2.5, 0.10 / (ewma_v * np.sqrt(252))))
            tp = price + 5.0 * atr_val * vol_mult
            sl = price - 2.5 * atr_val * vol_mult
            return ("BUY", tp, sl)
        elif ret_3m < -0.005 and ret_1m < 0:
            atr_val = self.get_atr(i)
            ewma_v = self._nan_safe(self.ewma_vol.iloc[i])
            vol_mult = 1.0
            if not np.isnan(ewma_v) and ewma_v > 0:
                vol_mult = max(0.5, min(2.5, 0.10 / (ewma_v * np.sqrt(252))))
            tp = price - 5.0 * atr_val * vol_mult
            sl = price + 2.5 * atr_val * vol_mult
            return ("SELL", tp, sl)
        return None

    def trend_following_vol_exit(self, i: int, entry_bar: int, direction: str) -> bool:
        """Exit on momentum reversal or after 40 bars."""
        if (i - entry_bar) >= 40:
            return True
        if i < 63:
            return False
        price = float(self.close.iloc[i])
        price_22 = float(self.close.iloc[i - 22])
        ret_1m = (price / price_22) - 1.0
        # Exit when short-term momentum flips
        if direction == "BUY" and ret_1m < -0.01:
            return True
        if direction == "SELL" and ret_1m > 0.01:
            return True
        return False


# ===========================================================================
# STRATEGY REGISTRY
# ===========================================================================
STRATEGY_REGISTRY = {
    "connors_rsi2": {
        "name": "Connors RSI-2",
        "index": 0,
        "entry_fn": "connors_rsi2",
        "exit_fn": "connors_rsi2_exit",
        "has_direction_exit": False,
        "description": "RSI(2)<5 + price>SMA200 -- Connors & Alvarez 2008",
        "academic_source": "Connors & Alvarez (2008)",
        "warmup": 210,
    },
    "vix_spike_reversal": {
        "name": "VIX Spike Reversal",
        "index": 1,
        "entry_fn": "vix_spike_reversal",
        "exit_fn": "vix_spike_exit",
        "has_direction_exit": False,
        "description": "3% drawdown + RSI2<20 (fear proxy) -- Connors Research 2010",
        "academic_source": "Connors Research (2010), Whaley (2009)",
        "warmup": 210,
    },
    "macd_momentum": {
        "name": "MACD Momentum",
        "index": 2,
        "entry_fn": "macd_momentum",
        "exit_fn": "macd_exit",
        "has_direction_exit": False,
        "description": "MACD(12,26,9) cross + RSI(14) filter",
        "academic_source": "Appel (1979), Murphy (1999)",
        "warmup": 60,
    },
    "ema_crossover": {
        "name": "EMA Crossover",
        "index": 3,
        "entry_fn": "ema_crossover",
        "exit_fn": "ema_exit",
        "has_direction_exit": True,
        "description": "EMA(9) cross EMA(21) + price>EMA(50)",
        "academic_source": "Moving Average Convergence systems",
        "warmup": 60,
    },
    "ichimoku_cloud": {
        "name": "Ichimoku Cloud",
        "index": 4,
        "entry_fn": "ichimoku_cloud",
        "exit_fn": "ichimoku_exit",
        "has_direction_exit": True,
        "description": "Tenkan-Kijun cross above cloud + green future cloud",
        "academic_source": "Hosoda (1968), Elliot et al. (2013)",
        "warmup": 60,
    },
    "bollinger_squeeze": {
        "name": "Bollinger Squeeze",
        "index": 5,
        "entry_fn": "bollinger_squeeze",
        "exit_fn": "bollinger_exit",
        "has_direction_exit": True,
        "description": "BB width < 20d min + Keltner squeeze -> breakout",
        "academic_source": "Bollinger (2001), Carter (TTM Squeeze)",
        "warmup": 30,
    },
    "vwap_reversion": {
        "name": "VWAP Reversion",
        "index": 6,
        "entry_fn": "vwap_reversion",
        "exit_fn": "vwap_exit",
        "has_direction_exit": False,
        "description": "Price >2 std below VWAP + RSI<30",
        "academic_source": "Berkowitz et al. (1988)",
        "warmup": 30,
    },
    "rsi_divergence": {
        "name": "RSI Divergence",
        "index": 7,
        "entry_fn": "rsi_divergence",
        "exit_fn": "rsi_divergence_exit",
        "has_direction_exit": True,
        "description": "Price lower low + RSI higher low (bullish divergence)",
        "academic_source": "Wilder (1978), Cardwell RSI divergence theory",
        "warmup": 30,
    },
    "supertrend": {
        "name": "Supertrend",
        "index": 8,
        "entry_fn": "supertrend_signal",
        "exit_fn": "supertrend_exit",
        "has_direction_exit": True,
        "description": "Supertrend(10,3) flip from down to up",
        "academic_source": "Pring (2002), ATR-based trailing systems",
        "warmup": 30,
    },
    "sfp": {
        "name": "Swing Failure Pattern",
        "index": 9,
        "entry_fn": "sfp_signal",
        "exit_fn": "sfp_exit",
        "has_direction_exit": False,
        "description": "Wick beyond prior swing high/low + close inside",
        "academic_source": "Hsaka (crypto), ICT Smart Money Concepts",
        "warmup": 40,
    },
    "bos": {
        "name": "Break of Structure",
        "index": 10,
        "entry_fn": "bos_signal",
        "exit_fn": "bos_exit",
        "has_direction_exit": False,
        "description": "Price breaks above/below prior swing point",
        "academic_source": "ICT BOS/CHOCH, Wyckoff structure",
        "warmup": 50,
    },
    "liquidation_cascade": {
        "name": "Liquidation Cascade",
        "index": 11,
        "entry_fn": "liquidation_cascade",
        "exit_fn": "liquidation_cascade_exit",
        "has_direction_exit": False,
        "description": "Volume >5x avg + sharp drop + reversal candle",
        "academic_source": "Binance cascade data, CryptoQuant research",
        "warmup": 30,
    },
    "momentum_crash_hedge": {
        "name": "Momentum Crash Hedge",
        "index": 12,
        "entry_fn": "momentum_crash_hedge",
        "exit_fn": "momentum_crash_exit",
        "has_direction_exit": False,
        "description": "EWMA vol scaling -- Daniel & Moskowitz (2016)",
        "academic_source": "Daniel & Moskowitz (2016) JFE",
        "warmup": 260,
    },
    "multi_strategy": {
        "name": "Multi-Strategy Consensus",
        "index": 13,
        "entry_fn": "multi_strategy_consensus",
        "exit_fn": "multi_strategy_exit",
        "has_direction_exit": False,
        "description": "3+ sub-strategies agree on direction",
        "academic_source": "Ensemble methods, Bates et al. (2019)",
        "warmup": 60,
    },
    "currency_momentum": {
        "name": "Currency Momentum",
        "index": 14,
        "entry_fn": "currency_momentum",
        "exit_fn": "currency_momentum_exit",
        "has_direction_exit": True,
        "description": "Multi-TF momentum: blend 1m/3m/12m returns, go with majority",
        "academic_source": "Menkhoff, Sarno, Schmeling & Schrimpf (2012) JFE",
        "warmup": 260,
    },
    "fx_value_ppp": {
        "name": "FX Value (PPP)",
        "index": 15,
        "entry_fn": "fx_value_ppp",
        "exit_fn": "fx_value_ppp_exit",
        "has_direction_exit": False,
        "description": "Buy cheap vs 5yr SMA + positive momentum filter",
        "academic_source": "Asness, Moskowitz & Pedersen (2013) JF",
        "warmup": 1290,
    },
    "trend_following_vol": {
        "name": "Trend Following Vol-Scaled",
        "index": 16,
        "entry_fn": "trend_following_vol",
        "exit_fn": "trend_following_vol_exit",
        "has_direction_exit": True,
        "description": "3m trend + inverse vol sizing, wide TP/SL for trends",
        "academic_source": "Moskowitz, Ooi & Pedersen (2012) JFE, Hurst et al. (2017)",
        "warmup": 260,
    },
}


# ===========================================================================
# BACKTESTING ENGINE
# ===========================================================================

def run_backtest(df: pd.DataFrame, strategy_key: str, symbol: str,
                 category: str = "crypto", max_hold: int = 30) -> dict:
    """
    Run walk-forward backtest for a single strategy on a single symbol.

    Returns dict with in_sample_stats, out_of_sample_stats, trades[].
    """
    strat_info = STRATEGY_REGISTRY[strategy_key]
    warmup = strat_info["warmup"]

    if len(df) < warmup + 60:
        return {"error": f"Not enough data: {len(df)} bars (need {warmup + 60})"}

    # Initialize strategy runner
    runner = StrategyRunner(df, category)
    entry_fn = getattr(runner, strat_info["entry_fn"])
    exit_fn = getattr(runner, strat_info["exit_fn"])
    has_dir_exit = strat_info["has_direction_exit"]

    # Walk-forward split: 70% in-sample, 30% out-of-sample
    total_bars = len(df) - warmup
    split_bar = warmup + int(total_bars * 0.70)

    # Transaction cost
    tx_cost = TRANSACTION_COSTS.get(category, 0.001)

    all_trades = []
    in_trade = False
    entry_price = 0.0
    entry_bar = 0
    trade_direction = ""
    trade_tp = 0.0
    trade_sl = 0.0
    last_exit_bar = -999  # Cooldown: prevent re-entry within 3 bars of exit
    COOLDOWN_BARS = 3

    for i in range(warmup, len(df)):
        if not in_trade:
            # Cooldown check: skip if we just exited recently
            if i - last_exit_bar < COOLDOWN_BARS:
                continue
            # Try to enter
            signal = entry_fn(i)
            if signal is not None:
                trade_direction, trade_tp, trade_sl = signal
                entry_price = float(runner.close.iloc[i])
                entry_bar = i
                in_trade = True
        else:
            # Check TP/SL
            price_now = float(runner.close.iloc[i])
            high_now = float(runner.high.iloc[i])
            low_now = float(runner.low.iloc[i])

            exit_reason = None
            exit_price = price_now

            if trade_direction == "BUY":
                if high_now >= trade_tp:
                    exit_reason = "TP_HIT"
                    exit_price = trade_tp
                elif low_now <= trade_sl:
                    exit_reason = "SL_HIT"
                    exit_price = trade_sl
            elif trade_direction == "SELL":
                if low_now <= trade_tp:
                    exit_reason = "TP_HIT"
                    exit_price = trade_tp
                elif high_now >= trade_sl:
                    exit_reason = "SL_HIT"
                    exit_price = trade_sl

            # Check strategy-specific exit
            if exit_reason is None:
                if has_dir_exit:
                    should_exit = exit_fn(i, entry_bar, trade_direction)
                else:
                    should_exit = exit_fn(i, entry_bar)
                if should_exit:
                    exit_reason = "SIGNAL_EXIT"
                    exit_price = price_now

            # Max hold exit
            if exit_reason is None and (i - entry_bar) >= max_hold:
                exit_reason = "TIME_EXIT"
                exit_price = price_now

            if exit_reason is not None:
                # Calculate P&L with transaction costs
                if trade_direction == "BUY":
                    raw_pnl = (exit_price - entry_price) / entry_price
                else:  # SELL
                    raw_pnl = (entry_price - exit_price) / entry_price

                # Subtract round-trip transaction costs
                net_pnl = raw_pnl - (2 * tx_cost)

                trade_record = {
                    "entry_date": str(df.index[entry_bar])[:10],
                    "exit_date": str(df.index[i])[:10],
                    "direction": trade_direction,
                    "entry_price": round(entry_price, 6),
                    "exit_price": round(exit_price, 6),
                    "raw_pnl_pct": round(raw_pnl * 100, 4),
                    "net_pnl_pct": round(net_pnl * 100, 4),
                    "tx_cost_pct": round(2 * tx_cost * 100, 4),
                    "days_held": i - entry_bar,
                    "exit_reason": exit_reason,
                    "won": net_pnl > 0,
                    "is_oos": i >= split_bar,
                }
                all_trades.append(trade_record)
                in_trade = False
                last_exit_bar = i

    if not all_trades:
        return {"error": "No trades generated", "symbol": symbol}

    # Split trades into in-sample and out-of-sample
    is_trades = [t for t in all_trades if not t["is_oos"]]
    oos_trades = [t for t in all_trades if t["is_oos"]]

    return {
        "strategy": strategy_key,
        "strategy_name": strat_info["name"],
        "symbol": symbol,
        "category": category,
        "total_bars": len(df),
        "split_bar": split_bar,
        "split_date": str(df.index[split_bar])[:10] if split_bar < len(df) else "N/A",
        "tx_cost_per_side": tx_cost,
        "in_sample_stats": compute_stats(is_trades, "in_sample"),
        "out_of_sample_stats": compute_stats(oos_trades, "out_of_sample"),
        "overall_stats": compute_stats(all_trades, "overall"),
        "trades": all_trades,
    }


def compute_stats(trades: list[dict], label: str) -> dict:
    """Compute statistical summary for a set of trades."""
    if not trades:
        return {
            "label": label,
            "n_trades": 0,
            "win_rate": 0.0,
            "sharpe": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_pct": 0.0,
            "total_return_pct": 0.0,
            "avg_pnl_pct": 0.0,
            "mean_win_pct": 0.0,
            "mean_loss_pct": 0.0,
            "avg_days_held": 0.0,
            "binomial_p": 1.0,
            "significant": False,
        }

    n = len(trades)
    wins = [t for t in trades if t["won"]]
    losses = [t for t in trades if not t["won"]]
    n_wins = len(wins)
    n_losses = len(losses)
    win_rate = n_wins / n

    pnls = [t["net_pnl_pct"] for t in trades]
    avg_pnl = sum(pnls) / n
    total_return = sum(pnls)
    pnl_std = (sum((p - avg_pnl) ** 2 for p in pnls) / max(n - 1, 1)) ** 0.5

    # Sharpe ratio (annualized, assuming avg 5 day hold -> ~50 trades/yr)
    avg_days = sum(t["days_held"] for t in trades) / n
    trades_per_year = 252.0 / max(avg_days, 1)
    sharpe = (avg_pnl / pnl_std) * (trades_per_year ** 0.5) if pnl_std > 0 else 0.0

    # Profit factor
    gross_profit = sum(t["net_pnl_pct"] for t in wins) if wins else 0.0
    gross_loss = abs(sum(t["net_pnl_pct"] for t in losses)) if losses else 0.001
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

    # Max drawdown
    equity_curve = []
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        equity += t["net_pnl_pct"]
        equity_curve.append(equity)
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd

    # Mean win / mean loss
    mean_win = sum(t["net_pnl_pct"] for t in wins) / n_wins if n_wins > 0 else 0.0
    mean_loss = sum(t["net_pnl_pct"] for t in losses) / n_losses if n_losses > 0 else 0.0

    # Binomial p-value (one-sided: P(wins >= observed | p=0.5))
    # Use normal approximation for large n to avoid overflow
    if n > 500:
        # Normal approximation to binomial
        z = (n_wins - n * 0.5) / (n * 0.25) ** 0.5
        # One-sided: P(X >= observed) using complementary error function
        p_val = 0.5 * math.erfc(z / math.sqrt(2))
    else:
        p_val = 0.0
        for k in range(n_wins, n + 1):
            p_val += math.comb(n, k) * (0.5 ** n)

    # Exit reason breakdown
    exit_reasons = {}
    for t in trades:
        r = t["exit_reason"]
        exit_reasons[r] = exit_reasons.get(r, 0) + 1

    return {
        "label": label,
        "n_trades": n,
        "wins": n_wins,
        "losses": n_losses,
        "win_rate": round(win_rate, 4),
        "sharpe": round(sharpe, 3),
        "profit_factor": round(profit_factor, 3),
        "max_drawdown_pct": round(max_dd, 3),
        "total_return_pct": round(total_return, 3),
        "avg_pnl_pct": round(avg_pnl, 4),
        "mean_win_pct": round(mean_win, 4),
        "mean_loss_pct": round(mean_loss, 4),
        "avg_days_held": round(avg_days, 1),
        "binomial_p": round(p_val, 6),
        "significant": p_val < 0.05,
        "exit_reasons": exit_reasons,
    }


# ===========================================================================
# DATA FETCHING
# ===========================================================================

def flatten_yf(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten MultiIndex columns from yfinance."""
    if isinstance(df.columns, pd.MultiIndex):
        ohlcv = {'Open', 'High', 'Low', 'Close', 'Volume'}
        level0_vals = set(df.columns.get_level_values(0))
        level1_vals = set(df.columns.get_level_values(1))
        if level0_vals & ohlcv:
            df.columns = df.columns.get_level_values(0)
        elif level1_vals & ohlcv:
            df.columns = df.columns.get_level_values(1)
        else:
            df.columns = df.columns.get_level_values(0)
    return df


def fetch_all_data(symbols: list[str], period: str = "5y") -> dict[str, pd.DataFrame]:
    """Fetch OHLCV data for all symbols."""
    data = {}
    print(f"\n  Fetching data for {len(symbols)} symbols (period={period})...")

    # Try batch download first
    ticker_str = " ".join(symbols)
    try:
        raw = yf.download(
            ticker_str,
            period=period,
            interval="1d",
            group_by="ticker" if len(symbols) > 1 else None,
            auto_adjust=True,
            threads=True,
            progress=False,
        )

        if raw is not None and not raw.empty:
            for sym in symbols:
                try:
                    if len(symbols) == 1:
                        df = raw.copy()
                    else:
                        if sym not in raw.columns.get_level_values(0):
                            continue
                        df = raw[sym].copy()

                    df = flatten_yf(df)
                    df = df.dropna(subset=["Close"])

                    if len(df) >= 100:
                        data[sym] = df
                        print(f"    {sym}: {len(df)} bars")
                    else:
                        print(f"    {sym}: only {len(df)} bars (skipped)")
                except Exception as e:
                    print(f"    {sym}: error extracting -- {e}")
            return data
    except Exception as e:
        print(f"  Batch download failed: {e}")

    # Fallback: individual downloads
    print("  Falling back to individual downloads...")
    for sym in symbols:
        try:
            df = yf.download(sym, period=period, interval="1d",
                             auto_adjust=True, progress=False)
            df = flatten_yf(df)
            df = df.dropna(subset=["Close"])
            if len(df) >= 100:
                data[sym] = df
                print(f"    {sym}: {len(df)} bars")
        except Exception as e:
            print(f"    {sym}: error -- {e}")

    return data


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(description="Backtest all Pine Script strategies")
    parser.add_argument("--strategies", type=str, default=None,
                        help="Comma-separated list of strategies to test (default: all)")
    parser.add_argument("--symbols", type=str, default=None,
                        help="Comma-separated list of symbols to test (overrides defaults)")
    parser.add_argument("--period", type=str, default="5y",
                        help="yfinance period (default: 5y)")
    parser.add_argument("--max-hold", type=int, default=30,
                        help="Maximum holding period in bars (default: 30)")
    args = parser.parse_args()

    start_time = time.time()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print("=" * 72)
    print("  PINE SCRIPT STRATEGY BACKTESTER")
    print(f"  {timestamp}")
    print(f"  14 strategies | Walk-forward validation | Realistic TX costs")
    print("=" * 72)

    # Determine which strategies to test
    if args.strategies:
        strategy_keys = [s.strip() for s in args.strategies.split(",")]
        invalid = [s for s in strategy_keys if s not in STRATEGY_REGISTRY]
        if invalid:
            print(f"\n  ERROR: Unknown strategies: {invalid}")
            print(f"  Available: {list(STRATEGY_REGISTRY.keys())}")
            sys.exit(1)
    else:
        strategy_keys = list(STRATEGY_REGISTRY.keys())

    # Determine symbols
    if args.symbols:
        override_symbols = [s.strip() for s in args.symbols.split(",")]
        # Override: use same symbols for all strategies
        all_symbols_needed = set(override_symbols)
    else:
        all_symbols_needed = set()
        for sk in strategy_keys:
            syms = STRATEGY_SYMBOLS.get(sk, ["BTC-USD", "SPY"])
            all_symbols_needed.update(syms)

    # Fetch data
    data = fetch_all_data(list(all_symbols_needed), args.period)
    if not data:
        print("\n  FATAL: No data fetched. Aborting.")
        sys.exit(1)

    print(f"\n  Data ready: {len(data)} symbols")

    # Run backtests
    all_results = {}
    summary_rows = []

    for sk in strategy_keys:
        strat_info = STRATEGY_REGISTRY[sk]
        print(f"\n{'='*60}")
        print(f"  [{strat_info['index']+1}/14] {strat_info['name']} ({sk})")
        print(f"  {strat_info['description']}")
        print(f"{'='*60}")

        if args.symbols:
            symbols_for_strat = [s.strip() for s in args.symbols.split(",")]
        else:
            symbols_for_strat = STRATEGY_SYMBOLS.get(sk, ["BTC-USD", "SPY"])

        strat_results = {}
        combined_trades = []

        for sym in symbols_for_strat:
            if sym not in data:
                print(f"    {sym}: no data available, skipping")
                continue

            category = DEFAULT_SYMBOLS.get(sym, {}).get("category", "crypto")
            result = run_backtest(data[sym], sk, sym, category, args.max_hold)

            if "error" in result:
                print(f"    {sym}: {result['error']}")
                strat_results[sym] = result
                continue

            overall = result["overall_stats"]
            oos = result["out_of_sample_stats"]
            n_is = result["in_sample_stats"]["n_trades"]
            n_oos = oos["n_trades"]

            sig_marker = " ***" if overall.get("significant") else ""
            print(f"    {sym}: {overall['n_trades']} trades "
                  f"(IS:{n_is} OOS:{n_oos}) | "
                  f"WR={overall['win_rate']*100:.1f}% | "
                  f"Sharpe={overall['sharpe']:.2f} | "
                  f"PF={overall['profit_factor']:.2f} | "
                  f"p={overall['binomial_p']:.4f}{sig_marker}")

            if n_oos > 0:
                oos_sig = " ***" if oos.get("significant") else ""
                print(f"      OOS: WR={oos['win_rate']*100:.1f}% | "
                      f"Sharpe={oos['sharpe']:.2f} | "
                      f"PF={oos['profit_factor']:.2f} | "
                      f"p={oos['binomial_p']:.4f}{oos_sig}")

            strat_results[sym] = result
            combined_trades.extend(result["trades"])

        # Combined stats across all symbols
        combined_overall = compute_stats(combined_trades, "combined")
        combined_oos = compute_stats(
            [t for t in combined_trades if t.get("is_oos")], "combined_oos"
        )

        if combined_overall["n_trades"] > 0:
            print(f"\n    COMBINED: {combined_overall['n_trades']} trades | "
                  f"WR={combined_overall['win_rate']*100:.1f}% | "
                  f"Sharpe={combined_overall['sharpe']:.2f} | "
                  f"PF={combined_overall['profit_factor']:.2f} | "
                  f"MaxDD={combined_overall['max_drawdown_pct']:.1f}% | "
                  f"p={combined_overall['binomial_p']:.4f}")

        # Verdict
        n = combined_overall["n_trades"]
        wr = combined_overall["win_rate"]
        pf = combined_overall["profit_factor"]
        sig = combined_overall["significant"]
        oos_sig = combined_oos.get("significant", False) if combined_oos["n_trades"] >= 10 else None

        if n >= 30 and wr > 0.55 and pf > 1.2 and sig:
            verdict = "PROVEN"
        elif n >= 30 and wr > 0.50 and pf > 1.0 and sig:
            verdict = "STATISTICALLY SIGNIFICANT"
        elif n >= 20 and wr > 0.50 and pf > 1.0:
            verdict = "PROMISING"
        elif n >= 10:
            verdict = "INSUFFICIENT DATA"
        else:
            verdict = "NO SIGNAL"

        print(f"    VERDICT: {verdict}")
        if oos_sig is not None:
            oos_verdict = "OOS CONFIRMED" if oos_sig else "OOS NOT SIGNIFICANT"
            print(f"    OOS VALIDATION: {oos_verdict}")

        # Save per-strategy JSON
        strat_output = {
            "strategy": sk,
            "strategy_name": strat_info["name"],
            "strategy_index": strat_info["index"],
            "description": strat_info["description"],
            "academic_source": strat_info["academic_source"],
            "backtest_timestamp": timestamp,
            "period": args.period,
            "symbols_tested": symbols_for_strat,
            "symbols_with_data": [s for s in symbols_for_strat if s in data],
            "per_symbol_results": strat_results,
            "combined_stats": combined_overall,
            "combined_oos_stats": combined_oos,
            "verdict": verdict,
        }

        # Remove full trade lists from per-symbol to save space in the per-strategy file,
        # keep only last 20 trades per symbol
        for sym_key in strat_output["per_symbol_results"]:
            sym_result = strat_output["per_symbol_results"][sym_key]
            if "trades" in sym_result and len(sym_result["trades"]) > 20:
                sym_result["trades_total"] = len(sym_result["trades"])
                sym_result["trades"] = sym_result["trades"][-20:]

        out_path = DATA_DIR / f"{sk}_backtest.json"
        with open(out_path, "w") as f:
            json.dump(strat_output, f, indent=2, default=str)
        print(f"    -> Saved: {out_path.name}")

        all_results[sk] = strat_output

        # Summary row
        summary_rows.append({
            "index": strat_info["index"],
            "strategy": sk,
            "name": strat_info["name"],
            "n_trades": combined_overall["n_trades"],
            "win_rate": combined_overall["win_rate"],
            "sharpe": combined_overall["sharpe"],
            "profit_factor": combined_overall["profit_factor"],
            "max_drawdown_pct": combined_overall["max_drawdown_pct"],
            "total_return_pct": combined_overall["total_return_pct"],
            "avg_pnl_pct": combined_overall["avg_pnl_pct"],
            "binomial_p": combined_overall["binomial_p"],
            "significant": combined_overall["significant"],
            "oos_n_trades": combined_oos["n_trades"],
            "oos_win_rate": combined_oos["win_rate"],
            "oos_sharpe": combined_oos["sharpe"],
            "oos_significant": combined_oos.get("significant", False),
            "verdict": verdict,
            "symbols_tested": len([s for s in symbols_for_strat if s in data]),
        })

    # ===========================================================================
    # FINAL SUMMARY
    # ===========================================================================
    elapsed = time.time() - start_time

    print(f"\n\n{'='*72}")
    print(f"  BACKTEST SUMMARY -- ALL STRATEGIES")
    print(f"  {timestamp} | Elapsed: {elapsed:.1f}s")
    print(f"{'='*72}")

    # Sort by verdict priority then by win rate
    verdict_order = {"PROVEN": 0, "STATISTICALLY SIGNIFICANT": 1,
                     "PROMISING": 2, "INSUFFICIENT DATA": 3, "NO SIGNAL": 4}
    summary_rows.sort(key=lambda r: (verdict_order.get(r["verdict"], 9), -r["win_rate"]))

    print(f"\n  {'#':<3} {'Strategy':<28} {'Trades':<7} {'WR%':<7} {'Sharpe':<8} "
          f"{'PF':<7} {'p-val':<10} {'Verdict':<20}")
    print(f"  {'-'*3} {'-'*28} {'-'*7} {'-'*7} {'-'*8} {'-'*7} {'-'*10} {'-'*20}")

    for row in summary_rows:
        sig_mark = "***" if row["significant"] else ""
        print(f"  {row['index']:<3} {row['name']:<28} {row['n_trades']:<7} "
              f"{row['win_rate']*100:<7.1f} {row['sharpe']:<8.2f} "
              f"{row['profit_factor']:<7.2f} {row['binomial_p']:<10.4f} "
              f"{row['verdict']:<20} {sig_mark}")

    # OOS summary
    oos_rows = [r for r in summary_rows if r["oos_n_trades"] > 0]
    if oos_rows:
        print(f"\n  OUT-OF-SAMPLE VALIDATION:")
        print(f"  {'Strategy':<28} {'OOS Trades':<12} {'OOS WR%':<10} {'OOS Sharpe':<12} {'Sig?':<6}")
        print(f"  {'-'*28} {'-'*12} {'-'*10} {'-'*12} {'-'*6}")
        for r in oos_rows:
            sig_mark = "YES" if r["oos_significant"] else "no"
            print(f"  {r['name']:<28} {r['oos_n_trades']:<12} "
                  f"{r['oos_win_rate']*100:<10.1f} {r['oos_sharpe']:<12.2f} {sig_mark:<6}")

    # Category summary
    proven = [r for r in summary_rows if r["verdict"] == "PROVEN"]
    significant = [r for r in summary_rows if r["verdict"] == "STATISTICALLY SIGNIFICANT"]
    promising = [r for r in summary_rows if r["verdict"] == "PROMISING"]
    insufficient = [r for r in summary_rows if r["verdict"] in ("INSUFFICIENT DATA", "NO SIGNAL")]

    print(f"\n  PROVEN:         {len(proven)} strategies")
    print(f"  SIGNIFICANT:    {len(significant)} strategies")
    print(f"  PROMISING:      {len(promising)} strategies")
    print(f"  INSUFFICIENT:   {len(insufficient)} strategies")

    # Save summary JSON
    summary_output = {
        "backtest_timestamp": timestamp,
        "elapsed_seconds": round(elapsed, 1),
        "period": args.period,
        "total_strategies": len(strategy_keys),
        "symbols_available": list(data.keys()),
        "transaction_costs": TRANSACTION_COSTS,
        "walk_forward_split": "70% in-sample / 30% out-of-sample",
        "strategies": summary_rows,
        "proven_strategies": [r["strategy"] for r in proven],
        "significant_strategies": [r["strategy"] for r in significant],
        "promising_strategies": [r["strategy"] for r in promising],
    }

    summary_path = DATA_DIR / "backtest_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary_output, f, indent=2, default=str)
    print(f"\n  Summary saved: {summary_path}")

    print(f"\n  All per-strategy results saved to: {DATA_DIR}/")
    print(f"  Total elapsed time: {elapsed:.1f}s")
    print("=" * 72)

    return 0


if __name__ == "__main__":
    sys.exit(main())
