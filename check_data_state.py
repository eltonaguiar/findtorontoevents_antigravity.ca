import json
import os
import glob
from pathlib import Path
from datetime import datetime

# 1. Check GH runs
try:
    with open("temp_gh_runs.json", "r") as f:
        runs = json.load(f)
    print("=== FAILING GITHUB ACTIONS (No subsequent success) ===")
    
    # Sort by createdAt descending
    runs.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
    
    workflow_status = {}
    for run in runs:
        name = run.get('name')
        status = run.get('status')
        conclusion = run.get('conclusion')
        url = run.get('url')
        createdAt = run.get('createdAt')
        
        if name not in workflow_status:
            workflow_status[name] = {"latest_conclusion": conclusion, "runs": []}
        
        workflow_status[name]["runs"].append(run)
        
    for name, data in workflow_status.items():
        if data["latest_conclusion"] in ["failure", "cancelled"]:
            print(f"- Workflow: {name}")
            print(f"  Latest Run: {data['latest_conclusion']} at {data['runs'][0].get('createdAt')} ({data['runs'][0].get('url')})")
            
except Exception as e:
    print(f"Error checking GH runs: {e}")

# 2. Check Data Payloads (orphaned or low fields)
print("\n=== DATA PAYLOADS & FEEDS (Low Rows or Incomplete Fields) ===")
def check_json_payloads(dir_path):
    if not os.path.exists(dir_path): return
    for fpath in glob.glob(os.path.join(dir_path, "*.json")):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if isinstance(data, list):
                rows = len(data)
                # Check fields in first row
                keys = list(data[0].keys()) if rows > 0 and isinstance(data[0], dict) else []
                empty_fields_count = 0
                if rows > 0 and isinstance(data[0], dict):
                    for k, v in data[0].items():
                        if v in [None, "", []]: empty_fields_count += 1
                        
                if rows < 5 or empty_fields_count > len(keys)*0.3:
                    print(f"- [WARN] {os.path.basename(fpath)}: {rows} rows. First row keys: {keys}. Missing fields: {empty_fields_count}/{len(keys)}")
            elif isinstance(data, dict):
                print(f"- [INFO] {os.path.basename(fpath)}: Dict with keys: {list(data.keys())[:5]}")
        except Exception as e:
            print(f"- [ERROR] {os.path.basename(fpath)}: Cannot parse JSON: {e}")

print("Checking root data dir...")
check_json_payloads("data")
print("Checking predictions/data dir...")
check_json_payloads("predictions/data")

# 3. Check for specific orphaned payloads not integrated to audit
print("\n=== ORPHANED PAYLOADS TO INTEGRATE (Not fully bridged to /audit) ===")
print("Looking files with 'audit' or 'payload' in name not linked...")
# Let's inspect some known paths based on directory listings...
