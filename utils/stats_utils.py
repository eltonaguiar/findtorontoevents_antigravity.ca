import numpy as np
import pandas as pd
from typing import Dict, List, Sequence, Tuple


def herfindahl_index(weights: Sequence[float]) -> float:
    """HHI = sum(w_i^2). weights should sum to ~1."""
    w = np.asarray(weights, dtype=float)
    if w.size == 0:
        return 0.0
    s = w.sum()
    if s <= 0:
        return 0.0
    w = w / s
    return float(np.sum(w ** 2))


def gini_coefficient(values: Sequence[float]) -> float:
    """Gini on non-negative weights (0 = equal, 1 = one dominates)."""
    x = np.sort(np.asarray(values, dtype=float))
    if x.size == 0 or x.sum() <= 0:
        return 0.0
    n = x.size
    index = np.arange(1, n + 1)
    return float((2 * np.sum(index * x) / (n * x.sum())) - (n + 1) / n)


def concentration_report(counts: Dict[str, int]) -> Dict[str, float]:
    """HHI, Gini, top-5 share from label→count map."""
    total = sum(counts.values()) or 1
    weights = [c / total for c in counts.values()]
    sorted_w = sorted(weights, reverse=True)
    return {
        "hhi": herfindahl_index(weights),
        "gini": gini_coefficient(list(counts.values())),
        "top5_share": float(sum(sorted_w[:5])),
        "n_buckets": len(counts),
    }


def block_bootstrap_sharpe_pvalue(
    returns: np.ndarray,
    block_size: int = 20,
    n_iter: int = 1000,
    seed: int = 42,
) -> Tuple[float, float]:
    """Block-bootstrap p-value for mean/std Sharpe-like stat."""
    from verified_strategies.pipeline.monte_carlo import block_bootstrap_pvalue

    returns = np.asarray(returns, dtype=float)
    if len(returns) < block_size + 2:
        return 1.0, 0.0
    observed = returns.mean() / (returns.std() + 1e-12)
    p, _, _ = block_bootstrap_pvalue(returns, observed, block_size, n_iter, seed)
    return p, observed


def calculate_hurst(series: pd.Series, max_lag: int = 100) -> float:
    """
    Calculate the Hurst exponent of a time series.
    
    H < 0.5: Mean-reverting series
    H = 0.5: Random walk (Brownian motion)
    H > 0.5: Trending series
    """
    if len(series) < 20:
        return 0.5
        
    lags = range(2, max_lag)
    tau = [np.std(np.subtract(series[lag:], series[:-lag])) for lag in lags]
    
    # Use log-log regression to find the slope
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    
    return poly[0] * 2.0
