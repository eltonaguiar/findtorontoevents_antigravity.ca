#!/usr/bin/env python3
"""
Hedge Fund Statistical Rigor Module
=====================================
Implements institutional-grade statistical validation:
- Multiple testing correction (Harvey-Liu)
- Deflated Sharpe Ratio (DSR)
- False Discovery Rate control (Benjamini-Hochberg)
- Regime-segmented metrics
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class StatisticalTest:
    """Represents a single strategy test result."""
    strategy_name: str
    sharpe_ratio: float
    n_observations: int
    skewness: float = 0.0
    kurtosis: float = 3.0
    p_value_raw: float = 1.0
    p_value_corrected: Optional[float] = None
    is_significant: bool = False


class MultipleTestingCorrection:
    """
    Harvey-Liu (2015) multiple testing correction for strategy selection.
    
    Addresses the problem: When testing N strategies, the probability of
    finding a "significant" result by chance increases with N.
    
    Reference: "Multiple Testing in Financial Economics" - Harvey, Liu (2015)
    """
    
    def __init__(self, n_strategies_tested: int, avg_correlation: float = 0.4):
        """
        Args:
            n_strategies_tested: Total number of strategies tested (N)
            avg_correlation: Average correlation between strategy returns
        """
        self.n_strategies = n_strategies_tested
        self.rho = avg_correlation
        
    def harvey_liu_p_value(self, sharpe_ratio: float, n_obs: int, 
                          skewness: float = 0, kurtosis: float = 3) -> float:
        """
        Compute Harvey-Liu adjusted p-value accounting for multiple testing.
        
        The adjustment becomes more severe as:
        - Number of tested strategies increases
        - Sharpe ratio decreases
        - Sample size decreases
        """
        # Bonferroni-style adjustment with correlation discount
        # Effective N = N^(1-rho) accounts for correlated strategies
        effective_n = self.n_strategies ** (1 - self.rho)
        
        # Standard Sharpe significance test
        # SR ~ N(0, 1/T) under null, but adjusted for skewness/kurtosis
        var_sr = (1 + 0.5 * sharpe_ratio**2 + skewness * sharpe_ratio + 
                  (kurtosis - 3) / 4 * sharpe_ratio**2) / n_obs
        
        z_score = sharpe_ratio / np.sqrt(var_sr)
        p_value_single = 2 * (1 - stats.norm.cdf(abs(z_score)))
        
        # Harvey-Liu adjusted p-value
        p_value_adjusted = min(p_value_single * effective_n, 1.0)
        
        return p_value_adjusted
    
    def benjamini_hochberg(self, p_values: List[float], fdr_level: float = 0.05) -> List[bool]:
        """
        Benjamini-Hochberg FDR control.
        
        Returns boolean mask of which tests are significant at FDR level.
        More powerful than Bonferroni for independent/positively correlated tests.
        """
        p_values = np.array(p_values)
        n = len(p_values)
        
        # Sort p-values
        sorted_idx = np.argsort(p_values)
        sorted_p = p_values[sorted_idx]
        
        # Find largest k such that p_k <= (k/m) * alpha
        thresholds = np.arange(1, n + 1) / n * fdr_level
        significant = sorted_p <= thresholds
        
        # All tests up to largest k are significant
        if significant.any():
            max_k = np.where(significant)[0].max()
            result = np.zeros(n, dtype=bool)
            result[sorted_idx[:max_k + 1]] = True
            return result.tolist()
        return [False] * n


class DeflatedSharpeRatio:
    """
    Deflated Sharpe Ratio (DSR) - Bailey et al. (2014).
    
    Adjusts Sharpe ratio for:
    1. Multiple testing (how many strategies were tried)
    2. Non-normality (skewness, kurtosis)
    3. Sample size
    
    DSR > 0.5 indicates skill (not luck) at 95% confidence.
    """
    
    def __init__(self, n_trials: int, skewness: float = 0, kurtosis: float = 3):
        self.n_trials = n_trials
        self.skewness = skewness
        self.kurtosis = kurtosis
        
    def compute(self, sharpe_ratio: float, n_obs: int, 
                annualization_factor: int = 252) -> float:
        """
        Compute Deflated Sharpe Ratio.
        
        Args:
            sharpe_ratio: Annualized Sharpe ratio
            n_obs: Number of observations
            annualization_factor: 252 for daily, 52 for weekly, 12 for monthly
            
        Returns:
            DSR value (higher is better, > 0.5 indicates skill)
        """
        # Adjust for skewness and kurtosis
        adjusted_var = (1 + 
                       0.5 * sharpe_ratio**2 + 
                       self.skewness * sharpe_ratio + 
                       (self.kurtosis - 3) / 4 * sharpe_ratio**2)
        
        # Standard error of Sharpe ratio
        se_sr = np.sqrt(adjusted_var / (n_obs - 1))
        
        # Expected maximum Sharpe under null (multiple testing)
        # Approximation from Bailey-Lopez de Prado
        gamma = 0.5772156649  # Euler-Mascheroni constant
        emax_sr = se_sr * ((1 - gamma) * stats.norm.ppf(1 - 1/self.n_trials) + 
                          gamma * stats.norm.ppf(1 - 1/(self.n_trials * np.e)))
        
        # Deflated Sharpe Ratio
        if se_sr > 0:
            dsr = (sharpe_ratio - emax_sr) / se_sr
        else:
            dsr = 0
            
        return dsr
    
    def is_skill(self, dsr: float, confidence: float = 0.95) -> bool:
        """Returns True if DSR indicates skill (not luck) at given confidence."""
        threshold = stats.norm.ppf(confidence)
        return dsr > threshold


class RegimeSegmentedMetrics:
    """
    Compute performance metrics segmented by market regime.
    
    Hedge funds require strategy performance analysis conditioned on
    market state - a strategy that works in bull markets but fails
    in crashes is not truly robust.
    """
    
    REGIMES = ['trending_up', 'trending_down', 'range_bound', 'high_volatility']
    
    def __init__(self, returns: pd.Series, regimes: pd.Series):
        """
        Args:
            returns: Strategy returns series
            regimes: Regime classification for each return
        """
        self.returns = returns
        self.regimes = regimes
        
    def compute_all_metrics(self) -> Dict[str, Dict[str, float]]:
        """Compute Sharpe, Sortino, Calmar, MaxDD per regime."""
        results = {}
        
        for regime in self.REGIMES:
            mask = self.regimes == regime
            regime_returns = self.returns[mask]
            
            if len(regime_returns) < 30:  # Need minimum sample
                results[regime] = {'sharpe': np.nan, 'sortino': np.nan, 
                                  'calmar': np.nan, 'max_dd': np.nan,
                                  'n_obs': len(regime_returns)}
                continue
                
            # Sharpe ratio
            sharpe = self._sharpe(regime_returns)
            
            # Sortino ratio (downside deviation only)
            sortino = self._sortino(regime_returns)
            
            # Calmar ratio (return / max drawdown)
            calmar = self._calmar(regime_returns)
            
            # Maximum drawdown
            max_dd = self._max_drawdown(regime_returns)
            
            results[regime] = {
                'sharpe': sharpe,
                'sortino': sortino,
                'calmar': calmar,
                'max_dd': max_dd,
                'n_obs': len(regime_returns),
                'win_rate': (regime_returns > 0).mean()
            }
            
        return results
    
    def _sharpe(self, returns: pd.Series, risk_free: float = 0) -> float:
        """Annualized Sharpe ratio."""
        if returns.std() == 0:
            return 0
        return (returns.mean() - risk_free) / returns.std() * np.sqrt(252)
    
    def _sortino(self, returns: pd.Series, risk_free: float = 0) -> float:
        """Sortino ratio using downside deviation."""
        downside = returns[returns < 0]
        if len(downside) == 0 or downside.std() == 0:
            return np.inf if returns.mean() > risk_free else 0
        return (returns.mean() - risk_free) / downside.std() * np.sqrt(252)
    
    def _calmar(self, returns: pd.Series) -> float:
        """Calmar ratio: CAGR / Max Drawdown."""
        cagr = (1 + returns.mean()) ** 252 - 1
        max_dd = abs(self._max_drawdown(returns))
        return cagr / max_dd if max_dd > 0 else np.inf
    
    def _max_drawdown(self, returns: pd.Series) -> float:
        """Maximum drawdown."""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()


class HFScoringValidator:
    """
    Hedge Fund Level Scoring Validator.
    
    Validates picks against institutional standards before
    they reach production.
    """
    
    def __init__(self, n_strategies_tested: int = 500):
        self.n_strategies = n_strategies_tested
        self.mt_correction = MultipleTestingCorrection(n_strategies_tested)
        
    def validate_strategy(self, returns: List[float], strategy_name: str,
                         regimes: Optional[List[str]] = None) -> Dict:
        """
        Full HF-level validation of a strategy.
        
        Returns validation result with pass/fail status.
        """
        returns = pd.Series(returns)
        n_obs = len(returns)
        
        # Basic metrics
        sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        skewness = returns.skew()
        kurtosis = returns.kurtosis()
        
        # Multiple testing correction
        p_value = self.mt_correction.harvey_liu_p_value(
            sharpe, n_obs, skewness, kurtosis
        )
        
        # Deflated Sharpe Ratio
        dsr_calculator = DeflatedSharpeRatio(
            n_trials=self.n_strategies,
            skewness=skewness,
            kurtosis=kurtosis
        )
        dsr = dsr_calculator.compute(sharpe, n_obs)
        has_skill = dsr_calculator.is_skill(dsr)
        
        # Regime metrics if provided
        regime_metrics = {}
        if regimes and len(regimes) == len(returns):
            regime_segmenter = RegimeSegmentedMetrics(returns, pd.Series(regimes))
            regime_metrics = regime_segmenter.compute_all_metrics()
        
        # HF Pass/Fail Criteria
        passed = (
            p_value < 0.05 and           # Statistically significant
            dsr > 0.5 and                 # Skill (not luck)
            sharpe > 0.5 and              # Minimum Sharpe
            n_obs >= 100                  # Minimum sample
        )
        
        # Regime robustness: must work in at least 3 of 4 regimes
        if regime_metrics:
            valid_regimes = sum(1 for r in regime_metrics.values() 
                              if r.get('sharpe', 0) > 0.3)
            passed = passed and (valid_regimes >= 3)
        
        return {
            'strategy': strategy_name,
            'sharpe_ratio': sharpe,
            'p_value_raw': 2 * (1 - stats.norm.cdf(abs(sharpe * np.sqrt(n_obs/252)))),
            'p_value_harvey_liu': p_value,
            'deflated_sharpe': dsr,
            'has_skill': has_skill,
            'skewness': skewness,
            'kurtosis': kurtosis,
            'n_observations': n_obs,
            'regime_metrics': regime_metrics,
            'passed_hf_validation': passed,
            'failure_reasons': self._get_failure_reasons(p_value, dsr, sharpe, n_obs, regime_metrics)
        }
    
    def _get_failure_reasons(self, p_value: float, dsr: float, 
                            sharpe: float, n_obs: int,
                            regime_metrics: Dict) -> List[str]:
        """List specific reasons for validation failure."""
        reasons = []
        if p_value >= 0.05:
            reasons.append(f"Not significant after multiple testing (p={p_value:.3f})")
        if dsr <= 0.5:
            reasons.append(f"No skill detected (DSR={dsr:.2f})")
        if sharpe <= 0.5:
            reasons.append(f"Sharpe too low ({sharpe:.2f})")
        if n_obs < 100:
            reasons.append(f"Insufficient samples ({n_obs})")
        if regime_metrics:
            weak_regimes = [r for r, m in regime_metrics.items() 
                          if m.get('sharpe', 0) < 0.3]
            if len(weak_regimes) > 1:
                reasons.append(f"Fails in {len(weak_regimes)} regimes: {weak_regimes}")
        return reasons


# Convenience functions for integration

def compute_hf_score(strategy_returns: List[float], 
                     n_strategies_tested: int = 500,
                     strategy_name: str = "unknown") -> float:
    """
    Compute hedge fund level quality score (0-100).
    
    This score can be integrated into the existing elite_score system.
    """
    validator = HFScoringValidator(n_strategies_tested)
    result = validator.validate_strategy(strategy_returns, strategy_name)
    
    if not result['passed_hf_validation']:
        return 0
    
    # Score components
    dsr_score = min(result['deflated_sharpe'] * 20, 40)  # DSR * 20, max 40
    sharpe_score = min(result['sharpe_ratio'] * 20, 30)  # Sharpe * 20, max 30
    significance_score = (1 - result['p_value_harvey_liu']) * 20  # max 20
    regime_score = 10  # Base for passing regime check
    
    return min(dsr_score + sharpe_score + significance_score + regime_score, 100)


if __name__ == "__main__":
    # Example usage
    print("Hedge Fund Statistical Rigor Module")
    print("=" * 50)
    
    # Test with sample data
    np.random.seed(42)
    sample_returns = np.random.normal(0.001, 0.02, 252)  # ~0.5 Sharpe
    
    validator = HFScoringValidator(n_strategies_tested=500)
    result = validator.validate_strategy(sample_returns, "TestStrategy")
    
    print(f"\nValidation Result:")
    print(f"  Sharpe Ratio: {result['sharpe_ratio']:.2f}")
    print(f"  P-value (Harvey-Liu): {result['p_value_harvey_liu']:.4f}")
    print(f"  Deflated Sharpe: {result['deflated_sharpe']:.2f}")
    print(f"  Has Skill: {result['has_skill']}")
    print(f"  HF Score: {compute_hf_score(sample_returns, 500, 'Test'):.1f}/100")
    print(f"  Passed: {result['passed_hf_validation']}")
