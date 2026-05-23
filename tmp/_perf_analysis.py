import json, os
from collections import defaultdict, Counter

payload_path = 'e:/findtorontoevents_antigravity.ca/audit_trail/data/dashboard_payload.json'
if not os.path.exists(payload_path):
    print('No dashboard payload found')
    exit()

with open(payload_path) as f:
    payload = json.load(f)

active = payload.get('picks', {}).get('active', [])
closed = payload.get('picks', {}).get('recent_closed', [])
systems = payload.get('systems', [])

print('=== SYSTEMS LEADERBOARD ===')
for s in sorted(systems, key=lambda x: x.get('win_rate', 0), reverse=True)[:20]:
    name = s.get('name', '?') or '?'
    wr = s.get('win_rate', 0) or 0
    pf = s.get('profit_factor', 0) or 0
    trades = s.get('total_trades', 0) or 0
    exp = s.get('expectancy', 0) or 0
    print(f'{name:40s} WR={wr:6.1f}% PF={pf:5.2f} Trades={trades:4d} Exp={exp:+.3f}')

print()
print('=== STRATEGY BREAKDOWN (active picks) ===')
strat_count = Counter()
strat_systems = defaultdict(set)
for p in active:
    strat = p.get('strategy', 'unknown')
    sys = p.get('source_system', 'unknown')
    strat_count[strat] += 1
    strat_systems[strat].add(sys)
for strat, count in strat_count.most_common(30):
    systems_list = ', '.join(sorted(strat_systems[strat]))
    print(f'{strat:45s} x{count:3d} from: {systems_list}')

print()
print('=== ACTIVE PICKS BY SYSTEM ===')
sys_picks = defaultdict(list)
for p in active:
    sys_picks[p.get('source_system', '?')].append(p)
for sys, picks in sorted(sys_picks.items(), key=lambda x: len(x[1]), reverse=True):
    avg_pnl = sum(p.get('pnl_pct', 0) for p in picks) / max(len(picks), 1)
    print(f'{sys:40s} {len(picks):3d} picks  avg_pnl={avg_pnl:+.2f}%')

print()
print('=== CONFLICTING PICKS (same symbol, opposite direction) ===')
symbol_dirs = defaultdict(list)
for p in active:
    sym = p.get('symbol', '?')
    direction = p.get('direction', '?')
    sys = p.get('source_system', '?')
    strat = p.get('strategy', '?')
    pnl = p.get('pnl_pct', 0)
    symbol_dirs[sym].append({'dir': direction, 'sys': sys, 'strat': strat, 'pnl': pnl})
for sym, entries in sorted(symbol_dirs.items()):
    dirs = set(e['dir'] for e in entries)
    if len(dirs) > 1:
        print(f'  CONFLICT: {sym}')
        for e in entries:
            d = e['dir']
            s = e['sys']
            st = e['strat']
            pnl = e['pnl']
            print(f'    {d:6s} from {s:30s} strat={st:30s} pnl={pnl:+.2f}%')

print()
print('=== CLOSED PICKS - MISSING DATES / SUSPICIOUS GAINS ===')
missing_date = 0
suspicious = []
for p in closed:
    closed_at = p.get('closed_at', '') or p.get('exit_time', '') or p.get('close_time', '')
    if not closed_at:
        missing_date += 1
        if missing_date <= 20:
            sym = p.get('symbol', '?')
            pnl = p.get('pnl_pct', 0)
            sys = p.get('source_system', '?')
            strat = p.get('strategy', '?')
            print(f'  NO CLOSE DATE: {sym:12s} pnl={pnl:+.2f}% sys={sys} strat={strat}')
    pnl = p.get('pnl_pct', 0) or 0
    if abs(pnl) > 15:
        suspicious.append(p)
print(f'  Total closed picks missing date: {missing_date}')

print()
print('=== SUSPICIOUS GAINS (|pnl| > 15%) ===')
for p in sorted(suspicious, key=lambda x: abs(x.get('pnl_pct', 0)), reverse=True)[:20]:
    sym = p.get('symbol', '?')
    pnl = p.get('pnl_pct', 0)
    sys = p.get('source_system', '?')
    strat = p.get('strategy', '?')
    ca = p.get('closed_at', '?')
    print(f'  {sym:12s} pnl={pnl:+.2f}% sys={sys} strat={strat} closed={ca}')

print()
print('=== DNA/GENOME STRATEGIES ===')
def is_dna(p):
    text = (p.get('strategy','') + p.get('source_system','')).lower()
    return any(k in text for k in ['dna', 'genome', 'evolved', 'mutation'])

dna_picks = [p for p in active if is_dna(p)]
print(f'  Active DNA/genome picks: {len(dna_picks)}')
for p in dna_picks:
    sym = p.get('symbol', '?')
    d = p.get('direction', '?')
    pnl = p.get('pnl_pct', 0)
    strat = p.get('strategy', '?')
    sys = p.get('source_system', '?')
    print(f'    {sym:12s} {d} pnl={pnl:+.2f}% strat={strat} sys={sys}')

dna_closed = [p for p in closed if is_dna(p)]
print(f'  Closed DNA/genome picks: {len(dna_closed)}')
wins = sum(1 for p in dna_closed if (p.get('pnl_pct',0) or 0) > 0)
print(f'  DNA WR: {wins}/{len(dna_closed)} = {wins/max(len(dna_closed),1)*100:.1f}%')

print()
print('=== TOP STRATEGIES BY CLOSED WIN RATE (min 5 trades) ===')
strat_results = defaultdict(lambda: {'wins': 0, 'total': 0, 'pnl_sum': 0})
for p in closed:
    strat = p.get('strategy', 'unknown')
    pnl = p.get('pnl_pct', 0) or 0
    strat_results[strat]['total'] += 1
    strat_results[strat]['pnl_sum'] += pnl
    if pnl > 0:
        strat_results[strat]['wins'] += 1

for strat, r in sorted(strat_results.items(), key=lambda x: x[1]['wins']/max(x[1]['total'],1) if x[1]['total'] >= 5 else 0, reverse=True)[:25]:
    if r['total'] >= 5:
        wr = r['wins']/r['total']*100
        avg = r['pnl_sum']/r['total']
        print(f'  {strat:45s} WR={wr:5.1f}% ({r["wins"]}/{r["total"]}) avg={avg:+.3f}%')

print()
print('=== WORST STRATEGIES BY CLOSED WIN RATE (min 5 trades) ===')
for strat, r in sorted(strat_results.items(), key=lambda x: x[1]['wins']/max(x[1]['total'],1) if x[1]['total'] >= 5 else 1)[:15]:
    if r['total'] >= 5:
        wr = r['wins']/r['total']*100
        avg = r['pnl_sum']/r['total']
        print(f'  {strat:45s} WR={wr:5.1f}% ({r["wins"]}/{r["total"]}) avg={avg:+.3f}%')

print()
print('=== KELTNER-SPECIFIC BREAKDOWN ===')
keltner_active = [p for p in active if 'keltner' in (p.get('strategy','')+'').lower()]
keltner_closed = [p for p in closed if 'keltner' in (p.get('strategy','')+'').lower()]
print(f'  Keltner active: {len(keltner_active)}')
print(f'  Keltner closed: {len(keltner_closed)}')
if keltner_closed:
    kw = sum(1 for p in keltner_closed if (p.get('pnl_pct',0) or 0) > 0)
    kavg = sum(p.get('pnl_pct',0) or 0 for p in keltner_closed) / len(keltner_closed)
    print(f'  Keltner WR: {kw}/{len(keltner_closed)} = {kw/len(keltner_closed)*100:.1f}%  avg_pnl={kavg:+.3f}%')
for p in keltner_active[:10]:
    sym = p.get('symbol', '?')
    d = p.get('direction', '?')
    pnl = p.get('pnl_pct', 0)
    sys = p.get('source_system', '?')
    print(f'    {sym:12s} {d} pnl={pnl:+.2f}% sys={sys}')
