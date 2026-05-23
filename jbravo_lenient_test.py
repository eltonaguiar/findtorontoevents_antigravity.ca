"""
J Bravo Smart Money Strategies - Lenient Version
===============================================

More lenient parameters to generate actual signals for testing.
"""

import requests
import math
from typing import List, Dict, Any
from datetime import datetime
import json

# Signal class
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

def smart_money_bos_lenient(data: List[Dict], symbol: str) -> List[Signal]:
    """Smart Money BOS - lenient version for testing."""
    if len(data) < 30:
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

    # Find swing points
    swing_highs = []
    swing_lows = []

    window = 2  # Even smaller window
    for i in range(window, len(highs) - window):
        # Swing high
        if all(highs[i] >= highs[i-j] for j in range(1, window+1)) and \
           all(highs[i] >= highs[i+j] for j in range(1, window+1)):
            swing_highs.append((i, highs[i]))

        # Swing low
        if all(lows[i] <= lows[i-j] for j in range(1, window+1)) and \
           all(lows[i] <= lows[i+j] for j in range(1, window+1)):
            swing_lows.append((i, lows[i]))

    if len(swing_highs) < 1 or len(swing_lows) < 1:
        return []

    # Use most recent swing levels
    recent_highs = [sh[1] for sh in swing_highs[-2:]]
    recent_lows = [sl[1] for sl in swing_lows[-2:]]

    prev_hh = max(recent_highs)
    prev_ll = min(recent_lows)

    # Much more lenient volume confirmation or no volume requirement
    vol_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
    vol_confirm = volumes[idx] > vol_avg * 0.8  # Much more lenient

    signals = []

    # BULLISH BOS
    breakout_pct = 0.001  # 0.1% breakout (more reasonable)
    if price > prev_hh * (1 + breakout_pct):
        conf = 0.65
        risk_multiple = 1.0  # More conservative
        tp = price + risk_multiple * atr_now
        sl = prev_hh

        if tp > price and sl < price:
            signals.append(Signal(
                symbol=symbol, direction="BUY",
                confidence=conf, entry_price=price,
                take_profit=tp, stop_loss=sl,
                reason=f"BOS BUY | Break>{prev_hh:.4f} ATR={atr_now:.2f}"
            ))

    # BEARISH BOS
    if price < prev_ll * (1 - breakout_pct):
        conf = 0.65
        risk_multiple = 1.0
        tp = price - risk_multiple * atr_now
        sl = prev_ll

        if tp < price and sl > price:
            signals.append(Signal(
                symbol=symbol, direction="SELL",
                confidence=conf, entry_price=price,
                take_profit=tp, stop_loss=sl,
                reason=f"BOS SELL | Break<{prev_ll:.4f} ATR={atr_now:.2f}"
            ))

    return signals

def fair_value_gap_lenient(data: List[Dict], symbol: str) -> List[Signal]:
    """Fair Value Gap - lenient version for testing."""
    if len(data) < 20:
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

    # Detect FVGs with very lenient conditions
    fvgs = []
    lookback = 10  # Look at last 10 bars only
    for i in range(max(0, idx-lookback), idx):
        if i > 0:
            # Bullish FVG - any gap up
            if lows[i] > highs[i-1]:
                gap_size = lows[i] - highs[i-1]
                # Very lenient - any gap larger than a tiny amount
                if gap_size > atr_values[i] * 0.05:  # Much smaller threshold
                    fvgs.append({
                        'type': 'bullish',
                        'top': lows[i],
                        'bottom': highs[i-1],
                        'mid': (lows[i] + highs[i-1]) / 2,
                        'size': gap_size
                    })

            # Bearish FVG - any gap down
            if highs[i] < lows[i-1]:
                gap_size = lows[i-1] - highs[i]
                if gap_size > atr_values[i] * 0.05:
                    fvgs.append({
                        'type': 'bearish',
                        'top': lows[i-1],
                        'bottom': highs[i],
                        'mid': (lows[i-1] + highs[i]) / 2,
                        'size': gap_size
                    })

    signals = []

    # Check if price is near any FVG (very wide range)
    for fvg in fvgs[-3:]:
        mid_price = fvg['mid']
        gap_size = fvg['size']

        # Very wide proximity tolerance
        near_fvg = abs(price - mid_price) / mid_price < 0.01  # 1% tolerance

        if near_fvg:
            if fvg['type'] == 'bullish':
                conf = 0.60
                tp = fvg['bottom'] - gap_size * 0.2
                sl = fvg['top'] + atr_now * 0.5
                if tp < price:
                    signals.append(Signal(
                        symbol=symbol, direction="SELL",
                        confidence=conf, entry_price=price,
                        take_profit=tp, stop_loss=sl,
                        reason=f"FVG SELL | Bullish Mid@{mid_price:.4f} Gap={gap_size:.4f}"
                    ))

            elif fvg['type'] == 'bearish':
                conf = 0.60
                tp = fvg['top'] + gap_size * 0.2
                sl = fvg['bottom'] - atr_now * 0.5
                if tp > price:
                    signals.append(Signal(
                        symbol=symbol, direction="BUY",
                        confidence=conf, entry_price=price,
                        take_profit=tp, stop_loss=sl,
                        reason=f"FVG BUY | Bearish Mid@{mid_price:.4f} Gap={gap_size:.4f}"
                    ))

    return signals

# Test functions
CRYPTO_PAIRS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']

def fetch_data(symbol: str) -> List[Dict]:
    """Fetch data from Binance."""
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
        return ohlcv_data
    except:
        return []

def calculate_metrics(signals: List[Signal]) -> Dict:
    """Calculate performance metrics."""
    if not signals:
        return {'return': 0, 'win_rate': 0, 'trades': 0, 'avg_rr': 0}

    balance = 10000
    wins = 0
    total_rr = 0

    for signal in signals:
        entry = signal.entry_price
        exit_price = signal.take_profit if signal.direction == 'BUY' else signal.stop_loss
        position_size = balance * 0.02

        if signal.direction == 'BUY':
            pnl = (exit_price - entry) / entry * position_size
            risk = (entry - signal.stop_loss) / entry * position_size
        else:
            pnl = (entry - exit_price) / entry * position_size
            risk = (signal.stop_loss - entry) / entry * position_size

        rr_ratio = pnl / risk if risk > 0 else 0
        total_rr += rr_ratio

        balance += pnl
        if pnl > 0:
            wins += 1

    total_return = (balance - 10000) / 10000 * 100
    win_rate = wins / len(signals) * 100 if signals else 0
    avg_rr = total_rr / len(signals) if signals else 0

    return {
        'return': total_return,
        'win_rate': win_rate,
        'trades': len(signals),
        'avg_rr': avg_rr
    }

def main():
    print("J BRAVO SMART MONEY STRATEGIES - LENIENT TEST")
    print("=" * 60)

    strategies = {
        'BOS Lenient': smart_money_bos_lenient,
        'FVG Lenient': fair_value_gap_lenient
    }

    all_results = []

    for strategy_name, strategy_func in strategies.items():
        print(f"\nTesting {strategy_name}:")
        print("-" * 40)

        for symbol in CRYPTO_PAIRS:
            data = fetch_data(symbol)
            if not data:
                print(f"{symbol}: No data")
                continue

            signals = strategy_func(data, symbol)
            metrics = calculate_metrics(signals)

            print(f"{symbol:8} | Return: {metrics['return']:6.2f}% | "
                  f"Win%: {metrics['win_rate']:5.1f}% | Trades: {metrics['trades']:2d} | "
                  f"Avg R:R: {metrics['avg_rr']:4.2f}")

            all_results.append({
                'strategy': strategy_name,
                'symbol': symbol,
                **metrics
            })

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY - LENIENT STRATEGIES")
    print("=" * 60)

    for strategy_name in strategies.keys():
        strategy_results = [r for r in all_results if r['strategy'] == strategy_name]
        if strategy_results:
            valid_results = [r for r in strategy_results if r['trades'] > 0]

            if valid_results:
                avg_return = sum(r['return'] for r in valid_results) / len(valid_results)
                avg_win_rate = sum(r['win_rate'] for r in valid_results) / len(valid_results)
                total_trades = sum(r['trades'] for r in strategy_results)

                best = max(valid_results, key=lambda x: x['return'])

                print(f"\n{strategy_name}:")
                print(f"  Average Return: {avg_return:.2f}%")
                print(f"  Average Win Rate: {avg_win_rate:.1f}%")
                print(f"  Total Trades: {total_trades}")
                print(f"  Pairs with Signals: {len(valid_results)}/{len(CRYPTO_PAIRS)}")
                print(f"  Best Pair: {best['symbol']} ({best['return']:.2f}%, {best['trades']} trades)")
            else:
                print(f"\n{strategy_name}: No signals generated")

if __name__ == "__main__":
    main()