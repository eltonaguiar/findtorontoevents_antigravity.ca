import sqlite3

conn = sqlite3.connect(r"e:\findtorontoevents_antigravity.ca\KIMI_RISEOFTHECLAW\data\kimi_trading.db")
cur = conn.cursor()

# Get picks table columns
cur.execute("PRAGMA table_info(picks)")
cols = cur.fetchall()
print("picks columns:", [c[1] for c in cols])

# Get signal table columns
cur.execute("PRAGMA table_info(signals)")
cols = cur.fetchall()
print("signals columns:", [c[1] for c in cols])

# Open picks by algorithm
cur.execute("SELECT algorithm, COUNT(*) FROM picks WHERE status='OPEN' GROUP BY algorithm ORDER BY COUNT(*) DESC LIMIT 30")
print("\nOpen picks by algorithm:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

# Open picks by symbol
cur.execute("SELECT symbol, COUNT(*) FROM picks WHERE status='OPEN' GROUP BY symbol ORDER BY COUNT(*) DESC LIMIT 20")
print("\nOpen picks by symbol:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

# Open picks age
cur.execute("SELECT MIN(entry_date), MAX(entry_date) FROM picks WHERE status='OPEN'")
dates = cur.fetchone()
print(f"\nOldest open pick: {dates[0]}")
print(f"Newest open pick: {dates[1]}")

# Check if any open picks have NULL exit-related data
cur.execute("SELECT COUNT(*) FROM picks WHERE status='OPEN' AND exit_price IS NULL")
null_exit = cur.fetchone()[0]
print(f"\nOpen picks with NULL exit_price: {null_exit}")

# Check entry_date distribution
cur.execute("SELECT entry_date, COUNT(*) FROM picks WHERE status='OPEN' GROUP BY entry_date ORDER BY entry_date")
print("\nOpen picks by entry_date:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

conn.close()
