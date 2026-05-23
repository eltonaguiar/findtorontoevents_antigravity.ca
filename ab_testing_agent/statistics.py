import numpy as np
import scipy.stats as stats
import pandas as pd
from statsmodels.stats.power import TTestIndPower
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class StatisticalAnalyzer:
    """Handles statistical calculations for A/B testing"""

    def __init__(self, significance_level: float = 0.05, power: float = 0.80):
        self.significance_level = significance_level
        self.power = power
        self.power_analysis = TTestIndPower()

    def calculate_sample_size(self, effect_size: float, std_dev: float = None) -> int:
        """
        Calculate required sample size for statistical power

        Args:
            effect_size: Minimum detectable effect size
            std_dev: Standard deviation (optional, will estimate if not provided)

        Returns:
            Required sample size per variant
        """
        if std_dev is None:
            # Conservative estimate - will be updated with actual data
            std_dev = 1.0

        # Convert to Cohen's d
        cohen_d = effect_size / std_dev

        sample_size = self.power_analysis.solve_power(
            effect_size=cohen_d,
            power=self.power,
            alpha=self.significance_level,
            ratio=1.0
        )

        return int(np.ceil(sample_size))

    def perform_t_test(self, group_a: List[float], group_b: List[float]) -> Dict:
        """
        Perform two-sample t-test

        Returns:
            Dict with t-statistic, p-value, confidence interval, effect size
        """
        t_stat, p_value = stats.ttest_ind(group_a, group_b, equal_var=False)

        # Calculate confidence interval
        mean_a, mean_b = np.mean(group_a), np.mean(group_b)
        std_a, std_b = np.std(group_a, ddof=1), np.std(group_b, ddof=1)
        n_a, n_b = len(group_a), len(group_b)

        # Pooled standard error
        se = np.sqrt(std_a**2 / n_a + std_b**2 / n_b)
        df = n_a + n_b - 2
        t_critical = stats.t.ppf(1 - self.significance_level/2, df)

        ci_lower = (mean_a - mean_b) - t_critical * se
        ci_upper = (mean_a - mean_b) + t_critical * se

        # Cohen's d effect size
        pooled_std = np.sqrt(((n_a-1)*std_a**2 + (n_b-1)*std_b**2) / (n_a + n_b - 2))
        effect_size = (mean_a - mean_b) / pooled_std

        return {
            't_statistic': t_stat,
            'p_value': p_value,
            'confidence_interval': (ci_lower, ci_upper),
            'effect_size': effect_size,
            'mean_difference': mean_a - mean_b,
            'significant': p_value < self.significance_level
        }

    def bayesian_analysis(self, group_a: List[float], group_b: List[float],
                         prior_alpha: float = 1.0, prior_beta: float = 1.0) -> Dict:
        """
        Perform Bayesian A/B testing with Beta-Binomial model

        Args:
            group_a, group_b: Lists of binary outcomes (0/1) or rates
            prior_alpha, prior_beta: Beta distribution priors

        Returns:
            Dict with posterior parameters and probability of A > B
        """
        # For simplicity, assume binary outcomes or convert to rates
        if all(isinstance(x, (int, float)) and x in [0, 1] for x in group_a + group_b):
            # Binary data
            successes_a = sum(group_a)
            trials_a = len(group_a)
            successes_b = sum(group_b)
            trials_b = len(group_b)
        else:
            # Continuous data - convert to binary based on median
            median = np.median(group_a + group_b)
            successes_a = sum(1 for x in group_a if x > median)
            trials_a = len(group_a)
            successes_b = sum(1 for x in group_b if x > median)
            trials_b = len(group_b)

        # Posterior parameters
        post_alpha_a = prior_alpha + successes_a
        post_beta_a = prior_beta + trials_a - successes_a
        post_alpha_b = prior_alpha + successes_b
        post_beta_b = prior_beta + trials_b - successes_b

        # Monte Carlo simulation for probability A > B
        n_simulations = 10000
        samples_a = np.random.beta(post_alpha_a, post_beta_a, n_simulations)
        samples_b = np.random.beta(post_alpha_b, post_beta_b, n_simulations)
        prob_a_better = np.mean(samples_a > samples_b)

        # Credible intervals
        ci_a = np.percentile(samples_a, [2.5, 97.5])
        ci_b = np.percentile(samples_b, [2.5, 97.5])

        return {
            'posterior_a': {'alpha': post_alpha_a, 'beta': post_beta_a},
            'posterior_b': {'alpha': post_alpha_b, 'beta': post_beta_b},
            'prob_a_better': prob_a_better,
            'credible_interval_a': ci_a,
            'credible_interval_b': ci_b,
            'expected_loss_a': np.mean(np.maximum(samples_b - samples_a, 0)),
            'expected_loss_b': np.mean(np.maximum(samples_a - samples_b, 0))
        }

    def check_sample_size_adequacy(self, current_n: int, required_n: int) -> Dict:
        """
        Check if current sample size is adequate
        """
        return {
            'current_sample_size': current_n,
            'required_sample_size': required_n,
            'is_adequate': current_n >= required_n,
            'completion_percentage': min(current_n / required_n * 100, 100)
        }

    def sequential_testing_bounds(self, alpha: float = 0.05, beta: float = 0.20) -> Tuple[float, float]:
        """
        Calculate sequential testing boundaries (Pocock boundaries)
        """
        # Simplified Pocock boundaries
        z_alpha = stats.norm.ppf(1 - alpha/2)
        z_beta = stats.norm.ppf(1 - beta)

        upper_bound = z_alpha
        lower_bound = -z_alpha

        return lower_bound, upper_bound