"""
stat_tests.py — Statistical testing functions for the trading engine.
All implementations from first principles using only the math module.
"""

import math
import random
from typing import List, Tuple, Callable, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _erf(x: float) -> float:
    """Approximation of the error function (Abramowitz & Stegun 7.1.26)."""
    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + 0.3275911 * x)
    y = 1.0 - (
        ((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t
         - 0.284496736) * t + 0.254829592
    ) * t * math.exp(-x * x)
    return sign * y


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via erf."""
    return 0.5 * (1.0 + _erf(x / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """Rational approximation of the standard normal quantile (inverse CDF).
    Uses Peter Acklam's algorithm — accurate to ~4.5e-4."""
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    if p < 0.5:
        return -_norm_ppf(1.0 - p)

    # Coefficients
    a = [
        -3.969683028665376e+01,  2.209460984245205e+02,
        -2.759285104469687e+02,  1.383577518672690e+02,
        -3.066479806614716e+01,  2.506628277459239e+00,
    ]
    b = [
        -5.447609879822406e+01,  1.615858368580409e+02,
        -1.556989798598866e+02,  6.680131188771972e+01,
        -1.328068155288572e+01,
    ]
    c = [
        -7.784894002430293e-03, -3.223964580411365e-01,
        -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00,  2.938163982698783e+00,
    ]
    d = [
        7.784695709041462e-03,  3.224671290700398e-01,
        2.445134137142996e+00,  3.754408661907416e+00,
    ]

    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
               ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1.0)
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5]) * q / \
               (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1.0)
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
                ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1.0)


def _t_cdf(t_val: float, df: float) -> float:
    """Student's t CDF via regularised incomplete beta function (continued fraction)."""
    x = df / (df + t_val * t_val)
    if t_val < 0:
        return 0.5 * _reg_incomplete_beta(df / 2.0, 0.5, x)
    else:
        return 1.0 - 0.5 * _reg_incomplete_beta(df / 2.0, 0.5, x)


def _reg_incomplete_beta(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta function I_x(a,b) via continued fraction (Lentz)."""
    if x < 0.0 or x > 1.0:
        raise ValueError("x must be in [0,1]")
    if x == 0.0 or x == 1.0:
        return x

    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1.0 - x) * b - lbeta) / a

    # Use Lentz's continued fraction
    f = 1.0
    c = 1.0
    d = 1.0 - (a + b) * x / (a + 1.0)
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    f = d

    max_iter = 500
    for m in range(1, max_iter + 1):
        # Even step
        num = m * (b - m) * x / ((a + 2*m - 1) * (a + 2*m))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        f *= c * d

        # Odd step
        num = -(a + m) * (a + b + m) * x / ((a + 2*m) * (a + 2*m + 1))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = c * d
        f *= delta

        if abs(delta - 1.0) < 1e-10:
            break

    return front * f


def _chi2_cdf(x: float, k: float) -> float:
    """Chi-square CDF via regularised lower incomplete gamma."""
    if x <= 0:
        return 0.0
    return _reg_lower_gamma(k / 2.0, x / 2.0)


def _reg_lower_gamma(a: float, x: float) -> float:
    """Regularised lower incomplete gamma P(a,x) via series expansion."""
    if x < 0:
        raise ValueError("x must be >= 0")
    if x == 0:
        return 0.0

    if x < a + 1.0:
        # Series
        ap = a
        s = 1.0 / a
        ds = s
        for _ in range(500):
            ap += 1.0
            ds *= x / ap
            s += ds
            if abs(ds) < abs(s) * 1e-12:
                break
        return s * math.exp(-x + a * math.log(x) - math.lgamma(a))
    else:
        # Continued fraction
        f = 1.0
        b0 = x + 1.0 - a
        c0 = 1e30
        d0 = 1.0 / b0 if b0 != 0 else 1e30
        f = d0
        for i in range(1, 500):
            an = -i * (i - a)
            bn = x + 2*i + 1 - a
            d0 = bn + an * d0
            if abs(d0) < 1e-30:
                d0 = 1e-30
            c0 = bn + an / c0
            if abs(c0) < 1e-30:
                c0 = 1e-30
            d0 = 1.0 / d0
            delta = c0 * d0
            f *= delta
            if abs(delta - 1.0) < 1e-12:
                break
        return 1.0 - f * math.exp(-x + a * math.log(x) - math.lgamma(a))


# ---------------------------------------------------------------------------
# 1. Wilson Score Interval
# ---------------------------------------------------------------------------

def wilson_score_interval(
    successes: int, trials: int, z: float = 1.96
) -> Tuple[float, float]:
    """Wilson score confidence interval for a proportion.

    Returns (lower, upper) bounds.
    """
    if trials == 0:
        return (0.0, 0.0)
    p_hat = successes / trials
    denom = 1.0 + z * z / trials
    centre = p_hat + z * z / (2.0 * trials)
    margin = z * math.sqrt((p_hat * (1.0 - p_hat) + z * z / (4.0 * trials)) / trials)
    lower = max(0.0, (centre - margin) / denom)
    upper = min(1.0, (centre + margin) / denom)
    return (lower, upper)


# ---------------------------------------------------------------------------
# 2. Two-Proportion Z-Test
# ---------------------------------------------------------------------------

def two_proportion_z_test(
    n1: int, s1: int, n2: int, s2: int
) -> Tuple[float, float, bool]:
    """Two-proportion z-test.

    Returns (z_stat, p_value, significant_at_05).
    """
    if n1 == 0 or n2 == 0:
        return (0.0, 1.0, False)

    p1 = s1 / n1
    p2 = s2 / n2
    p_pool = (s1 + s2) / (n1 + n2)

    if p_pool == 0.0 or p_pool == 1.0:
        return (0.0, 1.0, False)

    se = math.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n1 + 1.0 / n2))
    if se == 0.0:
        return (0.0, 1.0, False)

    z_stat = (p1 - p2) / se
    p_value = 2.0 * (1.0 - _norm_cdf(abs(z_stat)))
    return (z_stat, p_value, p_value < 0.05)


# ---------------------------------------------------------------------------
# 3. Welch's t-Test
# ---------------------------------------------------------------------------

def welch_t_test(
    mean1: float, std1: float, n1: int,
    mean2: float, std2: float, n2: int,
) -> Tuple[float, float, float, bool]:
    """Welch's t-test for unequal variances.

    Returns (t_stat, p_value, df, significant_at_05).
    """
    if n1 < 2 or n2 < 2:
        return (0.0, 1.0, 0.0, False)

    se1 = std1 * std1 / n1
    se2 = std2 * std2 / n2
    denom = math.sqrt(se1 + se2)

    if denom == 0.0:
        # Both groups have zero variance
        if mean1 == mean2:
            return (0.0, 1.0, float(n1 + n2 - 2), False)
        else:
            return (math.inf, 0.0, float(n1 + n2 - 2), True)

    t_stat = (mean1 - mean2) / denom

    # Welch-Satterthwaite degrees of freedom
    num_df = (se1 + se2) ** 2
    den_df = (se1 * se1 / (n1 - 1)) if (n1 > 1) else 0.0
    den_df += (se2 * se2 / (n2 - 1)) if (n2 > 1) else 0.0
    if den_df == 0.0:
        df = float(n1 + n2 - 2)
    else:
        df = num_df / den_df

    # Two-sided p-value: 2 * P(T > |t|)
    p_value = 2.0 * (1.0 - _t_cdf(abs(t_stat), df))
    p_value = max(0.0, min(1.0, p_value))

    return (t_stat, p_value, df, p_value < 0.05)


# ---------------------------------------------------------------------------
# 4. Chi-Square Independence Test
# ---------------------------------------------------------------------------

def chi_square_independence(
    observed: List[List[float]],
) -> Tuple[float, float, int, bool]:
    """Chi-square test of independence on a 2D contingency table.

    Returns (chi2, p_value, dof, significant_at_05).
    """
    r = len(observed)
    if r == 0:
        return (0.0, 1.0, 0, False)
    c = len(observed[0])

    row_totals = [sum(row) for row in observed]
    col_totals = [sum(observed[i][j] for i in range(r)) for j in range(c)]
    grand_total = sum(row_totals)

    if grand_total == 0:
        return (0.0, 1.0, 0, False)

    dof = (r - 1) * (c - 1)
    if dof <= 0:
        return (0.0, 1.0, 0, False)

    chi2 = 0.0
    for i in range(r):
        for j in range(c):
            expected = row_totals[i] * col_totals[j] / grand_total
            if expected > 0:
                chi2 += (observed[i][j] - expected) ** 2 / expected

    p_value = 1.0 - _chi2_cdf(chi2, float(dof))
    return (chi2, p_value, dof, p_value < 0.05)


# ---------------------------------------------------------------------------
# 5. Bonferroni Correction
# ---------------------------------------------------------------------------

def bonferroni_correction(alpha: float, num_tests: int) -> float:
    """Bonferroni-adjusted significance level."""
    if num_tests <= 0:
        return alpha
    return alpha / num_tests


# ---------------------------------------------------------------------------
# 6. Bootstrap CI
# ---------------------------------------------------------------------------

def bootstrap_ci(
    data: List[float],
    statistic_fn: Callable[[List[float]], float],
    n_boot: int = 10000,
    ci: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float]:
    """Bootstrap confidence interval for any statistic function.

    Returns (lower, upper) bounds.
    """
    if len(data) == 0:
        return (0.0, 0.0)

    rng = random.Random(seed)
    n = len(data)
    stats = []
    for _ in range(n_boot):
        sample = [rng.choice(data) for _ in range(n)]
        stats.append(statistic_fn(sample))

    stats.sort()
    lo_idx = int((1.0 - ci) / 2.0 * n_boot)
    hi_idx = int((1.0 + ci) / 2.0 * n_boot) - 1
    hi_idx = min(hi_idx, n_boot - 1)

    return (stats[lo_idx], stats[hi_idx])


# ---------------------------------------------------------------------------
# 7. Sharpe Ratio
# ---------------------------------------------------------------------------

def sharpe_ratio(returns: List[float], risk_free: float = 0.0) -> float:
    """Annualized Sharpe ratio (assumes daily returns, 252 trading days)."""
    n = len(returns)
    if n < 2:
        return 0.0

    excess = [r - risk_free for r in returns]
    mean_ex = sum(excess) / n
    var = sum((x - mean_ex) ** 2 for x in excess) / (n - 1)
    std = math.sqrt(var)

    if std == 0.0:
        return 0.0

    return (mean_ex / std) * math.sqrt(252)


# ---------------------------------------------------------------------------
# 8. Sortino Ratio
# ---------------------------------------------------------------------------

def sortino_ratio(returns: List[float], risk_free: float = 0.0) -> float:
    """Annualized Sortino ratio (assumes daily returns, 252 trading days)."""
    n = len(returns)
    if n < 2:
        return 0.0

    excess = [r - risk_free for r in returns]
    mean_ex = sum(excess) / n

    downside_sq = [min(x, 0.0) ** 2 for x in excess]
    ds_var = sum(downside_sq) / n

    if ds_var == 0.0:
        return 0.0

    ds_std = math.sqrt(ds_var)
    return (mean_ex / ds_std) * math.sqrt(252)


# ---------------------------------------------------------------------------
# 9. Profit Factor
# ---------------------------------------------------------------------------

def profit_factor(
    gains: List[float],
    losses: List[float],
    bootstrap: bool = False,
    n_boot: int = 10000,
    ci: float = 0.95,
    seed: int = 42,
) -> float | Tuple[float, float, float]:
    """Profit factor = sum(gains) / abs(sum(losses)).

    If bootstrap=True, returns (pf, ci_lower, ci_upper).
    """
    total_gains = sum(gains) if gains else 0.0
    total_losses = abs(sum(losses)) if losses else 0.0

    if total_losses == 0.0:
        pf = float('inf') if total_gains > 0 else 0.0
        if bootstrap:
            return (pf, pf, pf)
        return pf

    pf = total_gains / total_losses

    if not bootstrap:
        return pf

    # Bootstrap on combined trade PnLs
    all_trades = list(gains) + [-abs(l) for l in losses]
    if len(all_trades) == 0:
        return (pf, pf, pf)

    def _pf_fn(sample: List[float]) -> float:
        g = sum(x for x in sample if x > 0)
        l = abs(sum(x for x in sample if x < 0))
        if l == 0:
            return float('inf') if g > 0 else 0.0
        return g / l

    lo, hi = bootstrap_ci(all_trades, _pf_fn, n_boot, ci, seed)
    return (pf, lo, hi)


# ---------------------------------------------------------------------------
# 10. Max Consecutive
# ---------------------------------------------------------------------------

def max_consecutive(booleans: List[bool]) -> Tuple[int, int]:
    """Max consecutive True and False runs.

    Returns (max_true, max_false).
    """
    if not booleans:
        return (0, 0)

    max_t = 0
    max_f = 0
    cur_t = 0
    cur_f = 0

    for b in booleans:
        if b:
            cur_t += 1
            cur_f = 0
        else:
            cur_f += 1
            cur_t = 0
        max_t = max(max_t, cur_t)
        max_f = max(max_f, cur_f)

    return (max_t, max_f)


# ---------------------------------------------------------------------------
# 11. Kelly Criterion
# ---------------------------------------------------------------------------

def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Optimal Kelly fraction.

    Kelly = (p * b - q) / b  where b = avg_win / avg_loss, q = 1 - p
    """
    if avg_loss == 0.0:
        return 0.0
    b = avg_win / avg_loss
    if b == 0.0:
        return 0.0
    q = 1.0 - win_rate
    kelly = (win_rate * b - q) / b
    return max(0.0, kelly)


# ---------------------------------------------------------------------------
# 12. VaR and CVaR
# ---------------------------------------------------------------------------

def var_cvar(
    returns: List[float], confidence: float = 0.95
) -> Tuple[float, float]:
    """Value at Risk and Conditional VaR (Expected Shortfall).

    Returns (VaR, CVaR) as positive loss values.
    """
    if not returns:
        return (0.0, 0.0)

    sorted_r = sorted(returns)
    n = len(sorted_r)
    idx = int(math.floor((1.0 - confidence) * n))
    idx = max(0, min(idx, n - 1))

    var = -sorted_r[idx]

    # CVaR = average of returns at or below the VaR threshold
    tail = [r for r in sorted_r if r <= sorted_r[idx]]
    if tail:
        cvar = -sum(tail) / len(tail)
    else:
        cvar = var

    return (var, cvar)


# ---------------------------------------------------------------------------
# 13. Herfindahl-Hirschman Index
# ---------------------------------------------------------------------------

def herfindahl_hirschman(shares: List[float]) -> float:
    """HHI concentration index from a list of market shares (as fractions or percentages).

    If values sum to ~1, returns HHI in [0, 1].
    If values sum to ~100, returns HHI in [0, 10000].
    """
    if not shares:
        return 0.0

    total = sum(shares)
    if total == 0.0:
        return 0.0

    # Normalise to fractions
    fractions = [s / total for s in shares]
    return sum(f * f for f in fractions)
