import json
import os

# Diagnostic script to check active picks count for discrepancy troubleshooting
# Path: e:\findtorontoevents_antigravity.ca\audit_dashboard\data\dashboard_data.json

try:
    with open(r'e:\findtorontoevents_antigravity.ca\audit_dashboard\data\dashboard_data.json', 'r') as f:
        data = json.load(f)

    active_picks = data.get('picks', {}).get('active', [])
    print(f"Total active picks: {len(active_picks)}")

    for p in active_picks:
        print(f"Symbol: {p.get('symbol')}, System: {p.get('source_system')}, Age: {p.get('age_hours')}, PnL: {p.get('pnl_pct')}, Trust: {p.get('trust_tier')}, Score: {p.get('score')}")
except Exception as e:
    print(f"Error reading dashboard data: {e}")
