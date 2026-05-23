"""
Deflated Sharpe Ratio (DSR) -- Bailey & Lopez de Prado (2014)

Filters false-positive strategies by accounting for multiple testing bias.
When you run N backtests, the best Sharpe is inflated by selection bias.
DSR computes the probability that an observed Sharpe exceeds what you'd
expect from N independent trials with zero true alpha.

Reference:
    Bailey, D.H. and Lopez de Prado, M. (2014),
    "The Deflated Sharpe Ratio: Correcting for Selection Bias,
    Backtest Overfitting, and Non-Normality",
    Journal of Portfolio Management, 40(5), pp. 94-107.

Usage:
    from deflated_sharpe import filter_edge_strategies

    strategies = [
        {"name": "RSI-2", "sharpe": 2.1, "returns": [...], "trade_count": 200},
        ...
    ]
    genuine = filter_edge_strategies(strategies)
"""

import math
from typing import List, Dict

import numpy as np

try:
    from scipy.stats import norm as _scipy_norm

    def _norm_cdf(x: float) -> float:
        return float(_scipy_norm.cdf(x))

    def _norm_ppf(p: float) -> float:
        return float(_scipy_norm.ppf(p))

except ImportError:
    # Pure-Python fallback using math.erfc (no scipy needed).
    def _norm_cdf(x: float) -> float:
        """Standard normal CDF via erfc."""
        return 0.5 * math.erfc(-x / math.sqrt(2.0))

    def _norm_ppf(p: float) -> float:
        """Standard normal inverse CDF (Beasley-Springer-Moro approximation)."""
        if p <= 0:
            return -math.inf
        if p >= 1:
            return math.inf
        # Rational approximation (Abramowitz & Stegun 26.2.23, Peter Acklam refinement)
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


def returns_stats(returns: List[float]) -> Dict[str, float]:
    """Compute mean, variance, skewness, and excess kurtosis from a returns series.

    Args:
        returns: List of periodic returns (e.g. daily or per-trade).

    Returns:
        Dict with keys: mean, variance, skewness, kurtosis (excess).
    """
    r = np.asarray(returns, dtype=np.float64)
    n = len(r)
    if n < 4:
        raise ValueError(f"Need at least 4 returns to compute stats, got {n}")

    mu = np.mean(r)
    var = np.var(r, ddof=1)
    std = np.sqrt(var)

    if std == 0:
        return {"mean": float(mu), "variance": 0.0, "skewness": 0.0, "kurtosis": 0.0}

    # Sample skewness (Fisher)
    m3 = np.mean((r - mu) ** 3)
    skew = m3 / (std ** 3) * (n * n) / ((n - 1) * (n - 2))

    # Sample excess kurtosis (Fisher)
    m4 = np.mean((r - mu) ** 4)
    kurt_raw = m4 / (var ** 2)
    kurt = ((n + 1) * kurt_raw - 3 * (n - 1)) * (n - 1) / ((n - 2) * (n - 3))

    return {
        "mean": float(mu),
        "variance": float(var),
        "skewness": float(skew),
        "kurtosis": float(kurt),
    }


def sharpe_variance(sharpe: float, horizon: int, skew: float, kurtosis: float) -> float:
    """Variance of the Sharpe ratio estimator (Lo 2002, adjusted for non-normality).

    Args:
        sharpe: Estimated Sharpe ratio.
        horizon: Number of return observations (backtest length).
        skew: Sample skewness of returns.
        kurtosis: Sample excess kurtosis of returns.

    Returns:
        Variance of the Sharpe ratio estimate.
    """
    # From Bailey & Lopez de Prado (2014), Eq. 4:
    # Var(SR) = (1/T) * [1 - skew*SR + ((kurtosis-1)/4)*SR^2]
    # where kurtosis here is excess kurtosis
    return (1.0 / horizon) * (
        1.0
        - skew * sharpe
        + ((kurtosis) / 4.0) * sharpe ** 2
    )


def expected_max_sharpe(mean_sr: float, var_sr: float, nb_trials: int) -> float:
    """Expected maximum Sharpe ratio from N independent trials with zero true alpha.

    Uses the approximation from Bailey & Lopez de Prado (2014), Eq. 15,
    based on the expected maximum of N i.i.d. standard normal draws
    (Euler-Mascheroni correction).

    Args:
        mean_sr: Mean Sharpe ratio across all trials (typically ~0 under null).
        var_sr: Variance of the Sharpe ratio estimator.
        nb_trials: Number of independent strategy backtests conducted.

    Returns:
        Expected maximum Sharpe ratio under the null hypothesis.
    """
    if nb_trials <= 0:
        raise ValueError("nb_trials must be positive")
    if nb_trials == 1:
        return mean_sr

    std_sr = math.sqrt(var_sr) if var_sr > 0 else float("nan")  # NaN-safe BUG-1 fix
    euler_mascheroni = 0.5772156649

    # E[max(Z_1,...,Z_N)] approximation
    z = (1.0 - euler_mascheroni) * _norm_ppf(1.0 - 1.0 / nb_trials) + \
        euler_mascheroni * _norm_ppf(1.0 - 1.0 / (nb_trials * math.e))

    return mean_sr + std_sr * z


# DEPRECATED: Use alpha_engine.validation.sharpe_metrics instead (canonical implementation per TESTING_PROTOCOL v4.0)
def deflated_sharpe_ratio(
    estimated_sharpe: float,
    sr_variance: float,
    nb_trials: int,
    backtest_horizon: int,
    skew: float,
    kurtosis: float,
) -> float:
    """Deflated Sharpe Ratio -- probability that observed Sharpe is genuine.

    Computes P(SR > E[max(SR)]) under the null that all strategies have
    zero true Sharpe. A DSR >= 0.95 means the strategy's Sharpe is
    unlikely to be a false positive from multiple testing.

    Args:
        estimated_sharpe: Observed Sharpe ratio of the candidate strategy.
        sr_variance: Variance of the Sharpe ratio estimator (use sharpe_variance()).
        nb_trials: Total number of independent backtests run.
        backtest_horizon: Number of return observations in the backtest.
        skew: Sample skewness of the strategy's returns.
        kurtosis: Sample excess kurtosis of the strategy's returns.

    Returns:
        DSR probability in [0, 1]. Values >= 0.95 suggest genuine alpha.
    """
    # Expected max SR under null (mean_sr = 0 under H0)
    e_max_sr = expected_max_sharpe(0.0, sr_variance, nb_trials)

    # Standard error of the SR estimate
    sr_std = math.sqrt(sr_variance) if sr_variance > 0 else float("nan")  # NaN-safe BUG-1 fix

    # One-sided test: P(SR > E[max_SR])
    z = (estimated_sharpe - e_max_sr) / sr_std
    return float(_norm_cdf(z))


def filter_edge_strategies(
    strategies: List[Dict],
    dsr_threshold: float = 0.95,
    nb_trials: int = None,
) -> List[Dict]:
    """Filter strategies using the Deflated Sharpe Ratio.

    Takes a list of strategy result dicts and returns only those whose
    observed Sharpe ratio survives the DSR multiple-testing correction.

    Args:
        strategies: List of dicts, each with keys:
            - name (str): Strategy identifier.
            - sharpe (float): Observed Sharpe ratio.
            - returns (list[float]): Series of periodic returns.
            - trade_count (int): Number of trades executed.
        dsr_threshold: Minimum DSR probability to keep (default 0.95).
        nb_trials: Number of independent trials. If None, uses len(strategies).

    Returns:
        Filtered list of strategy dicts. Each dict gets an added 'dsr_score' field.
    """
    if not strategies:
        return []

    if nb_trials is None:
        nb_trials = len(strategies)

    genuine = []

    for strat in strategies:
        returns = strat["returns"]
        sr = strat["sharpe"]

        if len(returns) < 4:
            strat["dsr_score"] = 0.0
            continue

        stats = returns_stats(returns)
        horizon = len(returns)

        sr_var = sharpe_variance(sr, horizon, stats["skewness"], stats["kurtosis"])
        dsr = deflated_sharpe_ratio(
            estimated_sharpe=sr,
            sr_variance=sr_var,
            nb_trials=nb_trials,
            backtest_horizon=horizon,
            skew=stats["skewness"],
            kurtosis=stats["kurtosis"],
        )

        strat["dsr_score"] = round(dsr, 6)

        if dsr >= dsr_threshold:
            genuine.append(strat)

    return genuine


if __name__ == "__main__":
    np.random.seed(11)

    # Scenario: a quant team backtested 200 strategy variants, selected the
    # 10 with the highest in-sample Sharpe. DSR reveals which are genuine.
    NB_TRIALS = 1000
    strategies = []

    # --- Noise strategies (should mostly fail DSR) ---
    # Zero true alpha. Some get lucky in-sample Sharpes from short histories.
    # We hardcode plausible "cherry-picked best" Sharpes and attach
    # matching return series to make the demo deterministic and clear.
    noise_names = [
        "Overfit-MA-Cross", "Overfit-Breakout", "Overfit-RSI-Tilt",
        "Overfit-BBand", "Overfit-MACD-Div", "Overfit-Ichimoku",
        "Overfit-Fib-Retrace",
    ]
    for name in noise_names:
        # Pure noise: zero true mean, random daily returns, short history.
        n_obs = np.random.randint(50, 150)
        ret = np.random.normal(0.0, 0.02, n_obs)
        sr = float(np.mean(ret) / max(np.std(ret, ddof=1), 1e-12) * np.sqrt(252))
        strategies.append({
            "name": name,
            "sharpe": sr,
            "returns": ret.tolist(),
            "trade_count": n_obs,
        })

    # --- Genuine strategies (should pass DSR) ---
    # High Sharpe + long track records = statistically significant even after
    # correcting for 200 trials.
    genuine_configs = [
        ("Connors-RSI2-SPY", 0.003, 0.01, 750),   # Sharpe ~4.8
        ("MeanRevert-ETH",   0.002, 0.008, 600),   # Sharpe ~3.9
        ("FundingArb-BTC",   0.0025, 0.012, 500),  # Sharpe ~3.3
    ]
    for name, mu, sigma, n_obs in genuine_configs:
        ret = np.random.normal(mu, sigma, n_obs)
        sr = float(np.mean(ret) / np.std(ret, ddof=1) * np.sqrt(252))
        strategies.append({
            "name": name,
            "sharpe": sr,
            "returns": ret.tolist(),
            "trade_count": n_obs,
        })

    print("=" * 70)
    print("Deflated Sharpe Ratio -- Strategy Filter Demo")
    print(f"Total strategies presented: {len(strategies)}")
    print(f"Total backtests attempted (nb_trials): {NB_TRIALS}")
    print("=" * 70)

    print(f"\n{'Strategy':<22} {'Sharpe':>8} {'Obs':>6} {'DSR':>8} {'Pass?':>6}")
    print("-" * 54)

    genuine = filter_edge_strategies(
        strategies, dsr_threshold=0.95, nb_trials=NB_TRIALS
    )
    passing_names = {s["name"] for s in genuine}

    for s in strategies:
        passed = "YES" if s["name"] in passing_names else "no"
        print(
            f"{s['name']:<22} {s['sharpe']:>8.2f} "
            f"{len(s['returns']):>6} {s.get('dsr_score', 0):>8.4f} "
            f"{passed:>6}"
        )

    print(f"\n{len(genuine)} of {len(strategies)} strategies passed DSR >= 0.95")
    if genuine:
        print("\nGenuine strategies:")
        for s in genuine:
            print(f"  - {s['name']} (Sharpe={s['sharpe']:.2f}, DSR={s['dsr_score']:.4f})")

