#!/usr/bin/env python3
"""Analyze validated dataset to verify real statistics vs fabricated claims"""

import json
from collections import defaultdict

# Load the validated dataset
with open('audit_trail/data/universal_resolved_picks.json', 'r') as f:
    picks = json.load(f)

print(f"=" * 80)
print(f"VALIDATED DATASET ANALYSIS (universal_resolved_picks.json)")
print(f"=" * 80)
print(f"Total picks in validated dataset: {len(picks)}")

print(f"\n{'='*80}")
print("ASSET CLASS BREAKDOWN")
print(f"{'='*80}")
print(f"\n{'Asset Class':<15} {'Total':>8} {'Wins':>8} {'Losses':>8} {'WR%':>8} {'PF':>8}")
print("-" * 60)

asset_stats = {}
for p in picks:
    ac = p.get('asset_class', 'UNKNOWN')
    if ac not in asset_stats:
        asset_stats[ac] = {'total': 0, 'wins': 0, 'losses': 0, 'gross_wins': 0, 'gross_losses': 0}
    asset_stats[ac]['total'] += 1
    pnl = p.get('pnl_pct', 0)
    if pnl > 0:
        asset_stats[ac]['wins'] += 1
        asset_stats[ac]['gross_wins'] += pnl
    else:
        asset_stats[ac]['losses'] += 1
        asset_stats[ac]['gross_losses'] += abs(pnl)

for ac, s in sorted(asset_stats.items(), key=lambda x: x[1]['total'], reverse=True):
    wr = (s['wins'] / s['total'] * 100) if s['total'] > 0 else 0
    pf = (s['gross_wins'] / s['gross_losses']) if s['gross_losses'] > 0 else float('inf')
    pf_str = f"{pf:.2f}" if pf != float('inf') else "N/A"
    print(f"{ac:<15} {s['total']:>8} {s['wins']:>8} {s['losses']:>8} {wr:>7.1f}% {pf_str:>8}")

print(f"\n{'='*80}")
print("STRATEGY ANALYSIS (TOP 30 BY SAMPLE SIZE)")
print(f"{'='*80}")
print(f"\n{'Strategy':<55} {'n':>5} {'WR%':>8} {'PF':>8} {'AvgPnL':>10}")
print("-" * 90)

strategy_stats = {}
for p in picks:
    strat = p.get('strategy', 'unknown')
    src = p.get('source_system', 'unknown')
    key = f"[{src}] {strat}"
    if key not in strategy_stats:
        strategy_stats[key] = {'total': 0, 'wins': 0, 'losses': 0, 'gross_wins': 0, 'gross_losses': 0, 'avg_pnl': 0}
    strategy_stats[key]['total'] += 1
    pnl = p.get('pnl_pct', 0)
    strategy_stats[key]['avg_pnl'] += pnl
    if pnl > 0:
        strategy_stats[key]['wins'] += 1
        strategy_stats[key]['gross_wins'] += pnl
    else:
        strategy_stats[key]['losses'] += 1
        strategy_stats[key]['gross_losses'] += abs(pnl)

for k, s in sorted(strategy_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:30]:
    wr = (s['wins'] / s['total'] * 100) if s['total'] > 0 else 0
    pf = (s['gross_wins'] / s['gross_losses']) if s['gross_losses'] > 0 else float('inf')
    pf_str = f"{pf:.2f}" if pf != float('inf') else "N/A"
    avg = s['avg_pnl'] / s['total'] if s['total'] > 0 else 0
    print(f"{k[:55]:<55} {s['total']:>5} {wr:>7.1f}% {pf_str:>8} {avg:>9.2f}%")

print(f"\n{'='*80}")
print("CHECKING SPECIFIC CLAIMED STRATEGIES")
print(f"{'='*80}")

# Check ml_enhanced specifically
ml_enhanced_picks = [p for p in picks if 'ml_enhanced' in p.get('strategy', '').lower() or 'ml_enhanced' in str(p)]
print(f"\n--- ml_enhanced strategy check ---")
print(f"ml_enhanced mentions: {len(ml_enhanced_picks)}")

# Check kimi_signal_tracking
kimi_picks = [p for p in picks if 'kimi_signal_tracking' in p.get('strategy', '').lower() or 'kimi_signal_tracking' in str(p)]
print(f"kimi_signal_tracking mentions: {len(kimi_picks)}")

# Check aggregated_picks
agg_picks = [p for p in picks if 'aggregated_picks' in p.get('strategy', '').lower() or 'aggregated_picks' in str(p)]
print(f"aggregated_picks mentions: {len(agg_picks)}")

# Check cot_positioning
cot_picks = [p for p in picks if 'cot_positioning' in p.get('strategy', '').lower() or 'cot_positioning' in str(p)]
print(f"cot_positioning mentions: {len(cot_picks)}")

# Check by source_system
print(f"\n{'='*80}")
print("SOURCE SYSTEM BREAKDOWN")
print(f"{'='*80}")

src_stats = {}
for p in picks:
    src = p.get('source_system', 'unknown')
    if src not in src_stats:
        src_stats[src] = {'total': 0, 'wins': 0, 'losses': 0, 'gross_wins': 0, 'gross_losses': 0}
    src_stats[src]['total'] += 1
    pnl = p.get('pnl_pct', 0)
    if pnl > 0:
        src_stats[src]['wins'] += 1
        src_stats[src]['gross_wins'] += pnl
    else:
        src_stats[src]['losses'] += 1
        src_stats[src]['gross_losses'] += abs(pnl)

print(f"\n{'Source System':<40} {'n':>5} {'WR%':>8} {'PF':>8}")
print("-" * 65)
for src, s in sorted(src_stats.items(), key=lambda x: x[1]['total'], reverse=True):
    wr = (s['wins'] / s['total'] * 100) if s['total'] > 0 else 0
    pf = (s['gross_wins'] / s['gross_losses']) if s['gross_losses'] > 0 else float('inf')
    pf_str = f"{pf:.2f}" if pf != float('inf') else "N/A"
    print(f"{src:<40} {s['total']:>5} {wr:>7.1f}% {pf_str:>8}")

print(f"\n{'='*80}")
print("DIRECTION ANALYSIS")
print(f"{'='*80}")

dir_stats = defaultdict(lambda: {'total': 0, 'wins': 0, 'losses': 0, 'gross_wins': 0, 'gross_losses': 0})
for p in picks:
    direction = p.get('direction', 'UNKNOWN')
    dir_stats[direction]['total'] += 1
    pnl = p.get('pnl_pct', 0)
    if pnl > 0:
        dir_stats[direction]['wins'] += 1
        dir_stats[direction]['gross_wins'] += pnl
    else:
        dir_stats[direction]['losses'] += 1
        dir_stats[direction]['gross_losses'] += abs(pnl)

print(f"\n{'Direction':<15} {'n':>5} {'WR%':>8} {'PF':>8}")
print("-" * 40)
for direction, s in sorted(dir_stats.items(), key=lambda x: x[1]['total'], reverse=True):
    wr = (s['wins'] / s['total'] * 100) if s['total'] > 0 else 0
    pf = (s['gross_wins'] / s['gross_losses']) if s['gross_losses'] > 0 else float('inf')
    pf_str = f"{pf:.2f}" if pf != float('inf') else "N/A"
    print(f"{direction:<15} {s['total']:>5} {wr:>7.1f}% {pf_str:>8}")

print(f"\n{'='*80}")
print("CONFIDENCE BAND ANALYSIS (CRYPTO ONLY)")
print(f"{'='*80}")

conf_bands = [(0.50, 0.60), (0.60, 0.70), (0.70, 0.80), (0.80, 0.85), (0.85, 0.90), (0.90, 1.0)]
for low, high in conf_bands:
    band_picks = [p for p in picks if p.get('asset_class') == 'CRYPTO' and low <= p.get('confidence', 0) < high]
    if band_picks:
        wins = sum(1 for p in band_picks if p.get('pnl_pct', 0) > 0)
        total = len(band_picks)
        wr = wins / total * 100
        gross_wins = sum(p.get('pnl_pct', 0) for p in band_picks if p.get('pnl_pct', 0) > 0)
        gross_losses = sum(abs(p.get('pnl_pct', 0)) for p in band_picks if p.get('pnl_pct', 0) <= 0)
        pf = gross_wins / gross_losses if gross_losses > 0 else float('inf')
        pf_str = f"{pf:.2f}" if pf != float('inf') else "N/A"
        print(f"Confidence {low:.2f}-{high:.2f}: n={total:>5}, WR={wr:>6.1f}%, PF={pf_str}")

print(f"\n{'='*80}")
print("VERDICT ON PREVIOUS ANALYSIS")
print(f"{'='*80}")
print("""
CRITICISM VERIFICATION:

1. "ml_enhanced shows 33.3% WR in our dataset - COMPLETELY WRONG"
   Let's check actual ml_enhanced data:

2. "COT picks: n=0 in validated dataset"
   Let's verify: cot_positioning mentions = {len(cot_picks)}

3. "ETF in OOS: n=0"
   Let's verify actual ETF data

4. "$150k capital allocation" was FABRICATED
   This was NOT from the actual data
""")