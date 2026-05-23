"""
Fractional Differentiation (FFD) -- Lopez de Prado (2018), Chapter 5
====================================================================
Standard differencing (returns, d=1) destroys memory.  Raw prices are
non-stationary.  Fractional differentiation with d ~ 0.4 preserves
~60% of memory (high correlation with original series) while passing
the ADF stationarity test.

Reference: "Advances in Financial Machine Learning", M. Lopez de Prado,
Wiley 2018, Chapter 5, Algorithm 5.2 (Fixed-Width Window FFD).

Usage
-----
Standalone::

    from crypto_ml_edge.features.fracdiff import frac_diff_ffd
    ffd_series = frac_diff_ffd(df['close'], d=0.4)

Via feature engine (always included as ``close_ffd``)::

    from crypto_ml_edge.features import build_features
    feat = build_features(ohlcv_df)
    # feat['close_ffd'] is the fractionally differentiated close price
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def get_weights_ffd(d: float, threshold: float = 1e-4) -> np.ndarray:
    """Compute fixed-width window fractional differentiation weights.

    Lopez de Prado (2018), Chapter 5, Algorithm 5.2.

    The weights are the coefficients of the binomial series expansion
    of (1 - B)^d truncated when |w_k| < *threshold*.

    Parameters
    ----------
    d : float
        Fractional differentiation order (0 < d < 1).
    threshold : float
        Absolute weight cutoff.  Weights smaller than this are dropped,
        giving the "fixed-width window" variant.

    Returns
    -------
    np.ndarray
        Weight vector of shape ``(width, 1)``, ordered from oldest to
        newest (i.e. ``weights[0]`` multiplies the oldest bar in the
        window and ``weights[-1]`` multiplies the current bar).
    """
    weights = [1.0]
    k = 1
    while True:
        w = -weights[-1] * (d - k + 1) / k
        if abs(w) < threshold:
            break
        weights.append(w)
        k += 1
    return np.array(weights[::-1]).reshape(-1, 1)


def frac_diff_ffd(
    series: pd.Series,
    d: float = 0.4,
    threshold: float = 1e-4,
) -> pd.Series:
    """Apply fixed-width-window fractional differentiation to a price series.

    ``d=0.4`` is the sweet spot identified by Lopez de Prado: it passes
    the ADF stationarity test at the 5% level while retaining ~60% of
    the memory (Pearson correlation with the original series).

    Parameters
    ----------
    series : pd.Series
        Price series (e.g. close prices).  Must be numeric with no
        infinite values.
    d : float
        Differentiation order.  ``0 < d < 1``.  Common choices:

        * ``d=0.0`` -- no differencing (original series, non-stationary)
        * ``d=0.4`` -- default; best memory/stationarity trade-off
        * ``d=1.0`` -- full differencing (equivalent to returns)

    threshold : float
        Weight cutoff for the FFD window.  Default ``1e-4`` gives a
        ~282-bar lookback window for d=0.4 (practical for 1h data,
        ~12 days).  Use ``1e-5`` for higher precision (1458 bars,
        ~61 days) if you have enough data.

    Returns
    -------
    pd.Series
        Fractionally differentiated series.  Length is shorter than
        *series* by ``(window_width - 1)`` leading NaN rows which are
        dropped.  Index is preserved for the valid portion.
    """
    weights = get_weights_ffd(d, threshold)
    width = len(weights)

    if width > len(series):
        # Not enough data to apply even one convolution step.
        return pd.Series(dtype=float)

    result = pd.Series(index=series.index, dtype=float)
    series_values = series.values  # avoid repeated .iloc overhead

    for i in range(width - 1, len(series)):
        window = series_values[i - width + 1 : i + 1]
        result.iloc[i] = np.dot(weights.T, window)[0]

    return result.dropna()


def add_fracdiff_features(
    df: pd.DataFrame,
    price_col: str = "close",
    d: float = 0.4,
    threshold: float = 1e-4,
) -> pd.DataFrame:
    """Add a fractionally differentiated price column to a DataFrame.

    The new column is named ``{price_col}_ffd`` (e.g. ``close_ffd``).
    Rows where the FFD value could not be computed (leading warm-up
    window) will contain ``NaN``.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain *price_col*.
    price_col : str
        Column name of the raw price series.
    d : float
        Fractional differentiation order (default 0.4).
    threshold : float
        Weight cutoff for the FFD window.

    Returns
    -------
    pd.DataFrame
        Copy of *df* with an additional ``{price_col}_ffd`` column.

    Example
    -------
    ::

        df = add_fracdiff_features(df, 'close', d=0.4)
        # Now use 'close_ffd' as a feature instead of raw 'close' or returns
    """
    df = df.copy()
    ffd = frac_diff_ffd(df[price_col], d=d, threshold=threshold)
    col_name = f"{price_col}_ffd"
    df[col_name] = ffd
    return df
