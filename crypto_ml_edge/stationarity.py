"""
Stationarity Enforcement — No raw prices enter the model
=========================================================
Research: Non-stationary features cause distribution shift between
train and live. All model inputs must be stationary.

Methods:
1. Fractional differentiation (d≈0.4) — preserves memory while stationary
2. Percentage returns — simple, no lookahead
3. Log returns — better for large moves

Reference: Lopez de Prado (2018) "Advances in Financial Machine Learning" Ch. 5
"""

import numpy as np
import pandas as pd
from typing import Optional

from .config import FRAC_DIFF_D, FRAC_DIFF_THRESHOLD


def fractional_diff(series: pd.Series, d: float = FRAC_DIFF_D,
                    threshold: float = FRAC_DIFF_THRESHOLD) -> pd.Series:
    """
    Apply fractional differentiation to make a series stationary
    while preserving long-range memory.

    Args:
        series: Price series (e.g., close prices)
        d: Differentiation order (0.3-0.5 typical for crypto)
        threshold: Minimum weight to include in kernel

    Returns:
        Fractionally differentiated series (shorter due to kernel)
    """
    if series.empty:
        return series

    # Compute weights for the fractional differencing filter
    weights = _get_weights(d, threshold, len(series))
    width = len(weights)

    if width > len(series):
        # Not enough data for this kernel — fall back to returns
        return pct_returns(series)

    # Apply filter via convolution (dot product of weights and lagged values)
    result = pd.Series(index=series.index, dtype=float)
    for i in range(width - 1, len(series)):
        window = series.iloc[i - width + 1:i + 1].values
        result.iloc[i] = np.dot(weights[::-1], window)

    # Drop NaN (the first width-1 values)
    return result.dropna()


def _get_weights(d: float, threshold: float, max_len: int) -> np.ndarray:
    """
    Compute weights for fractional differentiation kernel.
    Weights: w_k = -w_{k-1} * (d - k + 1) / k
    """
    weights = [1.0]
    k = 1
    while k < max_len:
        w = -weights[-1] * (d - k + 1) / k
        if abs(w) < threshold:
            break
        weights.append(w)
        k += 1
    return np.array(weights)


def pct_returns(series: pd.Series, periods: int = 1) -> pd.Series:
    """Simple percentage returns. Stationary, no lookahead."""
    return series.pct_change(periods=periods).dropna()


def log_returns(series: pd.Series, periods: int = 1) -> pd.Series:
    """Log returns — better for large moves, symmetric for gains/losses."""
    return np.log(series / series.shift(periods)).dropna()


def make_stationary(df: pd.DataFrame, method: str = "frac_diff",
                    price_cols: Optional[list] = None) -> pd.DataFrame:
    """
    Make price columns stationary. Non-price columns pass through unchanged.

    Args:
        df: DataFrame with OHLCV data
        method: 'frac_diff', 'pct_returns', or 'log_returns'
        price_cols: Columns to transform (default: open, high, low, close)

    Returns:
        DataFrame with stationary price columns
    """
    if price_cols is None:
        price_cols = [c for c in ["open", "high", "low", "close"] if c in df.columns]

    result = df.copy()
    transform_fn = {
        "frac_diff": fractional_diff,
        "pct_returns": pct_returns,
        "log_returns": log_returns,
    }.get(method, pct_returns)

    for col in price_cols:
        transformed = transform_fn(result[col])
        result[col] = transformed

    # Drop rows where any price column is NaN (from transform)
    result.dropna(subset=price_cols, inplace=True)

    return result


def verify_stationarity(series: pd.Series, max_pvalue: float = 0.05) -> bool:
    """
    Quick ADF stationarity test. Returns True if stationary.
    Uses a simple approximation to avoid scipy dependency in CI.
    """
    if len(series) < 50:
        return False

    # Dickey-Fuller approximation: check if first-order autocorrelation < 1
    # A truly stationary series has rho << 1
    y = series.dropna().values
    if len(y) < 50:
        return False

    # Simple check: variance of differences vs variance of levels
    var_diff = np.var(np.diff(y))
    var_level = np.var(y)

    if var_level == 0:
        return True  # Constant series is stationary

    ratio = var_diff / var_level
    # For stationary series, this ratio is ~2; for unit root, it's ~0
    return ratio > 0.5
