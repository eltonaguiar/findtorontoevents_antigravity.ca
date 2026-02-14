#!/usr/bin/env python3
"""
================================================================================
EXTREME Signal System - Backtest Runner
================================================================================

Runs walk-forward backtests for the high-conviction signal system.
Validates performance against swarm research expectations.

Usage:
    python backtest.py --asset BTC --data-path data/BTC_daily.csv \
                       --config configs/extreme_signals.json \
                       --output backtest_results/BTC_backtest.json
================================================================================
"""

import argparse
import json
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from high_conviction_signals import HighConvictionSystem, ConvictionLevel


def load_data(data_path: str) -> pd.DataFrame:
    """Load and validate price data"""
    df = pd.read_csv(data_path)
    
    # Ensure required columns exist
    required = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    df.set_index('timestamp', inplace=True)
    
    return df


def run_walk_forward_backtest(
    asset: str,
    data: pd.DataFrame,
    train_size: int = 90,  # 90 days training
    test_size: int = 30,   # 30 days testing
    initial_capital: float = 10000.0
) -> dict:
    """
    Run walk-forward backtest
    
    This prevents look-ahead bias by only using past data for training
    """
    system = HighConvictionSystem()
    
    results = {
        'asset': asset,
        'start_date': data.index[0].isoformat(),
        'end_date': data.index[-1].isoformat(),
        'initial_capital': initial_capital,
        'trades': [],
        'equity_curve': [initial_capital],
        'signals': []
    }
    
    equity = initial_capital
    position = None
    
    # Walk forward
    for i in range(train_size, len(data) - test_size, test_size):
        train_data = data.iloc[i-train_size:i]
        test_data = data.iloc[i:i+test_size]
        
        # Generate signals for test period
        for j in range(len(test_data)):
            current_data = data.iloc[:i+j]
            
            if len(current_data) < train_size:
                continue
            
            # Generate signal
            signal = system.analyze(asset, current_data)
            
            if signal and signal.conviction == ConvictionLevel.EXTREME:
                # Record signal
                signal_record = {
                    'timestamp': signal.timestamp.isoformat(),
                    'entry_price': signal.entry_price,
                    'stop_loss': signal.stop_loss,
                    'take_profit_1': signal.take_profit_1,
                    'take_profit_2': signal.take_profit_2,
                    'take_profit_3': signal.take_profit_3,
                    'position_size': signal.position_size,
                    'conviction_score': signal.composite_score,
                    'model_agreement': signal.model_agreement_score
                }
                results['signals'].append(signal_record)
                
                # Simulate trade (simplified)
                if position is None:
                    # Enter position
                    position = {
                        'entry_price': test_data.iloc[j]['close'],
                        'size': signal.position_size * equity,
                        'stop': signal.stop_loss,
                        'tp1': signal.take_profit_1,
                        'tp2': signal.take_profit_2,
                        'tp3': signal.take_profit_3,
                        'entry_time': test_data.index[j]
                    }
            
            # Check existing position
            if position:
                current_price = test_data.iloc[j]['close']
                
                # Check stop loss
                if current_price <= position['stop']:
                    pnl = (position['stop'] - position['entry_price']) / position['entry_price']
                    trade_pnl = pnl * position['size']
                    equity += trade_pnl
                    
                    results['trades'].append({
                        'entry_time': position['entry_time'].isoformat(),
                        'exit_time': test_data.index[j].isoformat(),
                        'entry_price': position['entry_price'],
                        'exit_price': position['stop'],
                        'pnl_pct': pnl * 100,
                        'pnl_amount': trade_pnl,
                        'result': 'STOP_LOSS',
                        'hold_days': (test_data.index[j] - position['entry_time']).days
                    })
                    position = None
                
                # Check take profit 1
                elif current_price >= position['tp1']:
                    pnl = (position['tp1'] - position['entry_price']) / position['entry_price']
                    # Close 40% at TP1
                    trade_pnl = pnl * position['size'] * 0.4
                    equity += trade_pnl
                    position['size'] *= 0.6  # Remaining 60%
                    position['tp1'] = None  # Don't check again
                    
                    results['trades'].append({
                        'entry_time': position['entry_time'].isoformat(),
                        'exit_time': test_data.index[j].isoformat(),
                        'entry_price': position['entry_price'],
                        'exit_price': position['tp1'],
                        'pnl_pct': pnl * 100,
                        'pnl_amount': trade_pnl,
                        'result': 'TP1_PARTIAL',
                        'hold_days': (test_data.index[j] - position['entry_time']).days
                    })
        
        results['equity_curve'].append(equity)
    
    # Calculate metrics
    results['metrics'] = calculate_metrics(results['trades'], results['equity_curve'], initial_capital)
    
    return results


def calculate_metrics(trades: list, equity_curve: list, initial_capital: float) -> dict:
    """Calculate performance metrics"""
    if not trades:
        return {'status': 'No trades generated'}
    
    # Basic metrics
    total_trades = len(trades)
    winning_trades = [t for t in trades if t['pnl_amount'] > 0]
    losing_trades = [t for t in trades if t['pnl_amount'] <= 0]
    
    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
    
    # Returns
    total_return = (equity_curve[-1] - initial_capital) / initial_capital
    
    # Profit factor
    gross_profit = sum(t['pnl_amount'] for t in winning_trades) if winning_trades else 0
    gross_loss = abs(sum(t['pnl_amount'] for t in losing_trades)) if losing_trades else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    
    # Sharpe ratio (simplified)
    equity_returns = np.diff(equity_curve) / equity_curve[:-1]
    if len(equity_returns) > 1 and np.std(equity_returns) > 0:
        sharpe = np.mean(equity_returns) / np.std(equity_returns) * np.sqrt(365)
    else:
        sharpe = 0
    
    # Max drawdown
    peak = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - peak) / peak
    max_dd = np.min(drawdown) if len(drawdown) > 0 else 0
    
    # Average hold time
    avg_hold = np.mean([t['hold_days'] for t in trades]) if trades else 0
    
    return {
        'total_trades': total_trades,
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'win_rate': round(win_rate, 4),
        'total_return_pct': round(total_return * 100, 2),
        'profit_factor': round(profit_factor, 2),
        'sharpe_ratio': round(sharpe, 2),
        'max_drawdown_pct': round(max_dd * 100, 2),
        'avg_hold_days': round(avg_hold, 1),
        'final_equity': round(equity_curve[-1], 2)
    }


def compare_to_swarm_expectations(metrics: dict) -> dict:
    """Compare our results to swarm research expectations"""
    comparison = {
        'sharpe': {
            'ours': metrics.get('sharpe_ratio', 0),
            'swarm_expected': '1.0-1.5',
            'status': 'EXCEED' if metrics.get('sharpe_ratio', 0) > 1.5 else 'MEET' if metrics.get('sharpe_ratio', 0) >= 1.0 else 'BELOW'
        },
        'win_rate': {
            'ours': metrics.get('win_rate', 0) * 100,
            'swarm_expected': '60-70%',
            'status': 'EXCEED' if metrics.get('win_rate', 0) > 0.70 else 'MEET' if metrics.get('win_rate', 0) >= 0.60 else 'BELOW'
        },
        'max_dd': {
            'ours': abs(metrics.get('max_drawdown_pct', 0)),
            'swarm_expected': '15-20%',
            'status': 'EXCEED' if abs(metrics.get('max_drawdown_pct', 0)) < 15 else 'MEET' if abs(metrics.get('max_drawdown_pct', 0)) <= 20 else 'BELOW'
        }
    }
    return comparison


def main():
    parser = argparse.ArgumentParser(description='Run backtest for EXTREME signal system')
    parser.add_argument('--asset', required=True, help='Asset symbol (BTC, ETH, etc.)')
    parser.add_argument('--data-path', required=True, help='Path to price data CSV')
    parser.add_argument('--config', default='configs/extreme_signals.json', help='Config file path')
    parser.add_argument('--output', required=True, help='Output JSON file path')
    parser.add_argument('--initial-capital', type=float, default=10000.0, help='Starting capital')
    
    args = parser.parse_args()
    
    print(f"Running backtest for {args.asset}...")
    print(f"Data: {args.data_path}")
    
    # Load data
    data = load_data(args.data_path)
    print(f"Loaded {len(data)} days of data from {data.index[0]} to {data.index[-1]}")
    
    # Run backtest
    results = run_walk_forward_backtest(
        asset=args.asset,
        data=data,
        initial_capital=args.initial_capital
    )
    
    # Compare to swarm expectations
    results['swarm_comparison'] = compare_to_swarm_expectations(results['metrics'])
    
    # Save results
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print(f"BACKTEST RESULTS: {args.asset}")
    print("="*60)
    
    metrics = results['metrics']
    print(f"Total Trades: {metrics.get('total_trades', 0)}")
    print(f"Win Rate: {metrics.get('win_rate', 0)*100:.1f}%")
    print(f"Total Return: {metrics.get('total_return_pct', 0):+.2f}%")
    print(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
    print(f"Max Drawdown: {metrics.get('max_drawdown_pct', 0):.2f}%")
    print(f"Profit Factor: {metrics.get('profit_factor', 0):.2f}")
    
    print("\nComparison to Swarm Research:")
    for metric, vals in results['swarm_comparison'].items():
        print(f"  {metric}: {vals['ours']} vs {vals['swarm_expected']} → {vals['status']}")
    
    print(f"\nResults saved to: {args.output}")


if __name__ == '__main__':
    main()
