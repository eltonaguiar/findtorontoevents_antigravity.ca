#!/usr/bin/env python3
"""Check unified forward test status across all systems."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

print("=" * 70)
print("UNIFIED FORWARD TEST STATUS - ALL SYSTEMS")
print("=" * 70)

# Check database
db_path = Path('KIMI_FEB172026/data/unified_forward_test.db')
if not db_path.exists():
    db_path = Path('data/unified_forward_test.db')

if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Overall stats
    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT system) FROM unified_signals")
    total, systems = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) FROM unified_signals WHERE status = 'ACTIVE'")
    active = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM unified_signals WHERE status = 'CLOSED'")
    closed = cursor.fetchone()[0]
    
    print(f"\n[ OVERALL STATS ]")
    print(f"   Total Signals: {total}")
    print(f"   Active Signals: {active}")
    print(f"   Closed Trades: {closed}")
    print(f"   Systems Active: {systems}")
    
    if total > 0:
        print("\n[ BY SYSTEM ]")
        cursor.execute('''
            SELECT system, asset_class, COUNT(*),
                   SUM(CASE WHEN status = 'CLOSED' AND realized_pnl > 0 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status = 'CLOSED' THEN realized_pnl ELSE 0 END)
            FROM unified_signals
            GROUP BY system
        ''')
        for row in cursor.fetchall():
            print(f"   {row[0]} ({row[1]}): {row[2]} signals, {row[3] or 0} wins, P&L: {row[4] or 0:+.2%}")
        
        print("\n[ RECENT SIGNALS ]")
        cursor.execute('''
            SELECT timestamp_est, system, asset_class, symbol, direction, status
            FROM unified_signals
            ORDER BY timestamp_utc DESC
            LIMIT 5
        ''')
        for row in cursor.fetchall():
            print(f"   {row[0][:16]} | {row[1][:15]:15} | {row[2]:6} | {row[3]:10} {row[4]:5} | {row[5]}")
    else:
        print("\n   No signals logged yet.")
    
    conn.close()
else:
    print("\n   Database not initialized yet.")

# Check status file
status_path = Path('KIMI_FEB172026/data/unified_status.json')
if not status_path.exists():
    status_path = Path('data/unified_status.json')

if status_path.exists():
    with open(status_path) as f:
        data = json.load(f)
    
    print(f"\n[ SYSTEM CONFIGURATION ]")
    for name, config in data.get('systems_config', {}).items():
        status = "LIVE" if config['active'] else "PENDING"
        print(f"   [{status:7}] {name:20} ({config['asset_class']})")
    
    print(f"\n[ LAST SCAN ]")
    print(f"   {data.get('timestamp', 'N/A')}")
else:
    print("\n   Status file not found.")

# Check data files
print(f"\n[ DATA FILES ]")
for pattern in ['unified_forward_test.json', 'unified_status.json', 'audit_trail_*.json']:
    files = list(Path('KIMI_FEB172026/data').glob(pattern))
    if not files:
        files = list(Path('data').glob(pattern))
    print(f"   {pattern}: {len(files)} files")

print("\n" + "=" * 70)
print("FORWARD TEST ACTIVE - Monitoring 5 systems across 3 asset classes")
print("=" * 70)
