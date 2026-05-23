import json

d = json.load(open('audit_trail/data/dashboard_payload.json'))

# Check specifically for prop_firm
for s in d['systems']:
    if s.get('name') == 'prop_firm_strategies':
        print("=== PROP_FIRM_STRATEGIES SYSTEM ===")
        for k, v in s.items():
            print(f"  {k}: {v}")
