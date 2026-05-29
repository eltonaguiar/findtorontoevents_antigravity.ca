#!/usr/bin/env python3
"""Analyze forward proven backtest results to find top strategies."""
import json

with open('baby_strategies/forward_proven_backtest_results.json') as f:
    data = json.load(f)

print('=== TOP STRATEGIES BY OVERALL PF ===')
strats = []
for name, sdata in data['results'].items():
    o = sdata.get('overall', {})
    strats.append((name, o.get('pf', 0), o.get('wr', 0), o.get('trades', 0), o.get('avg_pnl', 0), o.get('rr', 0)))
strats.sort(key=lambda x: x[1], reverse=True)
for name, pf, wr, n, apnl, rr in strats:
    marker = ' *** T2 PASS' if pf > 1.5 and wr > 45 and n > 100 else ''
    print(f'  {name:35s} PF={pf:6.2f} WR={wr:5.1f}% n={n:5d} avg_pnl={apnl:+.3f}% RR={rr:.2f}{marker}')

print()
print('=== PER-SYMBOL WINNERS (PF>2.0, WR>50%, n>30) ===')
winners = []
for name, sdata in data['results'].items():
    for sym, sd in sdata.get('per_symbol', {}).items():
        if sd.get('pf', 0) > 2.0 and sd.get('wr', 0) > 50 and sd.get('trades', 0) > 30:
            winners.append((name, sym, sd['pf'], sd['wr'], sd['trades'], sd.get('avg_pnl', 0)))
            print(f'  {name:35s} {sym:12s} PF={sd["pf"]:6.2f} WR={sd["wr"]:5.1f}% n={sd["trades"]:5d} avg_pnl={sd.get("avg_pnl",0):+.3f}%')

print()
print(f'Total winner combinations: {len(winners)}')
print()

# Check non-crypto results
import glob
print('=== NON-CRYPTO BABY STRATEGY RESULTS ===')
for f in sorted(glob.glob('baby_strategies/results/*.json')):
    with open(f) as fh:
        d = json.load(fh)
    n = d.get('n', d.get('n_trades', 0))
    wr = d.get('wr', d.get('win_rate', 0))
    pf = d.get('pf', d.get('profit_factor', 0))
    strat = d.get('strategy', d.get('name', 'unknown'))
    sym = d.get('symbol', '?')
    ac = d.get('asset_class', 'unknown')
    mdd = d.get('mdd', d.get('max_drawdown', 0))
    sharpe = d.get('sharpe', d.get('sharpe_ratio', 0))
    errs = d.get('generation_errors', 0)
    sigs = d.get('signals_generated', 0)
    marker = ' *** T2 PASS' if pf > 1.5 and wr > 0.5 and n >= 30 else ''
    print(f'  {strat:40s} {sym:12s} {ac:10s} n={n:4d} WR={wr*100:5.1f}% PF={pf:6.2f} MDD={mdd*100:5.1f}% Sharpe={sharpe:6.2f} sigs={sigs} errs={errs}{marker}')

# Check strategy variations v2
print()
print('=== STRATEGY VARIATIONS V2 RESULTS ===')
try:
    with open('baby_strategies/new_strategy_variations_framework_results_v2.json') as f:
        vdata = json.load(f)
    for s in vdata:
        n = s.get('num_trades', 0)
        wr = s.get('win_rate', 0)
        pf = s.get('profit_factor', 0)
        name = s.get('strategy', 'unknown')
        sr = s.get('sharpe_ratio', 0)
        marker = ' *** T2 PASS' if pf > 1.5 and wr > 0.5 and n >= 30 else ''
        print(f'  {name:40s} n={n:4d} WR={wr*100:5.1f}% PF={pf:6.2f} Sharpe={sr:6.2f}{marker}')
except Exception as e:
    print(f'  Error reading v2 results: {e}')
