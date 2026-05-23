"""
Feature Vector Snapshot — captures all features at prediction time for retraining.

Design Section 3E: Every forward-test pick must store ALL features computed at
entry time so we can reconstruct labeled training rows without re-fetching
historical klines (which may produce different candle boundaries or missing data).
"""

import math
import numpy as np


def sanitize_feature_value(v):
    """Convert a single feature value to a JSON-serializable Python float.

    Handles: numpy scalars, numpy floats, NaN, Inf, Python ints/floats.
    Returns 0.0 for any non-finite value.
    """
    try:
        val = float(v)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(val) or math.isinf(val):
        return 0.0
    return val


def snapshot_from_dict(d: dict) -> dict:
    """Sanitize a dict of feature_name -> value."""
    return {str(k): sanitize_feature_value(v) for k, v in d.items()}


def snapshot_from_series(series) -> dict:
    """Snapshot from a pandas Series (index = feature names, values = feature values)."""
    return {str(k): sanitize_feature_value(v) for k, v in series.items()}


def snapshot_from_array(values, names: list) -> dict:
    """Snapshot from a numpy array + list of feature names.

    If names and values have different lengths, uses min(len) and
    labels any extras as 'feature_N'.
    """
    result = {}
    n = min(len(names), len(values))
    for i in range(n):
        result[str(names[i])] = sanitize_feature_value(values[i])
    # If values is longer than names, add remaining with generic keys
    for i in range(n, len(values)):
        result[f"feature_{i}"] = sanitize_feature_value(values[i])
    return result


def snapshot_from_dataframe_row(df, row_index: int = -1) -> dict:
    """Snapshot from a DataFrame row (last row by default).

    Uses column names as feature names.
    """
    row = df.iloc[row_index]
    return {str(col): sanitize_feature_value(row[col]) for col in df.columns}
