import json
import numpy as np
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, '.')
from ta.volatility import BollingerBands, AverageTrueRange
from alpha_engine.bollinger_meanrev import BBMeanRevTrader

def fetch_historical_klines(symbol, interval, max_bars=5000):
    '''Fetch historical klines from AsterDEX (Binance-compatible).'''
    base_url = 'https://fapi.asterdex.com/fapi/v1/klines'
    all_klines = []
    end_time = None
    call_count = 0
    max_calls = 50  # safety
    while len(all_klines) < max_bars and call_count < max_calls:
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': 1000
        }
        if end_time is not None:
            params['endTime'] = end_time
        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            klines = response.json()
        except Exception as e:
            print(f'Fetch error for {symbol} {interval}: {e}')
            break
        if not klines:
            break
        # Remove some overlap
        if end_time is not None:
            overlap = min(20, len(klines) // 50)
            klines = klines[:-overlap]
        all_klines = klines + all_klines
        end_time = klines[0][0] - 1
        call_count += 1
        if len(klines) < 1000:
            break
    if not all_klines:
        return None
    df_list = []
    for kline in all_klines:
        df_list.append({
            'timestamp': pd.to_datetime(kline[0], unit='ms'),
            'open': float(kline[1]),
            'high': float(kline[2]),
            'low': float(kline[3]),
            'close': float(kline[4]),
            'volume': float(kline[5])
        })
    df = pd.DataFrame(df_list)
    df.set_index('timestamp', inplace=True)
    df = df.sort_index()
    return df.tail(max_bars)

def generate_synthetic_data(symbol, n_bars=5000):
    np.random.seed(42)
    if 'BTC' in symbol:
        base_price = 60000
    elif 'ETH' in symbol:
        base_price = 3500
    else:
        base_price = 150
    n_bars = n_bars
    returns = np.random.normal(0, 0.01, n_bars)
    close = base_price * np.exp(np.cumsum(returns))
    noise = np.random.normal(0, 0.01 * 2, n_bars)
    high = np.maximum(close * (1 + np.abs(noise)), close)
    low = np.minimum(close * (1 - np.abs(noise)), close)
    open_prices = np.roll(close, 1)
    open_prices[0] = base_price
    index = pd.date_range(end=datetime.now(), periods=n_bars, freq='H')
    df = pd.DataFrame({
        'open': open_prices,
        'high': high,
        'low': low,
        'close': close,
        'volume': np.random.randint(1000, 10000, n_bars)
    }, index=index)
    return df

def backtest_strategy(df, interval):
    initial_capital = 100000.0
    # Compute indicators
    bb = BollingerBands(close=df['close'], window=20, window_dev=2.0)
    df['bb_lower'] = bb.bollinger_lband()
    df['bb_mid'] = bb.bollinger_mavg()
    df['bb_upper'] = bb.bollinger_hband()
    atr_ind = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14)
    df['atr'] = atr_ind.average_true_range()
    trader = BBMeanRevTrader(initial_cash=initial_capital, risk_per_trade=0.01)
    equity_curve = [initial_capital]
    peak = initial_capital
    max_dd = 0.0
    for _, row in df.iterrows():
        if pd.isna(row['bb_lower']) or pd.isna(row['atr']) or row['atr'] <= 0:
            equity = trader.current_equity(row['close'])
        else:
            trader.on_bar(row['high'], row['low'], row['close'], row['bb_upper'], row['bb_lower'], row['bb_mid'], row['atr'])
            equity = trader.current_equity(row['close'])
        equity_curve.append(equity)
        peak = max(peak, equity)
        dd = (peak - equity) / peak
        max_dd = max(max_dd, dd)
    total_return = (equity_curve[-1] / initial_capital - 1)
    bar_returns = pd.Series(equity_curve).pct_change().dropna()
    annual_factors = {'1h': 365.25 * 24, '4h': 365.25 * 6, '1d': 252}
    af = annual_factors[interval]
    sharpe = 0.0
    sortino = 0.0
    if len(bar_returns) > 10 and bar_returns.std() > 0:
        sharpe = bar_returns.mean() / bar_returns.std() * np.sqrt(af)
        downside = bar_returns[bar_returns < 0]
        ds_std = downside.std() if len(downside) > 0 else bar_returns.std()
        if ds_std > 0:
            sortino = bar_returns.mean() / ds_std * np.sqrt(af)
    years = len(df) / af
    annual_ret = (1 + total_return) ** (1 / years) - 1 if years > 0 else total_return
    calmar = annual_ret / max_dd if max_dd > 0 else 0.0
    num_trades = trader.trades
    open_pos = 1 if abs(trader.position) > 1e-8 else 0
    realized_pnl_pct = trader.realized_pnl / initial_capital
    return {
        'total_return': total_return,
        'sharpe': sharpe,
        'sortino': sortino,
        'max_dd': max_dd,
        'num_trades': num_trades,
        'open_positions': open_pos,
        'realized_pnl_pct': realized_pnl_pct,
        'calmar': calmar,
        'bars': len(df)
    }

if __name__ == '__main__':
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    intervals = ['1h', '4h', '1d']
    results = {}
    for symbol in symbols:
        for interval in intervals:
            key = f"{symbol}_{interval}"
            print(f"Fetching data for {key}...")
            df = fetch_historical_klines(symbol, interval)
            if df is None or len(df) < 300:
                print(f"Insufficient data, using synthetic for {key}")
                df = generate_synthetic_data(symbol, 5000)
            print(f"Data: {len(df)} bars for {key}")
            res = backtest_strategy(df, interval)
            results[key] = res
            print(f"{key}: Return {res['total_return']:.2%}, Sharpe {res['sharpe']:.2f}, Max DD {res['max_dd']:.2%}, Trades {res['num_trades']}")
    # Save JSON
    with open('bollinger_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    # Generate HTML table
    html = '<!DOCTYPE html><html><head><title>Bollinger Mean Reversion Backtest</title><style>table {{border-collapse: collapse;}} th, td {{border: 1px solid black; padding: 8px; text-align: center;}}</style></head><body><h1>Bollinger Bands Mean Reversion Backtest Results</h1><table><tr><th>Symbol/TF</th><th>Total Return</th><th>Sharpe</th><th>Sortino</th><th>Max DD</th><th>Num Trades</th><th>Open Pos</th><th>Real PnL%</th><th>Calmar</th><th>Bars</th></tr>'
    for key, r in results.items():
        html += f'<tr><td>{key}</td><td>{r["total_return"]:.2%}</td><td>{r["sharpe"]:.2f}</td><td>{r["sortino"]:.2f}</td><td>{r["max_dd"]:.2%}</td><td>{r["num_trades"]}</td><td>{r["open_positions"]}</td><td>{r["realized_pnl_pct"]:.2%}</td><td>{r["calmar"]:.2f}</td><td>{r["bars"]}</td></tr>'
    html += '</table></body></html>'
    with open('bollinger_results.html', 'w') as f:
        f.write(html)
    print("Full bollinger results saved to bollinger_results.json and bollinger_results.html")