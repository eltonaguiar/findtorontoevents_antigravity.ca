#!/usr/bin/env python3
"""
Statistical Scoring Framework for Prediction System Profitability
=================================================================
Implements the specification in research/PROFITABLE_SCORING_FRAMEWORK.md.

Usage:
    from alpha_engine.statistical_scoring_framework import StrategyCertifier
    certifier = StrategyCertifier(strategies_df, m_total=150)
    result = certifier.certify("strategy_042")
"""

from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# Constants & Thresholds
# ---------------------------------------------------------------------------

MIN_N_DISCOVERY = 30
MIN_N_VALIDATION = 100
MIN_N_MONEY_READY = 200

BONFERRONI_ALPHA = 0.05
FDR_ALPHA = 0.10

RISK_FREE_RATE = 0.02  # Annual
TRADING_DAYS = 252

# Cost model defaults (can be overridden)
DEFAULT_COMMISSION_PCT = 0.001  # 10 bps per trade
DEFAULT_SPREAD_BPS = 5.0
DEFAULT_BASE_SLIPPAGE = 0.0005  # 5 bps
DEFAULT_VOL_PENALTY = 0.1


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class MetricBundle:
    pf: float = 0.0
    sharpe: float = 0.0
    wr: float = 0.0
    sortino: float = 0.0
    calmar: float = 0.0
    dsr: float = 0.0


@dataclass
class BootstrapResult:
    pf_mean: float = 0.0
    pf_ci_lower: float = 0.0
    pf_ci_upper: float = 0.0
    sharpe_mean: float = 0.0
    sharpe_ci_lower: float = 0.0
    sharpe_ci_upper: float = 0.0
    wr_mean: float = 0.0
    wr_ci_lower: float = 0.0
    wr_ci_upper: float = 0.0


@dataclass
class WalkForwardResult:
    profitable_folds: int = 0
    total_folds: int = 0
    mean_oos_pf: float = 0.0
    fold_pfs: List[float] = field(default_factory=list)


@dataclass
class DirectionResult:
    flag: str = "INSUFFICIENT_DATA"  # BALANCED, DIRECTIONAL, INSUFFICIENT_DATA
    pf_bias: float = 0.0
    wr_bias: float = 0.0
    long: Dict = field(default_factory=dict)
    short: Dict = field(default_factory=dict)


@dataclass
class CertificationResult:
    strategy_id: str = ""
    certification_status: str = "FAIL"  # FAIL, DISCOVERY, VALIDATED, MONEY_READY
    gates: Dict[str, str] = field(default_factory=dict)
    metrics: Dict = field(default_factory=dict)
    direction: DirectionResult = field(default_factory=DirectionResult)
    multiple_testing: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core Metric Functions
# ---------------------------------------------------------------------------

def win_rate(trade_returns: np.ndarray) -> float:
    """Win Rate = proportion of positive returns."""
    if len(trade_returns) == 0:
        return 0.0
    return float(np.mean(trade_returns > 0))


def profit_factor(trade_returns: np.ndarray) -> float:
    """Profit Factor = gross profit / |gross loss|."""
    gross_profit = np.sum(trade_returns[trade_returns > 0])
    gross_loss = abs(np.sum(trade_returns[trade_returns < 0]))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return float(gross_profit / gross_loss)


def sharpe_ratio(daily_returns: np.ndarray, annualize: bool = True) -> float:
    """Sharpe ratio using daily returns."""
    if len(daily_returns) < 2:
        return 0.0
    excess = daily_returns - (RISK_FREE_RATE / TRADING_DAYS)
    std = np.std(excess, ddof=1)
    if std == 0:
        return 0.0
    sr = np.mean(excess) / std
    if annualize:
        sr *= math.sqrt(TRADING_DAYS)
    return float(sr)


def sortino_ratio(daily_returns: np.ndarray, mar: Optional[float] = None) -> float:
    """Sortino ratio using downside deviation."""
    if len(daily_returns) < 2:
        return 0.0
    if mar is None:
        mar = RISK_FREE_RATE / TRADING_DAYS
    excess = daily_returns - mar
    downside = excess[excess < 0]
    if len(downside) == 0:
        return float("inf") if np.mean(excess) > 0 else 0.0
    downside_dev = math.sqrt(np.mean(downside**2))
    if downside_dev == 0:
        return 0.0
    sortino = np.mean(excess) / downside_dev
    return float(sortino * math.sqrt(TRADING_DAYS))


def calmar_ratio(daily_returns: np.ndarray) -> float:
    """Calmar = CAGR / Max Drawdown."""
    if len(daily_returns) == 0:
        return 0.0
    equity = np.cumprod(1 + daily_returns)
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak
    max_dd = abs(np.min(drawdown))
    if max_dd == 0:
        return float("inf")
    years = len(daily_returns) / TRADING_DAYS
    if years == 0:
        return 0.0
    cagr = (equity[-1] / equity[0]) ** (1 / years) - 1
    return float(cagr / max_dd)


def deflated_sharpe_ratio(
    sharpe_hat: float,
    n_returns: int,
    skewness: float,
    kurtosis: float,
    v_ratio: float,
    m_trials: int,
) -> float:
    """
    Lopez de Prado (2018) Deflated Sharpe Ratio.
    Returns P(SR > 0 | observed Sharpe, sample stats, multiple trials).
    """
    if n_returns < 30 or m_trials < 1:
        return 0.0

    # Approximate the non-centrality parameter
    # This is a practical implementation; for production, use full numerical integration
    sr_var = (1 - skewness * sharpe_hat + (kurtosis - 1) / 4 * sharpe_hat**2) / (n_returns - 1)
    sr_std = math.sqrt(max(sr_var, 1e-12))

    # Adjust for multiple trials using Sidak correction approximation
    if m_trials > 1:
        sharpe_hat_adj = sharpe_hat - (sr_std * stats.norm.ppf(1 - (1 / m_trials)))
    else:
        sharpe_hat_adj = sharpe_hat

    # Z-score for true SR > 0
    z = sharpe_hat_adj / sr_std
    # Adjust for variance of Sharpe across trials (V)
    if v_ratio > 0:
        z /= math.sqrt(1 + v_ratio)

    dsr = stats.norm.cdf(z)
    return float(dsr)


# ---------------------------------------------------------------------------
# Sample Size & Power
# ---------------------------------------------------------------------------

def minimum_sample_size(
    expected_wr: float = 0.55,
    baseline_wr: float = 0.50,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    """
    Binomial power analysis for win rate.
    Returns minimum n to detect expected_wr > baseline_wr.
    """
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)

    p = expected_wr
    p0 = baseline_wr

    numerator = (z_alpha * math.sqrt(p0 * (1 - p0)) + z_beta * math.sqrt(p * (1 - p))) ** 2
    denominator = (p - p0) ** 2

    if denominator == 0:
        return 0
    return math.ceil(numerator / denominator)


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def bootstrap_metrics(
    trade_returns: np.ndarray,
    daily_returns: np.ndarray,
    n_bootstrap: int = 10000,
    random_state: Optional[int] = None,
) -> BootstrapResult:
    """
    Bootstrap trade returns and daily returns to estimate confidence intervals.
    """
    if random_state is not None:
        np.random.seed(random_state)

    n = len(trade_returns)
    if n < MIN_N_DISCOVERY:
        return BootstrapResult()

    pf_samples = []
    sharpe_samples = []
    wr_samples = []

    for _ in range(n_bootstrap):
        idx = np.random.choice(n, size=n, replace=True)
        boot_trades = trade_returns[idx]
        pf_samples.append(profit_factor(boot_trades))
        wr_samples.append(win_rate(boot_trades))

    # For Sharpe, bootstrap daily returns
    n_days = len(daily_returns)
    if n_days >= 30:
        for _ in range(n_bootstrap):
            idx = np.random.choice(n_days, size=n_days, replace=True)
            boot_daily = daily_returns[idx]
            sharpe_samples.append(sharpe_ratio(boot_daily, annualize=True))

    pf_samples = np.array(pf_samples)
    wr_samples = np.array(wr_samples)
    sharpe_samples = np.array(sharpe_samples) if sharpe_samples else np.array([0.0])

    return BootstrapResult(
        pf_mean=float(np.mean(pf_samples)),
        pf_ci_lower=float(np.percentile(pf_samples, 2.5)),
        pf_ci_upper=float(np.percentile(pf_samples, 97.5)),
        sharpe_mean=float(np.mean(sharpe_samples)),
        sharpe_ci_lower=float(np.percentile(sharpe_samples, 2.5)),
        sharpe_ci_upper=float(np.percentile(sharpe_samples, 97.5)),
        wr_mean=float(np.mean(wr_samples)),
        wr_ci_lower=float(np.percentile(wr_samples, 2.5)),
        wr_ci_upper=float(np.percentile(wr_samples, 97.5)),
    )


# ---------------------------------------------------------------------------
# Walk-Forward Analysis
# ---------------------------------------------------------------------------

def walk_forward_analysis(
    daily_returns: np.ndarray,
    n_folds: int = 10,
) -> WalkForwardResult:
    """
    Simple walk-forward: divide into contiguous folds.
    Returns OOS PF for each fold (no optimization; purely chronological test).
    """
    n = len(daily_returns)
    if n < n_folds * 30:
        return WalkForwardResult(total_folds=n_folds)

    fold_size = n // n_folds
    fold_pfs = []

    for i in range(1, n_folds):
        # Test on fold i
        start = i * fold_size
        end = (i + 1) * fold_size if i < n_folds - 1 else n
        oos_returns = daily_returns[start:end]
        fold_pfs.append(profit_factor(oos_returns))

    profitable = sum(1 for pf in fold_pfs if pf > 1.0)
    return WalkForwardResult(
        profitable_folds=profitable,
        total_folds=len(fold_pfs),
        mean_oos_pf=float(np.mean(fold_pfs)),
        fold_pfs=fold_pfs,
    )


# ---------------------------------------------------------------------------
# Out-of-Sample Split
# ---------------------------------------------------------------------------

def oos_split_metrics(daily_returns: np.ndarray, oos_pct: float = 0.30) -> MetricBundle:
    """Calculate metrics on the last oos_pct of data only."""
    n = len(daily_returns)
    split_idx = int(n * (1 - oos_pct))
    oos = daily_returns[split_idx:]
    if len(oos) < 30:
        return MetricBundle()
    return MetricBundle(
        pf=profit_factor(oos),
        sharpe=sharpe_ratio(oos),
        wr=win_rate(oos),
        sortino=sortino_ratio(oos),
    )


# ---------------------------------------------------------------------------
# Cost Model & Net Metrics
# ---------------------------------------------------------------------------

def apply_costs(
    trade_returns: np.ndarray,
    commission_pct: float = DEFAULT_COMMISSION_PCT,
    spread_bps: float = DEFAULT_SPREAD_BPS,
    base_slippage: float = DEFAULT_BASE_SLIPPAGE,
    vol_penalty: float = DEFAULT_VOL_PENALTY,
) -> np.ndarray:
    """
    Deduct per-trade costs from gross returns.
    Slippage is volatility-adjusted.
    """
    if len(trade_returns) < 20:
        realized_vol = 0.0
    else:
        realized_vol = float(np.std(trade_returns, ddof=1))

    slippage = base_slippage + (vol_penalty * realized_vol)
    total_cost = commission_pct + (spread_bps / 10000.0) + slippage

    # Intrabar replay adjustment: increase slippage by 10 bps for winners
    # This accounts for the 23-24% win-to-SL flip observed in replay
    intrabar_penalty = np.where(trade_returns > 0, 0.0010, 0.0)

    net_returns = trade_returns - total_cost - intrabar_penalty
    return net_returns


def calculate_net_metrics(
    trade_returns: np.ndarray,
    daily_returns: np.ndarray,
    commission_pct: float = DEFAULT_COMMISSION_PCT,
    spread_bps: float = DEFAULT_SPREAD_BPS,
) -> MetricBundle:
    """Calculate all metrics after deducting costs."""
    net_trade_returns = apply_costs(trade_returns, commission_pct, spread_bps)
    # Approximate net daily returns by scaling net trade returns proportionally
    if len(trade_returns) == len(daily_returns):
        net_daily = net_trade_returns
    else:
        # Scale daily returns by the ratio of net to gross sum
        gross_sum = np.sum(trade_returns)
        net_sum = np.sum(net_trade_returns)
        scale = net_sum / gross_sum if gross_sum != 0 else 1.0
        net_daily = daily_returns * scale

    return MetricBundle(
        pf=profit_factor(net_trade_returns),
        sharpe=sharpe_ratio(net_daily),
        wr=win_rate(net_trade_returns),
        sortino=sortino_ratio(net_daily),
        calmar=calmar_ratio(net_daily),
    )


# ---------------------------------------------------------------------------
# Direction Bias
# ---------------------------------------------------------------------------

def direction_bias(
    trades_df: pd.DataFrame,
) -> DirectionResult:
    """
    Calculate direction-specific metrics and bias flags.
    trades_df must have columns: 'direction' (LONG/SHORT), 'return'.
    """
    long_df = trades_df[trades_df["direction"] == "LONG"]
    short_df = trades_df[trades_df["direction"] == "SHORT"]

    n_long = len(long_df)
    n_short = len(short_df)

    if n_long < MIN_N_DISCOVERY or n_short < MIN_N_DISCOVERY:
        return DirectionResult(
            flag="INSUFFICIENT_DATA",
            long={"n": n_long},
            short={"n": n_short},
        )

    long_returns = long_df["return"].values
    short_returns = short_df["return"].values

    pf_long = profit_factor(long_returns)
    pf_short = profit_factor(short_returns)
    wr_long = win_rate(long_returns)
    wr_short = win_rate(short_returns)

    pf_bias = (pf_long - pf_short) / (pf_long + pf_short) if (pf_long + pf_short) > 0 else 0.0
    wr_bias = (wr_long - wr_short) / (wr_long + wr_short) if (wr_long + wr_short) > 0 else 0.0

    flag = "DIRECTIONAL" if abs(pf_bias) > 0.3 else "BALANCED"

    return DirectionResult(
        flag=flag,
        pf_bias=round(pf_bias, 3),
        wr_bias=round(wr_bias, 3),
        long={
            "n": n_long,
            "pf": round(pf_long, 3),
            "wr": round(wr_long, 3),
            "sharpe": round(sharpe_ratio(long_returns), 3),
        },
        short={
            "n": n_short,
            "pf": round(pf_short, 3),
            "wr": round(wr_short, 3),
            "sharpe": round(sharpe_ratio(short_returns), 3),
        },
    )


# ---------------------------------------------------------------------------
# Multiple Testing Correction
# ---------------------------------------------------------------------------

def bonferroni_threshold(alpha: float, m: int) -> float:
    """Returns adjusted alpha for Bonferroni correction."""
    return alpha / max(m, 1)


def benjamini_hochberg(p_values: np.ndarray, alpha: float = FDR_ALPHA) -> np.ndarray:
    """
    Returns boolean array: True for hypotheses that pass BH-FDR.
    """
    p_values = np.array(p_values)
    m = len(p_values)
    if m == 0:
        return np.array([], dtype=bool)

    sorted_idx = np.argsort(p_values)
    sorted_p = p_values[sorted_idx]

    # Find largest k where p(k) <= (k/m) * alpha
    thresholds = (np.arange(1, m + 1) / m) * alpha
    passed = sorted_p <= thresholds

    # Largest index where condition holds
    if not np.any(passed):
        return np.zeros(m, dtype=bool)

    max_k = np.max(np.where(passed)[0])
    result = np.zeros(m, dtype=bool)
    result[sorted_idx[: max_k + 1]] = True
    return result


def calculate_p_value(trade_returns: np.ndarray) -> float:
    """
    One-sample t-test against zero mean (testing if mean return > 0).
    Returns p-value.
    """
    if len(trade_returns) < 2:
        return 1.0
    t_stat, p_val = stats.ttest_1samp(trade_returns, 0.0)
    # One-tailed
    if t_stat > 0:
        return p_val / 2.0
    return 1.0


# ---------------------------------------------------------------------------
# Gate Evaluation
# ---------------------------------------------------------------------------

def evaluate_gate_0_data_quality(trade_returns: np.ndarray) -> Tuple[str, List[str]]:
    """Gate 0: Data Quality."""
    errors = []
    n = len(trade_returns)
    if n < MIN_N_DISCOVERY:
        errors.append(f"n={n} < minimum discovery threshold {MIN_N_DISCOVERY}")
    if np.any(np.isnan(trade_returns)):
        errors.append("NaN values in trade returns")
    if n >= MIN_N_DISCOVERY and np.std(trade_returns) == 0:
        errors.append("Zero variance in returns")
    status = "PASS" if not errors else "FAIL"
    return status, errors


def evaluate_gate_1_statistical_significance(
    trade_returns: np.ndarray,
    bootstrap: BootstrapResult,
    p_value: float,
    alpha_corrected: float,
) -> Tuple[str, List[str]]:
    """Gate 1: Statistical Significance."""
    errors = []
    if bootstrap.pf_ci_lower <= 1.0:
        errors.append(f"Bootstrap PF CI lower bound {bootstrap.pf_ci_lower:.3f} <= 1.0")
    if bootstrap.sharpe_ci_lower <= 0:
        errors.append(f"Bootstrap Sharpe CI lower bound {bootstrap.sharpe_ci_lower:.3f} <= 0")
    if p_value >= alpha_corrected:
        errors.append(f"p-value {p_value:.4f} >= corrected alpha {alpha_corrected:.4f}")
    status = "PASS" if not errors else "FAIL"
    return status, errors


def evaluate_gate_2_walk_forward(wfa: WalkForwardResult) -> Tuple[str, List[str]]:
    """Gate 2: Walk-Forward Robustness."""
    errors = []
    if wfa.total_folds == 0:
        errors.append("No walk-forward folds generated")
    else:
        profitable_ratio = wfa.profitable_folds / wfa.total_folds
        if profitable_ratio < 0.6:
            errors.append(f"Only {profitable_ratio:.1%} profitable WFA folds (< 60%)")
        if wfa.mean_oos_pf <= 1.2:
            errors.append(f"Mean OOS PF {wfa.mean_oos_pf:.3f} <= 1.2")
    status = "PASS" if not errors else "FAIL"
    return status, errors


def evaluate_gate_3_gross_profitability(gross: MetricBundle) -> Tuple[str, List[str]]:
    """Gate 3: Gross Profitability."""
    errors = []
    if gross.pf <= 1.5:
        errors.append(f"Gross PF {gross.pf:.3f} <= 1.5")
    if gross.sharpe <= 1.0:
        errors.append(f"Gross Sharpe {gross.sharpe:.3f} <= 1.0")
    if gross.wr <= 0.50:
        errors.append(f"Gross WR {gross.wr:.3f} <= 0.50")
    if gross.sortino <= 1.5:
        errors.append(f"Gross Sortino {gross.sortino:.3f} <= 1.5")
    status = "PASS" if not errors else "FAIL"
    return status, errors


def evaluate_gate_4_money_ready(net: MetricBundle, dsr: float) -> Tuple[str, List[str]]:
    """Gate 4: Money-Ready (Net After Costs)."""
    errors = []
    if net.pf <= 1.2:
        errors.append(f"Net PF {net.pf:.3f} <= 1.2")
    if net.sharpe <= 0.5:
        errors.append(f"Net Sharpe {net.sharpe:.3f} <= 0.5")
    if net.wr <= 0.45:
        errors.append(f"Net WR {net.wr:.3f} <= 0.45")
    if net.sortino <= 0.8:
        errors.append(f"Net Sortino {net.sortino:.3f} <= 0.8")
    if dsr <= 0.95:
        errors.append(f"DSR {dsr:.3f} <= 0.95")
    status = "PASS" if not errors else "FAIL"
    return status, errors


def evaluate_gate_5_direction_validation(
    direction: DirectionResult,
) -> Tuple[str, List[str]]:
    """Gate 5: Direction Validation."""
    errors = []
    if direction.flag == "DIRECTIONAL":
        # Both sides must individually pass Gate 4 thresholds, OR
        # strategy must be explicitly single-direction
        long_pf = direction.long.get("pf", 0)
        short_pf = direction.short.get("pf", 0)
        long_sharpe = direction.long.get("sharpe", 0)
        short_sharpe = direction.short.get("sharpe", 0)

        long_pass = long_pf > 1.2 and long_sharpe > 0.5
        short_pass = short_pf > 1.2 and short_sharpe > 0.5

        if not (long_pass or short_pass):
            errors.append(
                f"Directional strategy but neither side passes money-ready: "
                f"LONG(pf={long_pf}, sharpe={long_sharpe}) "
                f"SHORT(pf={short_pf}, sharpe={short_sharpe})"
            )
    status = "PASS" if not errors else "FAIL"
    return status, errors


# ---------------------------------------------------------------------------
# Main Certifier Class
# ---------------------------------------------------------------------------

class StrategyCertifier:
    def __init__(
        self,
        strategies_df: pd.DataFrame,
        m_total: int = 100,
        commission_pct: float = DEFAULT_COMMISSION_PCT,
        spread_bps: float = DEFAULT_SPREAD_BPS,
    ):
        """
        strategies_df: DataFrame with columns:
            - strategy_id
            - direction (LONG/SHORT)
            - trade_return (per-trade PnL %)
            - date (trade close date)
        m_total: Total number of strategies being tested (for multiplicity correction).
        """
        self.df = strategies_df.copy()
        self.m_total = m_total
        self.commission_pct = commission_pct
        self.spread_bps = spread_bps

    def certify(self, strategy_id: str) -> CertificationResult:
        """Run full certification pipeline for a single strategy."""
        result = CertificationResult(strategy_id=strategy_id)
        subset = self.df[self.df["strategy_id"] == strategy_id]

        if subset.empty:
            result.errors.append("Strategy not found in dataset")
            return result

        trade_returns = subset["trade_return"].values
        n = len(trade_returns)

        # Build daily returns (approximate: assume one trade per day max)
        daily_df = subset.groupby(subset["date"].dt.date if hasattr(subset["date"], "dt") else subset["date"])["trade_return"].sum()
        daily_returns = daily_df.values

        # --- GATE 0 ---
        g0_status, g0_errors = evaluate_gate_0_data_quality(trade_returns)
        result.gates["gate_0_data_quality"] = g0_status
        result.errors.extend(g0_errors)
        if g0_status == "FAIL":
            result.certification_status = "FAIL"
            return result

        # --- CALCULATE METRICS ---
        gross = MetricBundle(
            pf=profit_factor(trade_returns),
            sharpe=sharpe_ratio(daily_returns),
            wr=win_rate(trade_returns),
            sortino=sortino_ratio(daily_returns),
            calmar=calmar_ratio(daily_returns),
        )

        bootstrap = bootstrap_metrics(trade_returns, daily_returns)
        p_value = calculate_p_value(trade_returns)
        alpha_corr = bonferroni_threshold(BONFERRONI_ALPHA, self.m_total)

        wfa = walk_forward_analysis(daily_returns)
        oos = oos_split_metrics(daily_returns)
        net = calculate_net_metrics(
            trade_returns, daily_returns, self.commission_pct, self.spread_bps
        )

        # DSR calculation
        if len(daily_returns) >= 30:
            skew = float(stats.skew(daily_returns))
            kurt = float(stats.kurtosis(daily_returns))
            # Estimate V as variance of Sharpe across a random sample of strategies
            # For single-strategy cert, V=0 (no cross-sectional variance)
            dsr = deflated_sharpe_ratio(
                gross.sharpe, len(daily_returns), skew, kurt, v_ratio=0.0, m_trials=self.m_total
            )
        else:
            dsr = 0.0

        # --- GATE 1 ---
        g1_status, g1_errors = evaluate_gate_1_statistical_significance(
            trade_returns, bootstrap, p_value, alpha_corr
        )
        result.gates["gate_1_statistical_significance"] = g1_status
        result.errors.extend(g1_errors)

        # --- GATE 2 ---
        g2_status, g2_errors = evaluate_gate_2_walk_forward(wfa)
        result.gates["gate_2_walk_forward"] = g2_status
        result.errors.extend(g2_errors)

        # --- GATE 3 ---
        g3_status, g3_errors = evaluate_gate_3_gross_profitability(gross)
        result.gates["gate_3_gross_profitability"] = g3_status
        result.errors.extend(g3_errors)

        # --- GATE 4 ---
        g4_status, g4_errors = evaluate_gate_4_money_ready(net, dsr)
        result.gates["gate_4_money_ready"] = g4_status
        result.errors.extend(g4_errors)

        # --- GATE 5 ---
        direction = direction_bias(subset)
        g5_status, g5_errors = evaluate_gate_5_direction_validation(direction)
        result.gates["gate_5_direction_validation"] = g5_status
        result.errors.extend(g5_errors)

        # --- CERTIFICATION STATUS ---
        if all(v == "PASS" for v in result.gates.values()):
            result.certification_status = "MONEY_READY"
        elif result.gates.get("gate_4_money_ready") == "FAIL" and g3_status == "PASS":
            result.certification_status = "VALIDATED"
        elif result.gates.get("gate_1_statistical_significance") == "PASS":
            result.certification_status = "DISCOVERY"
        else:
            result.certification_status = "FAIL"

        # --- POPULATE METRICS ---
        result.metrics = {
            "gross": {
                "pf": round(gross.pf, 3),
                "sharpe": round(gross.sharpe, 3),
                "wr": round(gross.wr, 3),
                "sortino": round(gross.sortino, 3),
                "calmar": round(gross.calmar, 3),
            },
            "net": {
                "pf": round(net.pf, 3),
                "sharpe": round(net.sharpe, 3),
                "wr": round(net.wr, 3),
                "sortino": round(net.sortino, 3),
                "calmar": round(net.calmar, 3),
            },
            "bootstrap_ci": {
                "pf_lower": round(bootstrap.pf_ci_lower, 3),
                "pf_upper": round(bootstrap.pf_ci_upper, 3),
                "sharpe_lower": round(bootstrap.sharpe_ci_lower, 3),
                "sharpe_upper": round(bootstrap.sharpe_ci_upper, 3),
                "wr_lower": round(bootstrap.wr_ci_lower, 3),
                "wr_upper": round(bootstrap.wr_ci_upper, 3),
            },
            "dsr": round(dsr, 3),
            "walk_forward": {
                "profitable_folds": wfa.profitable_folds,
                "total_folds": wfa.total_folds,
                "mean_oos_pf": round(wfa.mean_oos_pf, 3),
                "fold_pfs": [round(p, 3) for p in wfa.fold_pfs],
            },
            "oos": {
                "pf": round(oos.pf, 3),
                "sharpe": round(oos.sharpe, 3),
                "wr": round(oos.wr, 3),
                "sortino": round(oos.sortino, 3),
            },
        }
        result.direction = direction
        result.multiple_testing = {
            "m": self.m_total,
            "p_value": round(p_value, 6),
            "alpha_bonferroni": round(alpha_corr, 6),
            "bonferroni_pass": p_value < alpha_corr,
            "fdr_q_value": None,  # Calculated at batch level
            "fdr_pass": None,
        }

        return result

    def certify_all(self) -> Dict[str, CertificationResult]:
        """Certify all strategies and apply batch-level FDR correction."""
        strategy_ids = self.df["strategy_id"].unique()
        results = {}
        p_values = []

        for sid in strategy_ids:
            res = self.certify(sid)
            results[sid] = res
            p_values.append(res.multiple_testing["p_value"])

        # Batch-level BH-FDR
        p_array = np.array(p_values)
        fdr_passed = benjamini_hochberg(p_array, alpha=FDR_ALPHA)

        for i, sid in enumerate(strategy_ids):
            results[sid].multiple_testing["fdr_pass"] = bool(fdr_passed[i])
            # Approximate q-value as the FDR threshold at this rank
            if fdr_passed[i]:
                rank = np.sum(p_array <= p_array[i])
                q = (rank / len(p_array)) * FDR_ALPHA
                results[sid].multiple_testing["fdr_q_value"] = round(float(q), 6)
            else:
                results[sid].multiple_testing["fdr_q_value"] = None

        return results


# ---------------------------------------------------------------------------
# CLI / Standalone
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Example: load from JSON and certify
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to trades JSON")
    parser.add_argument("--m-total", type=int, default=100, help="Total strategies tested")
    parser.add_argument("--strategy", default=None, help="Specific strategy ID to certify")
    args = parser.parse_args()

    with open(args.input) as f:
        records = json.load(f)

    df = pd.DataFrame(records)
    certifier = StrategyCertifier(df, m_total=args.m_total)

    if args.strategy:
        result = certifier.certify(args.strategy)
        print(json.dumps(result.__dict__, default=str, indent=2))
    else:
        results = certifier.certify_all()
        summary = {
            sid: {
                "status": r.certification_status,
                "gates": r.gates,
                "errors": r.errors,
            }
            for sid, r in results.items()
        }
        print(json.dumps(summary, indent=2))
