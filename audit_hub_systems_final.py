#!/usr/bin/env python3
"""
FINAL AUDIT: All Hub Systems with Unrealized P/L
"""

import json
from pathlib import Path

print('='*80)
print('ALL HUB SYSTEMS - FINAL VERIFIED AUDIT')
print('='*80)

# Check all systems
systems_data = []

# 1. Crypto ML Edge
print('\n[1] ML: Crypto ML Edge')
print('-'*60)
try:
    with open('crypto_ml_edge/data/active_picks.json', 'r') as f:
        data = json.load(f)
    active = data.get('picks', [])
    closed = data.get('closed_picks', [])
    
    active_pnl = sum(p.get('unrealized_pnl_pct', 0) for p in active)
    closed_pnl = sum(p.get('pnl_pct', 0) for p in closed)
    perf = data.get('performance', {})
    
    print(f'  Active picks: {len(active)}')
    print(f'  Closed picks: {len(closed)}')
    print(f'  Active Unrealized P/L: {active_pnl:+.2f}%')
    print(f'  Closed Realized P/L: {closed_pnl:+.2f}%')
    print(f'  Total Return: {perf.get("total_return_pct", 0):+.2f}%')
    print(f'  Status: {"WINNING" if active_pnl > 0 else "LOSING"}')
    
    systems_data.append({
        'name': 'ML: Crypto ML Edge',
        'active': len(active),
        'closed': len(closed),
        'active_pnl': active_pnl,
        'closed_pnl': closed_pnl,
        'total_pnl': active_pnl + closed_pnl
    })
except Exception as e:
    print(f'  [ERROR: {e}]')

# 2. Mercury 2
print('\n[2] ML: Mercury 2')
print('-'*60)
try:
    with open('mercury2/data/active_picks.json', 'r') as f:
        data = json.load(f)
    picks = data if isinstance(data, list) else data.get('picks', [])
    
    total_pnl = 0
    winners = 0
    losers = 0
    for p in picks:
        if isinstance(p, dict):
            pnl = p.get('unrealized_pnl', p.get('pnl_pct', p.get('current_pnl', 0)))
            total_pnl += float(pnl) if pnl else 0
            if pnl and float(pnl) > 0:
                winners += 1
            elif pnl and float(pnl) < 0:
                losers += 1
    
    print(f'  Active picks: {len(picks)}')
    print(f'  Winners: {winners}  Losers: {losers}')
    print(f'  Unrealized P/L: {total_pnl:+.2f}%')
    print(f'  Status: {"WINNING" if total_pnl > 0 else "LOSING"}')
    
    systems_data.append({
        'name': 'ML: Mercury 2',
        'active': len(picks),
        'closed': 0,
        'active_pnl': total_pnl,
        'closed_pnl': 0,
        'total_pnl': total_pnl
    })
except Exception as e:
    print(f'  [ERROR: {e}]')

# 3. Alpha Engine
print('\n[3] ML: Alpha Engine')
print('-'*60)
try:
    with open('alpha_engine/data/active_picks.json', 'r') as f:
        data = json.load(f)
    picks = data if isinstance(data, list) else data.get('picks', [])
    
    total_pnl = 0
    winners = 0
    losers = 0
    for p in picks:
        if isinstance(p, dict):
            pnl = p.get('unrealized_pnl', p.get('pnl_pct', 0))
            total_pnl += float(pnl) if pnl else 0
            if pnl and float(pnl) > 0:
                winners += 1
            elif pnl and float(pnl) < 0:
                losers += 1
    
    print(f'  Active picks: {len(picks)}')
    print(f'  Winners: {winners}  Losers: {losers}')
    print(f'  Unrealized P/L: {total_pnl:+.2f}%')
    print(f'  Status: {"WINNING" if total_pnl > 0 else "LOSING"}')
    
    systems_data.append({
        'name': 'ML: Alpha Engine',
        'active': len(picks),
        'closed': 0,
        'active_pnl': total_pnl,
        'closed_pnl': 0,
        'total_pnl': total_pnl
    })
except Exception as e:
    print(f'  [ERROR: {e}]')

# 4. Claude Gainer
print('\n[4] ML: Claude Gainer Tracker')
print('-'*60)
try:
    # Check multiple possible locations
    possible_paths = [
        'claude_gainer_ml/tracker/live_picks.json',
        'claude_gainer_ml/data/live_picks.json',
        'claude_gainer_ml/data/tracker.json',
    ]
    
    found = False
    for path in possible_paths:
        if Path(path).exists():
            with open(path, 'r') as f:
                data = json.load(f)
            picks = data.get('picks', data if isinstance(data, list) else [])
            
            total_pnl = sum(p.get('unrealized_pnl', p.get('pnl_pct', 0)) for p in picks if isinstance(p, dict))
            
            print(f'  Source: {path}')
            print(f'  Active picks: {len(picks)}')
            print(f'  Unrealized P/L: {total_pnl:+.2f}%')
            print(f'  Status: {"WINNING" if total_pnl > 0 else "LOSING"}')
            
            systems_data.append({
                'name': 'ML: Claude Gainer',
                'active': len(picks),
                'closed': 0,
                'active_pnl': total_pnl,
                'closed_pnl': 0,
                'total_pnl': total_pnl
            })
            found = True
            break
    
    if not found:
        print('  [NO DATA FILE FOUND]')
        # Try to find any JSON in claude_gainer_ml
        json_files = list(Path('claude_gainer_ml').rglob('*.json'))
        if json_files:
            print(f'  Available JSON files: {[f.name for f in json_files[:5]]}')
except Exception as e:
    print(f'  [ERROR: {e}]')

# FINAL SUMMARY
print('\n' + '='*80)
print('FINAL VERIFIED SUMMARY - HUB SYSTEMS')
print('='*80)

print('\n[WINNING SYSTEMS - Positive Unrealized P/L]')
print('-'*80)
winners = [s for s in systems_data if s['active_pnl'] > 0]
if winners:
    for s in sorted(winners, key=lambda x: x['active_pnl'], reverse=True):
        print(f"  {s['name']:<30} Picks: {s['active']:>3}  Unrealized: {s['active_pnl']:>+7.2f}%")
else:
    print('  NONE')

print('\n[LOSING SYSTEMS - Negative Unrealized P/L]')
print('-'*80)
losers = [s for s in systems_data if s['active_pnl'] <= 0]
if losers:
    for s in sorted(losers, key=lambda x: x['active_pnl']):
        print(f"  {s['name']:<30} Picks: {s['active']:>3}  Unrealized: {s['active_pnl']:>+7.2f}%")
else:
    print('  NONE')

print('\n' + '='*80)
print('RECOMMENDATION:')
print('='*80)
if winners:
    best = max(winners, key=lambda x: x['active_pnl'])
    print(f"  Focus on: {best['name']} ({best['active_pnl']:+.2f}% unrealized)")
    print(f"  Systems with positive unrealized P/L show current momentum.")
else:
    print("  All systems currently showing negative unrealized P/L.")
    print("  Consider reducing position sizes or waiting for better entries.")
print('='*80)
