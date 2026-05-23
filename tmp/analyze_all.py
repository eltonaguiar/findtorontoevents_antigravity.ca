import json
import os

# Read disabled strategies
with open(r'e:\findtorontoevents_antigravity.ca\stabilization\disabled_strategies.json', 'r') as f:
    disabled_data = json.load(f)

print("=== DISABLED STRATEGIES ===")
print(f"Disabled count: {len(disabled_data.get('disabled', []))}")
print(f"Keep count: {len(disabled_data.get('keep_strategies', []))}")
print()
print("Keep strategies:")
for s in disabled_data.get('keep_strategies', []):
    print(f"  {s}")
print()

# Read strategy performance
with open(r'e:\findtorontoevents_antigravity.ca\alpha_engine\data\strategy_performance.json', 'r') as f:
    perf_data = json.load(f)

# Classify all strategies
active = []
graveyard = []

for name, p in perf_data.items():
    info = {
        'name': name,
        'win_rate': p.get('win_rate', 0),
        'kelly': p.get('kelly_fraction', 0),
        'total_pnl': p.get('total_pnl_dollar', 0),
        'trades': p.get('closed_picks', 0),
        'sharpe': p.get('sharpe', 0),
        'profit_factor': p.get('profit_factor', 0),
        'avg_pnl_pct': p.get('avg_pnl_pct', 0),
    }
    
    # Positive EV: positive Kelly OR (50%+ WR with positive avg PnL)
    is_positive_ev = info['kelly'] > 0 or (info['win_rate'] >= 0.5 and info['avg_pnl_pct'] > 0)
    
    if is_positive_ev:
        active.append(info)
    else:
        graveyard.append(info)

active.sort(key=lambda x: x['total_pnl'], reverse=True)
graveyard.sort(key=lambda x: x['total_pnl'])

print(f"=== CLASSIFICATION RESULTS ===")
print(f"Total strategies with performance data: {len(perf_data)}")
print(f"Active (positive EV): {len(active)}")
print(f"Graveyard (negative EV): {len(graveyard)}")
print()

active_pnl = sum(s['total_pnl'] for s in active)
graveyard_pnl = sum(s['total_pnl'] for s in graveyard)
print(f"Active strategies total PnL: ${active_pnl:.2f}")
print(f"Graveyard strategies total PnL: ${graveyard_pnl:.2f}")
print(f"Combined PnL: ${active_pnl + graveyard_pnl:.2f}")
print()

print("=== ACTIVE STRATEGIES (KEEP) ===")
for s in active:
    print(f"  {s['name']:45s} | WR: {s['win_rate']*100:5.1f}% | Kelly: {s['kelly']:7.4f} | PnL: ${s['total_pnl']:8.2f} | Trades: {s['trades']:3d} | Sharpe: {s['sharpe']:7.2f}")
print()

print("=== GRAVEYARD STRATEGIES (DISABLE) ===")
for s in graveyard:
    print(f"  {s['name']:45s} | WR: {s['win_rate']*100:5.1f}% | Kelly: {s['kelly']:7.4f} | PnL: ${s['total_pnl']:8.2f} | Trades: {s['trades']:3d} | Sharpe: {s['sharpe']:7.2f}")

# Save full classification
output = {
    'classification_date': '2026-03-01',
    'summary': {
        'total_strategies': len(perf_data),
        'active_count': len(active),
        'graveyard_count': len(graveyard),
        'active_total_pnl': active_pnl,
        'graveyard_total_pnl': graveyard_pnl,
    },
    'active': [s['name'] for s in active],
    'graveyard': [s['name'] for s in graveyard],
    'active_details': active,
    'graveyard_details': graveyard,
}

with open(r'e:\findtorontoevents_antigravity.ca\tmp\strategy_classification.json', 'w') as f:
    json.dump(output, f, indent=2)
print("\nSaved to tmp/strategy_classification.json")
