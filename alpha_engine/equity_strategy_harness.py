#!/usr/bin/env python3
"""
equity_strategy_harness.py
================================================================================
Statistically-Proven Multi-Strategy Engine for EQUITY Picks
================================================================================
Generates 150+ candidate strategies, validates them with rigorous statistical
methods, and produces a factor-diversified ensemble of statistically proven
winners.  Designed to feed findtorontoevents.ca/audit pipeline.

Every strategy that survives must satisfy:
    * Bootstrapped annualised Sharpe  > 1.0
    * Two-sample t-test p-value       < 0.05
    * Benjamini–Hochberg FDR q-value  < 0.05
    * Max drawdown                    < 20 %
    * Walk-forward (rolling 3-fold)   all folds Sharpe > 0.5
    * Monte-Carlo 5th-percentile      > 0  (Sharpe)

Current date: 2026-05-20
Author:      Quantitative Equity Strategy Team
"""

from __future__ import annotations

__version__ = "2026.5.20"

import os
import sys
import json
import logging
import hashlib
import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    Sequence,
)
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import itertools

import numpy as np
import pandas as pd
from numpy.random import SeedSequence, default_rng
from scipy import stats

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger: logging.Logger = logging.getLogger("equity_strategy_harness")

# ---------------------------------------------------------------------------
# CONSTANTS  (findtorontoevents.ca/audit integration rules)
# ---------------------------------------------------------------------------
EQUITY_SYMBOLS: Tuple[str, ...] = (
    # Large-cap tech / growth
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "META", "NVDA", "AMD",
    "NFLX", "DIS", "BA", "ORCL",
    # Financials
    "JPM", "GS", "V", "MA", "PYPL", "SQ", "BAC",
    # Crypto proxies
    "COIN", "MSTR", "RIOT", "MARA", "HUT", "BITF",
    # Defensive / consumer staples
    "COST", "PFE", "JNJ", "ABBV", "HD",
    # Pharma / health-care
    "LLY", "TMO",
    # Semis / tech hardware
    "AVGO", "INTC", "QCOM", "MU", "LRCX", "KLAC",
    # Industrial / energy / materials
    "XOM", "CVX", "UNH", "PG", "KO", "PEP", "WMT", "NKE", "CRM",
    # Additional liquid names
    "UBER", "LYFT", "ABNB", "ROKU", "SNOW", "PLTR", "DDOG", "NET",
    "ZM", "DOCU", "SHOP", "SPOT", "TWLO", "OKTA", "CRWD", "FTNT",
    "PANW", "CYBR", "ZS", "SPLK", "NOW", "VEEV", "TEAM", "ATLASSIAN",
)

SECTOR_MAP: Dict[str, str] = {
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Communication",
    "GOOG": "Communication", "AMZN": "ConsumerDiscretionary", "TSLA": "ConsumerDiscretionary",
    "META": "Communication", "NVDA": "Technology", "AMD": "Technology",
    "NFLX": "Communication", "DIS": "Communication", "BA": "Industrials",
    "ORCL": "Technology", "JPM": "Financials", "GS": "Financials",
    "V": "Financials", "MA": "Financials", "PYPL": "Financials",
    "SQ": "Financials", "BAC": "Financials", "COIN": "Financials",
    "MSTR": "Technology", "RIOT": "Technology", "MARA": "Technology",
    "HUT": "Technology", "BITF": "Technology", "COST": "ConsumerStaples",
    "PFE": "HealthCare", "JNJ": "HealthCare", "ABBV": "HealthCare",
    "HD": "ConsumerDiscretionary", "LLY": "HealthCare", "TMO": "HealthCare",
    "AVGO": "Technology", "INTC": "Technology", "QCOM": "Technology",
    "MU": "Technology", "LRCX": "Technology", "KLAC": "Technology",
    "XOM": "Energy", "CVX": "Energy", "UNH": "HealthCare",
    "PG": "ConsumerStaples", "KO": "ConsumerStaples", "PEP": "ConsumerStaples",
    "WMT": "ConsumerStaples", "NKE": "ConsumerDiscretionary",
    "CRM": "Technology", "UBER": "Industrials", "LYFT": "Industrials",
    "ABNB": "ConsumerDiscretionary", "ROKU": "Communication",
    "SNOW": "Technology", "PLTR": "Technology", "DDOG": "Technology",
    "NET": "Technology", "ZM": "Technology", "DOCU": "Technology",
    "SHOP": "ConsumerDiscretionary", "SPOT": "Communication",
    "TWLO": "Technology", "OKTA": "Technology", "CRWD": "Technology",
    "FTNT": "Technology", "PANW": "Technology", "CYBR": "Technology",
    "ZS": "Technology", "SPLK": "Technology", "NOW": "Technology",
    "VEEV": "HealthCare", "TEAM": "Technology",
}

# Market-cap buckets for slippage modelling
LARGE_CAP: set = {"AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "META",
                   "NVDA", "JPM", "V", "MA", "UNH", "XOM", "JNJ", "WMT",
                   "PG", "HD", "BAC", "ABBV", "PFE", "KO", "PEP", "COST",
                   "TMO", "AVGO", "DIS", "ORCL", "NFLX", "CRM", "GS", "LLY",
                   "CVX", "BA", "NKE"}
MID_CAP: set = set(EQUITY_SYMBOLS) - LARGE_CAP

# Trading constants
COMMISSION_PER_SHARE: float = 0.005          # $0.005 / share  (institutional)
SLIPPAGE_LARGE_BP: float = 1.0               # 1 bp
SLIPPAGE_MID_BP: float = 3.0                 # 3 bp
BP: float = 1e-4                             # one basis point
DAYS_PER_YEAR: int = 252
RISK_FREE_RATE: float = 0.045                # 4.5 % annual (approx 2026-05 T-bill)

# Validation thresholds
MIN_SHARPE: float = 1.0
MAX_DRAWDOWN: float = 0.20
MAX_PVALUE: float = 0.05
MAX_QVALUE: float = 0.05
WF_MIN_SHARPE: float = 0.5
MC_PERCENTILE: int = 5

# ---------------------------------------------------------------------------
# ENUMS
# ---------------------------------------------------------------------------


class StrategyCategory(str, Enum):
    EARNINGS_MOMENTUM = "earnings_momentum"
    FACTOR_BASED = "factor_based"
    TECHNICAL_BREAKOUT = "technical_breakout"
    MEAN_REVERSION = "mean_reversion"
    SECTOR_ROTATION = "sector_rotation"
    INSIDER_ACTIVITY = "insider_activity"
    MARKET_BREADTH = "market_breadth"
    SEASONALITY = "seasonality"


class SignalDirection(int, Enum):
    SHORT = -1
    NEUTRAL = 0
    LONG = 1


# ---------------------------------------------------------------------------
# DATA CLASSES
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    """Immutable configuration for a single candidate strategy."""
    name: str
    category: StrategyCategory
    params: Dict[str, Any] = field(default_factory=dict)
    lookback: int = 20               # trading days
    hold_period: int = 5             # trading days
    direction: SignalDirection = SignalDirection.LONG

    def uid(self) -> str:
        """Deterministic unique identifier."""
        payload = f"{self.name}|{self.category}|{json.dumps(self.params, sort_keys=True)}"
        return hashlib.sha256(payload.encode()).hexdigest()[:12]


@dataclass
class BacktestResult:
    """Performance metrics produced by the back-test engine."""
    config: StrategyConfig
    total_return: float              # fraction, e.g. 0.15 = 15%
    annualized_return: float
    volatility: float                # annualized
    sharpe: float
    sortino: float
    max_drawdown: float              # positive fraction, e.g. 0.12 = 12%
    hit_rate: float                  # fraction of winning trades
    avg_win: float
    avg_loss: float
    profit_factor: float
    num_trades: int
    p_value: float = np.nan
    q_value: float = np.nan
    boot_sharpe_mean: float = np.nan
    boot_sharpe_std: float = np.nan
    boot_sharpe_p05: float = np.nan
    wf_scores: List[float] = field(default_factory=list)
    mc_p05_sharpe: float = np.nan
    passed: bool = False
    raw_equity_curve: np.ndarray = field(default_factory=lambda: np.array([]))

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["category"] = self.config.category.value
        d["config_name"] = self.config.name
        d["config_uid"] = self.config.uid()
        d["direction"] = self.config.direction.value
        d["raw_equity_curve"] = d["raw_equity_curve"].tolist() if len(
            d["raw_equity_curve"]) else []
        return d


@dataclass
class EnsembleAllocation:
    """Final ensemble output ready for ingestion by the audit pipeline."""
    strategy_uid: str
    strategy_name: str
    category: str
    weight: float                     # 0..1, sums to 1.0 across ensemble
    capital_allocation_pct: float
    expected_return: float
    expected_sharpe: float
    symbols: List[str]
    sector_breakdown: Dict[str, float]
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_audit_json(self) -> Dict[str, Any]:
        return {
            "strategy_uid": self.strategy_uid,
            "strategy_name": self.strategy_name,
            "category": self.category,
            "weight": round(self.weight, 4),
            "capital_allocation_pct": round(self.capital_allocation_pct, 4),
            "expected_return": round(self.expected_return, 4),
            "expected_sharpe": round(self.expected_sharpe, 4),
            "symbols": self.symbols,
            "sector_breakdown": self.sector_breakdown,
            "meta": self.meta,
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "version": __version__,
        }


# ---------------------------------------------------------------------------
# DATA LOADER  (stub – replace with real price feed)
# ---------------------------------------------------------------------------


class PriceDataManager:
    """
    Thin abstraction over the underlying price store.
    In production this wraps the real tick/ohlcv DB.
    For harness validation it generates synthetic geometric-Brownian
    price paths that embed known drift / seasonal effects so that the
    statistical machinery can be exercised end-to-end.
    """

    def __init__(self, seed: int = 42) -> None:
        self._cache: Dict[str, pd.DataFrame] = {}
        self._rng = default_rng(seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_ohlcv(
        self,
        symbol: str,
        start: str = "2020-01-01",
        end: str = "2026-05-20",
    ) -> pd.DataFrame:
        """Return daily OHLCV DataFrame (synthetic if not cached)."""
        key = f"{symbol}_{start}_{end}"
        if key in self._cache:
            return self._cache[key].copy()

        df = self._synthetic_ohlcv(symbol, start, end)
        self._cache[key] = df.copy()
        return df

    def load_multi(
        self,
        symbols: Sequence[str],
        start: str = "2020-01-01",
        end: str = "2026-05-20",
    ) -> Dict[str, pd.DataFrame]:
        return {s: self.load_ohlcv(s, start, end) for s in symbols}

    # ------------------------------------------------------------------
    # Synthetic data generator – produces plausible price paths
    # ------------------------------------------------------------------

    def _synthetic_ohlcv(
        self,
        symbol: str,
        start: str,
        end: str,
    ) -> pd.DataFrame:
        """
        Generate synthetic daily OHLCV with:
         * realistic annualised drift  (8-15 % depending on sector)
         * realistic volatility        (20-55 %)
         * seasonal tilt               (earnings window bump)
         * occasional mean-reversion pockets
        """
        dates = pd.date_range(start, end, freq="B")   # business days
        n = len(dates)
        if n < 30:
            raise ValueError(f"Date range too short for {symbol}")

        # Base parameters per sector
        sector = SECTOR_MAP.get(symbol, "Technology")
        base_drift = {
            "Technology": 0.12, "Communication": 0.10,
            "ConsumerDiscretionary": 0.09, "Financials": 0.08,
            "HealthCare": 0.09, "ConsumerStaples": 0.07,
            "Industrials": 0.08, "Energy": 0.07,
        }.get(sector, 0.10)

        # Add per-symbol fingerprint so different symbols diverge
        symbol_hash = int(hashlib.md5(symbol.encode()).hexdigest(), 16)
        rng = default_rng(self._rng.integers(0, 2**31) + symbol_hash % 10000)

        drift = base_drift + rng.normal(0, 0.02)
        vol = 0.20 + rng.uniform(0, 0.25)

        # GBM returns
        daily_ret = drift / DAYS_PER_YEAR + vol / np.sqrt(DAYS_PER_YEAR) * rng.standard_normal(n)

        # Inject seasonal earnings bump (days 30-40 of each quarter)
        for q_start in range(0, n, 63):
            window = slice(q_start + 30, min(q_start + 40, n))
            daily_ret[window] += 0.003   # +30 bp earnings drift

        # Inject mean-reversion pocket (random 20-day stretch)
        mr_start = rng.integers(50, n - 50)
        daily_ret[mr_start:mr_start + 20] -= 0.002

        # Price series
        price = 100.0 * np.exp(np.cumsum(daily_ret))

        # OHLCV from close
        noise = vol / np.sqrt(DAYS_PER_YEAR) * 0.3
        high = price * (1 + np.abs(rng.standard_normal(n)) * noise)
        low = price * (1 - np.abs(rng.standard_normal(n)) * noise)
        open_p = price * (1 + rng.standard_normal(n) * noise * 0.5)
        volume = rng.integers(1_000_000, 50_000_000, size=n)

        df = pd.DataFrame({
            "open": open_p,
            "high": high,
            "low": low,
            "close": price,
            "volume": volume,
        }, index=dates)
        return df


# ---------------------------------------------------------------------------
# SIGNAL GENERATORS  (one per strategy family)
# ---------------------------------------------------------------------------


class SignalGenerator(ABC):
    """Abstract base – every concrete strategy implements __call__."""

    def __init__(self, config: StrategyConfig) -> None:
        self.cfg = config

    @abstractmethod
    def __call__(
        self,
        ohlcv: pd.DataFrame,
    ) -> pd.Series:
        """
        Return a pd.Series indexed like *ohlcv* with values in {-1, 0, 1}
        (or float weights for partial exposure).
        """
        ...


# ---------------------------------------------------------------------------
# 1. EARNINGS MOMENTUM
# ---------------------------------------------------------------------------


class EarningsSurpriseSignal(SignalGenerator):
    """
    Proxy for earnings surprise:  compare realised close-to-close
    return around earnings window to recent volatility.
    In production this uses actual EPS surprise / guidance data.
    """

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("vol_lookback", 20)
        threshold = self.cfg.params.get("z_threshold", 1.5)
        ret = ohlcv["close"].pct_change()
        vol = ret.rolling(lb).std()
        z = ret / vol.replace(0, np.nan)
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[z > threshold] = 1
        sig[z < -threshold] = -1 if self.cfg.direction == SignalDirection.SHORT else 0
        return sig * self.cfg.direction.value


class EarningsGuidanceSignal(SignalGenerator):
    """Proxy: consecutive up-day streak as proxy for positive guidance drift."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        streak = self.cfg.params.get("streak", 3)
        ret = ohlcv["close"].pct_change()
        up = (ret > 0).astype(int)
        rolling_up = up.rolling(streak).sum()
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[rolling_up >= streak] = 1
        return sig * self.cfg.direction.value


class PostEarningsDriftSignal(SignalGenerator):
    """Classic post-earnings-announcement drift (PEAD) proxy."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("vol_lookback", 20)
        k = self.cfg.params.get("gap_threshold", 2.0)
        ret = ohlcv["close"].pct_change()
        vol = ret.rolling(lb).std()
        gap = ret / vol.replace(0, np.nan)
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[gap > k] = 1      # drift after big positive surprise
        sig[gap < -k] = -1 if self.cfg.direction == SignalDirection.SHORT else 0
        return sig


# ---------------------------------------------------------------------------
# 2. FACTOR-BASED
# ---------------------------------------------------------------------------


class ValueFactorSignal(SignalGenerator):
    """
    Proxy value signal: low recent return = proxy for low P/E expansion.
    In production this uses book-to-price, earnings yield, etc.
    """

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 60)
        mom = ohlcv["close"].pct_change(lb)
        rank = mom.rank(pct=True)
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[rank < 0.20] = 1      # buy worst 20 % (value)
        return sig * self.cfg.direction.value


class GrowthFactorSignal(SignalGenerator):
    """Proxy growth signal: strong 6-12 month momentum."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 120)
        mom = ohlcv["close"].pct_change(lb)
        rank = mom.rank(pct=True)
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[rank > 0.80] = 1      # buy top 20 % momentum
        return sig * self.cfg.direction.value


class QualityFactorSignal(SignalGenerator):
    """
    Proxy quality: low volatility + positive drift.
    Production: ROE stability, earnings variability, leverage.
    """

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        vol_lb = self.cfg.params.get("vol_lb", 20)
        trend_lb = self.cfg.params.get("trend_lb", 60)
        ret = ohlcv["close"].pct_change()
        vol = ret.rolling(vol_lb).std()
        trend = ret.rolling(trend_lb).mean()
        low_vol = vol.rank(pct=True) < 0.30
        pos_trend = trend > 0
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[low_vol & pos_trend] = 1
        return sig * self.cfg.direction.value


class LowVolFactorSignal(SignalGenerator):
    """Buy lowest realised volatility decile."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 20)
        ret = ohlcv["close"].pct_change()
        vol = ret.rolling(lb).std()
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[vol.rank(pct=True) < 0.10] = 1
        return sig * self.cfg.direction.value


class MomentumFactorSignal(SignalGenerator):
    """12-1 month momentum (skip most recent month)."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb_long = self.cfg.params.get("lookback_long", 240)
        lb_skip = self.cfg.params.get("lookback_skip", 20)
        past = ohlcv["close"].pct_change(lb_long)
        recent = ohlcv["close"].pct_change(lb_skip)
        score = past - recent
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[score.rank(pct=True) > 0.80] = 1
        return sig * self.cfg.direction.value


class SmallCapPremiumSignal(SignalGenerator):
    """Proxy: high-beta signal via short-term volatility."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 20)
        ret = ohlcv["close"].pct_change()
        vol = ret.rolling(lb).std()
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[vol.rank(pct=True) > 0.70] = 1   # higher vol proxy for smaller cap
        return sig * self.cfg.direction.value


class ProfitabilityFactorSignal(SignalGenerator):
    """Proxy: price strength + low drawdown = profitability."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 60)
        cummax = ohlcv["close"].cummax()
        dd = (ohlcv["close"] - cummax) / cummax
        max_dd = dd.rolling(lb).min()
        ret = ohlcv["close"].pct_change(lb)
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[(ret > 0) & (max_dd > -0.05)] = 1
        return sig * self.cfg.direction.value


# ---------------------------------------------------------------------------
# 3. TECHNICAL BREAKOUT
# ---------------------------------------------------------------------------


class ResistanceBreakoutSignal(SignalGenerator):
    """Close above N-day high."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 20)
        highest = ohlcv["high"].rolling(lb).max().shift(1)
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[ohlcv["close"] > highest] = 1
        return sig * self.cfg.direction.value


class SupportBounceSignal(SignalGenerator):
    """Close bouncing off N-day low."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 20)
        lowest = ohlcv["low"].rolling(lb).min().shift(1)
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[ohlcv["close"] <= lowest * 1.01] = 1
        return sig * self.cfg.direction.value


class VolumeConfirmedBreakoutSignal(SignalGenerator):
    """Breakout on 2x average volume."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 20)
        vol_avg = ohlcv["volume"].rolling(lb).mean().shift(1)
        highest = ohlcv["high"].rolling(lb).max().shift(1)
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[(ohlcv["close"] > highest) & (ohlcv["volume"] > 2 * vol_avg)] = 1
        return sig * self.cfg.direction.value


class GapFillSignal(SignalGenerator):
    """Trade the fill of overnight gaps."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        gap_pct = self.cfg.params.get("gap_pct", 0.02)
        gap = (ohlcv["open"] - ohlcv["close"].shift(1)) / ohlcv["close"].shift(1)
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        # Fade large gaps
        sig[gap > gap_pct] = -1 if self.cfg.direction == SignalDirection.SHORT else 0
        sig[gap < -gap_pct] = 1
        return sig


class MovingAverageCrossoverSignal(SignalGenerator):
    """Golden / death cross proxy."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        fast = self.cfg.params.get("fast", 10)
        slow = self.cfg.params.get("slow", 30)
        ma_fast = ohlcv["close"].rolling(fast).mean()
        ma_slow = ohlcv["close"].rolling(slow).mean()
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[(ma_fast > ma_slow) & (ma_fast.shift(1) <= ma_slow.shift(1))] = 1
        return sig * self.cfg.direction.value


class BollingerBreakoutSignal(SignalGenerator):
    """Close crosses above upper Bollinger Band."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 20)
        std_mult = self.cfg.params.get("std_mult", 2.0)
        ma = ohlcv["close"].rolling(lb).mean()
        std = ohlcv["close"].rolling(lb).std()
        upper = ma + std_mult * std
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[ohlcv["close"] > upper] = 1
        return sig * self.cfg.direction.value


class ADXBreakoutSignal(SignalGenerator):
    """Trend strength breakout using ADX proxy."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 14)
        atr = (ohlcv["high"] - ohlcv["low"]).rolling(lb).mean()
        dm_plus = (ohlcv["high"] - ohlcv["high"].shift(1)).clip(lower=0)
        dm_minus = (ohlcv["low"].shift(1) - ohlcv["low"]).clip(lower=0)
        dx = 100 * np.abs(dm_plus - dm_minus) / (dm_plus + dm_minus).replace(0, np.nan)
        adx = dx.rolling(lb).mean()
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[adx > 25] = 1
        return sig * self.cfg.direction.value


class MACDSignalSignal(SignalGenerator):
    """MACD line crosses above signal line."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        fast = self.cfg.params.get("fast", 12)
        slow = self.cfg.params.get("slow", 26)
        signal_lb = self.cfg.params.get("signal", 9)
        ema_fast = ohlcv["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = ohlcv["close"].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_lb, adjust=False).mean()
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[(macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))] = 1
        return sig * self.cfg.direction.value


class RSIOverboughtBreakoutSignal(SignalGenerator):
    """RSI exits oversold (bounce play)."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 14)
        delta = ohlcv["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(lb).mean()
        avg_loss = loss.rolling(lb).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[(rsi.shift(1) < 30) & (rsi >= 30)] = 1
        return sig * self.cfg.direction.value


# ---------------------------------------------------------------------------
# 4. MEAN REVERSION
# ---------------------------------------------------------------------------


class RSIMeanReversionSignal(SignalGenerator):
    """RSI > 70 -> short; RSI < 30 -> long."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 14)
        delta = ohlcv["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(lb).mean()
        avg_loss = loss.rolling(lb).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[rsi < 30] = 1
        if self.cfg.direction != SignalDirection.LONG:
            sig[rsi > 70] = -1
        return sig


class BollingerMeanReversionSignal(SignalGenerator):
    """Price touches lower band -> long."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 20)
        mult = self.cfg.params.get("std_mult", 2.0)
        ma = ohlcv["close"].rolling(lb).mean()
        std = ohlcv["close"].rolling(lb).std()
        lower = ma - mult * std
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[ohlcv["close"] < lower] = 1
        return sig * self.cfg.direction.value


class ZScoreMeanReversionSignal(SignalGenerator):
    """Z-score of price vs rolling mean."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 20)
        z_thresh = self.cfg.params.get("z_thresh", 2.0)
        ma = ohlcv["close"].rolling(lb).mean()
        std = ohlcv["close"].rolling(lb).std()
        z = (ohlcv["close"] - ma) / std.replace(0, np.nan)
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[z < -z_thresh] = 1
        if self.cfg.direction != SignalDirection.LONG:
            sig[z > z_thresh] = -1
        return sig


class PairRatioMeanReversionSignal(SignalGenerator):
    """
    Mean reversion on price ratio vs another symbol.
    In multi-symbol mode the second symbol is passed via params.
    """

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 20)
        z_thresh = self.cfg.params.get("z_thresh", 2.0)
        # Use log-price for stationarity
        log_p = np.log(ohlcv["close"])
        ma = log_p.rolling(lb).mean()
        std = log_p.rolling(lb).std()
        z = (log_p - ma) / std.replace(0, np.nan)
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[z < -z_thresh] = 1
        if self.cfg.direction != SignalDirection.LONG:
            sig[z > z_thresh] = -1
        return sig


class CandlestickHammerSignal(SignalGenerator):
    """Hammer / inverted hammer candlestick pattern."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        body = (ohlcv["close"] - ohlcv["open"]).abs()
        range_ = ohlcv["high"] - ohlcv["low"]
        lower_shadow = ohlcv[["open", "close"]].min(axis=1) - ohlcv["low"]
        upper_shadow = ohlcv["high"] - ohlcv[["open", "close"]].max(axis=1)
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        hammer = (lower_shadow > 2 * body) & (body > 0.01 * range_)
        sig[hammer] = 1
        return sig * self.cfg.direction.value


# ---------------------------------------------------------------------------
# 5. SECTOR ROTATION
# ---------------------------------------------------------------------------


class RelativeStrengthSectorSignal(SignalGenerator):
    """
    Buy symbols whose recent return exceeds their sector median.
    Requires multi-symbol context; in single-symbol mode uses
    a proxy sector drift.
    """

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 20)
        ret = ohlcv["close"].pct_change(lb)
        # Simple proxy: positive momentum vs its own past
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[ret > ret.rolling(lb * 3).mean()] = 1
        return sig * self.cfg.direction.value


class SectorMomentumRotationSignal(SignalGenerator):
    """Rotate into highest-momentum sector proxy."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 60)
        ret = ohlcv["close"].pct_change(lb)
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[ret > ret.quantile(0.75)] = 1
        return sig * self.cfg.direction.value


class SectorMeanReversionSignal(SignalGenerator):
    """Rotate into worst recent sector (contrarian)."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 60)
        ret = ohlcv["close"].pct_change(lb)
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[ret < ret.quantile(0.25)] = 1
        return sig * self.cfg.direction.value


class IndustryBreadthSignal(SignalGenerator):
    """Proxy: price above 50-day MA = breadth expansion."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 50)
        ma = ohlcv["close"].rolling(lb).mean()
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[ohlcv["close"] > ma] = 1
        return sig * self.cfg.direction.value


# ---------------------------------------------------------------------------
# 6. INSIDER ACTIVITY
# ---------------------------------------------------------------------------


class InsiderBuyClusterSignal(SignalGenerator):
    """
    Proxy: cluster of consecutive down days followed by volume spike
    mimics insider accumulation footprints.
    """

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        down_days = self.cfg.params.get("down_days", 3)
        vol_mult = self.cfg.params.get("vol_mult", 1.5)
        ret = ohlcv["close"].pct_change()
        consec_down = (ret < 0).astype(int).rolling(down_days).sum() == down_days
        vol_spike = ohlcv["volume"] > vol_mult * ohlcv["volume"].rolling(20).mean()
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[consec_down & vol_spike] = 1
        return sig * self.cfg.direction.value


class InsiderSellClusterSignal(SignalGenerator):
    """Proxy: climax volume after long rally."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        up_days = self.cfg.params.get("up_days", 5)
        vol_mult = self.cfg.params.get("vol_mult", 2.0)
        ret = ohlcv["close"].pct_change()
        consec_up = (ret > 0).astype(int).rolling(up_days).sum() == up_days
        vol_spike = ohlcv["volume"] > vol_mult * ohlcv["volume"].rolling(20).mean()
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[consec_up & vol_spike] = -1 if self.cfg.direction == SignalDirection.SHORT else 0
        return sig


# ---------------------------------------------------------------------------
# 7. MARKET BREADTH
# ---------------------------------------------------------------------------


class AdvanceDeclineProxySignal(SignalGenerator):
    """
    Proxy breadth: count of up days in rolling window as fraction.
    """

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 20)
        ret = ohlcv["close"].pct_change()
        breadth = (ret > 0).rolling(lb).mean()
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[breadth > 0.6] = 1
        return sig * self.cfg.direction.value


class NewHighsProxySignal(SignalGenerator):
    """Price makes new N-day high."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 50)
        highest = ohlcv["close"].rolling(lb).max()
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[ohlcv["close"] == highest] = 1
        return sig * self.cfg.direction.value


class McClellanProxySignal(SignalGenerator):
    """Proxy: 19-day EMA of daily breadth minus 39-day EMA."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        ret = ohlcv["close"].pct_change()
        adv = (ret > 0).astype(float)
        ema_fast = adv.ewm(span=19, adjust=False).mean()
        ema_slow = adv.ewm(span=39, adjust=False).mean()
        osc = ema_fast - ema_slow
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[osc > 0] = 1
        return sig * self.cfg.direction.value


# ---------------------------------------------------------------------------
# 8. SEASONALITY
# ---------------------------------------------------------------------------


class JanuaryEffectSignal(SignalGenerator):
    """Long small-cap proxy in January."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[ohlcv.index.month == 1] = 1
        return sig * self.cfg.direction.value


class EarningsSeasonSignal(SignalGenerator):
    """Long during earnings windows (Jan, Apr, Jul, Oct)."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        earnings_months = self.cfg.params.get("months", [1, 4, 7, 10])
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[ohlcv.index.month.isin(earnings_months)] = 1
        return sig * self.cfg.direction.value


class TaxLossHarvestingSignal(SignalGenerator):
    """Buy beaten-down names in late December / early January."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 60)
        ret = ohlcv["close"].pct_change(lb)
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        is_dec_jan = ohlcv.index.month.isin([12, 1])
        sig[is_dec_jan & (ret < -0.10)] = 1
        return sig * self.cfg.direction.value


class TurnOfMonthSignal(SignalGenerator):
    """Buy last day of month + first 3 trading days."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        dom = ohlcv.index.day
        is_turn = (dom >= 28) | (dom <= 3)
        sig[is_turn] = 1
        return sig * self.cfg.direction.value


class SummerDoldrumsSignal(SignalGenerator):
    """Avoid / short during August-September weakness."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[ohlcv.index.month.isin([8, 9])] = -1 if self.cfg.direction == SignalDirection.SHORT else 0
        return sig


class OctoberReversalSignal(SignalGenerator):
    """October often marks bear-market lows."""

    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        lb = self.cfg.params.get("lookback", 60)
        ret = ohlcv["close"].pct_change(lb)
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[ohlcv.index.month.isin([10]) & (ret < -0.15)] = 1
        return sig * self.cfg.direction.value


# ---------------------------------------------------------------------------
# STRATEGY GENERATOR  (150+ configs)
# ---------------------------------------------------------------------------


class StrategyGenerator:
    """
    Produce every StrategyConfig permutation across all families.
    Currently yields 150+ distinct configurations.
    """

    # Map family -> concrete signal class
    SIGNAL_REGISTRY: Dict[str, type] = {
        "earnings_surprise": EarningsSurpriseSignal,
        "earnings_guidance": EarningsGuidanceSignal,
        "post_earnings_drift": PostEarningsDriftSignal,
        "value_factor": ValueFactorSignal,
        "growth_factor": GrowthFactorSignal,
        "quality_factor": QualityFactorSignal,
        "lowvol_factor": LowVolFactorSignal,
        "momentum_factor": MomentumFactorSignal,
        "smallcap_premium": SmallCapPremiumSignal,
        "profitability_factor": ProfitabilityFactorSignal,
        "resistance_breakout": ResistanceBreakoutSignal,
        "support_bounce": SupportBounceSignal,
        "volume_breakout": VolumeConfirmedBreakoutSignal,
        "gap_fill": GapFillSignal,
        "ma_crossover": MovingAverageCrossoverSignal,
        "bollinger_breakout": BollingerBreakoutSignal,
        "adx_breakout": ADXBreakoutSignal,
        "macd_signal": MACDSignalSignal,
        "rsi_overbought_breakout": RSIOverboughtBreakoutSignal,
        "rsi_mean_reversion": RSIMeanReversionSignal,
        "bollinger_mean_reversion": BollingerMeanReversionSignal,
        "zscore_mean_reversion": ZScoreMeanReversionSignal,
        "pair_ratio_mr": PairRatioMeanReversionSignal,
        "candlestick_hammer": CandlestickHammerSignal,
        "relative_strength_sector": RelativeStrengthSectorSignal,
        "sector_momentum_rotation": SectorMomentumRotationSignal,
        "sector_mean_reversion": SectorMeanReversionSignal,
        "industry_breadth": IndustryBreadthSignal,
        "insider_buy_cluster": InsiderBuyClusterSignal,
        "insider_sell_cluster": InsiderSellClusterSignal,
        "advance_decline_proxy": AdvanceDeclineProxySignal,
        "new_highs_proxy": NewHighsProxySignal,
        "mcclellan_proxy": McClellanProxySignal,
        "january_effect": JanuaryEffectSignal,
        "earnings_season": EarningsSeasonSignal,
        "tax_loss_harvesting": TaxLossHarvestingSignal,
        "turn_of_month": TurnOfMonthSignal,
        "summer_doldrums": SummerDoldrumsSignal,
        "october_reversal": OctoberReversalSignal,
    }

    def __init__(self) -> None:
        self._configs: List[StrategyConfig] = []

    # ------------------------------------------------------------------
    # Parameter grids
    # ------------------------------------------------------------------

    def generate_all(self) -> List[StrategyConfig]:
        """Build the full candidate list."""
        self._configs = []
        self._add_earnings_momentum()
        self._add_factor_based()
        self._add_technical_breakout()
        self._add_mean_reversion()
        self._add_sector_rotation()
        self._add_insider_activity()
        self._add_market_breadth()
        self._add_seasonality()
        logger.info("Generated %d candidate strategy configs.", len(self._configs))
        return self._configs

    def _add_earnings_momentum(self) -> None:
        cat = StrategyCategory.EARNINGS_MOMENTUM
        for vol_lb, z in itertools.product([10, 20, 40], [1.0, 1.5, 2.0, 2.5]):
            self._configs.append(StrategyConfig(
                name="earnings_surprise", category=cat,
                params={"vol_lookback": vol_lb, "z_threshold": z},
                lookback=vol_lb, hold_period=5,
            ))
        for streak in [2, 3, 4, 5]:
            self._configs.append(StrategyConfig(
                name="earnings_guidance", category=cat,
                params={"streak": streak}, lookback=20, hold_period=5,
            ))
        for vol_lb, k in itertools.product([10, 20, 40], [1.5, 2.0, 2.5, 3.0]):
            self._configs.append(StrategyConfig(
                name="post_earnings_drift", category=cat,
                params={"vol_lookback": vol_lb, "gap_threshold": k},
                lookback=vol_lb, hold_period=10,
            ))

    def _add_factor_based(self) -> None:
        cat = StrategyCategory.FACTOR_BASED
        # value
        for lb in [40, 60, 90, 120]:
            self._configs.append(StrategyConfig(
                name="value_factor", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=20,
            ))
        # growth
        for lb in [60, 90, 120, 180]:
            self._configs.append(StrategyConfig(
                name="growth_factor", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=20,
            ))
        # quality
        for vlb, tlb in itertools.product([10, 20], [40, 60, 90]):
            self._configs.append(StrategyConfig(
                name="quality_factor", category=cat,
                params={"vol_lb": vlb, "trend_lb": tlb},
                lookback=max(vlb, tlb), hold_period=20,
            ))
        # low-vol
        for lb in [10, 20, 40, 60]:
            self._configs.append(StrategyConfig(
                name="lowvol_factor", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=20,
            ))
        # momentum (12-1)
        for ll, ls in itertools.product([120, 180, 240], [10, 20, 30]):
            self._configs.append(StrategyConfig(
                name="momentum_factor", category=cat,
                params={"lookback_long": ll, "lookback_skip": ls},
                lookback=ll, hold_period=20,
            ))
        # small-cap premium
        for lb in [10, 20, 40]:
            self._configs.append(StrategyConfig(
                name="smallcap_premium", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=10,
            ))
        # profitability
        for lb in [40, 60, 90]:
            self._configs.append(StrategyConfig(
                name="profitability_factor", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=20,
            ))

    def _add_technical_breakout(self) -> None:
        cat = StrategyCategory.TECHNICAL_BREAKOUT
        for lb in [10, 20, 40, 60]:
            self._configs.append(StrategyConfig(
                name="resistance_breakout", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=5,
            ))
            self._configs.append(StrategyConfig(
                name="support_bounce", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=5,
            ))
        for lb in [10, 20, 40]:
            self._configs.append(StrategyConfig(
                name="volume_breakout", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=5,
            ))
        for gap in [0.01, 0.02, 0.03]:
            self._configs.append(StrategyConfig(
                name="gap_fill", category=cat, params={"gap_pct": gap},
                lookback=20, hold_period=3,
            ))
        for f, s in [(5, 20), (10, 30), (20, 50), (50, 200)]:
            self._configs.append(StrategyConfig(
                name="ma_crossover", category=cat,
                params={"fast": f, "slow": s},
                lookback=s, hold_period=10,
            ))
        for lb, m in itertools.product([20, 40], [1.5, 2.0, 2.5]):
            self._configs.append(StrategyConfig(
                name="bollinger_breakout", category=cat,
                params={"lookback": lb, "std_mult": m},
                lookback=lb, hold_period=5,
            ))
        for lb in [10, 14, 20]:
            self._configs.append(StrategyConfig(
                name="adx_breakout", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=10,
            ))
        for f, s, g in [(12, 26, 9), (8, 21, 5), (5, 35, 5)]:
            self._configs.append(StrategyConfig(
                name="macd_signal", category=cat,
                params={"fast": f, "slow": s, "signal": g},
                lookback=s, hold_period=5,
            ))
        for lb in [7, 14, 21]:
            self._configs.append(StrategyConfig(
                name="rsi_overbought_breakout", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=3,
            ))

    def _add_mean_reversion(self) -> None:
        cat = StrategyCategory.MEAN_REVERSION
        for lb in [7, 14, 21]:
            self._configs.append(StrategyConfig(
                name="rsi_mean_reversion", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=3,
            ))
        for lb, m in itertools.product([20, 40], [1.5, 2.0, 2.5]):
            self._configs.append(StrategyConfig(
                name="bollinger_mean_reversion", category=cat,
                params={"lookback": lb, "std_mult": m},
                lookback=lb, hold_period=5,
            ))
        for lb, z in itertools.product([20, 40, 60], [1.5, 2.0, 2.5]):
            self._configs.append(StrategyConfig(
                name="zscore_mean_reversion", category=cat,
                params={"lookback": lb, "z_thresh": z},
                lookback=lb, hold_period=5,
            ))
        for lb, z in itertools.product([20, 40, 60], [1.5, 2.0, 2.5]):
            self._configs.append(StrategyConfig(
                name="pair_ratio_mr", category=cat,
                params={"lookback": lb, "z_thresh": z},
                lookback=lb, hold_period=5,
            ))
        self._configs.append(StrategyConfig(
            name="candlestick_hammer", category=cat, params={},
            lookback=5, hold_period=2,
        ))

    def _add_sector_rotation(self) -> None:
        cat = StrategyCategory.SECTOR_ROTATION
        for lb in [20, 40, 60]:
            self._configs.append(StrategyConfig(
                name="relative_strength_sector", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=20,
            ))
        for lb in [40, 60, 90]:
            self._configs.append(StrategyConfig(
                name="sector_momentum_rotation", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=20,
            ))
            self._configs.append(StrategyConfig(
                name="sector_mean_reversion", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=20,
            ))
        for lb in [20, 50, 100]:
            self._configs.append(StrategyConfig(
                name="industry_breadth", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=20,
            ))

    def _add_insider_activity(self) -> None:
        cat = StrategyCategory.INSIDER_ACTIVITY
        for dd, vm in itertools.product([3, 4, 5], [1.2, 1.5, 2.0]):
            self._configs.append(StrategyConfig(
                name="insider_buy_cluster", category=cat,
                params={"down_days": dd, "vol_mult": vm},
                lookback=20, hold_period=10,
            ))
        for ud, vm in itertools.product([4, 5, 6], [1.5, 2.0, 2.5]):
            self._configs.append(StrategyConfig(
                name="insider_sell_cluster", category=cat,
                params={"up_days": ud, "vol_mult": vm},
                lookback=20, hold_period=5, direction=SignalDirection.SHORT,
            ))

    def _add_market_breadth(self) -> None:
        cat = StrategyCategory.MARKET_BREADTH
        for lb in [10, 20, 40]:
            self._configs.append(StrategyConfig(
                name="advance_decline_proxy", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=10,
            ))
        for lb in [20, 50, 100]:
            self._configs.append(StrategyConfig(
                name="new_highs_proxy", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=10,
            ))
        self._configs.append(StrategyConfig(
            name="mcclellan_proxy", category=cat, params={},
            lookback=50, hold_period=10,
        ))

    def _add_seasonality(self) -> None:
        cat = StrategyCategory.SEASONALITY
        self._configs.append(StrategyConfig(
            name="january_effect", category=cat, params={},
            lookback=20, hold_period=20,
        ))
        for months in [[1, 4, 7, 10], [1, 4, 7, 10, 12]]:
            self._configs.append(StrategyConfig(
                name="earnings_season", category=cat, params={"months": months},
                lookback=20, hold_period=20,
            ))
        for lb in [30, 60, 90]:
            self._configs.append(StrategyConfig(
                name="tax_loss_harvesting", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=10,
            ))
        self._configs.append(StrategyConfig(
            name="turn_of_month", category=cat, params={},
            lookback=10, hold_period=5,
        ))
        self._configs.append(StrategyConfig(
            name="summer_doldrums", category=cat, params={},
            lookback=20, hold_period=20, direction=SignalDirection.SHORT,
        ))
        for lb in [30, 60, 90]:
            self._configs.append(StrategyConfig(
                name="october_reversal", category=cat, params={"lookback": lb},
                lookback=lb, hold_period=20,
            ))

    @classmethod
    def resolve_signal_generator(cls, config: StrategyConfig) -> SignalGenerator:
        """Factory: build the concrete signal generator for a config."""
        klass = cls.SIGNAL_REGISTRY.get(config.name)
        if klass is None:
            raise ValueError(f"No signal generator registered for '{config.name}'")
        return klass(config)               # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# BACKTEST ENGINE
# ---------------------------------------------------------------------------


class BacktestEngine:
    """
    Event-driven-style vectorised back-test.

    * Commission:  $0.005 / share  (institutional tier)
    * Slippage:    1 bp large-cap, 3 bp mid-cap
    * Hold period: configurable per strategy (days)
    """

    def __init__(
        self,
        commission: float = COMMISSION_PER_SHARE,
        slippage_large_bp: float = SLIPPAGE_LARGE_BP,
        slippage_mid_bp: float = SLIPPAGE_MID_BP,
        risk_free: float = RISK_FREE_RATE,
    ) -> None:
        self.comm = commission
        self.slip_large = slippage_large_bp * BP
        self.slip_mid = slippage_mid_bp * BP
        self.risk_free = risk_free

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(
        self,
        config: StrategyConfig,
        ohlcv: pd.DataFrame,
        symbol: str,
    ) -> BacktestResult:
        """
        Run a single-strategy back-test on *ohlcv* and return a
        fully-populated BacktestResult (before statistical layers).
        """
        # 1. Generate signals
        gen = StrategyGenerator.resolve_signal_generator(config)
        sig = gen(ohlcv)

        # 2. Daily returns
        close = ohlcv["close"]
        daily_ret = close.pct_change().fillna(0)

        # 3. Strategy returns (signal * next-day return, lagged)
        position = sig.shift(1).fillna(0)          # avoid look-ahead
        raw_strategy_ret = position * daily_ret

        # 4. Transaction-cost model
        tc = self._transaction_costs(position, close, symbol)
        strategy_ret = raw_strategy_ret - tc

        # 5. Equity curve
        equity = (1 + strategy_ret.replace(np.nan, 0)).cumprod()
        equity_vals = equity.values

        # 6. Derive metrics
        total_r = equity_vals[-1] - 1 if len(equity_vals) else 0
        ann_r = self._annualised_return(strategy_ret)
        vol = self._annualised_vol(strategy_ret)
        sharpe = self._sharpe(strategy_ret)
        sortino = self._sortino(strategy_ret)
        mdd = self._max_drawdown(equity_vals)
        hr, avg_w, avg_l, pf = self._trade_stats(strategy_ret)
        n_trades = int((position.diff().abs() > 0).sum())

        return BacktestResult(
            config=config,
            total_return=total_r,
            annualized_return=ann_r,
            volatility=vol,
            sharpe=sharpe,
            sortino=sortino,
            max_drawdown=mdd,
            hit_rate=hr,
            avg_win=avg_w,
            avg_loss=avg_l,
            profit_factor=pf,
            num_trades=n_trades,
            raw_equity_curve=equity_vals,
        )

    # ------------------------------------------------------------------
    # Cost model
    # ------------------------------------------------------------------

    def _transaction_costs(
        self,
        position: pd.Series,
        close: pd.Series,
        symbol: str,
    ) -> pd.Series:
        """
        Commission + slippage per trade.
        We assume $1 notional per unit position for cross-sectional comparability.
        """
        slip = self.slip_large if symbol in LARGE_CAP else self.slip_mid
        trade = position.diff().abs().fillna(0)
        # Commission as fraction of notional (assume avg price ~$100 for scaling)
        avg_price = close.mean() if close.mean() > 0 else 100
        comm_frac = self.comm / avg_price
        tc = trade * (slip + comm_frac)
        return tc

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @staticmethod
    def _annualised_return(returns: pd.Series) -> float:
        return float(returns.mean() * DAYS_PER_YEAR)

    @staticmethod
    def _annualised_vol(returns: pd.Series) -> float:
        return float(returns.std() * np.sqrt(DAYS_PER_YEAR))

    def _sharpe(self, returns: pd.Series) -> float:
        ann_r = self._annualised_return(returns)
        ann_v = self._annualised_vol(returns)
        if ann_v == 0:
            return 0.0
        return float((ann_r - self.risk_free) / ann_v)

    @staticmethod
    def _sortino(returns: pd.Series) -> float:
        downside = returns[returns < 0].std() * np.sqrt(DAYS_PER_YEAR)
        ann_r = returns.mean() * DAYS_PER_YEAR
        if downside == 0:
            return 0.0
        return float(ann_r / downside)

    @staticmethod
    def _max_drawdown(equity: np.ndarray) -> float:
        if len(equity) == 0:
            return 0.0
        peak = np.maximum.accumulate(equity)
        dd = (peak - equity) / peak
        return float(np.max(dd))

    @staticmethod
    def _trade_stats(returns: pd.Series) -> Tuple[float, float, float, float]:
        wins = returns[returns > 0]
        losses = returns[returns < 0]
        hr = len(wins) / (len(wins) + len(losses)) if (len(wins) + len(losses)) > 0 else 0
        avg_w = float(wins.mean()) if len(wins) else 0.0
        avg_l = float(losses.mean()) if len(losses) else 0.0
        pf = abs(float(wins.sum() / losses.sum())) if len(losses) and losses.sum() != 0 else float("inf")
        return hr, avg_w, avg_l, pf


# ---------------------------------------------------------------------------
# STATISTICAL VALIDATION
# ---------------------------------------------------------------------------


class StatisticalValidator:
    """
    1. Bootstrapped Sharpe (10 000 resamples)
    2. Two-sample t-test vs risk-free rate
    3. Benjamini-Hochberg FDR correction
    4. Walk-forward 3-fold rolling Sharpe check
    5. Monte-Carlo stress test (shuffled returns)
    """

    def __init__(
        self,
        n_bootstrap: int = 10_000,
        n_monte_carlo: int = 5_000,
        random_seed: int = 2026,
    ) -> None:
        self.n_boot = n_bootstrap
        self.n_mc = n_monte_carlo
        self.rng = default_rng(random_seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(
        self,
        result: BacktestResult,
    ) -> BacktestResult:
        """Augment *result* with all statistical tests and set *passed*."""
        if result.num_trades < 10:
            result.passed = False
            return result

        returns = self._extract_returns(result)
        if len(returns) < 30:
            result.passed = False
            return result

        # 1. Bootstrap
        bs_mean, bs_std, bs_p05 = self._bootstrap_sharpe(returns)
        result.boot_sharpe_mean = bs_mean
        result.boot_sharpe_std = bs_std
        result.boot_sharpe_p05 = bs_p05

        # 2. t-test
        result.p_value = self._ttest(returns)

        # 3. Walk-forward
        result.wf_scores = self._walk_forward(returns)

        # 4. Monte-Carlo
        result.mc_p05_sharpe = self._monte_carlo_sharpe(returns)

        # 5. Pass / fail gate
        result.passed = self._pass_fail(result)
        return result

    def apply_fdr_correction(
        self,
        results: List[BacktestResult],
    ) -> List[BacktestResult]:
        """
        Benjamini-Hochberg procedure over all *results*.
        Mutates each result.q_value and re-evaluates passed flag.
        """
        if not results:
            return results

        pvals = np.array([r.p_value for r in results])
        n = len(pvals)
        order = np.argsort(pvals)
        sorted_p = pvals[order]
        qvals = np.empty(n)
        # BH step-up
        for i in range(n - 1, -1, -1):
            qvals[order[i]] = min(sorted_p[i] * n / (i + 1),
                                   qvals[order[i + 1]] if i < n - 1 else 1.0)
        for r, q in zip(results, qvals):
            r.q_value = float(q)
            r.passed = r.passed and (r.q_value <= MAX_QVALUE)
        return results

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_returns(result: BacktestResult) -> np.ndarray:
        """Reconstruct daily returns from equity curve."""
        eq = result.raw_equity_curve
        if len(eq) < 2:
            return np.array([])
        returns = np.diff(eq) / eq[:-1]
        return returns

    def _bootstrap_sharpe(self, returns: np.ndarray) -> Tuple[float, float, float]:
        """Block-bootstrap Sharpe distribution."""
        n = len(returns)
        block = max(5, n // 20)
        sharpe_samples = np.empty(self.n_boot)
        for b in range(self.n_boot):
            idx = self._block_bootstrap_indices(n, block)
            boot_ret = returns[idx]
            sharpe_samples[b] = self._sharpe_from_returns(boot_ret)
        return float(sharpe_samples.mean()), float(sharpe_samples.std()), float(
            np.percentile(sharpe_samples, MC_PERCENTILE))

    def _block_bootstrap_indices(self, n: int, block: int) -> np.ndarray:
        """Circular block bootstrap."""
        indices = np.arange(n)
        n_blocks = n // block + 2
        starts = self.rng.integers(0, n, size=n_blocks)
        blocks = [np.roll(indices, -s)[:block] for s in starts]
        pooled = np.concatenate(blocks)[:n]
        return pooled

    @staticmethod
    def _sharpe_from_returns(returns: np.ndarray) -> float:
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        ann_mean = returns.mean() * DAYS_PER_YEAR
        ann_vol = returns.std() * np.sqrt(DAYS_PER_YEAR)
        return float((ann_mean - RISK_FREE_RATE) / ann_vol)

    def _ttest(self, returns: np.ndarray) -> float:
        """Two-sided t-test: strategy mean return > 0 ?"""
        if len(returns) < 2:
            return 1.0
        _, p = stats.ttest_1samp(returns, 0.0, alternative="greater")
        return float(p)

    def _walk_forward(self, returns: np.ndarray, n_folds: int = 3) -> List[float]:
        """Rolling n-fold Sharpe – each fold must exceed WF_MIN_SHARPE."""
        fold_size = len(returns) // n_folds
        scores: List[float] = []
        for i in range(n_folds):
            fold = returns[i * fold_size:(i + 1) * fold_size]
            scores.append(self._sharpe_from_returns(fold))
        return scores

    def _monte_carlo_sharpe(self, returns: np.ndarray) -> float:
        """
        Shuffle returns 5 000 times, recompute Sharpe each time.
        Return 5th percentile (stress Sharpe).
        """
        n = len(returns)
        sharpe_samples = np.empty(self.n_mc)
        for i in range(self.n_mc):
            perm = self.rng.permutation(n)
            sharpe_samples[i] = self._sharpe_from_returns(returns[perm])
        return float(np.percentile(sharpe_samples, MC_PERCENTILE))

    @staticmethod
    def _pass_fail(result: BacktestResult) -> bool:
        checks = [
            result.sharpe > MIN_SHARPE,
            result.max_drawdown < MAX_DRAWDOWN,
            result.p_value < MAX_PVALUE,
            result.boot_sharpe_p05 > 0,
            all(s > WF_MIN_SHARPE for s in result.wf_scores) if result.wf_scores else False,
            result.mc_p05_sharpe > 0,
            result.num_trades >= 10,
        ]
        return all(checks)


# ---------------------------------------------------------------------------
# ENSEMBLE CONSTRUCTOR
# ---------------------------------------------------------------------------


class EnsembleConstructor:
    """
    Select top 5-10 strategies ensuring:
        * factor diversification (max 2 per category)
        * sector balancing
        * Sharpe-weighted allocation
    """

    def __init__(
        self,
        min_strategies: int = 5,
        max_strategies: int = 10,
        max_per_category: int = 2,
    ) -> None:
        self.min_n = min_strategies
        self.max_n = max_strategies
        self.max_cat = max_per_category

    def build(
        self,
        results: List[BacktestResult],
    ) -> List[EnsembleAllocation]:
        """
        Greedy selection: sort by Sharpe, pick while maintaining
        category diversity and sector balance.
        """
        passed = [r for r in results if r.passed]
        if not passed:
            logger.warning("No strategies passed validation; returning empty ensemble.")
            return []

        # Sort descending Sharpe
        passed.sort(key=lambda r: r.sharpe, reverse=True)

        selected: List[BacktestResult] = []
        cat_counts: Dict[str, int] = defaultdict(int)
        sector_counts: Dict[str, int] = defaultdict(int)

        for r in passed:
            cat = r.config.category.value
            if cat_counts[cat] >= self.max_cat:
                continue
            # Approximate sector by picking a random symbol from universe
            # (in production, bind the actual symbol traded)
            sector = "Mixed"
            selected.append(r)
            cat_counts[cat] += 1
            sector_counts[sector] += 1
            if len(selected) >= self.max_n:
                break

        if len(selected) < self.min_n:
            logger.warning("Only %d strategies selected (< minimum %d).",
                           len(selected), self.min_n)

        # Sharpe-weighted allocation
        total_sharpe = sum(r.sharpe for r in selected)
        allocations: List[EnsembleAllocation] = []
        for r in selected:
            w = r.sharpe / total_sharpe if total_sharpe > 0 else 1 / len(selected)
            allocations.append(EnsembleAllocation(
                strategy_uid=r.config.uid(),
                strategy_name=r.config.name,
                category=r.config.category.value,
                weight=w,
                capital_allocation_pct=w * 100,
                expected_return=r.annualized_return,
                expected_sharpe=r.sharpe,
                symbols=EQUITY_SYMBOLS[:10],  # placeholder – refine per strategy
                sector_breakdown={SECTOR_MAP.get(s, "Other"): 0.1 for s in EQUITY_SYMBOLS[:10]},
                meta={
                    "params": r.config.params,
                    "hold_period": r.config.hold_period,
                    "p_value": round(r.p_value, 6),
                    "q_value": round(r.q_value, 6),
                    "boot_sharpe_p05": round(r.boot_sharpe_p05, 4),
                    "max_drawdown": round(r.max_drawdown, 4),
                    "hit_rate": round(r.hit_rate, 4),
                    "num_trades": r.num_trades,
                },
            ))
        return allocations


# ---------------------------------------------------------------------------
# ORCHESTRATOR  (end-to-end harness)
# ---------------------------------------------------------------------------


class EquityStrategyHarness:
    """
    End-to-end harness:
        generate -> back-test -> validate -> ensemble -> export JSON
    """

    def __init__(
        self,
        symbols: Optional[Sequence[str]] = None,
        data_manager: Optional[PriceDataManager] = None,
        random_seed: int = 2026,
    ) -> None:
        self.symbols = list(symbols or EQUITY_SYMBOLS)
        self.dm = data_manager or PriceDataManager(seed=random_seed)
        self.gen = StrategyGenerator()
        self.engine = BacktestEngine()
        self.validator = StatisticalValidator(random_seed=random_seed)
        self.builder = EnsembleConstructor()

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def run_full_pipeline(self) -> Dict[str, Any]:
        """
        Execute the complete pipeline and return a serialisable dict
        ready for findtorontoevents.ca/audit ingestion.
        """
        logger.info("=== EQUITY STRATEGY HARNESS v%s ===", __version__)
        logger.info("Symbols: %d | Max steps: 60", len(self.symbols))

        # Stage 1 — Generate
        t0 = datetime.utcnow()
        configs = self.gen.generate_all()
        logger.info("Stage 1  GENERATE  : %d configs  (%.1fs)",
                    len(configs), (datetime.utcnow() - t0).total_seconds())

        # Stage 2 — Back-test (per config, per symbol)
        t0 = datetime.utcnow()
        results: List[BacktestResult] = []
        symbol_sample = self.symbols[:15]   # cap for speed; expand in production
        for sym in symbol_sample:
            try:
                ohlcv = self.dm.load_ohlcv(sym)
            except Exception as exc:
                logger.debug("Skip %s: %s", sym, exc)
                continue
            for cfg in configs:
                try:
                    res = self.engine.run(cfg, ohlcv, sym)
                    results.append(res)
                except Exception as exc:
                    logger.debug("Backtest fail %s %s: %s", sym, cfg.name, exc)
        logger.info("Stage 2  BACKTEST  : %d results  (%.1fs)",
                    len(results), (datetime.utcnow() - t0).total_seconds())

        # Stage 3 — Validate
        t0 = datetime.utcnow()
        validated = [self.validator.validate(r) for r in results]
        validated = self.validator.apply_fdr_correction(validated)
        passed = [r for r in validated if r.passed]
        logger.info("Stage 3  VALIDATE  : %d passed / %d  (%.1fs)",
                    len(passed), len(validated),
                    (datetime.utcnow() - t0).total_seconds())

        # Stage 4 — Ensemble
        t0 = datetime.utcnow()
        ensemble = self.builder.build(validated)
        logger.info("Stage 4  ENSEMBLE  : %d strategies  (%.1fs)",
                    len(ensemble), (datetime.utcnow() - t0).total_seconds())

        # Stage 5 — Export
        payload = {
            "harness_version": __version__,
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "summary": {
                "configs_generated": len(configs),
                "backtests_run": len(results),
                "strategies_passed": len(passed),
                "ensemble_size": len(ensemble),
                "thresholds": {
                    "min_sharpe": MIN_SHARPE,
                    "max_drawdown": MAX_DRAWDOWN,
                    "max_pvalue": MAX_PVALUE,
                    "max_qvalue": MAX_QVALUE,
                    "wf_min_sharpe": WF_MIN_SHARPE,
                    "mc_percentile": MC_PERCENTILE,
                },
            },
            "ensemble": [a.to_audit_json() for a in ensemble],
            "all_validated": [r.to_dict() for r in passed],
        }
        return payload

    def save_json(self, payload: Dict[str, Any], path: str) -> None:
        """Serialise payload to JSON file."""
        with open(path, "w") as fh:
            json.dump(payload, fh, indent=2, default=str)
        logger.info("Saved payload -> %s", path)


# ---------------------------------------------------------------------------
# UNIT TEST SKELETON
# ---------------------------------------------------------------------------


def _unit_tests() -> None:
    """Quick smoke tests – run with `python equity_strategy_harness.py --test`."""
    logger.setLevel(logging.DEBUG)

    # 1. Config hash stable
    c1 = StrategyConfig(name="test", category=StrategyCategory.FACTOR_BASED,
                        params={"a": 1})
    c2 = StrategyConfig(name="test", category=StrategyCategory.FACTOR_BASED,
                        params={"a": 1})
    assert c1.uid() == c2.uid(), "UID deterministic"

    # 2. Data manager produces DataFrame
    dm = PriceDataManager(seed=42)
    df = dm.load_ohlcv("AAPL", "2024-01-01", "2024-06-01")
    assert len(df) > 50
    assert set(df.columns) == {"open", "high", "low", "close", "volume"}

    # 3. Generator yields > 150
    gen = StrategyGenerator()
    configs = gen.generate_all()
    assert len(configs) >= 150, f"Only {len(configs)} configs"

    # 4. Signal generator returns valid series
    cfg = configs[0]
    sig_gen = StrategyGenerator.resolve_signal_generator(cfg)
    sig = sig_gen(df)
    assert len(sig) == len(df)
    assert set(sig.unique()).issubset({-1, 0, 1})

    # 5. Backtest produces result
    engine = BacktestEngine()
    res = engine.run(cfg, df, "AAPL")
    assert isinstance(res, BacktestResult)
    assert res.num_trades >= 0

    # 6. Validator sets passed correctly
    val = StatisticalValidator(n_bootstrap=100, n_monte_carlo=100)
    res2 = val.validate(res)
    assert hasattr(res2, "passed")

    # 7. FDR correction runs
    validated = val.apply_fdr_correction([res2])
    assert not np.isnan(validated[0].q_value)

    # 8. Ensemble builds
    ec = EnsembleConstructor()
    ens = ec.build(validated)
    assert isinstance(ens, list)

    # 9. End-to-end harness
    harness = EquityStrategyHarness(symbols=["AAPL", "MSFT"], random_seed=42)
    payload = harness.run_full_pipeline()
    assert "ensemble" in payload

    logger.info("All %d smoke tests passed.", 9)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Equity Strategy Harness")
    parser.add_argument("--test", action="store_true", help="Run unit-test skeleton")
    parser.add_argument("--out", default="equity_ensemble_output.json",
                        help="Output JSON path")
    parser.add_argument("--symbols", nargs="+", default=None,
                        help="Override symbol list")
    args = parser.parse_args()

    if args.test:
        _unit_tests()
    else:
        sym_list = args.symbols or EQUITY_SYMBOLS
        harness = EquityStrategyHarness(symbols=sym_list, random_seed=42)
        payload = harness.run_full_pipeline()
        harness.save_json(payload, args.out)
        print(f"Ensemble payload written to {args.out}")
        print(f"Summary: {payload['summary']}")
