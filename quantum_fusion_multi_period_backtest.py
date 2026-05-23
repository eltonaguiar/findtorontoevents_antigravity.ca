"""
Quantum Fusion Strategy - Multi-Period Backtesting
==================================================

Comprehensive backtesting across multiple historical periods:
- 2026 YTD (Jan 2026 - Feb 2026)
- 2025 Full Year (Jan 2025 - Dec 2025)
- 2024 Full Year (Jan 2024 - Dec 2024)
- 2023 Full Year (Jan 2023 - Dec 2023)
- 2022 Full Year (Jan 2022 - Dec 2022)
- 2021 Full Year (Jan 2021 - Dec 2021)

Tests strategy consistency across different market regimes.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

from quantum_fusion_strategy import QuantumFusionStrategy

class MultiPeriodBacktester:
    """Backtester for multiple historical periods."""

    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.strategy = QuantumFusionStrategy()
        self.results = {}

    def define_test_periods(self):
        """Define the historical periods to test."""

        current_date = datetime(2026, 2, 27)  # Current date as of context

        periods = {
            '2026_YTD': {
                'start': datetime(2026, 1, 1),
                'end': current_date,
                'description': '2026 Year-to-Date (Jan-Feb 2026)',
                'market_regime': 'Post-Halving Recovery'
            },
            '2025_Full': {
                'start': datetime(2025, 1, 1),
                'end': datetime(2025, 12, 31),
                'description': '2025 Full Year',
                'market_regime': 'Bull Market Peak'
            },
            '2024_Full': {
                'start': datetime(2024, 1, 1),
                'end': datetime(2024, 12, 31),
                'description': '2024 Full Year',
                'market_regime': 'Bull Market Acceleration'
            },
            '2023_Full': {
                'start': datetime(2023, 1, 1),
                'end': datetime(2023, 12, 31),
                'description': '2023 Full Year',
                'market_regime': 'Post-FTX Recovery'
            },
            '2022_Full': {
                'start': datetime(2022, 1, 1),
                'end': datetime(2022, 12, 31),
                'description': '2022 Full Year',
                'market_regime': 'Bear Market'
            },
            '2021_Full': {
                'start': datetime(2021, 1, 1),
                'end': datetime(2021, 12, 31),
                'description': '2021 Full Year',
                'market_regime': 'Bull Market Parabolic'
            }
        }

        return periods

    def fetch_period_data(self, symbol: str, period_config: dict, timeframe: str = '1d'):
        """Fetch data for a specific period and timeframe."""

        try:
            # Map timeframe to yfinance interval
            interval_map = {
                '1h': '1h', '4h': '1h', '1d': '1d', '1w': '1wk', '1M': '1mo'
            }

            interval = interval_map.get(timeframe, '1d')

            # Download data
            data = yf.download(symbol, start=period_config['start'],
                             end=period_config['end'], interval=interval)

            if data.empty:
                print(f"❌ No data available for {symbol} in {period_config['description']}")
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

            return data

        except Exception as e:
            print(f"❌ Error fetching data for {symbol} in {period_config['description']}: {e}")
            return pd.DataFrame()

    def simulate_period_trades(self, data: pd.DataFrame, symbol: str, timeframe: str,
                              period_name: str) -> dict:
        """Simulate trades for a specific period."""

        if data.empty or len(data) < 100:
            return {'error': f'Insufficient data: {len(data)} points'}

        # Generate signals
        correlated_assets = {}
        if 'BTC' in symbol:
            correlated_assets['ETH'] = data.copy()
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
            signal_time = signal.entry_time if hasattr(signal, 'entry_time') else None
            signal_idx = None

            if signal_time:
                # Find closest timestamp
                for idx, timestamp in enumerate(data.index):
                    if timestamp >= signal_time:
                        signal_idx = idx
                        break
            else:
                # Use signal position in list as approximation
                signal_idx = len(data) - len(signals) + signals.index(signal) + 50

            if signal_idx is None or signal_idx >= len(data) - 5:
                continue

            # Simulate trade
            trade = self._simulate_single_trade(signal, data, signal_idx)
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

            returns = [t['pnl_percent'] / 100 for t in trades]
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if len(returns) > 1 and np.std(returns) > 0 else 0

            total_return = (capital - self.initial_capital) / self.initial_capital
            calmar_ratio = total_return / max_drawdown if max_drawdown > 0 else float('inf')
        else:
            avg_win = avg_loss = profit_factor = sharpe_ratio = calmar_ratio = 0

        result = {
            'period': period_name,
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
            'data_points': len(data),
            'signal_density': round(total_trades / len(data) * 100, 2) if len(data) > 0 else 0
        }

        return result

    def _simulate_single_trade(self, signal, data: pd.DataFrame, idx: int) -> dict:
        """Simulate a single trade."""

        entry_price = signal.entry_price
        stop_loss = signal.stop_loss
        take_profit = signal.take_profit

        # Look ahead for exit (max 20 bars for faster simulation)
        max_lookahead = min(20, len(data) - idx - 1)

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

        for i in range(1, max_lookahead + 1):
            current_idx = idx + i
            current_high = data['high'].iloc[current_idx]
            current_low = data['low'].iloc[current_idx]
            current_close = data['close'].iloc[current_idx]

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
                if current_high >= stop_loss:
                    trade_result.update({
                        'exit_time': data.index[current_idx],
                        'exit_price': stop_loss,
                        'exit_reason': 'stop_loss',
                        'pnl': entry_price - stop_loss,
                        'pnl_percent': (entry_price - stop_loss) / entry_price * 100,
                        'holding_period': i
                    })
                    break
                elif current_low <= take_profit:
                    trade_result.update({
                        'exit_time': data.index[current_idx],
                        'exit_price': take_profit,
                        'exit_reason': 'take_profit',
                        'pnl': entry_price - take_profit,
                        'pnl_percent': (entry_price - take_profit) / entry_price * 100,
                        'holding_period': i
                    })
                    break

        # If no exit found, close at end of look-ahead
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

    def run_multi_period_backtest(self):
        """Run comprehensive backtest across multiple periods."""

        print("🧬 Quantum Fusion Strategy - Multi-Period Backtesting")
        print("=" * 70)

        periods = self.define_test_periods()
        pairs = ['BTC-USD', 'ETH-USD']
        timeframes = ['1d', '4h']  # Focus on daily and 4h for comprehensive testing

        all_results = []
        period_summaries = {}

        for period_name, period_config in periods.items():
            print(f"\n📅 Testing Period: {period_config['description']}")
            print(f"   Market Regime: {period_config['market_regime']}")
            print("-" * 50)

            period_results = []
            period_summary = {
                'period': period_name,
                'description': period_config['description'],
                'regime': period_config['market_regime'],
                'total_trades': 0,
                'successful_tests': 0,
                'avg_win_rate': [],
                'avg_return': [],
                'avg_sharpe': []
            }

            for pair in pairs:
                for timeframe in timeframes:
                    result = self.simulate_period_trades(
                        self.fetch_period_data(pair, period_config, timeframe),
                        pair, timeframe, period_name
                    )

                    if 'error' not in result:
                        period_results.append(result)
                        period_summary['successful_tests'] += 1
                        period_summary['total_trades'] += result['total_trades']
                        period_summary['avg_win_rate'].append(result['win_rate'])
                        period_summary['avg_return'].append(result['total_return_percent'])
                        period_summary['avg_sharpe'].append(result['sharpe_ratio'])

                        print(f"   {pair} {timeframe}: {result['total_trades']} trades, "
                              f"Win Rate: {result['win_rate']:.1%}, Return: {result['total_return_percent']:.1f}%")

                        all_results.append(result)
                    else:
                        print(f"   {pair} {timeframe}: ❌ {result['error']}")

            # Calculate period summary
            if period_summary['successful_tests'] > 0:
                period_summary.update({
                    'avg_win_rate': round(np.mean(period_summary['avg_win_rate']), 4),
                    'avg_return': round(np.mean(period_summary['avg_return']), 4),
                    'avg_sharpe': round(np.mean(period_summary['avg_sharpe']), 4)
                })

            period_summaries[period_name] = period_summary

        # Overall analysis
        self._analyze_multi_period_results(all_results, period_summaries)

        # Save results
        self._save_multi_period_results(all_results, period_summaries)

    def _analyze_multi_period_results(self, all_results, period_summaries):
        """Analyze results across all periods."""

        print("\n" + "="*70)
        print("📊 MULTI-PERIOD ANALYSIS")
        print("="*70)

        # Overall statistics
        valid_results = [r for r in all_results if r['total_trades'] > 0]

        if valid_results:
            overall_win_rate = np.mean([r['win_rate'] for r in valid_results])
            overall_return = np.mean([r['total_return_percent'] for r in valid_results])
            overall_sharpe = np.mean([r['sharpe_ratio'] for r in valid_results])

            print(f"🎯 Overall Performance Across All Periods:")
            print(f"   • Average Win Rate: {overall_win_rate:.1%}")
            print(f"   • Average Total Return: {overall_return:.1f}%")
            print(f"   • Average Sharpe Ratio: {overall_sharpe:.2f}")
            print(f"   • Total Trades Executed: {sum(r['total_trades'] for r in valid_results)}")

            # Period-by-period analysis
            print(f"\n📅 Period-by-Period Performance:")
            for period_name, summary in period_summaries.items():
                if summary['successful_tests'] > 0:
                    print(f"   • {summary['description']}: {summary['avg_win_rate']:.1%} win rate, "
                          f"{summary['avg_return']:.1f}% return, {summary['total_trades']} trades")

            # Market regime analysis
            regime_performance = {}
            for result in valid_results:
                period_name = result['period']
                regime = period_summaries[period_name]['regime']
                if regime not in regime_performance:
                    regime_performance[regime] = []
                regime_performance[regime].append(result['win_rate'])

            print(f"\n🎭 Market Regime Performance:")
            for regime, win_rates in regime_performance.items():
                avg_win_rate = np.mean(win_rates)
                print(f"   • {regime}: {avg_win_rate:.1%} average win rate")

            # Consistency check
            win_rate_std = np.std([r['win_rate'] for r in valid_results])
            return_std = np.std([r['total_return_percent'] for r in valid_results])

            print(f"\n📈 Strategy Consistency:")
            print(f"   • Win Rate Standard Deviation: {win_rate_std:.3f} ({win_rate_std*100:.1f} percentage points)")
            print(f"   • Return Standard Deviation: {return_std:.1f} percentage points")

            # Validation criteria
            consistency_ok = win_rate_std < 0.15  # Win rate variation < 15%
            performance_ok = overall_win_rate >= 0.55
            return_ok = overall_return >= 5.0

            print(f"\n✅ VALIDATION CHECKS:")
            print(f"   • Performance ≥55% Win Rate: {'✅' if performance_ok else '❌'} ({overall_win_rate:.1%})")
            print(f"   • Return ≥5% Average: {'✅' if return_ok else '❌'} ({overall_return:.1f}%)")
            print(f"   • Consistency (Win Rate Std <15%): {'✅' if consistency_ok else '❌'} ({win_rate_std:.3f})")

            all_checks_pass = performance_ok and return_ok and consistency_ok

            print(f"\n🏆 MULTI-PERIOD VALIDATION: {'✅ PASSED' if all_checks_pass else '❌ FAILED'}")

            if all_checks_pass:
                print("   🎉 Strategy shows consistent performance across different market regimes!")
                print("   📈 Ready for production deployment with confidence!")
            else:
                print("   ⚠️ Strategy performance varies significantly across periods.")

        else:
            print("❌ No valid results generated across any period")

    def _save_multi_period_results(self, all_results, period_summaries):
        """Save multi-period backtest results."""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"quantum_fusion_multi_period_backtest_{timestamp}.json"

        results_data = {
            'summary': {
                'total_periods_tested': len(period_summaries),
                'total_combinations': len(all_results),
                'successful_tests': len([r for r in all_results if r['total_trades'] > 0]),
                'timestamp': timestamp
            },
            'period_summaries': period_summaries,
            'detailed_results': all_results
        }

        import json
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)

        print(f"\n💾 Multi-period backtest results saved to: {filename}")


if __name__ == "__main__":
    backtester = MultiPeriodBacktester(initial_capital=10000.0)
    backtester.run_multi_period_backtest()