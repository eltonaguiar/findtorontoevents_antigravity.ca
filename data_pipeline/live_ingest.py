"""
Live Parquet Ingestion Pipeline
=================================
Continuously fetches OHLCV data from Binance and appends to Parquet files.
Deduplicates on timestamp. Supports multiple timeframes.

Usage:
    python -m data_pipeline.live_ingest --pairs BTCUSDT ETHUSDT --intervals 1h 4h

Or from other modules:
    from data_pipeline.live_ingest import ingest_pair, ingest_all
"""

import os
import sys
import time
import logging
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

# Default storage location
PARQUET_DIR = Path(__file__).resolve().parent.parent / "data" / "parquet"

# Default pairs and intervals
DEFAULT_PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "LTCUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT", "SUIUSDT",
    "DOGEUSDT", "ARBUSDT", "INJUSDT", "FETUSDT",
]

DEFAULT_INTERVALS = ["1h", "4h"]


def _parquet_path(pair: str, interval: str, base_dir: Path = PARQUET_DIR) -> Path:
    """Get the Parquet file path for a pair/interval combination."""
    d = base_dir / pair.upper()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{interval}.parquet"


def ingest_pair(
    pair: str,
    interval: str = "1h",
    limit: int = 500,
    base_dir: Path = PARQUET_DIR,
) -> int:
    """
    Fetch latest OHLCV for a pair and append to Parquet, deduplicating.

    Returns: number of new bars added.
    """
    from ml_battleground.shared.data_fetcher import fetch_single

    df = fetch_single(pair, interval=interval, limit=limit)
    if df is None or len(df) < 1:
        logger.warning("No data fetched for %s %s", pair, interval)
        return 0

    # Reset index to get timestamp as a column
    if "timestamp" not in df.columns:
        df = df.reset_index()

    # Ensure timestamp is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    path = _parquet_path(pair, interval, base_dir)

    if path.exists():
        existing = pd.read_parquet(path)
        if "timestamp" in existing.columns:
            existing["timestamp"] = pd.to_datetime(existing["timestamp"], utc=True)

        # Merge and deduplicate
        combined = pd.concat([existing, df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["timestamp"], keep="last")
        combined = combined.sort_values("timestamp").reset_index(drop=True)
        new_bars = len(combined) - len(existing)
    else:
        combined = df.sort_values("timestamp").reset_index(drop=True)
        new_bars = len(combined)

    combined.to_parquet(path, compression="snappy", index=False)

    if new_bars > 0:
        logger.info(
            "Ingested %d new bars for %s %s (total: %d)",
            new_bars, pair, interval, len(combined),
        )

    return new_bars


def ingest_all(
    pairs: Optional[List[str]] = None,
    intervals: Optional[List[str]] = None,
    limit: int = 500,
    base_dir: Path = PARQUET_DIR,
) -> dict:
    """
    Ingest all pairs x intervals.

    Returns: dict of {pair: {interval: new_bars_count}}
    """
    pairs = pairs or DEFAULT_PAIRS
    intervals = intervals or DEFAULT_INTERVALS

    results = {}
    total_new = 0

    for pair in pairs:
        results[pair] = {}
        for interval in intervals:
            try:
                new_bars = ingest_pair(pair, interval, limit, base_dir)
                results[pair][interval] = new_bars
                total_new += new_bars
            except Exception as e:
                logger.error("Failed to ingest %s %s: %s", pair, interval, e)
                results[pair][interval] = -1
            time.sleep(0.15)  # rate limit

    logger.info(
        "Ingestion complete: %d new bars across %d pairs x %d intervals",
        total_new, len(pairs), len(intervals),
    )
    return results


def get_pair_data(
    pair: str,
    interval: str = "1h",
    last_n: Optional[int] = None,
    base_dir: Path = PARQUET_DIR,
) -> pd.DataFrame:
    """
    Read Parquet data for a pair/interval.

    Returns empty DataFrame if file doesn't exist.
    """
    path = _parquet_path(pair, interval, base_dir)
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    if last_n and len(df) > last_n:
        df = df.tail(last_n).reset_index(drop=True)
    return df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(description="Live Parquet Ingestion")
    parser.add_argument("--pairs", nargs="+", default=DEFAULT_PAIRS)
    parser.add_argument("--intervals", nargs="+", default=DEFAULT_INTERVALS)
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    results = ingest_all(args.pairs, args.intervals, args.limit)

    # Summary
    total = sum(
        v for pair_data in results.values()
        for v in pair_data.values() if v > 0
    )
    print(f"\nTotal new bars ingested: {total}")
