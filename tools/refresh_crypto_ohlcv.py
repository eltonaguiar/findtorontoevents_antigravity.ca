#!/usr/bin/env python3
"""
refresh_crypto_ohlcv.py — Populate ejaguiar1_stocks.crypto_ohlcv with 1h Binance klines.

Queries at_raw_picks for the active CRYPTO + MEMECOIN symbol universe, normalizes
tickers to Binance spot format, fetches 720 bars (30 days) of 1h klines from the
public Binance API, and bulk-upserts into MySQL.

Usage:
    python3 tools/refresh_crypto_ohlcv.py --dry-run   # preview only
    python3 tools/refresh_crypto_ohlcv.py --execute   # write to DB
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

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

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
DEFAULT_LIMIT = 720  # ~30 days of 1h bars
TIMEFRAME = "1h"
RATE_LIMIT_SLEEP = 0.25  # seconds between requests

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `crypto_ohlcv` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `symbol` varchar(20) NOT NULL,
  `timeframe` varchar(10) NOT NULL,
  `timestamp` bigint NOT NULL,
  `open` decimal(18,8) NOT NULL,
  `high` decimal(18,8) NOT NULL,
  `low` decimal(18,8) NOT NULL,
  `close` decimal(18,8) NOT NULL,
  `volume` decimal(24,8) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ohlcv` (`symbol`,`timeframe`,`timestamp`),
  KEY `idx_symbol_time` (`symbol`,`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
"""


def get_db_conn():
    """Open a pymysql connection to ejaguiar1_stocks."""
    creds = get_stocks_creds(raise_on_missing=True)
    return pymysql.connect(**creds)


def normalize_binance_symbol(raw: str) -> Optional[str]:
    """
    Normalize a raw symbol from at_raw_picks into a Binance spot symbol.
    Examples:
        BTCUSDT   -> BTCUSDT
        BTC       -> BTCUSDT
        BTC-USDT  -> BTCUSDT
        BTC/USD   -> BTCUSDT
        btcusdt   -> BTCUSDT
    Returns None if we cannot produce a reasonable guess.
    """
    if not raw:
        return None
    s = raw.strip().upper()
    # Already looks like a Binance pair (ends with common quote assets)
    if any(s.endswith(q) for q in ("USDT", "BUSD", "BTC", "ETH", "USDC", "FDUSD", "TUSD")):
        return s
    # Strip common separators and suffixes
    for sep in ("-", "/", "_", ":"):
        s = s.replace(sep, "")
    # If after stripping it ends with a quote asset, return it
    if any(s.endswith(q) for q in ("USDT", "BUSD", "BTC", "ETH", "USDC", "FDUSD", "TUSD")):
        return s
    # Append USDT as the default quote asset for crypto
    return s + "USDT"


def fetch_binance_klines(symbol: str, interval: str = TIMEFRAME, limit: int = DEFAULT_LIMIT) -> List[list]:
    """Fetch klines from Binance public API. Returns raw JSON list or empty list on failure."""
    url = f"{BINANCE_KLINES_URL}?symbol={symbol}&interval={interval}&limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "refresh_crypto_ohlcv/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if isinstance(data, list):
            return data
        # Binance error envelope
        if isinstance(data, dict) and data.get("code"):
            logger.warning("Binance API error for %s: %s %s", symbol, data.get("code"), data.get("msg"))
            return []
    except urllib.error.HTTPError as exc:
        logger.warning("Binance HTTP error for %s: %s", symbol, exc.code)
    except Exception as exc:
        logger.warning("Binance fetch failed for %s: %s", symbol, exc)
    return []


def klines_to_rows(symbol: str, klines: List[list]) -> List[Tuple]:
    """Convert Binance klines list into DB row tuples."""
    rows = []
    for k in klines:
        try:
            open_time = int(k[0])
            open_p = float(k[1])
            high_p = float(k[2])
            low_p = float(k[3])
            close_p = float(k[4])
            volume = float(k[5])
            rows.append((symbol, TIMEFRAME, open_time, open_p, high_p, low_p, close_p, volume))
        except (IndexError, ValueError, TypeError):
            continue
    return rows


def get_crypto_symbols(conn) -> List[str]:
    """Pull distinct CRYPTO + MEMECOIN symbols from at_raw_picks."""
    sql = """
        SELECT DISTINCT symbol
        FROM at_raw_picks
        WHERE asset_class IN ('CRYPTO','MEMECOIN')
          AND symbol IS NOT NULL
          AND symbol != ''
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return sorted({r[0] for r in rows if r[0]})


def bulk_upsert(conn, rows: List[Tuple], dry_run: bool = True) -> int:
    """Bulk INSERT ... ON DUPLICATE KEY UPDATE. Returns affected row count."""
    if not rows:
        return 0
    sql = """
        INSERT INTO crypto_ohlcv
          (symbol, timeframe, timestamp, open, high, low, close, volume)
        VALUES
          (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          open=VALUES(open),
          high=VALUES(high),
          low=VALUES(low),
          close=VALUES(close),
          volume=VALUES(volume)
    """
    if dry_run:
        logger.info("[DRY-RUN] Would upsert %d rows", len(rows))
        return len(rows)
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
        conn.commit()
        return cur.rowcount


def create_table_if_missing(conn) -> None:
    """Create crypto_ohlcv if it does not yet exist."""
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLE_SQL)
        conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh crypto_ohlcv from Binance 1h klines")
    parser.add_argument("--dry-run", action="store_true", help="Preview only; do not write")
    parser.add_argument("--execute", action="store_true", help="Actually write to DB")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Klines limit per symbol")
    args = parser.parse_args()

    dry_run = not args.execute
    if args.dry_run:
        dry_run = True

    logger.info("Starting refresh_crypto_ohlcv | dry_run=%s | limit=%s", dry_run, args.limit)

    conn = get_db_conn()
    create_table_if_missing(conn)

    raw_symbols = get_crypto_symbols(conn)
    logger.info("Found %d distinct CRYPTO/MEMECOIN symbols in at_raw_picks", len(raw_symbols))

    total_rows_upserted = 0
    success_symbols = 0
    fail_symbols = 0
    skipped_no_normalize = 0

    for raw_sym in raw_symbols:
        binance_sym = normalize_binance_symbol(raw_sym)
        if not binance_sym:
            logger.warning("Skipping %s — could not normalize to Binance symbol", raw_sym)
            skipped_no_normalize += 1
            continue

        klines = fetch_binance_klines(binance_sym, limit=args.limit)
        if not klines:
            logger.warning("No data returned for %s (Binance: %s)", raw_sym, binance_sym)
            fail_symbols += 1
            continue

        rows = klines_to_rows(binance_sym, klines)
        if not rows:
            logger.warning("No parseable rows for %s (Binance: %s)", raw_sym, binance_sym)
            fail_symbols += 1
            continue

        affected = bulk_upsert(conn, rows, dry_run=dry_run)
        logger.info(
            "%s (Binance: %s) -> %d klines | upsert affected %d rows",
            raw_sym, binance_sym, len(rows), affected,
        )
        total_rows_upserted += affected
        success_symbols += 1

        time.sleep(RATE_LIMIT_SLEEP)

    logger.info(
        "Done | symbols: %d success, %d failed, %d skipped | total rows upserted: %d",
        success_symbols, fail_symbols, skipped_no_normalize, total_rows_upserted,
    )

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
