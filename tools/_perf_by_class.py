"""Quick performance check by asset class. Run from repo root."""
import json, statistics, math, random
from collections import Counter

with open('audit_dashboard/data/dashboard_data.json') as f:
    dd = json.load(f)
closed = dd['picks']['recent_closed']
active = dd['picks'].get('active', [])

def pf_wr(pnls):
    if not pnls: return 0.0, 0.0
    gw = sum(x for x in pnls if x > 0)
    gl = abs(sum(x for x in pnls if x <= 0))
    pf = gw / gl if gl > 0 else 99.0
    wr = sum(1 for x in pnls if x > 0) / len(pnls) * 100
    return pf, wr

# --- Half-split decay check ---
print('\n--- HALF-SPLIT DECAY CHECK ---')
print(f'{"ASSET":<10} {"Old PF":>8} {"New PF":>8} {"Delta":>8}  Status')
for ac in ['CRYPTO', 'EQUITY', 'FOREX', 'COMMODITY']:
    picks_ac = [p for p in closed if (p.get('asset_class') or '').upper() == ac]
    picks_s = sorted(picks_ac, key=lambda p: p.get('closed_at') or p.get('entry_time') or '')
    half = len(picks_s) // 2
    opf, _ = pf_wr([float(p.get('pnl_pct') or 0) for p in picks_s[:half]])
    npf, _ = pf_wr([float(p.get('pnl_pct') or 0) for p in picks_s[half:]])
    if npf < 0.7 * opf:
        flag = 'DECAYING'
    elif npf >= opf * 0.9:
        flag = 'Stable'
    else:
        flag = 'Slightly weaker'
    print(f'{ac:<10} {opf:>8.2f} {npf:>8.2f} {npf-opf:>+8.2f}  {flag}')

# --- Exit type breakdown ---
print('\n--- EXIT TYPE BREAKDOWN ---')
for ac in ['CRYPTO', 'EQUITY', 'FOREX', 'COMMODITY']:
    picks_ac = [p for p in closed if (p.get('asset_class') or '').upper() == ac]
    exits = Counter(p.get('exit_reason') or p.get('result') or 'UNKNOWN' for p in picks_ac)
    top = ', '.join(f'{k}:{v}' for k, v in exits.most_common(5))
    print(f'  {ac:<12} {top}')

# --- Top active CRYPTO ---
print('\n--- TOP ACTIVE CRYPTO PICKS (by score) ---')
crypto_active = sorted(
    [p for p in active if (p.get('asset_class') or '').upper() == 'CRYPTO'],
    key=lambda p: float(p.get('score') or 0), reverse=True
)[:8]
print(f'{"Symbol":<14} {"Score":>6} {"Trust":>6} {"Tier":<6} {"Dir":<6} Strategy')
for p in crypto_active:
    sym = p.get('symbol', '?')
    sc = float(p.get('score') or 0)
    tr = float(p.get('trust_score') or 0)
    tier = str(p.get('hf_conviction_tier') or '-')
    dr = str(p.get('direction') or '?')
    strat = str(p.get('strategy') or '?')
    print(f'{sym:<14} {sc:>6.0f} {tr:>6.1f} {tier:<6} {dr:<6} {strat}')

# --- Top active EQUITY ---
print('\n--- TOP ACTIVE EQUITY PICKS (score>=40) ---')
eq_active = sorted(
    [p for p in active
     if (p.get('asset_class') or '').upper() == 'EQUITY'
     and float(p.get('score') or 0) >= 40],
    key=lambda p: float(p.get('score') or 0), reverse=True
)[:8]
print(f'{"Symbol":<14} {"Score":>6} {"Trust":>6} {"Dir":<6} Strategy')
for p in eq_active:
    sym = p.get('symbol', '?')
    sc = float(p.get('score') or 0)
    tr = float(p.get('trust_score') or 0)
    dr = str(p.get('direction') or '?')
    strat = str(p.get('strategy') or '?')
    print(f'{sym:<14} {sc:>6.0f} {tr:>6.1f} {dr:<6} {strat}')

# --- FOREX + COMMODITY active ---
print('\n--- ACTIVE FOREX PICKS ---')
fx_active = sorted(
    [p for p in active if (p.get('asset_class') or '').upper() == 'FOREX'],
    key=lambda p: float(p.get('score') or 0), reverse=True
)
for p in fx_active:
    sym = p.get('symbol', '?')
    sc = float(p.get('score') or 0)
    tr = float(p.get('trust_score') or 0)
    dr = str(p.get('direction') or '?')
    strat = str(p.get('strategy') or '?')
    print(f'  {sym:<14} score={sc:.0f} trust={tr:.1f} {dr}  {strat}')
if not fx_active:
    print('  (none)')
