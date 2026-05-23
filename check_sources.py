import sqlite3
conn = sqlite3.connect('predictions/data/predictions.db')
cursor = conn.cursor()

print('=== Sample Predictions by Source ===')
cursor.execute('''
    SELECT platform, predictor_id, symbol, direction, source_url 
    FROM predictions 
    WHERE status = 'ACTIVE'
    ORDER BY platform, predictor_id
    LIMIT 20
''')
for row in cursor.fetchall():
    url = row[4][:50] if row[4] else 'N/A'
    print(f'{row[0]:12} | {row[1][:30]:30} | {row[2]:8} | {row[3]:5} | {url}...')

print('\n=== Platform Breakdown ===')
cursor.execute("SELECT platform, COUNT(*) FROM predictions WHERE status = 'ACTIVE' GROUP BY platform ORDER BY COUNT(*) DESC")
for row in cursor.fetchall():
    print(f'{row[0]:15} | {row[1]:4} active')

print('\n=== Polymarket Predictors ===')
cursor.execute("SELECT DISTINCT predictor_id FROM predictions WHERE platform = 'polymarket' LIMIT 10")
for row in cursor.fetchall():
    print(f'  {row[0]}')

conn.close()
