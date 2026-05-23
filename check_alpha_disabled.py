#!/usr/bin/env python3
import json
from collections import defaultdict

with open('alpha_engine/data/active_picks.json', 'r') as f:
    picks = json.load(f)

# Load disabled strategies
disabled = set()
try:
    with open('stabilization/disabled_strategies.json', 'r') as f:
        data = json.load(f)
        disabled = set(data.get('disabled', []))
except:
    pass

print(f'Total active picks: {len(picks)}')
print(f'\nBy Strategy:')
print('-'*60)

by_strategy = defaultdict(lambda: {'count': 0, 'total_pnl': 0})

for pick in picks:
    if isinstance(pick, dict):
        strategy = pick.get('strategy', 'unknown')
        pnl = pick.get('unrealized_pnl', pick.get('pnl_pct', 0))
        by_strategy[strategy]['count'] += 1
        by_strategy[strategy]['total_pnl'] += float(pnl) if pnl else 0

# Show disabled vs active
print('\n[DISABLED STRATEGIES - Legacy Picks Winding Down]')
disabled_picks = [(s, d) for s, d in by_strategy.items() if s in disabled]
if disabled_picks:
    total_disabled = 0
    for strategy, data in disabled_picks:
        print(f"  {strategy}: {data['count']} picks, {data['total_pnl']:+.2f}% unrealized")
        total_disabled += data['count']
    print(f"  TOTAL DISABLED PICKS: {total_disabled}")
else:
    print('  None found')

print('\n[ACTIVE STRATEGIES]')
active_picks = [(s, d) for s, d in by_strategy.items() if s not in disabled]
if active_picks:
    for strategy, data in active_picks:
        print(f"  {strategy}: {data['count']} picks, {data['total_pnl']:+.2f}% unrealized")
else:
    print('  None found')
