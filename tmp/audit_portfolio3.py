import json

with open('audit_dashboard/data/claudes_test_state.json') as f:
    data = json.load(f)

print("="*80)
print("DEEP DIVE: CONTRARIAN BTC-USD unrealized PnL check")
print("="*80)
c = data['contrarian']
for p in c['positions']:
    if p['symbol'] == 'BTC-USD':
        print(f"  Entry: {p['entry_price']}, Current: {p['current_price']}")
        print(f"  Direction: SHORT")
        print(f"  Recorded pnl_pct: {p['pnl_pct']}, pnl_usd: {p['pnl_usd']}")
        calc = (p['entry_price'] - p['current_price']) / p['entry_price'] * 100
        calc_usd = p['size_usd'] * calc / 100
        print(f"  Calculated pnl_pct: {calc:.4f}%, pnl_usd: {calc_usd:.2f}")
        print(f"  Current price $71140.12 vs entry $68965.02 -> SHORT is losing")
        print(f"  This is CORRECT - the position shows an unrealized loss")

print()
print("="*80)
print("DEEP DIVE: MOMENTUM_RIDERS daily_pnl discrepancy")
print("="*80)
m = data['momentum_riders']
print(f"  daily_pnl: {m['daily_pnl']}")
print(f"  Actual equity change: {m['equity'] - m['initial_capital']}")
print(f"  daily_pnl says $4797 but actual equity is only +$23 from initial")
print(f"  The daily_pnl field seems to reflect PEAK unrealized, not current")
print(f"  This is MISLEADING and arguably WRONG")

print()
print("="*80)
print("IDENTICAL PORTFOLIO AUDIT (full detail)")
print("="*80)
# score_leaders vs regime_aligned vs anti_meme
for pair in [('score_leaders', 'regime_aligned'), ('score_leaders', 'anti_meme'), ('proven_only', 'claude_best'), ('proven_only', 'prop_conservative')]:
    p1, p2 = pair
    d1, d2 = data[p1], data[p2]
    pos1 = [(p['id'], p['symbol'], p['direction'], p['size_usd']) for p in d1['positions']]
    pos2 = [(p['id'], p['symbol'], p['direction'], p['size_usd']) for p in d2['positions']]
    same_ids = set(p[0] for p in pos1) == set(p[0] for p in pos2)
    same_sizes = all(p1s == p2s for p1s, p2s in zip(sorted(pos1), sorted(pos2)))
    print(f"\n{p1} vs {p2}:")
    print(f"  Same position IDs: {same_ids}")
    print(f"  Same sizes: {same_sizes}")
    print(f"  {p1} equity: {d1['equity']:.2f}, {p2} equity: {d2['equity']:.2f}")
    if not same_sizes:
        print(f"  {p1} sizes: {sorted([(p[1], p[3]) for p in pos1])}")
        print(f"  {p2} sizes: {sorted([(p[1], p[3]) for p in pos2])}")
    cl1 = [(t['id'], t['symbol'], t['size_usd']) for t in d1['closed']]
    cl2 = [(t['id'], t['symbol'], t['size_usd']) for t in d2['closed']]
    same_closed = sorted(cl1) == sorted(cl2)
    print(f"  Same closed trades: {same_closed}")

print()
print("="*80)
print("DEEP DIVE: sys_wr=100% but sys_pf=0.61 (contradictory)")
print("="*80)
print("  BTC-USD SHORT 'autocorrelation_exploiter':")
print("  sys_wr=100% means every trade wins, but sys_pf=0.61 (profit factor < 1)")
print("  A profit factor < 1 means the system LOSES money overall")
print("  These two metrics directly contradict each other")
print("  100% WR with PF < 1 is mathematically impossible in normal circumstances")
print("  (Could only happen if avg win is tiny relative to some other accounting)")

print()
print("="*80)
print("CHECK: All open position unrealized PnL vs mark-to-market")
print("="*80)
issues = []
for pid, port in data.items():
    for p in port['positions']:
        if p['current_price'] != p['entry_price']:
            if p['direction'] == 'LONG':
                expected_pnl_pct = (p['current_price'] - p['entry_price']) / p['entry_price'] * 100
            else:
                expected_pnl_pct = (p['entry_price'] - p['current_price']) / p['entry_price'] * 100
            expected_pnl_usd = p['size_usd'] * expected_pnl_pct / 100
            if abs(expected_pnl_usd - p['pnl_usd']) > 1.0:
                issues.append(f"[{pid}] {p['symbol']} {p['direction']}: current={p['current_price']}, entry={p['entry_price']}, expected_pnl_usd={expected_pnl_usd:.2f}, recorded={p['pnl_usd']:.2f}")
            if abs(expected_pnl_pct - p['pnl_pct']) > 0.1:
                issues.append(f"[{pid}] {p['symbol']} {p['direction']}: expected_pnl_pct={expected_pnl_pct:.4f}%, recorded={p['pnl_pct']:.4f}%")
if issues:
    for i in issues:
        print(f"  {i}")
else:
    print("  All open position PnL calculations are CORRECT")

print()
print("="*80)
print("CHECK: Equity history - any reversals or inconsistencies")
print("="*80)
for pid, port in data.items():
    eh = port['equity_history']
    # Check if any equity snapshot exceeds HWM
    for snap in eh:
        if snap['equity'] > port['high_water_mark'] + 0.01:
            print(f"  [{pid}] Equity snapshot {snap['equity']:.2f} exceeds HWM {port['high_water_mark']:.2f}")
    # Check for exact same timestamps
    times = [e['time'] for e in eh]
    if len(times) != len(set(times)):
        print(f"  [{pid}] Duplicate timestamps in equity_history")

print()
print("="*80)
print("CHECK: All portfolios 0 losses but some have unrealized losses")
print("="*80)
for pid, port in data.items():
    if port['losses'] == 0 and len(port['closed']) > 0:
        pass  # This is fine if all closed are wins
    # Check for stale positions (opened long ago with no movement)
    for p in port['positions']:
        if p['pnl_usd'] < -50:
            print(f"  [{pid}] {p['symbol']}: significant unrealized loss of ${p['pnl_usd']:.2f}")

print()
print("="*80)
print("FINAL CHECK: Position count sanity vs max_positions")
print("="*80)
for pid, port in data.items():
    if len(port['positions']) > port['max_positions']:
        print(f"  [{pid}] Has {len(port['positions'])} positions but max_positions={port['max_positions']}")
