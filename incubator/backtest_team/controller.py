#!/usr/bin/env python3
"""
Baby Strat Backtest Controller - Agent Team Deployment
=====================================================

Coordinates parallel backtesting of multiple Baby Strat candidates.
Acts as the "conductor" for the backtest agent team.

Usage:
    python controller.py --strategies all --days 90
    python controller.py --strategies strategy1,strategy2 --days 90
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class BacktestResult:
    """Result from a single strategy backtest."""
    strategy_name: str
    agent_id: str
    status: str  # "passed", "failed", "error"
    sharpe: Optional[float] = None
    win_rate: Optional[float] = None
    max_drawdown: Optional[float] = None
    total_trades: int = 0
    profit_factor: Optional[float] = None
    error_message: Optional[str] = None
    backtest_duration_sec: float = 0.0
    timestamp: str = ""


class BacktestController:
    """
    Orchestrates backtest runs for multiple Baby Strat strategies.
    
    Think of this as the "team lead" that:
    1. Discovers all strategies needing backtest
    2. Spawns parallel backtest workers
    3. Aggregates results
    4. Updates strategy metadata
    """
    
    def __init__(self, data_days: int = 90):
        self.data_days = data_days
        self.incubator_path = Path(__file__).parent.parent
        self.agents_path = self.incubator_path / "agents"
        self.results_path = self.incubator_path / "backtest_results"
        self.results_path.mkdir(exist_ok=True)
        
    def discover_strategies(self, strategy_filter: Optional[List[str]] = None) -> List[Dict]:
        """Find all strategies awaiting backtest."""
        strategies = []
        
        # Search all agent directories
        for agent_dir in self.agents_path.iterdir():
            if not agent_dir.is_dir():
                continue
                
            # Find all .py files (strategies) and their metadata
            for py_file in agent_dir.glob("*.py"):
                meta_file = Path(str(py_file) + ".meta.json")
                
                if not meta_file.exists():
                    continue
                    
                # Load metadata
                with open(meta_file) as f:
                    meta = json.load(f)
                
                # Skip if not awaiting backtest
                if meta.get("status") not in ["awaiting_backtest", "backtest_pending"]:
                    continue
                
                # Apply filter if specified
                if strategy_filter and meta.get("strategy_name") not in strategy_filter:
                    continue
                
                strategies.append({
                    "name": meta.get("strategy_name"),
                    "agent_id": meta.get("agent_id"),
                    "file": py_file,
                    "meta_file": meta_file,
                    "meta": meta
                })
        
        return strategies
    
    def run_backtest(self, strategy: Dict) -> BacktestResult:
        """Run backtest for a single strategy using the runner agent."""
        import time
        start_time = time.time()
        
        strategy_name = strategy["name"]
        agent_id = strategy["agent_id"]
        py_file = strategy["file"]
        
        print(f"\n[CONTROLLER] Deploying backtest agent for: {strategy_name}")
        print(f"             Agent: {agent_id}")
        print(f"             Data: {self.data_days} days historical")
        
        try:
            # Import the strategy
            import importlib.util
            spec = importlib.util.spec_from_file_location("strategy", py_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find the strategy class (first class ending with 'Strategy')
            strategy_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    attr_name.endswith('Strategy') and 
                    attr_name != 'Strategy'):
                    strategy_class = attr
                    break
            
            if not strategy_class:
                return BacktestResult(
                    strategy_name=strategy_name,
                    agent_id=agent_id,
                    status="error",
                    error_message="No strategy class found",
                    backtest_duration_sec=time.time() - start_time,
                    timestamp=datetime.now().isoformat()
                )
            
            # Run backtest via runner agent
            from backtest_team.runner import BacktestRunner
            runner = BacktestRunner(days=self.data_days)
            result = runner.run_strategy(strategy_class, strategy_name)
            
            # Update result with metadata
            result.strategy_name = strategy_name
            result.agent_id = agent_id
            result.backtest_duration_sec = time.time() - start_time
            result.timestamp = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            import traceback
            return BacktestResult(
                strategy_name=strategy_name,
                agent_id=agent_id,
                status="error",
                error_message=str(e) + "\n" + traceback.format_exc(),
                backtest_duration_sec=time.time() - start_time,
                timestamp=datetime.now().isoformat()
            )
    
    def update_metadata(self, strategy: Dict, result: BacktestResult):
        """Update strategy metadata with backtest results."""
        meta = strategy["meta"]
        
        # Update status based on result
        if result.status == "passed":
            meta["status"] = "backtest_passed"
        elif result.status == "failed":
            meta["status"] = "backtest_failed"
        else:
            meta["status"] = "backtest_error"
        
        # Update metrics
        meta["backtest_metrics"] = {
            "sharpe": result.sharpe,
            "win_rate": result.win_rate,
            "max_drawdown": result.max_drawdown,
            "total_trades": result.total_trades,
            "profit_factor": result.profit_factor,
            "timestamp": result.timestamp,
            "duration_sec": result.backtest_duration_sec
        }
        
        # Add to validation history
        if "validation_history" not in meta:
            meta["validation_history"] = []
        
        meta["validation_history"].append({
            "stage": "backtest",
            "status": result.status,
            "metrics": meta["backtest_metrics"],
            "timestamp": result.timestamp
        })
        
        # Save updated metadata
        with open(strategy["meta_file"], 'w') as f:
            json.dump(meta, f, indent=2)
        
        print(f"[CONTROLLER] Updated metadata: {strategy['meta_file']}")
    
    def save_team_report(self, results: List[BacktestResult]):
        """Save comprehensive team report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "data_days": self.data_days,
            "total_strategies": len(results),
            "passed": sum(1 for r in results if r.status == "passed"),
            "failed": sum(1 for r in results if r.status == "failed"),
            "errors": sum(1 for r in results if r.status == "error"),
            "results": [asdict(r) for r in results]
        }
        
        report_file = self.results_path / f"team_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n[CONTROLLER] Team report saved: {report_file}")
        return report
    
    def run(self, strategy_filter: Optional[List[str]] = None) -> Dict:
        """Run the full backtest team deployment."""
        print("=" * 60)
        print("BABY STRAT BACKTEST AGENT TEAM DEPLOYMENT")
        print("=" * 60)
        print(f"Controller: v1.0")
        print(f"Historical Data: {self.data_days} days")
        print(f"Pass Criteria: Sharpe >= 1.0, Win Rate >= 45%, Max DD <= 20%")
        print("=" * 60)
        
        # Discover strategies
        strategies = self.discover_strategies(strategy_filter)
        print(f"\n[CONTROLLER] Discovered {len(strategies)} strategies awaiting backtest")
        
        if not strategies:
            print("[CONTROLLER] No strategies to backtest. Exiting.")
            return {"status": "no_strategies"}
        
        for s in strategies:
            print(f"  - {s['name']} ({s['agent_id']})")
        
        # Run backtests
        results = []
        for strategy in strategies:
            result = self.run_backtest(strategy)
            results.append(result)
            
            # Update metadata
            self.update_metadata(strategy, result)
            
            # Print result
            status_icon = "PASS" if result.status == "passed" else "FAIL" if result.status == "failed" else "ERR"
            print(f"\n[{status_icon}] {result.strategy_name}")
            if result.status == "passed":
                print(f"   Sharpe: {result.sharpe:.2f} | Win Rate: {result.win_rate:.1%} | Trades: {result.total_trades}")
            elif result.error_message:
                print(f"   Error: {result.error_message[:200]}")
        
        # Save team report
        report = self.save_team_report(results)
        
        # Print summary
        print("\n" + "=" * 60)
        print("TEAM DEPLOYMENT SUMMARY")
        print("=" * 60)
        print(f"Total Strategies: {report['total_strategies']}")
        print(f"Passed: {report['passed']}")
        print(f"Failed: {report['failed']}")
        print(f"Errors: {report['errors']}")
        print("=" * 60)
        
        if report['passed'] > 0:
            print("\nPASSED STRATEGIES (Ready for Paper Trading):")
            for r in results:
                if r.status == "passed":
                    print(f"   * {r.strategy_name} - Sharpe: {r.sharpe:.2f}, WR: {r.win_rate:.1%}")
        
        return report


def main():
    parser = argparse.ArgumentParser(description="Baby Strat Backtest Controller")
    parser.add_argument("--strategies", default="all", 
                       help="Comma-separated strategy names or 'all'")
    parser.add_argument("--days", type=int, default=90,
                       help="Days of historical data to use")
    args = parser.parse_args()
    
    # Parse strategy filter
    strategy_filter = None
    if args.strategies != "all":
        strategy_filter = [s.strip() for s in args.strategies.split(",")]
    
    # Run controller
    controller = BacktestController(data_days=args.days)
    report = controller.run(strategy_filter)
    
    # Exit with appropriate code
    if report.get("passed", 0) > 0:
        print("\nBacktest team deployment complete. Strategies ready for paper trading.")
        return 0
    else:
        print("\nNo strategies passed backtest validation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
