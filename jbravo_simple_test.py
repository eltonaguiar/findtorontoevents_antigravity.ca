"""
Simplified J Bravo Smart Money Strategies Test
==============================================

Tests the core logic of J Bravo strategies without pandas dependency.
"""

import requests
import math
from typing import List, Dict, Any
from datetime import datetime
import json

# Signal class (simplified)
class Signal:
    def __init__(self, symbol: str, direction: str, confidence: float,
                 entry_price: float, take_profit: float, stop_loss: float, reason: str):
        self.symbol = symbol
        self.direction = direction
        self.confidence = confidence
        self.entry_price = entry_price
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.reason = reason

# Simplified indicator calculations
def ema(values: List[float], period: int) -> List[float]:
    """Calculate EMA."""
    if len(values) < period:
        return [0.0] * len(values)

    ema_values: List[float] = [0.0] * len(values)
    multiplier = 2 / (period + 1)

    # First EMA is SMA
    ema_values[period-1] = sum(values[:period]) / period

    for i in range(period, len(values)):
        ema_values[i] = (values[i] * multiplier) + (ema_values[i-1] * (1 - multiplier))

    return ema_values

def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
    """Calculate ATR."""
    if len(highs) < period + 1:
        return [0.0] * len(highs)

    atr_values: List[float] = [0.0] * len(highs)
    tr_values = []

    for i in range(1, len(highs)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr_values.append(tr)

    # First ATR is average of first TR values
    atr_values[period] = sum(tr_values[:period]) / period

    for i in range(period + 1, len(highs)):
        atr_values[i] = (atr_values[i-1] * (period - 1) + tr_values[i-1]) / period

    return atr_values

# J Bravo Strategy Implementations (Simplified)
def smart_money_bos_signals(data: List[Dict], symbol: str) -> List[Signal]:
    """Smart Money Break of Structure - simplified version."""
    if len(data) < 100:
        return []

    closes = [d['close'] for d in data]
    highs = [d['high'] for d in data]
    lows = [d['low'] for d in data]
    volumes = [d['volume'] for d in data]

    atr_values = atr(highs, lows, closes, 14)
    idx = len(closes) - 1

    if idx < 50 or atr_values[idx] == 0:
        return []

    price = closes[idx]
    atr_now = atr_values[idx]

    # Find swing points (simplified)
    swing_highs = []
    swing_lows = []

    for i in range(5, len(highs) - 5):
        # Check if this is a swing high
        is_high = True
        for j in range(1, 6):
            if highs[i] <= highs[i-j] or highs[i] <= highs[i+j]:
                is_high = False
                break
        if is_high:
            swing_highs.append((i, highs[i]))

        # Check if this is a swing low
        is_low = True
        for j in range(1, 6):
            if lows[i] >= lows[i-j] or lows[i] >= lows[i+j]:
                is_low = False
                break
        if is_low:
            swing_lows.append((i, lows[i]))

    if not swing_highs or not swing_lows:
        return []

    # Get recent swing levels
    recent_highs = [sh[1] for sh in swing_highs[-5:]]
    recent_lows = [sl[1] for sl in swing_lows[-5:]]

    prev_hh = max(recent_highs[:-1]) if len(recent_highs) > 1 else max(recent_highs)
    prev_ll = min(recent_lows[:-1]) if len(recent_lows) > 1 else min(recent_lows)

    # Volume confirmation
    vol_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
    vol_confirm = volumes[idx] > vol_avg * 1.2

    signals = []

    # BULLISH BOS
    if price > prev_hh * 1.001 and vol_confirm:
        conf = 0.75
        tp = price + 3.0 * atr_now
        sl = prev_hh
        signals.append(Signal(
            symbol=symbol, direction="BUY",
            confidence=conf, entry_price=price,
            take_profit=tp, stop_loss=sl,
            reason=f"SMART_MONEY_BOS BUY | Break>{prev_hh:.4f} VolConfirm ATR={atr_now:.2f}"
        ))

    # BEARISH BOS
    if price < prev_ll * 0.999 and vol_confirm:
        conf = 0.75
        tp = price - 3.0 * atr_now
        sl = prev_ll
        signals.append(Signal(
            symbol=symbol, direction="SELL",
            confidence=conf, entry_price=price,
            take_profit=tp, stop_loss=sl,
            reason=f"SMART_MONEY_BOS SELL | Break<{prev_ll:.4f} VolConfirm ATR={atr_now:.2f}"
        ))

    return signals

def fair_value_gap_signals(data: List[Dict], symbol: str) -> List[Signal]:
    """Fair Value Gap detection - simplified version."""
    if len(data) < 50:
        return []

    closes = [d['close'] for d in data]
    highs = [d['high'] for d in data]
    lows = [d['low'] for d in data]
    volumes = [d['volume'] for d in data]

    atr_values = atr(highs, lows, closes, 14)
    idx = len(closes) - 1

    if atr_values[idx] == 0:
        return []

    price = closes[idx]
    atr_now = atr_values[idx]

    # Detect FVGs in recent bars
    fvgs = []
    for i in range(max(0, idx-20), idx):
        # Bullish FVG: current low > previous high
        if i > 0 and lows[i] > highs[i-1]:
            gap_size = lows[i] - highs[i-1]
            if gap_size > atr_values[i] * 0.5:
                fvgs.append({
                    'type': 'bullish',
                    'top': lows[i],
                    'bottom': highs[i-1],
                    'mid': (lows[i] + highs[i-1]) / 2
                })

        # Bearish FVG: current high < previous low
        if i > 0 and highs[i] < lows[i-1]:
            gap_size = lows[i-1] - highs[i]
            if gap_size > atr_values[i] * 0.5:
                fvgs.append({
                    'type': 'bearish',
                    'top': lows[i-1],
                    'bottom': highs[i],
                    'mid': (lows[i-1] + highs[i]) / 2
                })

    # Volume confirmation
    vol_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
    vol_confirm = volumes[idx] > vol_avg * 1.1

    signals = []

    # Check if price is near any recent FVG
    for fvg in fvgs[-3:]:
        mid_price = fvg['mid']
        gap_size = fvg['top'] - fvg['bottom']

        # Price near FVG midpoint
        near_fvg = abs(price - mid_price) / mid_price < 0.002

        if near_fvg and vol_confirm:
            if fvg['type'] == 'bullish':
                conf = 0.70
                tp = fvg['bottom'] - gap_size * 0.5
                sl = fvg['top'] + atr_now * 0.5
                if tp < price:
                    signals.append(Signal(
                        symbol=symbol, direction="SELL",
                        confidence=conf, entry_price=price,
                        take_profit=tp, stop_loss=sl,
                        reason=f"FVG SELL | BullishFVG Mid@{mid_price:.4f} Gap={gap_size:.4f}"
                    ))

            elif fvg['type'] == 'bearish':
                conf = 0.70
                tp = fvg['top'] + gap_size * 0.5
                sl = fvg['bottom'] - atr_now * 0.5
                if tp > price:
                    signals.append(Signal(
                        symbol=symbol, direction="BUY",
                        confidence=conf, entry_price=price,
                        take_profit=tp, stop_loss=sl,
                        reason=f"FVG BUY | BearishFVG Mid@{mid_price:.4f} Gap={gap_size:.4f}"
                    ))

    return signals

# Test functions
CRYPTO_PAIRS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']

def fetch_data(symbol: str) -> List[Dict]:
    """Fetch data from Binance."""
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=500"
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

def calculate_metrics(signals: List[Signal]) -> Dict:
    """Calculate performance metrics."""
    if not signals:
        return {'return': 0, 'win_rate': 0, 'trades': 0}

    balance = 10000
    wins = 0

    for signal in signals:
        entry = signal.entry_price
        exit_price = signal.take_profit if signal.direction == 'BUY' else signal.stop_loss
        position_size = balance * 0.02

        if signal.direction == 'BUY':
            pnl = (exit_price - entry) / entry * position_size
        else:
            pnl = (entry - exit_price) / entry * position_size

        balance += pnl
        if pnl > 0:
            wins += 1

    total_return = (balance - 10000) / 10000 * 100
    win_rate = wins / len(signals) * 100 if signals else 0

    return {
        'return': total_return,
        'win_rate': win_rate,
        'trades': len(signals)
    }

def main():
    print("J BRAVO SMART MONEY STRATEGIES TEST")
    print("=" * 50)

    strategies = {
        'BOS': smart_money_bos_signals,
        'FVG': fair_value_gap_signals
    }

    all_results = []

    for strategy_name, strategy_func in strategies.items():
        print(f"\nTesting {strategy_name} Strategy:")
        print("-" * 30)

        for symbol in CRYPTO_PAIRS:
            data = fetch_data(symbol)
            if not data:
                print(f"{symbol}: No data")
                continue

            signals = strategy_func(data, symbol)
            metrics = calculate_metrics(signals)

            print(f"{symbol:8} | Return: {metrics['return']:6.2f}% | "
                  f"Win%: {metrics['win_rate']:5.1f}% | Trades: {metrics['trades']:2d}")

            all_results.append({
                'strategy': strategy_name,
                'symbol': symbol,
                **metrics
            })

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    for strategy_name in strategies.keys():
        strategy_results = [r for r in all_results if r['strategy'] == strategy_name]
        if strategy_results:
            avg_return = sum(r['return'] for r in strategy_results) / len(strategy_results)
            avg_win_rate = sum(r['win_rate'] for r in strategy_results) / len(strategy_results)
            total_trades = sum(r['trades'] for r in strategy_results)

            best = max(strategy_results, key=lambda x: x['return'])

            print(f"\n{strategy_name}:")
            print(f"  Average Return: {avg_return:.2f}%")
            print(f"  Average Win Rate: {avg_win_rate:.1f}%")
            print(f"  Total Trades: {total_trades}")
            print(f"  Best Pair: {best['symbol']} ({best['return']:.2f}%)")

if __name__ == "__main__":
    main()