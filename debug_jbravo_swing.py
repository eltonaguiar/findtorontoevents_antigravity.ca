"""
J Bravo Debug - Check what's happening with swing detection
"""

import requests
import math
from typing import List, Dict, Any
from datetime import datetime
import json

def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
    """Calculate ATR."""
    if len(highs) < period + 1:
        return [0.0] * len(highs)

    atr_values: List[float] = [0.0] * len(highs)
    tr_values = []

    for i in range(1, len(highs)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr_values.append(tr)

    if len(tr_values) >= period:
        atr_values[period] = sum(tr_values[:period]) / period

        for i in range(period + 1, len(highs)):
            atr_values[i] = (atr_values[i-1] * (period - 1) + tr_values[i-1]) / period

    return atr_values

def debug_swing_detection(data: List[Dict], symbol: str):
    """Debug swing detection."""
    if len(data) < 50:
        print(f"{symbol}: Not enough data ({len(data)} bars)")
        return

    closes = [d['close'] for d in data]
    highs = [d['high'] for d in data]
    lows = [d['low'] for d in data]
    volumes = [d['volume'] for d in data]

    atr_values = atr(highs, lows, closes, 14)
    idx = len(closes) - 1

    price = closes[idx]
    atr_now = atr_values[idx]

    print(f"\n{symbol} DEBUG:")
    print(f"  Current Price: {price:.4f}")
    print(f"  ATR: {atr_now:.4f}")
    print(f"  ATR %: {(atr_now/price*100):.2f}%")

    # Find swing points
    swing_highs = []
    swing_lows = []

    window = 5
    for i in range(window, len(highs) - window):
        # Swing high
        if highs[i] == max(highs[i-window:i+window+1]):
            swing_highs.append((i, highs[i]))

        # Swing low
        if lows[i] == min(lows[i-window:i+window+1]):
            swing_lows.append((i, lows[i]))

    print(f"  Swing Highs found: {len(swing_highs)}")
    print(f"  Swing Lows found: {len(swing_lows)}")

    if swing_highs:
        recent_highs = sorted([sh[1] for sh in swing_highs[-3:]], reverse=True)
        print(f"  Recent Highs: {[f'{h:.4f}' for h in recent_highs]}")
        if recent_highs:
            prev_hh = recent_highs[0]
            breakout_buffer = atr_now * 0.1
            print(f"  Prev HH: {prev_hh:.4f}")
            print(f"  Breakout Level: {prev_hh + breakout_buffer:.4f}")
            print(f"  Price > Breakout: {price > prev_hh + breakout_buffer}")

    if swing_lows:
        recent_lows = sorted([sl[1] for sl in swing_lows[-3:]])
        print(f"  Recent Lows: {[f'{l:.4f}' for l in recent_lows]}")
        if recent_lows:
            prev_ll = recent_lows[0]
            breakout_buffer = atr_now * 0.1
            print(f"  Prev LL: {prev_ll:.4f}")
            print(f"  Breakout Level: {prev_ll - breakout_buffer:.4f}")
            print(f"  Price < Breakout: {price < prev_ll - breakout_buffer}")

    # Volume check
    vol_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
    vol_confirm = volumes[idx] > vol_avg * 0.7
    print(f"  Current Volume: {volumes[idx]:.0f}")
    print(f"  Avg Volume: {vol_avg:.0f}")
    print(f"  Volume Confirm: {vol_confirm}")

def fetch_data(symbol: str, interval: str = '1h') -> List[Dict]:
    """Fetch data from Binance."""
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=200"
        response = requests.get(url, timeout=10)
        data = response.json()

        ohlcv_data = []
        for row in data:
            ohlcv_data.append({
                'timestamp': int(row[0]),
                'open': float(row[1]),
                'high': float(row[2]),
                'low': float(row[3]),
                'close': float(row[4]),
                'volume': float(row[5])
            })
        return ohlcv_data
    except:
        return []

def main():
    print("J BRAVO DEBUG - SWING DETECTION ANALYSIS")
    print("=" * 50)

    CRYPTO_PAIRS = ['BTCUSDT', 'ETHUSDT']

    for symbol in CRYPTO_PAIRS:
        data = fetch_data(symbol)
        if data:
            debug_swing_detection(data, symbol)
        else:
            print(f"{symbol}: Failed to fetch data")

if __name__ == "__main__":
    main()