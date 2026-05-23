import json

payload_path = r'e:\findtorontoevents_antigravity.ca\audit_trail\data\dashboard_payload.json'

with open(payload_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find all resolved picks in the payload
# In dashboard_payload.json, resolved picks can be found under systems -> [system] -> resolved_picks (if it exists)
# OR in the top-level 'headline_picks'? Let's check where the trades are.
# Wait, I don't see a global 'resolved_picks' in the first 800 lines of payload.
# But I saw them around line 203900.

# Let's search all lists in the JSON for objects with 'pnl_pct'.
def find_all_trades(obj, trades):
    if isinstance(obj, dict):
        if 'symbol' in obj and 'pnl_pct' in obj:
            trades.append(obj)
        for key, value in obj.items():
            find_all_trades(value, trades)
    elif isinstance(obj, list):
        for item in obj:
            find_all_trades(item, trades)

all_trades = []
find_all_trades(data, all_trades)
print(f"Total trades found in payload: {len(all_trades)}")

# Sort by PnL
all_trades.sort(key=lambda x: x['pnl_pct'])

print("\n--- BIGGEST INDIVIDUAL TRADE LOSERS ---")
for t in all_trades[:20]:
    print(f"Symbol: {t['symbol']}, System: {t.get('source', 'unknown')}, Strategy: {t.get('strategy', 'unknown')}, PnL: {t['pnl_pct']:.2f}%")

# Group by System and Symbol
from collections import defaultdict
system_stats = defaultdict(lambda: {'pnl': 0, 'trades': 0})
symbol_stats = defaultdict(lambda: {'pnl': 0, 'trades': 0})

for t in all_trades:
    sys = t.get('source') or t.get('source_system') or 'unknown'
    sym = t.get('symbol')
    pnl = t.get('pnl_pct', 0)
    
    system_stats[sys]['pnl'] += pnl
    system_stats[sys]['trades'] += 1
    
    symbol_stats[sym]['pnl'] += pnl
    symbol_stats[sym]['trades'] += 1

print("\n--- SYSTEM AGGREGATES FROM ALL TRADES ---")
sys_list = [{'name': k, 'pnl': v['pnl'], 'trades': v['trades']} for k, v in system_stats.items()]
sys_list.sort(key=lambda x: x['pnl'])
for s in sys_list[:15]:
    print(f"System: {s['name']}, trades: {s['trades']}, Cumulative PnL: {s['pnl']:.2f}%")

print("\n--- SYMBOL AGGREGATES FROM ALL TRADES ---")
sym_list = [{'name': k, 'pnl': v['pnl'], 'trades': v['trades']} for k, v in symbol_stats.items()]
sym_list.sort(key=lambda x: x['pnl'])
for s in sym_list[:15]:
    print(f"Symbol: {s['name']}, trades: {s['trades']}, Cumulative PnL: {s['pnl']:.2f}%")
