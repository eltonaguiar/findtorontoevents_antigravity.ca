import json

fpath = r"e:\findtorontoevents_antigravity.ca\predictions\data\active_predictions.json"
try:
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data and isinstance(data, list):
        row = data[0]
        missing = [k for k, v in row.items() if v in [None, "", []]]
        present = [k for k, v in row.items() if v not in [None, "", []]]
        print("Missing fields:", missing)
        print("Present fields:", present)
except Exception as e:
    print("Error:", e)
