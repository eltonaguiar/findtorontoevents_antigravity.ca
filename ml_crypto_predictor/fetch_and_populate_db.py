import sqlite3
import pandas as pd
import ccxt
import time
from datetime import datetime

# List of pairs
pairs = [
    'TRX/USDT', 'BTC/USDT', 'ALGO/USDT', 'ETH/USDT', 'DOT/USDT', 'SOL/USDT', 'XRP/USDT',
    'INJ/USDT', 'ARB/USDT', 'APE/USDT', 'DOGE/USDT', 'FET/USDT', 'DYDX/USDT', 'SHIB/USDT'
]

MIN_BARS = 3000  # Engine needs 2500+, fetch extra for safety
BATCH_SIZE = 1000
db_path = 'crypto_data.db'
timeframe = '1h'

# Use Bybit for historical data (Kraken ignores `since` for old dates, Binance is geo-blocked)
# Fallback chain: Bybit -> KuCoin -> Kraken
def get_exchange():
    for name in ['bybit', 'kucoin', 'kraken']:
        try:
            ex = getattr(ccxt, name)()
            test = ex.fetch_ohlcv('BTC/USDT', '1h', limit=5)
            if test and len(test) > 0:
                print(f'Using exchange: {name}')
                return ex, name
        except Exception as e:
            print(f'  {name} failed: {e}')
    raise RuntimeError('No working exchange found')

exchange, exchange_name = get_exchange()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Ensure table exists
cursor.execute('''CREATE TABLE IF NOT EXISTS klines (
    pair TEXT, timestamp TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL,
    UNIQUE(pair, timestamp)
)''')

for pair in pairs:
    # Get last timestamp and count from DB
    cursor.execute("SELECT MAX(timestamp), COUNT(*) FROM klines WHERE pair = ?", (pair,))
    row = cursor.fetchone()
    last_ts, bar_count = row[0], row[1]

    if bar_count >= MIN_BARS and last_ts:
        # Just fetch new bars since last timestamp
        since = exchange.parse8601(last_ts.replace(' ', 'T') + '+00:00') + 3600000
    else:
        # Need to backfill — ~4000 hourly bars (167 days back from now)
        # More than 2500+ needed but capped to avoid multi-hour backtesting
        from datetime import timedelta
        backfill_start = datetime.utcnow() - timedelta(days=170)
        since = exchange.parse8601(backfill_start.strftime('%Y-%m-%dT00:00:00Z'))

    # Kraken uses /USD not /USDT
    symbol = pair.replace('/USDT', '/USD') if exchange_name == 'kraken' else pair
    total_fetched = 0

    # Paginate to get enough bars (cap at 5 pages = ~5000 bars to keep backtest fast)
    for page in range(5):
        try:
            klines = exchange.fetch_ohlcv(symbol, timeframe, since, limit=BATCH_SIZE)
        except Exception as e:
            print(f'  Error fetching {pair} (page {page}): {e}')
            break

        if not klines:
            break

        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['pair'] = pair

        for _, r in df.iterrows():
            timestamp_str = r['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
            INSERT OR IGNORE INTO klines (pair, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (r['pair'], timestamp_str, r['open'], r['high'], r['low'], r['close'], r['volume']))

        total_fetched += len(klines)
        since = klines[-1][0] + 3600000  # next page starts after last bar

        if len(klines) < BATCH_SIZE:
            break  # no more data available

        time.sleep(0.5)  # rate limit courtesy

    cursor.execute("SELECT COUNT(*) FROM klines WHERE pair = ?", (pair,))
    final_count = cursor.fetchone()[0]
    print(f'Populated {total_fetched} new bars for {pair} (total: {final_count})')

conn.commit()
conn.close()

print('Database population complete.')
