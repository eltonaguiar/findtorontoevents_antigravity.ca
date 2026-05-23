import json

d = json.load(open('audit_trail/data/dashboard_payload.json'))

# Check all systems
print("=== ALL SYSTEMS ===")
for s in d['systems']:
    print(f"  Keys: {list(s.keys())}")
    break

# Check first few
for s in d['systems'][:10]:
    print(f"  {s.get('name', 'NO_NAME')}: active={s.get('active_count', 0)}, closed={s.get('closed_count', 0)}")

# Check specifically for prop_firm
print("\n=== PROP_FIRM_STRATEGIES ===")
for s in d['systems']:
    if 'prop' in str(s).lower():
        print(f"Found: {s.get('name', 'UNKNOWN')}")
