import json
from collections import defaultdict

d = json.load(open('C:/findtorontoevents_antigravity.ca/audit/data/dashboard_data.json'))
active = d.get('picks', {}).get('active', [])

print('=== ACTIVE PICKS BY ASSET CLASS AND STRATEGY ===')
by_ac_strat = defaultdict(lambda: defaultdict(list))
for p in active:
    ac = p.get('asset_class', 'CRYPTO')
    strat = p.get('strategy', 'unknown')
    sys = p.get('source_system', 'unknown')
    sym = p.get('symbol', '?')
    by_ac_strat[ac][f"{sys}::{strat}"].append(sym)

for ac in sorted(by_ac_strat.keys()):
    print(f"\n  {ac}:")
    for strat, syms in sorted(by_ac_strat[ac].items(), key=lambda x: -len(x[1])):
        print(f"    {strat:60s} n={len(syms)} symbols={','.join(syms[:5])}{'...' if len(syms)>5 else ''}")

print()
print('=== EQUITY SYMBOLS IN ACTIVE PICKS ===')
equity = [p for p in active if p.get('asset_class') == 'EQUITY']
print(f"Total EQUITY active picks: {len(equity)}")
syms = defaultdict(int)
for p in equity:
    syms[p.get('symbol', '?')] += 1
for sym, cnt in sorted(syms.items(), key=lambda x: -x[1])[:20]:
    print(f"  {sym}: {cnt}")

print()
print('=== FOREX SYMBOLS IN ACTIVE PICKS ===')
forex = [p for p in active if p.get('asset_class') == 'FOREX']
print(f"Total FOREX active picks: {len(forex)}")
syms = defaultdict(int)
for p in forex:
    syms[p.get('symbol', '?')] += 1
for sym, cnt in sorted(syms.items(), key=lambda x: -x[1])[:20]:
    print(f"  {sym}: {cnt}")

print()
print('=== COMMODITY SYMBOLS IN ACTIVE PICKS ===')
commodity = [p for p in active if p.get('asset_class') == 'COMMODITY']
print(f"Total COMMODITY active picks: {len(commodity)}")
syms = defaultdict(int)
for p in commodity:
    syms[p.get('symbol', '?')] += 1
for sym, cnt in sorted(syms.items(), key=lambda x: -x[1])[:20]:
    print(f"  {sym}: {cnt}")

print()
print('=== ETF SYMBOLS IN ACTIVE PICKS ===')
etf = [p for p in active if p.get('asset_class') == 'ETF']
print(f"Total ETF active picks: {len(etf)}")
syms = defaultdict(int)
for p in etf:
    syms[p.get('symbol', '?')] += 1
for sym, cnt in sorted(syms.items(), key=lambda x: -x[1])[:20]:
    print(f"  {sym}: {cnt}")

print()
print('=== FUTURES SYMBOLS IN ACTIVE PICKS ===')
futures = [p for p in active if p.get('asset_class') == 'FUTURES']
print(f"Total FUTURES active picks: {len(futures)}")
syms = defaultdict(int)
for p in futures:
    syms[p.get('symbol', '?')] += 1
for sym, cnt in sorted(syms.items(), key=lambda x: -x[1])[:20]:
    print(f"  {sym}: {cnt}")
