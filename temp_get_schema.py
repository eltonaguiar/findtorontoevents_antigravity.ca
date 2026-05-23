import sqlite3

dbs = [
    'E:/findtorontoevents_antigravity.ca/data/audit_trail.db',
    'E:/findtorontoevents_antigravity.ca/KIMI_RISEOFTHECLAW/data/kimi_trading.db',
    'E:/findtorontoevents_antigravity.ca/genome/strategy_registry.db'
]

with open('E:/findtorontoevents_antigravity.ca/temp_schemas.txt', 'w') as f:
    for db in dbs:
        f.write(f"\n--- Schema for {db} ---\n")
        try:
            conn = sqlite3.connect(db)
            cur = conn.cursor()
            cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
            for row in cur.fetchall():
                f.write(f"Table: {row[0]}\n")
                f.write(str(row[1]) + "\n")
            conn.close()
        except Exception as e:
            f.write(f"Error: {e}\n")
