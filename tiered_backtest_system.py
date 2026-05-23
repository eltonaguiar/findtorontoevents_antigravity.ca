"""
Tiered Backtest System - ALL STRATEGIES
=======================================

Tests ALL strategies from:
- baby_strategies/ (32 strategies)
- incubator/agents/codex_gpt5/ (26 strategies)
- incubator/agents/cursor_ai/ (28 strategies)

TIER 1: Multi-Pair Validation (BTC/ETH/SOL on 1h)
   - Criteria: Sharpe >= 1.0, Win Rate >= 45%, Max DD <= 25%, Min 12 trades
   - Failed strategies stop here

TIER 2: Multi-Timeframe Validation (1h/4h/1d)
   - Only Tier 1 passing strategies proceed
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import json
import os
import sys
import importlib.util
import inspect

# Strategy directories to scan
STRATEGY_DIRS = [
    ('baby_strategies', 'baby_strategies'),
    ('incubator/agents/codex_gpt5', 'codex'),
    ('incubator/agents/cursor_ai', 'cursor'),
]

PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
TIER_1_TIMEFRAME = '1h'
TIER_2_TIMEFRAMES = ['1h', '4h', '1d']

PASS_CRITERIA = {
    'min_sharpe': 1.0,
    'min_win_rate': 45.0,
    'max_drawdown': 25.0,
    'min_trades': 12
}

TIMEFRAME_CONFIGS = {
    '1h': {'rule': '1h', 'description': '1 Hour'},
    '4h': {'rule': '4h', 'description': '4 Hour'},
    '1d': {'rule': '1D', 'description': 'Daily'},
}


def load_strategy_from_file(filepath: str, name: str) -> Optional[Any]:
    """Load a strategy class from a Python file."""
    try:
        spec = importlib.util.spec_from_file_location(name, filepath)
        if not spec or not spec.loader:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find the strategy class
        for obj_name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                hasattr(obj, 'generate_signals') and
                obj_name not in ['Signal', 'Dict', 'List', 'Optional']):
                return obj
        return None
    except Exception as e:
        return None


def discover_all_strategies() -> Dict[str, Dict]:
    """Discover all strategies from all directories."""
    all_strategies = {}
    
    for directory, source in STRATEGY_DIRS:
        if not os.path.exists(directory):
            continue
            
        for filename in os.listdir(directory):
            if not filename.endswith('.py') or filename.startswith('_'):
                continue
            
            # Skip non-strategy files
            if filename in ['real_data_backtest.py', 'universal_market_reversal.py', 
                           'quantum_fusion_strategy.py', 'codex_agent.py']:
                continue
                
            strategy_name = filename[:-3]
            filepath = os.path.join(directory, filename)
            
            strategy_class = load_strategy_from_file(filepath, strategy_name)
            if strategy_class:
                all_strategies[strategy_name] = {
                    'class': strategy_class,
                    'filepath': filepath,
                    'source': source,
                    'directory': directory
                }
    
    return all_strategies


class TieredBacktester:
    """Tiered backtest system."""
    
    def __init__(self, db_path: str = 'crypto_data.db'):
        self.db_path = db_path
        self.results = {'tier_1': {}, 'tier_2': {}}
        self.passing_strategies = set()
        self._data_cache = {}
        
    def get_data(self, pair: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Get data with caching."""
        cache_key = f"{pair}_{timeframe}"
        if cache_key in self._data_cache:
            return self._data_cache[cache_key]
        
        try:
            conn = sqlite3.connect(self.db_path)
            query = f"SELECT timestamp, open, high, low, close, volume FROM klines WHERE pair = '{pair}' ORDER BY timestamp ASC"
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if df.empty:
                return None
                
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            if timeframe != '1h':
                config = TIMEFRAME_CONFIGS.get(timeframe, TIMEFRAME_CONFIGS['1h'])
                df = df.resample(config['rule']).agg({
                    'open': 'first', 'high': 'max', 'low': 'min', 
                    'close': 'last', 'volume': 'sum'
                }).dropna()
            
            self._data_cache[cache_key] = df
            return df
        except:
            return None
    
    def run_backtest(
        self, 
        strategy_class,
        data: pd.DataFrame,
        pair: str,
        direction_param: str = 'BOTH',
        max_signals: int = 30
    ) -> Dict:
        """Run fast backtest."""
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
                    
                    pnl = (exit_price - entry_price) / entry_price
                    if direction == 'SELL':
                        pnl = -pnl
                    
                    trades.append(pnl)
                except:
                    continue
            
            if len(trades) < 5:
                return self._empty_result(f"Only {len(trades)} trades")
            
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
            return self._empty_result(str(e))
    
    def _empty_result(self, error: str = "No signals") -> Dict:
        return {
            'trades': 0, 'wins': 0, 'losses': 0, 'win_rate': 0,
            'total_return': 0, 'sharpe_ratio': 0, 'max_drawdown': 0,
            'direction': 'NONE', 'error': error
        }
    
    def check_pass(self, result: Dict) -> Tuple[bool, List[str]]:
        reasons = []
        if result['trades'] < PASS_CRITERIA['min_trades']:
            reasons.append(f"Trades: {result['trades']}/{PASS_CRITERIA['min_trades']}")
        if result['sharpe_ratio'] < PASS_CRITERIA['min_sharpe']:
            reasons.append(f"Sharpe: {result['sharpe_ratio']:.2f}/{PASS_CRITERIA['min_sharpe']}")
        if result['win_rate'] < PASS_CRITERIA['min_win_rate']:
            reasons.append(f"WR: {result['win_rate']:.0f}%/{PASS_CRITERIA['min_win_rate']}%")
        if result['max_drawdown'] > PASS_CRITERIA['max_drawdown']:
            reasons.append(f"DD: {result['max_drawdown']:.1f}%/{PASS_CRITERIA['max_drawdown']}%")
        return len(reasons) == 0, reasons
    
    def run_tier_1(self, strategies: Dict[str, Dict]):
        """Tier 1: Multi-pair validation."""
        print("\n" + "="*80)
        print("TIER 1: MULTI-PAIR VALIDATION (BTC/ETH/SOL on 1h)")
        print("="*80)
        print(f"Criteria: Sharpe >= {PASS_CRITERIA['min_sharpe']}, "
              f"WR >= {PASS_CRITERIA['min_win_rate']}%, "
              f"DD <= {PASS_CRITERIA['max_drawdown']}%, "
              f"Trades >= {PASS_CRITERIA['min_trades']}")
        print("="*80)
        
        passed_list = []
        failed_list = []
        
        for strategy_name, config in sorted(strategies.items()):
            strategy_class = config['class']
            source = config.get('source', 'unknown')
            
            pair_results = {}
            best_result = None
            passed_any = False
            
            for pair in PAIRS:
                data = self.get_data(pair, TIER_1_TIMEFRAME)
                if data is None:
                    pair_results[pair] = {'error': 'No data'}
                    continue
                
                directions = ['LONG', 'SHORT', 'BOTH']
                best_dir = None
                
                for direction in directions:
                    result = self.run_backtest(strategy_class, data, pair, direction)
                    if result['trades'] > 0:
                        passed, reasons = self.check_pass(result)
                        result['passed'] = passed
                        result['fail_reasons'] = reasons
                        
                        if best_dir is None or result['sharpe_ratio'] > best_dir['sharpe_ratio']:
                            best_dir = result
                
                if best_dir and best_dir['trades'] > 0:
                    pair_results[pair] = best_dir
                    if best_dir.get('passed'):
                        passed_any = True
                        if best_result is None or best_dir['sharpe_ratio'] > best_result['sharpe_ratio']:
                            best_result = best_dir
                            best_result['pair'] = pair
            
            self.results['tier_1'][strategy_name] = {
                'pair_results': pair_results,
                'best_result': best_result,
                'passed': passed_any,
                'source': source
            }
            
            status = "PASS" if passed_any else "FAIL"
            source_tag = f"[{source[:5]:5s}]"
            
            if best_result:
                print(f"[{status}] {source_tag} {strategy_name:45s} | "
                      f"Sharpe: {best_result['sharpe_ratio']:6.2f} | "
                      f"WR: {best_result['win_rate']:5.1f}% | "
                      f"Trades: {best_result['trades']:3d} | "
                      f"Pair: {best_result.get('pair', 'N/A'):10s}")
            else:
                print(f"[FAIL] {source_tag} {strategy_name:45s} | No valid signals")
            
            if passed_any:
                passed_list.append(strategy_name)
                self.passing_strategies.add(strategy_name)
            else:
                failed_list.append(strategy_name)
        
        print("\n" + "="*80)
        print("TIER 1 SUMMARY")
        print("="*80)
        print(f"Total tested: {len(strategies)}")
        print(f"Passed (advancing to Tier 2): {len(passed_list)}")
        print(f"Failed (stopping): {len(failed_list)}")
        
        if passed_list:
            print(f"\nAdvancing strategies:")
            for name in passed_list:
                print(f"  - {name}")
        
        return passed_list
    
    def run_tier_2(self, strategies: Dict[str, Dict]):
        """Tier 2: Multi-timeframe validation."""
        print("\n" + "="*80)
        print("TIER 2: MULTI-TIMEFRAME VALIDATION (1h/4h/1d)")
        print("="*80)
        print(f"Testing {len(self.passing_strategies)} strategies that passed Tier 1")
        print("="*80)
        
        for strategy_name in sorted(self.passing_strategies):
            if strategy_name not in strategies:
                continue
            
            strategy_class = strategies[strategy_name]['class']
            tier_1_data = self.results['tier_1'].get(strategy_name, {})
            tier_1_best = tier_1_data.get('best_result', {})
            source = tier_1_data.get('source', 'unknown')
            
            best_pair = tier_1_best.get('pair', 'BTC/USDT')
            best_direction = tier_1_best.get('direction', 'LONG')
            
            tf_results = {}
            passed_count = 0
            
            for tf in TIER_2_TIMEFRAMES:
                data = self.get_data(best_pair, tf)
                if data is None:
                    tf_results[tf] = {'error': 'No data'}
                    continue
                
                result = self.run_backtest(strategy_class, data, best_pair, best_direction)
                if result['trades'] > 0:
                    passed, _ = self.check_pass(result)
                    result['passed'] = passed
                    if passed:
                        passed_count += 1
                tf_results[tf] = result
            
            self.results['tier_2'][strategy_name] = {
                'timeframe_results': tf_results,
                'best_pair': best_pair,
                'timeframes_passed': passed_count,
                'total_timeframes': len(TIER_2_TIMEFRAMES),
                'fully_robust': passed_count == len(TIER_2_TIMEFRAMES),
                'source': source
            }
            
            robust = "ROBUST" if passed_count == len(TIER_2_TIMEFRAMES) else "PARTIAL"
            source_tag = f"[{source[:5]:5s}]"
            print(f"[{robust}] {source_tag} {strategy_name:45s} | "
                  f"Passed {passed_count}/{len(TIER_2_TIMEFRAMES)} timeframes on {best_pair}")
        
        robust_count = sum(1 for r in self.results['tier_2'].values() if r.get('fully_robust'))
        partial_count = len(self.results['tier_2']) - robust_count
        
        print(f"\n" + "="*80)
        print("TIER 2 SUMMARY")
        print("="*80)
        print(f"Strategies tested: {len(self.results['tier_2'])}")
        print(f"Fully robust (all timeframes): {robust_count}")
        print(f"Partially robust: {partial_count}")
        
        if robust_count > 0:
            print(f"\nFully robust strategies:")
            for name, data in self.results['tier_2'].items():
                if data.get('fully_robust'):
                    print(f"  - {name}")
    
    def save_results(self):
        """Save results to JSON."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f'battleground/data/tiered_backtest_results_{timestamp}.json'
        os.makedirs('battleground/data', exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump({
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'criteria': PASS_CRITERIA,
                    'pairs': PAIRS,
                    'tier_2_timeframes': TIER_2_TIMEFRAMES
                },
                'results': self.results
            }, f, indent=2, default=str)
        
        print(f"\nResults saved: {output_path}")
        return output_path
    
    def update_dashboard(self):
        """Update dashboard with tiered results."""
        dashboard_path = 'battleground/data/baby_strats_dashboard.json'
        
        try:
            with open(dashboard_path, 'r') as f:
                dashboard = json.load(f)
        except:
            dashboard = {'strategies': []}
        
        dashboard['tiered_backtest'] = {
            'last_run': datetime.now().isoformat(),
            'tier_1_passed': len(self.passing_strategies),
            'tier_2_tested': len(self.results['tier_2']),
            'criteria': PASS_CRITERIA
        }
        
        existing = {s.get('name'): s for s in dashboard.get('strategies', [])}
        
        for strategy_name, tier_1_data in self.results['tier_1'].items():
            if strategy_name in existing:
                entry = existing[strategy_name]
            else:
                entry = {'name': strategy_name}
                dashboard['strategies'].append(entry)
            
            entry['tier_1_multi_pair'] = tier_1_data
            entry['strategy_source'] = tier_1_data.get('source', 'unknown')
            
            if strategy_name in self.results['tier_2']:
                tier_2_data = self.results['tier_2'][strategy_name]
                entry['tier_2_multi_timeframe'] = tier_2_data
                entry['validation_status'] = 'fully_validated' if tier_2_data.get('fully_robust') else 'multi_pair_validated'
            else:
                entry['validation_status'] = 'multi_pair_validated' if tier_1_data['passed'] else 'failed_tier_1'
        
        with open(dashboard_path, 'w') as f:
            json.dump(dashboard, f, indent=2, default=str)
        
        print(f"Dashboard updated: {dashboard_path}")


def main():
    print("\n" + "="*80)
    print("TIERED BACKTEST SYSTEM - ALL STRATEGIES")
    print("="*80)
    print("Tier 1: Multi-pair validation (BTC/ETH/SOL)")
    print("Tier 2: Multi-timeframe validation (1h/4h/1d)")
    print("="*80)
    
    strategies = discover_all_strategies()
    print(f"\nDiscovered {len(strategies)} strategies total")
    
    # Count by source
    sources = {}
    for s in strategies.values():
        src = s.get('source', 'unknown')
        sources[src] = sources.get(src, 0) + 1
    print("By source:", sources)
    
    backtester = TieredBacktester()
    
    # Run Tier 1
    passed = backtester.run_tier_1(strategies)
    
    # Run Tier 2 for passing strategies
    if passed:
        backtester.run_tier_2(strategies)
    
    # Save and update
    backtester.save_results()
    backtester.update_dashboard()
    
    print("\n" + "="*80)
    print("TIERED BACKTEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
