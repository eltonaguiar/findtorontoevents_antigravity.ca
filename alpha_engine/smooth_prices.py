"""
Savitzky-Golay price smoother (G7 enhancement).

Reduces tick noise on mid-cap assets before indicator calculation.
Optional utility -- strategies call smooth_prices() to get filtered close data.
Gracefully falls back to raw prices if scipy is unavailable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def smooth_prices(prices, window: int = 7, polyorder: int = 2):
    """Apply Savitzky-Golay filter to reduce price noise.

    Parameters
    ----------
    prices : array-like (list, np.ndarray, or pd.Series)
        Close price series.
    window : int
        Filter window length (must be odd and > polyorder). Default 7.
    polyorder : int
        Polynomial order for the local fit. Default 2.

    Returns
    -------
    Same type as input, with smoothed values. Length is preserved.
    If scipy is missing or the series is too short, returns *prices* unchanged.
    """
    try:
        from scipy.signal import savgol_filter
    except ImportError:
        return prices  # no scipy -- return raw

    # Coerce to numpy for the filter
    is_series = isinstance(prices, pd.Series)
    arr = np.asarray(prices, dtype=float)

    if len(arr) < window:
        return prices

    smoothed = savgol_filter(arr, window_length=window, polyorder=polyorder)

    if is_series:
        return pd.Series(smoothed, index=prices.index, name=prices.name)
    return smoothed


def smooth_ohlcv(df: pd.DataFrame, window: int = 7, polyorder: int = 2) -> pd.DataFrame:
    """Return a copy of an OHLCV DataFrame with smoothed Close column.

    Leaves Open, High, Low, Volume untouched (they are needed for
    candlestick / volume analysis). Only Close is filtered, which is
    what most indicator libraries (ta, talib) consume for signals.
    """
    out = df.copy()
    if "Close" in out.columns and len(out) >= window:
        out["Close"] = smooth_prices(out["Close"], window=window, polyorder=polyorder)
    return out
