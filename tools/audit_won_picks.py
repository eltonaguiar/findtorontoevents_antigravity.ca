#!/usr/bin/env python3
"""
audit_won_picks.py — Query DB for WON picks with negative PnL and optionally correct them.

Reports count and details of picks where status='WON' but pnl_pct < 0,
which is logically impossible (a won trade should have positive PnL).

Usage:
    python tools/audit_won_picks.py              # report only
    python tools/audit_won_picks.py --correct    # also fix their status to LOST
    python tools/audit_won_picks.py --dry-run    # show what would be corrected without executing
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def get_db_connection():
    """Get MySQL connection using env vars or defaults."""
    try:
        import pymysql
    except ImportError:
        print("ERROR: pymysql not installed. Run: pip install pymysql")
        sys.exit(1)

    host = os.environ.get("DB_STOCKS_HOST", os.environ.get("DB_HOST", "mysql.50webs.com"))
    port = int(os.environ.get("DB_STOCKS_PORT", os.environ.get("DB_PORT", "3306")))
    user = os.environ.get("DB_STOCKS_USER", os.environ.get("AUDIT_DB_USER", ""))
    password = os.environ.get("DB_PASS_STOCKS", os.environ.get("DB_STOCKS_PASSWORD", os.environ.get("AUDIT_DB_PASS", "")))
    database = os.environ.get("DB_STOCKS_NAME", os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"))

    if not user or not password:
        print("ERROR: DB credentials not set. Set DB_STOCKS_USER and DB_PASS_STOCKS (or AUDIT_DB_USER/AUDIT_DB_PASS).")
        sys.exit(1)

    return pymysql.connect(
        host=host, port=port, user=user,
        password=password, database=database,
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
    )


def audit_won_negative_picks(conn, dry_run=False):
    """Query for WON picks with negative PnL and optionally correct them."""
    cur = conn.cursor()

    # Find WON picks with negative PnL.
    # 2026-05-25: trading_picks schema has `category` (not `asset_class`)
    # and `created_at` (not `opened_at`). The old column names crashed the
    # tool on every run, blocking the won-picks contradiction audit.
    query = """
        SELECT id, symbol, direction, entry_price, exit_price, pnl_pct,
               status, exit_reason, strategy, source_system, category,
               created_at, closed_at
        FROM trading_picks
        WHERE status = 'WON' AND pnl_pct IS NOT NULL AND pnl_pct < 0
        ORDER BY pnl_pct ASC
    """
    cur.execute(query)
    rows = cur.fetchall()

    if not rows:
        print("No WON picks with negative PnL found. Database is clean.")
        return 0

    print(f"Found {len(rows)} WON picks with negative PnL:")
    print(f"{'ID':>10} {'Symbol':<15} {'Dir':<6} {'PnL%':>10} {'Exit Reason':<18} {'Strategy':<20} {'Source':<20}")
    print("-" * 105)

    total_pnl = 0.0
    for row in rows:
        total_pnl += float(row["pnl_pct"] or 0)
        print(f"{row['id']:>10} {str(row['symbol'])[:14]:<15} {str(row['direction'])[:5]:<6} "
              f"{float(row['pnl_pct']):>10.2f} {str(row['exit_reason'])[:17]:<18} "
              f"{str(row['strategy'])[:19]:<20} {str(row['source_system'])[:19]:<20}")

    avg_pnl = total_pnl / len(rows)
    print("-" * 105)
    print(f"Average PnL: {avg_pnl:.2f}% (range: {float(rows[-1]['pnl_pct']):.2f}% to {float(rows[0]['pnl_pct']):.2f}%)")
    print()

    # Show correction plan
    ids_to_correct = [row["id"] for row in rows]
    print(f"Records to correct: {len(ids_to_correct)}")
    print(f"  Status: WON -> LOST")
    print()

    if dry_run:
        print("DRY RUN: No changes made.")
        return len(rows)

    # Ask for confirmation
    confirm = input("Correct these picks? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        return len(rows)

    # Perform correction
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    updated = 0
    for row in rows:
        update_query = """
            UPDATE trading_picks
            SET status = 'LOST',
                exit_reason = CONCAT('AUTO_CORRECTED_FROM_WON:', COALESCE(exit_reason, 'UNKNOWN'))
            WHERE id = %s
        """
        try:
            cur.execute(update_query, (row["id"],))
            updated += 1
        except Exception as e:
            print(f"  ERROR updating id={row['id']}: {e}")

    conn.commit()
    print(f"Corrected {updated}/{len(rows)} picks. Status changed from WON to LOST.")
    return len(rows)


def summary_by_exit_reason(conn):
    """Show breakdown of negative-PnL WON picks by exit_reason."""
    cur = conn.cursor()
    query = """
        SELECT exit_reason, COUNT(*) as cnt,
               ROUND(AVG(pnl_pct), 2) as avg_pnl,
               MIN(pnl_pct) as min_pnl, MAX(pnl_pct) as max_pnl
        FROM trading_picks
        WHERE status = 'WON' AND pnl_pct < 0
        GROUP BY exit_reason
        ORDER BY cnt DESC
    """
    cur.execute(query)
    rows = cur.fetchall()

    if not rows:
        return

    print("\nBreakdown by exit_reason:")
    print(f"{'Exit Reason':<25} {'Count':>6} {'Avg PnL%':>10} {'Min PnL%':>10} {'Max PnL%':>10}")
    print("-" * 65)
    for row in rows:
        print(f"{str(row['exit_reason'])[:24]:<25} {row['cnt']:>6} "
              f"{float(row['avg_pnl']):>10.2f} {float(row['min_pnl']):>10.2f} {float(row['max_pnl']):>10.2f}")


def summary_by_direction(conn):
    """Show breakdown of negative-PnL WON picks by direction."""
    cur = conn.cursor()
    query = """
        SELECT direction, COUNT(*) as cnt,
               ROUND(AVG(pnl_pct), 2) as avg_pnl
        FROM trading_picks
        WHERE status = 'WON' AND pnl_pct < 0
        GROUP BY direction
        ORDER BY cnt DESC
    """
    cur.execute(query)
    rows = cur.fetchall()

    if not rows:
        return

    print("\nBreakdown by direction:")
    print(f"{'Direction':<10} {'Count':>6} {'Avg PnL%':>10}")
    print("-" * 30)
    for row in rows:
        print(f"{str(row['direction'])[:9]:<10} {row['cnt']:>6} {float(row['avg_pnl']):>10.2f}")


def main():
    parser = argparse.ArgumentParser(description="Audit WON picks with negative PnL")
    parser.add_argument("--correct", action="store_true", help="Correct status from WON to LOST")
    parser.add_argument("--dry-run", action="store_true", help="Show corrections without executing")
    args = parser.parse_args()

    print("=" * 60)
    print("WON PnL Contradiction Audit")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)
    print()

    conn = get_db_connection()
    try:
        count = audit_won_negative_picks(conn, dry_run=(args.dry_run or not args.correct))
        if count > 0:
            summary_by_exit_reason(conn)
            summary_by_direction(conn)
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
