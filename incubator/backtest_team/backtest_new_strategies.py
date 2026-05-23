#!/usr/bin/env python3
"""
Backtest the 200 new strategies from the downloaded batch.
Tests each strategy and reports which ones pass the Baby Strat criteria.
"""

import sys
import os
import importlib.util
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest_team.runner import generate_synthetic_crypto_data, BacktestRunner


@dataclass
class BacktestResult:
    strategy_name: str
    category: str
    sharpe: float
    win_rate: float
    max_dd: float
    total_return: float
    trades: int
    passed: bool


def load_strategy_from_file(filepath: Path):
    """Load a strategy class from a Python file."""
    try:
        spec = importlib.util.spec_from_file_location(filepath.stem, filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find the strategy class (first class ending with 'Strategy')
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and attr_name.endswith('Strategy') and attr_name != 'Strategy':
                return attr
        return None
    except Exception as e:
        print(f"  Error loading {filepath.name}: {e}")
        return None


def categorize_strategy(filename: str) -> str:
    """Categorize strategy by filename."""
    num = int(filename.split('_')[1])
    if 1 <= num <= 10:
        return "On-Chain"
    elif 11 <= num <= 15:
        return "Multi-Timeframe"
    elif 16 <= num <= 20:
        return "Cross-Asset"
    elif 21 <= num <= 25:
        return "Microstructure"
    elif 26 <= num <= 30:
        return "Session-Based"
    elif 31 <= num <= 35:
        return "Funding"
    elif 36 <= num <= 40:
        return "Volatility"
    elif 41 <= num <= 45:
        return "Machine Learning"
    elif 46 <= num <= 50:
        return "Stat Arb"
    else:
        return "Other"


def run_strategy_backtest(strategy_class, data: pd.DataFrame) -> dict:
    """Run a simple backtest on a strategy."""
    try:
        strategy = strategy_class()
        
        # Generate simple price data for strategies that need it
        prices = data['close'].tolist()
        returns = data['close'].pct_change().fillna(0).tolist()
        
        # Try different method signatures
        signal = None
        try:
            # Try with prices only
            if hasattr(strategy, 'analyze'):
                method = strategy.analyze
                import inspect
                sig = inspect.signature(method)
                params = list(sig.parameters.keys())
                
                if len(params) == 1:
                    signal = method(prices)
                elif 'prices' in params and 'volumes' in params:
                    volumes = data['volume'].tolist()
                    signal = method(prices, volumes)
                elif 'btc_prices' in params and 'spx_prices' in params:
                    # Cross-asset strategy
                    spx_data = generate_synthetic_crypto_data(days=len(data), seed=43)
                    signal = method(prices, spx_data['close'].tolist(), volumes)
                else:
                    # Default to prices only
                    signal = method(prices)
        except Exception as e:
            return {'error': str(e)}
        
        if signal is None:
            return {'error': 'No signal generated'}
            
        # Simulate trades based on signals
        position = 0
        trades = []
        equity = [10000.0]
        
        for i in range(1, len(prices)):
            price = prices[i]
            prev_price = prices[i-1]
            
            # Simple signal-based trading
            if signal.action == "buy" and position <= 0:
                position = 1
                trades.append({'entry': price, 'exit': None, 'type': 'long'})
            elif signal.action == "sell" and position >= 0:
                if position > 0 and trades:
                    trades[-1]['exit'] = price
                position = -1
                trades.append({'entry': price, 'exit': None, 'type': 'short'})
            
            # Update equity
            if position != 0:
                pnl = (price - prev_price) / prev_price * position
                equity.append(equity[-1] * (1 + pnl))
            else:
                equity.append(equity[-1])
        
        # Close final trade
        if trades and trades[-1]['exit'] is None:
            trades[-1]['exit'] = prices[-1]
        
        # Calculate metrics
        equity = np.array(equity)
        returns_pct = np.diff(equity) / equity[:-1]
        
        if len(returns_pct) == 0 or len(trades) == 0:
            return {'error': 'No trades executed'}
        
        # Sharpe ratio
        sharpe = np.mean(returns_pct) / (np.std(returns_pct) + 1e-8) * np.sqrt(365)
        
        # Win rate
        winning_trades = sum(1 for t in trades if t['exit'] and 
                           ((t['type'] == 'long' and t['exit'] > t['entry']) or
                            (t['type'] == 'short' and t['exit'] < t['entry'])))
        win_rate = winning_trades / len(trades) if trades else 0
        
        # Max drawdown
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        max_dd = np.min(drawdown)
        
        # Total return
        total_return = (equity[-1] - equity[0]) / equity[0]
        
        return {
            'sharpe': sharpe,
            'win_rate': win_rate,
            'max_dd': max_dd,
            'total_return': total_return,
            'trades': len(trades),
            'signal_confidence': getattr(signal, 'confidence', 0)
        }
        
    except Exception as e:
        return {'error': str(e)}


def main():
    """Run backtests on all new strategies."""
    print("=" * 80)
    print("BACKTESTING 200 NEW STRATEGIES")
    print("=" * 80)
    
    strategies_dir = Path(__file__).parent.parent / "agents" / "web_ai"
    strategy_files = sorted(strategies_dir.glob("strategy_*.py"))
    
    print(f"Found {len(strategy_files)} new strategies to test\n")
    
    # Generate test data
    data = generate_synthetic_crypto_data(days=180, seed=42)
    
    results = []
    passed_strategies = []
    failed_strategies = []
    
    for i, strategy_file in enumerate(strategy_files, 1):
        strategy_name = strategy_file.stem
        category = categorize_strategy(strategy_name)
        
        print(f"[{i}/{len(strategy_files)}] Testing {strategy_name} ({category})...", end=" ")
        
        # Load strategy
        strategy_class = load_strategy_from_file(strategy_file)
        if strategy_class is None:
            print("LOAD FAILED")
            failed_strategies.append((strategy_name, "Load failed"))
            continue
        
        # Run backtest
        result = run_strategy_backtest(strategy_class, data)
        
        if 'error' in result:
            print(f"ERROR: {result['error'][:50]}")
            failed_strategies.append((strategy_name, result['error']))
            continue
        
        # Check pass criteria
        passed = (result['sharpe'] >= 1.0 and 
                  result['win_rate'] >= 0.45 and 
                  result['max_dd'] >= -0.20)
        
        result_obj = BacktestResult(
            strategy_name=strategy_name,
            category=category,
            sharpe=result['sharpe'],
            win_rate=result['win_rate'],
            max_dd=result['max_dd'],
            total_return=result['total_return'],
            trades=result['trades'],
            passed=passed
        )
        results.append(result_obj)
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | Sharpe: {result['sharpe']:.2f} | WR: {result['win_rate']:.1%} | DD: {result['max_dd']:.1%}")
        
        if passed:
            passed_strategies.append(result_obj)
        else:
            failed_strategies.append((strategy_name, f"Sharpe {result['sharpe']:.2f}, WR {result['win_rate']:.1%}, DD {result['max_dd']:.1%}"))
    
    # Summary
    print("\n" + "=" * 80)
    print("BACKTEST SUMMARY")
    print("=" * 80)
    print(f"Total Strategies: {len(strategy_files)}")
    print(f"Passed: {len(passed_strategies)}")
    print(f"Failed: {len(failed_strategies)}")
    print(f"Pass Rate: {len(passed_strategies)/len(strategy_files)*100:.1f}%")
    
    if passed_strategies:
        print("\n" + "=" * 80)
        print("PASSED STRATEGIES (Ready for Integration)")
        print("=" * 80)
        for r in passed_strategies:
            print(f"  ✅ {r.strategy_name}")
            print(f"     Category: {r.category}")
            print(f"     Sharpe: {r.sharpe:.2f} | Win Rate: {r.win_rate:.1%} | Max DD: {r.max_dd:.1%}")
            print(f"     Return: {r.total_return:.1%} | Trades: {r.trades}")
            print()
    
    # Category breakdown
    print("\n" + "=" * 80)
    print("RESULTS BY CATEGORY")
    print("=" * 80)
    categories = {}
    for r in results:
        if r.category not in categories:
            categories[r.category] = {'total': 0, 'passed': 0}
        categories[r.category]['total'] += 1
        if r.passed:
            categories[r.category]['passed'] += 1
    
    for cat, stats in sorted(categories.items()):
        rate = stats['passed'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"  {cat}: {stats['passed']}/{stats['total']} passed ({rate:.1f}%)")
    
    # Save results
    output_file = Path(__file__).parent / "backtest_results_new_strategies.json"
    import json
    with open(output_file, 'w') as f:
        json.dump([{
            'strategy_name': r.strategy_name,
            'category': r.category,
            'sharpe': r.sharpe,
            'win_rate': r.win_rate,
            'max_dd': r.max_dd,
            'total_return': r.total_return,
            'trades': r.trades,
            'passed': r.passed
        } for r in results], f, indent=2)
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
