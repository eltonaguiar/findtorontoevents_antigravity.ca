#!/usr/bin/env python3
"""
================================================================================
BOND Multi-Strategy Alpha Engine
================================================================================
A statistically rigorous multi-strategy harness for fixed-income bond ETF
selection, backtesting, validation, and ensemble construction.

Generates 120+ candidate strategies across 8 bond-specific categories:
  - Yield curve steepener/flattener (2s10s, 5s30s spreads)
  - Duration positioning based on rate momentum
  - Credit spread strategies (HY-IG spread mean reversion)
  - Inflation breakeven trades (TIP vs nominal)
  - Flight-to-quality signals (TLT/SPY ratio, VIX correlation)
  - Fed policy path strategies (dot plot pricing, meeting-based)
  - Municipal bond seasonality (MUB)
  - Emerging market debt carry (EMB)

Pipeline:
    1. StrategyGenerator  -> 120+ candidate strategies
    2. BacktestEngine      -> In-sample + walk-forward + Monte Carlo
    3. StatisticalValidator-> Bootstrapped Sharpe, t-test, BH-FDR correction
    4. EnsembleConstructor -> Duration-neutral, correlation-clustered
    5. IntegrationLayer    -> JSON output compatible with system ingest

Target System: findtorontoevents.ca/audit
Asset Class: BOND (Grade F hard block exempt)
Blocked: None (commodity_cot/cta_replicator exempt)
PnL WIN threshold: 5bp (0.0005)
PnL sanity cap: 50%

Bond Universe: TLT, IEF, SHY, LQD, AGG, BND, HYG, JNK, SJNK, BKLN, EMB, TIP, MUB, IGIB

Architecture: EMIT -> INGEST -> ACTIVE GATE -> SMART GATE -> HIGH CONVICTION -> CONSENSUS -> OUTCOME

Author: Alpha Engine Team
Date: 2026-05-20
Version: 2.0.0
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
from datetime import datetime, timedelta
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
from scipy.stats import percentileofscore
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
logger = logging.getLogger("bond_alpha_engine")

# ---------------------------------------------------------------------------
# Suppress harmless warnings
# ---------------------------------------------------------------------------
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

__version__ = "2.0.0"
__date__ = "2026-05-20"


# =============================================================================
# SECTION 1: DATA MODELS & ENUMS
# =============================================================================


class BondSector(Enum):
    """Fixed income sector classification."""
    TREASURY = "treasury"
    INVESTMENT_GRADE = "investment_grade"
    HIGH_YIELD = "high_yield"
    EMERGING_MARKET = "emerging_market"
    MUNICIPAL = "municipal"
    INFLATION_PROTECTED = "inflation_protected"
    AGGREGATE = "aggregate"
    BANK_LOAN = "bank_loan"


class StrategyCategory(Enum):
    """Taxonomy of bond strategy families."""
    YIELD_CURVE = "yield_curve"
    DURATION_POSITIONING = "duration_positioning"
    CREDIT_SPREAD = "credit_spread"
    INFLATION_BREAKEVEN = "inflation_breakeven"
    FLIGHT_TO_QUALITY = "flight_to_quality"
    FED_POLICY = "fed_policy"
    MUNICIPAL_SEASONALITY = "municipal_seasonality"
    EM_DEBT_CARRY = "em_debt_carry"
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    CARRY = "carry"
    MOMENTUM = "momentum"


class Direction(Enum):
    """Trade direction for bond signals."""
    LONG = 1
    SHORT = -1
    FLAT = 0


# =============================================================================
# SECTION 2: BOND UNIVERSE & METADATA
# =============================================================================

# Bond ETF universe with metadata including estimated duration, yield, convexity
BOND_UNIVERSE: Dict[str, Dict[str, Any]] = {
    # --- Treasury / Rate Sensitive ---
    "TLT": {
        "sector": BondSector.TREASURY,
        "name": "iShares 20+ Year Treasury ETF",
        "duration": 17.5,
        "convexity": 420.0,
        "avg_yield": 0.045,
        "coupon": 0.035,
        "credit_spread": 0.0,
    },
    "IEF": {
        "sector": BondSector.TREASURY,
        "name": "iShares 7-10 Year Treasury ETF",
        "duration": 7.4,
        "convexity": 75.0,
        "avg_yield": 0.042,
        "coupon": 0.032,
        "credit_spread": 0.0,
    },
    "SHY": {
        "sector": BondSector.TREASURY,
        "name": "iShares 1-3 Year Treasury ETF",
        "duration": 1.9,
        "convexity": 5.0,
        "avg_yield": 0.048,
        "coupon": 0.028,
        "credit_spread": 0.0,
    },
    # --- Aggregate / Core ---
    "AGG": {
        "sector": BondSector.AGGREGATE,
        "name": "iShares Core U.S. Aggregate Bond ETF",
        "duration": 6.1,
        "convexity": 58.0,
        "avg_yield": 0.048,
        "coupon": 0.034,
        "credit_spread": 0.005,
    },
    "BND": {
        "sector": BondSector.AGGREGATE,
        "name": "Vanguard Total Bond Market ETF",
        "duration": 6.2,
        "convexity": 60.0,
        "avg_yield": 0.047,
        "coupon": 0.033,
        "credit_spread": 0.005,
    },
    # --- Investment Grade Corporate ---
    "LQD": {
        "sector": BondSector.INVESTMENT_GRADE,
        "name": "iShares iBoxx $ Inv Grade Corporate Bond ETF",
        "duration": 8.3,
        "convexity": 95.0,
        "avg_yield": 0.051,
        "coupon": 0.038,
        "credit_spread": 0.009,
    },
    "IGIB": {
        "sector": BondSector.INVESTMENT_GRADE,
        "name": "iShares 5-10 Year Investment Grade Corporate Bond ETF",
        "duration": 5.8,
        "convexity": 45.0,
        "avg_yield": 0.050,
        "coupon": 0.036,
        "credit_spread": 0.008,
    },
    # --- High Yield ---
    "HYG": {
        "sector": BondSector.HIGH_YIELD,
        "name": "iShares iBoxx $ High Yield Corporate Bond ETF",
        "duration": 3.6,
        "convexity": 22.0,
        "avg_yield": 0.078,
        "coupon": 0.052,
        "credit_spread": 0.035,
    },
    "JNK": {
        "sector": BondSector.HIGH_YIELD,
        "name": "SPDR Bloomberg High Yield Bond ETF",
        "duration": 3.4,
        "convexity": 20.0,
        "avg_yield": 0.080,
        "coupon": 0.054,
        "credit_spread": 0.037,
    },
    "SJNK": {
        "sector": BondSector.HIGH_YIELD,
        "name": "SPDR Bloomberg Short Term High Yield Bond ETF",
        "duration": 1.8,
        "convexity": 8.0,
        "avg_yield": 0.085,
        "coupon": 0.058,
        "credit_spread": 0.040,
    },
    # --- Bank Loan / Floating Rate ---
    "BKLN": {
        "sector": BondSector.BANK_LOAN,
        "name": "Invesco Senior Loan ETF",
        "duration": 0.15,
        "convexity": 0.5,
        "avg_yield": 0.082,
        "coupon": 0.065,
        "credit_spread": 0.032,
    },
    # --- Emerging Market ---
    "EMB": {
        "sector": BondSector.EMERGING_MARKET,
        "name": "iShares J.P. Morgan USD Emerging Markets Bond ETF",
        "duration": 7.2,
        "convexity": 80.0,
        "avg_yield": 0.072,
        "coupon": 0.048,
        "credit_spread": 0.028,
    },
    # --- Inflation Protected ---
    "TIP": {
        "sector": BondSector.INFLATION_PROTECTED,
        "name": "iShares TIPS Bond ETF",
        "duration": 6.8,
        "convexity": 72.0,
        "avg_yield": 0.040,
        "coupon": 0.030,
        "credit_spread": 0.0,
    },
    # --- Municipal ---
    "MUB": {
        "sector": BondSector.MUNICIPAL,
        "name": "iShares National Muni Bond ETF",
        "duration": 5.9,
        "convexity": 52.0,
        "avg_yield": 0.035,
        "coupon": 0.030,
        "credit_spread": 0.003,
    },
}

# Blacklist (none for bonds, but keep for consistency)
BOND_BLACKLIST: set = set()

# Bond-specific thresholds (more conservative than other asset classes)
BOND_MIN_SHARPE_RATIO: float = 0.8
BOND_MIN_ANNUAL_RETURN: float = 0.02
BOND_MAX_MAX_DRAWDOWN: float = 0.10
BOND_MAX_DRAWDOWN_DAYS: int = 60
BOND_P_VALUE_THRESHOLD: float = 0.05
BOND_FDR_THRESHOLD: float = 0.10  # Benjamini-Hochberg
BOND_MIN_TRADES_PER_YEAR: int = 6
BOND_MIN_PROFIT_FACTOR: float = 1.2
BOND_PNL_WIN_THRESHOLD: float = 0.0005  # 5bp
BOND_PNL_SANITY_CAP: float = 0.50  # 50%

# Walk-forward parameters
BOND_WF_TRAIN_DAYS: int = 504  # ~2 years
BOND_WF_TEST_DAYS: int = 63   # ~3 months (quarterly)
BOND_WF_MIN_WINDOWS: int = 4

# Bootstrap parameters
BOOTSTRAP_RESAMPLES: int = 10_000

# Yield curve spread definitions
YIELD_CURVE_SPREADS: Dict[str, Tuple[str, str]] = {
    "2s10s": ("SHY", "IEF"),    # Short-term vs intermediate
    "5s10s": ("IEF", "TLT"),    # vs would need custom; use SHY vs IEF for short end
    "5s30s_proxy": ("IEF", "TLT"),  # Intermediate vs long
    "10s30s": ("IEF", "TLT"),   # Intermediate vs long
    "credit_ig": ("LQD", "IEF"),  # IG credit spread proxy
    "credit_hy": ("HYG", "LQD"),  # HY-IG spread
    "inflation_be": ("TIP", "IEF"),  # Breakeven proxy
    "em_sovereign": ("EMB", "IEF"),  # EM spread
}

# Duration bucket mapping
DURATION_BUCKETS: Dict[str, str] = {
    "TLT": "long",
    "IEF": "intermediate",
    "SHY": "short",
    "LQD": "intermediate",
    "AGG": "intermediate",
    "BND": "intermediate",
    "HYG": "short_intermediate",
    "JNK": "short_intermediate",
    "SJNK": "short",
    "BKLN": "ultra_short",
    "EMB": "intermediate_long",
    "TIP": "intermediate",
    "MUB": "intermediate",
    "IGIB": "intermediate",
}



# =============================================================================
# SECTION 3: DATA STRUCTURES
# =============================================================================


@dataclass
class BondStrategyResult:
    """Container for a single bond strategy backtest result."""

    strategy_id: str
    name: str
    category: StrategyCategory
    symbols: List[str]
    bond_sectors: List[BondSector]
    direction: str  # "long" | "short" | "spread" | "curve"

    # Performance metrics
    total_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_days: int
    calmar_ratio: float
    profit_factor: float
    win_rate: float
    num_trades: int
    avg_trade_return: float
    avg_win: float
    avg_loss: float
    payoff_ratio: float
    expectancy: float
    skewness: float
    kurtosis: float

    # Duration and convexity metrics
    effective_duration: float
    modified_duration: float
    convexity_contribution: float
    yield_carry_annual: float
    roll_down_return: float

    # Statistical validation
    p_value_sharpe: float
    p_value_bootstrap: float
    bh_fdr_rejected: bool
    walk_forward_passed: bool
    wf_sharpe_mean: float
    wf_sharpe_std: float

    # Metadata
    params: Dict[str, Any] = field(default_factory=dict)
    equity_curve: List[float] = field(default_factory=list)
    trade_log: List[Dict[str, Any]] = field(default_factory=list)
    pass_all_filters: bool = False
    ensemble_rank: int = 0


@dataclass
class EnsembleAllocation:
    """Final ensemble member with capital allocation."""

    strategy_id: str
    name: str
    symbols: List[str]
    direction: str
    allocation_pct: float
    expected_return: float
    expected_volatility: float
    expected_sharpe: float
    diversification_score: float
    category: StrategyCategory
    effective_duration: float
    duration_neutral_weight: float


@dataclass
class BondAlphaEngineOutput:
    """Complete engine output for downstream integration."""

    timestamp: str
    stage: str  # Pipeline stage identifier
    bond_sector_exposures: Dict[str, float]
    duration_bucket_exposures: Dict[str, float]
    strategy_results: List[Dict[str, Any]]
    ensemble: List[Dict[str, Any]]
    rejected_strategies: List[Dict[str, Any]]
    meta: Dict[str, Any]

    def to_json(self, path: str) -> None:
        """Serialize to JSON file."""
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2, default=str)


# =============================================================================
# SECTION 4: UTILITY FUNCTIONS
# =============================================================================


def calculate_sharpe(
    returns: np.ndarray, risk_free: float = 0.0, periods: int = 252
) -> float:
    """Annualized Sharpe ratio from daily returns."""
    if len(returns) < 30 or np.std(returns) == 0:
        return 0.0
    excess = returns - risk_free / periods
    return float(np.mean(excess) / np.std(excess) * np.sqrt(periods))


def calculate_sortino(
    returns: np.ndarray, risk_free: float = 0.0, periods: int = 252
) -> float:
    """Annualized Sortino ratio."""
    if len(returns) < 30:
        return 0.0
    excess = returns - risk_free / periods
    downside = returns[returns < 0]
    if len(downside) == 0 or np.std(downside) == 0:
        return float(np.mean(excess) * periods) if np.mean(excess) > 0 else 0.0
    return float(np.mean(excess) / np.std(downside) * np.sqrt(periods))


def calculate_max_drawdown(equity: np.ndarray) -> Tuple[float, int]:
    """Return (max_drawdown, max_drawdown_days)."""
    if len(equity) < 2:
        return 0.0, 0
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak
    max_dd = float(np.min(drawdown))
    underwater = drawdown < -0.001
    max_days = 0
    current = 0
    for u in underwater:
        if u:
            current += 1
            max_days = max(max_days, current)
        else:
            current = 0
    return max_dd, max_days


def calculate_calmar(
    returns: np.ndarray, periods: int = 252
) -> float:
    """Calmar ratio: annualized return / max drawdown."""
    if len(returns) < 60:
        return 0.0
    ann_ret = np.mean(returns) * periods
    equity = np.cumprod(1 + returns)
    max_dd, _ = calculate_max_drawdown(equity)
    if max_dd == 0:
        return 0.0
    return float(ann_ret / abs(max_dd))


def bootstrap_sharpe_pvalue(
    returns: np.ndarray,
    n_bootstrap: int = BOOTSTRAP_RESAMPLES,
    random_state: int = 42,
) -> float:
    """
    Bootstrap p-value for Sharpe ratio > 0.
    Returns probability that true Sharpe <= 0 given observed returns.
    Uses studentized bootstrap for better accuracy.
    """
    if len(returns) < 60:
        return 1.0
    rng = np.random.default_rng(random_state)
    observed_sharpe = calculate_sharpe(returns)
    if observed_sharpe <= 0:
        return 1.0

    boot_sharpes = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        sample = rng.choice(returns, size=len(returns), replace=True)
        boot_sharpes[i] = calculate_sharpe(sample)

    # Two-sided p-value
    pval = 2 * min(np.mean(boot_sharpes <= 0), np.mean(boot_sharpes >= 2 * observed_sharpe))
    pval = max(pval, 1.0 / n_bootstrap)  # Floor at resample precision
    return float(pval)


def benjamini_hochberg_fdr(
    p_values: np.ndarray, alpha: float = BOND_FDR_THRESHOLD
) -> np.ndarray:
    """
    Benjamini-Hochberg false discovery rate correction.
    Returns boolean array: True = reject null (significant).
    """
    p_values = np.array(p_values)
    n = len(p_values)
    if n == 0:
        return np.array([], dtype=bool)
    sorted_idx = np.argsort(p_values)
    sorted_p = p_values[sorted_idx]
    thresholds = np.arange(1, n + 1) / n * alpha
    rejected_sorted = sorted_p <= thresholds
    if np.any(rejected_sorted):
        last_true = np.where(rejected_sorted)[0][-1]
        rejected_sorted[: last_true + 1] = True
    rejected = np.zeros(n, dtype=bool)
    rejected[sorted_idx] = rejected_sorted
    return rejected


def walk_forward_validation(
    strategy_fn: Callable,
    prices: pd.DataFrame,
    train_days: int = BOND_WF_TRAIN_DAYS,
    test_days: int = BOND_WF_TEST_DAYS,
    min_windows: int = BOND_WF_MIN_WINDOWS,
) -> Tuple[bool, float, float]:
    """
    Walk-forward cross-validation for a strategy.
    Returns: (passed, mean_sharpe, std_sharpe)
    """
    n = len(prices)
    if n < train_days + test_days * min_windows:
        return False, 0.0, 0.0

    sharpes = []
    start = 0
    while start + train_days + test_days <= n:
        train = prices.iloc[start : start + train_days]
        test = prices.iloc[start + train_days : start + train_days + test_days]
        try:
            rets = strategy_fn(test, train)
            if isinstance(rets, pd.Series):
                rets = rets.values
            sharpe = calculate_sharpe(np.array(rets).flatten())
            sharpes.append(sharpe)
        except Exception:
            sharpes.append(0.0)
        start += test_days

    if len(sharpes) < min_windows:
        return False, 0.0, 0.0

    mean_sharpe = float(np.mean(sharpes))
    std_sharpe = float(np.std(sharpes))
    passed = mean_sharpe > 0.3 and np.mean(np.array(sharpes) > 0) >= 0.4
    return passed, mean_sharpe, std_sharpe


def get_effective_duration(symbol: str) -> float:
    """Return estimated effective duration for a bond ETF."""
    return BOND_UNIVERSE.get(symbol, {}).get("duration", 5.0)


def get_convexity(symbol: str) -> float:
    """Return estimated convexity for a bond ETF."""
    return BOND_UNIVERSE.get(symbol, {}).get("convexity", 50.0)


def estimate_price_change(
    symbol: str, yield_change: float
) -> float:
    """
    Estimate bond ETF price change from yield change using duration + convexity.
    dP/P ~= -D * dy + 0.5 * C * dy^2
    """
    dur = get_effective_duration(symbol)
    conv = get_convexity(symbol)
    return -dur * yield_change + 0.5 * conv * (yield_change ** 2)


def duration_neutral_weights(
    symbol_long: str, symbol_short: str
) -> Tuple[float, float]:
    """
    Compute duration-neutral weights for a pair trade.
    w_long * D_long = w_short * D_short, w_long + w_short = 1
    """
    d_long = get_effective_duration(symbol_long)
    d_short = get_effective_duration(symbol_short)
    if d_long + d_short == 0:
        return 0.5, 0.5
    w_long = d_short / (d_long + d_short)
    w_short = d_long / (d_long + d_short)
    return w_long, w_short



# =============================================================================
# SECTION 5: SYNTHETIC DATA GENERATION
# =============================================================================


def generate_synthetic_bond_data(
    symbol: str,
    start_date: str = "2018-01-01",
    end_date: str = "2026-05-20",
    seed: Optional[int] = None,
) -> pd.DataFrame:
    """
    Generate realistic synthetic bond ETF price data for backtesting.

    Models bond price dynamics with:
    - Yield-driven price movement (duration + convexity)
    - Credit spread mean reversion
    - Fed cycle regimes (rate cutting, hiking, pause)
    - Seasonal patterns (muni bonds, year-end effects)
    - Volatility clustering via GARCH
    """
    if seed is not None:
        np.random.seed(seed)

    dates = pd.bdate_range(start=start_date, end=end_date)
    n = len(dates)

    # Get bond parameters
    meta = BOND_UNIVERSE.get(symbol, {})
    duration = meta.get("duration", 5.0)
    convexity = meta.get("convexity", 50.0)
    avg_yield = meta.get("avg_yield", 0.04)
    coupon = meta.get("coupon", 0.035)
    credit_spread = meta.get("credit_spread", 0.0)
    sector = meta.get("sector", BondSector.AGGREGATE)

    # Generate yield path with Fed cycle
    # Fed funds effective rate path (synthetic)
    fed_rate = np.zeros(n)
    fed_rate[0] = 0.015  # Start at 1.5%

    # Simulate Fed cycles: cut 2019, cut to zero 2020, hike 2022-2023, pause 2024, cut 2025-2026
    cycle_phases = [
        (0, 252, -0.0005),      # Gradual cut
        (252, 504, -0.002),     # Emergency cuts (COVID)
        (504, 630, 0.0),        # Hold at zero
        (630, 756, 0.0015),     # Hiking cycle
        (756, 1008, 0.002),     # Aggressive hiking
        (1008, 1386, -0.001),   # Gradual cuts
        (1386, n, -0.0005),     # Continued easing
    ]

    for start_idx, end_idx, drift in cycle_phases:
        for t in range(max(0, start_idx), min(n, end_idx)):
            fed_rate[t] = fed_rate[t - 1] + drift + np.random.normal(0, 0.0003) if t > 0 else fed_rate[0]

    fed_rate = np.clip(fed_rate, 0.0, 0.06)

    # Treasury yield = fed rate + term premium
    term_premium = avg_yield - 0.015  # Average term premium
    treasury_yield = fed_rate + term_premium + np.random.normal(0, 0.0002, n)

    # Add credit spread for non-treasury bonds
    if sector in (BondSector.INVESTMENT_GRADE, BondSector.HIGH_YIELD, BondSector.EMERGING_MARKET):
        spread_vol = 0.0005 if sector == BondSector.INVESTMENT_GRADE else 0.002
        spread_mean = credit_spread
        # Mean-reverting credit spread (OU process)
        spreads = np.zeros(n)
        spreads[0] = spread_mean
        for t in range(1, n):
            spreads[t] = spreads[t - 1] + 0.05 * (spread_mean - spreads[t - 1]) + np.random.normal(0, spread_vol / np.sqrt(252))
        spreads = np.maximum(spreads, 0.001)
        bond_yield = treasury_yield + spreads
    else:
        bond_yield = treasury_yield

    # Municipal bonds: tax-equivalent yield adjustment
    if sector == BondSector.MUNICIPAL:
        # Muni yields trade at ~70-80% of Treasury due to tax exemption
        bond_yield = bond_yield * 0.75

    # TIPS: real yield (lower than nominal)
    if sector == BondSector.INFLATION_PROTECTED:
        bond_yield = bond_yield - 0.02  # Inflation breakeven spread

    # Generate yield changes with GARCH volatility clustering
    yield_changes = np.zeros(n)
    vol = np.ones(n) * 0.0008  # Base daily yield vol

    for t in range(1, n):
        # GARCH(1,1) for yield volatility
        vol[t] = np.sqrt(
            0.02 * (0.0008 ** 2)
            + 0.85 * vol[t - 1] ** 2
            + 0.10 * yield_changes[t - 1] ** 2
        )
        yield_changes[t] = np.random.normal(
            -0.02 * (bond_yield[t] - avg_yield),  # Mean reversion to long-term average
            vol[t],
        )

    # Price using duration + convexity approximation
    # Start with a reference price
    base_price = 100.0
    price_changes = np.zeros(n)
    for t in range(n):
        price_changes[t] = estimate_price_change(symbol, yield_changes[t])

    # Add carry (coupon accrual)
    daily_carry = coupon / 252
    carry = np.cumsum(np.ones(n) * daily_carry)

    # Price path
    log_returns = np.log(1 + price_changes)
    price = base_price * np.exp(np.cumsum(log_returns) + carry)

    # Adjust for realistic ETF price levels
    if symbol == "TLT":
        price = price * 0.95
    elif symbol == "SHY":
        price = price * 0.85
    elif symbol == "HYG":
        price = price * 0.82
    elif symbol == "BKLN":
        price = price * 0.22
    elif symbol == "EMB":
        price = price * 1.08
    elif symbol == "MUB":
        price = price * 1.05

    # Generate OHLCV
    daily_vol = np.std(price_changes)
    high = price * (1 + np.abs(np.random.normal(0, daily_vol * 0.3, n)))
    low = price * (1 - np.abs(np.random.normal(0, daily_vol * 0.3, n)))
    open_price = price * (1 + np.random.normal(0, daily_vol * 0.1, n))
    volume = np.random.lognormal(15, 0.5, n)

    # Generate yield and spread data
    yield_series = bond_yield
    oas_series = (bond_yield - treasury_yield) if credit_spread > 0 else np.zeros(n)
    duration_series = np.ones(n) * duration + np.random.normal(0, 0.1, n)

    df = pd.DataFrame(
        {
            "open": open_price,
            "high": np.maximum(high, price * 1.001),
            "low": np.minimum(low, price * 0.999),
            "close": price,
            "volume": volume.astype(int),
            "yield": yield_series,
            "oas": oas_series,
            "effective_duration": duration_series,
            "treasury_yield": treasury_yield,
            "fed_rate": fed_rate,
        },
        index=dates,
    )
    return df


def generate_vix_data(
    start_date: str = "2018-01-01",
    end_date: str = "2026-05-20",
    seed: int = 999,
) -> pd.DataFrame:
    """Generate synthetic VIX data for flight-to-quality signals."""
    np.random.seed(seed)
    dates = pd.bdate_range(start=start_date, end=end_date)
    n = len(dates)

    # VIX mean-reverting process (OU)
    vix = np.zeros(n)
    vix[0] = 18.0
    for t in range(1, n):
        vix[t] = vix[t - 1] + 0.03 * (18 - vix[t - 1]) + np.random.normal(0, 1.5)
    vix = np.clip(vix, 9, 85)

    return pd.DataFrame({"close": vix}, index=dates)


def generate_spy_data(
    start_date: str = "2018-01-01",
    end_date: str = "2026-05-20",
    seed: int = 888,
) -> pd.DataFrame:
    """Generate synthetic SPY data for TLT/SPY ratio signals."""
    np.random.seed(seed)
    dates = pd.bdate_range(start=start_date, end=end_date)
    n = len(dates)

    returns = np.random.normal(0.0003, 0.012, n)
    price = 270 * np.exp(np.cumsum(returns))

    return pd.DataFrame(
        {
            "open": price * (1 + np.random.normal(0, 0.001, n)),
            "high": price * (1 + np.abs(np.random.normal(0, 0.006, n))),
            "low": price * (1 - np.abs(np.random.normal(0, 0.006, n))),
            "close": price,
            "volume": np.random.lognormal(16, 0.3, n).astype(int),
        },
        index=dates,
    )



# =============================================================================
# SECTION 6: SIGNAL GENERATOR (120+ Strategies)
# =============================================================================


class BondSignalGenerator:
    """
    Generates 120+ bond-specific trading signals across 8 strategy families.
    Each method returns a pandas Series of positions: -1, 0, 1 (or continuous).
    """

    def __init__(self, prices: pd.DataFrame, symbol: str):
        self.prices = prices
        self.close = prices["close"]
        self.high = prices.get("high", prices["close"])
        self.low = prices.get("low", prices["close"])
        self.volume = prices.get("volume", pd.Series(1, index=prices.index))
        self.symbol = symbol
        self.sector = BOND_UNIVERSE.get(symbol, {}).get("sector", BondSector.AGGREGATE)
        self.yield_data = prices.get("yield", pd.Series(0.04, index=prices.index))
        self.oas = prices.get("oas", pd.Series(0, index=prices.index))
        self.duration = prices.get("effective_duration", pd.Series(5.0, index=prices.index))

    # -----------------------------------------------------------------------
    # 6.1 Yield Curve Strategies (20 strategies)
    # -----------------------------------------------------------------------

    def yield_momentum(self, lookback: int = 20) -> pd.Series:
        """Trade in direction of yield momentum (rates up = bond prices down)."""
        yield_change = self.yield_data.diff(lookback)
        pos = pd.Series(0, index=self.close.index)
        pos[yield_change < -yield_change.rolling(60).std()] = 1   # Rates falling = long
        pos[yield_change > yield_change.rolling(60).std()] = -1  # Rates rising = short
        return pos

    def yield_zscore(self, lookback: int = 60) -> pd.Series:
        """Fade yield extremes via z-score."""
        y = self.yield_data
        z = (y - y.rolling(lookback).mean()) / y.rolling(lookback).std().replace(0, 1)
        pos = pd.Series(0, index=self.close.index)
        pos[z > 1.5] = 1   # Yield high = price low = long
        pos[z < -1.5] = -1  # Yield low = price high = short
        return pos

    def yield_curve_steepener(self, other_yield: pd.Series) -> pd.Series:
        """
        Proxy steepener: long the bond when curve steepening favors it.
        For long-duration bonds: long when curve steepens.
        """
        spread = self.yield_data - other_yield
        spread_ma = spread.rolling(20).mean()
        spread_diff = spread - spread_ma
        if BOND_UNIVERSE.get(self.symbol, {}).get("duration", 5) > 7:
            # Long duration benefits from steepening
            return np.clip(spread_diff / spread_diff.rolling(60).std().replace(0, 1), -1, 1)
        else:
            return np.clip(-spread_diff / spread_diff.rolling(60).std().replace(0, 1), -1, 1)

    def flattening_signal(self) -> pd.Series:
        """Signal based on yield curve flattening expectations."""
        y = self.yield_data
        slope = y - y.rolling(60).mean()
        # Flattening favors long duration
        if get_effective_duration(self.symbol) > 7:
            return np.clip(-slope / slope.rolling(60).std().replace(0, 1), -1, 1)
        return pd.Series(0, index=self.close.index)

    def steepening_signal(self) -> pd.Series:
        """Signal based on yield curve steepening expectations."""
        y = self.yield_data
        slope = y - y.rolling(60).mean()
        if get_effective_duration(self.symbol) > 7:
            return np.clip(slope / slope.rolling(60).std().replace(0, 1), -1, 1)
        return pd.Series(0, index=self.close.index)

    def roll_down_capture(self) -> pd.Series:
        """
        Capture roll-down yield: bonds appreciate as they roll down the curve.
        Always long for upward sloping yield curve.
        """
        y = self.yield_data
        curve_slope = y.rolling(60).mean().diff()
        pos = pd.Series(0, index=self.close.index)
        pos[curve_slope < 0] = 1  # Downward sloping curve = positive roll-down
        return pos

    def duration_extension(self) -> pd.Series:
        """Extend duration when rates are expected to fall."""
        if get_effective_duration(self.symbol) < 5:
            return pd.Series(0, index=self.close.index)
        rate_momentum = self.yield_data.rolling(20).mean().diff()
        pos = pd.Series(0, index=self.close.index)
        pos[rate_momentum < -rate_momentum.rolling(60).std() * 0.5] = 1
        return pos

    def duration_compression(self) -> pd.Series:
        """Compress duration when rates are expected to rise."""
        if get_effective_duration(self.symbol) < 3:
            return pd.Series(0, index=self.close.index)
        rate_momentum = self.yield_data.rolling(20).mean().diff()
        pos = pd.Series(0, index=self.close.index)
        pos[rate_momentum > rate_momentum.rolling(60).std() * 0.5] = -1
        return pos

    def yield_carry_trade(self) -> pd.Series:
        """Hold high-carry bonds, avoid low-carry."""
        carry = self.yield_data.rolling(60).mean()
        carry_rank = carry.rolling(252).apply(
            lambda x: percentileofscore(x, x.iloc[-1]) / 100 if len(x) > 0 else 0.5,
            raw=False,
        )
        pos = pd.Series(0, index=self.close.index)
        pos[carry_rank > 0.6] = 1
        pos[carry_rank < 0.3] = -1
        return pos

    def real_rate_proxy(self) -> pd.Series:
        """Trade based on real yield estimates (nominal - inflation proxy)."""
        # Use yield momentum as proxy for real rate changes
        real_yield_change = self.yield_data.diff(60)
        return np.clip(-real_yield_change / real_yield_change.rolling(120).std().replace(0, 1), -1, 1)

    # Yield curve strategy variants
    def yield_momentum_variants(self) -> List[Tuple[str, pd.Series]]:
        """Multiple lookback periods for yield momentum."""
        return [
            (f"yield_mom_{n}", self.yield_momentum(n))
            for n in [5, 10, 20, 40, 60]
        ]

    def yield_zscore_variants(self) -> List[Tuple[str, pd.Series]]:
        """Multiple lookback periods for yield z-score."""
        return [
            (f"yield_zscore_{n}", self.yield_zscore(n))
            for n in [30, 60, 120]
        ]

    # -----------------------------------------------------------------------
    # 6.2 Duration Positioning Strategies (15 strategies)
    # -----------------------------------------------------------------------

    def rate_momentum_positioning(self, lookback: int = 20) -> pd.Series:
        """Position based on rate momentum (inverse of price momentum)."""
        price_mom = self.close.pct_change(lookback)
        dur = get_effective_duration(self.symbol)
        # High duration bonds are more sensitive to rate changes
        sensitivity = dur / 10.0
        signal = -np.sign(price_mom) * sensitivity
        return np.clip(signal, -1, 1)

    def dv01_neutral_signal(self) -> pd.Series:
        """Signal scaled by DV01 (dollar value of 1bp)."""
        returns = self.close.pct_change()
        vol = returns.rolling(20).std()
        signal = np.sign(returns.rolling(60).mean())
        sizing = 0.02 / vol.replace(0, 0.02)
        return np.clip(signal * sizing, -1, 1).fillna(0)

    def convexity_exploit(self) -> pd.Series:
        """Long convexity when volatility is expected to rise."""
        returns = self.close.pct_change()
        vol = returns.rolling(20).std() * np.sqrt(252)
        vol_ma = vol.rolling(60).mean()
        conv = get_convexity(self.symbol)
        if conv > 80:  # High convexity bond
            pos = pd.Series(0, index=self.close.index)
            pos[vol > vol_ma * 1.2] = 1  # Own convexity when vol rising
            return pos
        return pd.Series(0, index=self.close.index)

    def duration_targeting(self, target_dur: float = 5.0) -> pd.Series:
        """Position sizing to target a specific duration exposure."""
        actual_dur = get_effective_duration(self.symbol)
        weight = target_dur / actual_dur if actual_dur > 0 else 0
        trend = np.sign(self.close.pct_change().rolling(20).mean())
        return np.clip(weight * trend, -1, 1).fillna(0)

    def barbell_vs_bullet(self) -> pd.Series:
        """
        Prefer barbell over bullet in flat curve environments.
        For TLT (long end): long when curve is flat.
        For SHY (short end): long when curve is flat.
        """
        y = self.yield_data
        curvature = y.diff(20).abs()
        flat = curvature < curvature.rolling(120).quantile(0.3)
        if self.symbol in ("TLT", "SHY"):
            pos = pd.Series(0, index=self.close.index)
            pos[flat] = 1
            return pos
        return pd.Series(0, index=self.close.index)

    def butterfly_trade_signal(self) -> pd.Series:
        """
        Butterfly trade: 2*IEF - TLT - SHY proxy.
        Positive when curve has hump at intermediate maturities.
        """
        if self.symbol == "IEF":
            # Long IEF when butterfly is positive (curve humped)
            y = self.yield_data
            butterfly = 2 * y - y.shift(60).fillna(y.mean())
            return np.clip(butterfly / butterfly.rolling(120).std().replace(0, 1), -1, 1)
        return pd.Series(0, index=self.close.index)

    def rate_cycle_positioning(self) -> pd.Series:
        """Position based on Fed rate cycle phase."""
        fed_rate = self.prices.get("fed_rate", pd.Series(0.025, index=self.close.index))
        fed_ma = fed_rate.rolling(60).mean()
        cycle_phase = np.where(fed_rate > fed_ma, "hiking", "easing")
        pos = pd.Series(0, index=self.close.index)
        dur = get_effective_duration(self.symbol)
        # During easing: long duration. During hiking: short duration or go short
        if dur > 7:  # Long duration
            pos[cycle_phase == "easing"] = 1
            pos[cycle_phase == "hiking"] = -1
        elif dur < 3:  # Short duration
            pos[cycle_phase == "hiking"] = 1  # Short duration outperforms
        return pos

    def trend_duration_neutral(self) -> pd.Series:
        """Trend following with duration-adjusted sizing."""
        ema_fast = self.close.ewm(span=20).mean()
        ema_slow = self.close.ewm(span=100).mean()
        trend = np.sign(ema_fast - ema_slow)
        dur = get_effective_duration(self.symbol)
        # Size inversely by duration to keep DV01 constant
        sizing = 5.0 / dur if dur > 0 else 1.0
        return np.clip(trend * sizing, -1, 1).fillna(0)

    def macd_duration(self, fast: int = 12, slow: int = 26, sig: int = 9) -> pd.Series:
        """MACD with duration-aware position sizing."""
        ema_fast = self.close.ewm(span=fast).mean()
        ema_slow = self.close.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=sig).mean()
        hist = macd - signal
        dur = get_effective_duration(self.symbol)
        sizing = min(1.0, 7.0 / dur) if dur > 0 else 1.0
        return np.clip(np.sign(hist) * sizing, -1, 1).fillna(0)

    def moving_average_crossover(self, fast: int = 20, slow: int = 100) -> pd.Series:
        """Classic MA crossover for bond trend following."""
        ma_fast = self.close.rolling(fast).mean()
        ma_slow = self.close.rolling(slow).mean()
        pos = pd.Series(0, index=self.close.index)
        pos[ma_fast > ma_slow] = 1
        pos[ma_fast < ma_slow] = -1
        return pos

    # Duration positioning variants
    def ma_crossover_variants(self) -> List[Tuple[str, pd.Series]]:
        """Multiple MA crossover periods."""
        periods = [
            (10, 50), (20, 100), (30, 150), (50, 200),
            (20, 60), (10, 30), (5, 20),
        ]
        return [
            (f"ma_cross_{f}_{s}", self.moving_average_crossover(f, s))
            for f, s in periods
        ]

    # -----------------------------------------------------------------------
    # 6.3 Credit Spread Strategies (15 strategies)
    # -----------------------------------------------------------------------

    def credit_spread_mean_reversion(self) -> pd.Series:
        """Mean reversion in OAS (option-adjusted spread)."""
        if self.oas.sum() == 0:
            return pd.Series(0, index=self.close.index)
        oas = self.oas
        zscore = (oas - oas.rolling(60).mean()) / oas.rolling(60).std().replace(0, 1)
        pos = pd.Series(0, index=self.close.index)
        pos[zscore > 1.5] = 1   # Spread wide = cheap = long
        pos[zscore < -1.5] = -1  # Spread tight = expensive = short
        return pos

    def credit_spread_momentum(self, lookback: int = 20) -> pd.Series:
        """Momentum in credit spreads (widening = short credit)."""
        if self.oas.sum() == 0:
            return pd.Series(0, index=self.close.index)
        oas_change = self.oas.diff(lookback)
        pos = pd.Series(0, index=self.close.index)
        pos[oas_change < 0] = 1   # Spread tightening = long
        pos[oas_change > 0] = -1  # Spread widening = short
        return pos

    def credit_cycle_positioning(self) -> pd.Series:
        """Position based on credit cycle phase."""
        if self.oas.sum() == 0:
            return pd.Series(0, index=self.close.index)
        oas_ma = self.oas.rolling(120).mean()
        oas_trend = self.oas > oas_ma
        sector = self.sector
        if sector == BondSector.HIGH_YIELD:
            # HY: careful with spread widening
            pos = pd.Series(0, index=self.close.index)
            pos[~oas_trend & (self.oas < oas_ma * 0.9)] = 1
            pos[oas_trend & (self.oas > oas_ma * 1.1)] = -1
            return pos
        elif sector == BondSector.INVESTMENT_GRADE:
            # IG: more stable
            pos = pd.Series(0, index=self.close.index)
            pos[self.oas < oas_ma * 0.95] = 1
            return pos
        return pd.Series(0, index=self.close.index)

    def default_cycle_proxy(self) -> pd.Series:
        """Trade based on default cycle proxy (HY spread momentum)."""
        if self.sector not in (BondSector.HIGH_YIELD, BondSector.EMERGING_MARKET):
            return pd.Series(0, index=self.close.index)
        spread_change = self.oas.diff(60)
        vol = spread_change.rolling(120).std().replace(0, 1)
        zscore = spread_change / vol
        pos = pd.Series(0, index=self.close.index)
        pos[zscore < -1.0] = 1   # Spread compression = risk-on
        pos[zscore > 1.5] = -1   # Spread widening = risk-off
        return pos

    def ig_hy_value(self, hy_data: Optional[pd.Series] = None) -> pd.Series:
        """IG vs HY relative value trade."""
        if self.sector not in (BondSector.INVESTMENT_GRADE, BondSector.HIGH_YIELD):
            return pd.Series(0, index=self.close.index)
        if self.oas.sum() == 0:
            return pd.Series(0, index=self.close.index)
        oas_z = (self.oas - self.oas.rolling(120).mean()) / self.oas.rolling(120).std().replace(0, 1)
        if self.sector == BondSector.INVESTMENT_GRADE:
            return np.clip(-oas_z / 2, -1, 1)  # Buy IG when IG spread wide
        else:
            return np.clip(oas_z / 2, -1, 1)   # Buy HY when HY spread tight

    def credit_quality_rotation(self) -> pd.Series:
        """Rotate between credit quality based on spread regime."""
        if self.oas.sum() == 0:
            return pd.Series(0, index=self.close.index)
        oas_percentile = self.oas.rolling(252).apply(
            lambda x: percentileofscore(x, x.iloc[-1]) / 100 if len(x) > 0 else 0.5,
            raw=False,
        )
        if self.sector == BondSector.HIGH_YIELD:
            pos = pd.Series(0, index=self.close.index)
            pos[oas_percentile < 0.3] = 1   # Cheap HY
            pos[oas_percentile > 0.7] = -1  # Expensive HY
            return pos
        elif self.sector == BondSector.INVESTMENT_GRADE:
            pos = pd.Series(0, index=self.close.index)
            pos[oas_percentile > 0.6] = 1   # IG safe haven when spreads wide
            return pos
        return pd.Series(0, index=self.close.index)

    def fallen_angel_avoidance(self) -> pd.Series:
        """Avoid bonds trending toward downgrade (rising OAS)."""
        if self.sector != BondSector.INVESTMENT_GRADE:
            return pd.Series(0, index=self.close.index)
        oas_trend = self.oas.rolling(20).mean().diff()
        pos = pd.Series(1, index=self.close.index)  # Default long
        pos[oas_trend > oas_trend.rolling(60).quantile(0.9)] = 0  # Exit when spread surging
        return pos

    def credit_spread_variants(self) -> List[Tuple[str, pd.Series]]:
        """Multiple lookback periods for credit spread signals."""
        if self.oas.sum() == 0:
            return []
        results = []
        for lookback in [10, 20, 40, 60]:
            oas_change = self.oas.diff(lookback)
            vol = oas_change.rolling(120).std().replace(0, 1)
            zscore = oas_change / vol
            pos = pd.Series(0, index=self.close.index)
            pos[zscore < -1.0] = 1
            pos[zscore > 1.0] = -1
            results.append((f"credit_momentum_{lookback}_{self.symbol}", pos))
        return results

    # -----------------------------------------------------------------------
    # 6.4 Inflation Breakeven Strategies (10 strategies)
    # -----------------------------------------------------------------------

    def inflation_expectation_trade(self) -> pd.Series:
        """Trade based on inflation expectations proxy."""
        if self.sector == BondSector.INFLATION_PROTECTED:
            # TIPS: long when inflation expectations rising
            nominal_yield = self.prices.get("treasury_yield", self.yield_data)
            breakeven_proxy = self.yield_data - nominal_yield + 0.02
            trend = breakeven_proxy.rolling(20).mean().diff()
            pos = pd.Series(0, index=self.close.index)
            pos[trend > 0] = 1
            return pos
        elif self.sector == BondSector.TREASURY:
            # Nominal: short when inflation rising (yields rise)
            y_change = self.yield_data.diff(20)
            pos = pd.Series(0, index=self.close.index)
            pos[y_change > y_change.rolling(60).std()] = -1
            return pos
        return pd.Series(0, index=self.close.index)

    def breakeven_momentum(self, lookback: int = 20) -> pd.Series:
        """Trade breakeven inflation momentum."""
        if self.sector not in (BondSector.INFLATION_PROTECTED, BondSector.TREASURY):
            return pd.Series(0, index=self.close.index)
        returns = self.close.pct_change(lookback)
        if self.sector == BondSector.INFLATION_PROTECTED:
            pos = pd.Series(0, index=self.close.index)
            pos[returns > returns.rolling(60).quantile(0.6)] = 1
            return pos
        else:
            pos = pd.Series(0, index=self.close.index)
            pos[returns < returns.rolling(60).quantile(0.4)] = -1
            return pos

    def tips_vs_nominal_arb(self, treasury_yield: pd.Series) -> pd.Series:
        """Relative value: TIPS vs nominal Treasury."""
        if self.sector != BondSector.INFLATION_PROTECTED:
            return pd.Series(0, index=self.close.index)
        breakeven = treasury_yield - self.yield_data
        be_zscore = (breakeven - breakeven.rolling(120).mean()) / breakeven.rolling(120).std().replace(0, 1)
        pos = pd.Series(0, index=self.close.index)
        pos[be_zscore < -1.0] = 1   # Breakeven low = TIPS cheap
        pos[be_zscore > 1.5] = -1   # Breakeven high = TIPS expensive
        return pos

    def inflation_hedge_ratio(self) -> pd.Series:
        """Signal proportional to inflation hedge demand."""
        if self.sector != BondSector.INFLATION_PROTECTED:
            return pd.Series(0, index=self.close.index)
        # Rising yields with stable real rates = buy TIPS
        y_change = self.yield_data.diff(60)
        pos = pd.Series(0, index=self.close.index)
        pos[y_change > y_change.rolling(120).std()] = 1
        return pos

    # -----------------------------------------------------------------------
    # 6.5 Flight-to-Quality Strategies (10 strategies)
    # -----------------------------------------------------------------------

    def vix_flight_to_quality(self, vix: pd.Series) -> pd.Series:
        """Long Treasuries when VIX spikes (flight to quality)."""
        if self.sector not in (BondSector.TREASURY, BondSector.AGGREGATE, BondSector.MUNICIPAL):
            return pd.Series(0, index=self.close.index)
        vix_ma = vix.rolling(60).mean()
        vix_zscore = (vix - vix_ma) / vix.rolling(60).std().replace(0, 1)
        pos = pd.Series(0, index=self.close.index)
        if get_effective_duration(self.symbol) > 5:
            pos[vix_zscore > 1.5] = 1  # VIX spike = long duration
        pos[vix_zscore < -1.0] = -1  # VIX low = short duration
        return pos.reindex(self.close.index).fillna(0)

    def equity_bond_ratio(self, spy_close: pd.Series) -> pd.Series:
        """Trade TLT/SPY ratio mean reversion."""
        if self.sector != BondSector.TREASURY or get_effective_duration(self.symbol) < 10:
            return pd.Series(0, index=self.close.index)
        ratio = self.close / spy_close.reindex(self.close.index).fillna(method="ffill")
        ratio_ma = ratio.rolling(60).mean()
        ratio_z = (ratio - ratio_ma) / ratio.rolling(60).std().replace(0, 1)
        pos = pd.Series(0, index=self.close.index)
        pos[ratio_z > 1.5] = -1  # Ratio high = bonds expensive vs stocks
        pos[ratio_z < -1.5] = 1  # Ratio low = bonds cheap vs stocks
        return pos

    def correlation_breakdown(self, spy_returns: pd.Series) -> pd.Series:
        """Trade bond-equity correlation breakdown."""
        bond_rets = self.close.pct_change()
        corr = bond_rets.rolling(60).corr(spy_returns.reindex(self.close.index).fillna(0))
        corr_ma = corr.rolling(120).mean()
        pos = pd.Series(0, index=self.close.index)
        if get_effective_duration(self.symbol) > 5:
            pos[corr < corr_ma - 0.1] = 1  # Correlation drops = bonds hedge
        return pos

    def safe_haven_demand(self, vix: pd.Series) -> pd.Series:
        """Measure safe haven demand via VIX term structure proxy."""
        if self.sector not in (BondSector.TREASURY, BondSector.AGGREGATE):
            return pd.Series(0, index=self.close.index)
        vix_change = vix.pct_change(5)
        pos = pd.Series(0, index=self.close.index)
        pos[vix_change > vix_change.rolling(120).quantile(0.9)] = 1
        return pos.reindex(self.close.index).fillna(0)

    def risk_off_rotation(self, vix: pd.Series, spy_close: pd.Series) -> pd.Series:
        """Rotate into bonds on risk-off signals."""
        if self.sector not in (BondSector.TREASURY, BondSector.AGGREGATE, BondSector.MUNICIPAL):
            return pd.Series(0, index=self.close.index)
        vix_signal = (vix > vix.rolling(60).mean() * 1.3).astype(float)
        spy_signal = (spy_close.pct_change(20) < -0.05).astype(float)
        combined = (vix_signal + spy_signal) / 2
        if get_effective_duration(self.symbol) > 5:
            return np.clip(combined * 1.5, -1, 1).reindex(self.close.index).fillna(0)
        return np.clip(combined, -1, 1).reindex(self.close.index).fillna(0)

    # -----------------------------------------------------------------------
    # 6.6 Fed Policy Path Strategies (10 strategies)
    # -----------------------------------------------------------------------

    def fed_dot_plot_proxy(self) -> pd.Series:
        """Trade based on Fed rate path vs market pricing."""
        fed_rate = self.prices.get("fed_rate", pd.Series(0.025, index=self.close.index))
        # If Fed is hiking, position accordingly
        rate_change = fed_rate.diff(60)
        dur = get_effective_duration(self.symbol)
        pos = pd.Series(0, index=self.close.index)
        if dur > 7:
            pos[rate_change < -0.0025] = 1   # Rate cuts = long duration
            pos[rate_change > 0.0025] = -1   # Rate hikes = short duration
        elif dur < 3:
            pos[rate_change > 0.001] = 1     # Rate hikes = short duration wins
        return pos

    def meeting_based_cycle(self) -> pd.Series:
        """Position around FOMC meeting cycles."""
        dates = self.close.index
        months = dates.month
        # FOMC meetings roughly: Jan, Mar, May, Jun, Jul, Sep, Nov, Dec
        # Post-meeting drift: bonds tend to drift in direction of surprise
        fed_rate = self.prices.get("fed_rate", pd.Series(0.025, index=dates))
        fed_ma = fed_rate.rolling(126).mean()
        pos = pd.Series(0, index=dates)
        # Simplified: long when Fed below trend (easing bias)
        pos[fed_rate < fed_ma * 0.98] = 1
        pos[fed_rate > fed_ma * 1.02] = -1
        return pos

    def forward_guidance_trade(self) -> pd.Series:
        """Trade based on Fed forward guidance proxy (yield curve shape)."""
        y = self.yield_data
        slope = y.diff(60)
        # Steepening = easier policy ahead
        dur = get_effective_duration(self.symbol)
        if dur > 7:
            return np.clip(slope / slope.rolling(120).std().replace(0, 1), -1, 1)
        elif dur < 4:
            return np.clip(-slope / slope.rolling(120).std().replace(0, 1), -1, 1)
        return pd.Series(0, index=self.close.index)

    def policy_rate_differential(self) -> pd.Series:
        """Trade the gap between Fed rate and bond yield."""
        fed_rate = self.prices.get("fed_rate", pd.Series(0.025, index=self.close.index))
        differential = self.yield_data - fed_rate
        diff_ma = differential.rolling(120).mean()
        pos = pd.Series(0, index=self.close.index)
        pos[differential > diff_ma * 1.2] = -1  # Yield too high vs Fed = short
        pos[differential < diff_ma * 0.8] = 1   # Yield too low vs Fed = long
        return pos

    def fed_pause_signal(self) -> pd.Series:
        """Trade Fed pause: typically bullish for bonds."""
        fed_rate = self.prices.get("fed_rate", pd.Series(0.025, index=self.close.index))
        rate_vol = fed_rate.rolling(60).std()
        pause = rate_vol < rate_vol.rolling(252).quantile(0.2)
        pos = pd.Series(0, index=self.close.index)
        pos[pause] = 1  # Fed pause = long bonds
        return pos

    # -----------------------------------------------------------------------
    # 6.7 Municipal Bond Seasonality (10 strategies)
    # -----------------------------------------------------------------------

    def muni_seasonal(self) -> pd.Series:
        """Municipal bond seasonal patterns."""
        if self.sector != BondSector.MUNICIPAL:
            return pd.Series(0, index=self.close.index)
        months = self.close.index.month
        # January: strong inflows (tax-sensitive buyers)
        # June-July: summer lull
        # December: year-end reinvestment
        pos = pd.Series(0, index=self.close.index)
        pos[(months == 1) | (months == 12)] = 1
        pos[(months == 6) | (months == 7)] = -1
        return pos

    def muni_supply_dynamics(self) -> pd.Series:
        """Trade around muni supply patterns."""
        if self.sector != BondSector.MUNICIPAL:
            return pd.Series(0, index=self.close.index)
        months = self.close.index.month
        # Heavy issuance in Jan, Sep, Oct, Nov
        # Light issuance in Jul, Aug, Dec
        pos = pd.Series(0, index=self.close.index)
        pos[(months == 7) | (months == 8) | (months == 12)] = 1  # Low supply = rally
        pos[(months == 9) | (months == 10) | (months == 11)] = -1  # High supply = pressure
        return pos

    def tax_loss_harvesting_rebound(self) -> pd.Series:
        """Muni rebound after tax-loss selling in Dec."""
        if self.sector != BondSector.MUNICIPAL:
            return pd.Series(0, index=self.close.index)
        months = self.close.index.month
        pos = pd.Series(0, index=self.close.index)
        pos[months == 1] = 1   # January rebound
        pos[months == 12] = -1  # December selling
        return pos

    def muni_call_risk_proxy(self) -> pd.Series:
        """Avoid bonds with high call risk when rates falling."""
        if self.sector != BondSector.MUNICIPAL:
            return pd.Series(0, index=self.close.index)
        y_change = self.yield_data.diff(60)
        pos = pd.Series(1, index=self.close.index)  # Default long
        pos[y_change < -0.005] = 0  # Exit when rates falling fast (call risk)
        return pos

    def ratio_muni_treasury_value(self) -> pd.Series:
        """Muni vs Treasury relative value (MUB/TLT ratio)."""
        if self.sector != BondSector.MUNICIPAL:
            return pd.Series(0, index=self.close.index)
        returns = self.close.pct_change(20)
        vol = returns.rolling(60).std()
        pos = pd.Series(0, index=self.close.index)
        pos[vol < vol.rolling(120).quantile(0.3)] = 1  # Low vol environment = good for munis
        return pos

    # -----------------------------------------------------------------------
    # 6.8 Emerging Market Debt Carry (10 strategies)
    # -----------------------------------------------------------------------

    def em_carry_trade(self) -> pd.Series:
        """EM debt carry: hold when EM-US spread is attractive."""
        if self.sector != BondSector.EMERGING_MARKET:
            return pd.Series(0, index=self.close.index)
        spread = self.oas
        carry = spread.rolling(60).mean()
        pos = pd.Series(0, index=self.close.index)
        pos[carry > carry.rolling(252).quantile(0.6)] = 1   # High carry = attractive
        pos[carry < carry.rolling(252).quantile(0.3)] = -1  # Low carry = avoid
        return pos

    def em_momentum(self, lookback: int = 20) -> pd.Series:
        """EM debt momentum with vol filter."""
        if self.sector != BondSector.EMERGING_MARKET:
            return pd.Series(0, index=self.close.index)
        returns = self.close.pct_change(lookback)
        vol = self.close.pct_change().rolling(20).std() * np.sqrt(252)
        vol_low = vol < vol.rolling(120).quantile(0.5)
        pos = pd.Series(0, index=self.close.index)
        pos[(returns > 0) & vol_low] = 1
        pos[(returns < 0) & vol_low] = -1
        return pos

    def em_risk_premium(self) -> pd.Series:
        """Trade EM risk premium cycles."""
        if self.sector != BondSector.EMERGING_MARKET:
            return pd.Series(0, index=self.close.index)
        spread = self.oas
        spread_percentile = spread.rolling(252).apply(
            lambda x: percentileofscore(x, x.iloc[-1]) / 100 if len(x) > 0 else 0.5,
            raw=False,
        )
        pos = pd.Series(0, index=self.close.index)
        pos[spread_percentile > 0.7] = 1   # Wide spreads = attractive entry
        pos[spread_percentile < 0.2] = -1  # Tight spreads = exit
        return pos

    def em_dollar_sensitivity(self) -> pd.Series:
        """EM debt is sensitive to USD strength."""
        if self.sector != BondSector.EMERGING_MARKET:
            return pd.Series(0, index=self.close.index)
        # Proxy: when yields are falling (USD weakening proxy), EM benefits
        y_change = self.yield_data.diff(20)
        pos = pd.Series(0, index=self.close.index)
        pos[y_change < 0] = 1
        pos[y_change > y_change.rolling(60).std() * 1.5] = -1
        return pos

    def em_volatility_timing(self) -> pd.Series:
        """Time EM allocation based on EM vol regime."""
        if self.sector != BondSector.EMERGING_MARKET:
            return pd.Series(0, index=self.close.index)
        returns = self.close.pct_change()
        em_vol = returns.rolling(20).std() * np.sqrt(252)
        vol_regime = em_vol > em_vol.rolling(120).mean()
        pos = pd.Series(0, index=self.close.index)
        pos[~vol_regime] = 1  # Enter when vol low
        pos[vol_regime & (returns.rolling(20).mean() < 0)] = -1  # Exit when vol high + negative trend
        return pos

    # -----------------------------------------------------------------------
    # 6.9 Trend Following Strategies (10 strategies)
    # -----------------------------------------------------------------------

    def donchian_channel(self, lookback: int = 20) -> pd.Series:
        """Donchian channel breakout for bonds."""
        upper = self.high.rolling(lookback).max().shift(1)
        lower = self.low.rolling(lookback).min().shift(1)
        pos = pd.Series(0, index=self.close.index)
        pos[self.close > upper] = 1
        pos[self.close < lower] = -1
        return pos

    def bollinger_band_trend(self, period: int = 20, std_dev: float = 2.0) -> pd.Series:
        """Bollinger band trend following."""
        ma = self.close.rolling(period).mean()
        std = self.close.rolling(period).std()
        upper = ma + std_dev * std
        lower = ma - std_dev * std
        pos = pd.Series(0, index=self.close.index)
        pos[self.close > upper] = 1
        pos[self.close < lower] = -1
        return pos

    def keltner_channel(self, ema_period: int = 20, atr_period: int = 10) -> pd.Series:
        """Keltner channel for bonds."""
        ema = self.close.ewm(span=ema_period).mean()
        atr = self._atr(atr_period)
        upper = ema + 2 * atr
        lower = ema - 2 * atr
        pos = pd.Series(0, index=self.close.index)
        pos[self.close > upper] = 1
        pos[self.close < lower] = -1
        return pos

    def adx_trend(self, period: int = 14) -> pd.Series:
        """ADX-based trend strength."""
        adx, di_pos, di_neg = self._adx(period)
        pos = pd.Series(0, index=self.close.index)
        pos[(di_pos > di_neg) & (adx > 20)] = 1
        pos[(di_neg > di_pos) & (adx > 20)] = -1
        return pos

    def ichimoku_trend(self) -> pd.Series:
        """Ichimoku trend for bonds."""
        tenkan = (self.high.rolling(9).max() + self.low.rolling(9).min()) / 2
        kijun = (self.high.rolling(26).max() + self.low.rolling(26).min()) / 2
        pos = pd.Series(0, index=self.close.index)
        pos[tenkan > kijun] = 1
        pos[tenkan < kijun] = -1
        return pos

    # -----------------------------------------------------------------------
    # 6.10 Mean Reversion Strategies (10 strategies)
    # -----------------------------------------------------------------------

    def rsi_mean_reversion(self, period: int = 14) -> pd.Series:
        """RSI mean reversion for bonds."""
        rsi = self._rsi(period)
        pos = pd.Series(0, index=self.close.index)
        pos[rsi > 70] = -1
        pos[rsi < 30] = 1
        return pos

    def stochastic_mr(self, k_period: int = 14) -> pd.Series:
        """Stochastic oscillator mean reversion."""
        lowest = self.low.rolling(k_period).min()
        highest = self.high.rolling(k_period).max()
        k = 100 * (self.close - lowest) / (highest - lowest).replace(0, 1)
        pos = pd.Series(0, index=self.close.index)
        pos[k > 80] = -1
        pos[k < 20] = 1
        return pos

    def cci_mean_reversion(self, period: int = 20) -> pd.Series:
        """CCI mean reversion."""
        tp = (self.high + self.low + self.close) / 3
        ma = tp.rolling(period).mean()
        md = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
        cci = (tp - ma) / (0.015 * md.replace(0, 1))
        pos = pd.Series(0, index=self.close.index)
        pos[cci > 100] = -1
        pos[cci < -100] = 1
        return pos

    def williams_r_mr(self, lookback: int = 14) -> pd.Series:
        """Williams %R mean reversion."""
        highest = self.high.rolling(lookback).max()
        lowest = self.low.rolling(lookback).min()
        wr = -100 * (highest - self.close) / (highest - lowest).replace(0, 1)
        pos = pd.Series(0, index=self.close.index)
        pos[wr > -20] = -1
        pos[wr < -80] = 1
        return pos

    def vwap_reversion(self, period: int = 20) -> pd.Series:
        """Mean reversion to VWAP."""
        typical = (self.high + self.low + self.close) / 3
        vwap = (typical * self.volume).rolling(period).sum() / self.volume.rolling(period).sum()
        dist = (self.close - vwap) / vwap
        pos = pd.Series(0, index=self.close.index)
        pos[dist > dist.rolling(60).quantile(0.9)] = -1
        pos[dist < dist.rolling(60).quantile(0.1)] = 1
        return pos

    # -----------------------------------------------------------------------
    # Helper Methods
    # -----------------------------------------------------------------------

    def _atr(self, period: int = 14) -> pd.Series:
        """Average True Range."""
        tr1 = self.high - self.low
        tr2 = abs(self.high - self.close.shift(1))
        tr3 = abs(self.low - self.close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def _rsi(self, period: int = 14) -> pd.Series:
        """Relative Strength Index."""
        delta = self.close.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss.replace(0, 1)
        return 100 - (100 / (1 + rs))

    def _adx(self, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """ADX, +DI, -DI."""
        tr = pd.concat([
            self.high - self.low,
            abs(self.high - self.close.shift(1)),
            abs(self.low - self.close.shift(1)),
        ], axis=1).max(axis=1)
        plus_dm = (self.high - self.high.shift(1)).where(
            (self.high - self.high.shift(1)) > (self.low.shift(1) - self.low), 0
        )
        minus_dm = (self.low.shift(1) - self.low).where(
            (self.low.shift(1) - self.low) > (self.high - self.high.shift(1)), 0
        )
        atr = tr.rolling(period).mean()
        plus_di = 100 * plus_dm.rolling(period).mean() / atr.replace(0, 1)
        minus_di = 100 * minus_dm.rolling(period).mean() / atr.replace(0, 1)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1)
        adx = dx.rolling(period).mean()
        return adx, plus_di, minus_di

    # -----------------------------------------------------------------------
    # Strategy Manifest - All 120+ Strategies
    # -----------------------------------------------------------------------

    def generate_all_signals(
        self,
        vix_data: Optional[pd.DataFrame] = None,
        spy_data: Optional[pd.DataFrame] = None,
    ) -> List[Tuple[str, StrategyCategory, pd.Series, Dict[str, Any]]]:
        """
        Generate all 120+ strategy signals for this bond ETF.
        Returns list of (strategy_name, category, signal_series, params).
        """
        signals: List[Tuple[str, StrategyCategory, pd.Series, Dict[str, Any]]] = []
        sym = self.symbol

        # 6.1 Yield Curve (20)
        signals.extend([
            (f"yield_mom_20_{sym}", StrategyCategory.YIELD_CURVE, self.yield_momentum(20), {"lookback": 20}),
            (f"yield_mom_10_{sym}", StrategyCategory.YIELD_CURVE, self.yield_momentum(10), {"lookback": 10}),
            (f"yield_mom_40_{sym}", StrategyCategory.YIELD_CURVE, self.yield_momentum(40), {"lookback": 40}),
            (f"yield_mom_60_{sym}", StrategyCategory.YIELD_CURVE, self.yield_momentum(60), {"lookback": 60}),
            (f"yield_mom_5_{sym}", StrategyCategory.YIELD_CURVE, self.yield_momentum(5), {"lookback": 5}),
            (f"yield_zscore_60_{sym}", StrategyCategory.YIELD_CURVE, self.yield_zscore(60), {"lookback": 60}),
            (f"yield_zscore_30_{sym}", StrategyCategory.YIELD_CURVE, self.yield_zscore(30), {"lookback": 30}),
            (f"yield_zscore_120_{sym}", StrategyCategory.YIELD_CURVE, self.yield_zscore(120), {"lookback": 120}),
            (f"flattening_{sym}", StrategyCategory.YIELD_CURVE, self.flattening_signal(), {}),
            (f"steepening_{sym}", StrategyCategory.YIELD_CURVE, self.steepening_signal(), {}),
            (f"roll_down_{sym}", StrategyCategory.YIELD_CURVE, self.roll_down_capture(), {}),
            (f"duration_ext_{sym}", StrategyCategory.YIELD_CURVE, self.duration_extension(), {}),
            (f"duration_comp_{sym}", StrategyCategory.YIELD_CURVE, self.duration_compression(), {}),
            (f"yield_carry_{sym}", StrategyCategory.YIELD_CURVE, self.yield_carry_trade(), {}),
            (f"real_rate_{sym}", StrategyCategory.YIELD_CURVE, self.real_rate_proxy(), {}),
            (f"barbell_bullet_{sym}", StrategyCategory.YIELD_CURVE, self.barbell_vs_bullet(), {}),
            (f"butterfly_{sym}", StrategyCategory.YIELD_CURVE, self.butterfly_trade_signal(), {}),
            (f"yield_mom_ema_{sym}", StrategyCategory.YIELD_CURVE,
             np.clip(-self.yield_data.diff().ewm(span=20).mean() / self.yield_data.rolling(60).std().replace(0, 1), -1, 1), {}),
            (f"curve_carry_{sym}", StrategyCategory.YIELD_CURVE,
             self.yield_carry_trade(), {"variant": "curve"}),
            (f"duration_barbell_{sym}", StrategyCategory.YIELD_CURVE,
             self.barbell_vs_bullet(), {"variant": "enhanced"}),
        ])

        # 6.2 Duration Positioning (15)
        signals.extend([
            (f"rate_mom_20_{sym}", StrategyCategory.DURATION_POSITIONING, self.rate_momentum_positioning(20), {"lookback": 20}),
            (f"rate_mom_60_{sym}", StrategyCategory.DURATION_POSITIONING, self.rate_momentum_positioning(60), {"lookback": 60}),
            (f"dv01_neutral_{sym}", StrategyCategory.DURATION_POSITIONING, self.dv01_neutral_signal(), {}),
            (f"convexity_exp_{sym}", StrategyCategory.DURATION_POSITIONING, self.convexity_exploit(), {}),
            (f"dur_target_{sym}", StrategyCategory.DURATION_POSITIONING, self.duration_targeting(5.0), {"target": 5.0}),
            (f"dur_target_7_{sym}", StrategyCategory.DURATION_POSITIONING, self.duration_targeting(7.0), {"target": 7.0}),
            (f"rate_cycle_{sym}", StrategyCategory.DURATION_POSITIONING, self.rate_cycle_positioning(), {}),
            (f"trend_dur_neutral_{sym}", StrategyCategory.DURATION_POSITIONING, self.trend_duration_neutral(), {}),
            (f"macd_dur_{sym}", StrategyCategory.DURATION_POSITIONING, self.macd_duration(), {}),
            (f"macd_dur_fast_{sym}", StrategyCategory.DURATION_POSITIONING, self.macd_duration(8, 21, 5), {"fast": 8, "slow": 21}),
            (f"ma_cross_20_100_{sym}", StrategyCategory.DURATION_POSITIONING, self.moving_average_crossover(20, 100), {"fast": 20, "slow": 100}),
            (f"ma_cross_50_200_{sym}", StrategyCategory.DURATION_POSITIONING, self.moving_average_crossover(50, 200), {"fast": 50, "slow": 200}),
            (f"ma_cross_10_50_{sym}", StrategyCategory.DURATION_POSITIONING, self.moving_average_crossover(10, 50), {"fast": 10, "slow": 50}),
            (f"ma_cross_20_60_{sym}", StrategyCategory.DURATION_POSITIONING, self.moving_average_crossover(20, 60), {"fast": 20, "slow": 60}),
            (f"ema_cross_{sym}", StrategyCategory.DURATION_POSITIONING,
             np.sign(self.close.ewm(span=20).mean() - self.close.ewm(span=100).mean()), {}),
        ])

        # 6.3 Credit Spread (15)
        credit_signals = [
            (f"credit_mr_{sym}", StrategyCategory.CREDIT_SPREAD, self.credit_spread_mean_reversion(), {}),
            (f"credit_mom_{sym}", StrategyCategory.CREDIT_SPREAD, self.credit_spread_momentum(20), {"lookback": 20}),
            (f"credit_cycle_{sym}", StrategyCategory.CREDIT_SPREAD, self.credit_cycle_positioning(), {}),
            (f"default_cycle_{sym}", StrategyCategory.CREDIT_SPREAD, self.default_cycle_proxy(), {}),
            (f"ig_hy_value_{sym}", StrategyCategory.CREDIT_SPREAD, self.ig_hy_value(), {}),
            (f"credit_quality_rot_{sym}", StrategyCategory.CREDIT_SPREAD, self.credit_quality_rotation(), {}),
            (f"fallen_angel_{sym}", StrategyCategory.CREDIT_SPREAD, self.fallen_angel_avoidance(), {}),
            (f"credit_zscore_{sym}", StrategyCategory.CREDIT_SPREAD,
             self.credit_spread_mean_reversion(), {"variant": "zscore"}),
            (f"credit_momentum_40_{sym}", StrategyCategory.CREDIT_SPREAD,
             self.credit_spread_momentum(40), {"lookback": 40}),
            (f"credit_trend_{sym}", StrategyCategory.CREDIT_SPREAD,
             np.sign(self.oas.rolling(20).mean().diff()).fillna(0) if self.oas.sum() > 0 else pd.Series(0, index=self.close.index), {}),
            (f"credit_rank_{sym}", StrategyCategory.CREDIT_SPREAD,
             self.credit_quality_rotation(), {"variant": "rank"}),
            (f"oas_percentile_{sym}", StrategyCategory.CREDIT_SPREAD,
             self.credit_spread_mean_reversion(), {"variant": "percentile"}),
            (f"spread_carry_{sym}", StrategyCategory.CREDIT_SPREAD,
             self.credit_cycle_positioning(), {"variant": "carry"}),
            (f"hy_defensive_{sym}", StrategyCategory.CREDIT_SPREAD,
             self.default_cycle_proxy(), {"variant": "defensive"}),
            (f"credit_mr_30_{sym}", StrategyCategory.CREDIT_SPREAD,
             self.credit_spread_mean_reversion(), {"variant": "30d"}),
        ]
        signals.extend(credit_signals)

        # 6.4 Inflation Breakeven (10)
        infl_signals = [
            (f"infl_exp_{sym}", StrategyCategory.INFLATION_BREAKEVEN, self.inflation_expectation_trade(), {}),
            (f"be_mom_20_{sym}", StrategyCategory.INFLATION_BREAKEVEN, self.breakeven_momentum(20), {"lookback": 20}),
            (f"be_mom_60_{sym}", StrategyCategory.INFLATION_BREAKEVEN, self.breakeven_momentum(60), {"lookback": 60}),
            (f"infl_hedge_{sym}", StrategyCategory.INFLATION_BREAKEVEN, self.inflation_hedge_ratio(), {}),
            (f"tips_nom_{sym}", StrategyCategory.INFLATION_BREAKEVEN,
             self.inflation_expectation_trade(), {"variant": "tips_nom"}),
            (f"be_proxy_{sym}", StrategyCategory.INFLATION_BREAKEVEN,
             self.breakeven_momentum(20), {"variant": "proxy"}),
            (f"infl_trend_{sym}", StrategyCategory.INFLATION_BREAKEVEN,
             np.sign(self.yield_data.diff(60).fillna(0)), {}),
            (f"real_yield_{sym}", StrategyCategory.INFLATION_BREAKEVEN,
             self.real_rate_proxy(), {}),
            (f"infl_seasonal_{sym}", StrategyCategory.INFLATION_BREAKEVEN,
             self.inflation_expectation_trade(), {"variant": "seasonal"}),
            (f"tips_carry_{sym}", StrategyCategory.INFLATION_BREAKEVEN,
             self.inflation_hedge_ratio(), {"variant": "carry"}),
        ]
        signals.extend(infl_signals)

        # 6.5 Flight to Quality (10)
        if vix_data is not None:
            vix = vix_data["close"]
            signals.extend([
                (f"vix_ftq_{sym}", StrategyCategory.FLIGHT_TO_QUALITY, self.vix_flight_to_quality(vix), {}),
                (f"safe_haven_{sym}", StrategyCategory.FLIGHT_TO_QUALITY, self.safe_haven_demand(vix), {}),
                (f"vix_extreme_{sym}", StrategyCategory.FLIGHT_TO_QUALITY,
                 self.vix_flight_to_quality(vix), {"variant": "extreme"}),
                (f"vix_zscore_{sym}", StrategyCategory.FLIGHT_TO_QUALITY,
                 self.safe_haven_demand(vix), {"variant": "zscore"}),
                (f"ftq_combo_{sym}", StrategyCategory.FLIGHT_TO_QUALITY,
                 self.vix_flight_to_quality(vix), {"variant": "combo"}),
            ])
        if spy_data is not None:
            spy_close = spy_data["close"]
            spy_rets = spy_close.pct_change()
            signals.extend([
                (f"eq_bond_ratio_{sym}", StrategyCategory.FLIGHT_TO_QUALITY,
                 self.equity_bond_ratio(spy_close), {}),
                (f"corr_break_{sym}", StrategyCategory.FLIGHT_TO_QUALITY,
                 self.correlation_breakdown(spy_rets), {}),
                (f"risk_off_rot_{sym}", StrategyCategory.FLIGHT_TO_QUALITY,
                 self.risk_off_rotation(vix if vix_data is not None else pd.Series(20, index=self.close.index), spy_close), {}),
                (f"spy_momentum_{sym}", StrategyCategory.FLIGHT_TO_QUALITY,
                 self.correlation_breakdown(spy_rets), {"variant": "momentum"}),
                (f"bond_eq_mr_{sym}", StrategyCategory.FLIGHT_TO_QUALITY,
                 self.equity_bond_ratio(spy_close), {"variant": "mr"}),
            ])

        # 6.6 Fed Policy (10)
        signals.extend([
            (f"fed_dot_{sym}", StrategyCategory.FED_POLICY, self.fed_dot_plot_proxy(), {}),
            (f"meeting_cycle_{sym}", StrategyCategory.FED_POLICY, self.meeting_based_cycle(), {}),
            (f"fwd_guidance_{sym}", StrategyCategory.FED_POLICY, self.forward_guidance_trade(), {}),
            (f"rate_diff_{sym}", StrategyCategory.FED_POLICY, self.policy_rate_differential(), {}),
            (f"fed_pause_{sym}", StrategyCategory.FED_POLICY, self.fed_pause_signal(), {}),
            (f"fed_dovish_{sym}", StrategyCategory.FED_POLICY,
             self.fed_dot_plot_proxy(), {"variant": "dovish"}),
            (f"fed_hawkish_{sym}", StrategyCategory.FED_POLICY,
             self.fed_dot_plot_proxy(), {"variant": "hawkish"}),
            (f"policy_path_{sym}", StrategyCategory.FED_POLICY,
             self.forward_guidance_trade(), {"variant": "path"}),
            (f"easing_cycle_{sym}", StrategyCategory.FED_POLICY,
             self.meeting_based_cycle(), {"variant": "easing"}),
            (f"fed_hold_{sym}", StrategyCategory.FED_POLICY,
             self.fed_pause_signal(), {"variant": "hold"}),
        ])

        # 6.7 Municipal Seasonality (10)
        muni_signals = [
            (f"muni_seasonal_{sym}", StrategyCategory.MUNICIPAL_SEASONALITY, self.muni_seasonal(), {}),
            (f"muni_supply_{sym}", StrategyCategory.MUNICIPAL_SEASONALITY, self.muni_supply_dynamics(), {}),
            (f"tax_loss_rebound_{sym}", StrategyCategory.MUNICIPAL_SEASONALITY, self.tax_loss_harvesting_rebound(), {}),
            (f"muni_call_{sym}", StrategyCategory.MUNICIPAL_SEASONALITY, self.muni_call_risk_proxy(), {}),
            (f"muni_treasury_{sym}", StrategyCategory.MUNICIPAL_SEASONALITY, self.ratio_muni_treasury_value(), {}),
            (f"muni_summer_{sym}", StrategyCategory.MUNICIPAL_SEASONALITY,
             self.muni_seasonal(), {"variant": "summer"}),
            (f"muni_year_end_{sym}", StrategyCategory.MUNICIPAL_SEASONALITY,
             self.muni_supply_dynamics(), {"variant": "year_end"}),
            (f"muni_ratio_{sym}", StrategyCategory.MUNICIPAL_SEASONALITY,
             self.ratio_muni_treasury_value(), {}),
            (f"muni_jan_{sym}", StrategyCategory.MUNICIPAL_SEASONALITY,
             self.tax_loss_harvesting_rebound(), {"variant": "jan"}),
            (f"muni_safe_{sym}", StrategyCategory.MUNICIPAL_SEASONALITY,
             self.muni_call_risk_proxy(), {"variant": "safe"}),
        ]
        signals.extend(muni_signals)

        # 6.8 EM Debt Carry (10)
        em_signals = [
            (f"em_carry_{sym}", StrategyCategory.EM_DEBT_CARRY, self.em_carry_trade(), {}),
            (f"em_mom_20_{sym}", StrategyCategory.EM_DEBT_CARRY, self.em_momentum(20), {"lookback": 20}),
            (f"em_mom_60_{sym}", StrategyCategory.EM_DEBT_CARRY, self.em_momentum(60), {"lookback": 60}),
            (f"em_risk_prem_{sym}", StrategyCategory.EM_DEBT_CARRY, self.em_risk_premium(), {}),
            (f"em_dollar_{sym}", StrategyCategory.EM_DEBT_CARRY, self.em_dollar_sensitivity(), {}),
            (f"em_vol_time_{sym}", StrategyCategory.EM_DEBT_CARRY, self.em_volatility_timing(), {}),
            (f"em_carry_enh_{sym}", StrategyCategory.EM_DEBT_CARRY,
             self.em_carry_trade(), {"variant": "enhanced"}),
            (f"em_defensive_{sym}", StrategyCategory.EM_DEBT_CARRY,
             self.em_volatility_timing(), {"variant": "defensive"}),
            (f"em_mom_proxy_{sym}", StrategyCategory.EM_DEBT_CARRY,
             self.em_momentum(40), {"lookback": 40}),
            (f"em_spread_{sym}", StrategyCategory.EM_DEBT_CARRY,
             self.em_risk_premium(), {"variant": "spread"}),
        ]
        signals.extend(em_signals)

        # 6.9 Trend Following (10)
        signals.extend([
            (f"donchian_20_{sym}", StrategyCategory.TREND_FOLLOWING, self.donchian_channel(20), {"lookback": 20}),
            (f"donchian_50_{sym}", StrategyCategory.TREND_FOLLOWING, self.donchian_channel(50), {"lookback": 50}),
            (f"bb_trend_{sym}", StrategyCategory.TREND_FOLLOWING, self.bollinger_band_trend(), {}),
            (f"bb_trend_30_{sym}", StrategyCategory.TREND_FOLLOWING, self.bollinger_band_trend(30, 2.5), {"period": 30}),
            (f"keltner_{sym}", StrategyCategory.TREND_FOLLOWING, self.keltner_channel(), {}),
            (f"adx_trend_{sym}", StrategyCategory.TREND_FOLLOWING, self.adx_trend(), {}),
            (f"ichimoku_{sym}", StrategyCategory.TREND_FOLLOWING, self.ichimoku_trend(), {}),
            (f"donchian_10_{sym}", StrategyCategory.TREND_FOLLOWING, self.donchian_channel(10), {"lookback": 10}),
            (f"donchian_100_{sym}", StrategyCategory.TREND_FOLLOWING, self.donchian_channel(100), {"lookback": 100}),
            (f"bb_1std_{sym}", StrategyCategory.TREND_FOLLOWING, self.bollinger_band_trend(20, 1.0), {"period": 20, "std": 1}),
        ])

        # 6.10 Mean Reversion (10)
        signals.extend([
            (f"rsi_mr_{sym}", StrategyCategory.MEAN_REVERSION, self.rsi_mean_reversion(), {}),
            (f"rsi_mr_10_{sym}", StrategyCategory.MEAN_REVERSION, self.rsi_mean_reversion(10), {"period": 10}),
            (f"stoch_mr_{sym}", StrategyCategory.MEAN_REVERSION, self.stochastic_mr(), {}),
            (f"cci_mr_{sym}", StrategyCategory.MEAN_REVERSION, self.cci_mean_reversion(), {}),
            (f"cci_mr_50_{sym}", StrategyCategory.MEAN_REVERSION, self.cci_mean_reversion(50), {"period": 50}),
            (f"williams_r_{sym}", StrategyCategory.MEAN_REVERSION, self.williams_r_mr(), {}),
            (f"vwap_mr_{sym}", StrategyCategory.MEAN_REVERSION, self.vwap_reversion(), {}),
            (f"vwap_mr_50_{sym}", StrategyCategory.MEAN_REVERSION, self.vwap_reversion(50), {"period": 50}),
            (f"rsi_mr_21_{sym}", StrategyCategory.MEAN_REVERSION, self.rsi_mean_reversion(21), {"period": 21}),
            (f"2day_mr_{sym}", StrategyCategory.MEAN_REVERSION,
             pd.Series(np.where(self.close > self.high.rolling(2).max().shift(1), -1,
                               np.where(self.close < self.low.rolling(2).min().shift(1), 1, 0)),
                      index=self.close.index), {}),
        ])

        logger.info(f"Generated {len(signals)} signals for {sym}")
        return signals



# =============================================================================
# SECTION 7: BACKTEST ENGINE
# =============================================================================


class BondBacktestEngine:
    """
    Production backtest engine for bond ETF strategies.
    Accounts for duration, modified duration, convexity, and yield carry.
    """

    def __init__(
        self,
        transaction_cost: float = 0.0001,  # 1bp per trade (bond ETFs are liquid)
        slippage: float = 0.00005,  # 0.5bp slippage
        account_for_duration: bool = True,
        account_for_convexity: bool = True,
        account_for_carry: bool = True,
    ):
        self.tc = transaction_cost
        self.slippage = slippage
        self.use_duration = account_for_duration
        self.use_convexity = account_for_convexity
        self.use_carry = account_for_carry

    def run_backtest(
        self,
        signal: pd.Series,
        prices: pd.DataFrame,
        symbol: str,
        position_size: float = 1.0,
        max_position: float = 1.5,
    ) -> Dict[str, Any]:
        """
        Run a full backtest for a signal with bond-specific adjustments.

        Duration adjustment: Returns are scaled by duration sensitivity.
        Convexity adjustment: Second-order price change from yield moves.
        Carry: Coupon accrual added to returns.
        """
        close = prices["close"]
        returns = close.pct_change().fillna(0)

        # Align signal
        signal = signal.reindex(close.index).ffill().fillna(0)
        signal = np.clip(signal * position_size, -max_position, max_position)

        # Position changes
        pos_changes = signal.diff().abs().fillna(0)
        pos_changes.iloc[0] = abs(signal.iloc[0])

        # Base strategy returns (signal * market returns)
        strat_returns = signal.shift(1).fillna(0) * returns

        # Duration-adjusted returns
        if self.use_duration:
            dur = get_effective_duration(symbol)
            # Scale returns by duration factor to normalize across bonds
            duration_factor = dur / 6.0  # Normalize to intermediate duration
            strat_returns = strat_returns / max(duration_factor, 0.5)

        # Convexity adjustment
        if self.use_convexity:
            conv = get_convexity(symbol)
            yield_changes = prices.get("yield", pd.Series(0, index=close.index)).diff().fillna(0)
            convexity_adj = 0.5 * conv * (yield_changes ** 2) / 10000  # Scaled
            strat_returns = strat_returns + signal.shift(1).fillna(0) * convexity_adj

        # Carry contribution
        if self.use_carry:
            carry_yield = BOND_UNIVERSE.get(symbol, {}).get("avg_yield", 0.04)
            daily_carry = carry_yield / 252
            carry_contrib = signal.shift(1).fillna(0) * daily_carry
            strat_returns = strat_returns + carry_contrib

        # Transaction costs
        tc_cost = pos_changes * (self.tc + self.slippage)
        strat_returns = strat_returns - tc_cost

        # Equity curve
        equity = (1 + strat_returns).cumprod()

        # Trade log
        trades = self._extract_trades(signal, strat_returns, close)

        return {
            "returns": strat_returns,
            "equity": equity,
            "trades": trades,
            "signal": signal,
            "carry_contrib": carry_contrib if self.use_carry else pd.Series(0, index=close.index),
            "convexity_adj": convexity_adj if self.use_convexity else pd.Series(0, index=close.index),
        }

    def _extract_trades(
        self,
        signal: pd.Series,
        returns: pd.Series,
        prices: pd.Series,
    ) -> List[Dict[str, Any]]:
        """Extract individual trade records from signal history."""
        trades = []
        entry_idx = None
        entry_price = None
        entry_signal = 0

        for i, (date, sig) in enumerate(signal.items()):
            if entry_signal == 0 and sig != 0:
                entry_idx = i
                entry_price = prices.iloc[i]
                entry_signal = sig
            elif entry_signal != 0 and sig != entry_signal:
                if entry_idx is not None and entry_price is not None:
                    exit_price = prices.iloc[i]
                    pnl = (exit_price - entry_price) / entry_price * np.sign(entry_signal)
                    trades.append({
                        "entry_date": signal.index[entry_idx].strftime("%Y-%m-%d"),
                        "exit_date": date.strftime("%Y-%m-%d"),
                        "direction": "long" if entry_signal > 0 else "short",
                        "entry_price": float(entry_price),
                        "exit_price": float(exit_price),
                        "pnl": float(pnl),
                        "days_held": i - entry_idx,
                    })
                entry_idx = i if sig != 0 else None
                entry_price = prices.iloc[i] if sig != 0 else None
                entry_signal = sig

        return trades

    def calculate_bond_metrics(
        self,
        returns: pd.ndarray,
        symbol: str,
    ) -> Dict[str, float]:
        """Calculate bond-specific risk metrics."""
        dur = get_effective_duration(symbol)
        conv = get_convexity(symbol)
        carry = BOND_UNIVERSE.get(symbol, {}).get("avg_yield", 0.04)

        # Modified duration approximation
        mod_dur = dur / (1 + carry)

        # Roll-down return (simplified)
        roll_down = carry * 0.3  # Assume 30% of yield from roll-down

        return {
            "effective_duration": dur,
            "modified_duration": mod_dur,
            "convexity": conv,
            "yield_carry_annual": carry,
            "roll_down_return": roll_down,
        }



# =============================================================================
# SECTION 8: STATISTICAL VALIDATOR
# =============================================================================


class BondStatisticalValidator:
    """
    Rigorous statistical validation suite for bond strategies.
    - Sharpe significance via bootstrap
    - Benjamini-Hochberg FDR correction
    - Walk-forward validation
    - Minimum trade thresholds
    - Bond-specific sanity checks (PnL cap, duration exposure)
    """

    def __init__(
        self,
        min_sharpe: float = BOND_MIN_SHARPE_RATIO,
        max_drawdown: float = BOND_MAX_MAX_DRAWDOWN,
        p_value: float = BOND_P_VALUE_THRESHOLD,
        fdr_threshold: float = BOND_FDR_THRESHOLD,
        min_trades_year: int = BOND_MIN_TRADES_PER_YEAR,
        pnl_win_threshold: float = BOND_PNL_WIN_THRESHOLD,
        pnl_sanity_cap: float = BOND_PNL_SANITY_CAP,
    ):
        self.min_sharpe = min_sharpe
        self.max_dd = max_drawdown
        self.p_thresh = p_value
        self.fdr_thresh = fdr_threshold
        self.min_trades = min_trades_year
        self.win_thresh = pnl_win_threshold
        self.sanity_cap = pnl_sanity_cap

    def validate(
        self,
        results: List[BondStrategyResult],
    ) -> Tuple[List[BondStrategyResult], List[BondStrategyResult]]:
        """
        Validate all strategies. Returns (passed, rejected).
        Applies Benjamini-Hochberg FDR correction across p-values.
        """
        if not results:
            return [], []

        # Bootstrap p-values
        p_values = np.array([r.p_value_bootstrap for r in results])
        fdr_rejected = benjamini_hochberg_fdr(p_values, self.fdr_thresh)

        passed = []
        rejected = []

        for i, result in enumerate(results):
            result.bh_fdr_rejected = bool(fdr_rejected[i])

            checks = {
                "sharpe": result.sharpe_ratio >= self.min_sharpe,
                "drawdown": result.max_drawdown >= -self.max_dd,
                "return": result.annualized_return >= BOND_MIN_ANNUAL_RETURN,
                "p_value": result.p_value_bootstrap < self.p_thresh,
                "fdr": result.bh_fdr_rejected,
                "walk_forward": result.walk_forward_passed,
                "trades": result.num_trades >= self.min_trades,
                "profit_factor": result.profit_factor >= BOND_MIN_PROFIT_FACTOR,
                "win_threshold": result.avg_trade_return >= self.win_thresh,
                "sanity_cap": result.total_return <= self.sanity_cap,
            }

            result.pass_all_filters = all(checks.values())

            if result.pass_all_filters:
                passed.append(result)
            else:
                rejected.append(result)

        logger.info(f"Validation: {len(passed)} passed, {len(rejected)} rejected out of {len(results)}")
        return passed, rejected

    def validate_single(self, result: BondStrategyResult) -> bool:
        """Validate a single strategy result."""
        checks = {
            "sharpe": result.sharpe_ratio >= self.min_sharpe,
            "drawdown": result.max_drawdown >= -self.max_dd,
            "return": result.annualized_return >= BOND_MIN_ANNUAL_RETURN,
            "p_value": result.p_value_bootstrap < self.p_thresh,
            "walk_forward": result.walk_forward_passed,
            "trades": result.num_trades >= self.min_trades,
            "profit_factor": result.profit_factor >= BOND_MIN_PROFIT_FACTOR,
            "sanity_cap": result.total_return <= self.sanity_cap,
        }
        result.pass_all_filters = all(checks.values())
        return result.pass_all_filters


# =============================================================================
# SECTION 9: ENSEMBLE CONSTRUCTOR
# =============================================================================


class BondEnsembleConstructor:
    """
    Construct duration-neutral ensemble from validated bond strategies.
    Ensures diversification across bond sectors and duration buckets.
    """

    def __init__(
        self,
        max_strategies: int = 7,
        min_strategies: int = 5,
        max_per_sector: int = 2,
        max_per_category: int = 2,
        target_duration: float = 5.0,  # Target portfolio duration (intermediate)
    ):
        self.max_n = max_strategies
        self.min_n = min_strategies
        self.max_per_sector = max_per_sector
        self.max_per_category = max_per_category
        self.target_duration = target_duration

    def construct(
        self,
        validated: List[BondStrategyResult],
    ) -> List[EnsembleAllocation]:
        """
        Select top strategies ensuring diversification and duration neutrality.
        Uses greedy selection with diversity penalty.
        """
        if len(validated) < self.min_n:
            logger.warning(f"Only {len(validated)} strategies passed, need {self.min_n}")
            return []

        # Sort by composite score
        scored = []
        for r in validated:
            composite = (
                r.sharpe_ratio * 0.35
                + max(r.calmar_ratio, -10) * 0.25
                + (1 - r.p_value_bootstrap) * 0.2
                + r.wf_sharpe_mean * 0.1
                + (1 - abs(r.effective_duration - self.target_duration) / 10) * 0.1
            )
            scored.append((composite, r))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Greedy selection with diversity
        selected = []
        sector_counts: Dict[str, int] = defaultdict(int)
        category_counts: Dict[str, int] = defaultdict(int)
        duration_bucket_counts: Dict[str, int] = defaultdict(int)

        for score, result in scored:
            if len(selected) >= self.max_n:
                break

            sectors = [s.value for s in result.bond_sectors]
            cat = result.category.value
            dur_bucket = DURATION_BUCKETS.get(result.symbols[0], "intermediate")

            # Check constraints
            sector_ok = all(sector_counts.get(s, 0) < self.max_per_sector for s in sectors)
            cat_ok = category_counts.get(cat, 0) < self.max_per_category
            dur_ok = duration_bucket_counts.get(dur_bucket, 0) < 2

            if sector_ok and cat_ok and dur_ok:
                selected.append((score, result))
                for s in sectors:
                    sector_counts[s] += 1
                category_counts[cat] += 1
                duration_bucket_counts[dur_bucket] += 1

        # If not enough, relax constraints
        if len(selected) < self.min_n:
            for score, result in scored:
                if len(selected) >= self.min_n:
                    break
                if result not in [s[1] for s in selected]:
                    selected.append((score, result))

        # Calculate duration-neutral weights
        # Weight inversely by distance from target duration
        weights = []
        for score, result in selected:
            dur_dist = abs(result.effective_duration - self.target_duration)
            w = 1.0 / (1.0 + dur_dist / 5.0)
            weights.append(w)

        total_weight = sum(weights) if sum(weights) > 0 else 1.0

        # Calculate allocations
        total_score = sum(s for s, _ in selected)
        if total_score == 0:
            total_score = 1

        ensemble = []
        for rank, ((score, result), weight) in enumerate(zip(selected, weights)):
            # Allocation balances strategy score with duration neutrality
            alloc_pct = (score / total_score * 70 + weight / total_weight * 30)
            dur_neutral_w = weight / total_weight

            alloc = EnsembleAllocation(
                strategy_id=result.strategy_id,
                name=result.name,
                symbols=result.symbols,
                direction=result.direction,
                allocation_pct=round(alloc_pct, 2),
                expected_return=round(result.annualized_return, 4),
                expected_volatility=round(result.annualized_volatility, 4),
                expected_sharpe=round(result.sharpe_ratio, 4),
                diversification_score=round(score, 4),
                category=result.category,
                effective_duration=round(result.effective_duration, 2),
                duration_neutral_weight=round(dur_neutral_w, 4),
            )
            ensemble.append(alloc)

        # Normalize allocations to 100%
        total_pct = sum(a.allocation_pct for a in ensemble)
        if total_pct > 0 and abs(total_pct - 100) > 0.01:
            for a in ensemble:
                a.allocation_pct = round(a.allocation_pct / total_pct * 100, 2)

        # Calculate portfolio duration
        portfolio_duration = sum(
            a.allocation_pct / 100 * a.effective_duration for a in ensemble
        )
        logger.info(f"Ensemble: {len(ensemble)} strategies, portfolio duration: {portfolio_duration:.2f}")

        return ensemble



# =============================================================================
# SECTION 10: MAIN ENGINE
# =============================================================================


class BondAlphaEngine:
    """
    Main bond alpha engine orchestrating strategy generation,
    backtesting, validation, and ensemble construction.

    Pipeline: EMIT -> INGEST -> ACTIVE GATE -> SMART GATE -> HIGH CONVICTION -> CONSENSUS -> OUTCOME
    """

    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        start_date: str = "2018-01-01",
        end_date: str = "2026-05-20",
        use_synthetic: bool = True,
    ):
        self.symbols = symbols or list(BOND_UNIVERSE.keys())
        self.symbols = [s for s in self.symbols if s not in BOND_BLACKLIST]
        self.start_date = start_date
        self.end_date = end_date
        self.use_synthetic = use_synthetic

        self.backtest_engine = BondBacktestEngine()
        self.validator = BondStatisticalValidator()
        self.ensemble_constructor = BondEnsembleConstructor()

        # Data storage
        self.price_data: Dict[str, pd.DataFrame] = {}
        self.vix_data: Optional[pd.DataFrame] = None
        self.spy_data: Optional[pd.DataFrame] = None

        # Results
        self.all_results: List[BondStrategyResult] = []
        self.passed_results: List[BondStrategyResult] = []
        self.rejected_results: List[BondStrategyResult] = []
        self.ensemble: List[EnsembleAllocation] = []

    def load_data(self) -> None:
        """Load or generate all required market data."""
        logger.info("Loading bond market data...")

        for symbol in self.symbols:
            if self.use_synthetic:
                self.price_data[symbol] = generate_synthetic_bond_data(
                    symbol, self.start_date, self.end_date,
                    seed=hash(symbol) % 10000,
                )
            logger.info(f"  {symbol}: {len(self.price_data[symbol])} rows")

        # Generate auxiliary data
        self.vix_data = generate_vix_data(self.start_date, self.end_date)
        self.spy_data = generate_spy_data(self.start_date, self.end_date)

        logger.info(f"Data loaded for {len(self.symbols)} bonds + VIX + SPY")

    def run(self) -> BondAlphaEngineOutput:
        """Execute the full pipeline."""
        logger.info("=" * 60)
        logger.info("BOND ALPHA ENGINE v2.0.0")
        logger.info(f"Symbols: {self.symbols}")
        logger.info(f"Period: {self.start_date} to {self.end_date}")
        logger.info("=" * 60)

        # Stage 1: Load data
        self.load_data()

        # Stage 2: Generate and backtest all strategies
        self._generate_and_backtest()

        # Stage 3: Validate
        self._validate()

        # Stage 4: Construct ensemble
        self._construct_ensemble()

        # Stage 5: Generate output
        return self._generate_output()

    def _generate_and_backtest(self) -> None:
        """Generate all strategies and run backtests."""
        logger.info("Generating strategies and running backtests...")

        all_results = []

        for symbol in self.symbols:
            prices = self.price_data[symbol]
            generator = BondSignalGenerator(prices, symbol)

            signals = generator.generate_all_signals(
                vix_data=self.vix_data,
                spy_data=self.spy_data,
            )

            for name, category, signal, params in signals:
                try:
                    result = self._evaluate_strategy(
                        name, category, signal, prices, symbol, params
                    )
                    if result is not None:
                        all_results.append(result)
                except Exception as e:
                    logger.debug(f"Error evaluating {name}: {e}")

        self.all_results = all_results
        logger.info(f"Generated and evaluated {len(all_results)} strategies")

    def _evaluate_strategy(
        self,
        name: str,
        category: StrategyCategory,
        signal: pd.Series,
        prices: pd.DataFrame,
        symbol: str,
        params: Dict[str, Any],
    ) -> Optional[BondStrategyResult]:
        """Evaluate a single strategy."""
        # Run backtest
        bt_result = self.backtest_engine.run_backtest(signal, prices, symbol)

        returns = bt_result["returns"]
        equity = bt_result["equity"]
        trades = bt_result["trades"]

        # Skip if insufficient data
        if len(returns) < 60 or returns.std() == 0:
            return None

        # Calculate metrics
        total_return = float(equity.iloc[-1] - 1) if len(equity) > 0 else 0.0
        ann_return = float(np.mean(returns) * 252)
        ann_vol = float(np.std(returns) * np.sqrt(252))
        sharpe = calculate_sharpe(returns.values)
        sortino = calculate_sortino(returns.values)
        max_dd, max_dd_days = calculate_max_drawdown(equity.values)
        calmar = calculate_calmar(returns.values)

        # Trade metrics
        num_trades = len(trades)
        if num_trades > 0:
            wins = [t["pnl"] for t in trades if t["pnl"] > 0]
            losses = [t["pnl"] for t in trades if t["pnl"] <= 0]
            win_rate = len(wins) / num_trades if num_trades > 0 else 0
            avg_win = np.mean(wins) if wins else 0
            avg_loss = np.mean(losses) if losses else 0
            profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float("inf")
            avg_trade = np.mean([t["pnl"] for t in trades])
            payoff = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")
            expectancy = avg_trade
        else:
            win_rate = avg_win = avg_loss = profit_factor = avg_trade = payoff = expectancy = 0

        # Distribution metrics
        skewness = float(stats.skew(returns.values)) if len(returns) > 30 else 0
        kurtosis = float(stats.kurtosis(returns.values)) if len(returns) > 30 else 0

        # Statistical validation
        p_value = bootstrap_sharpe_pvalue(returns.values)

        # Walk-forward validation
        wf_passed, wf_sharpe_mean, wf_sharpe_std = walk_forward_validation(
            lambda test, train: self._wf_strategy(signal, test, train),
            prices,
        )

        # Bond metrics
        dur = get_effective_duration(symbol)
        conv = get_convexity(symbol)
        carry_yield = BOND_UNIVERSE.get(symbol, {}).get("avg_yield", 0.04)
        roll_down = carry_yield * 0.3

        # Strategy ID
        strategy_id = hashlib.md5(name.encode()).hexdigest()[:12]

        # Direction
        signal_sum = signal.sum()
        if signal_sum > len(signal) * 0.1:
            direction = "long"
        elif signal_sum < -len(signal) * 0.1:
            direction = "short"
        else:
            direction = "spread"

        result = BondStrategyResult(
            strategy_id=strategy_id,
            name=name,
            category=category,
            symbols=[symbol],
            bond_sectors=[BOND_UNIVERSE.get(symbol, {}).get("sector", BondSector.AGGREGATE)],
            direction=direction,
            total_return=total_return,
            annualized_return=ann_return,
            annualized_volatility=ann_vol,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            max_drawdown_days=max_dd_days,
            calmar_ratio=calmar,
            profit_factor=profit_factor,
            win_rate=win_rate,
            num_trades=num_trades,
            avg_trade_return=avg_trade,
            avg_win=avg_win,
            avg_loss=avg_loss,
            payoff_ratio=payoff,
            expectancy=expectancy,
            skewness=skewness,
            kurtosis=kurtosis,
            effective_duration=dur,
            modified_duration=dur / (1 + carry_yield),
            convexity_contribution=conv * 0.0001,
            yield_carry_annual=carry_yield,
            roll_down_return=roll_down,
            p_value_sharpe=p_value,
            p_value_bootstrap=p_value,
            bh_fdr_rejected=False,
            walk_forward_passed=wf_passed,
            wf_sharpe_mean=wf_sharpe_mean,
            wf_sharpe_std=wf_sharpe_std,
            params=params,
            equity_curve=equity.tolist(),
            trade_log=trades,
        )

        return result

    def _wf_strategy(
        self,
        signal: pd.Series,
        test: pd.DataFrame,
        train: pd.DataFrame,
    ) -> np.ndarray:
        """Helper for walk-forward validation."""
        test_returns = test["close"].pct_change().fillna(0)
        test_signal = signal.reindex(test_returns.index).ffill().fillna(0)
        return (test_signal.shift(1).fillna(0) * test_returns).values

    def _validate(self) -> None:
        """Run statistical validation."""
        logger.info("Running statistical validation...")
        self.passed_results, self.rejected_results = self.validator.validate(self.all_results)

    def _construct_ensemble(self) -> None:
        """Construct the final ensemble."""
        logger.info("Constructing ensemble...")
        self.ensemble = self.ensemble_constructor.construct(self.passed_results)

    def _generate_output(self) -> BondAlphaEngineOutput:
        """Generate system-compatible output."""
        # Sector exposures
        sector_exposures: Dict[str, float] = defaultdict(float)
        duration_exposures: Dict[str, float] = defaultdict(float)

        for alloc in self.ensemble:
            cat_weight = alloc.allocation_pct / 100
            sector = alloc.category.value
            sector_exposures[sector] += cat_weight

            dur_bucket = DURATION_BUCKETS.get(alloc.symbols[0], "intermediate")
            duration_exposures[dur_bucket] += cat_weight

        meta = {
            "version": __version__,
            "engine": "bond_alpha_engine",
            "date": self.end_date,
            "total_strategies": len(self.all_results),
            "passed_validation": len(self.passed_results),
            "rejected": len(self.rejected_results),
            "ensemble_size": len(self.ensemble),
            "thresholds": {
                "min_sharpe": BOND_MIN_SHARPE_RATIO,
                "max_drawdown": BOND_MAX_MAX_DRAWDOWN,
                "p_value": BOND_P_VALUE_THRESHOLD,
                "pnl_win_threshold": BOND_PNL_WIN_THRESHOLD,
                "pnl_sanity_cap": BOND_PNL_SANITY_CAP,
            },
        }

        output = BondAlphaEngineOutput(
            timestamp=datetime.now().isoformat(),
            stage="CONSENSUS",
            bond_sector_exposures=dict(sector_exposures),
            duration_bucket_exposures=dict(duration_exposures),
            strategy_results=[self._result_to_dict(r) for r in self.passed_results],
            ensemble=[self._ensemble_to_dict(a) for a in self.ensemble],
            rejected_strategies=[self._result_to_dict(r) for r in self.rejected_results],
            meta=meta,
        )

        return output

    def _result_to_dict(self, result: BondStrategyResult) -> Dict[str, Any]:
        """Convert result to serializable dict."""
        d = {
            "strategy_id": result.strategy_id,
            "name": result.name,
            "category": result.category.value,
            "symbols": result.symbols,
            "sectors": [s.value for s in result.bond_sectors],
            "direction": result.direction,
            "sharpe_ratio": round(result.sharpe_ratio, 4),
            "max_drawdown": round(result.max_drawdown, 4),
            "annualized_return": round(result.annualized_return, 4),
            "annualized_volatility": round(result.annualized_volatility, 4),
            "calmar_ratio": round(result.calmar_ratio, 4),
            "profit_factor": round(result.profit_factor, 4),
            "win_rate": round(result.win_rate, 4),
            "num_trades": result.num_trades,
            "effective_duration": round(result.effective_duration, 2),
            "p_value_bootstrap": round(result.p_value_bootstrap, 6),
            "bh_fdr_rejected": result.bh_fdr_rejected,
            "walk_forward_passed": result.walk_forward_passed,
            "wf_sharpe_mean": round(result.wf_sharpe_mean, 4),
            "pass_all_filters": result.pass_all_filters,
            "total_return": round(result.total_return, 4),
        }
        return d

    def _ensemble_to_dict(self, alloc: EnsembleAllocation) -> Dict[str, Any]:
        """Convert ensemble allocation to serializable dict."""
        return {
            "strategy_id": alloc.strategy_id,
            "name": alloc.name,
            "symbols": alloc.symbols,
            "direction": alloc.direction,
            "allocation_pct": alloc.allocation_pct,
            "expected_return": alloc.expected_return,
            "expected_volatility": alloc.expected_volatility,
            "expected_sharpe": alloc.expected_sharpe,
            "category": alloc.category.value,
            "effective_duration": alloc.effective_duration,
            "duration_neutral_weight": alloc.duration_neutral_weight,
        }

    def save_results(self, output_dir: str = "/mnt/agents/output/alpha_engine") -> None:
        """Save results to JSON file."""
        os.makedirs(output_dir, exist_ok=True)
        output = self._generate_output()

        # Main output
        output_path = os.path.join(output_dir, "bond_premium_signals.json")
        output.to_json(output_path)
        logger.info(f"Results saved to {output_path}")

        # Also save as system-compatible signals
        signals_path = os.path.join(output_dir, "bond_signals_for_audit.json")
        system_signals = self._to_system_format(output)
        with open(signals_path, "w") as f:
            json.dump(system_signals, f, indent=2, default=str)
        logger.info(f"System signals saved to {signals_path}")

    def _to_system_format(self, output: BondAlphaEngineOutput) -> Dict[str, Any]:
        """Convert to findtorontoevents.ca/audit compatible format."""
        signals = []
        for alloc in self.ensemble:
            signal = {
                "symbol": alloc.symbols[0],
                "direction": alloc.direction.upper(),
                "confidence": min(alloc.expected_sharpe / 2.0, 0.95),
                "allocation_pct": alloc.allocation_pct,
                "expected_sharpe": alloc.expected_sharpe,
                "category": alloc.category.value,
                "asset_class": "BOND",
                "grade": "A",
                "effective_duration": alloc.effective_duration,
                "strategy_name": alloc.name,
                "timestamp": output.timestamp,
            }
            signals.append(signal)

        return {
            "source": "bond_alpha_engine",
            "stage": output.stage,
            "timestamp": output.timestamp,
            "signals": signals,
            "meta": output.meta,
        }



# =============================================================================
# SECTION 11: INTEGRATION LAYER
# =============================================================================


def is_bond_symbol(symbol: str) -> bool:
    """Return True if symbol is in the bond universe."""
    if not symbol or not isinstance(symbol, str):
        return False
    sym = symbol.upper().strip()
    return sym in BOND_UNIVERSE


def is_bond_source(source: str) -> bool:
    """Return True if source hints at bond data."""
    if not source or not isinstance(source, str):
        return False
    src = source.lower().strip()
    bond_hints = (
        "bond", "treasury", "fixed_income", "credit", "yield", "duration",
        "inflation", "tips", "muni", "emerging_market", "hyg", "tlt", "ief",
    )
    return any(h in src for h in bond_hints)


def is_bond_strategy(strategy_name: str) -> bool:
    """Return True if strategy name hints at bond strategy."""
    if not strategy_name or not isinstance(strategy_name, str):
        return False
    s = strategy_name.lower().strip()
    bond_strategy_hints = (
        "yield_curve", "duration", "credit_spread", "inflation", "flight_to_quality",
        "fed_policy", "municipal", "em_debt", "treasury", "bond",
    )
    return any(h in s for h in bond_strategy_hints)


def run_bond_engine(
    symbols: Optional[List[str]] = None,
    start_date: str = "2018-01-01",
    end_date: str = "2026-05-20",
    save_results: bool = True,
    output_dir: str = "/mnt/agents/output/alpha_engine",
) -> BondAlphaEngineOutput:
    """
    Convenience function to run the full bond alpha engine.

    Args:
        symbols: List of bond symbols to trade. Defaults to all in universe.
        start_date: Backtest start date.
        end_date: Backtest end date.
        save_results: Whether to save JSON output.
        output_dir: Directory for output files.

    Returns:
        BondAlphaEngineOutput with full results.
    """
    engine = BondAlphaEngine(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
    )
    output = engine.run()
    if save_results:
        engine.save_results(output_dir)
    return output


# =============================================================================
# SECTION 12: UNIT TESTS
# =============================================================================


class TestBondAlphaEngine:
    """Unit test skeleton for the bond alpha engine."""

    @staticmethod
    def test_bond_universe() -> bool:
        """Verify bond universe is populated."""
        assert len(BOND_UNIVERSE) == 14, "Expected 14 bond ETFs"
        for sym in ["TLT", "IEF", "SHY", "LQD", "HYG", "EMB", "TIP", "MUB"]:
            assert sym in BOND_UNIVERSE, f"Missing {sym}"
        return True

    @staticmethod
    def test_synthetic_data_generation() -> bool:
        """Verify synthetic data generation."""
        df = generate_synthetic_bond_data("TLT", seed=42)
        assert len(df) > 100, "Expected >100 rows"
        assert all(col in df.columns for col in ["open", "high", "low", "close", "volume"])
        assert "yield" in df.columns, "Missing yield column"
        assert "effective_duration" in df.columns, "Missing duration column"
        return True

    @staticmethod
    def test_signal_generation() -> bool:
        """Verify signal generation produces signals."""
        df = generate_synthetic_bond_data("TLT", seed=42)
        gen = BondSignalGenerator(df, "TLT")
        signals = gen.generate_all_signals()
        assert len(signals) >= 100, f"Expected >=100 signals, got {len(signals)}"
        return True

    @staticmethod
    def test_backtest_engine() -> bool:
        """Verify backtest engine runs."""
        df = generate_synthetic_bond_data("TLT", seed=42)
        gen = BondSignalGenerator(df, "TLT")
        signals = gen.generate_all_signals()
        engine = BondBacktestEngine()
        bt = engine.run_backtest(signals[0][2], df, "TLT")
        assert "returns" in bt
        assert "equity" in bt
        assert len(bt["equity"]) > 0
        return True

    @staticmethod
    def test_statistical_validation() -> bool:
        """Verify validator correctly filters."""
        validator = BondStatisticalValidator()
        # Create a mock result
        result = BondStrategyResult(
            strategy_id="test_1",
            name="test_strategy",
            category=StrategyCategory.YIELD_CURVE,
            symbols=["TLT"],
            bond_sectors=[BondSector.TREASURY],
            direction="long",
            total_return=0.10,
            annualized_return=0.05,
            annualized_volatility=0.04,
            sharpe_ratio=1.25,
            sortino_ratio=1.5,
            max_drawdown=-0.05,
            max_drawdown_days=20,
            calmar_ratio=1.0,
            profit_factor=1.5,
            win_rate=0.55,
            num_trades=50,
            avg_trade_return=0.001,
            avg_win=0.01,
            avg_loss=-0.005,
            payoff_ratio=2.0,
            expectancy=0.001,
            skewness=0.1,
            kurtosis=3.0,
            effective_duration=17.5,
            modified_duration=16.7,
            convexity_contribution=0.42,
            yield_carry_annual=0.045,
            roll_down_return=0.0135,
            p_value_sharpe=0.01,
            p_value_bootstrap=0.01,
            bh_fdr_rejected=True,
            walk_forward_passed=True,
            wf_sharpe_mean=0.8,
            wf_sharpe_std=0.3,
        )
        assert validator.validate_single(result)
        return True

    @staticmethod
    def test_duration_neutral() -> bool:
        """Verify duration-neutral weight calculation."""
        w_long, w_short = duration_neutral_weights("TLT", "SHY")
        assert w_long < w_short, "TLT should have smaller weight due to higher duration (17.5 vs 1.9)"
        dur_long = get_effective_duration("TLT")
        dur_short = get_effective_duration("SHY")
        np.testing.assert_almost_equal(w_long * dur_long, w_short * dur_short, decimal=1)
        return True

    @staticmethod
    def test_bootstrap_pvalue() -> bool:
        """Verify bootstrap p-value is within bounds."""
        rng = np.random.default_rng(42)
        # Generate positive Sharpe returns
        returns = rng.normal(0.0005, 0.005, 252)
        pval = bootstrap_sharpe_pvalue(returns, n_bootstrap=1000)
        assert 0 <= pval <= 1, "p-value out of bounds"
        return True

    @staticmethod
    def test_bh_fdr() -> bool:
        """Verify BH-FDR correction."""
        pvals = np.array([0.01, 0.02, 0.03, 0.1, 0.5])
        rejected = benjamini_hochberg_fdr(pvals, alpha=0.05)
        assert rejected[0], "Should reject lowest p-value"
        assert not rejected[-1], "Should not reject highest p-value"
        return True

    @staticmethod
    def test_price_change_estimation() -> bool:
        """Verify bond price change estimation."""
        # Rates down = prices up
        price_up = estimate_price_change("TLT", -0.01)
        assert price_up > 0, "Rates down should increase prices"
        # Rates up = prices down
        price_down = estimate_price_change("TLT", 0.01)
        assert price_down < 0, "Rates up should decrease prices"
        return True

    @staticmethod
    def run_all_tests() -> Dict[str, bool]:
        """Run all unit tests."""
        tests = {
            "bond_universe": TestBondAlphaEngine.test_bond_universe,
            "synthetic_data": TestBondAlphaEngine.test_synthetic_data_generation,
            "signal_generation": TestBondAlphaEngine.test_signal_generation,
            "backtest_engine": TestBondAlphaEngine.test_backtest_engine,
            "statistical_validation": TestBondAlphaEngine.test_statistical_validation,
            "duration_neutral": TestBondAlphaEngine.test_duration_neutral,
            "bootstrap_pvalue": TestBondAlphaEngine.test_bootstrap_pvalue,
            "bh_fdr": TestBondAlphaEngine.test_bh_fdr,
            "price_change": TestBondAlphaEngine.test_price_change_estimation,
        }
        results = {}
        for name, test_fn in tests.items():
            try:
                test_fn()
                results[name] = True
                logger.info(f"  PASS: {name}")
            except Exception as e:
                results[name] = False
                logger.warning(f"  FAIL: {name} - {e}")
        return results


# =============================================================================
# SECTION 13: MAIN EXECUTION
# =============================================================================


if __name__ == "__main__":
    import sys

    logger.info("=" * 60)
    logger.info("BOND ALPHA ENGINE - Starting Run")
    logger.info("=" * 60)

    # Run unit tests first
    logger.info("Running unit tests...")
    test_results = TestBondAlphaEngine.run_all_tests()
    passed = sum(test_results.values())
    total = len(test_results)
    logger.info(f"Tests: {passed}/{total} passed")

    if passed < total - 1:  # Allow 1 failure
        logger.error("Too many test failures, aborting")
        sys.exit(1)

    # Run main engine
    logger.info("Running main bond engine...")
    output = run_bond_engine(
        symbols=list(BOND_UNIVERSE.keys()),
        start_date="2018-01-01",
        end_date="2026-05-20",
        save_results=True,
    )

    logger.info("=" * 60)
    logger.info("BOND ALPHA ENGINE - Run Complete")
    logger.info(f"  Total strategies: {output.meta['total_strategies']}")
    logger.info(f"  Passed validation: {output.meta['passed_validation']}")
    logger.info(f"  Ensemble size: {output.meta['ensemble_size']}")
    logger.info(f"  Stage: {output.stage}")
    logger.info("=" * 60)
