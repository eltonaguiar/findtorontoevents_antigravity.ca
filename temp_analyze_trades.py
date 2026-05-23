import csv
import datetime
from collections import defaultdict

# Paths to the CSV files (adjust if needed)
order_path = r"C:\Users\zerou\Downloads\paper-trading-order-history-all-2026-03-07T04_52_25.146Z.csv"
chart_path = r"C:\Users\zerou\Downloads\BINANCE_SOLUSDT, 15.csv"

# Load chart data into a dict keyed by timestamp (int)
# Also capture all numeric indicator columns for later analysis
chart = {}
indicator_names = []
with open(chart_path, newline='') as f:
    reader = csv.DictReader(f)
    # Determine which columns are numeric indicators (exclude known price/volume fields)
    for col in reader.fieldnames:
        if col not in ['time', 'open', 'high', 'low', 'close', 'Volume']:
            indicator_names.append(col)
    for row in reader:
        ts = int(row['time'])
        # Convert indicator values to float where possible
        for ind in indicator_names:
            try:
                row[ind] = float(row[ind])
            except Exception:
                row[ind] = None
        chart[ts] = row

# Helper: find the next chart timestamp after a given datetime
def next_chart_ts(dt):
    ts = int(dt.timestamp())
    for ct in sorted(chart.keys()):
        if ct > ts:
            return ct
    return None

wins = 0
losses = 0
unknown = 0
# Store indicator values per trade outcome
win_indicators = defaultdict(list)
loss_indicators = defaultdict(list)

with open(order_path, newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        side = row['Side'].lower()
        fill_price_str = row.get('Fill Price')
        if not fill_price_str:
            continue
        fill_price = float(fill_price_str)
        # Parse placing time (expected format "YYYY-MM-DD HH:MM:SS")
        try:
            pt = datetime.datetime.strptime(row['Placing Time'], "%Y-%m-%d %H:%M:%S")
        except Exception:
            unknown += 1
            continue
        nxt_ts = next_chart_ts(pt)
        if nxt_ts is None:
            unknown += 1
            continue
        close_price = float(chart[nxt_ts]['close'])
        # Determine win/loss
        if side == 'buy':
            win = close_price > fill_price
        else:
            win = close_price < fill_price
        if win:
            wins += 1
            target_dict = win_indicators
        else:
            losses += 1
            target_dict = loss_indicators
        # Record indicator values at the next candle
        for ind in indicator_names:
            val = chart[nxt_ts][ind]
            if val is not None:
                target_dict[ind].append(val)

print(f"Total trades analyzed: {wins + losses}")
print(f"Wins: {wins}, Losses: {losses}, Unknown/Skipped: {unknown}")

# Compute average indicator values for wins vs losses
print("\nAverage indicator values for winning trades:")
for ind in indicator_names:
    vals = win_indicators.get(ind, [])
    if vals:
        avg = sum(vals) / len(vals)
        print(f"{ind}: {avg:.6f}")
print("\nAverage indicator values for losing trades:")
for ind in indicator_names:
    vals = loss_indicators.get(ind, [])
    if vals:
        avg = sum(vals) / len(vals)
        print(f"{ind}: {avg:.6f}")

# Simple difference (win avg - loss avg) to hint at correlation direction
print("\nDifference (Win Avg - Loss Avg):")
for ind in indicator_names:
    win_vals = win_indicators.get(ind, [])
    loss_vals = loss_indicators.get(ind, [])
    if win_vals and loss_vals:
        diff = (sum(win_vals)/len(win_vals)) - (sum(loss_vals)/len(loss_vals))
        print(f"{ind}: {diff:.6f}")
