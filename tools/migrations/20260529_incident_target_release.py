#!/usr/bin/env python3
"""Migration: add target_release column to all INCIDENT_<CLASS> tables.

Applied to ejaguiar1_stocks on 2026-05-29. The ENHANCEMENT_<CLASS> tables already
had target_release; the INCIDENT_<CLASS> tables did not, which broke the
cli_track.py incident upsert path (it INSERTs target_release) and left the
incidents.html "Target" column unpopulated for incidents. Additive + idempotent
(check-then-add), safe to re-run.

  python tools/migrations/20260529_incident_target_release.py            # apply
  python tools/migrations/20260529_incident_target_release.py --dry-run  # report
"""
from __future__ import annotations
import os, sys
import pymysql

CLASSES = ["OVERALL", "STOCKS", "ETFS", "CRYPTO", "FOREX", "COMMODITIES", "BONDS", "FUTURES", "PENNY"]
DRY = "--dry-run" in sys.argv


def main() -> int:
    conn = pymysql.connect(
        host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
        user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
        password=os.environ["DB_PASS_STOCKS"],
        database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
        port=3306, connect_timeout=25, autocommit=True,
    )
    cur = conn.cursor()
    for cls in CLASSES:
        tbl = f"INCIDENT_{cls}"
        cur.execute(f"SHOW COLUMNS FROM {tbl} LIKE 'target_release'")
        if cur.fetchone():
            print(f"  {tbl}: already has target_release")
            continue
        if DRY:
            print(f"  {tbl}: WOULD ADD target_release")
            continue
        cur.execute(f"ALTER TABLE {tbl} ADD COLUMN target_release VARCHAR(64) NULL AFTER recommended_fix")
        print(f"  {tbl}: ADDED target_release")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
