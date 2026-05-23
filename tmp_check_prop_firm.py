import json

d = json.load(open('audit_trail/data/dashboard_payload.json'))

# Find prop firm systems
pf = [s for s in d['systems'] if 'prop' in s.get('id','').lower()]
print('Prop firm systems:', pf)

# Count active prop firm picks
pf_picks = [p for p in d['active_picks'] if p.get('source_system') == 'prop_firm_strategies']
print(f'Active prop firm picks: {len(pf_picks)}')
for p in pf_picks[:5]:
    print(f"  {p['symbol']}: {p['direction']} via {p.get('strategy', 'unknown')}")
