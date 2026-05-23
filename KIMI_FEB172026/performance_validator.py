"""
KIMI_FEB172026 - Performance Validator
Continuously validates system performance and auto-tunes parameters
"""

import json
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger("KIMI_VALIDATOR")


class PerformanceValidator:
    """
    Validates trading performance and recommends system adjustments
    Self-tuning to optimize win rate and risk-adjusted returns
    """
    
    def __init__(self, data_dir: str = "KIMI_FEB172026/data"):
        self.data_dir = Path(data_dir)
        self.validation_history = []
        
        # Performance thresholds
        self.thresholds = {
            "min_win_rate": 0.55,  # 55% minimum
            "target_win_rate": 0.65,  # 65% target
            "min_sharpe": 1.0,
            "target_sharpe": 1.5,
            "max_drawdown": 0.15,  # 15% max
            "min_profit_factor": 1.3,
            "consecutive_losses": 5  # Alert after 5 losses
        }
    
    def validate_performance(self, days: int = 7) -> Dict:
        """
        Validate recent performance and generate recommendations
        """
        from sqlite_store import SQLiteStore
        
        store = SQLiteStore(str(self.data_dir / "kimi_trading.db"))
        
        # Get recent picks
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        df = store.get_picks(start_date=cutoff, limit=1000)
        
        if df.empty or len(df) < 10:
            return {
                "status": "insufficient_data",
                "message": f"Need at least 10 picks, have {len(df)}",
                "recommendations": []
            }
        
        # Calculate metrics
        closed = df[df['status'].isin(['WON', 'LOST'])]
        
        if len(closed) < 5:
            return {
                "status": "insufficient_closed",
                "message": f"Need at least 5 closed picks, have {len(closed)}",
                "recommendations": []
            }
        
        wins = len(closed[closed['status'] == 'WON'])
        losses = len(closed[closed['status'] == 'LOST'])
        win_rate = wins / len(closed) if len(closed) > 0 else 0
        
        # P&L metrics
        pnls = closed['pnl_pct'].tolist()
        total_pnl = sum(pnls)
        avg_pnl = np.mean(pnls) if pnls else 0
        
        # Sharpe ratio (simplified)
        returns = np.array(pnls) / 100  # Convert to decimal
        sharpe = 0
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252)
        
        # Profit factor
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Max drawdown calculation
        cumulative = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max if len(running_max) > 0 else np.array([0])
        max_dd = abs(min(drawdown.min(), 0)) / 100 if len(drawdown) > 0 else 0
        
        # Check consecutive losses
        consecutive_losses = 0
        max_consecutive = 0
        for status in closed['status'].values:
            if status == 'LOST':
                consecutive_losses += 1
                max_consecutive = max(max_consecutive, consecutive_losses)
            else:
                consecutive_losses = 0
        
        # Generate recommendations
        recommendations = []
        
        if win_rate < self.thresholds["min_win_rate"]:
            recommendations.append({
                "priority": "HIGH",
                "type": "win_rate_low",
                "message": f"Win rate {win_rate:.1%} below minimum {self.thresholds['min_win_rate']:.1%}",
                "action": "Increase confidence threshold to 0.70+ or reduce signal frequency"
            })
        
        if sharpe < self.thresholds["min_sharpe"]:
            recommendations.append({
                "priority": "MEDIUM",
                "type": "sharpe_low",
                "message": f"Sharpe {sharpe:.2f} below minimum {self.thresholds['min_sharpe']}",
                "action": "Review risk management - tighten stops or reduce position size"
            })
        
        if max_dd > self.thresholds["max_drawdown"]:
            recommendations.append({
                "priority": "HIGH",
                "type": "drawdown_high",
                "message": f"Max drawdown {max_dd:.1%} exceeds {self.thresholds['max_drawdown']:.1%}",
                "action": "IMMEDIATE: Reduce position sizes by 50% and review algo selection"
            })
        
        if profit_factor < self.thresholds["min_profit_factor"]:
            recommendations.append({
                "priority": "MEDIUM",
                "type": "profit_factor_low",
                "message": f"Profit factor {profit_factor:.2f} below {self.thresholds['min_profit_factor']}",
                "action": "Review R:R ratios - aim for minimum 1:2 on all trades"
            })
        
        if max_consecutive >= self.thresholds["consecutive_losses"]:
            recommendations.append({
                "priority": "HIGH",
                "type": "consecutive_losses",
                "message": f"{max_consecutive} consecutive losses detected",
                "action": "PAUSE: Stop new positions and review market conditions"
            })
        
        # Performance trends
        if len(pnls) >= 20:
            first_half = pnls[:len(pnls)//2]
            second_half = pnls[len(pnls)//2:]
            
            first_wr = len([p for p in first_half if p > 0]) / len(first_half)
            second_wr = len([p for p in second_half if p > 0]) / len(second_half)
            
            if second_wr < first_wr - 0.1:
                recommendations.append({
                    "priority": "MEDIUM",
                    "type": "deteriorating",
                    "message": f"Win rate declining: {first_wr:.1%} → {second_wr:.1%}",
                    "action": "Review and potentially eliminate underperforming algos"
                })
        
        # Overall status
        if not recommendations:
            status = "healthy"
        elif any(r["priority"] == "HIGH" for r in recommendations):
            status = "critical"
        else:
            status = "warning"
        
        validation_result = {
            "timestamp": datetime.now().isoformat(),
            "period_days": days,
            "status": status,
            "metrics": {
                "total_picks": len(df),
                "closed_picks": len(closed),
                "win_rate": round(win_rate, 4),
                "total_pnl_pct": round(total_pnl, 4),
                "avg_pnl_pct": round(avg_pnl, 4),
                "sharpe_ratio": round(sharpe, 4),
                "profit_factor": round(profit_factor, 4),
                "max_drawdown_pct": round(max_dd, 4),
                "max_consecutive_losses": max_consecutive
            },
            "recommendations": recommendations,
            "thresholds": self.thresholds
        }
        
        # Save validation
        self._save_validation(validation_result)
        
        return validation_result
    
    def _save_validation(self, result: Dict):
        """Save validation result to history"""
        self.validation_history.append(result)
        
        # Keep only last 100 validations
        self.validation_history = self.validation_history[-100:]
        
        # Save to file
        validation_path = self.data_dir / "validation_history.json"
        with open(validation_path, 'w') as f:
            json.dump(self.validation_history, f, indent=2)
    
    def auto_tune(self, validation_result: Dict) -> Dict:
        """
        Auto-tune system parameters based on validation
        """
        config_path = self.data_dir / "autonomous_config.json"
        
        if not config_path.exists():
            return {"status": "no_config"}
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        changes = []
        metrics = validation_result.get("metrics", {})
        
        # Tune confidence threshold based on win rate
        win_rate = metrics.get("win_rate", 0.5)
        current_threshold = config.get("min_confidence_threshold", 0.65)
        
        if win_rate < 0.50 and current_threshold < 0.75:
            # Too many losses, increase threshold
            old_threshold = current_threshold
            config["min_confidence_threshold"] = min(0.80, current_threshold + 0.05)
            changes.append({
                "parameter": "min_confidence_threshold",
                "old": old_threshold,
                "new": config["min_confidence_threshold"],
                "reason": f"Win rate {win_rate:.1%} too low"
            })
        elif win_rate > 0.75 and current_threshold > 0.50:
            # Win rate excellent, can lower threshold for more signals
            old_threshold = current_threshold
            config["min_confidence_threshold"] = max(0.50, current_threshold - 0.03)
            changes.append({
                "parameter": "min_confidence_threshold",
                "old": old_threshold,
                "new": config["min_confidence_threshold"],
                "reason": f"Win rate {win_rate:.1%} excellent, allowing more signals"
            })
        
        # Tune position size based on drawdown
        max_dd = metrics.get("max_drawdown_pct", 0)
        current_size = config.get("position_size_usd", 1000)
        
        if max_dd > 0.15:
            # High drawdown, reduce position size
            old_size = current_size
            config["position_size_usd"] = int(current_size * 0.7)
            changes.append({
                "parameter": "position_size_usd",
                "old": old_size,
                "new": config["position_size_usd"],
                "reason": f"Max drawdown {max_dd:.1%} too high"
            })
        elif max_dd < 0.05 and metrics.get("sharpe_ratio", 0) > 1.5:
            # Low drawdown and high sharpe, can increase size
            old_size = current_size
            config["position_size_usd"] = int(current_size * 1.1)
            changes.append({
                "parameter": "position_size_usd",
                "old": old_size,
                "new": config["position_size_usd"],
                "reason": "Strong performance, increasing exposure"
            })
        
        # Save updated config
        config["last_tuned"] = datetime.now().isoformat()
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return {
            "status": "tuned",
            "changes": changes,
            "config": config
        }
    
    def generate_report(self) -> str:
        """Generate a text report of current performance"""
        result = self.validate_performance(days=7)
        
        report = []
        report.append("=" * 80)
        report.append("KIMI_FEB172026 - Performance Validation Report")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Status: {result['status'].upper()}")
        report.append("")
        
        metrics = result["metrics"]
        report.append("METRICS (Last 7 Days):")
        report.append(f"  Total Picks:     {metrics['total_picks']}")
        report.append(f"  Closed Picks:    {metrics['closed_picks']}")
        report.append(f"  Win Rate:        {metrics['win_rate']:.1%}")
        report.append(f"  Total P&L:       {metrics['total_pnl_pct']:+.2f}%")
        report.append(f"  Avg P&L/Trade:   {metrics['avg_pnl_pct']:+.2f}%")
        report.append(f"  Sharpe Ratio:    {metrics['sharpe_ratio']:.2f}")
        report.append(f"  Profit Factor:   {metrics['profit_factor']:.2f}")
        report.append(f"  Max Drawdown:    {metrics['max_drawdown_pct']:.2f}%")
        report.append("")
        
        if result["recommendations"]:
            report.append("RECOMMENDATIONS:")
            for rec in result["recommendations"]:
                report.append(f"  [{rec['priority']}] {rec['message']}")
                report.append(f"    Action: {rec['action']}")
                report.append("")
        else:
            report.append("RECOMMENDATIONS: System performing well - no changes needed")
        
        report.append("=" * 80)
        
        return "\n".join(report)


def main():
    """Run validation as standalone script"""
    validator = PerformanceValidator()
    
    print(validator.generate_report())
    
    # Auto-tune
    result = validator.validate_performance()
    tune_result = validator.auto_tune(result)
    
    if tune_result.get("changes"):
        print("\n" + "=" * 80)
        print("AUTO-TUNING CHANGES:")
        print("=" * 80)
        for change in tune_result["changes"]:
            print(f"  {change['parameter']}: {change['old']} → {change['new']}")
            print(f"    Reason: {change['reason']}")


if __name__ == "__main__":
    main()
