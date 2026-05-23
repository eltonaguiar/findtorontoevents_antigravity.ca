import sqlite3, json
db = 'audit_trail/data/audit_trail.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
try:
    res = conn.execute("SELECT symbol, SUM(pnl_pct) as pnl, COUNT(*) as n FROM trading_picks WHERE status IN ('CLOSED', 'WON', 'LOST', 'TP_HIT', 'SL_HIT', 'EXPIRED') GROUP BY symbol HAVING pnl < 0 ORDER BY pnl ASC").fetchall()
    print(f"Total net-negative symbols: {len(res)}")
    print(json.dumps([dict(r) for r in res[:20]], indent=2))
except Exception as e:
    # Try alternate table name if trading_picks fails
    try:
        res = conn.execute("SELECT symbol, SUM(pnl_pct) as pnl, COUNT(*) as n FROM raw_picks WHERE status IN ('CLOSED', 'WON', 'LOST', 'TP_HIT', 'SL_HIT', 'EXPIRED') GROUP BY symbol HAVING pnl < 0 ORDER BY pnl ASC").fetchall()
        print(f"(fallback table: raw_picks) Total net-negative symbols: {len(res)}")
        print(json.dumps([dict(r) for r in res[:20]], indent=2))
    except:
        print(f"Error: {e}")
