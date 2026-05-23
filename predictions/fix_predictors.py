"""Fix missing predictor entries for Reddit and other sources"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "data" / "predictions.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== Fixing Missing Predictor Entries ===\n")

# Find all predictions without predictor entries
cursor.execute('''
    SELECT DISTINCT p.predictor_id, p.platform
    FROM predictions p
    LEFT JOIN predictors pred ON p.predictor_id = pred.predictor_id
    WHERE pred.predictor_id IS NULL
''')

missing = cursor.fetchall()
print(f"Found {len(missing)} predictors missing from predictors table\n")

for row in missing:
    predictor_id = row['predictor_id']
    platform = row['platform']
    # Extract display name from predictor_id
    display_name = predictor_id.split(':')[-1].replace('u/', '')
    
    # Count predictions for this predictor
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN outcome_pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome_pnl_pct < 0 THEN 1 ELSE 0 END) as losses,
            AVG(outcome_pnl_pct) as avg_pnl
        FROM predictions
        WHERE predictor_id = ? AND status != 'PENDING'
    ''', (predictor_id,))
    
    stats = cursor.fetchone()
    
    # Insert into predictors table
    cursor.execute('''
        INSERT OR REPLACE INTO predictors 
        (predictor_id, platform, display_name, total_predictions, wins, losses, 
         win_rate, avg_pnl_pct, first_seen, last_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    ''', (
        predictor_id,
        platform,
        display_name,
        stats['total'] or 0,
        stats['wins'] or 0,
        stats['losses'] or 0,
        (stats['wins'] or 0) / (stats['total'] or 1),
        stats['avg_pnl'] or 0
    ))
    
    print(f"  + {predictor_id[:40]:40} | {stats['total'] or 0} picks")

conn.commit()

# Now export
cursor.execute('SELECT COUNT(*) FROM predictors')
print(f"\nTotal predictors after fix: {cursor.fetchone()[0]}")

cursor.execute('''
    SELECT platform, COUNT(*) FROM predictors GROUP BY platform
''')
print("\nBy platform:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
print("\n✓ Fixed! Run export to update dashboard.")
