"""
Stream analysis of large SQL file
"""
import re
import json
from collections import defaultdict

SQL_FILE = r'C:\Users\zerou\Downloads\ejaguiar1_stocks_apr62026_extract.sql'


def stream_analyze():
    """Stream through the large SQL file."""
    
    table_counts = defaultdict(int)
    algorithms = []
    picks_sample = []
    rolling_perf = []
    
    print("Streaming analysis of 4.2GB SQL file...")
    print("This may take a few minutes...")
    print()
    
    with open(SQL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        line_num = 0
        for line in f:
            line_num += 1
            
            # Track table counts from INSERT statements
            if line.startswith('INSERT INTO'):
                match = re.search(r'INSERT INTO `([^`]+)`', line)
                if match:
                    table_counts[match.group(1)] += 1
            
            # Extract algorithm_performance data
            if 'algorithm_performance' in line and 'VALUES' in line:
                try:
                    # Parse algorithm_performance line
                    match = re.search(r'\((\d+),\s*\'([^\']+)\',\s*\'([^\']*)\',\s*(\d+),\s*(\d+),\s*([\d.]+),\s*([\-\d.]+)', line)
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
                except:
                    pass
            
            # Extract rolling performance
            if 'algorithm_rolling_perf' in line and 'VALUES' in line:
                try:
                    # Parse rolling perf - different format
                    match = re.search(r'VALUES \((\d+),\s*\'([^\']+)\',\s*\'([^\']+)\',\s*\'([^\']+)\',\s*\'([^\']+)\',\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)', line)
                    if match:
                        perf_id, table, algo, period, date, total, resolved, wins, losses, wr = match.groups()
                        rolling_perf.append({
                            'algorithm': algo,
                            'period': period,
                            'total_picks': int(total),
                            'resolved': int(resolved),
                            'wins': int(wins),
                            'losses': int(losses),
                            'win_rate': float(wr)
                        })
                except:
                    pass
            
            # Sample picks
            if 'alpha_picks' in line and len(picks_sample) < 500:
                try:
                    # Simple extraction of ticker and strategy
                    match = re.search(r'VALUES \(\d+,\s*\'([^\']+)\',\s*\'([^\']+)\'', line)
                    if match:
                        ticker, strategy = match.groups()
                        picks_sample.append({'ticker': ticker, 'strategy': strategy})
                except:
                    pass
            
            if line_num % 500000 == 0:
                print(f"  Processed {line_num:,} lines... Found {len(algorithms)} algorithms, {len(rolling_perf)} rolling records")
    
    print(f"\nCompleted: {line_num:,} lines processed")
    
    return table_counts, algorithms, rolling_perf, picks_sample


def analyze_and_report(table_counts, algorithms, rolling_perf, picks_sample):
    """Generate analysis report."""
    
    print("\n" + "=" * 80)
    print("DATABASE ANALYSIS REPORT")
    print("=" * 80)
    
    # Table counts
    print("\nTABLE RECORD COUNTS:")
    print("-" * 80)
    for table, count in sorted(table_counts.items(), key=lambda x: x[1], reverse=True)[:25]:
        print(f"  {table:<45} {count:>10,} records")
    
    # Algorithm analysis
    print("\n" + "=" * 80)
    print("ALGORITHM PERFORMANCE ANALYSIS")
    print("=" * 80)
    
    if algorithms:
        print(f"\nTotal algorithms analyzed: {len(algorithms)}")
        
        # Best by return
        print("\n🏆 TOP 15 BY AVERAGE RETURN:")
        print("-" * 80)
        best_return = sorted(algorithms, key=lambda x: x['avg_return'], reverse=True)[:15]
        for i, alg in enumerate(best_return, 1):
            status = "🔥" if alg['avg_return'] > 5 else "✅" if alg['avg_return'] > 0 else "⚠️"
            print(f"{status} {i:2}. {alg['name'][:38]:<38} {alg['avg_return']:>+7.2f}%  WR:{alg['win_rate']:>5.1f}%  N:{alg['total_trades']}")
        
        # Worst by return
        print("\n🚨 WORST 10 BY AVERAGE RETURN (FIX IMMEDIATELY):")
        print("-" * 80)
        worst_return = sorted(algorithms, key=lambda x: x['avg_return'])[:10]
        for i, alg in enumerate(worst_return, 1):
            print(f"🔴 {i:2}. {alg['name'][:38]:<38} {alg['avg_return']:>+7.2f}%  WR:{alg['win_rate']:>5.1f}%  N:{alg['total_trades']}")
        
        # Best by win rate
        print("\n🎯 TOP 15 BY WIN RATE:")
        print("-" * 80)
        best_wr = sorted(algorithms, key=lambda x: x['win_rate'], reverse=True)[:15]
        for i, alg in enumerate(best_wr, 1):
            emoji = "🔥" if alg['win_rate'] > 65 else "✅" if alg['win_rate'] > 55 else "⚠️"
            print(f"{emoji} {i:2}. {alg['name'][:38]:<38} WR:{alg['win_rate']:>5.1f}%  Return:{alg['avg_return']:>+7.2f}%  N:{alg['total_trades']}")
        
        # High volume algorithms
        print("\n📊 TOP 15 BY TRADE VOLUME:")
        print("-" * 80)
        high_vol = sorted(algorithms, key=lambda x: x['total_trades'], reverse=True)[:15]
        for i, alg in enumerate(high_vol, 1):
            status = "✅" if alg['avg_return'] > 0 else "🔴"
            print(f"{status} {i:2}. {alg['name'][:38]:<38} N:{alg['total_trades']:>5}  WR:{alg['win_rate']:>5.1f}%  Return:{alg['avg_return']:>+7.2f}%")
        
        # Edge identification
        print("\n" + "=" * 80)
        print("EDGE OPPORTUNITIES IDENTIFIED")
        print("=" * 80)
        
        edges = []
        
        # High win rate + positive return
        for alg in algorithms:
            if alg['win_rate'] >= 60 and alg['avg_return'] > 2 and alg['total_trades'] >= 10:
                edges.append({
                    'type': 'high_confidence',
                    'name': alg['name'],
                    'win_rate': alg['win_rate'],
                    'return': alg['avg_return'],
                    'trades': alg['total_trades']
                })
        
        edges.sort(key=lambda x: x['win_rate'], reverse=True)
        
        print(f"\nHigh-Confidence Algorithms (WR>=60%, Return>2%, N>=10):")
        for edge in edges[:10]:
            print(f"  🔥 {edge['name'][:40]:<40} WR:{edge['win_rate']:>5.1f}%  Return:{edge['return']:>+6.2f}%")
        
        # Volume opportunities (high volume but underperforming)
        print(f"\nHigh-Volume Concerns (High N but poor performance):")
        concerns = [a for a in algorithms if a['total_trades'] >= 50 and a['avg_return'] < -1]
        concerns.sort(key=lambda x: x['total_trades'], reverse=True)
        for alg in concerns[:10]:
            print(f"  🔴 {alg['name'][:40]:<40} N:{alg['total_trades']:>5}  Return:{alg['avg_return']:>+7.2f}%")
    
    # Rolling performance analysis
    if rolling_perf:
        print("\n" + "=" * 80)
        print("ROLLING PERFORMANCE INSIGHTS")
        print("=" * 80)
        
        by_algo = defaultdict(list)
        for perf in rolling_perf:
            by_algo[perf['algorithm']].append(perf)
        
        print(f"\nAlgorithms with rolling data: {len(by_algo)}")
        
        # Find consistent performers
        consistent = []
        for algo, perfs in by_algo.items():
            if len(perfs) >= 2:
                wrs = [p['win_rate'] for p in perfs]
                avg_wr = sum(wrs) / len(wrs)
                consistency = max(wrs) - min(wrs)  # Lower = more consistent
                if avg_wr > 55 and consistency < 20:
                    consistent.append({
                        'algo': algo,
                        'avg_wr': avg_wr,
                        'consistency': consistency,
                        'periods': len(perfs)
                    })
        
        consistent.sort(key=lambda x: x['avg_wr'], reverse=True)
        print("\nMost Consistent Performers (stable WR across periods):")
        for c in consistent[:10]:
            print(f"  ✅ {c['algo'][:40]:<40} Avg WR:{c['avg_wr']:>5.1f}%  Consistency:{c['consistency']:>4.1f}%")
    
    # Picks sample
    if picks_sample:
        print("\n" + "=" * 80)
        print("PICKS SAMPLE ANALYSIS")
        print("=" * 80)
        
        by_strategy = defaultdict(int)
        for pick in picks_sample:
            by_strategy[pick['strategy']] += 1
        
        print(f"\nSampled {len(picks_sample)} picks across {len(by_strategy)} strategies")
        print("\nTop strategies by pick volume (sample):")
        for strat, count in sorted(by_strategy.items(), key=lambda x: x[1], reverse=True)[:15]:
            print(f"  {strat:<40} {count:>5} picks")
    
    # Save results
    results = {
        'table_counts': dict(table_counts),
        'algorithms': algorithms,
        'edges': edges[:20] if 'edges' in dir() else [],
        'concerns': [{'name': a['name'], 'trades': a['total_trades'], 'return': a['avg_return']} 
                     for a in (concerns[:10] if 'concerns' in dir() else [])]
    }
    
    with open('sql_streaming_analysis.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("\n✅ Results saved to: sql_streaming_analysis.json")
    
    return results


def main():
    table_counts, algorithms, rolling_perf, picks_sample = stream_analyze()
    results = analyze_and_report(table_counts, algorithms, rolling_perf, picks_sample)
    return results


if __name__ == '__main__':
    main()
