#!/usr/bin/env python3
"""Real-time P&L check against Binance prices."""
import json, urllib.request

prices = {}
data = json.loads(urllib.request.urlopen(
    urllib.request.Request('https://api.binance.com/api/v3/ticker/price',
    headers={'User-Agent': 'Mozilla/5.0'}), timeout=15).read())
for d in data:
    prices[d['symbol']] = float(d['price'])

state = json.load(open('audit_dashboard/data/claudes_test_state.json'))

print("=" * 95)
print(f"{'#':>2} {'Portfolio':25s} {'PnL$':>10} {'PnL%':>8} | Positions")
print("-" * 95)

all_pnl = []
for pid, port in state.items():
    total_pnl = 0
    pos_details = []
    for pos in port.get('positions', []):
        sym = pos['symbol'].replace('-','').replace('/','').upper()
        if not sym.endswith('USDT'):
            sym = sym.replace('USD','USDT')
            if not sym.endswith('USDT'):
                sym += 'USDT'
        price = prices.get(sym, 0)
        entry = pos['entry_price']
        d = pos['direction']
        size = pos['size_usd']
        if price > 0 and entry > 0:
            if d == 'LONG':
                pnl_pct = ((price - entry) / entry) * 100
            else:
                pnl_pct = ((entry - price) / entry) * 100
            pnl_usd = size * (pnl_pct / 100)
            total_pnl += pnl_usd
            pos_details.append(f"{pos['symbol']:8s} {d:5s} {pnl_pct:+.2f}% (${pnl_usd:+.2f})")

    name = port['name']
    ic = port['initial_capital']
    pnl_pct_total = (total_pnl / ic) * 100
    all_pnl.append((name, total_pnl, pnl_pct_total, pos_details, ic))

all_pnl.sort(key=lambda x: x[2], reverse=True)
combined = 0
for i, (name, pnl, pct, details, ic) in enumerate(all_pnl):
    combined += pnl
    leader = " ***" if i == 0 else ""
    dstr = " | ".join(details) if details else "no positions"
    print(f"{i+1:>2} {name:25s} ${pnl:>+9.2f} {pct:>+7.3f}% | {dstr}{leader}")

print("=" * 95)
print(f"   COMBINED UNREALIZED P&L: ${combined:+.2f}")
btc = prices.get('BTCUSDT', 0)
eth = prices.get('ETHUSDT', 0)
xrp = prices.get('XRPUSDT', 0)
print(f"   BTC: ${btc:,.2f} | ETH: ${eth:,.2f} | XRP: ${xrp:,.4f}")
