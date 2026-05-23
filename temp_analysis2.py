import csv, sys, os, statistics
from datetime import datetime, timedelta

order_path = r'C:\\Users\\zerou\\Downloads\\paper-trading-order-history-all-2026-03-07T04_52_25.146Z.csv'
sol_path = r'C:\\Users\\zerou\\Downloads\\BINANCE_SOLUSDT, 15.csv'

# Load orders
orders = []
with open(order_path, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        orders.append(row)

# Filter filled orders only
filled = [o for o in orders if o.get('Status','').lower()=='filled']

# Load SOL data
sol = []
with open(sol_path, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # convert time to datetime
        try:
            ts = int(row['time'])
            row['_dt'] = datetime.utcfromtimestamp(ts)
        except Exception:
            continue
        sol.append(row)
# Index sol by datetime for fast lookup
sol_by_dt = {r['_dt']: r for r in sol}
# Sort sol times
sol_times = sorted(sol_by_dt.keys())

def find_nearest_before(dt):
    # returns the latest sol entry <= dt
    for t in reversed(sol_times):
        if t <= dt:
            return sol_by_dt[t]
    return None

def price_change_after(entry_price, entry_dt, candles=3):
    # find candle after entry_dt + candles*15 minutes
    target_dt = entry_dt + timedelta(minutes=15*candles)
    # find nearest sol entry after target_dt
    for t in sol_times:
        if t >= target_dt:
            r = sol_by_dt[t]
            try:
                close = float(r['close'])
                return (close - entry_price) / entry_price
            except Exception:
                return None
    return None

wins = 0
losses = 0
changes_win = []
changes_loss = []
for o in filled:
    side = o.get('Side','').lower()
    # parse entry time
    pt = o.get('Placing Time') or o.get('Closing Time')
    if not pt:
        continue
    try:
        entry_dt = datetime.strptime(pt, '%Y-%m-%d %H:%M:%S')
    except Exception:
        continue
    # get fill price
    try:
        price = float(o['Fill Price'])
    except Exception:
        continue
    # market condition at entry
    sol_entry = find_nearest_before(entry_dt)
    # compute forward change
    change = price_change_after(price, entry_dt, candles=3)
    if change is None:
        continue
    if side == 'buy':
        if change > 0:
            wins += 1
            changes_win.append(change)
        else:
            losses += 1
            changes_loss.append(change)
    elif side == 'sell':
        # for sell, profit if price goes down
        if change < 0:
            wins += 1
            changes_win.append(change)
        else:
            losses += 1
            changes_loss.append(change)

print('Total filled orders:', len(filled))
print('Winning trades:', wins)
print('Losing trades:', losses)
if changes_win:
    print('Avg forward change (wins):', sum(changes_win)/len(changes_win))
if changes_loss:
    print('Avg forward change (losses):', sum(changes_loss)/len(changes_loss))
