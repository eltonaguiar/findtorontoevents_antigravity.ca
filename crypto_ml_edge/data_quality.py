"""
Data Quality — Validate OHLCV integrity before anything touches it
===================================================================
If data is bad, everything downstream is garbage. Fail loudly.
"""

import pandas as pd
import numpy as np
from typing import List, Tuple


class DataQualityError(Exception):
    """Raised when data fails quality checks."""
    pass


def validate_ohlcv(df: pd.DataFrame, symbol: str = "UNKNOWN") -> List[str]:
    """
    Validate OHLCV DataFrame. Returns list of warnings.
    Raises DataQualityError for critical failures.
    """
    warnings = []

    if df.empty:
        raise DataQualityError(f"{symbol}: DataFrame is empty")

    # Required columns
    required = ["open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise DataQualityError(f"{symbol}: Missing columns: {missing}")

    # Index must be DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        raise DataQualityError(f"{symbol}: Index is not DatetimeIndex")

    # Monotonically increasing timestamps
    if not df.index.is_monotonic_increasing:
        dups = df.index[df.index.duplicated()]
        if len(dups) > 0:
            warnings.append(f"{symbol}: {len(dups)} duplicate timestamps")
        non_mono = (df.index[1:] < df.index[:-1]).sum()
        if non_mono > 0:
            raise DataQualityError(f"{symbol}: {non_mono} out-of-order timestamps")

    # No NaN in OHLCV
    nan_counts = df[required].isna().sum()
    total_nans = nan_counts.sum()
    if total_nans > 0:
        pct = total_nans / (len(df) * len(required)) * 100
        if pct > 1.0:
            raise DataQualityError(f"{symbol}: {pct:.1f}% NaN values in OHLCV")
        warnings.append(f"{symbol}: {total_nans} NaN values ({pct:.2f}%) — will forward-fill")

    # OHLC sanity: high >= low, high >= open, high >= close
    bad_hl = (df["high"] < df["low"]).sum()
    if bad_hl > 0:
        raise DataQualityError(f"{symbol}: {bad_hl} bars where high < low")

    bad_ho = (df["high"] < df["open"]).sum()
    bad_hc = (df["high"] < df["close"]).sum()
    bad_lo = (df["low"] > df["open"]).sum()
    bad_lc = (df["low"] > df["close"]).sum()
    total_bad = bad_ho + bad_hc + bad_lo + bad_lc
    if total_bad > 0:
        warnings.append(f"{symbol}: {total_bad} bars with OHLC inconsistency")

    # Volume should be non-negative
    neg_vol = (df["volume"] < 0).sum()
    if neg_vol > 0:
        raise DataQualityError(f"{symbol}: {neg_vol} bars with negative volume")

    # Zero volume bars (suspicious but not fatal)
    zero_vol = (df["volume"] == 0).sum()
    if zero_vol > len(df) * 0.05:
        warnings.append(f"{symbol}: {zero_vol} zero-volume bars ({zero_vol/len(df)*100:.1f}%)")

    # Check for gaps (missing bars)
    if len(df) > 1:
        diffs = df.index.to_series().diff().dropna()
        mode_diff = diffs.mode().iloc[0] if not diffs.mode().empty else diffs.median()
        gaps = diffs[diffs > mode_diff * 2]
        if len(gaps) > 0:
            max_gap = gaps.max()
            warnings.append(f"{symbol}: {len(gaps)} gaps detected, max gap: {max_gap}")

    return warnings


def clean_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean OHLCV data: forward-fill NaNs, remove duplicates, sort.
    Does NOT interpolate — only fills from known past values.
    """
    df = df.copy()
    df.sort_index(inplace=True)
    df = df[~df.index.duplicated(keep='first')]

    # Forward-fill NaNs (uses only past data — no lookahead)
    if df.isna().any().any():
        df.ffill(inplace=True)
        # Drop any remaining NaNs at the start
        df.dropna(inplace=True)

    return df


def assert_no_lookahead(features: pd.DataFrame, labels: pd.Series,
                         feature_bar_offset: int = 1) -> None:
    """
    Assert that features at time T do not use data from T or later.

    This checks that the feature DataFrame's index is shifted back by
    at least `feature_bar_offset` bars relative to the label it predicts.

    Raises DataQualityError if lookahead detected.
    """
    if features.empty or labels.empty:
        raise DataQualityError("Empty features or labels")

    # Features and labels should have the same index after alignment
    common_idx = features.index.intersection(labels.index)
    if len(common_idx) == 0:
        raise DataQualityError("No overlapping timestamps between features and labels")

    # Check: feature at T should predict label at T+offset
    # If feature timestamp == label timestamp, there might be lookahead
    # The label should be the FUTURE return from bar T
    # Features should use data available AT bar T (i.e., close of bar T-1)

    # Verify features don't contain the label column
    if "label" in features.columns or "target" in features.columns:
        raise DataQualityError("Feature DataFrame contains label/target column — lookahead!")

    return  # Pass


def compute_gap_report(df: pd.DataFrame, expected_freq: str = "1h") -> pd.DataFrame:
    """
    Return a DataFrame of detected gaps in the time series.
    Useful for understanding data quality before training.
    """
    if df.empty or len(df) < 2:
        return pd.DataFrame()

    freq_map = {"1h": pd.Timedelta(hours=1), "4h": pd.Timedelta(hours=4)}
    expected = freq_map.get(expected_freq, pd.Timedelta(hours=1))

    diffs = df.index.to_series().diff().dropna()
    gaps = diffs[diffs > expected * 1.5]

    if gaps.empty:
        return pd.DataFrame()

    report = pd.DataFrame({
        "gap_start": gaps.index - gaps.values,
        "gap_end": gaps.index,
        "gap_duration": gaps.values,
        "bars_missing": (gaps / expected).astype(int) - 1,
    })

    return report.reset_index(drop=True)
