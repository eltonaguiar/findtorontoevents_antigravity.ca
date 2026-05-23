import sqlite3
import json

# Check database
conn = sqlite3.connect('predictions/data/predictions.db')
cursor = conn.cursor()

print("=== ACTIVE PREDICTIONS BY SOURCE ===")
cursor.execute("SELECT platform, COUNT(*) FROM predictions WHERE status = 'ACTIVE' GROUP BY platform ORDER BY COUNT(*) DESC")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

print("\n=== EXPORTED JSON ===")
with open('predictions/data/leaderboard.json') as f:
    data = json.load(f)

print(f"Leaderboard: {len(data['leaderboard'])} predictors")
print(f"Active predictions: {len(data['active_predictions'])}")

by_platform = {}
for p in data['active_predictions']:
    plat = p.get('platform', 'unknown')
    by_platform[plat] = by_platform.get(plat, 0) + 1

print("\nBy platform in export:")
for plat, count in sorted(by_platform.items(), key=lambda x: -x[1]):
    print(f"  {plat}: {count}")

print("\n=== SAMPLE POLYMARKET PREDICTIONS ===")
cursor.execute("SELECT symbol, direction, take_profit, source_url FROM predictions WHERE platform = 'polymarket' AND status = 'ACTIVE' LIMIT 3")
for row in cursor.fetchall():
    print(f"  {row[0]} {row[1]} | TP: {row[2]} | {row[3][:60]}...")

conn.close()
