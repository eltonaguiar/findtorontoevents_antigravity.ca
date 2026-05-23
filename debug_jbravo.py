"""
Debug J Bravo Strategies
=======================

Debug version to see why no signals are generated.
"""

import requests
from typing import List, Dict, Any

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

def debug_bos(data: List[Dict], symbol: str) -> None:
    """Debug BOS signal generation."""
    print(f"\n=== DEBUG BOS for {symbol} ===")

    if len(data) < 50:
        print("Not enough data")
        return

    closes = [d['close'] for d in data]
    highs = [d['high'] for d in data]
    lows = [d['low'] for d in data]
    volumes = [d['volume'] for d in data]

    atr_values = atr(highs, lows, closes, 14)
    idx = len(closes) - 1

    print(f"Data length: {len(data)}")
    print(f"Current price: {closes[idx]:.4f}")
    print(f"Current ATR: {atr_values[idx]:.4f}")

    # Find swing points
    swing_highs = []
    swing_lows = []

    window = 3
    for i in range(window, len(highs) - window):
        # Swing high
        is_high = all(highs[i] >= highs[i-j] for j in range(1, window+1)) and \
                  all(highs[i] >= highs[i+j] for j in range(1, window+1))
        if is_high:
            swing_highs.append((i, highs[i]))

        # Swing low
        is_low = all(lows[i] <= lows[i-j] for j in range(1, window+1)) and \
                 all(lows[i] <= lows[i+j] for j in range(1, window+1))
        if is_low:
            swing_lows.append((i, lows[i]))

    print(f"Swing highs found: {len(swing_highs)}")
    print(f"Swing lows found: {len(swing_lows)}")

    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        recent_highs = [sh[1] for sh in swing_highs[-3:]]
        recent_lows = [sl[1] for sl in swing_lows[-3:]]

        prev_hh = max(recent_highs[:-1]) if len(recent_highs) > 1 else max(recent_highs)
        prev_ll = min(recent_lows[:-1]) if len(recent_lows) > 1 else min(recent_lows)

        print(f"Previous HH: {prev_hh:.4f}")
        print(f"Previous LL: {prev_ll:.4f}")

        # Volume check
        vol_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        vol_ratio = volumes[idx] / vol_avg
        print(f"Volume ratio: {vol_ratio:.2f} (need > 1.05)")

        vol_confirm = vol_ratio > 1.05
        print(f"Volume confirmed: {vol_confirm}")

        # Breakout checks
        breakout_pct = 0.0005
        bullish_breakout = closes[idx] > prev_hh * (1 + breakout_pct)
        bearish_breakout = closes[idx] < prev_ll * (1 - breakout_pct)

        print(f"Bullish breakout check: {closes[idx]:.4f} > {prev_hh * (1 + breakout_pct):.4f} = {bullish_breakout}")
        print(f"Bearish breakout check: {closes[idx]:.4f} < {prev_ll * (1 - breakout_pct):.4f} = {bearish_breakout}")

def debug_fvg(data: List[Dict], symbol: str) -> None:
    """Debug FVG signal generation."""
    print(f"\n=== DEBUG FVG for {symbol} ===")

    if len(data) < 30:
        print("Not enough data")
        return

    closes = [d['close'] for d in data]
    highs = [d['high'] for d in data]
    lows = [d['low'] for d in data]
    volumes = [d['volume'] for d in data]

    atr_values = atr(highs, lows, closes, 14)
    idx = len(closes) - 1

    print(f"Data length: {len(data)}")
    print(f"Current price: {closes[idx]:.4f}")
    print(f"Current ATR: {atr_values[idx]:.4f}")

    # Detect FVGs
    fvgs = []
    for i in range(max(0, idx-15), idx):
        if i > 0:
            # Bullish FVG
            if lows[i] > highs[i-1]:
                gap_size = lows[i] - highs[i-1]
                atr_threshold = atr_values[i] * 0.2
                if gap_size > atr_threshold:
                    fvgs.append({
                        'type': 'bullish',
                        'top': lows[i],
                        'bottom': highs[i-1],
                        'mid': (lows[i] + highs[i-1]) / 2,
                        'size': gap_size,
                        'atr_threshold': atr_threshold
                    })

            # Bearish FVG
            if highs[i] < lows[i-1]:
                gap_size = lows[i-1] - highs[i]
                atr_threshold = atr_values[i] * 0.2
                if gap_size > atr_threshold:
                    fvgs.append({
                        'type': 'bearish',
                        'top': lows[i-1],
                        'bottom': highs[i],
                        'mid': (lows[i-1] + highs[i]) / 2,
                        'size': gap_size,
                        'atr_threshold': atr_threshold
                    })

    print(f"FVGs found: {len(fvgs)}")
    for fvg in fvgs[-3:]:  # Show last 3
        print(f"  {fvg['type']} FVG: mid={fvg['mid']:.4f}, size={fvg['size']:.4f}, atr_thresh={fvg['atr_threshold']:.4f}")

    # Volume check
    vol_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
    vol_ratio = volumes[idx] / vol_avg
    print(f"Volume ratio: {vol_ratio:.2f} (need > 1.02)")

    vol_confirm = vol_ratio > 1.02
    print(f"Volume confirmed: {vol_confirm}")

    # Check proximity to FVGs
    price = closes[idx]
    for fvg in fvgs[-5:]:
        mid_price = fvg['mid']
        distance_pct = abs(price - mid_price) / mid_price
        near_fvg = distance_pct < 0.005
        print(f"  Distance to {fvg['type']} FVG: {distance_pct:.4f}% (near: {near_fvg})")

def main():
    # Test on BTC
    symbol = 'BTCUSDT'

    print("Fetching data...")
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=200"
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

        print(f"Fetched {len(ohlcv_data)} bars")

        debug_bos(ohlcv_data, symbol)
        debug_fvg(ohlcv_data, symbol)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()