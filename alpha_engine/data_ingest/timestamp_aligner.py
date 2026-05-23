"""
Alpha Engine -- Cross-Source Timestamp Aligner (A1.1)
======================================================
Normalises timestamps from heterogeneous data sources to a canonical
UTC DatetimeIndex with second precision.

Public API
----------
align_to_utc_second(df, source_name) -> pd.DataFrame
    Convert a single DataFrame's timestamps to UTC second-precision index.

align_all_sources(sources) -> dict[str, pd.DataFrame]
    Align multiple DataFrames and reindex to a common union timeline,
    forward-filling gaps up to 1 hour.

Notes
-----
- Timestamps lacking timezone info are assumed UTC and a WARNING is logged.
- The module is a pure ingest-layer utility; it never touches production pick
  paths directly. Callers in alpha_engine/smart_picks_engine.py or
  alpha_engine/production_scanner.py import and invoke it before merging
  multi-source OHLCV / macro frames.
"""

from __future__ import annotations

import logging
import warnings
from typing import Union

import pandas as pd

logger = logging.getLogger(__name__)

# Maximum gap that will be forward-filled when building the common timeline.
MAX_FORWARDFILL_SECONDS: int = 3_600  # 1 hour


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _coerce_to_datetime_index(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """Return *df* with a DatetimeIndex, raising ValueError if impossible."""
    if isinstance(df.index, pd.DatetimeIndex):
        return df

    # Try common column names
    for col in ("timestamp", "date", "datetime", "time", "Date", "Datetime"):
        if col in df.columns:
            df = df.set_index(col)
            logger.debug("[timestamp_aligner] %s: used column '%s' as index", source_name, col)
            return df

    raise ValueError(
        f"[timestamp_aligner] {source_name}: DataFrame has no DatetimeIndex and "
        "no recognised timestamp column ('timestamp', 'date', 'datetime', 'time')."
    )


def _detect_and_warn_tz_ambiguity(index: pd.DatetimeIndex, source_name: str) -> pd.DatetimeIndex:
    """If index has no timezone, emit a WARNING and assume UTC."""
    if index.tz is None:
        warnings.warn(
            f"[timestamp_aligner] {source_name}: timestamps have no timezone info — "
            "assuming UTC.  Pass tz-aware data to suppress this warning.",
            stacklevel=4,
        )
        logger.warning(
            "[timestamp_aligner] %s: tz-naive index; assuming UTC", source_name
        )
        return index.tz_localize("UTC")
    return index


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def align_to_utc_second(
    df: pd.DataFrame,
    source_name: str,
) -> pd.DataFrame:
    """Align a DataFrame's timestamps to UTC second precision.

    Parameters
    ----------
    df:
        Input DataFrame.  Must have either a DatetimeIndex or a column named
        'timestamp', 'date', 'datetime', or 'time'.
    source_name:
        Human-readable label used in log/warning messages (e.g. "binance",
        "coingecko").

    Returns
    -------
    pd.DataFrame
        Same data with a tz-aware UTC DatetimeIndex, floored to the second.
        The index name is set to ``"utc_timestamp"``.

    Raises
    ------
    ValueError
        If no usable timestamp column/index can be found.
    TypeError
        If the located column/index cannot be parsed as datetimes.
    """
    if df is None or df.empty:
        logger.warning("[timestamp_aligner] %s: received empty DataFrame — returning as-is", source_name)
        return df

    # Step 1: ensure we have a DatetimeIndex
    df = _coerce_to_datetime_index(df.copy(), source_name)

    # Step 2: parse index if it isn't already DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
            logger.debug("[timestamp_aligner] %s: parsed index as DatetimeIndex", source_name)
        except Exception as exc:
            raise TypeError(
                f"[timestamp_aligner] {source_name}: cannot convert index to datetime — {exc}"
            ) from exc

    # Step 3: detect and handle tz-naive
    df.index = _detect_and_warn_tz_ambiguity(df.index, source_name)

    # Step 4: convert to UTC
    if str(df.index.tz) != "UTC":
        df.index = df.index.tz_convert("UTC")
        logger.debug("[timestamp_aligner] %s: converted to UTC", source_name)

    # Step 5: floor to second precision
    df.index = df.index.floor("s")

    # Step 6: deduplicate — keep last occurrence for each second
    n_before = len(df)
    df = df[~df.index.duplicated(keep="last")]
    n_dupes = n_before - len(df)
    if n_dupes:
        logger.info(
            "[timestamp_aligner] %s: dropped %d duplicate timestamps after flooring to second",
            source_name, n_dupes,
        )

    # Step 7: sort ascending
    df.sort_index(inplace=True)

    df.index.name = "utc_timestamp"
    logger.info(
        "[timestamp_aligner] %s: aligned %d rows to UTC second precision (range: %s → %s)",
        source_name,
        len(df),
        df.index[0] if len(df) else "N/A",
        df.index[-1] if len(df) else "N/A",
    )
    return df


def align_all_sources(
    sources: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Align multiple DataFrames and reindex them to a common union timeline.

    Each DataFrame in *sources* is first passed through ``align_to_utc_second``.
    Then a union DatetimeIndex is built from all sources.  Each DataFrame is
    reindexed to this common timeline with forward-fill capped at
    ``MAX_FORWARDFILL_SECONDS`` seconds (default 1 hour).

    Parameters
    ----------
    sources:
        Mapping of source_name -> DataFrame (each with a timestamp index or
        column, as accepted by ``align_to_utc_second``).

    Returns
    -------
    dict[str, pd.DataFrame]
        Same keys as *sources*; each value has the common UTC DatetimeIndex.

    Notes
    -----
    - Sources with zero rows are kept in the output dict but their DataFrame
      will be all-NaN on the common timeline.
    - The common timeline is the *union* (outer join) of all individual
      timelines, which may be sparse.  Callers can further resample or
      dropna as appropriate.
    """
    if not sources:
        logger.warning("[timestamp_aligner] align_all_sources: received empty sources dict")
        return {}

    # Phase 1: align each source
    aligned: dict[str, pd.DataFrame] = {}
    for name, df in sources.items():
        try:
            aligned[name] = align_to_utc_second(df, name)
        except Exception as exc:
            logger.error("[timestamp_aligner] %s: alignment failed — %s", name, exc)
            aligned[name] = df  # keep original so caller can inspect

    # Phase 2: build union index
    all_indices = [
        adf.index for adf in aligned.values()
        if isinstance(adf.index, pd.DatetimeIndex) and len(adf) > 0
    ]
    if not all_indices:
        logger.warning("[timestamp_aligner] align_all_sources: no valid DatetimeIndex found in any source")
        return aligned

    union_index = all_indices[0]
    for idx in all_indices[1:]:
        union_index = union_index.union(idx)
    union_index = union_index.sort_values()

    logger.info(
        "[timestamp_aligner] Common timeline: %d timestamps (%s → %s)",
        len(union_index),
        union_index[0] if len(union_index) else "N/A",
        union_index[-1] if len(union_index) else "N/A",
    )

    # Phase 3: reindex each source, forward-fill gaps <= MAX_FORWARDFILL_SECONDS
    reindexed: dict[str, pd.DataFrame] = {}
    limit_periods = MAX_FORWARDFILL_SECONDS  # seconds; index is already at-second resolution

    for name, adf in aligned.items():
        if not isinstance(adf.index, pd.DatetimeIndex) or len(adf) == 0:
            # Can't reindex; fill with NaN frame
            reindexed[name] = pd.DataFrame(index=union_index, columns=adf.columns if hasattr(adf, 'columns') else [])
            logger.warning("[timestamp_aligner] %s: skipped reindex (empty or bad index)", name)
            continue

        try:
            reindexed_df = adf.reindex(union_index)
            # Forward-fill up to limit_periods rows (each row = 1 second on union index)
            reindexed_df = reindexed_df.ffill(limit=limit_periods)
            reindexed[name] = reindexed_df
            n_filled = reindexed_df.notna().all(axis=1).sum()
            logger.debug(
                "[timestamp_aligner] %s: reindexed to %d common timestamps (%d fully populated)",
                name, len(union_index), n_filled,
            )
        except Exception as exc:
            logger.error("[timestamp_aligner] %s: reindex failed — %s", name, exc)
            reindexed[name] = adf

    return reindexed
