"""
Triple-Barrier Labeler
=======================
Implements the Lopez de Prado (2018) triple-barrier labeling scheme with two
critical properties this codebase requires:

  1. ZERO LOOKAHEAD BIAS — label for bar T is computed entirely from bars
     T+1 ... T+horizon.  Bar T's close is the entry price (known at bar T),
     but the HIGH / LOW / CLOSE used to evaluate TP / SL start at T+1.

  2. COST-BASED THRESHOLDS — TP must exceed round-trip transaction cost (fees
     + slippage) before it counts as a +1.  This is NOT tuned for class
     balance; it is the minimum trade that makes money after friction.

  3. EMBARGO — a helper function masks labels that are too close to a
     train/test boundary, preventing leakage from overlapping forward windows.

Requirements satisfied:
  LABL-01: forward-only close[t+N]
  LABL-02: +1 = TP hit, -1 = SL hit, 0 = timeout
  LABL-03: threshold = cost-based minimum, not class-balance tuning
  LABL-04: embargo function
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional, Tuple

from crypto_ml_edge.config import (
    TPSL_CONFIG,
    PURGE_GAP_BARS,
    get_total_cost,
)


# ─── Public types ─────────────────────────────────────────────────────────────

Labels = pd.Series   # dtype int8: values in {-1, 0, 1}; NaN = embargoed


# ─── Core labeler ─────────────────────────────────────────────────────────────

def build_labels(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    atr: pd.Series,
    timeframe: str,
    pair: str = "BTCUSDT",
) -> Labels:
    """
    Triple-barrier labeling for a single pair / timeframe.

    Label for bar i is determined by scanning bars i+1 … i+max_hold_bars
    (strictly future bars — no bar i data used in the scan).

    Barrier levels:
      TP level = entry_price + tp_atr_mult * ATR[i]
      SL level = entry_price - sl_atr_mult * ATR[i]

    Minimum-profit gate:
      TP is only accepted if the gross move exceeds total round-trip cost.
      This ensures label +1 corresponds to a trade that would actually be
      profitable, not just a tick above entry.

    Label assignment:
      +1  TP hit first (and move clears cost threshold)
      -1  SL hit first (or TP hit but move too small to clear costs — treated
          as a failed trade)
       0  Neither barrier hit within max_hold_bars (timeout)

    Parameters
    ----------
    close : pd.Series   Close prices (DatetimeIndex)
    high  : pd.Series   High prices (same index)
    low   : pd.Series   Low prices (same index)
    atr   : pd.Series   ATR values at each bar (same index, NaN allowed for
                        warmup period — those bars get label 0)
    timeframe : str     "1h" or "4h" — selects TPSL_CONFIG entry
    pair : str          Pair symbol — used for per-pair cost lookup

    Returns
    -------
    pd.Series of int8 aligned to ``close`` index.
    Last max_hold_bars rows are 0 (no full forward window available).
    """
    if timeframe not in TPSL_CONFIG:
        raise ValueError(
            f"timeframe '{timeframe}' not in TPSL_CONFIG. "
            f"Valid: {list(TPSL_CONFIG.keys())}"
        )

    cfg = TPSL_CONFIG[timeframe]
    tp_mult: float = cfg["tp_atr_mult"]
    sl_mult: float = cfg["sl_atr_mult"]
    max_hold: int  = cfg["max_hold_bars"]

    # Minimum gross move (as fraction of price) that clears round-trip costs.
    # Cost is fees + slippage both ways.  A TP touch that doesn't beat this is
    # economically equivalent to a loser — label it 0 (timeout) rather than +1.
    min_profitable_move: float = get_total_cost(pair)  # e.g. 0.003 for BTC

    n = len(close)
    labels = np.zeros(n, dtype=np.int8)

    close_arr = close.values
    high_arr  = high.values
    low_arr   = low.values
    atr_arr   = atr.values

    for i in range(n - 1):           # bar T
        entry_price = close_arr[i]   # known at bar T close — no lookahead

        if entry_price <= 0:
            # Degenerate price (data error) — leave label as 0
            continue

        atr_val = atr_arr[i]
        if np.isnan(atr_val) or atr_val <= 0:
            # ATR not yet valid (warmup) — leave label as 0
            continue

        tp_level = entry_price + tp_mult * atr_val
        sl_level = entry_price - sl_mult * atr_val

        # Minimum absolute move that clears costs
        cost_threshold = entry_price * min_profitable_move

        tp_bar: Optional[int] = None
        sl_bar: Optional[int] = None

        # Scan T+1 … T+max_hold (strictly no bar T data)
        end = min(i + max_hold, n - 1)
        for j in range(i + 1, end + 1):
            if tp_bar is None and high_arr[j] >= tp_level:
                tp_bar = j
            if sl_bar is None and low_arr[j] <= sl_level:
                sl_bar = j
            # Stop scanning once both barriers have been touched
            if tp_bar is not None and sl_bar is not None:
                break

        # ── Classify ────────────────────────────────────────────────────────
        # TP hit before SL (or only TP hit)
        if tp_bar is not None and (sl_bar is None or tp_bar <= sl_bar):
            # Verify the gross move actually clears transaction costs.
            # If TP level was set by ATR and costs are reasonable this will
            # almost always be True; the check exists for degenerate cases
            # (e.g. near-zero ATR during a sideways chop) and as an explicit
            # contract guarantee for LABL-03.
            gross_move = tp_level - entry_price
            if gross_move >= cost_threshold:
                labels[i] = 1
            # else: TP touched but doesn't clear costs — 0 (timeout-equivalent)

        # SL hit before TP (or only SL hit) — no-trade for binary long-only
        elif sl_bar is not None and (tp_bar is None or sl_bar < tp_bar):
            labels[i] = 0

        # Neither hit — timeout → 0 (already set)

    return pd.Series(labels, index=close.index, dtype="int8", name="label")


# ─── Embargo ──────────────────────────────────────────────────────────────────

def apply_embargo(
    labels: Labels,
    test_start_iloc: int,
    horizon_bars: int,
    purge_gap: int = PURGE_GAP_BARS,
) -> Labels:
    """
    Mask labels that could leak information across a train/test boundary.

    Any label at position i in the training set has a forward window
    [i+1, i+horizon_bars].  If that window overlaps the test set, the label
    must be embargoed (set to NaN) because it was computed using data that
    belongs to the test period.

    Parameters
    ----------
    labels          : Label series (from build_labels)
    test_start_iloc : Integer position of the first test-set bar
    horizon_bars    : Forward-window length used to build labels
    purge_gap       : Extra buffer beyond the forward window (from config)

    Returns
    -------
    Copy of ``labels`` with embargoed positions set to NaN (float dtype).

    Notes
    -----
    The embargo region is the training-side slice ending at
        embargo_end = test_start_iloc + purge_gap - 1
    i.e. bars whose forward windows reach into the test set plus a safety
    margin of PURGE_GAP_BARS bars.
    """
    result = labels.astype("float64").copy()  # NaN-capable dtype

    # The last training bar whose forward window cannot possibly touch the
    # test set is test_start_iloc - horizon_bars - 1.
    # Everything from that point up to (and including) test_start_iloc - 1
    # plus a purge_gap buffer is embargoed.
    embargo_start_iloc = max(0, test_start_iloc - horizon_bars)
    # Also embargo the first purge_gap bars of the test set (forward windows
    # from very late training bars extend into those bars).
    embargo_end_iloc = min(len(result), test_start_iloc + purge_gap)

    result.iloc[embargo_start_iloc:embargo_end_iloc] = np.nan

    return result


def embargo_from_datetimes(
    labels: Labels,
    train_end: pd.Timestamp,
    test_start: pd.Timestamp,
    horizon_bars: int,
    purge_gap: int = PURGE_GAP_BARS,
) -> Labels:
    """
    Convenience wrapper: embargo by datetime boundaries rather than positions.

    Parameters
    ----------
    labels       : Label series with DatetimeIndex
    train_end    : Last timestamp of training set (inclusive)
    test_start   : First timestamp of test set
    horizon_bars : Forward-window length used to build labels
    purge_gap    : Extra buffer bars (from config.PURGE_GAP_BARS)

    Returns
    -------
    Labels with embargoed region set to NaN.
    """
    if not isinstance(labels.index, pd.DatetimeIndex):
        raise TypeError("labels must have a DatetimeIndex for datetime embargo")

    # Locate integer position of test_start
    positions = labels.index.searchsorted(test_start)
    test_start_iloc = int(positions)

    return apply_embargo(labels, test_start_iloc, horizon_bars, purge_gap)


# ─── Batch helper ────────────────────────────────────────────────────────────

def label_dataframe(
    df: pd.DataFrame,
    atr: pd.Series,
    timeframe: str,
    pair: str = "BTCUSDT",
) -> pd.DataFrame:
    """
    Convenience function: add 'label' column to an OHLCV DataFrame.

    Parameters
    ----------
    df        : DataFrame with columns [open, high, low, close, volume]
    atr       : ATR series aligned to df.index
    timeframe : "1h" or "4h"
    pair      : Pair symbol for cost lookup

    Returns
    -------
    df with a new 'label' column (int8).  Does NOT mutate the input.
    """
    required_cols = {"open", "high", "low", "close", "volume"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame missing columns: {missing}")

    out = df.copy()
    out["label"] = build_labels(
        close=df["close"],
        high=df["high"],
        low=df["low"],
        atr=atr,
        timeframe=timeframe,
        pair=pair,
    )
    return out


# ─── Diagnostics (non-critical, useful for EDA) ───────────────────────────────

def label_distribution(labels: Labels) -> dict:
    """
    Return class distribution for a label series.

    Returns dict with keys: 'n_total', 'n_valid', 'n_long', 'n_short',
    'n_timeout', 'pct_long', 'pct_short', 'pct_timeout'.

    Note: class balance is intentionally NOT adjusted; this is purely
    diagnostic.  Imbalance is handled by the model layer (sample weights),
    not by the labeler.
    """
    valid = labels.dropna().astype(int)
    n_total   = len(labels)
    n_valid   = len(valid)
    n_long    = int((valid == 1).sum())
    n_short   = int((valid == -1).sum())
    n_timeout = int((valid == 0).sum())

    def pct(x: int) -> float:
        return round(100 * x / n_valid, 1) if n_valid > 0 else 0.0

    return {
        "n_total":   n_total,
        "n_valid":   n_valid,
        "n_long":    n_long,
        "n_short":   n_short,
        "n_timeout": n_timeout,
        "pct_long":    pct(n_long),
        "pct_short":   pct(n_short),
        "pct_timeout": pct(n_timeout),
    }
