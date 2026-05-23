import json
from datetime import datetime, timezone

json_path = r'e:\findtorontoevents_antigravity.ca\audit_dashboard\data\dashboard_data.json'
with open(json_path, 'r') as f:
    data = json.load(f)

active = data.get('picks', {}).get('active', [])
now = datetime.now(timezone.utc)

def get_age(ts_str):
    if not ts_str: return 999
    try:
        if not (ts_str.endswith('Z') or '+' in ts_str or '-' in ts_str[10:]):
            ts_str += 'Z'
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return (now - dt).total_seconds() / 3600
    except:
        return 999

print(f"Audit of {len(active)} picks:")
for p in active:
    sym = p.get('symbol')
    age = get_age(p.get('timestamp'))
    pnl = p.get('pnl_pct', 0)
    asset = (p.get('asset_class') or '').upper()
    sys = (p.get('source_system') or '').lower()
    
    max_age = 336 if asset in ['FOREX', 'EQUITY', 'COMMODITY', 'FUTURES', 'BOND', 'ETF'] else 48
    
    is_stale = age > max_age and abs(pnl) < 1
    
    if is_stale:
        print(f"[STALE] {sym} ({sys}): {age:.1f}h, PnL {pnl}%")
    
    if p.get('trust_tier') in ['BANNED', 'UNTRUSTED']:
        print(f"[BANNED] {sym} ({sys}): Tier {p.get('trust_tier')}")

    # Check for resolved
    rl = str(p.get('_resolved_live') or '').upper()
    if rl in ['TP_HIT', 'SL_HIT']:
         print(f"[RESOLVED] {sym} ({sys}): {rl}")
