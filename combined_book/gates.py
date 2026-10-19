"""Go-live + kill gates; statistical reporting helpers."""
from __future__ import annotations

import math

import numpy as np

from combined_book.rules import (
    GO_LIVE_MAX_DD,
    GO_LIVE_N_MONTHS,
    GO_LIVE_PF,
    GO_LIVE_WR,
    KILL_AFTER_MONTHS,
    KILL_BOOTSTRAP_P,
    KILL_DRAWDOWN,
    KILL_PF,
    KILL_SHARPE,
    KILL_WR,
)


def wilson_ci(wins, n, z=1.96):
    if n <= 0:
        return (0.0, 0.0)
    phat = wins / n
    denom = 1.0 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n) / denom
    return (centre - margin, centre + margin)


def binomial_pvalue(wins, n, p0=0.5):
    if n <= 0:
        return 1.0
    phat = wins / n
    se = math.sqrt(p0 * (1 - p0) / n)
    if se == 0:
        return 0.0
    z = (phat - p0) / se
    return 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2))))


def profit_factor(returns):
    pos = sum(x for x in returns if x > 0)
    neg = -sum(x for x in returns if x < 0)
    return pos / neg if neg > 0 else float("inf")


def bootstrapped_pf(returns, seed=42, n_sims=2000):
    rng = np.random.default_rng(seed)
    arr = np.asarray(returns, dtype=float)
    pfs = []
    for _ in range(n_sims):
        sample = rng.choice(arr, size=len(arr), replace=True)
        pfs.append(profit_factor(sample))
    return pfs


def sharpe(returns, rf=0.0):
    arr = np.asarray(returns, dtype=float)
    if len(arr) < 2 or arr.std(ddof=0) == 0:
        return 0.0
    return float((arr.mean() - rf) / arr.std(ddof=0))


def annualized_sharpe(returns, periods_per_year=12):
    return sharpe(returns) * math.sqrt(periods_per_year)


def _erfinv(y):
    """Inverse error function via Newton's method (math.erf has no inverse)."""
    if y >= 1.0:
        return float("inf")
    if y <= -1.0:
        return float("-inf")
    x = 0.0
    for _ in range(100):
        err = math.erf(x) - y
        if abs(err) < 1e-12:
            break
        x -= err / ((2.0 / math.sqrt(math.pi)) * math.exp(-x * x))
    return x


def deflated_sharpe(sharpe_val, n_variants, n_samples):
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado).

    Penalizes the observed SR by the expected maximum Sharpe of ``n_variants``
    independent trials, which raises the effective hurdle.
    """
    if n_variants <= 1 or n_samples <= 1:
        return sharpe_val
    em = 0.5772156649015329  # Euler-Mascheroni
    def _phi_inv(p):
        return math.sqrt(2.0) * _erfinv(2.0 * p - 1.0)
    e_max = ((1.0 - em) * _phi_inv(1.0 - 1.0 / n_variants)
             + em * _phi_inv(1.0 - 1.0 / (n_variants * math.e)))
    sr_star = e_max * math.sqrt(1.0 / (n_samples - 1))
    return sharpe_val - sr_star


def random_entry_percentile(book_returns, ref_returns, seed=7, n_sims=1000):
    rng = np.random.default_rng(seed)
    book = np.asarray(book_returns, dtype=float)
    ref = np.asarray(ref_returns, dtype=float)
    n = min(len(book), len(ref))
    if n == 0:
        return 0.0
    actual = sharpe(book[:n])
    sims = []
    for _ in range(n_sims):
        perm = rng.permutation(n)
        sims.append(sharpe(ref[perm]))
    return float(np.mean(np.asarray(sims) <= actual))


def evaluate_go_live(stats):
    checks = {
        "n_months": stats["n_months"] >= GO_LIVE_N_MONTHS,
        "pf": stats["pf"] >= GO_LIVE_PF,
        "win_rate": stats["win_rate"] >= GO_LIVE_WR,
        "max_dd": stats["max_dd"] >= GO_LIVE_MAX_DD,
    }
    return all(checks.values()), checks


def evaluate_kill(stats):
    if stats["n_months"] < KILL_AFTER_MONTHS:
        return False, {}
    kills = {
        "drawdown": stats["max_dd"] < KILL_DRAWDOWN,
        "pf": stats["pf"] < KILL_PF,
        "win_rate": stats["win_rate"] < KILL_WR,
        "sharpe": stats["annualized_sharpe"] <= KILL_SHARPE,
        "bootstrap": stats["bootstrap_p_over_1"] > KILL_BOOTSTRAP_P,
    }
    return any(kills.values()), kills
