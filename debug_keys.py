import json
DASHBOARD_DATA_PATH = r'e:\findtorontoevents_antigravity.ca\audit_dashboard\data\dashboard_data.json'
with open(DASHBOARD_DATA_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

for k in ['picks', 'performance', 'leaderboard', 'summary']:
    if k in data:
        print(f"Key '{k}' type: {type(data[k])}")
        if isinstance(data[k], dict):
            print(f"  Sub-keys: {list(data[k].keys())[:20]}")
        elif isinstance(data[k], list):
            print(f"  Length: {len(data[k])}")
            if data[k]:
                print(f"  First item type: {type(data[k][0])}")
