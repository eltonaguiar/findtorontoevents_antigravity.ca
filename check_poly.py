import sqlite3
conn = sqlite3.connect('predictions/data/predictions.db')
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM predictors WHERE platform = 'polymarket'")
print(f'Polymarket predictors: {cursor.fetchone()[0]}')

cursor.execute("SELECT predictor_id, total_predictions FROM predictors WHERE platform = 'polymarket'")
for row in cursor.fetchall():
    print(f'  {row[0]} | {row[1]} picks')

conn.close()
