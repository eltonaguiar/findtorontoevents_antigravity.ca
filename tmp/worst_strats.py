import json

payload_path = r'e:\findtorontoevents_antigravity.ca\audit_trail\data\dashboard_payload.json'

with open(payload_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

systems = data.get('systems', [])
all_strats = []

for s in systems:
    sys_name = s.get('name', 'unknown')
    for strat in s.get('strategies', []):
        strat_name = strat.get('name', 'unknown')
        pnl = strat.get('total_pnl', 0)
        wr = strat.get('win_rate', 0)
        trades = strat.get('resolved', 0)
        
        if trades >= 10: # Only look at strategies with at least 10 trades
            all_strats.append({
                'id': f"{sys_name} | {strat_name}",
                'pnl': pnl,
                'wr': wr,
                'trades': trades
            })

# Sort by PnL
all_strats.sort(key=lambda x: x['pnl'])

print("\n--- WORST STRATEGIES BY TOTAL PNL (Min 10 trades) ---")
for s in all_strats[:15]:
    print(f"Strat: {s['id']}, PnL: {s['pnl']:.2f}%, WR: {s['wr']:.1f}%, Trades: {s['trades']}")

# Sort by Win Rate
all_strats.sort(key=lambda x: x['wr'])

print("\n--- WORST STRATEGIES BY WIN RATE (Min 10 trades) ---")
for s in all_strats[:15]:
    print(f"Strat: {s['id']}, WR: {s['wr']:.1f}%, PnL: {s['pnl']:.2f}%, Trades: {s['trades']}")
