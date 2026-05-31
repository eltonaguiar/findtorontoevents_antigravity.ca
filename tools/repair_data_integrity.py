#!/usr/bin/env python3
"""
Data Integrity Repair Tool — PR #1 (Critical Data Integrity Fixes)

Consolidates fixes for P0 data integrity incidents:
1. FOREX pnl_pct < -100% (Unit clamp bug)
2. WON status rows with negative pnl (Status/PnL contradiction)
3. Adds CHECK constraint for pnl_pct sign coherence (Migration)

Usage:
  python3 tools/repair_data_integrity.py           # dry-run preview
  python3 tools/repair_data_integrity.py --apply   # execute changes
"""

import argparse
import os
import sys
import pymysql
import logging
from datetime import datetime, timezone
from pathlib import Path

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── DB Connection ──────────────────────────────────────────────────────────────
DB_HOST = "mysql.50webs.com"
DB_USER = "ejaguiar1_stocks"
DB_PASS = os.getenv("DB_PASS_STOCKS", "")
DB_NAME = "ejaguiar1_stocks"

def get_conn():
    if not DB_PASS:
        raise RuntimeError("DB_PASS_STOCKS not set")
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        connect_timeout=15,
        charset="utf8mb4",
        autocommit=False,
    )

# ── Repair Logic ───────────────────────────────────────────────────────────────

def repair_forex_pnl(conn, apply: bool) -> dict:
    """Fix FOREX pnl_pct < -100% (unit clamp bug)."""
    cur = conn.cursor()
    
    # 1. Count affected rows
    cur.execute("""
        SELECT COUNT(*) FROM trading_picks 
        WHERE category = 'FOREX' AND pnl_pct < -100
    """)
    count = cur.fetchone()[0]
    
    stats = {"name": "FOREX PnL Clamp", "affected": count, "status": "SKIPPED"}
    
    if count > 0:
        if apply:
            # Use -100 as the clamp value for FOREX
            cur.execute("""
                UPDATE trading_picks 
                SET pnl_pct = -100, 
                    exit_reason = CONCAT(COALESCE(exit_reason, ''), ' (REPAIRED_PNL_CLAMP)'),
                    updated_at = NOW()
                WHERE category = 'FOREX' AND pnl_pct < -100
            """)
            conn.commit()
            stats["status"] = "FIXED"
        else:
            stats["status"] = "DRY_RUN"
            
    return stats

def repair_pnl_contradictions(conn, apply: bool) -> dict:
    """Re-label status rows with PnL sign contradictions."""
    cur = conn.cursor()
    
    # 1. Count affected rows
    # WON/TP_HIT with negative PnL OR LOST/SL_HIT with positive PnL
    cur.execute("""
        SELECT COUNT(*) FROM trading_picks
        WHERE (status IN ('WON', 'TP_HIT', 'closed_win') AND pnl_pct < 0)
           OR (status IN ('LOST', 'SL_HIT', 'closed_loss') AND pnl_pct > 0)
    """)
    count = cur.fetchone()[0]
    
    stats = {"name": "Status/PnL Contradiction", "affected": count, "status": "SKIPPED"}
    
    if count > 0:
        if apply:
            # Re-label based on PnL sign
            cur.execute("""
                UPDATE trading_picks
                SET status = CASE
                        WHEN pnl_pct < 0 THEN 'LOST'
                        ELSE 'WON'
                    END,
                    exit_reason = CONCAT(COALESCE(exit_reason, ''), ' (REPAIRED_PNL_CONTRADICTION)'),
                    updated_at = NOW()
                WHERE (status IN ('WON', 'TP_HIT', 'closed_win') AND pnl_pct < 0)
                   OR (status IN ('LOST', 'SL_HIT', 'closed_loss') AND pnl_pct > 0)
            """)
            conn.commit()
            stats["status"] = "FIXED"
        else:
            stats["status"] = "DRY_RUN"
            
    return stats

def apply_check_constraint(conn, apply: bool) -> dict:
    """Add CHECK constraint for pnl_pct sign coherence (Migration)."""
    cur = conn.cursor()
    
    # Check if constraint already exists (MySQL 8.0.16+ supports CHECK constraints)
    # We'll try to add it. If it fails because it exists, we handle it.
    
    stats = {"name": "PnL Sign CHECK Constraint", "affected": 0, "status": "SKIPPED"}
    
    # Note: MySQL CHECK constraints are only enforced in 8.0.16+. 
    # For older versions, this is a no-op but good for future-proofing.
    
    # We'll use a more robust way to check if we can add it.
    # Since we don't know the exact MySQL version, we'll attempt it.
    
    if apply:
        try:
            # This is a bit tricky in MySQL because you can't easily add a CHECK constraint 
            # to an existing table without ALTER TABLE.
            # We'll attempt to add it.
            cur.execute("""
                ALTER TABLE trading_picks 
                ADD CONSTRAINT chk_pnl_sign_coherence 
                CHECK (
                    (status IN ('WON', 'TP_HIT', 'closed_win') AND pnl_pct >= -0.01) OR
                    (status IN ('LOST', 'SL_HIT', 'closed_loss') AND pnl_pct <= 0.01) OR
                    (status NOT IN ('WON', 'TP_HIT', 'closed_win', 'LOST', 'SL_HIT', 'closed_loss'))
                )
            """)
            conn.commit()
            stats["status"] = "FIXED"
            stats["affected"] = 1
        except Exception as e:
            conn.rollback()
            if "Duplicate constraint" in str(e) or "already exists" in str(e).lower():
                stats["status"] = "ALREADY_EXISTS"
            else:
                stats["status"] = f"FAILED: {str(e)}"
    else:
        stats["status"] = "DRY_RUN (Migration check only)"
        
    return stats

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Repair data integrity issues in trading_picks")
    ap.add_argument("--apply", action="store_true", help="Execute changes (default: dry-run)")
    args = ap.parse_args()

    conn = get_conn()
    try:
        print("=" * 70)
        print("DATA INTEGRITY REPAIR TOOL — trading_picks")
        print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
        print("=" * 70)

        results = []
        
        # 1. FOREX PnL Clamp
        results.append(repair_forex_pnl(conn, args.apply))
        
        # 2. Status/PnL Contradiction
        results.append(repair_pnl_contradictions(conn, args.apply))
        
        # 3. CHECK Constraint
        results.append(apply_check_constraint(conn, args.apply))

        print(f"\n{'REPAIR TASK':<35} | {'STATUS':<15} | {'AFFECTED':<10}")
        print("-" * 70)
        total_affected = 0
        for r in results:
            print(f"{r['name']:<35} | {r['status']:<15} | {r['affected']:<10,}")
            if r['status'] in ("FIXED", "DRY_RUN"):
                total_affected += r['affected']
        
        print("-" * 70)
        print(f"{'TOTAL AFFECTED':<35} | {'':<15} | {total_affected:<10,}")
        print("=" * 70)
        
        if not args.apply and total_affected > 0:
            print("\n⚠️  This was a DRY-RUN. Run with --apply to execute changes.")
        elif args.apply:
            print("\n✅ Repairs applied successfully.")
        else:
            print("\nNo repairs needed.")

    except Exception as e:
        log.error(f"Repair failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
