#!/usr/bin/env python3
"""
Comprehensive audit of ALL incubator/agents/web_ai/ strategies
Flags overfitted parameter variants and fantasy metrics
"""

import json
from pathlib import Path
from collections import defaultdict

META_DIR = Path('incubator/agents/web_ai')

print("=" * 90)
print("INCUBATOR STRATEGY AUDIT - Checking 409 strategy variants")
print("=" * 90)

# Collect all meta.json files
meta_files = list(META_DIR.glob('*.meta.json'))
print(f"Found {len(meta_files)} meta.json files\n")

# Audit statistics
fantasy_sharpe = []  # Sharpe > 10
single_trade = []    # Only 1 forward trade
backtest_only = []   # No forward trades yet
forward_better = []  # Forward Sharpe > Backtest Sharpe (suspicious)
soc_variants = defaultdict(list)  # Group by base strategy name

total_audited = 0

for meta_file in meta_files:
    try:
        with open(meta_file, 'r') as f:
            data = json.load(f)
        
        total_audited += 1
        name = data.get('strategy_name', meta_file.stem)
        
        # Extract forward metrics
        fwd = data.get('forward_metrics', {})
        fwd_sharpe = fwd.get('sharpe', 0)
        fwd_trades = fwd.get('total_trades', 0)
        fwd_wr = fwd.get('win_rate', 0)
        
        # Extract backtest metrics
        bt = data.get('backtest_metrics', {})
        bt_sharpe = bt.get('sharpe', 0)
        
        # Categorize
        # 1. Fantasy Sharpe (>10 is unrealistic, >5 is excellent)
        if fwd_sharpe > 10:
            fantasy_sharpe.append({
                'name': name,
                'sharpe': fwd_sharpe,
                'trades': fwd_trades,
                'win_rate': fwd_wr
            })
        
        # 2. Single trade (insufficient data)
        if fwd_trades == 1:
            single_trade.append({
                'name': name,
                'sharpe': fwd_sharpe,
                'win_rate': fwd_wr
            })
        
        # 3. Backtest only (no forward data)
        if fwd_trades == 0:
            backtest_only.append(name)
        
        # 4. Forward better than backtest (suspicious)
        elif bt_sharpe > 0 and fwd_sharpe > bt_sharpe * 2:
            forward_better.append({
                'name': name,
                'bt_sharpe': bt_sharpe,
                'fwd_sharpe': fwd_sharpe,
                'trades': fwd_trades
            })
        
        # 5. Group SOC variants
        if 'crypto_soc' in name or 'crypto_drawdown' in name:
            # Extract base name (e.g., crypto_soc_mtf_orb_pivots from crypto_soc_mtf_orb_pivots_a01_v1)
            parts = name.split('_a')
            if len(parts) > 1:
                base = parts[0]
                variant = 'a' + parts[1]
                soc_variants[base].append({
                    'variant': variant,
                    'sharpe': fwd_sharpe,
                    'trades': fwd_trades,
                    'win_rate': fwd_wr
                })
        
    except Exception as e:
        pass

# Report findings
print("=" * 90)
print("AUDIT RESULTS")
print("=" * 90)

print(f"\n[1] FANTASY SHARPE RATIOS (>10.0) - {len(fantasy_sharpe)} strategies")
print("-" * 90)
if fantasy_sharpe:
    for s in sorted(fantasy_sharpe, key=lambda x: x['sharpe'], reverse=True)[:10]:
        print(f"  {s['name'][:50]:<50} Sharpe: {s['sharpe']:>8.2f}  ({s['trades']} trades, {s['win_rate']*100:.0f}% WR)")
else:
    print("  None found")

print(f"\n[2] SINGLE TRADE STRATEGIES - {len(single_trade)} strategies")
print("-" * 90)
if single_trade:
    for s in sorted(single_trade, key=lambda x: x['sharpe'], reverse=True):
        print(f"  {s['name'][:50]:<50} Sharpe: {s['sharpe']:>8.2f}  ({s['win_rate']*100:.0f}% WR)")
else:
    print("  None found")

print(f"\n[3] BACKTEST ONLY (No Forward Trades) - {len(backtest_only)} strategies")
print("-" * 90)
print(f"  {len(backtest_only)} strategies have 0 forward trades")

print(f"\n[4] FORWARD >> BACKTEST (Suspicious) - {len(forward_better)} strategies")
print("-" * 90)
if forward_better:
    for s in sorted(forward_better, key=lambda x: x['fwd_sharpe'], reverse=True)[:10]:
        print(f"  {s['name'][:50]:<50} BT: {s['bt_sharpe']:>6.2f} -> FWD: {s['fwd_sharpe']:>6.2f} ({s['trades']} trades)")

print(f"\n[5] SOC PARAMETER VARIANTS - {len(soc_variants)} base strategies")
print("-" * 90)
for base, variants in sorted(soc_variants.items()):
    total_fwd_trades = sum(v['trades'] for v in variants)
    avg_sharpe = sum(v['sharpe'] for v in variants) / len(variants) if variants else 0
    print(f"\n  {base}: {len(variants)} variants, {total_fwd_trades} total forward trades")
    print(f"    Variants: {', '.join(sorted(v['variant'] for v in variants))}")
    print(f"    Avg Sharpe: {avg_sharpe:.2f}")
    
    # Show best variant
    if variants:
        best = max(variants, key=lambda x: x['sharpe'])
        print(f"    Best: {best['variant']} (Sharpe: {best['sharpe']:.2f}, {best['trades']} trades)")

print("\n" + "=" * 90)
print("RECOMMENDATION: Parameter grid search without validation = OVERFITTING")
print("These 10 variants per strategy need to be merged/ensembled or culled.")
print("=" * 90)
