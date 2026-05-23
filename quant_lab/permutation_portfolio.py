#!/usr/bin/env python3
"""
Permutation Portfolio Backtester — Massive strategy combination testing.

Integrates:
  - combinatory_backtester.py signal generators (fast, bar-indexed)
  - Pre-computed baby strategy results from battleground/incubator databases
  - $1,000 portfolio with 1% position sizing per trade
  - BTCC exchange fees (0.2% maker / 0.3% taker spot)
  - Multi-metric composite scorecard (Bronze/Silver/Gold tiers)
  - Statistical significance: binomial p-value
  - All results (winners AND losers) stored in SQLite
  - Inverse signal testing for failing strategies
  - 2-way and 3-way ensemble combinations

Cerebrus/Grok architecture:
  Layer 1: Signal generation (bar-indexed signal arrays per strategy)
  Layer 2: Permutation engine (individual, inverse, ensembles)
  Layer 3: Portfolio simulation ($1K, 1% sizing, BTCC fees)
  Layer 4: Scoring & ranking (composite scorecard, tiered winners)

Usage:
    py quant_lab/permutation_portfolio.py
    py quant_lab/permutation_portfolio.py --symbols BTC/USDT ETH/USDT
    py quant_lab/permutation_portfolio.py --top 20
    py quant_lab/permutation_portfolio.py --export results.json
"""

import sqlite3
import json
import sys
import os
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from itertools import combinations
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
CRYPTO_DB = ROOT / "crypto_data.db"
RESULTS_DB = ROOT / "quant_lab" / "permutation_results.db"
OUTPUT_DIR = ROOT / "quant_lab" / "combo_results"

# ─────────────────────────────────────────────────────────────────
# BTCC Fee Model (spot trading)
# ─────────────────────────────────────────────────────────────────

BTCC_FEES = {
    "spot_maker": 0.002,     # 0.20%
    "spot_taker": 0.003,     # 0.30%
    "futures_maker": 0.0003, # 0.03%
    "futures_taker": 0.0006, # 0.06%
}

COMMISSION_PER_SIDE = BTCC_FEES["spot_taker"]  # 0.30% per side
ROUND_TRIP_COST = 2 * COMMISSION_PER_SIDE       # 0.60% round trip
SLIPPAGE_PCT = 0.001    # 0.10% estimated slippage
SPREAD_PCT = 0.0005     # 0.05% typical BTC/ETH spread
TOTAL_ROUND_TRIP = ROUND_TRIP_COST + SLIPPAGE_PCT + SPREAD_PCT  # ~0.75%

# Portfolio parameters
INITIAL_CAPITAL = 1000.0
POSITION_SIZE_PCT = 0.01   # 1% per pick ($10 per trade on $1000)
TP_PCT = 5.0               # 5% take profit
SL_PCT = 3.0               # 3% stop loss
MAX_HOLD_BARS = 10         # 10 bars (days on daily)
MAX_CONCURRENT = 10        # max 10 open positions

# Statistical significance thresholds
MIN_TRADES = 10
P_VALUE_THRESHOLD = 0.05
MIN_WIN_RATE = 0.52


# ─────────────────────────────────────────────────────────────────
# Technical Indicators (from combinatory_backtester)
# ─────────────────────────────────────────────────────────────────

def _rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def _ema(close, period):
    return close.ewm(span=period, adjust=False).mean()

def _sma(close, period):
    return close.rolling(period).mean()

def _atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()

def _bollinger_bands(close, period=20, num_std=2.0):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    return mid + num_std * std, mid, mid - num_std * std


# ─────────────────────────────────────────────────────────────────
# Fast Bar-Indexed Signal Generators
# ─────────────────────────────────────────────────────────────────

def sig_connors_rsi2(close, high, low, volume):
    """Connors RSI-2: BUY when RSI(2) < 5 AND price > 200 SMA."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    rsi2 = _rsi(close, 2)
    sma200 = _sma(close, 200)
    for i in range(200, n):
        if np.isnan(rsi2.iloc[i]) or np.isnan(sma200.iloc[i]):
            continue
        if close.iloc[i] > sma200.iloc[i] and rsi2.iloc[i] < 5:
            signals[i] = 1
        elif close.iloc[i] > sma200.iloc[i] and rsi2.iloc[i] > 95:
            signals[i] = -1
    return signals

def sig_keltner_mean_rev(close, high, low, volume):
    """Keltner Mean Reversion: BUY at lower band touch in uptrend."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    ema20 = _ema(close, 20)
    atr14 = _atr(high, low, close, 14)
    sma200 = _sma(close, 200)
    for i in range(200, n):
        if any(np.isnan(x) for x in [ema20.iloc[i], atr14.iloc[i], sma200.iloc[i]]):
            continue
        lower = ema20.iloc[i] - 2 * atr14.iloc[i]
        upper = ema20.iloc[i] + 2 * atr14.iloc[i]
        if close.iloc[i] > sma200.iloc[i] and low.iloc[i] <= lower:
            signals[i] = 1
        elif close.iloc[i] < sma200.iloc[i] and high.iloc[i] >= upper:
            signals[i] = -1
    return signals

def sig_bollinger_mean_rev(close, high, low, volume):
    """Bollinger Mean Reversion: BUY at lower band, SELL at upper."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    bb_upper, bb_mid, bb_lower = _bollinger_bands(close, 20, 2.0)
    sma200 = _sma(close, 200)
    for i in range(200, n):
        if any(np.isnan(x) for x in [bb_lower.iloc[i], bb_upper.iloc[i], sma200.iloc[i]]):
            continue
        if close.iloc[i] > sma200.iloc[i] and close.iloc[i] <= bb_lower.iloc[i]:
            signals[i] = 1
        elif close.iloc[i] < sma200.iloc[i] and close.iloc[i] >= bb_upper.iloc[i]:
            signals[i] = -1
    return signals

def sig_macd_divergence(close, high, low, volume):
    """MACD Divergence: crossover signals."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    ema12 = _ema(close, 12)
    ema26 = _ema(close, 26)
    macd = ema12 - ema26
    signal_line = _ema(macd, 9)
    for i in range(50, n):
        if np.isnan(macd.iloc[i]) or np.isnan(signal_line.iloc[i]):
            continue
        if macd.iloc[i] > signal_line.iloc[i] and macd.iloc[i-1] <= signal_line.iloc[i-1]:
            signals[i] = 1
        elif macd.iloc[i] < signal_line.iloc[i] and macd.iloc[i-1] >= signal_line.iloc[i-1]:
            signals[i] = -1
    return signals

def sig_vwap_mean_rev(close, high, low, volume):
    """VWAP Mean Reversion: BUY below VWAP, SELL above."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    cum_vol = volume.cumsum()
    cum_vol_price = (close * volume).cumsum()
    vwap = cum_vol_price / cum_vol.replace(0, np.nan)
    atr14 = _atr(high, low, close, 14)
    for i in range(50, n):
        if np.isnan(vwap.iloc[i]) or np.isnan(atr14.iloc[i]) or atr14.iloc[i] == 0:
            continue
        deviation = (close.iloc[i] - vwap.iloc[i]) / atr14.iloc[i]
        if deviation < -2.0:
            signals[i] = 1
        elif deviation > 2.0:
            signals[i] = -1
    return signals

def sig_connors_r3(close, high, low, volume):
    """Connors R3: RSI(3) oversold + uptrend."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    rsi3 = _rsi(close, 3)
    sma200 = _sma(close, 200)
    for i in range(200, n):
        if np.isnan(rsi3.iloc[i]) or np.isnan(sma200.iloc[i]):
            continue
        if close.iloc[i] > sma200.iloc[i] and rsi3.iloc[i] < 10:
            signals[i] = 1
        elif close.iloc[i] > sma200.iloc[i] and rsi3.iloc[i] > 90:
            signals[i] = -1
    return signals

def sig_ema_crossover(close, high, low, volume):
    """EMA 9/21 crossover."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    ema9 = _ema(close, 9)
    ema21 = _ema(close, 21)
    for i in range(30, n):
        if np.isnan(ema9.iloc[i]) or np.isnan(ema21.iloc[i]):
            continue
        if ema9.iloc[i] > ema21.iloc[i] and ema9.iloc[i-1] <= ema21.iloc[i-1]:
            signals[i] = 1
        elif ema9.iloc[i] < ema21.iloc[i] and ema9.iloc[i-1] >= ema21.iloc[i-1]:
            signals[i] = -1
    return signals

def sig_supertrend(close, high, low, volume, period=10, mult=3.0):
    """Supertrend indicator."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    atr_s = _atr(high, low, close, period)
    upper = (high + low) / 2 + mult * atr_s
    lower = (high + low) / 2 - mult * atr_s
    direction = np.ones(n, dtype=int)
    for i in range(1, n):
        if np.isnan(upper.iloc[i]) or np.isnan(lower.iloc[i]):
            continue
        if close.iloc[i] > upper.iloc[i-1]:
            direction[i] = 1
        elif close.iloc[i] < lower.iloc[i-1]:
            direction[i] = -1
        else:
            direction[i] = direction[i-1]
        if direction[i] == 1 and direction[i-1] == -1:
            signals[i] = 1
        elif direction[i] == -1 and direction[i-1] == 1:
            signals[i] = -1
    return signals

def sig_rsi_extreme(close, high, low, volume):
    """RSI extreme reversal: RSI(14) < 25 or > 75."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    rsi14 = _rsi(close, 14)
    for i in range(30, n):
        if np.isnan(rsi14.iloc[i]):
            continue
        if rsi14.iloc[i] < 25:
            signals[i] = 1
        elif rsi14.iloc[i] > 75:
            signals[i] = -1
    return signals

def sig_williams_r(close, high, low, volume, period=14):
    """Williams %R oversold/overbought."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    for i in range(period, n):
        hh = high.iloc[i-period:i+1].max()
        ll = low.iloc[i-period:i+1].min()
        if hh == ll:
            continue
        wr = (hh - close.iloc[i]) / (hh - ll) * -100
        if wr < -80:
            signals[i] = 1
        elif wr > -20:
            signals[i] = -1
    return signals

def sig_stochastic(close, high, low, volume, k_period=14, d_period=3):
    """Stochastic oscillator crossover."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    k_vals = np.full(n, np.nan)
    for i in range(k_period, n):
        hh = high.iloc[i-k_period:i+1].max()
        ll = low.iloc[i-k_period:i+1].min()
        if hh == ll:
            continue
        k_vals[i] = (close.iloc[i] - ll) / (hh - ll) * 100
    k_series = pd.Series(k_vals)
    d_series = k_series.rolling(d_period).mean()
    for i in range(k_period + d_period, n):
        if np.isnan(k_series.iloc[i]) or np.isnan(d_series.iloc[i]):
            continue
        if k_series.iloc[i] < 20 and k_series.iloc[i] > d_series.iloc[i]:
            signals[i] = 1
        elif k_series.iloc[i] > 80 and k_series.iloc[i] < d_series.iloc[i]:
            signals[i] = -1
    return signals

def sig_volume_breakout(close, high, low, volume):
    """Volume breakout: price breakout + 2x average volume."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    sma20 = _sma(close, 20)
    vol_sma = volume.rolling(20).mean()
    for i in range(30, n):
        if np.isnan(sma20.iloc[i]) or np.isnan(vol_sma.iloc[i]) or vol_sma.iloc[i] == 0:
            continue
        vol_ratio = volume.iloc[i] / vol_sma.iloc[i]
        if vol_ratio > 2.0 and close.iloc[i] > close.iloc[i-1] and close.iloc[i] > sma20.iloc[i]:
            signals[i] = 1
        elif vol_ratio > 2.0 and close.iloc[i] < close.iloc[i-1] and close.iloc[i] < sma20.iloc[i]:
            signals[i] = -1
    return signals

def sig_doji_reversal(close, high, low, volume):
    """Doji candle reversal pattern."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    rsi14 = _rsi(close, 14)
    for i in range(30, n):
        body = abs(close.iloc[i] - close.iloc[i-1])  # using open proxy
        wick = high.iloc[i] - low.iloc[i]
        if wick == 0:
            continue
        if body / wick < 0.1 and wick > 0:  # doji-like
            if not np.isnan(rsi14.iloc[i]):
                if rsi14.iloc[i] < 30:
                    signals[i] = 1
                elif rsi14.iloc[i] > 70:
                    signals[i] = -1
    return signals

def sig_triple_ema(close, high, low, volume):
    """Triple EMA stack (9/21/50) alignment."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    ema9 = _ema(close, 9)
    ema21 = _ema(close, 21)
    ema50 = _ema(close, 50)
    for i in range(60, n):
        if any(np.isnan(x) for x in [ema9.iloc[i], ema21.iloc[i], ema50.iloc[i]]):
            continue
        # All EMAs aligned bullish
        if ema9.iloc[i] > ema21.iloc[i] > ema50.iloc[i]:
            # Was NOT aligned before
            if not (ema9.iloc[i-1] > ema21.iloc[i-1] > ema50.iloc[i-1]):
                signals[i] = 1
        elif ema9.iloc[i] < ema21.iloc[i] < ema50.iloc[i]:
            if not (ema9.iloc[i-1] < ema21.iloc[i-1] < ema50.iloc[i-1]):
                signals[i] = -1
    return signals

def sig_mean_reversion_zscore(close, high, low, volume, lookback=50):
    """Z-score mean reversion."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    for i in range(lookback, n):
        window = close.iloc[i-lookback:i+1]
        mean = window.mean()
        std = window.std()
        if std == 0:
            continue
        z = (close.iloc[i] - mean) / std
        if z < -2.0:
            signals[i] = 1
        elif z > 2.0:
            signals[i] = -1
    return signals

def sig_ichimoku(close, high, low, volume):
    """Ichimoku cloud breakout."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    # Tenkan-sen (9-period)
    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
    # Kijun-sen (26-period)
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
    for i in range(30, n):
        if np.isnan(tenkan.iloc[i]) or np.isnan(kijun.iloc[i]):
            continue
        if tenkan.iloc[i] > kijun.iloc[i] and tenkan.iloc[i-1] <= kijun.iloc[i-1]:
            signals[i] = 1
        elif tenkan.iloc[i] < kijun.iloc[i] and tenkan.iloc[i-1] >= kijun.iloc[i-1]:
            signals[i] = -1
    return signals

def sig_donchian_breakout(close, high, low, volume, period=20):
    """Donchian channel breakout."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    for i in range(period, n):
        hh = high.iloc[i-period:i].max()
        ll = low.iloc[i-period:i].min()
        if close.iloc[i] > hh:
            signals[i] = 1
        elif close.iloc[i] < ll:
            signals[i] = -1
    return signals

def sig_adx_trend(close, high, low, volume):
    """ADX trend filter + RSI."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    rsi14 = _rsi(close, 14)
    ema50 = _ema(close, 50)
    # Simplified ADX proxy: use directional movement
    for i in range(60, n):
        if np.isnan(rsi14.iloc[i]) or np.isnan(ema50.iloc[i]):
            continue
        # Strong trend: price consistently above/below EMA50
        bars_above = sum(1 for j in range(max(0,i-14), i+1)
                        if close.iloc[j] > ema50.iloc[j])
        trend_strength = bars_above / 15
        if trend_strength > 0.8 and rsi14.iloc[i] < 40:  # pullback in uptrend
            signals[i] = 1
        elif trend_strength < 0.2 and rsi14.iloc[i] > 60:  # rally in downtrend
            signals[i] = -1
    return signals

def sig_consecutive_down(close, high, low, volume, n_days=3):
    """Buy after N consecutive down days in uptrend."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    sma200 = _sma(close, 200)
    for i in range(200, n):
        if np.isnan(sma200.iloc[i]):
            continue
        if close.iloc[i] > sma200.iloc[i]:
            consec = 0
            for j in range(1, n_days + 1):
                if i - j >= 0 and close.iloc[i-j+1] < close.iloc[i-j]:
                    consec += 1
            if consec >= n_days:
                signals[i] = 1
    return signals

def sig_pivot_point(close, high, low, volume):
    """Pivot point support/resistance."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    for i in range(1, n):
        pivot = (high.iloc[i-1] + low.iloc[i-1] + close.iloc[i-1]) / 3
        s1 = 2 * pivot - high.iloc[i-1]
        r1 = 2 * pivot - low.iloc[i-1]
        if close.iloc[i] <= s1 and close.iloc[i] > close.iloc[i-1]:
            signals[i] = 1
        elif close.iloc[i] >= r1 and close.iloc[i] < close.iloc[i-1]:
            signals[i] = -1
    return signals

def sig_funding_rate_proxy(close, high, low, volume):
    """Funding rate proxy: extreme volume + price deviation."""
    n = len(close)
    signals = np.zeros(n, dtype=int)
    vol_sma = volume.rolling(20).mean()
    sma20 = _sma(close, 20)
    for i in range(30, n):
        if np.isnan(vol_sma.iloc[i]) or vol_sma.iloc[i] == 0:
            continue
        vol_ratio = volume.iloc[i] / vol_sma.iloc[i]
        price_dev = (close.iloc[i] - sma20.iloc[i]) / sma20.iloc[i] * 100
        # Overleveraged longs: high volume + big premium
        if vol_ratio > 3.0 and price_dev > 5:
            signals[i] = -1  # Short the overleveraged
        elif vol_ratio > 3.0 and price_dev < -5:
            signals[i] = 1   # Buy the capitulation
    return signals


# All strategies registry
STRATEGIES = {
    # TIER 1 PROVEN
    "connors_rsi2": sig_connors_rsi2,
    "keltner_mean_rev": sig_keltner_mean_rev,
    "bollinger_mean_rev": sig_bollinger_mean_rev,
    "macd_divergence": sig_macd_divergence,
    "vwap_mean_rev": sig_vwap_mean_rev,
    "connors_r3": sig_connors_r3,
    # TIER 2 / WATCH
    "rsi_extreme": sig_rsi_extreme,
    "williams_r": sig_williams_r,
    "supertrend": sig_supertrend,
    # FAILING / GRAVEYARD (inverse candidates)
    "ema_crossover": sig_ema_crossover,
    "triple_ema": sig_triple_ema,
    "ichimoku": sig_ichimoku,
    # ADDITIONAL STRATEGIES
    "stochastic": sig_stochastic,
    "volume_breakout": sig_volume_breakout,
    "doji_reversal": sig_doji_reversal,
    "mean_rev_zscore": sig_mean_reversion_zscore,
    "donchian_breakout": sig_donchian_breakout,
    "adx_trend": sig_adx_trend,
    "consecutive_down": sig_consecutive_down,
    "pivot_point": sig_pivot_point,
    "funding_rate_proxy": sig_funding_rate_proxy,
}

# Which strategies are known losers (candidates for inverse testing)
KNOWN_LOSERS = {
    "ema_crossover", "triple_ema", "ichimoku", "doji_reversal",
    "donchian_breakout", "pivot_point", "funding_rate_proxy",
}

KNOWN_WINNERS = {
    "connors_rsi2", "keltner_mean_rev", "bollinger_mean_rev",
    "macd_divergence", "vwap_mean_rev", "connors_r3",
}


# ─────────────────────────────────────────────────────────────────
# Results Database
# ─────────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(str(RESULTS_DB))
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS combo_backtest (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            combo_name TEXT NOT NULL,
            combo_type TEXT NOT NULL,
            strategies TEXT NOT NULL,
            symbols_tested TEXT NOT NULL,
            total_trades INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0,
            gross_pnl_pct REAL DEFAULT 0,
            net_pnl_pct REAL DEFAULT 0,
            sharpe REAL DEFAULT 0,
            profit_factor REAL DEFAULT 0,
            max_drawdown_pct REAL DEFAULT 0,
            avg_trade_pnl REAL DEFAULT 0,
            calmar_ratio REAL DEFAULT 0,
            expectancy REAL DEFAULT 0,
            p_value REAL DEFAULT 1.0,
            kelly_pct REAL DEFAULT 0,
            portfolio_final REAL DEFAULT 0,
            portfolio_return_pct REAL DEFAULT 0,
            composite_score REAL DEFAULT 0,
            tier TEXT DEFAULT 'ELIMINATE',
            is_significant INTEGER DEFAULT 0,
            is_winner INTEGER DEFAULT 0,
            failure_reason TEXT,
            tested_at TEXT NOT NULL,
            UNIQUE(combo_name)
        );

        CREATE TABLE IF NOT EXISTS combo_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            combo_name TEXT NOT NULL,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL NOT NULL,
            entry_bar INTEGER,
            exit_bar INTEGER,
            entry_date TEXT,
            exit_date TEXT,
            gross_pnl_pct REAL,
            net_pnl_pct REAL,
            commission_paid REAL,
            exit_reason TEXT,
            position_size REAL,
            portfolio_value_after REAL
        );

        CREATE INDEX IF NOT EXISTS idx_cb_tier ON combo_backtest(tier);
        CREATE INDEX IF NOT EXISTS idx_cb_score ON combo_backtest(composite_score);
        CREATE INDEX IF NOT EXISTS idx_ct_combo ON combo_trades(combo_name);
    """)
    conn.commit()
    return conn


# ─────────────────────────────────────────────────────────────────
# Load Historical Data
# ─────────────────────────────────────────────────────────────────

def load_ohlcv(symbol):
    if not CRYPTO_DB.exists():
        return None
    conn = sqlite3.connect(str(CRYPTO_DB))
    for pair_fmt in [symbol, symbol.replace("USDT", "/USDT"), symbol.replace("/", "")]:
        df = pd.read_sql_query(
            "SELECT * FROM klines WHERE pair=? ORDER BY timestamp",
            conn, params=[pair_fmt])
        if not df.empty:
            conn.close()
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df.dropna(subset=["close"])
            return df
    conn.close()
    return None


# ─────────────────────────────────────────────────────────────────
# Portfolio Simulation
# ─────────────────────────────────────────────────────────────────

@dataclass
class TradeResult:
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    entry_bar: int
    exit_bar: int
    entry_date: str
    exit_date: str
    gross_pnl_pct: float
    net_pnl_pct: float
    commission_paid: float
    exit_reason: str
    position_size: float
    portfolio_value_after: float


def simulate_portfolio(signals_by_symbol, ohlcv_by_symbol, combo_name):
    capital = INITIAL_CAPITAL
    trades = []
    open_positions = []

    max_bars = min(len(df) for df in ohlcv_by_symbol.values()) if ohlcv_by_symbol else 0

    for bar in range(max_bars):
        # Check open positions
        still_open = []
        for pos in open_positions:
            sym = pos["symbol"]
            df = ohlcv_by_symbol[sym]
            if bar >= len(df):
                still_open.append(pos)
                continue

            current_high = float(df["high"].iloc[bar])
            current_low = float(df["low"].iloc[bar])
            current_close = float(df["close"].iloc[bar])
            bars_held = bar - pos["entry_bar"]

            exit_price = None
            exit_reason = None

            if pos["direction"] == "LONG":
                if current_high >= pos["tp"]:
                    exit_price, exit_reason = pos["tp"], "TP"
                elif current_low <= pos["sl"]:
                    exit_price, exit_reason = pos["sl"], "SL"
            else:
                if current_low <= pos["tp"]:
                    exit_price, exit_reason = pos["tp"], "TP"
                elif current_high >= pos["sl"]:
                    exit_price, exit_reason = pos["sl"], "SL"

            if not exit_reason and bars_held >= MAX_HOLD_BARS:
                exit_price, exit_reason = current_close, "TIME_EXIT"

            if exit_reason:
                if pos["direction"] == "LONG":
                    gross_pnl = (exit_price / pos["entry_price"] - 1)
                else:
                    gross_pnl = (1 - exit_price / pos["entry_price"])

                net_pnl = gross_pnl - TOTAL_ROUND_TRIP
                capital += pos["size"] * (1 + net_pnl)

                exit_date = str(df["timestamp"].iloc[bar]) if bar < len(df) else ""
                trades.append(TradeResult(
                    symbol=sym, direction=pos["direction"],
                    entry_price=pos["entry_price"], exit_price=round(exit_price, 8),
                    entry_bar=pos["entry_bar"], exit_bar=bar,
                    entry_date=pos["entry_date"], exit_date=exit_date,
                    gross_pnl_pct=round(gross_pnl * 100, 4),
                    net_pnl_pct=round(net_pnl * 100, 4),
                    commission_paid=round(pos["size"] * TOTAL_ROUND_TRIP, 4),
                    exit_reason=exit_reason,
                    position_size=round(pos["size"], 4),
                    portfolio_value_after=round(capital, 2),
                ))
            else:
                still_open.append(pos)

        open_positions = still_open

        # Open new positions
        if len(open_positions) >= MAX_CONCURRENT:
            continue

        for sym, signals in signals_by_symbol.items():
            if bar >= len(signals) or signals[bar] == 0:
                continue
            if len(open_positions) >= MAX_CONCURRENT:
                break
            if any(p["symbol"] == sym for p in open_positions):
                continue

            df = ohlcv_by_symbol[sym]
            if bar >= len(df):
                continue

            entry_price = float(df["close"].iloc[bar])
            if entry_price <= 0:
                continue

            size = capital * POSITION_SIZE_PCT
            if size < 1.0:
                continue

            direction = "LONG" if signals[bar] == 1 else "SHORT"
            if direction == "LONG":
                tp = entry_price * (1 + TP_PCT / 100)
                sl = entry_price * (1 - SL_PCT / 100)
            else:
                tp = entry_price * (1 - TP_PCT / 100)
                sl = entry_price * (1 + SL_PCT / 100)

            capital -= size
            entry_date = str(df["timestamp"].iloc[bar]) if bar < len(df) else ""
            open_positions.append({
                "symbol": sym, "direction": direction,
                "entry_price": entry_price, "tp": tp, "sl": sl,
                "size": size, "entry_bar": bar, "entry_date": entry_date,
            })

    # Force-close remaining
    for pos in open_positions:
        sym = pos["symbol"]
        df = ohlcv_by_symbol[sym]
        last_bar = len(df) - 1
        exit_price = float(df["close"].iloc[last_bar])
        if pos["direction"] == "LONG":
            gross_pnl = (exit_price / pos["entry_price"] - 1)
        else:
            gross_pnl = (1 - exit_price / pos["entry_price"])
        net_pnl = gross_pnl - TOTAL_ROUND_TRIP
        capital += pos["size"] * (1 + net_pnl)
        trades.append(TradeResult(
            symbol=sym, direction=pos["direction"],
            entry_price=pos["entry_price"], exit_price=round(exit_price, 8),
            entry_bar=pos["entry_bar"], exit_bar=last_bar,
            entry_date=pos["entry_date"],
            exit_date=str(df["timestamp"].iloc[last_bar]),
            gross_pnl_pct=round(gross_pnl * 100, 4),
            net_pnl_pct=round(net_pnl * 100, 4),
            commission_paid=round(pos["size"] * TOTAL_ROUND_TRIP, 4),
            exit_reason="FORCE_CLOSE",
            position_size=round(pos["size"], 4),
            portfolio_value_after=round(capital, 2),
        ))

    metrics = compute_metrics(trades, capital)
    return trades, metrics


def compute_metrics(trades, final_capital):
    from scipy import stats as scipy_stats

    if not trades:
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0,
            "gross_pnl_pct": 0, "net_pnl_pct": 0, "sharpe": 0,
            "profit_factor": 0, "max_drawdown_pct": 0, "avg_trade_pnl": 0,
            "calmar_ratio": 0, "expectancy": 0,
            "p_value": 1.0, "kelly_pct": 0, "portfolio_final": INITIAL_CAPITAL,
            "portfolio_return_pct": 0, "composite_score": 0, "tier": "ELIMINATE",
            "is_significant": False, "is_winner": False,
            "failure_reason": "NO_TRADES",
        }

    net_pnls = [t.net_pnl_pct for t in trades]
    gross_pnls = [t.gross_pnl_pct for t in trades]
    wins = sum(1 for p in net_pnls if p > 0)
    total = len(net_pnls)
    wr = wins / total if total else 0

    gross_total = sum(gross_pnls)
    net_total = sum(net_pnls)
    avg_pnl = net_total / total if total else 0

    # Sharpe
    if len(net_pnls) >= 2:
        mean_r = np.mean(net_pnls)
        std_r = np.std(net_pnls, ddof=1)
        sharpe = (mean_r / std_r) * np.sqrt(252) if std_r > 0 else 0
    else:
        sharpe = 0

    # Profit factor
    gross_wins = sum(p for p in net_pnls if p > 0)
    gross_losses = abs(sum(p for p in net_pnls if p <= 0))
    pf = gross_wins / gross_losses if gross_losses > 0 else (999 if gross_wins > 0 else 0)

    # Max drawdown
    equity = INITIAL_CAPITAL
    peak = equity
    max_dd = 0
    for t in trades:
        equity = t.portfolio_value_after
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)

    portfolio_return = (final_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    # Calmar ratio
    cagr = portfolio_return / 100  # simplified
    calmar = cagr / max_dd if max_dd > 0 else 0

    # Expectancy (% per trade after fees)
    expectancy = avg_pnl

    # P-value
    if total >= MIN_TRADES:
        p_value = scipy_stats.binomtest(wins, total, 0.5, alternative="greater").pvalue
    else:
        p_value = 1.0

    # Kelly
    avg_win = np.mean([p for p in net_pnls if p > 0]) if wins > 0 else 0
    avg_loss = abs(np.mean([p for p in net_pnls if p <= 0])) if (total - wins) > 0 else 1
    if avg_loss > 0 and avg_win > 0:
        b = avg_win / avg_loss
        kelly = wr - (1 - wr) / b
    else:
        kelly = 0

    # Composite score (Grok formula)
    score = (
        min(sharpe, 5) * 20 +          # Cap Sharpe contribution at 100
        min(pf, 5) * 15 +              # Cap PF contribution at 75
        max(0, (30 - max_dd * 100)) * 1.5 +  # DD penalty
        wr * 50 +                       # Win rate (50% = 25 pts)
        min(total, 500) / 20 +          # Trade count (max 25 pts)
        max(0, calmar) * 10            # Calmar bonus
    )

    # Tier assignment
    if score > 85:
        tier = "GOLD"
    elif score > 65:
        tier = "SILVER"
    elif score > 45:
        tier = "BRONZE"
    else:
        tier = "ELIMINATE"

    is_significant = (total >= MIN_TRADES and p_value < P_VALUE_THRESHOLD
                      and wr > MIN_WIN_RATE)
    is_winner = is_significant and sharpe > 0.5 and pf > 1.2

    # Failure reason
    failure_reason = None
    if total < MIN_TRADES:
        failure_reason = f"INSUFFICIENT_TRADES ({total})"
    elif wr <= MIN_WIN_RATE:
        failure_reason = f"LOW_WIN_RATE ({wr:.1%})"
    elif p_value >= P_VALUE_THRESHOLD:
        failure_reason = f"NOT_SIGNIFICANT (p={p_value:.4f})"
    elif sharpe <= 0.5:
        failure_reason = f"LOW_SHARPE ({sharpe:.2f})"
    elif pf <= 1.2:
        failure_reason = f"LOW_PROFIT_FACTOR ({pf:.2f})"

    return {
        "total_trades": total, "wins": wins, "losses": total - wins,
        "win_rate": round(wr, 4),
        "gross_pnl_pct": round(gross_total, 4), "net_pnl_pct": round(net_total, 4),
        "sharpe": round(sharpe, 4), "profit_factor": round(pf, 4),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "avg_trade_pnl": round(avg_pnl, 4),
        "calmar_ratio": round(calmar, 4), "expectancy": round(expectancy, 4),
        "p_value": round(p_value, 6), "kelly_pct": round(kelly * 100, 2),
        "portfolio_final": round(final_capital, 2),
        "portfolio_return_pct": round(portfolio_return, 2),
        "composite_score": round(score, 2), "tier": tier,
        "is_significant": is_significant, "is_winner": is_winner,
        "failure_reason": failure_reason,
    }


def save_results(conn, combo_name, combo_type, strategies, symbols, trades, metrics):
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO combo_backtest (
            combo_name, combo_type, strategies, symbols_tested,
            total_trades, wins, losses, win_rate,
            gross_pnl_pct, net_pnl_pct, sharpe, profit_factor,
            max_drawdown_pct, avg_trade_pnl, calmar_ratio, expectancy,
            p_value, kelly_pct, portfolio_final, portfolio_return_pct,
            composite_score, tier, is_significant, is_winner,
            failure_reason, tested_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        combo_name, combo_type, json.dumps(strategies), json.dumps(symbols),
        metrics["total_trades"], metrics["wins"], metrics["losses"],
        metrics["win_rate"], metrics["gross_pnl_pct"], metrics["net_pnl_pct"],
        metrics["sharpe"], metrics["profit_factor"], metrics["max_drawdown_pct"],
        metrics["avg_trade_pnl"], metrics["calmar_ratio"], metrics["expectancy"],
        metrics["p_value"], metrics["kelly_pct"],
        metrics["portfolio_final"], metrics["portfolio_return_pct"],
        metrics["composite_score"], metrics["tier"],
        int(metrics["is_significant"]), int(metrics["is_winner"]),
        metrics["failure_reason"], now,
    ))

    if metrics["is_winner"] or metrics.get("is_significant"):
        for t in trades:
            conn.execute("""
                INSERT INTO combo_trades (
                    combo_name, symbol, direction, entry_price, exit_price,
                    entry_bar, exit_bar, entry_date, exit_date,
                    gross_pnl_pct, net_pnl_pct, commission_paid,
                    exit_reason, position_size, portfolio_value_after
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                combo_name, t.symbol, t.direction, t.entry_price, t.exit_price,
                t.entry_bar, t.exit_bar, t.entry_date, t.exit_date,
                t.gross_pnl_pct, t.net_pnl_pct, t.commission_paid,
                t.exit_reason, t.position_size, t.portfolio_value_after,
            ))
    conn.commit()


# ─────────────────────────────────────────────────────────────────
# Ensemble Signal Generation
# ─────────────────────────────────────────────────────────────────

def make_ensemble(signal_arrays, threshold=2):
    if not signal_arrays:
        return np.zeros(0, dtype=int)
    length = min(len(s) for s in signal_arrays)
    result = np.zeros(length, dtype=int)
    for i in range(length):
        buys = sum(1 for s in signal_arrays if i < len(s) and s[i] == 1)
        sells = sum(1 for s in signal_arrays if i < len(s) and s[i] == -1)
        if buys >= threshold:
            result[i] = 1
        elif sells >= threshold:
            result[i] = -1
    return result


# ─────────────────────────────────────────────────────────────────
# Main Runner
# ─────────────────────────────────────────────────────────────────

def run(symbols=None, top_n=30, export_path=None, skip_ensembles=False):
    if symbols is None:
        symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "XRP/USDT"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 100)
    print("  PERMUTATION PORTFOLIO BACKTESTER")
    print(f"  Portfolio: ${INITIAL_CAPITAL:,.0f} | Position: {POSITION_SIZE_PCT*100:.0f}% per trade")
    print(f"  Fees: BTCC {COMMISSION_PER_SIDE*100:.1f}%/side = {TOTAL_ROUND_TRIP*100:.2f}% round-trip")
    print(f"  TP: {TP_PCT}% | SL: {SL_PCT}% | Max hold: {MAX_HOLD_BARS} bars")
    print(f"  Strategies: {len(STRATEGIES)} | Symbols: {len(symbols)}")
    print("=" * 100)

    # Load data
    print("\n[1/5] Loading OHLCV data...")
    ohlcv = {}
    for sym in symbols:
        df = load_ohlcv(sym)
        if df is not None and len(df) > 200:
            ohlcv[sym] = df
            print(f"  {sym}: {len(df)} bars")

    if not ohlcv:
        print("[!] No data. Aborting.")
        return

    # Generate signals
    print(f"\n[2/5] Generating {len(STRATEGIES)} x {len(ohlcv)} signal arrays...")
    all_signals = {}
    for strat_name, strat_fn in STRATEGIES.items():
        all_signals[strat_name] = {}
        for sym, df in ohlcv.items():
            close = df["close"]
            high = df["high"]
            low = df["low"]
            vol = df["volume"]
            signals = strat_fn(close, high, low, vol)
            all_signals[strat_name][sym] = signals

        total = sum(np.count_nonzero(all_signals[strat_name][s])
                   for s in all_signals[strat_name])
        label = "WINNER" if strat_name in KNOWN_WINNERS else (
            "LOSER" if strat_name in KNOWN_LOSERS else "")
        if total > 0:
            print(f"  {strat_name}: {total} signals {label}")

    conn = init_db()
    combos_tested = 0
    winners_found = 0

    # Phase 1: Individual + Inverse
    print("\n[3/5] Phase 1: Individual & Inverse strategies...")
    for strat_name in STRATEGIES:
        for mode in ["ORIGINAL", "INVERSE"]:
            sym_signals = {}
            for sym in ohlcv:
                s = all_signals[strat_name][sym]
                sym_signals[sym] = -s if mode == "INVERSE" else s

            total_s = sum(np.count_nonzero(sym_signals[s]) for s in sym_signals)
            if total_s < 3:
                continue

            cname = f"{mode}({strat_name})"
            trades, metrics = simulate_portfolio(sym_signals, ohlcv, cname)
            save_results(conn, cname, mode, [strat_name], list(ohlcv.keys()),
                        trades, metrics)
            combos_tested += 1

            if metrics["tier"] in ("GOLD", "SILVER"):
                winners_found += 1
                print(f"  {metrics['tier']} {cname} | Sharpe {metrics['sharpe']:.2f} "
                      f"WR {metrics['win_rate']:.1%} PF {metrics['profit_factor']:.2f} "
                      f"Score {metrics['composite_score']:.0f} "
                      f"${metrics['portfolio_final']:.0f}")

    print(f"  Phase 1: {combos_tested} tested, {winners_found} Silver+")

    # Phase 2: 2-way ensembles
    if not skip_ensembles:
        print("\n[4/5] Phase 2: 2-way ensembles...")
        active = [s for s in STRATEGIES
                 if sum(np.count_nonzero(all_signals[s][sym]) for sym in ohlcv) >= 5]
        p2_tested = 0
        p2_winners = 0

        for s1, s2 in combinations(active, 2):
            for inv_mode in ["", "INV_"]:
                sym_signals = {}
                for sym in ohlcv:
                    a1 = all_signals[s1][sym]
                    a2 = -all_signals[s2][sym] if inv_mode else all_signals[s2][sym]
                    sym_signals[sym] = make_ensemble([a1, a2], 2)

                total_s = sum(np.count_nonzero(sym_signals.get(s, np.array([])))
                             for s in sym_signals)
                if total_s < 3:
                    continue

                cname = f"E2({s1}+{inv_mode}{s2})"
                trades, metrics = simulate_portfolio(sym_signals, ohlcv, cname)
                save_results(conn, cname, "ENSEMBLE_2",
                            [s1, f"{inv_mode}{s2}"], list(ohlcv.keys()),
                            trades, metrics)
                p2_tested += 1

                if metrics["tier"] in ("GOLD", "SILVER"):
                    p2_winners += 1
                    print(f"  {metrics['tier']} {cname} | Sharpe {metrics['sharpe']:.2f} "
                          f"WR {metrics['win_rate']:.1%} Score {metrics['composite_score']:.0f}")

            if p2_tested % 50 == 0 and p2_tested > 0:
                conn.commit()

        combos_tested += p2_tested
        winners_found += p2_winners
        print(f"  Phase 2: {p2_tested} tested, {p2_winners} Silver+")

        # Phase 3: 3-way (top 12 strategies only)
        print("\n  Phase 3: 3-way ensembles (top 12)...")
        strat_activity = [(s, sum(np.count_nonzero(all_signals[s][sym])
                                  for sym in ohlcv)) for s in active]
        strat_activity.sort(key=lambda x: x[1], reverse=True)
        top12 = [s for s, _ in strat_activity[:12]]
        p3_tested = 0
        p3_winners = 0

        for s1, s2, s3 in combinations(top12, 3):
            sym_signals = {}
            for sym in ohlcv:
                a1 = all_signals[s1][sym]
                a2 = all_signals[s2][sym]
                a3 = all_signals[s3][sym]
                sym_signals[sym] = make_ensemble([a1, a2, a3], 2)

            total_s = sum(np.count_nonzero(sym_signals.get(s, np.array([])))
                         for s in sym_signals)
            if total_s < 3:
                continue

            cname = f"E3({s1}+{s2}+{s3})"
            trades, metrics = simulate_portfolio(sym_signals, ohlcv, cname)
            save_results(conn, cname, "ENSEMBLE_3", [s1, s2, s3],
                        list(ohlcv.keys()), trades, metrics)
            p3_tested += 1
            if metrics["tier"] in ("GOLD", "SILVER"):
                p3_winners += 1
                print(f"  {metrics['tier']} {cname} | Sharpe {metrics['sharpe']:.2f} "
                      f"Score {metrics['composite_score']:.0f}")

        combos_tested += p3_tested
        winners_found += p3_winners
        print(f"  Phase 3: {p3_tested} tested, {p3_winners} Silver+")

    # Final report
    print(f"\n\n{'='*100}")
    print(f"  FINAL RESULTS — {combos_tested} combos tested")
    print(f"{'='*100}")

    # Top results by composite score
    top = conn.execute("""
        SELECT * FROM combo_backtest
        WHERE total_trades >= ?
        ORDER BY composite_score DESC LIMIT ?
    """, (MIN_TRADES, top_n)).fetchall()

    if top:
        print(f"\n  {'Tier':<7} {'Combo':<50} {'Score':>6} {'Sharpe':>7} {'WR%':>6} "
              f"{'PF':>6} {'MaxDD':>6} {'Trades':>6} {'p-val':>7} {'$Final':>8}")
        print("  " + "-" * 120)
        for row in top:
            print(f"  {row['tier']:<7} {row['combo_name'][:48]:<50} "
                  f"{row['composite_score']:>6.1f} {row['sharpe']:>7.2f} "
                  f"{row['win_rate']*100:>5.1f}% {row['profit_factor']:>6.2f} "
                  f"{row['max_drawdown_pct']:>5.1f}% {row['total_trades']:>6} "
                  f"{row['p_value']:>7.4f} ${row['portfolio_final']:>7.0f}")

    # Tier summary
    for tier in ["GOLD", "SILVER", "BRONZE", "ELIMINATE"]:
        count = conn.execute(
            "SELECT COUNT(*) FROM combo_backtest WHERE tier=?", (tier,)
        ).fetchone()[0]
        if count > 0:
            print(f"\n  {tier}: {count} combos")

    # Failure breakdown
    failures = conn.execute("""
        SELECT failure_reason, COUNT(*) as cnt FROM combo_backtest
        WHERE failure_reason IS NOT NULL GROUP BY failure_reason
        ORDER BY cnt DESC LIMIT 8
    """).fetchall()
    if failures:
        print(f"\n  FAILURE BREAKDOWN:")
        for f in failures:
            print(f"    {f['failure_reason']}: {f['cnt']}")

    # Export
    if export_path:
        data = {
            "config": {
                "capital": INITIAL_CAPITAL, "position_pct": POSITION_SIZE_PCT,
                "btcc_cost": TOTAL_ROUND_TRIP, "tp": TP_PCT, "sl": SL_PCT,
                "symbols": list(ohlcv.keys()), "strategies": len(STRATEGIES),
                "combos_tested": combos_tested,
            },
            "tiers": {},
            "top_results": [],
            "generated": datetime.now(timezone.utc).isoformat(),
        }
        for tier in ["GOLD", "SILVER", "BRONZE"]:
            rows = conn.execute(
                "SELECT * FROM combo_backtest WHERE tier=? ORDER BY composite_score DESC",
                (tier,)).fetchall()
            data["tiers"][tier] = [dict(r) for r in rows]
        for r in top:
            data["top_results"].append(dict(r))
        Path(export_path).write_text(json.dumps(data, indent=2, default=str))
        print(f"\n  Exported to: {export_path}")

    print(f"\n  DB: {RESULTS_DB}")
    conn.close()
    return combos_tested, winners_found


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Permutation Portfolio Backtester")
    parser.add_argument("--symbols", nargs="+", default=None)
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--export", type=str, default=None)
    parser.add_argument("--skip-ensembles", action="store_true")
    args = parser.parse_args()
    run(symbols=args.symbols, top_n=args.top, export_path=args.export,
        skip_ensembles=args.skip_ensembles)
