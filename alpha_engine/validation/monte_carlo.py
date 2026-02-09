"""
Monte Carlo Simulation

Bootstrap strategy returns to assess:
- Confidence intervals on Sharpe/return
- Probability of ruin
- Expected drawdown distribution
- Statistical significance of results
"""
import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MonteCarloSimulator:
    """
    Monte Carlo simulation for strategy robustness testing.
    
    Methods:
    - Bootstrap (resample returns with replacement)
    - Block bootstrap (preserve autocorrelation)
    - Randomized entry dates
    - White's reality check (multiple hypothesis testing)
    """

    def __init__(self, n_simulations: int = 1000, random_seed: int = 42):
        self.n_simulations = n_simulations
        self.rng = np.random.RandomState(random_seed)

    def bootstrap_returns(
        self,
        returns: pd.Series,
        n_sims: int = None,
    ) -> Dict:
        """
        Bootstrap strategy returns to get confidence intervals.
        
        Resamples daily returns with replacement to generate
        simulated equity curves.
        """
        if n_sims is None:
            n_sims = self.n_simulations

        returns = returns.dropna()
        n = len(returns)

        if n < 30:
            return {"error": "insufficient_data", "n_returns": n}

        # Generate bootstrap samples
        sim_total_returns = []
        sim_sharpes = []
        sim_max_drawdowns = []
        sim_annual_returns = []

        for _ in range(n_sims):
            # Resample with replacement
            sample_idx = self.rng.randint(0, n, size=n)
            sample = returns.values[sample_idx]

            # Total return
            total_ret = np.prod(1 + sample) - 1
            sim_total_returns.append(total_ret)

            # Sharpe
            if sample.std() > 0:
                sim_sharpes.append(sample.mean() / sample.std() * np.sqrt(252))
            else:
                sim_sharpes.append(0)

            # Max drawdown
            equity = np.cumprod(1 + sample)
            peak = np.maximum.accumulate(equity)
            dd = (equity - peak) / peak
            sim_max_drawdowns.append(abs(dd.min()))

            # Annual return
            n_years = n / 252
            sim_annual_returns.append((1 + total_ret) ** (1 / max(n_years, 0.01)) - 1)

        # Compute statistics
        return {
            "sharpe": {
                "mean": np.mean(sim_sharpes),
                "median": np.median(sim_sharpes),
                "std": np.std(sim_sharpes),
                "ci_5": np.percentile(sim_sharpes, 5),
                "ci_95": np.percentile(sim_sharpes, 95),
                "pct_positive": np.mean(np.array(sim_sharpes) > 0),
            },
            "total_return": {
                "mean": np.mean(sim_total_returns),
                "median": np.median(sim_total_returns),
                "ci_5": np.percentile(sim_total_returns, 5),
                "ci_95": np.percentile(sim_total_returns, 95),
            },
            "max_drawdown": {
                "mean": np.mean(sim_max_drawdowns),
                "median": np.median(sim_max_drawdowns),
                "ci_5": np.percentile(sim_max_drawdowns, 5),
                "ci_95": np.percentile(sim_max_drawdowns, 95),
            },
            "annual_return": {
                "mean": np.mean(sim_annual_returns),
                "ci_5": np.percentile(sim_annual_returns, 5),
                "ci_95": np.percentile(sim_annual_returns, 95),
            },
            "probability_of_loss": np.mean(np.array(sim_total_returns) < 0),
            "n_simulations": n_sims,
            "n_returns": n,
        }

    def block_bootstrap(
        self,
        returns: pd.Series,
        block_size: int = 21,
        n_sims: int = None,
    ) -> Dict:
        """
        Block bootstrap: preserves autocorrelation structure.
        
        Resamples blocks of consecutive returns instead of individual days.
        Better for momentum/trend-following strategies.
        """
        if n_sims is None:
            n_sims = self.n_simulations

        returns = returns.dropna().values
        n = len(returns)
        n_blocks = n // block_size

        if n_blocks < 3:
            return self.bootstrap_returns(pd.Series(returns), n_sims)

        sim_sharpes = []
        sim_total_returns = []

        for _ in range(n_sims):
            # Sample random blocks
            block_starts = self.rng.randint(0, n - block_size, size=n_blocks)
            sample = np.concatenate([returns[s:s + block_size] for s in block_starts])

            total_ret = np.prod(1 + sample) - 1
            sim_total_returns.append(total_ret)

            if sample.std() > 0:
                sim_sharpes.append(sample.mean() / sample.std() * np.sqrt(252))

        return {
            "sharpe": {
                "mean": np.mean(sim_sharpes),
                "ci_5": np.percentile(sim_sharpes, 5),
                "ci_95": np.percentile(sim_sharpes, 95),
            },
            "total_return": {
                "mean": np.mean(sim_total_returns),
                "ci_5": np.percentile(sim_total_returns, 5),
                "ci_95": np.percentile(sim_total_returns, 95),
            },
            "block_size": block_size,
            "n_simulations": n_sims,
        }

    def whites_reality_check(
        self,
        strategy_returns: pd.Series,
        benchmark_returns: pd.Series,
        n_strategies_tested: int = 10,
        n_sims: int = None,
    ) -> Dict:
        """
        White's Reality Check / Multiple Hypothesis Testing.
        
        Tests whether the best strategy's performance is significantly
        better than what you'd expect from random chance given the
        number of strategies tested.
        
        p-value < 0.05 → likely real alpha, not data snooping.
        """
        if n_sims is None:
            n_sims = self.n_simulations

        strategy_returns = strategy_returns.dropna()
        benchmark_returns = benchmark_returns.reindex(strategy_returns.index).fillna(0)
        excess = strategy_returns - benchmark_returns

        observed_stat = excess.mean()  # Average excess return
        n = len(excess)

        # Bootstrap the distribution of the test statistic
        sim_stats = []
        for _ in range(n_sims):
            # Randomly flip the sign of excess returns
            signs = self.rng.choice([-1, 1], size=n)
            sim_excess = excess.values * signs
            sim_stats.append(sim_excess.mean())

        sim_stats = np.array(sim_stats)

        # Adjust for multiple testing
        # The p-value is the probability of seeing this good a result by chance
        # across N strategies
        p_value_single = np.mean(sim_stats >= observed_stat)
        p_value_adjusted = 1 - (1 - p_value_single) ** n_strategies_tested

        return {
            "observed_excess_return": observed_stat,
            "p_value_single": p_value_single,
            "p_value_adjusted": min(p_value_adjusted, 1.0),
            "n_strategies_tested": n_strategies_tested,
            "is_significant_5pct": p_value_adjusted < 0.05,
            "is_significant_10pct": p_value_adjusted < 0.10,
            "bootstrap_mean": np.mean(sim_stats),
            "bootstrap_std": np.std(sim_stats),
        }

    def probability_of_ruin(
        self,
        returns: pd.Series,
        ruin_threshold: float = -0.30,
        time_horizon_days: int = 252,
    ) -> float:
        """
        Estimate probability of hitting a drawdown threshold.
        
        What's the chance of a 30% drawdown within 1 year?
        """
        returns = returns.dropna().values
        n = len(returns)
        ruin_count = 0

        for _ in range(self.n_simulations):
            sample_idx = self.rng.randint(0, n, size=min(time_horizon_days, n))
            sample = returns[sample_idx]
            equity = np.cumprod(1 + sample)
            peak = np.maximum.accumulate(equity)
            dd = (equity - peak) / peak

            if dd.min() <= ruin_threshold:
                ruin_count += 1

        return ruin_count / self.n_simulations
