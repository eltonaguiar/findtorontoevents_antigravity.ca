#!/usr/bin/env python3
"""TESTING_PROTOCOL.MD - Layer 5 Monte Carlo Robustness Test"""

import sys
sys.path.insert(0, '.')
import numpy as np
import pandas as pd
import requests

# Use the Monte Carlo simulator from alpha_engine
from alpha_engine.validation.monte_carlo import MonteCarloSimulator

def get_klines(symbol, interval='15m', limit=500):
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
        print(f'Error fetching {symbol}: {e}')
        return None

def bollinger_mr_strategy(df, bb_period=20, bb_std=2.0, sma_period=200, tp_mult=2.5, sl_mult=1.5):
    """Bollinger Band Mean Reversion"""
    close = df['close']
    high = df['high']
    low = df['low']
    
    sma = close.rolling(bb_period).mean()
    std = close.rolling(bb_period).std()
    lower_band = sma - bb_std * std
    middle_band = sma
    sma200 = close.rolling(sma_period).mean()
    
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14, min_periods=1).mean()
    
    trades = []
    position = None
    
    for i in range(sma_period + bb_period, len(df)):
        current_price = close.iloc[i]
        prev_price = close.iloc[i-1]
        current_lower = lower_band.iloc[i]
        current_middle = middle_band.iloc[i]
        current_sma200 = sma200.iloc[i]
        current_atr = atr.iloc[i]
        
        if position is None:
            if current_price <= current_lower and current_price > current_sma200 * 0.9 and prev_price > current_lower and current_atr > 0:
                position = {'entry': current_price, 'tp': current_middle, 'sl': current_price - (current_atr * sl_mult), 'index': i}
        else:
            if current_price >= position['tp']:
                pnl = (position['tp'] - position['entry']) / position['entry'] * 100
                trades.append({'pnl': pnl})
                position = None
            elif current_price <= position['sl']:
                pnl = (position['sl'] - position['entry']) / position['entry'] * 100
                trades.append({'pnl': pnl})
                position = None
    
    return trades

def ensemble_4h_strategy(df, sma_short=20, sma_medium=50, tp_pct=3.0, sl_pct=2.0):
    """4h Ensemble Strategy"""
    close = df['close']
    high = df['high']
    low = df['low']
    
    sma20 = close.rolling(sma_short).mean()
    sma50 = close.rolling(sma_medium).mean()
    
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14, min_periods=1).mean()
    
    trades = []
    position = None
    
    for i in range(sma_medium + 20, len(df)):
        current_price = close.iloc[i]
        current_sma20 = sma20.iloc[i]
        current_sma50 = sma50.iloc[i]
        current_atr = atr.iloc[i]
        prev_sma20 = sma20.iloc[i-1]
        prev_sma50 = sma50.iloc[i-1]
        
        atr_pct = (current_atr / current_price) * 100 if current_price > 0 else 0
        
        if position is None:
            if current_sma20 > current_sma50 and prev_sma20 <= prev_sma50 and atr_pct < 1.0:
                position = {'entry': current_price, 'direction': 'LONG', 'tp': current_price * (1 + tp_pct / 100), 'sl': current_price * (1 - sl_pct / 100), 'index': i}
            elif current_sma20 < current_sma50 and prev_sma20 >= prev_sma50 and atr_pct < 1.0:
                position = {'entry': current_price, 'direction': 'SHORT', 'tp': current_price * (1 - tp_pct / 100), 'sl': current_price * (1 + sl_pct / 100), 'index': i}
        else:
            if position['direction'] == 'LONG':
                if current_price >= position['tp']:
                    pnl = (position['tp'] - position['entry']) / position['entry'] * 100
                    trades.append({'pnl': pnl})
                    position = None
                elif current_price <= position['sl']:
                    pnl = (position['sl'] - position['entry']) / position['entry'] * 100
                    trades.append({'pnl': pnl})
                    position = None
            else:
                if current_price <= position['tp']:
                    pnl = (position['entry'] - position['tp']) / position['entry'] * 100
                    trades.append({'pnl': pnl})
                    position = None
                elif current_price >= position['sl']:
                    pnl = (position['entry'] - position['sl']) / position['entry'] * 100
                    trades.append({'pnl': pnl})
                    position = None
    
    return trades

# Initialize Monte Carlo simulator (2000 simulations per TESTING_PROTOCOL.MD)
mc = MonteCarloSimulator(n_simulations=2000, random_seed=42)

print('='*70)
print('TESTING_PROTOCOL.MD - LAYER 5 MONTE CARLO ROBUSTNESS TEST')
print('2000 Bootstrap Simulations - Stationary Block Bootstrap')
print('='*70)

# Test the most promising strategies based on Layer 1-2 results
test_cases = [
    {'name': 'paxg_bollinger_mr_rehab', 'symbol': 'PAXGUSDT', 'func': bollinger_mr_strategy},
    {'name': 'forex_bb_mr_rehab_v1', 'symbol': 'EURUSDT', 'func': bollinger_mr_strategy},
    {'name': 'forex_ensemble_4h_rehab', 'symbol': 'GBPUSDT', 'func': ensemble_4h_strategy},
]

for tc in test_cases:
    print(f"\n### {tc['name']} on {tc['symbol']} ###")
    
    df = get_klines(tc['symbol'], '15m', 500)
    if df is None or len(df) < 250:
        print(f"  SKIPPED: insufficient data")
        continue
    
    trades = tc['func'](df)
    
    if len(trades) < 5:
        print(f"  SKIPPED: only {len(trades)} trades (need >= 5 for Monte Carlo)")
        continue
    
    # Convert to returns (as decimal, not percentage)
    returns = np.array([t['pnl'] for t in trades]) / 100
    
    # Run Monte Carlo with block bootstrap (preserves autocorrelation for momentum strategies)
    result = mc.bootstrap_returns(
        pd.Series(returns),
        use_block_bootstrap=True,
        strategy_type="mean_reversion",
        block_size=20,
        n_sims=2000
    )
    
    if 'error' in result:
        print(f"  ERROR: {result['error']}")
        continue
    
    sharpe = result['sharpe']
    total_ret = result['total_return']
    prob_loss = result.get('probability_of_loss', 0)
    
    print(f"  Trades: {len(trades)}")
    print(f"  Sharpe: {sharpe['mean']:.2f} (95% CI: {sharpe['ci_5']:.2f} - {sharpe['ci_95']:.2f})")
    print(f"  Total Return: {total_ret['mean']*100:.1f}% (95% CI: {total_ret['ci_5']*100:.1f}% - {total_ret['ci_95']*100:.1f}%)")
    print(f"  Prob of Loss: {prob_loss*100:.1f}%")
    print(f"  Pct Positive Sharpe: {sharpe['pct_positive']*100:.1f}%")
    
    # Layer 5 Gate: Sharpe > 0 (lower bound of CI > 0) AND prob of loss < 20%
    sharpe_pass = sharpe['ci_5'] > 0
    loss_pass = prob_loss < 0.20
    
    print(f"  Layer 5 Gates: Sharpe CI>0={('PASS' if sharpe_pass else 'FAIL')}, ProbLoss<20%={('PASS' if loss_pass else 'FAIL')}")

print('\n' + '='*70)