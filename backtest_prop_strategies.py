#!/usr/bin/env python3
'''Backtest prop-firm strategies on multiple assets.'''

import math
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from alpha_engine.prop_strategies import rsi, hma_slope, atr, volume_confirm  # Reuse indicators

def binomial_p(wins: int, n: int) -> float:
    if n == 0: return 1.0
    p = 0.0
    for k in range(wins, n+1):
        p += math.comb(n, k) * (0.5 ** k) * (0.5 ** (n - k))
    return p

def calc_sharpe(pnls):
    if len(pnls) < 2: return 0.0
    arr = np.array(pnls)
    mean = np.mean(arr)
    std = np.std(arr, ddof=1)
    return (mean / std) * np.sqrt(252) if std > 0 else 0.0

def fetch_data(symbol, period='5y'):
    df = yf.download(symbol, period=period, interval='1d', progress=False)
    df.columns = df.columns.get_level_values(0) if isinstance(df.columns, pd.MultiIndex) else df.columns
    return df.dropna()

def report(name, results):
    print(f'\n{"="*60}')
    print(f'  {name}')
    print(f'{"="*60}')
    n = results["n_trades"]
    if n == 0:
        print('  No trades.')
        return
    print(f'  Trades: {n}')
    print(f'  WR: {results["win_rate"]:.1%}')
    print(f'  Avg PnL: {results["avg_pnl"]:.2f}%')
    print(f'  Total PnL: {results["total_pnl"]:.1f}%')
    print(f'  Sharpe: {results["sharpe"]:.2f}')
    print(f'  p-value: {results["pval"]:.4f} {"*" if results["sig"] else ""}')
    sig = "*" if results["sig"] else ""
    print(f'  Significant: {sig}')

def backtest_connors(symbol='BTC-USD', period='5y'):
    df = fetch_data(symbol, period)
    if len(df) < 100: return {'n_trades':0, 'symbol':symbol}
    
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']
    
    r2 = rsi(close, 2)
    hs = hma_slope(close)
    atrv = atr(high, low, close)
    
    trades = []
    warmup = 50
    for i in range(warmup, len(close)):
        vol_ok = volume.iloc[i] > volume.iloc[max(0,i-20):i].mean() * 1.2
        
        if pd.isna([r2.iloc[i], hs.iloc[i], atrv.iloc[i]]).any(): continue
        
        entry_price = close.iloc[i]
        tp_dist = 2.5 * atrv.iloc[i]
        sl_dist = 1.5 * atrv.iloc[i]
        
        # Long
        if r2.iloc[i] < 10 and hs.iloc[i] > 0 and vol_ok:
            entry_i = i
            for j in range(i+1, min(i+11, len(close))):  # max 10 days
                if close.iloc[j] >= entry_price + tp_dist:
                    pnl = (tp_dist / entry_price) * 100
                    days = j - entry_i
                    trades.append({'pnl_pct': pnl, 'days': days, 'won': True})
                    break
                if close.iloc[j] <= entry_price - sl_dist:
                    pnl = -(sl_dist / entry_price) * 100
                    days = j - entry_i
                    trades.append({'pnl_pct': pnl, 'days': days, 'won': False})
                    break
            else:
                # time exit at close[i+10]
                pnl = (close.iloc[min(i+10, len(close)-1)] - entry_price) / entry_price * 100
                trades.append({'pnl_pct': pnl, 'days': 10, 'won': pnl>0})
        
        # Short similar
        elif r2.iloc[i] > 90 and hs.iloc[i] < 0 and vol_ok:
            entry_i = i
            for j in range(i+1, min(i+11, len(close))):
                if close.iloc[j] <= entry_price - tp_dist:
                    pnl = (tp_dist / entry_price) * 100
                    days = j - entry_i
                    trades.append({'pnl_pct': pnl, 'days': days, 'won': True})
                    break
                if close.iloc[j] >= entry_price + sl_dist:
                    pnl = -(sl_dist / entry_price) * 100
                    days = j - entry_i
                    trades.append({'pnl_pct': pnl, 'days': days, 'won': False})
                    break
            else:
                pnl = (entry_price - close.iloc[min(i+10, len(close)-1)]) / entry_price * 100
                trades.append({'pnl_pct': pnl, 'days': 10, 'won': pnl>0})
    
    n = len(trades)
    if n == 0: return {'n_trades':0, 'symbol':symbol}
    
    pnls = [t['pnl_pct'] for t in trades]
    wins = sum(1 for t in trades if t['won'])
    wr = wins / n
    avg_pnl = np.mean(pnls)
    total_pnl = sum(pnls)
    sharpe = calc_sharpe(pnls)
    pval = binomial_p(wins, n)
    sig = pval < 0.05
    
    return {
        'n_trades': n,
        'win_rate': wr,
        'avg_pnl': avg_pnl,
        'total_pnl': total_pnl,
        'sharpe': sharpe,
        'pval': pval,
        'sig': sig,
        'symbol': symbol
    }

if __name__ == '__main__':
    symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'SPY', 'QQQ', 'ES=F', 'NQ=F', 'YM=F', 'CL=F', 'GC=F']
    print('Backtesting Connors RSI2 Prop on:', symbols)
    for sym in symbols:
        res = backtest_connors(sym)
        report(f'Connors RSI2 Prop - {sym}', res)
