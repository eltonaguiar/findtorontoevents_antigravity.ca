#!/usr/bin/env python3
"""Check predictors and predictions tables.
Usage: python check_predictors.py [--db PATH]"""
import argparse
import sqlite3
from pathlib import Path

parser = argparse.ArgumentParser(description="Check predictors table")
parser.add_argument("--db", default=None, help="Path to predictions.db (default: predictions/data/predictions.db)")
args = parser.parse_args()

if args.db:
    db_path = args.db
else:
    db_path = str(Path(__file__).resolve().parent.parent / "predictions" / "data" / "predictions.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print('=== Predictors Table ===')
cursor.execute('SELECT COUNT(*) FROM predictors')
print(f'Total predictors: {cursor.fetchone()[0]}')

cursor.execute('''
    SELECT predictor_id, platform, total_predictions, wins, losses
    FROM predictors
    ORDER BY total_predictions DESC
    LIMIT 15
''')
for row in cursor.fetchall():
    print(f'  {row[0][:40]:40} | {row[1]:10} | {row[2]} picks | WR: {row[3]}/{row[4]}')

print('\n=== Predictions without Predictor entry ===')
cursor.execute('''
    SELECT p.platform, p.predictor_id, COUNT(*)
    FROM predictions p
    LEFT JOIN predictors pred ON p.predictor_id = pred.predictor_id
    WHERE pred.predictor_id IS NULL
    GROUP BY p.platform
    ORDER BY COUNT(*) DESC
''')
orphans = cursor.fetchall()
if orphans:
    for row in orphans:
        print(f'  {row[0]}: {row[1][:30]} - {row[2]} predictions')
else:
    print('  All predictions have predictor entries')

conn.close()
