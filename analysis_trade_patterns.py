import csv, datetime, time, os, sys
from pathlib import Path

# Paths to CSV files (assumed to be in the same directory as this script)
ORDER_CSV = r"C:\Users\zerou\Downloads\paper-trading-order-history-all-2026-03-07T04_52_25.146Z.csv"
SOL_CSV = r"C:\Users\zerou\Downloads\BINANCE_SOLUSDT, 15.csv"

# Load SOL price data into a dict keyed by timestamp (int seconds)
sol_prices = {}
with open(SOL_CSV, newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # time column is epoch seconds (int)
        ts = int(row['time'])
        # store close price as float
        sol_prices[ts] = float(row['close'])

# Helper to find the next price after a given timestamp
def next_price(ts):
    # find the smallest key greater than ts
    future = [t for t in sol_prices.keys() if t > ts]
    if not future:
        return None
    next_ts = min(future)
    return sol_prices[next_ts]

# Analyze orders
results = []
with open(ORDER_CSV, newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Only consider filled market orders for simplicity
        if row['Status'] != 'Filled':
            continue
        symbol = row['Symbol']
        side = row['Side'].lower()
        # Parse Placing Time (assume format "%Y-%m-%d %H:%M:%S")
        try:
            dt = datetime.datetime.strptime(row['Placing Time'], "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        ts = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp())
        entry_price = float(row['Fill Price']) if row['Fill Price'] else None
        if entry_price is None:
            continue
        # Get the next 15‑minute close price (the first timestamp after the order)
        nxt = next_price(ts)
        if nxt is None:
            continue
        # Determine win/loss based on side
        if side == 'buy':
            win = nxt > entry_price
        else:
            win = nxt < entry_price
        results.append({
            'symbol': symbol,
            'side': side,
            'entry_price': entry_price,
            'next_close': nxt,
            'win': win,
            'time': row['Placing Time']
        })

# Summarize
wins = sum(1 for r in results if r['win'])
losses = len(results) - wins
print(f"Analyzed {len(results)} filled market orders.")
print(f"Wins: {wins}, Losses: {losses}, Win rate: {wins/(len(results) or 1):.2%}")
# Show a few examples
for r in results[:10]:
    print(r)
