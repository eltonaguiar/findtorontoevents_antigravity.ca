import requests
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import json
from datetime import datetime

# Add alpha_engine to path
sys.path.insert(0, 'alpha_engine')
from indicators import (atr, bollinger_squeeze, hma_slope, keltner_channels, volume_expansion, zscore, rsi, hurst_exponent)

CRYPTO_PAIRS = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'SHIBUSDT', 
    'AVAXUSDT', 'LINKUSDT', 'LTCUSDT', 'BCHUSDT', 'XLMUSDT', 'ALGOUSDT', 'VETUSDT', 
    'ICPUSDT', 'FILUSDT', 'ATOMUSDT', 'NEARUSDT', 'MATICUSDT'
]

def fetch_crypto_data(symbol: str, interval: str = '1h', limit: int = 1000) -> pd.DataFrame:
    """Fetch OHLCV data from Binance API."""

    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        response = requests.get(url, timeout=10)
        data = response.json()

        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return pd.DataFrame()

def calculate_performance_metrics(signals: list, initial_balance: float = 10000.0) -> dict:
    """Calculate performance metrics using probabilistic TP/SL hit simulation."""

    if not signals:
        return {'total_return': 0, 'win_rate': 0, 'profit_factor': 0, 'max_drawdown': 0, 'num_trades': 0, 'expected_pnl_pct': 0}

    balance = initial_balance
    peak_balance = initial_balance
    max_drawdown = 0
    total_pnl = 0
    wins = 0
    num_trades = 0
    gross_profit = 0
    gross_loss = 0

    for signal in signals:
        entry_price = signal['entry_price']
        tp = signal['take_profit']
        sl = signal['stop_loss']
        direction = signal['direction']

        if direction == 'BUY':
            tp_dist = tp - entry_price
            sl_dist = entry_price - sl
            tp_pct = tp_dist / entry_price
            sl_pct = (sl - entry_price) / entry_price
        else:
            tp_dist = entry_price - tp
            sl_dist = sl - entry_price
            tp_pct = tp_dist / entry_price
            sl_pct = (entry_price - sl) / entry_price

        total_range = tp_dist + sl_dist
        if total_range == 0:
            continue
        prob_tp = sl_dist / total_range
        expected_pnl_pct = prob_tp * tp_pct + (1 - prob_tp) * sl_pct

        risk_amount = initial_balance * 0.02
        pnl = expected_pnl_pct * risk_amount
        total_pnl += pnl
        balance += pnl
        num_trades += 1
        if expected_pnl_pct > 0:
            wins += 1
            gross_profit += pnl
        else:
            gross_loss += abs(pnl)

        if balance > peak_balance:
            peak_balance = balance
        drawdown = (peak_balance - balance) / peak_balance
        max_drawdown = max(max_drawdown, drawdown)

    total_return = total_pnl / initial_balance * 100
    win_rate = wins / num_trades * 100 if num_trades else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    return {
        'total_return': total_return,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown * 100,
        'num_trades': num_trades,
        'expected_pnl_pct': total_pnl / (num_trades * initial_balance * 0.02) * 100 if num_trades else 0
    }

def variation1_keltner_hma(df: pd.DataFrame, symbol: str) -> list:
    """Keltner squeeze breakout aligned with HMA slope."""

    if len(df) < 50:
        return []

    kc = keltner_channels(df['high'], df['low'], df['close'])
    bs = bollinger_squeeze(df['close'], df['high'], df['low'])
    hs = hma_slope(df['close'])
    atrv = atr(df['high'], df['low'], df['close'])

    signals = []
    for i in range(50, len(df)):
        price = float(df['close'].iloc[i])
        if pd.isna(bs.iloc[i]) or pd.isna(hs.iloc[i]) or pd.isna(atrv.iloc[i]):
            continue
        if bs.iloc[i]:
            if price > kc['upper'].iloc[i] and hs.iloc[i] > 0:
                tp = price + 2.5 * atrv.iloc[i]
                sl = price - 1.5 * atrv.iloc[i]
                signals.append({'direction': 'BUY', 'entry_price': price, 'take_profit': tp, 'stop_loss': sl})
            elif price < kc['lower'].iloc[i] and hs.iloc[i] < 0:
                tp = price - 2.5 * atrv.iloc[i]
                sl = price + 1.5 * atrv.iloc[i]
                signals.append({'direction': 'SELL', 'entry_price': price, 'take_profit': tp, 'stop_loss': sl})
    return signals

def variation2_multi_sigma_volume(df: pd.DataFrame, symbol: str) -> list:
    """Multi-sigma reversal confirmed by volume expansion."""

    if len(df) < 100:
        return []

    rets = df['close'].pct_change()
    z = zscore(rets, 100)
    ve = volume_expansion(df['volume'], threshold=1.3)
    atrv = atr(df['high'], df['low'], df['close'])

    signals = []
    for i in range(100, len(df)):
        if pd.isna(z.iloc[i]) or pd.isna(ve.iloc[i]) or pd.isna(atrv.iloc[i]):
            continue
        if abs(z.iloc[i]) > 2.5 and ve.iloc[i]:
            price = float(df['close'].iloc[i])
            if z.iloc[i] > 2.5:
                tp = price - 2.0 * atrv.iloc[i]
                sl = price + 1.5 * atrv.iloc[i]
                signals.append({'direction': 'SELL', 'entry_price': price, 'take_profit': tp, 'stop_loss': sl})
            else:
                tp = price + 2.0 * atrv.iloc[i]
                sl = price - 1.5 * atrv.iloc[i]
                signals.append({'direction': 'BUY', 'entry_price': price, 'take_profit': tp, 'stop_loss': sl})
    return signals

def variation3_hurst_rsi(df: pd.DataFrame, symbol: str) -> list:
    """Hurst regime adaptive with RSI extremes."""

    if len(df) < 200:
        return []

    # Approximate rolling Hurst
    h_values = []
    step = 50
    for start in range(0, len(df)-100, step):
        end = min(start + 200, len(df))
        sample = df['close'].iloc[start:end]
        h = hurst_exponent(sample)
        h_values.extend([h] * step)
    h_series = pd.Series(h_values[:len(df)], index=df.index)
    rsi2 = rsi(df['close'], period=2)
    atrv = atr(df['high'], df['low'], df['close'])

    signals = []
    for i in range(100, len(df)):
        if pd.isna(h_series.iloc[i]) or pd.isna(rsi2.iloc[i]) or pd.isna(atrv.iloc[i]):
            continue
        h = h_series.iloc[i]
        r = rsi2.iloc[i]
        price = float(df['close'].iloc[i])
        if h < 0.40:
            if r < 10:
                tp = price + 2 * atrv.iloc[i]
                sl = price - 1 * atrv.iloc[i]
                signals.append({'direction': 'BUY', 'entry_price': price, 'take_profit': tp, 'stop_loss': sl})
            elif r > 90:
                tp = price - 2 * atrv.iloc[i]
                sl = price + 1 * atrv.iloc[i]
                signals.append({'direction': 'SELL', 'entry_price': price, 'take_profit': tp, 'stop_loss': sl})
    return signals

VARIATIONS = {
    'keltner_hma': variation1_keltner_hma,
    'multi_sigma_vol': variation2_multi_sigma_volume,
    'hurst_rsi': variation3_hurst_rsi
}

def run_variation_backtest(var_key: str, symbol: str) -> dict:
    df = fetch_crypto_data(symbol)
    if df.empty or len(df) < 200:
        return {'error': f'Insufficient data for {symbol}'}

    func = VARIATIONS[var_key]
    signals = func(df, symbol)
    metrics = calculate_performance_metrics(signals)
    return {
        'variation': var_key,
        'symbol': symbol,
        'signals_count': len(signals),
        **metrics
    }

def main():
    print('=' * 80)
    print('STRATEGY VARIATIONS BACKTEST - Lessons Applied (20 Crypto Pairs)')
    print('=' * 80)

    all_results = []
    for var_key, func in VARIATIONS.items():
        print(f'\n{func.__doc__.splitlines()[0]}')
        print('-' * 50)
        var_results = []
        for symbol in CRYPTO_PAIRS:
            result = run_variation_backtest(var_key, symbol)
            if 'error' not in result:
                var_results.append(result)
                all_results.append(result)
                print(f"{symbol:8} | Ret {result['total_return']:5.1f}% | Exp {result['expected_pnl_pct']:5.1f}% | Trades {result['num_trades']:3d} | PF {result['profit_factor']:4.2f}")
            else:
                print(f"{symbol:8} | ERROR: {result['error']}")

        if var_results:
            avg_ret = np.mean([r['total_return'] for r in var_results])
            avg_exp = np.mean([r['expected_pnl_pct'] for r in var_results])
            print(f"AVG: Ret {avg_ret:.1f}% | Exp PnL {avg_exp:.1f}% | Trades {sum(r['num_trades'] for r in var_results)}")

    print('\nTOP 10 PERFORMERS:')
    print('-' * 60)
    top = sorted(all_results, key=lambda x: x['total_return'], reverse=True)[:10]
    for r in top:
        print(f"{r['variation']:12} {r['symbol']:8} | Ret:{r['total_return']:6.1f}% | Exp:{r['expected_pnl_pct']:6.1f}% | PF:{r['profit_factor']:5.2f} | Trades:{r['num_trades']}")

    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'variations_backtest_{timestamp}.json'
    with open(filename, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f'\nFull results saved to {filename}')

if __name__ == '__main__':
    main()