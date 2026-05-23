"""
Forward Testing Coordinator

Coordinates parallel forward testing across multiple workers.
Ensures strategies that pass gates get comprehensive forward validation.
"""

import os
import sys
import json
import time
import sqlite3
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from incubator.testing.forward_test_tracker import ForwardTestTracker, StrategyGraduationCriteria
from incubator.testing.parallel_utils import claim_strategy, release_claim


class ForwardTestCoordinator:
    """
    Coordinates forward testing across multiple workers.
    
    Responsibilities:
    1. Discover strategies ready for forward testing
    2. Distribute work across workers using file locks
    3. Aggregate results into forward test database
    4. Identify graduation candidates
    """
    
    def __init__(self, 
                 db_path: str = "incubator/forward_test.db",
                 locks_dir: str = "battleground/data/forward_test/locks",
                 results_dir: str = "battleground/data/forward_test"):
        self.db_path = db_path
        self.locks_dir = Path(locks_dir)
        self.locks_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.tracker = ForwardTestTracker(db_path)
        
    def discover_strategies_needing_forward_test(self) -> List[Dict[str, Any]]:
        """Discover all strategies that need forward testing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get strategies in paper trading that haven't been updated recently
        cursor.execute('''
            SELECT strategy_name, agent_id, paper_started_at, forward_days
            FROM strategies
            WHERE status = 'paper_trading'
            ORDER BY forward_days ASC, paper_started_at ASC
        ''')
        
        strategies = []
        for row in cursor.fetchall():
            strategies.append({
                'strategy_name': row[0],
                'agent_id': row[1],
                'paper_started_at': row[2],
                'forward_days': row[3] or 0
            })
            
        conn.close()
        return strategies
        
    def discover_tier1_passed_strategies(self, tiered_results_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Discover strategies that passed Tier 1 backtesting.
        These are priority candidates for forward testing.
        """
        passed = []
        
        # If tiered results provided, use those
        if tiered_results_path and os.path.exists(tiered_results_path):
            with open(tiered_results_path, 'r') as f:
                results = json.load(f)
                
            for r in results.get('tier1_passed', []):
                passed.append({
                    'strategy_name': r['strategy_name'],
                    'agent_id': r.get('agent_id', 'unknown'),
                    'best_pair': r.get('best_pair'),
                    'best_sharpe': r.get('best_sharpe'),
                    'tier': 'tier1_passed'
                })
                
        # Also check for any graduated strategies that need monitoring
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT strategy_name, agent_id, status
            FROM strategies
            WHERE status IN ('graduated', 'live')
        ''')
        
        for row in cursor.fetchall():
            passed.append({
                'strategy_name': row[0],
                'agent_id': row[1],
                'tier': row[2]
            })
            
        conn.close()
        return passed
        
    def run_forward_test_for_strategy(self, 
                                      strategy_info: Dict[str, Any],
                                      worker_id: str,
                                      data_source: str = "real_time") -> Dict[str, Any]:
        """
        Run forward test for a single strategy.
        This is called by workers in parallel.
        """
        strategy_name = strategy_info['strategy_name']
        agent_id = strategy_info.get('agent_id', 'unknown')
        
        # Try to claim this strategy
        if not claim_strategy(f"forward_{strategy_name}", worker_id, str(self.locks_dir)):
            return {'status': 'already_claimed', 'strategy': strategy_name}
            
        try:
            print(f"[Worker {worker_id}] Forward testing: {strategy_name}")
            
            # Find strategy file
            strategy_file = self._find_strategy_file(strategy_name, agent_id)
            if not strategy_file:
                return {
                    'status': 'error',
                    'strategy': strategy_name,
                    'error': f'Strategy file not found for {agent_id}/{strategy_name}'
                }
                
            # Load and run strategy
            metrics, trades = self._run_strategy_forward(strategy_file, data_source)
            
            # Update tracker
            self.tracker.update_forward_metrics(strategy_name, metrics, trades)
            
            # Check graduation readiness
            graduation_check = self.tracker.evaluate_graduation(strategy_name)
            
            result = {
                'status': 'success',
                'strategy': strategy_name,
                'agent_id': agent_id,
                'metrics': metrics,
                'trades_count': len(trades),
                'graduation_ready': graduation_check.get('ready_for_graduation', False),
                'graduation_score': graduation_check.get('graduation_score', 0),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Save individual result
            result_path = self.results_dir / f"forward_result_{strategy_name}_{int(time.time())}.json"
            with open(result_path, 'w') as f:
                json.dump(result, f, indent=2)
                
            return result
            
        except Exception as e:
            return {
                'status': 'error',
                'strategy': strategy_name,
                'error': str(e)
            }
        finally:
            release_claim(f"forward_{strategy_name}", str(self.locks_dir))
            
    def _find_strategy_file(self, strategy_name: str, agent_id: str) -> Optional[Path]:
        """Find strategy Python file"""
        # Map agent_id to directory
        agent_dirs = {
            'baby_strategies': ROOT / 'baby_strategies',
            'codex_gpt5': ROOT / 'incubator' / 'agents' / 'codex_gpt5',
            'cursor_ai': ROOT / 'incubator' / 'agents' / 'cursor_ai',
            'web_ai': ROOT / 'incubator' / 'agents' / 'web_ai',
            'team_alpha': ROOT / 'incubator' / 'agents' / 'team_alpha',
            'claude_opus': ROOT / 'incubator' / 'agents' / 'claude_opus_batch',
        }
        
        agent_dir = agent_dirs.get(agent_id, ROOT / 'incubator' / 'agents' / agent_id)
        
        # Look for file
        if agent_dir.exists():
            for f in agent_dir.glob('*.py'):
                if strategy_name in f.name or f.stem == strategy_name:
                    return f
                    
        # Fallback: search all agent directories
        for agent_dir in (ROOT / 'incubator' / 'agents').glob('*'):
            if agent_dir.is_dir():
                for f in agent_dir.glob('*.py'):
                    if strategy_name in f.name or f.stem == strategy_name:
                        return f
                        
        return None
        
    def _run_strategy_forward(self, strategy_file: Path, data_source: str) -> Tuple[Dict, List]:
        """Run strategy against forward data"""
        # This is a simplified version - in production would integrate with
        # incubator.validation.update_forward_matches or similar
        
        # Load strategy module
        spec = importlib.util.spec_from_file_location(f"fwd_{strategy_file.stem}", strategy_file)
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
            raise ValueError(f"No Strategy class found in {strategy_file}")
            
        # Instantiate and run
        strategy = strategy_class()
        
        # Get signals from real-time data
        # This would integrate with your data feed
        metrics = {
            'sharpe': 0.0,  # Placeholder
            'win_rate': 0.0,
            'max_drawdown': 0.0,
            'expectancy': 0.0,
            'pnl_pct': 0.0,
            'trades_count': 0,
            'days_in_test': 0
        }
        trades = []
        
        return metrics, trades
        
    def run_parallel_forward_tests(self, 
                                   max_workers: int = 4,
                                   strategy_limit: Optional[int] = None) -> Dict[str, Any]:
        """Run forward tests in parallel across multiple workers"""
        strategies = self.discover_strategies_needing_forward_test()
        
        if strategy_limit:
            strategies = strategies[:strategy_limit]
            
        print(f"[Coordinator] Running forward tests for {len(strategies)} strategies with {max_workers} workers")
        
        results = {
            'total': len(strategies),
            'completed': 0,
            'errors': 0,
            'already_claimed': 0,
            'graduation_ready': 0
        }
        
        # Use process pool for parallel execution
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.run_forward_test_for_strategy,
                    s,
                    f"worker_{i % max_workers}",
                    "real_time"
                ): s for i, s in enumerate(strategies)
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    
                    if result['status'] == 'success':
                        results['completed'] += 1
                        if result.get('graduation_ready'):
                            results['graduation_ready'] += 1
                    elif result['status'] == 'already_claimed':
                        results['already_claimed'] += 1
                    else:
                        results['errors'] += 1
                        print(f"[Coordinator] Error: {result.get('error')}")
                        
                except Exception as e:
                    results['errors'] += 1
                    print(f"[Coordinator] Worker exception: {e}")
                    
        # Generate summary report
        self._generate_coordination_report(results)
        
        return results
        
    def _generate_coordination_report(self, results: Dict[str, Any]):
        """Generate coordination summary report"""
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'coordination_results': results,
            'strategies_in_pipeline': len(self.discover_strategies_needing_forward_test()),
            'graduation_candidates': len(self.tracker.get_all_strategies(status='paper_trading'))
        }
        
        report_path = self.results_dir / f"coordination_report_{int(time.time())}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"[Coordinator] Report saved: {report_path}")
        
    def auto_graduate_ready_strategies(self, 
                                       min_score: float = 75.0,
                                       dry_run: bool = True) -> List[Dict[str, Any]]:
        """
        Automatically graduate strategies that meet all criteria.
        
        Args:
            min_score: Minimum graduation score required
            dry_run: If True, only report what would be graduated
        """
        candidates = self.tracker.get_all_strategies(status='paper_trading')
        graduated = []
        
        for strategy in candidates:
            strategy_name = strategy['strategy_name']
            
            # Evaluate graduation readiness
            check = self.tracker.evaluate_graduation(strategy_name)
            
            if check.get('ready_for_graduation') and check.get('graduation_score', 0) >= min_score:
                graduation_info = {
                    'strategy_name': strategy_name,
                    'score': check['graduation_score'],
                    'metrics': check['metrics'],
                    'allocation_pct': self._calculate_allocation(check['graduation_score'])
                }
                
                if not dry_run:
                    success = self.tracker.graduate_strategy(
                        strategy_name,
                        graduation_info['allocation_pct'],
                        check.get('criteria_reasons', [])
                    )
                    graduation_info['graduated'] = success
                else:
                    graduation_info['graduated'] = False
                    graduation_info['dry_run'] = True
                    
                graduated.append(graduation_info)
                
        # Save graduation report
        report_path = self.results_dir / f"auto_graduation_{'dry_run' if dry_run else 'executed'}_{int(time.time())}.json"
        with open(report_path, 'w') as f:
            json.dump({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'dry_run': dry_run,
                'min_score': min_score,
                'graduated_count': len(graduated),
                'graduated': graduated
            }, f, indent=2)
            
        print(f"[Coordinator] {'Would graduate' if dry_run else 'Graduated'} {len(graduated)} strategies")
        print(f"[Coordinator] Report: {report_path}")
        
        return graduated
        
    def _calculate_allocation(self, score: float) -> float:
        """Calculate recommended allocation percentage based on score"""
        if score >= 90: return 5.0
        elif score >= 80: return 3.0
        elif score >= 70: return 2.0
        elif score >= 60: return 1.0
        else: return 0.5


# CLI interface
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Forward Testing Coordinator')
    parser.add_argument('--discover', action='store_true', help='Discover strategies needing forward test')
    parser.add_argument('--run', action='store_true', help='Run forward tests')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--limit', type=int, help='Limit number of strategies')
    parser.add_argument('--graduate', action='store_true', help='Auto-graduate ready strategies')
    parser.add_argument('--min-score', type=float, default=75.0, help='Minimum graduation score')
    parser.add_argument('--execute', action='store_true', help='Actually execute graduation (not dry run)')
    
    args = parser.parse_args()
    
    coordinator = ForwardTestCoordinator()
    
    if args.discover:
        strategies = coordinator.discover_strategies_needing_forward_test()
        print(f"Found {len(strategies)} strategies needing forward testing")
        for s in strategies[:10]:
            print(f"  - {s['strategy_name']} ({s['agent_id']}, {s['forward_days']} days)")
            
    elif args.run:
        results = coordinator.run_parallel_forward_tests(
            max_workers=args.workers,
            strategy_limit=args.limit
        )
        print(f"\nResults: {results}")
        
    elif args.graduate:
        graduated = coordinator.auto_graduate_ready_strategies(
            min_score=args.min_score,
            dry_run=not args.execute
        )
        print(f"\nGraduation candidates: {len(graduated)}")
        for g in graduated[:5]:
            print(f"  - {g['strategy_name']}: score={g['score']:.1f}, alloc={g['allocation_pct']}%")


if __name__ == '__main__':
    main()
