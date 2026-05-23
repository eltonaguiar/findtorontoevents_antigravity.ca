"""
SQLite connection manager for the audit trail.

Designed for easy swap to MySQL/PostgreSQL later:
- All DB-specific logic lives in this file
- Callers use get_connection() and never import sqlite3 directly
"""

import pathlib
import sqlite3
import threading

DB_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "audit_trail.db"
SCHEMA_PATH = pathlib.Path(__file__).resolve().parent / "schema.sql"

_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """Get a thread-local SQLite connection. Creates DB + schema on first call."""
    if not hasattr(_local, "conn") or _local.conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        # Initialize schema if needed
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)

        # Migrate: add enrichment columns added in 2025 if they don't exist yet
        _migrate_add_columns(conn)

        _local.conn = conn
    return _local.conn


def _migrate_add_columns(conn: sqlite3.Connection) -> None:
    """Idempotently add new columns to raw_picks for enrichment data."""
    new_cols = [
        ("enrichment_grade",        "TEXT"),
        ("enrichment_alignment",    "INTEGER"),
        ("enrichment_contrary",     "INTEGER"),
        ("enrichment_rsi",          "REAL"),
        ("enrichment_fear_greed",   "INTEGER"),
        ("enrichment_funding_rate", "REAL"),
        ("enrichment_nvt_ratio",    "REAL"),
        ("enrichment_nvt_signal",   "TEXT"),
        ("enrichment_weekly_mom",   "TEXT"),
        ("enrichment_pct_7d",       "REAL"),
        ("enrichment_btc_mempool",  "TEXT"),
        ("enrichment_btc_fee_sat",  "INTEGER"),
        ("enrichment_defi_cex_sig", "TEXT"),
        ("enrichment_defi_spread",  "REAL"),
        ("enrichment_dex_liq",      "TEXT"),
        ("enrichment_active_addrs", "INTEGER"),
        ("enrichment_data",         "TEXT"),
    ]
    existing = {row[1] for row in conn.execute("PRAGMA table_info(raw_picks)")}
    for col_name, col_type in new_cols:
        if col_name not in existing:
            conn.execute(f"ALTER TABLE raw_picks ADD COLUMN {col_name} {col_type}")
    conn.commit()


def close():
    """Close the thread-local connection."""
    if hasattr(_local, "conn") and _local.conn is not None:
        _local.conn.close()
        _local.conn = None
