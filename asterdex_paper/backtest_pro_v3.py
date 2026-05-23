#!/usr/bin/env python3
"""
Kimi Claw Pro v3 -- Regime-Aware Backtester
===========================================
Implements the full signal pipeline from the TradingView Pine Script:
  1. Regime Detection Engine (ADX + Choppiness + Volatility Ratio + Hurst)
  2. Adaptive Moving Averages (KAMA, HMA, VWAP)
  3. Multi-Timeframe Confluence (HTF 50%, Current 30%, LTF 20%)
  4. Volume Z-Score Analysis
  5. Bayesian Confidence Scoring
  6. Kelly Criterion + Circuit Breaker

Fetches 1 year of daily data for BTC, ETH, SOL, XRP, ADA via yfinance.
Run:  py backtest_pro_v3.py
"""

from __future__ import annotations

import math
import os
import sys
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# Force UTF-8 output on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_data(symbols: List[str], period: str = "1y", interval: str = "1d") -> Dict[str, pd.DataFrame]:
    """Fetch OHLCV data.  yfinance first, ccxt fallback for crypto."""
    data: Dict[str, pd.DataFrame] = {}

    # Map friendly names to yfinance tickers
    YF_MAP = {
        "BTC": "BTC-USD",
        "ETH": "ETH-USD",
        "SOL": "SOL-USD",
        "XRP": "XRP-USD",
        "ADA": "ADA-USD",
    }

    try:
        import yfinance as yf

        for name, ticker in YF_MAP.items():
            if name not in symbols:
                continue
            print(f"  Fetching {name} ({ticker}) via yfinance ...", end=" ", flush=True)
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            if df is None or df.empty:
                print("EMPTY")
                continue
            # Flatten multi-level columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            df.columns = [c.lower() for c in df.columns]
            required = {"open", "high", "low", "close", "volume"}
            if not required.issubset(set(df.columns)):
                print(f"MISSING COLS ({set(df.columns)})")
                continue
            df = df[["open", "high", "low", "close", "volume"]].copy()
            df.dropna(inplace=True)
            if len(df) < 60:
                print(f"TOO SHORT ({len(df)} bars)")
                continue
            data[name] = df
            print(f"OK  ({len(df)} bars)")

        if data:
            return data

    except ImportError:
        print("  yfinance not installed, trying ccxt ...")

    # ccxt fallback
    try:
        import ccxt

        exchange = ccxt.binance({"enableRateLimit": True})
        CCXT_MAP = {
            "BTC": "BTC/USDT",
            "ETH": "ETH/USDT",
            "SOL": "SOL/USDT",
            "XRP": "XRP/USDT",
            "ADA": "ADA/USDT",
        }
        for name, pair in CCXT_MAP.items():
            if name not in symbols:
                continue
            print(f"  Fetching {name} ({pair}) via ccxt ...", end=" ", flush=True)
            ohlcv = exchange.fetch_ohlcv(pair, timeframe="1d", limit=365)
            if not ohlcv:
                print("EMPTY")
                continue
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            df.dropna(inplace=True)
            if len(df) < 60:
                print(f"TOO SHORT ({len(df)} bars)")
                continue
            data[name] = df
            print(f"OK  ({len(df)} bars)")

    except ImportError:
        print("  ERROR: Neither yfinance nor ccxt available.")
        print("  Install one:  pip install yfinance   OR   pip install ccxt")
        sys.exit(1)

    return data


# ===========================================================================
# INDICATOR CALCULATIONS  (vectorised NumPy / Pandas)
# ===========================================================================

def true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """True Range array."""
    prev_c = np.roll(close, 1)
    prev_c[0] = close[0]
    return np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))


def rma(arr: np.ndarray, n: int) -> np.ndarray:
    """Wilder's smoothing (RMA) -- equivalent to ta.rma in Pine.
    Handles NaN inputs by finding the first window of n valid values."""
    out = np.full_like(arr, np.nan, dtype=float)
    if len(arr) < n:
        return out

    # Find first index where we have n consecutive non-NaN values
    seed_start = -1
    count = 0
    for i in range(len(arr)):
        if np.isnan(arr[i]):
            count = 0
        else:
            count += 1
            if count >= n:
                seed_start = i - n + 1
                break

    if seed_start < 0:
        return out  # Not enough valid data

    seed_end = seed_start + n
    out[seed_end - 1] = np.nanmean(arr[seed_start:seed_end])
    alpha = 1.0 / n
    for i in range(seed_end, len(arr)):
        val = arr[i] if not np.isnan(arr[i]) else 0.0
        out[i] = alpha * val + (1 - alpha) * out[i - 1]
    return out


def sma(arr: np.ndarray, n: int) -> np.ndarray:
    s = pd.Series(arr)
    return s.rolling(n, min_periods=n).mean().to_numpy()


def ema(arr: np.ndarray, n: int) -> np.ndarray:
    s = pd.Series(arr)
    return s.ewm(span=n, adjust=False).mean().to_numpy()


def stdev(arr: np.ndarray, n: int) -> np.ndarray:
    s = pd.Series(arr)
    return s.rolling(n, min_periods=n).std(ddof=0).to_numpy()


def wma(arr: np.ndarray, n: int) -> np.ndarray:
    """Weighted Moving Average."""
    weights = np.arange(1, n + 1, dtype=float)
    out = np.full_like(arr, np.nan, dtype=float)
    for i in range(n - 1, len(arr)):
        out[i] = np.dot(arr[i - n + 1 : i + 1], weights) / weights.sum()
    return out


def rolling_max(arr: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(arr).rolling(n, min_periods=n).max().to_numpy()


def rolling_min(arr: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(arr).rolling(n, min_periods=n).min().to_numpy()


def rsi(close: np.ndarray, n: int) -> np.ndarray:
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = rma(gain, n)
    avg_loss = rma(loss, n)
    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    return 100.0 - 100.0 / (1.0 + rs)


# ---------------------------------------------------------------------------
# 1. REGIME DETECTION ENGINE
# ---------------------------------------------------------------------------

def calc_adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int = 14) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """ADX, +DI, -DI."""
    up = np.diff(high, prepend=high[0])
    down = -np.diff(low, prepend=low[0])
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)

    tr = true_range(high, low, close)
    atr_n = rma(tr, n)
    atr_n = np.where(atr_n == 0, 1e-10, atr_n)

    plus_di = 100.0 * rma(plus_dm, n) / atr_n
    minus_di = 100.0 * rma(minus_dm, n) / atr_n

    dx_sum = plus_di + minus_di
    dx_sum = np.where(dx_sum == 0, 1e-10, dx_sum)
    dx = 100.0 * np.abs(plus_di - minus_di) / dx_sum
    adx_val = rma(dx, n)
    return adx_val, plus_di, minus_di


def calc_choppiness(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int = 14) -> np.ndarray:
    """
    Choppiness Index = 100 * log10(sum(TR, n) / (highest_high - lowest_low)) / log10(n)
    """
    tr = true_range(high, low, close)
    tr_sum = pd.Series(tr).rolling(n, min_periods=n).sum().to_numpy()
    hh = rolling_max(high, n)
    ll = rolling_min(low, n)
    rng = hh - ll
    rng = np.where(rng == 0, 1e-10, rng)
    chop = 100.0 * np.log10(tr_sum / rng) / np.log10(n)
    return chop


def calc_hurst(close: np.ndarray, n: int = 50) -> np.ndarray:
    """Hurst exponent approximation via R/S analysis (simplified, per Pine)."""
    hh = rolling_max(close, n)
    ll = rolling_min(close, n)
    max_rs = hh - ll
    std_n = stdev(close, n)
    std_n = np.where((std_n == 0) | np.isnan(std_n), 1e-10, std_n)
    rs = max_rs / std_n
    rs = np.where(rs <= 0, 1e-10, rs)
    h_est = 0.5 + (np.log(rs) / np.log(n) - 0.5) * 0.3
    return np.clip(h_est, 0.1, 0.9)


def calc_volatility_ratio(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """ATR(10) / ATR(20) -- volatility compression / expansion."""
    tr = true_range(high, low, close)
    atr10 = rma(tr, 10)
    atr20 = rma(tr, 20)
    atr20 = np.where((atr20 == 0) | np.isnan(atr20), 1e-10, atr20)
    return atr10 / atr20


@dataclass
class RegimeState:
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    QUIET = "QUIET"
    NORMAL = "NORMAL"


def classify_regime(adx: np.ndarray, chop: np.ndarray, vol_ratio: np.ndarray, hurst: np.ndarray) -> np.ndarray:
    """
    Regime classification with hysteresis, matching Pine logic:
      Trending:  ADX>25 AND Chop<50
      Ranging:   ADX<25 AND Chop>55
      Volatile:  vol_ratio>1.5 AND ADX>20
      Quiet:     vol_ratio<0.7 AND ADX<20
      else:      NORMAL
    Also uses Hurst + regime_score composite with hysteresis.
    """
    n = len(adx)
    regimes = np.empty(n, dtype=object)

    # Composite regime score (matching Pine)
    vol_pctrank = pd.Series(vol_ratio).rolling(100, min_periods=10).rank(pct=True).to_numpy() * 100
    vol_pctrank = np.nan_to_num(vol_pctrank, nan=50.0)

    # Trend persistence
    mom10 = np.zeros(n)
    mom20 = np.zeros(n)
    for i in range(20, n):
        if close_g[i - 10] != 0:
            mom10[i] = (close_g[i] - close_g[i - 10]) / close_g[i - 10] * 100
        if close_g[i - 20] != 0:
            mom20[i] = (close_g[i] - close_g[i - 20]) / close_g[i - 20] * 100
    mom_consistency = np.where(
        np.abs(mom10 - mom20) < np.abs(mom10) * 0.5, 1.0, 0.0
    )

    regime_score = (
        (vol_pctrank / 100) * 0.25
        + hurst * 0.35
        + (adx / 100) * 0.25
        + mom_consistency * 0.15
    )

    prev = "NORMAL"
    for i in range(n):
        if np.isnan(adx[i]) or np.isnan(chop[i]) or np.isnan(vol_ratio[i]):
            regimes[i] = "NORMAL"
            continue

        r = "NORMAL"

        # PRIMARY: Explicit ADX + Choppiness + Volatility rules from spec
        # These take priority and are evaluated first
        a = adx[i]
        ch = chop[i]
        vr = vol_ratio[i]

        if a > 25 and ch < 50:
            r = "TRENDING"
        elif a < 25 and ch > 55:
            r = "RANGING"
        elif vr > 1.5 and a > 20:
            r = "VOLATILE"
        elif vr < 0.7 and a < 20:
            r = "QUIET"
        else:
            # SECONDARY: Composite regime score with hysteresis
            sc = regime_score[i] if not np.isnan(regime_score[i]) else 0.5
            if sc > 0.65:
                r = "TRENDING"
            elif sc < 0.35:
                r = "RANGING"
            elif sc > 0.50 and prev == "TRENDING":
                r = "TRENDING"
            elif sc < 0.50 and prev == "RANGING":
                r = "RANGING"
            else:
                r = "NORMAL"

        regimes[i] = r
        prev = r

    return regimes


# ---------------------------------------------------------------------------
# 2. ADAPTIVE MOVING AVERAGES
# ---------------------------------------------------------------------------

def calc_kama(close: np.ndarray, length: int = 10, fast: int = 2, slow: int = 30) -> np.ndarray:
    """Kaufman Adaptive Moving Average."""
    n = len(close)
    out = np.full(n, np.nan)
    out[length - 1] = close[length - 1]  # seed

    fastest = 2.0 / (fast + 1)
    slowest = 2.0 / (slow + 1)

    for i in range(length, n):
        direction = abs(close[i] - close[i - length])
        volatility = sum(abs(close[j] - close[j - 1]) for j in range(i - length + 1, i + 1))
        if volatility == 0:
            er = 0.0
        else:
            er = direction / volatility
        sc = (er * (fastest - slowest) + slowest) ** 2
        prev = out[i - 1] if not np.isnan(out[i - 1]) else close[i]
        out[i] = prev + sc * (close[i] - prev)
    return out


def calc_hma(close: np.ndarray, length: int = 16) -> np.ndarray:
    """Hull Moving Average = WMA(sqrt(n)) of (2*WMA(n/2) - WMA(n))."""
    half = max(1, int(length / 2))
    sqrt_n = max(1, int(math.sqrt(length)))
    wma_half = wma(close, half)
    wma_full = wma(close, length)
    raw = 2.0 * wma_half - wma_full
    # Handle NaNs from the first wma
    raw = np.nan_to_num(raw, nan=0.0)
    return wma(raw, sqrt_n)


def calc_vwap(high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    """Cumulative VWAP (reset-free for daily data -- running cumulative)."""
    hlc3 = (high + low + close) / 3.0
    cum_vol = np.cumsum(volume)
    cum_pv = np.cumsum(hlc3 * volume)
    cum_vol = np.where(cum_vol == 0, 1e-10, cum_vol)
    return cum_pv / cum_vol


# ---------------------------------------------------------------------------
# 3. MULTI-TIMEFRAME CONFLUENCE
# ---------------------------------------------------------------------------

def calc_trend_score_series(close: np.ndarray) -> np.ndarray:
    """
    Per-bar trend score in [-1, +1]:
      EMA9 vs EMA21 → ma_score
      MACD vs Signal → macd_score
      Price vs EMA9 → price_score
      Average of three.
    """
    ema9 = ema(close, 9)
    ema21 = ema(close, 21)
    ma_score = np.where(ema9 > ema21, 1.0, np.where(ema9 < ema21, -1.0, 0.0))

    ema12 = ema(close, 12)
    ema26 = ema(close, 26)
    macd_line = ema12 - ema26
    macd_signal = ema(macd_line, 9)
    macd_score = np.where(macd_line > macd_signal, 1.0, np.where(macd_line < macd_signal, -1.0, 0.0))

    price_score = np.where(close > ema9, 1.0, np.where(close < ema9, -1.0, 0.0))

    return (ma_score + macd_score + price_score) / 3.0


def resample_htf(df: pd.DataFrame, factor: int) -> np.ndarray:
    """
    Simulate higher-timeframe close by taking every `factor`-th bar and
    forward-filling.  Returns trend score array aligned to original index.
    """
    close_arr = df["close"].values
    n = len(close_arr)

    # Sample every factor bars
    htf_close = np.full(n, np.nan)
    for i in range(0, n, factor):
        htf_close[i] = close_arr[i]
    # Forward fill
    s = pd.Series(htf_close).ffill().bfill()
    return calc_trend_score_series(s.to_numpy())


def calc_mtf_consensus(df: pd.DataFrame) -> np.ndarray:
    """
    3-TF consensus:  HTF(4x) 50%  +  Current 30%  +  LTF(from RSI<30) 20%.
    Returns score in range [-100, +100].
    """
    close_arr = df["close"].values

    # Current TF trend
    current_trend = calc_trend_score_series(close_arr)

    # HTF (simulate 4x aggregation -- e.g. daily → ~4-day)
    htf_trend = resample_htf(df, 4)

    # LTF signal: RSI<30 → oversold confirmation (+1), RSI>70 → overbought (-1)
    rsi_14 = rsi(close_arr, 14)
    ltf_score = np.where(rsi_14 < 30, 1.0, np.where(rsi_14 > 70, -1.0, 0.0))

    consensus = 0.50 * htf_trend + 0.30 * current_trend + 0.20 * ltf_score
    return consensus * 100  # scale to -100..+100


# ---------------------------------------------------------------------------
# 4. VOLUME Z-SCORE ANALYSIS
# ---------------------------------------------------------------------------

def calc_volume_zscore(volume: np.ndarray, n: int = 20) -> np.ndarray:
    vol_sma = sma(volume, n)
    rel_vol = volume / np.where(vol_sma == 0, 1e-10, vol_sma)
    rel_sma50 = sma(rel_vol, 50)
    rel_std50 = stdev(rel_vol, 50)
    rel_std50 = np.where((rel_std50 == 0) | np.isnan(rel_std50), 1e-10, rel_std50)
    z = (rel_vol - np.nan_to_num(rel_sma50, nan=1.0)) / np.nan_to_num(rel_std50, nan=1.0)
    return z, rel_vol


def calc_volume_score(volume: np.ndarray, close: np.ndarray, open_: np.ndarray,
                      vol_threshold: float = 1.2) -> np.ndarray:
    """
    Composite volume score 0-100 with spike + trend components.
    Matches Pine's volume_score formula.
    """
    n = len(volume)
    vol_sma = sma(volume, 20)
    vol_sma_safe = np.where((vol_sma == 0) | np.isnan(vol_sma), 1e-10, vol_sma)
    rel_vol = volume / vol_sma_safe

    z, _ = calc_volume_zscore(volume, 20)

    # Volume trend strength
    vol_ema_fast = ema(volume, 10)
    vol_ema_slow = ema(volume, 30)
    vol_trend_strength = np.abs(vol_ema_fast - vol_ema_slow) / vol_sma_safe * 100

    # Price/Volume divergence
    price_chg5 = np.zeros(n)
    vol_chg5 = np.zeros(n)
    for i in range(5, n):
        if close[i - 5] != 0:
            price_chg5[i] = (close[i] - close[i - 5]) / close[i - 5] * 100
        if volume[i - 5] != 0:
            vol_chg5[i] = (volume[i] - volume[i - 5]) / volume[i - 5] * 100

    bullish_div = (price_chg5 < -2) & (vol_chg5 > 50)
    bearish_div = (price_chg5 > 2) & (vol_chg5 < -30)

    vol_spike = rel_vol > vol_threshold
    vol_trend_rising = np.zeros(n, dtype=bool)
    for i in range(2, n):
        vol_trend_rising[i] = (volume[i] > volume[i - 1]) and (volume[i - 1] > volume[i - 2])

    # Composite (matching Pine formula)
    score = np.clip(
        30 * np.maximum(0, np.nan_to_num(z, nan=0.0) * 20)
        + 25 * (np.nan_to_num(vol_trend_strength, nan=0.0) / 2)
        + 20 * np.where(bullish_div | bearish_div, 1.0, np.where(vol_spike, 0.5, 0.0))
        + 15 * vol_trend_rising.astype(float)
        + 10 * np.where(rel_vol > 1.0, (rel_vol - 1.0) * 50, 0.0),
        0, 100
    )
    return score


# ---------------------------------------------------------------------------
# 5. BAYESIAN CONFIDENCE SCORING
# ---------------------------------------------------------------------------

REGIME_BASE_RATES = {
    "TRENDING": 0.65,
    "RANGING": 0.58,
    "VOLATILE": 0.52,
    "QUIET": 0.48,
    "NORMAL": 0.55,
}


def bayesian_confidence(
    regime: str,
    trend_likelihood: float,
    volume_likelihood: float,
    mtf_likelihood: float,
    regime_fitness: float,
) -> float:
    """
    Posterior = (prior_odds * combined_likelihood) / (1 + prior_odds * combined_likelihood)

    Each likelihood is a ratio vs base (>1 = supporting, <1 = opposing).
    We clamp each to [0.3, 3.0] to prevent extreme collapse from multiplication.
    """
    prior = REGIME_BASE_RATES.get(regime, 0.55)
    prior_odds = prior / (1 - prior) if prior < 1 else 99.0

    # Clamp individual likelihoods to prevent collapse
    t = np.clip(trend_likelihood, 0.3, 3.0)
    v = np.clip(volume_likelihood, 0.3, 3.0)
    m = np.clip(mtf_likelihood, 0.3, 3.0)
    r = np.clip(regime_fitness, 0.3, 3.0)

    combined = t * v * m * r
    posterior = (prior_odds * combined) / (1 + prior_odds * combined)
    return np.clip(posterior, 0, 1)


# ---------------------------------------------------------------------------
# 6. KELLY CRITERION + CIRCUIT BREAKER
# ---------------------------------------------------------------------------

def kelly_fraction(win_prob: float, tp_sl_ratio: float, regime: str) -> float:
    """
    f* = (p*b - q) / b   where p=win_prob, b=tp/sl ratio, q=1-p
    Quarter Kelly for safety.
    Regime-adjusted: Volatile=0.5x, Quiet=0.7x
    """
    p = np.clip(win_prob, 0.01, 0.99)
    b = max(tp_sl_ratio, 0.01)
    q = 1.0 - p
    f = (p * b - q) / b
    f = max(f, 0.0)

    # Quarter Kelly
    f *= 0.25

    # Regime adjustment
    if regime == "VOLATILE":
        f *= 0.5
    elif regime == "QUIET":
        f *= 0.7

    return min(f, 0.02)  # cap at 2%


# ---------------------------------------------------------------------------
# SIGNAL GRADING
# ---------------------------------------------------------------------------

def grade_signal(score: float) -> str:
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B+"
    elif score >= 60:
        return "B"
    elif score >= 50:
        return "C"
    else:
        return "D"


# ===========================================================================
# TRADE SIMULATION
# ===========================================================================

@dataclass
class Trade:
    entry_bar: int
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    regime: str
    grade: str
    confidence: float
    kelly_size: float
    exit_bar: Optional[int] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl_pct: float = 0.0


@dataclass
class EquityCurve:
    equity: float = 10000.0
    peak: float = 10000.0
    max_dd: float = 0.0
    circuit_breaker_active: bool = False
    trades: List[Trade] = field(default_factory=list)
    closed_trades: List[Trade] = field(default_factory=list)

    def update_drawdown(self):
        if self.equity > self.peak:
            self.peak = self.equity
        dd = (self.peak - self.equity) / self.peak * 100
        if dd > self.max_dd:
            self.max_dd = dd
        # Circuit breaker: halt if drawdown > 15%
        self.circuit_breaker_active = dd > 15.0
        return dd


# Global close array for regime classification (set before calling classify_regime)
close_g: np.ndarray = np.array([])


def run_backtest(name: str, df: pd.DataFrame) -> Dict:
    """Run full backtest on a single asset."""
    global close_g

    o = df["open"].values.astype(float)
    h = df["high"].values.astype(float)
    l = df["low"].values.astype(float)
    c = df["close"].values.astype(float)
    v = df["volume"].values.astype(float)
    close_g = c
    n = len(c)

    # ------ Indicators ------
    adx_arr, di_plus, di_minus = calc_adx(h, l, c, 14)
    chop_arr = calc_choppiness(h, l, c, 14)
    hurst_arr = calc_hurst(c, 50)
    vol_ratio = calc_volatility_ratio(h, l, c)

    # Regime
    regimes = classify_regime(adx_arr, chop_arr, vol_ratio, hurst_arr)

    # Adaptive MAs
    kama_fast = calc_kama(c, 9, 2, 30)
    kama_slow = calc_kama(c, 21, 2, 30)
    hma_16 = calc_hma(c, 16)
    vwap_arr = calc_vwap(h, l, c, v)

    # Trend score from MAs
    kama_bull = kama_fast > kama_slow
    hma_bull = c > hma_16
    vwap_bull = c > vwap_arr
    trend_score = kama_bull.astype(float) + hma_bull.astype(float) + vwap_bull.astype(float)

    # MTF consensus
    mtf_consensus = calc_mtf_consensus(df)

    # Volume analysis
    vol_z, rel_vol = calc_volume_zscore(v, 20)
    vol_score = calc_volume_score(v, c, o)

    # RSI
    rsi_14 = rsi(c, 14)
    rsi_2 = rsi(c, 2)

    # MACD
    ema12 = ema(c, 12)
    ema26 = ema(c, 26)
    macd_line = ema12 - ema26
    macd_signal = ema(macd_line, 9)
    macd_hist = macd_line - macd_signal

    # EMA 200 (trend filter)
    ema200 = ema(c, 200)

    # ATR for stops
    tr_arr = true_range(h, l, c)
    atr14 = rma(tr_arr, 14)

    # Price Z-score
    price_sma50 = sma(c, 50)
    price_std50 = stdev(c, 50)
    price_std50_safe = np.where((price_std50 == 0) | np.isnan(price_std50), 1e-10, price_std50)
    price_z = (c - np.nan_to_num(price_sma50, nan=c[0])) / np.nan_to_num(price_std50_safe, nan=1.0)

    # SFP detection
    swing_low = rolling_min(l, 5)
    swing_high = rolling_max(h, 5)
    # Shift by 1 for "prior"
    swing_low_prev = np.roll(swing_low, 1)
    swing_low_prev[0] = swing_low[0]
    swing_high_prev = np.roll(swing_high, 1)
    swing_high_prev[0] = swing_high[0]

    bullish_sfp = (l < swing_low_prev) & (c > swing_low_prev) & (c > o)
    bearish_sfp = (h > swing_high_prev) & (c < swing_high_prev) & (c < o)

    # Fear & Greed proxy
    vol_sma20 = sma(v, 20)
    vol_sma20_safe = np.where((vol_sma20 == 0) | np.isnan(vol_sma20), 1e-10, vol_sma20)
    rsi_normalized = np.abs(rsi_14 - 50) / 50
    vol_pctrank = pd.Series(vol_ratio).rolling(100, min_periods=10).rank(pct=True).to_numpy()
    vol_pctrank = np.nan_to_num(vol_pctrank, nan=0.5)
    mom5 = np.zeros(n)
    for i in range(5, n):
        if c[i - 5] != 0:
            mom5[i] = (c[i] - c[i - 5]) / c[i - 5] * 100
    mom_norm = np.clip((mom5 + 10) / 20, 0, 1)
    vol_dir = np.where(
        (v > vol_sma20_safe) & (c > o), 1.0,
        np.where((v > vol_sma20_safe) & (c < o), 0.0, 0.5)
    )
    fear_greed = rsi_normalized * 0.3 + vol_pctrank * 0.25 + mom_norm * 0.3 + vol_dir * 0.15

    # ------ Confluence Scoring ------
    # Long confluence (0-100)
    long_trend = np.where(kama_bull, 15.0, 0.0) + np.where(hma_bull, 10.0, 0.0) + np.where(mtf_consensus > 0, 5.0, 0.0)
    long_momentum = (
        np.where((macd_line > macd_signal) & (macd_hist > np.roll(macd_hist, 1)), 10.0, 0.0)
        + np.where((rsi_14 > 40) & (rsi_14 < 70), 5.0, 0.0)
        + np.where(adx_arr > 25, 5.0, 0.0)
        + np.where(rsi_2 < 20, 5.0, 0.0)
    )
    long_vol = np.where(vol_score > 50, 10.0, np.where(vol_score > 40, 5.0, 0.0)) + np.where(rel_vol > 1.5, 10.0, 0.0)
    long_stat = np.where((price_z < -2) & (c > ema200), 10.0, np.where(np.abs(price_z) < 1.5, 5.0, 0.0))
    long_stat += np.where(fear_greed < 0.2, 5.0, 0.0)
    long_quant = np.where(bullish_sfp, 5.0, 0.0) + np.where((hurst_arr > 0.5) & kama_bull, 3.0, 0.0) + np.where(chop_arr < 61.8, 2.0, 0.0)

    long_confluence = np.clip(long_trend + long_momentum + long_vol + long_stat + long_quant, 0, 100)

    # Short confluence
    short_trend = np.where(~kama_bull, 15.0, 0.0) + np.where(~hma_bull, 10.0, 0.0) + np.where(mtf_consensus < 0, 5.0, 0.0)
    short_momentum = (
        np.where((macd_line < macd_signal) & (macd_hist < np.roll(macd_hist, 1)), 10.0, 0.0)
        + np.where((rsi_14 > 30) & (rsi_14 < 60), 5.0, 0.0)
        + np.where(adx_arr > 25, 5.0, 0.0)
        + np.where(rsi_2 > 80, 5.0, 0.0)
    )
    short_vol = np.where(vol_score > 50, 10.0, np.where(vol_score > 40, 5.0, 0.0)) + np.where(rel_vol > 1.5, 10.0, 0.0)
    short_stat = np.where((price_z > 2) & (c < ema200), 10.0, np.where(np.abs(price_z) < 1.5, 5.0, 0.0))
    short_stat += np.where(fear_greed > 0.8, 5.0, 0.0)
    short_quant = np.where(bearish_sfp, 5.0, 0.0) + np.where((hurst_arr < 0.5) & (~kama_bull), 3.0, 0.0) + np.where(chop_arr < 61.8, 2.0, 0.0)

    short_confluence = np.clip(short_trend + short_momentum + short_vol + short_stat + short_quant, 0, 100)

    # ------ Signal Conditions (matching Pine) ------
    choppy = chop_arr > 61.8
    long_trend_ok = kama_bull & (mtf_consensus > 10) & (~choppy)
    long_mom_ok = ((macd_line > macd_signal) | (rsi_2 < 20)) & (rsi_14 < 75)
    long_vol_ok = vol_score > 35
    long_mtf_ok = np.abs(mtf_consensus) > 30

    short_trend_ok = (~kama_bull) & (mtf_consensus < -10) & (~choppy)
    short_mom_ok = ((macd_line < macd_signal) | (rsi_2 > 80)) & (rsi_14 > 25)
    short_vol_ok = vol_score > 35
    short_mtf_ok = np.abs(mtf_consensus) > 30

    # Threshold is lower for daily data (fewer bars = fewer signals)
    # Pine uses 75 on intraday; daily gets 50 to generate meaningful sample
    SIGNAL_THRESHOLD = 50

    # Relaxed conditions for daily: require trend + momentum + (volume OR mtf)
    long_condition = long_trend_ok & long_mom_ok & (long_vol_ok | long_mtf_ok) & (long_confluence >= SIGNAL_THRESHOLD)
    short_condition = short_trend_ok & short_mom_ok & (short_vol_ok | short_mtf_ok) & (short_confluence >= SIGNAL_THRESHOLD)

    # Trigger = condition AND NOT condition[1]  (edge detect)
    long_trigger = np.zeros(n, dtype=bool)
    short_trigger = np.zeros(n, dtype=bool)
    for i in range(1, n):
        long_trigger[i] = long_condition[i] and not long_condition[i - 1]
        short_trigger[i] = short_condition[i] and not short_condition[i - 1]

    # ------ Trade Simulation ------
    eq = EquityCurve()
    warmup = 55  # skip warmup bars

    for i in range(warmup, n):
        # Check open trades for exit
        for t in list(eq.trades):
            if t.direction == "LONG":
                # TP1 hit
                if h[i] >= t.take_profit_1:
                    t.exit_bar = i
                    t.exit_price = t.take_profit_1
                    t.exit_reason = "TP1"
                    t.pnl_pct = (t.exit_price - t.entry_price) / t.entry_price * 100
                # SL hit
                elif l[i] <= t.stop_loss:
                    t.exit_bar = i
                    t.exit_price = t.stop_loss
                    t.exit_reason = "SL"
                    t.pnl_pct = (t.exit_price - t.entry_price) / t.entry_price * 100
                # Time exit (5 bars, no profit)
                elif (i - t.entry_bar) >= 5 and c[i] < t.entry_price:
                    t.exit_bar = i
                    t.exit_price = c[i]
                    t.exit_reason = "TIME"
                    t.pnl_pct = (t.exit_price - t.entry_price) / t.entry_price * 100
            else:  # SHORT
                if l[i] <= t.take_profit_1:
                    t.exit_bar = i
                    t.exit_price = t.take_profit_1
                    t.exit_reason = "TP1"
                    t.pnl_pct = (t.entry_price - t.exit_price) / t.entry_price * 100
                elif h[i] >= t.stop_loss:
                    t.exit_bar = i
                    t.exit_price = t.stop_loss
                    t.exit_reason = "SL"
                    t.pnl_pct = (t.entry_price - t.exit_price) / t.entry_price * 100
                elif (i - t.entry_bar) >= 5 and c[i] > t.entry_price:
                    t.exit_bar = i
                    t.exit_price = c[i]
                    t.exit_reason = "TIME"
                    t.pnl_pct = (t.entry_price - t.exit_price) / t.entry_price * 100

            if t.exit_bar is not None:
                eq.equity += eq.equity * t.kelly_size * (t.pnl_pct / 100)
                eq.closed_trades.append(t)
                eq.trades.remove(t)

        eq.update_drawdown()

        # Skip new entries if circuit breaker active
        if eq.circuit_breaker_active:
            continue

        # Skip if already in a trade
        if eq.trades:
            continue

        regime = regimes[i] if regimes[i] is not None else "NORMAL"
        atr_val = atr14[i] if not np.isnan(atr14[i]) else c[i] * 0.02

        # ATR multiplier by regime
        atr_mult = 2.0
        if regime == "TRENDING":
            atr_mult = 2.6
        elif regime == "RANGING":
            atr_mult = 1.4
        elif regime == "VOLATILE":
            atr_mult = 2.0
        elif regime == "QUIET":
            atr_mult = 2.0

        # --- LONG SIGNAL ---
        if long_trigger[i]:
            conf = long_confluence[i]
            win_prob_est = conf / 100.0

            # Bayesian: likelihoods as ratios (1.0 = neutral, >1 = supporting)
            trend_lk = 0.5 + trend_score[i] / 3.0  # 0..3 -> 0.5..1.5
            vol_lk = 0.5 + vol_score[i] / 100.0     # 0..100 -> 0.5..1.5
            mtf_lk = 0.5 + (mtf_consensus[i] + 100) / 200.0  # -100..100 -> 0.5..1.5
            regime_fit = 1.5 if regime == "TRENDING" else (1.2 if regime in ("VOLATILE", "NORMAL") else 0.8)
            bayes_conf = bayesian_confidence(regime, trend_lk, vol_lk, mtf_lk, regime_fit)

            # Kelly
            tp_sl_ratio = 1.5  # TP1 at 1.5x ATR, SL at 1.0x ATR
            k_frac = kelly_fraction(bayes_conf, tp_sl_ratio, regime)

            sl = c[i] - atr_mult * atr_val
            tp1 = c[i] + atr_mult * atr_val * 1.5
            tp2 = c[i] + atr_mult * atr_val * 2.5

            trade = Trade(
                entry_bar=i,
                direction="LONG",
                entry_price=c[i],
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                regime=regime,
                grade=grade_signal(conf),
                confidence=bayes_conf,
                kelly_size=k_frac,
            )
            eq.trades.append(trade)

        # --- SHORT SIGNAL ---
        elif short_trigger[i]:
            conf = short_confluence[i]
            win_prob_est = conf / 100.0

            # Bayesian: short side likelihoods
            trend_lk = 0.5 + (3.0 - trend_score[i]) / 3.0
            vol_lk = 0.5 + vol_score[i] / 100.0
            mtf_lk = 0.5 + (100 - mtf_consensus[i]) / 200.0
            regime_fit = 1.5 if regime == "TRENDING" else (1.2 if regime in ("VOLATILE", "NORMAL") else 0.8)
            bayes_conf = bayesian_confidence(regime, trend_lk, vol_lk, mtf_lk, regime_fit)

            tp_sl_ratio = 1.5
            k_frac = kelly_fraction(bayes_conf, tp_sl_ratio, regime)

            sl = c[i] + atr_mult * atr_val
            tp1 = c[i] - atr_mult * atr_val * 1.5
            tp2 = c[i] - atr_mult * atr_val * 2.5

            trade = Trade(
                entry_bar=i,
                direction="SHORT",
                entry_price=c[i],
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                regime=regime,
                grade=grade_signal(conf),
                confidence=bayes_conf,
                kelly_size=k_frac,
            )
            eq.trades.append(trade)

    # Close any remaining open trades at last bar
    for t in list(eq.trades):
        t.exit_bar = n - 1
        t.exit_price = c[n - 1]
        t.exit_reason = "EOD"
        if t.direction == "LONG":
            t.pnl_pct = (t.exit_price - t.entry_price) / t.entry_price * 100
        else:
            t.pnl_pct = (t.entry_price - t.exit_price) / t.entry_price * 100
        eq.equity += eq.equity * t.kelly_size * (t.pnl_pct / 100)
        eq.closed_trades.append(t)
    eq.trades.clear()
    eq.update_drawdown()

    # ------ Compile Results ------
    all_trades = eq.closed_trades
    regime_counts = {}
    for i in range(n):
        r = regimes[i]
        regime_counts[r] = regime_counts.get(r, 0) + 1

    # Per-regime stats
    regime_stats = {}
    for regime_name in ["TRENDING", "RANGING", "VOLATILE", "QUIET", "NORMAL"]:
        rtrades = [t for t in all_trades if t.regime == regime_name]
        if rtrades:
            wins = [t for t in rtrades if t.pnl_pct > 0]
            losses = [t for t in rtrades if t.pnl_pct <= 0]
            pnls = [t.pnl_pct for t in rtrades]
            wr = len(wins) / len(rtrades) * 100
            avg_win = np.mean([t.pnl_pct for t in wins]) if wins else 0
            avg_loss = np.mean([t.pnl_pct for t in losses]) if losses else 0

            # Sharpe (annualized from daily-ish pnl)
            if len(pnls) > 1 and np.std(pnls) > 0:
                sharpe = np.mean(pnls) / np.std(pnls) * np.sqrt(252)
            else:
                sharpe = 0.0

            regime_stats[regime_name] = {
                "trades": len(rtrades),
                "win_rate": wr,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "sharpe": sharpe,
                "total_pnl": sum(pnls),
            }

    # Overall stats
    total_trades = len(all_trades)
    total_wins = len([t for t in all_trades if t.pnl_pct > 0])
    overall_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0
    pnl_list = [t.pnl_pct for t in all_trades]

    if len(pnl_list) > 1 and np.std(pnl_list) > 0:
        overall_sharpe = np.mean(pnl_list) / np.std(pnl_list) * np.sqrt(252)
    else:
        overall_sharpe = 0.0

    # Grade distribution
    grade_dist = {}
    for t in all_trades:
        grade_dist[t.grade] = grade_dist.get(t.grade, 0) + 1

    return {
        "name": name,
        "bars": n,
        "total_trades": total_trades,
        "win_rate": overall_wr,
        "total_pnl_pct": sum(pnl_list) if pnl_list else 0,
        "avg_pnl_pct": np.mean(pnl_list) if pnl_list else 0,
        "sharpe": overall_sharpe,
        "max_drawdown": eq.max_dd,
        "final_equity": eq.equity,
        "regime_counts": regime_counts,
        "regime_stats": regime_stats,
        "grade_distribution": grade_dist,
        "trades": all_trades,
    }


# ===========================================================================
# PRETTY PRINTING
# ===========================================================================

def print_header(title: str, width: int = 80):
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)


def print_section(title: str, width: int = 80):
    print()
    print(f"  --- {title} {'-' * max(0, width - len(title) - 8)}")


def print_results(results: List[Dict]):
    """Print detailed results for all assets."""

    print_header("KIMI CLAW PRO v3 -- REGIME-AWARE BACKTESTER RESULTS")

    # Per-asset summary
    print_section("Per-Asset Summary")
    print(f"  {'Asset':<8} {'Trades':>7} {'Win%':>7} {'AvgPnL':>8} {'TotPnL':>9} {'Sharpe':>8} {'MaxDD':>7} {'Final$':>10}")
    print(f"  {'-'*8} {'-'*7} {'-'*7} {'-'*8} {'-'*9} {'-'*8} {'-'*7} {'-'*10}")
    for r in results:
        print(
            f"  {r['name']:<8} {r['total_trades']:>7} {r['win_rate']:>6.1f}% "
            f"{r['avg_pnl_pct']:>7.2f}% {r['total_pnl_pct']:>8.2f}% "
            f"{r['sharpe']:>8.2f} {r['max_drawdown']:>6.1f}% "
            f"${r['final_equity']:>9,.2f}"
        )

    # Per-regime breakdown for each asset
    for r in results:
        print_section(f"{r['name']} -- Regime Breakdown")

        # Show regime bar counts
        print(f"  Regime Distribution (bars):")
        for regime, cnt in sorted(r["regime_counts"].items(), key=lambda x: -x[1]):
            pct = cnt / r["bars"] * 100
            bar_chart = "#" * int(pct / 2)
            print(f"    {regime:<12} {cnt:>5} bars ({pct:>5.1f}%)  {bar_chart}")

        print()
        if r["regime_stats"]:
            print(f"  {'Regime':<12} {'Trades':>7} {'Win%':>7} {'AvgWin':>8} {'AvgLoss':>8} {'TotPnL':>9} {'Sharpe':>8}")
            print(f"  {'-'*12} {'-'*7} {'-'*7} {'-'*8} {'-'*8} {'-'*9} {'-'*8}")
            for regime_name in ["TRENDING", "RANGING", "VOLATILE", "QUIET", "NORMAL"]:
                if regime_name in r["regime_stats"]:
                    rs = r["regime_stats"][regime_name]
                    print(
                        f"  {regime_name:<12} {rs['trades']:>7} {rs['win_rate']:>6.1f}% "
                        f"{rs['avg_win']:>7.2f}% {rs['avg_loss']:>7.2f}% "
                        f"{rs['total_pnl']:>8.2f}% {rs['sharpe']:>8.2f}"
                    )
        else:
            print("  No trades generated.")

        # Grade distribution
        if r["grade_distribution"]:
            print()
            print(f"  Signal Grade Distribution:")
            for g in ["A+", "A", "B+", "B", "C", "D"]:
                cnt = r["grade_distribution"].get(g, 0)
                if cnt > 0:
                    bar_chart = "#" * cnt
                    print(f"    {g:<4} {cnt:>4}  {bar_chart}")

    # Trade log (last 10 per asset)
    for r in results:
        if r["trades"]:
            print_section(f"{r['name']} -- Recent Trades (last 15)")
            print(
                f"  {'Dir':<6} {'Entry$':>10} {'Exit$':>10} {'SL$':>10} {'TP1$':>10} "
                f"{'PnL%':>7} {'Regime':<10} {'Grade':<5} {'Kelly%':>7} {'Conf':>6} {'Exit':>5}"
            )
            print(
                f"  {'-'*6} {'-'*10} {'-'*10} {'-'*10} {'-'*10} "
                f"{'-'*7} {'-'*10} {'-'*5} {'-'*7} {'-'*6} {'-'*5}"
            )
            for t in r["trades"][-15:]:
                print(
                    f"  {t.direction:<6} {t.entry_price:>10.2f} {t.exit_price:>10.2f} "
                    f"{t.stop_loss:>10.2f} {t.take_profit_1:>10.2f} "
                    f"{t.pnl_pct:>6.2f}% {t.regime:<10} {t.grade:<5} "
                    f"{t.kelly_size*100:>6.2f}% {t.confidence:>5.1f}% {t.exit_reason:>5}"
                )

    # Aggregate summary
    print_header("AGGREGATE SUMMARY")
    total_t = sum(r["total_trades"] for r in results)
    total_w = sum(len([t for t in r["trades"] if t.pnl_pct > 0]) for r in results)
    agg_wr = (total_w / total_t * 100) if total_t > 0 else 0
    agg_pnl = sum(r["total_pnl_pct"] for r in results) / max(len(results), 1)
    avg_sharpe = np.mean([r["sharpe"] for r in results])
    avg_dd = np.mean([r["max_drawdown"] for r in results])

    print(f"  Total trades across all assets:  {total_t}")
    print(f"  Aggregate win rate:              {agg_wr:.1f}%")
    print(f"  Average PnL per asset:           {agg_pnl:.2f}%")
    print(f"  Average Sharpe ratio:            {avg_sharpe:.2f}")
    print(f"  Average max drawdown:            {avg_dd:.1f}%")

    # Regime performance ranking (across all assets)
    print_section("Cross-Asset Regime Performance Ranking")
    regime_agg: Dict[str, List[float]] = {}
    for r in results:
        for rname, rs in r["regime_stats"].items():
            if rname not in regime_agg:
                regime_agg[rname] = []
            regime_agg[rname].append(rs["win_rate"])

    if regime_agg:
        print(f"  {'Regime':<12} {'Avg WR':>8} {'Assets':>7}")
        print(f"  {'-'*12} {'-'*8} {'-'*7}")
        for rname, wrs in sorted(regime_agg.items(), key=lambda x: -np.mean(x[1])):
            print(f"  {rname:<12} {np.mean(wrs):>7.1f}% {len(wrs):>7}")

    # Bayesian confidence analysis
    print_section("Bayesian Confidence vs Actual Outcome")
    all_trades_flat = []
    for r in results:
        all_trades_flat.extend(r["trades"])

    if all_trades_flat:
        conf_buckets = {"High (>70%)": [], "Medium (50-70%)": [], "Low (<50%)": []}
        for t in all_trades_flat:
            bucket = (
                "High (>70%)" if t.confidence > 0.70
                else "Medium (50-70%)" if t.confidence > 0.50
                else "Low (<50%)"
            )
            conf_buckets[bucket].append(t.pnl_pct > 0)

        print(f"  {'Confidence':>20} {'Trades':>7} {'Actual WR':>10}")
        print(f"  {'-'*20} {'-'*7} {'-'*10}")
        for bucket, outcomes in conf_buckets.items():
            if outcomes:
                wr = sum(outcomes) / len(outcomes) * 100
                print(f"  {bucket:>20} {len(outcomes):>7} {wr:>9.1f}%")

    print()
    print("=" * 80)
    print("  Backtest complete.  Kimi Claw Pro v3 Regime-Aware Engine.")
    print("=" * 80)
    print()


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    print()
    print("=" * 80)
    print("  KIMI CLAW PRO v3 -- REGIME-AWARE BACKTESTER")
    print("  Implements: Regime Detection | KAMA/HMA | MTF Confluence")
    print("              Volume Z-Score | Bayesian Confidence | Kelly Criterion")
    print("=" * 80)
    print()

    symbols = ["BTC", "ETH", "SOL", "XRP", "ADA"]

    print("[1/3] Fetching 1-year daily data ...")
    data = fetch_data(symbols, period="1y", interval="1d")

    if not data:
        print("\nERROR: No data fetched. Check your internet connection and yfinance/ccxt installation.")
        sys.exit(1)

    print(f"\n[2/3] Running backtests on {len(data)} assets ...")
    results = []
    for name, df in data.items():
        print(f"\n  Backtesting {name} ({len(df)} bars) ...", flush=True)
        r = run_backtest(name, df)
        results.append(r)
        print(f"    => {r['total_trades']} trades | WR {r['win_rate']:.1f}% | Sharpe {r['sharpe']:.2f} | MaxDD {r['max_drawdown']:.1f}%")

    print(f"\n[3/3] Compiling results ...")
    print_results(results)


if __name__ == "__main__":
    main()
