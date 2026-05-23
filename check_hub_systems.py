#!/usr/bin/env python3
"""
Check Hub Page Systems for Unrealized P/L > 0
"""

import json
from pathlib import Path

print('='*80)
print('HUB PAGE SYSTEMS - Detailed Unrealized P/L Audit')
print('='*80)

# Systems on the hub page
systems_to_check = [
    ('ML: Alpha Engine', 'alpha_engine/data/active_picks.json'),
    ('ML: Mercury 2', 'mercury2/data/active_picks.json'),
    ('ML: Crypto Signal Engine', 'crypto_signal_engine/data/active_picks.json'),
    ('ML: KIMI Rise of the Claw', 'KIMI_RISEOFTHECLAW/data/active_picks.json'),
    ('ML: Battleground', 'ml_battleground/ensemble_data/active_picks.json'),
    ('ML: Claude Gainer', 'claude_gainer_ml/claude_live_picks.json'),
    ('ML: Crypto ML Edge', 'crypto_ml_edge/live_signals.json'),
]

print('\n[System-by-System Breakdown]')
print('='*80)

results = []

for name, filepath in systems_to_check:
    path = Path(filepath)
    print(f'\n{name}')
    print('-'*60)
    
    if not path.exists():
        print(f'  [FILE NOT FOUND: {filepath}]')
        continue
    
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        
        # Handle different data structures
        picks = []
        if isinstance(data, list):
            picks = data
        elif isinstance(data, dict):
            picks = data.get('picks', data.get('active_picks', data.get('signals', [])))
        
        if not picks:
            print(f'  No active picks found')
            continue
        
        # Calculate stats
        total_pnl = 0
        positive_picks = []
        negative_picks = []
        
        for pick in picks:
            if not isinstance(pick, dict):
                continue
            
            # Get PnL - try multiple field names
            pnl = (pick.get('unrealized_pnl') or 
                   pick.get('pnl_pct') or 
                   pick.get('current_pnl') or 
                   pick.get('unrealized_pnl_pct') or 0)
            
            try:
                pnl = float(pnl)
            except:
                pnl = 0
            
            total_pnl += pnl
            
            symbol = (pick.get('symbol') or 
                     pick.get('ticker') or 
                     pick.get('pair') or 
                     pick.get('asset', 'Unknown'))
            
            if pnl > 0:
                positive_picks.append((symbol, pnl))
            elif pnl < 0:
                negative_picks.append((symbol, pnl))
        
        # Display results
        print(f'  Total Picks: {len(picks)}')
        print(f'  Winners: {len(positive_picks)}  Losers: {len(negative_picks)}')
        print(f'  Total Unrealized P/L: {total_pnl:+.2f}%')
        
        if total_pnl > 0:
            print(f'  Status: [POSITIVE]')
        elif total_pnl < 0:
            print(f'  Status: [NEGATIVE]')
        else:
            print(f'  Status: [FLAT]')
        
        # Show breakdown
        if positive_picks:
            print(f'  Top Winners:')
            for sym, pnl in sorted(positive_picks, key=lambda x: x[1], reverse=True)[:5]:
                print(f'    + {sym}: {pnl:+.2f}%')
        
        if negative_picks:
            print(f'  Top Losers:')
            for sym, pnl in sorted(negative_picks, key=lambda x: x[1])[:5]:
                print(f'    - {sym}: {pnl:+.2f}%')
        
        results.append({
            'name': name,
            'total_pnl': total_pnl,
            'picks': len(picks),
            'winners': len(positive_picks),
            'losers': len(negative_picks)
        })
        
    except Exception as e:
        print(f'  [ERROR: {e}]')

# Summary
print('\n' + '='*80)
print('SUMMARY: Systems with Unrealized P/L > 0')
print('='*80)

positive_systems = [r for r in results if r['total_pnl'] > 0]
negative_systems = [r for r in results if r['total_pnl'] <= 0]

if positive_systems:
    print('\n[WINNING SYSTEMS - Positive Unrealized P/L]')
    for r in sorted(positive_systems, key=lambda x: x['total_pnl'], reverse=True):
        print(f"  {r['name']:<35} PnL: {r['total_pnl']:>+7.2f}%  ({r['winners']}/{r['picks']} winning)")
else:
    print('\n[NO SYSTEMS with positive unrealized P/L found]')

if negative_systems:
    print('\n[LOSING SYSTEMS - Negative Unrealized P/L]')
    for r in sorted(negative_systems, key=lambda x: x['total_pnl']):
        print(f"  {r['name']:<35} PnL: {r['total_pnl']:>+7.2f}%  ({r['winners']}/{r['picks']} winning)")

print('\n' + '='*80)
