import json
import os

payload_path = r'e:\findtorontoevents_antigravity.ca\audit_trail\data\dashboard_payload.json'

if not os.path.exists(payload_path):
    print(f"Error: {payload_path} not found")
    exit(1)

with open(payload_path, 'r') as f:
    data = json.load(f)

print("\n--- TOP SYMBOL LOSERS (ALL) ---")
all_stats = data.get('summary', {}).get('clean_metrics', {}).get('top_symbols', [])
for sym in all_stats:
    if sym['pnl'] < 0:
        print(f"Symbol: {sym['symbol']}, PnL: {sym['pnl']:.2f}, % of Total: {sym['pct_of_total']:.1f}%")

print("\n--- SYSTEM PERFORMANCE (LOSERS) ---")
systems = data.get('systems', [])
losers = [s for s in systems if s.get('total_pnl_pct', 0) < 0] 
losers.sort(key=lambda x: x.get('total_pnl_pct', 0))

for s in losers[:20]: # Show top 20 losing systems
    print(f"System: {s['name']}, PnL: {s['total_pnl_pct']:.2f}%, Win Rate: {s.get('win_rate', 0)}%")

print("\n--- STRATEGY PERFORMANCE (LOSERS) ---")
all_strategies = []
for s in systems:
    for strats in s.get('strategies', []):
        if strats.get('total_pnl', 0) < 0:
            all_strategies.append({
                'system': s['name'],
                'strategy': strats['name'],
                'pnl': strats['total_pnl'],
                'wr': strats.get('win_rate', 0)
            })

all_strategies.sort(key=lambda x: x['pnl'])
for strat in all_strategies[:30]:
    print(f"[{strat['system']}] {strat['strategy']}: {strat['pnl']:.2f}% PnL, {strat['wr']:.1f}% WR")
