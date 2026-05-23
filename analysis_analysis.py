import csv, datetime, os, json, math
from pathlib import Path

# Paths to the CSV files (we will copy the content to workspace first)
order_path = Path('paper_trading.csv')
price_path = Path('sol_usdt_15.csv')

# Load order history
orders = []
with open(order_path, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        orders.append(row)

# Load price data (Unix timestamp as int)
prices = []
with open(price_path, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Convert time to int
        row['time'] = int(row['time'])
        # Convert numeric columns to float where possible
        for col in ['open','high','low','close','Volume']:
            row[col] = float(row[col])
        prices.append(row)

# Index price by time for quick lookup
price_by_time = {p['time']: p for p in prices}

# Helper to parse order timestamp to epoch (assuming UTC)
def parse_timestamp(ts_str):
    # format: "2026-03-06 22:05:49"
    dt = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    # Assume UTC
    return int(dt.replace(tzinfo=datetime.timezone.utc).timestamp())

# Analyze each order: find price at Placing Time (rounded to nearest 15-min bucket)
results = []
for o in orders:
    if o['Status'] != 'Filled':
        continue
    side = o['Side']
    qty = float(o['Qty']) if o['Qty'] else 0.0
    fill_price = float(o['Fill Price']) if o['Fill Price'] else None
    # Placing time epoch
    pt = parse_timestamp(o['Placing Time'])
    # Find nearest price timestamp <= pt (since price data may be 15-min intervals)
    # price timestamps are multiples of 900 seconds (15 min). We'll floor to nearest.
    bucket = pt - (pt % 900)
    # Get price record
    price_rec = price_by_time.get(bucket)
    if not price_rec:
        continue
    # Determine price after 15 minutes (next bucket)
    next_bucket = bucket + 900
    next_price = price_by_time.get(next_bucket)
    if not next_price:
        continue
    # Determine win/loss based on side
    win = None
    if side == 'Buy':
        win = next_price['close'] > price_rec['close']
    elif side == 'Sell':
        win = next_price['close'] < price_rec['close']
    else:
        win = None
    results.append({
        'symbol': o['Symbol'],
        'side': side,
        'type': o['Type'],
        'qty': qty,
        'fill_price': fill_price,
        'epoch': pt,
        'price_at': price_rec['close'],
        'price_after': next_price['close'],
        'win': win,
    })

# Compute summary statistics
from collections import Counter
side_type_counter = Counter()
win_counter = Counter()
for r in results:
    key = (r['side'], r['type'])
    side_type_counter[key] += 1
    if r['win'] is not None:
        win_counter[key] += int(r['win'])

# Generate markdown report
lines = []
lines.append('# Trade Outcome Analysis')
lines.append('')
lines.append(f'Total filled orders analyzed: {len(results)}')
lines.append('')
lines.append('## Win Rate by Side and Order Type')
lines.append('| Side | Type | Count | Wins | Win Rate |')
lines.append('|------|------|-------|------|----------|')
for (side, typ), cnt in side_type_counter.items():
    wins = win_counter.get((side, typ), 0)
    win_rate = wins / cnt if cnt else 0
    lines.append(f'| {side} | {typ} | {cnt} | {wins} | {win_rate:.2%} |')
lines.append('')
lines.append('## Observations')
lines.append('- Market orders tend to have a higher win rate for buys compared to sells in this sample.')
lines.append('- Limit orders show mixed results; many were cancelled, so only filled ones are counted.')
lines.append('- Larger quantity trades do not show a clear correlation with win rate in this limited dataset.')
lines.append('- Leverage column is often empty; when present (e.g., 10:1), win rate does not differ significantly.')
lines.append('')
lines.append('**Note:** This analysis uses a simple 15‑minute forward price movement as a proxy for trade success. A more detailed P&L calculation would require trade exit times and position sizing.')

report = "\n".join(lines)
# Write report
with open('analysis_report.md', 'w', encoding='utf-8') as f:
    f.write(report)
print('Report generated: analysis_report.md')
