import sqlite3
conn = sqlite3.connect('predictions/data/predictions.db')
cursor = conn.cursor()

print('=== Polymarket Predictions ===')
cursor.execute("SELECT COUNT(*), status FROM predictions WHERE platform = 'polymarket' GROUP BY status")
for row in cursor.fetchall():
    print(f'  Status {row[1]}: {row[0]}')

print('\n=== Sample Polymarket Predictions ===')
cursor.execute('''
    SELECT predictor_id, symbol, direction, status, scraped_at, source_url 
    FROM predictions 
    WHERE platform = 'polymarket'
    ORDER BY scraped_at DESC
    LIMIT 10
''')
for row in cursor.fetchall():
    print(f'{row[0][:30]:30} | {row[1]:8} | {row[2]:5} | {row[3]:8} | {row[4]}')

print('\n=== All Platforms - Total vs Active ===')
cursor.execute('''
    SELECT platform, 
           COUNT(*) as total,
           SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) as active
    FROM predictions 
    GROUP BY platform
    ORDER BY total DESC
''')
for row in cursor.fetchall():
    print(f'{row[0]:15} | Total: {row[1]:4} | Active: {row[2]:4}')

conn.close()
