#!/usr/bin/env python3
"""
PROBABILISTIC SHARPE RATIO ENGINE
Implements advanced statistical validation for trading strategies

Features:
- Probabilistic Sharpe ratio calculation
- Deflated Sharpe ratio (removes backtest overfitting)
- Monte Carlo strategy validation
- Model confidence intervals
- Risk-adjusted performance metrics
- Statistical significance testing
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np
import pandas as pd
try:
    from scipy import stats  # type: ignore[import-unresolved]
    from scipy.optimize import minimize_scalar  # type: ignore[import-unresolved]
except ImportError:
    stats = None  # type: ignore[assignment]
    minimize_scalar = None  # type: ignore[assignment]
import warnings

warnings.filterwarnings('ignore')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('probabilistic_sharpe.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class ProbabilisticSharpeConfig:
    """Configuration for probabilistic Sharpe analysis"""
    RISK_FREE_RATE: float = 0.02  # 2% annual risk-free rate
    ANNUALIZATION_FACTOR: int = 252  # Trading days per year
    MIN_OBSERVATIONS: int = 30  # Minimum returns for analysis
    CONFIDENCE_LEVEL: float = 0.95  # Statistical confidence level
    MONTE_CARLO_SIMS: int = 10000  # Monte Carlo simulations
    MAX_DRAWDOWN_CONFIDENCE: float = 0.99  # For CVaR calculations

# ============================================================================
# PROBABILISTIC SHARPE RATIO
# ============================================================================

class ProbabilisticSharpeAnalyzer:
    """Advanced Sharpe ratio analysis with statistical rigor"""

    def __init__(self, config: Optional[ProbabilisticSharpeConfig] = None):
        self.config = config or ProbabilisticSharpeConfig()

    def calculate_probabilistic_sharpe(self, returns: np.ndarray,
                                     benchmark_returns: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Calculate probabilistic Sharpe ratio with confidence intervals

        Returns:
            {
                'sharpe_ratio': float,
                'probabilistic_sharpe': float,
                'sharpe_ci_lower': float,
                'sharpe_ci_upper': float,
                'expected_max_sharpe': float,
                'sharpe_p_value': float,
                'is_significant': bool
            }
        """
        if len(returns) < self.config.MIN_OBSERVATIONS:
            return {'error': f'Need at least {self.config.MIN_OBSERVATIONS} observations'}

        # Annualize returns and volatility
        mean_return = float(np.mean(returns))
        volatility = float(np.std(returns, ddof=1))

        if volatility == 0:
            return {'error': 'Zero volatility - cannot calculate Sharpe ratio'}

        sharpe_ratio = self._annualize_sharpe(mean_return, volatility)

        # Probabilistic Sharpe ratio (expected value under null hypothesis)
        prob_sharpe = self._calculate_probabilistic_sharpe(returns)

        # Confidence intervals via bootstrap
        sharpe_ci_lower, sharpe_ci_upper = self._bootstrap_sharpe_ci(returns)

        # Expected maximum Sharpe (deflated Sharpe)
        expected_max_sharpe = self._calculate_expected_max_sharpe(len(returns))

        # Statistical significance test
        sharpe_p_value = self._sharpe_significance_test(returns)
        is_significant = sharpe_p_value < (1 - self.config.CONFIDENCE_LEVEL)

        return {
            'sharpe_ratio': sharpe_ratio,
            'probabilistic_sharpe': prob_sharpe,
            'sharpe_ci_lower': float(sharpe_ci_lower),
            'sharpe_ci_upper': float(sharpe_ci_upper),
            'expected_max_sharpe': float(expected_max_sharpe),
            'sharpe_p_value': sharpe_p_value,
            'is_significant': is_significant,
            'deflated_sharpe': sharpe_ratio - expected_max_sharpe,
            'sharpe_skill': max(0, sharpe_ratio - expected_max_sharpe)
        }

    def _annualize_sharpe(self, mean_return: float, volatility: float) -> float:
        """Annualize Sharpe ratio"""
        annualized_return = mean_return * self.config.ANNUALIZATION_FACTOR
        annualized_vol = volatility * np.sqrt(self.config.ANNUALIZATION_FACTOR)
        return (annualized_return - self.config.RISK_FREE_RATE) / annualized_vol

    def _calculate_probabilistic_sharpe(self, returns: np.ndarray) -> float:
        """Calculate probabilistic Sharpe ratio (PSR)"""
        n = len(returns)
        if n <= 1:
            return 0.0

        # Sharpe ratio
        mean_ret = float(np.mean(returns))
        std_ret = float(np.std(returns, ddof=1))
        sr = self._annualize_sharpe(mean_ret, std_ret)

        # Probabilistic Sharpe ratio formula
        # PSR = (SR / sqrt(2/n)) * sqrt(2 * max(SR^2, 0) + 1) - SR
        # Simplified approximation
        skew = stats.skew(returns)
        kurtosis = stats.kurtosis(returns, fisher=True)

        # Adjust for non-normality
        adjustment = 1 + (skew/6) * (sr/np.sqrt(n)) + (kurtosis/24) * (sr**2/n - 1/np.sqrt(n))

        return sr * adjustment

    def _bootstrap_sharpe_ci(self, returns: np.ndarray, n_boot: int = 10000) -> Tuple[float, float]:
        """Calculate Sharpe ratio confidence intervals via bootstrap"""
        n = len(returns)
        sharpe_ratios = []

        for _ in range(n_boot):
            # Bootstrap sample
            boot_returns = np.random.choice(returns, size=n, replace=True)
            mean_ret = float(np.mean(boot_returns))
            std_ret = float(np.std(boot_returns, ddof=1))

            if std_ret > 0:
                sr = self._annualize_sharpe(mean_ret, std_ret)
                sharpe_ratios.append(sr)

        if not sharpe_ratios:
            return 0.0, 0.0

        # Confidence intervals
        alpha = (1 - self.config.CONFIDENCE_LEVEL) / 2
        ci_lower = np.percentile(sharpe_ratios, alpha * 100)
        ci_upper = np.percentile(sharpe_ratios, (1 - alpha) * 100)

        return ci_lower, ci_upper

    def _calculate_expected_max_sharpe(self, n: int) -> float:
        """Calculate expected maximum Sharpe ratio (deflated Sharpe)"""
        # Bailey and Lopez de Prado (2014) deflated Sharpe ratio
        # E[max(SR)] ≈ sqrt(2/n * ln(N)) where N is number of trials
        # For single strategy, use conservative estimate
        return np.sqrt(2/n * np.log(n))

    def _sharpe_significance_test(self, returns: np.ndarray) -> float:
        """Test if Sharpe ratio is statistically significant"""
        n = len(returns)
        if n <= 1:
            return 1.0

        mean_ret = float(np.mean(returns))
        std_ret = float(np.std(returns, ddof=1))

        if std_ret == 0:
            return 1.0

        # t-statistic for Sharpe ratio
        sr = self._annualize_sharpe(mean_ret, std_ret)
        se_sr = np.sqrt((1 + sr**2/2) / (n - 1))  # Standard error of Sharpe ratio

        t_stat = sr / se_sr
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 1))

        return p_value

# ============================================================================
# MONTE CARLO STRATEGY VALIDATOR
# ============================================================================

class MonteCarloStrategyValidator:
    """Monte Carlo validation of trading strategies"""

    def __init__(self, config: Optional[ProbabilisticSharpeConfig] = None):
        self.config = config or ProbabilisticSharpeConfig()

    def validate_strategy(self, strategy_returns: np.ndarray,
                         benchmark_returns: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Monte Carlo validation of strategy performance

        Returns comprehensive statistical analysis including:
        - Probability of outperforming benchmark
        - Maximum drawdown distribution
        - Risk-adjusted return metrics
        - Strategy robustness measures
        """
        n_obs = len(strategy_returns)
        if n_obs < self.config.MIN_OBSERVATIONS:
            return {'error': f'Need at least {self.config.MIN_OBSERVATIONS} observations'}

        # Run Monte Carlo simulations
        mc_results = self._run_monte_carlo(strategy_returns, benchmark_returns)

        # Calculate key metrics
        strategy_metrics = self._calculate_strategy_metrics(strategy_returns)
        benchmark_metrics = None
        if benchmark_returns is not None:
            benchmark_metrics = self._calculate_strategy_metrics(benchmark_returns)

        # Outperformance analysis
        outperformance = self._analyze_outperformance(mc_results, benchmark_returns)

        # Risk metrics
        risk_metrics = self._calculate_risk_metrics(mc_results)

        return {
            'strategy_metrics': strategy_metrics,
            'benchmark_metrics': benchmark_metrics,
            'monte_carlo_results': mc_results,
            'outperformance_analysis': outperformance,
            'risk_metrics': risk_metrics,
            'validation_confidence': self._calculate_validation_confidence(mc_results)
        }

    def _run_monte_carlo(self, returns: np.ndarray,
                        benchmark_returns: Optional[np.ndarray]) -> Dict[str, Any]:
        """Run Monte Carlo simulations"""
        n_sims = self.config.MONTE_CARLO_SIMS
        n_obs = len(returns)

        # Fit distribution to returns
        dist_params = self._fit_returns_distribution(returns)

        sim_returns = []
        sim_cumulative = []
        sim_max_drawdowns = []
        sim_sharpe_ratios = []

        for _ in range(n_sims):
            # Generate simulated returns
            sim_ret = self._generate_simulated_returns(dist_params, n_obs)

            # Calculate metrics
            cum_ret = np.cumprod(1 + sim_ret)
            max_dd = self._calculate_max_drawdown(cum_ret)
            sharpe = self._calculate_sharpe_ratio(sim_ret)

            sim_returns.append(sim_ret)
            sim_cumulative.append(cum_ret)
            sim_max_drawdowns.append(max_dd)
            sim_sharpe_ratios.append(sharpe)

        return {
            'simulated_returns': sim_returns,
            'simulated_cumulative': sim_cumulative,
            'max_drawdowns': sim_max_drawdowns,
            'sharpe_ratios': sim_sharpe_ratios,
            'n_simulations': n_sims
        }

    def _fit_returns_distribution(self, returns: np.ndarray) -> Dict[str, float]:
        """Fit statistical distribution to returns"""
        # Use t-distribution for fat tails
        params = stats.t.fit(returns)
        return {
            'df': params[0],  # degrees of freedom
            'loc': params[1],  # location
            'scale': params[2]  # scale
        }

    def _generate_simulated_returns(self, dist_params: Dict[str, float], n: int) -> np.ndarray:
        """Generate simulated returns from fitted distribution"""
        return stats.t.rvs(
            df=dist_params['df'],
            loc=dist_params['loc'],
            scale=dist_params['scale'],
            size=n
        )

    def _calculate_max_drawdown(self, cumulative_returns: np.ndarray) -> float:
        """Calculate maximum drawdown"""
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - peak) / peak
        return np.min(drawdown)

    def _calculate_sharpe_ratio(self, returns: np.ndarray) -> float:
        """Calculate Sharpe ratio for simulation"""
        if len(returns) <= 1:
            return 0.0

        mean_ret = float(np.mean(returns))
        std_ret = float(np.std(returns, ddof=1))

        if std_ret == 0:
            return 0.0

        return self._annualize_sharpe(mean_ret, std_ret)

    def _annualize_sharpe(self, mean_return: float, volatility: float) -> float:
        """Annualize Sharpe ratio"""
        ann_return = mean_return * self.config.ANNUALIZATION_FACTOR
        ann_vol = volatility * np.sqrt(self.config.ANNUALIZATION_FACTOR)
        return (ann_return - self.config.RISK_FREE_RATE) / ann_vol

    def _calculate_strategy_metrics(self, returns: np.ndarray) -> Dict[str, Any]:
        """Calculate comprehensive strategy metrics"""
        cumulative = np.cumprod(1 + returns)
        max_dd = self._calculate_max_drawdown(cumulative)

        return {
            'total_return': cumulative[-1] - 1,
            'annualized_return': (cumulative[-1]) ** (self.config.ANNUALIZATION_FACTOR / len(returns)) - 1,
            'volatility': np.std(returns, ddof=1) * np.sqrt(self.config.ANNUALIZATION_FACTOR),
            'sharpe_ratio': self._calculate_sharpe_ratio(returns),
            'max_drawdown': max_dd,
            'calmar_ratio': (cumulative[-1] - 1) / abs(max_dd) if max_dd != 0 else float('inf'),
            'sortino_ratio': self._calculate_sortino_ratio(returns),
            'win_rate': np.mean(returns > 0),
            'profit_factor': np.sum(returns[returns > 0]) / abs(np.sum(returns[returns < 0])) if np.any(returns < 0) else float('inf')
        }

    def _calculate_sortino_ratio(self, returns: np.ndarray) -> float:
        """Calculate Sortino ratio (downside deviation)"""
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0:
            return float('inf')

        downside_vol = np.std(downside_returns, ddof=1) * np.sqrt(self.config.ANNUALIZATION_FACTOR)
        ann_return = np.mean(returns) * self.config.ANNUALIZATION_FACTOR

        return (ann_return - self.config.RISK_FREE_RATE) / downside_vol if downside_vol > 0 else float('inf')

    def _analyze_outperformance(self, mc_results: Dict, benchmark_returns: Optional[np.ndarray]) -> Dict[str, Any]:
        """Analyze strategy outperformance vs benchmark"""
        if benchmark_returns is None:
            return {'error': 'No benchmark provided'}

        strategy_sharpes = mc_results['sharpe_ratios']
        benchmark_sharpe = self._calculate_sharpe_ratio(benchmark_returns)

        # Probability of outperforming benchmark
        prob_outperform = np.mean(np.array(strategy_sharpes) > benchmark_sharpe)

        # Outperformance magnitude
        outperformance = np.array(strategy_sharpes) - benchmark_sharpe
        expected_outperformance = np.mean(outperformance)
        outperformance_std = np.std(outperformance, ddof=1)

        return {
            'probability_outperform': prob_outperform,
            'expected_outperformance': expected_outperformance,
            'outperformance_std': outperformance_std,
            'benchmark_sharpe': benchmark_sharpe,
            'outperformance_5th_percentile': np.percentile(outperformance, 5),
            'outperformance_95th_percentile': np.percentile(outperformance, 95)
        }

    def _calculate_risk_metrics(self, mc_results: Dict) -> Dict[str, float]:
        """Calculate risk metrics from Monte Carlo results"""
        max_drawdowns = np.array(mc_results['max_drawdowns'])
        sharpe_ratios = np.array(mc_results['sharpe_ratios'])

        return {
            'expected_max_drawdown': float(np.mean(max_drawdowns)),
            'max_drawdown_var_95': float(np.percentile(max_drawdowns, 5)),  # 5th percentile = 95% VaR
            'max_drawdown_cvar_95': float(np.mean(max_drawdowns[max_drawdowns <= np.percentile(max_drawdowns, 5)])),
            'sharpe_ratio_var_95': float(np.percentile(sharpe_ratios, 5)),
            'sharpe_ratio_cvar_95': float(np.mean(sharpe_ratios[sharpe_ratios <= np.percentile(sharpe_ratios, 5)])),
            'probability_positive_sharpe': float(np.mean(sharpe_ratios > 0)),
            'probability_high_sharpe': float(np.mean(sharpe_ratios > 1.0))  # Sharpe > 1.0
        }

    def _calculate_validation_confidence(self, mc_results: Dict) -> float:
        """Calculate overall validation confidence score"""
        sharpe_ratios = np.array(mc_results['sharpe_ratios'])
        max_drawdowns = np.array(mc_results['max_drawdowns'])

        # Confidence components
        sharpe_confidence = np.mean(sharpe_ratios > 0.5)  # P(Sharpe > 0.5)
        drawdown_confidence = np.mean(max_drawdowns > -0.20)  # P(MaxDD > -20%)
        stability_confidence = 1 - np.std(sharpe_ratios) / max(np.mean(sharpe_ratios), 0.01)  # Lower variability = higher confidence

        # Weighted average
        confidence = (0.4 * sharpe_confidence +
                     0.4 * drawdown_confidence +
                     0.2 * stability_confidence)

        return float(min(confidence, 1.0))  # Cap at 100%

# ============================================================================
# STRATEGY VALIDATION ENGINE
# ============================================================================

class StrategyValidationEngine:
    """Complete strategy validation with probabilistic methods"""

    def __init__(self, config: Optional[ProbabilisticSharpeConfig] = None):
        self.config = config or ProbabilisticSharpeConfig()
        self.sharpe_analyzer = ProbabilisticSharpeAnalyzer(config)
        self.mc_validator = MonteCarloStrategyValidator(config)

    def validate_trading_strategy(self, strategy_returns: np.ndarray,
                                benchmark_returns: Optional[np.ndarray] = None,
                                strategy_name: str = "Strategy") -> Dict[str, Any]:
        """
        Complete statistical validation of a trading strategy

        Returns comprehensive validation report
        """
        logger.info(f"Validating strategy: {strategy_name}")

        # Probabilistic Sharpe analysis
        sharpe_analysis = self.sharpe_analyzer.calculate_probabilistic_sharpe(
            strategy_returns, benchmark_returns
        )

        if 'error' in sharpe_analysis:
            return {'error': sharpe_analysis['error']}

        # Monte Carlo validation
        mc_validation = self.mc_validator.validate_strategy(
            strategy_returns, benchmark_returns
        )

        if 'error' in mc_validation:
            return {'error': mc_validation['error']}

        # Overall assessment
        overall_score = self._calculate_overall_score(sharpe_analysis, mc_validation)
        recommendation = self._generate_recommendation(overall_score, sharpe_analysis, mc_validation)

        return {
            'strategy_name': strategy_name,
            'validation_timestamp': datetime.now().isoformat(),
            'sharpe_analysis': sharpe_analysis,
            'monte_carlo_validation': mc_validation,
            'overall_score': overall_score,
            'recommendation': recommendation,
            'confidence_level': self.config.CONFIDENCE_LEVEL,
            'n_observations': len(strategy_returns)
        }

    def _calculate_overall_score(self, sharpe_analysis: Dict, mc_validation: Dict) -> float:
        """Calculate overall validation score (0-1)"""
        # Component scores
        sharpe_score = min(sharpe_analysis.get('sharpe_skill', 0) / 2.0, 1.0)  # Cap at Sharpe skill of 2.0
        significance_score = 1.0 if sharpe_analysis.get('is_significant', False) else 0.0
        robustness_score = mc_validation.get('validation_confidence', 0.0)

        # Weighted average
        overall_score = (0.4 * sharpe_score +
                        0.3 * significance_score +
                        0.3 * robustness_score)

        return overall_score

    def _generate_recommendation(self, overall_score: float,
                               sharpe_analysis: Dict, mc_validation: Dict) -> str:
        """Generate investment recommendation"""
        if overall_score >= 0.8:
            return "STRONG BUY - Excellent statistical properties and robustness"
        elif overall_score >= 0.6:
            return "BUY - Good performance with acceptable risk"
        elif overall_score >= 0.4:
            return "HOLD - Moderate performance, monitor closely"
        elif overall_score >= 0.2:
            return "WEAK SELL - Poor statistical significance"
        else:
            return "STRONG SELL - High risk of underperformance"

# ============================================================================
# INTEGRATION WITH EXISTING SYSTEM
# ============================================================================

def validate_backtest_results(backtest_results: Dict, benchmark_returns: Optional[np.ndarray] = None) -> Dict[str, Any]:
    """Validate backtest results using probabilistic methods"""
    engine = StrategyValidationEngine()

    validated_results = {}

    for strategy_name, result in backtest_results.items():
        if 'returns' in result:
            strategy_returns = np.array(result['returns'])
            validation = engine.validate_trading_strategy(
                strategy_returns, benchmark_returns, strategy_name
            )
            validated_results[strategy_name] = {
                'original_result': result,
                'statistical_validation': validation
            }
        else:
            validated_results[strategy_name] = {
                'original_result': result,
                'error': 'No returns data available for validation'
            }

    return validated_results

# ============================================================================
# STANDALONE TESTING
# ============================================================================

def test_probabilistic_sharpe():
    """Test probabilistic Sharpe ratio calculations"""
    print("Testing Probabilistic Sharpe Ratio Engine...")

    # Generate sample strategy returns (with positive Sharpe)
    np.random.seed(42)
    n_days = 252  # One year
    daily_returns = np.random.normal(0.001, 0.02, n_days)  # 0.1% mean, 2% vol

    config = ProbabilisticSharpeConfig()
    analyzer = ProbabilisticSharpeAnalyzer(config)

    result = analyzer.calculate_probabilistic_sharpe(daily_returns)

    print("\nProbabilistic Sharpe Analysis:")
    print(f"  Sharpe Ratio: {result['sharpe_ratio']:.4f}")
    print(f"  Probabilistic Sharpe: {result['probabilistic_sharpe']:.4f}")
    print(f"  CI Lower: {result['sharpe_ci_lower']:.4f}")
    print(f"  CI Upper: {result['sharpe_ci_upper']:.4f}")
    print(f"  Deflated Sharpe: {result['deflated_sharpe']:.4f}")
    print(f"  Significant: {result['is_significant']}")

    # Test Monte Carlo validation
    validator = MonteCarloStrategyValidator(config)
    mc_result = validator.validate_strategy(daily_returns)

    print("\nMonte Carlo Validation:")
    print(f"  Expected Max DD: {mc_result['risk_metrics']['expected_max_drawdown']:.4f}")
    print(f"  Sharpe Ratio VaR 95%: {mc_result['risk_metrics']['sharpe_ratio_var_95']:.4f}")
    print(f"  P(Sharpe > 0): {mc_result['risk_metrics']['probability_positive_sharpe']:.1%}")
    print(f"  Validation Confidence: {mc_result['validation_confidence']:.1%}")

    print("Probabilistic Sharpe Ratio Engine test completed!")

if __name__ == "__main__":
    test_probabilistic_sharpe()