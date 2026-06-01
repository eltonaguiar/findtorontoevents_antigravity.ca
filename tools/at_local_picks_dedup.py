
import sys
import os
from pathlib import Path
import logging

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.db_env import get_stocks_creds
import pymysql

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

def dedup_at_local_picks(dry_run=True):
    creds = get_stocks_creds()
    conn = pymysql.connect(**creds)
    try:
        with conn.cursor() as cur:
            # Count total rows
            cur.execute("SELECT COUNT(*) FROM at_local_picks")
            total_before = cur.fetchone()[0]
            log.info(f"Total rows in at_local_picks before: {total_before}")
            
            # Find duplicates
            sql_find = """
                SELECT symbol, direction, source_system, signal_timestamp, COUNT(*) as cnt
                FROM at_local_picks
                GROUP BY symbol, direction, source_system, signal_timestamp
                HAVING cnt > 1
            """
            cur.execute(sql_find)
            dupe_groups = cur.fetchall()
            total_to_delete = sum(r[4] - 1 for r in dupe_groups)
            log.info(f"Found {len(dupe_groups)} duplicate groups, total {total_to_delete} extra rows to delete.")
            
            if total_to_delete == 0:
                log.info("No duplicates found.")
                return
            
            if dry_run:
                log.info("DRY-RUN: No changes applied.")
                return

            # Deletion strategy: keep the row with MIN(id) for each group
            # We'll do it in chunks if possible, but for 300k rows, a single query might work if indexed correctly.
            # idx_dedup (symbol, direction, source_system, signal_timestamp) exists.
            
            sql_delete = """
                DELETE t1 FROM at_local_picks t1
                INNER JOIN (
                    SELECT MIN(id) as keeper_id, symbol, direction, source_system, signal_timestamp
                    FROM at_local_picks
                    GROUP BY symbol, direction, source_system, signal_timestamp
                    HAVING COUNT(*) > 1
                ) t2 ON t1.symbol <=> t2.symbol 
                   AND t1.direction <=> t2.direction 
                   AND t1.source_system <=> t2.source_system 
                   AND t1.signal_timestamp <=> t2.signal_timestamp
                WHERE t1.id != t2.keeper_id
            """
            log.info("Executing deletion... this may take a while.")
            cur.execute(sql_delete)
            deleted = cur.rowcount
            log.info(f"Deleted {deleted} rows.")
            conn.commit()
            
            cur.execute("SELECT COUNT(*) FROM at_local_picks")
            total_after = cur.fetchone()[0]
            log.info(f"Total rows in at_local_picks after: {total_after}")
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply changes")
    args = parser.parse_args()
    
    dedup_at_local_picks(dry_run=not args.apply)
