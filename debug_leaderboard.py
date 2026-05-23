import json
DASHBOARD_DATA_PATH = r'e:\findtorontoevents_antigravity.ca\audit_dashboard\data\dashboard_data.json'
with open(DASHBOARD_DATA_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

if 'leaderboard' in data and data['leaderboard']:
    print(f"Leaderboard item 0: {json.dumps(data['leaderboard'][0], indent=2)}")
