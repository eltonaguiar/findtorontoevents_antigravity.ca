"""DSR Hard Gate -- blocks model deployment unless statistically validated.
Based on Bailey & Lopez de Prado (2014) "The Deflated Sharpe Ratio"

Usage:
    from cross_aggregation.dsr_gate import validate_model_for_deployment

    result = validate_model_for_deployment(test_returns, n_trials=10)
    if not result["passed"]:
        log.warning(f"DSR gate FAILED: {result['reason']}")

Currently a SOFT gate (warns but does not block deployment).
# TODO: make hard gate after validation period
"""

import logging

log = logging.getLogger(__name__)

try:
    import numpy as np
    from scipy import stats
    _SCIPY_AVAILABLE = True
except ImportError:
    _SCIPY_AVAILABLE = False
    log.warning("scipy not available -- DSR gate disabled (pip install scipy)")


# DEPRECATED: Use alpha_engine.validation.sharpe_metrics instead (canonical implementation per TESTING_PROTOCOL v4.0)
def deflated_sharpe_ratio(observed_sr: float, sr_std: float, n_trials: int,
                           n_observations: int, skew: float = 0.0,
                           kurtosis: float = 3.0) -> float:
    """Calculate the Deflated Sharpe Ratio.

    Tests whether the observed Sharpe Ratio is statistically significant
    after correcting for multiple testing (data snooping).

    Args:
        observed_sr: Observed Sharpe Ratio of the strategy
        sr_std: Standard deviation of Sharpe Ratio estimates
        n_trials: Number of strategies/models tested (multiple testing correction)
        n_observations: Number of return observations
        skew: Skewness of returns
        kurtosis: Kurtosis of returns (3.0 = normal)

    Returns:
        p-value (0-1). Strategy passes if p > 0.95.
    """
    if not _SCIPY_AVAILABLE:
        return 0.0

    if n_trials < 1 or n_observations < 2 or sr_std <= 0:
        return 0.0

    # Expected max SR under null (Euler-Mascheroni approximation)
    euler_mascheroni = 0.5772156649
    e_max_sr = sr_std * (
        (1 - euler_mascheroni) * stats.norm.ppf(1 - 1 / n_trials) +
        euler_mascheroni * stats.norm.ppf(1 - 1 / (n_trials * np.e))
    )

    # PSR test statistic
    sr_diff = observed_sr - e_max_sr
    denominator = np.sqrt(
        (1 - skew * observed_sr + (kurtosis - 1) / 4 * observed_sr ** 2) / n_observations
    )

    if denominator == 0:
        return 0.0

    test_stat = sr_diff / denominator
    return float(stats.norm.cdf(test_stat))


def probabilistic_sharpe_ratio(observed_sr: float, benchmark_sr: float,
                                n_observations: int, skew: float = 0.0,
                                kurtosis: float = 3.0) -> float:
    """Probabilistic Sharpe Ratio -- is SR > benchmark with p>0.95?

    Args:
        observed_sr: Observed annualized Sharpe Ratio
        benchmark_sr: Benchmark SR to beat (0 = better than random)
        n_observations: Number of return observations
        skew: Skewness of returns
        kurtosis: Kurtosis of returns (3.0 = normal)

    Returns:
        p-value (0-1). Strategy passes if p > 0.95.
    """
    if not _SCIPY_AVAILABLE:
        return 0.0

    if n_observations < 2:
        return 0.0

    sr_diff = observed_sr - benchmark_sr
    denominator = np.sqrt(
        (1 - skew * observed_sr + (kurtosis - 1) / 4 * observed_sr ** 2) / n_observations
    )
    if denominator == 0:
        return 0.0
    return float(stats.norm.cdf(sr_diff / denominator))


def validate_model_for_deployment(returns, n_trials: int = 10,
                                   min_dsr: float = 0.95, min_psr: float = 0.95,
                                   benchmark_sr: float = 0.0) -> dict:
    """
    Hard gate: validate whether a model's returns pass DSR + PSR tests.

    This is the single entry point for all training pipelines to call after
    computing test-set returns.

    Args:
        returns: Array-like of strategy returns (daily or per-trade)
        n_trials: Number of models/strategies tested (for multiple testing correction)
        min_dsr: Minimum DSR p-value to pass (default 0.95)
        min_psr: Minimum PSR p-value to pass (default 0.95)
        benchmark_sr: SR to beat (default 0 = better than random)

    Returns:
        dict with: passed (bool), dsr_pvalue, psr_pvalue, sharpe, reason
    """
    if not _SCIPY_AVAILABLE:
        return {
            "passed": False,
            "dsr_pvalue": 0.0,
            "psr_pvalue": 0.0,
            "sharpe": 0.0,
            "reason": "scipy not installed -- DSR gate cannot run"
        }

    returns = np.asarray(returns, dtype=float)

    if len(returns) < 30:
        return {
            "passed": False,
            "dsr_pvalue": 0.0,
            "psr_pvalue": 0.0,
            "sharpe": 0.0,
            "reason": f"Insufficient data: {len(returns)} observations (need >=30)"
        }

    mean_r = np.mean(returns)
    std_r = np.std(returns, ddof=1)
    if std_r == 0:
        return {
            "passed": False,
            "dsr_pvalue": 0.0,
            "psr_pvalue": 0.0,
            "sharpe": 0.0,
            "reason": "Zero variance in returns"
        }

    sharpe = mean_r / std_r * np.sqrt(252)  # Annualized
    skew = float(stats.skew(returns))
    kurt = float(stats.kurtosis(returns, fisher=False))  # Excess=False -> raw kurtosis

    sr_std = std_r / np.sqrt(len(returns))

    dsr_p = deflated_sharpe_ratio(sharpe, sr_std, n_trials, len(returns), skew, kurt)
    psr_p = probabilistic_sharpe_ratio(sharpe, benchmark_sr, len(returns), skew, kurt)

    passed = dsr_p >= min_dsr and psr_p >= min_psr

    reason = "PASSED" if passed else (
        f"FAILED: DSR={dsr_p:.3f} (need >={min_dsr}), PSR={psr_p:.3f} (need >={min_psr})"
    )

    return {
        "passed": passed,
        "dsr_pvalue": round(dsr_p, 4),
        "psr_pvalue": round(psr_p, 4),
        "sharpe": round(sharpe, 4),
        "skew": round(skew, 4),
        "kurtosis": round(kurt, 4),
        "n_observations": len(returns),
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# FC-CRYPTO PRO system-level DSR gate (win/loss stats, no numpy required)
# ---------------------------------------------------------------------------
# This gate runs in the FC-PRO pipeline where we only have aggregate
# win/loss counts + average gain/loss per system. Pure math.erf — no scipy.

import math as _math


def _normal_cdf(x: float) -> float:
    """Standard normal CDF using math.erf (no scipy needed)."""
    return 0.5 * (1.0 + _math.erf(x / _math.sqrt(2.0)))


def _observed_sharpe_from_wl(
    wins: int, losses: int, avg_gain: float, avg_loss: float
) -> tuple[float, float, float, int] | None:
    """Compute observed Sharpe and moments from win/loss summary stats.

    Models returns as a two-point distribution:
      +avg_gain with probability p = wins/(wins+losses)
      -avg_loss with probability 1-p

    Returns (sharpe, skewness, excess_kurtosis, n) or None.
    """
    n = wins + losses
    if n < 2:
        return None

    p = wins / n
    mean_r = p * avg_gain - (1 - p) * avg_loss

    e_r2 = p * (avg_gain ** 2) + (1 - p) * (avg_loss ** 2)
    var = e_r2 - mean_r ** 2
    if var <= 0:
        return None

    std = _math.sqrt(var)
    sharpe = mean_r / std

    # Skewness: E[(R-mu)^3] / sigma^3
    e_r3 = p * ((avg_gain - mean_r) ** 3) + (1 - p) * ((-avg_loss - mean_r) ** 3)
    skew = e_r3 / (std ** 3)

    # Excess kurtosis: E[(R-mu)^4] / sigma^4 - 3
    e_r4 = p * ((avg_gain - mean_r) ** 4) + (1 - p) * ((-avg_loss - mean_r) ** 4)
    kurt = e_r4 / (std ** 4) - 3.0

    return (sharpe, skew, kurt, n)


def _psr_from_stats(
    sharpe: float, skew: float, excess_kurt: float, n: int, sr_bench: float = 0.0
) -> float:
    """Probabilistic Sharpe Ratio using pure Python math.

    PSR = Phi( (SR - SR*) * sqrt(n-1) / sqrt(1 - skew*SR + (kurt-1)/4 * SR^2) )
    """
    if n <= 1:
        return 0.0

    denom_sq = 1.0 - skew * sharpe + (excess_kurt - 1.0) / 4.0 * (sharpe ** 2)
    if denom_sq <= 0:
        denom_sq = 1.0

    z = (sharpe - sr_bench) * _math.sqrt(n - 1) / _math.sqrt(denom_sq)
    return _normal_cdf(z)


def passes_dsr_gate(
    system_id: str,
    wins: int,
    losses: int,
    avg_gain: float,
    avg_loss: float,
    min_trades: int = 20,
    alpha: float = 0.05,
    sr_benchmark: float = 0.0,
) -> tuple[bool, str]:
    """Discriminative Sharpe Ratio gate for FC-CRYPTO PRO.

    Returns (passes, reason_string).
    True only if the system has statistical evidence of a positive edge.

    Uses Bailey & Lopez de Prado (2012) Probabilistic Sharpe Ratio:
    - Calculates observed Sharpe from win/loss summary stats
    - Tests H0: true Sharpe <= sr_benchmark
    - Rejects H0 only if p-value < alpha (default 0.05)
    - Requires min_trades for statistical power

    Args:
        system_id: System identifier (for logging)
        wins: Number of winning trades
        losses: Number of losing trades
        avg_gain: Average gain per winner (positive, e.g. 0.05 = 5%)
        avg_loss: Average loss per loser (positive, e.g. 0.03 = 3%)
        min_trades: Minimum trades for statistical power (default 20)
        alpha: Significance level (default 0.05)
        sr_benchmark: Benchmark Sharpe to beat (default 0 = positive edge)

    Returns:
        Tuple of (passes_gate: bool, reason: str)
    """
    total = wins + losses

    # Gate 1: minimum trade count
    if total < min_trades:
        return False, f"insufficient trades ({total} < {min_trades})"

    # Gate 2: basic sanity
    if wins == 0:
        return False, "zero wins"
    if losses == 0 and total < 30:
        return False, f"perfect record but small sample ({total} < 30)"
    if losses == 0:
        return True, f"perfect record ({wins}W/0L, n={total})"

    # Gate 3: compute observed Sharpe
    stats = _observed_sharpe_from_wl(wins, losses, avg_gain, avg_loss)
    if stats is None:
        return False, "cannot compute Sharpe (insufficient variance)"

    sharpe, skew, kurt, n = stats

    # Gate 4: negative Sharpe = immediate fail
    if sharpe <= 0:
        return False, f"negative Sharpe ({sharpe:.3f})"

    # Gate 5: PSR significance test
    psr = _psr_from_stats(sharpe, skew, kurt, n, sr_benchmark)
    p_value = 1.0 - psr

    if p_value > alpha:
        return False, (
            f"DSR p={p_value:.4f} > {alpha} "
            f"(SR={sharpe:.3f}, n={n}, PSR={psr:.3f})"
        )

    return True, (
        f"DSR PASS: p={p_value:.4f}, SR={sharpe:.3f}, "
        f"PSR={psr:.3f}, n={n}, WR={wins/total*100:.1f}%"
    )


def compute_system_avg_gains(closed_picks: list[dict]) -> tuple[float, float]:
    """Compute average gain and average loss from closed picks.

    Returns (avg_gain, avg_loss) both as positive floats.
    Falls back to (0.05, 0.03) if no PnL data available.
    """
    gains: list[float] = []
    loss_list: list[float] = []

    for p in closed_picks:
        pnl = p.get("realized_pnl_pct") or p.get("pnl_pct") or p.get("pnl_percent")
        if pnl is None:
            entry = p.get("entry_price")
            exit_p = p.get("exit_price")
            if entry and exit_p and entry > 0:
                d = (p.get("direction") or p.get("signal_type") or "BUY").upper()
                if "SELL" in d or "SHORT" in d:
                    pnl = (entry - exit_p) / entry
                else:
                    pnl = (exit_p - entry) / entry

        if pnl is not None:
            pnl = float(pnl)
            if pnl > 0:
                gains.append(pnl)
            elif pnl < 0:
                loss_list.append(abs(pnl))

    avg_gain = sum(gains) / len(gains) if gains else 0.05
    avg_loss = sum(loss_list) / len(loss_list) if loss_list else 0.03

    return avg_gain, avg_loss
