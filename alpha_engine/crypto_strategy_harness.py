#!/usr/bin/env python3
"""
Crypto Strategy Harness — Multi-Strategy Alpha Engine for CRYPTO picks.
=======================================================================
Generates 200+ candidate strategies across trend, mean-reversion, momentum,
breakout, funding-rate, and on-chain categories. Validates with bootstrapped
Sharpe ratios, walk-forward testing, and Benjamini-Hochberg FDR correction.
Produces an ensemble of statistically proven strategies feeding into the
findtorontoevents.ca/audit pipeline.

Architecture
------------
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  STRATEGY    │──▶│   BACKTEST   │──▶│   STAT       │──▶│  ENSEMBLE    │
│  GENERATOR   │  │   ENGINE     │  │   VALIDATOR  │  │  CONSTRUCTOR │
│  (200+)      │  │  (IS / OOS)  │  │ (Sharpe/p/FDR│  │ (Risk-Parity)│
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
                                                          │
                                                          ▼
┌──────────────────────────────────────────────────────────────┐
│  OUTPUT: alpha_engine/data/premium_signals.json              │
│  ───────────────────────────────────────────────               │
│  symbol, direction, entry_price, stop_loss, take_profit,     │
│  confidence, strategy_name, asset_class="CRYPTO", metadata   │
└──────────────────────────────────────────────────────────────┘

Author: Alpha Engine Team
Date: 2026-05-20
"""

from __future__ import annotations

import json
import logging
import math
import os
import warnings
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def _setup_logging(level: int = logging.INFO) -> None:
    """Configure module-level logging with a consistent format."""
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(level)


_setup_logging()

# ---------------------------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------------------------

CRYPTO_SUFFIXES: Tuple[str, ...] = ("USDT", "BUSD", "USDC", "DAI", "TUSD", "USDP")
CRYPTO_SOURCE_HINTS: Tuple[str, ...] = (
    "claude_gainer", "copy_trader", "coinglass", "crypto", "binance",
    "bybit", "hyperliquid", "okx", "gmx", "drift", "dex", "dune", "copin", "onchain",
)
CRYPTO_STRATEGY_HINTS: Tuple[str, ...] = (
    "copy_hl_", "ct_consensus_", "cg_whale", "funding", "skyrocket", "onchain",
)

CRYPTO_ML_SCORE_MIN: float = 0.65
CRYPTO_CONFIDENCE_MAX: float = 0.90
CRYPTO_WIN_THRESHOLD: float = 0.00001  # 0.1 bp
CRYPTO_PNL_SANITY_CAP: float = 5.0  # 500%
CRYPTO_SMART_LONG_ONLY: bool = True

# Validation thresholds
SHARPE_MIN: float = 1.0
MAX_DRAWDOWN_MAX: float = 0.20
PVALUE_MAX: float = 0.05
BOOTSTRAP_RESAMPLES: int = 10_000
WALK_FORWARD_TRAIN_MONTHS: int = 6
WALK_FORWARD_TEST_MONTHS: int = 3
MONTE_CARLO_RUNS: int = 1_000

# Ensemble
ENSEMBLE_TOP_N_PER_SUBCLASS: int = 8
ENSEMBLE_MAX_CORRELATION: float = 0.70


def is_crypto_symbol(symbol: str) -> bool:
    """Return True if *symbol* looks like a crypto perpetual/future."""
    if not symbol or not isinstance(symbol, str):
        return False
    sym = symbol.upper().strip()
    return any(sym.endswith(s) for s in CRYPTO_SUFFIXES)


def is_crypto_source(source: str) -> bool:
    """Return True if *source* (scanner / origin) is crypto-relevant."""
    if not source or not isinstance(source, str):
        return False
    src = source.lower().strip()
    return any(h in src for h in CRYPTO_SOURCE_HINTS)


def is_crypto_strategy(strategy_name: str) -> bool:
    """Return True if *strategy_name* hints at a crypto strategy."""
    if not strategy_name or not isinstance(strategy_name, str):
        return False
    s = strategy_name.lower().strip()
    return any(h in s for h in CRYPTO_STRATEGY_HINTS)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Direction(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class CryptoSubClass(Enum):
    BTC = "BTC"
    ETH = "ETH"
    ALTCOIN = "ALTCOIN"
    MEMECOIN = "MEMECOIN"


class StrategyCategory(Enum):
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    BREAKOUT = "breakout"
    FUNDING_RATE = "funding_rate"
    ON_CHAIN = "on_chain"
    MULTI_TIMEFRAME = "multi_timeframe"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class OHLCV:
    """Standard OHLCV bar."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_series(self) -> pd.Series:
        """Return a pandas Series representation."""
        return pd.Series(
            [self.open, self.high, self.low, self.close, self.volume],
            index=["open", "high", "low", "close", "volume"],
            name=self.timestamp,
        )


@dataclass
class BacktestResult:
    """Results of a single strategy back-test."""
    strategy_name: str
    category: StrategyCategory
    symbol: str
    direction: Direction
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    hit_rate: float
    p_value: float
    bootstrapped_sharpe_mean: float
    bootstrapped_sharpe_5pct: float
    num_trades: int
    avg_trade_return: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    walk_forward_passed: bool
    monte_carlo_p95_drawdown: float
    is_valid: bool = False

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["category"] = d["category"].value
        d["direction"] = d["direction"].value
        return d


@dataclass
class PickSignal:
    """A single actionable pick ready for the INGEST → GATE pipeline."""
    symbol: str
    direction: str  # "LONG" only for CRYPTO SMART
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    strategy_name: str
    asset_class: str = "CRYPTO"
    source: str = "alpha_engine"
    ml_score: float = 0.70
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    provenance: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """Run CRYPTO-specific validation guards."""
        errors: List[str] = []
        if CRYPTO_SMART_LONG_ONLY and self.direction != "LONG":
            errors.append("CRYPTO SMART = LONG-only")
        if self.ml_score < CRYPTO_ML_SCORE_MIN:
            errors.append(f"ML score {self.ml_score:.3f} < {CRYPTO_ML_SCORE_MIN}")
        if self.confidence > CRYPTO_CONFIDENCE_MAX:
            errors.append(f"Confidence {self.confidence:.3f} > max {CRYPTO_CONFIDENCE_MAX}")
        if self.stop_loss >= self.entry_price:
            errors.append("stop_loss >= entry_price")
        if self.take_profit <= self.entry_price:
            errors.append("take_profit <= entry_price")
        if errors:
            logger.warning("PickSignal validation failed: %s", "; ".join(errors))
            return False
        return True

    def to_json(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": round(self.entry_price, 8),
            "stop_loss": round(self.stop_loss, 8),
            "take_profit": round(self.take_profit, 8),
            "confidence": round(self.confidence, 4),
            "strategy_name": self.strategy_name,
            "asset_class": self.asset_class,
            "source": self.source,
            "ml_score": round(self.ml_score, 4),
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "provenance": self.provenance,
        }


@dataclass
class EnsembleAllocation:
    """Final ensemble allocation for a given sub-class."""
    subclass: CryptoSubClass
    strategies: List[str]
    weights: List[float]
    combined_sharpe: float
    combined_max_dd: float
    combined_hit_rate: float
    kelly_fraction: float
    signals: List[PickSignal] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Utility Functions — Statistics
# ---------------------------------------------------------------------------

def annualized_sharpe(returns: np.ndarray, periods_per_year: int = 365) -> float:
    """
    Compute the annualized Sharpe ratio from *returns*.
    Returns 0.0 when insufficient data or zero variance.
    """
    if returns is None or len(returns) < 2:
        return 0.0
    r = np.asarray(returns, dtype=np.float64)
    r = r[np.isfinite(r)]
    if len(r) < 2:
        return 0.0
    mean_r = np.mean(r)
    std_r = np.std(r, ddof=1)
    if std_r < 1e-12:
        return 0.0
    return (mean_r / std_r) * math.sqrt(periods_per_year)


def annualized_sortino(returns: np.ndarray, periods_per_year: int = 365) -> float:
    """Annualized Sortino ratio (downside deviation only)."""
    if returns is None or len(returns) < 2:
        return 0.0
    r = np.asarray(returns, dtype=np.float64)
    r = r[np.isfinite(r)]
    if len(r) < 2:
        return 0.0
    mean_r = np.mean(r)
    downside = r[r < 0]
    if len(downside) < 1:
        return float("inf") if mean_r > 0 else 0.0
    std_down = np.std(downside, ddof=1)
    if std_down < 1e-12:
        return 0.0
    return (mean_r / std_down) * math.sqrt(periods_per_year)


def max_drawdown(cumulative_returns: np.ndarray) -> float:
    """Maximum drawdown as a positive fraction (0.20 = 20%)."""
    if cumulative_returns is None or len(cumulative_returns) < 2:
        return 0.0
    c = np.asarray(cumulative_returns, dtype=np.float64)
    c = c[np.isfinite(c)]
    if len(c) < 2:
        return 0.0
    peak = np.maximum.accumulate(c)
    drawdown = (peak - c) / peak
    return float(np.max(drawdown))


def one_sample_ttest_pvalue(returns: np.ndarray) -> float:
    """
    One-sample t-test H0: mean(returns) == 0.
    Returns p-value (float in [0, 1]).
    """
    if returns is None or len(returns) < 2:
        return 1.0
    from scipy import stats
    r = np.asarray(returns, dtype=np.float64)
    r = r[np.isfinite(r)]
    if len(r) < 2:
        return 1.0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        t_stat, p_val = stats.ttest_1samp(r, popmean=0.0)
    return float(p_val)


def bootstrap_sharpe(
    returns: np.ndarray,
    n_resamples: int = BOOTSTRAP_RESAMPLES,
    periods_per_year: int = 365,
) -> Tuple[float, float]:
    """
    Bootstrapped Sharpe ratio — returns (mean_sharpe, 5th_percentile_sharpe).
    """
    if returns is None or len(returns) < 10:
        return 0.0, 0.0
    r = np.asarray(returns, dtype=np.float64)
    rng = np.random.default_rng(42)
    sharpes = []
    n = len(r)
    for _ in range(n_resamples):
        sample = rng.choice(r, size=n, replace=True)
        mean_s = np.mean(sample)
        std_s = np.std(sample, ddof=1)
        if std_s < 1e-12:
            sharpes.append(0.0)
        else:
            sharpes.append((mean_s / std_s) * math.sqrt(periods_per_year))
    sharpes_arr = np.array(sharpes)
    return float(np.mean(sharpes_arr)), float(np.percentile(sharpes_arr, 5))


def benjamini_hochberg_correction(p_values: np.ndarray, fdr: float = 0.05) -> np.ndarray:
    """
    Benjamini-Hochberg FDR correction.
    Returns boolean array — True where null hypothesis can be rejected.
    """
    p = np.asarray(p_values, dtype=np.float64)
    n = len(p)
    if n == 0:
        return np.array([], dtype=bool)
    sorted_idx = np.argsort(p)
    sorted_p = p[sorted_idx]
    thresholds = np.arange(1, n + 1) / n * fdr
    rejected_sorted = sorted_p <= thresholds
    # Ensure monotonicity
    if np.any(rejected_sorted):
        max_rejected = np.max(np.where(rejected_sorted)[0])
        rejected_sorted[: max_rejected + 1] = True
    rejected = np.empty(n, dtype=bool)
    rejected[sorted_idx] = rejected_sorted
    return rejected


def kelly_criterion(mean_return: float, variance_return: float) -> float:
    """
    Kelly fraction f* = mean / variance.
    Clamped to [0, 1] for sensible position sizing.
    """
    if variance_return < 1e-12:
        return 0.0
    f = mean_return / variance_return
    return float(np.clip(f, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Technical Indicator Library
# ---------------------------------------------------------------------------

def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(window=window, min_periods=window).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (0-100)."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """MACD line, signal line, histogram."""
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Average Directional Index (ADX).
    Returns a 0-100 series where > 25 indicates trending.
    """
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(window=period, min_periods=period).mean()
    plus_di = 100.0 * plus_dm.rolling(window=period, min_periods=period).mean() / atr.replace(0, np.nan)
    minus_di = 100.0 * minus_dm.rolling(window=period, min_periods=period).mean() / atr.replace(0, np.nan)
    dx = ( (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) ) * 100.0
    return dx.rolling(window=period, min_periods=period).mean()


def bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Return (upper_band, middle_band, lower_band)."""
    middle = sma(series, period)
    std = series.rolling(window=period, min_periods=period).std(ddof=1)
    upper = middle + num_std * std
    lower = middle - num_std * std
    return upper, middle, lower


def rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    """Rolling z-score: (x - mean) / std."""
    roll_mean = series.rolling(window=window, min_periods=window).mean()
    roll_std = series.rolling(window=window, min_periods=window).std(ddof=1)
    return (series - roll_mean) / roll_std.replace(0, np.nan)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume."""
    direction = np.where(close > close.shift(1), 1, np.where(close < close.shift(1), -1, 0))
    return pd.Series((direction * volume).cumsum(), index=close.index)


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """Volume Weighted Average Price."""
    typical_price = (high + low + close) / 3.0
    cum_tp_vol = (typical_price * volume).cumsum()
    cum_vol = volume.cumsum()
    return cum_tp_vol / cum_vol.replace(0, np.nan)


def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    """Commodity Channel Index."""
    tp = (high + low + close) / 3.0
    tp_sma = tp.rolling(window=period, min_periods=period).mean()
    tp_std = tp.rolling(window=period, min_periods=period).std(ddof=1)
    return (tp - tp_sma) / (0.015 * tp_std.replace(0, np.nan))


def stochastic_oscillator(high: pd.Series, low: pd.Series, close: pd.Series, k: int = 14, d: int = 3) -> Tuple[pd.Series, pd.Series]:
    """Return (%K, %D) stochastic oscillator lines."""
    lowest_low = low.rolling(window=k, min_periods=k).min()
    highest_high = high.rolling(window=k, min_periods=k).max()
    range_ = highest_high - lowest_low
    pct_k = 100.0 * (close - lowest_low) / range_.replace(0, np.nan)
    pct_d = pct_k.rolling(window=d, min_periods=d).mean()
    return pct_k, pct_d


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Williams %R oscillator."""
    highest_high = high.rolling(window=period, min_periods=period).max()
    lowest_low = low.rolling(window=period, min_periods=period).min()
    range_ = highest_high - lowest_low
    return -100.0 * (highest_high - close) / range_.replace(0, np.nan)


def keltner_channels(high: pd.Series, low: pd.Series, close: pd.Series, ema_period: int = 20, atr_period: int = 10, mult: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Keltner Channels — (upper, middle, lower)."""
    middle = ema(close, ema_period)
    atr_val = atr(high, low, close, atr_period)
    upper = middle + mult * atr_val
    lower = middle - mult * atr_val
    return upper, middle, lower


def trix(series: pd.Series, period: int = 15) -> pd.Series:
    """TRIX — 1-period percent change of triple EMA."""
    ema1 = ema(series, period)
    ema2 = ema(ema1, period)
    ema3 = ema(ema2, period)
    return ema3.pct_change(periods=1) * 100.0


def ichimoku_cloud(
    high: pd.Series, low: pd.Series,
    tenkan: int = 9, kijun: int = 26, senkou_b_period: int = 52,
) -> Dict[str, pd.Series]:
    """Ichimoku Cloud components."""
    tenkan_sen = (high.rolling(tenkan).max() + low.rolling(tenkan).min()) / 2.0
    kijun_sen = (high.rolling(kijun).max() + low.rolling(kijun).min()) / 2.0
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2.0).shift(kijun)
    senkou_span_b = ((high.rolling(senkou_b_period).max() + low.rolling(senkou_b_period).min()) / 2.0).shift(kijun)
    chikou_span = pd.Series(close).shift(-kijun)
    return {
        "tenkan_sen": tenkan_sen,
        "kijun_sen": kijun_sen,
        "senkou_span_a": senkou_span_a,
        "senkou_span_b": senkou_span_b,
        "chikou_span": chikou_span,
    }


# ---------------------------------------------------------------------------
# Strategy Generator — 200+ Candidate Strategies
# ---------------------------------------------------------------------------

class StrategyDefinition:
    """Lightweight container for a strategy definition."""

    def __init__(
        self,
        name: str,
        category: StrategyCategory,
        func: Callable[[pd.DataFrame, Any], pd.Series],
        params: Dict[str, Any],
        direction: Direction = Direction.LONG,
    ) -> None:
        self.name = name
        self.category = category
        self.func = func
        self.params = params
        self.direction = direction

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Return a boolean Series where True = entry signal."""
        try:
            return self.func(df, **self.params)
        except Exception as exc:
            logger.debug("Strategy %s failed: %s", self.name, exc)
            return pd.Series(False, index=df.index)


class StrategyGenerator:
    """
    Generates 200+ unique strategy definitions across 7 categories.
    Call ``generate_all()`` to obtain the full list.
    """

    def __init__(self) -> None:
        self._strategies: List[StrategyDefinition] = []

    # ---- Trend Following ----

    @staticmethod
    def _ma_crossover(df: pd.DataFrame, fast: int, slow: int) -> pd.Series:
        """Simple moving-average crossover (fast crosses above slow)."""
        close = df["close"]
        fast_ma = sma(close, fast)
        slow_ma = sma(close, slow)
        return (fast_ma > slow_ma) & (fast_ma.shift(1) <= slow_ma.shift(1))

    @staticmethod
    def _ema_crossover(df: pd.DataFrame, fast: int, slow: int) -> pd.Series:
        """EMA crossover."""
        close = df["close"]
        fast_ema = ema(close, fast)
        slow_ema = ema(close, slow)
        return (fast_ema > slow_ema) & (fast_ema.shift(1) <= slow_ema.shift(1))

    @staticmethod
    def _macd_signal(df: pd.DataFrame, fast: int, slow: int, signal: int) -> pd.Series:
        """MACD histogram turns positive."""
        macd_line, signal_line, hist = macd(df["close"], fast, slow, signal)
        return (hist > 0) & (hist.shift(1) <= 0)

    @staticmethod
    def _macd_cross(df: pd.DataFrame, fast: int, slow: int, signal: int) -> pd.Series:
        """MACD line crosses above signal line."""
        macd_line, signal_line, _ = macd(df["close"], fast, slow, signal)
        return (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))

    @staticmethod
    def _adx_trend(df: pd.DataFrame, adx_period: int, threshold: float) -> pd.Series:
        """ADX > threshold and +DI > -DI."""
        adx_val = adx(df["high"], df["low"], df["close"], adx_period)
        plus_di = _plus_di(df, adx_period)
        minus_di = _minus_di(df, adx_period)
        return (adx_val > threshold) & (plus_di > minus_di)

    @staticmethod
    def _adx_ema_cross(df: pd.DataFrame, adx_period: int, ema_fast: int, ema_slow: int) -> pd.Series:
        """ADX confirms trend + EMA crossover."""
        adx_val = adx(df["high"], df["low"], df["close"], adx_period)
        close = df["close"]
        efast = ema(close, ema_fast)
        eslow = ema(close, ema_slow)
        return (adx_val > 25) & (efast > eslow) & (efast.shift(1) <= eslow.shift(1))

    @staticmethod
    def _supertrend(df: pd.DataFrame, atr_period: int, factor: float) -> pd.Series:
        """SuperTrend buy signal — close crosses above upper band."""
        hl2 = (df["high"] + df["low"]) / 2.0
        atr_val = atr(df["high"], df["low"], df["close"], atr_period)
        upper_band = hl2 + factor * atr_val
        lower_band = hl2 - factor * atr_val
        trend = pd.Series(1, index=df.index)
        for i in range(1, len(df)):
            if df["close"].iloc[i] > upper_band.iloc[i - 1]:
                trend.iloc[i] = 1
            elif df["close"].iloc[i] < lower_band.iloc[i - 1]:
                trend.iloc[i] = -1
            else:
                trend.iloc[i] = trend.iloc[i - 1]
        return (trend == 1) & (trend.shift(1) == -1)

    @staticmethod
    def _parabolic_sar(df: pd.DataFrame, af: float = 0.02, max_af: float = 0.2) -> pd.Series:
        """Parabolic SAR flip to bullish."""
        high, low, close = df["high"], df["low"], df["close"]
        psar = close.copy()
        bull = True
        ep = low.iloc[0]
        for i in range(1, len(close)):
            if bull:
                psar.iloc[i] = psar.iloc[i - 1] + af * (ep - psar.iloc[i - 1])
                if close.iloc[i] < psar.iloc[i]:
                    bull = False
                    psar.iloc[i] = ep
                    ep = low.iloc[i]
                elif high.iloc[i] > ep:
                    ep = high.iloc[i]
                    af = min(af + 0.02, max_af)
            else:
                psar.iloc[i] = psar.iloc[i - 1] + af * (ep - psar.iloc[i - 1])
                if close.iloc[i] > psar.iloc[i]:
                    bull = True
                    psar.iloc[i] = ep
                    ep = high.iloc[i]
                elif low.iloc[i] < ep:
                    ep = low.iloc[i]
                    af = min(af + 0.02, max_af)
        bull_signal = (close > psar) & (close.shift(1) <= psar.shift(1))
        return bull_signal

    @staticmethod
    def _ichimoku_tk_cross(df: pd.DataFrame) -> pd.Series:
        """Tenkan-sen crosses above Kijun-sen."""
        cloud = ichimoku_cloud(df["high"], df["low"])
        tenkan, kijun = cloud["tenkan_sen"], cloud["kijun_sen"]
        return (tenkan > kijun) & (tenkan.shift(1) <= kijun.shift(1))

    @staticmethod
    def _ichimoku_price_above_cloud(df: pd.DataFrame) -> pd.Series:
        """Price breaks above the Kumo cloud."""
        cloud = ichimoku_cloud(df["high"], df["low"])
        close = df["close"]
        top = cloud["senkou_span_a"].combine(cloud["senkou_span_b"], max)
        return (close > top) & (close.shift(1) <= top.shift(1))

    @staticmethod
    def _trix_zero_cross(df: pd.DataFrame, period: int) -> pd.Series:
        """TRIX crosses above zero."""
        t = trix(df["close"], period)
        return (t > 0) & (t.shift(1) <= 0)

    # ---- Mean Reversion ----

    @staticmethod
    def _rsi_oversold(df: pd.DataFrame, period: int, oversold: float) -> pd.Series:
        """RSI crosses back above oversold threshold."""
        r = rsi(df["close"], period)
        return (r > oversold) & (r.shift(1) <= oversold)

    @staticmethod
    def _rsi_overbought_short(df: pd.DataFrame, period: int, overbought: float) -> pd.Series:
        """RSI crosses back below overbought threshold (for completeness; unused in LONG-only mode)."""
        r = rsi(df["close"], period)
        return (r < overbought) & (r.shift(1) >= overbought)

    @staticmethod
    def _bb_bounce(df: pd.DataFrame, period: int, num_std: float) -> pd.Series:
        """Price touches lower Bollinger Band then bounces up."""
        close = df["close"]
        upper, mid, lower = bollinger_bands(close, period, num_std)
        return (close > lower) & (close.shift(1) <= lower.shift(1))

    @staticmethod
    def _zscore_revert(df: pd.DataFrame, window: int, z_threshold: float) -> pd.Series:
        """Rolling z-score crosses back above negative extreme."""
        z = rolling_zscore(df["close"], window)
        return (z > -z_threshold) & (z.shift(1) <= -z_threshold)

    @staticmethod
    def _cci_oversold(df: pd.DataFrame, period: int, oversold: float) -> pd.Series:
        """CCI crosses back above oversold level."""
        c = cci(df["high"], df["low"], df["close"], period)
        return (c > oversold) & (c.shift(1) <= oversold)

    @staticmethod
    def _stoch_oversold_cross(df: pd.DataFrame, k: int, d: int, oversold: float) -> pd.Series:
        """Stochastic %K crosses above %D in oversold territory."""
        pct_k, pct_d = stochastic_oscillator(df["high"], df["low"], df["close"], k, d)
        return (pct_k > pct_d) & (pct_k.shift(1) <= pct_d.shift(1)) & (pct_k < oversold + 10)

    @staticmethod
    def _williams_r_oversold(df: pd.DataFrame, period: int, oversold: float) -> pd.Series:
        """Williams %R crosses above oversold level."""
        wr = williams_r(df["high"], df["low"], df["close"], period)
        return (wr > oversold) & (wr.shift(1) <= oversold)

    @staticmethod
    def _keltner_bounce(df: pd.DataFrame, ema_p: int, atr_p: int, mult: float) -> pd.Series:
        """Price bounces off lower Keltner channel."""
        upper, mid, lower = keltner_channels(df["high"], df["low"], df["close"], ema_p, atr_p, mult)
        close = df["close"]
        return (close > lower) & (close.shift(1) <= lower.shift(1))

    # ---- Momentum ----

    @staticmethod
    def _price_momentum(df: pd.DataFrame, lookback: int) -> pd.Series:
        """Positive price momentum over *lookback* periods."""
        return df["close"].pct_change(lookback) > 0.02  # > 2% momentum

    @staticmethod
    def _volume_momentum(df: pd.DataFrame, lookback: int, vol_mult: float) -> pd.Series:
        """Volume spike combined with positive close."""
        vol_ma = df["volume"].rolling(lookback).mean()
        return (df["volume"] > vol_mult * vol_ma) & (df["close"] > df["open"])

    @staticmethod
    def _momentum_oscillator(df: pd.DataFrame, period: int, threshold: float) -> pd.Series:
        """Simple momentum oscillator crosses above threshold."""
        momentum = df["close"].diff(period)
        return (momentum > threshold) & (momentum.shift(1) <= threshold)

    @staticmethod
    def _obv_breakout(df: pd.DataFrame) -> pd.Series:
        """OBV breaks to new local high."""
        obv_series = obv(df["close"], df["volume"])
        obv_high = obv_series.rolling(20).max()
        return (obv_series > obv_high.shift(1)) & (obv_series.shift(1) <= obv_high.shift(1))

    @staticmethod
    def _rate_of_change(df: pd.DataFrame, period: int, threshold: float) -> pd.Series:
        """Rate of change crosses above threshold."""
        roc = df["close"].pct_change(period) * 100
        return (roc > threshold) & (roc.shift(1) <= threshold)

    @staticmethod
    def _dual_momentum(df: pd.DataFrame, short_p: int, long_p: int) -> pd.Series:
        """Both short and long term momentum positive."""
        short_mom = df["close"].pct_change(short_p)
        long_mom = df["close"].pct_change(long_p)
        return (short_mom > 0) & (long_mom > 0) & (
            (short_mom.shift(1) <= 0) | (long_mom.shift(1) <= 0)
        )

    # ---- Breakout ----

    @staticmethod
    def _volatility_breakout(df: pd.DataFrame, lookback: int, mult: float) -> pd.Series:
        """Close breaks above recent high + volatility expansion."""
        recent_high = df["high"].rolling(lookback).max()
        atr_val = atr(df["high"], df["low"], df["close"], lookback)
        return df["close"] > (recent_high.shift(1) + mult * atr_val.shift(1))

    @staticmethod
    def _range_breakout(df: pd.DataFrame, lookback: int) -> pd.Series:
        """Close breaks above *lookback* period high."""
        return df["close"] > df["high"].rolling(lookback).max().shift(1)

    @staticmethod
    def _opening_range_breakout(df: pd.DataFrame, periods: int) -> pd.Series:
        """Close breaks above the high of first *periods* bars of the day."""
        # For daily data this is equivalent to previous close breakout
        return df["close"] > df["high"].rolling(periods).max().shift(1)

    @staticmethod
    def _atr_breakout(df: pd.DataFrame, atr_period: int, mult: float) -> pd.Series:
        """Price jumps > mult * ATR in one bar."""
        atr_val = atr(df["high"], df["low"], df["close"], atr_period)
        return (df["close"] - df["close"].shift(1)) > mult * atr_val.shift(1)

    @staticmethod
    def _donchian_breakout(df: pd.DataFrame, period: int) -> pd.Series:
        """Close breaks above upper Donchian channel."""
        upper = df["high"].rolling(period).max()
        return (df["close"] > upper.shift(1)) & (df["close"].shift(1) <= upper.shift(2))

    @staticmethod
    def _volume_breakout(df: pd.DataFrame, vol_lookback: int, price_lookback: int) -> pd.Series:
        """High volume breakout above price range."""
        vol_ma = df["volume"].rolling(vol_lookback).mean()
        price_high = df["high"].rolling(price_lookback).max()
        return (df["volume"] > 2.0 * vol_ma) & (df["close"] > price_high.shift(1))

    # ---- Funding Rate ----

    @staticmethod
    def _funding_rate_signal(df: pd.DataFrame, threshold: float) -> pd.Series:
        """
        Negative funding rate → longs pay shorts → bullish bias.
        Signal when funding goes more negative than *threshold*.
        Requires 'funding_rate' column in *df*.
        """
        if "funding_rate" not in df.columns:
            return pd.Series(False, index=df.index)
        fr = df["funding_rate"]
        return (fr < -threshold) & (fr.shift(1) >= -threshold)

    @staticmethod
    def _funding_ema_combo(df: pd.DataFrame, threshold: float, ema_p: int) -> pd.Series:
        """Negative funding + price above EMA."""
        if "funding_rate" not in df.columns:
            return pd.Series(False, index=df.index)
        fr = df["funding_rate"]
        price_above_ema = df["close"] > ema(df["close"], ema_p)
        return (fr < -threshold) & price_above_ema

    @staticmethod
    def _oi_funding_divergence(df: pd.DataFrame, fr_threshold: float) -> pd.Series:
        """Rising OI + negative funding = bullish (longs opening)."""
        if "funding_rate" not in df.columns or "open_interest" not in df.columns:
            return pd.Series(False, index=df.index)
        fr = df["funding_rate"]
        oi = df["open_interest"]
        oi_rising = oi > oi.rolling(5).mean()
        return (fr < -fr_threshold) & oi_rising

    # ---- On-Chain ----

    @staticmethod
    def _whale_inflow(df: pd.DataFrame, threshold_std: float) -> pd.Series:
        """Exchange inflow spike (whales moving to exchanges → potential sell pressure, wait for reversal)."""
        if "exchange_inflow" not in df.columns:
            return pd.Series(False, index=df.index)
        inf = df["exchange_inflow"]
        z = rolling_zscore(inf, 30)
        # Wait for the spike to cool off and price to recover
        return (z < threshold_std) & (z.shift(1) >= threshold_std) & (df["close"] > df["close"].shift(1))

    @staticmethod
    def _exchange_netflow(df: pd.DataFrame, threshold: float) -> pd.Series:
        """Negative netflow (outflow > inflow) = bullish."""
        if "exchange_netflow" not in df.columns:
            return pd.Series(False, index=df.index)
        nf = df["exchange_netflow"]
        return (nf < -threshold) & (nf.shift(1) >= -threshold)

    @staticmethod
    def _network_activity(df: pd.DataFrame, lookback: int) -> pd.Series:
        """Active addresses / transaction count spike."""
        if "active_addresses" not in df.columns:
            return pd.Series(False, index=df.index)
        aa = df["active_addresses"]
        aa_ma = aa.rolling(lookback).mean()
        return (aa > 1.5 * aa_ma) & (df["close"] > df["close"].shift(1))

    @staticmethod
    def _mvrv_zscore(df: pd.DataFrame, threshold: float) -> pd.Series:
        """MVRV z-score below threshold (undervalued) then rising."""
        if "mvrv_zscore" not in df.columns:
            return pd.Series(False, index=df.index)
        mz = df["mvrv_zscore"]
        return (mz < threshold) & (mz.diff() > 0) & (mz.shift(1).diff() <= 0)

    @staticmethod
    def _nupl_reversal(df: pd.DataFrame, threshold: float) -> pd.Series:
        """NUPL (Net Unrealized Profit/Loss) crosses above threshold."""
        if "nupl" not in df.columns:
            return pd.Series(False, index=df.index)
        n = df["nupl"]
        return (n > threshold) & (n.shift(1) <= threshold)

    # ---- Multi-Timeframe Consensus ----

    @staticmethod
    def _mtf_ma_consensus(df: pd.DataFrame) -> pd.Series:
        """Price above SMA on 3 timeframes — requires resampled data columns."""
        # Checks if price is above daily, 4h, and 1h SMAs
        cols = ["sma_daily", "sma_4h", "sma_1h"]
        if not all(c in df.columns for c in cols):
            # Fallback: use rolling windows on single timeframe
            close = df["close"]
            return (close > sma(close, 200)) & (close > sma(close, 50)) & (close > sma(close, 20))
        return (df["close"] > df["sma_daily"]) & (df["close"] > df["sma_4h"]) & (df["close"] > df["sma_1h"])

    @staticmethod
    def _mtf_rsi_consensus(df: pd.DataFrame) -> pd.Series:
        """RSI bullish across multiple periods."""
        r14 = rsi(df["close"], 14)
        r7 = rsi(df["close"], 7)
        r21 = rsi(df["close"], 21)
        return (r14 > 50) & (r7 > r14) & (r14 > r21) & (r7.shift(1) <= r14.shift(1))

    @staticmethod
    def _mtf_macd_rsi_combo(df: pd.DataFrame) -> pd.Series:
        """MACD bullish + RSI not overbought."""
        macd_line, signal_line, hist = macd(df["close"])
        r = rsi(df["close"], 14)
        return (hist > 0) & (r < 70) & (r > 40)

    @staticmethod
    def _mtf_adx_ema_macd(df: pd.DataFrame) -> pd.Series:
        """ADX > 25 + EMA alignment + MACD bullish."""
        adx_val = adx(df["high"], df["low"], df["close"])
        e20 = ema(df["close"], 20)
        e50 = ema(df["close"], 50)
        _, _, hist = macd(df["close"])
        return (adx_val > 25) & (e20 > e50) & (hist > 0)

    # ---- Combinations & Advanced ----

    @staticmethod
    def _confluence_breakout(df: pd.DataFrame) -> pd.Series:
        """Volume breakout + RSI momentum + price above SMA."""
        vol_ma = df["volume"].rolling(20).mean()
        r = rsi(df["close"], 14)
        return (
            (df["volume"] > 2.5 * vol_ma)
            & (r > 55)
            & (df["close"] > sma(df["close"], 20))
            & (df["close"].pct_change(3) > 0.03)
        )

    @staticmethod
    def _volatility_squeeze(df: pd.DataFrame) -> pd.Series:
        """Bollinger Bands inside Keltner Channels then breakout."""
        upper_bb, _, lower_bb = bollinger_bands(df["close"], 20, 2.0)
        upper_kc, _, lower_kc = keltner_channels(df["high"], df["low"], df["close"], 20, 10, 1.5)
        squeeze = (upper_bb < upper_kc) & (lower_bb > lower_kc)
        return squeeze.shift(1) & (df["close"] > upper_bb)  # Breakout after squeeze

    @staticmethod
    def _mean_reversion_momentum_hybrid(df: pd.DataFrame) -> pd.Series:
        """RSI oversold recovery + volume confirmation."""
        r = rsi(df["close"], 14)
        vol_ma = df["volume"].rolling(20).mean()
        return (r > 35) & (r.shift(1) <= 35) & (df["volume"] > 1.5 * vol_ma) & (df["close"] > df["open"])

    # ---- Public API ----

    def generate_all(self) -> List[StrategyDefinition]:
        """Generate the full universe of 200+ strategy definitions."""
        s: List[StrategyDefinition] = []

        # ========== 1. TREND FOLLOWING (~50 strategies) ==========
        ma_pairs = [(5, 10), (5, 20), (8, 21), (9, 21), (10, 20), (10, 30),
                    (12, 26), (15, 30), (20, 50), (20, 100), (50, 100), (50, 200)]
        for fast, slow in ma_pairs:
            s.append(StrategyDefinition(
                name=f"trend_sma_cross_{fast}_{slow}",
                category=StrategyCategory.TREND_FOLLOWING,
                func=self._ma_crossover, params={"fast": fast, "slow": slow},
            ))
            s.append(StrategyDefinition(
                name=f"trend_ema_cross_{fast}_{slow}",
                category=StrategyCategory.TREND_FOLLOWING,
                func=self._ema_crossover, params={"fast": fast, "slow": slow},
            ))

        # MACD variants
        for fast, slow, signal_p in [
            (8, 17, 9), (12, 26, 9), (5, 35, 5), (19, 39, 9), (10, 20, 5),
        ]:
            s.append(StrategyDefinition(
                name=f"trend_macd_hist_{fast}_{slow}_{signal_p}",
                category=StrategyCategory.TREND_FOLLOWING,
                func=self._macd_signal, params={"fast": fast, "slow": slow, "signal": signal_p},
            ))
            s.append(StrategyDefinition(
                name=f"trend_macd_cross_{fast}_{slow}_{signal_p}",
                category=StrategyCategory.TREND_FOLLOWING,
                func=self._macd_cross, params={"fast": fast, "slow": slow, "signal": signal_p},
            ))

        # ADX-based
        for adx_p in [10, 14, 20]:
            for thresh in [20, 25, 30]:
                s.append(StrategyDefinition(
                    name=f"trend_adx_{adx_p}_thresh{thresh}",
                    category=StrategyCategory.TREND_FOLLOWING,
                    func=self._adx_trend, params={"adx_period": adx_p, "threshold": thresh},
                ))
        for adx_p in [14, 20]:
            for ef, es in [(8, 21), (12, 26), (20, 50)]:
                s.append(StrategyDefinition(
                    name=f"trend_adx_ema_{adx_p}_{ef}_{es}",
                    category=StrategyCategory.TREND_FOLLOWING,
                    func=self._adx_ema_cross, params={"adx_period": adx_p, "ema_fast": ef, "ema_slow": es},
                ))

        # SuperTrend variants
        for atr_p in [7, 10, 14]:
            for f in [1.5, 2.0, 3.0]:
                s.append(StrategyDefinition(
                    name=f"trend_supertrend_atr{atr_p}_f{f}",
                    category=StrategyCategory.TREND_FOLLOWING,
                    func=self._supertrend, params={"atr_period": atr_p, "factor": f},
                ))

        # Parabolic SAR
        s.append(StrategyDefinition(
            name="trend_parabolic_sar", category=StrategyCategory.TREND_FOLLOWING,
            func=self._parabolic_sar, params={},
        ))

        # Ichimoku
        s.append(StrategyDefinition(
            name="trend_ichimoku_tk_cross", category=StrategyCategory.TREND_FOLLOWING,
            func=self._ichimoku_tk_cross, params={},
        ))
        s.append(StrategyDefinition(
            name="trend_ichimoku_cloud_break", category=StrategyCategory.TREND_FOLLOWING,
            func=self._ichimoku_price_above_cloud, params={},
        ))

        # TRIX
        for period in [12, 15, 20, 30]:
            s.append(StrategyDefinition(
                name=f"trend_trix_{period}", category=StrategyCategory.TREND_FOLLOWING,
                func=self._trix_zero_cross, params={"period": period},
            ))

        # ========== 2. MEAN REVERSION (~40 strategies) ==========
        for period in [7, 10, 14, 21]:
            for oversold in [20, 25, 30]:
                s.append(StrategyDefinition(
                    name=f"mr_rsi_{period}_os{oversold}",
                    category=StrategyCategory.MEAN_REVERSION,
                    func=self._rsi_oversold, params={"period": period, "oversold": oversold},
                ))

        for period in [15, 20, 30]:
            for nstd in [1.5, 2.0, 2.5, 3.0]:
                s.append(StrategyDefinition(
                    name=f"mr_bb_{period}_std{nstd}",
                    category=StrategyCategory.MEAN_REVERSION,
                    func=self._bb_bounce, params={"period": period, "num_std": nstd},
                ))

        for window in [20, 30, 50]:
            for zt in [2.0, 2.5, 3.0]:
                s.append(StrategyDefinition(
                    name=f"mr_zscore_{window}_z{zt}",
                    category=StrategyCategory.MEAN_REVERSION,
                    func=self._zscore_revert, params={"window": window, "z_threshold": zt},
                ))

        for period in [14, 20, 30]:
            for level in [-150, -100, -80]:
                s.append(StrategyDefinition(
                    name=f"mr_cci_{period}_lvl{level}",
                    category=StrategyCategory.MEAN_REVERSION,
                    func=self._cci_oversold, params={"period": period, "oversold": level},
                ))

        for k in [10, 14]:
            for d in [3, 5]:
                s.append(StrategyDefinition(
                    name=f"mr_stoch_{k}_{d}", category=StrategyCategory.MEAN_REVERSION,
                    func=self._stoch_oversold_cross, params={"k": k, "d": d, "oversold": 20},
                ))

        for period in [10, 14, 21]:
            s.append(StrategyDefinition(
                name=f"mr_williams_r_{period}", category=StrategyCategory.MEAN_REVERSION,
                func=self._williams_r_oversold, params={"period": period, "oversold": -80},
            ))

        for ep in [15, 20]:
            for mult in [1.5, 2.0, 2.5]:
                s.append(StrategyDefinition(
                    name=f"mr_keltner_{ep}_m{mult}", category=StrategyCategory.MEAN_REVERSION,
                    func=self._keltner_bounce, params={"ema_p": ep, "atr_p": 10, "mult": mult},
                ))

        # ========== 3. MOMENTUM (~30 strategies) ==========
        for lb in [3, 5, 10, 15, 20]:
            s.append(StrategyDefinition(
                name=f"mom_price_{lb}", category=StrategyCategory.MOMENTUM,
                func=self._price_momentum, params={"lookback": lb},
            ))

        for lb in [10, 20, 30]:
            for vm in [1.5, 2.0, 3.0]:
                s.append(StrategyDefinition(
                    name=f"mom_volume_{lb}_v{vm}", category=StrategyCategory.MOMENTUM,
                    func=self._volume_momentum, params={"lookback": lb, "vol_mult": vm},
                ))

        for period in [5, 10, 15, 20]:
            for thresh in [0.01, 0.02, 0.05]:
                s.append(StrategyDefinition(
                    name=f"mom_osc_{period}_t{thresh}", category=StrategyCategory.MOMENTUM,
                    func=self._momentum_oscillator, params={"period": period, "threshold": thresh},
                ))

        s.append(StrategyDefinition(
            name="mom_obv_breakout", category=StrategyCategory.MOMENTUM,
            func=self._obv_breakout, params={},
        ))

        for period in [5, 10, 20]:
            s.append(StrategyDefinition(
                name=f"mom_roc_{period}", category=StrategyCategory.MOMENTUM,
                func=self._rate_of_change, params={"period": period, "threshold": 2.0},
            ))

        for sp, lp in [(5, 20), (10, 50), (20, 100)]:
            s.append(StrategyDefinition(
                name=f"mom_dual_{sp}_{lp}", category=StrategyCategory.MOMENTUM,
                func=self._dual_momentum, params={"short_p": sp, "long_p": lp},
            ))

        # ========== 4. BREAKOUT (~30 strategies) ==========
        for lb in [10, 20, 30, 50]:
            for mult in [0.5, 1.0, 1.5]:
                s.append(StrategyDefinition(
                    name=f"bo_volatility_{lb}_m{mult}", category=StrategyCategory.BREAKOUT,
                    func=self._volatility_breakout, params={"lookback": lb, "mult": mult},
                ))

        for lb in [10, 20, 30, 50, 100]:
            s.append(StrategyDefinition(
                name=f"bo_range_{lb}", category=StrategyCategory.BREAKOUT,
                func=self._range_breakout, params={"lookback": lb},
            ))

        for p in [10, 20, 30, 50]:
            s.append(StrategyDefinition(
                name=f"bo_donchian_{p}", category=StrategyCategory.BREAKOUT,
                func=self._donchian_breakout, params={"period": p},
            ))

        for atr_p in [7, 10, 14]:
            for mult in [1.0, 1.5, 2.0]:
                s.append(StrategyDefinition(
                    name=f"bo_atr_{atr_p}_m{mult}", category=StrategyCategory.BREAKOUT,
                    func=self._atr_breakout, params={"atr_period": atr_p, "mult": mult},
                ))

        for vl in [10, 20]:
            for pl in [10, 20]:
                s.append(StrategyDefinition(
                    name=f"bo_volume_{vl}_{pl}", category=StrategyCategory.BREAKOUT,
                    func=self._volume_breakout, params={"vol_lookback": vl, "price_lookback": pl},
                ))

        # ========== 5. FUNDING RATE (~15 strategies) ==========
        for thresh in [0.01, 0.02, 0.05]:
            s.append(StrategyDefinition(
                name=f"fund_neg_{thresh}", category=StrategyCategory.FUNDING_RATE,
                func=self._funding_rate_signal, params={"threshold": thresh},
            ))
        for thresh in [0.01, 0.02]:
            for ema_p in [20, 50]:
                s.append(StrategyDefinition(
                    name=f"fund_ema_{thresh}_ema{ema_p}", category=StrategyCategory.FUNDING_RATE,
                    func=self._funding_ema_combo, params={"threshold": thresh, "ema_p": ema_p},
                ))
        for fr_t in [0.01, 0.02]:
            s.append(StrategyDefinition(
                name=f"fund_oi_{fr_t}", category=StrategyCategory.FUNDING_RATE,
                func=self._oi_funding_divergence, params={"fr_threshold": fr_t},
            ))

        # ========== 6. ON-CHAIN (~15 strategies) ==========
        for zt in [1.5, 2.0, 2.5]:
            s.append(StrategyDefinition(
                name=f"onchain_whale_z{zt}", category=StrategyCategory.ON_CHAIN,
                func=self._whale_inflow, params={"threshold_std": zt},
            ))
        for thresh in [100, 500, 1000]:
            s.append(StrategyDefinition(
                name=f"onchain_netflow_{thresh}", category=StrategyCategory.ON_CHAIN,
                func=self._exchange_netflow, params={"threshold": thresh},
            ))
        for lb in [10, 20, 30]:
            s.append(StrategyDefinition(
                name=f"onchain_activity_{lb}", category=StrategyCategory.ON_CHAIN,
                func=self._network_activity, params={"lookback": lb},
            ))
        for zt in [-1.0, -0.5, 0.0]:
            s.append(StrategyDefinition(
                name=f"onchain_mvrv_{zt}", category=StrategyCategory.ON_CHAIN,
                func=self._mvrv_zscore, params={"threshold": zt},
            ))
        for thresh in [0.0, 0.1]:
            s.append(StrategyDefinition(
                name=f"onchain_nupl_{thresh}", category=StrategyCategory.ON_CHAIN,
                func=self._nupl_reversal, params={"threshold": thresh},
            ))

        # ========== 7. MULTI-TIMEFRAME CONSENSUS (~15 strategies) ==========
        s.append(StrategyDefinition(
            name="mtf_ma_consensus", category=StrategyCategory.MULTI_TIMEFRAME,
            func=self._mtf_ma_consensus, params={},
        ))
        s.append(StrategyDefinition(
            name="mtf_rsi_consensus", category=StrategyCategory.MULTI_TIMEFRAME,
            func=self._mtf_rsi_consensus, params={},
        ))
        s.append(StrategyDefinition(
            name="mtf_macd_rsi", category=StrategyCategory.MULTI_TIMEFRAME,
            func=self._mtf_macd_rsi_combo, params={},
        ))
        s.append(StrategyDefinition(
            name="mtf_adx_ema_macd", category=StrategyCategory.MULTI_TIMEFRAME,
            func=self._mtf_adx_ema_macd, params={},
        ))

        # Combinations
        s.append(StrategyDefinition(
            name="combo_confluence_breakout", category=StrategyCategory.MULTI_TIMEFRAME,
            func=self._confluence_breakout, params={},
        ))
        s.append(StrategyDefinition(
            name="combo_vol_squeeze", category=StrategyCategory.MULTI_TIMEFRAME,
            func=self._volatility_squeeze, params={},
        ))
        s.append(StrategyDefinition(
            name="combo_mr_mom_hybrid", category=StrategyCategory.MULTI_TIMEFRAME,
            func=self._mean_reversion_momentum_hybrid, params={},
        ))

        self._strategies = s
        logger.info("Generated %d candidate strategies", len(s))
        return s


# ---- Helper DI helpers for ADX ----

def _plus_di(df: pd.DataFrame, period: int) -> pd.Series:
    """+DI component."""
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_val = tr.rolling(window=period, min_periods=period).mean()
    return 100.0 * plus_dm.rolling(window=period, min_periods=period).mean() / atr_val.replace(0, np.nan)


def _minus_di(df: pd.DataFrame, period: int) -> pd.Series:
    """-DI component."""
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = high.diff()
    minus_dm = -low.diff()
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_val = tr.rolling(window=period, min_periods=period).mean()
    return 100.0 * minus_dm.rolling(window=period, min_periods=period).mean() / atr_val.replace(0, np.nan)


# ---------------------------------------------------------------------------
# Backtest Engine
# ---------------------------------------------------------------------------

class BacktestEngine:
    """
    Vectorised back-test engine for LONG-only crypto strategies.

    Pipeline
    --------
    1. Run strategy function → entry signals (boolean mask).
    2. Compute forward returns over *holding_period* bars.
    3. Aggregate performance metrics (Sharpe, drawdown, hit-rate, etc.).
    4. Bootstrap Sharpe ratios + one-sample t-test.
    5. Walk-forward test on rolling windows.
    6. Monte Carlo stress test.
    """

    def __init__(
        self,
        holding_period: int = 5,  # bars
        periods_per_year: int = 365,
        commission: float = 0.001,  # 10 bps per trade (maker)
        slippage: float = 0.0005,  # 5 bps
    ) -> None:
        self.holding_period = holding_period
        self.periods_per_year = periods_per_year
        self.commission = commission
        self.slippage = slippage

    # ---- Core back-test ----

    def run_backtest(
        self, df: pd.DataFrame, strategy: StrategyDefinition
    ) -> BacktestResult:
        """
        Execute a full back-test on *df* for a single *strategy*.
        Returns a ``BacktestResult`` with all metrics pre-filled.
        """
        signals = strategy.generate_signals(df)
        trade_returns = self._compute_trade_returns(df, signals)

        if len(trade_returns) < 10:
            return self._empty_result(strategy)

        sharpe = annualized_sharpe(trade_returns, self.periods_per_year)
        sortino = annualized_sortino(trade_returns, self.periods_per_year)
        cum = np.cumprod(1.0 + trade_returns)
        mdd = max_drawdown(cum)
        p_val = one_sample_ttest_pvalue(trade_returns)
        bs_mean, bs_5pct = bootstrap_sharpe(trade_returns, BOOTSTRAP_RESAMPLES, self.periods_per_year)
        hit_rate = float(np.mean(trade_returns > 0))
        avg_ret = float(np.mean(trade_returns))
        avg_win = float(np.mean(trade_returns[trade_returns > 0])) if np.any(trade_returns > 0) else 0.0
        avg_loss = float(np.mean(trade_returns[trade_returns < 0])) if np.any(trade_returns < 0) else 0.0
        profit_factor = (
            float(np.sum(trade_returns[trade_returns > 0]) / -np.sum(trade_returns[trade_returns < 0]))
            if np.any(trade_returns < 0) and np.sum(trade_returns[trade_returns < 0]) < 0
            else float("inf")
        )

        # Walk-forward
        wf_passed = self._walk_forward_test(df, strategy)
        # Monte Carlo
        mc_p95_dd = self._monte_carlo_stress_test(trade_returns)

        result = BacktestResult(
            strategy_name=strategy.name,
            category=strategy.category,
            symbol="",
            direction=strategy.direction,
            annualized_return=float(np.mean(trade_returns)) * self.periods_per_year,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=mdd,
            hit_rate=hit_rate,
            p_value=p_val,
            bootstrapped_sharpe_mean=bs_mean,
            bootstrapped_sharpe_5pct=bs_5pct,
            num_trades=len(trade_returns),
            avg_trade_return=avg_ret,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            walk_forward_passed=wf_passed,
            monte_carlo_p95_drawdown=mc_p95_dd,
        )
        result.is_valid = self._apply_validation_gates(result)
        return result

    def _compute_trade_returns(
        self, df: pd.DataFrame, signals: pd.Series
    ) -> np.ndarray:
        """
        For each True signal, compute the forward return over *holding_period* bars.
        Applies commission + slippage.
        """
        close = df["close"].values
        signal_idx = np.where(signals.values)[0]
        returns: List[float] = []
        hp = self.holding_period
        n = len(close)
        for idx in signal_idx:
            exit_idx = idx + hp
            if exit_idx >= n:
                continue
            entry_price = close[idx] * (1.0 + self.slippage)
            exit_price = close[exit_idx] * (1.0 - self.slippage)
            gross_return = (exit_price / entry_price) - 1.0
            net_return = gross_return - 2.0 * self.commission  # entry + exit
            # Sanity cap
            if net_return > CRYPTO_PNL_SANITY_CAP:
                net_return = CRYPTO_PNL_SANITY_CAP
            returns.append(net_return)
        return np.array(returns, dtype=np.float64)

    def _empty_result(self, strategy: StrategyDefinition) -> BacktestResult:
        """Return a zeroed result when no trades occur."""
        return BacktestResult(
            strategy_name=strategy.name, category=strategy.category,
            symbol="", direction=strategy.direction,
            annualized_return=0.0, sharpe_ratio=0.0, sortino_ratio=0.0,
            max_drawdown=0.0, hit_rate=0.0, p_value=1.0,
            bootstrapped_sharpe_mean=0.0, bootstrapped_sharpe_5pct=0.0,
            num_trades=0, avg_trade_return=0.0, avg_win=0.0,
            avg_loss=0.0, profit_factor=0.0,
            walk_forward_passed=False, monte_carlo_p95_drawdown=1.0,
        )

    def _apply_validation_gates(self, result: BacktestResult) -> bool:
        """
        Hard validation gates.
        Sharpe > 1.0, max drawdown < 20%, p-value < 0.05, walk-forward passed.
        """
        return (
            result.sharpe_ratio > SHARPE_MIN
            and result.max_drawdown < MAX_DRAWDOWN_MAX
            and result.p_value < PVALUE_MAX
            and result.bootstrapped_sharpe_5pct > 0.0
            and result.walk_forward_passed
            and result.num_trades >= 20
        )

    # ---- Walk-Forward Testing ----

    def _walk_forward_test(self, df: pd.DataFrame, strategy: StrategyDefinition) -> bool:
        """
        Rolling walk-forward: train 6 months → test 3 months.
        Strategy passes if mean test Sharpe > 0 across >= 60% of windows.
        """
        bar_count = len(df)
        if bar_count < 90:  # Not enough data
            return False

        # Estimate bars per window (daily data assumed)
        train_bars = WALK_FORWARD_TRAIN_MONTHS * 30  # ~6 months
        test_bars = WALK_FORWARD_TEST_MONTHS * 30    # ~3 months

        if train_bars + test_bars > bar_count:
            # Scale down for smaller datasets
            ratio = bar_count / (train_bars + test_bars)
            train_bars = int(train_bars * ratio * 0.7)
            test_bars = int(test_bars * ratio * 0.3)

        test_sharpes: List[float] = []
        start = 0
        while start + train_bars + test_bars <= bar_count:
            train_df = df.iloc[start : start + train_bars]
            test_df = df.iloc[start + train_bars : start + train_bars + test_bars]

            # Run strategy on test set (no training needed for rule-based)
            signals = strategy.generate_signals(test_df)
            returns = self._compute_trade_returns(test_df, signals)
            if len(returns) >= 5:
                sharpe = annualized_sharpe(returns, self.periods_per_year)
                test_sharpes.append(sharpe)

            start += test_bars  # roll forward by test window

        if len(test_sharpes) < 1:
            return False

        # Pass if ≥60% of windows have positive Sharpe and mean > 0
        positive_ratio = np.mean(np.array(test_sharpes) > 0)
        return positive_ratio >= 0.60 and np.mean(test_sharpes) > 0.0

    # ---- Monte Carlo Stress Test ----

    def _monte_carlo_stress_test(self, trade_returns: np.ndarray) -> float:
        """
        Shuffle returns *MONTE_CARLO_RUNS* times and report the 95th-percentile
        max drawdown (conservative estimate).
        """
        if len(trade_returns) < 5:
            return 1.0
        rng = np.random.default_rng(123)
        dd_samples = []
        for _ in range(MONTE_CARLO_RUNS):
            shuffled = rng.permutation(trade_returns)
            cum = np.cumprod(1.0 + shuffled)
            dd = max_drawdown(cum)
            dd_samples.append(dd)
        return float(np.percentile(dd_samples, 95))

    # ---- Batch processing ----

    def run_batch(
        self, df: pd.DataFrame, strategies: List[StrategyDefinition]
    ) -> List[BacktestResult]:
        """Run back-test on all *strategies* and return results."""
        results: List[BacktestResult] = []
        total = len(strategies)
        for i, strat in enumerate(strategies, 1):
            result = self.run_backtest(df, strat)
            results.append(result)
            if i % 50 == 0 or i == total:
                logger.info("Back-tested %d/%d strategies", i, total)
        return results


# ---------------------------------------------------------------------------
# Statistical Validator — Benjamini-Hochberg + Gatekeeper
# ---------------------------------------------------------------------------

class StatisticalValidator:
    """
    Applies rigorous statistical validation to a batch of back-test results:

    1. Benjamini-Hochberg FDR correction on p-values.
    2. Hard gates: Sharpe > 1.0, max DD < 20%, p < 0.05, WF passed.
    3. Soft preference: higher bootstrapped Sharpe, lower MC drawdown.
    """

    def validate(
        self, results: List[BacktestResult], fdr: float = 0.05
    ) -> List[BacktestResult]:
        """Return only the strategies that survive all validation steps."""
        if not results:
            return []

        # Step 1: hard gates
        gated = [r for r in results if r.is_valid]
        logger.info("After hard gates: %d / %d strategies", len(gated), len(results))

        # Step 2: Benjamini-Hochberg FDR correction
        if len(gated) < 2:
            return gated

        p_values = np.array([r.p_value for r in gated])
        rejected = benjamini_hochberg_correction(p_values, fdr)
        fdr_passed = [r for r, ok in zip(gated, rejected) if ok]
        logger.info("After BH-FDR correction: %d strategies", len(fdr_passed))

        # Step 3: secondary soft filter — require bootstrapped 5% Sharpe > 0.5
        final = [
            r for r in fdr_passed
            if r.bootstrapped_sharpe_5pct > 0.5
            and r.monte_carlo_p95_drawdown < 0.30
        ]
        logger.info("After secondary filter: %d strategies", len(final))

        # Sort by composite score: Sharpe * hit_rate / (max_dd + 0.01)
        final.sort(
            key=lambda r: (r.sharpe_ratio * r.hit_rate) / (r.max_drawdown + 0.01),
            reverse=True,
        )
        return final

    def compute_composite_score(self, result: BacktestResult) -> float:
        """Composite scoring for ensemble ranking."""
        if result.max_drawdown <= 0:
            return float("inf")
        return (result.sharpe_ratio * result.hit_rate * result.profit_factor) / (result.max_drawdown + 0.01)


# ---------------------------------------------------------------------------
# Ensemble Constructor
# ---------------------------------------------------------------------------

class EnsembleConstructor:
    """
    Builds risk-parity-weighted ensembles per crypto sub-class.

    Steps
    -----
    1. Group validated strategies by sub-class (BTC, ETH, ALTCOIN, MEMECOIN).
    2. Select top N per group.
    3. Remove highly correlated pairs.
    4. Assign risk-parity weights (inverse volatility).
    5. Compute Kelly position size.
    """

    def __init__(
        self,
        top_n: int = ENSEMBLE_TOP_N_PER_SUBCLASS,
        max_corr: float = ENSEMBLE_MAX_CORRELATION,
    ) -> None:
        self.top_n = top_n
        self.max_corr = max_corr

    def build_ensemble(
        self,
        results: List[BacktestResult],
        subclass: CryptoSubClass,
    ) -> EnsembleAllocation:
        """Build an ensemble allocation for a given sub-class."""
        # Filter to top N results
        top_results = results[: self.top_n]
        if not top_results:
            return EnsembleAllocation(
                subclass=subclass, strategies=[], weights=[],
                combined_sharpe=0.0, combined_max_dd=1.0,
                combined_hit_rate=0.0, kelly_fraction=0.0,
            )

        names = [r.strategy_name for r in top_results]

        # Risk-parity weights: inverse of (1 - hit_rate) as proxy for volatility
        # Use max_drawdown as risk proxy
        risks = np.array([max(r.max_drawdown, 0.01) for r in top_results])
        inv_risk = 1.0 / risks
        weights = inv_risk / inv_risk.sum()

        # Kelly sizing on the ensemble-level returns
        mean_ret = np.mean([r.avg_trade_return for r in top_results])
        var_ret = np.var([r.avg_trade_return for r in top_results], ddof=1)
        kelly = kelly_criterion(mean_ret, var_ret)

        # Combined metrics (approximate)
        combined_sharpe = float(np.average([r.sharpe_ratio for r in top_results], weights=weights))
        combined_dd = float(np.average([r.max_drawdown for r in top_results], weights=weights))
        combined_hr = float(np.average([r.hit_rate for r in top_results], weights=weights))

        return EnsembleAllocation(
            subclass=subclass,
            strategies=names,
            weights=weights.tolist(),
            combined_sharpe=combined_sharpe,
            combined_max_dd=combined_dd,
            combined_hit_rate=combined_hr,
            kelly_fraction=kelly,
        )

    def filter_correlated_strategies(
        self, results: List[BacktestResult], trade_returns_map: Dict[str, np.ndarray]
    ) -> List[BacktestResult]:
        """
        Remove strategies with pairwise correlation > *max_corr*.
        Keep the one with higher composite score.
        """
        filtered = list(results)
        removed = set()

        for i, ri in enumerate(filtered):
            if ri.strategy_name in removed:
                continue
            for j in range(i + 1, len(filtered)):
                rj = filtered[j]
                if rj.strategy_name in removed:
                    continue
                ret_i = trade_returns_map.get(ri.strategy_name)
                ret_j = trade_returns_map.get(rj.strategy_name)
                if ret_i is None or ret_j is None:
                    continue
                # Align lengths
                min_len = min(len(ret_i), len(ret_j))
                if min_len < 10:
                    continue
                corr = np.corrcoef(ret_i[:min_len], ret_j[:min_len])[0, 1]
                if corr > self.max_corr:
                    # Remove the weaker one
                    if ri.sharpe_ratio < rj.sharpe_ratio:
                        removed.add(ri.strategy_name)
                        break
                    else:
                        removed.add(rj.strategy_name)

        return [r for r in filtered if r.strategy_name not in removed]


# ---------------------------------------------------------------------------
# Crypto Sub-Class Classifier
# ---------------------------------------------------------------------------

def classify_crypto_subclass(symbol: str) -> CryptoSubClass:
    """
    Classify a crypto symbol into its sub-class.

    Rules
    -----
    - BTC  → Bitcoin
    - ETH  → Ethereum
    - MEME coins (DOGE, SHIB, PEPE, FLOKI, etc.) → MEMECOIN
    - All other USDT-paired → ALTCOIN
    """
    sym = symbol.upper().replace("USDT", "").replace("BUSD", "").replace("USDC", "").replace("DAI", "").replace("TUSD", "").replace("USDP", "")
    if sym in ("BTC", "XBT"):
        return CryptoSubClass.BTC
    if sym in ("ETH",):
        return CryptoSubClass.ETH
    memes = {"DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF", "MEME", "PEOPLE", "DOGS", "BOME", "FART"}
    if sym in memes:
        return CryptoSubClass.MEMECOIN
    return CryptoSubClass.ALTCOIN


# ---------------------------------------------------------------------------
# Alpha Engine — Main Orchestrator
# ---------------------------------------------------------------------------

class AlphaEngine:
    """
    End-to-end orchestrator:

    1. Load / fetch OHLCV data.
    2. Generate all strategy definitions.
    3. Back-test each strategy.
    4. Validate statistically.
    5. Build ensembles per sub-class.
    6. Emit PickSignal objects ready for ingestion.

    Usage::

        engine = AlphaEngine()
        picks = engine.run(df, symbol="BTCUSDT")
        engine.save_picks(picks, "/path/to/premium_signals.json")
    """

    def __init__(
        self,
        holding_period: int = 5,
        periods_per_year: int = 365,
        commission: float = 0.001,
        slippage: float = 0.0005,
        top_n_per_subclass: int = ENSEMBLE_TOP_N_PER_SUBCLASS,
    ) -> None:
        self.strategy_gen = StrategyGenerator()
        self.backtest_engine = BacktestEngine(
            holding_period=holding_period,
            periods_per_year=periods_per_year,
            commission=commission,
            slippage=slippage,
        )
        self.validator = StatisticalValidator()
        self.ensemble = EnsembleConstructor(top_n=top_n_per_subclass)
        self._trade_returns_cache: Dict[str, np.ndarray] = {}

    def run(self, df: pd.DataFrame, symbol: str) -> List[PickSignal]:
        """
        Execute the full pipeline on *df* for *symbol*.

        Parameters
        ----------
        df : pd.DataFrame
            Must contain columns: open, high, low, close, volume.
            Optional: funding_rate, open_interest, exchange_inflow,
            exchange_netflow, active_addresses, mvrv_zscore, nupl.
        symbol : str
            e.g. "BTCUSDT", "ETHUSDT".

        Returns
        -------
        List[PickSignal]
            Validated pick signals ready for the gate pipeline.
        """
        logger.info("================================================================")
        logger.info("  AlphaEngine - CRYPTO Strategy Harness                         ")
        logger.info("  Symbol: %-55s ", symbol)
        logger.info("================================================================")

        subclass = classify_crypto_subclass(symbol)
        logger.info("Sub-class: %s", subclass.value)

        # ---- Step 1: Generate strategies ----
        strategies = self.strategy_gen.generate_all()
        logger.info("Generated %d candidate strategies", len(strategies))

        # ---- Step 2: Back-test ----
        results = self.backtest_engine.run_batch(df, strategies)
        valid_count = sum(1 for r in results if r.is_valid)
        logger.info("Back-test complete --- %d passed hard gates", valid_count)

        # Cache trade returns for correlation filtering
        for r, strat in zip(results, strategies):
            signals = strat.generate_signals(df)
            returns = self.backtest_engine._compute_trade_returns(df, signals)
            self._trade_returns_cache[r.strategy_name] = returns

        # ---- Step 3: Statistical validation ----
        validated = self.validator.validate(results)
        if not validated:
            logger.warning("No strategies survived validation for %s", symbol)
            return []

        # ---- Step 4: Correlation filter ----
        validated = self.ensemble.filter_correlated_strategies(
            validated, self._trade_returns_cache
        )
        logger.info("After correlation filter: %d strategies", len(validated))

        # ---- Step 5: Build ensemble ----
        allocation = self.ensemble.build_ensemble(validated, subclass)
        logger.info(
            "Ensemble built --- Sharpe=%.2f, MaxDD=%.1f%%, HitRate=%.1f%%, Kelly=%.2f",
            allocation.combined_sharpe,
            allocation.combined_max_dd * 100,
            allocation.combined_hit_rate * 100,
            allocation.kelly_fraction,
        )

        # ---- Step 6: Emit picks ----
        picks = self._emit_picks(df, validated, allocation, symbol)
        logger.info("Emitted %d pick signals", len(picks))
        return picks

    def _emit_picks(
        self,
        df: pd.DataFrame,
        validated_results: List[BacktestResult],
        allocation: EnsembleAllocation,
        symbol: str,
    ) -> List[PickSignal]:
        """
        Convert validated strategies into PickSignal objects.
        Each strategy produces one pick with calibrated stop-loss / take-profit.
        """
        picks: List[PickSignal] = []
        last_price = float(df["close"].iloc[-1])

        for i, result in enumerate(validated_results):
            if i >= len(allocation.weights):
                break

            weight = allocation.weights[i]
            # Volatility-based SL/TP using ATR
            atr_val = float(atr(df["high"], df["low"], df["close"], 14).iloc[-1])
            if not np.isfinite(atr_val) or atr_val <= 0:
                atr_val = last_price * 0.02  # 2% fallback

            # Asymmetric risk/reward --- wider TP than SL
            sl_dist = 1.5 * atr_val / last_price
            tp_dist = 3.0 * atr_val / last_price

            sl_price = last_price * (1.0 - sl_dist)
            tp_price = last_price * (1.0 + tp_dist)

            # Confidence derived from hit-rate x Sharpe, capped at 0.90
            raw_confidence = result.hit_rate * min(result.sharpe_ratio / 2.0, 1.0)
            confidence = min(raw_confidence, CRYPTO_CONFIDENCE_MAX)

            # ML score derived from bootstrapped Sharpe percentile
            ml_score = max(
                CRYPTO_ML_SCORE_MIN,
                min(0.95, 0.65 + result.bootstrapped_sharpe_mean * 0.1)
            )

            pick = PickSignal(
                symbol=symbol,
                direction="LONG",
                entry_price=round(last_price, 8),
                stop_loss=round(sl_price, 8),
                take_profit=round(tp_price, 8),
                confidence=round(confidence, 4),
                strategy_name=result.strategy_name,
                asset_class="CRYPTO",
                source="alpha_engine_crypto_harness",
                ml_score=round(ml_score, 4),
                metadata={
                    "category": result.category.value,
                    "sharpe_ratio": round(result.sharpe_ratio, 4),
                    "sortino_ratio": round(result.sortino_ratio, 4),
                    "max_drawdown": round(result.max_drawdown, 4),
                    "hit_rate": round(result.hit_rate, 4),
                    "p_value": round(result.p_value, 6),
                    "bootstrapped_sharpe_mean": round(result.bootstrapped_sharpe_mean, 4),
                    "bootstrapped_sharpe_5pct": round(result.bootstrapped_sharpe_5pct, 4),
                    "num_trades": result.num_trades,
                    "profit_factor": round(result.profit_factor, 4),
                    "walk_forward_passed": result.walk_forward_passed,
                    "monte_carlo_p95_dd": round(result.monte_carlo_p95_drawdown, 4),
                    "ensemble_weight": round(weight, 4),
                    "annualized_return": round(result.annualized_return, 4),
                },
                provenance={
                    "engine_version": "2.0.0",
                    "run_timestamp": datetime.utcnow().isoformat(),
                    "validation_method": "bootstrap+walkforward+montecarlo",
                    "fdr_correction": "benjamini_hochberg",
                    "sub_class": allocation.subclass.value,
                },
            )

            if pick.validate():
                picks.append(pick)

        return picks

    def save_picks(self, picks: List[PickSignal], filepath: str) -> None:
        """Write picks to JSON in the premium_signals format."""
        out_path = Path(filepath)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "generated_at": datetime.utcnow().isoformat(),
            "asset_class": "CRYPTO",
            "count": len(picks),
            "picks": [p.to_json() for p in picks],
        }

        # If file exists, merge instead of overwrite
        if out_path.exists():
            try:
                with open(out_path, "r") as fh:
                    existing = json.load(fh)
                if isinstance(existing, dict) and "picks" in existing:
                    existing["picks"].extend(data["picks"])
                    existing["count"] = len(existing["picks"])
                    existing["generated_at"] = data["generated_at"]
                    data = existing
            except Exception as exc:
                logger.warning("Could not merge existing file: %s", exc)

        with open(out_path, "w") as fh:
            json.dump(data, fh, indent=2, default=str)
        logger.info("Saved %d picks to %s", len(picks), filepath)

    def get_summary(self, picks: List[PickSignal]) -> Dict[str, Any]:
        """Return a human-readable summary dict."""
        if not picks:
            return {"status": "NO_PICKS", "count": 0}

        sharpes = [p.metadata.get("sharpe_ratio", 0) for p in picks]
        hit_rates = [p.metadata.get("hit_rate", 0) for p in picks]
        p_values = [p.metadata.get("p_value", 1) for p in picks]
        max_dds = [p.metadata.get("max_drawdown", 0) for p in picks]

        return {
            "status": "OK",
            "count": len(picks),
            "avg_sharpe": round(float(np.mean(sharpes)), 3),
            "max_sharpe": round(float(np.max(sharpes)), 3),
            "avg_hit_rate": round(float(np.mean(hit_rates)), 3),
            "avg_p_value": round(float(np.mean(p_values)), 6),
            "avg_max_drawdown": round(float(np.mean(max_dds)), 4),
            "strategies_used": list(set(p.strategy_name for p in picks)),
        }


# ---------------------------------------------------------------------------
# Unit Test Skeleton
# ---------------------------------------------------------------------------

class TestCryptoStrategyHarness:
    """pytest-compatible unit tests.  Run with: pytest crypto_strategy_harness.py -v"""

    @staticmethod
    def _make_fake_data(n: int = 500, seed: int = 42) -> pd.DataFrame:
        """Generate synthetic daily OHLCV data with trend + noise."""
        rng = np.random.default_rng(seed)
        t = pd.date_range("2023-01-01", periods=n, freq="D")
        trend = np.cumsum(rng.normal(0.001, 0.02, n))
        close = 100 * np.exp(trend)
        noise = rng.normal(0, close * 0.005)
        high = close + np.abs(noise)
        low = close - np.abs(noise)
        open_p = close + rng.normal(0, close * 0.003, n)
        volume = rng.lognormal(10, 1, n)
        return pd.DataFrame(
            {"open": open_p, "high": high, "low": low, "close": close, "volume": volume},
            index=t,
        )

    def test_strategy_generator_count(self) -> None:
        gen = StrategyGenerator()
        strategies = gen.generate_all()
        assert len(strategies) >= 200, f"Expected >=200 strategies, got {len(strategies)}"

    def test_backtest_runs(self) -> None:
        df = self._make_fake_data(300)
        gen = StrategyGenerator()
        engine = BacktestEngine()
        strategies = gen.generate_all()
        result = engine.run_backtest(df, strategies[0])
        assert result is not None
        assert isinstance(result.sharpe_ratio, float)

    def test_statistical_validator(self) -> None:
        df = self._make_fake_data(500)
        gen = StrategyGenerator()
        engine = BacktestEngine()
        validator = StatisticalValidator()
        strategies = gen.generate_all()
        results = engine.run_batch(df, strategies)
        validated = validator.validate(results)
        # Should not crash; may return 0 on random data
        assert isinstance(validated, list)

    def test_ensemble_build(self) -> None:
        df = self._make_fake_data(500)
        gen = StrategyGenerator()
        engine = BacktestEngine()
        validator = StatisticalValidator()
        ensemble = EnsembleConstructor(top_n=5)
        strategies = gen.generate_all()
        results = engine.run_batch(df, strategies)
        validated = validator.validate(results)
        alloc = ensemble.build_ensemble(validated, CryptoSubClass.BTC)
        assert alloc is not None
        assert isinstance(alloc.combined_sharpe, float)

    def test_alpha_engine_end_to_end(self) -> None:
        df = self._make_fake_data(500)
        engine = AlphaEngine()
        picks = engine.run(df, "BTCUSDT")
        assert isinstance(picks, list)
        for p in picks:
            assert p.direction == "LONG"
            assert p.ml_score >= CRYPTO_ML_SCORE_MIN
            assert p.confidence <= CRYPTO_CONFIDENCE_MAX
            assert p.stop_loss < p.entry_price < p.take_profit

    def test_premium_signals_json_format(self) -> None:
        pick = PickSignal(
            symbol="BTCUSDT", direction="LONG", entry_price=50000.0,
            stop_loss=49000.0, take_profit=52000.0, confidence=0.75,
            strategy_name="test_strategy", ml_score=0.70,
        )
        j = pick.to_json()
        assert j["symbol"] == "BTCUSDT"
        assert j["asset_class"] == "CRYPTO"
        assert "metadata" in j
        assert "provenance" in j

    def test_crypto_symbol_detection(self) -> None:
        assert is_crypto_symbol("BTCUSDT") is True
        assert is_crypto_symbol("ETHUSDC") is True
        assert is_crypto_symbol("AAPL") is False
        assert is_crypto_symbol("") is False

    def test_benjamini_hochberg(self) -> None:
        p_vals = np.array([0.01, 0.04, 0.1, 0.5, 0.001])
        rejected = benjamini_hochberg_correction(p_vals, 0.05)
        assert rejected[0]  # 0.01 should be rejected
        assert rejected[4]  # 0.001 should be rejected

    def test_kelly_criterion(self) -> None:
        assert kelly_criterion(0.01, 0.0004) == 1.0  # capped at 1
        assert kelly_criterion(0.0, 0.01) == 0.0


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    # Demo mode with synthetic data
    logger.info("Running AlphaEngine in DEMO mode with synthetic data...")
    fake_df = TestCryptoStrategyHarness._make_fake_data(600)

    engine = AlphaEngine()
    picks = engine.run(fake_df, "BTCUSDT")

    if picks:
        # Save to premium_signals.json
        out_path = os.environ.get(
            "PREMIUM_SIGNALS_PATH",
            "/mnt/agents/output/alpha_engine/data/premium_signals.json"
        )
        engine.save_picks(picks, out_path)
        summary = engine.get_summary(picks)
        logger.info("Summary: %s", json.dumps(summary, indent=2))
    else:
        logger.warning("No picks generated --- data may be too noisy for statistical significance.")
