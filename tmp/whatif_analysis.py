#!/usr/bin/env python3
"""What-if investment analysis across all portfolio data."""
import json, sys
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

with open('audit_dashboard/data/claudes_test_state.json') as f:
    state = json.load(f)

print('=' * 80)
print('  WHAT-IF INVESTMENT ANALYSIS')
print('=' * 80)

# 1. BY PORTFOLIO
print('\n[1] WHAT-IF BY PORTFOLIO ($10K initial)')
print('-' * 70)
results = []
for pid, port in sorted(state.items()):
    if not isinstance(port, dict) or 'positions' not in port:
        continue
    initial = port.get('initial_capital', 10000)
    equity = port.get('equity', initial)
    closed = port.get('closed', [])
    pnl_pct = ((equity - initial) / initial) * 100
    trades = len(closed)
    wins = port.get('wins', 0)
    losses = port.get('losses', 0)
    wr = (wins / trades * 100) if trades > 0 else 0
    roi_10k = pnl_pct / 100 * 10000
    results.append((pid, pnl_pct, roi_10k, trades, wins, losses, wr, len(port.get('positions', []))))

results.sort(key=lambda x: x[1], reverse=True)
for r in results:
    pid, pnl, roi, t, w, l, wr, op = r
    if t > 0 or op > 0:
        print(f'  {pid:35s} PnL={pnl:+.3f}% (${roi:+,.2f}) | {t} trades (W{w}/L{l} {wr:.0f}%) | {op} open')
    else:
        print(f'  {pid:35s} IDLE (no activity)')

# 2. BY CONFIDENCE
print('\n[2] WHAT-IF BY CONFIDENCE BUCKET')
print('-' * 70)
conf_buckets = {'0.98-1.00': [], '0.95-0.98': [], '0.90-0.95': [], '<0.90': []}
for pid, port in state.items():
    if not isinstance(port, dict):
        continue
    for t in port.get('closed', []):
        conf = t.get('confidence', 0)
        net = t.get('net_pnl_usd', t.get('pnl_usd', 0))
        pnl_pct = t.get('pnl_pct', 0)
        rec = (t, net, pnl_pct)
        if conf >= 0.98:
            conf_buckets['0.98-1.00'].append(rec)
        elif conf >= 0.95:
            conf_buckets['0.95-0.98'].append(rec)
        elif conf >= 0.90:
            conf_buckets['0.90-0.95'].append(rec)
        else:
            conf_buckets['<0.90'].append(rec)

for bucket in ['0.98-1.00', '0.95-0.98', '0.90-0.95', '<0.90']:
    trades = conf_buckets[bucket]
    if not trades:
        print(f'  Confidence {bucket}: 0 trades')
        continue
    total_pnl = sum(t[1] for t in trades)
    wins = sum(1 for t in trades if t[1] > 0)
    losses = len(trades) - wins
    wr = wins / len(trades) * 100
    avg_pnl = total_pnl / len(trades)
    best = max(trades, key=lambda x: x[2])
    worst = min(trades, key=lambda x: x[2])
    avg_size = sum(t[0].get('size_usd', 500) for t in trades) / len(trades)
    scaled_pnl = total_pnl * (10000 / avg_size) if avg_size > 0 else 0
    print(f'  Confidence {bucket}:')
    print(f'    Trades: {len(trades)} | W={wins} L={losses} WR={wr:.1f}%')
    print(f'    Total Net PnL: ${total_pnl:+,.2f} | Avg per trade: ${avg_pnl:+,.2f}')
    print(f'    $10K scaled ROI: ${scaled_pnl:+,.2f}')
    print(f'    Best: {best[0]["symbol"]} {best[2]:+.2f}% | Worst: {worst[0]["symbol"]} {worst[2]:+.2f}%')
    print()

# 3. BY STRATEGY
print('\n[3] WHAT-IF BY STRATEGY')
print('-' * 70)
strat_map = defaultdict(list)
for pid, port in state.items():
    if not isinstance(port, dict):
        continue
    for t in port.get('closed', []):
        strat = t.get('strategy', 'unknown')
        net = t.get('net_pnl_usd', t.get('pnl_usd', 0))
        pnl_pct = t.get('pnl_pct', 0)
        strat_map[strat].append((t, net, pnl_pct))

strat_results = []
for strat, trades in strat_map.items():
    total = sum(t[1] for t in trades)
    wins = sum(1 for t in trades if t[1] > 0)
    wr = wins / len(trades) * 100 if trades else 0
    avg_pnl_pct = sum(t[2] for t in trades) / len(trades)
    strat_results.append((strat, len(trades), wins, len(trades) - wins, wr, total, avg_pnl_pct))

strat_results.sort(key=lambda x: x[5], reverse=True)
for s, cnt, w, l, wr, pnl, avg in strat_results:
    print(f'  {s[:45]:45s} {cnt:2d}t W={w}/L={l} WR={wr:5.1f}% PnL=${pnl:+,.2f} Avg={avg:+.2f}%')

# 4. BY SYMBOL
print('\n[4] WHAT-IF BY SYMBOL')
print('-' * 70)
sym_map = defaultdict(list)
for pid, port in state.items():
    if not isinstance(port, dict):
        continue
    for t in port.get('closed', []):
        sym = t.get('symbol', '?')
        net = t.get('net_pnl_usd', t.get('pnl_usd', 0))
        sym_map[sym].append(net)

sym_results = [(sym, len(pnls), sum(pnls), sum(1 for p in pnls if p > 0)) for sym, pnls in sym_map.items()]
sym_results.sort(key=lambda x: x[2], reverse=True)
for sym, cnt, pnl, wins in sym_results:
    wr = wins / cnt * 100 if cnt else 0
    print(f'  {sym:15s} {cnt:2d} trades W={wins}/L={cnt-wins} WR={wr:5.1f}% Total=${pnl:+,.2f}')

# 5. OPTIMAL COMBO
print('\n[5] OPTIMAL COMBO ANALYSIS')
print('-' * 70)
if strat_results:
    best_strat = strat_results[0]
    worst_strat = strat_results[-1]
    print(f'  BEST Strategy:  {best_strat[0]}')
    print(f'    {best_strat[1]} trades | WR: {best_strat[4]:.1f}% | PnL: ${best_strat[5]:+,.2f}')
    print(f'  WORST Strategy: {worst_strat[0]}')
    print(f'    {worst_strat[1]} trades | WR: {worst_strat[4]:.1f}% | PnL: ${worst_strat[5]:+,.2f}')

    # What if only took high-confidence + winning strategies?
    good_strats = set(s[0] for s in strat_results if s[5] > 0)
    opt_trades = []
    for pid, port in state.items():
        if not isinstance(port, dict):
            continue
        for t in port.get('closed', []):
            if t.get('strategy') in good_strats and t.get('confidence', 0) >= 0.95:
                opt_trades.append(t)

    if opt_trades:
        opt_pnl = sum(t.get('net_pnl_usd', t.get('pnl_usd', 0)) for t in opt_trades)
        opt_wins = sum(1 for t in opt_trades if t.get('net_pnl_usd', t.get('pnl_usd', 0)) > 0)
        opt_wr = opt_wins / len(opt_trades) * 100
        print(f'\n  OPTIMAL FILTER (winning strategy + confidence >= 0.95):')
        print(f'    Trades: {len(opt_trades)} | WR: {opt_wr:.1f}% | PnL: ${opt_pnl:+,.2f}')
    else:
        print('\n  No trades match optimal filter')

print('\n' + '=' * 80)
