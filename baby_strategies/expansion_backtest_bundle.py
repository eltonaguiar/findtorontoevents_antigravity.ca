#!/usr/bin/env python3
"""
Multi-Asset Expansion Strategy Bundle
======================================
Creates and backtests strategies per asset class with quality gates.

Quality Gates:
- Win Rate >= 45%
- Profit Factor >= 1.2
- Total PnL > 0
- Minimum 3 trades

Asset Classes: FOREX, COMMODITY, EQUITY, ETF, FUTURES
"""

import sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np
import requests
import json
from typing import Dict, List, Optional

def get_klines(symbol: str, interval: str = '15m', limit: int = 500) -> Optional[pd.DataFrame]:
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        df = pd.DataFrame(data, columns=['open_time','open','high','low','close','volume','close_time','quote','trades','taker_base','taker_quote','ignore'])
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        return df[['open','high','low','close']]
    except Exception as e:
        return None

def strategy_bollinger_mr(df, params=None):
    params = params or {}
    bb_period = params.get('bb_period', 20)
    bb_std = params.get('bb_std', 2.0)
    sma_period = params.get('sma_period', 200)
    tp_mult = params.get('tp_mult', 2.5)
    sl_mult = params.get('sl_mult', 1.5)
    
    close = df['close']
    high = df['high']
    low = df['low']
    
    sma = close.rolling(bb_period).mean()
    std = close.rolling(bb_period).std()
    lower_band = sma - bb_std * std
    sma200 = close.rolling(sma_period).mean()
    
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14, min_periods=1).mean()
    
    trades = []
    position = None
    
    for i in range(sma_period + bb_period, len(df)):
        current_price = close.iloc[i]
        prev_price = close.iloc[i-1]
        current_lower = lower_band.iloc[i]
        current_sma200 = sma200.iloc[i]
        current_atr = atr.iloc[i]
        
        if position is None:
            if current_price <= current_lower and current_price > current_sma200 * 0.9:
                if prev_price > current_lower:
                    position = {'entry': current_price, 'type': 'LONG', 'sl': current_price - current_atr * sl_mult, 'tp': current_price + (current_price - current_lower) * tp_mult}
        else:
            if current_price >= position['tp'] or current_price <= position['sl']:
                pnl = (current_price - position['entry']) / position['entry'] * 100 if position['type'] == 'LONG' else 0
                trades.append(pnl)
                position = None
    return trades

def strategy_rsi_reversion(df, params=None):
    params = params or {}
    rsi_period = params.get('rsi_period', 14)
    oversold = params.get('oversold', 30)
    overbought = params.get('overbought', 70)
    tp_pct = params.get('tp_pct', 2.0)
    sl_pct = params.get('sl_pct', 1.0)
    
    close = df['close']
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    
    trades = []
    position = None
    
    for i in range(rsi_period + 10, len(df)):
        current_price = close.iloc[i]
        current_rsi = rsi.iloc[i]
        
        if position is None:
            if current_rsi <= oversold:
                position = {'entry': current_price, 'sl': current_price * (1 - sl_pct/100), 'tp': current_price * (1 + tp_pct/100)}
        else:
            if current_price >= position['tp'] or current_price <= position['sl']:
                pnl = (current_price - position['entry']) / position['entry'] * 100
                trades.append(pnl)
                position = None
            elif current_rsi >= overbought:
                pnl = (current_price - position['entry']) / position['entry'] * 100
                trades.append(pnl)
                position = None
    return trades

def strategy_sma_crossover(df, params=None):
    params = params or {}
    fast = params.get('fast', 20)
    slow = params.get('slow', 50)
    tp_pct = params.get('tp_pct', 3.0)
    sl_pct = params.get('sl_pct', 1.5)
    
    close = df['close']
    sma_fast = close.rolling(fast).mean()
    sma_slow = close.rolling(slow).mean()
    
    trades = []
    position = None
    
    for i in range(slow + 5, len(df)):
        current_price = close.iloc[i]
        current_fast = sma_fast.iloc[i]
        current_slow = sma_slow.iloc[i]
        prev_fast = sma_fast.iloc[i-1]
        prev_slow = sma_slow.iloc[i-1]
        
        if position is None:
            if current_fast > current_slow and prev_fast <= prev_slow:
                position = {'entry': current_price, 'type': 'LONG', 'sl': current_price * (1 - sl_pct/100), 'tp': current_price * (1 + tp_pct/100)}
            elif current_fast < current_slow and prev_fast >= prev_slow:
                position = {'entry': current_price, 'type': 'SHORT', 'sl': current_price * (1 + sl_pct/100), 'tp': current_price * (1 - tp_pct/100)}
        else:
            if position['type'] == 'LONG':
                if current_price >= position['tp'] or current_price <= position['sl']:
                    pnl = (current_price - position['entry']) / position['entry'] * 100
                    trades.append(pnl)
                    position = None
            else:
                if current_price <= position['tp'] or current_price >= position['sl']:
                    pnl = (position['entry'] - current_price) / position['entry'] * 100
                    trades.append(pnl)
                    position = None
    return trades

STRATEGY_BUNDLES = {
    'FOREX': [
        ('BB_MR_EURUSD', strategy_bollinger_mr, {'bb_std': 1.5, 'tp_mult': 2.0}),
        ('RSI_REV_EURUSD', strategy_rsi_reversion, {'oversold': 25}),
        ('SMA_CROSS_4H', strategy_sma_crossover, {'fast': 20, 'slow': 50}),
    ],
    'COMMODITY': [
        ('BB_MR_PAXG', strategy_bollinger_mr, {'bb_std': 2.0, 'tp_mult': 2.5}),
        ('RSI_REV_PAXG', strategy_rsi_reversion, {'tp_pct': 3.0}),
        ('SMA_CROSS_GOLD', strategy_sma_crossover, {'fast': 30, 'slow': 100}),
    ],
    'EQUITY': [
        ('BB_MR_TECH', strategy_bollinger_mr, {'bb_std': 2.0, 'tp_mult': 3.0}),
        ('RSI_REV_MOMENTUM', strategy_rsi_reversion, {'tp_pct': 4.0}),
    ],
    'ETF': [('BB_MR_ETF', strategy_bollinger_mr, {'bb_std': 2.0})],
    'FUTURES': [('BB_MR_CONTANGO', strategy_bollinger_mr, {'bb_std': 2.5})]
}

SYMBOLS = {
    'FOREX': ['EURUSDT', 'GBPUSDT', 'AUDUSDT'],
    'COMMODITY': ['PAXGUSDT', 'XAUTUSDT'],
    'EQUITY': ['BTCUSDT', 'ETHUSDT'],
    'ETF': ['BNBUSDT'],
    'FUTURES': ['ETHUSDT']
}

def run_backtest(strategy_fn, df, params) -> Dict:
    trades = strategy_fn(df, params)
    if len(trades) < 3:
        return {'trades': len(trades), 'wins': 0, 'losses': 0, 'wr': 0, 'pf': 0, 'pnl': 0, 'pass': False}
    
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 1
    profit_factor = (avg_win * len(wins)) / (avg_loss * len(losses)) if losses and len(losses) > 0 else 99.99
    total_pnl = sum(trades)
    passes = win_rate >= 45 and profit_factor >= 1.2 and total_pnl > 0
    
    return {'trades': len(trades), 'wins': len(wins), 'losses': len(losses), 'wr': round(win_rate, 1), 'pf': round(profit_factor, 2), 'pnl': round(total_pnl, 2), 'pass': passes}

def run_full_bundle():
    results = {}
    for asset_class, strategies in STRATEGY_BUNDLES.items():
        print(f"\n=== {asset_class} ===")
        results[asset_class] = {}
        symbols = SYMBOLS.get(asset_class, [])
        
        for strat_name, strat_fn, params in strategies:
            best_result = {'trades': 0, 'pass': False}
            for symbol in symbols:
                df = get_klines(symbol, '15m', 300)
                if df is None or len(df) < 200:
                    continue
                result = run_backtest(strat_fn, df, params)
                if result['trades'] > best_result['trades']:
                    best_result = result
            
            results[asset_class][strat_name] = best_result
            status = "PASS" if best_result.get('pass') else "FAIL"
            print(f"  {strat_name}: WR={best_result.get('wr',0)}% PF={best_result.get('pf',0):.2f} PnL={best_result.get('pnl',0)}% [{status}]")
    
    return results

if __name__ == "__main__":
    print("Starting Multi-Asset Expansion Backtest Bundle...")
    results = run_full_bundle()
    
    print("\n=== FINAL SUMMARY ===")
    passed = failed = 0
    for ac, strats in results.items():
        for name, r in strats.items():
            if r.get('pass'): passed += 1
            else: failed += 1
    print(f"Total: {passed} passed / {failed} failed")
    
    with open('tmp_expansion_backtest_results.json', 'w') as f:
        json.dump(results, f, indent=2)