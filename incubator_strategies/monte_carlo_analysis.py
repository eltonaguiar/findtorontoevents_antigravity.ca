import json
import numpy as np
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, '.')
from alpha_engine.rsi_momentum_strategy import rsi_momentum_strategy

def fetch_historical_klines(symbol, interval, max_bars=10000):
    base_url = 'https://fapi.asterdex.com/fapi/v1/klines'
    all_klines = []
    end_time = None
    call_count = 0
    max_calls = 50

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

def get_trades(df):
    initial_capital = 100000.0
    risk_per_trade = 0.01
    slippage = 0.001
    commission_per_side = 0.0005

    signals = rsi_momentum_strategy(df)

    equity = initial_capital
    trades = []
    position_open = False
    pos_size = 0.0
    entry_price = 0.0
    sl_price = 0.0

    for i in range(len(df)):
        row = df.iloc[i]
        current_price = row['close']

        if position_open:
            exit_triggered = False
            exit_price = 0.0

            if current_price <= sl_price:
                exit_price = current_price * (1 - slippage)
                exit_triggered = True
            elif signals['exit_long'].iloc[i]:
                exit_price = current_price * (1 - slippage)
                exit_triggered = True

            if exit_triggered:
                pnl_gross = pos_size * (exit_price - entry_price)
                turnover_entry = pos_size * entry_price
                turnover_exit = pos_size * exit_price
                comm = commission_per_side * (turnover_entry + turnover_exit)
                pnl_net = pnl_gross - comm
                pnl_pct = pnl_net / turnover_entry if turnover_entry > 0 else 0
                trades.append(pnl_pct)
                equity += pnl_net
                position_open = False

        else:
            if signals['entry_long'].iloc[i]:
                sl_pct = signals['sl_pct'].iloc[i]
                entry_price = current_price * (1 + slippage)
                sl_price = entry_price * (1 + sl_pct)
                risk_dist = entry_price - sl_price
                if risk_dist <= 0:
                    continue
                pos_size = (equity * risk_per_trade) / risk_dist
                position_open = True

    if position_open:
        current_price = df['close'].iloc[-1]
        exit_price = current_price * (1 - slippage)
        pnl_gross = pos_size * (exit_price - entry_price)
        turnover_entry = pos_size * entry_price
        turnover_exit = pos_size * exit_price
        comm = commission_per_side * (turnover_entry + turnover_exit)
        pnl_net = pnl_gross - comm
        pnl_pct = pnl_net / turnover_entry if turnover_entry > 0 else 0
        trades.append(pnl_pct)

    years = (df.index[-1] - df.index[0]).days / 365.25 if len(df) > 1 else 0
    return np.array(trades), years

if __name__ == '__main__':
    Path('incubator_strategies').mkdir(exist_ok=True)
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    intervals = ['1h', '4h', '1d']
    results = {}

    for symbol in symbols:
        for interval in intervals:
            key = f"{symbol}_{interval}"
            print(f"Processing {key}...")
            df = fetch_historical_klines(symbol, interval)
            if df is None or len(df) < 300:
                print(f"Insufficient data for {key}, skipping.")
                continue
            trades, years = get_trades(df)
            if len(trades) < 30:
                print(f"Insufficient trades ({len(trades)}) for {key}, skipping.")
                continue
            print(f"{key}: {len(trades)} trades over {years:.1f} years")

            n_sims = 1000
            sharpes = []
            total_rets = []
            max_dds = []
            ruin_probs = []

            trades_per_year = len(trades) / years if years > 0 else 0

            for _ in range(n_sims):
                sample = np.random.choice(trades, size=len(trades), replace=True)
                equity = np.cumprod(1 + sample)
                total_ret = equity[-1] - 1
                total_rets.append(total_ret)

                peak = np.maximum.accumulate(equity)
                dd = (peak - equity) / peak
                max_dd = dd.max()
                max_dds.append(max_dd)

                mean_ret = np.mean(sample)
                std_ret = np.std(sample)
                sharpe = mean_ret / std_ret * np.sqrt(trades_per_year) if std_ret > 0 else 0.0
                sharpes.append(sharpe)

                ruin = 1 if (max_dd > 0.10 or total_ret < 0) else 0
                ruin_probs.append(ruin)

            mc_res = {
                'median_sharpe': float(np.median(sharpes)),
                'sharpe_5': float(np.percentile(sharpes, 5)),
                'sharpe_95': float(np.percentile(sharpes, 95)),
                'ret_5': float(np.percentile(total_rets, 5)),
                'ret_95': float(np.percentile(total_rets, 95)),
                'max_dd_95': float(np.percentile(max_dds, 95)),
                'ruin_prob': float(np.mean(ruin_probs)),
                'num_trades': int(len(trades)),
                'years': float(years)
            }
            results[key] = mc_res
            print(f"  Median Sharpe: {mc_res['median_sharpe']:.2f} (5-95%: {mc_res['sharpe_5']:.2f} to {mc_res['sharpe_95']:.2f})")
            print(f"  Ret 5-95%: {mc_res['ret_5']:.1%} to {mc_res['ret_95']:.1%}")
            print(f"  95th DD: {mc_res['max_dd_95']:.1%}, Ruin prob: {mc_res['ruin_prob']:.1%}")

    with open('incubator_strategies/monte_carlo_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print("\nMonte Carlo results saved to incubator_strategies/monte_carlo_results.json")