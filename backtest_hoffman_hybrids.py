#!/usr/bin/env python3
"""
Backtest Hoffman Winning Combos + New Hybrid Strategies
"""

import sys
sys.path.insert(0, '.')

import time
import numpy as np
import pandas as pd
import requests
from datetime import datetime, timezone

from baby_strategies.hoffman_winning_combos import ALL_STRATEGIES

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT', 'XRPUSDT']

def fetch_klines(symbol, interval='15m', limit=1000):
    url = 'https://api.binance.com/api/v3/klines'
    resp = requests.get(url, params={'symbol': symbol, 'interval': interval, 'limit': limit}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    df = pd.DataFrame(data, columns=['open_time', 'open', 'high', 'low', 'close', 'volume',
                                     'close_time', 'qav', 'trades', 'tbbav', 'tbqav', 'ignore'])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    return df

def simulate_trades(signals_by_bar, df, max_hold=2):
    trades = []
    position = None
    
    for bar_idx in range(len(df)):
        price = df['close'].iloc[bar_idx]
        high = df['high'].iloc[bar_idx]
        low = df['low'].iloc[bar_idx]
        
        if position is not None:
            entry = position['entry_price']
            hold_bars = bar_idx - position['entry_bar']
            
            if position['direction'] == 'BUY':
                if low <= position['sl']:
                    pnl = (position['sl'] - entry) / entry * 100
                    trades.append({'pnl_pct': pnl, 'exit': 'SL', 'hold': hold_bars})
                    position = None
                    continue
                elif high >= position['tp']:
                    pnl = (position['tp'] - entry) / entry * 100
                    trades.append({'pnl_pct': pnl, 'exit': 'TP', 'hold': hold_bars})
                    position = None
                    continue
            else:
                if high >= position['sl']:
                    pnl = (entry - position['sl']) / entry * 100
                    trades.append({'pnl_pct': pnl, 'exit': 'SL', 'hold': hold_bars})
                    position = None
                    continue
                elif low <= position['tp']:
                    pnl = (entry - position['tp']) / entry * 100
                    trades.append({'pnl_pct': pnl, 'exit': 'TP', 'hold': hold_bars})
                    position = None
                    continue
            
            if hold_bars >= max_hold:
                pnl = (price - entry) / entry * 100 if position['direction'] == 'BUY' else (entry - price) / entry * 100
                trades.append({'pnl_pct': pnl, 'exit': 'TIME', 'hold': hold_bars})
                position = None
                continue
        
        if position is None and bar_idx in signals_by_bar:
            sig = signals_by_bar[bar_idx]
            position = {
                'entry_bar': bar_idx,
                'entry_price': sig.entry_price,
                'tp': sig.take_profit,
                'sl': sig.stop_loss,
                'direction': sig.direction,
            }
    
    return trades

def backtest_strategy(strategy_class, all_data):
    all_trades = []
    
    for sym, df in all_data.items():
        signals_by_bar = {}
        warmup = 60
        
        for i in range(warmup, len(df)):
            subset = df.iloc[:i+1].reset_index(drop=True)
            try:
                sigs = strategy_class.generate_signals(subset, sym)
                if sigs:
                    signals_by_bar[i] = max(sigs, key=lambda s: s.confidence)
            except:
                continue
        
        # Use max_hold=2 for scalper strategies, 16 for others
        max_hold = 2 if 'scalper' in strategy_class.NAME else 16
        trades = simulate_trades(signals_by_bar, df, max_hold)
        all_trades.extend(trades)
    
    if not all_trades:
        return {'trades': 0, 'wr': 0, 'pf': 0, 'pnl': 0}
    
    wins = [t for t in all_trades if t['pnl_pct'] > 0]
    losses = [t for t in all_trades if t['pnl_pct'] <= 0]
    
    total_pnl = sum(t['pnl_pct'] for t in all_trades)
    gross_profit = sum(t['pnl_pct'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['pnl_pct'] for t in losses)) if losses else 0.001
    
    return {
        'trades': len(all_trades),
        'wr': round(len(wins)/len(all_trades)*100, 1),
        'pf': round(gross_profit/gross_loss, 2),
        'pnl': round(total_pnl, 2)
    }

def main():
    print('=' * 90)
    print('  Hoffman Winning Combos + Hybrid Strategies Backtest')
    print(f'  {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}')
    print('=' * 90)
    
    # Fetch data
    print('\nFetching historical data...')
    all_data = {}
    for sym in SYMBOLS:
        try:
            all_data[sym] = fetch_klines(sym)
            print(f'  {sym}: {len(all_data[sym])} bars')
        except Exception as e:
            print(f'  {sym}: FAILED - {e}')
        time.sleep(0.3)
    
    if not all_data:
        print('No data fetched - aborting')
        return
    
    print(f'\nBacktesting {len(ALL_STRATEGIES)} strategies...')
    print('-' * 90)
    print(f"{'Status':<6} {'Strategy':<30} {'Trades':>6} {'Win%':>6} {'PF':>6} {'PnL%':>8}")
    print('-' * 90)
    
    results = []
    for strat in ALL_STRATEGIES:
        metrics = backtest_strategy(strat, all_data)
        results.append({
            'name': strat.NAME,
            'expected': strat.EXPECTED_WR,
            **metrics
        })
        
        status = '+' if metrics['wr'] >= 50 else 'o' if metrics['wr'] >= 40 else 'x'
        print(f"{status:<6} {strat.NAME:<30} {metrics['trades']:>6} {metrics['wr']:>6.1f} {metrics['pf']:>6.2f} {metrics['pnl']:>+8.1f}")
    
    print('-' * 90)
    
    # Summary
    print('\n' + '=' * 90)
    print('  RANKING BY WIN RATE (Target: >50%)')
    print('=' * 90)
    
    sorted_results = sorted(results, key=lambda x: x['wr'], reverse=True)
    for i, r in enumerate(sorted_results, 1):
        medal = "[1]" if i == 1 else "[2]" if i == 2 else "[3]" if i == 3 else "   "
        over50 = "PASS >50%" if r['wr'] >= 50 else ""
        print(f"{medal} {i}. {r['name']:<35} WR: {r['wr']:>5.1f}%  ({r['expected']:<9} expected)  {over50}")
    
    # Count how many achieved >50%
    over_50 = [r for r in results if r['wr'] >= 50]
    print(f"\n{len(over_50)}/{len(results)} strategies achieved >50% win rate")
    
    # Best by category
    print('\n' + '=' * 90)
    print('  BEST BY CATEGORY')
    print('=' * 90)
    
    # Best overall
    best = max(results, key=lambda x: x['wr'])
    print(f"  Best Win Rate:  {best['name']} ({best['wr']}%)")
    
    # Most trades
    most_trades = max(results, key=lambda x: x['trades'])
    print(f"  Most Trades:    {most_trades['name']} ({most_trades['trades']} trades)")
    
    # Best PnL
    best_pnl = max(results, key=lambda x: x['pnl'])
    print(f"  Best PnL:       {best_pnl['name']} ({best_pnl['pnl']}%)")
    
    # New hybrids summary
    print('\n' + '=' * 90)
    print('  NEW HYBRID STRATEGIES (Scalper + Filter)')
    print('=' * 90)
    hybrids = [r for r in results if 'scalper' in r['name']]
    for r in sorted(hybrids, key=lambda x: x['wr'], reverse=True):
        status = "OK" if r['wr'] >= 50 else "--"
        print(f"  {status} {r['name']:<35} WR: {r['wr']:>5.1f}%  |  Trades: {r['trades']:>4}  |  PF: {r['pf']:>4.2f}")

if __name__ == '__main__':
    main()
