import json, sys
from collections import defaultdict, Counter

with open('audit_dashboard/data/claudes_test_state.json') as f:
    data = json.load(f)

print(f'Total portfolios: {len(data)}')
print(f'Portfolio IDs: {list(data.keys())}')
print()

# Price ranges for sanity checks
PRICE_RANGES = {
    'BTC': (50000, 120000),
    'ETH': (1000, 6000),
    'DOGE': (0.01, 1.0),
    'SOL': (20, 400),
    'XRP': (0.3, 5.0),
    'BNB': (200, 1000),
    'TRX': (0.05, 0.5),
    'ADA': (0.1, 3.0),
    'AVAX': (10, 200),
    'DOT': (3, 50),
    'LINK': (5, 50),
    'MATIC': (0.3, 3.0),
    'UNI': (3, 30),
    'LTC': (50, 300),
    'NEAR': (1, 20),
    'WLD': (0.1, 15),
    'SEI': (0.01, 5),
    'NOT': (0.00001, 0.05),
    'HUMA': (0.001, 1.0),
    'ZRO': (0.5, 20),
}

def get_base_symbol(symbol):
    s = symbol.upper().replace('-USD','').replace('USDT','').replace('USD','')
    return s

issues = []

# Track cross-portfolio data
all_position_sets = {}
symbol_portfolio_count = defaultdict(list)

for pid, port in data.items():
    prefix = f'[{pid}]'

    # === EQUITY MATH ===
    initial = port['initial_capital']
    equity = port['equity']
    cash = port['cash']
    hwm = port['high_water_mark']
    wins = port['wins']
    losses = port['losses']

    # Sum open position sizes
    open_pos_total = sum(p['size_usd'] for p in port['positions'])
    expected_equity_from_positions = cash + open_pos_total
    diff = abs(expected_equity_from_positions - equity)
    if diff > 10:
        issues.append(('CRITICAL', f'{prefix} Equity math: cash({cash:.2f}) + positions({open_pos_total:.2f}) = {expected_equity_from_positions:.2f}, but equity = {equity:.2f} (diff={diff:.2f})'))

    # HWM check
    if hwm < equity - 0.01:
        issues.append(('HIGH', f'{prefix} high_water_mark ({hwm:.2f}) < equity ({equity:.2f})'))

    # Win/loss count vs closed trades
    closed = port['closed']
    actual_wins = sum(1 for t in closed if t.get('net_pnl_usd', 0) > 0)
    actual_losses = sum(1 for t in closed if t.get('net_pnl_usd', 0) <= 0)
    if wins != actual_wins:
        issues.append(('HIGH', f'{prefix} wins={wins} but actual winning closed trades={actual_wins}'))
    if losses != actual_losses:
        issues.append(('HIGH', f'{prefix} losses={losses} but actual losing closed trades={actual_losses}'))
    if wins + losses != len(closed):
        issues.append(('HIGH', f'{prefix} wins({wins})+losses({losses})={wins+losses} != len(closed)={len(closed)}'))

    # Realized PnL sum check
    realized_pnl = sum(t.get('net_pnl_usd', 0) for t in closed)
    unrealized_pnl = sum(p.get('pnl_usd', 0) for p in port['positions'])
    total_pnl = realized_pnl + unrealized_pnl
    equity_pnl = equity - initial
    pnl_diff = abs(total_pnl - equity_pnl)
    if pnl_diff > 50:
        issues.append(('HIGH', f'{prefix} PnL reconciliation: realized({realized_pnl:.2f}) + unrealized({unrealized_pnl:.2f}) = {total_pnl:.2f}, but equity-initial = {equity_pnl:.2f} (diff={pnl_diff:.2f})'))

    # === OPEN POSITIONS ===
    pos_ids = set()
    pos_symbols = []
    for p in port['positions']:
        pid_id = p['id']
        sym = p['symbol']
        base = get_base_symbol(sym)
        direction = p['direction']
        entry = p['entry_price']
        tp = p['take_profit']
        sl = p['stop_loss']
        size = p['size_usd']

        pos_symbols.append(sym)
        symbol_portfolio_count[sym].append(pid)

        # Duplicate ID check
        if pid_id in pos_ids:
            issues.append(('CRITICAL', f'{prefix} Duplicate open position ID: {pid_id}'))
        pos_ids.add(pid_id)

        # Price range check
        if base in PRICE_RANGES:
            lo, hi = PRICE_RANGES[base]
            if entry < lo or entry > hi:
                issues.append(('CRITICAL', f'{prefix} {sym} entry_price={entry} outside expected range [{lo}, {hi}]'))

        # TP/SL direction check
        if direction == 'LONG':
            if tp <= entry:
                issues.append(('CRITICAL', f'{prefix} {sym} LONG but take_profit({tp}) <= entry({entry})'))
            if sl >= entry:
                issues.append(('CRITICAL', f'{prefix} {sym} LONG but stop_loss({sl}) >= entry({entry})'))
        elif direction == 'SHORT':
            if tp >= entry:
                issues.append(('CRITICAL', f'{prefix} {sym} SHORT but take_profit({tp}) >= entry({entry})'))
            if sl <= entry:
                issues.append(('CRITICAL', f'{prefix} {sym} SHORT but stop_loss({sl}) <= entry({entry})'))

        # Size check
        if size <= 0 or size > 100000:
            issues.append(('HIGH', f'{prefix} {sym} size_usd={size} is suspicious'))

        # Strategy check
        if not p.get('strategy'):
            issues.append(('MEDIUM', f'{prefix} {sym} has no strategy name'))

        # Timestamp check
        opened = p.get('opened_at', '')
        if '2027' in opened or '2025' in opened:
            issues.append(('HIGH', f'{prefix} {sym} opened_at={opened} seems wrong year'))

    # Track position sets for cross-portfolio comparison
    all_position_sets[pid] = frozenset((p['id'], p['symbol'], p['direction']) for p in port['positions'])

    # === CLOSED TRADES ===
    closed_ids = set()
    for t in closed:
        tid = t['id']
        sym = t['symbol']
        base = get_base_symbol(sym)
        direction = t['direction']
        entry = t['entry_price']
        exit_p = t.get('exit_price', 0)
        pnl_pct = t.get('pnl_pct', 0)
        pnl_usd = t.get('pnl_usd', 0)
        net_pnl = t.get('net_pnl_usd', 0)
        size = t['size_usd']

        # Duplicate closed trade ID within this portfolio
        if tid in closed_ids:
            issues.append(('MEDIUM', f'{prefix} Duplicate closed trade ID: {tid} ({sym})'))
        closed_ids.add(tid)

        # Price range check for entry
        if base in PRICE_RANGES:
            lo, hi = PRICE_RANGES[base]
            if entry < lo or entry > hi:
                issues.append(('CRITICAL', f'{prefix} CLOSED {sym} entry_price={entry} outside [{lo}, {hi}]'))
            if exit_p and (exit_p < lo * 0.1 or exit_p > hi * 3):
                issues.append(('CRITICAL', f'{prefix} CLOSED {sym} exit_price={exit_p} WAY outside reasonable range (base range [{lo}, {hi}])'))

        # PnL calculation verification
        if exit_p and entry:
            if direction == 'LONG':
                expected_pnl_pct = (exit_p - entry) / entry * 100
            else:
                expected_pnl_pct = (entry - exit_p) / entry * 100

            pnl_diff = abs(expected_pnl_pct - pnl_pct)
            if pnl_diff > 0.5:
                issues.append(('CRITICAL', f'{prefix} CLOSED {sym} PnL% mismatch: calculated={expected_pnl_pct:.4f}%, recorded={pnl_pct:.4f}% (diff={pnl_diff:.4f}%)'))

        # pnl_usd vs size * pnl_pct check
        if pnl_usd != 0:
            expected_pnl_usd = size * pnl_pct / 100
            pnl_usd_diff = abs(expected_pnl_usd - pnl_usd)
            if pnl_usd_diff > 2.0:
                issues.append(('HIGH', f'{prefix} CLOSED {sym} pnl_usd mismatch: size({size:.2f})*pnl%({pnl_pct:.4f})/100 = {expected_pnl_usd:.2f}, recorded={pnl_usd:.2f} (diff={pnl_usd_diff:.2f})'))

        # net_pnl should be less than gross pnl (commissions deducted)
        if net_pnl > pnl_usd and pnl_usd > 0:
            issues.append(('HIGH', f'{prefix} CLOSED {sym} net_pnl({net_pnl:.2f}) > gross_pnl({pnl_usd:.2f}) - impossible'))

        # Exit reason check
        reason = t.get('exit_reason', '')
        if reason not in ('TP', 'SL', 'MANUAL', 'TIMEOUT', 'SIGNAL', 'TRAILING', ''):
            issues.append(('LOW', f'{prefix} CLOSED {sym} unusual exit_reason: {reason}'))

        # TP hit but exit_price beyond TP (slippage ok but not extreme)
        if reason == 'TP' and tp:
            if direction == 'LONG' and exit_p > tp * 1.05:
                issues.append(('MEDIUM', f'{prefix} CLOSED {sym} TP hit but exit({exit_p}) >> TP({tp}) by {((exit_p/tp)-1)*100:.1f}%'))
            elif direction == 'SHORT' and exit_p < tp * 0.95:
                issues.append(('MEDIUM', f'{prefix} CLOSED {sym} TP hit SHORT but exit({exit_p}) << TP({tp})'))

# === CROSS-PORTFOLIO CHECKS ===

# Check for identical position sets
portfolio_ids = list(all_position_sets.keys())
for i in range(len(portfolio_ids)):
    for j in range(i+1, len(portfolio_ids)):
        p1, p2 = portfolio_ids[i], portfolio_ids[j]
        if all_position_sets[p1] and all_position_sets[p1] == all_position_sets[p2]:
            issues.append(('HIGH', f'Portfolios {p1} and {p2} have IDENTICAL position sets'))

# Check symbol concentration across portfolios
for sym, ports in symbol_portfolio_count.items():
    if len(ports) > 10:
        issues.append(('MEDIUM', f'Symbol {sym} appears in {len(ports)} portfolios: too concentrated'))

# Check for the specific TRX exit price issue in contrarian (noticed it was 0.06697 which is way below normal TRX range)
# Already handled by price range checks

# Print results
print('='*80)
print('AUDIT REPORT')
print('='*80)

severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
issues.sort(key=lambda x: severity_order.get(x[0], 99))

counts = Counter(sev for sev, _ in issues)
print(f'CRITICAL: {counts.get("CRITICAL", 0)}')
print(f'HIGH: {counts.get("HIGH", 0)}')
print(f'MEDIUM: {counts.get("MEDIUM", 0)}')
print(f'LOW: {counts.get("LOW", 0)}')
print(f'TOTAL ISSUES: {sum(counts.values())}')
print()

for sev, msg in issues:
    print(f'[{sev}] {msg}')

print()
print('='*80)
print('PORTFOLIO SUMMARY')
print('='*80)
for pid, port in data.items():
    eq = port['equity']
    init = port['initial_capital']
    pnl = eq - init
    n_open = len(port['positions'])
    n_closed = len(port['closed'])
    print(f'{pid}: equity=${eq:.2f} (PnL=${pnl:.2f}), open={n_open}, closed={n_closed}, W={port["wins"]}/L={port["losses"]}')

print()
print('='*80)
print('SYMBOL CONCENTRATION')
print('='*80)
sym_counts = Counter()
for sym, ports in symbol_portfolio_count.items():
    sym_counts[sym] = len(ports)
for sym, cnt in sym_counts.most_common(20):
    print(f'  {sym}: in {cnt} portfolios')
