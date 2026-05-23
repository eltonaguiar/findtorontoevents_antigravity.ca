import sqlite3
conn = sqlite3.connect('crypto_data.db')
cursor = conn.cursor()
cursor.execute('SELECT DISTINCT pair FROM klines LIMIT 20')
print('Available pairs:')
for row in cursor.fetchall():
    print(f"  {row[0]}")
cursor.execute('SELECT COUNT(*) FROM klines')
print(f'\nTotal rows: {cursor.fetchone()[0]:,}')
cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM klines')
min_ts, max_ts = cursor.fetchone()
print(f'Date range: {min_ts} to {max_ts}')
conn.close()
