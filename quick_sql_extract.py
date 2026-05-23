#!/usr/bin/env python3
"""
Quick extraction of algorithm performance data from SQL file
Processes in chunks to handle 4.2GB file
"""
import re
import json

SQL_FILE = r'C:\Users\zerou\Downloads\ejaguiar1_stocks_apr62026_extract.sql'
OUTPUT_FILE = 'extracted_algo_perf.json'

def extract_chunk(f, chunk_size=1024*1024):
    """Read file in chunks."""
    while True:
        chunk = f.read(chunk_size)
        if not chunk:
            break
        yield chunk

def main():
    algorithms = []
    line_count = 0
    
    print("Extracting algorithm performance data...")
    print("Processing 4.2GB file in chunks...")
    
    with open(SQL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        # Read line by line for INSERT statements
        for line in f:
            line_count += 1
            
            if 'algorithm_performance' in line and 'VALUES' in line:
                # Extract algorithm data
                # Pattern: (id, 'name', 'type', total_picks, total_trades, win_rate, avg_return, ...)
                match = re.search(
                    r'\((\d+),\s*\'([^\']+)\',\s*\'([^\']*)\',\s*(\d+),\s*(\d+),\s*([\d.]+),\s*([\-\d.]+)',
                    line
                )
                if match:
                    alg_id, name, strat_type, total_picks, total_trades, win_rate, avg_return = match.groups()
                    algorithms.append({
                        'id': int(alg_id),
                        'name': name,
                        'type': strat_type,
                        'total_picks': int(total_picks),
                        'total_trades': int(total_trades),
                        'win_rate': float(win_rate),
                        'avg_return': float(avg_return)
                    })
            
            if line_count % 1000000 == 0:
                print(f"  Processed {line_count:,} lines, found {len(algorithms)} algorithms...")
    
    print(f"\n✓ Total: {line_count:,} lines processed")
    print(f"✓ Found {len(algorithms)} algorithms")
    
    # Save raw data
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(algorithms, f, indent=2)
    print(f"✓ Saved to {OUTPUT_FILE}")
    
    # Analysis
    print("\n" + "=" * 80)
    print("ALGORITHM PERFORMANCE ANALYSIS")
    print("=" * 80)
    
    # Best by return
    print("\n🏆 TOP 15 BY AVERAGE RETURN:")
    print("-" * 80)
    best_return = sorted(algorithms, key=lambda x: x['avg_return'], reverse=True)[:15]
    for i, alg in enumerate(best_return, 1):
        emoji = "🔥" if alg['avg_return'] > 5 else "✅" if alg['avg_return'] > 0 else "⚠️"
        print(f"{emoji} {i:2}. {alg['name'][:40]:<40} {alg['avg_return']:>+7.2f}%  WR:{alg['win_rate']:>5.1f}%  N:{alg['total_trades']}")
    
    # Worst
    print("\n🚨 WORST 10 BY AVERAGE RETURN:")
    print("-" * 80)
    worst = sorted(algorithms, key=lambda x: x['avg_return'])[:10]
    for i, alg in enumerate(worst, 1):
        print(f"🔴 {i:2}. {alg['name'][:40]:<40} {alg['avg_return']:>+7.2f}%  WR:{alg['win_rate']:>5.1f}%  N:{alg['total_trades']}")
    
    # Best by WR
    print("\n🎯 TOP 15 BY WIN RATE (min 10 trades):")
    print("-" * 80)
    filtered = [a for a in algorithms if a['total_trades'] >= 10]
    best_wr = sorted(filtered, key=lambda x: x['win_rate'], reverse=True)[:15]
    for i, alg in enumerate(best_wr, 1):
        emoji = "🔥" if alg['win_rate'] > 65 else "✅" if alg['win_rate'] > 55 else "⚠️"
        print(f"{emoji} {i:2}. {alg['name'][:40]:<40} WR:{alg['win_rate']:>5.1f}%  Return:{alg['avg_return']:>+7.2f}%")
    
    # High volume
    print("\n📊 TOP 15 BY TRADE VOLUME:")
    print("-" * 80)
    high_vol = sorted(algorithms, key=lambda x: x['total_trades'], reverse=True)[:15]
    for i, alg in enumerate(high_vol, 1):
        status = "✅" if alg['avg_return'] > 0 else "🔴"
        print(f"{status} {i:2}. {alg['name'][:40]:<40} N:{alg['total_trades']:>5}  Return:{alg['avg_return']:>+7.2f}%")
    
    # Edge identification
    print("\n" + "=" * 80)
    print("EDGE OPPORTUNITIES")
    print("=" * 80)
    
    # High confidence algorithms
    edges = [a for a in algorithms if a['win_rate'] >= 60 and a['avg_return'] > 2 and a['total_trades'] >= 10]
    edges.sort(key=lambda x: x['win_rate'], reverse=True)
    
    print(f"\nHigh-Confidence Algorithms (WR>=60%, Return>2%, N>=10): {len(edges)} found")
    for alg in edges[:15]:
        print(f"  🔥 {alg['name'][:45]:<45} WR:{alg['win_rate']:>5.1f}%  Return:{alg['avg_return']:>+6.2f}%")
    
    # Concerns
    print(f"\n🚨 High-Volume Concerns (N>=50, Return<-1%):")
    concerns = [a for a in algorithms if a['total_trades'] >= 50 and a['avg_return'] < -1]
    concerns.sort(key=lambda x: x['total_trades'], reverse=True)
    for alg in concerns[:10]:
        print(f"  🔴 {alg['name'][:45]:<45} N:{alg['total_trades']:>5}  Return:{alg['avg_return']:>+7.2f}%")
    
    # Statistical summary
    print("\n" + "=" * 80)
    print("STATISTICAL SUMMARY")
    print("=" * 80)
    
    returns = [a['avg_return'] for a in algorithms]
    win_rates = [a['win_rate'] for a in algorithms]
    volumes = [a['total_trades'] for a in algorithms]
    
    print(f"\nAlgorithms with positive returns: {sum(1 for r in returns if r > 0)}/{len(algorithms)} ({sum(1 for r in returns if r > 0)/len(algorithms)*100:.1f}%)")
    print(f"Algorithms with WR > 55%: {sum(1 for w in win_rates if w > 55)}/{len(algorithms)} ({sum(1 for w in win_rates if w > 55)/len(algorithms)*100:.1f}%)")
    print(f"Average return across all: {sum(returns)/len(returns):+.2f}%")
    print(f"Average win rate: {sum(win_rates)/len(win_rates):.1f}%")
    print(f"Total trades analyzed: {sum(volumes):,}")
    
    # Top performers by category
    print("\n" + "=" * 80)
    print("CATEGORY ANALYSIS")
    print("=" * 80)
    
    by_type = {}
    for alg in algorithms:
        t = alg['type'] or 'unknown'
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(alg)
    
    print(f"\nPerformance by Algorithm Type:")
    for t, algs in sorted(by_type.items(), key=lambda x: sum(a['avg_return'] for a in x[1])/len(x[1]), reverse=True):
        avg_ret = sum(a['avg_return'] for a in algs) / len(algs)
        avg_wr = sum(a['win_rate'] for a in algs) / len(algs)
        total_trades = sum(a['total_trades'] for a in algs)
        print(f"  {t:<25} Count:{len(algs):>3}  AvgReturn:{avg_ret:>+7.2f}%  AvgWR:{avg_wr:>5.1f}%  TotalTrades:{total_trades:,}")
    
    return algorithms

if __name__ == '__main__':
    main()
