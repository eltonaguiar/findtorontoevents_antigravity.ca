#!/usr/bin/env python3
"""
Bundle Test - Test top SOC performers in ensembles
Sort by Forward Sharpe, require minimum sample size
"""

import json
from pathlib import Path
from collections import defaultdict
import statistics

META_DIR = Path('incubator/agents/web_ai')

print("=" * 90)
print("BUNDLE TEST - Top SOC Performers (Sorted by Forward Sharpe)")
print("=" * 90)
print("Minimum 5 forward trades required for statistical validity")
print("=" * 90)

# Load all meta files
all_strategies = []

for meta_file in META_DIR.glob('*.meta.json'):
    try:
        with open(meta_file, 'r') as f:
            data = json.load(f)
        
        name = data.get('strategy_name', meta_file.stem)
        fwd = data.get('forward_metrics', {})
        bt = data.get('backtest_metrics', {})
        
        if not fwd:
            continue
        
        all_strategies.append({
            'name': name,
            'fwd_sharpe': fwd.get('sharpe') or 0,
            'fwd_trades': fwd.get('total_trades') or 0,
            'fwd_wr': fwd.get('win_rate') or 0,
            'fwd_dd': fwd.get('max_drawdown') or 0,
            'bt_sharpe': bt.get('sharpe') or 0,
            'bt_trades': bt.get('total_trades') or 0,
        })
    except:
        pass

# Filter to SOC strategies only
soc_strategies = [s for s in all_strategies if 'crypto_soc' in s['name'] or 'crypto_drawdown' in s['name']]

print(f"\nTotal SOC strategies: {len(soc_strategies)}")

# Tier 1: Sufficient sample size (>=5 trades)
tier1 = [s for s in soc_strategies if s['fwd_trades'] >= 5]
tier1_sorted = sorted(tier1, key=lambda x: x['fwd_sharpe'], reverse=True)

print(f"\n{'='*90}")
print(f"TIER 1: Sufficient Sample Size (>=5 forward trades) - {len(tier1)} strategies")
print(f"{'='*90}")
print(f"{'Rank':<6} {'Strategy':<50} {'FW Sharpe':>10} {'Trades':>8} {'FW WR':>8} {'BT Sharpe':>10}")
print("-" * 90)

for i, s in enumerate(tier1_sorted[:15], 1):
    print(f"{i:<6} {s['name'][:50]:<50} {s['fwd_sharpe']:>10.2f} {s['fwd_trades']:>8} {s['fwd_wr']*100:>7.0f}% {s['bt_sharpe']:>10.2f}")

# Tier 2: Insufficient sample size (2-4 trades)
tier2 = [s for s in soc_strategies if 2 <= s['fwd_trades'] < 5]
tier2_sorted = sorted(tier2, key=lambda x: x['fwd_sharpe'], reverse=True)

print(f"\n{'='*90}")
print(f"TIER 2: Insufficient Sample (2-4 trades) - {len(tier2)} strategies - WATCH LIST")
print(f"{'='*90}")
print(f"{'Rank':<6} {'Strategy':<50} {'FW Sharpe':>10} {'Trades':>8} {'FW WR':>8} {'Status':>15}")
print("-" * 90)

for i, s in enumerate(tier2_sorted[:10], 1):
    status = "SUSPICIOUS" if s['fwd_sharpe'] > 10 else "MONITOR"
    print(f"{i:<6} {s['name'][:50]:<50} {s['fwd_sharpe']:>10.2f} {s['fwd_trades']:>8} {s['fwd_wr']*100:>7.0f}% {status:>15}")

# Tier 3: Single trade or none
tier3 = [s for s in soc_strategies if s['fwd_trades'] < 2]

print(f"\n{'='*90}")
print(f"TIER 3: No Valid Data (<2 trades) - {len(tier3)} strategies - IGNORE")
print(f"{'='*90}")
print(f"These strategies have insufficient data to evaluate:")
for s in tier3[:5]:
    print(f"  - {s['name']}: {s['fwd_trades']} trades")
if len(tier3) > 5:
    print(f"  ... and {len(tier3)-5} more")

# BUNDLE RECOMMENDATIONS
print(f"\n{'='*90}")
print("BUNDLE RECOMMENDATIONS (Ensemble Top Performers)")
print(f"{'='*90}")

# Create bundles by base strategy name
bundles = defaultdict(list)
for s in soc_strategies:
    if s['fwd_trades'] >= 2:  # At least some data
        # Extract base name
        parts = s['name'].split('_a')
        if len(parts) > 1:
            base = parts[0]
            bundles[base].append(s)

print("\nRecommended Bundles (variants with >=2 trades):")
for base, variants in sorted(bundles.items()):
    if len(variants) >= 3:  # Only show bundles with 3+ variants
        total_trades = sum(v['fwd_trades'] for v in variants)
        weighted_sharpe = sum(v['fwd_sharpe'] * v['fwd_trades'] for v in variants) / total_trades if total_trades > 0 else 0
        
        print(f"\n  {base}:")
        print(f"    Variants: {len(variants)}")
        print(f"    Total Forward Trades: {total_trades}")
        print(f"    Weighted Avg Sharpe: {weighted_sharpe:.2f}")
        print(f"    Top 3 Variants:")
        for v in sorted(variants, key=lambda x: x['fwd_sharpe'], reverse=True)[:3]:
            print(f"      - {v['name'][-10:]}: Sharpe {v['fwd_sharpe']:.2f} ({v['fwd_trades']} trades)")

# Final verdict
print(f"\n{'='*90}")
print("FINAL VERDICT")
print(f"{'='*90}")
print(f"""
ANALYSIS:
- {len(tier1)} strategies have sufficient sample size (>=5 trades)
- {len(tier2)} strategies need more data (2-4 trades)  
- {len(tier3)} strategies have no valid data (<2 trades)

TOP PERFORMERS (Tier 1, by Forward Sharpe):
""")

for i, s in enumerate(tier1_sorted[:5], 1):
    print(f"{i}. {s['name']}: Sharpe {s['fwd_sharpe']:.2f} ({s['fwd_trades']} trades, {s['fwd_wr']*100:.0f}% WR)")

print(f"""
RECOMMENDATIONS:
1. DISABLE all Tier 3 strategies (<2 trades) - no statistical validity
2. CREATE ENSEMBLES for each base strategy (average variants together)
3. REQUIRE minimum 20 forward trades before promoting to live
4. SET MAXIMUM Sharpe cap at 5.0 - anything higher is data error
5. MERGE the 10 parameter variants per strategy into 1 ensemble
""")
print("=" * 90)
