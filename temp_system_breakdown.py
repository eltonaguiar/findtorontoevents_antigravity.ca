import csv
import json
from collections import defaultdict
import statistics

trades = []
with open(r'C:\Users\zerou\Downloads\antigravity_closed_picks_2026-03-27 (6).csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            pnl = float(row['PnL%'].replace('%', '').strip()) if row.get('PnL%') else 0
            system = row.get('System', 'unknown').strip()
            trades.append({
                'system': system,
                'pnl': pnl,
                'direction': row.get('Direction', 'LONG').strip().upper(),
                'score': float(row['Score']) if row.get('Score') else None,
                'grade': row.get('Grade', '').strip(),
                'asset_class': row.get('Asset Class', 'UNKNOWN').strip().upper()
            })
        except:
            pass

# System breakdown
by_system = defaultdict(list)
for t in trades:
    by_system[t['system']].append(t)

print("SYSTEM BREAKDOWN WITHIN CRYPTO:")
print("-" * 70)
print(f"{'System':<20} {'Count':>8} {'Avg PnL':>10} {'WR':>8} {'Win Count':>10}")
print("-" * 70)

system_stats = []
for sys, trades_list in by_system.items():
    pnls = [t['pnl'] for t in trades_list]
    wins = sum(1 for p in pnls if p > 0)
    wr = wins / len(pnls) * 100 if pnls else 0
    avg = statistics.mean(pnls) if pnls else 0
    system_stats.append((sys, len(trades_list), avg, wr, wins))

system_stats.sort(key=lambda x: x[2], reverse=True)

for sys, count, avg, wr, wins in system_stats:
    print(f"{sys:<20} {count:>8} {avg:>+9.2f}% {wr:>7.1f}% {wins:>10}")

# Strategy breakdown for top systems
print("\n\nSTRATEGY BREAKDOWN (Top 5 Systems):")
print("-" * 80)

for sys, _, _, _, _ in system_stats[:5]:
    sys_trades = by_system[sys]
    by_strategy = defaultdict(list)
    for t in sys_trades:
        strat = t.get('grade', 'unknown')
        by_strategy[strat].append(t)
    
    print(f"\n{sys.upper()}:")
    print(f"  {'Strategy':<25} {'Count':>6} {'Avg PnL':>10} {'WR':>8}")
    print(f"  {'-'*55}")
    
    strat_stats = []
    for strat, strat_trades in by_strategy.items():
        pnls = [t['pnl'] for t in strat_trades]
        wins = sum(1 for p in pnls if p > 0)
        wr = wins / len(pnls) * 100 if pnls else 0
        avg = statistics.mean(pnls) if pnls else 0
        strat_stats.append((strat, len(strat_trades), avg, wr))
    
    strat_stats.sort(key=lambda x: x[2], reverse=True)
    
    for strat, count, avg, wr in strat_stats[:5]:
        print(f"  {strat:<25} {count:>6} {avg:>+9.2f}% {wr:>7.1f}%")

# Score bucket by direction
print("\n\nSCORE CORRELATION BY DIRECTION (CRYPTO):")
print("-" * 70)

crypto_trades = [t for t in trades if 'CRYPTO' in t['asset_class'].upper() or t['asset_class'] == '']

for direction in ['LONG', 'SHORT']:
    dir_trades = [t for t in crypto_trades if t['direction'] == direction and t['score'] is not None]
    
    score_buckets = defaultdict(list)
    for t in dir_trades:
        s = t['score']
        if s >= 80:
            bucket = '80-100'
        elif s >= 60:
            bucket = '60-79'
        elif s >= 40:
            bucket = '40-59'
        else:
            bucket = '0-39'
        score_buckets[bucket].append(t['pnl'])
    
    print(f"\n{direction}:")
    print(f"  {'Score Bucket':<15} {'Count':>7} {'Avg PnL':>10} {'WR':>8}")
    print(f"  {'-'*45}")
    
    for bucket in ['80-100', '60-79', '40-59', '0-39']:
        if bucket in score_buckets:
            pnls = score_buckets[bucket]
            wins = sum(1 for p in pnls if p > 0)
            wr = wins / len(pnls) * 100 if pnls else 0
            avg = statistics.mean(pnls) if pnls else 0
            print(f"  {bucket:<15} {len(pnls):>7} {avg:>+9.2f}% {wr:>7.1f}%")

# Save enhanced results
enhanced = {
    'system_breakdown': [
        {'system': s, 'count': c, 'avg_pnl': f"{a:+.2f}%", 'win_rate': f"{w:.1f}%", 'wins': win}
        for s, c, a, w, win in system_stats
    ]
}

with open('enhanced_system_stats.json', 'w') as f:
    json.dump(enhanced, f, indent=2)

print("\n\nEnhanced stats saved to: enhanced_system_stats.json")
