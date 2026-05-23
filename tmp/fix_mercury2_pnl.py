#!/usr/bin/env python3
"""Fix Mercury2 closed picks: compute pnl_pct from entry_price, exit_price, direction."""

import json
import os

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'mercury2', 'data', 'closed_picks.json')

with open(DATA_FILE, 'r') as f:
    picks = json.load(f)

wins = 0
losses = 0
total_pnl = 0.0

for pick in picks:
    entry = pick.get('entry_price')
    exit_p = pick.get('exit_price')
    direction = (pick.get('direction') or pick.get('signal_type', '')).upper()

    if entry and exit_p and entry != 0:
        if direction in ('LONG', 'BUY'):
            pnl = (exit_p - entry) / entry * 100
        elif direction in ('SHORT', 'SELL'):
            pnl = (entry - exit_p) / entry * 100
        else:
            pnl = (exit_p - entry) / entry * 100  # default to long

        pick['pnl_pct'] = round(pnl, 4)
        total_pnl += pnl
        if pnl >= 0:
            wins += 1
        else:
            losses += 1
    else:
        pick['pnl_pct'] = None

with open(DATA_FILE, 'w') as f:
    json.dump(picks, f, indent=2)

total = len(picks)
avg_pnl = total_pnl / total if total > 0 else 0

print(f"=== Mercury2 Closed Picks PnL Fix ===")
print(f"Total picks:  {total}")
print(f"Wins:         {wins}")
print(f"Losses:       {losses}")
print(f"Win rate:     {wins/total*100:.1f}%" if total > 0 else "Win rate: N/A")
print(f"Avg PnL:      {avg_pnl:.4f}%")
print(f"Total PnL:    {total_pnl:.4f}%")
print(f"\nFile updated: {os.path.abspath(DATA_FILE)}")
