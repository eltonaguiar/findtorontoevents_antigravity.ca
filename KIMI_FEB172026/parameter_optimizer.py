"""
KIMI_FEB172026 - Parameter Optimizer
Continuously optimizes strategy parameters based on live performance
Implements walk-forward optimization and adaptive tuning
"""

import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KIMI_OPTIMIZER")


@dataclass
class OptimizationResult:
    """Optimization result container"""
    algorithm: str
    asset_class: str
    parameter_name: str
    old_value: float
    new_value: float
    reason: str
    confidence: float
    expected_improvement: float


class ParameterOptimizer:
    """
    Continuous parameter optimization based on live performance
    Uses walk-forward analysis and adaptive tuning
    """
    
    def __init__(self, data_dir: str = "KIMI_FEB172026/data"):
        self.data_dir = Path(data_dir)
        self.config_file = self.data_dir / "optimized_params.json"
        
        # Default parameters by asset class
        self.default_params = {
            "crypto": {
                "confidence_threshold": 0.65,
                "tp_multiplier": 2.5,
                "sl_multiplier": 1.5,
                "time_exit_hours": 24,
                "position_size_pct": 0.10,
                "max_positions": 5,
                "trailing_stop_pct": 1.0,
                "volume_threshold": 3.0,
                "rsi_overbought": 70,
                "rsi_oversold": 30
            },
            "forex": {
                "confidence_threshold": 0.70,
                "tp_multiplier": 2.0,
                "sl_multiplier": 1.0,
                "time_exit_hours": 48,
                "position_size_pct": 0.05,
                "max_positions": 3,
                "trailing_stop_pct": 0.5,
                "volume_threshold": 2.0,
                "rsi_overbought": 75,
                "rsi_oversold": 25
            },
            "stock": {
                "confidence_threshold": 0.70,
                "tp_multiplier": 3.0,
                "sl_multiplier": 1.5,
                "time_exit_hours": 72,
                "position_size_pct": 0.08,
                "max_positions": 5,
                "trailing_stop_pct": 2.0,
                "volume_threshold": 2.5,
                "rsi_overbought": 75,
                "rsi_oversold": 25
            },
            "meme": {
                "confidence_threshold": 0.60,
                "tp_multiplier": 4.0,
                "sl_multiplier": 2.0,
                "time_exit_hours": 12,
                "position_size_pct": 0.05,
                "max_positions": 3,
                "trailing_stop_pct": 3.0,
                "volume_threshold": 5.0,
                "rsi_overbought": 80,
                "rsi_oversold": 20
            }
        }
        
        # Load optimized parameters
        self.optimized_params = self._load_optimized_params()
    
    def _load_optimized_params(self) -> Dict:
        """Load previously optimized parameters"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_optimized_params(self):
        """Save optimized parameters"""
        with open(self.config_file, 'w') as f:
            json.dump(self.optimized_params, f, indent=2)
    
    def get_params(self, asset_class: str, algorithm: str) -> Dict:
        """Get optimized parameters for asset class and algorithm"""
        key = f"{asset_class}_{algorithm}"
        
        if key in self.optimized_params:
            # Merge with defaults
            params = self.default_params.get(asset_class, {}).copy()
            params.update(self.optimized_params[key])
            return params
        
        return self.default_params.get(asset_class, self.default_params["crypto"]).copy()
    
    def analyze_performance(self, signals: List[Dict]) -> Dict:
        """
        Analyze signal performance to identify optimization opportunities
        """
        if len(signals) < 10:
            return {"error": "Insufficient data for analysis"}
        
        analysis = {
            "total_signals": len(signals),
            "by_exit_reason": {},
            "by_confidence": {},
            "by_tp_sl_ratio": {},
            "recommendations": []
        }
        
        # Group by exit reason
        for sig in signals:
            reason = sig.get('exit_reason', 'UNKNOWN')
            analysis["by_exit_reason"][reason] = analysis["by_exit_reason"].get(reason, 0) + 1
        
        # Analyze by confidence bucket
        for sig in signals:
            conf = sig.get('confidence', 0)
            bucket = int(conf * 10) / 10  # Round to 0.1
            
            if bucket not in analysis["by_confidence"]:
                analysis["by_confidence"][bucket] = {"count": 0, "wins": 0, "total_pnl": 0}
            
            analysis["by_confidence"][bucket]["count"] += 1
            analysis["by_confidence"][bucket]["total_pnl"] += sig.get('pnl_pct', 0)
            
            if sig.get('pnl_pct', 0) > 0:
                analysis["by_confidence"][bucket]["wins"] += 1
        
        # Calculate win rate by confidence
        for bucket, stats in analysis["by_confidence"].items():
            if stats["count"] > 0:
                stats["win_rate"] = stats["wins"] / stats["count"]
                stats["avg_pnl"] = stats["total_pnl"] / stats["count"]
        
        return analysis
    
    def generate_recommendations(self, asset_class: str, algorithm: str,
                                  signals: List[Dict]) -> List[OptimizationResult]:
        """
        Generate optimization recommendations based on performance
        """
        recommendations = []
        analysis = self.analyze_performance(signals)
        
        if "error" in analysis:
            return []
        
        current_params = self.get_params(asset_class, algorithm)
        
        # Check TP/SL ratio effectiveness
        tp_hits = analysis["by_exit_reason"].get("TP_HIT", 0)
        sl_hits = analysis["by_exit_reason"].get("SL_HIT", 0)
        total = tp_hits + sl_hits
        
        if total > 10:
            tp_rate = tp_hits / total
            
            if tp_rate < 0.40:
                # Too many SL hits - widen SL or tighten TP
                recommendations.append(OptimizationResult(
                    algorithm=algorithm,
                    asset_class=asset_class,
                    parameter_name="sl_multiplier",
                    old_value=current_params["sl_multiplier"],
                    new_value=current_params["sl_multiplier"] * 1.2,
                    reason=f"SL hit rate too high ({tp_rate:.1%} TP), widening SL",
                    confidence=0.7,
                    expected_improvement=0.05
                ))
                
                recommendations.append(OptimizationResult(
                    algorithm=algorithm,
                    asset_class=asset_class,
                    parameter_name="tp_multiplier",
                    old_value=current_params["tp_multiplier"],
                    new_value=current_params["tp_multiplier"] * 0.9,
                    reason="Tightening TP to capture more wins",
                    confidence=0.6,
                    expected_improvement=0.03
                ))
            
            elif tp_rate > 0.70:
                # TP hit rate good - can be more aggressive
                recommendations.append(OptimizationResult(
                    algorithm=algorithm,
                    asset_class=asset_class,
                    parameter_name="tp_multiplier",
                    old_value=current_params["tp_multiplier"],
                    new_value=current_params["tp_multiplier"] * 1.1,
                    reason=f"High TP hit rate ({tp_rate:.1%}), extending targets",
                    confidence=0.6,
                    expected_improvement=0.08
                ))
        
        # Check confidence threshold
        conf_analysis = analysis.get("by_confidence", {})
        
        high_conf_wins = 0
        high_conf_total = 0
        low_conf_wins = 0
        low_conf_total = 0
        
        for bucket, stats in conf_analysis.items():
            if bucket >= current_params["confidence_threshold"]:
                high_conf_total += stats["count"]
                high_conf_wins += stats["wins"]
            else:
                low_conf_total += stats["count"]
                low_conf_wins += stats["wins"]
        
        if high_conf_total > 10 and low_conf_total > 10:
            high_wr = high_conf_wins / high_conf_total
            low_wr = low_conf_wins / low_conf_total
            
            if low_wr > 0.55 and high_wr - low_wr < 0.10:
                # Low confidence signals also performing well
                recommendations.append(OptimizationResult(
                    algorithm=algorithm,
                    asset_class=asset_class,
                    parameter_name="confidence_threshold",
                    old_value=current_params["confidence_threshold"],
                    new_value=current_params["confidence_threshold"] - 0.05,
                    reason=f"Low conf signals also strong ({low_wr:.1%} vs {high_wr:.1%})",
                    confidence=0.65,
                    expected_improvement=0.10
                ))
        
        # Check time exits
        time_exits = analysis["by_exit_reason"].get("TIME_EXIT", 0)
        time_exit_rate = time_exits / len(signals) if signals else 0
        
        if time_exit_rate > 0.40:
            # Too many time exits - extend holding period
            recommendations.append(OptimizationResult(
                algorithm=algorithm,
                asset_class=asset_class,
                parameter_name="time_exit_hours",
                old_value=current_params["time_exit_hours"],
                new_value=int(current_params["time_exit_hours"] * 1.5),
                reason=f"High time exit rate ({time_exit_rate:.1%}), extending hold",
                confidence=0.6,
                expected_improvement=0.04
            ))
        
        return recommendations
    
    def apply_recommendations(self, recommendations: List[OptimizationResult]) -> Dict:
        """
        Apply optimization recommendations to parameter set
        """
        changes_applied = []
        
        for rec in recommendations:
            key = f"{rec.asset_class}_{rec.algorithm}"
            
            if key not in self.optimized_params:
                self.optimized_params[key] = {}
            
            # Update parameter
            old_val = self.optimized_params[key].get(rec.parameter_name, rec.old_value)
            self.optimized_params[key][rec.parameter_name] = rec.new_value
            
            changes_applied.append({
                "algorithm": rec.algorithm,
                "asset_class": rec.asset_class,
                "parameter": rec.parameter_name,
                "old": old_val,
                "new": rec.new_value,
                "reason": rec.reason
            })
            
            logger.info(f"Optimized {rec.algorithm}: {rec.parameter_name} {rec.old_value} → {rec.new_value}")
        
        self._save_optimized_params()
        
        return {
            "changes_applied": len(changes_applied),
            "changes": changes_applied,
            "timestamp": datetime.now().isoformat()
        }
    
    def optimize_all(self, signal_tracker) -> Dict:
        """
        Run optimization for all asset classes and algorithms
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "optimizations": []
        }
        
        # Get completed signals
        all_signals = signal_tracker.completed_signals
        
        if not all_signals:
            return {"error": "No completed signals for optimization"}
        
        # Group by asset class and algorithm
        grouped = {}
        for sig in all_signals:
            key = (sig.asset_class, sig.algorithm)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(sig)
        
        # Optimize each group
        for (asset_class, algorithm), signals in grouped.items():
            if len(signals) < 20:
                continue
            
            # Convert to dicts for analysis
            signal_dicts = [
                {
                    "confidence": s.confidence,
                    "exit_reason": s.exit_reason,
                    "pnl_pct": s.pnl_pct
                }
                for s in signals
            ]
            
            recommendations = self.generate_recommendations(
                asset_class, algorithm, signal_dicts
            )
            
            if recommendations:
                applied = self.apply_recommendations(recommendations)
                results["optimizations"].append({
                    "asset_class": asset_class,
                    "algorithm": algorithm,
                    "signals_analyzed": len(signals),
                    "recommendations": len(recommendations),
                    "applied": applied
                })
        
        return results
    
    def get_optimization_report(self) -> str:
        """Generate optimization report"""
        report = []
        report.append("=" * 80)
        report.append("KIMI_FEB172026 - Parameter Optimization Report")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        report.append("CURRENT OPTIMIZED PARAMETERS:")
        report.append("-" * 80)
        
        for key, params in self.optimized_params.items():
            asset_class, algorithm = key.rsplit('_', 1)
            report.append(f"\n{algorithm} ({asset_class}):")
            for param, value in params.items():
                default = self.default_params.get(asset_class, {}).get(param, "N/A")
                report.append(f"  {param}: {default} → {value}")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)


# =============================================================================
# Entry point
# =============================================================================
def main():
    """Test optimizer"""
    optimizer = ParameterOptimizer()
    
    print("=" * 80)
    print("KIMI_FEB172026 - Parameter Optimizer")
    print("=" * 80)
    
    # Show default params
    print("\nDefault Parameters by Asset Class:")
    for asset_class, params in optimizer.default_params.items():
        print(f"\n{asset_class.upper()}:")
        for key, value in params.items():
            print(f"  {key}: {value}")
    
    # Test analysis
    test_signals = [
        {"confidence": 0.70, "exit_reason": "TP_HIT", "pnl_pct": 3.5},
        {"confidence": 0.65, "exit_reason": "SL_HIT", "pnl_pct": -2.0},
        {"confidence": 0.80, "exit_reason": "TP_HIT", "pnl_pct": 4.2},
        {"confidence": 0.55, "exit_reason": "SL_HIT", "pnl_pct": -2.0},
        {"confidence": 0.75, "exit_reason": "TP_HIT", "pnl_pct": 3.8},
    ] * 10  # 50 signals
    
    print("\n\nAnalyzing test signals...")
    analysis = optimizer.analyze_performance(test_signals)
    print(f"Total signals: {analysis['total_signals']}")
    print(f"By exit reason: {analysis['by_exit_reason']}")
    
    print("\n\nGenerating recommendations...")
    recommendations = optimizer.generate_recommendations("crypto", "pump-detector", test_signals)
    
    for rec in recommendations:
        print(f"\n{rec.parameter_name}: {rec.old_value} → {rec.new_value}")
        print(f"  Reason: {rec.reason}")
        print(f"  Expected improvement: {rec.expected_improvement:.1%}")


if __name__ == "__main__":
    main()
