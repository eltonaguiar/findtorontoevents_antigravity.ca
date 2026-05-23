import json

d = json.load(open('audit_trail/data/dashboard_payload.json'))

# Check all systems
print("=== ALL SYSTEMS ===")
for s in d['systems']:
    print(f"  {s['id']}: active={s.get('active_count', 0)}, closed={s.get('closed_count', 0)}")

# Check specifically for prop_firm
print("\n=== PROP_FIRM_STRATEGIES ===")
for s in d['systems']:
    if s.get('id') == 'prop_firm_strategies':
        print(f"Found: {s}")
