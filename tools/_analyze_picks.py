#!/usr/bin/env python3
"""Analyze recent closed picks by asset class and source system."""
import json

with open('audit_dashboard/data/dashboard_data.json') as f:
    data = json.load(f)

picks = data.get('picks', {})
recent = picks.get('recent_closed', [])
print('Recent closed total:', len(recent))

def analyze_class(picks_list, name):
    if not picks_list:
        print(f'{name}: no recent closed picks')
        return
    wins = [p for p in picks_list if (p.get('pnl_pct', 0) or 0) > 0]
    losses = [p for p in picks_list if (p.get('pnl_pct', 0) or 0) < 0]
    flat = [p for p in picks_list if (p.get('pnl_pct', 0) or 0) == 0]
    avg_win = sum(p.get('pnl_pct', 0) for p in wins) / len(wins) if wins else 0
    avg_loss = sum(p.get('pnl_pct', 0) for p in losses) / len(losses) if losses else 0
    wr = len(wins) / (len(wins) + len(losses)) * 100 if (wins or losses) else 0
    pf_val = (sum(p.get('pnl_pct', 0) for p in wins) / abs(sum(p.get('pnl_pct', 0) for p in losses))) if losses and wins else 0

    sources = {}
    for p in picks_list:
        src = p.get('source_system', p.get('source', 'unknown'))
        if src not in sources:
            sources[src] = {'w': 0, 'l': 0, 'pnl': 0}
        pnl = p.get('pnl_pct', 0) or 0
        if pnl > 0:
            sources[src]['w'] += 1
        elif pnl < 0:
            sources[src]['l'] += 1
        sources[src]['pnl'] += pnl

    print(f'{name}: n={len(picks_list)} WR={wr:.1f}% PF={pf_val:.2f} AvgWin={avg_win:.2f}% AvgLoss={avg_loss:.2f}% flat={len(flat)}')
    print('  Sources by PnL (worst first):')
    for src, v in sorted(sources.items(), key=lambda x: x[1]['pnl'])[:8]:
        wr_s = v['w'] / (v['w'] + v['l']) * 100 if (v['w'] + v['l']) else 0
        print(f'    {src}: W={v["w"]} L={v["l"]} WR={wr_s:.0f}% PnL={v["pnl"]:.2f}%')
    print()

for cls in ['FOREX', 'EQUITY', 'CRYPTO', 'COMMODITY', 'ETF', 'BOND']:
    picks_list = [p for p in recent if p.get('asset_class') == cls]
    analyze_class(picks_list, cls)

# Strategy-level breakdown for FOREX 
print('=== FOREX STRATEGIES (all closed, worst) ===')
by_ac = data['performance'].get('by_asset_class', {})
# Check if there are strategy-specific breakdowns in the data
strat_data = data.get('cross_strategy_permutations', {})
print('cross_strategy_permutations type:', type(strat_data))
if isinstance(strat_data, dict):
    print('keys:', list(strat_data.keys())[:10])
elif isinstance(strat_data, list):
    forex_strats = [s for s in strat_data if 'forex' in str(s.get('asset_class', '')).lower() or 'FOREX' in str(s.get('asset_class', ''))]
    print(f'FOREX entries: {len(forex_strats)}')
    for s in sorted(forex_strats, key=lambda x: x.get('profit_factor', 0))[:10]:
        print(f'  {json.dumps(s)[:200]}')
