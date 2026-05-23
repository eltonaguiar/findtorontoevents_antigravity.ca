"""Statistical rigor utilities for the audit system.

Production-grade implementations of hedge-fund-standard statistical tests:
* Bootstrap confidence intervals (standard and block) for Profit Factor,
  Win Rate, Sharpe ratio, or any scalar performance metric.
* Probabilistic Sharpe Ratio (Bailey-Lopez de Prado 2012) -- probability
  that an estimated Sharpe exceeds a benchmark.
* Deflated Sharpe Ratio (Bailey-Lopez de Prado 2014) -- corrects the
  headline Sharpe for the number of independent trials searched.
* Benjamini-Hochberg False Discovery Rate correction for families of
  strategy hypothesis tests.

All functions are pure (no side effects), operate on numpy arrays, and
return JSON-serializable scalars so they can be piped directly into the
dashboard JSON feed.

This module is OPT-IN.  Nothing in the production pick-generation path
imports it yet (per CLAUDE.md Wire-Up Rule).  A follow-up PR will wire
``bootstrap_ci`` into ``audit_trail.metrics.compute_summary`` and
``deflated_sharpe_ratio`` into ``anti_overfit_gate.passed_dsr_check``.

Public API
----------
bootstrap_ci(values, n_bootstrap=1000, confidence=0.95) -> tuple[float, float, float]
probabilistic_sharpe_ratio(returns, benchmark_sharpe=0.0) -> float
deflated_sharpe_ratio(returns, n_trials, skewness, kurtosis) -> float
benjamini_hochberg_fdr(p_values, alpha=0.05) -> tuple[np.ndarray, np.ndarray]
block_bootstrap_ci(values, block_size=None, n_bootstrap=1000) -> tuple[float, float, float]
"""

from __future__ import annotations

import logging
import math
from typing import Sequence

import numpy as np

logger = logging.getLogger(__name__)

__all__ = [
    "bootstrap_ci",
    "probabilistic_sharpe_ratio",
    "deflated_sharpe_ratio",
    "benjamini_hochberg_fdr",
    "block_bootstrap_ci",
]

# ---------------------------------------------------------------------------
# 1. Standard Bootstrap Confidence Interval
# ---------------------------------------------------------------------------


def bootstrap_ci(
    values: Sequence[float] | np.ndarray,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    """Bootstrap percentile confidence interval for any scalar metric.

    Draws ``n_bootstrap`` resamples (with replacement) from *values* and
    computes the empirical ``(1-confidence)/2`` and ``1-(1-confidence)/2``
    quantiles of the bootstrap distribution.

    Parameters
    ----------
    values : 1-D array-like
        Observed metric values (e.g. per-trade Profit Factors, per-strategy
        Win Rates, or daily Sharpe numerators).  Must contain at least 2
        finite elements.
    n_bootstrap : int, default 1000
        Number of bootstrap resamples.  1000 is the AFML minimum for
        stable CIs; 10000 is used in production when CI width matters.
    confidence : float, default 0.95
        Two-sided confidence level.  Must be in ``(0, 1)``.

    Returns
    -------
    tuple(lower_bound, upper_bound, point_estimate)
        All three floats are JSON-serializable.  If the input cannot be
        processed, returns ``(0.0, 0.0, 0.0)`` and logs a warning.

    References
    ----------
    * Efron, B. & Tibshirani, R. (1993). *An Introduction to the
      Bootstrap*.  Chapman & Hall.  Chapter 13.
    * Lopez de Prado, M. (2018). *Advances in Financial Machine Learning*.
      Wiley.  Chapter 13.
    """
    v = np.asarray(values, dtype=np.float64)
    v = v[np.isfinite(v)]

    if v.size < 2:
        logger.warning("bootstrap_ci: need >= 2 finite values, got %d", v.size)
        return 0.0, 0.0, 0.0
    if not (0.0 < confidence < 1.0):
        logger.warning("bootstrap_ci: confidence must be in (0,1), got %f", confidence)
        return 0.0, 0.0, 0.0
    if n_bootstrap < 1:
        logger.warning("bootstrap_ci: n_bootstrap must be >= 1, got %d", n_bootstrap)
        return 0.0, 0.0, 0.0

    point_estimate = float(np.mean(v))
    rng = np.random.default_rng()
    n = v.size
    boot_means = np.empty(n_bootstrap, dtype=np.float64)
    for i in range(n_bootstrap):
        sample = rng.choice(v, size=n, replace=True)
        boot_means[i] = sample.mean()

    alpha_half = (1.0 - confidence) / 2.0
    lower = float(np.quantile(boot_means, alpha_half))
    upper = float(np.quantile(boot_means, 1.0 - alpha_half))
    return lower, upper, point_estimate


# ---------------------------------------------------------------------------
# 2. Block Bootstrap CI (time-series dependence)
# ---------------------------------------------------------------------------


def block_bootstrap_ci(
    values: Sequence[float] | np.ndarray,
    block_size: int | None = None,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    """Block-bootstrap confidence interval for autocorrelated series.

    Resamples contiguous *blocks* (with replacement) rather than individual
    observations, preserving the local serial dependence structure in
    financial returns.  If ``block_size`` is not supplied it is set to the
    integer ceiling of ``n^(1/3)``, the Politis-White rule-of-thumb.

    Parameters
    ----------
    values : 1-D array-like
        Time-ordered observations (e.g. daily strategy returns).  Must
        contain at least ``2 * block_size`` finite elements.
    block_size : int or None, default None
        Block length in observation units.  None => ``ceil(n^(1/3))``.
    n_bootstrap : int, default 1000
        Number of bootstrap resamples.
    confidence : float, default 0.95
        Two-sided confidence level in ``(0, 1)``.

    Returns
    -------
    tuple(lower_bound, upper_bound, point_estimate)
        Degenerate inputs return ``(0.0, 0.0, 0.0)`` with a logged warning.

    References
    ----------
    * Kunsch, H. R. (1989). The Jackknife and the Bootstrap for General
      Stationary Observations. *Annals of Statistics*, 17(3), 1217-1241.
    * Politis, D. N. & White, H. (2004). Automatic Block-Length Selection
      for the Dependent Bootstrap. *Econometric Reviews*, 23(1), 53-70.
    """
    v = np.asarray(values, dtype=np.float64)
    v = v[np.isfinite(v)]
    n = v.size

    if block_size is None:
        block_size = max(1, int(math.ceil(n ** (1.0 / 3.0))))
    else:
        block_size = max(1, int(block_size))

    if n < 2 * block_size:
        logger.warning(
            "block_bootstrap_ci: need >= %d obs for block_size=%d, got %d",
            2 * block_size,
            block_size,
            n,
        )
        return 0.0, 0.0, 0.0
    if not (0.0 < confidence < 1.0):
        logger.warning("block_bootstrap_ci: confidence must be in (0,1)")
        return 0.0, 0.0, 0.0
    if n_bootstrap < 1:
        return 0.0, 0.0, 0.0

    point_estimate = float(v.mean())
    rng = np.random.default_rng()
    n_blocks = int(math.ceil(n / block_size))
    boot_means = np.empty(n_bootstrap, dtype=np.float64)

    for i in range(n_bootstrap):
        blocks: list[np.ndarray] = []
        for _ in range(n_blocks):
            start = rng.integers(0, n - block_size + 1)
            blocks.append(v[start : start + block_size])
        concatenated = np.concatenate(blocks)[:n]
        boot_means[i] = concatenated.mean()

    alpha_half = (1.0 - confidence) / 2.0
    lower = float(np.quantile(boot_means, alpha_half))
    upper = float(np.quantile(boot_means, 1.0 - alpha_half))
    return lower, upper, point_estimate


# ---------------------------------------------------------------------------
# 3. Probabilistic Sharpe Ratio (Bailey-Lopez de Prado 2012)
# ---------------------------------------------------------------------------


def probabilistic_sharpe_ratio(
    returns: Sequence[float] | np.ndarray,
    benchmark_sharpe: float = 0.0,
) -> float:
    """Probability that the true Sharpe ratio exceeds a benchmark.

    PSR(SR*) = Z[ (SR - SR*) / sqrt(V(SR)) ]

    where SR is the estimated Sharpe, SR* is the benchmark (typically 0),
    and V(SR) is the variance of the Sharpe estimator adjusted for
    non-normality (skewness and kurtosis).

    A PSR >= 0.95 is the standard Lopez de Prado production threshold:
    we are 95% confident the strategy has genuine positive risk-adjusted
    returns after accounting for estimation noise.

    Parameters
    ----------
    returns : 1-D array-like
        Periodic (e.g. daily) returns of the strategy.  Must contain
        >= 4 finite observations.
    benchmark_sharpe : float, default 0.0
        The null-hypothesis Sharpe to test against.  0.0 tests "better
        than cash"; 0.5 tests "better than a decent CTA".

    Returns
    -------
    float
        PSR in ``[0, 1]``.  Degenerate inputs return 0.0 with a warning.

    References
    ----------
    * Bailey, D. H. & Lopez de Prado, M. (2012). The Sharpe Ratio
      Efficient Frontier. *Risk*, 25(2), 91-94.
    * Lopez de Prado, M. (2018). *Advances in Financial Machine Learning*.
      Wiley.  Chapter 14, Equation 14.1.
    """
    r = np.asarray(returns, dtype=np.float64)
    r = r[np.isfinite(r)]
    n = r.size

    if n < 4:
        logger.warning("psr: need >= 4 observations, got %d", n)
        return 0.0

    mu = r.mean()
    sd = r.std(ddof=1)
    if sd < 1e-12:
        logger.warning("psr: zero variance returns")
        return 1.0 if mu > benchmark_sharpe else 0.0

    sharpe = mu / sd

    # Non-normality adjusted variance of the Sharpe estimator (Lo 2002)
    z = (r - mu) / sd
    skew = float(((n * n) / ((n - 1) * (n - 2))) * np.mean(z ** 3))
    kurt_raw = float(np.mean(z ** 4))
    kurt = float(
        ((n + 1) * kurt_raw - 3.0 * (n - 1))
        * (n - 1)
        / ((n - 2) * (n - 3))
    )

    sr_var = (1.0 / n) * (
        1.0 - skew * sharpe + (kurt / 4.0) * sharpe * sharpe
    )
    sr_std = math.sqrt(max(sr_var, 1e-16))

    if sr_std < 1e-12:
        return 1.0 if sharpe > benchmark_sharpe else 0.0

    z_score = (sharpe - benchmark_sharpe) / sr_std
    return float(_norm_cdf(z_score))


# ---------------------------------------------------------------------------
# 4. Deflated Sharpe Ratio (Bailey-Lopez de Prado 2014)
# ---------------------------------------------------------------------------


def deflated_sharpe_ratio(
    returns: Sequence[float] | np.ndarray,
    n_trials: int,
    skewness: float | None = None,
    kurtosis: float | None = None,
) -> float:
    """Deflated Sharpe Ratio -- Sharpe corrected for multiple testing.

    DSR = P(SR > E[max(SR_n)] | n_trials, skew, kurtosis)

    When many strategies are backtested and the best one is selected,
    the headline Sharpe is upward-biased.  DSR estimates the probability
    that the *selected* Sharpe is still statistically significant after
    accounting for the fact that it was the maximum of ``n_trials``
    independent draws from the null distribution.

    A DSR >= 0.95 means the selected strategy survives the multiplicity
    correction at the 5% level.

    Parameters
    ----------
    returns : 1-D array-like
        Periodic returns of the *selected* strategy.  Must contain >= 4
        finite observations.
    n_trials : int
        Number of independent strategy configurations tested.  Must be >= 1.
    skewness : float or None, default None
        Pre-computed Fisher-adjusted skewness.  If None, estimated from
        *returns*.
    kurtosis : float or None, default None
        Pre-computed Fisher-adjusted excess kurtosis.  If None, estimated
        from *returns*.

    Returns
    -------
    float
        DSR probability in ``[0, 1]``.  Degenerate inputs return 0.0.

    References
    ----------
    * Bailey, D. H. & Lopez de Prado, M. (2014). The Deflated Sharpe
      Ratio: Correcting for Selection Bias, Backtest Overfitting and
      Non-Normality. *Journal of Portfolio Management*, 40(5), 94-107.
    * Lopez de Prado, M. (2018). *Advances in Financial Machine Learning*.
      Wiley.  Chapter 14, Equation 14.5.
    """
    r = np.asarray(returns, dtype=np.float64)
    r = r[np.isfinite(r)]
    n = r.size

    if n < 4:
        logger.warning("dsr: need >= 4 observations, got %d", n)
        return 0.0
    if n_trials < 1:
        logger.warning("dsr: n_trials must be >= 1, got %d", n_trials)
        return 0.0

    mu = r.mean()
    sd = r.std(ddof=1)
    if sd < 1e-12:
        logger.warning("dsr: zero variance returns")
        return 1.0 if mu > 0.0 else 0.0

    sharpe = mu / sd

    if skewness is None or kurtosis is None:
        z = (r - mu) / sd
        skewness = float(((n * n) / ((n - 1) * (n - 2))) * np.mean(z ** 3))
        kurt_raw = float(np.mean(z ** 4))
        kurtosis = float(
            ((n + 1) * kurt_raw - 3.0 * (n - 1))
            * (n - 1)
            / ((n - 2) * (n - 3))
        )

    # Variance of Sharpe estimator (non-normality adjusted)
    sr_var = (1.0 / n) * (
        1.0 - skewness * sharpe + (kurtosis / 4.0) * sharpe * sharpe
    )
    sr_std = math.sqrt(max(sr_var, 1e-16))

    # Expected max SR under the null (mean=0, variance=sr_var)
    if n_trials == 1:
        e_max = 0.0
    else:
        gamma = 0.5772156649  # Euler-Mascheroni constant
        e_max = sr_std * (
            (1.0 - gamma) * _norm_ppf(1.0 - 1.0 / n_trials)
            + gamma * _norm_ppf(1.0 - 1.0 / (n_trials * math.e))
        )

    return float(_norm_cdf((sharpe - e_max) / sr_std))


# ---------------------------------------------------------------------------
# 5. Benjamini-Hochberg False Discovery Rate
# ---------------------------------------------------------------------------


def benjamini_hochberg_fdr(
    p_values: Sequence[float] | np.ndarray,
    alpha: float = 0.05,
) -> tuple[np.ndarray, np.ndarray]:
    """Benjamini-Hochberg FDR correction for multiple hypothesis tests.

    Controls the expected proportion of falsely rejected null hypotheses
    among all rejected nulls.  More powerful than Bonferroni when testing
    many strategies simultaneously because it allows a controlled rate of
    false discoveries rather than demanding zero.

    Parameters
    ----------
    p_values : 1-D array-like
        Raw p-values from m independent hypothesis tests.  Must all be in
        ``[0, 1]``.  NaN values are treated as 1.0 (never rejected).
    alpha : float, default 0.05
        Target false discovery rate.  Must be in ``(0, 1)``.

    Returns
    -------
    rejected : np.ndarray, shape (m,)
        Boolean array; ``rejected[i]`` is True iff null hypothesis i is
        rejected at FDR = alpha.
    p_adjusted : np.ndarray, shape (m,)
        BH-adjusted p-values (q-values).  These are monotonic and can be
        thresholded at any level without re-running the procedure.

    References
    ----------
    * Benjamini, Y. & Hochberg, Y. (1995). Controlling the False
      Discovery Rate: A Practical and Powerful Approach to Multiple
      Testing. *Journal of the Royal Statistical Society*, Series B,
      57(1), 289-300.
    * Storey, J. D. (2003). The Positive False Discovery Rate: A Bayesian
      Interpretation and the q-value. *Annals of Statistics*, 31(6),
      2013-2035.
    """
    p = np.asarray(p_values, dtype=np.float64)
    if p.size == 0:
        return np.array([], dtype=bool), np.array([], dtype=np.float64)

    if not (0.0 < alpha < 1.0):
        logger.warning("bh_fdr: alpha must be in (0,1), got %f; using 0.05", alpha)
        alpha = 0.05

    # Sanitize: clip to [0,1] and replace NaN with 1.0
    p = np.where(np.isnan(p), 1.0, np.clip(p, 0.0, 1.0))

    m = p.size
    order = np.argsort(p)
    p_sorted = p[order]

    # BH procedure: find largest k such that p_k <= (k/m) * alpha
    ranks = np.arange(1, m + 1)
    thresholds = (ranks / m) * alpha
    below = p_sorted <= thresholds

    if not np.any(below):
        rejected_sorted = np.zeros(m, dtype=bool)
        k_max = 0
    else:
        k_max = int(np.max(np.where(below)[0]) + 1)
        rejected_sorted = np.zeros(m, dtype=bool)
        rejected_sorted[:k_max] = True

    # Adjusted p-values (q-values) via the Benjamini-Yekutieli step-up
    p_adjusted_sorted = np.minimum.accumulate(
        np.minimum(p_sorted * m / ranks, 1.0)[::-1]
    )[::-1]

    # Unsort back to original order
    rejected = np.empty(m, dtype=bool)
    p_adjusted = np.empty(m, dtype=np.float64)
    rejected[order] = rejected_sorted
    p_adjusted[order] = p_adjusted_sorted

    return rejected, p_adjusted


# ---------------------------------------------------------------------------
# Internal: standard normal CDF and PPF (no scipy dependency)
# ---------------------------------------------------------------------------


def _norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _norm_ppf(p: float) -> float:
    """Standard normal inverse CDF -- Acklam (2003) approximation.

    Accurate to ~1.5e-9 over the entire domain.  Falls back to the
    extremes ``-inf`` / ``inf`` for p <= 0 or p >= 1.
    """
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf

    # Acklam coefficients
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]

    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        num = ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
        den = (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        return num / den

    if p <= p_high:
        q = p - 0.5
        r = q * q
        num = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
        den = (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
        return num / den

    q = math.sqrt(-2.0 * math.log(1.0 - p))
    num = ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
    den = (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
    return -num / den
