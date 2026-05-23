import json
from collections import defaultdict

d = json.load(open('C:/findtorontoevents_antigravity.ca/audit/data/dashboard_data.json'))
recent_closed = d.get('picks', {}).get('recent_closed', [])

print('=== CLOSED PICKS: WORST SYSTEMS BY ASSET CLASS ===')
by_ac = defaultdict(lambda: defaultdict(lambda: {'wins':0,'losses':0,'pnl':0.0,'count':0,'strats':set()}))
for p in recent_closed:
    ac = p.get('asset_class', 'CRYPTO')
    sys = p.get('source_system', 'unknown')
    strat = p.get('strategy', 'unknown')
    pnl = float(p.get('pnl_pct') or 0)
    status = p.get('status', '')
    by_ac[ac][sys]['count'] += 1
    by_ac[ac][sys]['strats'].add(strat[:30])
    if status in ('WON','TP_HIT','WIN'):
        by_ac[ac][sys]['wins'] += 1
        by_ac[ac][sys]['pnl'] += pnl
    elif status in ('LOST','SL_HIT','LOSS'):
        by_ac[ac][sys]['losses'] += 1
        by_ac[ac][sys]['pnl'] += pnl

for ac in sorted(by_ac.keys()):
    print(f"\n  {ac}:")
    systems_data = by_ac[ac]
    rows = []
    for sys, data in systems_data.items():
        total = data['wins'] + data['losses']
        if total < 5:
            continue
        wr = data['wins'] / total * 100 if total > 0 else 0
        pf_est = data['wins'] / data['losses'] if data['losses'] > 0 else (None if data['wins']==0 else float('inf'))
        rows.append((data['pnl'], wr, pf_est, total, sys, data['wins'], data['losses']))
    rows.sort()
    for pnl, wr, pf, total, sys, wins, losses in rows[:15]:
        pf_str = f"{pf:.2f}" if pf is not None else "N/A"
        print(f"    {sys:35s} n={total:4d} WR={wr:5.1f}% PF={pf_str:>6} PnL={pnl:>9.1f}%")

print()
print('=== KEY BAD SYSTEMS: DETAILED BREAKDOWN ===')
key_systems = ['ml_crypto_predictor', 'ml_crypto_pred', 'claude_gainer', 'kimi_signal_tracking', 'stocks_competition', 'alpha_engine', 'multi_asset_institutional', 'multi_asset_scanner', 'institutional_picks_engine', 'alpha_engine_fast', 'riseoftheclaw', 'aggregated_picks']
for ks in key_systems:
    by_ac_ks = defaultdict(lambda: {'wins':0,'losses':0,'pnl':0.0,'count':0})
    for p in recent_closed:
        if p.get('source_system') != ks:
            continue
        ac = p.get('asset_class', 'CRYPTO')
        pnl = float(p.get('pnl_pct') or 0)
        status = p.get('status', '')
        by_ac_ks[ac]['count'] += 1
        if status in ('WON','TP_HIT','WIN'):
            by_ac_ks[ac]['wins'] += 1
            by_ac_ks[ac]['pnl'] += pnl
        elif status in ('LOST','SL_HIT','LOSS'):
            by_ac_ks[ac]['losses'] += 1
            by_ac_ks[ac]['pnl'] += pnl
    if by_ac_ks:
        print(f"\n  {ks}:")
        for ac, data in sorted(by_ac_ks.items()):
            total = data['wins'] + data['losses']
            if total == 0:
                continue
            wr = data['wins'] / total * 100
            pf = data['wins'] / data['losses'] if data['losses'] > 0 else None
            pf_str = f"{pf:.2f}" if pf is not None else "N/A"
            print(f"    {ac:12s} n={total:4d} WR={wr:5.1f}% PF={pf_str:>6} PnL={data['pnl']:>9.1f}%")
