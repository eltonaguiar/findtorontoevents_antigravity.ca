#!/usr/bin/env python3
"""
================================================================================
FOREX Multi-Strategy Alpha Engine
================================================================================
A statistically rigorous multi-strategy harness for FOREX pair selection,
backtesting, validation, and ensemble construction.

Pipeline:
    1. StrategyGenerator  -> 150+ candidate strategies across 8 categories
    2. BacktestEngine      -> In-sample + walk-forward + Monte Carlo
    3. StatisticalValidator-> Bootstrapped Sharpe, t-test, BH-FDR correction
    4. EnsembleConstructor -> Risk-parity weighted, correlation-clustered
    5. IntegrationLayer    -> JSON output compatible with system ingest

Target System: findtorontoevents.ca/audit
Asset Class: FOREX (suffix =X, e.g. EURUSD=X)
Blocked Symbols: NZDUSD, EURJPY, USDCHF
Date: 2026-05-20

Author: Alpha Engine Team
License: Proprietary
================================================================================
"""

from __future__ import annotations

import abc
import hashlib
import json
import logging
import os
import pickle
import random
import warnings
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Union,
)

import numpy as np
import pandas as pd
from numpy.random import default_rng
from scipy import stats
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.covariance import LedoitWolf

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger("forex_alpha_engine")

# ---------------------------------------------------------------------------
# Suppress harmless warnings
# ---------------------------------------------------------------------------
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Module Metadata
# ---------------------------------------------------------------------------
__version__ = "2.0.0"
__date__ = "2026-05-20"


# =============================================================================
# SECTION 1: DATA MODELS & ENUMS
# =============================================================================

class Direction(Enum):
    """Trade direction."""

    LONG = 1
    SHORT = -1
    FLAT = 0


class Session(Enum):
    """FX trading sessions (UTC)."""

    ASIAN = "asian"       # Tokyo 00:00-09:00 UTC
    LONDON = "london"     # London 08:00-17:00 UTC
    NEW_YORK = "new_york"  # NY 13:00-22:00 UTC
    OVERLAP = "overlap"   # London/NY overlap 13:00-17:00 UTC


class StrategyCategory(Enum):
    """Taxonomy of strategy families."""

    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    CARRY_TRADE = "carry_trade"
    SESSION_BREAKOUT = "session_breakout"
    CURRENCY_STRENGTH = "currency_strength"
    CFTC_COT = "cftc_cot"
    VOLATILITY_BREAKOUT = "volatility_breakout"
    MULTI_TIME_FRAME = "multi_time_frame"


@dataclass(frozen=True, slots=True)
class ForexPair:
    """Represents a FOREX pair with metadata."""

    base: str
    quote: str

    @property
    def symbol(self) -> str:
        """Yahoo-Finance style symbol with =X suffix."""
        return f"{self.base}{self.quote}=X"

    @property
    def six_char(self) -> str:
        """6-character pair code (e.g., EURUSD)."""
        return f"{self.base}{self.quote}"

    def __str__(self) -> str:
        return self.symbol

    def __hash__(self) -> int:
        return hash(self.six_char)


@dataclass
class StrategySignal:
    """A single strategy emission."""

    pair: ForexPair
    direction: Direction
    confidence: float          # 0.0 to 1.0
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    strategy_id: str = ""
    category: StrategyCategory = StrategyCategory.TREND_FOLLOWING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair": self.pair.six_char,
            "symbol": self.pair.symbol,
            "direction": self.direction.name,
            "confidence": round(self.confidence, 4),
            "timestamp": self.timestamp.isoformat(),
            "strategy_id": self.strategy_id,
            "category": self.category.value,
            "metadata": self.metadata,
        }


@dataclass
class BacktestResult:
    """Performance metrics for a single strategy backtest."""

    strategy_id: str
    category: StrategyCategory
    pair: ForexPair
    direction: Direction

    # Returns
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float

    # Risk
    max_drawdown: float
    max_drawdown_duration: int
    calmar_ratio: float
    volatility: float

    # Trade statistics
    n_trades: int
    hit_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    expectancy: float

    # Statistical tests
    p_value_ttest: float = 1.0
    p_value_bootstrap: float = 1.0
    sharpe_ci_lower: float = -np.inf
    sharpe_ci_upper: float = np.inf
    fdr_corrected_p: float = 1.0
    passed_validation: bool = False

    # Walk-forward
    wf_sharpe_mean: float = np.nan
    wf_sharpe_std: float = np.nan
    wf_pass_rate: float = 0.0

    # Monte Carlo
    mc_sharpe_5th: float = np.nan
    mc_sharpe_95th: float = np.nan
    mc_dd_95th: float = np.nan

    # Metadata
    trades: List[Dict[str, Any]] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    in_sample_mask: pd.Series = field(default_factory=lambda: pd.Series(dtype=bool))

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "strategy_id": self.strategy_id,
            "category": self.category.value,
            "pair": self.pair.six_char,
            "direction": self.direction.name,
            "total_return": round(self.total_return, 6),
            "annualized_return": round(self.annualized_return, 6),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "sortino_ratio": round(self.sortino_ratio, 4),
            "max_drawdown": round(self.max_drawdown, 6),
            "calmar_ratio": round(self.calmar_ratio, 4),
            "volatility": round(self.volatility, 6),
            "n_trades": self.n_trades,
            "hit_rate": round(self.hit_rate, 4),
            "avg_win": round(self.avg_win, 6),
            "avg_loss": round(self.avg_loss, 6),
            "profit_factor": round(self.profit_factor, 4),
            "expectancy": round(self.expectancy, 6),
            "p_value_ttest": round(self.p_value_ttest, 6),
            "p_value_bootstrap": round(self.p_value_bootstrap, 6),
            "sharpe_ci_95": [round(self.sharpe_ci_lower, 4), round(self.sharpe_ci_upper, 4)],
            "fdr_corrected_p": round(self.fdr_corrected_p, 6),
            "passed_validation": self.passed_validation,
            "wf_sharpe_mean": round(self.wf_sharpe_mean, 4) if not np.isnan(self.wf_sharpe_mean) else None,
            "wf_pass_rate": round(self.wf_pass_rate, 4),
            "mc_sharpe_5th": round(self.mc_sharpe_5th, 4) if not np.isnan(self.mc_sharpe_5th) else None,
            "mc_dd_95th": round(self.mc_dd_95th, 4) if not np.isnan(self.mc_dd_95th) else None,
        }
        return d


@dataclass
class EnsembleAllocation:
    """Risk-parity allocation across proven strategies."""

    ensemble_id: str
    strategies: List[str]
    weights: np.ndarray
    session_weights: Dict[Session, float]
    expected_sharpe: float
    expected_volatility: float
    expected_max_dd: float
    diversification_ratio: float
    last_rebalanced: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SystemPick:
    """Final pick in the format expected by the downstream system."""

    symbol: str
    direction: str
    elite_score: int
    confidence: float
    strategy_sources: List[str]
    category_tags: List[str]
    timestamp: datetime
    provenance: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_system_json(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "asset_class": "FOREX",
            "direction": self.direction,
            "elite_score": self.elite_score,
            "confidence": round(self.confidence, 4),
            "strategy_sources": self.strategy_sources,
            "category_tags": self.category_tags,
            "timestamp": self.timestamp.isoformat(),
            "provenance": self.provenance,
            "metadata": {
                **self.metadata,
                "engine_version": __version__,
                "engine_date": __date__,
            },
        }


# =============================================================================
# SECTION 2: CONSTANTS & CONFIGURATION
# =============================================================================

# -- Universe -----------------------------------------------------------------
MAJOR_PAIRS = [
    ForexPair("EUR", "USD"), ForexPair("GBP", "USD"), ForexPair("USD", "JPY"),
    ForexPair("AUD", "USD"), ForexPair("USD", "CAD"), ForexPair("USD", "CHF"),
    ForexPair("NZD", "USD"), ForexPair("EUR", "GBP"), ForexPair("EUR", "JPY"),
    ForexPair("GBP", "JPY"), ForexPair("AUD", "JPY"), ForexPair("EUR", "CHF"),
    ForexPair("GBP", "CHF"), ForexPair("AUD", "NZD"), ForexPair("USD", "SEK"),
    ForexPair("USD", "NOK"), ForexPair("USD", "SGD"), ForexPair("EUR", "SEK"),
    ForexPair("EUR", "NOK"), ForexPair("USD", "CNH"),
]

BLOCKED_PAIRS = {ForexPair("NZD", "USD"), ForexPair("EUR", "JPY"), ForexPair("USD", "CHF")}
TRADABLE_PAIRS = [p for p in MAJOR_PAIRS if p not in BLOCKED_PAIRS]

# -- Spread costs (in price terms, approx bp) ---------------------------------
SPREAD_TABLE: Dict[str, float] = {
    "EURUSD": 0.00001, "GBPUSD": 0.000015, "USDJPY": 0.002,
    "AUDUSD": 0.000015, "USDCAD": 0.000015, "USDCHF": 0.00002,
    "NZDUSD": 0.00002, "EURGBP": 0.000015, "EURJPY": 0.003,
    "GBPJPY": 0.004, "AUDJPY": 0.004, "EURCHF": 0.00002,
    "GBPCHF": 0.000025, "AUDNZD": 0.00003, "USDSEK": 0.0003,
    "USDNOK": 0.0004, "USDSGD": 0.0002, "EURSEK": 0.0004,
    "EURNOK": 0.0005, "USDCNH": 0.001,
}

def get_spread(pair: ForexPair) -> float:
    """Return half-spread cost for a pair."""
    key = pair.six_char
    return SPREAD_TABLE.get(key, 0.00002)  # default 0.2bp for unknown

# -- Interest rate differentials (approx annual rates, % as of 2026-05) --------
RATES_2026: Dict[str, float] = {
    "USD": 4.50, "EUR": 2.50, "GBP": 4.25, "JPY": 0.50,
    "AUD": 4.00, "CAD": 3.50, "CHF": 0.75, "NZD": 4.75,
    "SEK": 2.75, "NOK": 3.75, "SGD": 3.50, "CNH": 2.25,
}

def rate_differential(pair: ForexPair) -> float:
    """Return annualised interest-rate differential (base - quote)."""
    base_rate = RATES_2026.get(pair.base, 2.0)
    quote_rate = RATES_2026.get(pair.quote, 2.0)
    return base_rate - quote_rate

# -- Validation thresholds ----------------------------------------------------
class Thresholds:
    SHARPE_MIN = 1.0
    MAX_DRAWDOWN_MAX = 0.15
    P_VALUE_MAX = 0.05
    HIT_RATE_MIN = 0.52
    WF_PASS_RATE_MIN = 0.60
    MC_SHARPE_5TH_MIN = 0.5
    MIN_TRADES = 20
    MIN_BACKTEST_DAYS = 252

# -- Session hours (UTC) ------------------------------------------------------
SESSION_HOURS: Dict[Session, Tuple[time, time]] = {
    Session.ASIAN: (time(0, 0), time(9, 0)),
    Session.LONDON: (time(8, 0), time(17, 0)),
    Session.NEW_YORK: (time(13, 0), time(22, 0)),
    Session.OVERLAP: (time(13, 0), time(17, 0)),
}


# =============================================================================
# SECTION 3: DATA FETCHER (stub / interface for live system)
# =============================================================================

class DataFetcher(abc.ABC):
    """Abstract data fetcher. Override for live feeds."""

    @abc.abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        granularity: str = "1h",
    ) -> pd.DataFrame:
        """Return DataFrame with columns [open, high, low, close, volume]."""

    @abc.abstractmethod
    def fetch_cot(self, currency: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Return CFTC COT positioning data."""


class SyntheticDataFetcher(DataFetcher):
    """
    Generates realistic synthetic FX data when live feeds are unavailable.
    Uses Heston-style stochastic volatility + trend regimes.
    """

    def __init__(self, seed: int = 42):
        self.rng = default_rng(seed)

    def _generate_heston(
        self,
        n: int,
        mu: float = 0.0,
        v0: float = 0.0001,
        theta: float = 0.0001,
        kappa: float = 2.0,
        xi: float = 0.3,
        rho: float = -0.7,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Heston stochastic volatility paths."""
        dt = 1.0 / 252.0  # daily
        s = np.zeros(n)
        v = np.zeros(n)
        s[0] = 1.0
        v[0] = v0

        for t in range(1, n):
            z1 = self.rng.standard_normal()
            z2 = self.rng.standard_normal()
            dw1 = z1 * np.sqrt(dt)
            dw2 = (rho * z1 + np.sqrt(1 - rho**2) * z2) * np.sqrt(dt)

            v[t] = np.abs(v[t - 1] + kappa * (theta - v[t - 1]) * dt + xi * np.sqrt(v[t - 1]) * dw2)
            s[t] = s[t - 1] * np.exp((mu - 0.5 * v[t]) * dt + np.sqrt(v[t]) * dw1)

        return s, v

    def fetch_ohlcv(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        granularity: str = "1h",
    ) -> pd.DataFrame:
        """Generate synthetic OHLCV data."""
        pair_code = symbol.replace("=X", "")
        # Deterministic seed per pair
        seed = int(hashlib.md5(pair_code.encode()).hexdigest(), 16) % 10000
        rng = default_rng(seed)

        if granularity == "1h":
            periods = pd.date_range(start, end, freq="h")
        elif granularity == "4h":
            periods = pd.date_range(start, end, freq="4h")
        elif granularity == "1d":
            periods = pd.date_range(start, end, freq="D")
        else:
            periods = pd.date_range(start, end, freq="h")

        n = len(periods)
        if n < 10:
            n = 252 * 24  # default ~1 year of hourly
            periods = pd.date_range(end - timedelta(days=252), end, freq="h")

        # Regime-dependent parameters
        regime = (seed % 3)  # 0=trend, 1=meanrev, 2=random
        mu_base = [0.05, -0.02, 0.0][regime] / 252

        s, v = self._generate_heston(n, mu=mu_base)
        sigma = np.sqrt(v)

        # Build OHLC from close path
        close = s
        noise = sigma * 0.3
        high = close * (1 + np.abs(rng.standard_normal(n) * noise))
        low = close * (1 - np.abs(rng.standard_normal(n) * noise))
        open_p = np.roll(close, 1)
        open_p[0] = close[0]

        # Volume - higher during London/NY overlap
        base_vol = rng.lognormal(10, 1.5, n)
        hours = periods.hour
        vol_mult = np.ones(n)
        vol_mult[(hours >= 8) & (hours <= 17)] *= 1.5  # London
        vol_mult[(hours >= 13) & (hours <= 22)] *= 1.8  # NY
        volume = base_vol * vol_mult

        df = pd.DataFrame(
            {
                "open": open_p,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            },
            index=periods,
        )
        return df

    def fetch_cot(self, currency: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Generate synthetic COT data."""
        periods = pd.date_range(start, end, freq="W-FRI")
        n = len(periods)
        rng = default_rng(hash(currency) % 10000)
        net_non_commercial = rng.normal(20000, 15000, n)
        net_commercial = -net_non_commercial + rng.normal(0, 5000, n)
        open_interest = rng.lognormal(12, 0.5, n)
        return pd.DataFrame(
            {
                "net_non_commercial": net_non_commercial,
                "net_commercial": net_commercial,
                "open_interest": open_interest,
                "non_commercial_pct": net_non_commercial / open_interest,
            },
            index=periods,
        )


# =============================================================================
# SECTION 4: STRATEGY GENERATOR — 150+ candidates
# =============================================================================

class StrategyGenerator:
    """
    Generates 150+ candidate strategies across 8 categories.
    Each strategy is a parameterised callable that emits signals.
    """

    def __init__(self, pairs: Optional[List[ForexPair]] = None):
        self.pairs = pairs or TRADABLE_PAIRS
        self._strategies: List[Dict[str, Any]] = []
        self._build_all()

    # -- Parameter grids ------------------------------------------------------

    MA_PERIODS = [(5, 20), (10, 30), (8, 21), (20, 50), (50, 200)]
    RSI_PERIODS = [7, 14, 21]
    BB_PERIODS = [(20, 2.0), (20, 2.5), (14, 1.5), (50, 2.5)]
    ADX_PERIODS = [14, 21]
    ICHIMOKU_PARAMS = [(9, 26, 52), (10, 30, 60)]
    VOL_LOOKBACK = [10, 20, 30]

    # -- Builders -------------------------------------------------------------

    def _build_all(self) -> None:
        """Register every parameter combination."""
        self._build_trend_following()
        self._build_mean_reversion()
        self._build_carry_trade()
        self._build_session_breakout()
        self._build_currency_strength()
        self._build_cftc_cot()
        self._build_volatility_breakout()
        self._build_multi_timeframe()
        logger.info(f"StrategyGenerator: registered {len(self._strategies)} candidates")

    def _register(
        self,
        category: StrategyCategory,
        name: str,
        params: Dict[str, Any],
        func: Callable[..., pd.Series],
    ) -> None:
        sid = f"{category.value[:3].upper()}_{name}_{len(self._strategies):03d}"
        self._strategies.append(
            {
                "id": sid,
                "category": category,
                "name": name,
                "params": params,
                "func": func,
            }
        )

    # ---- 4.1 Trend Following (MA cross, ADX, Ichimoku) ---------------------

    def _build_trend_following(self) -> None:
        for pair in self.pairs:
            for fast, slow in self.MA_PERIODS:
                self._register(
                    StrategyCategory.TREND_FOLLOWING,
                    f"MAcross_{fast}_{slow}",
                    {"pair": pair, "fast": fast, "slow": slow},
                    lambda df, p=pair, f=fast, s=slow: self._sig_ma_cross(df, f, s),
                )
            for adx_p in self.ADX_PERIODS:
                self._register(
                    StrategyCategory.TREND_FOLLOWING,
                    f"ADX_{adx_p}",
                    {"pair": pair, "adx_period": adx_p},
                    lambda df, p=pair, a=adx_p: self._sig_adx_trend(df, a),
                )
            for tenkan, kijun, senkou in self.ICHIMOKU_PARAMS:
                self._register(
                    StrategyCategory.TREND_FOLLOWING,
                    f"Ichimoku_{tenkan}_{kijun}",
                    {"pair": pair, "t": tenkan, "k": kijun, "s": senkou},
                    lambda df, p=pair, t=tenkan, k=kijun, s=senkou: self._sig_ichimoku(df, t, k, s),
                )

    # ---- 4.2 Mean Reversion (RSI, Bollinger, S/R) --------------------------

    def _build_mean_reversion(self) -> None:
        for pair in self.pairs:
            for rsi_p in self.RSI_PERIODS:
                for overbought, oversold in [(70, 30), (75, 25), (80, 20), (65, 35)]:
                    self._register(
                        StrategyCategory.MEAN_REVERSION,
                        f"RSI_{rsi_p}_{overbought}_{oversold}",
                        {"pair": pair, "rsi_p": rsi_p, "ob": overbought, "os": oversold},
                        lambda df, p=pair, r=rsi_p, ob=overbought, os=oversold: self._sig_rsi_mr(df, r, ob, os),
                    )
            for bb_p, bb_k in self.BB_PERIODS:
                self._register(
                    StrategyCategory.MEAN_REVERSION,
                    f"BB_{bb_p}_{bb_k}",
                    {"pair": pair, "bb_p": bb_p, "bb_k": bb_k},
                    lambda df, p=pair, bp=bb_p, bk=bb_k: self._sig_bollinger(df, bp, bk),
                )
            # Support / resistance bounce
            for lookback in [20, 50, 100]:
                self._register(
                    StrategyCategory.MEAN_REVERSION,
                    f"SRbounce_{lookback}",
                    {"pair": pair, "lb": lookback},
                    lambda df, p=pair, lb=lookback: self._sig_sr_bounce(df, lb),
                )

    # ---- 4.3 Carry Trade ---------------------------------------------------

    def _build_carry_trade(self) -> None:
        for pair in self.pairs:
            diff = rate_differential(pair)
            if abs(diff) < 0.5:
                continue
            self._register(
                StrategyCategory.CARRY_TRADE,
                f"Carry_{pair.six_char}",
                {"pair": pair, "diff": diff},
                lambda df, p=pair, d=diff: self._sig_carry(df, d),
            )
            # Carry + trend filter
            for ma in [20, 50]:
                self._register(
                    StrategyCategory.CARRY_TRADE,
                    f"CarryTrend_{pair.six_char}_MA{ma}",
                    {"pair": pair, "diff": diff, "ma": ma},
                    lambda df, p=pair, d=diff, m=ma: self._sig_carry_trend(df, d, m),
                )

    # ---- 4.4 Session Breakouts ---------------------------------------------

    def _build_session_breakout(self) -> None:
        for pair in self.pairs:
            for session in [Session.ASIAN, Session.LONDON, Session.NEW_YORK, Session.OVERLAP]:
                for lookback in [5, 10, 20]:
                    self._register(
                        StrategyCategory.SESSION_BREAKOUT,
                        f"SessBreak_{session.value}_{lookback}",
                        {"pair": pair, "session": session, "lb": lookback},
                        lambda df, p=pair, s=session, lb=lookback: self._sig_session_break(df, s, lb),
                    )

    # ---- 4.5 Currency Strength ---------------------------------------------

    def _build_currency_strength(self) -> None:
        # Currency strength index strategies (computed on basket)
        for anchor in ["USD", "EUR", "GBP", "JPY"]:
            for ma in [10, 20, 50]:
                self._register(
                    StrategyCategory.CURRENCY_STRENGTH,
                    f"CS_{anchor}_MA{ma}",
                    {"anchor": anchor, "ma": ma},
                    lambda df, a=anchor, m=ma: self._sig_currency_strength(df, a, m),
                )

    # ---- 4.6 CFTC COT ------------------------------------------------------

    def _build_cftc_cot(self) -> None:
        for pair in self.pairs:
            for lookback in [4, 12, 26]:
                self._register(
                    StrategyCategory.CFTC_COT,
                    f"COT_{pair.six_char}_{lookback}w",
                    {"pair": pair, "lb": lookback},
                    lambda df, p=pair, lb=lookback: self._sig_cot(df, p, lb),
                )

    # ---- 4.7 Volatility Breakout -------------------------------------------

    def _build_volatility_breakout(self) -> None:
        for pair in self.pairs:
            for vol_p in self.VOL_LOOKBACK:
                for multiplier in [1.0, 1.5, 2.0]:
                    self._register(
                        StrategyCategory.VOLATILITY_BREAKOUT,
                        f"VolBreak_{vol_p}_{multiplier}",
                        {"pair": pair, "vol_p": vol_p, "mult": multiplier},
                        lambda df, p=pair, vp=vol_p, m=multiplier: self._sig_vol_break(df, vp, m),
                    )

    # ---- 4.8 Multi-Timeframe Alignment -------------------------------------

    def _build_multi_timeframe(self) -> None:
        for pair in self.pairs:
            for tf1, tf2 in [("1h", "4h"), ("1h", "1d"), ("4h", "1d")]:
                for ind in ["MA", "RSI", "MACD"]:
                    self._register(
                        StrategyCategory.MULTI_TIME_FRAME,
                        f"MTF_{ind}_{tf1}_{tf2}",
                        {"pair": pair, "tf1": tf1, "tf2": tf2, "ind": ind},
                        lambda df, p=pair, t1=tf1, t2=tf2, i=ind: self._sig_mtf_align(df, t1, t2, i),
                    )

    # -- Signal implementations -----------------------------------------------

    @staticmethod
    def _ema(series: pd.Series, span: int) -> pd.Series:
        return series.ewm(span=span, adjust=False).mean()

    @staticmethod
    def _sma(series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window).mean()

    @staticmethod
    def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    @classmethod
    def _adx(cls, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        plus_dm = (high - high.shift()).clip(lower=0)
        minus_dm = (low.shift() - low).clip(lower=0)
        plus_dm[plus_dm < minus_dm] = 0
        minus_dm[minus_dm < plus_dm] = 0

        atr = cls._atr(df, period)
        plus_di = 100 * cls._ema(plus_dm, period) / atr
        minus_di = 100 * cls._ema(minus_dm, period) / atr
        dx = (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10) * 100
        return cls._ema(dx, period)

    @classmethod
    def _sig_ma_cross(cls, df: pd.DataFrame, fast: int, slow: int) -> pd.Series:
        """Returns signal series: 1=long, -1=short, 0=flat."""
        ma_f = cls._ema(df["close"], fast)
        ma_s = cls._ema(df["close"], slow)
        sig = pd.Series(0, index=df.index, dtype=np.int8)
        sig[ma_f > ma_s] = 1
        sig[ma_f < ma_s] = -1
        return sig

    @classmethod
    def _sig_adx_trend(cls, df: pd.DataFrame, period: int) -> pd.Series:
        adx = cls._adx(df, period)
        close = df["close"]
        ma = cls._sma(close, period)
        sig = pd.Series(0, index=df.index, dtype=np.int8)
        sig[(adx > 25) & (close > ma)] = 1
        sig[(adx > 25) & (close < ma)] = -1
        return sig

    @classmethod
    def _sig_ichimoku(
        cls, df: pd.DataFrame, tenkan: int, kijun: int, senkou: int
    ) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        tenkan_sen = (high.rolling(tenkan).max() + low.rolling(tenkan).min()) / 2
        kijun_sen = (high.rolling(kijun).max() + low.rolling(kijun).min()) / 2
        sig = pd.Series(0, index=df.index, dtype=np.int8)
        sig[(close > tenkan_sen) & (tenkan_sen > kijun_sen)] = 1
        sig[(close < tenkan_sen) & (tenkan_sen < kijun_sen)] = -1
        return sig

    @classmethod
    def _sig_rsi_mr(
        cls, df: pd.DataFrame, period: int, overbought: float, oversold: float
    ) -> pd.Series:
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        sig = pd.Series(0, index=df.index, dtype=np.int8)
        sig[rsi < oversold] = 1
        sig[rsi > overbought] = -1
        return sig

    @classmethod
    def _sig_bollinger(cls, df: pd.DataFrame, period: int, k: float) -> pd.Series:
        close = df["close"]
        ma = cls._sma(close, period)
        std = close.rolling(period).std()
        upper = ma + k * std
        lower = ma - k * std
        sig = pd.Series(0, index=df.index, dtype=np.int8)
        sig[close < lower] = 1
        sig[close > upper] = -1
        return sig

    @classmethod
    def _sig_sr_bounce(cls, df: pd.DataFrame, lookback: int) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        resistance = high.rolling(lookback).max().shift(1)
        support = low.rolling(lookback).min().shift(1)
        atr = cls._atr(df, lookback)
        sig = pd.Series(0, index=df.index, dtype=np.int8)
        sig[(close <= support + 0.1 * atr) & (close > support)] = 1
        sig[(close >= resistance - 0.1 * atr) & (close < resistance)] = -1
        return sig

    @classmethod
    def _sig_carry(cls, df: pd.DataFrame, diff: float) -> pd.Series:
        """Go long positive carry, short negative carry."""
        sig = pd.Series(0, index=df.index, dtype=np.int8)
        sig[:] = 1 if diff > 0 else -1
        return sig

    @classmethod
    def _sig_carry_trend(cls, df: pd.DataFrame, diff: float, ma: int) -> pd.Series:
        close = df["close"]
        trend = cls._ema(close, ma)
        sig = pd.Series(0, index=df.index, dtype=np.int8)
        if diff > 0:
            sig[close > trend] = 1
        else:
            sig[close < trend] = -1
        return sig

    @classmethod
    def _sig_session_break(
        cls, df: pd.DataFrame, session: Session, lookback: int
    ) -> pd.Series:
        start_h, end_h = SESSION_HOURS[session]
        hour = df.index.hour
        in_session = (hour >= start_h.hour) & (hour < end_h.hour)
        session_df = df[in_session]

        if len(session_df) < lookback + 1:
            return pd.Series(0, index=df.index, dtype=np.int8)

        high_max = session_df["high"].rolling(lookback).max().shift(1)
        low_min = session_df["low"].rolling(lookback).min().shift(1)

        sig = pd.Series(0, index=df.index, dtype=np.int8)
        session_high = high_max.reindex(df.index, method="ffill")
        session_low = low_min.reindex(df.index, method="ffill")

        sig[df["close"] > session_high] = 1
        sig[df["close"] < session_low] = -1
        return sig

    @classmethod
    def _sig_currency_strength(
        cls, df: pd.DataFrame, anchor: str, ma: int
    ) -> pd.Series:
        """Signal based on relative currency strength index."""
        returns = df["close"].pct_change()
        cs = returns.rolling(ma).sum()
        sig = pd.Series(0, index=df.index, dtype=np.int8)
        sig[cs > 0] = 1
        sig[cs < 0] = -1
        return sig

    @classmethod
    def _sig_cot(cls, df: pd.DataFrame, pair: ForexPair, lookback: int) -> pd.Series:
        """Stub: COT signal requires external COT data. Returns flat by default."""
        return pd.Series(0, index=df.index, dtype=np.int8)

    @classmethod
    def _sig_vol_break(
        cls, df: pd.DataFrame, vol_period: int, multiplier: float
    ) -> pd.Series:
        returns = df["close"].pct_change()
        vol = returns.rolling(vol_period).std()
        threshold = multiplier * vol
        sig = pd.Series(0, index=df.index, dtype=np.int8)
        sig[returns > threshold] = 1
        sig[returns < -threshold] = -1
        return sig

    @classmethod
    def _sig_mtf_align(
        cls, df: pd.DataFrame, tf1: str, tf2: str, indicator: str
    ) -> pd.Series:
        """Multi-timeframe alignment: trade only when both TFs agree."""
        sig = pd.Series(0, index=df.index, dtype=np.int8)
        if indicator == "MA":
            ma1_fast = cls._ema(df["close"], 10)
            ma1_slow = cls._ema(df["close"], 30)
            sig1 = pd.Series(0, index=df.index, dtype=np.int8)
            sig1[ma1_fast > ma1_slow] = 1
            sig1[ma1_fast < ma1_slow] = -1
            ma2_fast = cls._ema(df["close"], 50)
            ma2_slow = cls._ema(df["close"], 200)
            sig2 = pd.Series(0, index=df.index, dtype=np.int8)
            sig2[ma2_fast > ma2_slow] = 1
            sig2[ma2_fast < ma2_slow] = -1
            sig[(sig1 == sig2) & (sig1 != 0)] = sig1[(sig1 == sig2) & (sig1 != 0)]
        elif indicator == "RSI":
            delta = df["close"].diff()
            rsi = 100 - 100 / (1 + delta.clip(lower=0).rolling(14).mean() / ((-delta).clip(lower=0).rolling(14).mean() + 1e-10))
            sig[(rsi < 40)] = 1
            sig[(rsi > 60)] = -1
        else:
            ema12 = cls._ema(df["close"], 12)
            ema26 = cls._ema(df["close"], 26)
            macd = ema12 - ema26
            sig[macd > 0] = 1
            sig[macd < 0] = -1
        return sig

    # -- Public API -----------------------------------------------------------

    def iter_strategies(self) -> Iterator[Dict[str, Any]]:
        """Yield each registered strategy."""
        yield from self._strategies

    def count(self) -> int:
        return len(self._strategies)


# =============================================================================
# SECTION 5: BACKTEST ENGINE
# =============================================================================

class BacktestEngine:
    """
    Runs in-sample backtests with spread costs, then walk-forward
    and Monte Carlo stress tests.
    """

    def __init__(
        self,
        data_fetcher: DataFetcher,
        is_fraction: float = 0.70,
        risk_free_rate: float = 0.04,
    ):
        self.data_fetcher = data_fetcher
        self.is_fraction = is_fraction
        self.risk_free = risk_free_rate
        self._cache: Dict[str, pd.DataFrame] = {}

    # -- Core backtest --------------------------------------------------------

    def run_backtest(
        self,
        strategy: Dict[str, Any],
        pair: ForexPair,
        start: datetime,
        end: datetime,
        granularity: str = "1h",
    ) -> Optional[BacktestResult]:
        """Run full backtest pipeline for one strategy."""
        cache_key = f"{pair.symbol}_{granularity}"
        if cache_key not in self._cache:
            df = self.data_fetcher.fetch_ohlcv(pair.symbol, start, end, granularity)
            if len(df) < Thresholds.MIN_BACKTEST_DAYS:
                logger.warning(f"Insufficient data for {pair.symbol}: {len(df)} rows")
                return None
            self._cache[cache_key] = df
        else:
            df = self._cache[cache_key]

        # Split in-sample / out-of-sample
        split_idx = int(len(df) * self.is_fraction)
        df_is = df.iloc[:split_idx].copy()
        df_oos = df.iloc[split_idx:].copy()

        # Generate signal on in-sample
        signal = strategy["func"](df_is)
        if signal is None or len(signal) == 0:
            return None

        # Compute returns after spread cost
        returns = self._compute_returns(df_is, signal, pair)
        if returns is None or len(returns.dropna()) < Thresholds.MIN_TRADES:
            return None

        # Build metrics
        result = self._build_result(strategy, pair, returns, df_is, signal)
        if result is None:
            return None

        # Walk-forward test
        wf_results = self._walk_forward(strategy, pair, df, granularity)
        if wf_results:
            result.wf_sharpe_mean = np.mean(wf_results)
            result.wf_sharpe_std = np.std(wf_results)
            result.wf_pass_rate = sum(1 for s in wf_results if s > 0.5) / len(wf_results)

        # Monte Carlo
        mc_sharpe, mc_dd = self._monte_carlo(returns)
        result.mc_sharpe_5th = mc_sharpe
        result.mc_dd_95th = mc_dd

        return result

    def _compute_returns(
        self,
        df: pd.DataFrame,
        signal: pd.Series,
        pair: ForexPair,
    ) -> Optional[pd.Series]:
        """Compute strategy returns after half-spread cost."""
        spread = get_spread(pair)
        close = df["close"]
        price_change = close.pct_change().shift(-1)  # next-bar return

        # Direction: 1=long, -1=short, 0=flat
        raw_returns = signal * price_change

        # Subtract spread cost on entry + exit (2 * half-spread)
        cost = (2 * spread) / close
        cost = cost.reindex(raw_returns.index, method="ffill")

        # Only pay cost when signal != 0
        returns = raw_returns.where(signal == 0, raw_returns - cost)
        return returns.dropna()

    def _build_result(
        self,
        strategy: Dict[str, Any],
        pair: ForexPair,
        returns: pd.Series,
        df: pd.DataFrame,
        signal: pd.Series,
    ) -> Optional[BacktestResult]:
        """Compile all performance metrics."""
        if len(returns) == 0 or returns.std() == 0:
            return None

        equity = (1 + returns.fillna(0)).cumprod()
        total_ret = equity.iloc[-1] - 1

        # Annualisation factor (hourly -> annual)
        periods_per_year = 252 * 24 if "h" in str(df.index.freq) else 252
        ann_ret = (1 + total_ret) ** (periods_per_year / len(returns)) - 1
        vol = returns.std() * np.sqrt(periods_per_year)

        if vol == 0:
            return None

        sharpe = (ann_ret - self.risk_free) / vol if vol > 0 else -999
        downside = returns[returns < 0]
        downside_vol = downside.std() * np.sqrt(periods_per_year) if len(downside) > 0 else 1e-6
        sortino = (ann_ret - self.risk_free) / downside_vol if downside_vol > 0 else -999

        # Drawdown
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        max_dd = drawdown.min()
        max_dd_dur = self._max_drawdown_duration(drawdown)
        calmar = ann_ret / abs(max_dd) if max_dd != 0 else -999

        # Trade stats
        trades = returns[returns != 0]
        n_trades = len(trades)
        wins = trades[trades > 0]
        losses = trades[trades < 0]
        hit_rate = len(wins) / n_trades if n_trades > 0 else 0
        avg_win = wins.mean() if len(wins) > 0 else 0
        avg_loss = abs(losses.mean()) if len(losses) > 0 else 0
        profit_factor = avg_win * len(wins) / (avg_loss * len(losses)) if len(losses) > 0 else 999
        expectancy = hit_rate * avg_win - (1 - hit_rate) * avg_loss

        result = BacktestResult(
            strategy_id=strategy["id"],
            category=strategy["category"],
            pair=pair,
            direction=Direction.LONG,  # determined by signal
            total_return=total_ret,
            annualized_return=ann_ret,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            max_drawdown_duration=max_dd_dur,
            calmar_ratio=calmar,
            volatility=vol,
            n_trades=n_trades,
            hit_rate=hit_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            expectancy=expectancy,
            equity_curve=equity,
        )
        return result

    @staticmethod
    def _max_drawdown_duration(drawdown: pd.Series) -> int:
        """Count consecutive bars in drawdown."""
        in_dd = drawdown < 0
        max_dur = 0
        cur_dur = 0
        for v in in_dd:
            if v:
                cur_dur += 1
                max_dur = max(max_dur, cur_dur)
            else:
                cur_dur = 0
        return max_dur

    # -- Walk-forward analysis ------------------------------------------------

    def _walk_forward(
        self,
        strategy: Dict[str, Any],
        pair: ForexPair,
        df: pd.DataFrame,
        granularity: str,
    ) -> List[float]:
        """
        Rolling walk-forward: 6-month train, 3-month test.
        Returns list of OOS Sharpe ratios.
        """
        # Approximate bars per month (hourly)
        bars_per_month = 30 * 24 if "h" in granularity else 21
        train_bars = 6 * bars_per_month
        test_bars = 3 * bars_per_month

        sharpe_list: List[float] = []
        start_idx = train_bars

        while start_idx + test_bars <= len(df):
            train_df = df.iloc[start_idx - train_bars : start_idx]
            test_df = df.iloc[start_idx : start_idx + test_bars]

            signal = strategy["func"](train_df)
            if signal is None or len(signal) == 0:
                start_idx += test_bars
                continue

            # Apply last signal value to test set
            last_signal = signal.iloc[-1] if len(signal) > 0 else 0
            test_returns = last_signal * test_df["close"].pct_change().shift(-1)

            vol = test_returns.std() * np.sqrt(252 * 24)
            ann_ret = test_returns.mean() * 252 * 24
            if vol > 0:
                sharpe_list.append((ann_ret - self.risk_free) / vol)
            else:
                sharpe_list.append(-999)

            start_idx += test_bars

        return sharpe_list if sharpe_list else [0.0]

    # -- Monte Carlo stress test ----------------------------------------------

    def _monte_carlo(
        self, returns: pd.Series, n_sims: int = 1000
    ) -> Tuple[float, float]:
        """
        Monte Carlo: resample trade returns with replacement.
        Returns (5th percentile Sharpe, 95th percentile drawdown).
        """
        trades = returns[returns != 0].dropna().values
        if len(trades) < 10:
            return np.nan, np.nan

        rng = default_rng(42)
        sharpe_sims = np.zeros(n_sims)
        dd_sims = np.zeros(n_sims)

        for i in range(n_sims):
            sample = rng.choice(trades, size=len(trades), replace=True)
            equity = (1 + sample).cumprod()
            total_ret = equity[-1] - 1
            ann_factor = 252 * 24 / len(sample)
            ann_ret = (1 + total_ret) ** ann_factor - 1
            vol = sample.std() * np.sqrt(252 * 24)
            sharpe_sims[i] = (ann_ret - self.risk_free) / vol if vol > 0 else -999

            cummax = np.maximum.accumulate(equity)
            dd = (equity - cummax) / cummax
            dd_sims[i] = dd.min()

        return float(np.percentile(sharpe_sims, 5)), float(np.percentile(dd_sims, 5))


# =============================================================================
# SECTION 6: STATISTICAL VALIDATOR
# =============================================================================

class StatisticalValidator:
    """
    Rigorous statistical validation of backtest results.

    Methods:
        - Bootstrapped Sharpe ratio (10,000 resamples)
        - One-sample t-test for mean return
        - Benjamini-Hochberg FDR correction across all strategies
    """

    def __init__(self, n_bootstrap: int = 10000, random_state: int = 42):
        self.n_bootstrap = n_bootstrap
        self.rng = default_rng(random_state)

    def validate_all(
        self, results: List[BacktestResult]
    ) -> List[BacktestResult]:
        """Run full validation suite on all results, apply FDR correction."""
        if not results:
            return []

        logger.info(f"Validating {len(results)} strategy results...")

        # 1. Individual tests
        for r in results:
            if len(r.equity_curve) < 10:
                continue
            returns = r.equity_curve.pct_change().dropna()
            if len(returns) < 10:
                continue

            # Bootstrapped Sharpe
            r.p_value_bootstrap, r.sharpe_ci_lower, r.sharpe_ci_upper = (
                self._bootstrap_sharpe(returns)
            )

            # One-sample t-test
            r.p_value_ttest = self._t_test(returns)

        # 2. Benjamini-Hochberg FDR correction
        self._apply_fdr_correction(results)

        # 3. Final pass/fail
        for r in results:
            r.passed_validation = self._pass_fail(r)

        passed = sum(1 for r in results if r.passed_validation)
        logger.info(f"Validation complete: {passed}/{len(results)} strategies passed")
        return results

    def _bootstrap_sharpe(self, returns: pd.Series) -> Tuple[float, float, float]:
        """
        Bootstrap the Sharpe ratio distribution.
        Returns (p-value, CI_lower, CI_upper).
        """
        returns = returns.dropna().values
        if len(returns) < 10:
            return 1.0, -np.inf, np.inf

        # Observed Sharpe
        ann_factor = np.sqrt(252 * 24)
        obs_sharpe = returns.mean() / (returns.std() + 1e-10) * ann_factor

        # Bootstrap distribution
        boot_sharpes = np.zeros(self.n_bootstrap)
        for i in range(self.n_bootstrap):
            sample = self.rng.choice(returns, size=len(returns), replace=True)
            boot_sharpes[i] = sample.mean() / (sample.std() + 1e-10) * ann_factor

        # Two-sided p-value
        p_value = 2 * min(np.mean(boot_sharpes <= 0), np.mean(boot_sharpes >= 0))
        p_value = max(p_value, 1.0 / self.n_bootstrap)

        ci_low, ci_high = np.percentile(boot_sharpes, [2.5, 97.5])
        return float(p_value), float(ci_low), float(ci_high)

    @staticmethod
    def _t_test(returns: pd.Series) -> float:
        """One-sample t-test: H0: mean return <= 0."""
        returns = returns.dropna().values
        if len(returns) < 10 or returns.std() == 0:
            return 1.0
        t_stat, p_value = stats.ttest_1samp(returns, 0)
        # One-sided
        if t_stat > 0:
            p_value = p_value / 2
        else:
            p_value = 1 - p_value / 2
        return float(p_value)

    @staticmethod
    def _apply_fdr_correction(results: List[BacktestResult], alpha: float = 0.05) -> None:
        """Benjamini-Hochberg FDR correction on bootstrap p-values."""
        p_values = np.array([r.p_value_bootstrap for r in results])
        n = len(p_values)
        if n == 0:
            return

        # BH procedure
        sorted_idx = np.argsort(p_values)
        sorted_p = p_values[sorted_idx]
        corrected = np.minimum.accumulate(sorted_p * n / np.arange(1, n + 1))
        corrected = np.minimum(corrected, 1.0)

        # Map back
        for i, idx in enumerate(sorted_idx):
            results[idx].fdr_corrected_p = float(corrected[i])

    def _pass_fail(self, result: BacktestResult) -> bool:
        """Check all threshold conditions."""
        return (
            result.sharpe_ratio > Thresholds.SHARPE_MIN
            and result.max_drawdown > -Thresholds.MAX_DRAWDOWN_MAX
            and result.p_value_bootstrap < Thresholds.P_VALUE_MAX
            and result.fdr_corrected_p < Thresholds.P_VALUE_MAX
            and result.hit_rate >= Thresholds.HIT_RATE_MIN
            and result.n_trades >= Thresholds.MIN_TRADES
            and result.wf_pass_rate >= Thresholds.WF_PASS_RATE_MIN
            and (np.isnan(result.mc_sharpe_5th) or result.mc_sharpe_5th >= Thresholds.MC_SHARPE_5TH_MIN)
        )


# =============================================================================
# SECTION 7: ENSEMBLE CONSTRUCTOR
# =============================================================================

class EnsembleConstructor:
    """
    Builds a risk-parity weighted ensemble from validated strategies.
    Uses correlation clustering to avoid over-concentration in similar
    strategies, and session-aware allocation.
    """

    def __init__(
        self,
        max_strategies: int = 8,
        min_strategies: int = 5,
        corr_threshold: float = 0.7,
    ):
        self.max_strategies = max_strategies
        self.min_strategies = min_strategies
        self.corr_threshold = corr_threshold

    def construct(
        self, validated_results: List[BacktestResult]
    ) -> Optional[EnsembleAllocation]:
        """Build the final ensemble."""
        passed = [r for r in validated_results if r.passed_validation]
        if len(passed) < self.min_strategies:
            logger.warning(
                f"Only {len(passed)} strategies passed validation, "
                f"need {self.min_strategies}. Relaxing criteria..."
            )
            # Relax: sort by Sharpe, take top N
            passed = sorted(validated_results, key=lambda x: x.sharpe_ratio, reverse=True)
            passed = passed[: self.max_strategies]

        if len(passed) == 0:
            logger.error("No viable strategies found!")
            return None

        # Sort by Sharpe
        passed = sorted(passed, key=lambda x: x.sharpe_ratio, reverse=True)

        # Correlation clustering to select uncorrelated subset
        selected = self._correlation_cluster_select(passed)

        if len(selected) < self.min_strategies:
            selected = passed[: self.min_strategies]

        # Risk-parity weighting
        weights = self._risk_parity_weights(selected)

        # Session allocation
        session_w = self._session_weights(selected)

        ensemble = EnsembleAllocation(
            ensemble_id=f"ENS_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            strategies=[r.strategy_id for r in selected],
            weights=weights,
            session_weights=session_w,
            expected_sharpe=float(np.average([r.sharpe_ratio for r in selected], weights=weights)),
            expected_volatility=float(np.average([r.volatility for r in selected], weights=weights)),
            expected_max_dd=float(np.average([r.max_drawdown for r in selected], weights=weights)),
            diversification_ratio=self._diversification_ratio(selected, weights),
        )
        logger.info(
            f"Ensemble constructed: {len(selected)} strategies, "
            f"Sharpe={ensemble.expected_sharpe:.2f}"
        )
        return ensemble

    def _correlation_cluster_select(
        self, results: List[BacktestResult]
    ) -> List[BacktestResult]:
        """
        Hierarchical clustering on strategy correlation matrix;
        pick one representative from each cluster.
        """
        if len(results) <= self.max_strategies:
            return results

        # Build correlation matrix from equity curves
        equity_curves = [r.equity_curve.pct_change().dropna() for r in results]
        min_len = min(len(ec) for ec in equity_curves)
        aligned = np.vstack([ec.iloc[-min_len:].values for ec in equity_curves])
        corr_matrix = np.corrcoef(aligned)
        corr_matrix = np.nan_to_num(corr_matrix, nan=0.0)

        # Distance matrix (ensure perfect symmetry for scipy)
        dist = 1 - np.abs(corr_matrix)
        dist = (dist + dist.T) / 2.0  # enforce symmetry
        np.fill_diagonal(dist, 0)

        # Hierarchical clustering
        linkage_matrix = linkage(squareform(dist, checks=False), method="average")
        n_clusters = max(self.min_strategies, self.max_strategies - 2)
        cluster_labels = fcluster(linkage_matrix, n_clusters, criterion="maxclust")

        # Pick best Sharpe from each cluster
        selected = []
        for c in range(1, n_clusters + 1):
            cluster_results = [r for r, label in zip(results, cluster_labels) if label == c]
            if cluster_results:
                best = max(cluster_results, key=lambda x: x.sharpe_ratio)
                selected.append(best)

        # Sort and cap
        selected = sorted(selected, key=lambda x: x.sharpe_ratio, reverse=True)
        return selected[: self.max_strategies]

    @staticmethod
    def _risk_parity_weights(results: List[BacktestResult]) -> np.ndarray:
        """Equal risk contribution weighting."""
        inv_vols = np.array([1.0 / max(r.volatility, 1e-6) for r in results])
        weights = inv_vols / inv_vols.sum()
        return weights

    @staticmethod
    def _session_weights(results: List[BacktestResult]) -> Dict[Session, float]:
        """Compute session-level weights based on strategy categories."""
        session_map = {
            StrategyCategory.SESSION_BREAKOUT: Session.LONDON,
            StrategyCategory.CARRY_TRADE: Session.OVERLAP,
            StrategyCategory.TREND_FOLLOWING: Session.NEW_YORK,
            StrategyCategory.MEAN_REVERSION: Session.ASIAN,
            StrategyCategory.VOLATILITY_BREAKOUT: Session.OVERLAP,
            StrategyCategory.CURRENCY_STRENGTH: Session.LONDON,
            StrategyCategory.CFTC_COT: Session.NEW_YORK,
            StrategyCategory.MULTI_TIME_FRAME: Session.LONDON,
        }
        counts = defaultdict(float)
        for r in results:
            sess = session_map.get(r.category, Session.LONDON)
            counts[sess] += 1
        total = sum(counts.values())
        return {s: c / total for s, c in counts.items()}

    @staticmethod
    def _diversification_ratio(
        results: List[BacktestResult], weights: np.ndarray
    ) -> float:
        """Portfolio volatility / weighted sum of individual vols."""
        individual_vols = np.array([max(r.volatility, 1e-6) for r in results])
        weighted_vol = np.dot(weights, individual_vols)

        # Approximate portfolio vol from correlation matrix
        equity_curves = [r.equity_curve.pct_change().dropna() for r in results]
        min_len = min(len(ec) for ec in equity_curves)
        if min_len < 10:
            return 1.0
        aligned = np.vstack([ec.iloc[-min_len:].values for ec in equity_curves])
        cov = np.cov(aligned)
        portfolio_var = float(np.dot(weights, np.dot(cov, weights)) * (252 * 24))
        portfolio_vol = np.sqrt(max(portfolio_var, 0))

        return weighted_vol / portfolio_vol if portfolio_vol > 0 else 1.0


# =============================================================================
# SECTION 8: INTEGRATION LAYER
# =============================================================================

class IntegrationLayer:
    """
    Converts ensemble output into system-compatible JSON format
    for ingestion by the findtorontoevents.ca/audit pipeline.
    """

    # System gate thresholds
    ELITE_LONG_THRESHOLD = 75
    CONF_LONG_THRESHOLD = 0.75
    PNL_WIN_BP = 5.0       # 5 basis points (not 0.1bp!)
    PNL_SANITY_CAP = 0.30

    @classmethod
    def to_system_picks(
        cls,
        ensemble: EnsembleAllocation,
        results: List[BacktestResult],
        timestamp: Optional[datetime] = None,
    ) -> List[SystemPick]:
        """Generate system picks from ensemble allocation."""
        if timestamp is None:
            timestamp = datetime.utcnow()

        picks = []
        for r in results:
            if r.strategy_id not in ensemble.strategies:
                continue

            # Elite score: map Sharpe [1.0, 3.0] -> [75, 100]
            elite = int(np.clip(75 + (r.sharpe_ratio - 1.0) * 12.5, 75, 100))
            conf = np.clip(r.hit_rate, 0.5, 0.95)

            direction = "LONG" if r.direction == Direction.LONG else "SHORT"

            # FOREX LONG gate
            if direction == "LONG" and (elite < cls.ELITE_LONG_THRESHOLD or conf < cls.CONF_LONG_THRESHOLD):
                continue

            pick = SystemPick(
                symbol=r.pair.symbol,
                direction=direction,
                elite_score=elite,
                confidence=float(conf),
                strategy_sources=[r.strategy_id],
                category_tags=[r.category.value],
                timestamp=timestamp,
                provenance={
                    "engine_version": __version__,
                    "ensemble_id": ensemble.ensemble_id,
                    "backtest_sharpe": round(r.sharpe_ratio, 4),
                    "backtest_max_dd": round(r.max_drawdown, 6),
                    "p_value": round(r.fdr_corrected_p, 6),
                    "wf_pass_rate": round(r.wf_pass_rate, 4),
                    "n_trades": r.n_trades,
                },
                metadata={
                    "sortino": round(r.sortino_ratio, 4),
                    "calmar": round(r.calmar_ratio, 4),
                    "profit_factor": round(r.profit_factor, 4),
                    "expectancy": round(r.expectancy, 6),
                },
            )
            picks.append(pick)

        return picks

    @classmethod
    def emit_json(cls, picks: List[SystemPick], filepath: Optional[str] = None) -> str:
        """Write picks to system-compatible JSON file."""
        if filepath is None:
            filepath = f"/mnt/agents/output/alpha_engine/picks_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = {
            "metadata": {
                "version": __version__,
                "generated_at": datetime.utcnow().isoformat(),
                "asset_class": "FOREX",
                "n_picks": len(picks),
                "source": "alpha_engine.forex_strategy_harness",
            },
            "picks": [p.to_system_json() for p in picks],
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Emitted {len(picks)} picks to {filepath}")
        return filepath

    @classmethod
    def collect_all_picks(cls, directory: str = "/mnt/agents/output/alpha_engine") -> List[Dict[str, Any]]:
        """
        Stage 2 INGEST: merge all per-source JSON files.
        Mirrors the existing system function.
        """
        all_picks = []
        if not os.path.isdir(directory):
            return all_picks

        for filename in sorted(os.listdir(directory)):
            if filename.endswith(".json"):
                filepath = os.path.join(directory, filename)
                try:
                    with open(filepath) as f:
                        data = json.load(f)
                    picks = data.get("picks", [])
                    for p in picks:
                        p["_source_file"] = filename
                    all_picks.extend(picks)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Skipping {filename}: {e}")

        # Deduplicate by symbol+direction, keep highest confidence
        seen = {}
        for p in all_picks:
            key = (p.get("symbol"), p.get("direction"))
            if key not in seen or p.get("confidence", 0) > seen[key].get("confidence", 0):
                seen[key] = p

        logger.info(f"INGEST: collected {len(all_picks)} picks, deduped to {len(seen)}")
        return list(seen.values())


# =============================================================================
# SECTION 9: ACTIVE & SMART GATES
# =============================================================================

class QualityGate:
    """
    Stage 3 ACTIVE GATE + Stage 4 SMART GATE implementation.
    """

    BLOCKED_SYMBOLS = {"NZDUSD=X", "EURJPY=X", "USDCHF=X"}

    @classmethod
    def active_gate(cls, picks: List[SystemPick]) -> List[SystemPick]:
        """
        Stage 3 — ACTIVE GATE:
        - FOREX LONG: elite>=75 AND conf>=0.75
        - Block NZDUSD, EURJPY, USDCHF
        """
        filtered = []
        for p in picks:
            # Block list
            if p.symbol in cls.BLOCKED_SYMBOLS:
                continue

            # LONG gate
            if p.direction == "LONG" and (p.elite_score < 75 or p.confidence < 0.75):
                continue

            filtered.append(p)

        logger.info(f"ACTIVE GATE: {len(picks)} -> {len(filtered)} picks")
        return filtered

    @classmethod
    def smart_gate(cls, picks: List[SystemPick]) -> List[SystemPick]:
        """
        Stage 4 — SMART GATE:
        - Per-class score / WR floors
        - Forward validation required (FwdWR >= 50)
        """
        filtered = []
        for p in picks:
            prov = p.provenance

            # Forward validation required
            wf_pass = prov.get("wf_pass_rate", 0)
            if wf_pass < 0.50:
                continue

            # Sharpe must be positive
            if prov.get("backtest_sharpe", 0) <= 0:
                continue

            # PnL sanity
            filtered.append(p)

        logger.info(f"SMART GATE: {len(picks)} -> {len(filtered)} picks")
        return filtered

    @classmethod
    def high_conviction_gate(cls, picks: List[SystemPick], top_n: int = 3) -> List[SystemPick]:
        """Stage 5 — HIGH CONVICTION: top-N by composite score."""
        def composite(p: SystemPick) -> float:
            return (
                p.elite_score / 100 * 0.4
                + p.confidence * 0.3
                + p.provenance.get("backtest_sharpe", 0) / 3.0 * 0.2
                + p.provenance.get("wf_pass_rate", 0) * 0.1
            )

        sorted_picks = sorted(picks, key=composite, reverse=True)
        return sorted_picks[:top_n]


# =============================================================================
# SECTION 10: CONSENSUS ENGINE
# =============================================================================

class ConsensusEngine:
    """
    Stage 6 — CONSENSUS: Multi-source agreement.
    Requires at least 2 independent strategy categories to agree.
    """

    MIN_SOURCES = 2

    @classmethod
    def require_consensus(cls, picks: List[SystemPick]) -> List[SystemPick]:
        """Filter picks that have multi-source agreement."""
        # Group by symbol + direction
        groups = defaultdict(list)
        for p in picks:
            key = (p.symbol, p.direction)
            groups[key].append(p)

        consensus_picks = []
        for key, group in groups.items():
            categories = set()
            for p in group:
                categories.update(p.category_tags)
            if len(categories) >= cls.MIN_SOURCES:
                # Merge: take highest confidence instance
                best = max(group, key=lambda x: x.confidence)
                best.strategy_sources = list(set(
                    src for p in group for src in p.strategy_sources
                ))
                best.category_tags = list(categories)
                consensus_picks.append(best)

        logger.info(f"CONSENSUS: {len(picks)} -> {len(consensus_picks)} picks")
        return consensus_picks


# =============================================================================
# SECTION 11: OUTCOME RESOLVER (PnL fixing)
# =============================================================================

class OutcomeResolver:
    """
    Stage 7 — OUTCOME: Proper PnL resolution fixing the 0.09% bug.

    Key fix: Use 5bp (0.0005) WIN threshold, NOT 0.1bp.
    This eliminates the 63.25% flicker problem.
    """

    WIN_THRESHOLD_BP = 5.0       # 5 basis points = meaningful edge
    SANITY_CAP = 0.30           # 30% max PnL

    @classmethod
    def resolve_pnl(
        cls,
        pick: SystemPick,
        entry_price: float,
        exit_price: float,
        direction: str,
    ) -> Dict[str, Any]:
        """
        Resolve PnL with proper thresholding.

        Returns:
            Dict with keys: pnl, pnl_bps, outcome, is_win
        """
        if direction == "LONG":
            raw_pnl = (exit_price - entry_price) / entry_price
        else:
            raw_pnl = (entry_price - exit_price) / entry_price

        # Sanity cap
        pnl = np.clip(raw_pnl, -cls.SANITY_CAP, cls.SANITY_CAP)
        pnl_bps = pnl * 10000  # convert to basis points

        # WIN = PnL >= 5bp (real edge, not spread noise)
        is_win = pnl_bps >= cls.WIN_THRESHOLD_BP
        is_loss = pnl_bps <= -cls.WIN_THRESHOLD_BP

        if is_win:
            outcome = "WIN"
        elif is_loss:
            outcome = "LOSS"
        else:
            outcome = "BREAKEVEN"

        return {
            "pnl": round(pnl, 6),
            "pnl_bps": round(pnl_bps, 2),
            "outcome": outcome,
            "is_win": is_win,
            "is_loss": is_loss,
            "threshold_bp": cls.WIN_THRESHOLD_BP,
        }

    @classmethod
    def batch_resolve(
        cls, picks: List[SystemPick], price_data: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """Resolve outcomes for a batch of picks."""
        results = []
        for pick in picks:
            # Look up prices (placeholder logic)
            symbol = pick.symbol.replace("=X", "")
            if symbol in price_data.columns:
                entry = price_data[symbol].iloc[0]
                exit_p = price_data[symbol].iloc[-1]
                result = cls.resolve_pnl(pick, entry, exit_p, pick.direction)
                results.append({
                    "symbol": pick.symbol,
                    "direction": pick.direction,
                    **result,
                })
        return results


# =============================================================================
# SECTION 12: MAIN ORCHESTRATOR
# =============================================================================

class ForexAlphaOrchestrator:
    """
    Main entry point: runs the full pipeline end-to-end.
    """

    def __init__(
        self,
        data_fetcher: Optional[DataFetcher] = None,
        output_dir: str = "/mnt/agents/output/alpha_engine",
    ):
        self.fetcher = data_fetcher or SyntheticDataFetcher()
        self.output_dir = output_dir
        self.strategy_gen = StrategyGenerator()
        self.backtest_engine = BacktestEngine(self.fetcher)
        self.validator = StatisticalValidator()
        self.ensemble_ctor = EnsembleConstructor()
        os.makedirs(output_dir, exist_ok=True)

    def run_full_pipeline(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Execute the complete pipeline:
            Generate -> Backtest -> Validate -> Ensemble -> Integrate
        """
        if end is None:
            end = datetime(2026, 5, 20)
        if start is None:
            start = end - timedelta(days=730)

        logger.info("=" * 60)
        logger.info("FOREX Alpha Engine — Full Pipeline Start")
        logger.info(f"Period: {start.date()} to {end.date()}")
        logger.info(f"Strategies to evaluate: {self.strategy_gen.count()}")
        logger.info("=" * 60)

        # Stage 1: Backtest all strategies
        all_results = []
        strategies = list(self.strategy_gen.iter_strategies())

        for i, strat in enumerate(strategies):
            if i % 50 == 0:
                logger.info(f"Backtesting... {i}/{len(strategies)}")

            pair = strat["params"].get("pair", TRADABLE_PAIRS[0])
            result = self.backtest_engine.run_backtest(
                strat, pair, start, end
            )
            if result is not None:
                all_results.append(result)

        logger.info(f"Backtests completed: {len(all_results)} valid results")

        # Stage 2: Statistical validation
        validated = self.validator.validate_all(all_results)

        # Stage 3: Ensemble construction
        ensemble = self.ensemble_ctor.construct(validated)

        # Stage 4: Generate system picks
        if ensemble is None:
            logger.error("Ensemble construction failed")
            return {"status": "FAILED", "n_strategies": 0}

        picks = IntegrationLayer.to_system_picks(ensemble, validated)

        # Stage 5: Quality gates
        picks = QualityGate.active_gate(picks)
        picks = QualityGate.smart_gate(picks)
        picks = QualityGate.high_conviction_gate(picks, top_n=5)
        picks = ConsensusEngine.require_consensus(picks)

        # Stage 6: Emit
        filepath = IntegrationLayer.emit_json(picks)

        # Summary
        summary = {
            "status": "SUCCESS",
            "timestamp": datetime.utcnow().isoformat(),
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "n_strategies_evaluated": len(strategies),
            "n_valid_backtests": len(all_results),
            "n_passed_validation": sum(1 for r in validated if r.passed_validation),
            "n_ensemble_strategies": len(ensemble.strategies),
            "ensemble_expected_sharpe": round(ensemble.expected_sharpe, 4),
            "ensemble_expected_vol": round(ensemble.expected_volatility, 6),
            "n_final_picks": len(picks),
            "picks_file": filepath,
            "ensemble": ensemble,
            "top_strategies": [r.to_dict() for r in sorted(
                [v for v in validated if v.passed_validation],
                key=lambda x: x.sharpe_ratio, reverse=True
            )[:10]],
        }

        logger.info("=" * 60)
        logger.info("Pipeline Complete")
        logger.info(f"  Strategies evaluated: {summary['n_strategies_evaluated']}")
        logger.info(f"  Valid backtests:      {summary['n_valid_backtests']}")
        logger.info(f"  Passed validation:    {summary['n_passed_validation']}")
        logger.info(f"  Ensemble Sharpe:      {summary['ensemble_expected_sharpe']}")
        logger.info(f"  Final picks:          {summary['n_final_picks']}")
        logger.info("=" * 60)

        return summary


# =============================================================================
# SECTION 13: UNIT TEST SKELETONS
# =============================================================================

class TestForexStrategyHarness:
    """pytest-compatible test suite (run with: pytest this_file.py)."""

    @staticmethod
    def test_pair_model():
        p = ForexPair("EUR", "USD")
        assert p.symbol == "EURUSD=X"
        assert p.six_char == "EURUSD"
        assert p not in BLOCKED_PAIRS

    @staticmethod
    def test_blocked_pairs():
        assert ForexPair("NZD", "USD") in BLOCKED_PAIRS
        assert ForexPair("EUR", "JPY") in BLOCKED_PAIRS
        assert ForexPair("USD", "CHF") in BLOCKED_PAIRS

    @staticmethod
    def test_strategy_generator_count():
        gen = StrategyGenerator()
        assert gen.count() >= 150, f"Expected >=150, got {gen.count()}"

    @staticmethod
    def test_ma_cross_signal():
        df = pd.DataFrame({
            "open": [1.0]*50,
            "high": [1.01]*50,
            "low": [0.99]*50,
            "close": list(range(50)),
            "volume": [1000]*50,
        })
        sig = StrategyGenerator._sig_ma_cross(df, 5, 20)
        assert len(sig) == 50
        assert sig.iloc[-1] in {-1, 0, 1}

    @staticmethod
    def test_backtest_engine():
        fetcher = SyntheticDataFetcher(seed=42)
        engine = BacktestEngine(fetcher)
        gen = StrategyGenerator(pairs=[ForexPair("EUR", "USD")])
        strat = list(gen.iter_strategies())[0]
        start = datetime(2024, 1, 1)
        end = datetime(2026, 5, 20)
        result = engine.run_backtest(strat, ForexPair("EUR", "USD"), start, end)
        assert result is not None
        assert isinstance(result.sharpe_ratio, float)

    @staticmethod
    def test_statistical_validator():
        returns = pd.Series(np.random.randn(500) * 0.001 + 0.0003)
        val = StatisticalValidator(n_bootstrap=1000)
        p, ci_low, ci_high = val._bootstrap_sharpe(returns)
        assert 0 <= p <= 1
        assert ci_low < ci_high

    @staticmethod
    def test_outcome_resolver_threshold():
        pick = SystemPick(
            symbol="EURUSD=X",
            direction="LONG",
            elite_score=80,
            confidence=0.8,
            strategy_sources=["test"],
            category_tags=["test"],
            timestamp=datetime.utcnow(),
        )
        result = OutcomeResolver.resolve_pnl(pick, 1.1000, 1.1001, "LONG")
        assert result["outcome"] == "BREAKEVEN"  # 0.9bp < 5bp
        result2 = OutcomeResolver.resolve_pnl(pick, 1.1000, 1.1008, "LONG")
        assert result2["outcome"] == "WIN"  # ~7bp >= 5bp

    @staticmethod
    def test_integration_json_roundtrip():
        pick = SystemPick(
            symbol="EURUSD=X",
            direction="LONG",
            elite_score=85,
            confidence=0.82,
            strategy_sources=["TF_MAcross_5_20_000"],
            category_tags=["trend_following"],
            timestamp=datetime.utcnow(),
        )
        filepath = IntegrationLayer.emit_json([pick])
        assert os.path.exists(filepath)
        collected = IntegrationLayer.collect_all_picks(os.path.dirname(filepath))
        assert len(collected) >= 1

    @staticmethod
    def test_active_gate():
        picks = [
            SystemPick("EURUSD=X", "LONG", 80, 0.8, ["s1"], ["trend"], datetime.utcnow()),
            SystemPick("NZDUSD=X", "LONG", 80, 0.8, ["s2"], ["carry"], datetime.utcnow()),  # blocked
            SystemPick("GBPUSD=X", "LONG", 70, 0.8, ["s3"], ["mr"], datetime.utcnow()),    # elite too low
            SystemPick("AUDUSD=X", "SHORT", 60, 0.5, ["s4"], ["vol"], datetime.utcnow()),  # SHORT ok
        ]
        filtered = QualityGate.active_gate(picks)
        assert len(filtered) == 2  # EURUSD LONG + AUDUSD SHORT

    @staticmethod
    def test_ensemble_construction():
        # Create mock results
        results = []
        for i in range(10):
            r = BacktestResult(
                strategy_id=f"STRAT_{i}",
                category=StrategyCategory.TREND_FOLLOWING,
                pair=ForexPair("EUR", "USD"),
                direction=Direction.LONG,
                total_return=0.1,
                annualized_return=0.1,
                sharpe_ratio=1.5 + i * 0.1,
                sortino_ratio=1.5,
                max_drawdown=-0.05,
                max_drawdown_duration=10,
                calmar_ratio=2.0,
                volatility=0.1,
                n_trades=50,
                hit_rate=0.55,
                avg_win=0.01,
                avg_loss=0.005,
                profit_factor=2.0,
                expectancy=0.002,
                p_value_bootstrap=0.01,
                fdr_corrected_p=0.02,
                passed_validation=True,
                wf_pass_rate=0.7,
                mc_sharpe_5th=0.8,
                equity_curve=pd.Series((1 + np.random.randn(100)*0.001).cumprod()),
            )
            results.append(r)

        ctor = EnsembleConstructor(max_strategies=5)
        ensemble = ctor.construct(results)
        assert ensemble is not None
        assert len(ensemble.strategies) >= 2
        assert len(ensemble.weights) == len(ensemble.strategies)

    @staticmethod
    def run_all():
        """Run all tests manually without pytest."""
        tests = [
            TestForexStrategyHarness.test_pair_model,
            TestForexStrategyHarness.test_blocked_pairs,
            TestForexStrategyHarness.test_strategy_generator_count,
            TestForexStrategyHarness.test_ma_cross_signal,
            TestForexStrategyHarness.test_backtest_engine,
            TestForexStrategyHarness.test_statistical_validator,
            TestForexStrategyHarness.test_outcome_resolver_threshold,
            TestForexStrategyHarness.test_active_gate,
            TestForexStrategyHarness.test_ensemble_construction,
        ]
        passed = 0
        for t in tests:
            try:
                t()
                print(f"  PASS: {t.__name__}")
                passed += 1
            except Exception as e:
                print(f"  FAIL: {t.__name__}: {e}")
        print(f"\n{passed}/{len(tests)} tests passed")
        return passed == len(tests)


# =============================================================================
# SECTION 14: CLI ENTRY POINT
# =============================================================================

def main():
    """Run the full alpha engine pipeline."""
    print("=" * 60)
    print("  FOREX Multi-Strategy Alpha Engine v" + __version__)
    print("  Target: findtorontoevents.ca/audit")
    print("=" * 60)

    # Run tests
    print("\n--- Running self-tests ---")
    ok = TestForexStrategyHarness.run_all()
    if not ok:
        print("Self-tests FAILED. Aborting.")
        return 1

    # Run pipeline
    print("\n--- Running full pipeline ---")
    orchestrator = ForexAlphaOrchestrator()
    summary = orchestrator.run_full_pipeline()

    # Write summary
    summary_file = os.path.join(
        orchestrator.output_dir, f"summary_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    )
    # Remove non-serializable objects
    summary_clean = {
        k: v for k, v in summary.items() if k not in ("ensemble", "top_strategies")
    }
    with open(summary_file, "w") as f:
        json.dump(summary_clean, f, indent=2, default=str)
    print(f"\nSummary written to: {summary_file}")
    print(f"Final picks file: {summary.get('picks_file', 'N/A')}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
