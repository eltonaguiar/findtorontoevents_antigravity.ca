import sqlite3
from pathlib import Path

db_path = Path(r"e:\findtorontoevents_antigravity.ca\alpha_engine\data\alpha.db")
if not db_path.exists():
    print(f"Database not found: {db_path}")
    exit()

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f"Tables: {tables}")

for table in tables:
    cur.execute(f"SELECT COUNT(*) as c FROM {table}")
    print(f"  {table}: {cur.fetchone()[0]} rows")

# Open picks
if 'picks' in tables:
    cur.execute("SELECT COUNT(*) FROM picks WHERE status='OPEN'")
    open_count = cur.fetchone()[0]
    print(f"\nOPEN picks in SQLite: {open_count}")

    cur.execute("SELECT status, COUNT(*) as c FROM picks GROUP BY status ORDER BY c DESC")
    for row in cur.fetchall():
        print(f"  Status '{row[0]}': {row[1]}")

    # KIMI specific
    cur.execute("SELECT COUNT(*) FROM picks WHERE strategy LIKE '%kimi%' AND status='OPEN'")
    kimi_open = cur.fetchone()[0]
    print(f"\nKIMI open picks: {kimi_open}")

    cur.execute("SELECT COUNT(*) FROM picks WHERE strategy LIKE '%kimi%'")
    kimi_total = cur.fetchone()[0]
    print(f"KIMI total picks: {kimi_total}")

# Signals table
if 'signals' in tables:
    cur.execute("SELECT COUNT(*) FROM signals")
    sig_count = cur.fetchone()[0]
    print(f"\nTotal signals recorded: {sig_count}")

    cur.execute("SELECT strategy, COUNT(*) as c FROM signals GROUP BY strategy ORDER BY c DESC LIMIT 20")
    print("\nTop 20 strategies by signal count:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")

conn.close()

# Also check paper_trading db
paper_db = Path(r"e:\findtorontoevents_antigravity.ca\paper_trading\data\paper.db")
if paper_db.exists():
    print("\n" + "=" * 60)
    print("PAPER TRADING DATABASE")
    print("=" * 60)
    conn2 = sqlite3.connect(str(paper_db))
    conn2.row_factory = sqlite3.Row
    cur2 = conn2.cursor()
    
    cur2.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables2 = [r[0] for r in cur2.fetchall()]
    print(f"Tables: {tables2}")
    
    for t in tables2:
        cur2.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"  {t}: {cur2.fetchone()[0]} rows")
    
    if 'positions' in tables2:
        cur2.execute("SELECT status, COUNT(*) FROM positions GROUP BY status ORDER BY COUNT(*) DESC")
        print("\nPosition status breakdown:")
        for row in cur2.fetchall():
            print(f"  {row[0]}: {row[1]}")
        
        cur2.execute("SELECT COUNT(*) FROM positions WHERE status='ACTIVE'")
        active = cur2.fetchone()[0]
        print(f"\nACTIVE positions: {active}")
        
        # KIMI positions
        cur2.execute("SELECT COUNT(*) FROM positions WHERE strategy_name LIKE '%kimi%' AND status='ACTIVE'")
        kimi_active = cur2.fetchone()[0]
        print(f"KIMI active positions: {kimi_active}")
        
        cur2.execute("SELECT COUNT(*) FROM positions WHERE strategy_name LIKE '%kimi%'")
        kimi_total = cur2.fetchone()[0]
        print(f"KIMI total positions: {kimi_total}")
    
    conn2.close()
