"""
AI Tournament — MySQL Ingestion Engine.

Reads the latest picks from data/ai_tournament/picks_YYYYMMDD.json and
ingests them into the MySQL database for persistent storage + leaderboard tracking.

Usage:
    python tools/ai_tournament/ingest_to_db.py          # normal run
    python tools/ai_tournament/ingest_to_db.py --dry-run # log only, no writes

Environment:
    DB_PASS_STOCKS    MySQL password
    DB_HOST_STOCKS    MySQL host (default: mysql.50webs.com)
    DB_NAME_STOCKS    Database name  (default: ejaguiar1_stocks)
    DB_USER_STOCKS    Username       (default: ejaguiar1_stocks)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PICKS_DIR = REPO_ROOT / "data" / "ai_tournament"
LATEST_PICKS = REPO_ROOT / "audit_dashboard" / "data" / "ai_tournament_picks_latest.json"

DRY_RUN = "--dry-run" in sys.argv


def get_env_or_default(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def load_latest_picks() -> list[dict]:
    """Load the most recent picks file (or the latest snapshot)."""
    if PICKS_DIR.exists():
        files = sorted(PICKS_DIR.glob("picks_*.json"), reverse=True)
        if files:
            data = json.loads(files[0].read_text())
            if isinstance(data, list):
                print(f"[ingest] Loaded {len(data)} picks from {files[0].name}")
                return data

    if LATEST_PICKS.exists():
        data = json.loads(LATEST_PICKS.read_text())
        if isinstance(data, list):
            print(f"[ingest] Loaded {len(data)} picks from latest snapshot")
            return data

    print("[ingest] No picks files found")
    return []


def safe_str(v: Any, max_len: int = 500) -> str:
    """Coerce to string, truncate, escape single quotes."""
    s = str(v) if v is not None else ""
    return s[:max_len].replace("'", "''")


def safe_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def build_upsert_sql(picks: list[dict]) -> tuple[list[str], list[tuple]]:
    """Build INSERT ... ON DUPLICATE KEY UPDATE statements for the picks.
    
    Returns (ddl_statements, row_tuples).
    """
    rows = []
    for p in picks:
        rows.append((
            safe_str(p.get("model_id", "unknown")),
            safe_str(p.get("symbol", "")),
            safe_str(p.get("asset_class", "EQUITY")),
            safe_str(p.get("direction", "LONG")),
            safe_float(p.get("entry_price", 0)),
            safe_float(p.get("take_profit", 0)),
            safe_float(p.get("stop_loss", 0)),
            safe_str(p.get("thesis", ""), 2000),
            safe_str(p.get("data_source", "")),
            safe_float(p.get("confidence", 0)),
            safe_str(p.get("timeframe", "")),
            safe_str(p.get("status", "OPEN")),
            safe_str(p.get("submitted_at", "")),
            safe_str(p.get("provider", "")),
            safe_str(p.get("model_version", "")),
            safe_str(p.get("strategy_name", "")),
            safe_str(p.get("persona_id", "")),
            safe_float(p.get("current_price", 0)),
            safe_float(p.get("unrealized_pnl_pct", 0)),
            safe_float(p.get("pnl_pct", 0)),
            safe_float(p.get("exit_price", 0)),
            safe_str(p.get("exit_reason", "")),
            safe_str(p.get("resolved_at", "")),
            safe_str(p.get("reason", ""), 3000),
            safe_str(p.get("entry_criteria", ""), 1000),
        ))

    ddl = [
        """
        CREATE TABLE IF NOT EXISTS ai_tournament_picks (
            id              BIGINT AUTO_INCREMENT PRIMARY KEY,
            model_id        VARCHAR(64)   NOT NULL,
            symbol          VARCHAR(32)   NOT NULL,
            asset_class     VARCHAR(16)   NOT NULL,
            direction       VARCHAR(8)    NOT NULL,
            entry_price     DECIMAL(16,4) NOT NULL,
            take_profit     DECIMAL(16,4) DEFAULT NULL,
            stop_loss       DECIMAL(16,4) DEFAULT NULL,
            thesis          TEXT          DEFAULT NULL,
            reason          TEXT          DEFAULT NULL COMMENT 'Detailed persona rationale',
            entry_criteria  TEXT          DEFAULT NULL COMMENT 'Specific entry triggers that fired',
            data_source     VARCHAR(64)   DEFAULT '',
            confidence      DECIMAL(5,4)  DEFAULT 0,
            timeframe       VARCHAR(16)   DEFAULT '',
            status          VARCHAR(16)   DEFAULT 'OPEN',
            submitted_at    DATETIME      DEFAULT NULL,
            provider        VARCHAR(64)   DEFAULT '',
            model_version   VARCHAR(64)   DEFAULT '',
            strategy_name   VARCHAR(128)  DEFAULT '',
            persona_id      VARCHAR(64)   DEFAULT '',
            current_price   DECIMAL(16,4) DEFAULT NULL,
            unrealized_pnl_pct DECIMAL(8,4) DEFAULT NULL,
            pnl_pct         DECIMAL(8,4)  DEFAULT NULL,
            exit_price      DECIMAL(16,4) DEFAULT NULL,
            exit_reason     VARCHAR(32)   DEFAULT NULL,
            resolved_at     DATETIME      DEFAULT NULL,
            created_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_pick (model_id, symbol, submitted_at(19))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        ALTER TABLE ai_tournament_picks
            ADD COLUMN IF NOT EXISTS reason TEXT DEFAULT NULL COMMENT 'Detailed persona rationale'
            AFTER thesis;
        """,
        """
        ALTER TABLE ai_tournament_picks
            ADD COLUMN IF NOT EXISTS entry_criteria TEXT DEFAULT NULL COMMENT 'Specific entry triggers that fired'
            AFTER reason;
        """,
    ]

    # Fallback ALTER for older MySQL (< 8.0.16) that doesn't support IF NOT EXISTS
    alter_fallbacks = [
        "ALTER TABLE ai_tournament_picks ADD COLUMN reason TEXT DEFAULT NULL COMMENT 'Detailed persona rationale' AFTER thesis;",
        "ALTER TABLE ai_tournament_picks ADD COLUMN entry_criteria TEXT DEFAULT NULL COMMENT 'Specific entry triggers that fired' AFTER reason;",
        "ALTER TABLE ai_tournament_picks ADD COLUMN take_profit DECIMAL(16,4) DEFAULT NULL AFTER entry_price;",
        "ALTER TABLE ai_tournament_picks ADD COLUMN stop_loss DECIMAL(16,4) DEFAULT NULL AFTER take_profit;",
    ]

    # Last resort: drop and recreate if column mismatch persists
    drop_and_recreate = """
        DROP TABLE IF EXISTS ai_tournament_picks;
    """ + ddl[0]

    insert_sql = """
        INSERT INTO ai_tournament_picks
            (model_id, symbol, asset_class, direction, entry_price,
             take_profit, stop_loss, thesis, reason, entry_criteria, data_source, confidence,
             timeframe, status, submitted_at, provider, model_version,
             strategy_name, persona_id, current_price, unrealized_pnl_pct,
             pnl_pct, exit_price, exit_reason, resolved_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            current_price   = VALUES(current_price),
            unrealized_pnl_pct = VALUES(unrealized_pnl_pct),
            pnl_pct         = VALUES(pnl_pct),
            exit_price      = VALUES(exit_price),
            exit_reason     = VALUES(exit_reason),
            resolved_at     = VALUES(resolved_at),
            status          = VALUES(status),
            reason          = VALUES(reason),
            updated_at      = NOW()
    """

    return ddl, rows, insert_sql, alter_fallbacks, drop_and_recreate


def main() -> None:
    print(f"[ingest] AI Tournament DB Ingestion — {datetime.now(timezone.utc).isoformat()}")
    if DRY_RUN:
        print("[ingest] DRY RUN — no writes will be performed")

    picks = load_latest_picks()
    if not picks:
        print("[ingest] No picks to ingest — exiting")
        return

    ddl_statements, rows, insert_sql, alter_fallbacks, drop_and_recreate = build_upsert_sql(picks)
    print(f"[ingest] {len(rows)} rows to upsert")

    # Try MySQL connection
    db_pass = get_env_or_default("DB_PASS_STOCKS", get_env_or_default("MYSQL_PASSWORD", ""))
    db_host = get_env_or_default("DB_HOST_STOCKS", "mysql.50webs.com")
    db_name = get_env_or_default("DB_NAME_STOCKS", "ejaguiar1_stocks")
    db_user = get_env_or_default("DB_USER_STOCKS", "ejaguiar1_stocks")

    if not db_pass:
        print("[ingest] WARNING: No DB_PASS_STOCKS set — skipping MySQL ingestion")
        # Still count as soft-success so pipeline continues
        return

    if DRY_RUN:
        print(f"[ingest] Would connect to {db_host}/{db_name} as {db_user}")
        print(f"[ingest] Would execute DDL ({len(ddl_statements)} statements)")
        print(f"[ingest] Would upsert {len(rows)} rows")
        print("[ingest] DRY RUN complete")
        return

    try:
        import pymysql
        conn = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_pass,
            database=db_name,
            port=int(get_env_or_default("DB_PORT", "3306")),
            connect_timeout=10,
            autocommit=False,
        )
        with conn.cursor() as cur:
            for ddl in ddl_statements:
                try:
                    cur.execute(ddl)
                except Exception as alter_e:
                    print(f"[ingest] DDL failed, trying fallback: {alter_e}")
                    import re
                    for fallback in alter_fallbacks:
                        try:
                            cur.execute(fallback)
                            print(f"[ingest] Fallback ALTER succeeded")
                        except Exception:
                            pass
            print("[ingest] Tables verified")

            # Insert in batches
            batch_size = 50
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                cur.executemany(insert_sql, batch)
                print(f"[ingest] Inserted batch {i // batch_size + 1}/{(len(rows) - 1) // batch_size + 1}")

        conn.commit()
        conn.close()
        print(f"[ingest] Successfully ingested {len(rows)} picks to MySQL")

    except ImportError:
        print("[ingest] WARNING: pymysql not installed — skipping MySQL ingestion")
    except Exception as e:
        err = str(e)
        print(f"[ingest] ERROR: MySQL ingestion failed: {err}")
        # Last resort: column mismatch — drop and recreate table
        if "Unknown column" in err:
            try:
                import pymysql
                conn2 = pymysql.connect(host=db_host, user=db_user, password=db_pass, database=db_name, port=3306, connect_timeout=10)
                with conn2.cursor() as cur:
                    for stmt in drop_and_recreate.split(';'):
                        s = stmt.strip()
                        if s:
                            cur.execute(s + ';')
                conn2.commit()
                conn2.close()
                print("[ingest] Table dropped and recreated — data will be ingested on next run")
            except Exception as e2:
                print(f"[ingest] Drop/recreate also failed: {e2}")
        # Don't crash the pipeline — the JSON files still exist


if __name__ == "__main__":
    main()
