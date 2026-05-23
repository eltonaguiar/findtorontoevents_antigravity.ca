#!/usr/bin/env python3
"""Analyze SHORT strategies to identify profitable ones for exemption."""

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    with open(ROOT / "audit_trail" / "data" / "dashboard_payload.json") as f:
        data = json.load(f)

    all_picks = data['picks']['active'] + data['picks'].get('recent_closed', [])
    short_picks = [p for p in all_picks if p.get('direction', '').upper() == 'SHORT']

    print('=' * 80)
    print('SHORT STRATEGY ANALYSIS - Profitable Shorts for Exemption')
    print('=' * 80)
    print(f'Total SHORT picks analyzed: {len(short_picks)}')
    print()

    # Group by strategy
    by_strategy = defaultdict(lambda: {'pnls': [], 'wins': 0, 'total': 0, 'sources': set()})

    for p in short_picks:
        strat = p.get('strategy', 'unknown') or 'unknown'
        pnl = p.get('pnl_pct', 0) or 0
        by_strategy[strat]['pnls'].append(pnl)
        by_strategy[strat]['total'] += 1
        if pnl > 0:
            by_strategy[strat]['wins'] += 1
        by_strategy[strat]['sources'].add(p.get('source_system', 'unknown'))

    # Find profitable strategies (WR >= 50% and positive avg PnL)
    profitable = []
    for strat, stats in by_strategy.items():
        if stats['total'] >= 5:  # Minimum sample size
            wr = stats['wins'] / stats['total'] * 100
            avg_pnl = sum(stats['pnls']) / len(stats['pnls'])
            total_pnl = sum(stats['pnls'])
            if wr >= 50 and avg_pnl > 0:
                profitable.append({
                    'strategy': strat,
                    'trades': stats['total'],
                    'wins': stats['wins'],
                    'wr': wr,
                    'avg_pnl': avg_pnl,
                    'total_pnl': total_pnl,
                    'sources': stats['sources']
                })

    # Sort by total PnL
    profitable.sort(key=lambda x: -x['total_pnl'])

    print(f'Found {len(profitable)} PROFITABLE short strategies (WR>=50%, +PnL, 5+ trades)')
    print(f'out of {len(by_strategy)} total short strategies')
    print()
    print('=' * 80)

    for p in profitable[:15]:
        print(f"Strategy: {p['strategy'][:60]}")
        print(f"  Trades: {p['trades']}, Wins: {p['wins']}, WR: {p['wr']:.1f}%")
        print(f"  Avg PnL: {p['avg_pnl']:+.4f}%, Total PnL: {p['total_pnl']:+.2f}%")
        print(f"  Sources: {', '.join(p['sources'])}")
        print()

    # Also check contrarian_consensus specifically
    print('=' * 80)
    print('CONTRARIAN CONSENSUS SHORT SPECIFIC ANALYSIS')
    print('=' * 80)
    contrarian_shorts = [p for p in all_picks 
                         if p.get('strategy', '').lower() == 'contrarian_consensus' 
                         and p.get('direction', '').upper() == 'SHORT']
    if contrarian_shorts:
        pnls = [p.get('pnl_pct', 0) or 0 for p in contrarian_shorts]
        wins = sum(1 for pnl in pnls if pnl > 0)
        wr = wins / len(pnls) * 100
        avg_pnl = sum(pnls) / len(pnls)
        print(f"Trades: {len(contrarian_shorts)}, Wins: {wins}, WR: {wr:.1f}%, Avg PnL: {avg_pnl:+.4f}%")
        print("\nRecent trades:")
        for p in contrarian_shorts[-5:]:
            print(f"  {p.get('symbol', 'N/A')} {p.get('direction', 'N/A')}: {p.get('pnl_pct', 0):+.2f}%")
    else:
        print("No contrarian_consensus SHORT picks found")

    print()
    print('=' * 80)
    print('RECOMMENDATION')
    print('=' * 80)
    if profitable:
        print("The following SHORT strategies should be EXEMPTED from the blanket SHORT block:")
        for p in profitable[:10]:
            print(f"  - '{p['strategy']}': {p['wr']:.1f}% WR, {p['avg_pnl']:+.4f}% avg PnL")
    else:
        print("No profitable SHORT strategies found with current criteria.")

if __name__ == "__main__":
    main()
