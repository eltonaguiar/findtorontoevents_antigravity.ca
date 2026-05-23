import sqlite3
import pandas as pd
import glob
import os

dbs = [
    'KIMI_RISEOFTHECLAW/data/kimi_trading.db',
    'data/audit_trail.db',
    'genome/genetic_programmer.db',
    'data/live_picks.db',
    'coinglass_strategies/data/coinglass.db',
    'audit_dashboard/data/trading_history.db'
]

for db_path in dbs:
    full_path = f"e:/findtorontoevents_antigravity.ca/{db_path}"
    if not os.path.exists(full_path):
        continue
    
    print(f"\n--- Checking {db_path} ---")
    try:
        conn = sqlite3.connect(full_path)
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)['name'].tolist()
        print(f"Tables: {tables}")
        
        for table in tables:
            try:
                df = pd.read_sql(f"SELECT * FROM {table} LIMIT 1", conn)
                cols = df.columns.tolist()
                
                # Look for PnL related columns
                pnl_cols = [c for c in cols if 'pnl' in c.lower() or 'profit' in c.lower() or 'return' in c.lower()]
                if pnl_cols:
                    print(f"  Table '{table}' has PnL columns: {pnl_cols}")
                    
                    # Try to get average PnL if possible
                    try:
                        stats = pd.read_sql(f"SELECT COUNT(*) as count, AVG({pnl_cols[0]}) as avg_pnl FROM {table} WHERE {pnl_cols[0]} IS NOT NULL", conn)
                        print(f"    Total rows: {stats['count'].iloc[0]}, Avg PnL: {stats['avg_pnl'].iloc[0]}")
                    except Exception as e:
                        pass
            except Exception as e:
                pass
        conn.close()
    except Exception as e:
        print(f"Error reading {db_path}: {e}")
