#!/usr/bin/env python3
"""Find and audit entries with suspiciously high PnL (>100%)"""

import json

with open('alpha_engine/data/prove_winners_results.json', 'r') as f:
    data = json.load(f)

print('=== ENTRIES WITH |PnL| > 100% ===')
found = 0
for i, entry in enumerate(data):
    pnl = entry.get('total_pnl_pct', 0)
    if abs(pnl) > 100:
        found += 1
        print(f'\n[{i}] Strategy: {entry.get("strategy")}')
        print(f'    Total PnL: {pnl}%')
        print(f'    Trades: {entry.get("total_trades")}')
        print(f'    Win Rate: {entry.get("win_rate")}%')
        print(f'    Avg Win: {entry.get("avg_win")}%')
        print(f'    Avg Loss: {entry.get("avg_loss")}%')
        print(f'    Verdict: {entry.get("verdict")}')
        
        # Check symbol breakdown for individual high PnL
        sym_breakdown = entry.get('sym_breakdown', {})
        high_sym = {k: v for k, v in sym_breakdown.items() if abs(v.get('pnl', 0)) > 50}
        if high_sym:
            print(f'    HIGH PnL SYMBOLS (>50%):')
            for sym, vals in high_sym.items():
                print(f'      {sym}: {vals.get("pnl"):+.2f}% ({vals.get("n")} trades)')

if not found:
    print("None found in prove_winners_results.json")

# Also check other files
print('\n' + '='*60)
print('Checking challenge_v3_history.json...')
try:
    with open('alpha_engine/data/challenge_v3_history.json', 'r') as f:
        hist = json.load(f)
    for i, entry in enumerate(hist.get('history', [])):
        pnl = entry.get('total_pnl_pct', 0)
        if abs(pnl) > 100:
            print(f'  [{i}] {entry.get("strategy", "unknown")}: {pnl}%')
except Exception as e:
    print(f'  Error: {e}')
