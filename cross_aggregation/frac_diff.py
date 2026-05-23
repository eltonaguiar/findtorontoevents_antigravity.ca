"""
Fractional Differentiation — Fixed-Width Window (FFD)
=====================================================
Lopez de Prado, Advances in Financial Machine Learning, Ch. 5.

Raw prices are non-stationary (unit root), which violates ML model assumptions.
Standard differencing (returns) removes ALL memory. Fractional differentiation
with d~0.4 removes just enough non-stationarity while preserving predictive
memory — the optimal balance for ML features.

Usage::

    from cross_aggregation.frac_diff import frac_diff_ffd, add_frac_diff_features

    # Single series
    close_ffd = frac_diff_ffd(df["close"], d=0.4)

    # Batch: adds close_ffd, high_ffd, low_ffd, volume_ffd columns
    df = add_frac_diff_features(df, d=0.4)
"""

import numpy as np
import pandas as pd


def get_weights_ffd(d: float, threshold: float = 1e-4) -> np.ndarray:
    """Fixed-width window fractional differentiation weights.

    Computes the binomial series weights w_k = prod_{i=1}^{k} (d - i + 1) / i,
    truncated when |w_k| < threshold.

    Parameters
    ----------
    d : float
        Differentiation order. 0 = original series, 1 = first difference.
        Typical range for prices: 0.3-0.5 (0.4 recommended).
    threshold : float
        Weight cutoff — smaller values use more history (more memory retained).

    Returns
    -------
    np.ndarray
        Weight vector, shape (width, 1), oldest-to-newest ordering.
    """
    w = [1.0]
    k = 1
    while True:
        w_next = -w[-1] * (d - k + 1) / k
        if abs(w_next) < threshold:
            break
        w.append(w_next)
        k += 1
    return np.array(w[::-1]).reshape(-1, 1)


def frac_diff_ffd(series: pd.Series, d: float = 0.4,
                  threshold: float = 1e-4) -> pd.Series:
    """Apply fixed-width window fractional differentiation to a price series.

    The FFD method uses a fixed number of weights (determined by threshold),
    making it practical for real-time applications — no expanding window.

    Parameters
    ----------
    series : pd.Series
        Price series (e.g., close prices). Must be numeric.
    d : float
        Differentiation order (0.3-0.5 typical, 0.4 recommended).
    threshold : float
        Weight cutoff threshold. Smaller = more memory retained.

    Returns
    -------
    pd.Series
        Fractionally differentiated series (same index, NaN-padded at start
        where insufficient history exists for the weight window).
    """
    weights = get_weights_ffd(d, threshold)
    width = len(weights)
    result = pd.Series(index=series.index, dtype=float)

    # Vectorised dot product for each valid window position
    values = series.values.astype(float)
    w_flat = weights.flatten()
    for i in range(width - 1, len(values)):
        result.iloc[i] = np.dot(w_flat, values[i - width + 1: i + 1])

    return result


def add_frac_diff_features(df: pd.DataFrame, d: float = 0.4,
                           threshold: float = 1e-4) -> pd.DataFrame:
    """Add fractionally differentiated price features to a DataFrame.

    For each OHLCV column present, adds a ``{col}_ffd`` column containing
    the FFD-transformed series.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain some subset of 'close', 'high', 'low', 'volume'.
        Column names are case-insensitive (handles 'Close' and 'close').
    d : float
        Differentiation order (default 0.4, Lopez de Prado recommendation).
    threshold : float
        Weight cutoff for FFD window width.

    Returns
    -------
    pd.DataFrame
        Original DataFrame with added ``*_ffd`` columns.
    """
    # Handle both lowercase and Title-case column names
    col_map = {}
    for target in ["close", "high", "low", "volume"]:
        if target in df.columns:
            col_map[target] = target
        elif target.capitalize() in df.columns:
            col_map[target] = target.capitalize()

    for label, actual_col in col_map.items():
        df[f"{label}_ffd"] = frac_diff_ffd(df[actual_col], d=d,
                                           threshold=threshold)

    return df
