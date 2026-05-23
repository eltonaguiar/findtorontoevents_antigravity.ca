import requests
import json
response = requests.get('https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/audit_dashboard/data/claudes_test_state.json')
d = response.json()
bad = []
for pname, p in d.items():
    for t in p.get('positions', []) + p.get('closed', []):
        sym = t.get('symbol', '')
        entry = t.get('entry_price', 0)
        pnl = t.get('pnl_pct', 0)
        if ('DOGE' in sym and entry > 1) or ('AVAX' in sym and entry > 50) or ('JNJ' in sym and entry > 500) or ('TRX' in sym and entry < 0.1) or entry > 100000 or entry < 0.000001 or abs(pnl) > 80:
            bad.append(f'{sym} entry={entry:.4f} pnl={pnl:.1f}% in {pname}')
print('BAD TRADES:', len(bad))
if bad:
    print(bad[:10])
print('\\nMomentum Riders:', d.get('momentum_riders', {}).get('equity', 'N/A'), d.get('momentum_riders', {}).get('positions', []))
print('High Conviction:', d.get('high_conviction', {}).get('equity', 'N/A'))
print('Total portfolios:', len(d))
for pname in ['rsi_capitulation', 'contrarian', 'prop_aggressive']:
    p = d.get(pname, {})
    eq = p.get('equity', 0)
    print(f'{pname}: eq={eq}')