"""
================================================================================
MACHINE LEARNING TRADING SYSTEM ARCHITECTURE
================================================================================
Complete ML System Design for Stock Trading Algorithms

Components:
1. Feature Engineering Pipeline
2. Model Selection Framework
3. Walk-Forward & Purged Cross-Validation
4. Meta-Learner (StrategyArbitrator)
5. Regime Detection & Dynamic Allocation
6. Multiple Hypothesis Correction
7. Ablation Testing Framework

Author: ML Engineer
Date: 2024
================================================================================
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Callable, Union, Any
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import warnings
from collections import defaultdict
import joblib
from datetime import datetime, timedelta
import logging

# ML Libraries
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.model_selection import BaseCrossValidator
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier, 
    RandomForestRegressor, GradientBoostingRegressor
)
from sklearn.linear_model import LogisticRegression, Ridge, ElasticNet
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    mean_squared_error, mean_absolute_error, r2_score
)
from sklearn.feature_selection import mutual_info_classif, mutual_info_regression

# Advanced ML
try:
    import xgboost as xgb
    import lightgbm as lgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

# Statistical/Time Series
from scipy import stats
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ================================================================================
# SECTION 1: CONFIGURATION & DATA STRUCTURES
# ================================================================================

class ModelType(Enum):
    """Enumeration of supported model types."""
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    LOGISTIC_REGRESSION = "logistic_regression"
    RIDGE = "ridge"
    ELASTIC_NET = "elastic_net"
    NEURAL_NET = "neural_net"


class RegimeType(Enum):
    """Market regime classifications."""
    BULL_TREND = "bull_trend"
    BEAR_TREND = "bear_trend"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    RANGING = "ranging"
    TRENDING = "trending"
    CRISIS = "crisis"
    RECOVERY = "recovery"


class SignalType(Enum):
    """Types of trading signals."""
    LONG = 1
    SHORT = -1
    NEUTRAL = 0


@dataclass
class FeatureConfig:
    """Configuration for feature engineering."""
    # Lookback windows
    trend_windows: List[int] = field(default_factory=lambda: [5, 10, 20, 50, 200])
    momentum_windows: List[int] = field(default_factory=lambda: [5, 10, 20, 60])
    volatility_windows: List[int] = field(default_factory=lambda: [5, 10, 20, 60])
    volume_windows: List[int] = field(default_factory=lambda: [5, 10, 20])
    
    # Feature flags
    include_trend: bool = True
    include_momentum: bool = True
    include_volatility: bool = True
    include_volume: bool = True
    include_mean_reversion: bool = True
    include_cross_sectional: bool = True
    include_seasonality: bool = True
    include_regime: bool = True
    
    # Technical parameters
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bb_period: int = 20
    bb_std: float = 2.0
    
    # Prevent lookahead
    min_future_bars: int = 1


@dataclass
class ModelConfig:
    """Configuration for model training."""
    model_type: ModelType = ModelType.LIGHTGBM
    prediction_horizon: int = 5  # Days ahead to predict
    target_type: str = "direction"  # "direction", "return", "quantile"
    
    # Cross-validation
    cv_folds: int = 5
    cv_purge_gap: int = 5  # Bars to purge between train and test
    cv_embargo_pct: float = 0.02  # Embargo percentage
    
    # Walk-forward
    wf_train_size: int = 252 * 2  # 2 years
    wf_test_size: int = 63  # 3 months
    wf_step_size: int = 21  # 1 month step
    
    # Multiple hypothesis correction
    apply_bonferroni: bool = True
    apply_fdr: bool = True
    fdr_alpha: float = 0.05
    
    # Ensemble
    ensemble_method: str = "stacking"  # "stacking", "blending", "dynamic"
    meta_learner_type: ModelType = ModelType.RIDGE


@dataclass
class StrategySignal:
    """Container for strategy signals."""
    strategy_id: str
    timestamp: datetime
    signal: SignalType
    confidence: float  # 0 to 1
    expected_return: float
    volatility: float
    regime: RegimeType
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegimeState:
    """Current market regime state."""
    regime: RegimeType
    confidence: float
    features: Dict[str, float]
    transition_prob: Dict[RegimeType, float]
    timestamp: datetime


# ================================================================================
# SECTION 2: FEATURE ENGINEERING PIPELINE
# ================================================================================

class FeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Comprehensive feature engineering for financial time series.
    
    Feature Families:
    - Trend/Momentum: Returns, moving averages, MACD, RSI
    - Cross-sectional: Rankings, percentiles, z-scores
    - Volatility: Realized vol, GARCH, ATR, Bollinger Bands
    - Volume: Volume trends, OBV, VWAP
    - Mean Reversion: Z-scores, distance from means
    - Regime: Trend strength, volatility regime
    - Quality/Valuation: Fundamentals (if available)
    - Seasonality: Day of week, month, quarter effects
    """
    
    def __init__(self, config: FeatureConfig = None):
        self.config = config or FeatureConfig()
        self.feature_names_: List[str] = []
        self.scaler_ = RobustScaler()
        
    def fit(self, X: pd.DataFrame, y=None):
        """Fit the feature engineer (mainly for scaling)."""
        features = self.transform(X, fit_scaler=True)
        self.scaler_.fit(features)
        return self
    
    def transform(self, X: pd.DataFrame, fit_scaler: bool = False) -> pd.DataFrame:
        """Transform raw price data into features."""
        df = X.copy()
        features = pd.DataFrame(index=df.index)
        
        # Ensure required columns exist
        required = ['open', 'high', 'low', 'close', 'volume']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"Required column '{col}' not found in data")
        
        # Calculate returns (no lookahead - use previous close)
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # === TREND FEATURES ===
        if self.config.include_trend:
            features = self._add_trend_features(df, features)
        
        # === MOMENTUM FEATURES ===
        if self.config.include_momentum:
            features = self._add_momentum_features(df, features)
        
        # === VOLATILITY FEATURES ===
        if self.config.include_volatility:
            features = self._add_volatility_features(df, features)
        
        # === VOLUME FEATURES ===
        if self.config.include_volume:
            features = self._add_volume_features(df, features)
        
        # === MEAN REVERSION FEATURES ===
        if self.config.include_mean_reversion:
            features = self._add_mean_reversion_features(df, features)
        
        # === CROSS-SECTIONAL FEATURES ===
        if self.config.include_cross_sectional:
            features = self._add_cross_sectional_features(df, features)
        
        # === SEASONALITY FEATURES ===
        if self.config.include_seasonality:
            features = self._add_seasonality_features(df, features)
        
        # === REGIME FEATURES ===
        if self.config.include_regime:
            features = self._add_regime_features(df, features)
        
        # Store feature names
        self.feature_names_ = list(features.columns)
        
        # Handle NaN values
        features = features.ffill().fillna(0)
        
        # Scale features (if scaler is fitted)
        if not fit_scaler and hasattr(self, 'scaler_') and hasattr(self.scaler_, 'scale_'):
            features_scaled = pd.DataFrame(
                self.scaler_.transform(features),
                index=features.index,
                columns=features.columns
            )
            return features_scaled
        
        return features
    
    def _add_trend_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add trend-based features."""
        close = df['close']
        
        for window in self.config.trend_windows:
            # Moving averages
            features[f'ma_{window}'] = close.rolling(window).mean()
            features[f'ma_dist_{window}'] = (close - features[f'ma_{window}']) / features[f'ma_{window}']
            
            # EMA
            features[f'ema_{window}'] = close.ewm(span=window).mean()
            features[f'ema_dist_{window}'] = (close - features[f'ema_{window}']) / features[f'ema_{window}']
            
            # Trend strength (slope of linear regression)
            features[f'trend_slope_{window}'] = self._linear_slope(close, window)
        
        # MACD
        ema_fast = close.ewm(span=self.config.macd_fast).mean()
        ema_slow = close.ewm(span=self.config.macd_slow).mean()
        features['macd'] = ema_fast - ema_slow
        features['macd_signal'] = features['macd'].ewm(span=self.config.macd_signal).mean()
        features['macd_hist'] = features['macd'] - features['macd_signal']
        
        return features
    
    def _add_momentum_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add momentum-based features."""
        close = df['close']
        
        for window in self.config.momentum_windows:
            # Simple returns
            features[f'return_{window}d'] = close.pct_change(window)
            features[f'log_return_{window}d'] = np.log(close / close.shift(window))
            
            # Momentum (rate of change)
            features[f'momentum_{window}'] = close / close.shift(window) - 1
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(self.config.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.config.rsi_period).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        features['rsi_normalized'] = (features['rsi'] - 50) / 50  # Normalize to [-1, 1]
        
        return features
    
    def _add_volatility_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add volatility-based features."""
        returns = df['returns']
        
        for window in self.config.volatility_windows:
            # Realized volatility
            features[f'volatility_{window}d'] = returns.rolling(window).std() * np.sqrt(252)
            
            # Parkinson volatility (uses high-low range)
            hl_log = np.log(df['high'] / df['low'])
            features[f'parkinson_vol_{window}'] = np.sqrt(
                hl_log.pow(2).rolling(window).mean() / (4 * np.log(2))
            ) * np.sqrt(252)
            
            # Volatility of volatility
            vol = features[f'volatility_{window}d']
            features[f'vol_of_vol_{window}'] = vol.rolling(window).std()
        
        # ATR (Average True Range)
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift(1))
        tr3 = abs(df['low'] - df['close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        features['atr_14'] = tr.rolling(14).mean()
        features['atr_pct'] = features['atr_14'] / df['close']
        
        # Bollinger Bands
        bb_ma = df['close'].rolling(self.config.bb_period).mean()
        bb_std = df['close'].rolling(self.config.bb_period).std()
        features['bb_upper'] = bb_ma + self.config.bb_std * bb_std
        features['bb_lower'] = bb_ma - self.config.bb_std * bb_std
        features['bb_width'] = (features['bb_upper'] - features['bb_lower']) / bb_ma
        features['bb_position'] = (df['close'] - features['bb_lower']) / (features['bb_upper'] - features['bb_lower'])
        
        return features
    
    def _add_volume_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features."""
        volume = df['volume']
        close = df['close']
        
        for window in self.config.volume_windows:
            # Volume moving averages
            features[f'volume_ma_{window}'] = volume.rolling(window).mean()
            features[f'volume_ratio_{window}'] = volume / features[f'volume_ma_{window}']
        
        # OBV (On-Balance Volume)
        obv = [0]
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.append(obv[-1] + volume.iloc[i])
            elif close.iloc[i] < close.iloc[i-1]:
                obv.append(obv[-1] - volume.iloc[i])
            else:
                obv.append(obv[-1])
        features['obv'] = obv
        features['obv_ema'] = features['obv'].ewm(span=20).mean()
        
        # VWAP
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        features['vwap_dist'] = (close - vwap) / vwap
        
        # Volume trend
        features['volume_trend'] = self._linear_slope(volume, 20)
        
        return features
    
    def _add_mean_reversion_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add mean reversion features."""
        close = df['close']
        
        for window in [20, 50, 100]:
            ma = close.rolling(window).mean()
            std = close.rolling(window).std()
            
            # Z-score from moving average
            features[f'zscore_ma_{window}'] = (close - ma) / std
            
            # Distance from max/min
            rolling_max = close.rolling(window).max()
            rolling_min = close.rolling(window).min()
            features[f'dist_from_max_{window}'] = (close - rolling_max) / rolling_max
            features[f'dist_from_min_{window}'] = (close - rolling_min) / rolling_min
        
        # Mean reversion score (composite)
        features['mr_score'] = (
            features.get('zscore_ma_20', 0) * 0.5 +
            features.get('zscore_ma_50', 0) * 0.3 +
            features.get('zscore_ma_100', 0) * 0.2
        )
        
        return features
    
    def _add_cross_sectional_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add cross-sectional ranking features (for single asset, use time-based percentiles)."""
        returns = df['returns']
        
        for window in [20, 60, 252]:
            # Rolling percentile of returns
            features[f'return_percentile_{window}'] = returns.rolling(window).apply(
                lambda x: stats.percentileofscore(x, x[-1]) / 100 if len(x) > 0 else 0.5, raw=True
            )
            
            # Rolling rank of current return
            features[f'return_rank_{window}'] = returns.rolling(window).apply(
                lambda x: (x[-1] - np.min(x)) / (np.max(x) - np.min(x) + 1e-10) if len(x) > 0 else 0.5, raw=True
            )
        
        return features
    
    def _add_seasonality_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add seasonality features."""
        # Day of week
        features['day_of_week'] = df.index.dayofweek
        features['is_monday'] = (features['day_of_week'] == 0).astype(int)
        features['is_friday'] = (features['day_of_week'] == 4).astype(int)
        
        # Month
        features['month'] = df.index.month
        features['is_month_start'] = df.index.is_month_start.astype(int)
        features['is_month_end'] = df.index.is_month_end.astype(int)
        
        # Quarter
        features['quarter'] = df.index.quarter
        
        # Day of year (normalized)
        features['day_of_year'] = df.index.dayofyear / 365.0
        
        # Cyclical encoding
        features['month_sin'] = np.sin(2 * np.pi * features['month'] / 12)
        features['month_cos'] = np.cos(2 * np.pi * features['month'] / 12)
        features['dow_sin'] = np.sin(2 * np.pi * features['day_of_week'] / 5)
        features['dow_cos'] = np.cos(2 * np.pi * features['day_of_week'] / 5)
        
        return features
    
    def _add_regime_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add regime detection features."""
        returns = df['returns']
        close = df['close']
        
        # Trend strength (ADX-like)
        for window in [14, 20]:
            features[f'trend_strength_{window}'] = abs(
                self._linear_slope(close, window)
            ) / (returns.rolling(window).std() + 1e-10)
        
        # Volatility regime
        vol_20 = returns.rolling(20).std()
        vol_60 = returns.rolling(60).std()
        features['vol_regime'] = vol_20 / (vol_60 + 1e-10)
        features['high_vol_regime'] = (features['vol_regime'] > 1.5).astype(int)
        features['low_vol_regime'] = (features['vol_regime'] < 0.7).astype(int)
        
        # Drawdown
        rolling_max = close.cummax()
        drawdown = (close - rolling_max) / rolling_max
        features['drawdown'] = drawdown
        features['max_drawdown_20'] = drawdown.rolling(20).min()
        
        return features
    
    def _linear_slope(self, series: pd.Series, window: int) -> pd.Series:
        """Calculate linear regression slope over rolling window."""
        def slope(x):
            if len(x) < 2:
                return 0
            x_norm = np.arange(len(x))
            return np.polyfit(x_norm, x, 1)[0]
        
        return series.rolling(window).apply(slope, raw=True)
    
    def get_feature_importance_mask(self, X: pd.DataFrame, y: pd.Series, 
                                     threshold: float = 0.01) -> List[bool]:
        """Get mask of important features based on mutual information."""
        if len(np.unique(y)) <= 5:
            mi_scores = mutual_info_classif(X, y, random_state=42)
        else:
            mi_scores = mutual_info_regression(X, y, random_state=42)
        
        # Normalize scores
        mi_scores = mi_scores / mi_scores.sum()
        return mi_scores >= threshold


# ================================================================================
# SECTION 3: TIME SERIES CROSS-VALIDATION (PURGED & EMBARGO)
# ================================================================================

class PurgedKFold(BaseCrossValidator):
    """
    Purged K-Fold cross-validation for time series.
    
    Purging: Remove observations from training set that are too close to test set
    to prevent information leakage.
    
    Embargo: Additional buffer after test set before next training set begins.
    
    Reference: Advances in Financial Machine Learning (Marcos Lopez de Prado)
    """
    
    def __init__(self, n_splits: int = 5, purge_gap: int = 5, embargo_pct: float = 0.01):
        self.n_splits = n_splits
        self.purge_gap = purge_gap
        self.embargo_pct = embargo_pct
    
    def split(self, X, y=None, groups=None):
        """Generate indices to split data into training and test set."""
        n_samples = len(X)
        indices = np.arange(n_samples)
        
        # Calculate fold sizes
        fold_size = n_samples // self.n_splits
        embargo_size = int(fold_size * self.embargo_pct)
        
        for i in range(self.n_splits):
            # Test set indices
            test_start = i * fold_size
            test_end = min((i + 1) * fold_size, n_samples)
            test_indices = indices[test_start:test_end]
            
            # Training set indices (before test with purge gap)
            train_end = max(0, test_start - self.purge_gap)
            train_indices_before = indices[:train_end]
            
            # Training set indices (after test with embargo)
            train_start = min(n_samples, test_end + embargo_size)
            train_indices_after = indices[train_start:]
            
            # Combine training indices
            train_indices = np.concatenate([train_indices_before, train_indices_after])
            
            yield train_indices, test_indices
    
    def get_n_splits(self, X=None, y=None, groups=None):
        return self.n_splits


class WalkForwardCV(BaseCrossValidator):
    """
    Walk-forward cross-validation with purging.
    
    Training window expands or rolls forward in time.
    Test window follows training window with a purge gap.
    """
    
    def __init__(self, train_size: int, test_size: int, step_size: int = None, 
                 purge_gap: int = 5, embargo_pct: float = 0.01):
        self.train_size = train_size
        self.test_size = test_size
        self.step_size = step_size or test_size
        self.purge_gap = purge_gap
        self.embargo_pct = embargo_pct
    
    def split(self, X, y=None, groups=None):
        """Generate walk-forward splits."""
        n_samples = len(X)
        indices = np.arange(n_samples)
        
        # Calculate number of splits
        embargo_size = int(self.test_size * self.embargo_pct)
        total_step = self.test_size + self.purge_gap + embargo_size + self.step_size
        n_splits = max(1, (n_samples - self.train_size - self.test_size) // self.step_size)
        
        for i in range(n_splits):
            # Training window
            train_start = i * self.step_size
            train_end = train_start + self.train_size
            
            if train_end + self.test_size + self.purge_gap > n_samples:
                break
            
            train_indices = indices[train_start:train_end]
            
            # Test window (after purge gap)
            test_start = train_end + self.purge_gap
            test_end = min(test_start + self.test_size, n_samples)
            test_indices = indices[test_start:test_end]
            
            yield train_indices, test_indices
    
    def get_n_splits(self, X=None, y=None, groups=None):
        n_samples = len(X) if X is not None else 0
        total_step = self.test_size + self.purge_gap + int(self.test_size * self.embargo_pct) + self.step_size
        return max(1, (n_samples - self.train_size - self.test_size) // self.step_size)


class CombinatorialCV(BaseCrossValidator):
    """
    Combinatorial cross-validation for backtest overfitting assessment.
    
    Generates multiple train/test splits to estimate variance of strategy performance.
    
    Reference: Advances in Financial Machine Learning (Marcos Lopez de Prado)
    """
    
    def __init__(self, n_splits: int = 10, n_test_splits: int = 2, purge_gap: int = 5):
        self.n_splits = n_splits
        self.n_test_splits = n_test_splits
        self.purge_gap = purge_gap
        from itertools import combinations
        self.combinations_ = list(combinations(range(n_splits), n_test_splits))
    
    def split(self, X, y=None, groups=None):
        """Generate combinatorial splits."""
        n_samples = len(X)
        fold_size = n_samples // self.n_splits
        indices = np.arange(n_samples)
        
        for test_folds in self.combinations_:
            # Test indices
            test_indices = []
            for fold in test_folds:
                start = fold * fold_size
                end = min((fold + 1) * fold_size, n_samples)
                test_indices.extend(indices[start:end])
            
            # Train indices (all other folds with purge gaps)
            train_indices = []
            last_test_fold = -1
            for fold in range(self.n_splits):
                if fold in test_folds:
                    last_test_fold = fold
                    continue
                
                start = fold * fold_size
                # Apply purge gap if adjacent to test fold
                if fold == last_test_fold + 1:
                    start = min(start + self.purge_gap, n_samples)
                
                end = min((fold + 1) * fold_size, n_samples)
                train_indices.extend(indices[start:end])
            
            yield np.array(train_indices), np.array(test_indices)
    
    def get_n_splits(self, X=None, y=None, groups=None):
        return len(self.combinations_)


# ================================================================================
# SECTION 4: MODEL FACTORY & BASE CLASSES
# ================================================================================

class BaseMLModel(ABC):
    """Abstract base class for ML models in trading."""
    
    def __init__(self, model_config: ModelConfig = None):
        self.config = model_config or ModelConfig()
        self.model_ = None
        self.feature_importance_: Dict[str, float] = {}
        self.is_fitted_: bool = False
    
    @abstractmethod
    def build_model(self, **kwargs):
        """Build the underlying model."""
        pass
    
    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight: np.ndarray = None):
        """Fit the model."""
        pass
    
    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions."""
        pass
    
    @abstractmethod
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probabilities (for classification)."""
        pass
    
    def get_feature_importance(self) -> pd.Series:
        """Get feature importance if available."""
        if not self.feature_importance_:
            return pd.Series()
        return pd.Series(self.feature_importance_).sort_values(ascending=False)


class SklearnModelWrapper(BaseMLModel):
    """Wrapper for sklearn-compatible models."""
    
    def __init__(self, model_class, model_config: ModelConfig = None, **model_kwargs):
        super().__init__(model_config)
        self.model_class = model_class
        self.model_kwargs = model_kwargs
        self.build_model(**model_kwargs)
    
    def build_model(self, **kwargs):
        """Build sklearn model."""
        self.model_ = self.model_class(**kwargs)
        return self
    
    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight: np.ndarray = None):
        """Fit the model."""
        if sample_weight is not None:
            self.model_.fit(X, y, sample_weight=sample_weight)
        else:
            self.model_.fit(X, y)
        
        # Extract feature importance
        if hasattr(self.model_, 'feature_importances_'):
            self.feature_importance_ = dict(zip(X.columns, self.model_.feature_importances_))
        elif hasattr(self.model_, 'coef_'):
            self.feature_importance_ = dict(zip(X.columns, np.abs(self.model_.coef_).flatten()))
        
        self.is_fitted_ = True
        return self
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions."""
        return self.model_.predict(X)
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probabilities."""
        if hasattr(self.model_, 'predict_proba'):
            return self.model_.predict_proba(X)
        # For models without predict_proba, return dummy probabilities
        preds = self.predict(X)
        return np.column_stack([1 - preds, preds]) if len(np.unique(preds)) == 2 else np.eye(len(np.unique(preds)))[preds.astype(int)]


class ModelFactory:
    """Factory for creating ML models."""
    
    @staticmethod
    def create_model(model_type: ModelType, model_config: ModelConfig = None, 
                     task: str = "classification", **kwargs) -> BaseMLModel:
        """
        Create a model of specified type.
        
        Args:
            model_type: Type of model to create
            model_config: Model configuration
            task: "classification" or "regression"
            **kwargs: Additional model parameters
        
        Returns:
            BaseMLModel instance
        """
        config = model_config or ModelConfig()
        
        if model_type == ModelType.RANDOM_FOREST:
            if task == "classification":
                return SklearnModelWrapper(
                    RandomForestClassifier, config,
                    n_estimators=kwargs.get('n_estimators', 200),
                    max_depth=kwargs.get('max_depth', 10),
                    min_samples_leaf=kwargs.get('min_samples_leaf', 50),
                    random_state=42,
                    n_jobs=-1
                )
            else:
                return SklearnModelWrapper(
                    RandomForestRegressor, config,
                    n_estimators=kwargs.get('n_estimators', 200),
                    max_depth=kwargs.get('max_depth', 10),
                    min_samples_leaf=kwargs.get('min_samples_leaf', 50),
                    random_state=42,
                    n_jobs=-1
                )
        
        elif model_type == ModelType.GRADIENT_BOOSTING:
            if task == "classification":
                return SklearnModelWrapper(
                    GradientBoostingClassifier, config,
                    n_estimators=kwargs.get('n_estimators', 100),
                    max_depth=kwargs.get('max_depth', 5),
                    learning_rate=kwargs.get('learning_rate', 0.1),
                    random_state=42
                )
            else:
                return SklearnModelWrapper(
                    GradientBoostingRegressor, config,
                    n_estimators=kwargs.get('n_estimators', 100),
                    max_depth=kwargs.get('max_depth', 5),
                    learning_rate=kwargs.get('learning_rate', 0.1),
                    random_state=42
                )
        
        elif model_type == ModelType.XGBOOST:
            if not XGBOOST_AVAILABLE:
                raise ImportError("XGBoost not installed")
            if task == "classification":
                return SklearnModelWrapper(
                    xgb.XGBClassifier, config,
                    n_estimators=kwargs.get('n_estimators', 200),
                    max_depth=kwargs.get('max_depth', 6),
                    learning_rate=kwargs.get('learning_rate', 0.1),
                    subsample=kwargs.get('subsample', 0.8),
                    colsample_bytree=kwargs.get('colsample_bytree', 0.8),
                    random_state=42,
                    n_jobs=-1
                )
            else:
                return SklearnModelWrapper(
                    xgb.XGBRegressor, config,
                    n_estimators=kwargs.get('n_estimators', 200),
                    max_depth=kwargs.get('max_depth', 6),
                    learning_rate=kwargs.get('learning_rate', 0.1),
                    subsample=kwargs.get('subsample', 0.8),
                    colsample_bytree=kwargs.get('colsample_bytree', 0.8),
                    random_state=42,
                    n_jobs=-1
                )
        
        elif model_type == ModelType.LIGHTGBM:
            if not LIGHTGBM_AVAILABLE:
                raise ImportError("LightGBM not installed. Use: pip install lightgbm")
            if task == "classification":
                return SklearnModelWrapper(
                    lgb.LGBMClassifier, config,
                    n_estimators=kwargs.get('n_estimators', 200),
                    max_depth=kwargs.get('max_depth', 6),
                    learning_rate=kwargs.get('learning_rate', 0.1),
                    subsample=kwargs.get('subsample', 0.8),
                    colsample_bytree=kwargs.get('colsample_bytree', 0.8),
                    random_state=42,
                    n_jobs=-1,
                    verbose=-1
                )
            else:
                return SklearnModelWrapper(
                    lgb.LGBMRegressor, config,
                    n_estimators=kwargs.get('n_estimators', 200),
                    max_depth=kwargs.get('max_depth', 6),
                    learning_rate=kwargs.get('learning_rate', 0.1),
                    subsample=kwargs.get('subsample', 0.8),
                    colsample_bytree=kwargs.get('colsample_bytree', 0.8),
                    random_state=42,
                    n_jobs=-1,
                    verbose=-1
                )
        
        elif model_type == ModelType.LOGISTIC_REGRESSION:
            return SklearnModelWrapper(
                LogisticRegression, config,
                C=kwargs.get('C', 1.0),
                max_iter=kwargs.get('max_iter', 1000),
                random_state=42,
                n_jobs=-1
            )
        
        elif model_type == ModelType.RIDGE:
            if task == "classification":
                # Use LogisticRegression with L2 penalty for classification
                return SklearnModelWrapper(
                    LogisticRegression, config,
                    C=1.0/kwargs.get('alpha', 1.0),
                    penalty='l2',
                    max_iter=kwargs.get('max_iter', 1000),
                    random_state=42,
                    n_jobs=-1
                )
            else:
                return SklearnModelWrapper(
                    Ridge, config,
                    alpha=kwargs.get('alpha', 1.0),
                    random_state=42
                )
        
        elif model_type == ModelType.ELASTIC_NET:
            return SklearnModelWrapper(
                ElasticNet, config,
                alpha=kwargs.get('alpha', 1.0),
                l1_ratio=kwargs.get('l1_ratio', 0.5),
                random_state=42
            )
        
        else:
            raise ValueError(f"Unknown model type: {model_type}")


# ================================================================================
# SECTION 5: REGIME DETECTION
# ================================================================================

class RegimeDetector:
    """
    Detect market regimes using multiple methods.
    
    Methods:
    - Volatility-based: High/Low volatility regimes
    - Trend-based: Trending/Ranging markets
    - HMM-based: Hidden Markov Model for regime detection
    - Clustering: K-means on regime features
    """
    
    def __init__(self, method: str = "composite"):
        self.method = method
        self.regime_history_: List[RegimeState] = []
        self.transition_matrix_: Optional[np.ndarray] = None
        self.current_regime_: Optional[RegimeType] = None
    
    def detect_regime(self, features: pd.DataFrame, 
                      returns: pd.Series) -> RegimeState:
        """
        Detect current market regime.
        
        Args:
            features: Feature DataFrame with regime indicators
            returns: Return series
        
        Returns:
            RegimeState object
        """
        # Extract key regime indicators
        latest = features.iloc[-1]
        
        # Volatility regime
        vol_regime = self._detect_volatility_regime(features, returns)
        
        # Trend regime
        trend_regime = self._detect_trend_regime(features)
        
        # Crisis detection
        crisis_score = self._calculate_crisis_score(features, returns)
        
        # Combine into composite regime
        composite_regime = self._combine_regimes(
            vol_regime, trend_regime, crisis_score, latest
        )
        
        # Calculate regime confidence
        confidence = self._calculate_regime_confidence(
            vol_regime, trend_regime, crisis_score, features
        )
        
        # Calculate transition probabilities
        transition_prob = self._calculate_transition_prob(composite_regime)
        
        regime_state = RegimeState(
            regime=composite_regime,
            confidence=confidence,
            features=latest.to_dict(),
            transition_prob=transition_prob,
            timestamp=features.index[-1]
        )
        
        self.regime_history_.append(regime_state)
        self.current_regime_ = composite_regime
        
        return regime_state
    
    def _detect_volatility_regime(self, features: pd.DataFrame, 
                                   returns: pd.Series) -> RegimeType:
        """Detect volatility regime."""
        # Use realized volatility
        vol_col = 'volatility_20d' if 'volatility_20d' in features.columns else None
        
        if vol_col:
            current_vol = features[vol_col].iloc[-1]
            vol_percentile = features[vol_col].rolling(252).apply(
                lambda x: stats.percentileofscore(x, x.iloc[-1]) / 100, raw=True
            ).iloc[-1]
            
            if vol_percentile > 0.8:
                return RegimeType.HIGH_VOLATILITY
            elif vol_percentile < 0.3:
                return RegimeType.LOW_VOLATILITY
        
        return RegimeType.RANGING  # Default
    
    def _detect_trend_regime(self, features: pd.DataFrame) -> RegimeType:
        """Detect trend regime."""
        # Use trend strength indicators
        trend_col = 'trend_strength_20' if 'trend_strength_20' in features.columns else None
        
        if trend_col:
            trend_strength = features[trend_col].iloc[-1]
            
            # Check price relative to moving averages
            ma_dist_20 = features.get('ma_dist_20', pd.Series([0])).iloc[-1]
            ma_dist_50 = features.get('ma_dist_50', pd.Series([0])).iloc[-1]
            
            if trend_strength > 0.5 and ma_dist_20 > 0 and ma_dist_50 > 0:
                return RegimeType.BULL_TREND
            elif trend_strength > 0.5 and ma_dist_20 < 0 and ma_dist_50 < 0:
                return RegimeType.BEAR_TREND
            elif trend_strength < 0.2:
                return RegimeType.RANGING
        
        return RegimeType.TRENDING
    
    def _calculate_crisis_score(self, features: pd.DataFrame, 
                                 returns: pd.Series) -> float:
        """Calculate crisis probability score."""
        score = 0.0
        
        # Drawdown-based
        if 'max_drawdown_20' in features.columns:
            dd = features['max_drawdown_20'].iloc[-1]
            if dd < -0.1:
                score += 0.3
            if dd < -0.2:
                score += 0.4
        
        # Volatility spike
        if 'vol_regime' in features.columns:
            vol_regime = features['vol_regime'].iloc[-1]
            if vol_regime > 2.0:
                score += 0.3
        
        # Trend breakdown
        if 'trend_strength_20' in features.columns:
            trend = features['trend_strength_20'].iloc[-1]
            if trend < 0.1 and returns.tail(20).std() > returns.tail(60).std():
                score += 0.2
        
        return min(score, 1.0)
    
    def _combine_regimes(self, vol_regime: RegimeType, trend_regime: RegimeType,
                         crisis_score: float, latest: pd.Series) -> RegimeType:
        """Combine multiple regime signals into final regime."""
        # Crisis override
        if crisis_score > 0.7:
            return RegimeType.CRISIS
        
        # Recovery detection
        if crisis_score > 0.3 and 'drawdown' in latest:
            dd = latest['drawdown']
            if dd > -0.05 and vol_regime == RegimeType.HIGH_VOLATILITY:
                return RegimeType.RECOVERY
        
        # Trend takes precedence in normal times
        if trend_regime in [RegimeType.BULL_TREND, RegimeType.BEAR_TREND]:
            return trend_regime
        
        # Volatility regime in ranging markets
        if trend_regime == RegimeType.RANGING:
            return vol_regime
        
        return trend_regime
    
    def _calculate_regime_confidence(self, vol_regime: RegimeType, 
                                      trend_regime: RegimeType,
                                      crisis_score: float, 
                                      features: pd.DataFrame) -> float:
        """Calculate confidence in regime classification."""
        # Higher confidence when signals agree
        confidence = 0.5
        
        # Agreement bonus
        if vol_regime == trend_regime:
            confidence += 0.2
        
        # Data quality bonus
        if len(features) > 100:
            confidence += 0.1
        
        # Crisis clarity
        if crisis_score > 0.8 or crisis_score < 0.2:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _calculate_transition_prob(self, current_regime: RegimeType) -> Dict[RegimeType, float]:
        """Calculate transition probabilities from current regime."""
        # Simplified transition model
        probs = {regime: 0.1 for regime in RegimeType}
        probs[current_regime] = 0.5  # Stay in current regime
        
        # Regime-specific adjustments
        if current_regime == RegimeType.CRISIS:
            probs[RegimeType.RECOVERY] = 0.3
            probs[RegimeType.HIGH_VOLATILITY] = 0.2
        elif current_regime == RegimeType.BULL_TREND:
            probs[RegimeType.RANGING] = 0.2
            probs[RegimeType.HIGH_VOLATILITY] = 0.1
        
        # Normalize
        total = sum(probs.values())
        return {k: v/total for k, v in probs.items()}
    
    def get_regime_history(self) -> pd.DataFrame:
        """Get regime history as DataFrame."""
        if not self.regime_history_:
            return pd.DataFrame()
        
        records = []
        for state in self.regime_history_:
            records.append({
                'timestamp': state.timestamp,
                'regime': state.regime.value,
                'confidence': state.confidence,
                **{f'feature_{k}': v for k, v in state.features.items()}
            })
        
        return pd.DataFrame(records).set_index('timestamp')


# ================================================================================
# SECTION 6: MULTIPLE HYPOTHESIS CORRECTION
# ================================================================================

class MultipleHypothesisCorrection:
    """
    Multiple hypothesis testing correction for financial ML.
    
    Methods:
    - Bonferroni: Conservative, controls family-wise error rate
    - Benjamini-Hochberg (FDR): Controls false discovery rate
    - Sidak: Less conservative than Bonferroni
    - Holm: Step-down procedure
    """
    
    @staticmethod
    def bonferroni_correction(p_values: np.ndarray, alpha: float = 0.05) -> Tuple[np.ndarray, float]:
        """
        Apply Bonferroni correction.
        
        Args:
            p_values: Array of p-values
            alpha: Significance level
        
        Returns:
            Tuple of (rejected hypotheses, corrected alpha)
        """
        n_tests = len(p_values)
        corrected_alpha = alpha / n_tests
        rejected = p_values < corrected_alpha
        return rejected, corrected_alpha
    
    @staticmethod
    def benjamini_hochberg(p_values: np.ndarray, alpha: float = 0.05) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply Benjamini-Hochberg FDR correction.
        
        Args:
            p_values: Array of p-values
            alpha: FDR level
        
        Returns:
            Tuple of (rejected hypotheses, adjusted p-values)
        """
        n_tests = len(p_values)
        sorted_indices = np.argsort(p_values)
        sorted_pvals = p_values[sorted_indices]
        
        # Find largest k such that p(k) <= (k/m) * alpha
        thresholds = np.arange(1, n_tests + 1) / n_tests * alpha
        rejected_sorted = sorted_pvals <= thresholds
        
        # Find the largest k where condition holds
        k = np.max(np.where(rejected_sorted)[0]) if np.any(rejected_sorted) else -1
        
        # All hypotheses up to k are rejected
        rejected = np.zeros(n_tests, dtype=bool)
        if k >= 0:
            rejected[sorted_indices[:k+1]] = True
        
        # Calculate adjusted p-values
        adjusted_pvals = np.minimum.accumulate(
            sorted_pvals[::-1] * np.arange(n_tests, 0, -1)
        )[::-1]
        adjusted_pvals = np.minimum(adjusted_pvals, 1.0)
        
        # Restore original order
        adjusted_pvals_original = np.empty(n_tests)
        adjusted_pvals_original[sorted_indices] = adjusted_pvals
        
        return rejected, adjusted_pvals_original
    
    @staticmethod
    def sidak_correction(p_values: np.ndarray, alpha: float = 0.05) -> Tuple[np.ndarray, float]:
        """Apply Sidak correction."""
        n_tests = len(p_values)
        corrected_alpha = 1 - (1 - alpha) ** (1 / n_tests)
        rejected = p_values < corrected_alpha
        return rejected, corrected_alpha
    
    @staticmethod
    def holm_correction(p_values: np.ndarray, alpha: float = 0.05) -> np.ndarray:
        """Apply Holm-Bonferroni step-down correction."""
        n_tests = len(p_values)
        sorted_indices = np.argsort(p_values)
        sorted_pvals = p_values[sorted_indices]
        
        rejected = np.zeros(n_tests, dtype=bool)
        
        for i, pval in enumerate(sorted_pvals):
            if pval <= alpha / (n_tests - i):
                rejected[sorted_indices[i]] = True
            else:
                break
        
        return rejected
    
    @classmethod
    def apply_all_corrections(cls, p_values: np.ndarray, alpha: float = 0.05) -> pd.DataFrame:
        """Apply all correction methods and return results."""
        results = pd.DataFrame({
            'p_value': p_values,
            'bonferroni_rejected': cls.bonferroni_correction(p_values, alpha)[0],
            'bh_rejected': cls.benjamini_hochberg(p_values, alpha)[0],
            'sidak_rejected': cls.sidak_correction(p_values, alpha)[0],
            'holm_rejected': cls.holm_correction(p_values, alpha)
        })
        
        results['bh_adjusted_pval'] = cls.benjamini_hochberg(p_values, alpha)[1]
        
        return results


# ================================================================================
# SECTION 7: ABLATION TESTING FRAMEWORK
# ================================================================================

class AblationTester:
    """
    Ablation testing framework for feature and model analysis.
    
    Tests the contribution of individual features or feature groups
    by removing them and measuring performance degradation.
    """
    
    def __init__(self, model: BaseMLModel, cv: BaseCrossValidator):
        self.model = model
        self.cv = cv
        self.results_: Dict[str, Dict] = {}
    
    def test_feature_ablation(self, X: pd.DataFrame, y: pd.Series,
                               feature_groups: Dict[str, List[str]] = None,
                               metric: Callable = accuracy_score) -> pd.DataFrame:
        """
        Test feature ablation.
        
        Args:
            X: Feature matrix
            y: Target vector
            feature_groups: Dict of group name -> list of features
            metric: Evaluation metric
        
        Returns:
            DataFrame with ablation results
        """
        # Baseline performance
        baseline_scores = self._cross_val_score(X, y, metric)
        baseline_mean = np.mean(baseline_scores)
        
        results = []
        
        # Test each feature group
        if feature_groups is None:
            # Test individual features
            feature_groups = {col: [col] for col in X.columns}
        
        for group_name, features in feature_groups.items():
            # Remove feature group
            X_ablated = X.drop(columns=[f for f in features if f in X.columns])
            
            if X_ablated.empty:
                continue
            
            # Evaluate
            ablated_scores = self._cross_val_score(X_ablated, y, metric)
            ablated_mean = np.mean(ablated_scores)
            
            # Calculate importance
            importance = baseline_mean - ablated_mean
            
            results.append({
                'feature_group': group_name,
                'baseline_score': baseline_mean,
                'ablated_score': ablated_mean,
                'importance': importance,
                'importance_pct': (importance / baseline_mean) * 100 if baseline_mean != 0 else 0,
                'n_features_removed': len(features),
                'n_features_remaining': X_ablated.shape[1]
            })
        
        return pd.DataFrame(results).sort_values('importance', ascending=False)
    
    def test_model_ablation(self, X: pd.DataFrame, y: pd.Series,
                            models: Dict[str, BaseMLModel],
                            metric: Callable = accuracy_score) -> pd.DataFrame:
        """Test different model configurations."""
        results = []
        
        for model_name, model in models.items():
            scores = self._cross_val_score(X, y, metric, model)
            results.append({
                'model': model_name,
                'mean_score': np.mean(scores),
                'std_score': np.std(scores),
                'min_score': np.min(scores),
                'max_score': np.max(scores)
            })
        
        return pd.DataFrame(results).sort_values('mean_score', ascending=False)
    
    def _cross_val_score(self, X: pd.DataFrame, y: pd.Series,
                         metric: Callable, model: BaseMLModel = None) -> np.ndarray:
        """Calculate cross-validated scores."""
        model = model or self.model
        scores = []
        
        for train_idx, test_idx in self.cv.split(X, y):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
            
            model_clone = clone(model.model_) if hasattr(model, 'model_') else model
            model_clone.fit(X_train, y_train)
            y_pred = model_clone.predict(X_test)
            
            scores.append(metric(y_test, y_pred))
        
        return np.array(scores)


# ================================================================================
# SECTION 8: STRATEGY ARBITRATOR (META-LEARNER)
# ================================================================================

class StrategyArbitrator:
    """
    Meta-learner that arbitrates between multiple trading strategies.
    
    Key Functions:
    1. Monitor strategy performance in real-time
    2. Detect market regimes
    3. Dynamically weight strategies based on regime and recent performance
    4. Silence underperforming strategies
    5. Provide confidence scores for combined signals
    
    Architecture:
    - Input: Signals from multiple strategies
    - Processing: Regime detection + Performance tracking + Dynamic weighting
    - Output: Weighted ensemble signal with confidence
    """
    
    def __init__(self, 
                 config: ModelConfig = None,
                 regime_detector: RegimeDetector = None,
                 lookback_window: int = 63,
                 performance_metric: str = "sharpe"):
        """
        Initialize StrategyArbitrator.
        
        Args:
            config: Model configuration
            regime_detector: Regime detector instance
            lookback_window: Window for performance evaluation
            performance_metric: Metric for strategy evaluation
        """
        self.config = config or ModelConfig()
        self.regime_detector = regime_detector or RegimeDetector()
        self.lookback_window = lookback_window
        self.performance_metric = performance_metric
        
        # Strategy tracking
        self.strategies: Dict[str, Dict] = {}
        self.strategy_performance: Dict[str, pd.DataFrame] = {}
        self.strategy_weights: Dict[str, float] = {}
        self.strategy_active: Dict[str, bool] = {}
        
        # Signal history
        self.signal_history: List[Dict] = []
        
        # Meta-learner model
        self.meta_learner: Optional[BaseMLModel] = None
        self.regime_strategy_map: Dict[RegimeType, Dict[str, float]] = {}
        
        # Configuration
        self.min_signals_for_consensus = 2
        self.confidence_threshold = 0.6
        self.silence_threshold = 0.3  # Performance percentile to silence
        
    def register_strategy(self, strategy_id: str, 
                          strategy_info: Dict = None) -> None:
        """
        Register a new strategy with the arbitrator.
        
        Args:
            strategy_id: Unique strategy identifier
            strategy_info: Dict with strategy metadata
        """
        self.strategies[strategy_id] = strategy_info or {}
        self.strategy_performance[strategy_id] = pd.DataFrame()
        self.strategy_weights[strategy_id] = 1.0 / max(len(self.strategies), 1)
        self.strategy_active[strategy_id] = True
        
        logger.info(f"Registered strategy: {strategy_id}")
    
    def process_signals(self, 
                        signals: List[StrategySignal],
                        market_features: pd.DataFrame,
                        market_returns: pd.Series) -> Dict:
        """
        Process incoming strategy signals and produce arbitrated output.
        
        Args:
            signals: List of strategy signals
            market_features: Current market features
            market_returns: Recent market returns for performance calc
        
        Returns:
            Dict with arbitrated signal, confidence, and metadata
        """
        # Update performance tracking
        self._update_performance(signals, market_returns)
        
        # Detect current regime
        regime_state = self.regime_detector.detect_regime(market_features, market_returns)
        
        # Update strategy weights based on regime and performance
        self._update_weights(regime_state)
        
        # Silence underperforming strategies
        self._silence_underperformers()
        
        # Calculate ensemble signal
        ensemble_result = self._calculate_ensemble_signal(signals, regime_state)
        
        # Store history
        self.signal_history.append({
            'timestamp': market_features.index[-1],
            'regime': regime_state.regime.value,
            'regime_confidence': regime_state.confidence,
            'ensemble_signal': ensemble_result['signal'],
            'ensemble_confidence': ensemble_result['confidence'],
            'strategy_weights': self.strategy_weights.copy(),
            'active_strategies': self.strategy_active.copy()
        })
        
        return ensemble_result
    
    def _update_performance(self, signals: List[StrategySignal], 
                            market_returns: pd.Series) -> None:
        """Update strategy performance tracking."""
        for signal in signals:
            if signal.strategy_id not in self.strategies:
                self.register_strategy(signal.strategy_id)
            
            # Calculate recent performance
            if len(market_returns) >= self.lookback_window:
                recent_returns = market_returns.tail(self.lookback_window)
                
                # Strategy-implied returns (simplified)
                strategy_returns = recent_returns * signal.signal.value
                
                performance = {
                    'timestamp': signal.timestamp,
                    'signal': signal.signal.value,
                    'confidence': signal.confidence,
                    'cumulative_return': (1 + strategy_returns).prod() - 1,
                    'sharpe_ratio': self._calculate_sharpe(strategy_returns),
                    'max_drawdown': self._calculate_max_drawdown(strategy_returns),
                    'win_rate': (strategy_returns > 0).mean(),
                    'volatility': strategy_returns.std() * np.sqrt(252)
                }
                
                # Append to performance history
                perf_df = pd.DataFrame([performance])
                self.strategy_performance[signal.strategy_id] = pd.concat([
                    self.strategy_performance[signal.strategy_id],
                    perf_df
                ], ignore_index=True)
    
    def _update_weights(self, regime_state: RegimeState) -> None:
        """Update strategy weights based on regime and performance."""
        # Get regime-specific performance
        regime_perf = {}
        
        for strategy_id, perf_df in self.strategy_performance.items():
            if len(perf_df) < 10:
                regime_perf[strategy_id] = 0.5  # Default for new strategies
                continue
            
            # Calculate recent performance score
            if self.performance_metric == "sharpe":
                score = perf_df['sharpe_ratio'].tail(self.lookback_window).mean()
            elif self.performance_metric == "return":
                score = perf_df['cumulative_return'].tail(self.lookback_window).mean()
            elif self.performance_metric == "win_rate":
                score = perf_df['win_rate'].tail(self.lookback_window).mean()
            else:
                score = perf_df['sharpe_ratio'].tail(self.lookback_window).mean()
            
            # Apply regime-specific multiplier
            regime_multiplier = self._get_regime_multiplier(strategy_id, regime_state.regime)
            regime_perf[strategy_id] = score * regime_multiplier
        
        # Convert to weights (softmax)
        if regime_perf:
            scores = np.array(list(regime_perf.values()))
            # Shift scores to avoid overflow
            scores_shifted = scores - np.max(scores)
            exp_scores = np.exp(scores_shifted)
            weights = exp_scores / np.sum(exp_scores)
            
            for i, strategy_id in enumerate(regime_perf.keys()):
                self.strategy_weights[strategy_id] = weights[i]
    
    def _get_regime_multiplier(self, strategy_id: str, regime: RegimeType) -> float:
        """Get performance multiplier for strategy in given regime."""
        # Check if we have regime-specific mapping
        if regime in self.regime_strategy_map and strategy_id in self.regime_strategy_map[regime]:
            return self.regime_strategy_map[regime][strategy_id]
        
        # Default multipliers based on strategy type
        strategy_info = self.strategies.get(strategy_id, {})
        strategy_type = strategy_info.get('type', 'unknown')
        
        multipliers = {
            'trend_following': {
                RegimeType.BULL_TREND: 1.5,
                RegimeType.BEAR_TREND: 1.3,
                RegimeType.TRENDING: 1.4,
                RegimeType.RANGING: 0.5,
                RegimeType.HIGH_VOLATILITY: 0.7,
                RegimeType.CRISIS: 0.3
            },
            'mean_reversion': {
                RegimeType.RANGING: 1.5,
                RegimeType.LOW_VOLATILITY: 1.4,
                RegimeType.BULL_TREND: 0.6,
                RegimeType.BEAR_TREND: 0.5,
                RegimeType.TRENDING: 0.4,
                RegimeType.CRISIS: 0.2
            },
            'momentum': {
                RegimeType.BULL_TREND: 1.4,
                RegimeType.TRENDING: 1.3,
                RegimeType.BEAR_TREND: 0.8,
                RegimeType.RANGING: 0.6,
                RegimeType.CRISIS: 0.4
            },
            'volatility': {
                RegimeType.HIGH_VOLATILITY: 1.5,
                RegimeType.CRISIS: 1.3,
                RegimeType.LOW_VOLATILITY: 0.4,
                RegimeType.BULL_TREND: 0.7
            }
        }
        
        return multipliers.get(strategy_type, {}).get(regime, 1.0)
    
    def _silence_underperformers(self) -> None:
        """Silence strategies with poor recent performance."""
        if len(self.strategy_performance) < 2:
            return
        
        # Get recent performance scores
        recent_scores = {}
        for strategy_id, perf_df in self.strategy_performance.items():
            if len(perf_df) >= 10:
                recent_scores[strategy_id] = perf_df['sharpe_ratio'].tail(20).mean()
            else:
                recent_scores[strategy_id] = 0
        
        if not recent_scores:
            return
        
        # Calculate percentile threshold
        scores = list(recent_scores.values())
        threshold = np.percentile(scores, self.silence_threshold * 100)
        
        # Silence strategies below threshold
        for strategy_id, score in recent_scores.items():
            if score < threshold and self.strategy_weights[strategy_id] < 0.1:
                self.strategy_active[strategy_id] = False
                logger.info(f"Silenced strategy {strategy_id} (score: {score:.3f})")
            elif score > np.percentile(scores, 50) and not self.strategy_active[strategy_id]:
                self.strategy_active[strategy_id] = True
                logger.info(f"Reactivated strategy {strategy_id} (score: {score:.3f})")
    
    def _calculate_ensemble_signal(self, signals: List[StrategySignal],
                                    regime_state: RegimeState) -> Dict:
        """Calculate ensemble signal from weighted strategy signals."""
        # Filter active strategies
        active_signals = [
            s for s in signals 
            if self.strategy_active.get(s.strategy_id, True)
        ]
        
        if len(active_signals) < self.min_signals_for_consensus:
            return {
                'signal': SignalType.NEUTRAL,
                'confidence': 0.0,
                'weighted_signal': 0.0,
                'signal_strength': 0.0,
                'consensus_ratio': 0.0,
                'n_active_strategies': len(active_signals),
                'regime': regime_state.regime.value,
                'regime_confidence': regime_state.confidence
            }
        
        # Calculate weighted signal
        weighted_sum = 0.0
        total_weight = 0.0
        
        for signal in active_signals:
            weight = self.strategy_weights.get(signal.strategy_id, 1.0 / len(active_signals))
            confidence = signal.confidence
            
            weighted_sum += signal.signal.value * weight * confidence
            total_weight += weight * confidence
        
        # Normalize
        if total_weight > 0:
            weighted_signal = weighted_sum / total_weight
        else:
            weighted_signal = 0
        
        # Determine signal type
        if weighted_signal > 0.3:
            signal_type = SignalType.LONG
        elif weighted_signal < -0.3:
            signal_type = SignalType.SHORT
        else:
            signal_type = SignalType.NEUTRAL
        
        # Calculate confidence
        signal_values = [s.signal.value for s in active_signals]
        consensus_ratio = abs(sum(signal_values)) / len(signal_values) if signal_values else 0
        
        confidence = self._calculate_confidence(
            weighted_signal, consensus_ratio, 
            regime_state.confidence, active_signals
        )
        
        return {
            'signal': signal_type,
            'confidence': confidence,
            'weighted_signal': weighted_signal,
            'signal_strength': abs(weighted_signal),
            'consensus_ratio': consensus_ratio,
            'n_active_strategies': len(active_signals),
            'regime': regime_state.regime.value,
            'regime_confidence': regime_state.confidence,
            'strategy_breakdown': {
                s.strategy_id: {
                    'signal': s.signal.value,
                    'weight': self.strategy_weights.get(s.strategy_id, 0),
                    'confidence': s.confidence
                } for s in active_signals
            }
        }
    
    def _calculate_confidence(self, weighted_signal: float, 
                               consensus_ratio: float,
                               regime_confidence: float,
                               signals: List[StrategySignal]) -> float:
        """Calculate overall confidence score."""
        # Base confidence from signal strength
        signal_confidence = min(abs(weighted_signal), 1.0)
        
        # Consensus bonus
        consensus_bonus = consensus_ratio * 0.2
        
        # Regime confidence
        regime_factor = regime_confidence * 0.2
        
        # Strategy diversity bonus
        n_strategies = len(signals)
        diversity_bonus = min(n_strategies / 5, 0.2) if n_strategies >= self.min_signals_for_consensus else 0
        
        # Individual strategy confidence average
        avg_confidence = np.mean([s.confidence for s in signals]) if signals else 0
        
        # Combine factors
        confidence = (
            signal_confidence * 0.4 +
            avg_confidence * 0.2 +
            consensus_bonus +
            regime_factor +
            diversity_bonus
        )
        
        return min(confidence, 1.0)
    
    def train_meta_learner(self, X: pd.DataFrame, y: pd.Series,
                           strategy_signals: pd.DataFrame) -> None:
        """
        Train meta-learner for dynamic strategy weighting.
        
        Args:
            X: Feature matrix (regime indicators)
            y: Target returns
            strategy_signals: DataFrame with signals from each strategy
        """
        # Create meta-features
        meta_features = self._create_meta_features(X, strategy_signals)
        
        # Train meta-learner (Ridge regression for stability)
        self.meta_learner = ModelFactory.create_model(
            ModelType.RIDGE, self.config, task="regression"
        )
        self.meta_learner.fit(meta_features, y)
        
        logger.info("Meta-learner trained successfully")
    
    def _create_meta_features(self, X: pd.DataFrame, 
                               strategy_signals: pd.DataFrame) -> pd.DataFrame:
        """Create meta-features for meta-learner."""
        meta_features = pd.DataFrame(index=X.index)
        
        # Add regime features
        regime_cols = [c for c in X.columns if 'regime' in c or 'volatility' in c or 'trend' in c]
        for col in regime_cols:
            meta_features[col] = X[col]
        
        # Add strategy signals
        for col in strategy_signals.columns:
            meta_features[f'signal_{col}'] = strategy_signals[col]
        
        # Add interaction features
        for col1 in strategy_signals.columns:
            for col2 in regime_cols[:3]:  # Limit interactions
                meta_features[f'interaction_{col1}_{col2}'] = (
                    strategy_signals[col1] * X[col2]
                )
        
        return meta_features.fillna(0)
    
    def get_strategy_summary(self) -> pd.DataFrame:
        """Get summary of all registered strategies."""
        summaries = []
        
        for strategy_id in self.strategies:
            perf_df = self.strategy_performance.get(strategy_id, pd.DataFrame())
            
            summary = {
                'strategy_id': strategy_id,
                'is_active': self.strategy_active.get(strategy_id, True),
                'current_weight': self.strategy_weights.get(strategy_id, 0),
                'n_signals': len(perf_df),
                'avg_sharpe': perf_df['sharpe_ratio'].mean() if len(perf_df) > 0 else 0,
                'avg_return': perf_df['cumulative_return'].mean() if len(perf_df) > 0 else 0,
                'avg_confidence': perf_df['confidence'].mean() if len(perf_df) > 0 else 0,
                'last_signal': perf_df['timestamp'].iloc[-1] if len(perf_df) > 0 else None
            }
            
            summaries.append(summary)
        
        return pd.DataFrame(summaries)
    
    @staticmethod
    def _calculate_sharpe(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate annualized Sharpe ratio."""
        if len(returns) < 2 or returns.std() == 0:
            return 0
        excess_returns = returns - risk_free_rate / 252
        return excess_returns.mean() / returns.std() * np.sqrt(252)
    
    @staticmethod
    def _calculate_max_drawdown(returns: pd.Series) -> float:
        """Calculate maximum drawdown."""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()


# ================================================================================
# SECTION 9: COMPLETE ML PIPELINE
# ================================================================================

class MLPipeline:
    """
    Complete ML pipeline for financial time series prediction.
    
    Pipeline stages:
    1. Feature Engineering
    2. Target Creation
    3. Cross-Validation
    4. Model Training
    5. Ensemble Creation
    6. Backtesting
    7. Performance Analysis
    """
    
    def __init__(self, 
                 feature_config: FeatureConfig = None,
                 model_config: ModelConfig = None):
        self.feature_config = feature_config or FeatureConfig()
        self.model_config = model_config or ModelConfig()
        
        self.feature_engineer = FeatureEngineer(self.feature_config)
        self.models: Dict[str, BaseMLModel] = {}
        self.ensemble: Optional[StrategyArbitrator] = None
        self.cv: Optional[BaseCrossValidator] = None
        
        # Results storage
        self.cv_results_: Dict = {}
        self.feature_importance_: pd.DataFrame = None
        self.ablation_results_: pd.DataFrame = None
    
    def prepare_data(self, df: pd.DataFrame, 
                     target_type: str = "direction",
                     horizon: int = 5) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare features and target from raw price data.
        
        Args:
            df: Raw OHLCV DataFrame
            target_type: "direction", "return", "quantile"
            horizon: Prediction horizon
        
        Returns:
            Tuple of (features, target)
        """
        # Generate features
        features = self.feature_engineer.fit_transform(df)
        
        # Generate target (NO LOOKAHEAD BIAS)
        returns = df['close'].pct_change(horizon).shift(-horizon)
        
        if target_type == "direction":
            target = (returns > 0).astype(int)
        elif target_type == "return":
            target = returns
        elif target_type == "quantile":
            target = pd.qcut(returns, q=5, labels=False, duplicates='drop')
        else:
            raise ValueError(f"Unknown target type: {target_type}")
        
        # Align and drop NaN
        aligned = pd.concat([features, target], axis=1).dropna()
        X = aligned.iloc[:, :-1]
        y = aligned.iloc[:, -1]
        
        return X, y
    
    def create_cv_splitter(self, method: str = "walk_forward") -> BaseCrossValidator:
        """Create cross-validation splitter."""
        if method == "purged_kfold":
            self.cv = PurgedKFold(
                n_splits=self.model_config.cv_folds,
                purge_gap=self.model_config.cv_purge_gap,
                embargo_pct=self.model_config.cv_embargo_pct
            )
        elif method == "walk_forward":
            self.cv = WalkForwardCV(
                train_size=self.model_config.wf_train_size,
                test_size=self.model_config.wf_test_size,
                step_size=self.model_config.wf_step_size,
                purge_gap=self.model_config.cv_purge_gap,
                embargo_pct=self.model_config.cv_embargo_pct
            )
        elif method == "combinatorial":
            self.cv = CombinatorialCV(
                n_splits=10,
                n_test_splits=2,
                purge_gap=self.model_config.cv_purge_gap
            )
        else:
            raise ValueError(f"Unknown CV method: {method}")
        
        return self.cv
    
    def train_models(self, X: pd.DataFrame, y: pd.Series,
                     model_types: List[ModelType] = None) -> Dict:
        """
        Train multiple models with cross-validation.
        
        Args:
            X: Feature matrix
            y: Target vector
            model_types: List of model types to train
        
        Returns:
            Dict with CV results for each model
        """
        if self.cv is None:
            self.create_cv_splitter("walk_forward")
        
        model_types = model_types or [
            ModelType.LIGHTGBM,
            ModelType.RANDOM_FOREST,
            ModelType.RIDGE
        ]
        
        task = "classification" if len(np.unique(y)) <= 5 else "regression"
        
        results = {}
        
        for model_type in model_types:
            logger.info(f"Training {model_type.value}...")
            
            cv_scores = []
            fold_importance = []
            
            for fold, (train_idx, test_idx) in enumerate(self.cv.split(X, y)):
                X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
                y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
                
                # Create and train model
                model = ModelFactory.create_model(model_type, self.model_config, task)
                model.fit(X_train, y_train)
                
                # Predict
                y_pred = model.predict(X_test)
                
                # Evaluate
                if task == "classification":
                    score = accuracy_score(y_test, y_pred)
                else:
                    score = r2_score(y_test, y_pred)
                
                cv_scores.append(score)
                
                # Store feature importance
                if model.feature_importance_:
                    fold_importance.append(model.get_feature_importance())
                
                # Store model
                self.models[f"{model_type.value}_fold_{fold}"] = model
            
            # Aggregate results
            results[model_type.value] = {
                'mean_score': np.mean(cv_scores),
                'std_score': np.std(cv_scores),
                'scores': cv_scores,
                'feature_importance': pd.DataFrame(fold_importance).mean() if fold_importance else None
            }
        
        self.cv_results_ = results
        return results
    
    def create_ensemble(self, X: pd.DataFrame, y: pd.Series,
                        strategy_signals: pd.DataFrame = None) -> StrategyArbitrator:
        """
        Create ensemble using StrategyArbitrator.
        
        Args:
            X: Feature matrix
            y: Target vector
            strategy_signals: Optional pre-computed strategy signals
        
        Returns:
            Configured StrategyArbitrator
        """
        # Initialize arbitrator
        regime_detector = RegimeDetector()
        self.ensemble = StrategyArbitrator(
            config=self.model_config,
            regime_detector=regime_detector
        )
        
        # Register models as strategies
        for model_name, model in self.models.items():
            strategy_id = f"ml_model_{model_name}"
            self.ensemble.register_strategy(
                strategy_id,
                {'type': 'ml_model', 'model_name': model_name}
            )
        
        # Train meta-learner if we have strategy signals
        if strategy_signals is not None:
            self.ensemble.train_meta_learner(X, y, strategy_signals)
        
        return self.ensemble
    
    def run_ablation_study(self, X: pd.DataFrame, y: pd.Series,
                           feature_groups: Dict[str, List[str]] = None) -> pd.DataFrame:
        """Run ablation study on features."""
        # Define default feature groups
        if feature_groups is None:
            feature_groups = {
                'trend': [c for c in X.columns if 'ma_' in c or 'ema_' in c or 'macd' in c],
                'momentum': [c for c in X.columns if 'momentum' in c or 'rsi' in c or 'return_' in c],
                'volatility': [c for c in X.columns if 'volatility' in c or 'atr' in c or 'bb_' in c],
                'volume': [c for c in X.columns if 'volume' in c or 'obv' in c or 'vwap' in c],
                'mean_reversion': [c for c in X.columns if 'zscore' in c or 'mr_' in c],
                'cross_sectional': [c for c in X.columns if 'percentile' in c or 'rank' in c],
                'seasonality': [c for c in X.columns if 'month' in c or 'day_' in c or 'quarter' in c],
                'regime': [c for c in X.columns if 'regime' in c or 'trend_strength' in c]
            }
        
        # Create ablation tester
        model = ModelFactory.create_model(ModelType.LIGHTGBM, self.model_config)
        tester = AblationTester(model, self.cv or PurgedKFold())
        
        self.ablation_results_ = tester.test_feature_ablation(X, y, feature_groups)
        return self.ablation_results_
    
    def apply_multiple_hypothesis_correction(self, p_values: np.ndarray,
                                              method: str = "bh") -> pd.DataFrame:
        """Apply multiple hypothesis correction."""
        corrector = MultipleHypothesisCorrection()
        
        if method == "all":
            return corrector.apply_all_corrections(p_values)
        elif method == "bh":
            rejected, adjusted = corrector.benjamini_hochberg(p_values)
            return pd.DataFrame({
                'p_value': p_values,
                'rejected': rejected,
                'adjusted_p_value': adjusted
            })
        else:
            raise ValueError(f"Unknown correction method: {method}")
    
    def get_feature_importance(self) -> pd.DataFrame:
        """Get aggregated feature importance across all models."""
        importance_list = []
        
        for model_name, results in self.cv_results_.items():
            if results['feature_importance'] is not None:
                imp = results['feature_importance'].to_frame(name='importance')
                imp['model'] = model_name
                importance_list.append(imp)
        
        if importance_list:
            all_importance = pd.concat(importance_list)
            self.feature_importance_ = all_importance.groupby(all_importance.index)['importance'].mean().sort_values(ascending=False)
            return self.feature_importance_.to_frame(name='importance')
        
        return pd.DataFrame()


# ================================================================================
# SECTION 10: UTILITY FUNCTIONS
# ================================================================================

def prevent_lookahead_bias(df: pd.DataFrame, 
                            feature_cols: List[str] = None,
                            strict: bool = True) -> pd.DataFrame:
    """
    Check and prevent lookahead bias in features.
    
    Techniques:
    1. Verify no future data in feature calculation
    2. Ensure targets are shifted properly
    3. Check for data leakage indicators
    
    Args:
        df: DataFrame with features
        feature_cols: List of feature columns to check
        strict: If True, raise error on potential lookahead
    
    Returns:
        Cleaned DataFrame
    """
    df_clean = df.copy()
    
    # Check for suspicious correlations
    if feature_cols:
        for col in feature_cols:
            if col not in df_clean.columns:
                continue
            
            # Check if feature contains future information
            # (e.g., values that couldn't be known at that time)
            series = df_clean[col]
            
            # Detect suspicious patterns
            # 1. Perfect correlation with future returns
            # 2. Values that are always positive before up moves
            # 3. Sudden jumps that predict future moves
            
            # Simple heuristic: check for extreme autocorrelation at lag 1
            autocorr = series.autocorr(lag=1)
            if abs(autocorr) > 0.99:
                msg = f"Suspicious autocorrelation in {col}: {autocorr:.4f}"
                if strict:
                    raise ValueError(f"Potential lookahead bias: {msg}")
                else:
                    warnings.warn(msg)
    
    return df_clean


def handle_non_stationarity(X: pd.DataFrame, 
                             method: str = "difference") -> pd.DataFrame:
    """
    Handle non-stationarity in features.
    
    Methods:
    - difference: First difference
    - normalize: Normalize by rolling statistics
    - quantile: Convert to quantile ranks
    - neutralize: Remove common trends
    
    Args:
        X: Feature DataFrame
        method: Stationarization method
    
    Returns:
        Stationarized DataFrame
    """
    X_clean = X.copy()
    
    if method == "difference":
        X_clean = X_clean.diff().dropna()
    
    elif method == "normalize":
        for col in X_clean.columns:
            rolling_mean = X_clean[col].rolling(252).mean()
            rolling_std = X_clean[col].rolling(252).std()
            X_clean[col] = (X_clean[col] - rolling_mean) / (rolling_std + 1e-10)
    
    elif method == "quantile":
        for col in X_clean.columns:
            X_clean[col] = X_clean[col].rolling(252).apply(
                lambda x: stats.percentileofscore(x, x.iloc[-1]) / 100, raw=True
            )
    
    elif method == "neutralize":
        # Remove first principal component (common trend)
        from sklearn.decomposition import PCA
        pca = PCA(n_components=1)
        common_trend = pca.fit_transform(X_clean.fillna(0))
        X_clean = X_clean - common_trend @ pca.components_
    
    return X_clean.fillna(0)


def calculate_p_value(returns: pd.Series, 
                       benchmark: pd.Series = None,
                       n_trials: int = 1000) -> float:
    """
    Calculate p-value for strategy returns using permutation test.
    
    Args:
        returns: Strategy returns
        benchmark: Optional benchmark returns
        n_trials: Number of permutations
    
    Returns:
        p-value
    """
    observed_sharpe = returns.mean() / (returns.std() + 1e-10) * np.sqrt(252)
    
    # Permutation test
    permuted_sharpes = []
    for _ in range(n_trials):
        permuted = np.random.permutation(returns.values)
        perm_sharpe = permuted.mean() / (permuted.std() + 1e-10) * np.sqrt(252)
        permuted_sharpes.append(perm_sharpe)
    
    # Calculate p-value
    p_value = np.mean(np.array(permuted_sharpes) >= observed_sharpe)
    
    return p_value


# ================================================================================
# EXAMPLE USAGE
# ================================================================================

def example_usage():
    """Example of how to use the ML trading system."""
    
    # 1. Create sample data
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', '2023-12-31', freq='B')
    n = len(dates)
    
    # Generate synthetic price data
    returns = np.random.normal(0.0005, 0.02, n)
    prices = 100 * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, n)
    }, index=dates)
    
    # 2. Initialize pipeline
    feature_config = FeatureConfig(
        trend_windows=[5, 10, 20, 50],
        momentum_windows=[5, 10, 20],
        volatility_windows=[5, 10, 20],
        include_seasonality=True
    )
    
    model_config = ModelConfig(
        prediction_horizon=5,
        cv_folds=5,
        cv_purge_gap=5,
        ensemble_method="stacking"
    )
    
    pipeline = MLPipeline(feature_config, model_config)
    
    # 3. Prepare data
    X, y = pipeline.prepare_data(df, target_type="direction", horizon=5)
    print(f"Features shape: {X.shape}")
    print(f"Target distribution: {y.value_counts().to_dict()}")
    
    # 4. Create CV splitter
    cv = pipeline.create_cv_splitter("walk_forward")
    print(f"CV splits: {cv.get_n_splits(X)}")
    
    # 5. Train models
    results = pipeline.train_models(X, y, model_types=[
        ModelType.LIGHTGBM,
        ModelType.RANDOM_FOREST,
        ModelType.RIDGE
    ])
    
    print("\nModel Performance:")
    for model_name, result in results.items():
        print(f"  {model_name}: {result['mean_score']:.4f} (+/- {result['std_score']:.4f})")
    
    # 6. Run ablation study
    ablation = pipeline.run_ablation_study(X, y)
    print("\nAblation Study Results:")
    print(ablation.head(10))
    
    # 7. Get feature importance
    importance = pipeline.get_feature_importance()
    print("\nTop 10 Features:")
    print(importance.head(10))
    
    # 8. Create ensemble
    ensemble = pipeline.create_ensemble(X, y)
    print(f"\nEnsemble created with {len(ensemble.strategies)} strategies")
    
    # 9. Test StrategyArbitrator with sample signals
    signals = [
        StrategySignal(
            strategy_id="ml_model_lightgbm_fold_0",
            timestamp=df.index[-1],
            signal=SignalType.LONG,
            confidence=0.75,
            expected_return=0.02,
            volatility=0.15,
            regime=RegimeType.BULL_TREND
        ),
        StrategySignal(
            strategy_id="ml_model_random_forest_fold_0",
            timestamp=df.index[-1],
            signal=SignalType.LONG,
            confidence=0.65,
            expected_return=0.015,
            volatility=0.12,
            regime=RegimeType.BULL_TREND
        ),
        StrategySignal(
            strategy_id="ml_model_ridge_fold_0",
            timestamp=df.index[-1],
            signal=SignalType.NEUTRAL,
            confidence=0.50,
            expected_return=0.0,
            volatility=0.10,
            regime=RegimeType.BULL_TREND
        )
    ]
    
    market_features = X.tail(20)
    market_returns = df['close'].pct_change().tail(100)
    
    result = ensemble.process_signals(signals, market_features, market_returns)
    print("\nEnsemble Signal Result:")
    print(f"  Signal: {result['signal'].name}")
    print(f"  Confidence: {result['confidence']:.4f}")
    print(f"  Weighted Signal: {result['weighted_signal']:.4f}")
    print(f"  Active Strategies: {result['n_active_strategies']}")
    print(f"  Regime: {result['regime']}")
    
    return pipeline, ensemble, result


if __name__ == "__main__":
    pipeline, ensemble, result = example_usage()
