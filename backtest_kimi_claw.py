import ccxt
import pandas as pd
import numpy as np
from scipy.stats import ttest_1samp
import json
import time

def compute_rsi(series, period=2):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Symbols
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT']

# Exchange
exchange = ccxt.binance()

# Timeframe
timeframe = '5m'

# 3 years in milliseconds
since = int(time.time() * 1000) - (3 * 365 * 24 * 60 * 60 * 1000)

results = {}

for symbol in symbols:
    # Fetch data with paging
    ohlcv = []
    current_since = since
    while True:
        new_ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=1000)
        if not new_ohlcv:
            break
        ohlcv += new_ohlcv
        current_since = new_ohlcv[-1][0] + 1
        if current_since >= int(time.time() * 1000):
            break
        time.sleep(1)  # rate limit

    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('date', inplace=True)

    # Indicator
    df['rsi'] = compute_rsi(df['close'])

    # Signals
    df['buy'] = (df['rsi'] < 30) & (df['rsi'].shift(1) >= 30)
    df['sell'] = (df['rsi'] > 70) & (df['rsi'].shift(1) <= 70)

    # Simulate trades
    trades = []
    position = 0  # 0 neutral, 1 long, -1 short
    entry_price = None
    entry_time = None
    for idx, row in df.iterrows():
        if row['buy'] and position != 1:
            if position == -1:
                # Close short
                return_pct = (entry_price - row['close']) / entry_price
                trades.append(return_pct)
            # Enter long
            position = 1
            entry_price = row['close']
            entry_time = idx
        elif row['sell'] and position != -1:
            if position == 1:
                # Close long
                return_pct = (row['close'] - entry_price) / entry_price
                trades.append(return_pct)
            # Enter short
            position = -1
            entry_price = row['close']
            entry_time = idx

    # Close any open position at end
    if position != 0:
        exit_price = df['close'][-1]
        if position == 1:
            return_pct = (exit_price - entry_price) / entry_price
        else:
            return_pct = (entry_price - exit_price) / entry_price
        trades.append(return_pct)

    num_trades = len(trades)
    if num_trades < 500:
        print(f"Warning: Only {num_trades} trades for {symbol}. Still low.")

    # Metrics
    win_rate = np.mean(np.array(trades) > 0) if trades else 0
    returns = np.array(trades)
    mean_return = np.mean(returns)
    std_return = np.std(returns)
    sharpe = (mean_return / std_return) * np.sqrt(12 * 24 * 365) if std_return != 0 else 0

    # Max drawdown
    cum_returns = np.cumprod(1 + returns)
    peak = np.maximum.accumulate(cum_returns)
    drawdown = (peak - cum_returns) / peak
    max_dd = np.max(drawdown) if len(drawdown) > 0 else 0

    # t-test
    t_stat, p_value = ttest_1samp(returns, 0) if len(returns) > 1 else (0, 1)

    results[symbol] = {
        'num_trades': num_trades,
        'win_rate': win_rate,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd,
        't_stat': t_stat,
        'p_value': p_value
    }

# Output JSON
print(json.dumps(results, indent=4, default=str))
