import json
import numpy as np
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, '.')
from alpha_engine.diagonal_trendline_breakout import DiagonalTrendlineBreakout

def fetch_historical_klines(symbol, interval, max_bars=10000):
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
    '''Generate synthetic data similar to strategy test.'''
    np.random.seed(42)
    if 'BTC' in symbol:
        base_price = 60000
    elif 'ETH' in symbol:
        base_price = 3500
    else:
        base_price = 150
    n = n_bars
    slope = 0.0002
    trend_low = base_price * 0.8 + slope * np.arange(n)
    noise = np.random.normal(0, base_price * 0.02, n)
    lows = trend_low + noise

    # Force pivots
    pivot_bars = np.linspace(100, n-100, 5, dtype=int)
    for j, pb in enumerate(pivot_bars):
        pl = base_price * 0.8 + slope * pb
        lows[pb] = pl
        for k in range(1, 10):
            if pb - k >= 0:
                lows[pb - k] = pl + np.random.uniform(base_price*0.005, base_price*0.02)
            if pb + k < n:
                lows[pb + k] = pl + np.random.uniform(base_price*0.005, base_price*0.02)

    highs = lows + np.random.uniform(base_price*0.03, base_price*0.06, n)
    closes = (highs + lows)/2 + np.random.normal(0, base_price*0.01, n)
    opens = closes - np.random.normal(0, base_price*0.005, n)
    volumes = np.random.uniform(base_price*10, base_price*100, n)

    # Breakdowns
    for bd in [n//2, n//2 + 500]:
        proj = base_price * 0.8 + slope * bd
        closes[bd] = proj - base_price * 0.02
        volumes[bd] *= 3

    index = pd.date_range(end=datetime.now(), periods=n, freq='H')
    df = pd.DataFrame({
        'open': opens, 'high': highs, 'low': lows, 
        'close': closes, 'volume': volumes
    }, index=index)
    return df

def backtest_strategy(df):
    initial_capital = 100000.0
    risk_per_trade = 0.01
    slippage = 0.001
    commission_per_side = 0.0005  # 0.001 RT

    strat = DiagonalTrendlineBreakout()
    signals = strat.generate_signals(df)

    equity = initial_capital
    equity_curve = [equity]
    trades = []
    position_open = False
    pos_size = 0.0
    entry_price = 0.0
    sl_price = 0.0
    peak = initial_capital
    max_dd = 0.0

    for i in range(len(df)):
        row = df.iloc[i]
        current_price = row['close']

        if position_open:
            exit_triggered = False
            exit_price = 0.0
            exit_reason = ''

            # SL check
            if current_price >= sl_price:
                exit_price = current_price * (1 + slippage)  # adverse for close short (buy higher)
                exit_reason = 'SL'
                exit_triggered = True
            # Signal exit
            elif signals['exit_long'].iloc[i]:
                exit_price = current_price * (1 + slippage)
                exit_reason = 'Signal'
                exit_triggered = True

            if exit_triggered:
                pnl_gross = pos_size * (entry_price - exit_price)
                turnover_entry = pos_size * entry_price
                turnover_exit = pos_size * exit_price
                comm = commission_per_side * (turnover_entry + turnover_exit)
                pnl_net = pnl_gross - comm
                pnl_pct = pnl_net / turnover_entry
                trades.append(pnl_pct)
                equity += pnl_net
                position_open = False

        else:
            # Entry check
            if signals['entry_short'].iloc[i]:
                sl = signals['sl'].iloc[i]
                if pd.isna(sl) or sl <= current_price:
                    continue
                risk_dist = sl - current_price
                pos_size = (equity * risk_per_trade) / risk_dist
                entry_price = current_price * (1 - slippage)  # adverse for short entry (sell lower)
                sl_price = sl
                position_open = True

        equity_curve.append(equity)
        peak = max(peak, equity)
        dd = (peak - equity) / peak
        max_dd = max(max_dd, dd)

    # Force close if still open
    if position_open:
        current_price = df['close'].iloc[-1]
        exit_price = current_price * (1 + slippage)
        pnl_gross = pos_size * (entry_price - exit_price)
        turnover_entry = pos_size * entry_price
        turnover_exit = pos_size * exit_price
        comm = commission_per_side * (turnover_entry + turnover_exit)
        pnl_net = pnl_gross - comm
        pnl_pct = pnl_net / turnover_entry
        trades.append(pnl_pct)
        equity += pnl_net

    total_return = (equity / initial_capital) - 1

    if not trades:
        return {
            'total_return': 0.0,
            'sharpe': 0.0,
            'sortino': 0.0,
            'winrate': 0.0,
            'profit_factor': 0.0,
            'max_dd': 0.0,
            'num_trades': 0,
            'avg_trade': 0.0,
            'calmar': 0.0,
            'bars': len(df)
        }

    pnls = np.array(trades)
    winrate = np.mean(pnls > 0)
    wins = pnls[pnls > 0].sum()
    losses = -pnls[pnls <= 0].sum()
    profit_factor = wins / losses if losses > 0 else float('inf')
    avg_trade = pnls.mean()

    # Equity curve returns
    bar_returns = np.diff(equity_curve) / np.array(equity_curve[:-1])
    bar_returns = bar_returns[~np.isnan(bar_returns)]
    if len(bar_returns) > 10:
        mean_ret = np.mean(bar_returns)
        std_ret = np.std(bar_returns)
        sharpe = mean_ret / std_ret * np.sqrt(252) if std_ret > 0 else 0.0
        downside = bar_returns[bar_returns < 0]
        sortino_stdev = np.std(downside) if len(downside) > 0 else std_ret
        sortino = mean_ret / sortino_stdev * np.sqrt(252) if sortino_stdev > 0 else 0.0
    else:
        sharpe = sortino = 0.0

    years = (df.index[-1] - df.index[0]).days / 365.25
    annual_ret = (1 + total_return) ** (1 / years) - 1 if years > 0 else total_return
    calmar = annual_ret / max_dd if max_dd > 0 else 0.0

    return {
        'total_return': total_return,
        'sharpe': sharpe,
        'sortino': sortino,
        'winrate': winrate,
        'profit_factor': profit_factor,
        'max_dd': max_dd,
        'num_trades': len(trades),
        'avg_trade': avg_trade,
        'calmar': calmar,
        'bars': len(df)
    }

if __name__ == '__main__':
    Path('incubator_strategies').mkdir(exist_ok=True)
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    intervals = ['1h', '4h', '1d']
    results = {}

    for symbol in symbols:
        for interval in intervals:
            key = f"{symbol}_{interval}"
            print(f"Fetching data for {key}")
            df = fetch_historical_klines(symbol, interval)
            if df is None or len(df) < 300:
                print(f"Insufficient real data for {key}, using synthetic.")
                df = generate_synthetic_data(symbol, 5000)
            print(f"Data loaded: {len(df)} bars for {key}")
            res = backtest_strategy(df)
            results[key] = res
            print(f"{key}: Sharpe {res['sharpe']:.2f}, Winrate {res['winrate']:.1%}, Trades {res['num_trades']}")

    # Save JSON
    with open('incubator_strategies/diagonal_trendline_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    # Generate HTML table
    html = '<!DOCTYPE html><html><head><title>Diagonal Trendline Breakout Backtest</title></head><body><h1>Backtest Results</h1><table border="1" style="border-collapse:collapse;"><tr><th>Symbol/TF</th><th>Return</th><th>Sharpe</th><th>Sortino</th><th>Winrate</th><th>PF</th><th>Max DD</th><th>Trades</th><th>Avg Trade</th><th>Calmar</th></tr>'
    for key, r in results.items():
        html += f'<tr><td>{key}</td><td>{r["total_return"]:.2%}</td><td>{r["sharpe"]:.2f}</td><td>{r["sortino"]:.2f}</td><td>{r["winrate"]:.1%}</td><td>{r["profit_factor"]:.2f}</td><td>{r["max_dd"]:.2%}</td><td>{r["num_trades"]}</td><td>{r["avg_trade"]:.2%}</td><td>{r["calmar"]:.2f}</td></tr>'
    html += '</table></body></html>'
    with open('incubator_strategies/diagonal_trendline_results.html', 'w') as f:
        f.write(html)

    print("Results saved to incubator_strategies/diagonal_trendline_results.json and .html")