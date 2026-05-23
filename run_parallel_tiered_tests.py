#!/usr/bin/env python3
"""
Parallel Tiered Backtest Runner

Runs multiple workers in parallel to test strategies through Tier 1 and Tier 2 gates.
Adds passing strategies to battleground for forward test tracking.

Usage:
    python run_parallel_tiered_tests.py --workers 4
    python run_parallel_tiered_tests.py --quick  # Test subset only
"""

import sys
import os
import argparse
import multiprocessing as mp
from pathlib import Path
from typing import Dict, List, Any
import json
import time
from datetime import datetime, timezone

# Add project root
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from incubator.testing import (
    run_tier1_backtest, 
    run_tier2_backtest,
    check_pass_criteria,
    get_all_pairs,
    claim_strategy,
    release_claim,
    load_data
)

# Strategy directories
STRATEGY_DIRS = [
    ('baby_strategies', 'baby'),
    ('incubator/agents/codex_gpt5', 'codex'),
    ('incubator/agents/cursor_ai', 'cursor'),
    ('incubator/agents/claude_opus_batch', 'opus'),
    ('incubator/agents/team_alpha', 'alpha'),
    ('incubator/agents/web_ai', 'web'),
]

PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
TIMEFRAMES = ['1h', '4h', '1d']


def discover_strategies(quick_mode: bool = False) -> Dict[str, Dict]:
    """Discover all strategy files"""
    strategies = {}
    
    for dir_path, agent_id in STRATEGY_DIRS:
        dir_full = ROOT / dir_path
        if not dir_full.exists():
            continue
            
        for py_file in dir_full.glob('*.py'):
            if py_file.name.startswith('_') or py_file.name == '__init__.py':
                continue
                
            strategy_name = py_file.stem
            strategies[strategy_name] = {
                'file': py_file,
                'agent_id': agent_id,
                'path': str(py_file.relative_to(ROOT))
            }
    
    print(f"[DISCOVER] Found {len(strategies)} strategies")
    
    if quick_mode:
        # Only test a subset for quick validation
        import random
        sample_size = min(20, len(strategies))
        sampled = dict(random.sample(list(strategies.items()), sample_size))
        print(f"[QUICK MODE] Testing {sample_size} random strategies")
        return sampled
    
    return strategies


def load_strategy_class(strategy_info: Dict):
    """Load strategy class from file"""
    try:
        spec = importlib.util.spec_from_file_location(
            f"strategy_{strategy_info['file'].stem}", 
            strategy_info['file']
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find strategy class
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and attr_name.endswith('Strategy'):
                return attr, None
                
        return None, "No Strategy class found"
    except Exception as e:
        return None, str(e)


def test_strategy_worker(args):
    """Worker function for parallel testing"""
    strategy_name, strategy_info, worker_id = args
    
    # Try to claim this strategy
    lock_file = f"battleground/locks/{strategy_name}.lock"
    if os.path.exists(lock_file):
        return None  # Already being processed
    
    # Create lock
    try:
        os.makedirs("battleground/locks", exist_ok=True)
        with open(lock_file, 'w') as f:
            f.write(f"{worker_id}\n{time.time()}")
    except:
        return None
    
    try:
        print(f"[{worker_id}] Testing {strategy_name}...")
        
        # Import here to avoid pickling issues
        import importlib.util
        
        spec = importlib.util.spec_from_file_location(
            f"strat_{strategy_name}", 
            strategy_info['file']
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find strategy class
        strategy_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and attr_name.endswith('Strategy'):
                strategy_class = attr
                break
        
        if not strategy_class:
            return {'name': strategy_name, 'error': 'No Strategy class'}
        
        # Tier 1: Test on BTC/ETH/SOL
        tier1_result = run_tier1_backtest(strategy_class, worker_id)
        
        if not tier1_result.get('passed'):
            return {
                'name': strategy_name,
                'agent_id': strategy_info['agent_id'],
                'tier1_passed': False,
                'tier1_best_sharpe': tier1_result.get('best_result', {}).get('sharpe_ratio', 0),
                'tier1_best_wr': tier1_result.get('best_result', {}).get('win_rate', 0),
                'tier1_best_pair': tier1_result.get('best_result', {}).get('pair', 'N/A')
            }
        
        # Tier 2: Multi-timeframe validation
        best_result = tier1_result['best_result']
        tier2_result = run_tier2_backtest(
            strategy_class,
            best_result['pair'],
            best_result.get('direction', 'LONG'),
            worker_id
        )
        
        return {
            'name': strategy_name,
            'agent_id': strategy_info['agent_id'],
            'tier1_passed': True,
            'tier1_best_sharpe': best_result['sharpe_ratio'],
            'tier1_best_wr': best_result['win_rate'],
            'tier1_best_pair': best_result['pair'],
            'tier1_max_dd': best_result['max_drawdown'],
            'tier1_trades': best_result['trades'],
            'tier2_fully_robust': tier2_result.get('fully_robust', False),
            'tier2_timeframes_passed': tier2_result.get('timeframes_passed', 0),
            'tier2_results': tier2_result.get('timeframe_results', {})
        }
        
    except Exception as e:
        return {'name': strategy_name, 'error': str(e)}
    finally:
        # Release lock
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
        except:
            pass


def run_parallel_tests(workers: int = 4, quick_mode: bool = False):
    """Run parallel tiered tests"""
    strategies = discover_strategies(quick_mode)
    
    if not strategies:
        print("[ERROR] No strategies found")
        return
    
    print(f"[PARALLEL] Starting {workers} workers for {len(strategies)} strategies")
    
    # Prepare work items
    work_items = [
        (name, info, f"worker_{i % workers}")
        for i, (name, info) in enumerate(strategies.items())
    ]
    
    results = []
    tier1_passed = []
    tier2_fully_robust = []
    tier2_partial = []
    
    # Run in parallel
    with mp.Pool(workers) as pool:
        for result in pool.imap_unordered(test_strategy_worker, work_items):
            if result:
                results.append(result)
                
                if result.get('tier1_passed'):
                    tier1_passed.append(result)
                    
                    if result.get('tier2_fully_robust'):
                        tier2_fully_robust.append(result)
                    elif result.get('tier2_timeframes_passed', 0) > 0:
                        tier2_partial.append(result)
    
    # Save results
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    
    results_data = {
        'timestamp': timestamp,
        'total_tested': len(results),
        'tier1_passed': len(tier1_passed),
        'tier2_fully_robust': len(tier2_fully_robust),
        'tier2_partial': len(tier2_partial),
        'tier1_passed_details': tier1_passed,
        'tier2_fully_robust_details': tier2_fully_robust,
        'tier2_partial_details': tier2_partial
    }
    
    output_file = ROOT / 'battleground' / 'data' / f'tiered_results_{timestamp}.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results_data, f, indent=2, default=str)
    
    print(f"\n[RESULTS] Saved to {output_file}")
    print(f"[SUMMARY] Tier 1 Passed: {len(tier1_passed)}")
    print(f"[SUMMARY] Tier 2 Fully Robust: {len(tier2_fully_robust)}")
    print(f"[SUMMARY] Tier 2 Partial: {len(tier2_partial)}")
    
    # Update battleground
    update_battleground(results_data, timestamp)
    
    return results_data


def update_battleground(results: Dict, timestamp: str):
    """Update battleground with new passing strategies"""
    battleground_file = ROOT / 'battleground' / 'data' / 'baby_strats_dashboard.json'
    
    # Load existing
    existing = {}
    if battleground_file.exists():
        try:
            with open(battleground_file, 'r') as f:
                existing = json.load(f)
        except:
            pass
    
    # Add Tier 2 strategies to tracking
    strategies = existing.get('strategies', [])
    existing_names = {s['name'] for s in strategies}
    
    # Add fully robust strategies
    for strat in results.get('tier2_fully_robust_details', []):
        if strat['name'] not in existing_names:
            strategies.append({
                'name': strat['name'],
                'agent_id': strat['agent_id'],
                'status': 'paper_trading',
                'tier': 'tier2_fully_robust',
                'best_pair': strat['tier1_best_pair'],
                'backtest_sharpe': strat['tier1_best_sharpe'],
                'backtest_win_rate': strat['tier1_best_wr'],
                'backtest_max_dd': strat['tier1_max_dd'],
                'added_at': timestamp,
                'forward_sharpe': None,
                'forward_win_rate': None,
                'forward_trades': 0
            })
    
    # Add partial tier 2
    for strat in results.get('tier2_partial_details', []):
        if strat['name'] not in existing_names:
            strategies.append({
                'name': strat['name'],
                'agent_id': strat['agent_id'],
                'status': 'paper_trading',
                'tier': 'tier2_partial',
                'best_pair': strat['tier1_best_pair'],
                'backtest_sharpe': strat['tier1_best_sharpe'],
                'backtest_win_rate': strat['tier1_best_wr'],
                'backtest_max_dd': strat['tier1_max_dd'],
                'added_at': timestamp,
                'forward_sharpe': None,
                'forward_win_rate': None,
                'forward_trades': 0
            })
    
    existing['strategies'] = strategies
    existing['last_updated'] = timestamp
    existing['total_tracked'] = len(strategies)
    
    with open(battleground_file, 'w') as f:
        json.dump(existing, f, indent=2)
    
    print(f"[BATTLEGROUND] Updated with {len(strategies)} strategies")


def main():
    parser = argparse.ArgumentParser(description='Parallel Tiered Backtest Runner')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--quick', action='store_true', help='Quick mode - test subset only')
    args = parser.parse_args()
    
    print("="*60)
    print("PARALLEL TIERED BACKTEST RUNNER")
    print("="*60)
    
    results = run_parallel_tests(args.workers, args.quick)
    
    print("\n" + "="*60)
    print("TOP PERFORMERS (Tier 2 Fully Robust):")
    print("="*60)
    
    for strat in results.get('tier2_fully_robust_details', [])[:10]:
        print(f"  {strat['name'][:40]:<40} | "
              f"Sharpe: {strat['tier1_best_sharpe']:>5.2f} | "
              f"WR: {strat['tier1_best_wr']:>5.1f}% | "
              f"Pair: {strat['tier1_best_pair']}")


if __name__ == "__main__":
    main()
