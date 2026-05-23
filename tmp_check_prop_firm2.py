import json

d = json.load(open('audit_trail/data/dashboard_payload.json'))

# Check systems for prop firm
print("=== SYSTEMS WITH 'prop' ===")
for s in d['systems']:
    if 'prop' in s.get('id', '').lower():
        print(f"Found system: {s['id']} - active: {s.get('active_count', 0)} closed: {s.get('closed_count', 0)}")

# Check active picks for prop_firm_strategies
pf_picks = [p for p in d['picks']['active'] if p.get('source_system') == 'prop_firm_strategies']
print(f"\n=== ACTIVE PROP FIRM PICKS: {len(pf_picks)} ===")
for p in pf_picks[:5]:
    print(f"  {p['symbol']}: {p['direction']} via {p.get('strategy', 'unknown')}")
