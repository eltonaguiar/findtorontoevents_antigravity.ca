#!/usr/bin/env python3
"""
Multi-Asset Strategy Expansion Bundle
======================================
Creates and backtests 20+ strategies per asset class with quality gates.

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

# Asset class symbols
ASSET_SYMBOLS = {
    'FOREX': ['EURUSDT', 'GBPUSDT', 'AUDUSDT', 'USDCAD', 'USDJPY', 'USDCHF', 'NZDUSDT'],
    'COMMODITY': ['PAXGUSDT', 'XAUTUSDT', 'XLMUSDT', 'DOTUSDT', 'AVAXUSDT', 'LINKUSDT', 'UNIUSDT'],
    'EQUITY': ['BNBUSDT', 'SOLUSDT', 'ADAUSDT', 'XRPUSDT', 'DOGEUSDT', 'MATICUSDT', 'LTCUSDT', 'ETCUSDT'],
    'ETF': ['BTCTUSDT', 'PAXGUSDT', 'LINKUSDT', 'BNBUSDT'],
    'FUTURES': ['PERPUSDT', 'SOLUSDT', 'ETHUSDT', 'BTCUSDT', 'BNBUSDT']
}

def get_klines(symbol: str, interval: str = '15m', limit: int = 500) -> Optional[pd.DataFrame]:
    """Fetch klines from Binance"""
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
    except:
        return None

# ============= STRATEGY TEMPLATES =============

def strategy_bollinger_mr(df, params=None):
    """Bollinger Band Mean Reversion"""
    params = params or {}
    close = df['close']
    bb_period = params.get('bb_period', 20)
    bb_std = params.get('bb_std', 2.0)
    
    sma = close.rolling(bb_period).mean()
    std = close.rolling(bb_period).std()
    lower = sma - bb_std * std
    
    signals = []
    for i in range(bb_period, len(df)):
        if close.iloc[i] <= lower.iloc[i] and close.iloc[i-1] > lower.iloc[i-1]:
            entry = close.iloc[i]
            tp = sma.iloc[i]
            sl = entry - (entry * 0.02)
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_rsi_reversal(df, params=None):
    """RSI Mean Reversal"""
    params = params or {}
    close = df['close']
    rsi_period = params.get('rsi_period', 14)
    oversold = params.get('oversold', 30)
    
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    signals = []
    for i in range(rsi_period, len(df)):
        if rsi.iloc[i] < oversold and rsi.iloc[i-1] >= oversold:
            entry = close.iloc[i]
            tp = entry * 1.03
            sl = entry * 0.98
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_macd_crossover(df, params=None):
    """MACD Crossover Momentum"""
    params = params or {}
    close = df['close']
    fast = params.get('fast', 12)
    slow = params.get('slow', 26)
    signal_period = params.get('signal', 9)
    
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=signal_period, adjust=False).mean()
    
    signals = []
    for i in range(slow, len(df)):
        if macd.iloc[i] > signal.iloc[i] and macd.iloc[i-1] <= signal.iloc[i-1]:
            entry = close.iloc[i]
            tp = entry * 1.04
            sl = entry * 0.97
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_supertend(df, params=None):
    """Supertrend Trend Following"""
    params = params or {}
    close = df['close']
    high = df['high']
    low = df['low']
    period = params.get('period', 10)
    multiplier = params.get('multiplier', 3.0)
    
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    
    hl_avg = (high + low) / 2
    upper = hl_avg + multiplier * atr
    lower = hl_avg - multiplier * atr
    
    signals = []
    for i in range(period, len(df)):
        if close.iloc[i] > upper.iloc[i-1]:
            entry = close.iloc[i]
            tp = entry * 1.05
            sl = lower.iloc[i]
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_keltner_mr(df, params=None):
    """Keltner Channel Mean Reversion"""
    params = params or {}
    close = df['close']
    high = df['high']
    low = df['low']
    period = params.get('period', 20)
    mult = params.get('mult', 2.0)
    
    ema = close.ewm(span=period, adjust=False).mean()
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    
    lower = ema - mult * atr
    
    signals = []
    for i in range(period, len(df)):
        if close.iloc[i] <= lower.iloc[i] and close.iloc[i-1] > lower.iloc[i-1]:
            entry = close.iloc[i]
            tp = ema.iloc[i]
            sl = entry - (atr.iloc[i] * 1.5)
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_vwap_reversion(df, params=None):
    """VWAP Mean Reversion"""
    params = params or {}
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df.get('volume', pd.Series([1]*len(close)))
    
    typical = (high + low + close) / 3
    vwap = (typical * volume).cumsum() / volume.cumsum()
    
    signals = []
    for i in range(50, len(df)):
        if close.iloc[i] < vwap.iloc[i] * 0.98:
            entry = close.iloc[i]
            tp = vwap.iloc[i]
            sl = entry * 0.98
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_stochastic_mr(df, params=None):
    """Stochastic Oscillator Mean Reversion"""
    params = params or {}
    close = df['close']
    high = df['high']
    low = df['low']
    k_period = params.get('k_period', 14)
    d_period = params.get('d_period', 3)
    
    lowest_low = low.rolling(k_period).min()
    highest_high = high.rolling(k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d = k.rolling(d_period).mean()
    
    signals = []
    for i in range(k_period, len(df)):
        if k.iloc[i] < 20 and d.iloc[i] < 20 and k.iloc[i] > d.iloc[i]:
            entry = close.iloc[i]
            tp = close.iloc[i] * 1.03
            sl = close.iloc[i] * 0.97
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_adx_trend(df, params=None):
    """ADX Trend Strength"""
    params = params or {}
    close = df['close']
    high = df['high']
    low = df['low']
    period = params.get('period', 14)
    adx_thresh = params.get('adx_thresh', 25)
    
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where(plus_dm > 0, 0)
    minus_dm = minus_dm.where(minus_dm > 0, 0)
    
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(period).mean()
    
    signals = []
    for i in range(period * 2, len(df)):
        if adx.iloc[i] > adx_thresh and plus_di.iloc[i] > minus_di.iloc[i]:
            entry = close.iloc[i]
            tp = entry * 1.04
            sl = entry * 0.97
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_williams_r(df, params=None):
    """Williams %R Mean Reversion"""
    params = params or {}
    close = df['close']
    high = df['high']
    low = df['low']
    period = params.get('period', 14)
    
    highest_high = high.rolling(period).max()
    lowest_low = low.rolling(period).min()
    wr = -100 * (highest_high - close) / (highest_high - lowest_low)
    
    signals = []
    for i in range(period, len(df)):
        if wr.iloc[i] < -80 and wr.iloc[i-1] >= -80:
            entry = close.iloc[i]
            tp = close.iloc[i] * 1.03
            sl = close.iloc[i] * 0.97
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_cci_reversal(df, params=None):
    """CCI Reversal"""
    params = params or {}
    close = df['close']
    high = df['high']
    low = df['low']
    period = params.get('period', 20)
    
    tp = (high + low + close) / 3
    sma_tp = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean())
    cci = (tp - sma_tp) / (0.015 * mad)
    
    signals = []
    for i in range(period, len(df)):
        if cci.iloc[i] < -100 and cci.iloc[i-1] >= -100:
            entry = close.iloc[i]
            tp_price = close.iloc[i] * 1.03
            sl_price = close.iloc[i] * 0.97
            signals.append({'entry': entry, 'tp': tp_price, 'sl': sl_price, 'direction': 'LONG'})
    return signals

def strategy_momentum_continuation(df, params=None):
    """Momentum Continuation"""
    params = params or {}
    close = df['close']
    lookback = params.get('lookback', 10)
    threshold = params.get('threshold', 0.02)
    
    roc = close.pct_change(lookback)
    
    signals = []
    for i in range(lookback, len(df)):
        if roc.iloc[i] > threshold:
            entry = close.iloc[i]
            tp = entry * 1.05
            sl = entry * 0.96
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_volume_spike(df, params=None):
    """Volume Spike Reversal"""
    params = params or {}
    close = df['close']
    volume = df.get('volume', pd.Series([1]*len(close)))
    
    avg_vol = volume.rolling(20).mean()
    vol_ratio = volume / avg_vol
    
    signals = []
    for i in range(20, len(df)):
        if vol_ratio.iloc[i] > 2.0 and close.iloc[i] < close.iloc[i-1]:
            entry = close.iloc[i]
            tp = close.iloc[i] * 1.04
            sl = close.iloc[i] * 0.97
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_double_bottom(df, params=None):
    """Double Bottom Reversal"""
    params = params or {}
    close = df['close']
    
    signals = []
    for i in range(20, len(df)):
        # Look for double bottom pattern
        window = close.iloc[max(0,i-20):i]
        if len(window) >= 10:
            min_idx = window.idxmin()
            if min_idx < i - 5 and close.iloc[i] > close.iloc[min_idx]:
                entry = close.iloc[i]
                tp = entry * 1.04
                sl = entry * 0.97
                signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_gap_fill(df, params=None):
    """Gap Fill Strategy"""
    params = params or {}
    close = df['close']
    open_p = df['open']
    
    signals = []
    for i in range(1, len(df)):
        gap = (open_p.iloc[i] - close.iloc[i-1]) / close.iloc[i-1]
        if gap < -0.01:  # Down gap
            entry = close.iloc[i]
            tp = close.iloc[i-1]
            sl = open_p.iloc[i]
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_pivot_reversal(df, params=None):
    """Pivot Point Reversal"""
    params = params or {}
    close = df['close']
    high = df['high']
    low = df['low']
    
    # Simple pivot calculation
    pivot = (high.shift(1) + low.shift(1) + close.shift(1)) / 3
    
    signals = []
    for i in range(2, len(df)):
        if close.iloc[i] < pivot.iloc[i-1] and close.iloc[i-1] >= pivot.iloc[i-1]:
            entry = close.iloc[i]
            tp = pivot.iloc[i-1]
            sl = low.iloc[i]
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_ema_cross(df, params=None):
    """EMA Crossover"""
    params = params or {}
    close = df['close']
    fast = params.get('fast', 9)
    slow = params.get('slow', 21)
    
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    
    signals = []
    for i in range(slow, len(df)):
        if ema_fast.iloc[i] > ema_slow.iloc[i] and ema_fast.iloc[i-1] <= ema_slow.iloc[i-1]:
            entry = close.iloc[i]
            tp = entry * 1.05
            sl = ema_slow.iloc[i]
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_breakout(df, params=None):
    """Price Breakout"""
    params = params or {}
    close = df['close']
    lookback = params.get('lookback', 20)
    
    signals = []
    for i in range(lookback, len(df)):
        high_range = close.iloc[i-lookback:i].max()
        if close.iloc[i] > high_range:
            entry = close.iloc[i]
            tp = entry * 1.06
            sl = close.iloc[i] * 0.97
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_bollinger_breakout(df, params=None):
    """Bollinger Band Breakout"""
    params = params or {}
    close = df['close']
    bb_period = params.get('bb_period', 20)
    bb_std = params.get('bb_std', 2.0)
    
    sma = close.rolling(bb_period).mean()
    std = close.rolling(bb_period).std()
    upper = sma + bb_std * std
    
    signals = []
    for i in range(bb_period, len(df)):
        if close.iloc[i] > upper.iloc[i] and close.iloc[i-1] <= upper.iloc[i-1]:
            entry = close.iloc[i]
            tp = entry * 1.06
            sl = sma.iloc[i]
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_atr_reversal(df, params=None):
    """ATR-based Reversal"""
    params = params or {}
    close = df['close']
    high = df['high']
    low = df['low']
    period = params.get('period', 14)
    
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    
    signals = []
    for i in range(period, len(df)):
        if close.iloc[i] < close.iloc[i-1] - atr.iloc[i]:
            entry = close.iloc[i]
            tp = close.iloc[i] + atr.iloc[i]
            sl = close.iloc[i] - (atr.iloc[i] * 0.5)
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_fib_retracement(df, params=None):
    """Fibonacci Retracement"""
    params = params or {}
    close = df['close']
    lookback = params.get('lookback', 50)
    
    signals = []
    for i in range(lookback, len(df)):
        high_val = close.iloc[i-lookback:i].max()
        low_val = close.iloc[i-lookback:i].min()
        range_val = high_val - low_val
        
        # Check for 61.8% retracement
        retracement = high_val - (range_val * 0.618)
        if close.iloc[i] >= retracement and close.iloc[i-1] < retracement:
            entry = close.iloc[i]
            tp = high_val
            sl = low_val + (range_val * 0.382)
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

def strategy_ichi_cloud(df, params=None):
    """Ichimoku Cloud Signal"""
    params = params or {}
    close = df['close']
    high = df['high']
    low = df['low']
    
    # Ichimoku components
    nine_high = high.rolling(9).max()
    nine_low = low.rolling(9).min()
    tenkan = (nine_high + nine_low) / 2
    
    twenty_six_high = high.rolling(26).max()
    twenty_six_low = low.rolling(26).min()
    kijun = (twenty_six_high + twenty_six_low) / 2
    
    signals = []
    for i in range(26, len(df)):
        if close.iloc[i] > tenkan.iloc[i] and close.iloc[i] > kijun.iloc[i]:
            entry = close.iloc[i]
            tp = close.iloc[i] * 1.05
            sl = kijun.iloc[i]
            signals.append({'entry': entry, 'tp': tp, 'sl': sl, 'direction': 'LONG'})
    return signals

# Strategy registry
STRATEGIES = {
    'bollinger_mr': strategy_bollinger_mr,
    'rsi_reversal': strategy_rsi_reversal,
    'macd_crossover': strategy_macd_crossover,
    'supertend': strategy_supertend,
    'keltner_mr': strategy_keltner_mr,
    'vwap_reversion': strategy_vwap_reversion,
    'stochastic_mr': strategy_stochastic_mr,
    'adx_trend': strategy_adx_trend,
    'williams_r': strategy_williams_r,
    'cci_reversal': strategy_cci_reversal,
    'momentum_continuation': strategy_momentum_continuation,
    'volume_spike': strategy_volume_spike,
    'double_bottom': strategy_double_bottom,
    'gap_fill': strategy_gap_fill,
    'pivot_reversal': strategy_pivot_reversal,
    'ema_cross': strategy_ema_cross,
    'breakout': strategy_breakout,
    'bollinger_breakout': strategy_bollinger_breakout,
    'atr_reversal': strategy_atr_reversal,
    'fib_retracement': strategy_fib_retracement,
    'ichi_cloud': strategy_ichi_cloud,
}

def run_backtest(strategy_func, symbol: str, asset_class: str) -> Dict:
    """Run backtest on a single strategy-symbol pair"""
    df = get_klines(symbol, '15m', 500)
    if df is None or len(df) < 100:
        return None
    
    try:
        signals = strategy_func(df)
    except Exception as e:
        return None
    
    if not signals:
        return None
    
    # Simulate trades
    trades = []
    for sig in signals[:20]:  # Limit to 20 trades
        entry = sig['entry']
        tp = sig['tp']
        sl = sig['sl']
        
        # Check outcome (simplified - check if price reached TP or SL in next 20 bars)
        outcome = 'FLAT'
        pnl_pct = 0.0
        
        # Find bars after entry
        idx = df[df['close'] >= entry].index
        if len(idx) > 0:
            start_idx = df.index.get_loc(idx[0])
            future = df.iloc[start_idx:min(start_idx+20, len(df))]
            
            if len(future) > 0:
                high_max = future['high'].max()
                low_min = future['low'].min()
                
                if high_max >= tp:
                    outcome = 'WIN'
                    pnl_pct = (tp - entry) / entry * 100
                elif low_min <= sl:
                    outcome = 'LOSS'
                    pnl_pct = (sl - entry) / entry * 100
                else:
                    outcome = 'FLAT'
                    pnl_pct = 0.0
        
        trades.append({'outcome': outcome, 'pnl_pct': pnl_pct})
    
    if not trades:
        return None
    
    wins = sum(1 for t in trades if t['outcome'] == 'WIN')
    losses = sum(1 for t in trades if t['outcome'] == 'LOSS')
    total = len(trades)
    win_rate = wins / total if total > 0 else 0
    
    win_pnl = sum(t['pnl_pct'] for t in trades if t['outcome'] == 'WIN')
    loss_pnl = abs(sum(t['pnl_pct'] for t in trades if t['outcome'] == 'LOSS'))
    
    pf = win_pnl / loss_pnl if loss_pnl > 0 else 0
    total_pnl = sum(t['pnl_pct'] for t in trades)
    
    return {
        'strategy': strategy_func.__name__,
        'symbol': symbol,
        'asset_class': asset_class,
        'trades': total,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'profit_factor': pf,
        'total_pnl_pct': total_pnl
    }

def run_all_backtests():
    """Run backtests for all strategies across all asset classes"""
    results = []
    
    for asset_class, symbols in ASSET_SYMBOLS.items():
        print(f'\n=== {asset_class} ===')
        
        for strat_name, strat_func in STRATEGIES.items():
            for symbol in symbols[:3]:  # Test on first 3 symbols per asset class
                result = run_backtest(strat_func, symbol, asset_class)
                if result:
                    results.append(result)
                    
                    # Print live results
                    wr = result['win_rate'] * 100
                    pf = result['profit_factor']
                    pnl = result['total_pnl_pct']
                    status = 'PASS' if wr >= 45 and pf >= 1.2 and pnl > 0 else 'FAIL'
                    print(f"  {strat_name:20s} {symbol:12s} n={result['trades']:2d} WR={wr:5.1f}% PF={pf:5.2f} PnL={pnl:>6.1f}% [{status}]")
    
    return results

def save_results(results: List[Dict], output_file: str = 'tmp_expansion_results.json'):
    """Save results to JSON"""
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f'\nResults saved to {output_file}')

def summarize_results(results: List[Dict]):
    """Summarize results by strategy"""
    by_strategy = {}
    for r in results:
        strat = r['strategy']
        if strat not in by_strategy:
            by_strategy[strat] = {'trades': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0, 'symbols': set()}
        
        by_strategy[strat]['trades'] += r['trades']
        by_strategy[strat]['wins'] += r['wins']
        by_strategy[strat]['losses'] += r['losses']
        by_strategy[strat]['total_pnl'] += r['total_pnl_pct']
        by_strategy[strat]['symbols'].add(r['symbol'])
    
    print('\n=== STRATEGY SUMMARY (Quality Gates: WR>=45%, PF>=1.2, PnL>0) ===')
    
    summary = []
    for strat, data in by_strategy.items():
        total = data['trades']
        if total < 3:
            continue
        wr = data['wins'] / total * 100 if total > 0 else 0
        win_pnl = sum(r['total_pnl_pct'] for r in results if r['strategy'] == strat and r['total_pnl_pct'] > 0)
        loss_pnl = abs(sum(r['total_pnl_pct'] for r in results if r['strategy'] == strat and r['total_pnl_pct'] < 0))
        pf = win_pnl / loss_pnl if loss_pnl > 0 else 0
        pnl = data['total_pnl']
        
        passed = wr >= 45 and pf >= 1.2 and pnl > 0
        status = 'PASS' if passed else 'FAIL'
        
        summary.append({
            'strategy': strat,
            'trades': total,
            'wr': wr,
            'pf': pf,
            'pnl': pnl,
            'status': status
        })
    
    # Sort by PnL
    summary.sort(key=lambda x: x['pnl'], reverse=True)
    
    for s in summary:
        print(f"  {s['strategy']:30s} n={s['trades']:3d} WR={s['wr']:5.1f}% PF={s['pf']:5.2f} PnL={s['pnl']:>7.1f}% [{s['status']}]")
    
    passed = sum(1 for s in summary if s['status'] == 'PASS')
    print(f'\nTotal: {len(summary)} strategies tested, {passed} passed quality gates')

if __name__ == '__main__':
    print('=== MULTI-ASSET STRATEGY EXPANSION BUNDLE ===')
    print('Quality Gates: WR>=45%, PF>=1.2, PnL>0, min 3 trades\n')
    
    results = run_all_backtests()
    summarize_results(results)
    save_results(results)