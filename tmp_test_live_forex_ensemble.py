#!/usr/bin/env python3
"""Live market test for forex_ensemble_4h_rehab strategy"""

import sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# Import the strategy
from baby_strategies.forex_ensemble_4h_rehab import ForexEnsemble4hRehabStrategy


def get_klines(symbol, interval='15m', limit=100):
    """Fetch live klines from Binance"""
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote', 'trades', 'taker_base', 'taker_quote', 'ignore'
        ])
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        return df[['open', 'high', 'low', 'close']]
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None


def get_live_price(symbol):
    """Get current price from Binance"""
    url = f'https://api.binance.com/api/v3/ticker/price?symbol={symbol}'
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        return float(data['price'])
    except:
        return None


# FOREX pairs to test
FOREX_PAIRS = ["EURUSDT", "GBPUSDT", "AUDUSDT", "USDCAD"]

print("=" * 70)
print(f"LIVE MARKET TEST: forex_ensemble_4h_rehab")
print(f"Time: {datetime.utcnow().isoformat()} UTC")
print("=" * 70)

strategy = ForexEnsemble4hRehabStrategy()

signals_found = []

for symbol in FOREX_PAIRS:
    print(f"\n### Testing {symbol} ###")
    
    # Get latest 100 candles for signal generation
    df = get_klines(symbol, '15m', 100)
    if df is None or len(df) < 50:
        print(f"  Insufficient data")
        continue
    
    # Get live price
    live_price = get_live_price(symbol)
    current_price = float(df['close'].iloc[-1])
    
    print(f"  Current price: {current_price:.8f}")
    if live_price:
        print(f"  Live price:    {live_price:.8f}")
    
    # Generate signals using the strategy
    signals = strategy.generate_signals(df, symbol)
    
    if signals:
        for sig in signals:
            print(f"  SIGNAL: {sig.direction} @ {sig.entry_price}")
            print(f"    TP: {sig.take_profit} | SL: {sig.stop_loss}")
            print(f"    Confidence: {sig.confidence}")
            print(f"    Reason: {sig.reason}")
            signals_found.append({
                'symbol': symbol,
                'signal': sig
            })
    else:
        # Show current market conditions for debugging
        close = df['close']
        sma20 = close.rolling(20).mean()
        sma50 = close.rolling(50).mean()
        
        high = df['high']
        low = df['low']
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        current_sma20 = float(sma20.iloc[-1])
        current_sma50 = float(sma50.iloc[-1])
        prev_sma20 = float(sma20.iloc[-2])
        prev_sma50 = float(sma50.iloc[-2])
        current_atr = float(atr.iloc[-1])
        atr_pct = (current_atr / current_price) * 100
        
        print(f"  No signal triggered")
        print(f"    SMA20: {current_sma20:.8f} | SMA50: {current_sma50:.8f}")
        print(f"    Trend: {'UP' if current_sma20 > current_sma50 else 'DOWN'}")
        print(f"    Cross: {'UP' if prev_sma20 <= prev_sma50 and current_sma20 > current_sma50 else 'DOWN' if prev_sma20 >= prev_sma50 and current_sma20 < current_sma50 else 'NONE'}")
        print(f"    ATR%: {atr_pct:.2f}% (threshold: <1.0%)")
        print(f"    Compression: {'YES' if atr_pct < 1.0 else 'NO'}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

if signals_found:
    print(f"Total signals: {len(signals_found)}")
    for s in signals_found:
        print(f"  - {s['symbol']}: {s['signal'].direction} @ {s['signal'].entry_price} (conf: {s['signal'].confidence})")
else:
    print("No live signals triggered.")
    print("The 4h ensemble strategy requires:")
    print("  1. SMA crossover (20 crossing 50)")
    print("  2. Low volatility (ATR% < 1.0%)")
    print("  Current market conditions may not meet both criteria.")

print("=" * 70)