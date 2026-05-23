"""Sync paper trading positions to MySQL at_signal_outcomes table.

This allows the Hoffman tracker and other MySQL-based analytics to access
paper trading data for backtesting, historicals, and further analysis.
"""

import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from alpha_engine.asset_class import normalize_asset_class

logger = logging.getLogger("paper_trading.mysql_sync")

PAPER_DB = Path(__file__).parent / "data" / "paper.db"

# MySQL config — same as strategy_health
MYSQL_HOST = os.environ.get("MYSQL_HOST") or "mysql.50webs.com"
MYSQL_USER = os.environ.get("MYSQL_USER") or "ejaguiar1_stocks"
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD") or "stocks"
MYSQL_DB = os.environ.get("MYSQL_DB") or "ejaguiar1_stocks"


def _source_system(strategy_name: str) -> str:
    """Map strategy name to source_system identifier.

    Uses the actual strategy display_name for proper audit trail naming.
    """
    try:
        from paper_trading.strategies import STRATEGY_METADATA
        meta = STRATEGY_METADATA.get(strategy_name)
        if meta:
            return meta["display_name"]
    except ImportError:
        pass
    return strategy_name.replace("_", " ").title()


def _map_status_to_outcome(status: str, pnl_pct: float) -> str:
    """Map paper trading status to at_signal_outcomes outcome."""
    if status == "ACTIVE":
        return "OPEN"
    if status == "TP_HIT":
        return "TP_HIT"
    if status == "SL_HIT":
        return "SL_HIT"
    if status == "EXPIRED":
        return "WIN" if pnl_pct and pnl_pct > 0 else "LOSS"
    return status


def _resolve_asset_class(position: dict) -> str:
    """Normalize asset class for MySQL writes from explicit fields or symbol."""
    return normalize_asset_class(position).upper()


def sync_to_mysql():
    """Read all positions from paper.db and upsert into MySQL at_signal_outcomes."""
    try:
        import pymysql
    except ImportError:
        logger.warning("pymysql not installed — skipping MySQL sync")
        return 0

    if not PAPER_DB.exists():
        logger.warning(f"Paper DB not found: {PAPER_DB}")
        return 0

    # Read from SQLite
    sqlite_conn = sqlite3.connect(str(PAPER_DB))
    sqlite_conn.row_factory = sqlite3.Row
    positions = sqlite_conn.execute("SELECT * FROM positions").fetchall()
    sqlite_conn.close()

    if not positions:
        logger.info("No positions in paper.db to sync")
        return 0

    # Connect to MySQL
    try:
        mysql_conn = pymysql.connect(
            host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD,
            database=MYSQL_DB, charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=15, read_timeout=30,
        )
    except Exception as e:
        logger.error(f"MySQL connection failed: {e}")
        return 0

    cur = mysql_conn.cursor()

    # Ensure table exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS at_signal_outcomes (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        symbol          VARCHAR(50)     NOT NULL,
        direction       VARCHAR(10)     DEFAULT 'LONG',
        entry_price     DECIMAL(18,8)   DEFAULT NULL,
        take_profit     DECIMAL(18,8)   DEFAULT NULL,
        stop_loss       DECIMAL(18,8)   DEFAULT NULL,
        exit_price      DECIMAL(18,8)   DEFAULT NULL,
        outcome         VARCHAR(20)     DEFAULT NULL,
        pnl_pct         DECIMAL(10,4)   DEFAULT NULL,
        source_system   VARCHAR(100)    NOT NULL,
        strategy        VARCHAR(100)    DEFAULT NULL,
        asset_class     VARCHAR(20)     DEFAULT 'CRYPTO',
        opened_at       DATETIME        DEFAULT NULL,
        closed_at       DATETIME        DEFAULT NULL,
        created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol     (symbol),
        INDEX idx_outcome    (outcome),
        INDEX idx_system     (source_system),
        INDEX idx_strategy   (strategy),
        UNIQUE INDEX idx_dedup (symbol, direction, source_system, opened_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    synced = 0
    for pos in positions:
        pos = dict(pos)
        strategy = pos.get("strategy", "")
        source = _source_system(strategy)
        outcome = _map_status_to_outcome(
            pos.get("status", ""), pos.get("pnl_pct")
        )
        asset_class = _resolve_asset_class(pos)

        # Parse dates
        opened_at = pos.get("entry_date")
        closed_at = pos.get("exit_date")

        try:
            cur.execute("""
                INSERT INTO at_signal_outcomes
                    (symbol, direction, entry_price, take_profit, stop_loss,
                     exit_price, outcome, pnl_pct, source_system, strategy,
                     asset_class, opened_at, closed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    exit_price = VALUES(exit_price),
                    outcome = VALUES(outcome),
                    pnl_pct = VALUES(pnl_pct),
                    closed_at = VALUES(closed_at)
            """, (
                pos.get("symbol"), pos.get("direction"),
                pos.get("entry_price"), pos.get("tp"), pos.get("sl"),
                pos.get("exit_price"), outcome, pos.get("pnl_pct"),
                source, strategy, asset_class,
                opened_at, closed_at,
            ))
            synced += 1
        except Exception as e:
            logger.debug(f"MySQL upsert failed for {pos.get('symbol')}: {e}")

    mysql_conn.commit()
    mysql_conn.close()

    logger.info(f"MySQL sync complete: {synced}/{len(positions)} positions synced")
    return synced
