#!/usr/bin/env python3
"""
System Registry - Track and manage all trading systems

Maintains reliability scores, performance history, and status for all trading
systems in the crypto prediction ecosystem.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

class SystemRegistry:
    """
    Registry for tracking all trading systems, their reliability,
    performance history, and current status.
    """
    
    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize system registry.
        
        Args:
            registry_path: Path to registry JSON file
        """
        if registry_path is None:
            registry_path = Path(__file__).resolve().parent / "data" / "system_registry.json"
        
        self.registry_path = registry_path
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Known systems with categories
        self.known_systems = [
            # Core ML Systems
            "alpha_engine",
            "ml_crypto_predictor",
            "crypto_ml_edge",
            "mercury2",
            "claude_gainer_ml",
            "crypto_gainer_ml",
            
            # Strategy DNA Systems
            "strategy_dna",
            "meta_strategy",
            "baby_strategies",
            
            # Signal Engines
            "signal_engine",
            "breakout_arena",
            "regime_terminal",
            
            # Trading Systems
            "kimi_rotc",
            "kimi_feb17",
            "riseoftheclaw",
            
            # Alternative Systems
            "social_predict",
            "goldmine",
            "stocks_comp",
            
            # Battleground Systems
            "ml_battleground",
            "quantum_fusion",
        ]
        
        # System categories for weight adjustments
        self.system_categories = {
            "ml_heavy": ["ml_crypto_predictor", "crypto_ml_edge", "mercury2", 
                        "claude_gainer_ml", "crypto_gainer_ml"],
            "strategy_dna": ["strategy_dna", "meta_strategy", "baby_strategies"],
            "signal_engines": ["signal_engine", "breakout_arena", "regime_terminal"],
            "trading_systems": ["kimi_rotc", "kimi_feb17", "riseoftheclaw", "alpha_engine"],
            "alternative": ["social_predict", "goldmine", "stocks_comp"],
            "battleground": ["ml_battleground", "quantum_fusion"]
        }
        
        # Load or initialize registry
        self.registry = self._load_registry()
    
    def _load_registry(self) -> Dict[str, Dict[str, Any]]:
        """Load registry from file or create default."""
        if self.registry_path.exists():
            with open(self.registry_path, 'r') as f:
                registry = json.load(f)
                
                # Ensure all known systems are present
                for system in self.known_systems:
                    if system not in registry:
                        registry[system] = self._create_default_entry(system)
                
                return registry
        else:
            # Create new registry with default entries
            registry = {}
            for system in self.known_systems:
                registry[system] = self._create_default_entry(system)
            
            self._save_registry(registry)
            return registry
    
    def _create_default_entry(self, system_name: str) -> Dict[str, Any]:
        """Create default registry entry for a system."""
        category = self._get_system_category(system_name)
        base_weight = self._get_base_weight(system_name)
        
        return {
            "name": system_name,
            "category": category,
            "reliability_score": 0.7,  # Default starting score
            "weight": base_weight,
            "status": "unknown",  # unknown, active, inactive, degraded
            "last_signal_time": None,
            "last_check": None,
            "signal_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "neutral_count": 0,
            "performance_history": [],
            "avg_confidence": 0.5,
            "avg_pnl": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.5,
            "profit_factor": 1.0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
    
    def _get_system_category(self, system_name: str) -> str:
        """Get category for a system."""
        for category, systems in self.system_categories.items():
            if system_name in systems:
                return category
        return "unknown"
    
    def _get_base_weight(self, system_name: str) -> float:
        """Get base weight for a system based on category."""
        category = self._get_system_category(system_name)
        weight_map = {
            "ml_heavy": 1.2,      # ML systems get higher base weight
            "strategy_dna": 1.0,  # DNA systems are baseline
            "signal_engines": 0.9, # Signal engines slightly lower
            "trading_systems": 1.0,
            "alternative": 0.8,   # Alternative data systems
            "battleground": 0.9,
            "unknown": 0.7,
        }
        return weight_map.get(category, 0.7)
    
    def _save_registry(self, registry: Optional[Dict] = None):
        """Save registry to file."""
        if registry is None:
            registry = self.registry
        
        # Update timestamps
        for system_data in registry.values():
            system_data["updated_at"] = datetime.now().isoformat()
        
        with open(self.registry_path, 'w') as f:
            json.dump(registry, f, indent=2, default=str)
    
    def get_system(self, system_name: str) -> Optional[Dict[str, Any]]:
        """Get registry entry for a system."""
        return self.registry.get(system_name)
    
    def update_system_status(
        self,
        system_name: str,
        status: str,
        signal_count: int = 0,
        last_signal_time: Optional[str] = None
    ) -> bool:
        """
        Update system status and signal information.
        
        Args:
            system_name: Name of the system
            status: New status ("active", "inactive", "degraded", "unknown")
            signal_count: Number of signals from this poll
            last_signal_time: ISO timestamp of last signal
            
        Returns:
            True if update successful, False otherwise
        """
        if system_name not in self.registry:
            return False
        
        entry = self.registry[system_name]
        entry["status"] = status
        entry["last_check"] = datetime.now().isoformat()
        
        if signal_count > 0:
            entry["signal_count"] += signal_count
            entry["last_signal_time"] = last_signal_time or datetime.now().isoformat()
        
        self._save_registry()
        return True
    
    def record_performance(
        self,
        system_name: str,
        outcome: str,
        pnl: float = 0.0,
        confidence: float = 0.5,
        signal_hash: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Record performance outcome for a system.
        
        Args:
            system_name: Name of the system
            outcome: "success", "failure", or "neutral"
            pnl: Profit/loss percentage
            confidence: Signal confidence (0-1)
            signal_hash: Unique identifier for the signal
            metadata: Additional performance metadata
            
        Returns:
            True if recorded successfully, False otherwise
        """
        if system_name not in self.registry:
            return False
        
        entry = self.registry[system_name]
        
        # Update counts
        if outcome == "success":
            entry["success_count"] += 1
        elif outcome == "failure":
            entry["failure_count"] += 1
        elif outcome == "neutral":
            entry["neutral_count"] += 1
        
        # Add to performance history
        performance_record = {
            "timestamp": datetime.now().isoformat(),
            "outcome": outcome,
            "pnl": pnl,
            "confidence": confidence,
            "signal_hash": signal_hash,
            "metadata": metadata or {},
        }
        
        entry["performance_history"].append(performance_record)
        
        # Keep only recent history (last 500 entries)
        if len(entry["performance_history"]) > 500:
            entry["performance_history"] = entry["performance_history"][-500:]
        
        # Update metrics
        self._update_system_metrics(entry)
        
        self._save_registry()
        return True
    
    def _update_system_metrics(self, entry: Dict[str, Any]):
        """Update calculated metrics for a system."""
        history = entry["performance_history"]
        
        if not history:
            return
        
        # Calculate success rate
        successes = entry["success_count"]
        failures = entry["failure_count"]
        total_trades = successes + failures
        
        if total_trades > 0:
            win_rate = successes / total_trades
            entry["win_rate"] = win_rate
        else:
            win_rate = 0.5
        
        # Calculate average PnL
        pnls = [r["pnl"] for r in history if r["pnl"] != 0]
        if pnls:
            avg_pnl = np.mean(pnls)
            entry["avg_pnl"] = avg_pnl
            
            # Calculate Sharpe ratio (simplified)
            if len(pnls) > 1:
                returns_series = pd.Series(pnls)
                sharpe = returns_series.mean() / returns_series.std() if returns_series.std() > 0 else 0
                entry["sharpe_ratio"] = sharpe
            
            # Calculate profit factor
            gross_profit = sum(p for p in pnls if p > 0)
            gross_loss = abs(sum(p for p in pnls if p < 0))
            if gross_loss > 0:
                profit_factor = gross_profit / gross_loss
                entry["profit_factor"] = profit_factor
        
        # Calculate max drawdown
        if len(history) >= 10:
            # Simple drawdown calculation from PnL sequence
            cumulative = np.cumsum([r["pnl"] for r in history])
            running_max = np.maximum.accumulate(cumulative)
            drawdowns = (cumulative - running_max) / (running_max + 1e-10)
            max_dd = abs(np.min(drawdowns)) if len(drawdowns) > 0 else 0
            entry["max_drawdown"] = max_dd
        
        # Calculate average confidence
        confidences = [r["confidence"] for r in history if "confidence" in r]
        if confidences:
            entry["avg_confidence"] = np.mean(confidences)
        
        # Update reliability score
        self._update_reliability_score(entry)
    
    def _update_reliability_score(self, entry: Dict[str, Any]):
        """Update reliability score based on performance metrics."""
        win_rate = entry.get("win_rate", 0.5)
        profit_factor = entry.get("profit_factor", 1.0)
        sharpe_ratio = entry.get("sharpe_ratio", 0.0)
        avg_pnl = entry.get("avg_pnl", 0.0)
        
        # Normalize metrics to 0-1 range
        win_rate_score = win_rate  # Already 0-1
        
        # Profit factor: 1.0 = break-even, >1.5 = good, <0.5 = bad
        pf_score = min(max((profit_factor - 0.5) / 1.5, 0), 1)
        
        # Sharpe ratio: >1.0 = good, <0 = bad
        sharpe_score = min(max(sharpe_ratio / 2.0 + 0.5, 0), 1)
        
        # Average PnL: >0.02 = good, <0 = bad
        pnl_score = min(max(avg_pnl / 0.05 + 0.5, 0), 1)
        
        # Weighted combination
        reliability = (
            0.4 * win_rate_score +
            0.3 * pf_score +
            0.2 * sharpe_score +
            0.1 * pnl_score
        )
        
        # Apply confidence adjustment
        avg_confidence = entry.get("avg_confidence", 0.5)
        confidence_adjustment = 0.8 + 0.4 * avg_confidence  # 0.8-1.2 range
        
        reliability *= confidence_adjustment
        reliability = min(max(reliability, 0), 1)  # Clamp to 0-1
        
        entry["reliability_score"] = reliability
        
        # Update weight based on reliability
        base_weight = self._get_base_weight(entry["name"])
        entry["weight"] = base_weight * (0.5 + 0.5 * reliability)
    
    def get_active_systems(self) -> List[Dict[str, Any]]:
        """Get list of active systems."""
        active = []
        for name, data in self.registry.items():
            if data["status"] == "active":
                active.append(data)
        return active
    
    def get_systems_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get systems by category."""
        systems = []
        for name, data in self.registry.items():
            if data["category"] == category:
                systems.append(data)
        return systems
    
    def get_top_systems(self, n: int = 10, metric: str = "reliability_score") -> List[Dict[str, Any]]:
        """Get top N systems by specified metric."""
        systems = list(self.registry.values())
        
        if metric == "reliability_score":
            systems.sort(key=lambda x: x.get("reliability_score", 0), reverse=True)
        elif metric == "win_rate":
            systems.sort(key=lambda x: x.get("win_rate", 0), reverse=True)
        elif metric == "profit_factor":
            systems.sort(key=lambda x: x.get("profit_factor", 0), reverse=True)
        elif metric == "sharpe_ratio":
            systems.sort(key=lambda x: x.get("sharpe_ratio", 0), reverse=True)
        
        return systems[:n]
    
    def calculate_portfolio_diversification(
        self,
        system_weights: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate portfolio diversification metrics.
        
        Args:
            system_weights: Dictionary mapping system names to weights
            
        Returns:
            Diversification metrics
        """
        total_weight = sum(system_weights.values())
        if total_weight == 0:
            return {"diversification_score": 0.0, "effective_n": 0.0}
        
        # Normalize weights
        normalized_weights = {k: v/total_weight for k, v in system_weights.items()}
        
        # Calculate Herfindahl-Hirschman Index (HHI)
        hhi = sum(w ** 2 for w in normalized_weights.values())
        
        # Effective number of systems (1/HHI)
        effective_n = 1 / hhi if hhi > 0 else 0
        
        # Diversification score (0-1, higher is better)
        max_systems = len(normalized_weights)
        perfect_diversification = 1 / max_systems if max_systems > 0 else 1
        diversification_score = 1 - (hhi - perfect_diversification) / (1 - perfect_diversification)
        
        # Category diversification
        category_weights = {}
        for system, weight in normalized_weights.items():
            category = self._get_system_category(system)
            category_weights[category] = category_weights.get(category, 0) + weight
        
        category_hhi = sum(w ** 2 for w in category_weights.values())
        category_diversification = 1 - (category_hhi - 1/len(category_weights)) / (1 - 1/len(category_weights)) if len(category_weights) > 1 else 0
        
        return {
            "diversification_score": float(max(0, min(diversification_score, 1))),
            "effective_n_systems": float(effective_n),
            "category_diversification": float(category_diversification),
            "hhi": float(hhi),
            "category_weights": category_weights,
        }
    
    def generate_dashboard_data(self) -> Dict[str, Any]:
        """Generate data for dashboard display."""
        active_systems = self.get_active_systems()
        top_systems = self.get_top_systems(10, "reliability_score")
        
        # Calculate overall metrics
        total_signals = sum(s["signal_count"] for s in self.registry.values())
        total_success = sum(s["success_count"] for s in self.registry.values())
        total_failure = sum(s["failure_count"] for s in self.registry.values())
        
        overall_win_rate = total_success / (total_success + total_failure) if (total_success + total_failure) > 0 else 0
        
        # System health summary
        status_counts = {}
        for data in self.registry.values():
            status = data["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Category performance
        category_performance = {}
        for category in self.system_categories.keys():
            cat_systems = self.get_systems_by_category(category)
            if cat_systems:
                avg_reliability = np.mean([s["reliability_score"] for s in cat_systems])
                category_performance[category] = {
                    "count": len(cat_systems),
                    "avg_reliability": float(avg_reliability),
                    "active_count": sum(1 for s in cat_systems if s["status"] == "active"),
                }
        
        return {
            "last_update": datetime.now().isoformat(),
            "total_systems": len(self.registry),
            "active_systems": len(active_systems),
            "total_signals": total_signals,
            "overall_win_rate": float(overall_win_rate),
            "status_summary": status_counts,
            "top_systems": top_systems[:5],
            "category_performance": category_performance,
            "registry_path": str(self.registry_path),
        }
    
    def export_to_csv(self, output_path: Optional[Path] = None) -> Path:
        """Export registry data to CSV."""
        if output_path is None:
            output_path = self.registry_path.parent / "system_registry_export.csv"
        
        # Convert to DataFrame
        rows = []
        for name, data in self.registry.items():
            row = {
                "system_name": name,
                "category": data.get("category", "unknown"),
                "status": data.get("status", "unknown"),
                "reliability_score": data.get("reliability_score", 0.5),
                "weight": data.get("weight", 1.0),
                "signal_count": data.get("signal_count", 0),
                "success_count": data.get("success_count", 0),
                "failure_count": data.get("failure_count", 0),
                "win_rate": data.get("win_rate", 0.5),
                "profit_factor": data.get("profit_factor", 1.0),
                "sharpe_ratio": data.get("sharpe_ratio", 0.0),
                "avg_pnl": data.get("avg_pnl", 0.0),
                "max_drawdown": data.get("max_drawdown", 0.0),
                "last_signal_time": data.get("last_signal_time"),
                "last_check": data.get("last_check"),
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
        
        return output_path


# Factory function for easy access
def create_system_registry(registry_path: Optional[str] = None) -> SystemRegistry:
    """
    Factory function to create system registry.
    
    Args:
        registry_path: Optional path to registry file
        
    Returns:
        SystemRegistry instance
    """
    path = Path(registry_path) if registry_path else None
    return SystemRegistry(path)


if __name__ == "__main__":
    # Example usage
    registry = SystemRegistry()
    
    print("System Registry Test")
    print("=" * 70)
    
    # Get active systems
    active = registry.get_active_systems()
    print(f"Active systems: {len(active)}")
    
    # Get top systems
    top_systems = registry.get_top_systems(5, "reliability_score")
    print("\nTop 5 systems by reliability:")
    for i, system in enumerate(top_systems, 1):
        print(f"{i:2d}. {system['name']:20s} "
              f"Rel: {system['reliability_score']:.3f} "
              f"WR: {system['win_rate']:.1%} "
              f"PF: {system['profit_factor']:.2f}")
    
    # Generate dashboard data
    dashboard_data = registry.generate_dashboard_data()
    print(f"\nTotal systems: {dashboard_data['total_systems']}")
    print(f"Active systems: {dashboard_data['active_systems']}")
    print(f"Overall win rate: {dashboard_data['overall_win_rate']:.1%}")
    
    # Export to CSV
    csv_path = registry.export_to_csv()
    print(f"\nRegistry exported to: {csv_path}")