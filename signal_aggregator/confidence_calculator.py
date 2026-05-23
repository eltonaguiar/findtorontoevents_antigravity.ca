#!/usr/bin/env python3
"""
Confidence Calculator - Advanced Bayesian Confidence Scoring

Implements Bayesian updating, Kalman filtering, and regime-aware confidence
adjustment for signal aggregation.

Key Features:
1. Bayesian updating with conjugate priors (Beta distribution for binary outcomes)
2. Kalman filtering for time-varying confidence estimation
3. Regime-aware confidence adjustments
4. Multi-system fusion with Dempster-Shafer theory
5. Historical performance weighting with exponential decay
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import json
from pathlib import Path

class BayesianConfidenceCalculator:
    """
    Bayesian confidence calculator using conjugate priors for signal reliability.
    
    For binary outcomes (success/failure), we use Beta-Binomial conjugate prior:
    - Prior: Beta(α, β)
    - Likelihood: Binomial(n, p)
    - Posterior: Beta(α + successes, β + failures)
    
    Confidence is calculated as the mean of the posterior distribution.
    """
    
    def __init__(self, prior_alpha: float = 2.0, prior_beta: float = 2.0):
        """
        Initialize with prior parameters.
        
        Args:
            prior_alpha: Alpha parameter for Beta prior (pseudo-successes)
            prior_beta: Beta parameter for Beta prior (pseudo-failures)
        """
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
        
        # Cache for system performance
        self.performance_cache = {}
        
    def update_system_confidence(
        self, 
        system_name: str,
        outcomes: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Update system confidence using Bayesian updating.
        
        Args:
            system_name: Name of the trading system
            outcomes: List of outcome dictionaries with keys:
                - outcome: "success", "failure", or "neutral"
                - pnl: Profit/loss percentage
                - timestamp: When the outcome occurred
                - confidence: Original signal confidence
                
        Returns:
            Dictionary with confidence metrics:
                - posterior_mean: Mean of posterior Beta distribution
                - posterior_variance: Variance of posterior
                - credible_interval_95: 95% credible interval
                - bayesian_p_value: Probability that true success rate < 0.5
        """
        # Count successes and failures
        successes = sum(1 for o in outcomes if o.get("outcome") == "success")
        failures = sum(1 for o in outcomes if o.get("outcome") == "failure")
        neutrals = sum(1 for o in outcomes if o.get("outcome") == "neutral")
        
        total_trials = successes + failures
        
        if total_trials == 0:
            # No data, return prior
            posterior_alpha = self.prior_alpha
            posterior_beta = self.prior_beta
        else:
            # Update with observed data
            posterior_alpha = self.prior_alpha + successes
            posterior_beta = self.prior_beta + failures
        
        # Calculate posterior metrics
        posterior_mean = posterior_alpha / (posterior_alpha + posterior_beta)
        posterior_variance = (posterior_alpha * posterior_beta) / \
                           ((posterior_alpha + posterior_beta) ** 2 * \
                            (posterior_alpha + posterior_beta + 1))
        
        # 95% credible interval
        credible_interval = stats.beta.interval(
            0.95, posterior_alpha, posterior_beta
        )
        
        # Bayesian p-value: P(success_rate < 0.5 | data)
        bayesian_p_value = stats.beta.cdf(0.5, posterior_alpha, posterior_beta)
        
        # Calculate weighted confidence considering PnL
        if successes + failures > 0:
            avg_success_pnl = np.mean([
                o.get("pnl", 0) for o in outcomes 
                if o.get("outcome") == "success" and o.get("pnl") is not None
            ]) if any(o.get("outcome") == "success" for o in outcomes) else 0
            
            avg_failure_pnl = np.mean([
                abs(o.get("pnl", 0)) for o in outcomes 
                if o.get("outcome") == "failure" and o.get("pnl") is not None
            ]) if any(o.get("outcome") == "failure" for o in outcomes) else 0
            
            # Adjust confidence based on PnL magnitude
            pnl_adjustment = min(avg_success_pnl / 0.05, 1.0)  # Normalize to 5% target
            pnl_penalty = min(avg_failure_pnl / 0.02, 1.0)  # Penalize large losses
            
            weighted_confidence = posterior_mean * (0.7 + 0.3 * pnl_adjustment) * \
                                (1.0 - 0.2 * pnl_penalty)
        else:
            weighted_confidence = posterior_mean
        
        return {
            "system": system_name,
            "successes": successes,
            "failures": failures,
            "neutrals": neutrals,
            "total_trials": total_trials,
            "posterior_alpha": posterior_alpha,
            "posterior_beta": posterior_beta,
            "posterior_mean": float(posterior_mean),
            "posterior_variance": float(posterior_variance),
            "credible_interval_95": [float(credible_interval[0]), float(credible_interval[1])],
            "bayesian_p_value": float(bayesian_p_value),
            "weighted_confidence": float(weighted_confidence),
            "last_update": datetime.now().isoformat(),
        }
    
    def calculate_signal_confidence(
        self,
        system_confidences: Dict[str, float],
        signal_attributes: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculate confidence for a specific signal considering multiple systems.
        
        Args:
            system_confidences: Dictionary mapping system names to their confidence scores
            signal_attributes: Signal attributes including:
                - symbol: Trading symbol
                - direction: long/short
                - systems_agreed: List of systems agreeing on this signal
                - individual_confidences: Confidence from each system
                - timeframe: Signal timeframe
                - market_regime: Current market regime
                
        Returns:
            Dictionary with confidence metrics:
                - consensus_confidence: Fused confidence from all systems
                - dempster_shafer_confidence: Confidence using D-S theory
                - kalman_confidence: Time-filtered confidence
                - regime_adjusted_confidence: Adjusted for market regime
                - final_confidence: Final confidence score (0-1)
        """
        systems_agreed = signal_attributes.get("systems_agreed", [])
        individual_confidences = signal_attributes.get("individual_confidences", {})
        market_regime = signal_attributes.get("market_regime", "neutral")
        
        if not systems_agreed:
            return {"final_confidence": 0.0}
        
        # Method 1: Weighted average based on system reliability
        weights = []
        confidences = []
        
        for system in systems_agreed:
            system_weight = system_confidences.get(system, {}).get("weighted_confidence", 0.5)
            signal_confidence = individual_confidences.get(system, 0.5)
            
            # Combined weight
            combined_weight = system_weight * signal_confidence
            
            weights.append(combined_weight)
            confidences.append(signal_confidence)
        
        if sum(weights) == 0:
            weighted_avg = np.mean(confidences) if confidences else 0.5
        else:
            weighted_avg = np.average(confidences, weights=weights)
        
        # Method 2: Dempster-Shafer theory for evidence combination
        ds_confidence = self._dempster_shafer_combination(confidences)
        
        # Method 3: Kalman filter (if we have time series data)
        kalman_confidence = self._kalman_filter_confidence(
            systems_agreed, confidences, signal_attributes
        )
        
        # Method 4: Regime adjustment
        regime_adjusted = self._regime_adjust_confidence(
            weighted_avg, market_regime, signal_attributes
        )
        
        # Final confidence: weighted combination of methods
        final_confidence = (
            0.4 * weighted_avg +
            0.3 * ds_confidence +
            0.2 * kalman_confidence +
            0.1 * regime_adjusted
        )
        
        # Apply sigmoid scaling to emphasize high confidence signals
        final_confidence = 1 / (1 + np.exp(-10 * (final_confidence - 0.6)))
        
        return {
            "weighted_average_confidence": float(weighted_avg),
            "dempster_shafer_confidence": float(ds_confidence),
            "kalman_filter_confidence": float(kalman_confidence),
            "regime_adjusted_confidence": float(regime_adjusted),
            "final_confidence": float(final_confidence),
            "systems_count": len(systems_agreed),
            "agreement_ratio": len(systems_agreed) / len(system_confidences) if system_confidences else 0,
        }
    
    def _dempster_shafer_combination(self, confidences: List[float]) -> float:
        """
        Combine confidences using Dempster-Shafer theory.
        
        Simple implementation assuming binary frame of discernment:
        - Hypothesis H: Signal is correct
        - Not H: Signal is incorrect
        
        Each system provides basic probability assignment (BPA):
        - m(H) = confidence
        - m(¬H) = 1 - confidence
        - m(Θ) = 0 (uncertainty assigned to whole set)
        """
        if not confidences:
            return 0.5
        
        # Initialize with first system
        m_h = confidences[0]
        m_not_h = 1 - confidences[0]
        
        # Combine with remaining systems
        for conf in confidences[1:]:
            m_i_h = conf
            m_i_not_h = 1 - conf
            
            # Dempster's rule of combination
            k = m_h * m_i_not_h + m_not_h * m_i_h  # Conflict
            if k >= 1.0:  # Avoid division by zero
                continue
            
            new_m_h = (m_h * m_i_h + m_h * m_i_not_h + m_not_h * m_i_h) / (1 - k)
            new_m_not_h = (m_not_h * m_i_not_h + m_h * m_i_not_h + m_not_h * m_i_h) / (1 - k)
            
            m_h = new_m_h
            m_not_h = new_m_not_h
        
        # Return belief in H (signal is correct)
        return m_h
    
    def _kalman_filter_confidence(
        self,
        systems: List[str],
        confidences: List[float],
        signal_attributes: Dict[str, Any]
    ) -> float:
        """
        Apply Kalman filter to estimate true confidence from noisy measurements.
        
        Simple implementation assuming:
        - State: True confidence (hidden variable)
        - Measurement: Observed confidence from each system
        - Process noise: Small random walk
        - Measurement noise: Based on system reliability
        """
        if not confidences:
            return 0.5
        
        # Simple Kalman filter (scalar version)
        # Initial state estimate
        x = np.mean(confidences)
        P = 0.1  # Initial error covariance
        
        # Process and measurement noise
        Q = 0.01  # Process noise covariance
        R = 0.05  # Measurement noise covariance
        
        for z in confidences:
            # Prediction step
            x_pred = x
            P_pred = P + Q
            
            # Update step
            K = P_pred / (P_pred + R)  # Kalman gain
            x = x_pred + K * (z - x_pred)
            P = (1 - K) * P_pred
        
        return float(x)
    
    def _regime_adjust_confidence(
        self,
        base_confidence: float,
        market_regime: str,
        signal_attributes: Dict[str, Any]
    ) -> float:
        """
        Adjust confidence based on market regime.
        
        Different regimes affect signal reliability:
        - Trending (bull/bear): Trend-following signals more reliable
        - Sideways: Mean-reversion signals more reliable
        - High volatility: All signals less reliable
        - Low volatility: Breakout signals more reliable
        """
        direction = signal_attributes.get("direction", "long")
        signal_type = signal_attributes.get("signal_type", "trend")
        
        regime_adjustments = {
            "bull": {
                "trend": 1.2,  # Trend signals amplified in bull markets
                "mean_reversion": 0.8,
                "breakout": 1.1,
                "default": 1.0,
            },
            "bear": {
                "trend": 1.2,  # Trend signals also work in bear markets (shorts)
                "mean_reversion": 0.8,
                "breakout": 0.9,
                "default": 1.0,
            },
            "sideways": {
                "trend": 0.7,
                "mean_reversion": 1.3,  # Mean reversion excels in sideways
                "breakout": 0.8,
                "default": 1.0,
            },
            "high_vol": {
                "trend": 0.6,  # High volatility reduces all signal reliability
                "mean_reversion": 0.7,
                "breakout": 0.5,
                "default": 0.6,
            },
            "low_vol": {
                "trend": 0.9,
                "mean_reversion": 1.0,
                "breakout": 1.4,  # Breakouts work well after low vol periods
                "default": 1.0,
            },
            "neutral": {
                "trend": 1.0,
                "mean_reversion": 1.0,
                "breakout": 1.0,
                "default": 1.0,
            },
        }
        
        regime_map = regime_adjustments.get(market_regime, regime_adjustments["neutral"])
        adjustment = regime_map.get(signal_type, regime_map["default"])
        
        # Apply adjustment with bounds
        adjusted = base_confidence * adjustment
        return float(np.clip(adjusted, 0.0, 1.0))
    
    def calculate_portfolio_confidence(
        self,
        signals: List[Dict[str, Any]],
        portfolio_state: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculate portfolio-level confidence considering diversification and risk.
        
        Args:
            signals: List of candidate signals
            portfolio_state: Current portfolio state including:
                - current_positions: List of open positions
                - portfolio_value: Total portfolio value
                - max_drawdown: Current maximum drawdown
                - correlation_matrix: Asset correlations
                
        Returns:
            Portfolio confidence metrics:
                - diversification_score: How well signals diversify risk
                - correlation_penalty: Penalty for high correlation
                - concentration_penalty: Penalty for position concentration
                - overall_portfolio_confidence: Combined confidence
        """
        if not signals:
            return {"overall_portfolio_confidence": 0.0}
        
        # Extract symbols from signals
        signal_symbols = [s.get("symbol") for s in signals if s.get("symbol")]
        
        # Calculate diversification score (more symbols = better)
        unique_symbols = set(signal_symbols)
        diversification_score = min(len(unique_symbols) / 10, 1.0)
        
        # Calculate correlation penalty
        correlation_matrix = portfolio_state.get("correlation_matrix", {})
        correlation_penalty = self._calculate_correlation_penalty(
            signal_symbols, correlation_matrix
        )
        
        # Calculate concentration penalty
        current_positions = portfolio_state.get("current_positions", [])
        concentration_penalty = self._calculate_concentration_penalty(
            signals, current_positions, portfolio_state.get("portfolio_value", 1.0)
        )
        
        # Calculate average signal confidence
        signal_confidences = [s.get("confidence", 0.5) for s in signals]
        avg_confidence = np.mean(signal_confidences) if signal_confidences else 0.5
        
        # Combine factors
        overall_confidence = (
            0.5 * avg_confidence +
            0.2 * diversification_score +
            0.15 * (1 - correlation_penalty) +
            0.15 * (1 - concentration_penalty)
        )
        
        return {
            "diversification_score": float(diversification_score),
            "correlation_penalty": float(correlation_penalty),
            "concentration_penalty": float(concentration_penalty),
            "average_signal_confidence": float(avg_confidence),
            "overall_portfolio_confidence": float(overall_confidence),
        }
    
    def _calculate_correlation_penalty(
        self,
        symbols: List[str],
        correlation_matrix: Dict[str, Dict[str, float]]
    ) -> float:
        """Calculate penalty for high correlation between signals."""
        if len(symbols) < 2:
            return 0.0
        
        total_correlation = 0
        count = 0
        
        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                if sym1 in correlation_matrix and sym2 in correlation_matrix[sym1]:
                    corr = abs(correlation_matrix[sym1][sym2])
                    total_correlation += corr
                    count += 1
        
        if count == 0:
            return 0.0
        
        avg_correlation = total_correlation / count
        
        # Penalty increases with correlation
        # No penalty for corr < 0.3, max penalty for corr > 0.8
        penalty = max(0, (avg_correlation - 0.3) / 0.5)
        return float(min(penalty, 1.0))
    
    def _calculate_concentration_penalty(
        self,
        signals: List[Dict[str, Any]],
        current_positions: List[Dict[str, Any]],
        portfolio_value: float
    ) -> float:
        """Calculate penalty for position concentration."""
        # Calculate proposed position sizes
        proposed_sizes = {}
        for signal in signals:
            symbol = signal.get("symbol")
            if not symbol:
                continue
            
            # Estimate position size (simplified)
            position_size_pct = signal.get("position_size_pct", 0.02)
            proposed_sizes[symbol] = proposed_sizes.get(symbol, 0) + position_size_pct
        
        # Add existing positions
        for position in current_positions:
            symbol = position.get("symbol")
            size_pct = position.get("size_pct", 0)
            if symbol:
                proposed_sizes[symbol] = proposed_sizes.get(symbol, 0) + size_pct
        
        # Calculate Herfindahl-Hirschman Index (HHI) for concentration
        total_exposure = sum(proposed_sizes.values())
        if total_exposure == 0:
            return 0.0
        
        # Normalize to sum to 1 for HHI calculation
        normalized_sizes = {k: v/total_exposure for k, v in proposed_sizes.items()}
        
        # HHI = sum of squared market shares
        hhi = sum(share ** 2 for share in normalized_sizes.values())
        
        # Convert HHI to penalty (0-1 scale)
        # Perfect diversification: HHI = 1/n
        # Max concentration: HHI = 1 (single position)
        n = len(normalized_sizes)
        if n <= 1:
            return 1.0  # Max penalty for single position
        
        perfect_hhi = 1 / n
        penalty = (hhi - perfect_hhi) / (1 - perfect_hhi)
        
        return float(max(0, min(penalty, 1.0)))


class TimeDecayCalculator:
    """
    Calculate confidence with exponential time decay.
    
    Recent performance matters more than old performance.
    """
    
    def __init__(self, half_life_days: float = 30.0):
        """
        Initialize with half-life parameter.
        
        Args:
            half_life_days: Number of days for performance to decay to half weight
        """
        self.half_life_days = half_life_days
        self.decay_rate = np.log(2) / half_life_days
    
    def calculate_time_decayed_confidence(
        self,
        performance_history: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate confidence with exponential time decay.
        
        Args:
            performance_history: List of performance records with:
                - timestamp: When the performance occurred
                - outcome: "success", "failure", or "neutral"
                - pnl: Profit/loss percentage
                
        Returns:
            Time-decayed confidence score (0-1)
        """
        if not performance_history:
            return 0.5
        
        total_weight = 0
        weighted_success = 0
        
        now = datetime.now()
        
        for record in performance_history:
            timestamp_str = record.get("timestamp")
            if not timestamp_str:
                continue
            
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                continue
            
            # Calculate age in days
            age_days = (now - timestamp).total_seconds() / (24 * 3600)
            
            # Exponential decay weight
            weight = np.exp(-self.decay_rate * age_days)
            
            outcome = record.get("outcome")
            if outcome == "success":
                weighted_success += weight
                total_weight += weight
            elif outcome == "failure":
                total_weight += weight
        
        if total_weight == 0:
            return 0.5
        
        return weighted_success / total_weight
    
    def calculate_recent_trend(
        self,
        performance_history: List[Dict[str, Any]],
        lookback_days: float = 7.0
    ) -> Dict[str, float]:
        """
        Calculate recent performance trend.
        
        Args:
            performance_history: Performance records
            lookback_days: Lookback period for trend calculation
            
        Returns:
            Dictionary with trend metrics:
                - recent_confidence: Confidence in lookback period
                - trend_slope: Performance trend (positive = improving)
                - trend_strength: How strong the trend is
        """
        if not performance_history:
            return {
                "recent_confidence": 0.5,
                "trend_slope": 0.0,
                "trend_strength": 0.0,
            }
        
        now = datetime.now()
        cutoff_time = now - timedelta(days=lookback_days)
        
        # Filter recent records
        recent_records = []
        for record in performance_history:
            timestamp_str = record.get("timestamp")
            if not timestamp_str:
                continue
            
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                continue
            
            if timestamp >= cutoff_time:
                recent_records.append(record)
        
        if not recent_records:
            return {
                "recent_confidence": 0.5,
                "trend_slope": 0.0,
                "trend_strength": 0.0,
            }
        
        # Calculate recent confidence
        recent_successes = sum(1 for r in recent_records if r.get("outcome") == "success")
        recent_failures = sum(1 for r in recent_records if r.get("outcome") == "failure")
        
        recent_total = recent_successes + recent_failures
        recent_confidence = recent_successes / recent_total if recent_total > 0 else 0.5
        
        # Calculate trend using linear regression on daily performance
        daily_performance = {}
        for record in performance_history:
            timestamp_str = record.get("timestamp")
            if not timestamp_str:
                continue
            
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                date_key = timestamp.date()
            except (ValueError, TypeError):
                continue
            
            outcome = record.get("outcome")
            pnl = record.get("pnl", 0)
            
            if date_key not in daily_performance:
                daily_performance[date_key] = {"successes": 0, "failures": 0, "total_pnl": 0}
            
            if outcome == "success":
                daily_performance[date_key]["successes"] += 1
                daily_performance[date_key]["total_pnl"] += pnl
            elif outcome == "failure":
                daily_performance[date_key]["failures"] += 1
                daily_performance[date_key]["total_pnl"] -= abs(pnl)
        
        # Convert to time series
        dates = sorted(daily_performance.keys())
        if len(dates) < 3:
            return {
                "recent_confidence": float(recent_confidence),
                "trend_slope": 0.0,
                "trend_strength": 0.0,
            }
        
        # Calculate daily success rates
        daily_rates = []
        for date in dates:
            day_data = daily_performance[date]
            total = day_data["successes"] + day_data["failures"]
            if total > 0:
                rate = day_data["successes"] / total
                daily_rates.append(rate)
            else:
                daily_rates.append(0.5)
        
        # Linear regression for trend
        x = np.arange(len(daily_rates))
        y = np.array(daily_rates)
        
        if len(y) > 1:
            slope, intercept = np.polyfit(x, y, 1)
            r_squared = np.corrcoef(x, y)[0, 1] ** 2 if len(y) > 2 else 0
        else:
            slope, intercept, r_squared = 0.0, 0.5, 0.0
        
        return {
            "recent_confidence": float(recent_confidence),
            "trend_slope": float(slope),
            "trend_strength": float(r_squared),
        }


# Factory function for easy access
def create_confidence_calculator(method: str = "bayesian", **kwargs):
    """
    Factory function to create confidence calculator.
    
    Args:
        method: Calculation method ("bayesian", "time_decay", or "combined")
        **kwargs: Additional arguments for the calculator
        
    Returns:
        Appropriate confidence calculator instance
    """
    if method == "bayesian":
        return BayesianConfidenceCalculator(**kwargs)
    elif method == "time_decay":
        return TimeDecayCalculator(**kwargs)
    elif method == "combined":
        # Return a composite calculator
        class CompositeCalculator:
            def __init__(self, **kwargs):
                self.bayesian = BayesianConfidenceCalculator(**kwargs)
                self.time_decay = TimeDecayCalculator(**kwargs)
            
            def calculate_combined_confidence(self, performance_history):
                bayesian_result = self.bayesian.update_system_confidence(
                    "composite", performance_history
                )
                time_decay_result = self.time_decay.calculate_time_decayed_confidence(
                    performance_history
                )
                
                # Combine results
                combined = 0.6 * bayesian_result["weighted_confidence"] + \
                          0.4 * time_decay_result
                
                return {
                    "bayesian_confidence": bayesian_result["weighted_confidence"],
                    "time_decay_confidence": time_decay_result,
                    "combined_confidence": combined,
                }
        
        return CompositeCalculator(**kwargs)
    else:
        raise ValueError(f"Unknown confidence calculation method: {method}")


if __name__ == "__main__":
    # Example usage
    calculator = BayesianConfidenceCalculator()
    
    # Example performance history
    performance_history = [
        {"timestamp": "2026-02-28T10:00:00Z", "outcome": "success", "pnl": 0.03},
        {"timestamp": "2026-02-27T14:30:00Z", "outcome": "failure", "pnl": -0.02},
        {"timestamp": "2026-02-26T09:15:00Z", "outcome": "success", "pnl": 0.05},
        {"timestamp": "2026-02-25T16:45:00Z", "outcome": "success", "pnl": 0.02},
        {"timestamp": "2026-02-24T11:20:00Z", "outcome": "failure", "pnl": -0.01},
    ]
    
    result = calculator.update_system_confidence("test_system", performance_history)
    print("Bayesian Confidence Calculation:")
    print(json.dumps(result, indent=2))
    
    # Time decay example
    time_decay_calc = TimeDecayCalculator(half_life_days=14)
    decayed_conf = time_decay_calc.calculate_time_decayed_confidence(performance_history)
    print(f"\nTime-decayed confidence: {decayed_conf:.3f}")
    
    # Trend calculation
    trend_result = time_decay_calc.calculate_recent_trend(performance_history)
    print(f"\nRecent trend: {trend_result}")