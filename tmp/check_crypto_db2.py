import sqlite3
conn = sqlite3.connect('crypto_data.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(klines)")
print('Klines schema:')
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")
cursor.execute('SELECT DISTINCT symbol FROM klines LIMIT 15')
print('\nSample symbols:', [s[0] for s in cursor.fetchall()])
cursor.execute('SELECT COUNT(*) FROM klines')
print('Total rows:', cursor.fetchone()[0])
cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM klines')
print('Date range:', cursor.fetchone())
conn.close()
