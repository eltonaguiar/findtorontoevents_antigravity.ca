"""
Comprehensive J Bravo Smart Money Strategies Backtest
======================================================

Thoroughly tests the new J Bravo-inspired Smart Money Concepts strategies
across multiple crypto pairs to find true winners and optimal parameters.
"""

import requests
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import J Bravo strategies
from baby_strategies.hoffman_variations import (
    hoffman_smart_money_bos_signals,
    hoffman_fair_value_gap_signals,
    hoffman_change_of_character_signals,
    hoffman_order_block_signals,
    hoffman_liquidity_zone_signals
)

# Strategy configurations
J_BRAVO_STRATEGIES = {
    'smart_money_bos': {
        'name': 'Smart Money BOS',
        'function': hoffman_smart_money_bos_signals,
        'description': 'Break of Structure with order block confirmation'
    },
    'fair_value_gap': {
        'name': 'Fair Value Gap',
        'function': hoffman_fair_value_gap_signals,
        'description': 'FVG detection and gap filling'
    },
    'change_of_character': {
        'name': 'Change of Character',
        'function': hoffman_change_of_character_signals,
        'description': 'Consolidation to trending transition'
    },
    'order_block': {
        'name': 'Order Block',
        'function': hoffman_order_block_signals,
        'description': 'High-volume order area targeting'
    },
    'liquidity_zone': {
        'name': 'Liquidity Zone',
        'function': hoffman_liquidity_zone_signals,
        'description': 'Liquidity zone rejection trading'
    }
}

# Crypto pairs to test
CRYPTO_PAIRS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
    'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LTCUSDT', 'LINKUSDT',
    'UNIUSDT', 'ALGOUSDT', 'VETUSDT', 'ICPUSDT', 'FILUSDT'
]

def fetch_crypto_data(symbol: str, interval: str = '15m', limit: int = 1000) -> List[Dict]:
    """Fetch OHLCV data from Binance API and return as list of dicts."""
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
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

    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return []

def ohlcv_to_dataframe(ohlcv_data: List[Dict]) -> Any:
    """Convert OHLCV list to a simple dataframe-like structure for the strategies."""
    if not ohlcv_data:
        return None

    # Create a simple object that mimics pandas DataFrame for the strategies
    class SimpleDataFrame:
        def __init__(self, data):
            self.data = data
            self._cached_arrays = {}

        def __len__(self):
            return len(self.data)

        def __getitem__(self, key):
            if key in ['open', 'high', 'low', 'close', 'volume']:
                if key not in self._cached_arrays:
                    self._cached_arrays[key] = [row[key] for row in self.data]
                return self._cached_arrays[key]
            return None

    return SimpleDataFrame(ohlcv_data)

def calculate_performance_metrics(signals: List, initial_balance: float = 10000) -> Dict[str, Any]:
    """Calculate comprehensive performance metrics from signals."""
    if not signals:
        return {
            'total_return': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'num_trades': 0,
            'avg_trade': 0,
            'sharpe_ratio': 0,
            'total_pnl': 0
        }

    balance = initial_balance
    peak_balance = initial_balance
    max_drawdown = 0
    trades = []
    winning_trades = 0

    for signal in signals:
        entry_price = signal.entry_price
        exit_price = signal.take_profit if signal.direction == 'BUY' else signal.stop_loss
        position_size = balance * 0.02  # 2% risk per trade

        if signal.direction == 'BUY':
            pnl = (exit_price - entry_price) / entry_price * position_size
        else:  # SELL
            pnl = (entry_price - exit_price) / entry_price * position_size

        balance += pnl
        trades.append(pnl)

        # Update drawdown
        if balance > peak_balance:
            peak_balance = balance
        drawdown = (peak_balance - balance) / peak_balance
        max_drawdown = max(max_drawdown, drawdown)

        if pnl > 0:
            winning_trades += 1

    total_return = (balance - initial_balance) / initial_balance * 100
    win_rate = winning_trades / len(trades) if trades else 0
    avg_trade = sum(trades) / len(trades) if trades else 0

    # Profit factor
    winning_trades_sum = sum(t for t in trades if t > 0)
    losing_trades_sum = abs(sum(t for t in trades if t < 0))
    profit_factor = winning_trades_sum / losing_trades_sum if losing_trades_sum > 0 else float('inf')

    # Sharpe ratio (simplified)
    if len(trades) > 1:
        returns = [t/initial_balance for t in trades]
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        sharpe_ratio = mean_return / std_dev * (365 ** 0.5) if std_dev > 0 else 0
    else:
        sharpe_ratio = 0

    return {
        'total_return': total_return,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'num_trades': len(trades),
        'avg_trade': avg_trade,
        'sharpe_ratio': sharpe_ratio,
        'total_pnl': balance - initial_balance
    }

def run_strategy_backtest(strategy_key: str, symbol: str) -> Dict[str, Any]:
    """Run backtest for a specific strategy on a symbol."""
    print(f"Testing {J_BRAVO_STRATEGIES[strategy_key]['name']} on {symbol}...")

    # Fetch data
    ohlcv_data = fetch_crypto_data(symbol)
    if not ohlcv_data or len(ohlcv_data) < 200:
        return {'error': f'Insufficient data for {symbol}'}

    df = ohlcv_to_dataframe(ohlcv_data)
    if df is None:
        return {'error': f'Failed to process data for {symbol}'}

    # Generate signals
    strategy_func = J_BRAVO_STRATEGIES[strategy_key]['function']
    signals = strategy_func(df, symbol)

    # Calculate performance
    metrics = calculate_performance_metrics(signals)

    return {
        'strategy': J_BRAVO_STRATEGIES[strategy_key]['name'],
        'symbol': symbol,
        'signals_count': len(signals),
        **metrics
    }

def main():
    """Run comprehensive backtests across all strategies and pairs."""
    print("=" * 80)
    print("J BRAVO SMART MONEY STRATEGIES COMPREHENSIVE BACKTEST")
    print("=" * 80)
    print(f"Testing {len(J_BRAVO_STRATEGIES)} strategies across {len(CRYPTO_PAIRS)} crypto pairs")
    print(f"Total combinations: {len(J_BRAVO_STRATEGIES) * len(CRYPTO_PAIRS)}")
    print()

    all_results = []

    for strategy_key in J_BRAVO_STRATEGIES.keys():
        strategy_results = []

        for symbol in CRYPTO_PAIRS:
            result = run_strategy_backtest(strategy_key, symbol)
            if 'error' not in result:
                strategy_results.append(result)
                all_results.append(result)

        # Print strategy summary
        if strategy_results:
            print(f"\n{J_BRAVO_STRATEGIES[strategy_key]['name']} Results:")
            print("-" * 50)

            # Sort by total return
            sorted_results = sorted(strategy_results, key=lambda x: x['total_return'], reverse=True)

            for result in sorted_results[:5]:  # Top 5 performers
                print(f"{result['symbol']:8} | "
                      f"Return: {result['total_return']:6.2f}% | "
                      f"Trades: {result['signals_count']:3d} | "
                      f"Win%: {result['win_rate']*100:5.1f}% | "
                      f"PF: {result['profit_factor']:4.2f}")

    # Overall analysis
    print("\n" + "=" * 80)
    print("OVERALL ANALYSIS")
    print("=" * 80)

    # Best performers by strategy
    for strategy_key in J_BRAVO_STRATEGIES.keys():
        strategy_name = J_BRAVO_STRATEGIES[strategy_key]['name']
        strategy_data = [r for r in all_results if r['strategy'] == strategy_name]

        if strategy_data:
            best = max(strategy_data, key=lambda x: x['total_return'])
            avg_return = sum([r['total_return'] for r in strategy_data]) / len(strategy_data)
            avg_win_rate = sum([r['win_rate'] for r in strategy_data]) / len(strategy_data)

            print(f"\n{strategy_name}:")
            print(f"  Best Pair: {best['symbol']} ({best['total_return']:.2f}%)")
            print(f"  Avg Return: {avg_return:.2f}%")
            print(f"  Avg Win Rate: {avg_win_rate*100:.1f}%")
            print(f"  Total Signals: {sum(r['signals_count'] for r in strategy_data)}")

    # Best overall strategies
    print("\nTOP PERFORMING STRATEGIES:")
    print("-" * 40)

    # Group by strategy and calculate averages
    strategy_performance = {}
    for result in all_results:
        strategy = result['strategy']
        if strategy not in strategy_performance:
            strategy_performance[strategy] = []
        strategy_performance[strategy].append(result['total_return'])

    for strategy, returns in strategy_performance.items():
        avg_return = sum(returns) / len(returns)
        max_return = max(returns)
        print(f"{strategy:20} | Avg: {avg_return:6.2f}% | Best: {max_return:6.2f}%")

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"jbravo_backtest_results_{timestamp}.json"

    with open(filename, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\nDetailed results saved to: {filename}")

if __name__ == "__main__":
    main()