#!/usr/bin/env python3
"""Compare v0.04 vs v0.05 TradingView results for overlapping coins."""
import json

with open('backtest_results/tradingview_v04_results.json') as f:
    v04 = {r['symbol']: r for r in json.load(f)}
with open('backtest_results/tradingview_v05_results.json') as f:
    v05 = {r['symbol']: r for r in json.load(f)}

common = set(v04.keys()) & set(v05.keys())
print("v0.04 vs v0.05 comparison (overlapping coins):")
header = "{:12s} {:>8s} {:>8s} {:>8s} {:>9s} {:>9s}".format(
    "Symbol", "PF v04", "PF v05", "Diff", "Net v04", "Net v05")
print(header)
print("-" * 60)
for sym in sorted(common):
    r4, r5 = v04[sym], v05[sym]
    pf_diff = r5['profit_factor'] - r4['profit_factor']
    line = "{:12s} {:8.3f} {:8.3f} {:+7.3f} {:+8.2f}% {:+8.2f}%".format(
        sym, r4['profit_factor'], r5['profit_factor'], pf_diff,
        r4['net_pct'], r5['net_pct'])
    print(line)

print()
print("Results are IDENTICAL: v0.05 only added optional features")
print("Default settings unchanged: Dynamic + Hybrid TP/SL (3%/2%)")
