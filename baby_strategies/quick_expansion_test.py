#!/usr/bin/env python3
"""Quick Multi-Asset Strategy Test - Fast version"""

import sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np
import requests
import json

# Asset class symbols - single representative per class
ASSET_SYMBOLS = {
    'FOREX': ['EURUSDT'],
    'COMMODITY': ['PAXGUSDT'],
    'EQUITY': ['BNBUSDT'],
    'ETF': ['BTCTUSDT'],
    'FUTURES': ['PERPUSDT']
}

def get_klines(symbol, limit=200):
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit={limit}'
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        df = pd.DataFrame(data)
        df.columns = ['open_time','open','high','low','close','volume','close_time','quote','trades','taker_base','taker_quote','ignore']
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        return df[['open','high','low','close']]
    except:
        return None

# Simple strategy templates
def strat_bollinger_mr(df):
    close = df['close']
    sma = close.rolling(20).mean()
    std = close.rolling(20).std()
    lower = sma - 2 * std
    signals = []
    for i in range(20, len(df)-5):
        if close.iloc[i] <= lower.iloc[i] and close.iloc[i-1] > lower.iloc[i-1]:
            signals.append({'entry': close.iloc[i], 'tp': sma.iloc[i], 'sl': close.iloc[i]*0.98})
    return signals[:5]

def strat_rsi_rev(df):
    close = df['close']
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    signals = []
    for i in range(14, len(df)-5):
        if rsi.iloc[i] < 30 and rsi.iloc[i-1] >= 30:
            signals.append({'entry': close.iloc[i], 'tp': close.iloc[i]*1.03, 'sl': close.iloc[i]*0.97})
    return signals[:5]

def strat_macd(df):
    close = df['close']
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    signals = []
    for i in range(26, len(df)-5):
        if macd.iloc[i] > signal.iloc[i] and macd.iloc[i-1] <= signal.iloc[i-1]:
            signals.append({'entry': close.iloc[i], 'tp': close.iloc[i]*1.04, 'sl': close.iloc[i]*0.97})
    return signals[:5]

def strat_supertrend(df):
    close = df['close']
    high = df['high']
    low = df['low']
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(10).mean()
    hl_avg = (high + low) / 2
    upper = hl_avg + 3 * atr
    signals = []
    for i in range(10, len(df)-5):
        if close.iloc[i] > upper.iloc[i-1]:
            signals.append({'entry': close.iloc[i], 'tp': close.iloc[i]*1.05, 'sl': (hl_avg - 3*atr).iloc[i]})
    return signals[:5]

def strat_keltner_mr(df):
    close = df['close']
    high = df['high']
    low = df['low']
    ema = close.ewm(span=20, adjust=False).mean()
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(20).mean()
    lower = ema - 2 * atr
    signals = []
    for i in range(20, len(df)-5):
        if close.iloc[i] <= lower.iloc[i] and close.iloc[i-1] > lower.iloc[i-1]:
            signals.append({'entry': close.iloc[i], 'tp': ema.iloc[i], 'sl': close.iloc[i] - atr.iloc[i]*1.5})
    return signals[:5]

def strat_stoch_mr(df):
    close = df['close']
    high = df['high']
    low = df['low']
    k = 100 * (close - low.rolling(14).min()) / (high.rolling(14).max() - low.rolling(14).min())
    d = k.rolling(3).mean()
    signals = []
    for i in range(14, len(df)-5):
        if k.iloc[i] < 20 and d.iloc[i] < 20 and k.iloc[i] > d.iloc[i]:
            signals.append({'entry': close.iloc[i], 'tp': close.iloc[i]*1.03, 'sl': close.iloc[i]*0.97})
    return signals[:5]

def strat_adx_trend(df):
    close = df['close']
    high = df['high']
    low = df['low']
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    plus_dm = high.diff().where(high.diff() > 0, 0).rolling(14).mean()
    minus_dm = (-low.diff()).where(-low.diff() > 0, 0).rolling(14).mean()
    plus_di = 100 * plus_dm / atr
    minus_di = 100 * minus_dm / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(14).mean()
    signals = []
    for i in range(28, len(df)-5):
        if adx.iloc[i] > 25 and plus_di.iloc[i] > minus_di.iloc[i]:
            signals.append({'entry': close.iloc[i], 'tp': close.iloc[i]*1.04, 'sl': close.iloc[i]*0.97})
    return signals[:5]

def strat_williams_r(df):
    close = df['close']
    high = df['high']
    low = df['low']
    wr = -100 * (high.rolling(14).max() - close) / (high.rolling(14).max() - low.rolling(14).min())
    signals = []
    for i in range(14, len(df)-5):
        if wr.iloc[i] < -80 and wr.iloc[i-1] >= -80:
            signals.append({'entry': close.iloc[i], 'tp': close.iloc[i]*1.03, 'sl': close.iloc[i]*0.97})
    return signals[:5]

def strat_ema_cross(df):
    close = df['close']
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    signals = []
    for i in range(21, len(df)-5):
        if ema9.iloc[i] > ema21.iloc[i] and ema9.iloc[i-1] <= ema21.iloc[i-1]:
            signals.append({'entry': close.iloc[i], 'tp': close.iloc[i]*1.05, 'sl': ema21.iloc[i]})
    return signals[:5]

def strat_breakout(df):
    close = df['close']
    signals = []
    for i in range(20, len(df)-5):
        if close.iloc[i] > close.iloc[i-20:i].max():
            signals.append({'entry': close.iloc[i], 'tp': close.iloc[i]*1.06, 'sl': close.iloc[i]*0.97})
    return signals[:5]

STRATS = {
    'bollinger_mr': strat_bollinger_mr,
    'rsi_reversal': strat_rsi_rev,
    'macd_crossover': strat_macd,
    'supertrend': strat_supertrend,
    'keltner_mr': strat_keltner_mr,
    'stochastic_mr': strat_stoch_mr,
    'adx_trend': strat_adx_trend,
    'williams_r': strat_williams_r,
    'ema_cross': strat_ema_cross,
    'breakout': strat_breakout
}

def backtest(strategy_func, symbol, asset_class):
    df = get_klines(symbol)
    if df is None or len(df) < 50:
        return None
    try:
        signals = strategy_func(df)
    except:
        return None
    if not signals:
        return None
    
    trades = []
    for sig in signals:
        entry = sig['entry']
        tp = sig['tp']
        sl = sig['sl']
        idx = df[df['close'] >= entry].index
        if len(idx) > 0:
            start = df.index.get_loc(idx[0])
            future = df.iloc[start:min(start+10, len(df))]
            if len(future) > 0:
                if future['high'].max() >= tp:
                    trades.append((tp-entry)/entry*100)
                elif future['low'].min() <= sl:
                    trades.append((sl-entry)/entry*100)
                else:
                    trades.append(0)
    
    if not trades:
        return None
    wins = sum(1 for t in trades if t > 0)
    losses = sum(1 for t in trades if t < 0)
    wr = wins / len(trades) * 100
    win_pnl = sum(t for t in trades if t > 0)
    loss_pnl = abs(sum(t for t in trades if t < 0))
    pf = win_pnl / loss_pnl if loss_pnl > 0 else 0
    pnl = sum(trades)
    return {'strat': strategy_func.__name__, 'symbol': symbol, 'ac': asset_class, 'n': len(trades), 'wr': wr, 'pf': pf, 'pnl': pnl}

if __name__ == '__main__':
    print('=== QUICK EXPANSION TEST ===')
    results = []
    for ac, syms in ASSET_SYMBOLS.items():
        for sym in syms:
            for name, func in STRATS.items():
                r = backtest(func, sym, ac)
                if r:
                    results.append(r)
                    status = 'PASS' if r['wr'] >= 45 and r['pf'] >= 1.2 and r['pnl'] > 0 else 'FAIL'
                    print(f"{ac:10s} {sym:12s} {name:15s} n={r['n']:2d} WR={r['wr']:5.1f}% PF={r['pf']:5.2f} PnL={r['pnl']:>6.1f}% [{status}]")
    
    # Summary
    by_strat = {}
    for r in results:
        s = r['strat']
        if s not in by_strat:
            by_strat[s] = {'wins': 0, 'losses': 0, 'trades': 0, 'pnl': 0}
        by_strat[s]['trades'] += r['n']
        by_strat[s]['pnl'] += r['pnl']
        for _ in range(r['n']):
            if r['wr'] > 50:
                by_strat[s]['wins'] += 1
            else:
                by_strat[s]['losses'] += 1
    
    print('\n=== SUMMARY ===')
    passed = 0
    for s, d in sorted(by_strat.items(), key=lambda x: x[1]['pnl'], reverse=True):
        wr = d['wins']/d['trades']*100 if d['trades'] > 0 else 0
        win_pnl = sum(r['pnl'] for r in results if r['strat']==s and r['pnl']>0)
        loss_pnl = abs(sum(r['pnl'] for r in results if r['strat']==s and r['pnl']<0))
        pf = win_pnl/loss_pnl if loss_pnl > 0 else 0
        ok = wr >= 45 and pf >= 1.2 and d['pnl'] > 0
        if ok: passed += 1
        print(f"{s:20s} n={d['trades']:3d} WR={wr:5.1f}% PF={pf:5.2f} PnL={d['pnl']:>6.1f}% [{'PASS' if ok else 'FAIL'}]")
    print(f'\n{passed}/{len(by_strat)} strategies passed quality gates')