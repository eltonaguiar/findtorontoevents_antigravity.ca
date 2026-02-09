"""
ML Ranker Strategy

Uses gradient boosting (LightGBM/XGBoost) to rank stocks by predicted forward returns.
The ML model acts as a "feature combiner" that learns non-linear interactions
between all factor families.
"""
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from .base import BaseStrategy, StrategyConfig, StrategyType, HoldingPeriod, Signal

logger = logging.getLogger(__name__)


class MLRankerStrategy(BaseStrategy):
    """
    Machine learning cross-sectional ranker.
    
    Uses LightGBM to predict forward returns from all features.
    Ranks stocks by predicted return and picks top-K.
    
    This is the "hybrid" approach: rules filter → ML ranker.
    """

    def __init__(self, config=None, model_type="lightgbm"):
        super().__init__(config)
        self.model_type = model_type
        self.model = None
        self.feature_importance = None
        self._is_trained = False

    def _default_config(self) -> StrategyConfig:
        return StrategyConfig(
            name="ml_ranker",
            description="LightGBM cross-sectional ranker: predict forward returns from features",
            strategy_type=StrategyType.LONG_ONLY,
            holding_period=HoldingPeriod.SWING,
            max_positions=20,
            top_k=20,
            rebalance_frequency="weekly",
            tags=["ml", "cross_sectional", "ranker"],
        )

    def train(
        self,
        features: pd.DataFrame,
        forward_returns: pd.Series,
        sample_weight: Optional[pd.Series] = None,
    ) -> Dict:
        """
        Train the ML model on historical features and forward returns.
        
        Args:
            features: Feature matrix (index = (date, ticker) or flat)
            forward_returns: Forward N-day returns (same index as features)
            sample_weight: Optional sample weights
            
        Returns:
            Dict with training metrics
        """
        # Drop NaN rows
        valid = features.dropna(how="all").index.intersection(forward_returns.dropna().index)
        X = features.loc[valid].fillna(0)
        y = forward_returns.loc[valid]

        if len(X) < 100:
            logger.warning(f"Insufficient data for training: {len(X)} rows")
            return {"error": "insufficient_data", "rows": len(X)}

        logger.info(f"Training ML ranker on {len(X)} samples, {X.shape[1]} features")

        # Store feature names
        self.feature_names = X.columns.tolist()

        if self.model_type == "lightgbm":
            metrics = self._train_lightgbm(X, y, sample_weight)
        elif self.model_type == "xgboost":
            metrics = self._train_xgboost(X, y, sample_weight)
        else:
            metrics = self._train_sklearn(X, y, sample_weight)

        self._is_trained = True
        return metrics

    def _train_lightgbm(self, X, y, sample_weight=None) -> Dict:
        """Train LightGBM model."""
        try:
            import lightgbm as lgb

            params = {
                "objective": "regression",
                "metric": "rmse",
                "boosting_type": "gbdt",
                "num_leaves": 31,
                "learning_rate": 0.05,
                "feature_fraction": 0.7,
                "bagging_fraction": 0.7,
                "bagging_freq": 5,
                "verbose": -1,
                "n_jobs": -1,
                "min_child_samples": 20,
                "reg_alpha": 0.1,
                "reg_lambda": 0.1,
            }

            dtrain = lgb.Dataset(X, label=y, weight=sample_weight)
            self.model = lgb.train(params, dtrain, num_boost_round=200)

            # Feature importance
            importance = self.model.feature_importance(importance_type="gain")
            self.feature_importance = pd.Series(
                importance, index=self.feature_names, name="importance"
            ).sort_values(ascending=False)

            # In-sample metrics
            pred = self.model.predict(X)
            corr = np.corrcoef(pred, y)[0, 1]

            return {"model": "lightgbm", "corr": corr, "n_features": X.shape[1], "n_samples": len(X)}

        except ImportError:
            logger.warning("LightGBM not installed, falling back to sklearn")
            return self._train_sklearn(X, y, sample_weight)

    def _train_xgboost(self, X, y, sample_weight=None) -> Dict:
        """Train XGBoost model."""
        try:
            import xgboost as xgb

            params = {
                "objective": "reg:squarederror",
                "max_depth": 6,
                "learning_rate": 0.05,
                "n_estimators": 200,
                "subsample": 0.7,
                "colsample_bytree": 0.7,
                "reg_alpha": 0.1,
                "reg_lambda": 0.1,
                "verbosity": 0,
            }

            self.model = xgb.XGBRegressor(**params)
            self.model.fit(X, y, sample_weight=sample_weight)

            importance = self.model.feature_importances_
            self.feature_importance = pd.Series(
                importance, index=self.feature_names, name="importance"
            ).sort_values(ascending=False)

            pred = self.model.predict(X)
            corr = np.corrcoef(pred, y)[0, 1]

            return {"model": "xgboost", "corr": corr, "n_features": X.shape[1], "n_samples": len(X)}

        except ImportError:
            logger.warning("XGBoost not installed, falling back to sklearn")
            return self._train_sklearn(X, y, sample_weight)

    def _train_sklearn(self, X, y, sample_weight=None) -> Dict:
        """Fallback: sklearn GradientBoostingRegressor."""
        from sklearn.ensemble import GradientBoostingRegressor

        self.model = GradientBoostingRegressor(
            n_estimators=200, max_depth=5, learning_rate=0.05,
            subsample=0.7, max_features=0.7,
        )
        self.model.fit(X, y, sample_weight=sample_weight)

        importance = self.model.feature_importances_
        self.feature_importance = pd.Series(
            importance, index=self.feature_names, name="importance"
        ).sort_values(ascending=False)

        pred = self.model.predict(X)
        corr = np.corrcoef(pred, y)[0, 1]

        return {"model": "sklearn_gbr", "corr": corr, "n_features": X.shape[1], "n_samples": len(X)}

    def predict(self, features: pd.DataFrame) -> pd.Series:
        """Predict forward returns from features."""
        if not self._is_trained or self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        # Align features to training columns
        X = features.reindex(columns=self.feature_names, fill_value=0).fillna(0)

        if self.model_type == "lightgbm":
            pred = self.model.predict(X)
        else:
            pred = self.model.predict(X)

        return pd.Series(pred, index=features.index, name="predicted_return")

    def generate_signals(self, features: pd.DataFrame, date: pd.Timestamp, universe: List[str]) -> List[Signal]:
        if not self._is_trained:
            return []

        signals = []
        try:
            # Get features for this date
            if isinstance(features.index, pd.MultiIndex):
                if date not in features.index.get_level_values(0):
                    return []
                date_features = features.loc[date]
            else:
                if date not in features.index:
                    return []
                date_features = features.loc[[date]]

            # Filter to universe
            if isinstance(date_features.index, pd.MultiIndex):
                valid_tickers = [t for t in universe if t in date_features.index.get_level_values(-1)]
            else:
                valid_tickers = [t for t in universe if t in date_features.index]

            if not valid_tickers:
                return []

            # Predict
            X = date_features.reindex(valid_tickers).reindex(columns=self.feature_names, fill_value=0).fillna(0)
            predictions = self.predict(X)

            # Rank and pick top-K
            ranked = predictions.sort_values(ascending=False)
            top_k = ranked.head(self.config.top_k)

            for ticker, pred_return in top_k.items():
                score = max(0, min(1, (pred_return + 0.1) / 0.2))  # Normalize around 0

                # Get top contributing features for explainability
                if self.feature_importance is not None:
                    top_features = self.feature_importance.head(5).index.tolist()
                    drivers = {}
                    for f in top_features:
                        if f in X.columns and ticker in X.index:
                            drivers[f] = float(X.loc[ticker, f])
                else:
                    drivers = {"predicted_return": float(pred_return)}

                signals.append(Signal(
                    ticker=ticker, date=date, score=score,
                    direction=1 if pred_return > 0 else -1,
                    confidence=min(abs(pred_return) * 10, 0.9),
                    holding_period=self.config.holding_period.value,
                    drivers=drivers,
                    category="ml_ranked",
                ))

        except Exception as e:
            logger.warning(f"ML ranker signal generation failed: {e}")

        return sorted(signals, key=lambda s: s.score, reverse=True)

    def get_feature_importance(self, top_n: int = 20) -> pd.Series:
        """Get top feature importances for explainability."""
        if self.feature_importance is None:
            return pd.Series(dtype=float)
        return self.feature_importance.head(top_n)

    def get_shap_values(self, X: pd.DataFrame) -> Optional[np.ndarray]:
        """Get SHAP values for model explainability."""
        try:
            import shap
            if self.model_type == "lightgbm":
                explainer = shap.TreeExplainer(self.model)
            else:
                explainer = shap.TreeExplainer(self.model)
            return explainer.shap_values(X)
        except ImportError:
            logger.warning("SHAP not installed")
            return None
