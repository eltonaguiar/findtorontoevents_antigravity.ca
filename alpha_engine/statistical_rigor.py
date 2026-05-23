"""
Statistical Rigor — Bootstrap CIs, Multiple-Testing Correction, PSR
====================================================================

The hedge-fund-grade statistical layer for `findtorontoevents.ca/audit`.
Adds the three things the audit page is missing per the plan TL;DR:

    1. **Bootstrap confidence intervals** for any per-trade metric
       (Profit Factor, Win Rate, Sharpe, Sortino, MAR, ...). Uses
       paired-bootstrap resampling so CIs respect trade-count noise.

    2. **Benjamini-Hochberg FDR correction** (López de Prado deflation
       move) — when N source-systems are tested at α=0.05, ~5%
       false-discovery rate is *guaranteed* without correction. BH
       gives the largest k such that p_(k) ≤ k/N · α and rejects only
       those.

    3. **Probabilistic Sharpe Ratio (PSR, Bailey & López de Prado 2012)**
       — the probability that the *true* Sharpe exceeds a benchmark
       given finite-sample skew/kurtosis. Companion to the existing
       `deflated_sharpe.py` (DSR is PSR with multiple-testing baked
       in via the Sharpe-Ratio Index Factor).

Design notes
------------
* Pure-Python fallbacks for every scipy dependency; the audit pipeline
  must run on minimal CI containers.
* Every public function is **stateless and side-effect free** so it can
  be called from `audit_trail/dashboard_generator.py` mid-render
  without leaking I/O.
* All functions accept either a `list[float]` of per-trade returns or
  a `numpy.ndarray`. They never mutate the input.
* No randomness without an explicit `seed=` parameter so dashboard
  numbers are reproducible.

References
----------
* Efron & Tibshirani (1993) "An Introduction to the Bootstrap".
* Benjamini & Hochberg (1995) "Controlling the False Discovery Rate".
* Bailey, D.H. & López de Prado, M. (2012) "The Sharpe Ratio Efficient
  Frontier", Journal of Risk 15(2).
* López de Prado, M. (2018) "Advances in Financial Machine Learning",
  ch. 7 (CPCV) and ch. 14 (deflated metrics).

Wiring plan
-----------
This module is an **opt-in sidecar** today. Target production caller
is `audit_trail/dashboard_generator.py` (Week 2 of the plan): wrap
each per-class PF/WR/Sharpe with `bootstrap_ci(...)` and surface the
[5th, 95th] band on the audit page.
"""

from __future__ import annotations

import math
import random
from typing import Callable, Iterable, Sequence, Tuple

try:
    import numpy as _np
    _HAS_NUMPY = True
except ImportError:  # pragma: no cover - numpy is in requirements but be defensive
    _np = None
    _HAS_NUMPY = False

try:
    from scipy.stats import norm as _scipy_norm  # type: ignore

    def _norm_cdf(x: float) -> float:
        return float(_scipy_norm.cdf(x))

    def _norm_ppf(p: float) -> float:
        """Standard normal inverse CDF (quantile function).

        Used by :func:`deflated_sharpe_ratio` for E[max SR] under the null.
        Falls back to Acklam's approximation if scipy is unavailable.
        """
        return float(_scipy_norm.ppf(p))

except ImportError:  # pragma: no cover - scipy fallback path
    def _norm_cdf(x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def _norm_ppf(p: float) -> float:
        """Standard normal inverse CDF — Acklam (2003) approximation.

        Accurate to ~1.5e-9 over the entire domain. Falls back to ±inf
        for p <= 0 or p >= 1. Source: Peter J. Acklam, "An algorithm for
        computing the inverse normal cumulative distribution function".
        """
        if p <= 0.0:
            return -math.inf
        if p >= 1.0:
            return math.inf

        # Acklam coefficients
        a = (-3.969683028665376e01, 2.209460984245205e02,
             -2.759285104469687e02, 1.383577518672690e02,
             -3.066479806614716e01, 2.506628277459239e00)
        b = (-5.447609879822406e01, 1.615858368580409e02,
             -1.556989798598866e02, 6.680131188771972e01,
             -1.328068155288572e01)
        c = (-7.784894002430293e-03, -3.223964580411365e-01,
             -2.400758277161838e00, -2.549732539343734e00,
             4.374664141464968e00, 2.938163982698783e00)
        d = (7.784695709041462e-03, 3.224671290700398e-01,
             2.445134137142996e00, 3.754408661907416e00)

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


# ---------------------------------------------------------------------------
# Per-trade metric primitives
# ---------------------------------------------------------------------------
def profit_factor(returns: Sequence[float]) -> float:
    """Sum of wins divided by abs(sum of losses).

    Returns ``float('inf')`` if there are wins but no losses (the
    convention used elsewhere in the audit). Returns ``0.0`` if the
    series is empty or has no wins.
    """
    if not returns:
        return 0.0
    wins = sum(r for r in returns if r > 0)
    losses = sum(r for r in returns if r < 0)
    if losses == 0:
        return float("inf") if wins > 0 else 0.0
    return wins / abs(losses)


def win_rate(returns: Sequence[float]) -> float:
    """Fraction of strictly-positive returns."""
    if not returns:
        return 0.0
    n_win = sum(1 for r in returns if r > 0)
    return n_win / len(returns)


def sharpe(returns: Sequence[float], periods_per_year: float = 252.0) -> float:
    """Per-trade Sharpe annualised by sqrt(periods_per_year).

    Treats the input as a series of *per-trade* returns. Use
    ``periods_per_year=252`` for daily, ``365`` for crypto-daily, or
    the average trades-per-year for trade-stream Sharpe.
    """
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    if var <= 0:
        return 0.0
    sd = math.sqrt(var)
    return (mean / sd) * math.sqrt(periods_per_year)


# ---------------------------------------------------------------------------
# Bootstrap confidence intervals
# ---------------------------------------------------------------------------
def bootstrap_ci(
    returns: Sequence[float],
    metric: Callable[[Sequence[float]], float] = profit_factor,
    n_resamples: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """Paired bootstrap confidence interval for any per-trade metric.

    Args:
        returns: per-trade return series (e.g. ``pnl_pct`` from closed picks).
        metric: callable returning a scalar from a return series.
            Default is :func:`profit_factor`. Pass :func:`win_rate`,
            :func:`sharpe`, or any custom callable.
        n_resamples: bootstrap replicates. 1000 is the plan default
            (Efron & Tibshirani recommend 1000-2000 for percentile CIs).
        alpha: total tail probability. ``0.05`` returns the
            [2.5th, 97.5th] band; ``0.10`` returns [5th, 95th]
            (the plan default for the audit page).
        seed: RNG seed for reproducibility — same input + same seed
            always yields the same band.

    Returns:
        (point_estimate, lower, upper) — the metric on the original
        sample, plus the lower/upper percentile bounds.

    Notes:
        * Empty / singleton inputs return ``(metric(returns), nan, nan)``
          rather than raising — dashboards must never crash on a thin
          source-system.
        * Infinite point estimates (e.g. PF with zero losses) are
          preserved; their CIs may also be infinite.
    """
    point = metric(returns)
    n = len(returns)
    if n < 2:
        return (point, float("nan"), float("nan"))

    rng = random.Random(seed)
    if _HAS_NUMPY:
        arr = _np.asarray(returns, dtype=float)
        nprng = _np.random.default_rng(seed)
        idx = nprng.integers(0, n, size=(n_resamples, n))
        replicates = [metric(arr[i].tolist()) for i in idx]
    else:  # pragma: no cover - exercised in numpy-less environments
        replicates = []
        for _ in range(n_resamples):
            sample = [returns[rng.randrange(n)] for _ in range(n)]
            replicates.append(metric(sample))

    finite = [r for r in replicates if math.isfinite(r)]
    if not finite:
        return (point, float("nan"), float("nan"))
    finite.sort()
    lo_idx = int(math.floor((alpha / 2.0) * len(finite)))
    hi_idx = int(math.ceil((1.0 - alpha / 2.0) * len(finite))) - 1
    lo_idx = max(0, min(lo_idx, len(finite) - 1))
    hi_idx = max(0, min(hi_idx, len(finite) - 1))
    return (point, finite[lo_idx], finite[hi_idx])


# ---------------------------------------------------------------------------
# Benjamini-Hochberg FDR correction
# ---------------------------------------------------------------------------
def benjamini_hochberg(
    p_values: Sequence[float],
    fdr: float = 0.05,
) -> list[bool]:
    """Benjamini-Hochberg FDR step-up procedure.

    Args:
        p_values: per-test p-values (e.g. one per source-system from
            a one-sided t-test of mean PnL > 0).
        fdr: desired false-discovery rate (default 5%).

    Returns:
        A list of ``bool`` aligned to ``p_values`` — ``True`` for
        tests that survive the BH cutoff.

    Algorithm:
        1. Sort p-values ascending.
        2. Find the largest k such that p_(k) ≤ (k / N) · fdr.
        3. Reject the null for all tests with p ≤ p_(k).
    """
    n = len(p_values)
    if n == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda t: t[1])
    # Find largest k satisfying the BH inequality
    k_star = -1
    for k, (_, p) in enumerate(indexed, start=1):
        if p <= (k / n) * fdr:
            k_star = k
    if k_star < 0:
        return [False] * n
    cutoff = indexed[k_star - 1][1]
    return [p <= cutoff for p in p_values]


# ---------------------------------------------------------------------------
# Probabilistic Sharpe Ratio (PSR)
# ---------------------------------------------------------------------------
def _moments(returns: Sequence[float]) -> tuple[float, float, float, float]:
    """Return (mean, std, skew, excess_kurtosis) using sample formulas."""
    n = len(returns)
    mean = sum(returns) / n
    centered = [r - mean for r in returns]
    m2 = sum(c * c for c in centered) / n
    if m2 <= 0:
        return (mean, 0.0, 0.0, 0.0)
    sd = math.sqrt(m2)
    m3 = sum(c ** 3 for c in centered) / n
    m4 = sum(c ** 4 for c in centered) / n
    skew = m3 / (sd ** 3)
    excess_kurt = m4 / (m2 ** 2) - 3.0
    # Use sample std (n-1) for downstream Sharpe consistency
    sd_sample = math.sqrt(sum(c * c for c in centered) / (n - 1)) if n > 1 else 0.0
    return (mean, sd_sample, skew, excess_kurt)


def probabilistic_sharpe_ratio(
    returns: Sequence[float],
    sharpe_benchmark: float = 0.0,
    periods_per_year: float = 252.0,
) -> float:
    """Probabilistic Sharpe Ratio (Bailey & López de Prado 2012).

    PSR = Pr( true_SR > sharpe_benchmark | observed_SR )
        = Φ( (SR_obs - SR_*) · sqrt(n - 1) /
             sqrt(1 - skew·SR_obs + ((kurt - 1)/4)·SR_obs²) )

    where SR_obs and SR_* are *non-annualised* per-trade Sharpe values.

    Args:
        returns: per-trade returns.
        sharpe_benchmark: annualised benchmark Sharpe (default 0).
        periods_per_year: annualisation factor (default 252 for daily).

    Returns:
        Probability in [0, 1] that the true Sharpe exceeds the
        benchmark. Returns 0.5 if the input is too thin to estimate.
    """
    n = len(returns)
    if n < 4:
        return 0.5
    mean, sd, skew, excess_kurt = _moments(returns)
    if sd <= 0:
        return 0.5
    sr_obs = mean / sd  # per-trade
    sr_bench = sharpe_benchmark / math.sqrt(periods_per_year)
    denom = 1.0 - skew * sr_obs + ((excess_kurt) / 4.0) * (sr_obs ** 2)
    if denom <= 0:
        return 0.5
    z = (sr_obs - sr_bench) * math.sqrt(n - 1) / math.sqrt(denom)
    return _norm_cdf(z)


# ---------------------------------------------------------------------------
# Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014)
# Cherry-picked from Kimi's hedge-fund-uplift work 2026-05-02. Genuinely missing
# from the original module — required to deflate Sharpe estimates by the
# multiple-trials selection bias inherent in any backtest sweep.
# ---------------------------------------------------------------------------
def deflated_sharpe_ratio(
    returns: Sequence[float],
    n_trials: int,
    skewness: float | None = None,
    kurtosis: float | None = None,
) -> float:
    """Deflated Sharpe Ratio — Sharpe corrected for multiple-testing selection bias.

    DSR = P(SR > E[max(SR_n)] | n_trials, skew, kurtosis)

    When many strategies are backtested and the best one is selected, the
    headline Sharpe is upward-biased. DSR estimates the probability that the
    *selected* Sharpe is statistically significant after accounting for the
    fact that it was the maximum of ``n_trials`` independent draws from the
    null distribution.

    A DSR >= 0.95 means the selected strategy survives the multiplicity
    correction at the 5% level.

    Parameters
    ----------
    returns : 1-D sequence
        Periodic returns of the *selected* strategy. Must contain >= 4 finite
        observations.
    n_trials : int
        Number of independent strategy configurations tested. Must be >= 1.
    skewness : float or None, default None
        Pre-computed Fisher-adjusted skewness. If None, estimated from returns.
    kurtosis : float or None, default None
        Pre-computed Fisher-adjusted excess kurtosis. If None, estimated.

    Returns
    -------
    float
        DSR probability in ``[0, 1]``. Degenerate inputs return 0.0.

    References
    ----------
    * Bailey, D. H. & Lopez de Prado, M. (2014). The Deflated Sharpe Ratio:
      Correcting for Selection Bias, Backtest Overfitting and Non-Normality.
      *Journal of Portfolio Management*, 40(5), 94-107.
    * Lopez de Prado, M. (2018). *Advances in Financial Machine Learning*.
      Wiley. Chapter 14, Equation 14.5.
    """
    # Filter to finite values (preserve order; pure-Python implementation)
    r = [x for x in returns if isinstance(x, (int, float)) and math.isfinite(x)]
    n = len(r)

    if n < 4:
        return 0.0
    if n_trials < 1:
        return 0.0

    mu = sum(r) / n
    var = sum((x - mu) ** 2 for x in r) / (n - 1)  # ddof=1
    sd = math.sqrt(var)
    if sd < 1e-12:
        return 1.0 if mu > 0.0 else 0.0

    sharpe = mu / sd

    if skewness is None or kurtosis is None:
        # Fisher-Pearson moments on standardized residuals
        z = [(x - mu) / sd for x in r]
        m3 = sum(zz ** 3 for zz in z) / n
        m4 = sum(zz ** 4 for zz in z) / n
        if skewness is None:
            skewness = (n * n) / ((n - 1) * (n - 2)) * m3
        if kurtosis is None:
            # Excess kurtosis (Fisher), bias-corrected
            kurtosis = ((n + 1) * m4 - 3.0 * (n - 1)) * (n - 1) / ((n - 2) * (n - 3))

    # Variance of Sharpe estimator (non-normality adjusted).
    # Floor at 1/n (i.i.d. normal baseline) to prevent sr_var <= 0 when the
    # non-normality terms over-correct for highly regular return sequences.
    sr_var = (1.0 / n) * (1.0 - skewness * sharpe + (kurtosis / 4.0) * sharpe * sharpe)
    sr_var = max(sr_var, 1.0 / n)  # never less than the i.i.d.-normal lower bound
    sr_std = math.sqrt(sr_var)

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
# Convenience: full per-class statistical block for the audit page
# ---------------------------------------------------------------------------
def audit_metrics_block(
    returns: Sequence[float],
    *,
    n_resamples: int = 1000,
    alpha: float = 0.10,
    seed: int = 42,
    periods_per_year: float = 252.0,
) -> dict:
    """One-call helper that produces the dashboard-ready metric block.

    Returns a dict shaped for direct JSON serialisation into
    ``dashboard_payload.json``::

        {
          "n": 381,
          "profit_factor": {"point": 1.385, "lo": 1.05, "hi": 1.71},
          "win_rate":      {"point": 0.523, "lo": 0.48, "hi": 0.57},
          "sharpe":        {"point": 0.85,  "lo": 0.41, "hi": 1.27},
          "psr_vs_zero":   0.962
        }
    """
    pf_point, pf_lo, pf_hi = bootstrap_ci(
        returns, profit_factor, n_resamples=n_resamples, alpha=alpha, seed=seed
    )
    wr_point, wr_lo, wr_hi = bootstrap_ci(
        returns, win_rate, n_resamples=n_resamples, alpha=alpha, seed=seed + 1
    )
    sh_point, sh_lo, sh_hi = bootstrap_ci(
        returns,
        lambda r: sharpe(r, periods_per_year=periods_per_year),
        n_resamples=n_resamples,
        alpha=alpha,
        seed=seed + 2,
    )
    return {
        "n": len(returns),
        "profit_factor": {"point": pf_point, "lo": pf_lo, "hi": pf_hi},
        "win_rate":      {"point": wr_point, "lo": wr_lo, "hi": wr_hi},
        "sharpe":        {"point": sh_point, "lo": sh_lo, "hi": sh_hi},
        "psr_vs_zero":   probabilistic_sharpe_ratio(
            returns, sharpe_benchmark=0.0, periods_per_year=periods_per_year
        ),
    }


__all__ = [
    "audit_metrics_block",
    "benjamini_hochberg",
    "bootstrap_ci",
    "deflated_sharpe_ratio",
    "probabilistic_sharpe_ratio",
    "profit_factor",
    "sharpe",
    "win_rate",
]
