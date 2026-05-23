"""
statistical_gates.py — Layer 4 Statistical Significance Gates

Implements the four mandatory checks from TESTING_PROTOCOL.MD Layer 4
for strategy promotion decisions. All functions use numpy only (no scipy).

Gates:
  1. Benjamini-Hochberg FDR correction  — controls false discovery rate
  2. Deflated Sharpe Ratio (DSR)        — adjusts Sharpe for data-snooping
  3. Newey-West t-statistic             — serial-correlation-robust inference
  4. Statistical power analysis          — flags underpowered tests

References:
  - Benjamini & Hochberg (1995), "Controlling the False Discovery Rate"
  - Bailey & Lopez de Prado (2014), "The Deflated Sharpe Ratio"
  - Newey & West (1987), "A Simple, Positive Semi-Definite,
    Heteroskedasticity and Autocorrelation Consistent Covariance Matrix"
  - Cohen (1988), "Statistical Power Analysis for the Behavioral Sciences"

Usage:
    from alpha_engine.validation.statistical_gates import run_all_gates

    result = run_all_gates(
        strategy_returns=[0.01, -0.005, 0.003, ...],
        num_trials=200,
        p_value=0.03,
        p_values_family=[0.03, 0.12, 0.005, 0.45],
    )
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Union

import numpy as np


# ---------------------------------------------------------------------------
# Pure-Python normal distribution helpers (no scipy dependency)
# ---------------------------------------------------------------------------

def _norm_cdf(x: float) -> float:
    """Standard normal CDF via math.erfc."""
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _norm_ppf(p: float) -> float:
    """Standard normal inverse CDF (Beasley-Springer-Moro / Acklam)."""
    if p <= 0:
        return -math.inf
    if p >= 1:
        return math.inf
    a = [
        -3.969683028665376e+01, 2.209460984245205e+02,
        -2.759285104469687e+02, 1.383577518672690e+02,
        -3.066479806614716e+01, 2.506628277459239e+00,
    ]
    b = [
        -5.447609879822406e+01, 1.615858368580409e+02,
        -1.556989798598866e+02, 6.680131188771972e+01,
        -1.328068155288572e+01,
    ]
    c = [
        -7.784894002430293e-03, -3.223964580411365e-01,
        -2.400758277161838e+00, -2.549732539343734e+00,
        4.374664141464968e+00, 2.938163982698783e+00,
    ]
    d = [
        7.784695709041462e-03, 3.224671290700398e-01,
        2.445134137142996e+00, 3.754408661907416e+00,
    ]
    p_low = 0.02425
    p_high = 1.0 - p_low
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1.0)
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5]) * q / \
               (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1.0)
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1.0)


# ===================================================================
# Gate 1: Benjamini-Hochberg FDR Correction
# ===================================================================

def benjamini_hochberg(
    p_values: List[float],
    alpha: float = 0.05,
) -> Dict:
    """Apply Benjamini-Hochberg procedure to control false discovery rate.

    Given a family of p-values from multiple strategy tests, computes
    adjusted q-values and determines which hypotheses are rejected
    while controlling FDR at level *alpha*.

    Args:
        p_values: List of raw p-values from individual strategy tests.
        alpha: Target FDR level (default 0.05).

    Returns:
        Dict with keys:
            q_values    — list of BH-adjusted q-values (same order as input)
            rejected    — list of bools indicating which hypotheses are rejected
            n_rejected  — count of rejections
            pass        — True if at least one hypothesis is rejected
            method      — "benjamini_hochberg"
    """
    m = len(p_values)
    if m == 0:
        return {
            "q_values": [],
            "rejected": [],
            "n_rejected": 0,
            "pass": False,
            "method": "benjamini_hochberg",
        }

    p_arr = np.array(p_values, dtype=np.float64)
    # Sort indices by p-value ascending
    sorted_idx = np.argsort(p_arr)
    sorted_p = p_arr[sorted_idx]

    # BH adjusted p-values: q_i = p_(i) * m / i  (rank i starts at 1)
    ranks = np.arange(1, m + 1, dtype=np.float64)
    raw_q = sorted_p * m / ranks

    # Enforce monotonicity: q_(i) = min(q_(i), q_(i+1)) working backwards
    adjusted_q = np.minimum.accumulate(raw_q[::-1])[::-1]
    adjusted_q = np.clip(adjusted_q, 0.0, 1.0)

    # Map back to original order
    q_values = np.empty(m, dtype=np.float64)
    q_values[sorted_idx] = adjusted_q

    rejected = q_values <= alpha
    n_rejected = int(np.sum(rejected))

    return {
        "q_values": q_values.tolist(),
        "rejected": rejected.tolist(),
        "n_rejected": n_rejected,
        "pass": n_rejected > 0,
        "method": "benjamini_hochberg",
    }


# ===================================================================
# Gate 2: Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014)
# ===================================================================

def deflated_sharpe_ratio(
    returns: Union[List[float], np.ndarray],
    num_trials: int,
    annualization_factor: int = 252,
    dsr_threshold: float = 0.95,
) -> Dict:
    """Compute the Deflated Sharpe Ratio adjusting for data-snooping bias.

    When *num_trials* backtests have been run, the best observed Sharpe is
    inflated by selection bias. DSR computes the probability that the
    observed Sharpe exceeds the expected maximum Sharpe from *num_trials*
    independent zero-alpha strategies.

    Args:
        returns: Array of periodic (e.g. daily) strategy returns.
        num_trials: Total number of independent backtests conducted.
        annualization_factor: Periods per year (252 for daily, 52 weekly).
        dsr_threshold: Probability threshold for pass (default 0.95).

    Returns:
        Dict with keys:
            sharpe          — annualized Sharpe ratio
            dsr_probability — P(true Sharpe > expected max under null)
            expected_max_sr — expected maximum Sharpe under null hypothesis
            pass            — True if dsr_probability >= dsr_threshold
            method          — "deflated_sharpe_ratio"
    """
    r = np.asarray(returns, dtype=np.float64)
    n = len(r)

    if n < 4:
        return {
            "sharpe": float("nan"),
            "dsr_probability": 0.0,
            "expected_max_sr": float("nan"),
            "pass": False,
            "method": "deflated_sharpe_ratio",
        }

    mu = float(np.mean(r))
    std = float(np.std(r, ddof=1))
    if std < 1e-15:
        return {
            "sharpe": 0.0,
            "dsr_probability": 0.0,
            "expected_max_sr": float("nan"),
            "pass": False,
            "method": "deflated_sharpe_ratio",
        }

    sr = (mu / std) * math.sqrt(annualization_factor)

    # Sample skewness (Fisher corrected)
    m3 = float(np.mean((r - mu) ** 3))
    skew = m3 / (std ** 3) * (n * n) / ((n - 1) * (n - 2))

    # Sample excess kurtosis (Fisher corrected)
    m4 = float(np.mean((r - mu) ** 4))
    var = std ** 2
    kurt_raw = m4 / (var ** 2)
    kurt = ((n + 1) * kurt_raw - 3 * (n - 1)) * (n - 1) / ((n - 2) * (n - 3))

    # Variance of Sharpe estimator (Bailey & Lopez de Prado 2014, Eq. 4)
    sr_var = (1.0 / n) * (1.0 - skew * sr + (kurt / 4.0) * sr ** 2)
    sr_std = math.sqrt(sr_var) if sr_var > 0 else float("nan")  # NaN-safe BUG-1 fix (Kimi-flagged 2026-05-20)

    # Expected maximum Sharpe under null (mean_sr=0)
    # Uses Euler-Mascheroni corrected order statistic approximation
    num_trials = max(num_trials, 1)
    if num_trials == 1:
        e_max_sr = 0.0
    else:
        euler_mascheroni = 0.5772156649
        z = ((1.0 - euler_mascheroni)
             * _norm_ppf(1.0 - 1.0 / num_trials)
             + euler_mascheroni
             * _norm_ppf(1.0 - 1.0 / (num_trials * math.e)))
        e_max_sr = sr_std * z  # mean_sr = 0 under null

    # DSR = P(SR > E[max SR]) one-sided test
    z_score = (sr - e_max_sr) / sr_std
    dsr_prob = _norm_cdf(z_score)

    return {
        "sharpe": round(sr, 6),
        "dsr_probability": round(dsr_prob, 6),
        "expected_max_sr": round(e_max_sr, 6),
        "pass": bool(dsr_prob >= dsr_threshold),
        "method": "deflated_sharpe_ratio",
    }


# ===================================================================
# Gate 3: Newey-West t-statistic
# ===================================================================

def newey_west_tstat(
    returns: Union[List[float], np.ndarray],
    max_lag: Optional[int] = None,
    significance_level: float = 0.05,
) -> Dict:
    """Compute t-statistic on mean returns with Newey-West HAC adjustment.

    Standard t-tests assume i.i.d. returns, which is violated when returns
    exhibit serial correlation or heteroskedasticity. Newey-West computes
    a heteroskedasticity and autocorrelation consistent (HAC) standard
    error using a Bartlett kernel with automatic lag selection.

    Args:
        returns: Array of periodic strategy returns (e.g. per-trade).
        max_lag: Maximum lag for autocovariance sum. If None, uses
                 floor(4 * (n/100)^(2/9)) per Newey-West (1994).
        significance_level: Two-sided significance level (default 0.05).

    Returns:
        Dict with keys:
            mean_return   — sample mean of returns
            nw_std_error  — Newey-West HAC standard error of the mean
            t_stat        — t-statistic (mean / nw_std_error)
            p_value       — two-sided p-value (normal approximation)
            pass          — True if p_value < significance_level
            max_lag_used  — lag truncation used
            method        — "newey_west"
    """
    r = np.asarray(returns, dtype=np.float64)
    n = len(r)

    if n < 4:
        return {
            "mean_return": float("nan"),
            "nw_std_error": float("nan"),
            "t_stat": float("nan"),
            "p_value": 1.0,
            "pass": False,
            "max_lag_used": 0,
            "method": "newey_west",
        }

    mu = float(np.mean(r))
    e = r - mu  # residuals from mean model

    # Automatic lag selection: Newey-West (1994) rule of thumb
    if max_lag is None:
        max_lag = int(math.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))
    max_lag = max(max_lag, 0)

    # Variance at lag 0 (gamma_0)
    gamma_0 = float(np.dot(e, e)) / n

    # Sum weighted autocovariances (Bartlett kernel)
    nw_var = gamma_0
    for lag in range(1, max_lag + 1):
        weight = 1.0 - lag / (max_lag + 1.0)  # Bartlett weight
        gamma_lag = float(np.dot(e[lag:], e[:-lag])) / n
        nw_var += 2.0 * weight * gamma_lag

    # Ensure positive semi-definiteness
    nw_var = max(nw_var, 1e-20)

    # Standard error of the mean
    nw_se = math.sqrt(nw_var / n)

    if nw_se < 1e-15:
        return {
            "mean_return": mu,
            "nw_std_error": 0.0,
            "t_stat": float("nan"),
            "p_value": 1.0,
            "pass": False,
            "max_lag_used": max_lag,
            "method": "newey_west",
        }

    t_stat = mu / nw_se
    # Two-sided p-value using normal approximation (valid for large n)
    p_value = 2.0 * (1.0 - _norm_cdf(abs(t_stat)))

    return {
        "mean_return": round(mu, 8),
        "nw_std_error": round(nw_se, 8),
        "t_stat": round(t_stat, 4),
        "p_value": round(p_value, 6),
        "pass": bool(p_value < significance_level),
        "max_lag_used": max_lag,
        "method": "newey_west",
    }


# ===================================================================
# Gate 4: Statistical Power Analysis
# ===================================================================

def power_analysis(
    n_trades: int,
    effect_size: Optional[float] = None,
    returns: Optional[Union[List[float], np.ndarray]] = None,
    alpha: float = 0.05,
    power_threshold: float = 0.80,
) -> Dict:
    """Compute statistical power for a one-sample t-test on mean returns.

    Power = P(reject H0 | H1 is true). If power < 0.80, the test is
    underpowered and a non-significant result is inconclusive rather
    than evidence of no effect.

    Effect size is Cohen's d = mean / std. If *returns* are provided,
    effect_size is estimated from the data. Otherwise, supply it directly.

    Args:
        n_trades: Number of trades / observations.
        effect_size: Cohen's d. If None, computed from *returns*.
        returns: Strategy returns (used to estimate effect_size if not given).
        alpha: Significance level (default 0.05).
        power_threshold: Minimum acceptable power (default 0.80).

    Returns:
        Dict with keys:
            effect_size       — Cohen's d used
            n_trades          — sample size
            power             — estimated statistical power
            min_trades_needed — minimum n for power >= power_threshold
            pass              — True if power >= power_threshold
            method            — "power_analysis"
    """
    # Estimate effect size from returns if not provided
    if effect_size is None:
        if returns is None or len(returns) < 2:
            return {
                "effect_size": float("nan"),
                "n_trades": n_trades,
                "power": 0.0,
                "min_trades_needed": None,
                "pass": False,
                "method": "power_analysis",
            }
        r = np.asarray(returns, dtype=np.float64)
        mu = float(np.mean(r))
        std = float(np.std(r, ddof=1))
        if std < 1e-15:
            return {
                "effect_size": 0.0,
                "n_trades": n_trades,
                "power": 0.0,
                "min_trades_needed": None,
                "pass": False,
                "method": "power_analysis",
            }
        effect_size = mu / std

    # Power calculation for one-sample z-test (normal approximation)
    # Under H1, the test statistic ~ N(d*sqrt(n), 1)
    # Power = P(Z > z_alpha - d*sqrt(n))  for one-sided
    # For two-sided: Power = P(|Z| > z_{alpha/2}) under H1
    z_crit = _norm_ppf(1.0 - alpha / 2.0)  # two-sided critical value
    ncp = abs(effect_size) * math.sqrt(max(n_trades, 1))  # non-centrality
    # Power = Phi(ncp - z_crit) + Phi(-ncp - z_crit)
    # The second term is negligible for positive ncp
    power = _norm_cdf(ncp - z_crit) + _norm_cdf(-ncp - z_crit)
    power = min(max(power, 0.0), 1.0)

    # Minimum sample size for desired power
    min_n = _min_sample_size(abs(effect_size), alpha, power_threshold)

    return {
        "effect_size": round(effect_size, 6),
        "n_trades": n_trades,
        "power": round(power, 4),
        "min_trades_needed": min_n,
        "pass": bool(power >= power_threshold),
        "method": "power_analysis",
    }


def _min_sample_size(
    effect_size: float,
    alpha: float = 0.05,
    target_power: float = 0.80,
) -> Optional[int]:
    """Find minimum n for a one-sample z-test to achieve target_power.

    Uses the formula: n = ((z_alpha/2 + z_beta) / d)^2
    where d is Cohen's d and z_beta = Phi^{-1}(target_power).
    """
    if effect_size < 1e-10:
        return None  # infinite samples needed for zero effect
    z_alpha = _norm_ppf(1.0 - alpha / 2.0)
    z_beta = _norm_ppf(target_power)
    n = math.ceil(((z_alpha + z_beta) / effect_size) ** 2)
    return max(n, 2)


# ===================================================================
# Aggregate: Run All Gates
# ===================================================================

def run_all_gates(
    strategy_returns: Union[List[float], np.ndarray],
    num_trials: int = 1,
    p_value: float = 1.0,
    p_values_family: Optional[List[float]] = None,
    annualization_factor: int = 252,
    fdr_alpha: float = 0.05,
    nw_significance: float = 0.05,
    dsr_threshold: float = 0.95,
    power_threshold: float = 0.80,
) -> Dict:
    """Run all four Layer 4 statistical gates and return a summary.

    This is the main entry point for strategy promotion decisions.
    A strategy should pass ALL gates to be considered statistically valid.

    Args:
        strategy_returns: Array of periodic returns for the candidate strategy.
        num_trials: Total number of independent backtests run (for DSR).
        p_value: Raw p-value of the strategy's performance test.
        p_values_family: List of p-values from all tested strategies in the
            family (for BH-FDR). If None, uses [p_value] as a single test.
        annualization_factor: Periods per year (252 daily, 52 weekly).
        fdr_alpha: FDR significance level for BH correction.
        nw_significance: Significance level for Newey-West t-test.
        dsr_threshold: DSR probability threshold.
        power_threshold: Minimum statistical power.

    Returns:
        Dict with keys:
            gates           — dict of individual gate results
            all_passed      — True if all four gates pass
            n_passed        — count of gates passed (0-4)
            summary         — human-readable summary string
    """
    r = np.asarray(strategy_returns, dtype=np.float64)

    # Gate 1: Benjamini-Hochberg FDR
    if p_values_family is None:
        p_values_family = [p_value]
    bh_result = benjamini_hochberg(p_values_family, alpha=fdr_alpha)

    # Gate 2: Deflated Sharpe Ratio
    dsr_result = deflated_sharpe_ratio(
        r, num_trials=num_trials,
        annualization_factor=annualization_factor,
        dsr_threshold=dsr_threshold,
    )

    # Gate 3: Newey-West t-stat
    nw_result = newey_west_tstat(r, significance_level=nw_significance)

    # Gate 4: Power analysis
    pow_result = power_analysis(
        n_trades=len(r),
        returns=r,
        alpha=nw_significance,
        power_threshold=power_threshold,
    )

    gates = {
        "benjamini_hochberg": bh_result,
        "deflated_sharpe": dsr_result,
        "newey_west": nw_result,
        "power_analysis": pow_result,
    }

    passed = [g["pass"] for g in gates.values()]
    n_passed = sum(passed)
    all_passed = all(passed)

    # Build summary
    labels = {
        "benjamini_hochberg": "BH-FDR",
        "deflated_sharpe": "Deflated Sharpe",
        "newey_west": "Newey-West",
        "power_analysis": "Power",
    }
    parts = []
    for key, label in labels.items():
        status = "PASS" if gates[key]["pass"] else "FAIL"
        parts.append(f"{label}={status}")
    summary = f"Layer 4 Gates: {n_passed}/4 passed [{', '.join(parts)}]"

    return {
        "gates": gates,
        "all_passed": all_passed,
        "n_passed": n_passed,
        "summary": summary,
    }


# ===================================================================
# CLI demo
# ===================================================================

if __name__ == "__main__":
    np.random.seed(42)

    # Simulate a strategy with genuine edge
    n_obs = 500
    daily_returns = np.random.normal(0.001, 0.015, n_obs)

    # Simulate a family of 20 strategy p-values (most are noise)
    p_vals = [0.03, 0.12, 0.005, 0.45, 0.78, 0.01, 0.67, 0.34,
              0.91, 0.23, 0.04, 0.56, 0.88, 0.15, 0.009, 0.72,
              0.38, 0.62, 0.07, 0.95]

    result = run_all_gates(
        strategy_returns=daily_returns.tolist(),
        num_trials=200,
        p_value=0.03,
        p_values_family=p_vals,
    )

    print("=" * 60)
    print("Layer 4 Statistical Gates — Demo Run")
    print("=" * 60)
    print(f"\n{result['summary']}\n")

    for gate_name, gate_result in result["gates"].items():
        print(f"--- {gate_name} ---")
        for k, v in gate_result.items():
            if isinstance(v, list) and len(v) > 5:
                print(f"  {k}: [{v[0]:.4f}, {v[1]:.4f}, ... ({len(v)} items)]")
            elif isinstance(v, float):
                print(f"  {k}: {v:.6f}")
            else:
                print(f"  {k}: {v}")
        print()

    print(f"All passed: {result['all_passed']}")
