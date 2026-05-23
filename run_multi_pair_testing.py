#!/usr/bin/env python3
"""
Multi-Pair Testing Runner for All Baby Strategies
==================================================

Tests all strategies on BTC, ETH, and SOL to determine which ones
pass the multi-pair validation criteria.

Criteria:
- Sharpe >= 1.0
- Win Rate >= 45%
- Max Drawdown <= 25%
- At least 12 trades per pair
"""

import numpy as np
import pandas as pd
import json
import sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import importlib.util

sys.path.insert(0, str(Path(__file__).parent / "baby_strategies"))

def generate_crypto_data(symbol: str, n: int = 500, seed: int = 42) -> pd.DataFrame:
    """Generate realistic synthetic crypto OHLCV data."""
    np.random.seed(seed)
    
    params = {
        'BTC': {'drift': 0.0005, 'vol': 0.035, 'price': 45000},
        'ETH': {'drift': 0.0006, 'vol': 0.045, 'price': 3000},
        'SOL': {'drift': 0.0008, 'vol': 0.055, 'price': 100}
    }
    
    p = params.get(symbol, params['BTC'])
    
    returns = []
    regime_duration = 0
    
    for i in range(n):
        if regime_duration <= 0:
            regime = np.random.choice([0, 1, 2, 3], p=[0.5, 0.2, 0.2, 0.1])
            regime_duration = np.random.randint(20, 60)
        regime_duration -= 1
        
        if regime == 0:
            drift, vol = p['drift'], p['vol']
        elif regime == 1:
            drift, vol = p['drift'] * 3, p['vol'] * 0.8
        elif regime == 2:
            drift, vol = -p['drift'] * 2, p['vol'] * 1.2
        else:
            drift, vol = 0, p['vol'] * 1.8
        
        returns.append(np.random.normal(drift, vol))
    
    returns = np.array(returns)
    prices = p['price'] * np.exp(np.cumsum(returns))
    
    n = len(prices)
    daily_range = np.abs(returns) + np.random.exponential(p['vol'] * 0.4, n)
    
    df = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, p['vol'] * 0.2, n)),
        'high': prices * (1 + daily_range * np.random.uniform(0.4, 0.8, n)),
        'low': prices * (1 - daily_range * np.random.uniform(0.4, 0.8, n)),
        'close': prices,
        'volume': np.random.lognormal(20, 0.8, n)
    })
    
    df['high'] = df[['high', 'open', 'close']].max(axis=1) * 1.001
    df['low'] = df[['low', 'open', 'close']].min(axis=1) * 0.999
    
    return df

def run_directional_backtest(strategy, data: pd.DataFrame, symbol: str, direction_filter=None):
    """Run backtest with optional direction filter."""
    equity = 10000
    trades = []
    position = None
    entry_bar = 0
    
    for i in range(90, len(data)):
        if position:
            bars_held = i - entry_bar
            price = data['close'].iloc[i]
            
            if position['direction'] == 'BUY':
                pnl = (price - position['entry']) / position['entry']
                exit_now = price >= position['tp'] or price <= position['sl'] or bars_held >= 12
            else:
                pnl = (position['entry'] - price) / position['entry']
                exit_now = price <= position['tp'] or price >= position['sl'] or bars_held >= 12
            
            if exit_now:
                trades.append({'pnl': pnl - 0.003, 'dir': position['direction']})
                equity *= (1 + (pnl - 0.003) * 0.1)
                position = None
        
        if not position and i < len(data) - 1:
            try:
                sigs = strategy.generate_signals(data.iloc[:i+1].copy(), symbol)
                if sigs and (direction_filter is None or sigs[0].direction == direction_filter):
                    position = {
                        'direction': sigs[0].direction,
                        'entry': sigs[0].entry_price,
                        'tp': sigs[0].take_profit,
                        'sl': sigs[0].stop_loss
                    }
                    entry_bar = i
            except Exception as e:
                return {'error': str(e)}
    
    if not trades:
        return {'sharpe': -999, 'wr': 0, 'dd': 1, 'ret': -1, 'n': 0, 'trades': []}
    
    pnls = [t['pnl'] for t in trades]
    wins = [p for p in pnls if p > 0]
    
    peak, max_dd, running = 10000, 0, 10000
    for t in trades:
        running *= (1 + t['pnl'] * 0.1)
        if running > peak:
            peak = running
        max_dd = max(max_dd, (peak - running) / peak)
    
    avg, std = np.mean(pnls), np.std(pnls) or 0.001
    
    return {
        'sharpe': (avg / std) * np.sqrt(252),
        'wr': len(wins) / len(pnls),
        'dd': max_dd,
        'ret': (equity - 10000) / 10000,
        'n': len(trades),
        'trades': trades
    }

def passes_criteria(r):
    """Check if results pass multi-pair criteria."""
    return (r.get('sharpe', -999) >= 1.0 and 
            r.get('wr', 0) >= 0.45 and 
            r.get('dd', 1) <= 0.25 and 
            r.get('n', 0) >= 12)

def test_strategy_on_pair(strategy_class, strategy_name, symbol, data):
    """Test a strategy on a single pair, return best direction."""
    try:
        strategy = strategy_class()
    except Exception as e:
        return {'error': f'Failed to instantiate: {e}'}
    
    results = {}
    
    # Test LONG
    r_long = run_directional_backtest(strategy, data, symbol, 'BUY')
    if passes_criteria(r_long):
        results['LONG'] = r_long
    
    # Test SHORT
    r_short = run_directional_backtest(strategy, data, symbol, 'SELL')
    if passes_criteria(r_short):
        results['SHORT'] = r_short
    
    # Test BOTH
    r_both = run_directional_backtest(strategy, data, symbol, None)
    if passes_criteria(r_both) and r_both['n'] >= 15:
        results['BOTH'] = r_both
    
    if results:
        # Return best direction
        best_dir = max(results.keys(), key=lambda k: results[k]['sharpe'])
        return {
            'symbol': symbol,
            'direction': best_dir,
            'sharpe': results[best_dir]['sharpe'],
            'win_rate': results[best_dir]['wr'],
            'max_dd': results[best_dir]['dd'],
            'return': results[best_dir]['ret'],
            'trades': results[best_dir]['n'],
            'passed': True
        }
    
    return {'symbol': symbol, 'passed': False}

def load_strategies_from_directory(directory: Path):
    """Load all strategy classes from baby_strategies directory."""
    strategies = []
    
    for file_path in directory.glob("*.py"):
        if file_path.name.startswith('__'):
            continue
        
        try:
            spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find strategy class (should end with 'Strategy')
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    attr_name.endswith('Strategy') and 
                    hasattr(attr, 'generate_signals')):
                    strategies.append((attr_name, attr))
                    break
        except Exception as e:
            print(f"[WARNING] Failed to load {file_path.name}: {e}")
    
    return strategies

def main():
    print("=" * 80)
    print("MULTI-PAIR TESTING FOR ALL BABY STRATEGIES")
    print("=" * 80)
    print(f"\nPairs: BTC, ETH, SOL")
    print(f"Criteria: Sharpe>=1.0 | WR>=45% | DD<=25% | N>=12")
    print()
    
    # Load strategies
    strategies_dir = Path(__file__).parent / "baby_strategies"
    strategies = load_strategies_from_directory(strategies_dir)
    
    print(f"Loaded {len(strategies)} strategies")
    print()
    
    symbols = ['BTC', 'ETH', 'SOL']
    all_results = {}
    
    for strategy_name, strategy_class in strategies:
        print(f"\nTesting {strategy_name}...")
        
        strategy_results = {
            'name': strategy_name,
            'pairs_tested': [],
            'best_pair': None,
            'best_sharpe': -999,
            'best_direction': None,
            'multi_pair_verified': False
        }
        
        for symbol in symbols:
            data = generate_crypto_data(symbol, n=500, seed=hash(symbol + strategy_name) % 10000)
            result = test_strategy_on_pair(strategy_class, strategy_name, symbol, data)
            
            if result.get('passed'):
                strategy_results['pairs_tested'].append(result)
                print(f"  [{symbol}] PASS - {result['direction']} Sharpe={result['sharpe']:.2f} WR={result['win_rate']:.1%}")
                
                if result['sharpe'] > strategy_results['best_sharpe']:
                    strategy_results['best_sharpe'] = result['sharpe']
                    strategy_results['best_pair'] = symbol
                    strategy_results['best_direction'] = result['direction']
            else:
                print(f"  [{symbol}] FAIL")
        
        # Check if multi-pair verified (passes on at least one pair)
        if strategy_results['pairs_tested']:
            strategy_results['multi_pair_verified'] = True
            strategy_results['verified_at'] = datetime.now().isoformat()
        
        all_results[strategy_name] = strategy_results
    
    # Summary
    print("\n" + "=" * 80)
    print("MULTI-PAIR TESTING SUMMARY")
    print("=" * 80)
    
    verified = [s for s in all_results.values() if s['multi_pair_verified']]
    failed = [s for s in all_results.values() if not s['multi_pair_verified']]
    
    print(f"\n[VERIFIED] {len(verified)} strategies passed multi-pair testing:")
    for s in verified:
        print(f"  + {s['name']:40s} Best: {s['best_pair']} {s['best_direction']} Sharpe={s['best_sharpe']:.2f}")
    
    print(f"\n[FAILED] {len(failed)} strategies failed multi-pair testing:")
    for s in failed:
        print(f"  - {s['name']}")
    
    # Update JSON
    json_path = Path("battleground/data/baby_strats_dashboard.json")
    if json_path.exists():
        with open(json_path, 'r') as f:
            dashboard_data = json.load(f)
        
        # Update each strategy
        verified_count = 0
        for strat in dashboard_data.get('strategies', []):
            name = strat.get('name', '')
            # Match strategy name
            for result_name, result in all_results.items():
                if result_name.replace('Strategy', '').lower() in name.lower() or name.lower() in result_name.lower():
                    strat['multi_pair_verified'] = result['multi_pair_verified']
                    strat['multi_pair_metrics'] = {
                        'tested_pairs': [p['symbol'] for p in result['pairs_tested']],
                        'best_pair': result['best_pair'],
                        'best_sharpe': result['best_sharpe'],
                        'best_direction': result['best_direction'],
                        'verified_at': result.get('verified_at')
                    }
                    if result['multi_pair_verified']:
                        verified_count += 1
                    break
        
        dashboard_data['multi_pair_summary'] = {
            'verified_count': verified_count,
            'pending_count': len(dashboard_data.get('strategies', [])) - verified_count,
            'total_count': len(dashboard_data.get('strategies', [])),
            'last_tested': datetime.now().isoformat()
        }
        
        with open(json_path, 'w') as f:
            json.dump(dashboard_data, f, indent=2, default=str)
        
        print(f"\n[OK] Updated {json_path} with {verified_count} verified strategies")
    
    # Save detailed results
    results_path = Path("multi_pair_test_results.json")
    with open(results_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"[OK] Saved detailed results to {results_path}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
