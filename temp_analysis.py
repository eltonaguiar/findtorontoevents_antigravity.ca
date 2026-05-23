import csv, sys, os, math, statistics
from datetime import datetime

order_path = r'C:\\Users\\zerou\\Downloads\\paper-trading-order-history-all-2026-03-07T04_52_25.146Z.csv'
sol_path = r'C:\\Users\\zerou\\Downloads\\BINANCE_SOLUSDT, 15.csv'

# Load orders
orders = []
with open(order_path, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        orders.append(row)

win_orders = []
loss_orders = []
for o in orders:
    profit = None
    for key in o.keys():
        if 'profit' in key.lower() or 'pnl' in key.lower() or 'gain' in key.lower():
            profit = o[key]
            break
    if profit is None:
        continue
    try:
        profit_val = float(profit)
    except:
        continue
    if profit_val > 0:
        win_orders.append(o)
    else:
        loss_orders.append(o)

print(f'Total orders: {len(orders)}')
print(f'Winning orders: {len(win_orders)}')
print(f'Losing orders: {len(loss_orders)}')

# Load SOLUSDT 15 min data
sol = []
with open(sol_path, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        sol.append(row)


def parse_time(row):
    for key in row.keys():
        if 'time' in key.lower() or 'date' in key.lower():
            val = row[key]
            try:
                return datetime.fromisoformat(val)
            except:
                try:
                    return datetime.strptime(val, '%Y-%m-%d %H:%M:%S')
                except:
                    continue
    return None

sol_by_time = {}
for r in sol:
    t = parse_time(r)
    if t:
        sol_by_time[t] = r

win_conditions = []
loss_conditions = []
for o in win_orders:
    t = parse_time(o)
    if not t:
        continue
    closest = None
    for st in sol_by_time:
        if st <= t and (closest is None or st > closest):
            closest = st
    if closest:
        win_conditions.append(sol_by_time[closest])
for o in loss_orders:
    t = parse_time(o)
    if not t:
        continue
    closest = None
    for st in sol_by_time:
        if st <= t and (closest is None or st > closest):
            closest = st
    if closest:
        loss_conditions.append(sol_by_time[closest])

def avg_price_change(conds):
    changes = []
    for cond in conds:
        try:
            open_price = float(cond['open'])
            close_price = float(cond['close'])
            changes.append((close_price - open_price) / open_price)
        except:
            continue
    return statistics.mean(changes) if changes else None

print('Avg price change (next candle) win:', avg_price_change(win_conditions))
print('Avg price change (next candle) loss:', avg_price_change(loss_conditions))
