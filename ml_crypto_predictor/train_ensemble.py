"""
Regime-Aware LightGBM Ensemble Trainer
======================================
Trains separate LightGBM models for each regime:
- Model 0: CRASH regime (defensive, tight stops)
- Model 1: RANGE regime (mean reversion)
- Model 2: TREND regime (momentum following)

Features:
- Optuna hyperparameter optimization
- Probability calibration with isotonic regression
- Walk-forward validation
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import joblib
import json

from sklearn.model_selection import TimeSeriesSplit
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logging.warning("lightgbm not available")

try:
    import optuna
    from optuna.samplers import TPESampler
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    logging.warning("optuna not available, using default hyperparameters")

from alpha_engine.config import LAG_FEATURES, ROLLING_WINDOWS

logger = logging.getLogger(__name__)


@dataclass
class RegimeModelMetrics:
    """Metrics for a regime-specific model."""
    regime: str
    n_samples: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    avg_proba: float
    calibration_error: float


class RegimeAwareEnsemble:
    """
    Ensemble of regime-specific LightGBM models.
    """
    
    REGIME_NAMES = {0: 'CRASH', 1: 'RANGE', 2: 'TREND'}
    
    def __init__(
        self,
        n_estimators: int = 100,
        learning_rate: float = 0.05,
        max_depth: int = 6,
        feature_fraction: float = 0.8,
        bagging_fraction: float = 0.8,
        bagging_freq: int = 5,
        min_child_samples: int = 20,
        reg_alpha: float = 0.1,
        reg_lambda: float = 0.1,
        use_optuna: bool = True,
        n_optuna_trials: int = 50
    ):
        self.params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'boosting_type': 'gbdt',
            'n_estimators': n_estimators,
            'learning_rate': learning_rate,
            'max_depth': max_depth,
            'feature_fraction': feature_fraction,
            'bagging_fraction': bagging_fraction,
            'bagging_freq': bagging_freq,
            'min_child_samples': min_child_samples,
            'reg_alpha': reg_alpha,
            'reg_lambda': reg_lambda,
            'verbose': -1,
            'random_state': 42
        }
        
        self.use_optuna = use_optuna and OPTUNA_AVAILABLE
        self.n_optuna_trials = n_optuna_trials
        
        self.models: Dict[int, lgb.LGBMClassifier] = {}
        self.calibrators: Dict[int, CalibratedClassifierCV] = {}
        self.feature_names: List[str] = []
        self.metrics: Dict[int, RegimeModelMetrics] = {}
    
    def _compute_features(
        self,
        df: pd.DataFrame,
        target_horizon: int = 12  # 12 bars ahead (e.g., 1h for 5m bars)
    ) -> pd.DataFrame:
        """
        Compute feature set for modeling.
        """
        features = pd.DataFrame(index=df.index)
        
        close = df['close']
        volume = df.get('volume', pd.Series(1, index=df.index))
        
        # Returns
        for lag in LAG_FEATURES[:6]:  # Use first 6 lags
            features[f'return_lag_{lag}'] = close.pct_change(lag)
        
        # Rolling statistics
        for window in ROLLING_WINDOWS[:5]:
            features[f'volatility_{window}'] = close.pct_change().rolling(window).std()
            features[f'sma_ratio_{window}'] = close / close.rolling(window).mean()
            features[f'volume_sma_{window}'] = volume / volume.rolling(window).mean()
        
        # Price action features
        features['high_low_range'] = (df['high'] - df['low']) / close
        features['open_close'] = (df['close'] - df['open']) / close
        features['body_size'] = abs(df['close'] - df['open']) / (df['high'] - df['low'] + 1e-10)
        
        # Target: Future return direction
        future_return = close.shift(-target_horizon) / close - 1
        features['target'] = (future_return > 0).astype(int)
        
        # Time features
        features['hour'] = df.index.hour
        features['day_of_week'] = df.index.dayofweek
        
        self.feature_names = [c for c in features.columns if c != 'target']
        
        return features.dropna()
    
    def _optimize_hyperparams(
        self,
        X: np.ndarray,
        y: np.ndarray,
        regime: str
    ) -> Dict:
        """
        Use Optuna to find optimal hyperparameters.
        """
        if not OPTUNA_AVAILABLE:
            return self.params.copy()
        
        def objective(trial):
            params = {
                'objective': 'binary',
                'metric': 'binary_logloss',
                'boosting_type': 'gbdt',
                'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'max_depth': trial.suggest_int('max_depth', 3, 12),
                'feature_fraction': trial.suggest_float('feature_fraction', 0.6, 1.0),
                'bagging_fraction': trial.suggest_float('bagging_fraction', 0.6, 1.0),
                'bagging_freq': trial.suggest_int('bagging_freq', 1, 10),
                'min_child_samples': trial.suggest_int('min_child_samples', 10, 100),
                'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
                'verbose': -1,
                'random_state': 42
            }
            
            # Time series cross-validation
            tscv = TimeSeriesSplit(n_splits=3)
            scores = []
            
            for train_idx, val_idx in tscv.split(X):
                X_train, X_val = X[train_idx], X[val_idx]
                y_train, y_val = y[train_idx], y[val_idx]
                
                model = lgb.LGBMClassifier(**params)
                model.fit(X_train, y_train)
                
                pred = model.predict(X_val)
                scores.append(f1_score(y_val, pred, zero_division=0))
            
            return np.mean(scores)
        
        study = optuna.create_study(
            direction='maximize',
            sampler=TPESampler(seed=42)
        )
        study.optimize(objective, n_trials=self.n_optuna_trials, show_progress_bar=False)
        
        best_params = study.best_params
        best_params['objective'] = 'binary'
        best_params['metric'] = 'binary_logloss'
        best_params['boosting_type'] = 'gbdt'
        best_params['verbose'] = -1
        best_params['random_state'] = 42
        
        logger.info(f"Best params for {regime}: {best_params}")
        
        return best_params
    
    def train_regime_model(
        self,
        regime_id: int,
        df: pd.DataFrame,
        optimize: bool = True
    ) -> RegimeModelMetrics:
        """
        Train a model for a specific regime.
        """
        if not LIGHTGBM_AVAILABLE:
            raise ImportError("lightgbm is required")
        
        features = self._compute_features(df)
        
        if len(features) < 100:
            logger.warning(f"Insufficient data for regime {regime_id}: {len(features)} samples")
            return RegimeModelMetrics(
                regime=self.REGIME_NAMES.get(regime_id, f'REGIME_{regime_id}'),
                n_samples=len(features),
                accuracy=0, precision=0, recall=0, f1=0,
                avg_proba=0, calibration_error=0
            )
        
        X = features[self.feature_names].values
        y = features['target'].values
        
        # Split: 80% train, 20% validation
        split_idx = int(0.8 * len(X))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Optimize or use default params
        if optimize and self.use_optuna:
            params = self._optimize_hyperparams(X_train, y_train, self.REGIME_NAMES[regime_id])
        else:
            params = self.params.copy()
        
        # Train base model
        model = lgb.LGBMClassifier(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)]
        )
        
        # Calibrate probabilities
        calibrator = CalibratedClassifierCV(model, method='isotonic', cv='prefit')
        calibrator.fit(X_val, y_val)
        
        # Evaluate
        y_pred = calibrator.predict(X_val)
        y_proba = calibrator.predict_proba(X_val)[:, 1]
        
        # Compute calibration error
        prob_true = []
        prob_pred = []
        for i in range(10):
            mask = (y_proba >= i * 0.1) & (y_proba < (i + 1) * 0.1)
            if mask.sum() > 0:
                prob_true.append(y_val[mask].mean())
                prob_pred.append(y_proba[mask].mean())
        
        calibration_error = np.mean(np.abs(np.array(prob_true) - np.array(prob_pred)))
        
        metrics = RegimeModelMetrics(
            regime=self.REGIME_NAMES.get(regime_id, f'REGIME_{regime_id}'),
            n_samples=len(features),
            accuracy=accuracy_score(y_val, y_pred),
            precision=precision_score(y_val, y_pred, zero_division=0),
            recall=recall_score(y_val, y_pred, zero_division=0),
            f1=f1_score(y_val, y_pred, zero_division=0),
            avg_proba=y_proba.mean(),
            calibration_error=calibration_error
        )
        
        self.models[regime_id] = model
        self.calibrators[regime_id] = calibrator
        self.metrics[regime_id] = metrics
        
        logger.info(
            f"Trained {metrics.regime} model: "
            f"n={metrics.n_samples}, f1={metrics.f1:.3f}, "
            f"cal_err={metrics.calibration_error:.3f}"
        )
        
        return metrics
    
    def train(
        self,
        regime_data: Dict[int, pd.DataFrame],
        optimize: bool = True
    ) -> Dict[int, RegimeModelMetrics]:
        """
        Train models for all regimes.
        
        Args:
            regime_data: Dict mapping regime_id -> DataFrame for that regime
        """
        for regime_id, df in regime_data.items():
            if df is not None and not df.empty:
                self.train_regime_model(regime_id, df, optimize)
            else:
                logger.warning(f"No data for regime {regime_id}")
        
        return self.metrics
    
    def predict(
        self,
        features: pd.DataFrame,
        regime_id: int
    ) -> Tuple[int, float]:
        """
        Predict for a sample given regime.
        
        Returns:
            (prediction, probability)
        """
        if regime_id not in self.calibrators:
            # Default to neutral
            return 0, 0.5
        
        X = features[self.feature_names].values.reshape(1, -1)
        
        proba = self.calibrators[regime_id].predict_proba(X)[0]
        pred = 1 if proba[1] > 0.5 else 0
        
        return pred, proba[1]
    
    def predict_proba(
        self,
        features: pd.DataFrame,
        regime_id: int
    ) -> float:
        """Get probability of positive return."""
        _, proba = self.predict(features, regime_id)
        return proba
    
    def get_feature_importance(self, regime_id: int) -> pd.DataFrame:
        """Get feature importance for a regime model."""
        if regime_id not in self.models:
            return pd.DataFrame()
        
        importance = self.models[regime_id].feature_importances_
        
        return pd.DataFrame({
            'feature': self.feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)
    
    def save(self, path: Path):
        """Save ensemble to disk."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        joblib.dump({
            'models': self.models,
            'calibrators': self.calibrators,
            'feature_names': self.feature_names,
            'metrics': self.metrics,
            'params': self.params
        }, path / 'regime_ensemble.joblib')
        
        # Save metrics as JSON
        metrics_dict = {
            str(k): {
                'regime': v.regime,
                'n_samples': v.n_samples,
                'accuracy': v.accuracy,
                'precision': v.precision,
                'recall': v.recall,
                'f1': v.f1,
                'avg_proba': v.avg_proba,
                'calibration_error': v.calibration_error
            }
            for k, v in self.metrics.items()
        }
        
        with open(path / 'metrics.json', 'w') as f:
            json.dump(metrics_dict, f, indent=2)
        
        # Save feature importance
        for regime_id in self.models:
            fi = self.get_feature_importance(regime_id)
            fi.to_csv(path / f'feature_importance_{self.REGIME_NAMES[regime_id]}.csv', index=False)
        
        logger.info(f"Ensemble saved to {path}")
    
    def load(self, path: Path):
        """Load ensemble from disk."""
        path = Path(path)
        model_path = path / 'regime_ensemble.joblib'
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path}")
        
        data = joblib.load(model_path)
        
        self.models = data['models']
        self.calibrators = data['calibrators']
        self.feature_names = data['feature_names']
        self.metrics = data['metrics']
        self.params = data['params']
        
        logger.info(f"Ensemble loaded from {path}")


def load_regime_models(model_path: Path = Path("models/regime_ensemble")) -> Dict[int, 'RegimeAwareEnsemble']:
    """
    Load trained regime models.
    
    Returns dict mapping regime_id -> ensemble
    """
    ensemble = RegimeAwareEnsemble()
    ensemble.load(model_path)
    
    # Return dict for easy access
    return {regime_id: ensemble for regime_id in ensemble.models.keys()}


def train_regime_ensemble(
    price_data: pd.DataFrame,
    regime_labels: pd.Series,
    model_path: Path = Path("models/regime_ensemble"),
    optimize: bool = True
) -> RegimeAwareEnsemble:
    """
    Train regime-specific ensemble from labeled data.
    
    Args:
        price_data: OHLCV DataFrame
        regime_labels: Series of regime IDs (0, 1, 2) aligned with price_data
        model_path: Where to save models
        optimize: Whether to use Optuna for hyperparameter tuning
    """
    # Split data by regime
    regime_data = {}
    for regime_id in [0, 1, 2]:
        mask = regime_labels == regime_id
        if mask.sum() > 0:
            regime_data[regime_id] = price_data[mask]
    
    # Train ensemble
    ensemble = RegimeAwareEnsemble()
    ensemble.train(regime_data, optimize=optimize)
    ensemble.save(model_path)
    
    return ensemble
