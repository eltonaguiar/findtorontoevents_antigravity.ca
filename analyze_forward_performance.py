#!/usr/bin/env python3
"""Analyze forward testing performance from closed picks"""

import json
from collections import defaultdict

def main():
    # Load closed picks
    with open('battleground/data/closed_picks.json', 'r') as f:
        picks = json.load(f)

    # Analyze by strategy
    by_strategy = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total_pnl': 0, 'trades': []})
    
    for pick in picks:
        strat = pick['strategy']
        if pick['status'] == 'WIN':
            by_strategy[strat]['wins'] += 1
        else:
            by_strategy[strat]['losses'] += 1
        
        by_strategy[strat]['total_pnl'] += pick['pnl_pct']
        by_strategy[strat]['trades'].append(pick['pnl_pct'])

    # Print summary
    print('='*80)
    print('FORWARD TESTING PERFORMANCE SUMMARY (Feb 24 - Mar 7, 2026)')
    print('='*80)
    print(f"{'Strategy':<50} {'Trades':<8} {'Win Rate':<10} {'Total PnL':<10} {'Avg PnL':<10}")
    print('-'*80)

    sorted_strats = sorted(by_strategy.items(), key=lambda x: x[1]['total_pnl'], reverse=True)
    
    for strat, data in sorted_strats:
        total = data['wins'] + data['losses']
        wr = data['wins'] / total if total > 0 else 0
        avg_pnl = data['total_pnl'] / total if total > 0 else 0
        print(f"{strat[:49]:<50} {total:<8} {wr:<10.1%} {data['total_pnl']:<10.2f} {avg_pnl:<10.2f}")

    print('='*80)
    
    # Summary stats
    total_trades = sum(d['wins'] + d['losses'] for d in by_strategy.values())
    total_wins = sum(d['wins'] for d in by_strategy.values())
    total_pnl = sum(d['total_pnl'] for d in by_strategy.values())
    
    print(f"\nOVERALL SUMMARY:")
    print(f"  Total Trades: {total_trades}")
    print(f"  Overall Win Rate: {total_wins/total_trades:.1%}")
    print(f"  Total PnL: {total_pnl:.2f}%")
    print(f"  Number of Strategies: {len(by_strategy)}")
    
    # Top performers
    print(f"\nTOP PERFORMERS:")
    for i, (strat, data) in enumerate(sorted_strats[:3], 1):
        total = data['wins'] + data['losses']
        wr = data['wins'] / total
        print(f"  {i}. {strat} (WR: {wr:.1%}, PnL: {data['total_pnl']:+.2f}%)")
    
    print('='*80)

if __name__ == "__main__":
    main()
