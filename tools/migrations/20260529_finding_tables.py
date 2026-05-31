#!/usr/bin/env python3
"""Migration: create FINDING_<CLASS> tables on ejaguiar1_stocks.

One table per asset class (mirrors INCIDENT_<CLASS> / ENHANCEMENT_<CLASS>).
Idempotent via CREATE TABLE IF NOT EXISTS. Safe to re-run. Times stored UTC.

Default mode is DRY-RUN (prints the 9 CREATE statements without DB connect).
Pass --apply to actually execute on the live DB.

  python tools/migrations/20260529_finding_tables.py            # dry-run
  python tools/migrations/20260529_finding_tables.py --apply    # write

Deviation from 20260529_incident_target_release.py: that script applies by
default and uses --dry-run to skip writes. The build spec for this migration
explicitly inverts the polarity (dry-run default, --apply writes) and requires
the dry-run path to skip the DB connection entirely so it runs in CI without
secrets. Both behaviors honored here.
"""
from __future__ import annotations
import os, sys

CLASSES = ["OVERALL", "STOCKS", "ETFS", "CRYPTO", "FOREX", "COMMODITIES", "BONDS", "FUTURES", "PENNY"]
APPLY = "--apply" in sys.argv

DDL_TEMPLATE = """CREATE TABLE IF NOT EXISTS FINDING_{cls} (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity ENUM('P0','P1','P2','P3','INFO','NOTEWORTHY') NOT NULL DEFAULT 'INFO',
    status ENUM('OPEN','INVESTIGATING','CONFIRMED','RESOLVED','WONTFIX') NOT NULL DEFAULT 'OPEN',
    agent VARCHAR(80) NULL,
    evidence TEXT NULL,
    linked_incident_id INT NULL,
    linked_enhancement_id INT NULL,
    created_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_title (title),
    INDEX ix_status (status),
    INDEX ix_severity (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""


def main() -> int:
    statements = [DDL_TEMPLATE.format(cls=cls) for cls in CLASSES]

    if not APPLY:
        print("# DRY-RUN (no DB connection). Pass --apply to execute on live DB.")
        print(f"# Target: ejaguiar1_stocks @ mysql.50webs.com")
        print(f"# Classes: {CLASSES}")
        print()
        for cls, stmt in zip(CLASSES, statements):
            print(f"-- [{cls}]")
            print(stmt + ";")
            print()
        print(f"# {len(statements)} CREATE TABLE statements ready (re-run with --apply to write).")
        return 0

    import pymysql  # only required when actually applying
    conn = pymysql.connect(
        host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
        user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
        password=os.environ["DB_PASS_STOCKS"],
        database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
        port=3306, connect_timeout=25, autocommit=True,
    )
    cur = conn.cursor()
    for cls, stmt in zip(CLASSES, statements):
        tbl = f"FINDING_{cls}"
        cur.execute(stmt)
        # CREATE TABLE IF NOT EXISTS emits a warning (not an error) if it already
        # existed; check existence to report meaningfully.
        cur.execute(f"SHOW TABLES LIKE %s", (tbl,))
        exists = cur.fetchone() is not None
        print(f"  {tbl}: {'OK (exists)' if exists else 'CREATED'}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
