#!/usr/bin/env python3
"""Generate a detailed portfolio report."""
import json

state = json.load(open('audit_dashboard/data/claudes_test_state.json'))

for pid in ['score_leaders', 'proven_only', 'claude_best', 'high_conviction', 'consensus_plays', 'prop_conservative']:
    port = state[pid]
    ic = port['initial_capital']
    pp = port['position_pct']
    print(f"\n=== {port['name']} (method={port['methodology']}) ===")
    print(f"Capital: ${ic:,} | Per trade: {pp*100}% = ~${ic*pp:,.0f}")
    print(f"Max positions: {port['max_positions']} | Commission: 0.15%/side | Slippage: 0.05%")
    for pos in port['positions']:
        entry = pos['entry_price']
        tp = pos['take_profit']
        sl = pos['stop_loss']
        d = pos['direction']
        if d == 'LONG':
            sl_pct = abs(entry - sl) / entry * 100
            tp_pct = abs(tp - entry) / entry * 100
        else:
            sl_pct = abs(sl - entry) / entry * 100
            tp_pct = abs(entry - tp) / entry * 100
        print(f"  {pos['symbol']:12s} {d:5s} entry={entry:.6g} TP(+{tp_pct:.1f}%) SL(-{sl_pct:.1f}%) R:R={pos['rr']:.1f} conf={pos['confidence']} size=${pos['size_usd']:,.0f} comm=${pos['commission_entry']:.2f} sys={pos['source_system']}")

print("\n\n=== FULL TRADING PARAMETERS (Auditor Reference) ===")
print("Exchange: Binance (simulated paper trading)")
print("Commission: 0.15% per side (IBKR Canadian broker rate)")
print("Slippage: 0.05% per side (estimated for liquid pairs)")
print("Round-trip cost: 0.40% total (0.15% x2 commission + 0.05% x2 slippage)")
print("TP/SL: Set by source system strategy at entry, NOT modified after")
print("Position sizing: % of current cash balance, varies by portfolio")
print("No leverage used")
print("No margin")
print("Funding rate: NOT included (material for holds >24h)")
print("Market hours: 24/7 crypto, market hours for equity")
print("Price source: Binance spot API (live, updated each cycle)")
print("Update frequency: Every 30 min (120 min for swing)")
print("Exit conditions: TP hit OR SL hit (no trailing stops, no time-based exits)")
