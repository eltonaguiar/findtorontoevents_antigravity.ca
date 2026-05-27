#!/usr/bin/env python3
"""
tools/fix_forex_pnl_clamping.py — Fix FOREX PnL clamping bug (P0 #23).

Problem: FOREX picks with PnL < -100% (e.g. -106,700%) are stored in `trading_picks`.
These are artifacts of price-unit mismatches that escaped the sanity cap.

Operations:
  1. Identify FOREX picks with PnL < -100% (or other extreme outliers).
  2. Clamp them to the FOREX sanity cap (-30%).
  3. Log the changes.

Usage:
  python tools/fix_forex_pnl_clamping.py            # dry-run
  python tools/fix_forex_pnl_clamping.py --apply    # execute
"""
import argparse
import os
import pymysql
from tools.db_env import get_stocks_creds

def get_db_connection():
    creds = get_stocks_creds()
    return pymysql.connect(
        host=creds["host"],
        port=creds["port"],
        user=creds["user"],
        password=creds["password"],
        database=creds["database"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

def run(apply=False):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Identify FOREX picks with extreme PnL (<-100%)
    sql = "SELECT id, symbol, pnl_pct FROM trading_picks WHERE category='FOREX' AND pnl_pct < -100"
    cur.execute(sql)
    rows = cur.fetchall()
    
    if not rows:
        print("No extreme FOREX PnL outliers found.")
        conn.close()
        return

    print(f"Found {len(rows)} FOREX picks with extreme PnL (<-100%).")
    for r in rows:
        print(f"  id={r['id']} sym={r['symbol']} pnl={r['pnl_pct']}%")
        
    if not apply:
        print("\nDRY-RUN: Would clamp these to -30%. Run with --apply to execute.")
        conn.close()
        return

    # Clamp to -30%
    ids = [r['id'] for r in rows]
    placeholders = ",".join(["%s"] * len(ids))
    cur.execute(f"UPDATE trading_picks SET pnl_pct=-30.0 WHERE id IN ({placeholders})", ids)
    conn.commit()
    print(f"Applied: clamped {len(rows)} FOREX picks to -30%.")
    conn.close()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    run(apply=args.apply)
