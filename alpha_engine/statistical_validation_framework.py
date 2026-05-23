#!/usr/bin/env python3
"""
================================================================================
Multi-Strategy Statistical Validation Framework
================================================================================
Unified statistical validation suite used by ALL asset-class strategy agents.
Provides rigorous hypothesis testing, multiple-testing correction, walk-forward
validation, Monte-Carlo stress testing, and ensemble construction.

Components
----------
* StrategyBacktest          — unified back-test interface (IS / OOS)
* BootstrapValidator        — bootstrapped Sharpe + confidence intervals
* MultipleTestingCorrector  — Benjamini-Hochberg FDR + Bonferroni
* WalkForwardValidator      — rolling-window validation
* MonteCarloStressTester    — synthetic path generation
* EnsembleConstructor       — risk-parity + correlation-clustered ensemble

Integration (example)
---------------------
    from statistical_validation_framework import (
        StrategyBacktest, BootstrapValidator,
        MultipleTestingCorrector, WalkForwardValidator,
        MonteCarloStressTester, EnsembleConstructor,
    )

    backtest = StrategyBacktest(ohlc_df, signals)
    result = backtest.run()

    boot = BootstrapValidator(result.returns, n_resamples=10_000)
    sharpe_ci = boot.sharpe_confidence_interval(alpha=0.05)

    mtc = MultipleTestingCorrector([r.p_value for r in all_results])
    significant = mtc.bh_fdr(alpha=0.05)

Target:  Eliminate fluke winners via rigorous statistical controls.

Author: Alpha Engine Team (ported from Kimi research bundle)
Date: 2026-05-21 (port)
Originally: 2026-05-20
================================================================================
"""
from __future__ import annotations

import json
import logging
import warnings
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import numpy as np
import pandas as pd
from numpy.random import default_rng

# Lazy imports for heavy deps (scipy, sklearn) — core classes work with just numpy
_scipy_stats: Any = None
_scipy_cluster: Any = None
_scipy_spatial: Any = None
_sklearn_cov: Any = None


def _ensure_scipy_stats():
    global _scipy_stats
    if _scipy_stats is None:
        try:
            import scipy.stats as s
            _scipy_stats = s
        except ImportError:
            raise ImportError(
                "scipy is required for statistical tests. "
                "Install: pip install scipy"
            )
    return _scipy_stats


def _ensure_scipy_cluster():
    global _scipy_cluster
    if _scipy_cluster is None:
        try:
            from scipy.cluster import hierarchy as h
            _scipy_cluster = h
        except ImportError:
            raise ImportError(
                "scipy.cluster is required for ensemble clustering. "
                "Install: pip install scipy"
            )
    return _scipy_cluster


def _ensure_scipy_spatial():
    global _scipy_spatial
    if _scipy_spatial is None:
        try:
            from scipy.spatial import distance as d
            _scipy_spatial = d
        except ImportError:
            raise ImportError(
                "scipy.spatial is required for ensemble clustering. "
                "Install: pip install scipy"
            )
    return _scipy_spatial


def _ensure_sklearn_cov():
    global _sklearn_cov
    if _sklearn_cov is None:
        try:
            from sklearn.covariance import LedoitWolf as L
            _sklearn_cov = L
        except ImportError:
            raise ImportError(
                "scikit-learn is required for covariance shrinkage (LedoitWolf). "
                "Install: pip install scikit-learn"
            )
    return _sklearn_cov

logger = logging.getLogger("statistical_validation_framework")


def _setup_logging(level: int = logging.INFO) -> None:
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
warnings.filterwarnings("ignore", category=RuntimeWarning)

__version__ = "2.0.0"
__date__ = "2026-05-20"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RISK_FREE_RATE: float = 0.045  # 4.5% annual
TRADING_DAYS_YEAR: int = 252
BOOTSTRAP_RESAMPLES_DEFAULT: int = 10_000
MONTE_CARLO_RUNS_DEFAULT: int = 1_000
WALK_FORWARD_TRAIN_MONTHS: int = 6
WALK_FORWARD_TEST_MONTHS: int = 3
MAX_DRAWDOWN_MAX: float = 0.20
SHARPE_MIN: float = 1.0
PVALUE_MAX: float = 0.05
ENSEMBLE_MAX_CORRELATION: float = 0.70


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Direction(Enum):
    LONG = 1
    SHORT = -1
    FLAT = 0


class Outcome(Enum):
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"


class StrategyStatus(Enum):
    ACTIVE = "active"
    REJECTED = "rejected"
    PAUSED = "paused"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class Signal:
    """A single strategy signal / trade instruction."""
    timestamp: datetime
    direction: Direction
    price: float
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_long(self) -> bool:
        return self.direction == Direction.LONG

    @property
    def is_short(self) -> bool:
        return self.direction == Direction.SHORT


@dataclass
class BacktestResult:
    """Comprehensive backtest outcome."""
    strategy_id: str
    strategy_name: str
    asset_class: str
    direction: str

    # Returns
    total_return: float
    annualized_return: float
    daily_returns: pd.Series = field(repr=False)

    # Risk metrics
    sharpe_ratio: float
    sortino_ratio: float
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
    skewness: float = 0.0
    kurtosis: float = 0.0

    # Validation
    is_valid: bool = True
    rejection_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "asset_class": self.asset_class,
            "direction": self.direction,
            "total_return": round(self.total_return, 6),
            "annualized_return": round(self.annualized_return, 6),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "sortino_ratio": round(self.sortino_ratio, 4),
            "max_drawdown": round(self.max_drawdown, 6),
            "max_drawdown_duration": self.max_drawdown_duration,
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
            "sharpe_ci_lower": round(self.sharpe_ci_lower, 4),
            "sharpe_ci_upper": round(self.sharpe_ci_upper, 4),
            "skewness": round(self.skewness, 4),
            "kurtosis": round(self.kurtosis, 4),
            "is_valid": self.is_valid,
            "rejection_reason": self.rejection_reason,
        }

    @property
    def returns_array(self) -> np.ndarray:
        return self.daily_returns.values


@dataclass
class WalkForwardResult:
    """Result from walk-forward validation."""
    strategy_id: str
    windows: int
    in_sample_sharpes: List[float] = field(default_factory=list)
    out_of_sample_sharpes: List[float] = field(default_factory=list)
    in_sample_returns: List[float] = field(default_factory=list)
    out_of_sample_returns: List[float] = field(default_factory=list)
    consistency_score: float = 0.0  # fraction of windows where OOS sharpe > 0
    is_robust: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "windows": self.windows,
            "is_sharpe_mean": round(float(np.mean(self.in_sample_sharpes)), 4) if self.in_sample_sharpes else 0,
            "oos_sharpe_mean": round(float(np.mean(self.out_of_sample_sharpes)), 4) if self.out_of_sample_sharpes else 0,
            "consistency_score": round(self.consistency_score, 4),
            "is_robust": self.is_robust,
        }


@dataclass
class MonteCarloResult:
    """Monte-Carlo stress test result."""
    strategy_id: str
    n_runs: int
    observed_sharpe: float
    simulated_sharpes: np.ndarray = field(repr=False)
    percentile_5: float = 0.0
    percentile_95: float = 0.0
    probability_of_loss: float = 0.0
    max_dd_95: float = 0.0
    passes_stress: bool = False

    def __post_init__(self):
        if len(self.simulated_sharpes) > 0:
            self.percentile_5 = float(np.percentile(self.simulated_sharpes, 5))
            self.percentile_95 = float(np.percentile(self.simulated_sharpes, 95))
            self.probability_of_loss = float(np.mean(self.simulated_sharpes < 0))
            # Tight gate: the 5th percentile bootstrap Sharpe must be > 0.
            # This means ≥95% of bootstrap resamples produce a positive Sharpe,
            # not just that the observed Sharpe beats the 5th percentile.
            # Harder to pass — eliminates strategies that are only good on average
            # but have fat left tails that produce negative outcomes frequently.
            self.passes_stress = self.percentile_5 > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "n_runs": self.n_runs,
            "observed_sharpe": round(self.observed_sharpe, 4),
            "percentile_5": round(self.percentile_5, 4),
            "percentile_95": round(self.percentile_95, 4),
            "probability_of_loss": round(self.probability_of_loss, 4),
            "max_dd_95": round(self.max_dd_95, 4),
            "passes_stress": self.passes_stress,
        }


@dataclass
class EnsembleResult:
    """Final ensemble construction result."""
    ensemble_sharpe: float
    ensemble_volatility: float
    ensemble_max_dd: float
    ensemble_return: float
    selected_strategies: List[str] = field(default_factory=list)
    weights: Dict[str, float] = field(default_factory=dict)
    correlation_matrix: Optional[np.ndarray] = field(default=None, repr=False)
    clusters: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ensemble_sharpe": round(self.ensemble_sharpe, 4),
            "ensemble_volatility": round(self.ensemble_volatility, 6),
            "ensemble_max_dd": round(self.ensemble_max_dd, 6),
            "ensemble_return": round(self.ensemble_return, 6),
            "n_selected": len(self.selected_strategies),
            "selected_strategies": self.selected_strategies,
            "weights": {k: round(v, 4) for k, v in self.weights.items()},
            "clusters": self.clusters,
        }


# ---------------------------------------------------------------------------
# 1. StrategyBacktest — unified back-test interface
# ---------------------------------------------------------------------------
class StrategyBacktest:
    """
    Run a vectorised back-test on OHLCV data given a sequence of signals.

    Parameters
    ----------
    ohlc : pd.DataFrame
        Must contain columns ['open','high','low','close','volume'] with DatetimeIndex.
    signals : List[Signal]
        Entry / exit signals produced by a strategy.
    asset_class : str
        Used for asset-class-specific slippage and thresholds.
    strategy_id : str
    strategy_name : str
    """

    SLIPPAGE_BPS: Dict[str, float] = {
        "CRYPTO": 1.0, "EQUITY": 2.0, "ETF": 2.0, "FOREX": 0.5,
        "COMMODITY": 3.0, "BOND": 1.0, "FUTURES": 1.5,
        "STOCK": 2.0, "INDEX": 2.0,
    }

    def __init__(
        self,
        ohlc: pd.DataFrame,
        signals: List[Signal],
        asset_class: str = "EQUITY",
        strategy_id: str = "",
        strategy_name: str = "",
    ) -> None:
        self.ohlc = ohlc.copy()
        self.signals = sorted(signals, key=lambda s: s.timestamp)
        self.asset_class = asset_class.upper()
        self.strategy_id = strategy_id
        self.strategy_name = strategy_name
        self.slippage_pct = self.SLIPPAGE_BPS.get(self.asset_class, 2.0) / 10000.0

        # ensure DatetimeIndex
        if not isinstance(self.ohlc.index, pd.DatetimeIndex):
            self.ohlc.index = pd.to_datetime(self.ohlc.index)

    def _apply_slippage(self, price: float, direction: Direction) -> float:
        """Apply conservative slippage."""
        if direction == Direction.LONG:
            return price * (1 + self.slippage_pct)
        elif direction == Direction.SHORT:
            return price * (1 - self.slippage_pct)
        return price

    def run(self) -> BacktestResult:
        """Execute back-test and return result."""
        if self.ohlc.empty or len(self.signals) < 2:
            return self._empty_result("Insufficient data or signals")

        # Build daily position series from signals
        daily_position = pd.Series(0, index=self.ohlc.index, dtype=float)
        current_pos: float = 0.0

        for sig in self.signals:
            mask = self.ohlc.index >= sig.timestamp
            if mask.any():
                daily_position.loc[mask] = sig.direction.value
                current_pos = sig.direction.value

        if daily_position.abs().sum() == 0:
            return self._empty_result("No active positions")

        # daily returns: position * market return
        close = self.ohlc["close"]
        market_returns = close.pct_change().fillna(0.0)
        strategy_returns = daily_position.shift(1).fillna(0) * market_returns
        strategy_returns = strategy_returns.dropna()

        if strategy_returns.std() == 0 or len(strategy_returns) < 10:
            return self._empty_result("No variation in strategy returns")

        # metrics
        total_ret = float((1 + strategy_returns).prod() - 1)
        n_days = len(strategy_returns)
        ann_ret = float((1 + total_ret) ** (TRADING_DAYS_YEAR / max(n_days, 1)) - 1)
        vol = float(strategy_returns.std() * np.sqrt(TRADING_DAYS_YEAR))
        excess_ret = strategy_returns - (RISK_FREE_RATE / TRADING_DAYS_YEAR)
        xs_mean = excess_ret.mean()
        xs_std = excess_ret.std(ddof=1)
        sharpe = float(xs_mean / xs_std * np.sqrt(TRADING_DAYS_YEAR)) if xs_std > 0 else 0.0

        # Sortino
        downside = strategy_returns[strategy_returns < 0].std(ddof=1)
        sortino = float(xs_mean / downside * np.sqrt(TRADING_DAYS_YEAR)) if downside > 0 else 0.0

        # drawdown
        cum = (1 + strategy_returns).cumprod()
        peak = cum.cummax()
        dd = (cum - peak) / peak
        max_dd = float(dd.min())
        max_dd_duration = int((dd < 0).astype(int).groupby((dd == 0).cumsum()).sum().max())
        calmar = abs(ann_ret / max_dd) if max_dd != 0 else 0.0

        # trade statistics (use signal changes as trade boundaries)
        trades = []
        entry_price: Optional[float] = None
        entry_dir = Direction.FLAT
        for sig in self.signals:
            if sig.direction != Direction.FLAT and entry_price is None:
                entry_price = self._apply_slippage(sig.price, sig.direction)
                entry_dir = sig.direction
            elif sig.direction == Direction.FLAT and entry_price is not None:
                exit_price = sig.price
                pnl = (exit_price - entry_price) / entry_price * entry_dir.value
                trades.append(pnl)
                entry_price = None

        n_trades = len(trades)
        if n_trades > 0:
            trades_arr = np.array(trades)
            hit_rate = float(np.mean(trades_arr > 0))
            avg_win = float(np.mean(trades_arr[trades_arr > 0])) if np.any(trades_arr > 0) else 0.0
            avg_loss = float(np.mean(trades_arr[trades_arr <= 0])) if np.any(trades_arr <= 0) else 0.0
            profit_factor = abs(avg_win * np.sum(trades_arr > 0) / (avg_loss * np.sum(trades_arr <= 0))) if avg_loss != 0 else float('inf')
            expectancy = float(np.mean(trades_arr))
        else:
            hit_rate = avg_win = avg_loss = profit_factor = expectancy = 0.0

        # t-test p-value (lazy import scipy.stats)
        _stats = _ensure_scipy_stats()
        t_stat, p_val = _stats.ttest_1samp(strategy_returns, 0)
        p_val = float(p_val) if np.isfinite(p_val) else 1.0

        return BacktestResult(
            strategy_id=self.strategy_id,
            strategy_name=self.strategy_name,
            asset_class=self.asset_class,
            direction="MIXED",
            total_return=total_ret,
            annualized_return=ann_ret,
            daily_returns=strategy_returns,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            max_drawdown_duration=max_dd_duration,
            calmar_ratio=calmar,
            volatility=vol,
            n_trades=n_trades,
            hit_rate=hit_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            expectancy=expectancy,
            p_value_ttest=p_val,
            skewness=float(strategy_returns.skew()),
            kurtosis=float(strategy_returns.kurtosis()),
        )

    def _empty_result(self, reason: str) -> BacktestResult:
        return BacktestResult(
            strategy_id=self.strategy_id,
            strategy_name=self.strategy_name,
            asset_class=self.asset_class,
            direction="FLAT",
            total_return=0.0,
            annualized_return=0.0,
            daily_returns=pd.Series(dtype=float),
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown=0.0,
            max_drawdown_duration=0,
            calmar_ratio=0.0,
            volatility=0.0,
            n_trades=0,
            hit_rate=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            profit_factor=0.0,
            expectancy=0.0,
            is_valid=False,
            rejection_reason=reason,
        )


# ---------------------------------------------------------------------------
# 2. BootstrapValidator
# ---------------------------------------------------------------------------
class BootstrapValidator:
    """Bootstrapped Sharpe ratio with percentile confidence intervals."""

    def __init__(
        self,
        daily_returns: Union[pd.Series, np.ndarray],
        n_resamples: int = BOOTSTRAP_RESAMPLES_DEFAULT,
        random_seed: Optional[int] = None,
    ) -> None:
        self.returns = np.asarray(daily_returns).flatten()
        self.n_resamples = n_resamples
        self.rng = default_rng(random_seed)
        self._cached_sharpes: Optional[np.ndarray] = None

    def _annualised_sharpe(self, daily: np.ndarray) -> float:
        if len(daily) < 10 or daily.std(ddof=1) == 0:
            return 0.0
        xs = daily - (RISK_FREE_RATE / TRADING_DAYS_YEAR)
        return float(xs.mean() / xs.std(ddof=1) * np.sqrt(TRADING_DAYS_YEAR))

    def _compute(self) -> np.ndarray:
        if self._cached_sharpes is not None:
            return self._cached_sharpes
        n = len(self.returns)
        sharpes = np.empty(self.n_resamples)
        for i in range(self.n_resamples):
            sample = self.rng.choice(self.returns, size=n, replace=True)
            sharpes[i] = self._annualised_sharpe(sample)
        self._cached_sharpes = sharpes
        return sharpes

    def sharpe_confidence_interval(self, alpha: float = 0.05) -> Tuple[float, float]:
        """Return (lower, upper) percentile CI for Sharpe ratio."""
        sharpes = self._compute()
        lower = float(np.percentile(sharpes, 100 * alpha / 2))
        upper = float(np.percentile(sharpes, 100 * (1 - alpha / 2)))
        return (lower, upper)

    def p_value(self, null_sharpe: float = 0.0) -> float:
        """Bootstrap p-value: fraction of resampled Sharpes <= null_sharpe."""
        sharpes = self._compute()
        observed = self._annualised_sharpe(self.returns)
        if observed >= null_sharpe:
            return float(np.mean(sharpes <= null_sharpe))
        else:
            return float(np.mean(sharpes >= null_sharpe))

    def summary(self) -> Dict[str, float]:
        ci = self.sharpe_confidence_interval(alpha=0.05)
        return {
            "observed_sharpe": round(self._annualised_sharpe(self.returns), 4),
            "sharpe_ci_95_lower": round(ci[0], 4),
            "sharpe_ci_95_upper": round(ci[1], 4),
            "p_value_vs_zero": round(self.p_value(0.0), 6),
            "bootstrap_samples": self.n_resamples,
        }


# ---------------------------------------------------------------------------
# 3. MultipleTestingCorrector
# ---------------------------------------------------------------------------
class MultipleTestingCorrector:
    """
    Benjamini-Hochberg FDR and Bonferroni correction for multiple-hypothesis
    testing across hundreds of strategies.
    """

    def __init__(self, p_values: Sequence[float]) -> None:
        self.p_values = np.array(p_values, dtype=float)
        self.n = len(self.p_values)
        self._sorted_indices = np.argsort(self.p_values)

    def bh_fdr(self, alpha: float = 0.05) -> np.ndarray:
        """
        Benjamini-Hochberg procedure.  Returns boolean mask of length n;
        True = significant after FDR correction.
        """
        if self.n == 0:
            return np.array([], dtype=bool)
        sorted_p = self.p_values[self._sorted_indices]
        thresholds = np.arange(1, self.n + 1) / self.n * alpha
        # find largest k such that p_(k) <= threshold_k
        significant_sorted = sorted_p <= thresholds
        if not significant_sorted.any():
            return np.zeros(self.n, dtype=bool)
        # all p-values up to the largest significant one are significant
        max_k = np.where(significant_sorted)[0].max()
        result_sorted = np.zeros(self.n, dtype=bool)
        result_sorted[: max_k + 1] = True
        # unsort
        result = np.empty(self.n, dtype=bool)
        result[self._sorted_indices] = result_sorted
        return result

    def bonferroni(self, alpha: float = 0.05) -> np.ndarray:
        """Bonferroni correction.  Very conservative."""
        if self.n == 0:
            return np.array([], dtype=bool)
        return self.p_values <= (alpha / self.n)

    def adaptive_fdr(self, alpha: float = 0.05, pi0_method: str = "storey") -> np.ndarray:
        """
        Storey's adaptive FDR (q-value style) using the bootstrap pi0 estimator.
        Falls back to BH-FDR if pi0 estimation fails.
        """
        if self.n == 0:
            return np.array([], dtype=bool)
        try:
            # Storey pi0: proportion of true null hypotheses
            lambda_vals = np.arange(0.05, 0.95, 0.05)
            pi0s = [(self.p_values > lam).mean() / (1 - lam) for lam in lambda_vals]
            pi0 = min(np.median(pi0s), 1.0)
            adjusted_alpha = alpha / pi0 if pi0 > 0 else alpha
            return self.bh_fdr(alpha=adjusted_alpha)
        except Exception:
            logger.warning("Adaptive FDR failed, falling back to BH-FDR")
            return self.bh_fdr(alpha=alpha)

    def summary(self, alpha: float = 0.05) -> Dict[str, Any]:
        bh_sig = self.bh_fdr(alpha)
        bonf_sig = self.bonferroni(alpha)
        try:
            adaptive_sig = self.adaptive_fdr(alpha)
        except Exception:
            adaptive_sig = bh_sig
        return {
            "n_tests": self.n,
            "alpha": alpha,
            "significant_bh_fdr": int(bh_sig.sum()),
            "significant_bonferroni": int(bonf_sig.sum()),
            "significant_adaptive_fdr": int(adaptive_sig.sum()),
            "fraction_significant_bh": round(float(bh_sig.mean()), 4) if self.n > 0 else 0,
        }


# ---------------------------------------------------------------------------
# 4. WalkForwardValidator
# ---------------------------------------------------------------------------
class WalkForwardValidator:
    """Rolling walk-forward validation with expanding or fixed windows."""

    def __init__(
        self,
        daily_returns: Union[pd.Series, np.ndarray],
        train_months: int = WALK_FORWARD_TRAIN_MONTHS,
        test_months: int = WALK_FORWARD_TEST_MONTHS,
    ) -> None:
        self.returns = pd.Series(daily_returns).dropna()
        self.train_months = train_months
        self.test_months = test_months

    def _sharpe(self, s: pd.Series) -> float:
        if len(s) < 10 or s.std(ddof=1) == 0:
            return 0.0
        xs = s - (RISK_FREE_RATE / TRADING_DAYS_YEAR)
        return float(xs.mean() / xs.std(ddof=1) * np.sqrt(TRADING_DAYS_YEAR))

    def run(
        self,
        strategy_id: str = "",
        min_train_days: int = 30,
    ) -> WalkForwardResult:
        """Execute walk-forward and return result."""
        returns = self.returns
        if len(returns) < min_train_days + 20:
            return WalkForwardResult(strategy_id=strategy_id, windows=0)

        # generate monthly-based windows
        is_sharpes: List[float] = []
        oos_sharpes: List[float] = []
        is_returns: List[float] = []
        oos_returns: List[float] = []

        start_idx = 0
        train_days = self.train_months * 21
        test_days = self.test_months * 21

        while start_idx + train_days + test_days <= len(returns):
            train = returns.iloc[start_idx : start_idx + train_days]
            test = returns.iloc[
                start_idx + train_days : start_idx + train_days + test_days
            ]

            if len(train) >= min_train_days and len(test) >= 5:
                is_sharpes.append(self._sharpe(train))
                oos_sharpes.append(self._sharpe(test))
                is_returns.append(float((1 + train).prod() - 1))
                oos_returns.append(float((1 + test).prod() - 1))

            start_idx += test_days  # roll forward by test window

        n_windows = len(is_sharpes)
        if n_windows == 0:
            return WalkForwardResult(strategy_id=strategy_id, windows=0)

        # consistency: fraction of OOS windows with Sharpe > 0
        consistency = float(np.mean(np.array(oos_sharpes) > 0))
        robust = consistency >= 0.5 and np.mean(oos_sharpes) > 0

        return WalkForwardResult(
            strategy_id=strategy_id,
            windows=n_windows,
            in_sample_sharpes=is_sharpes,
            out_of_sample_sharpes=oos_sharpes,
            in_sample_returns=is_returns,
            out_of_sample_returns=oos_returns,
            consistency_score=consistency,
            is_robust=robust,
        )


# ---------------------------------------------------------------------------
# 5. MonteCarloStressTester
# ---------------------------------------------------------------------------
class MonteCarloStressTester:
    """Generate synthetic price paths and test strategy robustness."""

    def __init__(
        self,
        daily_returns: Union[pd.Series, np.ndarray],
        n_runs: int = MONTE_CARLO_RUNS_DEFAULT,
        random_seed: Optional[int] = None,
    ) -> None:
        self.returns = np.asarray(daily_returns).flatten()
        self.n_runs = n_runs
        self.rng = default_rng(random_seed)

    def _sharpe(self, s: np.ndarray) -> float:
        if len(s) < 10 or s.std(ddof=1) == 0:
            return 0.0
        xs = s - (RISK_FREE_RATE / TRADING_DAYS_YEAR)
        return float(xs.mean() / xs.std(ddof=1) * np.sqrt(TRADING_DAYS_YEAR))

    def run(
        self,
        strategy_id: str = "",
        scenario: str = "bootstrap",
        shock_params: Optional[Dict[str, float]] = None,
    ) -> MonteCarloResult:
        """
        Run Monte-Carlo simulation.

        scenario: 'bootstrap' | 'parametric' | 'regime_shift' | 'crash'
        """
        n = len(self.returns)
        observed_sharpe = self._sharpe(self.returns)
        simulated = np.empty(self.n_runs)
        max_dds = np.empty(self.n_runs)

        mu = np.mean(self.returns)
        sigma = np.std(self.returns, ddof=1)
        shock = shock_params or {}

        for i in range(self.n_runs):
            if scenario == "bootstrap":
                path = self.rng.choice(self.returns, size=n, replace=True)
            elif scenario == "parametric":
                path = self.rng.normal(mu, sigma, size=n)
            elif scenario == "regime_shift":
                # Two-regime model: random switch point
                switch = self.rng.integers(n // 4, 3 * n // 4)
                vol_mult = shock.get("vol_multiplier", 2.0)
                path = np.concatenate([
                    self.rng.normal(mu, sigma, size=switch),
                    self.rng.normal(mu, sigma * vol_mult, size=n - switch),
                ])
            elif scenario == "crash":
                # Insert a -X% shock day
                crash_pct = shock.get("crash_pct", -0.05)
                path = self.rng.choice(self.returns, size=n, replace=True)
                crash_day = self.rng.integers(n // 2, n)
                path[crash_day] = crash_pct
            else:
                path = self.rng.choice(self.returns, size=n, replace=True)

            simulated[i] = self._sharpe(path)
            # max drawdown
            cum = np.cumprod(1 + path)
            peak = np.maximum.accumulate(cum)
            dd = (cum - peak) / peak
            max_dds[i] = dd.min()

        return MonteCarloResult(
            strategy_id=strategy_id,
            n_runs=self.n_runs,
            observed_sharpe=observed_sharpe,
            simulated_sharpes=simulated,
            max_dd_95=float(np.percentile(max_dds, 5)),
        )


# ---------------------------------------------------------------------------
# 6. EnsembleConstructor
# ---------------------------------------------------------------------------
class EnsembleConstructor:
    """
    Build a risk-parity, correlation-clustered ensemble from validated
    strategy back-test results.
    """

    def __init__(
        self,
        results: Sequence[BacktestResult],
        max_correlation: float = ENSEMBLE_MAX_CORRELATION,
    ) -> None:
        self.results = [r for r in results if r.is_valid and len(r.daily_returns) > 10]
        self.max_correlation = max_correlation

    def _build_returns_matrix(self) -> pd.DataFrame:
        """Align daily returns across strategies."""
        if not self.results:
            return pd.DataFrame()
        series_dict = {}
        for r in self.results:
            key = f"{r.strategy_id}_{r.strategy_name}"
            series_dict[key] = r.daily_returns
        df = pd.DataFrame(series_dict).fillna(0.0)
        return df

    def _cluster_strategies(self, corr_matrix: pd.DataFrame, n_clusters: int = 5) -> Dict[str, int]:
        """Hierarchical clustering on correlation distance."""
        if corr_matrix.empty or corr_matrix.shape[0] < 3:
            return {k: 0 for k in corr_matrix.columns}
        # distance = 1 - |correlation|
        dist = 1 - np.abs(corr_matrix)
        np.fill_diagonal(dist.values, 0)
        # Ensure it's a valid distance matrix
        dist = np.clip(dist, 0, 1)
        _spatial = _ensure_scipy_spatial()
        condensed = _spatial.squareform(dist.values, checks=False)
        _clust = _ensure_scipy_cluster()
        Z = _clust.linkage(condensed, method="ward")
        n_clust = min(n_clusters, corr_matrix.shape[0])
        labels = _clust.fcluster(Z, n_clust, criterion="maxclust")
        return {col: int(label) for col, label in zip(corr_matrix.columns, labels)}

    def _risk_parity_weights(self, cov_matrix: pd.DataFrame) -> pd.Series:
        """Inverse-volatility weights with risk-parity constraint."""
        if cov_matrix.empty:
            return pd.Series()
        # Use Ledoit-Wolf shrinkage for stability (lazy import sklearn)
        try:
            LedoitWolf = _ensure_sklearn_cov()
            lw = LedoitWolf().fit(cov_matrix.values)
            shrunk_cov = pd.DataFrame(lw.covariance_, index=cov_matrix.index, columns=cov_matrix.columns)
        except Exception:
            shrunk_cov = cov_matrix

        vols = np.sqrt(np.diag(shrunk_cov.values))
        inv_vol = 1.0 / np.where(vols == 0, 1e-6, vols)
        weights = inv_vol / inv_vol.sum()
        return pd.Series(weights, index=cov_matrix.index)

    def build_ensemble(
        self,
        top_n_per_cluster: int = 3,
        min_sharpe: float = SHARPE_MIN,
    ) -> EnsembleResult:
        """
        Select strategies and compute ensemble weights.

        Pipeline:
            1. Filter by min_sharpe and valid p-value
            2. Remove highly correlated pairs
            3. Cluster remaining strategies
            4. Select top-N from each cluster
            5. Risk-parity weighting
            6. Compute ensemble statistics
        """
        if not self.results:
            return EnsembleResult(
                ensemble_sharpe=0.0, ensemble_volatility=0.0,
                ensemble_max_dd=0.0, ensemble_return=0.0,
            )

        # Step 1: filter
        filtered = [
            r for r in self.results
            if r.sharpe_ratio >= min_sharpe and r.p_value_ttest < PVALUE_MAX
        ]
        if not filtered:
            logger.warning("No strategies passed Sharpe + p-value filter")
            return EnsembleResult(
                ensemble_sharpe=0.0, ensemble_volatility=0.0,
                ensemble_max_dd=0.0, ensemble_return=0.0,
            )

        # Step 2: returns matrix
        returns_df = self._build_returns_matrix()
        valid_keys = [f"{r.strategy_id}_{r.strategy_name}" for r in filtered]
        returns_df = returns_df[[c for c in valid_keys if c in returns_df.columns]]

        if returns_df.empty:
            return EnsembleResult(ensemble_sharpe=0.0, ensemble_volatility=0.0,
                                  ensemble_max_dd=0.0, ensemble_return=0.0)

        # Step 3: correlation filtering
        corr = returns_df.corr()
        to_drop: set = set()
        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                c1, c2 = corr.columns[i], corr.columns[j]
                if abs(corr.loc[c1, c2]) > self.max_correlation:
                    # drop the one with lower Sharpe
                    s1 = next((r.sharpe_ratio for r in filtered if f"{r.strategy_id}_{r.strategy_name}" == c1), 0)
                    s2 = next((r.sharpe_ratio for r in filtered if f"{r.strategy_id}_{r.strategy_name}" == c2), 0)
                    to_drop.add(c2 if s1 >= s2 else c1)
        remaining_cols = [c for c in returns_df.columns if c not in to_drop]
        returns_df = returns_df[remaining_cols]

        if returns_df.empty or returns_df.shape[1] == 0:
            return EnsembleResult(ensemble_sharpe=0.0, ensemble_volatility=0.0,
                                  ensemble_max_dd=0.0, ensemble_return=0.0)

        # Step 4: cluster
        corr_filtered = returns_df.corr()
        clusters = self._cluster_strategies(corr_filtered)

        # Step 5: select top-N per cluster
        cluster_map = defaultdict(list)
        for col, clust_id in clusters.items():
            sharpe = next(
                (r.sharpe_ratio for r in filtered if f"{r.strategy_id}_{r.strategy_name}" == col), 0
            )
            cluster_map[clust_id].append((col, sharpe))

        selected: List[str] = []
        for clust_id, members in cluster_map.items():
            members_sorted = sorted(members, key=lambda x: x[1], reverse=True)
            selected.extend([m[0] for m in members_sorted[:top_n_per_cluster]])

        ensemble_returns = returns_df[selected]
        cov_matrix = ensemble_returns.cov() * TRADING_DAYS_YEAR

        # Step 6: risk-parity weights
        weights = self._risk_parity_weights(cov_matrix)
        weights_dict = {k: float(v) for k, v in weights.items()}

        # Normalize weights to sum to 1
        total_w = sum(weights_dict.values())
        if total_w > 0:
            weights_dict = {k: v / total_w for k, v in weights_dict.items()}

        # Compute ensemble stats
        port_returns = ensemble_returns @ pd.Series(weights_dict)
        total_ret = float((1 + port_returns).prod() - 1)
        vol = float(port_returns.std() * np.sqrt(TRADING_DAYS_YEAR))
        xs = port_returns - (RISK_FREE_RATE / TRADING_DAYS_YEAR)
        sharpe = float(xs.mean() / xs.std(ddof=1) * np.sqrt(TRADING_DAYS_YEAR)) if xs.std() > 0 else 0.0

        cum = (1 + port_returns).cumprod()
        peak = cum.cummax()
        dd = (cum - peak) / peak
        max_dd = float(dd.min())

        return EnsembleResult(
            ensemble_sharpe=sharpe,
            ensemble_volatility=vol,
            ensemble_max_dd=max_dd,
            ensemble_return=total_ret,
            selected_strategies=selected,
            weights=weights_dict,
            correlation_matrix=corr_filtered.values,
            clusters=clusters,
        )


# ---------------------------------------------------------------------------
# Unified Validator — convenience wrapper
# ---------------------------------------------------------------------------
class UnifiedValidator:
    """
    One-shot validation pipeline that runs ALL tests on a single strategy
    and returns a comprehensive pass/fail report.
    """

    def __init__(
        self,
        backtest_result: BacktestResult,
        n_bootstrap: int = BOOTSTRAP_RESAMPLES_DEFAULT,
        n_monte_carlo: int = MONTE_CARLO_RUNS_DEFAULT,
        random_seed: Optional[int] = 42,
    ) -> None:
        self.bt = backtest_result
        self.n_bootstrap = n_bootstrap
        self.n_monte_carlo = n_monte_carlo
        self.seed = random_seed

    def validate(self) -> Dict[str, Any]:
        """Run full validation suite and return report."""
        returns = self.bt.daily_returns
        if len(returns) < 30:
            return {"passed": False, "reason": "insufficient_return_history", "strategy_id": self.bt.strategy_id}

        # 1. Bootstrap
        boot = BootstrapValidator(returns, n_resamples=self.n_bootstrap, random_seed=self.seed)
        boot_ci = boot.sharpe_confidence_interval(alpha=0.05)
        boot_p = boot.p_value(0.0)

        # 2. Walk-forward
        wfv = WalkForwardValidator(returns)
        wfv_result = wfv.run(strategy_id=self.bt.strategy_id)

        # 3. Monte-Carlo
        mc = MonteCarloStressTester(returns, n_runs=self.n_monte_carlo, random_seed=self.seed)
        mc_result = mc.run(strategy_id=self.bt.strategy_id, scenario="bootstrap")

        # Pass/fail logic
        checks = {
            "sharpe_above_min": self.bt.sharpe_ratio >= SHARPE_MIN,
            "max_dd_within_limit": self.bt.max_drawdown >= -MAX_DRAWDOWN_MAX,
            "p_value_significant": boot_p < PVALUE_MAX,
            "ci_lower_positive": boot_ci[0] > 0,
            "walk_forward_robust": wfv_result.is_robust,
            "monte_carlo_passes": mc_result.passes_stress,
            "consistency_50pct": wfv_result.consistency_score >= 0.5,
        }

        all_passed = all(checks.values())

        return {
            "strategy_id": self.bt.strategy_id,
            "strategy_name": self.bt.strategy_name,
            "passed": all_passed,
            "checks": checks,
            "bootstrap": boot.summary(),
            "walk_forward": wfv_result.to_dict(),
            "monte_carlo": mc_result.to_dict(),
            "backtest": self.bt.to_dict(),
        }


# ---------------------------------------------------------------------------
# Batch validation helper (used by asset-class agents)
# ---------------------------------------------------------------------------
def validate_strategy_batch(
    backtest_results: Sequence[BacktestResult],
    alpha_fdr: float = 0.05,
    n_bootstrap: int = BOOTSTRAP_RESAMPLES_DEFAULT,
) -> Dict[str, Any]:
    """
    Validate a batch of strategies: bootstrap + multiple-testing correction.
    Returns which strategies survive statistical scrutiny.
    """
    validations: List[Dict[str, Any]] = []
    p_values: List[float] = []
    strategy_ids: List[str] = []

    for bt in backtest_results:
        if not bt.is_valid or len(bt.daily_returns) < 30:
            validations.append({
                "strategy_id": bt.strategy_id,
                "passed": False,
                "reason": "invalid_or_insufficient_data",
            })
            continue

        boot = BootstrapValidator(bt.daily_returns, n_resamples=n_bootstrap)
        p_val = boot.p_value(0.0)
        p_values.append(p_val)
        strategy_ids.append(bt.strategy_id)

        ci = boot.sharpe_confidence_interval(alpha=0.05)
        validations.append({
            "strategy_id": bt.strategy_id,
            "strategy_name": bt.strategy_name,
            "sharpe_ratio": round(bt.sharpe_ratio, 4),
            "p_value": round(p_val, 6),
            "sharpe_ci_95": [round(ci[0], 4), round(ci[1], 4)],
            "passed_raw": bt.sharpe_ratio >= SHARPE_MIN and p_val < PVALUE_MAX,
        })

    # Multiple-testing correction
    mtc = MultipleTestingCorrector(p_values)
    significant = mtc.bh_fdr(alpha=alpha_fdr)
    bonf = mtc.bonferroni(alpha=alpha_fdr)

    for i, sig in enumerate(significant):
        validations[i]["passed_bh_fdr"] = bool(sig)
        validations[i]["passed_bonferroni"] = bool(bonf[i])

    passed_ids = [
        v["strategy_id"] for v in validations
        if v.get("passed_raw", False) and v.get("passed_bh_fdr", False)
    ]

    return {
        "n_strategies": len(backtest_results),
        "n_tested": len(p_values),
        "n_passed_raw": sum(1 for v in validations if v.get("passed_raw", False)),
        "n_passed_bh_fdr": int(significant.sum()),
        "n_passed_bonferroni": int(bonf.sum()),
        "passed_strategy_ids": passed_ids,
        "mtc_summary": mtc.summary(alpha=alpha_fdr),
        "details": validations,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Statistical Validation Framework")
    parser.add_argument("--example-run", action="store_true", help="Run example validation")
    args = parser.parse_args()

    if args.example_run:
        # Create synthetic data for demonstration
        rng = default_rng(42)
        dates = pd.date_range("2024-01-01", "2025-05-20", freq="B")
        returns = pd.Series(rng.normal(0.0005, 0.01, size=len(dates)), index=dates)

        boot = BootstrapValidator(returns, n_resamples=5_000, random_seed=42)
        print("Bootstrap summary:", json.dumps(boot.summary(), indent=2))

        mtc = MultipleTestingCorrector([0.01, 0.03, 0.12, 0.8, 0.001])
        print("MTC summary:", json.dumps(mtc.summary(alpha=0.05), indent=2))

        wfv = WalkForwardValidator(returns)
        wfv_result = wfv.run(strategy_id="demo")
        print("Walk-forward:", json.dumps(wfv_result.to_dict(), indent=2))

        mc = MonteCarloStressTester(returns, n_runs=1_000, random_seed=42)
        mc_result = mc.run(strategy_id="demo", scenario="bootstrap")
        print("Monte-Carlo:", json.dumps(mc_result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
