import json

with open('predictions/data/leaderboard.json') as f:
    data = json.load(f)

print(f"Updated: {data.get('updated_at')}")
print(f"Leaderboard entries: {len(data.get('leaderboard', []))}")
print(f"Active predictions: {len(data.get('active_predictions', []))}")

print('\n=== Leaderboard ===')
for p in data.get('leaderboard', [])[:10]:
    print(f"  {p.get('predictor_id', '')[:40]:40} | {p.get('total_predictions', 0)} picks")

print('\n=== Active by Platform ===')
from collections import Counter
platforms = [p.get('platform') for p in data.get('active_predictions', [])]
for platform, count in Counter(platforms).most_common():
    print(f'  {platform}: {count}')
