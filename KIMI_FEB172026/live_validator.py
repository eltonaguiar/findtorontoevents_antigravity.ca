"""
KIMI_FEB172026 - Live Validator
Continuous validation and tuning system
Tracks signals, validates outcomes, optimizes parameters
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Import our modules
from signal_tracker import SignalTracker
from backtest_engine import BacktestEngine
from parameter_optimizer import ParameterOptimizer
from asset_strategies import get_strategy_for_asset, get_config_for_asset
from sqlite_store import SQLiteStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KIMI_LIVE_VALIDATOR")


class LiveValidator:
    """
    Continuous validation and optimization system
    - Tracks all signals in real-time
    - Validates outcomes against live market
    - Optimizes parameters based on results
    - Generates performance reports
    """
    
    def __init__(self):
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.tracker = SignalTracker(str(self.data_dir))
        self.backtest = BacktestEngine(str(self.data_dir))
        self.optimizer = ParameterOptimizer(str(self.data_dir))
        self.store = SQLiteStore(str(self.data_dir / "kimi_trading.db"))
        
        # Validation schedule
        self.validation_interval_hours = 4
        self.optimization_interval_hours = 24
        self.report_interval_hours = 168  # Weekly
        
        self.last_validation = None
        self.last_optimization = None
        self.validation_count = 0
        
        logger.info("Live Validator initialized")
    
    async def run_validation_cycle(self):
        """
        Run one validation cycle
        1. Check outcomes of active signals
        2. Update performance metrics
        3. Generate validation report
        """
        logger.info("=" * 80)
        logger.info("Running validation cycle...")
        logger.info("=" * 80)
        
        # 1. Check all active signals against live market
        await self.tracker.check_all_outcomes()
        
        # 2. Calculate performance by asset class
        performance = self._calculate_performance()
        
        # 3. Validate against targets
        validation = self._validate_performance(performance)
        
        # 4. Save validation results
        self._save_validation(validation)
        
        self.last_validation = datetime.now()
        self.validation_count += 1
        
        logger.info(f"Validation cycle {self.validation_count} complete")
        
        return validation
    
    def _calculate_performance(self) -> Dict:
        """Calculate performance metrics for all asset classes"""
        performance = {}
        
        for asset_class in ["crypto", "forex", "stock", "meme"]:
            stats = self.tracker.get_performance_stats(
                days=7,
                asset_class=asset_class
            )
            
            if "error" not in stats:
                performance[asset_class] = stats
        
        # Overall performance
        all_stats = self.tracker.get_performance_stats(days=7)
        performance["overall"] = all_stats
        
        return performance
    
    def _validate_performance(self, performance: Dict) -> Dict:
        """
        Validate performance against targets
        Generate recommendations
        """
        validation = {
            "timestamp": datetime.now().isoformat(),
            "validation_number": self.validation_count,
            "performance": performance,
            "status": "healthy",  # healthy, warning, critical
            "recommendations": [],
            "alerts": []
        }
        
        # Targets
        targets = {
            "min_win_rate": 0.55,
            "target_win_rate": 0.65,
            "min_sharpe": 1.0,
            "target_sharpe": 1.5,
            "max_drawdown": 0.15
        }
        
        # Check each asset class
        for asset_class, stats in performance.items():
            if asset_class == "overall":
                continue
            
            win_rate = stats.get("win_rate", 0)
            sharpe = stats.get("sharpe_ratio", 0)
            max_dd = stats.get("max_drawdown_pct", 0) / 100
            
            # Win rate check
            if win_rate < targets["min_win_rate"]:
                validation["alerts"].append({
                    "severity": "high",
                    "asset_class": asset_class,
                    "metric": "win_rate",
                    "value": win_rate,
                    "target": targets["min_win_rate"],
                    "message": f"{asset_class} win rate {win_rate:.1%} below minimum {targets['min_win_rate']:.1%}"
                })
                validation["status"] = "warning"
            
            # Sharpe check
            if sharpe < targets["min_sharpe"]:
                validation["alerts"].append({
                    "severity": "medium",
                    "asset_class": asset_class,
                    "metric": "sharpe",
                    "value": sharpe,
                    "target": targets["min_sharpe"],
                    "message": f"{asset_class} Sharpe {sharpe:.2f} below minimum {targets['min_sharpe']}"
                })
            
            # Drawdown check
            if max_dd > targets["max_drawdown"]:
                validation["alerts"].append({
                    "severity": "critical",
                    "asset_class": asset_class,
                    "metric": "max_drawdown",
                    "value": max_dd,
                    "target": targets["max_drawdown"],
                    "message": f"{asset_class} drawdown {max_dd:.1%} exceeds maximum {targets['max_drawdown']:.1%}"
                })
                validation["status"] = "critical"
        
        # Generate recommendations
        if validation["alerts"]:
            validation["recommendations"] = self._generate_recommendations(validation["alerts"])
        
        return validation
    
    def _generate_recommendations(self, alerts: List[Dict]) -> List[Dict]:
        """Generate optimization recommendations from alerts"""
        recommendations = []
        
        for alert in alerts:
            asset_class = alert["asset_class"]
            metric = alert["metric"]
            
            if metric == "win_rate":
                recommendations.append({
                    "priority": "high",
                    "action": "increase_confidence_threshold",
                    "asset_class": asset_class,
                    "current": get_config_for_asset(asset_class).confidence_threshold,
                    "recommended": min(0.85, get_config_for_asset(asset_class).confidence_threshold + 0.05),
                    "reason": "Win rate below target - filtering for higher quality signals"
                })
            
            elif metric == "sharpe":
                recommendations.append({
                    "priority": "medium",
                    "action": "adjust_position_sizing",
                    "asset_class": asset_class,
                    "reason": "Sharpe ratio low - review risk management"
                })
            
            elif metric == "max_drawdown":
                recommendations.append({
                    "priority": "critical",
                    "action": "reduce_exposure",
                    "asset_class": asset_class,
                    "reason": "Drawdown too high - immediate risk reduction required"
                })
        
        return recommendations
    
    def _save_validation(self, validation: Dict):
        """Save validation results"""
        validation_file = self.data_dir / "validation_results.json"
        
        # Load existing
        if validation_file.exists():
            with open(validation_file, 'r') as f:
                history = json.load(f)
        else:
            history = []
        
        # Add new validation
        history.append(validation)
        
        # Keep last 100 validations
        history = history[-100:]
        
        # Save
        with open(validation_file, 'w') as f:
            json.dump(history, f, indent=2, default=str)
    
    async def run_optimization(self) -> Dict:
        """
        Run parameter optimization based on recent performance
        """
        logger.info("=" * 80)
        logger.info("Running parameter optimization...")
        logger.info("=" * 80)
        
        # Run optimizer
        result = self.optimizer.optimize_all(self.tracker)
        
        self.last_optimization = datetime.now()
        
        logger.info(f"Optimization complete: {len(result.get('optimizations', []))} strategies updated")
        
        return result
    
    def generate_report(self) -> str:
        """Generate comprehensive validation report"""
        report = []
        report.append("=" * 80)
        report.append("KIMI_FEB172026 - Live Validation Report")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Validations Run: {self.validation_count}")
        report.append(f"Active Signals: {len(self.tracker.active_signals)}")
        report.append(f"Completed Signals: {len(self.tracker.completed_signals)}")
        report.append("")
        
        # Performance by asset class
        performance = self._calculate_performance()
        
        report.append("PERFORMANCE BY ASSET CLASS (7 Days):")
        report.append("-" * 80)
        
        for asset_class, stats in performance.items():
            if asset_class == "overall":
                continue
            
            report.append(f"\n{asset_class.upper()}:")
            report.append(f"  Signals: {stats.get('total_signals', 0)}")
            report.append(f"  Win Rate: {stats.get('win_rate', 0):.1%}")
            report.append(f"  Total P&L: {stats.get('total_pnl_pct', 0):+.2f}%")
            report.append(f"  Sharpe: {stats.get('sharpe_ratio', 0):.2f}")
            report.append(f"  Profit Factor: {stats.get('profit_factor', 0):.2f}")
            report.append(f"  TP/SL/Time: {stats.get('tp_hits', 0)}/{stats.get('sl_hits', 0)}/{stats.get('time_exits', 0)}")
        
        # Overall
        if "overall" in performance:
            overall = performance["overall"]
            report.append("\n" + "=" * 80)
            report.append("OVERALL PERFORMANCE:")
            report.append("-" * 80)
            report.append(f"Total Signals: {overall.get('total_signals', 0)}")
            report.append(f"Win Rate: {overall.get('win_rate', 0):.1%}")
            report.append(f"Total Return: {overall.get('total_pnl_pct', 0):+.2f}%")
            report.append(f"Sharpe Ratio: {overall.get('sharpe_ratio', 0):.2f}")
            report.append(f"Max Drawdown: {overall.get('max_drawdown_pct', 0):.2f}%")
        
        # Algorithm breakdown
        report.append("\n" + "=" * 80)
        report.append("ALGORITHM PERFORMANCE:")
        report.append("-" * 80)
        
        algo_perf = self.tracker.get_algorithm_performance()
        for algo in algo_perf[:10]:
            report.append(f"\n{algo['algorithm']}:")
            report.append(f"  Signals: {algo['total_signals']}, Wins: {algo['wins']}, Losses: {algo['losses']}")
            report.append(f"  Win Rate: {algo['win_rate']:.1%}, Total P&L: {algo['total_pnl_pct']:+.2f}%")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)
    
    async def run_continuous(self):
        """Run validation continuously"""
        logger.info("Starting continuous validation...")
        
        while True:
            try:
                # Run validation cycle
                await self.run_validation_cycle()
                
                # Check if optimization needed
                if (self.last_optimization is None or 
                    (datetime.now() - self.last_optimization).total_seconds() > 
                    self.optimization_interval_hours * 3600):
                    
                    await self.run_optimization()
                
                # Save report
                report = self.generate_report()
                report_file = self.data_dir / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
                with open(report_file, 'w') as f:
                    f.write(report)
                
                logger.info(f"Report saved to {report_file}")
                
                # Wait for next cycle
                await asyncio.sleep(self.validation_interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"Error in validation loop: {e}")
                await asyncio.sleep(300)  # 5 min retry


# =============================================================================
# Entry point
# =============================================================================
async def main():
    """Run live validator"""
    print("=" * 80)
    print("KIMI_FEB172026 - Live Validation System")
    print("=" * 80)
    print("\nThis system will:")
    print("1. Track all signals and validate outcomes")
    print("2. Calculate performance metrics every 4 hours")
    print("3. Optimize parameters every 24 hours")
    print("4. Generate performance reports")
    print("\nPress Ctrl+C to stop")
    print("=" * 80)
    
    validator = LiveValidator()
    
    # Run one validation immediately
    await validator.run_validation_cycle()
    
    # Print report
    print("\n" + validator.generate_report())
    
    # Start continuous validation
    await validator.run_continuous()


if __name__ == "__main__":
    asyncio.run(main())
