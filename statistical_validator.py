#!/usr/bin/env python3
"""
Statistical Validation Suite
Addresses: Insufficient sample sizes, need for rigorous testing

Implements:
- Deflated Sharpe Ratio (accounts for multiple testing)
- Probabilistic Sharpe Ratio (probability Sharpe > benchmark)
- Monte Carlo simulation (10,000 runs)
- Bootstrap confidence intervals
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple, Optional


class StatisticalValidator:
    """
    Comprehensive statistical validation for trading strategies.
    """
    
    def __init__(self, n_bootstrap: int = 10000, n_monte_carlo: int = 10000):
        self.n_bootstrap = n_bootstrap
        self.n_monte_carlo = n_monte_carlo
    
    def deflated_sharpe_ratio(self, 
                             sharpe: float,
                             n_trials: int,
                             skewness: float,
                             kurtosis: float,
                             periods_per_year: int = 252) -> float:
        """
        Calculate Deflated Sharpe Ratio (Lopez de Prado).
        
        Adjusts Sharpe ratio for multiple testing bias.
        """
        # Estimate variance of Sharpe ratios across trials
        # V = (1 + (skewness * sharpe) + ((kurtosis - 1) / 4) * sharpe^2) / (periods - 1)
        
        variance = (1 + skewness * sharpe + ((kurtosis - 1) / 4) * sharpe**2) / (periods_per_year - 1)
        
        # Multiple testing adjustment
        # DSR = sharpe * sqrt(1 - V * log(n_trials))
        
        if variance * np.log(n_trials) >= 1:
            return 0.0  # Overfitting too severe
        
        dsr = sharpe * np.sqrt(1 - variance * np.log(n_trials))
        return dsr
    
    def probabilistic_sharpe_ratio(self,
                                   observed_sharpe: float,
                                   benchmark_sharpe: float,
                                   n_periods: int,
                                   skewness: float,
                                   kurtosis: float) -> float:
        """
        Calculate Probabilistic Sharpe Ratio.
        
        Probability that observed Sharpe exceeds benchmark.
        """
        # Standard error of Sharpe ratio
        # SE = sqrt((1 + (skewness * S) + ((kurtosis - 1)/4) * S^2) / (n-1))
        
        se = np.sqrt((1 + skewness * observed_sharpe + 
                     ((kurtosis - 1) / 4) * observed_sharpe**2) / (n_periods - 1))
        
        # Z-score
        z_score = (observed_sharpe - benchmark_sharpe) / se
        
        # P(SR > benchmark)
        psr = stats.norm.cdf(z_score)
        return psr
    
    def monte_carlo_simulation(self,
                              returns: np.ndarray,
                              n_simulations: int = None) -> Dict:
        """
        Run Monte Carlo simulation for strategy robustness.
        
        Shuffles returns to test if performance is due to luck.
        """
        if n_simulations is None:
            n_simulations = self.n_monte_carlo
        
        n_periods = len(returns)
        simulated_sharpes = []
        simulated_cumulative = []
        
        for _ in range(n_simulations):
            # Random permutation of returns
            shuffled = np.random.choice(returns, size=n_periods, replace=True)
            
            # Calculate metrics
            mean_return = np.mean(shuffled)
            std_return = np.std(shuffled)
            
            if std_return > 0:
                sharpe = mean_return / std_return * np.sqrt(252)
                simulated_sharpes.append(sharpe)
            
            # Cumulative return
            cumulative = np.prod(1 + shuffled) - 1
            simulated_cumulative.append(cumulative)
        
        # Calculate actual metrics
        actual_sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
        actual_cumulative = np.prod(1 + returns) - 1
        
        # Percentiles
        sharpe_percentile = stats.percentileofscore(simulated_sharpes, actual_sharpe)
        cumulative_percentile = stats.percentileofscore(simulated_cumulative, actual_cumulative)
        
        # Probability of positive return
        prob_profit = sum(1 for c in simulated_cumulative if c > 0) / n_simulations
        
        return {
            'actual_sharpe': float(actual_sharpe),
            'sharpe_percentile': float(sharpe_percentile),
            'actual_cumulative': float(actual_cumulative),
            'cumulative_percentile': float(cumulative_percentile),
            'prob_profit': float(prob_profit),
            'simulated_sharpes': {
                'mean': float(np.mean(simulated_sharpes)),
                'std': float(np.std(simulated_sharpes)),
                '5th': float(np.percentile(simulated_sharpes, 5)),
                '95th': float(np.percentile(simulated_sharpes, 95))
            },
            'is_significant': sharpe_percentile > 95  # Top 5%
        }
    
    def bootstrap_confidence_interval(self,
                                     returns: np.ndarray,
                                     statistic_func = None,
                                     confidence: float = 0.95) -> Dict:
        """
        Calculate bootstrap confidence intervals.
        """
        if statistic_func is None:
            statistic_func = lambda x: np.mean(x) / np.std(x) * np.sqrt(252) if np.std(x) > 0 else 0
        
        n = len(returns)
        bootstrap_stats = []
        
        for _ in range(self.n_bootstrap):
            # Resample with replacement
            sample = np.random.choice(returns, size=n, replace=True)
            stat = statistic_func(sample)
            bootstrap_stats.append(stat)
        
        # Calculate confidence interval
        alpha = 1 - confidence
        ci_lower = np.percentile(bootstrap_stats, alpha/2 * 100)
        ci_upper = np.percentile(bootstrap_stats, (1 - alpha/2) * 100)
        
        actual_stat = statistic_func(returns)
        
        return {
            'statistic': float(actual_stat),
            'confidence_level': confidence,
            'ci_lower': float(ci_lower),
            'ci_upper': float(ci_upper),
            'is_significant': ci_lower > 0,  # CI excludes zero
            'bootstrap_mean': float(np.mean(bootstrap_stats)),
            'bootstrap_std': float(np.std(bootstrap_stats))
        }
    
    def minimum_sample_size(self,
                           expected_sharpe: float,
                           desired_precision: float = 0.5,
                           confidence: float = 0.95) -> int:
        """
        Calculate minimum sample size needed for reliable Sharpe estimate.
        """
        # Formula: n = (Z * sigma / E)^2
        # Where Z is z-score, sigma is std of Sharpe, E is desired precision
        
        z_score = stats.norm.ppf((1 + confidence) / 2)
        
        # Approximate standard error of Sharpe
        se = 1 / np.sqrt(252)  # Rough approximation
        
        n = (z_score * se / desired_precision) ** 2
        
        return int(np.ceil(n))
    
    def comprehensive_validation(self, returns: np.ndarray) -> Dict:
        """
        Run all validation tests.
        """
        n = len(returns)
        
        if n < 30:
            return {'error': f'Insufficient data: {n} samples (need >30)'}
        
        # Calculate basic stats
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        sharpe = mean_return / std_return * np.sqrt(252) if std_return > 0 else 0
        skewness = stats.skew(returns)
        kurtosis = stats.kurtosis(returns)
        
        # Run all tests
        results = {
            'sample_size': n,
            'mean_return': float(mean_return),
            'std_return': float(std_return),
            'sharpe_ratio': float(sharpe),
            'skewness': float(skewness),
            'kurtosis': float(kurtosis),
            'monte_carlo': self.monte_carlo_simulation(returns),
            'bootstrap': self.bootstrap_confidence_interval(returns),
            'psr': self.probabilistic_sharpe_ratio(
                sharpe, 0.0, n, skewness, kurtosis
            ),
            'minimum_sample': self.minimum_sample_size(sharpe)
        }
        
        # Overall assessment
        checks = [
            results['monte_carlo']['is_significant'],
            results['bootstrap']['is_significant'],
            results['psr'] > 0.95,
            n >= results['minimum_sample']
        ]
        
        results['is_validated'] = all(checks)
        results['checks_passed'] = sum(checks)
        results['total_checks'] = len(checks)
        
        return results


# Example usage
if __name__ == "__main__":
    # Generate sample returns
    np.random.seed(42)
    
    # Strategy with edge (positive drift)
    returns_with_edge = np.random.normal(0.0005, 0.02, 500)  # 0.05% daily return, 2% vol
    
    # Random strategy (no edge)
    returns_random = np.random.normal(0, 0.02, 500)
    
    validator = StatisticalValidator(n_bootstrap=10000, n_monte_carlo=10000)
    
    print("="*60)
    print("STATISTICAL VALIDATION TEST")
    print("="*60)
    
    print("\nStrategy WITH edge:")
    results = validator.comprehensive_validation(returns_with_edge)
    print(f"  Sample size: {results['sample_size']}")
    print(f"  Sharpe ratio: {results['sharpe_ratio']:.3f}")
    print(f"  Monte Carlo percentile: {results['monte_carlo']['sharpe_percentile']:.1f}%")
    print(f"  Bootstrap 95% CI: [{results['bootstrap']['ci_lower']:.3f}, {results['bootstrap']['ci_upper']:.3f}]")
    print(f"  PSR (prob SR > 0): {results['psr']:.3f}")
    print(f"  Validated: {results['is_validated']}")
    
    print("\nStrategy WITHOUT edge (random):")
    results = validator.comprehensive_validation(returns_random)
    print(f"  Sample size: {results['sample_size']}")
    print(f"  Sharpe ratio: {results['sharpe_ratio']:.3f}")
    print(f"  Monte Carlo percentile: {results['monte_carlo']['sharpe_percentile']:.1f}%")
    print(f"  Bootstrap 95% CI: [{results['bootstrap']['ci_lower']:.3f}, {results['bootstrap']['ci_upper']:.3f}]")
    print(f"  PSR (prob SR > 0): {results['psr']:.3f}")
    print(f"  Validated: {results['is_validated']}")
    
    print("="*60)
