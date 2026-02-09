"""
Walk-Forward Validation

The gold standard for time-series strategy validation.
Train on window, test on next period, roll forward.
No lookahead bias by construction.
"""
import logging
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .metrics import PerformanceMetrics, StrategyMetrics

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardFold:
    """A single walk-forward fold."""
    fold_id: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    train_metrics: StrategyMetrics
    test_metrics: StrategyMetrics
    n_trades: int


@dataclass
class WalkForwardResult:
    """Aggregate walk-forward results."""
    folds: List[WalkForwardFold]
    aggregate_metrics: StrategyMetrics
    oos_sharpe: float           # Out-of-sample Sharpe
    oos_return: float
    is_sharpe: float            # In-sample Sharpe
    sharpe_decay: float         # How much Sharpe decays OOS
    consistency: float          # % of folds with positive OOS return
    avg_oos_sharpe: float
    total_oos_trades: int


class WalkForwardValidator:
    """
    Walk-forward optimization and validation.
    
    Splits data into rolling train/test windows.
    Trains strategy on each window, tests on next period.
    Aggregates results across all folds.
    
    This is the "truth machine" — if it works here, it's real.
    """

    def __init__(
        self,
        train_days: int = 756,    # ~3 years
        test_days: int = 126,     # ~6 months
        step_days: int = 63,      # ~3 months roll
        min_trades: int = 10,
    ):
        from .. import config
        self.train_days = train_days
        self.test_days = test_days
        self.step_days = step_days
        self.min_trades = min_trades

    def generate_folds(self, dates: pd.DatetimeIndex) -> List[Tuple[pd.DatetimeIndex, pd.DatetimeIndex]]:
        """Generate train/test fold date ranges."""
        folds = []
        total_needed = self.train_days + self.test_days
        n = len(dates)

        if n < total_needed:
            logger.warning(f"Insufficient data: {n} days, need {total_needed}")
            return folds

        start = 0
        while start + total_needed <= n:
            train_idx = dates[start:start + self.train_days]
            test_idx = dates[start + self.train_days:start + self.train_days + self.test_days]

            if len(test_idx) > 0:
                folds.append((train_idx, test_idx))

            start += self.step_days

        logger.info(f"Generated {len(folds)} walk-forward folds")
        return folds

    def validate(
        self,
        strategy_fn: Callable,
        features: pd.DataFrame,
        prices: pd.DataFrame,
        benchmark: Optional[pd.Series] = None,
    ) -> WalkForwardResult:
        """
        Run walk-forward validation.
        
        Args:
            strategy_fn: Callable that takes (train_features, test_features, train_prices, test_prices)
                        and returns test_returns Series
            features: Full feature matrix
            prices: Full price data
            benchmark: Benchmark returns
            
        Returns:
            WalkForwardResult with fold-by-fold and aggregate metrics
        """
        dates = prices.index
        folds_dates = self.generate_folds(dates)

        if not folds_dates:
            return WalkForwardResult(
                folds=[], aggregate_metrics=StrategyMetrics(),
                oos_sharpe=0, oos_return=0, is_sharpe=0,
                sharpe_decay=0, consistency=0, avg_oos_sharpe=0, total_oos_trades=0,
            )

        fold_results = []
        all_oos_returns = []
        is_sharpes = []
        oos_sharpes = []

        for i, (train_dates, test_dates) in enumerate(folds_dates):
            try:
                # Split data
                train_features = features.loc[features.index.isin(train_dates) | 
                                              (isinstance(features.index, pd.MultiIndex) and 
                                               features.index.get_level_values(0).isin(train_dates))]
                test_features = features.loc[features.index.isin(test_dates) |
                                             (isinstance(features.index, pd.MultiIndex) and 
                                              features.index.get_level_values(0).isin(test_dates))]
                train_prices = prices.loc[train_dates]
                test_prices = prices.loc[test_dates]

                # Run strategy
                test_returns = strategy_fn(train_features, test_features, train_prices, test_prices)

                if test_returns is None or len(test_returns) < 5:
                    continue

                # Compute metrics
                bench_test = benchmark.loc[test_dates] if benchmark is not None else None
                test_metrics = PerformanceMetrics.compute_all(test_returns, bench_test)

                # In-sample metrics (quick estimate)
                train_returns = prices.loc[train_dates].pct_change().mean(axis=1).dropna()
                train_metrics = PerformanceMetrics.compute_all(train_returns)

                fold = WalkForwardFold(
                    fold_id=i,
                    train_start=train_dates[0],
                    train_end=train_dates[-1],
                    test_start=test_dates[0],
                    test_end=test_dates[-1],
                    train_metrics=train_metrics,
                    test_metrics=test_metrics,
                    n_trades=0,
                )
                fold_results.append(fold)
                all_oos_returns.append(test_returns)
                is_sharpes.append(train_metrics.sharpe_ratio)
                oos_sharpes.append(test_metrics.sharpe_ratio)

            except Exception as e:
                logger.warning(f"Fold {i} failed: {e}")
                continue

        if not fold_results:
            return WalkForwardResult(
                folds=[], aggregate_metrics=StrategyMetrics(),
                oos_sharpe=0, oos_return=0, is_sharpe=0,
                sharpe_decay=0, consistency=0, avg_oos_sharpe=0, total_oos_trades=0,
            )

        # Aggregate OOS returns
        combined_oos = pd.concat(all_oos_returns)
        aggregate = PerformanceMetrics.compute_all(combined_oos, benchmark)

        avg_is = np.mean(is_sharpes) if is_sharpes else 0
        avg_oos = np.mean(oos_sharpes) if oos_sharpes else 0
        decay = 1 - (avg_oos / avg_is) if avg_is != 0 else 1

        consistency = sum(1 for s in oos_sharpes if s > 0) / len(oos_sharpes) if oos_sharpes else 0

        return WalkForwardResult(
            folds=fold_results,
            aggregate_metrics=aggregate,
            oos_sharpe=aggregate.sharpe_ratio,
            oos_return=aggregate.total_return,
            is_sharpe=avg_is,
            sharpe_decay=decay,
            consistency=consistency,
            avg_oos_sharpe=avg_oos,
            total_oos_trades=sum(f.n_trades for f in fold_results),
        )
