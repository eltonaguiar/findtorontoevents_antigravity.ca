#!/usr/bin/env python3
"""View the transparency dashboard"""

import json
from datetime import datetime

with open('stabilization/transparency_dashboard.json', 'r') as f:
    dash = json.load(f)

print("=" * 80)
print("ALPHA ENGINE TRANSPARENCY DASHBOARD")
print(f"Generated: {dash['generated_at']}")
print(f"Status: {dash['system_status']}")
print("=" * 80)

print("\n[SUMMARY]")
s = dash['summary']
print(f"  Total Strategies:    {s['total_strategies']}")
print(f"  Active:              {s['active_strategies']}")
print(f"  Disabled:            {s['disabled_strategies']}")
print(f"  Fantasy Data Purged: {s['fantasy_entries_purged']}")
print(f"  Forward Trades:      {s['total_forward_trades']}")
print(f"  Total PnL:           {s['total_pnl_pct']:+.2f}%")

print("\n[DISABLED STRATEGIES - The 9 Losers]")
print(f"  Disabled at: {dash['disabled_strategies']['disabled_at']}")
print(f"  Reason: {dash['disabled_strategies']['reason']}")
print()
for strat in dash['disabled_strategies']['list']:
    print(f"  [X] {strat['name'][:40]:<40} {strat['pnl_pct']:>+6.2f}%  ({strat['trades']} trades, {strat['win_rate']:.0f}% WR)")
print(f"\n  Total PnL saved by disabling: {dash['disabled_strategies']['total_pnl_saved_by_disabling']:+.2f}%")

print("\n[TOP ACTIVE STRATEGIES]")
for strat in dash['active_profit_strategies']:
    print(f"  [OK] {strat['name'][:40]:<40} {strat['pnl_pct']:>+6.2f}%  ({strat['trades']} trades, {strat['win_rate']:.0f}% WR)")

print("\n[WATCH LIST - Monitor Closely]")
for strat in dash['watch_list']:
    print(f"  [!] {strat['name'][:40]:<40} {strat['pnl_pct']:>+6.2f}%  ({strat['trades']} trades, {strat['win_rate']:.0f}% WR) - {strat['note']}")

print("\n[DATA INTEGRITY]")
di = dash['data_integrity']
print(f"  Fantasy entries purged: {di['fantasy_entries_removed']}")
print(f"  Max acceptable PnL: {di['max_acceptable_pnl_pct']}%")
print(f"  Audit rule: {di['audit_rule']}")

print("\n[GUARD STATUS]")
gs = dash['guard_status']
print(f"  Strategy Guard: {'ACTIVE' if gs['strategy_guard_active'] else 'INACTIVE'}")
print(f"  Files patched: {len(gs['files_patched'])}")
for f in gs['files_patched']:
    print(f"    - {f}")

print("\n[NEXT ACTIONS]")
for action in dash['next_actions']:
    print(f"  > {action}")

print("=" * 80)
