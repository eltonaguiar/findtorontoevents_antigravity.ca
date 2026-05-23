"""
Purged K-Fold Cross-Validation for Time Series

Standard K-fold leaks future information. Purged K-fold:
1. Respects temporal ordering
2. Purges observations near the train/test boundary
3. Adds embargo period to prevent leakage

This is essential for any ML model used in trading.
"""
import logging
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .metrics import PerformanceMetrics, StrategyMetrics

logger = logging.getLogger(__name__)


class PurgedKFoldCV:
    """
    Purged K-Fold Cross-Validation for time series.
    
    Unlike standard CV:
    - Preserves temporal order within folds
    - Purges N days around train/test boundary
    - Adds embargo period after each test set
    
    This prevents information leakage that would inflate results.
    """

    def __init__(
        self,
        n_folds: int = 5,
        purge_days: int = 5,
        embargo_days: int = 5,
    ):
        from .. import config
        self.n_folds = n_folds
        self.purge_days = purge_days
        self.embargo_days = embargo_days

    def split(self, dates: pd.DatetimeIndex) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Generate purged train/test indices.
        
        Returns list of (train_indices, test_indices) tuples.
        """
        n = len(dates)
        fold_size = n // self.n_folds
        indices = np.arange(n)
        splits = []

        for i in range(self.n_folds):
            test_start = i * fold_size
            test_end = min((i + 1) * fold_size, n)

            test_idx = indices[test_start:test_end]

            # Train = everything NOT in test window (± purge/embargo)
            purge_start = max(0, test_start - self.purge_days)
            embargo_end = min(n, test_end + self.embargo_days)

            train_mask = np.ones(n, dtype=bool)
            train_mask[purge_start:embargo_end] = False
            train_idx = indices[train_mask]

            if len(train_idx) > 0 and len(test_idx) > 0:
                splits.append((train_idx, test_idx))

        logger.info(f"Generated {len(splits)} purged CV folds (purge={self.purge_days}d, embargo={self.embargo_days}d)")
        return splits

    def validate(
        self,
        strategy_fn: Callable,
        features: pd.DataFrame,
        target: pd.Series,
        dates: pd.DatetimeIndex = None,
    ) -> Dict:
        """
        Run purged K-fold cross-validation.
        
        Args:
            strategy_fn: Callable(train_X, train_y, test_X) -> predictions
            features: Feature matrix
            target: Target variable (forward returns)
            dates: Date index for temporal ordering
            
        Returns:
            Dict with fold metrics and aggregate scores
        """
        if dates is None:
            dates = features.index if not isinstance(features.index, pd.MultiIndex) else \
                    features.index.get_level_values(0).unique()

        splits = self.split(dates)
        fold_metrics = []
        all_preds = []
        all_actuals = []

        for fold_id, (train_idx, test_idx) in enumerate(splits):
            try:
                train_dates = dates[train_idx]
                test_dates = dates[test_idx]

                # Filter features and target
                if isinstance(features.index, pd.MultiIndex):
                    train_X = features.loc[features.index.get_level_values(0).isin(train_dates)]
                    test_X = features.loc[features.index.get_level_values(0).isin(test_dates)]
                    train_y = target.loc[target.index.get_level_values(0).isin(train_dates)]
                    test_y = target.loc[target.index.get_level_values(0).isin(test_dates)]
                else:
                    train_X = features.iloc[train_idx]
                    test_X = features.iloc[test_idx]
                    train_y = target.iloc[train_idx]
                    test_y = target.iloc[test_idx]

                # Drop NaN
                valid_train = train_X.dropna(how="all").index.intersection(train_y.dropna().index)
                valid_test = test_X.dropna(how="all").index.intersection(test_y.dropna().index)

                if len(valid_train) < 50 or len(valid_test) < 10:
                    continue

                train_X = train_X.loc[valid_train].fillna(0)
                train_y = train_y.loc[valid_train]
                test_X = test_X.loc[valid_test].fillna(0)
                test_y = test_y.loc[valid_test]

                # Run strategy
                predictions = strategy_fn(train_X, train_y, test_X)

                if predictions is None:
                    continue

                # Compute fold metrics
                pred_series = pd.Series(predictions, index=test_y.index)
                correlation = pred_series.corr(test_y)

                # IC (Information Coefficient)
                rank_ic = pred_series.rank().corr(test_y.rank())

                fold_metrics.append({
                    "fold": fold_id,
                    "train_size": len(train_X),
                    "test_size": len(test_X),
                    "ic": correlation,
                    "rank_ic": rank_ic,
                    "test_start": str(test_dates[0].date()),
                    "test_end": str(test_dates[-1].date()),
                })

                all_preds.extend(predictions)
                all_actuals.extend(test_y.values)

            except Exception as e:
                logger.warning(f"Fold {fold_id} failed: {e}")
                continue

        if not fold_metrics:
            return {"error": "all_folds_failed", "folds": []}

        # Aggregate
        ics = [f["ic"] for f in fold_metrics]
        rank_ics = [f["rank_ic"] for f in fold_metrics]

        overall_corr = np.corrcoef(all_preds, all_actuals)[0, 1] if all_preds else 0

        return {
            "folds": fold_metrics,
            "avg_ic": np.mean(ics),
            "std_ic": np.std(ics),
            "avg_rank_ic": np.mean(rank_ics),
            "ic_ir": np.mean(ics) / np.std(ics) if np.std(ics) > 0 else 0,  # IC Information Ratio
            "overall_correlation": overall_corr,
            "n_folds": len(fold_metrics),
            "pct_positive_ic": sum(1 for ic in ics if ic > 0) / len(ics),
        }
