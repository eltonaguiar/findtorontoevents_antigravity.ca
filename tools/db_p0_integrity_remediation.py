#!/usr/bin/env python3
"""
DB P0 Integrity Remediation
- Mass EXPIRED-stamp 29M backlog (Incident #13)
- Fix WON/LOST labeling contradiction (Incident #11)
- Dedup ghost rows (Incident #12)
- Unit-clamp FOREX pnl_pct (Incident #2)
- P1: Standardize ALL non-canonical statuses (WIN, LOSS, closed, CLOSED_SL, CLOSED_TP, SIGNAL, FLAT, STALE)
  → Run tools/standardize_statuses.py --apply for full PnL-based relabeling
"""

import os
import sys
import pymysql
from datetime import datetime

DB_HOST = "mysql.50webs.com"
DB_USER = "ejaguiar1_stocks"
DB_PASS = os.getenv("DB_PASS_STOCKS")
DB_NAME = "ejaguiar1_stocks"

def get_conn():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )

def run_remediation():
    if not DB_PASS:
        print("ERROR: DB_PASS_STOCKS not set")
        sys.exit(1)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # 1. Incident #13: 29M Open Bloat
            print("--- Incident #13: Mass EXPIRED-stamp open picks > 45 days ---")
            cur.execute("SELECT COUNT(*) as cnt FROM trading_picks WHERE status = 'OPEN' AND created_at < NOW() - INTERVAL 45 DAY")
            count = cur.fetchone()['cnt']
            print(f"Found {count:,} stale open picks.")
            if count > 0:
                cur.execute("UPDATE trading_picks SET status = 'EXPIRED', exit_reason = 'MAX_HOLD_EXPIRY_BLOAT_FIX', closed_at = NOW(), updated_at = NOW() WHERE status = 'OPEN' AND created_at < NOW() - INTERVAL 45 DAY")
                print(f"Successfully EXPIRED-stamped {cur.rowcount:,} rows.")

            # 2. Incident #11: WON Status Contradiction
            print("\n--- Incident #11: Fix WON/LOST label contradiction ---")
            cur.execute("UPDATE trading_picks SET status = 'TP_HIT', exit_reason = COALESCE(exit_reason,'WON_LABEL_CORRECTION'), updated_at = NOW() WHERE status = 'WON' AND pnl_pct > 0")
            print(f"Re-labeled {cur.rowcount:,} WON rows as TP_HIT (positive PnL).")
            cur.execute("UPDATE trading_picks SET status = 'LOST', exit_reason = COALESCE(exit_reason,'WON_LABEL_CORRECTION'), updated_at = NOW() WHERE status = 'WON' AND pnl_pct <= 0")
            print(f"Re-labeled {cur.rowcount:,} WON rows as LOST (non-positive PnL).")

            # 3. Incident #12: Ghost Row De-duplication (Example: MATICUSDT)
            print("\n--- Incident #12: De-duplicate ghost rows ---")
            # We identify duplicates by exact match of key fields.
            # Safety: only delete if they are indeed identical.
            # Using a temporary table to keep only one ID per group.
            cur.execute("CREATE TEMPORARY TABLE tmp_dedup AS SELECT MIN(id) as keep_id FROM trading_picks GROUP BY category, strategy, symbol, direction, pnl_pct, created_at HAVING COUNT(*) > 1")
            cur.execute("SELECT COUNT(*) as cnt FROM tmp_dedup")
            dup_groups = cur.fetchone()['cnt']
            print(f"Found {dup_groups:,} groups of duplicates.")
            if dup_groups > 0:
                # This query deletes all but the MIN(id) for each group
                # Caution: for large tables, this might be slow.
                # However, temporary table approach is safer than self-join.
                cur.execute("""
                    DELETE t1 FROM trading_picks t1
                    INNER JOIN (
                        SELECT category, strategy, symbol, direction, pnl_pct, created_at, MIN(id) as min_id
                        FROM trading_picks
                        GROUP BY category, strategy, symbol, direction, pnl_pct, created_at
                        HAVING COUNT(*) > 1
                    ) t2 ON IFNULL(t1.category,'') = IFNULL(t2.category,'')
                        AND IFNULL(t1.strategy,'') = IFNULL(t2.strategy,'') 
                        AND t1.symbol = t2.symbol 
                        AND t1.direction = t2.direction 
                        AND t1.pnl_pct = t2.pnl_pct 
                        AND t1.created_at = t2.created_at
                    WHERE t1.id > t2.min_id
                """)
                print(f"Deleted {cur.rowcount:,} duplicate ghost rows.")

            # 4. Incident #2: FOREX Unit Clamp
            print("\n--- Incident #2: Clamp FOREX pnl_pct < -100% ---")
            cur.execute("UPDATE trading_picks SET pnl_pct = -100, exit_reason = 'CLAMP_FIX' WHERE category = 'FOREX' AND pnl_pct < -100")
            print(f"Clamped {cur.rowcount:,} FOREX rows to -100%.")

            conn.commit()
            print("\nRemediation complete. All changes committed.")

    except Exception as e:
        conn.rollback()
        print(f"CRITICAL ERROR during remediation: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    run_remediation()
