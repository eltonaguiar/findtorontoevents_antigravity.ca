import sqlite3

conn = sqlite3.connect('data/audit_trail.db')
cursor = conn.cursor()

# Get tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print("Tables in audit_trail.db:")
for t in tables:
    print(f"  - {t}")

# Check raw_picks table structure
if 'raw_picks' in tables:
    print("\n=== RAW_PICKS SCHEMA ===")
    cursor.execute("PRAGMA table_info(raw_picks)")
    for col in cursor.fetchall():
        print(f"  {col[1]} ({col[2]})")
    
    # Count records
    cursor.execute("SELECT COUNT(*) FROM raw_picks")
    print(f"\nTotal raw_picks: {cursor.fetchone()[0]}")
    
    # Check for status column values
    cursor.execute("SELECT status, COUNT(*) FROM raw_picks GROUP BY status")
    print("\nStatus distribution:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    # Strategy performance
    print("\n=== STRATEGY PERFORMANCE (5+ closed picks) ===")
    cursor.execute("""
        SELECT source_system, strategy, 
               COUNT(*) as total_picks,
               SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN status='LOST' THEN 1 ELSE 0 END) as losses,
               ROUND(AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END), 2) as avg_pnl,
               ROUND(SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END) * 100.0 / 
                     NULLIF(SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END), 0), 1) as win_rate
        FROM raw_picks
        WHERE status IN ('WON', 'LOST')
        GROUP BY source_system, strategy
        HAVING total_picks >= 5
        ORDER BY win_rate DESC, total_picks DESC
    """)
    
    for row in cursor.fetchall():
        print(f"{row[0]:25} | {row[1]:35} | Picks: {row[2]:3} | Wins: {row[3]:3} | Losses: {row[4]:3} | WR: {row[6]}% | Avg PnL: {row[5]}%")

conn.close()
