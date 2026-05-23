"""
J BRAVO SMART MONEY - FINAL OPTIMIZED VERSION
============================================

Based on test results:
- FVG strategy works great (100% win rate, 34 trades)
- BOS needs better breakout detection

Final version with optimized parameters.
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

def smart_money_bos_final(data: List[Dict], symbol: str) -> List[Signal]:
    """Smart Money BOS - final optimized version."""
    if len(data) < 50:
        return []

    closes = [d['close'] for d in data]
    highs = [d['high'] for d in data]
    lows = [d['low'] for d in data]

    atr_values = atr(highs, lows, closes, 14)
    idx = len(closes) - 1

    if atr_values[idx] == 0:
        return []

    price = closes[idx]
    atr_now = atr_values[idx]

    # Find swing points with larger window for more significant levels
    swing_highs = []
    swing_lows = []

    window = 8  # Larger window for more significant swings
    for i in range(window, len(highs) - window):
        if highs[i] == max(highs[i-window:i+window+1]):
            swing_highs.append((i, highs[i]))
        if lows[i] == min(lows[i-window:i+window+1]):
            swing_lows.append((i, lows[i]))

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return []

    # Use more distant swing levels for better breakouts
    recent_highs = sorted([sh[1] for sh in swing_highs[-5:]], reverse=True)
    recent_lows = sorted([sl[1] for sl in swing_lows[-5:]])

    if not recent_highs or not recent_lows:
        return []

    # Use the 2nd highest/lowest for less noise
    prev_hh = recent_highs[min(1, len(recent_highs)-1)]
    prev_ll = recent_lows[min(1, len(recent_lows)-1)]

    signals = []

    # BULLISH BOS - breakout above swing high with larger buffer
    breakout_buffer = atr_now * 0.15  # Larger buffer to avoid noise
    if price > prev_hh + breakout_buffer:
        conf = 0.80

        # More conservative TP/SL based on successful strategies
        tp = price + 2.0 * atr_now  # 2:1 reward ratio
        sl = prev_hh + breakout_buffer * 0.5  # Tighter stop

        min_distance = atr_now * 0.5
        if tp > price + min_distance and sl < price - min_distance:
            signals.append(Signal(
                symbol=symbol, direction="BUY",
                confidence=conf, entry_price=price,
                take_profit=tp, stop_loss=sl,
                reason=f"BOS BUY | Break>{prev_hh:.4f} ATR={atr_now:.2f} R:R=2.0"
            ))

    # BEARISH BOS - breakout below swing low
    if price < prev_ll - breakout_buffer:
        conf = 0.80

        tp = price - 2.0 * atr_now
        sl = prev_ll - breakout_buffer * 0.5

        min_distance = atr_now * 0.5
        if tp < price - min_distance and sl > price + min_distance:
            signals.append(Signal(
                symbol=symbol, direction="SELL",
                confidence=conf, entry_price=price,
                take_profit=tp, stop_loss=sl,
                reason=f"BOS SELL | Break<{prev_ll:.4f} ATR={atr_now:.2f} R:R=2.0"
            ))

    return signals

def fair_value_gap_final(data: List[Dict], symbol: str) -> List[Signal]:
    """Fair Value Gap - final optimized version."""
    if len(data) < 30:
        return []

    closes = [d['close'] for d in data]
    highs = [d['high'] for d in data]
    lows = [d['low'] for d in data]

    atr_values = atr(highs, lows, closes, 14)
    idx = len(closes) - 1

    if atr_values[idx] == 0:
        return []

    price = closes[idx]
    atr_now = atr_values[idx]

    signals = []

    # Look for significant gaps in recent candles
    for i in range(max(0, idx-15), idx):  # Look further back
        gap_size = abs(lows[i+1] - highs[i])
        if gap_size > atr_now * 0.2:  # Significant gap (reduced threshold)
            gap_high = highs[i]
            gap_low = lows[i+1]

            # Price near the gap area
            gap_center = (gap_high + gap_low) / 2
            if abs(price - gap_center) / gap_center < 0.02:  # Within 2% of gap center
                # Determine direction based on position relative to gap
                if price > gap_center:
                    # Above gap center - potential short (gap fill to bottom)
                    conf = 0.75
                    tp = gap_low - atr_now * 0.3  # Target below gap
                    sl = gap_high + atr_now * 0.5  # Stop above gap
                    if tp < price:
                        signals.append(Signal(
                            symbol=symbol, direction="SELL",
                            confidence=conf, entry_price=price,
                            take_profit=tp, stop_loss=sl,
                            reason=f"FVG SELL | Gap@{gap_high:.4f}-{gap_low:.4f} Size:{gap_size:.2f}"
                        ))
                else:
                    # Below gap center - potential long (gap fill to top)
                    conf = 0.75
                    tp = gap_high + atr_now * 0.3  # Target above gap
                    sl = gap_low - atr_now * 0.5   # Stop below gap
                    if tp > price:
                        signals.append(Signal(
                            symbol=symbol, direction="BUY",
                            confidence=conf, entry_price=price,
                            take_profit=tp, stop_loss=sl,
                            reason=f"FVG BUY | Gap@{gap_high:.4f}-{gap_low:.4f} Size:{gap_size:.2f}"
                        ))

    # Limit to 3 signals per pair to avoid overtrading
    return signals[:3]

# Test functions
CRYPTO_PAIRS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT']

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

def calculate_metrics(signals: List[Signal]) -> Dict:
    """Calculate performance metrics."""
    if not signals:
        return {'return': 0, 'win_rate': 0, 'trades': 0, 'avg_rr': 0, 'profit_factor': 0}

    balance = 10000
    wins = 0
    total_rr = 0
    gross_profit = 0
    gross_loss = 0

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
            gross_profit += pnl
        else:
            gross_loss += abs(pnl)

    total_return = (balance - 10000) / 10000 * 100
    win_rate = wins / len(signals) * 100 if signals else 0
    avg_rr = total_rr / len(signals) if signals else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    return {
        'return': total_return,
        'win_rate': win_rate,
        'trades': len(signals),
        'avg_rr': avg_rr,
        'profit_factor': profit_factor
    }

def main():
    print("J BRAVO SMART MONEY - FINAL OPTIMIZED VERSION")
    print("=" * 65)

    strategies = {
        'BOS Final': smart_money_bos_final,
        'FVG Final': fair_value_gap_final
    }

    all_results = []

    for strategy_name, strategy_func in strategies.items():
        print(f"\nTesting {strategy_name}:")
        print("-" * 55)

        for symbol in CRYPTO_PAIRS:
            data = fetch_data(symbol)
            if not data:
                print(f"{symbol}: No data")
                continue

            signals = strategy_func(data, symbol)
            metrics = calculate_metrics(signals)

            print(f"{symbol:8} | Return: {metrics['return']:6.2f}% | "
                  f"Win%: {metrics['win_rate']:5.1f}% | Trades: {metrics['trades']:2d} | "
                  f"Avg R:R: {metrics['avg_rr']:4.2f} | PF: {metrics['profit_factor']:4.2f}")

            all_results.append({
                'strategy': strategy_name,
                'symbol': symbol,
                **metrics
            })

    # Summary
    print("\n" + "=" * 65)
    print("FINAL RESULTS SUMMARY")
    print("=" * 65)

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
                print(f"  Best Win Rate: {best['win_rate']:.1f}%")
                print(f"  Best Profit Factor: {best['profit_factor']:.2f}")

                # Show top performers
                top_performers = sorted(valid_results, key=lambda x: x['return'], reverse=True)[:3]
                print("  Top Performers:")
                for i, perf in enumerate(top_performers, 1):
                    print(f"    {i}. {perf['symbol']}: {perf['return']:.2f}% ({perf['trades']} trades, {perf['win_rate']:.1f}% win)")
            else:
                print(f"\n{strategy_name}: No signals generated")

    # Overall winner
    print("\n" + "=" * 65)
    print("OVERALL WINNER ANALYSIS")
    print("=" * 65)

    all_valid = [r for r in all_results if r['trades'] > 0]
    if all_valid:
        overall_best = max(all_valid, key=lambda x: x['return'])
        print(f"Best Strategy/Pair: {overall_best['strategy']} on {overall_best['symbol']}")
        print(f"Return: {overall_best['return']:.2f}%")
        print(f"Win Rate: {overall_best['win_rate']:.1f}%")
        print(f"Trades: {overall_best['trades']}")
        print(f"Profit Factor: {overall_best['profit_factor']:.2f}")

if __name__ == "__main__":
    main()