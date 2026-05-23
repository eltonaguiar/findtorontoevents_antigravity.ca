#!/usr/bin/env python3
"""
Extract algorithm performance from SQL dump
"""
import re
import json

SQL_FILE = r'C:\Users\zerou\Downloads\ejaguiar1_stocks_apr62026_extract.sql'
OUTPUT_FILE = 'algorithm_performance_analysis.json'

def extract_algorithms():
    """Extract all algorithm performance data."""
    algorithms = []
    
    print("Scanning 4.2GB SQL file for algorithm_performance data...")
    
    with open(SQL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        # Read in chunks
        chunk_size = 100 * 1024 * 1024  # 100MB chunks
        buffer = ""
        total_read = 0
        
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            
            total_read += len(chunk)
            buffer += chunk
            
            # Find INSERT statements in buffer
            # Pattern matches: INSERT INTO `algorithm_performance`...VALUES (...),(...),...;
            pattern = r'INSERT INTO `algorithm_performance`[^;]+VALUES\s+(.+?);'
            matches = re.findall(pattern, buffer, re.DOTALL)
            
            for match in matches:
                # Parse individual rows
                # Row format: (id, 'name', 'type', picks, trades, wr, return, ...)
                rows = re.findall(
                    r'\((\d+),\s*\'([^\']*)\',\s*\'([^\']*)\',\s*(\d+),\s*(\d+),\s*([\d.]+),\s*([\-\d.]+)',
                    match
                )
                
                for row in rows:
                    alg_id, name, strat_type, total_picks, total_trades, win_rate, avg_return = row
                    algorithms.append({
                        'id': int(alg_id),
                        'name': name,
                        'type': strat_type,
                        'total_picks': int(total_picks),
                        'total_trades': int(total_trades),
                        'win_rate': float(win_rate),
                        'avg_return': float(avg_return)
                    })
            
            # Keep last 1MB in buffer for multi-chunk matches
            buffer = buffer[-1024*1024:] if len(buffer) > 1024*1024 else buffer
            
            if total_read % (500 * 1024 * 1024) == 0:
                print(f"  Processed {total_read/1024/1024/1024:.1f}GB, found {len(algorithms)} algorithms...")
    
    print(f"\nTotal: {total_read/1024/1024/1024:.1f}GB processed")
    print(f"Found {len(algorithms)} algorithms")
    
    return algorithms


def analyze_and_report(algorithms):
    """Generate comprehensive analysis."""
    
    print("\n" + "=" * 80)
    print("ALGORITHM PERFORMANCE ANALYSIS")
    print("=" * 80)
    
    # Best by return
    print("\nTOP 15 BY AVERAGE RETURN:")
    print("-" * 80)
    best_return = sorted(algorithms, key=lambda x: x['avg_return'], reverse=True)[:15]
    for i, alg in enumerate(best_return, 1):
        emoji = "[TOP]" if alg['avg_return'] > 5 else "[OK]" if alg['avg_return'] > 0 else "[BAD]"
        print(f"{emoji} {i:2}. {alg['name'][:40]:<40} {alg['avg_return']:>+7.2f}%  WR:{alg['win_rate']:>5.1f}%  N:{alg['total_trades']}")
    
    # Worst
    print("\nWORST 10 BY AVERAGE RETURN:")
    print("-" * 80)
    worst = sorted(algorithms, key=lambda x: x['avg_return'])[:10]
    for i, alg in enumerate(worst, 1):
        print(f"[CRIT] {i:2}. {alg['name'][:40]:<40} {alg['avg_return']:>+7.2f}%  WR:{alg['win_rate']:>5.1f}%  N:{alg['total_trades']}")
    
    # Best by WR
    print("\nTOP 15 BY WIN RATE (min 10 trades):")
    print("-" * 80)
    filtered = [a for a in algorithms if a['total_trades'] >= 10]
    best_wr = sorted(filtered, key=lambda x: x['win_rate'], reverse=True)[:15]
    for i, alg in enumerate(best_wr, 1):
        emoji = "[TOP]" if alg['win_rate'] > 65 else "[OK]" if alg['win_rate'] > 55 else "[BAD]"
        print(f"{emoji} {i:2}. {alg['name'][:40]:<40} WR:{alg['win_rate']:>5.1f}%  Return:{alg['avg_return']:>+7.2f}%")
    
    # High volume
    print("\nTOP 15 BY TRADE VOLUME:")
    print("-" * 80)
    high_vol = sorted(algorithms, key=lambda x: x['total_trades'], reverse=True)[:15]
    for i, alg in enumerate(high_vol, 1):
        status = "[OK]" if alg['avg_return'] > 0 else "[CRIT]"
        print(f"{status} {i:2}. {alg['name'][:40]:<40} N:{alg['total_trades']:>5}  Return:{alg['avg_return']:>+7.2f}%")
    
    # Edge opportunities
    print("\n" + "=" * 80)
    print("EDGE OPPORTUNITIES")
    print("=" * 80)
    
    # High confidence algorithms
    edges = [a for a in algorithms if a['win_rate'] >= 60 and a['avg_return'] > 2 and a['total_trades'] >= 10]
    edges.sort(key=lambda x: x['win_rate'], reverse=True)
    
    print(f"\nHigh-Confidence Algorithms (WR>=60%, Return>2%, N>=10): {len(edges)} found")
    for alg in edges[:15]:
        print(f"  [EDGE] {alg['name'][:45]:<45} WR:{alg['win_rate']:>5.1f}%  Return:{alg['avg_return']:>+6.2f}%")
    
    # Concerns
    print(f"\nHigh-Volume Concerns (N>=50, Return<-1%):")
    concerns = [a for a in algorithms if a['total_trades'] >= 50 and a['avg_return'] < -1]
    concerns.sort(key=lambda x: x['total_trades'], reverse=True)
    for alg in concerns[:10]:
        print(f"  [FIX] {alg['name'][:45]:<45} N:{alg['total_trades']:>5}  Return:{alg['avg_return']:>+7.2f}%")
    
    # Statistical summary
    print("\n" + "=" * 80)
    print("STATISTICAL SUMMARY")
    print("=" * 80)
    
    returns = [a['avg_return'] for a in algorithms]
    win_rates = [a['win_rate'] for a in algorithms]
    volumes = [a['total_trades'] for a in algorithms]
    
    positive = sum(1 for r in returns if r > 0)
    high_wr = sum(1 for w in win_rates if w > 55)
    
    print(f"\nTotal algorithms: {len(algorithms)}")
    print(f"With positive returns: {positive}/{len(algorithms)} ({positive/len(algorithms)*100:.1f}%)")
    print(f"With WR > 55%: {high_wr}/{len(algorithms)} ({high_wr/len(algorithms)*100:.1f}%)")
    print(f"Average return: {sum(returns)/len(returns):+.2f}%")
    print(f"Average win rate: {sum(win_rates)/len(win_rates):.1f}%")
    print(f"Total trades: {sum(volumes):,}")
    
    # Category analysis
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
    
    return {
        'algorithms': algorithms,
        'edges': edges[:20],
        'concerns': [{'name': a['name'], 'trades': a['total_trades'], 'return': a['avg_return']} for a in concerns[:10]],
        'stats': {
            'total': len(algorithms),
            'positive_pct': positive/len(algorithms)*100,
            'high_wr_pct': high_wr/len(algorithms)*100,
            'avg_return': sum(returns)/len(returns),
            'avg_wr': sum(win_rates)/len(win_rates),
            'total_trades': sum(volumes)
        }
    }


def main():
    algorithms = extract_algorithms()
    results = analyze_and_report(algorithms)
    
    # Save results
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n\nResults saved to: {OUTPUT_FILE}")
    
    return results


if __name__ == '__main__':
    main()
