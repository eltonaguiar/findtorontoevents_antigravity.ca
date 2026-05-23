#!/usr/bin/env python3
"""
KIMI Rise of the Claw — Vectorized Backtest Engine v1
======================================================
Runs all 20 tournament algorithms over 5 years of historical daily OHLCV data.
Vectorised NumPy/Pandas operations — targets < 2 minutes total runtime.

Outputs:
  data/backtest_rankings.json  — scored results for tournament dashboard
  data/backtest_detail.json    — per-strategy trade-by-trade summary

Usage:
  python backtest_engine.py                     # full 5yr backtest
  python backtest_engine.py --period 1y         # quick 1yr sanity check
  python backtest_engine.py --strategies macd   # single strategy

Elimination threshold:
  Requires  > 20 trades + Sharpe > 0.5 to survive Week 1
  Requires  > 50 trades + win rate >= 55%  to be "promoted"

Requires: yfinance, pandas, numpy
Python 3.11+
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCRIPT_DIR  = Path(__file__).resolve().parent
DATA_DIR    = SCRIPT_DIR / "data"

STOP_LOSS    = -0.08   # -8%
TAKE_PROFIT  =  0.15   # +15%
MAX_HOLD     = 30      # days
CAPITAL      = 10_000.0
ALLOC_PER    = 2_000.0
MAX_POS      = 3

PROMOTE_TRADES   = 50
PROMOTE_WINRATE  = 55.0

# ─── Symbol universes (same as live_scanner.py) ─────────────────────────────

STOCKS_ETF = [
    "SPY","QQQ","VTI","IWM","DIA",
    "XLK","XLF","XLE","XLV","XLI","ARKK",
    "SOXX","XBI","XRT","JETS",
    "TQQQ","LABU","UVXY",
    "GLD","SLV","TLT","HYG",
    "AAPL","MSFT","NVDA","AMD","INTC",
    "META","GOOGL","AMZN","NFLX",
    "TSLA","COIN","MSTR","SHOP","SQ",
    "UBER","PYPL","ROKU",
    "JPM","BAC","XOM","CVX",
]
CRYPTO = [
    "BTC-USD","ETH-USD","BNB-USD","XRP-USD","SOL-USD",
    "ADA-USD","AVAX-USD","DOT-USD","LINK-USD","MATIC-USD",
    "LTC-USD","TRX-USD","ETC-USD","BCH-USD","ATOM-USD",
    "NEAR-USD","ALGO-USD","FIL-USD","ICP-USD","VET-USD",
    "HBAR-USD","THETA-USD","GRT-USD","ZEC-USD","DASH-USD",
    "APT-USD","OP-USD",
    "DOGE-USD","SHIB-USD","PEPE-USD",
    "FLOKI-USD","BONK-USD",
    "SAND-USD","MANA-USD","ENJ-USD","CHZ-USD",
]
FOREX = [
    "EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X",
    "AUDUSD=X","USDCAD=X","NZDUSD=X",
    "EURJPY=X","GBPJPY=X","EURGBP=X",
    "AUDJPY=X","NZDJPY=X","CADJPY=X",
    "USDMXN=X","USDZAR=X",
]
PENNY = [
    "GME","AMC","PLTR","SOFI","HOOD","BBAI",
    "MARA","RIOT","CLSK","BTBT",
    "RIVN","LCID","NKLA",
    "XPEV","NIO",
    "NVAX","BNGO",
    "SNDL","CLOV","SPCE","UWMC",
]

PAIR_MAP = {
    "SPY":"QQQ","QQQ":"IWM","IWM":"SPY",
    "XLK":"XLF","XLF":"XLE",
    "GLD":"SLV","SLV":"GLD","TLT":"HYG","HYG":"TLT",
    "BTC-USD":"ETH-USD","ETH-USD":"SOL-USD",
    "SOL-USD":"ADA-USD","ADA-USD":"DOT-USD",
    "LINK-USD":"DOT-USD","AVAX-USD":"SOL-USD",
    "LTC-USD":"BCH-USD","BCH-USD":"ETC-USD",
    "AAPL":"MSFT","MSFT":"GOOGL","GOOGL":"AMZN",
    "COIN":"MSTR","MARA":"RIOT",
    "XOM":"CVX","JPM":"BAC",
    "AUDJPY=X":"NZDJPY=X","NZDJPY=X":"AUDJPY=X",
    "SOXX":"XBI","XBI":"SOXX",
}

# ---------------------------------------------------------------------------
# Vectorised indicator helpers
# ---------------------------------------------------------------------------

def _vwma_v(close: np.ndarray, volume: np.ndarray, p: int) -> np.ndarray:
    cv = np.where(volume == 0, np.nan, volume)
    out = np.full(len(close), np.nan)
    for i in range(p - 1, len(close)):
        w = cv[i - p + 1:i + 1]
        c = close[i - p + 1:i + 1]
        mask = ~np.isnan(w)
        out[i] = np.sum(c[mask] * w[mask]) / np.sum(w[mask]) if mask.sum() > 0 else np.nan
    return out


def _zscore_v(arr: np.ndarray, lookback: int) -> np.ndarray:
    s = pd.Series(arr)
    m = s.rolling(lookback).mean()
    sd = s.rolling(lookback).std()
    return ((s - m) / sd.replace(0, np.nan)).values


def _rsi_v(close: np.ndarray, p: int = 14) -> np.ndarray:
    delta = np.diff(close, prepend=close[0])
    gain  = np.where(delta > 0, delta, 0.0)
    loss  = np.where(delta < 0, -delta, 0.0)
    s = pd.Series(close)
    g = pd.Series(gain).rolling(p, min_periods=p).mean()
    l = pd.Series(loss).rolling(p, min_periods=p).mean()
    rs = g / l.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).values


def _ema_v(close: np.ndarray, span: int) -> np.ndarray:
    return pd.Series(close).ewm(span=span, adjust=False).mean().values


def _sma_v(arr: np.ndarray, p: int) -> np.ndarray:
    return pd.Series(arr).rolling(p).mean().values


def _atr_v(high: np.ndarray, low: np.ndarray, close: np.ndarray, p: int) -> np.ndarray:
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
    return pd.Series(tr).rolling(p).mean().values


def _stochrsi_v(close: np.ndarray, rsi_p: int = 14, stoch_p: int = 14):
    rsi = pd.Series(_rsi_v(close, rsi_p))
    rsi_min = rsi.rolling(stoch_p).min()
    rsi_max = rsi.rolling(stoch_p).max()
    rng = (rsi_max - rsi_min).replace(0, np.nan)
    k = ((rsi - rsi_min) / rng * 100)
    d = k.rolling(3).mean()
    return k.values, d.values


# ---------------------------------------------------------------------------
# Signal generators — return boolean array (entry signal on that bar)
# ---------------------------------------------------------------------------

def sig_rsi_oversold(df: pd.DataFrame, **_) -> np.ndarray:
    rsi = _rsi_v(df["Close"].values)
    return rsi < 30


def sig_funding_rate_arb(df: pd.DataFrame, **_) -> np.ndarray:
    c, v = df["Close"].values, df["Volume"].values
    n = len(c)
    if n < 80: return np.zeros(n, bool)
    vwma = _vwma_v(c, v, 20)
    basis = np.where(vwma > 0, (c - vwma) / vwma, np.nan)
    z = _zscore_v(basis, 60)
    return np.where(np.isnan(z), False, z < -2.0)


def sig_pairs_trading(df: pd.DataFrame, pair_df: pd.DataFrame | None = None, **_) -> np.ndarray:
    n = len(df)
    if pair_df is None or len(pair_df) < 120:
        return np.zeros(n, bool)
    c1 = np.log(df["Close"].values)
    c2 = np.log(pair_df["Close"].reindex(df.index, method="nearest").values)
    min_len = min(len(c1), len(c2))
    c1, c2 = c1[-min_len:], c2[-min_len:]
    signals = np.zeros(min_len, bool)
    for i in range(60, min_len):
        y_w, x_w = c1[i - 60:i], c2[i - 60:i]
        cov = np.cov(x_w, y_w)
        hr = cov[0, 1] / cov[0, 0] if cov[0, 0] != 0 else 1.0
        spread = c1[:i] - hr * c2[:i]
        m, s = spread[-60:].mean(), spread[-60:].std()
        if s > 0 and (spread[-1] - m) / s < -2.0:
            signals[i] = True
    # Pad to original length
    out = np.zeros(n, bool)
    out[-min_len:] = signals
    return out


def sig_bollinger_mean_rev(df: pd.DataFrame, **_) -> np.ndarray:
    c = df["Close"].values
    v = df["Volume"].values
    n = len(c)
    if n < 50: return np.zeros(n, bool)
    sma = _sma_v(c, 20)
    std = pd.Series(c).rolling(20).std().values
    bb_low = sma - 2 * std
    rsi = _rsi_v(c, 14)
    vol_avg = _sma_v(v.astype(float), 20)
    vol_ratio = np.where(vol_avg > 0, v / vol_avg, 0.0)
    sma50 = _sma_v(c, 50)
    return (c <= bb_low) & (rsi < 30) & (vol_ratio > 2.0) & (c > sma50 * 0.85)


def sig_flash_crash(df: pd.DataFrame, **_) -> np.ndarray:
    c = df["Close"].values
    v = df["Volume"].values
    n = len(c)
    if n < 25: return np.zeros(n, bool)
    rolling_high = pd.Series(c).rolling(20).max().values
    dd = np.where(rolling_high > 0, (c - rolling_high) / rolling_high, 0.0)
    rsi = _rsi_v(c, 6)
    vol_avg = _sma_v(v.astype(float), 20)
    vol_ratio = np.where(vol_avg > 0, v / vol_avg, 0.0)
    return (dd < -0.05) & (rsi < 25) & (vol_ratio > 2.0)


def sig_quality_minus_junk(df: pd.DataFrame, **_) -> np.ndarray:
    c = df["Close"].values
    n = len(c)
    if n < 200: return np.zeros(n, bool)
    returns = pd.Series(c).pct_change().values
    vol20 = pd.Series(returns).rolling(20).std().values
    stab = np.where(vol20 > 0, 1.0 / vol20, np.nan)
    sma200 = _sma_v(c, 200)
    # Simplified: stability high + above 200d SMA
    stab_z = pd.Series(stab).rolling(60).apply(
        lambda x: (x[-1] - np.nanmean(x)) / (np.nanstd(x) + 1e-9), raw=True
    ).values
    return (stab_z > 0.5) & (c > sma200)


def sig_bab(df: pd.DataFrame, spy_df: pd.DataFrame | None = None, **_) -> np.ndarray:
    """Betting Against Beta: low-beta + above 200d SMA."""
    c = df["Close"].values
    n = len(c)
    if n < 200: return np.zeros(n, bool)
    ret = pd.Series(c).pct_change().values
    if spy_df is not None and len(spy_df) >= n:
        bench = spy_df["Close"].reindex(df.index, method="nearest").pct_change().values
    else:
        bench = pd.Series(ret).rolling(5).mean().values
    # Rolling 60-day beta
    beta = np.full(n, np.nan)
    for i in range(60, n):
        r_a = ret[i - 60:i]
        r_b = bench[i - 60:i]
        valid = ~(np.isnan(r_a) | np.isnan(r_b))
        if valid.sum() < 30: continue
        var_b = r_b[valid].var()
        if var_b > 0:
            beta[i] = np.cov(r_a[valid], r_b[valid])[0, 1] / var_b
    sma200 = _sma_v(c, 200)
    return (beta < 0.8) & (c > sma200)


def sig_macd(df: pd.DataFrame, **_) -> np.ndarray:
    c = df["Close"].values
    ema12 = _ema_v(c, 12)
    ema26 = _ema_v(c, 26)
    macd_line = ema12 - ema26
    signal_line = _ema_v(macd_line, 9)
    hist = macd_line - signal_line
    n = len(hist)
    prev_hist = np.roll(hist, 1)
    return (hist > 0) & (prev_hist <= 0)


def sig_golden_cross(df: pd.DataFrame, **_) -> np.ndarray:
    c = df["Close"].values
    n = len(c)
    if n < 202: return np.zeros(n, bool)
    sma50  = _sma_v(c, 50)
    sma200 = _sma_v(c, 200)
    prev50  = np.roll(sma50, 1)
    prev200 = np.roll(sma200, 1)
    return (sma50 > sma200) & (prev50 <= prev200)


def sig_momentum_factor(df: pd.DataFrame, **_) -> np.ndarray:
    c = df["Close"].values
    n = len(c)
    if n < 252: return np.zeros(n, bool)
    out = np.zeros(n, bool)
    for i in range(252, n):
        ret_12_1 = c[i - 21] / c[i - 252] - 1
        ret_3mo  = c[i] / c[i - 63] - 1
        if ret_12_1 > 0.10 and ret_3mo > 0:
            out[i] = True
    return out


def sig_stoch_rsi(df: pd.DataFrame, **_) -> np.ndarray:
    c = df["Close"].values
    n = len(c)
    if n < 35: return np.zeros(n, bool)
    k, _ = _stochrsi_v(c)
    prev_k = np.roll(k, 1)
    return (k < 20) & (k > prev_k)


def sig_cci_reversal(df: pd.DataFrame, **_) -> np.ndarray:
    n = len(df)
    if n < 25 or "High" not in df.columns: return np.zeros(n, bool)
    tp = (df["High"].values + df["Low"].values + df["Close"].values) / 3
    sma_tp = _sma_v(tp, 20)
    mad = pd.Series(tp).rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True).values
    cci = np.where(mad > 0, (tp - sma_tp) / (0.015 * mad), np.nan)
    prev = np.roll(cci, 1)
    return (prev < -100) & (cci > -100)


def sig_williams_r(df: pd.DataFrame, **_) -> np.ndarray:
    n = len(df)
    if n < 15 or "High" not in df.columns: return np.zeros(n, bool)
    c = df["Close"].values
    h = df["High"].values
    l = df["Low"].values
    high_n = pd.Series(h).rolling(14).max().values
    low_n  = pd.Series(l).rolling(14).min().values
    rng = high_n - low_n
    willr = np.where(rng > 0, (high_n - c) / rng * -100, np.nan)
    prev = np.roll(willr, 1)
    return (prev < -80) & (willr > -80)


def sig_donchian_breakout(df: pd.DataFrame, **_) -> np.ndarray:
    c = df["Close"].values
    v = df["Volume"].values
    n = len(c)
    if n < 25: return np.zeros(n, bool)
    high20 = pd.Series(c).shift(1).rolling(20).max().values
    vol_avg = _sma_v(v.astype(float), 20)
    vol_ratio = np.where(vol_avg > 0, v / vol_avg, 0.0)
    return (c > high20) & (vol_ratio > 1.5)


def sig_supertrend(df: pd.DataFrame, **_) -> np.ndarray:
    n = len(df)
    if n < 25 or "High" not in df.columns: return np.zeros(n, bool)
    c = df["Close"].values
    h = df["High"].values
    l = df["Low"].values
    hl2 = (h + l) / 2
    atr = _atr_v(h, l, c, 10)
    mult = 3.0
    upper_b = hl2 + mult * atr
    lower_b = hl2 - mult * atr
    direction = np.zeros(n, dtype=int)
    for i in range(1, n):
        if np.isnan(atr[i]): continue
        fl = lower_b[i] if direction[i - 1] != 1 else max(lower_b[i], lower_b[i - 1])
        fu = upper_b[i] if direction[i - 1] != -1 else min(upper_b[i], upper_b[i - 1])
        if c[i] > fu:
            direction[i] = 1
        elif c[i] < fl:
            direction[i] = -1
        else:
            direction[i] = direction[i - 1] if direction[i - 1] != 0 else 1
    prev_dir = np.roll(direction, 1)
    return (direction == 1) & (prev_dir != 1)


def sig_keltner_bounce(df: pd.DataFrame, **_) -> np.ndarray:
    n = len(df)
    if n < 25 or "High" not in df.columns: return np.zeros(n, bool)
    c = df["Close"].values
    h = df["High"].values
    l = df["Low"].values
    ema = _ema_v(c, 20)
    atr = _atr_v(h, l, c, 20)
    lower_kc = ema - 2.0 * atr
    rsi = _rsi_v(c, 14)
    prev_rsi = np.roll(rsi, 1)
    return (c < lower_kc) & (rsi < 40) & (rsi > prev_rsi)


def sig_volume_spike(df: pd.DataFrame, **_) -> np.ndarray:
    v = df["Volume"].values
    n = len(v)
    if n < 21: return np.zeros(n, bool)
    avg = _sma_v(v.astype(float), 20)
    return np.where(avg > 0, v / avg > 2.0, False)


def sig_volume_breakout(df: pd.DataFrame, **_) -> np.ndarray:
    v = df["Volume"].values
    n = len(v)
    if n < 21: return np.zeros(n, bool)
    avg = _sma_v(v.astype(float), 20)
    return np.where(avg > 0, v / avg > 2.0, False)


def sig_momentum_volume(df: pd.DataFrame, **_) -> np.ndarray:
    c = df["Close"].values
    v = df["Volume"].values
    n = len(c)
    if n < 21: return np.zeros(n, bool)
    mom = np.where(
        np.roll(c, 5) > 0,
        (c - np.roll(c, 5)) / np.roll(c, 5),
        0.0,
    )
    avg = _sma_v(v.astype(float), 20)
    spike = np.where(avg > 0, v / avg > 1.5, False)
    return (mom > 0.02) & spike


def sig_ma_crossover(df: pd.DataFrame, **_) -> np.ndarray:
    c = df["Close"].values
    if len(c) < 51: return np.zeros(len(c), bool)
    fast = _sma_v(c, 10)
    slow = _sma_v(c, 50)
    prev_fast = np.roll(fast, 1)
    prev_slow = np.roll(slow, 1)
    return (fast > slow) & (prev_fast <= prev_slow)


def sig_short_squeeze(df: pd.DataFrame, **_) -> np.ndarray:
    """Near 52-week high + volume surge + RSI momentum (short-squeeze setup)."""
    c = df["Close"].values
    v = df["Volume"].values
    n = len(c)
    if n < 60: return np.zeros(n, bool)
    high_52w = pd.Series(c).rolling(min(n, 252)).max().values
    sma20    = _sma_v(c, 20)
    vol_avg  = _sma_v(v.astype(float), 20)
    vol_ratio = np.where(vol_avg > 0, v / vol_avg, 0.0)
    rsi = _rsi_v(c, 14)
    pct_from_high = np.where(high_52w > 0, c / high_52w, 0.0)
    return (pct_from_high > 0.93) & (vol_ratio > 2.5) & (rsi > 55) & (rsi < 82) & (c > sma20)


def sig_sector_rotation(df: pd.DataFrame, **_) -> np.ndarray:
    """20d return > 4% AND price > SMA10 > SMA50 (sector momentum rotation)."""
    c = df["Close"].values
    n = len(c)
    if n < 55: return np.zeros(n, bool)
    sma10 = _sma_v(c, 10)
    sma50 = _sma_v(c, 50)
    prev_c = np.roll(c, 20)
    ret_20 = np.where(prev_c > 0, (c - prev_c) / prev_c, 0.0)
    return (ret_20 > 0.04) & (c > sma10) & (sma10 > sma50)


def sig_carry_momentum(df: pd.DataFrame, **_) -> np.ndarray:
    """Carry trade: FX pair above SMA50 + positive 10d momentum + RSI 38-68."""
    c = df["Close"].values
    n = len(c)
    if n < 55: return np.zeros(n, bool)
    sma50  = _sma_v(c, 50)
    rsi    = _rsi_v(c, 14)
    prev10 = np.roll(c, 10)
    ret_10 = np.where(prev10 > 0, (c - prev10) / prev10, 0.0)
    return (c > sma50) & (ret_10 > -0.002) & (rsi > 38) & (rsi < 68)


def sig_gap_and_go(df: pd.DataFrame, **_) -> np.ndarray:
    """Large single-day gap (>4%) + volume 2.5x + RSI 45-80 (momentum continuation)."""
    c = df["Close"].values
    v = df["Volume"].values
    n = len(c)
    if n < 25: return np.zeros(n, bool)
    prev_c  = np.roll(c, 1)
    daily_ret = np.where(prev_c > 0, (c - prev_c) / prev_c, 0.0)
    vol_avg = _sma_v(v.astype(float), 20)
    vol_ratio = np.where(vol_avg > 0, v / vol_avg, 0.0)
    rsi = _rsi_v(c, 14)
    return (daily_ret > 0.04) & (vol_ratio > 2.5) & (rsi > 45) & (rsi < 80)


def sig_ema_ribbon(df: pd.DataFrame, **_) -> np.ndarray:
    """EMA Ribbon: 8/13/21/34/55 all bullish-stacked on same bar (fresh alignment = entry)."""
    c = df["Close"].values
    n = len(c)
    if n < 60: return np.zeros(n, bool)
    e8  = _ema_v(c, 8)
    e13 = _ema_v(c, 13)
    e21 = _ema_v(c, 21)
    e34 = _ema_v(c, 34)
    e55 = _ema_v(c, 55)
    stacked      = (e8 > e13) & (e13 > e21) & (e21 > e34) & (e34 > e55)
    prev_stacked = np.roll(stacked, 1)
    prev_stacked[0] = False
    return stacked & ~prev_stacked


def sig_bollinger_squeeze(df: pd.DataFrame, **_) -> np.ndarray:
    """TTM Squeeze: Bollinger Bands inside Keltner Channel → volatility breakout."""
    c = df["Close"].values
    n = len(c)
    if n < 25 or "High" not in df.columns: return np.zeros(n, bool)
    h = df["High"].values
    l = df["Low"].values
    sma20    = _sma_v(c, 20)
    std20    = pd.Series(c).rolling(20).std().values
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20
    atr20    = _atr_v(h, l, c, 20)
    ema20    = _ema_v(c, 20)
    kc_upper = ema20 + 1.5 * atr20
    kc_lower = ema20 - 1.5 * atr20
    squeeze      = (bb_upper < kc_upper) & (bb_lower > kc_lower)
    prev_squeeze = np.roll(squeeze, 1)
    prev_squeeze[0] = False
    prev3 = np.roll(c, 3)
    momentum_up  = (c > sma20) & (prev3 > 0) & (c > prev3)
    return ~squeeze & prev_squeeze & momentum_up


def sig_meme_velocity(df: pd.DataFrame, **_) -> np.ndarray:
    """Meme Velocity: 5d return >12% + acceleration + volume 3x = pump onset."""
    c = df["Close"].values
    v = df["Volume"].values
    n = len(c)
    if n < 25: return np.zeros(n, bool)
    prev5     = np.roll(c, 5)
    prev3     = np.roll(c, 3)
    ret_5     = np.where(prev5 > 0, (c - prev5) / prev5, 0.0)
    ret_3     = np.where(prev3 > 0, (c - prev3) / prev3, 0.0)
    vol_avg   = _sma_v(v.astype(float), 20)
    vol_ratio = np.where(vol_avg > 0, v / vol_avg, 0.0)
    rsi       = _rsi_v(c, 14)
    accel     = ret_3 > ret_5 * 0.5
    return (ret_5 > 0.12) & accel & (vol_ratio > 3.0) & (rsi < 85)


# ---------------------------------------------------------------------------
# Strategy definitions — mirrors ALGO_DEFS in live_scanner.py
# ---------------------------------------------------------------------------

STRAT_DEFS: dict[str, dict] = {
    "funding-rate-arb":        {"name":"Funding Rate Arbitrage",   "tier":"TIER_1","cat":"crypto", "syms":["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD","ADA-USD","AVAX-USD","DOT-USD","LINK-USD","MATIC-USD","LTC-USD","TRX-USD","ATOM-USD","NEAR-USD","ALGO-USD","ETC-USD","BCH-USD","VET-USD","HBAR-USD","GRT-USD"], "fn":sig_funding_rate_arb},
    "pairs-trading":           {"name":"Pairs Trading (Cointegration)","tier":"TIER_1","cat":"stock","syms":["SPY","QQQ","IWM","XLK","XLF","XLE","GLD","SLV","TLT","HYG","BTC-USD","ETH-USD","SOL-USD","ADA-USD","DOT-USD","LINK-USD","AVAX-USD","LTC-USD","BCH-USD","AAPL","MSFT","GOOGL","AMZN","COIN","MSTR","MARA","RIOT","XOM","CVX","JPM","BAC"], "fn":sig_pairs_trading},
    "betting-against-beta":    {"name":"Betting Against Beta",     "tier":"TIER_1","cat":"stock", "syms":["AAPL","MSFT","NVDA","AMD","META","AMZN","GOOGL","NFLX","SHOP","PYPL","SPY","QQQ","VTI","IWM","XLF","XLV","GLD","TLT","JPM","BAC","XOM"], "fn":sig_bab},
    "flash-crash-reversal":    {"name":"Flash Crash Reversal",     "tier":"TIER_1","cat":"crypto","syms":["BTC-USD","ETH-USD","SOL-USD","AVAX-USD","ADA-USD","LINK-USD","DOT-USD","MATIC-USD","NEAR-USD","ATOM-USD","DOGE-USD","SHIB-USD","PEPE-USD","TSLA","NVDA","AMD","COIN","MSTR","MARA","RIOT","RIVN","LCID","NKLA","SPY","QQQ","IWM","ARKK"], "fn":sig_flash_crash},
    "quality-minus-junk":      {"name":"Quality Minus Junk",       "tier":"TIER_1","cat":"stock", "syms":["AAPL","MSFT","NVDA","META","AMZN","GOOGL","NFLX","SHOP","UBER","PYPL","JPM","BAC","XOM","CVX","SPY","QQQ","VTI","IWM","XLK","XLF","XLE","GLD","TLT"], "fn":sig_quality_minus_junk},
    "meme-bollinger-mean-rev": {"name":"Bollinger Mean Reversion (Meme)","tier":"TIER_1","cat":"meme","syms":["DOGE-USD","SHIB-USD","PEPE-USD","SAND-USD","MANA-USD","CHZ-USD","ENJ-USD","NEAR-USD","ALGO-USD","VET-USD"], "fn":sig_bollinger_mean_rev},
    "macd-momentum":           {"name":"MACD Momentum",            "tier":"TIER_1","cat":"crypto","syms":["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD","ADA-USD","AVAX-USD","DOT-USD","LINK-USD","MATIC-USD","DOGE-USD","SHIB-USD","PEPE-USD","NEAR-USD","ATOM-USD","LTC-USD","TRX-USD","ETC-USD","BCH-USD","HBAR-USD"], "fn":sig_macd},
    "golden-cross-stocks":     {"name":"Golden Cross",             "tier":"TIER_1","cat":"stock", "syms":["AAPL","MSFT","NVDA","AMD","META","AMZN","GOOGL","NFLX","TSLA","COIN","MSTR","SHOP","SQ","PYPL","SPY","QQQ","VTI","IWM","ARKK","JPM","BAC","XOM","CVX","GLD","TLT"], "fn":sig_golden_cross},
    "momentum-factor":         {"name":"12-1 Momentum Factor",     "tier":"TIER_1","cat":"stock", "syms":["AAPL","MSFT","NVDA","AMD","META","AMZN","GOOGL","NFLX","SHOP","UBER","COIN","TSLA","MSTR","SQ","SPY","QQQ","VTI","IWM","XLK","XLE","XLF","ARKK","GLD","TLT","JPM","BAC","XOM"], "fn":sig_momentum_factor},
    "crypto-momentum-scout":   {"name":"Crypto RSI Scout",         "tier":"SCOUT", "cat":"crypto","syms":["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD","ADA-USD","AVAX-USD","DOT-USD","LINK-USD","MATIC-USD","LTC-USD","TRX-USD","ETC-USD","BCH-USD","ATOM-USD","NEAR-USD","ALGO-USD","VET-USD","HBAR-USD","DOGE-USD","SHIB-USD","SAND-USD","MANA-USD","APT-USD"], "fn":sig_rsi_oversold},
    "volume-spike-scout":      {"name":"Volume Spike Scout",       "tier":"SCOUT", "cat":"crypto","syms":["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD","ADA-USD","AVAX-USD","DOT-USD","LINK-USD","MATIC-USD","LTC-USD","TRX-USD","ETC-USD","ATOM-USD","NEAR-USD","DOGE-USD","SHIB-USD","PEPE-USD","SAND-USD","MANA-USD","CHZ-USD","VET-USD","HBAR-USD"], "fn":sig_volume_spike},
    "meme-scanner-live":       {"name":"Meme Coin Scout",          "tier":"SCOUT", "cat":"meme",  "syms":["DOGE-USD","SHIB-USD","PEPE-USD","SAND-USD","MANA-USD","CHZ-USD","TRX-USD","HBAR-USD","VET-USD"], "fn":sig_momentum_volume},
    "penny-tracker-live":      {"name":"Penny Stock Scout",        "tier":"SCOUT", "cat":"penny", "syms":["GME","AMC","PLTR","SOFI","HOOD","BBAI","MARA","RIOT","CLSK","BTBT","RIVN","LCID","NKLA","SNDL","CLOV"], "fn":sig_volume_breakout},
    "forex-scanner-live":      {"name":"Forex MA Scout",           "tier":"SCOUT", "cat":"forex", "syms":["EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","AUDUSD=X","USDCAD=X","NZDUSD=X","EURJPY=X","GBPJPY=X","EURGBP=X","USDMXN=X","USDZAR=X"], "fn":sig_ma_crossover},
    "stoch-rsi-crypto":        {"name":"StochRSI Scout",           "tier":"SCOUT", "cat":"crypto","syms":["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD","ADA-USD","AVAX-USD","DOT-USD","LINK-USD","MATIC-USD","LTC-USD","TRX-USD","ATOM-USD","NEAR-USD","DOGE-USD","SHIB-USD","PEPE-USD","SAND-USD","MANA-USD","VET-USD"], "fn":sig_stoch_rsi},
    "cci-crypto-reversal":     {"name":"CCI Reversal Scout",       "tier":"SCOUT", "cat":"crypto","syms":["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD","DOGE-USD","SHIB-USD","PEPE-USD","ADA-USD","AVAX-USD","LINK-USD","DOT-USD","NEAR-USD","ALGO-USD","VET-USD","HBAR-USD","SAND-USD","MANA-USD","CHZ-USD","ENJ-USD"], "fn":sig_cci_reversal},
    "williams-r-scout":        {"name":"Williams %R Scout",        "tier":"SCOUT", "cat":"meme",  "syms":["DOGE-USD","SHIB-USD","PEPE-USD","SAND-USD","MANA-USD","CHZ-USD","ENJ-USD","NEAR-USD","ALGO-USD","VET-USD","GME","AMC","PLTR","MARA","RIOT","RIVN","LCID"], "fn":sig_williams_r},
    "donchian-stock-breakout": {"name":"Donchian Breakout",        "tier":"SCOUT", "cat":"stock", "syms":["AAPL","MSFT","NVDA","AMD","META","AMZN","GOOGL","NFLX","TSLA","COIN","MSTR","SHOP","UBER","SQ","SPY","QQQ","IWM","ARKK","GME","AMC","PLTR","SOFI","MARA","RIOT"], "fn":sig_donchian_breakout},
    "supertrend-crypto":       {"name":"Supertrend Scout",         "tier":"SCOUT", "cat":"crypto","syms":["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD","ADA-USD","AVAX-USD","DOT-USD","LINK-USD","MATIC-USD","DOGE-USD","SHIB-USD","NEAR-USD","ATOM-USD","LTC-USD"], "fn":sig_supertrend},
    "keltner-bounce":          {"name":"Keltner Bounce Scout",     "tier":"SCOUT", "cat":"crypto","syms":["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD","DOGE-USD","SHIB-USD","PEPE-USD","ADA-USD","AVAX-USD","LINK-USD","DOT-USD","NEAR-USD","MATIC-USD","MARA","RIOT","COIN","TSLA","NVDA"], "fn":sig_keltner_bounce},
    # v4 new strategies
    "short-squeeze":           {"name":"Short Squeeze Setup",      "tier":"TIER_1","cat":"penny","syms":["GME","AMC","PLTR","SOFI","MARA","RIOT","CLSK","RIVN","LCID","NVAX","BNGO","SPCE","XPEV","NIO","TSLA","COIN","HOOD","BBAI","UWMC"], "fn":sig_short_squeeze},
    "sector-rotation":         {"name":"Sector Rotation Momentum", "tier":"TIER_1","cat":"stock","syms":["XLK","XLF","XLE","XLV","XLI","SOXX","XBI","XRT","ARKK","JETS","SPY","QQQ","IWM","GLD","TLT"], "fn":sig_sector_rotation},
    "carry-trade-momentum":    {"name":"Carry Trade Momentum",     "tier":"TIER_1","cat":"forex","syms":["AUDJPY=X","NZDJPY=X","CADJPY=X","GBPJPY=X","EURJPY=X","AUDUSD=X","NZDUSD=X"], "fn":sig_carry_momentum},
    "gap-and-go-stocks":       {"name":"Gap-and-Go Breakout",      "tier":"SCOUT", "cat":"penny","syms":["GME","AMC","MARA","RIOT","RIVN","LCID","NVAX","BNGO","XPEV","NIO","PLTR","SOFI","TSLA","NVDA","AMD","COIN","MSTR","DOGE-USD","SHIB-USD","PEPE-USD","FLOKI-USD"], "fn":sig_gap_and_go},
    "ema-ribbon":              {"name":"EMA Ribbon (8/13/21/34/55)","tier":"TIER_1","cat":"stock","syms":["AAPL","MSFT","NVDA","AMD","META","AMZN","GOOGL","NFLX","TSLA","COIN","MSTR","SHOP","SQ","UBER","SPY","QQQ","VTI","IWM","ARKK","SOXX","XBI","BTC-USD","ETH-USD","SOL-USD","BNB-USD","AVAX-USD","DOGE-USD","SHIB-USD"], "fn":sig_ema_ribbon},
    "bollinger-squeeze":       {"name":"Bollinger Squeeze Breakout","tier":"TIER_1","cat":"crypto","syms":["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD","ADA-USD","AVAX-USD","DOT-USD","LINK-USD","MATIC-USD","DOGE-USD","SHIB-USD","PEPE-USD","FLOKI-USD","MARA","RIOT","TSLA","NVDA","COIN","SPY","QQQ","SOXX","XBI"], "fn":sig_bollinger_squeeze},
    "meme-velocity":           {"name":"Meme Velocity Pump Detector","tier":"TIER_1","cat":"meme","syms":["DOGE-USD","SHIB-USD","PEPE-USD","FLOKI-USD","BONK-USD","SAND-USD","MANA-USD","CHZ-USD","ENJ-USD","GME","AMC","MARA","RIOT","NVAX","BNGO","SPCE","RIVN"], "fn":sig_meme_velocity},
}


# ---------------------------------------------------------------------------
# Regime labelling — build daily stock/crypto regime series for 5yr window
# ---------------------------------------------------------------------------

def build_regime_series(spy_df: pd.DataFrame | None, btc_df: pd.DataFrame | None) -> dict[str, dict]:
    """
    Build daily regime labels over the backtest period.
    Returns {date_str: {'stock': 'bull'/'bear'/'neutral', 'crypto': 'bull'/'bear'/'neutral'}}

    Stock regime: SPY 20d volatility + 200d SMA position
    Crypto regime: BTC 30d return + 20d volatility
    """
    regime_by_date: dict[str, dict] = {}

    # ── Stock regime ─────────────────────────────────────────────────────────
    stock_regime_series: pd.Series | None = None
    if spy_df is not None and len(spy_df) >= 220:
        spy_ret = spy_df["Close"].pct_change()
        vol_20  = spy_ret.rolling(20).std() * 100
        sma200  = spy_df["Close"].rolling(200).mean()
        above_200 = spy_df["Close"] > sma200
        stock_regime_series = pd.Series("neutral", index=spy_df.index)
        bull_mask = (vol_20 < 1.2) & above_200
        bear_mask = (vol_20 > 2.0) | (~above_200)
        stock_regime_series[bull_mask] = "bull"
        stock_regime_series[bear_mask] = "bear"

    # ── Crypto regime ─────────────────────────────────────────────────────────
    crypto_regime_series: pd.Series | None = None
    if btc_df is not None and len(btc_df) >= 35:
        btc_ret_30 = btc_df["Close"].pct_change(30)
        btc_vol_20 = btc_df["Close"].pct_change().rolling(20).std() * 100
        crypto_regime_series = pd.Series("neutral", index=btc_df.index)
        bull_mask_c = btc_ret_30 > 0.10
        bear_mask_c = (btc_ret_30 < -0.15) | (btc_vol_20 > 4.5)
        crypto_regime_series[bull_mask_c] = "bull"
        crypto_regime_series[bear_mask_c] = "bear"

    # ── Combine into date-keyed dict ──────────────────────────────────────────
    all_dates = set()
    if stock_regime_series is not None:
        all_dates.update([str(d)[:10] for d in stock_regime_series.index])
    if crypto_regime_series is not None:
        all_dates.update([str(d)[:10] for d in crypto_regime_series.index])

    # Build forward-fill lookup dicts for fast date access
    stock_lookup: dict[str, str] = {}
    if stock_regime_series is not None:
        for d, v in zip(stock_regime_series.index, stock_regime_series.values):
            stock_lookup[str(d)[:10]] = str(v)
    crypto_lookup: dict[str, str] = {}
    if crypto_regime_series is not None:
        for d, v in zip(crypto_regime_series.index, crypto_regime_series.values):
            crypto_lookup[str(d)[:10]] = str(v)

    for date_str in all_dates:
        regime_by_date[date_str] = {
            "stock":  stock_lookup.get(date_str, "neutral"),
            "crypto": crypto_lookup.get(date_str, "neutral"),
        }

    return regime_by_date


# ---------------------------------------------------------------------------
# Vectorised backtest core
# ---------------------------------------------------------------------------

def backtest_strategy(
    strat_id: str,
    strat: dict,
    all_data: dict[str, pd.DataFrame],
    regime_series: dict | None = None,
) -> dict:
    """
    Run a single strategy over all its symbols.
    regime_series: optional {date_str: {'stock':..., 'crypto':...}} from build_regime_series()
    Returns per-trade results and aggregate stats.
    """
    sig_fn: Callable = strat["fn"]
    trades = []
    spy_df = all_data.get("SPY")

    for sym in strat["syms"]:
        df = all_data.get(sym)
        if df is None or len(df) < 30:
            continue
        pair_df = all_data.get(PAIR_MAP.get(sym, ""))

        try:
            if strat_id == "pairs-trading":
                entry_signals = sig_fn(df, pair_df=pair_df)
            elif strat_id == "betting-against-beta":
                entry_signals = sig_fn(df, spy_df=spy_df)
            else:
                entry_signals = sig_fn(df)
        except Exception:
            continue

        close = df["Close"].values
        dates = df.index
        n = len(close)

        # Simulate trades using vectorised exit logic
        i = 0
        while i < n:
            if not entry_signals[i]:
                i += 1
                continue

            entry_price = close[i]
            entry_date  = str(dates[i])[:10]
            if entry_price <= 0:
                i += 1
                continue

            # Scan forward for exit
            exit_idx = None
            exit_reason = "TIME_EXIT"
            for j in range(i + 1, min(i + MAX_HOLD + 1, n)):
                ret = (close[j] - entry_price) / entry_price
                if ret >= TAKE_PROFIT:
                    exit_idx = j
                    exit_reason = "TAKE_PROFIT"
                    break
                elif ret <= STOP_LOSS:
                    exit_idx = j
                    exit_reason = "STOP_LOSS"
                    break
            if exit_idx is None:
                exit_idx = min(i + MAX_HOLD, n - 1)

            exit_price = close[exit_idx]
            ret = (exit_price - entry_price) / entry_price
            pnl = ALLOC_PER * ret

            # Tag trade with market regime at entry
            trade_regime = regime_series.get(entry_date, {}) if regime_series else {}
            cat = strat.get("cat", "stock")
            regime_label = trade_regime.get("crypto" if cat in ("crypto", "meme") else "stock", "neutral")

            trades.append({
                "symbol":       sym,
                "entry_date":   entry_date,
                "exit_date":    str(dates[exit_idx])[:10],
                "entry_price":  round(float(entry_price), 6),
                "exit_price":   round(float(exit_price), 6),
                "ret_pct":      round(ret * 100, 3),
                "pnl":          round(pnl, 2),
                "exit_reason":  exit_reason,
                "outcome":      "win" if ret >= 0 else "loss",
                "regime":       regime_label,
            })

            i = exit_idx + 1  # no re-entry on same symbol until after exit

    # Aggregate stats
    n_trades = len(trades)
    if n_trades == 0:
        return {
            "id": strat_id, "name": strat["name"], "tier": strat["tier"],
            "cat": strat["cat"], "trades": 0, "wins": 0, "losses": 0,
            "win_rate": 0.0, "total_pnl": 0.0, "avg_pnl": 0.0,
            "sharpe": 0.0, "max_dd": 0.0, "rank": "insufficient_data",
            "trade_log": [],
        }

    wins   = sum(1 for t in trades if t["outcome"] == "win")
    losses = n_trades - wins
    wr     = wins / n_trades * 100
    pnls   = np.array([t["pnl"] for t in trades])
    total_pnl = float(pnls.sum())
    avg_pnl   = float(pnls.mean())

    # Sharpe on per-trade returns
    ret_arr = np.array([t["ret_pct"] for t in trades])
    sharpe = float(ret_arr.mean() / ret_arr.std()) if ret_arr.std() > 0 else 0.0

    # Max drawdown on cumulative PnL curve
    cum = np.cumsum(pnls)
    rolling_max = np.maximum.accumulate(cum)
    dd = cum - rolling_max
    max_dd = float(dd.min())

    # Promotion logic
    if n_trades >= PROMOTE_TRADES and wr >= PROMOTE_WINRATE:
        rank = "promoted"
    elif n_trades >= PROMOTE_TRADES and wr < PROMOTE_WINRATE:
        rank = "eliminated"
    elif n_trades >= 20 and sharpe > 0.5:
        rank = "testing_ok"
    else:
        rank = "testing"

    # Regime breakdown: performance by bull/bear/neutral
    regime_breakdown: dict[str, dict] = {}
    for regime_label in ("bull", "bear", "neutral"):
        rtrades = [t for t in trades if t.get("regime") == regime_label]
        if rtrades:
            r_wins = sum(1 for t in rtrades if t["outcome"] == "win")
            r_pnls = np.array([t["pnl"] for t in rtrades])
            regime_breakdown[regime_label] = {
                "trades":   len(rtrades),
                "win_rate": round(r_wins / len(rtrades) * 100, 1),
                "total_pnl": round(float(r_pnls.sum()), 2),
                "sharpe":   round(float(r_pnls.mean() / r_pnls.std()) if r_pnls.std() > 0 else 0.0, 3),
            }

    return {
        "id": strat_id,
        "name": strat["name"],
        "tier": strat["tier"],
        "cat": strat["cat"],
        "trades": n_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wr, 2),
        "total_pnl": round(total_pnl, 2),
        "avg_pnl": round(avg_pnl, 2),
        "sharpe": round(sharpe, 3),
        "max_dd": round(max_dd, 2),
        "regime_breakdown": regime_breakdown,
        "rank": rank,
        "trade_log": trades[-100:],  # keep last 100 trades for detail file
    }


# ---------------------------------------------------------------------------
# Tournament score from backtest results
# ---------------------------------------------------------------------------

def score_from_backtest(r: dict) -> float:
    """
    v4 Institutional composite score (0-100):
      30 pts — Sharpe ratio (Sharpe=1.5 → max 30pts)
      25 pts — win rate (0-100%)
      20 pts — max drawdown inverted ($0 DD → 20pts)
      15 pts — profit factor (gross wins / gross losses; PF=2 → 15pts)
      10 pts — activity bonus (trade count coverage)
    """
    # Sharpe: max 30pts
    sharpe_pts = min(max(r["sharpe"] * 20, 0), 30) if r["sharpe"] > 0 else 0.0

    # Win rate: max 25pts
    wr_pts = min(r["win_rate"], 100) * 0.25

    # Max drawdown inverted: max 20pts (each $500 DD → -10pts)
    dd_pts = max(0.0, min(20.0, 20.0 + r["max_dd"] * 0.04))

    # Profit factor from trades
    trades = r.get("trade_log", [])
    gross_wins   = sum(t["pnl"] for t in trades if t["pnl"] > 0) if trades else 0.0
    gross_losses = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0)) if trades else 0.001
    pf = (gross_wins / gross_losses) if gross_losses > 0.001 else (1.5 if gross_wins > 0 else 1.0)
    pf_pts = min(max((pf - 0.5) * 7.5, 0), 15)

    # Activity: 0-10 pts based on trade count (100 trades → 10pts)
    activity_pts = min(r["trades"] / 100 * 10, 10)

    return round(sharpe_pts + wr_pts + dd_pts + pf_pts + activity_pts, 1)


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def run_backtest(period: str = "5y", strategies: list[str] | None = None):
    print("=" * 64)
    print("KIMI Rise of the Claw — Vectorized Backtest Engine v3")
    print(f"  Period: {period}  |  v4 scoring  |  27 strategies  |  Regime-performance breakdown")
    print("=" * 64)
    now = datetime.now(timezone.utc)

    target_strats = strategies or list(STRAT_DEFS.keys())
    all_syms: set[str] = set()
    for sid in target_strats:
        if sid in STRAT_DEFS:
            all_syms.update(STRAT_DEFS[sid]["syms"])
    all_syms.add("SPY")  # needed for BAB benchmark

    print(f"Fetching {len(all_syms)} symbols ({period}) ...")
    all_data: dict[str, pd.DataFrame] = {}
    for sym in sorted(all_syms):
        try:
            df = yf.Ticker(sym).history(period=period, auto_adjust=True)
            if df is not None and not df.empty and len(df) >= 30:
                all_data[sym] = df
        except Exception:
            pass
    print(f"  Loaded {len(all_data)} symbols\n")

    # Build regime series from SPY + BTC for regime-performance breakdown
    print("Building regime series (SPY + BTC-USD)...")
    _btc_df = all_data.get("BTC-USD")
    if _btc_df is None or (hasattr(_btc_df, 'empty') and _btc_df.empty):
        _btc_df = yf.Ticker("BTC-USD").history(period=period, auto_adjust=True)
    regime_series = build_regime_series(
        spy_df=all_data.get("SPY"),
        btc_df=_btc_df,
    )
    if regime_series:
        bull_days  = sum(1 for v in regime_series.values() if v["stock"] == "bull")
        bear_days  = sum(1 for v in regime_series.values() if v["stock"] == "bear")
        neut_days  = sum(1 for v in regime_series.values() if v["stock"] == "neutral")
        print(f"  {len(regime_series)} dates labelled: stock regime — bull={bull_days}, bear={bear_days}, neutral={neut_days}\n")
    else:
        print("  Warning: could not build regime series (insufficient SPY data)\n")

    results = []
    for sid in target_strats:
        strat = STRAT_DEFS.get(sid)
        if not strat:
            continue
        print(f"  Backtesting  {strat['name']:40s} ...", end=" ", flush=True)
        r = backtest_strategy(sid, strat, all_data, regime_series=regime_series or None)
        rb = r.get("regime_breakdown", {})
        rb_str = ""
        if rb:
            rb_str = "  [" + " | ".join(
                f"{k}: WR={v['win_rate']}% ({v['trades']}t)" for k, v in rb.items()
            ) + "]"
        print(f"{r['trades']:4d} trades  WR={r['win_rate']:5.1f}%  "
              f"PnL=${r['total_pnl']:+8.2f}  Sharpe={r['sharpe']:5.2f}  [{r['rank']}]{rb_str}")
        results.append(r)

    # Score and rank
    for r in results:
        r["bt_score"] = score_from_backtest(r)
    results.sort(key=lambda x: x["bt_score"], reverse=True)
    for i, r in enumerate(results):
        r["bt_rank"] = i + 1

    # Save backtest_rankings.json (dashboard-ready)
    rankings_out = {
        "lastUpdated":      now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "period":           period,
        "totalStrategies":  len(results),
        "note": "Vectorized 5yr backtest v3 — category-aware SL/TP, regime-performance breakdown",
        "rankings": [
            {
                "rank":            r["bt_rank"],
                "id":              r["id"],
                "name":            r["name"],
                "tier":            r["tier"],
                "category":        r["cat"],
                "score":           r["bt_score"],
                "trades":          r["trades"],
                "winRate":         r["win_rate"],
                "totalPnl":        r["total_pnl"],
                "avgPnl":          r["avg_pnl"],
                "sharpe":          r["sharpe"],
                "maxDd":           r["max_dd"],
                "rank_label":      r["rank"],
                "regimeBreakdown": r.get("regime_breakdown", {}),
            }
            for r in results
        ],
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "backtest_rankings.json", "w", encoding="utf-8") as f:
        json.dump(rankings_out, f, indent=2)

    # Save detail file (trade logs)
    detail_out = {
        "lastUpdated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "strategies":  results,
    }
    detail_out_lite = {
        "lastUpdated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "strategies": [
            {k: v for k, v in r.items() if k != "trade_log"}
            for r in results
        ],
    }
    with open(DATA_DIR / "backtest_detail.json", "w", encoding="utf-8") as f:
        json.dump(detail_out_lite, f, indent=2)

    print()
    print("=" * 64)
    print("Top 5 strategies by backtest score:")
    for r in results[:5]:
        status = "PROMOTED" if r["rank"] == "promoted" else ("ELIMINATED" if r["rank"] == "eliminated" else r["rank"].upper())
        print(f"  #{r['bt_rank']:2d}  {r['name']:40s}  score={r['bt_score']:5.1f}  "
              f"WR={r['win_rate']:5.1f}%  [{status}]")
    promoted = [r for r in results if r["rank"] == "promoted"]
    eliminated = [r for r in results if r["rank"] == "eliminated"]
    print(f"\nPromotion threshold ({PROMOTE_TRADES} trades + {PROMOTE_WINRATE}% WR):")
    print(f"  Promoted: {len(promoted)}  |  Eliminated: {len(eliminated)}  |  Still testing: {len(results)-len(promoted)-len(eliminated)}")
    print()
    print(f"Saved: data/backtest_rankings.json  data/backtest_detail.json")
    print("Done.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KIMI Vectorized Backtest Engine")
    parser.add_argument("--period", default="5y", help="yfinance period (e.g. 5y, 2y, 1y)")
    parser.add_argument("--strategies", nargs="*", help="Specific strategy IDs to run")
    args = parser.parse_args()
    sys.exit(run_backtest(period=args.period, strategies=args.strategies))
