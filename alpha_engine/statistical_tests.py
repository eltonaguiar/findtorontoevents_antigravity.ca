#!/usr/bin/env python3
"""
Statistical Validation Tests for Backtest Analysis Pipeline
===========================================================
Implements institutional-grade statistical tests used by top quant firms
(AlgoXpert, Renaissance, Two Sigma) for validating strategy edge.

Tests:
  - Shapiro-Wilk: Are returns normally distributed?
  - Levene's: Is variance stable across time windows?
  - One-way ANOVA: Are mean returns significantly different across windows?
  - Welch's ANOVA: ANOVA without equal-variance assumption
  - Kruskal-Wallis: Non-parametric alternative when normality fails

Uses scipy.stats when available; falls back to numpy-only approximations.
Windows UTF-8 safe.
"""

import math
import os
import sys
from typing import Optional

import numpy as np

# Windows UTF-8 fix
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8")
            except Exception:
                pass

# Try scipy; degrade gracefully if unavailable
try:
    from scipy import stats as sp_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# Default significance level
ALPHA = 0.05

# Minimum samples required for each test
MIN_SAMPLES_SHAPIRO = 8
MIN_SAMPLES_PER_GROUP = 3
MIN_GROUPS = 2


# ---------------------------------------------------------------------------
# Shapiro-Wilk: normality of return distribution
# ---------------------------------------------------------------------------
def shapiro_wilk_test(pnls: list, alpha: float = ALPHA) -> dict:
    """Test whether trade PnLs follow a normal distribution.

    Significant result (p < alpha) means returns are NOT normal.
    Financial returns are almost never normal (fat tails), so a
    significant result is expected and informs which downstream
    tests are appropriate (parametric vs non-parametric).

    Args:
        pnls: list of float PnL percentages
        alpha: significance level (default 0.05)

    Returns:
        dict with statistic, p_value, normal (bool), interpretation
    """
    arr = np.array([p for p in pnls if p is not None and np.isfinite(p)], dtype=float)
    if len(arr) < MIN_SAMPLES_SHAPIRO:
        return {
            "test": "shapiro_wilk",
            "statistic": None,
            "p_value": None,
            "normal": None,
            "pass": None,
            "n": len(arr),
            "interpretation": f"Insufficient data ({len(arr)} < {MIN_SAMPLES_SHAPIRO})",
        }

    if HAS_SCIPY:
        # scipy caps at 5000 samples; subsample if needed
        test_arr = arr[:5000] if len(arr) > 5000 else arr
        stat, p_value = sp_stats.shapiro(test_arr)
    else:
        stat, p_value = _shapiro_fallback(arr)

    is_normal = p_value >= alpha
    return {
        "test": "shapiro_wilk",
        "statistic": round(float(stat), 6),
        "p_value": round(float(p_value), 6),
        "normal": is_normal,
        "pass": True,  # informational — not a pass/fail gate
        "n": len(arr),
        "interpretation": (
            "Returns appear normally distributed (p >= {:.2f})".format(alpha)
            if is_normal
            else "Returns are NOT normal (fat tails likely) — use non-parametric tests"
        ),
    }


def _shapiro_fallback(arr: np.ndarray) -> tuple:
    """Approximate normality check using skewness + kurtosis (D'Agostino-like)."""
    n = len(arr)
    if n < 8:
        return (0.0, 1.0)
    mean = np.mean(arr)
    std = np.std(arr, ddof=1)
    if std < 1e-12:
        return (1.0, 1.0)
    z = (arr - mean) / std
    skew = float(np.mean(z ** 3))
    kurt = float(np.mean(z ** 4)) - 3.0
    # Jarque-Bera statistic as proxy
    jb = (n / 6.0) * (skew ** 2 + (kurt ** 2) / 4.0)
    # Approximate p-value from chi-squared(2)
    p_value = math.exp(-jb / 2.0) if jb < 100 else 0.0
    w_stat = max(0.0, 1.0 - jb / n)  # pseudo W-statistic
    return (w_stat, min(1.0, p_value))


# ---------------------------------------------------------------------------
# Levene's test: homogeneity of variance across windows
# ---------------------------------------------------------------------------
def levenes_test(window_pnl_arrays: list, alpha: float = ALPHA) -> dict:
    """Test whether variance is stable across time windows.

    Significant result (p < alpha) means variance is NOT equal across
    windows — the strategy behaves inconsistently over time.

    Args:
        window_pnl_arrays: list of lists, each containing PnL values for one window
        alpha: significance level

    Returns:
        dict with statistic, p_value, equal_variance (bool), interpretation
    """
    groups = _filter_groups(window_pnl_arrays)
    if len(groups) < MIN_GROUPS:
        return _insufficient_groups_result("levenes", len(groups))

    if HAS_SCIPY:
        stat, p_value = sp_stats.levene(*groups, center="median")
    else:
        stat, p_value = _levene_fallback(groups)

    equal_var = p_value >= alpha
    return {
        "test": "levenes",
        "statistic": round(float(stat), 6),
        "p_value": round(float(p_value), 6),
        "equal_variance": equal_var,
        "pass": equal_var,
        "n_groups": len(groups),
        "group_sizes": [len(g) for g in groups],
        "interpretation": (
            "Variance is stable across windows (good consistency)"
            if equal_var
            else "Variance differs across windows — strategy may be unstable"
        ),
    }


def _levene_fallback(groups: list) -> tuple:
    """Pure-numpy Levene's test (median-centered)."""
    k = len(groups)
    N = sum(len(g) for g in groups)
    z_groups = []
    for g in groups:
        arr = np.array(g)
        median = np.median(arr)
        z_groups.append(np.abs(arr - median))

    z_bar = np.mean(np.concatenate(z_groups))
    z_bar_i = [np.mean(z) for z in z_groups]
    n_i = [len(z) for z in z_groups]

    numerator = sum(n * (zb - z_bar) ** 2 for n, zb in zip(n_i, z_bar_i))
    numerator /= (k - 1)

    denominator = sum(
        np.sum((z - zb) ** 2) for z, zb in zip(z_groups, z_bar_i)
    )
    denominator /= (N - k)

    if denominator < 1e-12:
        return (0.0, 1.0)

    f_stat = numerator / denominator
    df1, df2 = k - 1, N - k
    p_value = _f_survival(f_stat, df1, df2)
    return (float(f_stat), float(p_value))


# ---------------------------------------------------------------------------
# One-way ANOVA: mean differences across windows
# ---------------------------------------------------------------------------
def anova_test(window_pnl_arrays: list, alpha: float = ALPHA) -> dict:
    """One-way ANOVA testing if mean PnL differs across windows.

    Significant result (p < alpha) means at least one window's mean
    differs — not necessarily bad, but flags inconsistency.
    Assumes equal variances (check Levene's first).

    Args:
        window_pnl_arrays: list of lists, each containing PnL values for one window
        alpha: significance level

    Returns:
        dict with statistic, p_value, means_equal (bool), interpretation
    """
    groups = _filter_groups(window_pnl_arrays)
    if len(groups) < MIN_GROUPS:
        return _insufficient_groups_result("anova", len(groups))

    if HAS_SCIPY:
        stat, p_value = sp_stats.f_oneway(*groups)
    else:
        stat, p_value = _anova_fallback(groups)

    means_equal = p_value >= alpha
    group_means = [round(float(np.mean(g)), 4) for g in groups]
    return {
        "test": "anova",
        "statistic": round(float(stat), 6),
        "p_value": round(float(p_value), 6),
        "means_equal": means_equal,
        "pass": means_equal,
        "n_groups": len(groups),
        "group_means": group_means,
        "interpretation": (
            "Mean PnL is consistent across windows (no significant difference)"
            if means_equal
            else "Mean PnL differs significantly across windows — check for regime shifts"
        ),
    }


def _anova_fallback(groups: list) -> tuple:
    """Pure-numpy one-way ANOVA."""
    k = len(groups)
    N = sum(len(g) for g in groups)
    arrays = [np.array(g) for g in groups]
    grand_mean = np.mean(np.concatenate(arrays))

    ss_between = sum(len(a) * (np.mean(a) - grand_mean) ** 2 for a in arrays)
    ss_within = sum(np.sum((a - np.mean(a)) ** 2) for a in arrays)

    df_between = k - 1
    df_within = N - k

    if df_within <= 0 or ss_within < 1e-12:
        return (0.0, 1.0)

    ms_between = ss_between / df_between
    ms_within = ss_within / df_within
    f_stat = ms_between / ms_within

    p_value = _f_survival(f_stat, df_between, df_within)
    return (float(f_stat), float(p_value))


# ---------------------------------------------------------------------------
# Welch's ANOVA: does not assume equal variances
# ---------------------------------------------------------------------------
def welch_anova_test(window_pnl_arrays: list, alpha: float = ALPHA) -> dict:
    """Welch's ANOVA — preferred when Levene's test rejects equal variances.

    Args:
        window_pnl_arrays: list of lists, each containing PnL values for one window
        alpha: significance level

    Returns:
        dict with statistic, p_value, means_equal (bool), interpretation
    """
    groups = _filter_groups(window_pnl_arrays)
    if len(groups) < MIN_GROUPS:
        return _insufficient_groups_result("welch_anova", len(groups))

    arrays = [np.array(g, dtype=float) for g in groups]
    k = len(arrays)
    n_i = np.array([len(a) for a in arrays], dtype=float)
    means = np.array([np.mean(a) for a in arrays])
    variances = np.array([np.var(a, ddof=1) for a in arrays])

    # Guard against zero variance
    variances = np.maximum(variances, 1e-12)

    w_i = n_i / variances
    w_sum = np.sum(w_i)
    weighted_mean = np.sum(w_i * means) / w_sum

    numerator = np.sum(w_i * (means - weighted_mean) ** 2) / (k - 1)

    lambda_term = np.sum((1.0 - w_i / w_sum) ** 2 / (n_i - 1))
    denominator = 1.0 + (2.0 * (k - 2) / (k ** 2 - 1)) * lambda_term

    if denominator < 1e-12:
        return _insufficient_groups_result("welch_anova", len(groups))

    f_stat = float(numerator / denominator)
    df1 = k - 1
    df2 = float((k ** 2 - 1) / (3.0 * lambda_term)) if lambda_term > 0 else 1e6

    if HAS_SCIPY:
        p_value = 1.0 - sp_stats.f.cdf(f_stat, df1, df2)
    else:
        p_value = _f_survival(f_stat, df1, df2)

    means_equal = p_value >= alpha
    group_means = [round(float(m), 4) for m in means]
    return {
        "test": "welch_anova",
        "statistic": round(f_stat, 6),
        "p_value": round(float(p_value), 6),
        "means_equal": means_equal,
        "pass": means_equal,
        "n_groups": k,
        "group_means": group_means,
        "interpretation": (
            "Mean PnL is consistent across windows (Welch's — no equal-var assumption)"
            if means_equal
            else "Mean PnL differs significantly across windows (Welch's)"
        ),
    }


# ---------------------------------------------------------------------------
# Kruskal-Wallis: non-parametric alternative to ANOVA
# ---------------------------------------------------------------------------
def kruskal_wallis_test(window_pnl_arrays: list, alpha: float = ALPHA) -> dict:
    """Kruskal-Wallis H-test — non-parametric ANOVA for non-normal distributions.

    Use when Shapiro-Wilk rejects normality (which is common for financial returns).

    Args:
        window_pnl_arrays: list of lists, each containing PnL values for one window
        alpha: significance level

    Returns:
        dict with statistic, p_value, distributions_equal (bool), interpretation
    """
    groups = _filter_groups(window_pnl_arrays)
    if len(groups) < MIN_GROUPS:
        return _insufficient_groups_result("kruskal_wallis", len(groups))

    if HAS_SCIPY:
        stat, p_value = sp_stats.kruskal(*groups)
    else:
        stat, p_value = _kruskal_fallback(groups)

    distributions_equal = p_value >= alpha
    return {
        "test": "kruskal_wallis",
        "statistic": round(float(stat), 6),
        "p_value": round(float(p_value), 6),
        "distributions_equal": distributions_equal,
        "pass": distributions_equal,
        "n_groups": len(groups),
        "group_sizes": [len(g) for g in groups],
        "interpretation": (
            "PnL distributions are consistent across windows (non-parametric)"
            if distributions_equal
            else "PnL distributions differ across windows — possible regime change"
        ),
    }


def _kruskal_fallback(groups: list) -> tuple:
    """Pure-numpy Kruskal-Wallis."""
    all_data = np.concatenate([np.array(g) for g in groups])
    N = len(all_data)
    ranks = np.empty(N)
    sorted_idx = np.argsort(all_data)
    ranks[sorted_idx] = np.arange(1, N + 1, dtype=float)

    # Handle ties by averaging ranks
    unique_vals, counts = np.unique(all_data, return_counts=True)
    if np.any(counts > 1):
        for val, cnt in zip(unique_vals, counts):
            if cnt > 1:
                mask = all_data == val
                ranks[mask] = np.mean(ranks[mask])

    # Split ranks back into groups
    idx = 0
    rank_groups = []
    for g in groups:
        rank_groups.append(ranks[idx:idx + len(g)])
        idx += len(g)

    # H statistic
    h = (12.0 / (N * (N + 1))) * sum(
        len(rg) * (np.mean(rg) - (N + 1) / 2.0) ** 2 for rg in rank_groups
    )

    k = len(groups)
    df = k - 1
    # Approximate p-value from chi-squared distribution
    p_value = _chi2_survival(h, df)
    return (float(h), float(p_value))


# ---------------------------------------------------------------------------
# Convenience: run all tests
# ---------------------------------------------------------------------------
def run_all_tests(
    all_pnls: list,
    window_pnl_arrays: list,
    alpha: float = ALPHA,
) -> dict:
    """Run the full statistical validation suite.

    Args:
        all_pnls: flat list of all trade PnL percentages
        window_pnl_arrays: list of per-window PnL arrays
        alpha: significance level

    Returns:
        dict with all test results, overall_pass, and summary
    """
    shapiro = shapiro_wilk_test(all_pnls, alpha)
    levene = levenes_test(window_pnl_arrays, alpha)
    anova = anova_test(window_pnl_arrays, alpha)
    welch = welch_anova_test(window_pnl_arrays, alpha)
    kruskal = kruskal_wallis_test(window_pnl_arrays, alpha)

    # Choose the appropriate ANOVA result based on normality + equal variance
    is_normal = shapiro.get("normal", False)
    equal_var = levene.get("equal_variance", False)

    if is_normal and equal_var:
        recommended_test = "anova"
        recommended_result = anova
    elif is_normal and not equal_var:
        recommended_test = "welch_anova"
        recommended_result = welch
    else:
        recommended_test = "kruskal_wallis"
        recommended_result = kruskal

    # Count passes (excluding Shapiro-Wilk which is informational)
    # Use bool() to handle numpy.bool_ from scipy comparisons
    tests_with_verdict = [levene, recommended_result]
    passes = sum(1 for t in tests_with_verdict if t.get("pass") is not None and bool(t["pass"]))
    total = sum(1 for t in tests_with_verdict if t.get("pass") is not None)
    overall_pass = passes == total if total > 0 else None

    return {
        "shapiro_wilk": shapiro,
        "levenes": levene,
        "anova": anova,
        "welch_anova": welch,
        "kruskal_wallis": kruskal,
        "recommended_test": recommended_test,
        "recommended_result": bool(recommended_result["pass"]) if recommended_result.get("pass") is not None else None,
        "overall_pass": overall_pass,
        "passes": passes,
        "total_tests": total,
        "alpha": alpha,
        "scipy_available": HAS_SCIPY,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _filter_groups(window_pnl_arrays: list) -> list:
    """Filter out empty or too-small groups."""
    return [
        [float(v) for v in g if v is not None]
        for g in window_pnl_arrays
        if g and len([v for v in g if v is not None]) >= MIN_SAMPLES_PER_GROUP
    ]


def _insufficient_groups_result(test_name: str, n_groups: int) -> dict:
    return {
        "test": test_name,
        "statistic": None,
        "p_value": None,
        "pass": None,
        "n_groups": n_groups,
        "interpretation": f"Insufficient groups ({n_groups} < {MIN_GROUPS}, each needs {MIN_SAMPLES_PER_GROUP}+ samples)",
    }


def _f_survival(f_stat: float, df1: float, df2: float) -> float:
    """Approximate survival function for F-distribution (no scipy)."""
    if f_stat <= 0:
        return 1.0
    try:
        x = df2 / (df2 + df1 * f_stat)
        return _betainc(df2 / 2.0, df1 / 2.0, x)
    except (ValueError, OverflowError, ZeroDivisionError):
        return 0.5


def _chi2_survival(x: float, df: int) -> float:
    """Approximate survival function for chi-squared distribution."""
    if x <= 0:
        return 1.0
    # Wilson-Hilferty approximation
    z = ((x / df) ** (1.0 / 3.0) - (1.0 - 2.0 / (9.0 * df))) / math.sqrt(2.0 / (9.0 * df))
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def _betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function approximation."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    # Use continued fraction expansion (Lentz's method)
    max_iter = 200
    eps = 1e-10
    lnbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lnbeta) / a

    # Lentz's continued fraction
    f = 1.0
    c = 1.0
    d = 1.0 - (a + b) * x / (a + 1.0)
    if abs(d) < eps:
        d = eps
    d = 1.0 / d
    f = d

    for m in range(1, max_iter + 1):
        # Even step
        numerator = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m))
        d = 1.0 + numerator * d
        if abs(d) < eps:
            d = eps
        d = 1.0 / d
        c = 1.0 + numerator / c
        if abs(c) < eps:
            c = eps
        f *= d * c

        # Odd step
        numerator = -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + numerator * d
        if abs(d) < eps:
            d = eps
        d = 1.0 / d
        c = 1.0 + numerator / c
        if abs(c) < eps:
            c = eps
        delta = d * c
        f *= delta

        if abs(delta - 1.0) < eps:
            break

    return min(1.0, max(0.0, front * f))


# ---------------------------------------------------------------------------
# CLI entry point for standalone testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("STATISTICAL TESTS — Module Self-Test")
    print("=" * 70)
    print(f"scipy available: {HAS_SCIPY}")
    print()

    # Generate synthetic test data
    rng = np.random.default_rng(42)
    # 5 windows of ~20 trades each with consistent performance
    consistent_windows = [rng.normal(0.5, 2.0, 20).tolist() for _ in range(5)]
    all_consistent = [v for w in consistent_windows for v in w]

    print("--- Consistent strategy (5 windows, ~same distribution) ---")
    results = run_all_tests(all_consistent, consistent_windows)
    for key in ["shapiro_wilk", "levenes", "anova", "welch_anova", "kruskal_wallis"]:
        r = results[key]
        print(f"  {key}: p={r.get('p_value', 'N/A')}  pass={r.get('pass', 'N/A')}")
        print(f"    {r.get('interpretation', '')}")
    print(f"  Recommended test: {results['recommended_test']}")
    print(f"  Overall pass: {results['overall_pass']}")
    print()

    # Inconsistent windows (different means)
    shifting_windows = [
        rng.normal(0.5, 1.0, 20).tolist(),
        rng.normal(1.5, 1.0, 20).tolist(),
        rng.normal(-0.5, 1.0, 20).tolist(),
        rng.normal(2.0, 1.0, 20).tolist(),
        rng.normal(-1.0, 1.0, 20).tolist(),
    ]
    all_shifting = [v for w in shifting_windows for v in w]

    print("--- Shifting strategy (5 windows, different means) ---")
    results2 = run_all_tests(all_shifting, shifting_windows)
    for key in ["shapiro_wilk", "levenes", "anova", "welch_anova", "kruskal_wallis"]:
        r = results2[key]
        print(f"  {key}: p={r.get('p_value', 'N/A')}  pass={r.get('pass', 'N/A')}")
        print(f"    {r.get('interpretation', '')}")
    print(f"  Recommended test: {results2['recommended_test']}")
    print(f"  Overall pass: {results2['overall_pass']}")
