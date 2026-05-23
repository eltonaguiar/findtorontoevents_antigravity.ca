#!/usr/bin/env python3
import json, urllib.request, sys
sys.stdout.reconfigure(encoding='utf-8')

# Fetch live prices
bybit = {}
for cat in ['spot', 'linear']:
    url = f'https://api.bybit.com/v5/market/tickers?category={cat}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=15)
    for t in json.loads(resp.read())['result']['list']:
        if t['symbol'] not in bybit:
            bybit[t['symbol']] = float(t['lastPrice'])

with open('audit_dashboard/data/claudes_test_state.json') as f:
    state = json.load(f)

print('=== FULL PORTFOLIO EQUITY AUDIT (vs LIVE Bybit) ===')
print()
total_stored = 0
total_true = 0
big_pnl = []

for name, pf in sorted(state.items()):
    if not isinstance(pf, dict) or 'positions' not in pf:
        continue
    initial = pf.get('initial_capital', 10000)
    commission = pf.get('total_commission', 0)
    slippage = pf.get('total_slippage', 0)
    closed = pf.get('closed', pf.get('recent_closed', []))
    realized = sum(t.get('pnl_usd', 0) for t in closed)

    unrealized_live = 0
    for pos in pf.get('positions', []):
        sym = pos.get('symbol', '?')
        entry = pos.get('entry_price', 0)
        size = pos.get('size_usd', 0)
        direction = pos.get('direction', 'LONG')
        norm = sym.replace('-USD', 'USDT').replace('-', '')
        live = bybit.get(norm)

        if live and entry and size:
            if direction == 'LONG':
                pnl_pct = ((live - entry) / entry) * 100
            else:
                pnl_pct = ((entry - live) / entry) * 100
            pnl_usd = (pnl_pct / 100) * size
            unrealized_live += pnl_usd

            if abs(pnl_pct) > 10:
                big_pnl.append(f'  !! {name}/{sym}: {pnl_pct:+.2f}% (${pnl_usd:+,.2f}) entry={entry} live={live}')
        else:
            unrealized_live += pos.get('pnl_usd', 0)

    true_equity = initial + realized + unrealized_live - commission - slippage
    stored_equity = pf.get('equity', 0)
    diff = stored_equity - true_equity
    total_stored += stored_equity
    total_true += true_equity

    flag = ''
    if abs(diff) > 50:
        flag = ' *** PHANTOM'
    elif abs(diff) > 5:
        flag = ' * drift'

    stored_pnl_pct = (stored_equity - initial) / initial * 100
    true_pnl_pct = (true_equity - initial) / initial * 100

    if abs(diff) > 1 or len(pf.get('positions', [])) > 0:
        print(f'{name:35s} stored=${stored_equity:>12,.2f} ({stored_pnl_pct:+.3f}%)  true=${true_equity:>12,.2f} ({true_pnl_pct:+.3f}%)  diff=${diff:>8,.2f}{flag}')

print()
print(f'TOTAL STORED:  ${total_stored:>12,.2f}')
print(f'TOTAL TRUE:    ${total_true:>12,.2f}')
print(f'TOTAL PHANTOM: ${total_stored - total_true:>12,.2f}')

print()
if big_pnl:
    print('=== POSITIONS WITH >10% PnL ===')
    for b in big_pnl:
        print(b)
else:
    print('No positions with >10% PnL found (all within range)')
