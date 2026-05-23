"""
Walk-Forward / Rolling-Origin Backtest Framework
================================================
Prevents overfitting by testing on data the model has never seen.

Train on data up to t, test on t+1…t+N, then roll forward.

This addresses the HIGH IMPACT issue: "We backtest on full history then go live. 
No walk-forward validation. This is the #1 cause of overfitting."

Usage:
    from walk_forward_validator import WalkForwardValidator
    
    wfv = WalkForwardValidator(
        train_window_days=30,
        test_window_days=7,
        min_train_trades=20,
        min_test_trades=5
    )
    
    results = wfv.validate_strategy(
        strategy_id="hurst_regime_adaptive",
        trades=historical_trades
    )
    
    if results['is_robust']:
        # Strategy passed walk-forward validation
        promote_to_core(strategy_id)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import statistics
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('WalkForwardValidator')


@dataclass
class WalkForwardWindow:
    """Single train/test window"""
    window_id: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    
    train_trades: List[Dict] = field(default_factory=list)
    test_trades: List[Dict] = field(default_factory=list)
    
    # Train metrics
    train_win_rate: float = 0.0
    train_expectancy: float = 0.0
    train_sharpe: float = 0.0
    
    # Test metrics
    test_win_rate: float = 0.0
    test_expectancy: float = 0.0
    test_sharpe: float = 0.0
    
    # Robustness score
    degradation: float = 0.0  # How much worse test is vs train
    passed: bool = False


@dataclass
class WalkForwardResults:
    """Complete walk-forward validation results"""
    strategy_id: str
    total_windows: int = 0
    passed_windows: int = 0
    failed_windows: int = 0
    
    avg_train_expectancy: float = 0.0
    avg_test_expectancy: float = 0.0
    avg_degradation: float = 0.0
    
    consistency_score: float = 0.0  # 0-1, how consistent across windows
    robustness_score: float = 0.0  # 0-1, overall robustness
    
    is_robust: bool = False
    recommendation: str = ""
    windows: List[WalkForwardWindow] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'strategy_id': self.strategy_id,
            'total_windows': self.total_windows,
            'passed_windows': self.passed_windows,
            'failed_windows': self.failed_windows,
            'pass_rate': round(self.passed_windows / max(self.total_windows, 1), 2),
            'avg_train_expectancy': round(self.avg_train_expectancy, 4),
            'avg_test_expectancy': round(self.avg_test_expectancy, 4),
            'avg_degradation': round(self.avg_degradation, 4),
            'consistency_score': round(self.consistency_score, 2),
            'robustness_score': round(self.robustness_score, 2),
            'is_robust': self.is_robust,
            'recommendation': self.recommendation
        }


class WalkForwardValidator:
    """
    Rolling-origin backtest validator
    
    Prevents overfitting by ensuring strategy works on out-of-sample data
    """
    
    def __init__(
        self,
        train_window_days: int = 30,
        test_window_days: int = 7,
        step_days: int = 7,
        min_train_trades: int = 10,
        min_test_trades: int = 3,
        max_degradation: float = 0.5,  # Test can be 50% worse than train
        min_pass_rate: float = 0.6,  # 60% of windows must pass
        min_consistency: float = 0.5  # Consistency threshold
    ):
        self.train_window_days = train_window_days
        self.test_window_days = test_window_days
        self.step_days = step_days
        self.min_train_trades = min_train_trades
        self.min_test_trades = min_test_trades
        self.max_degradation = max_degradation
        self.min_pass_rate = min_pass_rate
        self.min_consistency = min_consistency
    
    def create_windows(
        self,
        trades: List[Dict],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[WalkForwardWindow]:
        """
        Create rolling train/test windows from trade history
        """
        if not trades:
            return []
        
        # Sort trades by date
        sorted_trades = sorted(trades, key=lambda x: x.get('timestamp', ''))
        
        # Determine date range
        if not start_date:
            first_trade = sorted_trades[0]
            start_date = datetime.fromisoformat(first_trade['timestamp'].replace('Z', '+00:00'))
        
        if not end_date:
            last_trade = sorted_trades[-1]
            end_date = datetime.fromisoformat(last_trade['timestamp'].replace('Z', '+00:00'))
        
        windows = []
        window_id = 0
        current_date = start_date
        
        while current_date + timedelta(days=self.train_window_days + self.test_window_days) <= end_date:
            # Define window boundaries
            train_start = current_date
            train_end = current_date + timedelta(days=self.train_window_days)
            test_start = train_end
            test_end = test_start + timedelta(days=self.test_window_days)
            
            window = WalkForwardWindow(
                window_id=window_id,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end
            )
            
            # Assign trades to windows
            for trade in sorted_trades:
                trade_time = datetime.fromisoformat(trade.get('timestamp', '2020-01-01').replace('Z', '+00:00'))
                
                if train_start <= trade_time < train_end:
                    window.train_trades.append(trade)
                elif test_start <= trade_time < test_end:
                    window.test_trades.append(trade)
            
            # Only keep windows with sufficient data
            if (len(window.train_trades) >= self.min_train_trades and
                len(window.test_trades) >= self.min_test_trades):
                windows.append(window)
                window_id += 1
            
            # Step forward
            current_date += timedelta(days=self.step_days)
        
        return windows
    
    def calculate_metrics(self, trades: List[Dict]) -> Dict[str, float]:
        """Calculate performance metrics for a set of trades"""
        if not trades:
            return {'win_rate': 0, 'expectancy': 0, 'sharpe': 0}
        
        pnls = [t.get('pnl_percent', 0) for t in trades]
        wins = sum(1 for p in pnls if p > 0)
        
        win_rate = wins / len(trades)
        
        avg_pnl = statistics.mean(pnls)
        avg_win = statistics.mean([p for p in pnls if p > 0]) if wins > 0 else 0
        avg_loss = statistics.mean([p for p in pnls if p <= 0]) if wins < len(trades) else 0
        
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
        
        # Sharpe (simplified, assuming risk-free rate = 0)
        if len(pnls) > 1:
            try:
                std = statistics.stdev(pnls)
                sharpe = (avg_pnl / std) * math.sqrt(252) if std > 0 else 0  # Annualized
            except:
                sharpe = 0
        else:
            sharpe = 0
        
        return {
            'win_rate': win_rate,
            'expectancy': expectancy,
            'sharpe': sharpe,
            'avg_pnl': avg_pnl,
            'total_trades': len(trades)
        }
    
    def evaluate_window(self, window: WalkForwardWindow) -> WalkForwardWindow:
        """Evaluate a single train/test window"""
        # Calculate train metrics
        train_metrics = self.calculate_metrics(window.train_trades)
        window.train_win_rate = train_metrics['win_rate']
        window.train_expectancy = train_metrics['expectancy']
        window.train_sharpe = train_metrics['sharpe']
        
        # Calculate test metrics
        test_metrics = self.calculate_metrics(window.test_trades)
        window.test_win_rate = test_metrics['win_rate']
        window.test_expectancy = test_metrics['expectancy']
        window.test_sharpe = test_metrics['sharpe']
        
        # Calculate degradation
        if window.train_expectancy != 0:
            window.degradation = (window.train_expectancy - window.test_expectancy) / abs(window.train_expectancy)
        else:
            window.degradation = 0 if window.test_expectancy >= 0 else 1
        
        # Determine if window passes
        # Pass if: test expectancy > 0 AND degradation < max_degradation
        window.passed = (
            window.test_expectancy > 0 and
            window.degradation < self.max_degradation
        )
        
        return window
    
    def validate_strategy(
        self,
        strategy_id: str,
        trades: List[Dict]
    ) -> WalkForwardResults:
        """
        Run complete walk-forward validation on a strategy
        """
        results = WalkForwardResults(strategy_id=strategy_id)
        
        # Create windows
        windows = self.create_windows(trades)
        
        if len(windows) < 2:
            results.recommendation = "INSUFFICIENT_DATA"
            logger.warning(f"{strategy_id}: Only {len(windows)} windows, need at least 2")
            return results
        
        # Evaluate each window
        for window in windows:
            evaluated = self.evaluate_window(window)
            results.windows.append(evaluated)
            
            if evaluated.passed:
                results.passed_windows += 1
            else:
                results.failed_windows += 1
        
        results.total_windows = len(windows)
        
        # Calculate aggregate metrics
        if windows:
            results.avg_train_expectancy = statistics.mean([w.train_expectancy for w in windows])
            results.avg_test_expectancy = statistics.mean([w.test_expectancy for w in windows])
            results.avg_degradation = statistics.mean([w.degradation for w in windows])
            
            # Consistency score (low std = high consistency)
            test_expectancies = [w.test_expectancy for w in windows]
            if len(test_expectancies) > 1:
                try:
                    std_exp = statistics.stdev(test_expectancies)
                    mean_exp = statistics.mean(test_expectancies)
                    cv = std_exp / abs(mean_exp) if mean_exp != 0 else float('inf')
                    results.consistency_score = max(0, 1 - min(cv, 1))
                except:
                    results.consistency_score = 0
            
            # Robustness score
            pass_rate = results.passed_windows / results.total_windows
            degradation_penalty = max(0, results.avg_degradation)
            results.robustness_score = (
                pass_rate * 0.5 +
                results.consistency_score * 0.3 +
                (1 - degradation_penalty) * 0.2
            )
        
        # Final determination
        pass_rate = results.passed_windows / max(results.total_windows, 1)
        
        if pass_rate >= self.min_pass_rate and results.consistency_score >= self.min_consistency:
            results.is_robust = True
            results.recommendation = "APPROVED_FOR_CORE"
        elif pass_rate >= 0.4:
            results.is_robust = False
            results.recommendation = "INCUBATOR_ONLY"
        else:
            results.is_robust = False
            results.recommendation = "REJECT_OVERFIT"
        
        return results
    
    def batch_validate(
        self,
        strategies: Dict[str, List[Dict]]  # strategy_id -> trades
    ) -> Dict[str, WalkForwardResults]:
        """Validate multiple strategies"""
        results = {}
        
        for strategy_id, trades in strategies.items():
            logger.info(f"Validating {strategy_id}...")
            results[strategy_id] = self.validate_strategy(strategy_id, trades)
        
        return results
    
    def generate_validation_report(
        self,
        results: Dict[str, WalkForwardResults]
    ) -> Dict[str, Any]:
        """Generate summary report for all validations"""
        approved = []
        incubator = []
        rejected = []
        
        for strat_id, result in results.items():
            if result.recommendation == "APPROVED_FOR_CORE":
                approved.append({
                    'strategy_id': strat_id,
                    'robustness_score': result.robustness_score,
                    'test_expectancy': result.avg_test_expectancy
                })
            elif result.recommendation == "INCUBATOR_ONLY":
                incubator.append({
                    'strategy_id': strat_id,
                    'robustness_score': result.robustness_score,
                    'pass_rate': result.passed_windows / max(result.total_windows, 1)
                })
            else:
                rejected.append({
                    'strategy_id': strat_id,
                    'reason': 'Overfitting detected',
                    'degradation': result.avg_degradation
                })
        
        return {
            'validation_date': datetime.now().isoformat(),
            'parameters': {
                'train_window_days': self.train_window_days,
                'test_window_days': self.test_window_days,
                'min_pass_rate': self.min_pass_rate,
                'max_degradation': self.max_degradation
            },
            'summary': {
                'total_validated': len(results),
                'approved_for_core': len(approved),
                'incubator_only': len(incubator),
                'rejected': len(rejected),
                'approval_rate': round(len(approved) / len(results) * 100, 1) if results else 0
            },
            'approved_strategies': approved,
            'incubator_strategies': incubator,
            'rejected_strategies': rejected
        }


# Example usage
if __name__ == "__main__":
    import random
    
    print("=" * 80)
    print("WALK-FORWARD VALIDATOR - Demo")
    print("=" * 80)
    
    validator = WalkForwardValidator(
        train_window_days=30,
        test_window_days=7,
        step_days=7
    )
    
    # Generate synthetic trade data for demonstration
    def generate_trades(strategy_type: str, n: int = 100) -> List[Dict]:
        """Generate synthetic trade history"""
        trades = []
        base_date = datetime(2024, 1, 1)
        
        for i in range(n):
            # Create realistic patterns
            if strategy_type == "robust":
                # Consistent positive edge
                pnl = random.gauss(0.8, 2.0)
                win_rate = 0.55
            elif strategy_type == "overfit":
                # Great in-sample, poor out-of-sample
                if i < 70:
                    pnl = random.gauss(1.5, 1.5)  # Good in first 70%
                else:
                    pnl = random.gauss(-0.5, 2.0)  # Bad later
                win_rate = 0.6
            elif strategy_type == "noise":
                # Random, no edge
                pnl = random.gauss(0, 2.0)
                win_rate = 0.50
            else:
                pnl = random.gauss(0.2, 1.5)
                win_rate = 0.52
            
            trade_date = base_date + timedelta(days=i)
            trades.append({
                'timestamp': trade_date.isoformat(),
                'pnl_percent': pnl if random.random() < win_rate else -abs(pnl),
                'symbol': 'BTC-USDT'
            })
        
        return trades
    
    # Test different strategy types
    test_strategies = {
        'robust_trend_follower': generate_trades('robust', 150),
        'overfit_pattern': generate_trades('overfit', 150),
        'random_noise': generate_trades('noise', 150),
        'weak_edge': generate_trades('weak', 150)
    }
    
    results = validator.batch_validate(test_strategies)
    report = validator.generate_validation_report(results)
    
    print(f"\n[CHART] VALIDATION REPORT")
    print("-" * 80)
    print(f"Total Strategies: {report['summary']['total_validated']}")
    print(f"Approved for Core: {report['summary']['approved_for_core']}")
    print(f"Incubator Only: {report['summary']['incubator_only']}")
    print(f"Rejected: {report['summary']['rejected']}")
    print(f"Approval Rate: {report['summary']['approval_rate']}%")
    
    print(f"\n[LIST] STRATEGY DETAILS")
    print("-" * 80)
    print(f"{'Strategy':<30} {'Status':<20} {'Robustness':<12} {'Test Exp':<10}")
    print("-" * 80)
    
    for strat_id, result in results.items():
        print(f"{strat_id:<30} {result.recommendation:<20} "
              f"{result.robustness_score:<12.2f} {result.avg_test_expectancy:<10.2f}%")
    
    print("\n" + "=" * 80)
