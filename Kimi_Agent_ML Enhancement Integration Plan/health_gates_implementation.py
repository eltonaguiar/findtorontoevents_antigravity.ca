"""
ML Enhancement Integration - Health Gates Implementation
Crypto Prediction System - Metrics & KPI Framework

This module implements the health gate system for validating ML enhancements
before deployment to production.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import numpy as np
from datetime import datetime, timedelta


class GateStatus(Enum):
    """Status of a health gate check."""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


class Severity(Enum):
    """Alert severity levels."""
    P1_CRITICAL = "p1_critical"
    P2_WARNING = "p2_warning"
    P3_INFO = "p3_info"


@dataclass
class MetricThreshold:
    """Threshold configuration for a metric."""
    metric_name: str
    green_threshold: float
    yellow_threshold: float
    red_threshold: float
    comparison: str = "less_than"  # "less_than" or "greater_than"
    
    def evaluate(self, value: float) -> Tuple[GateStatus, str]:
        """Evaluate a metric value against thresholds."""
        if self.comparison == "less_than":
            if value <= self.green_threshold:
                return GateStatus.PASS, f"{self.metric_name}={value:.4f} <= {self.green_threshold} (green)"
            elif value <= self.yellow_threshold:
                return GateStatus.WARNING, f"{self.metric_name}={value:.4f} <= {self.yellow_threshold} (yellow)"
            else:
                return GateStatus.FAIL, f"{self.metric_name}={value:.4f} > {self.red_threshold} (red)"
        else:  # greater_than
            if value >= self.green_threshold:
                return GateStatus.PASS, f"{self.metric_name}={value:.4f} >= {self.green_threshold} (green)"
            elif value >= self.yellow_threshold:
                return GateStatus.WARNING, f"{self.metric_name}={value:.4f} >= {self.yellow_threshold} (yellow)"
            else:
                return GateStatus.FAIL, f"{self.metric_name}={value:.4f} < {self.red_threshold} (red)"


@dataclass
class GateResult:
    """Result of a health gate check."""
    gate_name: str
    overall_status: GateStatus
    metric_results: List[Tuple[str, GateStatus, str]]
    timestamp: datetime
    recommendations: List[str]


class FeatureHealthMetrics:
    """Calculate and evaluate feature health metrics."""
    
    # Total features in contract
    TOTAL_FEATURES = 39
    
    @staticmethod
    def calculate_dead_features(features_df: np.ndarray, epsilon: float = 0.001) -> Dict:
        """
        Calculate dead features (zero variance or near-constant).
        
        Args:
            features_df: Array of shape (n_samples, n_features)
            epsilon: Threshold for considering a feature dead
            
        Returns:
            Dict with count, percentage, and feature indices
        """
        stds = np.std(features_df, axis=0)
        unique_ratios = np.array([
            len(np.unique(features_df[:, i])) / len(features_df) 
            for i in range(features_df.shape[1])
        ])
        
        dead_mask = (stds < epsilon) | (unique_ratios < 0.001)
        dead_indices = np.where(dead_mask)[0].tolist()
        
        return {
            'count': len(dead_indices),
            'percentage': len(dead_indices) / features_df.shape[1] * 100,
            'indices': dead_indices,
            'stds': stds.tolist()
        }
    
    @staticmethod
    def calculate_constant_features(features_df: np.ndarray) -> Dict:
        """Calculate constant features (max == min)."""
        constant_mask = np.max(features_df, axis=0) == np.min(features_df, axis=0)
        constant_indices = np.where(constant_mask)[0].tolist()
        
        return {
            'count': len(constant_indices),
            'percentage': len(constant_indices) / features_df.shape[1] * 100,
            'indices': constant_indices
        }
    
    @staticmethod
    def calculate_psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
        """
        Calculate Population Stability Index.
        
        Args:
            expected: Reference distribution
            actual: Current distribution
            bins: Number of bins
            
        Returns:
            PSI value
        """
        # Create bins based on expected distribution
        breakpoints = np.percentile(expected, np.linspace(0, 100, bins + 1))
        breakpoints[-1] += 1e-10  # Ensure max value is included
        
        expected_counts, _ = np.histogram(expected, breakpoints)
        actual_counts, _ = np.histogram(actual, breakpoints)
        
        # Add small constant to avoid division by zero
        expected_percents = expected_counts / len(expected) + 1e-10
        actual_percents = actual_counts / len(actual) + 1e-10
        
        psi = np.sum((actual_percents - expected_percents) * 
                     np.log(actual_percents / expected_percents))
        
        return float(psi)
    
    @staticmethod
    def calculate_feature_drift(reference_df: np.ndarray, current_df: np.ndarray) -> Dict:
        """
        Calculate drift metrics for all features.
        
        Returns:
            Dict with PSI, KS, and mean shift for each feature
        """
        n_features = reference_df.shape[1]
        results = {
            'psi': [],
            'ks': [],
            'mean_shift_z': [],
            'features_with_significant_drift': []
        }
        
        for i in range(n_features):
            ref = reference_df[:, i]
            curr = current_df[:, i]
            
            # PSI
            psi = FeatureHealthMetrics.calculate_psi(ref, curr)
            results['psi'].append(psi)
            
            # KS statistic (simplified)
            ks = np.max(np.abs(
                np.sort(ref) - np.sort(curr)
            ))
            results['ks'].append(ks)
            
            # Mean shift z-score
            mean_shift = (np.mean(curr) - np.mean(ref)) / (np.std(ref) / np.sqrt(len(curr)))
            results['mean_shift_z'].append(mean_shift)
            
            # Track significant drift
            if psi >= 0.25 or abs(mean_shift) >= 3:
                results['features_with_significant_drift'].append(i)
        
        results['max_psi'] = max(results['psi'])
        results['max_ks'] = max(results['ks'])
        results['max_mean_shift_z'] = max(abs(z) for z in results['mean_shift_z'])
        
        return results
    
    @staticmethod
    def calculate_max_correlation(features_df: np.ndarray) -> float:
        """Calculate maximum absolute correlation between features."""
        corr_matrix = np.corrcoef(features_df.T)
        # Get upper triangle (excluding diagonal)
        upper_tri = corr_matrix[np.triu_indices_from(corr_matrix, k=1)]
        return float(np.max(np.abs(upper_tri)))
    
    @staticmethod
    def calculate_coverage(features_df: np.ndarray) -> Dict:
        """Calculate feature coverage (non-null percentage)."""
        # Assuming NaN for missing values
        null_mask = np.isnan(features_df)
        
        # Coverage per row (entry)
        row_coverage = (1 - null_mask.sum(axis=1) / features_df.shape[1]) * 100
        
        # Coverage per feature
        feature_coverage = (1 - null_mask.sum(axis=0) / features_df.shape[0]) * 100
        
        return {
            'overall_coverage': float(np.mean(row_coverage)),
            'min_feature_coverage': float(np.min(feature_coverage)),
            'null_rate_by_feature': null_mask.sum(axis=0).tolist()
        }


class ModelPerformanceMetrics:
    """Calculate and evaluate model performance metrics."""
    
    @staticmethod
    def calculate_precision_at_k(y_true: np.ndarray, y_pred_proba: np.ndarray, 
                                  k_percentages: List[float] = [0.1, 0.2, 0.5]) -> Dict:
        """
        Calculate precision at top K% predictions.
        
        Args:
            y_true: True labels (0 or 1)
            y_pred_proba: Predicted probabilities
            k_percentages: List of K percentages to evaluate
            
        Returns:
            Dict with precision at each K
        """
        results = {}
        n = len(y_true)
        
        # Sort by predicted probability (descending)
        sorted_indices = np.argsort(y_pred_proba)[::-1]
        y_true_sorted = y_true[sorted_indices]
        
        for k in k_percentages:
            k_count = int(n * k)
            if k_count == 0:
                results[f'precision_at_{int(k*100)}'] = 0.0
                continue
                
            top_k_true = y_true_sorted[:k_count]
            precision = np.mean(top_k_true)
            results[f'precision_at_{int(k*100)}'] = float(precision)
        
        return results
    
    @staticmethod
    def calculate_auc_roc(y_true: np.ndarray, y_pred_proba: np.ndarray) -> float:
        """Calculate AUC-ROC using trapezoidal rule."""
        # Sort by predicted probability
        sorted_indices = np.argsort(y_pred_proba)
        y_true_sorted = y_true[sorted_indices]
        
        # Calculate TPR and FPR at each threshold
        n_pos = np.sum(y_true)
        n_neg = len(y_true) - n_pos
        
        tpr = np.cumsum(y_true_sorted[::-1]) / n_pos
        fpr = np.cumsum(1 - y_true_sorted[::-1]) / n_neg
        
        # Add (0,0) point
        tpr = np.concatenate([[0], tpr])
        fpr = np.concatenate([[0], fpr])
        
        # Calculate AUC using trapezoidal rule
        auc = np.trapz(tpr, fpr)
        return float(auc)
    
    @staticmethod
    def calculate_calibration_error(y_true: np.ndarray, y_pred_proba: np.ndarray,
                                     n_bins: int = 10) -> Dict:
        """
        Calculate Expected Calibration Error (ECE) and Max Calibration Error (MCE).
        
        Returns:
            Dict with ECE, MCE, and per-bin statistics
        """
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        mce = 0.0
        bin_stats = []
        
        for i in range(n_bins):
            mask = (y_pred_proba >= bin_boundaries[i]) & (y_pred_proba < bin_boundaries[i + 1])
            if i == n_bins - 1:  # Include right edge for last bin
                mask = (y_pred_proba >= bin_boundaries[i]) & (y_pred_proba <= bin_boundaries[i + 1])
            
            if np.sum(mask) == 0:
                continue
                
            bin_confidence = np.mean(y_pred_proba[mask])
            bin_accuracy = np.mean(y_true[mask])
            bin_size = np.sum(mask)
            
            calibration_error = abs(bin_accuracy - bin_confidence)
            ece += (bin_size / len(y_true)) * calibration_error
            mce = max(mce, calibration_error)
            
            bin_stats.append({
                'bin': i,
                'confidence': float(bin_confidence),
                'accuracy': float(bin_accuracy),
                'size': int(bin_size),
                'error': float(calibration_error)
            })
        
        return {
            'ece': float(ece),
            'mce': float(mce),
            'bin_stats': bin_stats
        }
    
    @staticmethod
    def calculate_log_loss(y_true: np.ndarray, y_pred_proba: np.ndarray, 
                           epsilon: float = 1e-15) -> float:
        """Calculate log loss (cross-entropy)."""
        # Clip probabilities to avoid log(0)
        y_pred_proba = np.clip(y_pred_proba, epsilon, 1 - epsilon)
        
        log_loss = -np.mean(
            y_true * np.log(y_pred_proba) + 
            (1 - y_true) * np.log(1 - y_pred_proba)
        )
        return float(log_loss)


class TradingPerformanceMetrics:
    """Calculate and evaluate trading performance metrics."""
    
    @staticmethod
    def calculate_expectancy(trade_pnls: np.ndarray) -> Dict:
        """
        Calculate expectancy metrics.
        
        Args:
            trade_pnls: Array of trade PnLs (as decimals, e.g., 0.01 for 1%)
            
        Returns:
            Dict with expectancy, win rate, avg win/loss
        """
        wins = trade_pnls[trade_pnls > 0]
        losses = trade_pnls[trade_pnls <= 0]
        
        win_rate = len(wins) / len(trade_pnls) if len(trade_pnls) > 0 else 0
        avg_win = np.mean(wins) if len(wins) > 0 else 0
        avg_loss = abs(np.mean(losses)) if len(losses) > 0 else 0
        
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        return {
            'expectancy': float(expectancy),
            'win_rate': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'profit_factor': float(np.sum(wins) / abs(np.sum(losses))) if len(losses) > 0 else float('inf')
        }
    
    @staticmethod
    def calculate_expectancy_drop(trade_pnls: np.ndarray, window: int = 50) -> float:
        """Calculate maximum drop in rolling expectancy."""
        if len(trade_pnls) < window:
            return 0.0
        
        rolling_expectancies = []
        for i in range(window, len(trade_pnls) + 1):
            window_pnls = trade_pnls[i-window:i]
            exp = TradingPerformanceMetrics.calculate_expectancy(window_pnls)
            rolling_expectancies.append(exp['expectancy'])
        
        rolling_expectancies = np.array(rolling_expectancies)
        peak = np.maximum.accumulate(rolling_expectancies)
        drawdowns = peak - rolling_expectancies
        
        return float(np.max(drawdowns))
    
    @staticmethod
    def calculate_sl_hit_rate(trade_pnls: np.ndarray, sl_hit_flags: np.ndarray) -> float:
        """
        Calculate stop loss hit rate.
        
        Args:
            trade_pnls: Array of trade PnLs
            sl_hit_flags: Boolean array indicating SL hits
            
        Returns:
            SL hit rate as percentage
        """
        return float(np.mean(sl_hit_flags) * 100)
    
    @staticmethod
    def calculate_adverse_entry_bps(entry_prices: np.ndarray, 
                                     price_history: np.ndarray,
                                     seconds_after: int = 30) -> float:
        """
        Calculate adverse entry in basis points.
        
        Args:
            entry_prices: Array of entry prices
            price_history: Price data after each entry
            seconds_after: Window to measure adverse move
            
        Returns:
            Average adverse entry in bps
        """
        # Simplified - in practice would use actual price history
        # For now, assume price_history contains worst price in window
        adverse_moves = (entry_prices - price_history) / entry_prices * 10000
        return float(np.mean(adverse_moves))


class RiskMetrics:
    """Calculate and evaluate risk metrics."""
    
    @staticmethod
    def calculate_max_drawdown(equity_curve: np.ndarray) -> Dict:
        """
        Calculate maximum drawdown and duration.
        
        Args:
            equity_curve: Array of portfolio values over time
            
        Returns:
            Dict with max DD, peak, trough, duration
        """
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (peak - equity_curve) / peak
        
        max_dd_idx = np.argmax(drawdown)
        max_dd = drawdown[max_dd_idx]
        
        # Find peak before max DD
        peak_idx = np.argmax(equity_curve[:max_dd_idx + 1])
        
        # Find recovery (if any)
        recovery_idx = max_dd_idx
        for i in range(max_dd_idx, len(equity_curve)):
            if equity_curve[i] >= equity_curve[peak_idx]:
                recovery_idx = i
                break
        
        return {
            'max_drawdown': float(max_dd * 100),  # As percentage
            'peak_value': float(peak_idx),
            'trough_value': float(max_dd_idx),
            'duration_days': int(recovery_idx - peak_idx)
        }
    
    @staticmethod
    def calculate_var(daily_pnls: np.ndarray, confidence: float = 0.95) -> float:
        """
        Calculate Value at Risk.
        
        Args:
            daily_pnls: Array of daily PnLs (as decimals)
            confidence: Confidence level (e.g., 0.95 for 95%)
            
        Returns:
            VaR as negative percentage
        """
        var = np.percentile(daily_pnls, (1 - confidence) * 100)
        return float(var * 100)  # As percentage
    
    @staticmethod
    def calculate_var_breach_rate(daily_pnls: np.ndarray, var_95: float) -> float:
        """Calculate rate of VaR breaches."""
        breaches = np.sum(daily_pnls < var_95 / 100)  # Convert back to decimal
        return float(breaches / len(daily_pnls) * 100)
    
    @staticmethod
    def calculate_regime_concentration(regime_pnls: Dict[str, float]) -> float:
        """
        Calculate Herfindahl index of PnL by regime.
        
        Args:
            regime_pnls: Dict mapping regime name to PnL
            
        Returns:
            Concentration index (0 = perfectly diversified, 1 = single regime)
        """
        total_pnl = sum(abs(pnl) for pnl in regime_pnls.values())
        if total_pnl == 0:
            return 0.0
        
        shares = [abs(pnl) / total_pnl for pnl in regime_pnls.values()]
        hhi = sum(s ** 2 for s in shares)
        
        return float(hhi)


class HealthGateChecker:
    """Main class for checking health gates."""
    
    # Threshold configurations
    FEATURE_THRESHOLDS = {
        'dead_feature_count': MetricThreshold('dead_feature_count', 5, 10, 10, 'less_than'),
        'dead_feature_percent': MetricThreshold('dead_feature_percent', 12, 25, 25, 'less_than'),
        'constant_feature_count': MetricThreshold('constant_feature_count', 0, 3, 3, 'less_than'),
        'feature_drift_psi': MetricThreshold('feature_drift_psi', 0.1, 0.25, 0.25, 'less_than'),
        'max_feature_correlation': MetricThreshold('max_feature_correlation', 0.8, 0.9, 0.9, 'less_than'),
        'feature_coverage_percent': MetricThreshold('feature_coverage_percent', 99, 95, 95, 'greater_than'),
    }
    
    MODEL_THRESHOLDS = {
        'precision_at_20': MetricThreshold('precision_at_20', 0.52, 0.50, 0.50, 'greater_than'),
        'auc_roc': MetricThreshold('auc_roc', 0.55, 0.53, 0.53, 'greater_than'),
        'ece': MetricThreshold('ece', 0.05, 0.10, 0.10, 'less_than'),
        'log_loss': MetricThreshold('log_loss', 0.65, 0.68, 0.68, 'less_than'),
    }
    
    TRADING_THRESHOLDS = {
        'expectancy_per_trade': MetricThreshold('expectancy_per_trade', 0.0015, 0.001, 0.001, 'greater_than'),
        'expectancy_drop': MetricThreshold('expectancy_drop', 0.0020, 0.0030, 0.0030, 'less_than'),
        'win_rate': MetricThreshold('win_rate', 0.50, 0.48, 0.48, 'greater_than'),
        'sl_hit_rate': MetricThreshold('sl_hit_rate', 35, 45, 45, 'less_than'),
        'profit_factor': MetricThreshold('profit_factor', 1.3, 1.1, 1.1, 'greater_than'),
    }
    
    RISK_THRESHOLDS = {
        'max_intraday_drawdown': MetricThreshold('max_intraday_drawdown', 3.0, 5.0, 5.0, 'less_than'),
        'daily_var_95': MetricThreshold('daily_var_95', -2.0, -3.0, -3.0, 'greater_than'),
        'regime_concentration': MetricThreshold('regime_concentration', 0.25, 0.35, 0.35, 'less_than'),
    }
    
    OPERATIONAL_THRESHOLDS = {
        'latency_p99': MetricThreshold('latency_p99', 150, 300, 300, 'less_than'),
        'sl_calibrator_coverage': MetricThreshold('sl_calibrator_coverage', 80, 50, 50, 'greater_than'),
        'system_uptime': MetricThreshold('system_uptime', 99.9, 99.0, 99.0, 'greater_than'),
    }
    
    @classmethod
    def check_gate_1_feature_health(cls, metrics: Dict) -> GateResult:
        """
        Check Gate 1: Feature Health Gate.
        
        Required metrics:
        - dead_feature_count
        - constant_feature_count
        - feature_coverage_percent
        - feature_drift_psi
        - max_feature_correlation
        """
        results = []
        recommendations = []
        
        required_metrics = [
            'dead_feature_count', 'constant_feature_count', 'feature_coverage_percent',
            'feature_drift_psi', 'max_feature_correlation'
        ]
        
        for metric_name in required_metrics:
            if metric_name not in metrics:
                results.append((metric_name, GateStatus.FAIL, f"Missing metric: {metric_name}"))
                recommendations.append(f"Add monitoring for {metric_name}")
                continue
            
            threshold = cls.FEATURE_THRESHOLDS.get(metric_name)
            if threshold:
                status, message = threshold.evaluate(metrics[metric_name])
                results.append((metric_name, status, message))
                
                if status == GateStatus.FAIL:
                    recommendations.append(f"URGENT: {metric_name} is failing - investigate immediately")
                elif status == GateStatus.WARNING:
                    recommendations.append(f"WARNING: {metric_name} approaching threshold")
        
        # Determine overall status
        if any(r[1] == GateStatus.FAIL for r in results):
            overall = GateStatus.FAIL
        elif any(r[1] == GateStatus.WARNING for r in results):
            overall = GateStatus.WARNING
        else:
            overall = GateStatus.PASS
        
        return GateResult(
            gate_name="Gate 1: Feature Health",
            overall_status=overall,
            metric_results=results,
            timestamp=datetime.now(),
            recommendations=recommendations
        )
    
    @classmethod
    def check_gate_2_model_quality(cls, metrics: Dict) -> GateResult:
        """Check Gate 2: Model Quality Gate."""
        results = []
        recommendations = []
        
        required_metrics = ['precision_at_20', 'auc_roc', 'ece', 'log_loss']
        
        for metric_name in required_metrics:
            if metric_name not in metrics:
                results.append((metric_name, GateStatus.FAIL, f"Missing metric: {metric_name}"))
                continue
            
            threshold = cls.MODEL_THRESHOLDS.get(metric_name)
            if threshold:
                status, message = threshold.evaluate(metrics[metric_name])
                results.append((metric_name, status, message))
                
                if status == GateStatus.FAIL:
                    recommendations.append(f"Model quality issue: {metric_name}")
        
        overall = GateStatus.FAIL if any(r[1] == GateStatus.FAIL for r in results) else \
                  GateStatus.WARNING if any(r[1] == GateStatus.WARNING for r in results) else \
                  GateStatus.PASS
        
        return GateResult(
            gate_name="Gate 2: Model Quality",
            overall_status=overall,
            metric_results=results,
            timestamp=datetime.now(),
            recommendations=recommendations
        )
    
    @classmethod
    def check_gate_3_trading_live(cls, metrics: Dict, baseline_metrics: Dict) -> GateResult:
        """Check Gate 3: Trading Live Gate."""
        results = []
        recommendations = []
        
        # Check absolute thresholds
        for metric_name in ['expectancy_per_trade', 'win_rate', 'sl_hit_rate']:
            if metric_name in metrics:
                threshold = cls.TRADING_THRESHOLDS.get(metric_name)
                if threshold:
                    status, message = threshold.evaluate(metrics[metric_name])
                    results.append((metric_name, status, message))
        
        # Check baseline-relative metrics
        if 'adverse_entry_bps' in metrics and 'adverse_entry_bps' in baseline_metrics:
            current = metrics['adverse_entry_bps']
            baseline = baseline_metrics['adverse_entry_bps']
            improvement = baseline - current
            
            if improvement >= 1:  # At least 1 bps improvement
                status = GateStatus.PASS
                message = f"adverse_entry_bps improved by {improvement:.1f} bps"
            elif improvement >= -2:  # Within 2 bps
                status = GateStatus.WARNING
                message = f"adverse_entry_bps neutral ({improvement:.1f} bps)"
            else:
                status = GateStatus.FAIL
                message = f"adverse_entry_bps degraded by {abs(improvement):.1f} bps"
            
            results.append(('adverse_entry_bps', status, message))
        
        # Check max drawdown against baseline
        if 'max_intraday_drawdown' in metrics and 'max_intraday_drawdown' in baseline_metrics:
            current = metrics['max_intraday_drawdown']
            baseline = baseline_metrics['max_intraday_drawdown']
            
            if current <= baseline:
                status = GateStatus.PASS
                message = f"max_drawdown {current:.2f}% <= baseline {baseline:.2f}%"
            elif current <= baseline + 1:
                status = GateStatus.WARNING
                message = f"max_drawdown {current:.2f}% slightly above baseline"
            else:
                status = GateStatus.FAIL
                message = f"max_drawdown {current:.2f}% exceeds baseline + 1%"
            
            results.append(('max_intraday_drawdown', status, message))
        
        overall = GateStatus.FAIL if any(r[1] == GateStatus.FAIL for r in results) else \
                  GateStatus.WARNING if any(r[1] == GateStatus.WARNING for r in results) else \
                  GateStatus.PASS
        
        return GateResult(
            gate_name="Gate 3: Trading Live",
            overall_status=overall,
            metric_results=results,
            timestamp=datetime.now(),
            recommendations=recommendations
        )


# Example usage
if __name__ == "__main__":
    # Example: Check Gate 1
    gate1_metrics = {
        'dead_feature_count': 4,
        'constant_feature_count': 0,
        'feature_coverage_percent': 99.5,
        'feature_drift_psi': 0.08,
        'max_feature_correlation': 0.75
    }
    
    result = HealthGateChecker.check_gate_1_feature_health(gate1_metrics)
    print(f"\n{result.gate_name}")
    print(f"Overall Status: {result.overall_status.value}")
    print("Metric Results:")
    for metric, status, message in result.metric_results:
        print(f"  {metric}: {status.value} - {message}")
    if result.recommendations:
        print("Recommendations:")
        for rec in result.recommendations:
            print(f"  - {rec}")
