import json
from collections import defaultdict

with open('audit_dashboard/data/claudes_test_state.json') as f:
    data = json.load(f)

print("="*80)
print("DEEP DIVE: CONTRARIAN TRX TRADE")
print("="*80)
c = data['contrarian']
for t in c['closed']:
    if 'TRX' in t['symbol']:
        print(f"  Symbol: {t['symbol']}")
        print(f"  Direction: {t['direction']}")
        print(f"  Entry: {t['entry_price']}")
        print(f"  Exit: {t['exit_price']}")
        print(f"  TP target: {t['take_profit']}")
        print(f"  SL target: {t['stop_loss']}")
        print(f"  PnL%: {t['pnl_pct']}")
        print(f"  PnL USD: {t['pnl_usd']}")
        print(f"  Net PnL: {t['net_pnl_usd']}")
        print(f"  Size: {t['size_usd']}")
        print(f"  Exit reason: {t['exit_reason']}")
        # Verify: SHORT TRX entry=0.289566, exit=0.06697
        # PnL% = (0.289566 - 0.06697) / 0.289566 * 100 = 76.87%
        calc_pnl = (t['entry_price'] - t['exit_price']) / t['entry_price'] * 100
        print(f"  Calculated PnL%: {calc_pnl:.4f}%")
        print(f"  TRX going from $0.2896 to $0.0670 is a 76.87% DROP - EXTREMELY SUSPICIOUS")
        print(f"  This would be a massive crash, unlikely in ~30 min timeframe")
        print()

print("="*80)
print("DEEP DIVE: PROP FIRM PORTFOLIOS (Initial Capital)")
print("="*80)
for pid in ['prop_conservative', 'prop_aggressive', 'prop_swing']:
    p = data[pid]
    print(f"\n{pid}:")
    print(f"  initial_capital: {p['initial_capital']}")
    print(f"  equity: {p['equity']}")
    print(f"  cash: {p['cash']}")
    print(f"  prop_firm: {p['prop_firm']}")
    print(f"  daily_loss_limit_pct: {p['daily_loss_limit_pct']}")
    print(f"  max_drawdown_limit_pct: {p['max_drawdown_limit_pct']}")
    print(f"  profit_target_pct: {p['profit_target_pct']}")

print()
print("="*80)
print("DEEP DIVE: MOMENTUM_RIDERS equity jump/crash")
print("="*80)
m = data['momentum_riders']
print(f"  Equity: {m['equity']}")
print(f"  HWM: {m['high_water_mark']}")
print(f"  Max drawdown: {m['max_drawdown_pct']}%")
print(f"  Equity went from $10000 to HWM $14797 then dropped to $10023")
print(f"  That's a 32% drawdown - concerning for a portfolio that only had 1 closed trade")
print(f"  daily_pnl: {m['daily_pnl']}")
print("  Equity history:")
for eh in m['equity_history']:
    print(f"    {eh['time']}: ${eh['equity']:.2f}")
print()
print(f"  Only 1 closed trade (XRP) with net_pnl=$23.20")
print(f"  But equity went to $14797 (unrealized) then crashed back")
print(f"  This is NOT an error per se, but a massive unrealized gain evaporated")

print()
print("="*80)
print("DEEP DIVE: DUPLICATE POSITION IDS ACROSS PORTFOLIOS")
print("="*80)
# Check if same position ID appears in multiple portfolios (same trade shared across portfolios)
id_to_portfolios = defaultdict(list)
for pid, port in data.items():
    for p in port['positions']:
        id_to_portfolios[p['id']].append((pid, p['symbol'], p['size_usd']))

print("Position IDs shared across portfolios (OPEN):")
for pid_id, entries in sorted(id_to_portfolios.items()):
    if len(entries) > 1:
        print(f"  ID {pid_id}:")
        for portfolio, sym, size in entries:
            print(f"    {portfolio}: {sym} size=${size:.2f}")

print()
# Same for closed
id_to_portfolios_closed = defaultdict(list)
for pid, port in data.items():
    for t in port['closed']:
        id_to_portfolios_closed[t['id']].append((pid, t['symbol'], t['size_usd'], t.get('net_pnl_usd', 0)))

print("Trade IDs shared across portfolios (CLOSED):")
shared_count = 0
for tid, entries in sorted(id_to_portfolios_closed.items()):
    if len(entries) > 1:
        shared_count += 1
        if shared_count <= 10:
            print(f"  ID {tid}:")
            for portfolio, sym, size, pnl in entries:
                print(f"    {portfolio}: {sym} size=${size:.2f} net_pnl=${pnl:.2f}")
if shared_count > 10:
    print(f"  ... and {shared_count - 10} more shared trade IDs")
print(f"  Total shared trade IDs: {shared_count}")

print()
print("="*80)
print("DEEP DIVE: CLOSED TRADE TP COMPARISON (fixing audit logic)")
print("="*80)
# The earlier check was comparing exit_price against the LAST position's TP (carry-over bug)
# Let's properly check each closed trade's own TP
issues_tp = []
for pid, port in data.items():
    for t in port['closed']:
        tp = t.get('take_profit')
        sl = t.get('stop_loss')
        exit_p = t.get('exit_price', 0)
        direction = t['direction']
        reason = t.get('exit_reason', '')
        sym = t['symbol']

        if reason == 'TP' and tp and exit_p:
            if direction == 'LONG':
                # Exit should be >= TP (or close to it with slippage)
                if exit_p < tp * 0.95:
                    issues_tp.append(f"[{pid}] {sym} LONG TP hit but exit({exit_p}) << TP({tp})")
                elif exit_p > tp * 1.10:
                    pct_over = ((exit_p / tp) - 1) * 100
                    issues_tp.append(f"[{pid}] {sym} LONG TP hit but exit({exit_p}) >> TP({tp}) by {pct_over:.1f}% - EXIT MUCH HIGHER THAN TP")
            elif direction == 'SHORT':
                # For short, exit should be <= TP
                if exit_p > tp * 1.05:
                    issues_tp.append(f"[{pid}] {sym} SHORT TP hit but exit({exit_p}) >> TP({tp})")
                elif exit_p < tp * 0.5:
                    pct_under = (1 - (exit_p / tp)) * 100
                    issues_tp.append(f"[{pid}] {sym} SHORT TP hit but exit({exit_p}) << TP({tp}) by {pct_under:.1f}% - MASSIVE OVERSHOOT")

for issue in issues_tp:
    print(f"  {issue}")

print()
print("="*80)
print("DEEP DIVE: POSITIONS WITH UNREALIZED PnL != 0 but current_price == entry_price")
print("="*80)
for pid, port in data.items():
    for p in port['positions']:
        if p['pnl_usd'] != 0 and p['current_price'] == p['entry_price']:
            print(f"  [{pid}] {p['symbol']}: pnl_usd={p['pnl_usd']} but current_price==entry_price")
        if p['pnl_usd'] == 0 and p['current_price'] != p['entry_price']:
            print(f"  [{pid}] {p['symbol']}: pnl_usd=0 but current_price({p['current_price']}) != entry_price({p['entry_price']})")

print()
print("="*80)
print("DEEP DIVE: BTC-USD SHORT positions (sys_wr=100% but sys_pf=0.61)")
print("="*80)
for pid, port in data.items():
    for p in port['positions']:
        if p['symbol'] == 'BTC-USD' and p['direction'] == 'SHORT':
            print(f"  [{pid}] BTC-USD SHORT: entry={p['entry_price']}, TP={p['take_profit']}, SL={p['stop_loss']}")
            print(f"    sys_wr={p['sys_wr']}%, sys_pf={p['sys_pf']}")
            print(f"    current_price={p['current_price']}, pnl_usd={p['pnl_usd']}")
            # TP at $52216 from $68965 entry = 24.3% drop target
            drop_pct = (p['entry_price'] - p['take_profit']) / p['entry_price'] * 100
            print(f"    Needs {drop_pct:.1f}% drop to hit TP - very aggressive target")

print()
print("="*80)
print("DEEP DIVE: EQUITY vs EXPECTED from closed PnL + open unrealized + commissions")
print("="*80)
for pid, port in data.items():
    initial = port['initial_capital']
    equity = port['equity']
    realized = sum(t.get('net_pnl_usd', 0) for t in port['closed'])
    unrealized = sum(p.get('pnl_usd', 0) for p in port['positions'])
    open_commissions = sum(p.get('commission_entry', 0) + p.get('slippage_entry', 0) for p in port['positions'])
    expected = initial + realized + unrealized - open_commissions
    diff = abs(expected - equity)
    if diff > 5:
        print(f"  [{pid}] Expected: {initial} + realized({realized:.2f}) + unrealized({unrealized:.2f}) - open_comm({open_commissions:.2f}) = {expected:.2f}")
        print(f"          Actual equity: {equity:.2f}, DIFF: {diff:.2f}")
