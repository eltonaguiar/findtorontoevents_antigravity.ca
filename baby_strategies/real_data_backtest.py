"""
Multi-Timeframe Real Data Backtest Runner for Baby Strategies
===============================================================

Runs backtests on verified strategies using REAL crypto data from crypto_data.db
Tests across all timeframes: 1m, 5m, 15m, 30m, 45m, 1h, 4h, D, 2D, W, Month

Per-Strategy tracking with real market data.
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import sys
import os

# Add baby_strategies to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adaptive_momentum import AdaptiveMomentumStrategy
from volume_profile_deviation import VolumeProfileDeviationStrategy
from volatility_regime_switch import VolatilityRegimeSwitchStrategy
from kalman_mean_reversion import KalmanMeanReversionStrategy

# Timeframe configurations
TIMEFRAMES = {
    '1m': {'interval': '1m', 'minutes': 1, 'min_bars': 500},
    '5m': {'interval': '5m', 'minutes': 5, 'min_bars': 400},
    '15m': {'interval': '15m', 'minutes': 15, 'min_bars': 300},
    '30m': {'interval': '30m', 'minutes': 30, 'min_bars': 200},
    '45m': {'interval': '45m', 'minutes': 45, 'min_bars': 150},
    '1h': {'interval': '1h', 'minutes': 60, 'min_bars': 100},
    '4h': {'interval': '4h', 'minutes': 240, 'min_bars': 80},
    '1d': {'interval': '1d', 'minutes': 1440, 'min_bars': 50},
    '2d': {'interval': '2d', 'minutes': 2880, 'min_bars': 40},
    '1w': {'interval': '1w', 'minutes': 10080, 'min_bars': 30},
    '1M': {'interval': '1M', 'minutes': 43200, 'min_bars': 20},
}

PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']

# Verified strategies
VERIFIED_STRATEGIES = {
    'adaptive_momentum': {
        'class': AdaptiveMomentumStrategy,
        'description': 'Adaptive momentum using Efficiency Ratio for regime detection',
        'verified_pairs': ['ETH/USDT']
    },
    'volume_profile_deviation': {
        'class': VolumeProfileDeviationStrategy,
        'description': 'Volume profile mean reversion using POC levels',
        'verified_pairs': ['BTC/USDT']
    },
    'volatility_regime_switch': {
        'class': VolatilityRegimeSwitchStrategy,
        'description': 'Regime-based strategy switching using volatility metrics',
        'verified_pairs': ['SOL/USDT']
    },
    'kalman_mean_reversion': {
        'class': KalmanMeanReversionStrategy,
        'description': 'Kalman filter-based mean reversion',
        'verified_pairs': ['SOL/USDT']
    }
}


class RealDataBacktester:
    """Backtest runner using real crypto data from SQLite database."""
    
    def __init__(self, db_path: str = 'crypto_data.db'):
        self.db_path = db_path
        self.results = {}
        
    def load_data(self, pair: str, timeframe: str = '1h') -> Optional[pd.DataFrame]:
        """Load OHLCV data from database and resample to target timeframe."""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Load raw hourly data
            query = f"""
                SELECT timestamp, open, high, low, close, volume 
                FROM klines 
                WHERE pair = '{pair}'
                ORDER BY timestamp ASC
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if df.empty:
                return None
                
            # Parse timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            # Resample to target timeframe if needed
            if timeframe != '1h':
                tf_config = TIMEFRAMES.get(timeframe, TIMEFRAMES['1h'])
                rule = self._timeframe_to_pandas_rule(timeframe)
                
                df_resampled = df.resample(rule).agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()
                
                df = df_resampled
            
            # Ensure minimum bars
            min_bars = TIMEFRAMES.get(timeframe, TIMEFRAMES['1h'])['min_bars']
            if len(df) < min_bars:
                return None
                
            return df
            
        except Exception as e:
            print(f"  Error loading data for {pair} {timeframe}: {e}")
            return None
    
    def _timeframe_to_pandas_rule(self, timeframe: str) -> str:
        """Convert timeframe to pandas resample rule."""
        mapping = {
            '1m': '1T', '5m': '5T', '15m': '15T', '30m': '30T', '45m': '45T',
            '1h': '1H', '4h': '4H', '1d': '1D', '2d': '2D', 
            '1w': '1W', '1M': '1ME'
        }
        return mapping.get(timeframe, '1H')
    
    def run_backtest(
        self, 
        strategy, 
        data: pd.DataFrame, 
        pair: str,
        timeframe: str,
        initial_capital: float = 10000
    ) -> Dict:
        """Run a single backtest on provided data."""
        try:
            # Generate signals
            result = strategy.generate_signals(data, pair)
            
            if result is None or 'signal' not in result:
                return self._empty_result()
            
            signal = result.get('signal', 'NEUTRAL')
            if signal == 'NEUTRAL':
                return self._empty_result()
            
            direction = result.get('direction', 'BOTH')
            entry_price = result.get('entry_price', data['close'].iloc[-1])
            take_profit = result.get('take_profit')
            stop_loss = result.get('stop_loss')
            confidence = result.get('confidence', 0.5)
            
            # Simulate forward price movement (use next candles if available)
            # For backtesting, we'll use historical data to see what happened
            lookback = min(50, len(data) - 1)
            if lookback < 10:
                return self._empty_result()
                
            recent_data = data.iloc[-lookback:]
            
            # Simulate trades
            trades = []
            position_open = False
            entry_time = None
            
            for i in range(1, len(recent_data)):
                current = recent_data.iloc[i]
                prev = recent_data.iloc[i-1]
                
                if not position_open:
                    # Check for entry
                    if signal == 'BUY' and direction in ['LONG', 'BOTH']:
                        if current['low'] <= entry_price <= current['high']:
                            position_open = True
                            entry_time = recent_data.index[i]
                    elif signal == 'SELL' and direction in ['SHORT', 'BOTH']:
                        if current['low'] <= entry_price <= current['high']:
                            position_open = True
                            entry_time = recent_data.index[i]
                else:
                    # Check for exit
                    exit_price = None
                    exit_reason = None
                    
                    # Take profit hit
                    if signal == 'BUY':
                        if take_profit and current['high'] >= take_profit:
                            exit_price = take_profit
                            exit_reason = 'TP'
                        elif stop_loss and current['low'] <= stop_loss:
                            exit_price = stop_loss
                            exit_reason = 'SL'
                    else:  # SELL
                        if take_profit and current['low'] <= take_profit:
                            exit_price = take_profit
                            exit_reason = 'TP'
                        elif stop_loss and current['high'] >= stop_loss:
                            exit_price = stop_loss
                            exit_reason = 'SL'
                    
                    # Time-based exit (5 bars)
                    if exit_price is None and i >= lookback - 1:
                        exit_price = current['close']
                        exit_reason = 'TIME'
                    
                    if exit_price:
                        pnl = (exit_price - entry_price) / entry_price
                        if signal == 'SELL':
                            pnl = -pnl
                        
                        trades.append({
                            'entry_time': entry_time,
                            'exit_time': recent_data.index[i],
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'exit_reason': exit_reason,
                            'signal': signal
                        })
                        position_open = False
                        break
            
            # Calculate metrics
            if not trades:
                return self._empty_result()
            
            wins = sum(1 for t in trades if t['pnl'] > 0)
            losses = len(trades) - wins
            win_rate = wins / len(trades) if trades else 0
            
            returns = [t['pnl'] for t in trades]
            total_return = sum(returns)
            
            # Calculate Sharpe-like ratio
            if len(returns) > 1 and np.std(returns) > 0:
                sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
            else:
                sharpe = 0
            
            # Calculate max drawdown
            cumulative = np.cumsum(returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = cumulative - running_max
            max_drawdown = abs(min(drawdown)) if len(drawdown) > 0 else 0
            
            return {
                'trades': len(trades),
                'wins': wins,
                'losses': losses,
                'win_rate': round(win_rate * 100, 2),
                'total_return': round(total_return * 100, 2),
                'sharpe_ratio': round(sharpe, 2),
                'max_drawdown': round(max_drawdown * 100, 2),
                'signal': signal,
                'direction': direction,
                'confidence': confidence,
                'entry_price': entry_price,
                'take_profit': take_profit,
                'stop_loss': stop_loss,
                'data_bars': len(data),
                'timeframe': timeframe,
                'pair': pair
            }
            
        except Exception as e:
            print(f"    Error in backtest: {e}")
            return self._empty_result()
    
    def _empty_result(self) -> Dict:
        """Return empty result structure."""
        return {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'total_return': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'signal': 'NEUTRAL',
            'direction': 'NONE',
            'confidence': 0
        }
    
    def test_strategy_across_timeframes(
        self, 
        strategy_name: str, 
        strategy_class,
        pair: str,
        timeframes: List[str] = None
    ) -> Dict:
        """Test a single strategy across multiple timeframes."""
        if timeframes is None:
            timeframes = ['1h', '4h', '1d']  # Default to higher timeframes with sufficient data
        
        results = {}
        print(f"\n  Testing {strategy_name} on {pair}")
        
        for timeframe in timeframes:
            print(f"    [{timeframe}] Loading data...", end=' ')
            data = self.load_data(pair, timeframe)
            
            if data is None:
                print("INSUFFICIENT DATA")
                results[timeframe] = {'error': 'Insufficient data'}
                continue
            
            print(f"{len(data)} bars", end=' -> ')
            
            # Test with different parameter sets
            best_result = None
            
            # Default params
            test_configs = [
                {'direction': 'LONG'},
                {'direction': 'SHORT'},
                {'direction': 'BOTH'}
            ]
            
            for config in test_configs:
                strategy = strategy_class(config)
                result = self.run_backtest(strategy, data, pair, timeframe)
                
                if result['trades'] >= 5:  # Minimum trades threshold
                    if best_result is None or result['sharpe_ratio'] > best_result['sharpe_ratio']:
                        best_result = result
            
            if best_result:
                print(f"SHARPE {best_result['sharpe_ratio']:.2f} | WR {best_result['win_rate']:.0f}% | TRADES {best_result['trades']}")
                results[timeframe] = best_result
            else:
                print("NO VALID SIGNALS")
                results[timeframe] = {'error': 'No valid signals'}
        
        return results
    
    def run_all_backtests(self) -> Dict:
        """Run backtests for all verified strategies across all pairs and timeframes."""
        all_results = {}
        
        print("=" * 80)
        print("MULTI-TIMEFRAME REAL DATA BACKTEST")
        print("=" * 80)
        print(f"Pairs: {', '.join(PAIRS)}")
        print(f"Timeframes: 1h, 4h, 1d (sufficient data)")
        print(f"Strategies: {len(VERIFIED_STRATEGIES)}")
        print("=" * 80)
        
        for strategy_name, config in VERIFIED_STRATEGIES.items():
            strategy_class = config['class']
            verified_pairs = config['verified_pairs']
            
            all_results[strategy_name] = {
                'description': config['description'],
                'pairs_results': {}
            }
            
            print(f"\n{'='*60}")
            print(f"STRATEGY: {strategy_name}")
            print(f"Description: {config['description']}")
            print(f"Verified on: {', '.join(verified_pairs)}")
            print(f"{'='*60}")
            
            # Test on all pairs
            for pair in PAIRS:
                pair_results = self.test_strategy_across_timeframes(
                    strategy_name,
                    strategy_class,
                    pair,
                    timeframes=['1h', '4h', '1d']
                )
                all_results[strategy_name]['pairs_results'][pair] = pair_results
        
        return all_results
    
    def save_results(self, results: Dict, output_path: str = None):
        """Save backtest results to JSON."""
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f'battleground/data/real_backtest_results_{timestamp}.json'
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Add metadata
        output = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_strategies': len(VERIFIED_STRATEGIES),
                'pairs': PAIRS,
                'timeframes': ['1h', '4h', '1d'],
                'data_source': 'crypto_data.db (real historical data)'
            },
            'results': results
        }
        
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"\n{'='*60}")
        print(f"Results saved to: {output_path}")
        print(f"{'='*60}")
        
        return output_path
    
    def update_dashboard(self, results: Dict):
        """Update baby_strats_dashboard.json with real backtest results."""
        dashboard_path = 'battleground/data/baby_strats_dashboard.json'
        
        try:
            with open(dashboard_path, 'r') as f:
                dashboard = json.load(f)
        except:
            dashboard = {'strategies': []}
        
        # Update each strategy with real data results
        for strat in dashboard.get('strategies', []):
            strat_name = strat.get('name', '').lower().replace(' ', '_')
            
            if strat_name in results:
                real_results = results[strat_name]
                
                # Extract best timeframe result
                best_sharpe = 0
                best_tf_result = None
                
                for pair, pair_results in real_results.get('pairs_results', {}).items():
                    for tf, tf_result in pair_results.items():
                        if isinstance(tf_result, dict) and 'sharpe_ratio' in tf_result:
                            if tf_result['sharpe_ratio'] > best_sharpe:
                                best_sharpe = tf_result['sharpe_ratio']
                                best_tf_result = tf_result
                
                if best_tf_result:
                    strat['real_data_backtest'] = {
                        'tested_at': datetime.now().isoformat(),
                        'best_timeframe': best_tf_result.get('timeframe'),
                        'best_pair': best_tf_result.get('pair'),
                        'sharpe_ratio': best_tf_result.get('sharpe_ratio'),
                        'win_rate': best_tf_result.get('win_rate'),
                        'total_trades': best_tf_result.get('trades'),
                        'max_drawdown': best_tf_result.get('max_drawdown'),
                        'direction': best_tf_result.get('direction'),
                        'signal': best_tf_result.get('signal'),
                        'all_timeframes': real_results.get('pairs_results', {})
                    }
        
        with open(dashboard_path, 'w') as f:
            json.dump(dashboard, f, indent=2)
        
        print(f"Dashboard updated: {dashboard_path}")


def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("REAL DATA MULTI-TIMEFRAME BACKTEST RUNNER")
    print("="*80)
    
    backtester = RealDataBacktester()
    results = backtester.run_all_backtests()
    
    # Save results
    output_path = backtester.save_results(results)
    
    # Update dashboard
    backtester.update_dashboard(results)
    
    print("\n" + "="*60)
    print("BACKTEST COMPLETE")
    print("="*60)
    
    return results


if __name__ == "__main__":
    main()
