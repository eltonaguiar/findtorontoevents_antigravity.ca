import json
import os
import glob

# 1. GH Actions
try:
    with open("temp_gh_runs.json", "r", encoding="utf-8") as f:
        runs = json.load(f)
    print("=== FAILING GITHUB ACTIONS ===")
    runs.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
    workflow_status = {}
    for run in runs:
        name = run.get('name')
        if name not in workflow_status:
            workflow_status[name] = {"latest_conclusion": run.get('conclusion'), "runs": []}
        workflow_status[name]["runs"].append(run)
    
    for name, data in workflow_status.items():
        if data["latest_conclusion"] in ["failure", "cancelled"]:
            print(f"- {name}: {data['latest_conclusion']} at {data['runs'][0].get('createdAt')} ({data['runs'][0].get('url')})")
except Exception as e:
    print(f"Error reading GH runs: {e}")

# 2. Incomplete / Low Fields Payloads
def check_json(p):
    if not os.path.exists(p): return
    for fpath in glob.glob(os.path.join(p, "*.json")):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if isinstance(data, list):
                rows = len(data)
                if rows == 0:
                    print(f"[EMPTY] {fpath}")
                    continue
                first = data[0] if isinstance(data[0], dict) else {}
                keys = list(first.keys())
                empty = sum(1 for v in first.values() if v in [None, "", []])
                
                print(f"[DATA] {fpath}: {rows} rows. First row missing {empty}/{len(keys)} fields.")
                if rows < 5:
                    print(f"  -> Low row count ({rows})")
            elif isinstance(data, dict):
                print(f"[DICT] {fpath}: {len(data.keys())} keys")
        except Exception as e:
            pass

print("\n=== PAYLOADS ANALYSIS ===")
check_json("data")
check_json("predictions/data")
