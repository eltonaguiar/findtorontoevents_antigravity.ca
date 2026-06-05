#!/usr/bin/env python3
"""
refresh_stock_ohlcv.py — Populate ejaguiar1_stocks.stock_ohlcv with 1h yfinance data.

Queries at_raw_picks for the non-crypto symbol universe (EQUITY, ETF, FOREX,
FUTURES, COMMODITY, BOND, etc.), fetches 60 days of 1h bars via yfinance, and
bulk-upserts into MySQL.

Usage:
    python3 tools/refresh_stock_ohlcv.py --dry-run   # preview only
    python3 tools/refresh_stock_ohlcv.py --execute   # write to DB
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import pymysql

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.db_env import get_stocks_creds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

TIMEFRAME = "1h"
PERIOD = "60d"
BATCH_SIZE = 10
RATE_LIMIT_SLEEP = 1.0  # seconds between batch calls
SOURCE = "yahoo"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `stock_ohlcv` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `symbol` varchar(20) NOT NULL,
  `timeframe` varchar(10) NOT NULL,
  `timestamp` bigint NOT NULL,
  `open` decimal(12,4) NOT NULL,
  `high` decimal(12,4) NOT NULL,
  `low` decimal(12,4) NOT NULL,
  `close` decimal(12,4) NOT NULL,
  `volume` bigint NOT NULL,
  `source` varchar(50) DEFAULT 'yahoo',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ohlcv` (`symbol`,`timeframe`,`timestamp`),
  KEY `idx_symbol_time` (`symbol`,`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
"""


def get_db_conn():
    """Open a pymysql connection to ejaguiar1_stocks."""
    creds = get_stocks_creds(raise_on_missing=True)
    return pymysql.connect(**creds)


def normalize_yf_symbol(raw: str) -> Optional[str]:
    """
    Light normalization for yfinance symbols.
    Preserves yfinance suffixes like =X, =F, -USD, etc.
    """
    if not raw:
        return None
    s = raw.strip().upper()
    # Remove internal spaces
    s = s.replace(" ", "")
    return s


def get_stock_symbols(conn) -> List[str]:
    """Pull distinct non-crypto / non-memecoin / non-sports symbols from at_raw_picks."""
    sql = """
        SELECT DISTINCT symbol
        FROM at_raw_picks
        WHERE asset_class NOT IN ('CRYPTO','MEMECOIN','SPORTS','UNKNOWN')
          AND symbol IS NOT NULL
          AND symbol != ''
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return sorted({normalize_yf_symbol(r[0]) for r in rows if r[0] and normalize_yf_symbol(r[0])})


def _ms_timestamp(dt) -> int:
    """Convert a pandas Timestamp to Unix milliseconds."""
    if pd.isna(dt):
        return 0
    # Ensure UTC
    if hasattr(dt, "tz_convert"):
        dt = dt.tz_convert("UTC")
    elif hasattr(dt, "tz_localize") and dt.tzinfo is None:
        dt = dt.tz_localize("UTC")
    return int(dt.timestamp() * 1000)


def _to_int_volume(v) -> int:
    """Safely coerce volume to int."""
    if pd.isna(v):
        return 0
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return 0


def df_to_rows(symbol: str, df: pd.DataFrame) -> List[Tuple]:
    """Convert a single-symbol yfinance DataFrame into DB row tuples."""
    rows = []
    if df is None or df.empty:
        return rows
    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    # Standardize column names
    col_map = {c.lower(): c for c in df.columns}
    if "close" not in col_map:
        return rows
    for idx, row in df.iterrows():
        try:
            ts = _ms_timestamp(idx)
            open_p = float(row[col_map.get("open", "Open")])
            high_p = float(row[col_map.get("high", "High")])
            low_p = float(row[col_map.get("low", "Low")])
            close_p = float(row[col_map.get("close", "Close")])
            vol = _to_int_volume(row.get(col_map.get("volume", "Volume"), 0))
            rows.append((symbol, TIMEFRAME, ts, open_p, high_p, low_p, close_p, vol, SOURCE))
        except (KeyError, ValueError, TypeError):
            continue
    return rows


def fetch_yf_single(symbol: str, period: str = PERIOD, interval: str = TIMEFRAME) -> Optional[pd.DataFrame]:
    """Fetch one symbol via yfinance.download with error suppression."""
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance is not installed: pip install yfinance")
        return None
    try:
        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            threads=False,
            auto_adjust=False,
        )
        if df is None or df.empty:
            return None
        return df
    except Exception as exc:
        logger.debug("yfinance single fetch failed for %s: %s", symbol, exc)
        return None


def fetch_yf_batch(symbols: List[str], period: str = PERIOD, interval: str = TIMEFRAME) -> Dict[str, pd.DataFrame]:
    """
    Fetch a batch of symbols via yfinance.download(group_by='ticker').
    Returns a dict mapping symbol -> DataFrame.
    """
    result: Dict[str, pd.DataFrame] = {}
    if not symbols:
        return result
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance is not installed: pip install yfinance")
        return result

    tickers_str = " ".join(symbols)
    try:
        df = yf.download(
            tickers_str,
            period=period,
            interval=interval,
            group_by="ticker",
            progress=False,
            threads=False,
            auto_adjust=False,
        )
    except Exception as exc:
        logger.warning("yfinance batch failed for %s: %s", tickers_str, exc)
        return result

    if df is None or df.empty:
        return result

    # If single ticker, group_by="ticker" still returns flat columns with a MultiIndex
    # If multi ticker, top level of columns is the symbol
    if isinstance(df.columns, pd.MultiIndex):
        top_level = df.columns.get_level_values(0).unique()
        for sym in top_level:
            sub = df[sym].dropna(how="all")
            if not sub.empty and len(sub) > 1:
                result[sym] = sub
    else:
        # Single ticker fallback
        if not df.empty and len(df) > 1:
            result[symbols[0]] = df
    return result


def bulk_upsert(conn, rows: List[Tuple], dry_run: bool = True) -> int:
    """Bulk INSERT ... ON DUPLICATE KEY UPDATE. Returns affected row count."""
    if not rows:
        return 0
    sql = """
        INSERT INTO stock_ohlcv
          (symbol, timeframe, timestamp, open, high, low, close, volume, source)
        VALUES
          (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          open=VALUES(open),
          high=VALUES(high),
          low=VALUES(low),
          close=VALUES(close),
          volume=VALUES(volume),
          source=VALUES(source)
    """
    if dry_run:
        logger.info("[DRY-RUN] Would upsert %d rows", len(rows))
        return len(rows)
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
        conn.commit()
        return cur.rowcount


def create_table_if_missing(conn) -> None:
    """Create stock_ohlcv if it does not yet exist."""
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLE_SQL)
        conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh stock_ohlcv from yfinance 1h data")
    parser.add_argument("--dry-run", action="store_true", help="Preview only; do not write")
    parser.add_argument("--execute", action="store_true", help="Actually write to DB")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Symbols per yfinance batch")
    parser.add_argument("--period", default=PERIOD, help="yfinance period (e.g., 60d, 30d)")
    args = parser.parse_args()

    dry_run = not args.execute
    if args.dry_run:
        dry_run = True

    logger.info("Starting refresh_stock_ohlcv | dry_run=%s | period=%s | batch_size=%s", dry_run, args.period, args.batch_size)

    conn = get_db_conn()
    create_table_if_missing(conn)

    symbols = get_stock_symbols(conn)
    logger.info("Found %d distinct non-crypto symbols in at_raw_picks", len(symbols))

    total_rows_upserted = 0
    success_symbols = 0
    fail_symbols = 0

    # Process in batches
    for i in range(0, len(symbols), args.batch_size):
        batch = symbols[i : i + args.batch_size]
        logger.info("Batch %d/%d: %s", i // args.batch_size + 1, (len(symbols) - 1) // args.batch_size + 1, batch)

        batch_results = fetch_yf_batch(batch, period=args.period)
        fetched_in_batch = set(batch_results.keys())
        missing = [s for s in batch if s not in fetched_in_batch]

        # Retry missing symbols individually
        for sym in missing:
            df = fetch_yf_single(sym, period=args.period)
            if df is not None and not df.empty:
                batch_results[sym] = df
            else:
                logger.warning("No data for %s (delisted or bad ticker)", sym)

        for sym, df in batch_results.items():
            rows = df_to_rows(sym, df)
            if not rows:
                logger.warning("No parseable rows for %s", sym)
                fail_symbols += 1
                continue
            affected = bulk_upsert(conn, rows, dry_run=dry_run)
            logger.info("%s -> %d bars | upsert affected %d rows", sym, len(rows), affected)
            total_rows_upserted += affected
            success_symbols += 1

        # Count any symbols that are still missing after individual retry as failures
        still_missing = [s for s in batch if s not in batch_results]
        for sym in still_missing:
            fail_symbols += 1

        time.sleep(RATE_LIMIT_SLEEP)

    logger.info(
        "Done | symbols: %d success, %d failed | total rows upserted: %d",
        success_symbols, fail_symbols, total_rows_upserted,
    )

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
