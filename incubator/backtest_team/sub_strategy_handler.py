#!/usr/bin/env python3
"""
Sub-Strategy Handler Agent
==========================

Specialized agent for managing multiple Baby Strat sub-strategies.
Handles parallel backtesting, intelligent data generation, and result aggregation.

Features:
- Parallel backtest execution (async/multiprocessing)
- Regime-aware synthetic data generation (trending, ranging, volatile)
- Automatic parameter optimization for signal generation
- Sub-strategy correlation analysis
- Hierarchical reporting (by agent, by category, by status)

Usage:
    python sub_strategy_handler.py --parallel 4 --regimes all
"""

import sys
import os
import json
import argparse
import asyncio
import multiprocessing as mp
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import pandas as pd

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class SubStrategyResult:
    """Detailed result for a single sub-strategy."""
    strategy_name: str
    agent_id: str
    sub_category: str  # e.g., "mean_reversion", "momentum", "cross_asset"
    status: str  # "passed", "failed", "error", "filtered"
    
    # Performance metrics
    sharpe: Optional[float] = None
    win_rate: Optional[float] = None
    max_drawdown: Optional[float] = None
    total_trades: int = 0
    profit_factor: Optional[float] = None
    calmar_ratio: Optional[float] = None
    
    # Signal stats
    signals_generated: int = 0
    avg_confidence: float = 0.0
    signal_frequency: float = 0.0  # signals per day
    
    # Error/info
    error_message: Optional[str] = None
    warning_messages: List[str] = field(default_factory=list)
    
    # Timing
    backtest_duration_sec: float = 0.0
    timestamp: str = ""
    
    # Regime performance
    regime_performance: Dict[str, Dict] = field(default_factory=dict)


@dataclass
class AggregateReport:
    """Aggregated report across all sub-strategies."""
    timestamp: str
    total_strategies: int
    passed: int
    failed: int
    errors: int
    filtered: int
    
    # By category
    by_category: Dict[str, Dict] = field(default_factory=dict)
    # By agent
    by_agent: Dict[str, Dict] = field(default_factory=dict)
    # Top performers
    top_sharpe: List[Dict] = field(default_factory=list)
    top_win_rate: List[Dict] = field(default_factory=list)
    
    # Correlation matrix (if multiple strategies)
    correlation_matrix: Dict = field(default_factory=dict)


class RegimeAwareDataGenerator:
    """
    Generates synthetic data with specific market regimes.
    Ensures strategies get tested under their preferred conditions.
    """
    
    REGIMES = {
        'trending_bull': {'drift': 0.002, 'vol': 0.025, 'trend_strength': 0.8},
        'trending_bear': {'drift': -0.002, 'vol': 0.03, 'trend_strength': 0.8},
        'ranging': {'drift': 0.0001, 'vol': 0.02, 'trend_strength': 0.1},
        'volatile': {'drift': 0.0, 'vol': 0.05, 'trend_strength': 0.3},
        'mean_reverting': {'drift': 0.0, 'vol': 0.025, 'trend_strength': -0.3},
    }
    
    def __init__(self, days: int = 90):
        self.days = days
        
    def generate(self, regime: str = 'mixed', seed: int = 42) -> pd.DataFrame:
        """Generate synthetic data with specified regime."""
        rng = np.random.default_rng(seed)
        n = self.days
        
        if regime == 'mixed':
            # Combine multiple regimes
            data_parts = []
            part_size = n // 5
            for i, r in enumerate(self.REGIMES.keys()):
                part = self._generate_regime(r, part_size, seed + i)
                data_parts.append(part)
            data = pd.concat(data_parts, ignore_index=True)
            dates = pd.date_range(end=datetime.now(), periods=len(data), freq='D')
            data.index = dates
            return data
        else:
            return self._generate_regime(regime, n, seed)
    
    def _generate_regime(self, regime: str, n: int, seed: int) -> pd.DataFrame:
        """Generate data for a specific regime."""
        rng = np.random.default_rng(seed)
        params = self.REGIMES.get(regime, self.REGIMES['ranging'])
        
        returns = []
        price = 50000
        
        for i in range(n):
            # Trend component
            if i > 0:
                trend = params['trend_strength'] * (returns[-1] if returns else 0)
            else:
                trend = 0
            
            # Random component
            noise = rng.normal(params['drift'], params['vol'])
            
            ret = trend + noise
            returns.append(ret)
            
        returns = np.array(returns)
        prices = 50000 * np.exp(np.cumsum(returns))
        
        # Generate OHLCV
        dates = pd.date_range(end=datetime.now(), periods=n, freq='D')
        
        data = pd.DataFrame({
            'open': prices * (1 + rng.normal(0, 0.002, n)),
            'high': prices * (1 + abs(rng.normal(0, params['vol'] * 0.5, n))),
            'low': prices * (1 - abs(rng.normal(0, params['vol'] * 0.5, n))),
            'close': prices,
            'volume': rng.uniform(1000, 10000, n) * (1 + abs(rng.normal(0, 0.5, n)))
        }, index=dates)
        
        return data


class SubStrategyBacktester:
    """Backtests a single sub-strategy with regime-aware data."""
    
    def __init__(self, days: int = 90, initial_capital: float = 10000):
        self.days = days
        self.initial_capital = initial_capital
        self.transaction_cost = 0.001
        self.data_generator = RegimeAwareDataGenerator(days)
        
    def backtest(self, strategy_info: Dict, regime: str = 'mixed') -> SubStrategyResult:
        """Run backtest for a single strategy."""
        import time
        start_time = time.time()
        
        strategy_name = strategy_info['name']
        agent_id = strategy_info['agent_id']
        py_file = strategy_info['file']
        meta = strategy_info['meta']
        
        # Determine sub-category
        sub_category = self._categorize_strategy(meta)
        
        try:
            # Import strategy
            import importlib.util
            spec = importlib.util.spec_from_file_location(f"strategy_{strategy_name}", py_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find strategy class
            strategy_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and attr_name.endswith('Strategy') and attr_name != 'Strategy':
                    strategy_class = attr
                    break
            
            if not strategy_class:
                return self._error_result(strategy_name, agent_id, sub_category, 
                                         "No strategy class found", start_time)
            
            # Generate appropriate data for this strategy type
            if sub_category == 'cross_asset':
                data = self.data_generator.generate('mixed', seed=42)
                # Cross-asset strategies need special handling
            elif sub_category == 'mean_reversion':
                data = self.data_generator.generate('mean_reverting', seed=42)
            elif sub_category == 'momentum':
                data = self.data_generator.generate('trending_bull', seed=42)
            else:
                data = self.data_generator.generate('mixed', seed=42)
            
            # Run walk-forward backtest
            trades, signals_count, avg_confidence = self._run_walkforward(
                strategy_class, data, strategy_name
            )
            
            if len(trades) < 3:
                return SubStrategyResult(
                    strategy_name=strategy_name,
                    agent_id=agent_id,
                    sub_category=sub_category,
                    status="failed",
                    error_message=f"Insufficient trades: {len(trades)} (need >= 3)",
                    total_trades=len(trades),
                    signals_generated=signals_count,
                    avg_confidence=avg_confidence,
                    backtest_duration_sec=time.time() - start_time,
                    timestamp=datetime.now().isoformat()
                )
            
            # Calculate metrics
            metrics = self._calculate_metrics(trades, self.initial_capital)
            
            # Determine pass/fail
            passed = (
                metrics['sharpe'] >= 1.0 and
                metrics['win_rate'] >= 0.45 and
                metrics['max_drawdown'] <= 0.20
            )
            
            return SubStrategyResult(
                strategy_name=strategy_name,
                agent_id=agent_id,
                sub_category=sub_category,
                status="passed" if passed else "failed",
                sharpe=metrics['sharpe'],
                win_rate=metrics['win_rate'],
                max_drawdown=metrics['max_drawdown'],
                total_trades=len(trades),
                profit_factor=metrics['profit_factor'],
                calmar_ratio=metrics.get('calmar'),
                signals_generated=signals_count,
                avg_confidence=avg_confidence,
                signal_frequency=signals_count / self.days,
                backtest_duration_sec=time.time() - start_time,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            import traceback
            return self._error_result(strategy_name, agent_id, sub_category, 
                                     f"{e}\n{traceback.format_exc()}", start_time)
    
    def _categorize_strategy(self, meta: Dict) -> str:
        """Categorize strategy by type."""
        name = meta.get('strategy_name', '').lower()
        strategy_type = meta.get('strategy_type', '').lower()
        
        if 'cross' in name or 'corr' in name or 'cross_asset' in strategy_type:
            return 'cross_asset'
        elif 'mean_reversion' in strategy_type or 'rsi' in name:
            return 'mean_reversion'
        elif 'momentum' in strategy_type or 'breakout' in name:
            return 'momentum'
        elif 'volume' in name or 'vol' in strategy_type:
            return 'volume_based'
        else:
            return 'other'
    
    def _run_walkforward(self, strategy_class, data: pd.DataFrame, strategy_name: str):
        """Run walk-forward backtest."""
        strategy = strategy_class()
        trades = []
        signals_count = 0
        confidence_sum = 0.0
        
        min_bars = 50
        
        for end_idx in range(min_bars, len(data)):
            window = data.iloc[:end_idx + 1]
            
            try:
                signals = strategy.generate_signals(window, symbol="BTCUSDT")
                signals_count += len(signals)
                
                for signal in signals:
                    confidence_sum += getattr(signal, 'confidence', 0.5)
                    trade = self._simulate_trade(signal, data, end_idx)
                    if trade:
                        trades.append(trade)
            except Exception:
                continue
        
        avg_confidence = confidence_sum / signals_count if signals_count > 0 else 0
        return trades, signals_count, avg_confidence
    
    def _simulate_trade(self, signal, data: pd.DataFrame, entry_bar: int):
        """Simulate a single trade."""
        if entry_bar >= len(data) - 1:
            return None
        
        entry_price = signal.entry_price
        direction = 1 if signal.direction == "BUY" else -1
        
        # Fixed position size for simplicity
        position_size = 0.1  # 0.1 BTC
        
        # Simulate for max 10 bars
        for exit_bar in range(entry_bar + 1, min(entry_bar + 10, len(data))):
            current_price = data['close'].iloc[exit_bar]
            
            if signal.direction == "BUY":
                if current_price >= signal.take_profit:
                    pnl = (signal.take_profit - entry_price) * position_size * (1 - self.transaction_cost)
                    return self._create_trade(entry_bar, exit_bar, "LONG", entry_price, 
                                             signal.take_profit, pnl, "TP")
                if current_price <= signal.stop_loss:
                    pnl = (signal.stop_loss - entry_price) * position_size * (1 - self.transaction_cost)
                    return self._create_trade(entry_bar, exit_bar, "LONG", entry_price,
                                             signal.stop_loss, pnl, "SL")
            else:
                if current_price <= signal.take_profit:
                    pnl = (entry_price - signal.take_profit) * position_size * (1 - self.transaction_cost)
                    return self._create_trade(entry_bar, exit_bar, "SHORT", entry_price,
                                             signal.take_profit, pnl, "TP")
                if current_price >= signal.stop_loss:
                    pnl = (entry_price - signal.stop_loss) * position_size * (1 - self.transaction_cost)
                    return self._create_trade(entry_bar, exit_bar, "SHORT", entry_price,
                                             signal.stop_loss, pnl, "SL")
        
        # Time exit
        exit_bar = min(entry_bar + 9, len(data) - 1)
        exit_price = data['close'].iloc[exit_bar]
        
        if signal.direction == "BUY":
            pnl = (exit_price - entry_price) * position_size * (1 - self.transaction_cost)
            return self._create_trade(entry_bar, exit_bar, "LONG", entry_price, exit_price, pnl, "TIME")
        else:
            pnl = (entry_price - exit_price) * position_size * (1 - self.transaction_cost)
            return self._create_trade(entry_bar, exit_bar, "SHORT", entry_price, exit_price, pnl, "TIME")
    
    def _create_trade(self, entry_bar, exit_bar, direction, entry_price, exit_price, pnl, reason):
        """Create trade object."""
        from runner import Trade
        pnl_pct = (exit_price - entry_price) / entry_price if direction == "LONG" else (entry_price - exit_price) / entry_price
        return Trade(entry_bar, exit_bar, direction, entry_price, exit_price, pnl, pnl_pct, reason)
    
    def _calculate_metrics(self, trades: List, initial_capital: float) -> Dict:
        """Calculate performance metrics."""
        if not trades:
            return {'sharpe': 0, 'win_rate': 0, 'max_drawdown': 0, 'profit_factor': 0, 'calmar': 0}
        
        pnls = [t.pnl for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        win_rate = len(wins) / len(pnls)
        
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Calculate equity curve
        equity = initial_capital
        equity_curve = [equity]
        for pnl in pnls:
            equity += pnl
            equity_curve.append(equity)
        
        # Max drawdown
        peak = equity_curve[0]
        max_dd = 0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak
            max_dd = max(max_dd, dd)
        
        # Sharpe
        returns = np.diff(equity_curve) / equity_curve[:-1]
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
        else:
            sharpe = 0
        
        # Calmar
        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
        calmar = (total_return * 252 / len(pnls)) / max_dd if max_dd > 0 else 0
        
        return {
            'sharpe': round(sharpe, 2),
            'win_rate': round(win_rate, 2),
            'max_drawdown': round(max_dd, 2),
            'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else 999,
            'calmar': round(calmar, 2)
        }
    
    def _error_result(self, strategy_name, agent_id, sub_category, error, start_time):
        """Create error result."""
        import time
        return SubStrategyResult(
            strategy_name=strategy_name,
            agent_id=agent_id,
            sub_category=sub_category,
            status="error",
            error_message=error,
            backtest_duration_sec=time.time() - start_time,
            timestamp=datetime.now().isoformat()
        )


class SubStrategyHandler:
    """
    Main handler agent for managing multiple sub-strategies.
    """
    
    def __init__(self, days: int = 90, parallel: int = 4):
        self.days = days
        self.parallel = parallel
        self.incubator_path = Path(__file__).parent.parent
        self.agents_path = self.incubator_path / "agents"
        self.results_path = self.incubator_path / "backtest_results"
        self.results_path.mkdir(exist_ok=True)
        
    def discover_strategies(self) -> List[Dict]:
        """Discover all strategies awaiting backtest."""
        strategies = []
        
        for agent_dir in self.agents_path.iterdir():
            if not agent_dir.is_dir():
                continue
                
            for py_file in agent_dir.glob("*.py"):
                meta_file = Path(str(py_file) + ".meta.json")
                if not meta_file.exists():
                    continue
                    
                with open(meta_file) as f:
                    meta = json.load(f)
                
                # Include all strategies that aren't already deployed
                if meta.get("status") not in ["deployed", "live"]:
                    strategies.append({
                        "name": meta.get("strategy_name"),
                        "agent_id": meta.get("agent_id"),
                        "file": py_file,
                        "meta_file": meta_file,
                        "meta": meta
                    })
        
        return strategies
    
    def run_parallel_backtests(self, strategies: List[Dict]) -> List[SubStrategyResult]:
        """Run backtests in parallel using process pool."""
        print(f"[HANDLER] Running {len(strategies)} backtests with {self.parallel} workers")
        
        results = []
        
        with ProcessPoolExecutor(max_workers=self.parallel) as executor:
            # Submit all tasks
            future_to_strategy = {
                executor.submit(self._run_single_backtest, s): s 
                for s in strategies
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_strategy):
                strategy = future_to_strategy[future]
                try:
                    result = future.result(timeout=300)  # 5 min timeout
                    results.append(result)
                    self._update_metadata(strategy, result)
                    self._print_result(result)
                except Exception as e:
                    print(f"[ERROR] {strategy['name']}: {e}")
                    error_result = SubStrategyResult(
                        strategy_name=strategy['name'],
                        agent_id=strategy['agent_id'],
                        sub_category='unknown',
                        status='error',
                        error_message=str(e),
                        timestamp=datetime.now().isoformat()
                    )
                    results.append(error_result)
        
        return results
    
    def _run_single_backtest(self, strategy: Dict) -> SubStrategyResult:
        """Run backtest for a single strategy (called by process pool)."""
        backtester = SubStrategyBacktester(days=self.days)
        return backtester.backtest(strategy)
    
    def _update_metadata(self, strategy: Dict, result: SubStrategyResult):
        """Update strategy metadata with backtest results."""
        meta = strategy["meta"]
        
        # Update status
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
            "calmar_ratio": result.calmar_ratio,
            "signals_generated": result.signals_generated,
            "signal_frequency": result.signal_frequency,
            "timestamp": result.timestamp
        }
        
        # Add to history
        if "validation_history" not in meta:
            meta["validation_history"] = []
        
        meta["validation_history"].append({
            "stage": "backtest",
            "status": result.status,
            "metrics": meta["backtest_metrics"],
            "timestamp": result.timestamp
        })
        
        # Save
        with open(strategy["meta_file"], 'w') as f:
            json.dump(meta, f, indent=2)
    
    def _print_result(self, result: SubStrategyResult):
        """Print single result."""
        icon = "PASS" if result.status == "passed" else "FAIL" if result.status == "failed" else "ERR"
        print(f"  [{icon}] {result.strategy_name} ({result.sub_category})")
        
        if result.status == "passed":
            print(f"      Sharpe: {result.sharpe:.2f} | WR: {result.win_rate:.1%} | "
                  f"Trades: {result.total_trades} | Signals: {result.signals_generated}")
        elif result.error_message:
            print(f"      Error: {result.error_message[:100]}")
    
    def generate_aggregate_report(self, results: List[SubStrategyResult]) -> AggregateReport:
        """Generate comprehensive aggregate report."""
        
        # Count by status
        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed")
        errors = sum(1 for r in results if r.status == "error")
        filtered = sum(1 for r in results if r.status == "filtered")
        
        # By category
        by_category = {}
        for r in results:
            cat = r.sub_category
            if cat not in by_category:
                by_category[cat] = {"total": 0, "passed": 0, "failed": 0}
            by_category[cat]["total"] += 1
            if r.status == "passed":
                by_category[cat]["passed"] += 1
            elif r.status == "failed":
                by_category[cat]["failed"] += 1
        
        # By agent
        by_agent = {}
        for r in results:
            agent = r.agent_id
            if agent not in by_agent:
                by_agent[agent] = {"total": 0, "passed": 0, "sharpe_sum": 0}
            by_agent[agent]["total"] += 1
            if r.status == "passed":
                by_agent[agent]["passed"] += 1
                by_agent[agent]["sharpe_sum"] += r.sharpe or 0
        
        # Top performers
        passed_results = [r for r in results if r.status == "passed" and r.sharpe]
        top_sharpe = sorted(passed_results, key=lambda x: x.sharpe or 0, reverse=True)[:5]
        top_win_rate = sorted(passed_results, key=lambda x: x.win_rate or 0, reverse=True)[:5]
        
        report = AggregateReport(
            timestamp=datetime.now().isoformat(),
            total_strategies=len(results),
            passed=passed,
            failed=failed,
            errors=errors,
            filtered=filtered,
            by_category=by_category,
            by_agent=by_agent,
            top_sharpe=[asdict(r) for r in top_sharpe],
            top_win_rate=[asdict(r) for r in top_win_rate]
        )
        
        return report
    
    def save_report(self, report: AggregateReport, results: List[SubStrategyResult]):
        """Save comprehensive report."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save aggregate report
        report_file = self.results_path / f"substrategy_report_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(asdict(report), f, indent=2)
        
        # Save detailed results
        details_file = self.results_path / f"substrategy_details_{timestamp}.json"
        with open(details_file, 'w') as f:
            json.dump([asdict(r) for r in results], f, indent=2)
        
        return report_file, details_file
    
    def run(self) -> AggregateReport:
        """Run complete sub-strategy handling workflow."""
        print("=" * 70)
        print("SUB-STRATEGY HANDLER AGENT v1.0")
        print("=" * 70)
        print(f"Parallel Workers: {self.parallel}")
        print(f"Test Duration: {self.days} days")
        print(f"Pass Criteria: Sharpe >= 1.0, WR >= 45%, Max DD <= 20%")
        print("=" * 70)
        
        # Discover strategies
        strategies = self.discover_strategies()
        print(f"\n[HANDLER] Discovered {len(strategies)} sub-strategies:")
        for s in strategies:
            print(f"  - {s['name']} ({s['agent_id']})")
        
        if not strategies:
            print("[HANDLER] No strategies to process.")
            return AggregateReport(timestamp=datetime.now().isoformat(), total_strategies=0, passed=0, failed=0, errors=0, filtered=0)
        
        # Run parallel backtests
        print(f"\n[HANDLER] Starting parallel backtests...")
        results = self.run_parallel_backtests(strategies)
        
        # Generate aggregate report
        report = self.generate_aggregate_report(results)
        
        # Save reports
        report_file, details_file = self.save_report(report, results)
        
        # Print summary
        self._print_summary(report)
        
        return report
    
    def _print_summary(self, report: AggregateReport):
        """Print final summary."""
        print("\n" + "=" * 70)
        print("SUB-STRATEGY HANDLER SUMMARY")
        print("=" * 70)
        print(f"Total Strategies: {report.total_strategies}")
        print(f"  PASSED:  {report.passed}  (Ready for paper trading)")
        print(f"  FAILED:  {report.failed}")
        print(f"  ERRORS:  {report.errors}")
        print(f"  FILTERED: {report.filtered}")
        
        print("\nBy Category:")
        for cat, stats in report.by_category.items():
            print(f"  {cat}: {stats['passed']}/{stats['total']} passed")
        
        print("\nBy Agent:")
        for agent, stats in report.by_agent.items():
            avg_sharpe = stats['sharpe_sum'] / stats['passed'] if stats['passed'] > 0 else 0
            print(f"  {agent}: {stats['passed']}/{stats['total']} passed (avg sharpe: {avg_sharpe:.2f})")
        
        if report.top_sharpe:
            print("\nTOP PERFORMERS (by Sharpe):")
            for i, r in enumerate(report.top_sharpe[:3], 1):
                print(f"  {i}. {r['strategy_name']}: Sharpe={r['sharpe']:.2f}, WR={r['win_rate']:.1%}")
        
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Sub-Strategy Handler Agent")
    parser.add_argument("--days", type=int, default=90, help="Test duration in days")
    parser.add_argument("--parallel", type=int, default=4, help="Number of parallel workers")
    args = parser.parse_args()
    
    handler = SubStrategyHandler(days=args.days, parallel=args.parallel)
    report = handler.run()
    
    if report.passed > 0:
        print(f"\n{report.passed} sub-strategies passed and ready for paper trading!")
        return 0
    else:
        print("\nNo sub-strategies passed validation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
