#!/usr/bin/env python3
"""
bridge_picks_to_signals.py — Bridge daily stock picks to the live signal engine.

Reads picks from stock_picks, miracle_picks2, miracle_picks3 tables and inserts them
as signals into lm_signals, allowing the live_trade.php auto_execute to paper trade them.

This fixes the CRITICAL ARCHITECTURAL GAP: zero forward/backtest overlap.
Backtested algorithms (Cursor Genius A+, ETF Masters A, Sector Momentum A, etc.)
will now generate live signals for paper trading validation.

Run via GitHub Actions daily after stock picks are generated.

Usage:
    python scripts/bridge_picks_to_signals.py [--dry-run] [--days 1]
"""

import os
import sys
import json
import argparse
import mysql.connector
from datetime import datetime, timedelta

# ─── Config ──────────────────────────────────────────────────────────────────
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', ''),
    'password': os.environ.get('DB_PASS', ''),
    'database': os.environ.get('DB_NAME', 'ejaguiar1_stocks'),
    'charset': 'utf8'
}

API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

# Algorithm mapping: stock_picks algorithm -> live signal algorithm name
# Only bridge A/A+ grade algorithms to avoid polluting live signals with D-grade
ALGO_MAP = {
    # A+ Grade
    'Cursor Genius':      {'enabled': True,  'grade': 'A+', 'sharpe': 5.27,
                           'tp': 10.0, 'sl': 5.0, 'hold': 168},  # 7 days
    # A Grade
    'ETF Masters':        {'enabled': True,  'grade': 'A',  'sharpe': 2.05,
                           'tp': 10.0, 'sl': 5.0, 'hold': 168},
    'Sector Momentum':    {'enabled': True,  'grade': 'A',  'sharpe': 2.12,
                           'tp': 10.0, 'sl': 5.0, 'hold': 168},
    # C Grade — enable with caution
    'Sector Rotation':    {'enabled': False, 'grade': 'C',  'sharpe': 0.97,
                           'tp': 10.0, 'sl': 5.0, 'hold': 168},
    # D Grade — DISABLED
    'Blue Chip Growth':   {'enabled': False, 'grade': 'D',  'sharpe': -0.74,
                           'tp': 10.0, 'sl': 5.0, 'hold': 168},
    'Technical Momentum': {'enabled': False, 'grade': 'D',  'sharpe': -3.09,
                           'tp': 10.0, 'sl': 5.0, 'hold': 168},
    'Composite Rating':   {'enabled': False, 'grade': 'D',  'sharpe': -3.36,
                           'tp': 10.0, 'sl': 5.0, 'hold': 168},
}

# Crypto/Forex algorithm mapping for horizon picks
HORIZON_MAP = {
    'Trend Following': {
        'CRYPTO': {'enabled': True,  'grade': 'A+', 'sharpe': 4.45,
                   'tp': 10.0, 'sl': 5.0, 'hold': 720},  # 30 days
        'FOREX':  {'enabled': True,  'grade': 'A',  'sharpe': 2.42,
                   'tp': 2.0, 'sl': 1.0, 'hold': 336},   # 14 days
    },
    'Mean Reversion': {
        'CRYPTO': {'enabled': False, 'grade': 'D',  'sharpe': -1.56,
                   'tp': 10.0, 'sl': 5.0, 'hold': 720},  # DISABLED for crypto
        'FOREX':  {'enabled': True,  'grade': 'A',  'sharpe': 2.29,
                   'tp': 2.0, 'sl': 1.0, 'hold': 336},
    },
}


def get_db_connection():
    """Connect to the database."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as e:
        print(f"DB connection error: {e}")
        sys.exit(1)


def ensure_bridge_table(cursor):
    """Ensure the bridge tracking table exists."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lm_picks_bridge (
            id INT AUTO_INCREMENT PRIMARY KEY,
            source_table VARCHAR(50) NOT NULL,
            source_id INT NOT NULL,
            signal_id INT DEFAULT NULL,
            algorithm_name VARCHAR(100) NOT NULL,
            ticker VARCHAR(20) NOT NULL,
            pick_date DATE NOT NULL,
            direction VARCHAR(10) DEFAULT 'LONG',
            entry_price DECIMAL(12,4) DEFAULT NULL,
            tp_pct DECIMAL(5,2) DEFAULT NULL,
            sl_pct DECIMAL(5,2) DEFAULT NULL,
            max_hold_hours INT DEFAULT 168,
            status VARCHAR(20) DEFAULT 'pending',
            created_at DATETIME,
            UNIQUE KEY uq_source (source_table, source_id),
            INDEX idx_status (status),
            INDEX idx_date (pick_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8
    """)


def fetch_recent_stock_picks(cursor, days=1):
    """Fetch recent picks from stock_picks table (Cursor Genius, ETF Masters, etc.)."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
    picks = []

    # stock_picks table
    try:
        cursor.execute("""
            SELECT id, ticker, algorithm_name, pick_date, entry_price, direction,
                   signal_strength, rationale
            FROM stock_picks
            WHERE pick_date >= %s
            ORDER BY pick_date DESC
        """, (cutoff,))
        for row in cursor.fetchall():
            picks.append({
                'source_table': 'stock_picks',
                'source_id': row[0],
                'ticker': row[1],
                'algorithm': row[2] if row[2] else 'Unknown',
                'pick_date': row[3],
                'entry_price': float(row[4]) if row[4] else None,
                'direction': row[5] if row[5] else 'LONG',
                'strength': int(row[6]) if row[6] else 70,
                'rationale': row[7] if row[7] else '',
                'asset_class': 'STOCK'
            })
    except mysql.connector.Error as e:
        print(f"stock_picks query error: {e}")

    # miracle_picks2 table (additional algorithms)
    try:
        cursor.execute("""
            SELECT id, ticker, algorithm_name, pick_date, entry_price, direction,
                   signal_strength, rationale
            FROM miracle_picks2
            WHERE pick_date >= %s
            ORDER BY pick_date DESC
        """, (cutoff,))
        for row in cursor.fetchall():
            picks.append({
                'source_table': 'miracle_picks2',
                'source_id': row[0],
                'ticker': row[1],
                'algorithm': row[2] if row[2] else 'Unknown',
                'pick_date': row[3],
                'entry_price': float(row[4]) if row[4] else None,
                'direction': row[5] if row[5] else 'LONG',
                'strength': int(row[6]) if row[6] else 70,
                'rationale': row[7] if row[7] else '',
                'asset_class': 'STOCK'
            })
    except mysql.connector.Error as e:
        print(f"miracle_picks2 query error: {e}")

    # miracle_picks3 table (more algorithms)
    try:
        cursor.execute("""
            SELECT id, ticker, algorithm_name, pick_date, entry_price, direction,
                   signal_strength, rationale
            FROM miracle_picks3
            WHERE pick_date >= %s
            ORDER BY pick_date DESC
        """, (cutoff,))
        for row in cursor.fetchall():
            picks.append({
                'source_table': 'miracle_picks3',
                'source_id': row[0],
                'ticker': row[1],
                'algorithm': row[2] if row[2] else 'Unknown',
                'pick_date': row[3],
                'entry_price': float(row[4]) if row[4] else None,
                'direction': row[5] if row[5] else 'LONG',
                'strength': int(row[6]) if row[6] else 70,
                'rationale': row[7] if row[7] else '',
                'asset_class': 'STOCK'
            })
    except mysql.connector.Error as e:
        print(f"miracle_picks3 query error: {e}")

    return picks


def is_already_bridged(cursor, source_table, source_id):
    """Check if a pick has already been bridged to a signal."""
    cursor.execute(
        "SELECT id FROM lm_picks_bridge WHERE source_table = %s AND source_id = %s",
        (source_table, source_id)
    )
    return cursor.fetchone() is not None


def create_signal(cursor, pick, algo_config):
    """Insert a signal into lm_signals and return the signal_id."""
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    expires = (datetime.utcnow() + timedelta(hours=algo_config['hold'])).strftime('%Y-%m-%d %H:%M:%S')

    # Build algorithm name with [Bridge] prefix for traceability
    algo_name = f"{pick['algorithm']} [Bridge]"

    signal_type = 'BUY' if pick['direction'] == 'LONG' else 'SELL'

    try:
        cursor.execute("""
            INSERT INTO lm_signals (
                asset_class, symbol, algorithm_name, signal_type, signal_strength,
                entry_price, target_tp_pct, target_sl_pct, max_hold_hours,
                timeframe, rationale, signal_time, expires_at, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
        """, (
            pick['asset_class'],
            pick['ticker'],
            algo_name,
            signal_type,
            pick['strength'],
            pick['entry_price'] or 0,
            algo_config['tp'],
            algo_config['sl'],
            algo_config['hold'],
            'daily',
            f"Bridged from {pick['source_table']} #{pick['source_id']}. "
            f"Backtest grade: {algo_config['grade']}, Sharpe: {algo_config['sharpe']}. "
            f"{pick['rationale'][:200] if pick['rationale'] else ''}",
            now,
            expires
        ))
        return cursor.lastrowid
    except mysql.connector.Error as e:
        print(f"  Signal insert error for {pick['ticker']}: {e}")
        return None


def bridge_pick(cursor, pick, algo_config, dry_run=False):
    """Bridge a single pick: create signal + log bridge entry."""
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    if dry_run:
        print(f"  [DRY RUN] Would bridge {pick['source_table']}#{pick['source_id']}: "
              f"{pick['ticker']} {pick['direction']} via {pick['algorithm']} "
              f"(Grade {algo_config['grade']}, Sharpe {algo_config['sharpe']})")
        return True

    signal_id = create_signal(cursor, pick, algo_config)
    if not signal_id:
        return False

    # Log bridge entry
    try:
        cursor.execute("""
            INSERT INTO lm_picks_bridge (
                source_table, source_id, signal_id, algorithm_name,
                ticker, pick_date, direction, entry_price,
                tp_pct, sl_pct, max_hold_hours, status, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'bridged', %s)
        """, (
            pick['source_table'],
            pick['source_id'],
            signal_id,
            pick['algorithm'],
            pick['ticker'],
            pick['pick_date'],
            pick['direction'],
            pick['entry_price'],
            algo_config['tp'],
            algo_config['sl'],
            algo_config['hold'],
            now
        ))
        return True
    except mysql.connector.Error as e:
        print(f"  Bridge log error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Bridge daily stock picks to live signal engine')
    parser.add_argument('--dry-run', action='store_true', help='Preview without inserting')
    parser.add_argument('--days', type=int, default=1, help='Look back N days for picks')
    parser.add_argument('--force-all', action='store_true', help='Include C/D grade algorithms')
    args = parser.parse_args()

    print(f"=== Bridge Picks to Signals ===")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Lookback: {args.days} day(s)")
    print(f"Force all grades: {args.force_all}")
    print()

    conn = get_db_connection()
    cursor = conn.cursor()

    ensure_bridge_table(cursor)
    conn.commit()

    # Fetch recent picks
    picks = fetch_recent_stock_picks(cursor, args.days)
    print(f"Found {len(picks)} recent picks across all tables")

    # Filter and bridge
    bridged = 0
    skipped_algo = 0
    skipped_dup = 0
    skipped_disabled = 0
    errors = 0

    for pick in picks:
        algo = pick['algorithm']

        # Check if algorithm is in our map
        if algo not in ALGO_MAP:
            skipped_algo += 1
            continue

        config = ALGO_MAP[algo]

        # Check if enabled (skip D-grade unless --force-all)
        if not config['enabled'] and not args.force_all:
            skipped_disabled += 1
            continue

        # Check if already bridged
        if is_already_bridged(cursor, pick['source_table'], pick['source_id']):
            skipped_dup += 1
            continue

        # Bridge it
        ok = bridge_pick(cursor, pick, config, dry_run=args.dry_run)
        if ok:
            bridged += 1
            print(f"  Bridged: {pick['ticker']} via {algo} ({config['grade']}) "
                  f"from {pick['source_table']}#{pick['source_id']}")
        else:
            errors += 1

    if not args.dry_run:
        conn.commit()

    print()
    print(f"=== Summary ===")
    print(f"Total picks found:    {len(picks)}")
    print(f"Bridged to signals:   {bridged}")
    print(f"Skipped (unknown):    {skipped_algo}")
    print(f"Skipped (disabled):   {skipped_disabled}")
    print(f"Skipped (duplicate):  {skipped_dup}")
    print(f"Errors:               {errors}")
    print()

    # Print enabled algorithms
    print("=== Enabled Algorithms ===")
    for name, cfg in sorted(ALGO_MAP.items()):
        status = "ENABLED" if cfg['enabled'] else "DISABLED"
        print(f"  {name:25s} Grade {cfg['grade']:3s} Sharpe {cfg['sharpe']:6.2f}  [{status}]")

    cursor.close()
    conn.close()
    print("\nDone.")


if __name__ == '__main__':
    main()
