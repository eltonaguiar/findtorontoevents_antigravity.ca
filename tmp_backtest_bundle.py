#!/usr/bin/env python3
"""TESTING_PROTOCOL.MD - Layer 1-2 Backtest Bundle for FOREX/COMMODITY Expansion Strategies"""

import sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime

# ============= DATA FETCHING =============
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

# ============= STRATEGY IMPLEMENTATIONS =============
def bollinger_mr_strategy(df, bb_period=20, bb_std=2.0, sma_period=200, tp_mult=2.5, sl_mult=1.5):
    """Bollinger Band Mean Reversion - used by FOREX and COMMODITY strategies"""
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
                position = {
                    'entry': current_price,
                    'tp': current_middle,
                    'sl': current_price - (current_atr * sl_mult),
                    'index': i
                }
        else:
            if current_price >= position['tp']:
                pnl = (position['tp'] - position['entry']) / position['entry'] * 100
                trades.append({'pnl': pnl, 'type': 'TP', 'bars': i - position['index']})
                position = None
            elif current_price <= position['sl']:
                pnl = (position['sl'] - position['entry']) / position['entry'] * 100
                trades.append({'pnl': pnl, 'type': 'SL', 'bars': i - position['index']})
                position = None
    
    return trades

def ensemble_4h_strategy(df, sma_short=20, sma_medium=50, tp_pct=3.0, sl_pct=2.0):
    """4h Ensemble Strategy - FOREX expansion"""
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
                position = {
                    'entry': current_price,
                    'direction': 'LONG',
                    'tp': current_price * (1 + tp_pct / 100),
                    'sl': current_price * (1 - sl_pct / 100),
                    'index': i
                }
            elif current_sma20 < current_sma50 and prev_sma20 >= prev_sma50 and atr_pct < 1.0:
                position = {
                    'entry': current_price,
                    'direction': 'SHORT',
                    'tp': current_price * (1 - tp_pct / 100),
                    'sl': current_price * (1 + sl_pct / 100),
                    'index': i
                }
        else:
            if position['direction'] == 'LONG':
                if current_price >= position['tp']:
                    pnl = (position['tp'] - position['entry']) / position['entry'] * 100
                    trades.append({'pnl': pnl, 'type': 'TP', 'direction': 'LONG', 'bars': i - position['index']})
                    position = None
                elif current_price <= position['sl']:
                    pnl = (position['sl'] - position['entry']) / position['entry'] * 100
                    trades.append({'pnl': pnl, 'type': 'SL', 'direction': 'LONG', 'bars': i - position['index']})
                    position = None
            else:
                if current_price <= position['tp']:
                    pnl = (position['entry'] - position['tp']) / position['entry'] * 100
                    trades.append({'pnl': pnl, 'type': 'TP', 'direction': 'SHORT', 'bars': i - position['index']})
                    position = None
                elif current_price >= position['sl']:
                    pnl = (position['entry'] - position['sl']) / position['entry'] * 100
                    trades.append({'pnl': pnl, 'type': 'SL', 'direction': 'SHORT', 'bars': i - position['index']})
                    position = None
    
    return trades

# ============= STRATEGIES TO TEST =============
strategies = [
    {'name': 'forex_bb_mr_rehab_v1', 'symbols': ['EURUSDT', 'GBPUSDT', 'AUDUSDT'], 'strategy_func': bollinger_mr_strategy},
    {'name': 'forex_ensemble_4h_rehab', 'symbols': ['EURUSDT', 'GBPUSDT', 'AUDUSDT', 'USDCAD'], 'strategy_func': ensemble_4h_strategy},
    {'name': 'paxg_bollinger_mr_rehab', 'symbols': ['PAXGUSDT'], 'strategy_func': bollinger_mr_strategy},
    {'name': 'xag_ensemble_rehab', 'symbols': ['XAGUSDT', 'XLMUSDT'], 'strategy_func': ensemble_4h_strategy},
]

print('='*70)
print('TESTING_PROTOCOL.MD - LAYER 1-2 BACKTEST BUNDLE')
print('FOREX/COMMODITY EXPANSION STRATEGIES')
print('='*70)

results = []
for strat in strategies:
    print(f"\n### {strat['name']} ###")
    strat_results = {'strategy': strat['name'], 'symbols': {}}
    
    for sym in strat['symbols']:
        df = get_klines(sym, '15m', 500)
        if df is None or len(df) < 250:
            print(f'  {sym}: SKIPPED (insufficient data)')
            continue
        
        trades = strat['strategy_func'](df)
        
        if len(trades) > 0:
            pnls = [t['pnl'] for t in trades]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p <= 0]
            wr = len(wins) / len(pnls) * 100
            avg_win = np.mean(wins) if wins else 0
            avg_loss = np.mean(losses) if losses else 0
            pf = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
            total_pnl = sum(pnls)
            
            # Layer 2: Calculate IS/OOS (70/30 split)
            is_cutoff = int(len(pnls) * 0.70)
            is_pnls = pnls[:is_cutoff] if is_cutoff > 0 else []
            oos_pnls = pnls[is_cutoff:]
            
            is_wr = len([p for p in is_pnls if p > 0]) / len(is_pnls) * 100 if is_pnls else 0
            oos_wr = len([p for p in oos_pnls if p > 0]) / len(oos_pnls) * 100 if oos_pnls else 0
            
            drift = abs(oos_wr - is_wr) if oos_pnls and is_pnls else 0
            
            print(f'  {sym}: n={len(trades)} WR={wr:.1f}% PF={pf:.2f} PnL={total_pnl:.1f}% | IS_WR={is_wr:.1f}% OOS_WR={oos_wr:.1f}% Drift={drift:.1f}pp')
            
            strat_results['symbols'][sym] = {
                'trades': len(trades),
                'wr': wr,
                'pf': pf,
                'pnl': total_pnl,
                'is_wr': is_wr,
                'oos_wr': oos_wr,
                'drift': drift
            }
        else:
            print(f'  {sym}: n=0 (no signals)')
    
    results.append(strat_results)

# Aggregate by strategy
print('\n' + '='*70)
print('AGGREGATE RESULTS BY STRATEGY')
print('='*70)

for r in results:
    all_symbols = r['symbols']
    if not all_symbols:
        print(f"\n### {r['strategy']}: NO VALID RESULTS")
        continue
    
    total_trades = sum(s['trades'] for s in all_symbols.values())
    total_pnl = sum(s['pnl'] for s in all_symbols.values())
    
    total_wins = sum(int(s['trades'] * s['wr'] / 100) for s in all_symbols.values())
    total_losses = sum(s['trades'] for s in all_symbols.values()) - total_wins
    
    agg_wr = total_wins / (total_wins + total_losses) * 100 if (total_wins + total_losses) > 0 else 0
    
    weighted_pf = sum(s['pf'] * s['trades'] for s in all_symbols.values()) / total_trades if total_trades > 0 else 0
    
    max_drift = max(s['drift'] for s in all_symbols.values()) if all_symbols else 0
    
    print(f"\n### {r['strategy']}")
    print(f"  Total: n={total_trades} WR={agg_wr:.1f}% PF={weighted_pf:.2f} PnL={total_pnl:.1f}%")
    print(f"  Layer 2.5 Gates: WR>=50%={'PASS' if agg_wr >= 50 else 'FAIL'}, PF>=1.2={'PASS' if weighted_pf >= 1.2 else 'FAIL'}, Drift<15pp={'PASS' if max_drift < 15 else 'FAIL'}")

print('\n' + '='*70)