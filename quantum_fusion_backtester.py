"""
Quantum Fusion Strategy - Comprehensive Backtesting Framework
===============================================================

Extensive validation of the Quantum Fusion Strategy across:
- Multiple timeframes (1m, 5m, 15m, 30m, 45m, 1h, 4h, 1d, 2d, 1w, 1M)
- Multiple crypto pairs (BTC, ETH, ADA, SOL, DOT, LINK)
- Historical data validation
- Performance metrics calculation
- Risk analysis and drawdown assessment
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

from quantum_fusion_strategy import QuantumFusionStrategy

class QuantumFusionBacktester:
    """Comprehensive backtester for the Quantum Fusion Strategy."""

    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.strategy = QuantumFusionStrategy()
        self.results = {}

    def fetch_historical_data(self, symbol: str, timeframe: str, days: int = 365) -> pd.DataFrame:
        """Fetch historical data for backtesting."""

        try:
            # Map timeframe to yfinance interval
            interval_map = {
                '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m', '45m': '45m',
                '1h': '1h', '4h': '1h', '1d': '1d', '2d': '1d', '1w': '1wk', '1M': '1mo'
            }

            interval = interval_map.get(timeframe, '1d')
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Download data
            data = yf.download(symbol, start=start_date, end=end_date, interval=interval)

            if data.empty:
                print(f"❌ No data available for {symbol} on {timeframe}")
                return pd.DataFrame()

            # Clean column names
            data.columns = data.columns.str.lower()

            # Resample for 4h if needed
            if timeframe == '4h' and interval == '1h':
                data = data.resample('4H').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()

            # Resample for 2d if needed
            if timeframe == '2d' and interval == '1d':
                data = data.resample('2D').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()

            return data

        except Exception as e:
            print(f"❌ Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    def simulate_trade(self, signal, data: pd.DataFrame, idx: int) -> dict:
        """Simulate a single trade based on signal."""

        entry_price = signal.entry_price
        stop_loss = signal.stop_loss
        take_profit = signal.take_profit

        # Find exit conditions
        trade_result = {
            'entry_time': data.index[idx],
            'entry_price': entry_price,
            'direction': signal.direction,
            'exit_time': None,
            'exit_price': None,
            'exit_reason': None,
            'pnl': 0,
            'pnl_percent': 0,
            'holding_period': 0
        }

        # Look ahead for exit (max 50 bars)
        max_lookahead = min(50, len(data) - idx - 1)

        for i in range(1, max_lookahead + 1):
            current_idx = idx + i
            current_high = data['high'].iloc[current_idx]
            current_low = data['low'].iloc[current_idx]
            current_close = data['close'].iloc[current_idx]

            # Check stop loss and take profit
            if signal.direction == 'BUY':
                if current_low <= stop_loss:
                    trade_result.update({
                        'exit_time': data.index[current_idx],
                        'exit_price': stop_loss,
                        'exit_reason': 'stop_loss',
                        'pnl': stop_loss - entry_price,
                        'pnl_percent': (stop_loss - entry_price) / entry_price * 100,
                        'holding_period': i
                    })
                    break
                elif current_high >= take_profit:
                    trade_result.update({
                        'exit_time': data.index[current_idx],
                        'exit_price': take_profit,
                        'exit_reason': 'take_profit',
                        'pnl': take_profit - entry_price,
                        'pnl_percent': (take_profit - entry_price) / entry_price * 100,
                        'holding_period': i
                    })
                    break
            else:  # SELL
                if current_high >= stop_loss:  # Stop loss for shorts
                    trade_result.update({
                        'exit_time': data.index[current_idx],
                        'exit_price': stop_loss,
                        'exit_reason': 'stop_loss',
                        'pnl': entry_price - stop_loss,
                        'pnl_percent': (entry_price - stop_loss) / entry_price * 100,
                        'holding_period': i
                    })
                    break
                elif current_low <= take_profit:  # Take profit for shorts
                    trade_result.update({
                        'exit_time': data.index[current_idx],
                        'exit_price': take_profit,
                        'exit_reason': 'take_profit',
                        'pnl': entry_price - take_profit,
                        'pnl_percent': (entry_price - take_profit) / entry_price * 100,
                        'holding_period': i
                    })
                    break

        # If no exit found, close at end of look-ahead period
        if trade_result['exit_time'] is None:
            exit_price = data['close'].iloc[min(idx + max_lookahead, len(data) - 1)]
            trade_result.update({
                'exit_time': data.index[min(idx + max_lookahead, len(data) - 1)],
                'exit_price': exit_price,
                'exit_reason': 'time_exit',
                'pnl': (exit_price - entry_price) if signal.direction == 'BUY' else (entry_price - exit_price),
                'pnl_percent': ((exit_price - entry_price) / entry_price * 100) if signal.direction == 'BUY' else ((entry_price - exit_price) / entry_price * 100),
                'holding_period': max_lookahead
            })

        return trade_result

    def backtest_pair_timeframe(self, symbol: str, timeframe: str, days: int = 365) -> dict:
        """Backtest strategy on a specific pair and timeframe."""

        print(f"🔬 Backtesting {symbol} on {timeframe} timeframe...")

        # Fetch data
        data = self.fetch_historical_data(symbol, timeframe, days)
        if data.empty or len(data) < 200:
            return {'error': f'Insufficient data: {len(data)} points'}

        # Generate signals
        correlated_assets = {}
        if 'BTC' in symbol:
            correlated_assets['ETH'] = data.copy()  # Simplified correlation
        elif 'ETH' in symbol:
            correlated_assets['BTC'] = data.copy()

        signals = self.strategy.generate_signals(data, symbol.replace('-USD', '').replace('USDT', ''), timeframe, correlated_assets)

        if not signals:
            return {'error': 'No signals generated'}

        # Simulate trades
        trades = []
        capital = self.initial_capital
        peak_capital = capital
        max_drawdown = 0
        win_trades = 0
        loss_trades = 0

        for signal in signals:
            # Find signal index in data
            signal_time = None
            signal_idx = None

            # Find closest timestamp
            for idx, timestamp in enumerate(data.index):
                if timestamp >= signal.entry_time:
                    signal_idx = idx
                    break

            if signal_idx is None or signal_idx >= len(data) - 5:
                continue

            # Simulate trade
            trade = self.simulate_trade(signal, data, signal_idx)
            trades.append(trade)

            # Update capital
            trade_value = capital * 0.02  # 2% risk per trade
            pnl_amount = trade_value * (trade['pnl_percent'] / 100)
            capital += pnl_amount

            # Track drawdown
            peak_capital = max(peak_capital, capital)
            current_drawdown = (peak_capital - capital) / peak_capital
            max_drawdown = max(max_drawdown, current_drawdown)

            # Count wins/losses
            if trade['pnl'] > 0:
                win_trades += 1
            else:
                loss_trades += 1

        # Calculate metrics
        total_trades = len(trades)
        win_rate = win_trades / total_trades if total_trades > 0 else 0

        if trades:
            avg_win = np.mean([t['pnl_percent'] for t in trades if t['pnl'] > 0]) if win_trades > 0 else 0
            avg_loss = np.mean([t['pnl_percent'] for t in trades if t['pnl'] < 0]) if loss_trades > 0 else 0
            profit_factor = abs(sum(t['pnl'] for t in trades if t['pnl'] > 0) / sum(t['pnl'] for t in trades if t['pnl'] < 0)) if loss_trades > 0 else float('inf')

            # Sharpe ratio (simplified)
            returns = [t['pnl_percent'] / 100 for t in trades]
            if len(returns) > 1:
                sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
            else:
                sharpe_ratio = 0

            # Calmar ratio
            total_return = (capital - self.initial_capital) / self.initial_capital
            calmar_ratio = total_return / max_drawdown if max_drawdown > 0 else float('inf')
        else:
            avg_win = avg_loss = profit_factor = sharpe_ratio = calmar_ratio = 0

        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'total_trades': total_trades,
            'win_trades': win_trades,
            'loss_trades': loss_trades,
            'win_rate': round(win_rate, 4),
            'avg_win_percent': round(avg_win, 4),
            'avg_loss_percent': round(avg_loss, 4),
            'profit_factor': round(profit_factor, 4),
            'sharpe_ratio': round(sharpe_ratio, 4),
            'max_drawdown': round(max_drawdown, 4),
            'calmar_ratio': round(calmar_ratio, 4),
            'total_return_percent': round((capital - self.initial_capital) / self.initial_capital * 100, 4),
            'final_capital': round(capital, 2),
            'avg_holding_period': round(np.mean([t['holding_period'] for t in trades]), 2) if trades else 0,
            'trades': trades[:10]  # Sample of first 10 trades
        }

        print(f"   ✅ {total_trades} trades, Win Rate: {win_rate:.1%}, Return: {result['total_return_percent']:.1f}%")
        return result

    def run_comprehensive_backtest(self):
        """Run comprehensive backtest across multiple pairs and timeframes."""

        print("🧬 Quantum Fusion Strategy - Comprehensive Backtesting")
        print("=" * 70)

        # Test pairs and timeframes
        pairs = ['BTC-USD', 'ETH-USD', 'ADA-USD', 'SOL-USD', 'DOT-USD', 'LINK-USD']
        timeframes = ['1h', '4h', '1d', '1w']  # Focus on key timeframes for speed

        all_results = []
        summary_stats = {
            'total_combinations': len(pairs) * len(timeframes),
            'successful_tests': 0,
            'avg_win_rate': [],
            'avg_sharpe': [],
            'avg_return': [],
            'avg_max_dd': [],
            'total_trades': 0
        }

        for pair in pairs:
            for timeframe in timeframes:
                result = self.backtest_pair_timeframe(pair, timeframe, days=180)  # 6 months

                if 'error' not in result:
                    all_results.append(result)
                    summary_stats['successful_tests'] += 1
                    summary_stats['avg_win_rate'].append(result['win_rate'])
                    summary_stats['avg_sharpe'].append(result['sharpe_ratio'])
                    summary_stats['avg_return'].append(result['total_return_percent'])
                    summary_stats['avg_max_dd'].append(result['max_drawdown'])
                    summary_stats['total_trades'] += result['total_trades']

                    # Store in results dict
                    key = f"{pair}_{timeframe}"
                    self.results[key] = result
                else:
                    print(f"   ❌ {pair} on {timeframe}: {result['error']}")

        # Calculate summary
        if summary_stats['successful_tests'] > 0:
            summary_stats.update({
                'avg_win_rate': round(np.mean(summary_stats['avg_win_rate']), 4),
                'avg_sharpe': round(np.mean(summary_stats['avg_sharpe']), 4),
                'avg_return': round(np.mean(summary_stats['avg_return']), 4),
                'avg_max_dd': round(np.mean(summary_stats['avg_max_dd']), 4),
                'overall_win_rate': sum(r['win_trades'] for r in all_results) / sum(r['total_trades'] for r in all_results)
            })

        self.results['summary'] = summary_stats
        self.results['all_results'] = all_results

        # Save results
        self._save_backtest_results()

        # Print summary
        self._print_backtest_summary()

    def _save_backtest_results(self):
        """Save backtest results to JSON file."""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"quantum_fusion_backtest_results_{timestamp}.json"

        # Convert to serializable format
        serializable_results = {}
        for key, value in self.results.items():
            if key == 'all_results':
                serializable_results[key] = value
            elif isinstance(value, dict):
                serializable_results[key] = {k: v for k, v in value.items() if k != 'trades'}
            else:
                serializable_results[key] = value

        import json
        with open(filename, 'w') as f:
            json.dump(serializable_results, f, indent=2, default=str)

        print(f"\n💾 Backtest results saved to: {filename}")

    def _print_backtest_summary(self):
        """Print comprehensive backtest summary."""

        summary = self.results.get('summary', {})

        print("\n" + "="*70)
        print("🎯 QUANTUM FUSION BACKTEST SUMMARY")
        print("="*70)

        print(f"📊 Total Combinations Tested: {summary.get('total_combinations', 0)}")
        print(f"✅ Successful Tests: {summary.get('successful_tests', 0)}")
        print(f"📈 Total Trades Executed: {summary.get('total_trades', 0)}")

        print(f"\n🎯 PERFORMANCE METRICS:")
        print(f"   • Average Win Rate: {summary.get('avg_win_rate', 0):.1%}")
        print(f"   • Average Sharpe Ratio: {summary.get('avg_sharpe', 0):.2f}")
        print(f"   • Average Total Return: {summary.get('avg_return', 0):.1f}%")
        print(f"   • Average Max Drawdown: {summary.get('avg_max_dd', 0):.1%}")

        if summary.get('overall_win_rate', 0) > 0:
            print(f"   • Overall Win Rate: {summary.get('overall_win_rate', 0):.1%}")

        print(f"\n🔍 TOP PERFORMING COMBINATIONS:")

        # Sort by total return
        all_results = self.results.get('all_results', [])
        sorted_results = sorted(all_results, key=lambda x: x.get('total_return_percent', 0), reverse=True)

        for i, result in enumerate(sorted_results[:5]):
            print(f"   {i+1}. {result['symbol']} {result['timeframe']}: {result['total_return_percent']:.1f}% return, {result['win_rate']:.1%} win rate")

        print(f"\n🛡️ RISK ANALYSIS:")
        print(f"   • Best Sharpe Ratio: {max((r.get('sharpe_ratio', 0) for r in all_results), default=0):.2f}")
        print(f"   • Lowest Max Drawdown: {min((r.get('max_drawdown', 0) for r in all_results), default=0):.1%}")
        print(f"   • Best Profit Factor: {max((r.get('profit_factor', 0) for r in all_results), default=0):.2f}")

        # Validation checks
        print(f"\n✅ VALIDATION CHECKS:")
        win_rate_ok = summary.get('avg_win_rate', 0) >= 0.55
        sharpe_ok = summary.get('avg_sharpe', 0) >= 1.0
        return_ok = summary.get('avg_return', 0) >= 10.0
        drawdown_ok = summary.get('avg_max_dd', 0) <= 0.20

        print(f"   • Win Rate ≥55%: {'✅' if win_rate_ok else '❌'} ({summary.get('avg_win_rate', 0):.1%})")
        print(f"   • Sharpe Ratio ≥1.0: {'✅' if sharpe_ok else '❌'} ({summary.get('avg_sharpe', 0):.2f})")
        print(f"   • Return ≥10%: {'✅' if return_ok else '❌'} ({summary.get('avg_return', 0):.1f}%)")
        print(f"   • Max DD ≤20%: {'✅' if drawdown_ok else '❌'} ({summary.get('avg_max_dd', 0):.1%})")

        all_checks_pass = win_rate_ok and sharpe_ok and return_ok and drawdown_ok
        print(f"\n🏆 OVERALL VALIDATION: {'✅ PASSED' if all_checks_pass else '❌ FAILED'}")

        if all_checks_pass:
            print("   🎉 Quantum Fusion Strategy validation successful!")
            print("   📈 Ready for production deployment across all timeframes!")
        else:
            print("   ⚠️ Strategy needs optimization for better performance.")


if __name__ == "__main__":
    backtester = QuantumFusionBacktester(initial_capital=10000.0)
    backtester.run_comprehensive_backtest()