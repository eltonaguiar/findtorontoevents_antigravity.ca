import json

print("=" * 80)
print("  COPY TRADER INTELLIGENCE — FULL RESULTS SUMMARY")
print("=" * 80)

# Qualified traders
with open('copy_trader_intel/data/qualified_traders.json') as f:
    qt = json.load(f)
traders = qt.get('traders', [])
print(f"\n--- QUALIFIED TRADERS ({len(traders)}) ---")
for t in traders:
    label = t.get('label', 'unknown')
    wr = t.get('win_rate', 0) * 100
    pf = t.get('profit_factor', 0)
    pnl = t.get('total_realized_pnl', 0)
    trades = t.get('total_trades', 0)
    edge = t.get('edge_score', 0)
    acct = t.get('account_value', 0)
    coins = t.get('top_coins', [])
    top_coins = ', '.join([c[0] for c in coins[:3]]) if coins else 'N/A'
    print(f"  {label:30s} WR:{wr:5.1f}%  PF:{pf:6.1f}  PnL:${pnl:>12,.0f}  Trades:{trades:>5}  Edge:{edge:>3}  Coins:{top_coins}")

# Active picks
with open('copy_trader_intel/data/active_picks.json') as f:
    picks = json.load(f)
longs = sum(1 for p in picks if p.get('direction') == 'LONG')
shorts = sum(1 for p in picks if p.get('direction') == 'SHORT')
coins = set(p.get('symbol', '') for p in picks)
print(f"\n--- ACTIVE PICKS ({len(picks)}) ---")
print(f"  LONG: {longs} | SHORT: {shorts} | Unique coins: {len(coins)}")

# Strategy profiles
try:
    with open('copy_trader_intel/data/strategy_profiles.json') as f:
        sp = json.load(f)
    profiles = sp.get('profiles', [])
    print(f"\n--- STRATEGY PROFILES ({len(profiles)}) ---")
    for p in profiles:
        dna = p.get('strategy_dna', {})
        perf = p.get('performance', {})
        safety = p.get('safety_gate_impact', {})
        label = p.get('label', 'unknown')
        style = dna.get('trading_style', '?')
        entry = dna.get('entry_style', '?')
        hold = dna.get('median_hold_hours', 0)
        wr = perf.get('win_rate', 0) * 100
        pf = perf.get('profit_factor', 0)
        rr = perf.get('risk_reward_ratio', 0)
        gate = safety.get('recommendation', '?')
        coins_str = ', '.join(p.get('primary_coins', [])[:3])
        print(f"  {label:30s} {style:16s} {entry:22s} Hold:{hold:6.1f}h  WR:{wr:5.1f}%  PF:{pf:6.1f}  R:R:{rr:5.1f}  Safety:{gate}")
except FileNotFoundError:
    print("\n  No strategy profiles found yet")

# Extracted strategies
try:
    with open('copy_trader_intel/data/extracted_strategies.json') as f:
        es = json.load(f)
    strategies = es.get('strategies', [])
    print(f"\n--- EXTRACTED STRATEGIES ({len(strategies)}) ---")
    for s in strategies:
        sid = s.get('strategy_id', '?')
        desc = s.get('description', '')
        rules = s.get('rules', {})
        tp = rules.get('tp_pct', 0)
        sl = rules.get('sl_pct', 0)
        gate = s.get('safety_gate_mode', '?')
        dual = s.get('run_dual_mode', False)
        expected = s.get('expected_performance', {})
        exp_wr = expected.get('win_rate', 0) * 100
        print(f"  {sid:35s} TP:{tp:5.2f}% SL:{sl:5.2f}% ExpWR:{exp_wr:5.1f}%  Gate:{gate:25s}  Dual:{dual}")
except FileNotFoundError:
    print("\n  No extracted strategies found yet")

print(f"\n{'='*80}")
