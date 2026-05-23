"""
J BRAVO EXTENSIVE BACKTEST - 20+ CRYPTO PAIRS
==============================================

Comprehensive backtesting of winning J Bravo strategies across 20+ crypto pairs.
Testing individual pair performance and overall system robustness.
"""

import requests
import math
from typing import List, Dict, Any
from datetime import datetime
import json
import time

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

    atr_values = [0.0] * len(highs)
    tr_values = []

    for i in range(1, len(highs)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr_values.append(tr)

    if len(tr_values) >= period:
        atr_values[period] = sum(tr_values[:period]) / period

        for i in range(period + 1, len(highs)):
            atr_values[i] = (atr_values[i-1] * (period - 1) + tr_values[i-1]) / period

    return atr_values

def rsi(closes: List[float], period: int = 14) -> List[float]:
    """Calculate RSI."""
    if len(closes) < period + 1:
        return [50.0] * len(closes)

    rsi_values = [50.0] * len(closes)
    gains = []
    losses = []

    for i in range(1, len(closes)):
        change = closes[i] - closes[i-1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    if len(gains) >= period:
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        if avg_loss == 0:
            rsi_values[period] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_values[period] = 100.0 - (100.0 / (1.0 + rs))

        for i in range(period + 1, len(closes)):
            avg_gain = (avg_gain * (period - 1) + gains[i-1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i-1]) / period

            if avg_loss == 0:
                rsi_values[i] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_values[i] = 100.0 - (100.0 / (1.0 + rs))

    return rsi_values

# =====================================================================
# TOP PERFORMING STRATEGIES
# =====================================================================

def adaptive_atr_fvg(data: List[Dict], symbol: str) -> List[Signal]:
    """Adaptive ATR FVG - Best performing strategy."""
    if len(data) < 100:
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

    # Calculate ATR percentile rank for adaptive scaling
    lookback = 50
    if idx >= lookback:
        recent_atr = atr_values[max(0, idx-lookback):idx+1]
        valid_atr = [a for a in recent_atr if a > 0]
        if valid_atr:
            percentile = sum(1 for a in valid_atr if a <= atr_now) / len(valid_atr)
        else:
            percentile = 0.5
    else:
        percentile = 0.5

    # Adaptive multipliers based on volatility
    if percentile < 0.3:  # Low volatility
        tp_mult = 1.5
        sl_mult = 0.8
    elif percentile > 0.7:  # High volatility
        tp_mult = 2.5
        sl_mult = 1.2
    else:  # Medium volatility
        tp_mult = 2.0
        sl_mult = 1.0

    signals = []

    # Look for gaps with adaptive ATR scaling
    for i in range(max(0, idx-12), idx):
        gap_size = abs(lows[i+1] - highs[i])
        if gap_size > atr_now * 0.18:  # Adaptive gap threshold
            gap_high = highs[i]
            gap_low = lows[i+1]
            gap_center = (gap_high + gap_low) / 2

            if abs(price - gap_center) / gap_center < 0.025:
                if price > gap_center:
                    # Short with adaptive targets
                    conf = 0.75
                    tp = gap_low - tp_mult * atr_now
                    sl = gap_high + sl_mult * atr_now
                    if tp < price:
                        signals.append(Signal(
                            symbol=symbol, direction="SELL",
                            confidence=conf, entry_price=price,
                            take_profit=tp, stop_loss=sl,
                            reason=f"ADAPT_FVG SELL | Gap@{gap_high:.4f}-{gap_low:.4f} ATR_pct={percentile:.1%}"
                        ))
                else:
                    # Long with adaptive targets
                    conf = 0.75
                    tp = gap_high + tp_mult * atr_now
                    sl = gap_low - sl_mult * atr_now
                    if tp > price:
                        signals.append(Signal(
                            symbol=symbol, direction="BUY",
                            confidence=conf, entry_price=price,
                            take_profit=tp, stop_loss=sl,
                            reason=f"ADAPT_FVG BUY | Gap@{gap_high:.4f}-{gap_low:.4f} ATR_pct={percentile:.1%}"
                        ))

    return signals[:2]

def fvg_momentum_filter(data: List[Dict], symbol: str) -> List[Signal]:
    """FVG + Momentum Filter - Strong performer."""
    if len(data) < 50:
        return []

    closes = [d['close'] for d in data]
    highs = [d['high'] for d in data]
    lows = [d['low'] for d in data]

    atr_values = atr(highs, lows, closes, 14)
    rsi_values = rsi(closes, 14)
    idx = len(closes) - 1

    if atr_values[idx] == 0:
        return []

    price = closes[idx]
    atr_now = atr_values[idx]
    rsi_now = rsi_values[idx]

    signals = []

    # Look for significant gaps with momentum confirmation
    for i in range(max(0, idx-15), idx):
        gap_size = abs(lows[i+1] - highs[i])
        if gap_size > atr_now * 0.15:  # Significant gap
            gap_high = highs[i]
            gap_low = lows[i+1]
            gap_center = (gap_high + gap_low) / 2

            # Price near gap area
            if abs(price - gap_center) / gap_center < 0.025:
                # Check momentum alignment
                momentum_conf = 0.0

                # RSI momentum filter
                if price > gap_center and rsi_now < 70:  # Oversold for shorts
                    momentum_conf = 0.8
                elif price < gap_center and rsi_now > 30:  # Overbought for longs
                    momentum_conf = 0.8

                if momentum_conf > 0:
                    if price > gap_center:
                        # Short opportunity
                        conf = 0.75 * momentum_conf
                        tp = gap_low - atr_now * 0.4
                        sl = gap_high + atr_now * 0.6
                        if tp < price:
                            signals.append(Signal(
                                symbol=symbol, direction="SELL",
                                confidence=conf, entry_price=price,
                                take_profit=tp, stop_loss=sl,
                                reason=f"FVG+MOM SELL | Gap@{gap_high:.4f}-{gap_low:.4f} RSI={rsi_now:.1f}"
                            ))
                    else:
                        # Long opportunity
                        conf = 0.75 * momentum_conf
                        tp = gap_high + atr_now * 0.4
                        sl = gap_low - atr_now * 0.6
                        if tp > price:
                            signals.append(Signal(
                                symbol=symbol, direction="BUY",
                                confidence=conf, entry_price=price,
                                take_profit=tp, stop_loss=sl,
                                reason=f"FVG+MOM BUY | Gap@{gap_high:.4f}-{gap_low:.4f} RSI={rsi_now:.1f}"
                            ))

    return signals[:2]

# =====================================================================
# EXTENDED CRYPTO PAIR LIST
# =====================================================================

EXTENDED_CRYPTO_PAIRS = [
    # Major coins
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT',
    # Large caps
    'AVAXUSDT', 'LTCUSDT', 'LINKUSDT', 'ALGOUSDT', 'VETUSDT', 'ICPUSDT',
    # Mid caps
    'FILUSDT', 'TRXUSDT', 'ETCUSDT', 'XLMUSDT', 'THETAUSDT', 'FTMUSDT',
    # Altcoins
    'NEARUSDT', 'FLOWUSDT', 'SANDUSDT', 'MANAUSDT', 'AXSUSDT', 'CHZUSDT',
    # Total: 24 pairs
]

def fetch_data(symbol: str, interval: str = '1h', limit: int = 300) -> List[Dict]:
    """Fetch data from Binance with retry logic."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            response = requests.get(url, timeout=15)
            data = response.json()

            if not isinstance(data, list) or len(data) < 50:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return []

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
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return []
    return []

def calculate_metrics(signals: List[Signal]) -> Dict:
    """Calculate performance metrics."""
    if not signals:
        return {'return': 0, 'win_rate': 0, 'trades': 0, 'avg_rr': 0, 'profit_factor': 0,
                'avg_win': 0, 'avg_loss': 0, 'max_win': 0, 'max_loss': 0}

    balance = 10000
    wins = 0
    total_rr = 0
    gross_profit = 0
    gross_loss = 0
    win_returns = []
    loss_returns = []

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
            win_returns.append(pnl)
        else:
            gross_loss += abs(pnl)
            loss_returns.append(abs(pnl))

    total_return = (balance - 10000) / 10000 * 100
    win_rate = wins / len(signals) * 100 if signals else 0
    avg_rr = total_rr / len(signals) if signals else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    avg_win = sum(win_returns) / len(win_returns) if win_returns else 0
    avg_loss = sum(loss_returns) / len(loss_returns) if loss_returns else 0
    max_win = max(win_returns) if win_returns else 0
    max_loss = max(loss_returns) if loss_returns else 0

    return {
        'return': total_return,
        'win_rate': win_rate,
        'trades': len(signals),
        'avg_rr': avg_rr,
        'profit_factor': profit_factor,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'max_win': max_win,
        'max_loss': max_loss
    }

def run_extensive_backtest():
    """Run comprehensive backtest across 20+ crypto pairs."""
    print("J BRAVO EXTENSIVE BACKTEST - 20+ CRYPTO PAIRS")
    print("=" * 70)
    print(f"Testing {len(EXTENDED_CRYPTO_PAIRS)} crypto pairs")
    print(f"Strategies: Adaptive ATR FVG, FVG + Momentum")
    print(f"Timeframe: 1h, Data points: 300 per pair")
    print()

    strategies = {
        'Adaptive ATR FVG': adaptive_atr_fvg,
        'FVG + Momentum': fvg_momentum_filter
    }

    all_results = []
    pair_results = {pair: {} for pair in EXTENDED_CRYPTO_PAIRS}

    # Test each strategy
    for strategy_name, strategy_func in strategies.items():
        print(f"Testing {strategy_name}:")
        print("-" * 50)

        strategy_total_trades = 0
        strategy_total_return = 0
        valid_pairs = 0

        for i, symbol in enumerate(EXTENDED_CRYPTO_PAIRS):
            print(f"[{i+1:2d}/{len(EXTENDED_CRYPTO_PAIRS)}] {symbol:10}", end=" | ")

            data = fetch_data(symbol)
            if not data:
                print("No data")
                continue

            signals = strategy_func(data, symbol)
            metrics = calculate_metrics(signals)

            pair_results[symbol][strategy_name] = metrics

            if metrics['trades'] > 0:
                valid_pairs += 1
                strategy_total_trades += metrics['trades']
                strategy_total_return += metrics['return']

            print(f"Return: {metrics['return']:6.2f}% | "
                  f"Win%: {metrics['win_rate']:5.1f}% | Trades: {metrics['trades']:2d}")

            all_results.append({
                'strategy': strategy_name,
                'symbol': symbol,
                **metrics
            })

        # Strategy summary
        avg_return = strategy_total_return / valid_pairs if valid_pairs > 0 else 0
        print(f"\n{strategy_name} SUMMARY:")
        print(f"  Pairs with signals: {valid_pairs}/{len(EXTENDED_CRYPTO_PAIRS)}")
        print(f"  Total trades: {strategy_total_trades}")
        print(f"  Average return per pair: {avg_return:.2f}%")
        print()

    # Overall analysis
    print("=" * 70)
    print("EXTENSIVE BACKTEST ANALYSIS")
    print("=" * 70)

    # Best performing pairs overall
    print("\n🏆 TOP PERFORMING PAIRS (by total return):")
    pair_total_returns = {}
    for symbol in EXTENDED_CRYPTO_PAIRS:
        total_return = 0
        total_trades = 0
        for strategy_name in strategies.keys():
            if symbol in pair_results and strategy_name in pair_results[symbol]:
                metrics = pair_results[symbol][strategy_name]
                total_return += metrics['return']
                total_trades += metrics['trades']
        if total_trades > 0:
            pair_total_returns[symbol] = (total_return, total_trades)

    top_pairs = sorted(pair_total_returns.items(), key=lambda x: x[1][0], reverse=True)[:10]
    for i, (symbol, (return_pct, trades)) in enumerate(top_pairs, 1):
        print(f"  {i}. {symbol:10} | Return: {return_pct:6.2f}% | Trades: {trades}")

    # Strategy comparison
    print("\n📊 STRATEGY COMPARISON:")
    for strategy_name in strategies.keys():
        strategy_data = [r for r in all_results if r['strategy'] == strategy_name and r['trades'] > 0]
        if strategy_data:
            avg_return = sum(r['return'] for r in strategy_data) / len(strategy_data)
            avg_win_rate = sum(r['win_rate'] for r in strategy_data) / len(strategy_data)
            total_trades = sum(r['trades'] for r in strategy_data)
            valid_pairs = len(strategy_data)

            print(f"  {strategy_name}:")
            print(f"    Average Return: {avg_return:.2f}%")
            print(f"    Average Win Rate: {avg_win_rate:.1f}%")
            print(f"    Total Trades: {total_trades}")
            print(f"    Valid Pairs: {valid_pairs}/{len(EXTENDED_CRYPTO_PAIRS)}")

    # Individual pair deep dive
    print("\n🔍 INDIVIDUAL PAIR ANALYSIS:")
    print("Top 5 pairs with most consistent performance:")

    pair_consistency = {}
    for symbol in EXTENDED_CRYPTO_PAIRS:
        if symbol in pair_results:
            returns = []
            win_rates = []
            for strategy_name in strategies.keys():
                if strategy_name in pair_results[symbol]:
                    metrics = pair_results[symbol][strategy_name]
                    if metrics['trades'] > 0:
                        returns.append(metrics['return'])
                        win_rates.append(metrics['win_rate'])

            if returns:
                avg_return = sum(returns) / len(returns)
                avg_win_rate = sum(win_rates) / len(win_rates)
                consistency_score = avg_return * (avg_win_rate / 100)  # Return weighted by win rate
                pair_consistency[symbol] = (avg_return, avg_win_rate, consistency_score)

    top_consistent = sorted(pair_consistency.items(), key=lambda x: x[1][2], reverse=True)[:5]
    for i, (symbol, (avg_ret, avg_wr, score)) in enumerate(top_consistent, 1):
        print(f"  {i}. {symbol:10} | Avg Return: {avg_ret:5.2f}% | Avg Win Rate: {avg_wr:5.1f}% | Score: {score:.3f}")

    # Market regime analysis
    print("\n🌊 MARKET REGIME ANALYSIS:")
    large_cap = ['BTCUSDT', 'ETHUSDT']
    mid_cap = ['BNBUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT', 'AVAXUSDT', 'LTCUSDT']
    small_cap = [p for p in EXTENDED_CRYPTO_PAIRS if p not in large_cap + mid_cap]

    for category, pairs in [("Large Cap", large_cap), ("Mid Cap", mid_cap), ("Small Cap", small_cap)]:
        category_returns = []
        for symbol in pairs:
            if symbol in pair_consistency:
                category_returns.append(pair_consistency[symbol][0])

        if category_returns:
            avg_category_return = sum(category_returns) / len(category_returns)
            print(f"  {category}: {avg_category_return:.2f}% average return")

    # Export detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"jbravo_extensive_backtest_{timestamp}.json"

    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'pairs_tested': EXTENDED_CRYPTO_PAIRS,
            'strategies': list(strategies.keys()),
            'pair_results': pair_results,
            'all_results': all_results,
            'summary': {
                'total_pairs': len(EXTENDED_CRYPTO_PAIRS),
                'strategies_tested': len(strategies),
                'top_pairs': top_pairs[:5],
                'top_consistent': top_consistent
            }
        }, f, indent=2)

    print(f"\n💾 Detailed results saved to: {results_file}")

    return all_results, pair_results

if __name__ == "__main__":
    results, pair_results = run_extensive_backtest()