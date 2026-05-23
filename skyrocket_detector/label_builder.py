"""
Skyrocket Label Builder
========================
Builds binary labels from OHLCV data for the skyrocket detector.

For each bar t, computes:
  max_forward_return = max(high[t+1 : t+FORWARD_WINDOW]) / close[t] - 1
  label = 1 if max_forward_return >= SKYROCKET_THRESHOLD else 0

Also computes time_to_peak (bars until max high was reached).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def build_labels(
    df: pd.DataFrame,
    threshold: float = None,
    forward_window: int = None,
) -> pd.DataFrame:
    """
    Add skyrocket labels to an OHLCV DataFrame.

    Args:
        df: DataFrame with columns [open, high, low, close, volume].
             Must have a datetime index or a 'timestamp' column.
        threshold: Minimum forward return to label as skyrocket (default: config.SKYROCKET_THRESHOLD).
        forward_window: Number of bars to look ahead (default: config.FORWARD_WINDOW).

    Returns:
        DataFrame with added columns:
          - max_forward_return: best possible return in the forward window
          - time_to_peak: bars until that max was reached
          - label: 1 if max_forward_return >= threshold, else 0
        Last `forward_window` bars will have NaN labels (can't look ahead).
    """
    if threshold is None:
        threshold = config.SKYROCKET_THRESHOLD
    if forward_window is None:
        forward_window = config.FORWARD_WINDOW

    df = df.copy()
    n = len(df)

    close_arr = df["close"].values.astype(float)
    high_arr = df["high"].values.astype(float)

    max_forward_ret = np.full(n, np.nan)
    time_to_peak = np.full(n, np.nan, dtype=float)

    for i in range(n - forward_window):
        # Forward window: bars i+1 through i+forward_window (inclusive)
        start = i + 1
        end = i + forward_window + 1  # exclusive slice

        forward_highs = high_arr[start:end]
        if len(forward_highs) == 0:
            continue

        max_high = np.max(forward_highs)
        max_forward_ret[i] = (max_high / close_arr[i]) - 1.0

        # Time to peak: index of first occurrence of max high in forward window
        peak_idx = np.argmax(forward_highs)
        time_to_peak[i] = peak_idx + 1  # +1 because bar i+1 is 1 bar ahead

    df["max_forward_return"] = max_forward_ret
    df["time_to_peak"] = time_to_peak
    df["label"] = np.where(max_forward_ret >= threshold, 1, np.nan)
    # Set label to 0 where we have a valid return but it's below threshold
    valid_mask = ~np.isnan(max_forward_ret)
    df.loc[valid_mask & (df["max_forward_return"] < threshold), "label"] = 0

    # Print stats
    total_bars = n
    labelable = valid_mask.sum()
    positives = int((df["label"] == 1).sum())
    negatives = int((df["label"] == 0).sum())
    unlabeled = total_bars - labelable
    pos_rate = positives / labelable * 100 if labelable > 0 else 0

    print(f"[label_builder] Total bars: {total_bars}")
    print(f"[label_builder] Labelable bars: {labelable} (last {forward_window} bars unlabeled)")
    print(f"[label_builder] Positive (skyrocket): {positives} ({pos_rate:.1f}%)")
    print(f"[label_builder] Negative: {negatives}")
    if positives > 0:
        avg_ttp = df.loc[df["label"] == 1, "time_to_peak"].mean()
        avg_ret = df.loc[df["label"] == 1, "max_forward_return"].mean()
        print(f"[label_builder] Avg time to peak (positives): {avg_ttp:.1f} bars")
        print(f"[label_builder] Avg max forward return (positives): {avg_ret:.1%}")

    return df


def build_labels_from_arrays(
    timestamps: list,
    opens: list,
    highs: list,
    lows: list,
    closes: list,
    volumes: list,
    threshold: float = None,
    forward_window: int = None,
) -> pd.DataFrame:
    """
    Convenience: build labels from raw arrays (e.g., from API responses).

    Args:
        timestamps: list of timestamps (ms or datetime)
        opens, highs, lows, closes, volumes: OHLCV arrays
        threshold, forward_window: override config defaults

    Returns:
        Labeled DataFrame.
    """
    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })
    return build_labels(df, threshold=threshold, forward_window=forward_window)
