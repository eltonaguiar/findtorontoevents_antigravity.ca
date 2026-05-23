#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Universal Data Validator
==========================================
Validates signals, OHLCV data, and FRED data before they hit scoring/gates.
Part of Phase 3 remediation — see FOREX_COMMODITIES_BONDS.MD.

Usage:
    from alpha_engine.data_validator import validate_signal, validate_ohlcv, validate_fred_data

    result = validate_signal(pick)
    if not result.valid:
        logger.warning(f"Signal validation failed: {result.errors}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Direction normalization map
DIRECTION_NORMALIZE = {
    "BUY": "LONG",
    "SELL": "SHORT",
    "LONG": "LONG",
    "SHORT": "SHORT",
}

VALID_DIRECTIONS = {"LONG", "SHORT"}
VALID_ASSET_CLASSES = {"CRYPTO", "FOREX", "COMMODITY", "FUTURES", "ETF", "BOND", "EQUITY", "STOCK"}


@dataclass
class ValidationResult:
    """Result of a validation check."""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    normalized: bool = False  # True if we modified the input


def validate_signal(signal: dict) -> ValidationResult:
    """Validate a trading signal has all required fields and sane values.

    Normalizes direction (BUY->LONG, SELL->SHORT) in-place.
    Checks price sanity, required fields, and asset class.

    Args:
        signal: Pick dict with at minimum: symbol, direction, entry_price,
                stop_loss, take_profit, strategy

    Returns:
        ValidationResult with errors/warnings. signal dict may be modified in-place.
    """
    errors = []
    warnings = []
    normalized = False

    # Required fields
    required = ["symbol", "direction", "entry_price", "stop_loss", "take_profit", "strategy"]
    for field_name in required:
        val = signal.get(field_name)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"Missing required field: {field_name}")

    if errors:
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    # Direction normalization
    raw_dir = str(signal.get("direction", "")).upper().strip()
    if raw_dir in DIRECTION_NORMALIZE:
        normalized_dir = DIRECTION_NORMALIZE[raw_dir]
        if normalized_dir != raw_dir:
            signal["direction"] = normalized_dir
            normalized = True
    else:
        errors.append(f"Invalid direction: '{raw_dir}' (expected BUY/SELL/LONG/SHORT)")

    # Asset class normalization
    raw_ac = str(signal.get("asset_class") or signal.get("category") or "").upper().strip()
    if raw_ac == "STOCK":
        signal["asset_class"] = "EQUITY"
        normalized = True
        raw_ac = "EQUITY"
    elif raw_ac and raw_ac not in VALID_ASSET_CLASSES:
        warnings.append(f"Unknown asset class: '{raw_ac}'")

    # Price sanity
    entry = float(signal.get("entry_price", 0) or 0)
    tp = float(signal.get("take_profit", 0) or 0)
    sl = float(signal.get("stop_loss", 0) or 0)
    direction = signal.get("direction", "")

    if entry <= 0:
        errors.append(f"Invalid entry_price: {entry}")

    if tp > 0 and sl > 0 and entry > 0:
        if direction == "LONG":
            if sl >= entry:
                errors.append(f"LONG signal: stop_loss ({sl}) >= entry_price ({entry})")
            if tp <= entry:
                errors.append(f"LONG signal: take_profit ({tp}) <= entry_price ({entry})")
        elif direction == "SHORT":
            if sl <= entry:
                errors.append(f"SHORT signal: stop_loss ({sl}) <= entry_price ({entry})")
            if tp >= entry:
                errors.append(f"SHORT signal: take_profit ({tp}) >= entry_price ({entry})")

        # R:R sanity check
        if abs(entry - sl) > 1e-12:
            rr = abs(tp - entry) / abs(entry - sl)
            if rr < 0.5:
                warnings.append(f"Very low R:R ratio: {rr:.2f}")
            elif rr > 10:
                warnings.append(f"Suspiciously high R:R ratio: {rr:.2f}")

    # Confidence sanity
    conf = float(signal.get("confidence", 0) or 0)
    if conf < 0 or conf > 1:
        warnings.append(f"Confidence out of [0,1] range: {conf}")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        normalized=normalized,
    )


def validate_ohlcv(
    df: pd.DataFrame,
    symbol: str,
    min_bars: int = 60,
    max_gap_ratio: float = 0.1,
) -> ValidationResult:
    """Validate OHLCV DataFrame for strategy consumption.

    Checks:
    - Minimum bar count
    - No future-dated bars
    - Positive prices
    - Gap detection (missing bars)
    - Volume presence

    Args:
        df: DataFrame with Open, High, Low, Close, Volume columns
        symbol: Symbol name for logging
        min_bars: Minimum required bars
        max_gap_ratio: Max ratio of gaps to total bars

    Returns:
        ValidationResult
    """
    errors = []
    warnings = []

    if df is None or df.empty:
        return ValidationResult(valid=False, errors=[f"{symbol}: Empty DataFrame"])

    if len(df) < min_bars:
        errors.append(f"{symbol}: Only {len(df)} bars (need {min_bars})")

    # Check for future-dated bars
    now = datetime.now(timezone.utc)
    if hasattr(df.index, 'max'):
        max_date = df.index.max()
        if hasattr(max_date, 'tzinfo') and max_date.tzinfo is None:
            max_date = max_date.tz_localize(timezone.utc)
        if max_date > now + timedelta(days=1):
            errors.append(f"{symbol}: Future-dated bars detected (max={max_date})")

    # Check for non-positive prices
    for col in ["Open", "High", "Low", "Close"]:
        if col in df.columns:
            non_positive = (df[col] <= 0).sum()
            if non_positive > 0:
                errors.append(f"{symbol}: {non_positive} non-positive {col} values")

    # Check for NaN in Close
    if "Close" in df.columns:
        nan_count = df["Close"].isna().sum()
        if nan_count > 0:
            ratio = nan_count / len(df)
            if ratio > 0.2:
                errors.append(f"{symbol}: {nan_count} NaN Close values ({ratio:.1%})")
            else:
                warnings.append(f"{symbol}: {nan_count} NaN Close values ({ratio:.1%})")

    # Gap detection (daily data: >3 day gap = likely missing bar)
    if len(df) > 1 and hasattr(df.index, 'to_series'):
        diffs = df.index.to_series().diff().dropna()
        if hasattr(diffs, 'dt'):
            large_gaps = (diffs.dt.days > 5).sum()
            if large_gaps > 0:
                gap_ratio = large_gaps / len(df)
                if gap_ratio > max_gap_ratio:
                    warnings.append(f"{symbol}: {large_gaps} large gaps (>{max_gap_ratio:.1%} of bars)")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_fred_data(
    series_id: str,
    data: list[dict],
    max_age_hours: float = 48,
) -> ValidationResult:
    """Validate FRED data freshness and completeness.

    Args:
        series_id: FRED series code (e.g., "DGS10")
        data: List of {"date": "YYYY-MM-DD", "value": float} dicts
        max_age_hours: Max acceptable data age

    Returns:
        ValidationResult
    """
    errors = []
    warnings = []

    if not data:
        return ValidationResult(valid=False, errors=[f"FRED {series_id}: No data"])

    # Check freshness
    try:
        latest_date = max(datetime.strptime(row["date"], "%Y-%m-%d") for row in data)
        age = datetime.utcnow() - latest_date
        if age > timedelta(hours=max_age_hours):
            if age > timedelta(days=7):
                errors.append(f"FRED {series_id}: Data is {age.days} days old (latest={latest_date.date()})")
            else:
                warnings.append(f"FRED {series_id}: Data is {age.total_seconds()/3600:.1f}h old (latest={latest_date.date()})")
    except (ValueError, KeyError) as e:
        errors.append(f"FRED {series_id}: Date parsing error — {e}")

    # Check for too many missing values
    values = [row.get("value") for row in data]
    none_count = sum(1 for v in values if v is None)
    if none_count > len(values) * 0.2:
        warnings.append(f"FRED {series_id}: {none_count}/{len(values)} missing values")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def normalize_all_directions(picks: list[dict]) -> int:
    """Normalize directions in a batch of picks. Returns count of changes."""
    changes = 0
    for pick in picks:
        result = validate_signal(pick)
        if result.normalized:
            changes += 1
    return changes


# ── A1.2: Ingestion-time outlier detection ────────────────────────────────

def check_return_outliers(
    df: pd.DataFrame,
    threshold: float = 5.0,
    return_col: str = "Close",
    flag_col: str = "outlier_flag",
) -> ValidationResult:
    """Detect extreme return outliers in OHLCV data using z-score gating.

    Computes 1-period log returns on *return_col*, then flags any bar whose
    |z-score| exceeds *threshold* (default 5.0 sigma).  A z-score this large
    is economically implausible for most assets on a single bar and usually
    indicates a data error, bad split-adjustment, or bad feed.

    The check is ADDITIVE — it does NOT modify the DataFrame.  Callers decide
    what to do with flagged rows (drop, clip, or quarantine).

    Args:
        df:           DataFrame that must contain *return_col*.  A DatetimeIndex
                      is assumed but not required.
        threshold:    |z-score| above which a bar is flagged.  Default 5.0.
        return_col:   Column used to compute returns.  Default "Close".
        flag_col:     Unused in output — documents the intended downstream
                      column name callers should add when writing flags back.

    Returns:
        ValidationResult where:
          - valid=True  iff no flagged bars exist.
          - errors list contains one entry per flagged bar:
              "Outlier at <index>: z=<z> (return=<ret>)"
          - warnings list is populated when fewer than 10 bars exist
            (z-score unreliable on micro-samples).

    Example::

        result = check_return_outliers(ohlcv_df)
        if not result.valid:
            logger.warning("Return outliers found: %s", result.errors)
    """
    errors: list[str] = []
    warnings: list[str] = []

    if df is None or df.empty:
        return ValidationResult(valid=False, errors=["check_return_outliers: empty DataFrame"])

    if return_col not in df.columns:
        return ValidationResult(
            valid=False,
            errors=[f"check_return_outliers: column '{return_col}' not found in DataFrame"],
        )

    series = df[return_col].dropna()

    if len(series) < 2:
        return ValidationResult(
            valid=True,
            warnings=["check_return_outliers: fewer than 2 non-null bars — skipping z-score check"],
        )

    if len(series) < 10:
        warnings.append(
            f"check_return_outliers: only {len(series)} bars — z-score may be unreliable"
        )

    log_returns = np.log(series / series.shift(1)).dropna()

    if log_returns.empty:
        return ValidationResult(valid=True, warnings=warnings)

    mean = log_returns.mean()
    std = log_returns.std(ddof=1)

    if std == 0 or np.isnan(std):
        return ValidationResult(
            valid=True,
            warnings=warnings + ["check_return_outliers: zero std — constant price series"],
        )

    z_scores = (log_returns - mean) / std
    flagged = z_scores[np.abs(z_scores) > threshold]

    for idx, z in flagged.items():
        ret = log_returns.loc[idx]
        errors.append(
            f"Outlier at {idx}: z={z:.2f} (log_return={ret:.6f})"
        )

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
