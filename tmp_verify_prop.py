import json

d = json.load(open('audit_trail/data/dashboard_payload.json'))

# Check for prop_firm_strategies
for s in d['systems']:
    if s.get('name') == 'prop_firm_strategies':
        print("[OK] PROP_FIRM_STRATEGIES FOUND IN DASHBOARD")
        print(f"  Active picks: {s.get('active_picks', 0)}")
        print(f"  Closed picks: {s.get('closed_picks', 0)}")
        print(f"  Status: {s.get('status', 'unknown')}")
        break
else:
    print("[MISSING] PROP_FIRM_STRATEGIES NOT FOUND")
