"""
Consistency Tracker - Rolling Performance Metrics
==================================================
Tracks the stability of expectancy, Sharpe ratio, and other metrics
over rolling windows to detect edge decay early.

Key Metrics:
- Rolling 30-day Sharpe ratio
- Coefficient of Variation of expectancy (CV)
- Expectancy stability score
- Regime match rate
- Slippage drift

Based on feedback: "Optimize stability of expectancy, not WR"

Usage:
    from consistency_tracker import ConsistencyTracker
    
    tracker = ConsistencyTracker()
    
    # Add daily trade results
    tracker.add_trade('funding_carry', 1.2, datetime.now())
    
    # Get consistency report
    report = tracker.get_consistency_report('funding_carry')
    if report['sharpe_30d'] < 0.5:
        print("Strategy decaying - reduce size or pause")
"""

import json
import logging
import math
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ConsistencyTracker')


@dataclass
class RollingWindow:
    """Rolling window of trade data"""
    trades: deque = field(default_factory=lambda: deque(maxlen=100))
    window_days: int = 30
    
    def add_trade(self, pnl_percent: float, timestamp: datetime):
        """Add a trade to the window"""
        self.trades.append({
            'pnl': pnl_percent,
            'timestamp': timestamp
        })
        
        # Remove old trades
        cutoff = timestamp - timedelta(days=self.window_days)
        while self.trades and self.trades[0]['timestamp'] < cutoff:
            self.trades.popleft()
    
    def get_trades(self) -> List[Dict]:
        """Get trades in window"""
        return list(self.trades)
    
    def is_valid(self, min_trades: int = 10) -> bool:
        """Check if window has enough data"""
        return len(self.trades) >= min_trades


@dataclass
class ConsistencyMetrics:
    """Consistency metrics for a strategy"""
    strategy_id: str
    
    # Rolling metrics
    sharpe_30d: float = 0.0
    expectancy_30d: float = 0.0
    win_rate_30d: float = 0.0
    
    # Stability metrics
    cv_expectancy: float = 0.0  # Coefficient of variation
    expectancy_stability: float = 0.0  # 0-1 score
    sharpe_stability: float = 0.0
    
    # Regime metrics
    regime_match_rate: float = 0.0
    trades_in_good_regime: int = 0
    total_trades: int = 0
    
    # Execution metrics
    avg_slippage: float = 0.0
    slippage_drift: float = 0.0  # vs expected
    
    # Overall score
    consistency_score: float = 0.0  # 0-1 composite
    health_status: str = "insufficient_data"
    recommendation: str = "hold"


class ConsistencyTracker:
    """
    Track rolling consistency metrics for strategies
    
    Detects edge decay before it becomes a major drawdown
    """
    
    def __init__(
        self,
        sharpe_threshold: float = 0.5,
        cv_threshold: float = 0.5,
        min_trades_for_metrics: int = 10
    ):
        self.windows: Dict[str, RollingWindow] = defaultdict(
            lambda: RollingWindow(window_days=30)
        )
        self.historical_metrics: Dict[str, List[Dict]] = defaultdict(list)
        
        # Thresholds
        self.sharpe_threshold = sharpe_threshold
        self.cv_threshold = cv_threshold
        self.min_trades = min_trades_for_metrics
        
        # Load existing data
        self._load_data()
    
    def _load_data(self):
        """Load historical consistency data"""
        try:
            with open('consistency_tracker_data.json', 'r') as f:
                data = json.load(f)
                for strat_id, metrics_list in data.items():
                    self.historical_metrics[strat_id] = metrics_list
        except FileNotFoundError:
            pass
    
    def _save_data(self):
        """Save consistency data"""
        with open('consistency_tracker_data.json', 'w') as f:
            json.dump(dict(self.historical_metrics), f, indent=2, default=str)
    
    def add_trade(
        self,
        strategy_id: str,
        pnl_percent: float,
        timestamp: Optional[datetime] = None,
        expected_slippage: float = 0.1,
        actual_slippage: float = 0.1,
        regime: str = "unknown",
        good_regime: bool = True
    ):
        """
        Add a trade result
        
        Args:
            strategy_id: Strategy identifier
            pnl_percent: Trade PnL in percent
            timestamp: Trade timestamp
            expected_slippage: Expected slippage from model
            actual_slippage: Actual observed slippage
            regime: Market regime at trade time
            good_regime: Whether this was a good regime for the strategy
        """
        ts = timestamp or datetime.now()
        
        # Add to rolling window
        self.windows[strategy_id].add_trade(pnl_percent, ts)
        
        # Track slippage
        slippage_data = {
            'timestamp': ts.isoformat(),
            'expected': expected_slippage,
            'actual': actual_slippage,
            'drift': actual_slippage - expected_slippage,
            'regime': regime,
            'good_regime': good_regime
        }
        
        # Save to historical
        if strategy_id not in self.historical_metrics:
            self.historical_metrics[strategy_id] = []
        
        self.historical_metrics[strategy_id].append({
            'timestamp': ts.isoformat(),
            'pnl': pnl_percent,
            'slippage': slippage_data
        })
        
        self._save_data()
    
    def calculate_sharpe(self, trades: List[Dict], annualize: bool = True) -> float:
        """Calculate Sharpe ratio from trades"""
        if len(trades) < 5:
            return 0.0
        
        pnls = [t['pnl'] for t in trades]
        
        avg_pnl = statistics.mean(pnls)
        
        if len(pnls) > 1:
            try:
                std_pnl = statistics.stdev(pnls)
            except:
                return 0.0
        else:
            return 0.0
        
        if std_pnl == 0:
            return 0.0
        
        # Daily Sharpe (assuming trades are roughly daily)
        sharpe = avg_pnl / std_pnl
        
        if annualize:
            sharpe *= math.sqrt(252)
        
        return sharpe
    
    def calculate_cv(self, values: List[float]) -> float:
        """Calculate coefficient of variation (std/mean)"""
        if len(values) < 2:
            return 0.0
        
        mean_val = statistics.mean(values)
        if mean_val == 0:
            return 0.0
        
        try:
            std_val = statistics.stdev(values)
            return std_val / abs(mean_val)
        except:
            return 0.0
    
    def get_consistency_metrics(self, strategy_id: str) -> ConsistencyMetrics:
        """Calculate all consistency metrics for a strategy"""
        window = self.windows[strategy_id]
        trades = window.get_trades()
        
        metrics = ConsistencyMetrics(strategy_id=strategy_id)
        
        if not window.is_valid(self.min_trades):
            return metrics
        
        pnls = [t['pnl'] for t in trades]
        
        # Basic metrics
        metrics.total_trades = len(trades)
        metrics.expectancy_30d = statistics.mean(pnls)
        metrics.win_rate_30d = sum(1 for p in pnls if p > 0) / len(pnls)
        metrics.sharpe_30d = self.calculate_sharpe(trades)
        
        # Calculate rolling CV over sub-windows
        if len(trades) >= 20:
            # Split into 3 sub-windows for CV calculation
            sub_size = len(trades) // 3
            sub_expectancies = []
            for i in range(3):
                start = i * sub_size
                end = start + sub_size if i < 2 else len(trades)
                sub_pnls = pnls[start:end]
                if sub_pnls:
                    sub_expectancies.append(statistics.mean(sub_pnls))
            
            if sub_expectancies:
                metrics.cv_expectancy = self.calculate_cv(sub_expectancies)
        
        # Expectancy stability (inverse of CV, capped)
        metrics.expectancy_stability = max(0, 1 - min(metrics.cv_expectancy, 1))
        
        # Sharpe stability (is it positive and consistent?)
        if metrics.sharpe_30d > 0.5:
            metrics.sharpe_stability = min(metrics.sharpe_30d / 2.0, 1.0)
        
        # Regime metrics from historical data
        hist = self.historical_metrics.get(strategy_id, [])
        if hist:
            good_regime_trades = sum(1 for h in hist[-50:] if h.get('slippage', {}).get('good_regime', True))
            metrics.trades_in_good_regime = good_regime_trades
            metrics.regime_match_rate = good_regime_trades / min(len(hist[-50:]), 50)
        
        # Slippage drift
        if hist:
            recent = hist[-20:]
            if recent:
                avg_drift = statistics.mean([h.get('slippage', {}).get('drift', 0) for h in recent])
                metrics.slippage_drift = avg_drift
                metrics.avg_slippage = statistics.mean([h.get('slippage', {}).get('actual', 0) for h in recent])
        
        # Composite consistency score
        metrics.consistency_score = (
            metrics.expectancy_stability * 0.3 +
            metrics.sharpe_stability * 0.3 +
            metrics.regime_match_rate * 0.2 +
            (1 - min(abs(metrics.slippage_drift) * 10, 1)) * 0.2
        )
        
        # Health status
        if metrics.sharpe_30d < 0:
            metrics.health_status = "decaying"
            metrics.recommendation = "pause"
        elif metrics.sharpe_30d < self.sharpe_threshold:
            metrics.health_status = "weak"
            metrics.recommendation = "reduce_size"
        elif metrics.cv_expectancy > self.cv_threshold:
            metrics.health_status = "unstable"
            metrics.recommendation = "review"
        elif metrics.consistency_score > 0.7:
            metrics.health_status = "strong"
            metrics.recommendation = "hold"
        else:
            metrics.health_status = "acceptable"
            metrics.recommendation = "hold"
        
        return metrics
    
    def get_consistency_report(self, strategy_id: str) -> Dict[str, Any]:
        """Get full consistency report for a strategy"""
        metrics = self.get_consistency_metrics(strategy_id)
        
        return {
            'strategy_id': metrics.strategy_id,
            'timestamp': datetime.now().isoformat(),
            'rolling_30d': {
                'sharpe': round(metrics.sharpe_30d, 3),
                'expectancy': round(metrics.expectancy_30d, 4),
                'win_rate': round(metrics.win_rate_30d, 3),
                'trades': metrics.total_trades
            },
            'stability': {
                'cv_expectancy': round(metrics.cv_expectancy, 3),
                'expectancy_stability': round(metrics.expectancy_stability, 3),
                'sharpe_stability': round(metrics.sharpe_stability, 3),
                'consistency_score': round(metrics.consistency_score, 3)
            },
            'execution': {
                'avg_slippage': round(metrics.avg_slippage, 4),
                'slippage_drift': round(metrics.slippage_drift, 4),
                'regime_match_rate': round(metrics.regime_match_rate, 3)
            },
            'health': {
                'status': metrics.health_status,
                'recommendation': metrics.recommendation
            }
        }
    
    def get_all_strategies_report(self) -> Dict[str, Any]:
        """Get consistency report for all strategies"""
        all_strategies = set(self.windows.keys()) | set(self.historical_metrics.keys())
        
        reports = []
        for strat_id in all_strategies:
            report = self.get_consistency_report(strat_id)
            reports.append(report)
        
        # Sort by consistency score
        reports.sort(key=lambda x: x['stability']['consistency_score'], reverse=True)
        
        # Summary
        total = len(reports)
        strong = sum(1 for r in reports if r['health']['status'] == 'strong')
        decaying = sum(1 for r in reports if r['health']['status'] == 'decaying')
        
        return {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_strategies': total,
                'strong': strong,
                'decaying': decaying,
                'avg_consistency_score': round(
                    statistics.mean([r['stability']['consistency_score'] for r in reports]) if reports else 0, 3
                )
            },
            'strategies': reports
        }
    
    def should_reduce_size(self, strategy_id: str) -> Tuple[bool, str]:
        """Check if strategy size should be reduced"""
        metrics = self.get_consistency_metrics(strategy_id)
        
        if metrics.health_status == "decaying":
            return True, f"Sharpe {metrics.sharpe_30d:.2f} < 0, pausing"
        
        if metrics.health_status == "weak":
            return True, f"Sharpe {metrics.sharpe_30d:.2f} below threshold"
        
        if metrics.slippage_drift > 0.2:
            return True, f"Slippage drift {metrics.slippage_drift:.2f}% above limit"
        
        return False, "OK"


# Example usage
if __name__ == "__main__":
    import random
    
    print("=" * 80)
    print("CONSISTENCY TRACKER - Demo")
    print("=" * 80)
    
    tracker = ConsistencyTracker()
    
    # Generate synthetic trade data
    base_date = datetime.now() - timedelta(days=35)
    
    # Strategy 1: Consistent edge
    for i in range(40):
        pnl = random.gauss(0.8, 1.5)  # Positive drift, low vol
        tracker.add_trade(
            'consistent_strategy',
            pnl,
            base_date + timedelta(days=i),
            expected_slippage=0.1,
            actual_slippage=0.1 + random.gauss(0, 0.02),
            good_regime=True
        )
    
    # Strategy 2: Decaying edge
    for i in range(40):
        if i < 20:
            pnl = random.gauss(0.8, 1.5)  # Good early
        else:
            pnl = random.gauss(-0.3, 2.0)  # Bad later
        tracker.add_trade(
            'decaying_strategy',
            pnl,
            base_date + timedelta(days=i),
            expected_slippage=0.1,
            actual_slippage=0.15,  # Higher slippage
            good_regime=i < 25
        )
    
    # Get reports
    print("\n[CHART] CONSISTENT STRATEGY")
    print("-" * 80)
    report1 = tracker.get_consistency_report('consistent_strategy')
    print(f"Sharpe (30d): {report1['rolling_30d']['sharpe']}")
    print(f"Expectancy: {report1['rolling_30d']['expectancy']}%")
    print(f"CV: {report1['stability']['cv_expectancy']}")
    print(f"Consistency Score: {report1['stability']['consistency_score']}")
    print(f"Status: {report1['health']['status']} -> {report1['health']['recommendation']}")
    
    print("\n[CHART] DECAYING STRATEGY")
    print("-" * 80)
    report2 = tracker.get_consistency_report('decaying_strategy')
    print(f"Sharpe (30d): {report2['rolling_30d']['sharpe']}")
    print(f"Expectancy: {report2['rolling_30d']['expectancy']}%")
    print(f"CV: {report2['stability']['cv_expectancy']}")
    print(f"Consistency Score: {report2['stability']['consistency_score']}")
    print(f"Status: {report2['health']['status']} -> {report2['health']['recommendation']}")
    
    # Full report
    print("\n[LIST] ALL STRATEGIES SUMMARY")
    print("-" * 80)
    full_report = tracker.get_all_strategies_report()
    print(f"Total: {full_report['summary']['total_strategies']}")
    print(f"Strong: {full_report['summary']['strong']}")
    print(f"Decaying: {full_report['summary']['decaying']}")
    print(f"Avg Consistency: {full_report['summary']['avg_consistency_score']}")
    
    print("\n" + "=" * 80)
