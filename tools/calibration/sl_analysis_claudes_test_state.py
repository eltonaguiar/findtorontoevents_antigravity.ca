import json
from collections import defaultdict
from statistics import mean, stdev

with open('audit_dashboard/data/claudes_test_state.json', 'r', encoding='utf-8') as f:
    state = json.load(f)

sl_stats = defaultdict(lambda: {'count': 0, 'total_dist': 0.0, 'dists': []})
tp_stats = defaultdict(lambda: {'count': 0, 'total_dist': 0.0, 'dists': []})
exit_reasons = defaultdict(int)

for port_id, port in state.items():
    closed = port.get('closed', [])
    for trade in closed:
        asset = trade.get('asset_class', 'UNKNOWN')
        entry = trade.get('entry_price', 0)
        sl = trade.get('stop_loss', 0)
        tp = trade.get('take_profit', 0)
        exit_reason = trade.get('exit_reason', 'UNKNOWN')
        
        exit_reasons[exit_reason] += 1
        
        if entry > 0:
            if sl > 0:
                dist_pct = abs(sl - entry) / entry * 100
                sl_stats[asset]['count'] += 1
                sl_stats[asset]['total_dist'] += dist_pct
                sl_stats[asset]['dists'].append(dist_pct)
            
            if tp > 0:
                dist_pct = abs(tp - entry) / entry * 100
                tp_stats[asset]['count'] += 1
                tp_stats[asset]['total_dist'] += dist_pct
                tp_stats[asset]['dists'].append(dist_pct)

print("Exit Reasons:")
for reason, count in sorted(exit_reasons.items(), key=lambda x: x[1], reverse=True):
    print(f"  {reason}: {count}")

print("\nSL Distance Stats by Asset Class:")
for asset in sl_stats:
    stats = sl_stats[asset]
    if stats['count'] > 0:
        avg = stats['total_dist'] / stats['count']
        std = stdev(stats['dists']) if len(stats['dists']) > 1 else 0
        print(f"{asset}: n={stats['count']}, avg SL dist={avg:.2f}%, std={std:.2f}%")

print("\nTP Distance Stats by Asset Class:")
for asset in tp_stats:
    stats = tp_stats[asset]
    if stats['count'] > 0:
        avg = stats['total_dist'] / stats['count']
        std = stdev(stats['dists']) if len(stats['dists']) > 1 else 0
        print(f"{asset}: n={stats['count']}, avg TP dist={avg:.2f}%, std={std:.2f}%")