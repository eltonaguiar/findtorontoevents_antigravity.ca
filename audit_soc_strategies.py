#!/usr/bin/env python3
"""
Audit for crypto_soc_* strategies - investigate single-trade entries
"""

import sqlite3
import json
from pathlib import Path
from collections import defaultdict

# Check the main trading database
db_path = 'KIMI_RISEOFTHECLAW/data/kimi_trading.db'

print("=" * 80)
print("SOC STRATEGY AUDIT")
print("=" * 80)

if not Path(db_path).exists():
    print(f"Database not found: {db_path}")
    # List what databases exist
    dbs = list(Path('.').rglob('*.db'))
    dbs = [d for d in dbs if 'Temp' not in str(d)]
    print(f"Found {len(dbs)} databases:")
    for d in dbs[:10]:
        print(f"  {d}")
    exit()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print(f"\nDatabase: {db_path}")
print(f"Tables: {tables}")

# Search for SOC strategies in each table
for table in tables:
    try:
        cursor.execute(f'PRAGMA table_info({table})')
        cols = [col[1] for col in cursor.fetchall()]
        
        # Check for strategy/signal_name/name columns
        search_cols = [c for c in cols if c in ['strategy', 'signal_name', 'name', 'strategy_name']]
        
        for col in search_cols:
            try:
                cursor.execute(f"SELECT {col}, COUNT(*) FROM {table} WHERE {col} LIKE '%soc%' GROUP BY {col}")
                rows = cursor.fetchall()
                if rows:
                    print(f"\n[{table}.{col}] Found SOC strategies:")
                    for row in rows:
                        print(f"  - {row[0]}: {row[1]} entries")
            except:
                pass
                
        # Also check for drawdown strategies
        for col in search_cols:
            try:
                cursor.execute(f"SELECT {col}, COUNT(*) FROM {table} WHERE {col} LIKE '%drawdown%' GROUP BY {col}")
                rows = cursor.fetchall()
                if rows:
                    print(f"\n[{table}.{col}] Found drawdown strategies:")
                    for row in rows:
                        print(f"  - {row[0]}: {row[1]} entries")
            except:
                pass
                    
    except Exception as e:
        pass

conn.close()

print("\n" + "=" * 80)
print("Searching other databases...")
print("=" * 80)

other_dbs = [
    'battleground/data/bundle_babies.db',
    'incubator/forward_test.db',
]

for db_path in other_dbs:
    if not Path(db_path).exists():
        continue
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]
        
        for table in tables:
            try:
                cursor.execute(f'SELECT * FROM {table} LIMIT 1')
                cols = [desc[1] for desc in cursor.description]
                
                if 'strategy' in cols:
                    cursor.execute(f"SELECT strategy, COUNT(*) FROM {table} WHERE strategy LIKE '%soc%' GROUP BY strategy")
                    rows = cursor.fetchall()
                    if rows:
                        print(f"\n[{db_path}::{table}] Found:")
                        for row in rows:
                            print(f"  - {row[0]}: {row[1]} entries")
            except:
                pass
        
        conn.close()
    except Exception as e:
        print(f"Error with {db_path}: {e}")
