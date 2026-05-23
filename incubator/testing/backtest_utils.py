"""
Backtest Utilities - Standardized Testing Functions
====================================================

Use these functions for all strategy testing. Do not create custom testing code.

Functions:
- run_tier1_backtest: Test strategy on BTC/ETH/SOL (Tier 1)
- run_tier2_backtest: Test strategy on multiple timeframes (Tier 2)
- run_full_backtest: Test on all 14 pairs for asset-specific discovery
- check_pass_criteria: Verify if results meet pass thresholds
- load_data: Load OHLCV data from database
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import json
import os

# Standard pairs and timeframes
TIER_1_PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
ALL_PAIRS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT',
    'ALGO/USDT', 'APE/USDT', 'ARB/USDT', 'DOGE/USDT', 'DOT/USDT',
    'DYDX/USDT', 'FET/USDT', 'INJ/USDT', 'SHIB/USDT', 'TRX/USDT', 'XRP/USDT'
]
TIMEFRAMES = ['1h', '4h', '1d']

# Pass criteria for all tests
PASS_CRITERIA = {
    'min_sharpe': 1.0,
    'min_win_rate': 45.0,
    'max_drawdown': 25.0,
    'min_trades': 12
}

# Timeframe resample rules
TIMEFRAME_CONFIGS = {
    '1h': {'rule': '1h', 'description': '1 Hour'},
    '4h': {'rule': '4h', 'description': '4 Hour'},
    '1d': {'rule': '1D', 'description': 'Daily'},
}

# Data cache for performance
_data_cache = {}


def get_tier1_pairs() -> List[str]:
    """Get Tier 1 pairs (BTC/ETH/SOL)."""
    return TIER_1_PAIRS.copy()


def get_all_pairs() -> List[str]:
    """Get all 14 available pairs."""
    return ALL_PAIRS.copy()


def get_timeframes() -> List[str]:
    """Get available timeframes."""
    return TIMEFRAMES.copy()


def load_data(pair: str, timeframe: str, db_path: str = 'crypto_data.db') -> Optional[pd.DataFrame]:
    """
    Load OHLCV data from database with caching.
    
    Args:
        pair: Trading pair (e.g., 'BTC/USDT')
        timeframe: Timeframe (e.g., '1h', '4h', '1d')
        db_path: Path to SQLite database
        
    Returns:
        DataFrame with columns [open, high, low, close, volume] or None
    """
    cache_key = f"{pair}_{timeframe}"
    if cache_key in _data_cache:
        return _data_cache[cache_key]
    
    try:
        conn = sqlite3.connect(db_path)
        query = f"SELECT timestamp, open, high, low, close, volume FROM klines WHERE pair = '{pair}' ORDER BY timestamp ASC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return None
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Resample if needed
        if timeframe != '1h':
            config = TIMEFRAME_CONFIGS.get(timeframe, TIMEFRAME_CONFIGS['1h'])
            df = df.resample(config['rule']).agg({
                'open': 'first', 'high': 'max', 'low': 'min',
                'close': 'last', 'volume': 'sum'
            }).dropna()
        
        _data_cache[cache_key] = df
        return df
    except Exception as e:
        print(f"Error loading data for {pair} {timeframe}: {e}")
        return None


def run_single_backtest(
    strategy_class,
    data: pd.DataFrame,
    pair: str,
    direction_param: str = 'BOTH',
    max_signals: int = 30
) -> Dict:
    """
    Run a single backtest on provided data.
    
    Args:
        strategy_class: Strategy class with generate_signals method
        data: OHLCV DataFrame
        pair: Trading pair name
        direction_param: 'LONG', 'SHORT', or 'BOTH'
        max_signals: Maximum signals to test
        
    Returns:
        Dict with backtest results
    """
    try:
        trades = []
        step = max(25, len(data) // max_signals)
        test_points = list(range(100, len(data) - 20, step))[:max_signals]
        
        for i in test_points:
            hist_data = data.iloc[:i]
            future_window = data.iloc[i:min(i+20, len(data))]
            
            try:
                strategy = strategy_class({'direction': direction_param})
                signals = strategy.generate_signals(hist_data, pair.replace('/', ''))
                
                if not signals:
                    continue
                
                signal = signals[-1] if isinstance(signals, list) else signals
                direction = getattr(signal, 'direction', 'NEUTRAL')
                
                if direction not in ['BUY', 'SELL']:
                    continue
                
                entry_price = getattr(signal, 'entry_price', hist_data['close'].iloc[-1])
                take_profit = getattr(signal, 'take_profit', None)
                stop_loss = getattr(signal, 'stop_loss', None)
                
                # Simulate trade
                exit_price = None
                for _, future_bar in future_window.iloc[1:].iterrows():
                    if direction == 'BUY':
                        if take_profit and future_bar['high'] >= take_profit:
                            exit_price = take_profit
                            break
                        elif stop_loss and future_bar['low'] <= stop_loss:
                            exit_price = stop_loss
                            break
                    else:
                        if take_profit and future_bar['low'] <= take_profit:
                            exit_price = take_profit
                            break
                        elif stop_loss and future_bar['high'] >= stop_loss:
                            exit_price = stop_loss
                            break
                
                if exit_price is None:
                    exit_price = future_window.iloc[-1]['close']
                
                if entry_price == 0:
                    continue
                    
                pnl = (exit_price - entry_price) / entry_price
                if direction == 'SELL':
                    pnl = -pnl
                
                trades.append(pnl)
            except:
                continue
        
        if len(trades) < 5:
            return {
                'trades': 0, 'wins': 0, 'losses': 0, 'win_rate': 0,
                'total_return': 0, 'sharpe_ratio': 0, 'max_drawdown': 0,
                'direction': direction_param, 'error': f'Only {len(trades)} trades'
            }
        
        returns = np.array(trades)
        wins = np.sum(returns > 0)
        total = len(returns)
        win_rate = wins / total * 100
        total_return = np.sum(returns) * 100
        
        if np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(52)
        else:
            sharpe = 0
        
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = cumulative - running_max
        max_dd = abs(np.min(drawdowns)) * 100 if len(drawdowns) > 0 else 0
        
        return {
            'trades': int(total),
            'wins': int(wins),
            'losses': int(total - wins),
            'win_rate': round(win_rate, 2),
            'total_return': round(total_return, 2),
            'sharpe_ratio': round(sharpe, 2),
            'max_drawdown': round(max_dd, 2),
            'direction': direction_param
        }
    except Exception as e:
        return {
            'trades': 0, 'wins': 0, 'losses': 0, 'win_rate': 0,
            'total_return': 0, 'sharpe_ratio': 0, 'max_drawdown': 0,
            'direction': direction_param, 'error': str(e)
        }


def check_pass_criteria(result: Dict) -> Tuple[bool, List[str]]:
    """
    Check if backtest result meets pass criteria.
    
    Args:
        result: Backtest result dict
        
    Returns:
        (passed: bool, reasons: list of failure reasons)
    """
    reasons = []
    
    if result.get('trades', 0) < PASS_CRITERIA['min_trades']:
        reasons.append(f"Trades: {result.get('trades', 0)}/{PASS_CRITERIA['min_trades']}")
    
    if result.get('sharpe_ratio', 0) < PASS_CRITERIA['min_sharpe']:
        reasons.append(f"Sharpe: {result.get('sharpe_ratio', 0):.2f}/{PASS_CRITERIA['min_sharpe']}")
    
    if result.get('win_rate', 0) < PASS_CRITERIA['min_win_rate']:
        reasons.append(f"WR: {result.get('win_rate', 0):.0f}%/{PASS_CRITERIA['min_win_rate']}%")
    
    if result.get('max_drawdown', 0) > PASS_CRITERIA['max_drawdown']:
        reasons.append(f"DD: {result.get('max_drawdown', 0):.1f}%/{PASS_CRITERIA['max_drawdown']}%")
    
    return len(reasons) == 0, reasons


def run_tier1_backtest(
    strategy_class,
    worker_id: str = 'worker_1',
    pairs: List[str] = None
) -> Dict:
    """
    Run Tier 1 backtest: Test on BTC/ETH/SOL (or specified pairs).
    
    Args:
        strategy_class: Strategy class with generate_signals method
        worker_id: Worker identifier for logging
        pairs: List of pairs to test (default: TIER_1_PAIRS)
        
    Returns:
        Dict with results for all pairs
    """
    if pairs is None:
        pairs = TIER_1_PAIRS
    
    print(f"[{worker_id}] Tier 1 testing on {len(pairs)} pairs...")
    
    pair_results = {}
    best_result = None
    passed_pairs = []
    
    for pair in pairs:
        data = load_data(pair, '1h')
        if data is None:
            pair_results[pair] = {'error': 'No data available'}
            continue
        
        # Test all directions
        directions = ['LONG', 'SHORT', 'BOTH']
        best_dir = None
        
        for direction in directions:
            result = run_single_backtest(strategy_class, data, pair, direction)
            if result['trades'] > 0:
                passed, reasons = check_pass_criteria(result)
                result['passed'] = passed
                result['fail_reasons'] = reasons
                
                if best_dir is None or result['sharpe_ratio'] > best_dir['sharpe_ratio']:
                    best_dir = result
        
        if best_dir and best_dir['trades'] > 0:
            pair_results[pair] = best_dir
            if best_dir.get('passed'):
                passed_pairs.append(pair)
                if best_result is None or best_dir['sharpe_ratio'] > best_result['sharpe_ratio']:
                    best_result = best_dir
                    best_result['pair'] = pair
    
    tier1_passed = any(p in passed_pairs for p in TIER_1_PAIRS)
    
    return {
        'pair_results': pair_results,
        'best_result': best_result,
        'passed': tier1_passed,
        'passed_pairs': passed_pairs,
        'pairs_passed': len(passed_pairs),
        'total_pairs_tested': len(pairs),
        'worker_id': worker_id
    }


def run_tier2_backtest(
    strategy_class,
    best_pair: str,
    best_direction: str = 'LONG',
    worker_id: str = 'worker_1'
) -> Dict:
    """
    Run Tier 2 backtest: Test on multiple timeframes.
    
    Args:
        strategy_class: Strategy class
        best_pair: Pair that passed Tier 1
        best_direction: Direction that worked best
        worker_id: Worker identifier
        
    Returns:
        Dict with timeframe results
    """
    print(f"[{worker_id}] Tier 2 testing on {best_pair}...")
    
    tf_results = {}
    passed_count = 0
    
    for tf in TIMEFRAMES:
        data = load_data(best_pair, tf)
        if data is None:
            tf_results[tf] = {'error': 'No data'}
            continue
        
        result = run_single_backtest(strategy_class, data, best_pair, best_direction)
        if result['trades'] > 0:
            passed, _ = check_pass_criteria(result)
            result['passed'] = passed
            if passed:
                passed_count += 1
        tf_results[tf] = result
    
    return {
        'timeframe_results': tf_results,
        'best_pair': best_pair,
        'timeframes_passed': passed_count,
        'total_timeframes': len(TIMEFRAMES),
        'fully_robust': passed_count == len(TIMEFRAMES),
        'worker_id': worker_id
    }


def run_full_backtest(
    strategy_class,
    pairs: List[str] = None,
    worker_id: str = 'worker_1'
) -> Dict:
    """
    Run full backtest on all pairs to classify strategy type.
    
    Args:
        strategy_class: Strategy class
        pairs: List of pairs to test (default: all pairs)
        worker_id: Worker identifier
        
    Returns:
        Dict with results and classification
    """
    if pairs is None:
        pairs = ALL_PAIRS
    
    print(f"[{worker_id}] Full backtest: Testing {strategy_class.__name__} on {len(pairs)} pairs...")
    
    pair_results = {}
    passed_pairs = []
    best_result = None
    
    for pair in pairs:
        data = load_data(pair, '1h')
        if data is None:
            pair_results[pair] = {'error': 'No data'}
            continue
        
        # Test all directions and pick best
        best_dir = None
        for direction in ['LONG', 'SHORT', 'BOTH']:
            result = run_single_backtest(strategy_class, data, pair, direction)
            if result['trades'] > 0:
                passed, reasons = check_pass_criteria(result)
                result['passed'] = passed
                result['fail_reasons'] = reasons
                
                if best_dir is None or result['sharpe_ratio'] > best_dir['sharpe_ratio']:
                    best_dir = result
        
        if best_dir and best_dir['trades'] > 0:
            pair_results[pair] = best_dir
            if best_dir.get('passed'):
                passed_pairs.append(pair)
                if best_result is None or best_dir['sharpe_ratio'] > best_result['sharpe_ratio']:
                    best_result = best_dir
                    best_result['pair'] = pair
    
    # Classify strategy
    if not passed_pairs:
        classification = 'FAILED'
    elif any(p in passed_pairs for p in TIER_1_PAIRS):
        classification = 'BROAD'
    else:
        classification = 'ASSET_SPECIFIC'
    
    return {
        'pair_results': pair_results,
        'best_result': best_result,
        'passed': len(passed_pairs) > 0,
        'passed_pairs': passed_pairs,
        'pairs_passed': len(passed_pairs),
        'total_pairs_tested': len(ALL_PAIRS),
        'classification': classification,
        'worker_id': worker_id
    }
