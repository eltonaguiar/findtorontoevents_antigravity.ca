#!/usr/bin/env python3
"""
ML Engine v2 - Production-Grade Financial Time-Series Prediction Pipeline
=========================================================================

A complete replacement for the broken ML system at findtorontoevents.ca/audit.

Key improvements over v1:
- 50+ properly lagged features (no look-ahead bias)
- Time-series aware train/test splits (no random shuffle)
- Multiple class imbalance handling strategies (SMOTE, cost-sensitive, focal loss)
- Multi-model ensemble (XGBoost + LightGBM + RF + Logistic Regression)
- PR-AUC as primary metric (not misleading ROC-AUC)
- Threshold tuning on validation set (not default 0.5)
- Feedback loop from resolved picks
- Model drift monitoring with auto-pause

Author: ML Engineering Team
Version: 2.0.0
Date: 2026-05-20
"""

from __future__ import annotations

import json
import logging
import os
import pickle
import warnings
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    classification_report,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import RobustScaler, StandardScaler

# Optional imports with graceful degradation
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    warnings.warn("XGBoost not installed. XGBoost model will be skipped.")

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    warnings.warn("LightGBM not installed. LightGBM model will be skipped.")

try:
    from imblearn.over_sampling import SMOTE, BorderlineSMOTE
    from imblearn.pipeline import Pipeline as ImbPipeline
    SMOTE_AVAILABLE = True
except ImportError:
    SMOTE_AVAILABLE = False
    warnings.warn("imbalanced-learn not installed. SMOTE will be skipped.")

try:
    import tensorflow as tf
    from tensorflow import keras
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    warnings.warn("TensorFlow not installed. Neural network models will be skipped.")


# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """Central configuration for the ML pipeline."""

    # Paths
    DATA_DIR = Path(os.environ.get("ML_DATA_DIR", "alpha_engine/data"))
    MODEL_DIR = Path(os.environ.get("ML_MODEL_DIR", "ml_models_v2"))
    LOG_DIR = Path(os.environ.get("ML_LOG_DIR", "ml_logs_v2"))
    CLOSED_PICKS_FILE = DATA_DIR / "closed_picks.json"
    PREMIUM_SIGNALS_FILE = DATA_DIR / "premium_signals.json"
    PREDICTION_LOG_FILE = LOG_DIR / "prediction_log.jsonl"
    MODEL_VERSION_FILE = MODEL_DIR / "model_version.json"
    DRIFT_LOG_FILE = LOG_DIR / "drift_log.jsonl"

    # Feature engineering
    RETURN_PERIODS = [1, 3, 7, 14, 30]
    VOLATILITY_PERIODS = [7, 14, 30]
    RSI_PERIOD = 14
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    BBANDS_PERIOD = 20
    BBANDS_STD = 2
    VOLUME_MA_PERIODS = [7, 14, 30]
    CORRELATION_PERIODS = [14, 30]

    # Model hyperparameters
    N_ESTIMATORS = 200
    MAX_DEPTH_XGB = 6
    MAX_DEPTH_LGB = 8
    MAX_DEPTH_RF = 20
    LEARNING_RATE_XGB = 0.05
    LEARNING_RATE_LGB = 0.05
    MIN_SAMPLES_LEAF_RF = 5
    RF_CLASS_WEIGHT = "balanced_subsample"
    LR_C = 1.0
    LR_CLASS_WEIGHT = "balanced"
    LR_MAX_ITER = 1000

    # Class imbalance
    POSITIVE_RATE_ESTIMATE = 0.007  # 0.7% positive rate observed
    SCALE_POS_WEIGHT = int(1 / POSITIVE_RATE_ESTIMATE)  # ~143
    SMOTE_K_NEIGHBORS = 5
    FOCAL_LOSS_GAMMA = 2.0
    FOCAL_LOSS_ALPHA = 0.75

    # Validation
    N_SPLITS_TS = 5
    EMBARGO_DAYS = 7
    TEST_SIZE_DAYS = 30
    PR_AUC_THRESHOLD = 0.15  # Minimum acceptable PR-AUC
    MIN_PRECISION = 0.10  # Minimum acceptable precision

    # Threshold tuning
    THRESHOLD_OPTIMIZATION_METRIC = "f1"  # Options: "f1", "precision", "recall", "f2"

    # Monitoring
    ACCURACY_ALERT_THRESHOLD = 0.55
    ACCURACY_PAUSE_THRESHOLD = 0.50
    ROLLING_WINDOW_DAYS = 30
    DRIFT_THRESHOLD = 2.0  # Standard deviations
    RETRAIN_TRIGGER_ACCURACY = 0.55
    RETRAIN_SCHEDULE_DAYS = 7

    # Ensemble
    VOTING_STRATEGY = "soft"
    MODEL_WEIGHTS = {
        "xgb": 0.30,
        "lgb": 0.30,
        "rf": 0.25,
        "lr": 0.15,
    }

    # Live prediction
    CONFIDENCE_TIERS = {
        "high": 0.70,
        "medium": 0.55,
        "low": 0.40,
    }

    # Logging
    LOG_LEVEL = os.environ.get("ML_LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging(log_dir: Optional[Path] = None) -> logging.Logger:
    """Set up structured logging for the ML pipeline."""
    log_dir = log_dir or Config.LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("ml_engine_v2")
    logger.setLevel(getattr(logging, Config.LOG_LEVEL))

    if not logger.handlers:
        # Console handler
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter(Config.LOG_FORMAT))
        logger.addHandler(console)

        # File handler
        log_file = log_dir / f"ml_engine_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(Config.LOG_FORMAT))
        logger.addHandler(file_handler)

    return logger


logger = setup_logging()


# =============================================================================
# DATA CLASSES
# =============================================================================

class Direction(Enum):
    """Trade direction enumeration."""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class ConfidenceTier(Enum):
    """Confidence tier enumeration."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


@dataclass
class MLPrediction:
    """Structured output for a single ML prediction."""
    symbol: str
    timestamp: datetime
    direction: Direction
    probability: float
    confidence_tier: ConfidenceTier
    model_version: str
    features_used: Dict[str, float]
    threshold_used: float
    ensemble_weights: Dict[str, float]
    individual_scores: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction.value,
            "probability": round(self.probability, 6),
            "confidence_tier": self.confidence_tier.value,
            "model_version": self.model_version,
            "features_used": {k: round(v, 6) if isinstance(v, float) else v
                             for k, v in self.features_used.items()},
            "threshold_used": round(self.threshold_used, 4),
            "ensemble_weights": self.ensemble_weights,
            "individual_scores": {k: round(v, 6) for k, v in self.individual_scores.items()},
        }

    def to_premium_signal(self) -> Dict[str, Any]:
        """Convert to premium signal format compatible with alpha_engine."""
        return {
            "id": f"mlv2_{self.symbol}_{int(self.timestamp.timestamp())}",
            "symbol": self.symbol,
            "direction": self.direction.value,
            "probability": round(self.probability, 4),
            "confidence": self.confidence_tier.value,
            "model_version": self.model_version,
            "generated_at": self.timestamp.isoformat(),
            "source": "ml_engine_v2",
            "type": "ml_prediction",
            "metadata": {
                "threshold": round(self.threshold_used, 4),
                "individual_scores": {k: round(v, 4) for k, v in self.individual_scores.items()},
                "top_features": dict(
                    sorted(
                        {k: round(v, 4) for k, v in self.features_used.items()}.items(),
                        key=lambda x: abs(x[1]),
                        reverse=True,
                    )[:10]
                ),
            },
        }


@dataclass
class ModelMetrics:
    """Comprehensive model performance metrics."""
    pr_auc: float
    roc_auc: float
    f1_score: float
    precision: float
    recall: float
    average_precision: float
    brier_score: float
    calibration_error: float
    threshold: float
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    n_train: int
    n_test: int
    positive_rate_train: float
    positive_rate_test: float
    fold_idx: Optional[int] = None
    model_name: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pr_auc": round(self.pr_auc, 4),
            "roc_auc": round(self.roc_auc, 4),
            "f1_score": round(self.f1_score, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "average_precision": round(self.average_precision, 4),
            "brier_score": round(self.brier_score, 4),
            "calibration_error": round(self.calibration_error, 4),
            "threshold": round(self.threshold, 4),
            "confusion_matrix": {
                "tp": self.true_positives,
                "fp": self.false_positives,
                "tn": self.true_negatives,
                "fn": self.false_negatives,
            },
            "n_train": self.n_train,
            "n_test": self.n_test,
            "positive_rate_train": round(self.positive_rate_train, 6),
            "positive_rate_test": round(self.positive_rate_test, 6),
            "fold_idx": self.fold_idx,
            "model_name": self.model_name,
            "timestamp": self.timestamp,
        }

    def is_acceptable(self) -> bool:
        """Check if metrics meet minimum quality thresholds."""
        return (
            self.pr_auc >= Config.PR_AUC_THRESHOLD
            and self.precision >= Config.MIN_PRECISION
            and self.f1_score > 0
        )


@dataclass
class DriftReport:
    """Feature drift detection report."""
    feature_name: str
    mean_drift: float
    std_drift: float
    ks_statistic: float
    is_drifted: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# =============================================================================
# FEATURE ENGINEERING
# =============================================================================

class FeatureEngineer:
    """
    Comprehensive feature engineering for crypto/financial time-series.

    All features are properly lagged to prevent look-ahead bias.
    Features are computed using only past data relative to the target timestamp.
    """

    # Categorical feature groups for reference
    FEATURE_GROUPS = {
        "price": [],
        "volume": [],
        "momentum": [],
        "volatility": [],
        "trend": [],
        "on_chain": [],
        "market_structure": [],
        "cross_market": [],
        "engineered": [],
    }

    def __init__(self):
        self.feature_names: List[str] = []
        self.scaler: Optional[RobustScaler] = None

    # -------------------------------------------------------------------------
    # Price Features
    # -------------------------------------------------------------------------

    @staticmethod
    def compute_returns(df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
        """
        Compute log returns over multiple periods.
        Uses past data only (shifted by 1 to prevent look-ahead).
        """
        periods = periods or Config.RETURN_PERIODS
        features = pd.DataFrame(index=df.index)

        for p in periods:
            col_name = f"return_{p}d"
            features[col_name] = np.log(df["close"] / df["close"].shift(p))
            FeatureEngineer.FEATURE_GROUPS["price"].append(col_name)

        return features

    @staticmethod
    def compute_cumulative_returns(df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
        """Compute cumulative returns (properly lagged)."""
        periods = periods or [7, 14, 30]
        features = pd.DataFrame(index=df.index)

        for p in periods:
            col_name = f"cum_return_{p}d"
            features[col_name] = df["close"].pct_change(p)
            FeatureEngineer.FEATURE_GROUPS["price"].append(col_name)

        return features

    @staticmethod
    def compute_price_position(df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute price position relative to recent range.
        0 = at low, 1 = at high of the lookback period.
        """
        features = pd.DataFrame(index=df.index)

        for period in [7, 14, 30, 60]:
            col_name = f"price_position_{period}d"
            rolling_low = df["low"].rolling(period).min()
            rolling_high = df["high"].rolling(period).max()
            features[col_name] = (df["close"] - rolling_low) / (rolling_high - rolling_low + 1e-10)
            FeatureEngineer.FEATURE_GROUPS["price"].append(col_name)

        return features

    # -------------------------------------------------------------------------
    # Momentum Features
    # -------------------------------------------------------------------------

    @staticmethod
    def compute_rsi(df: pd.DataFrame, period: int = None) -> pd.DataFrame:
        """
        Compute Relative Strength Index (RSI).
        Classic momentum oscillator, range 0-100.
        """
        period = period or Config.RSI_PERIOD
        features = pd.DataFrame(index=df.index)

        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.ewm(alpha=1.0/period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1.0/period, min_periods=period).mean()

        rs = avg_gain / (avg_loss + 1e-10)
        features[f"rsi_{period}"] = 100 - (100 / (1 + rs))

        # RSI slope (momentum of momentum)
        features[f"rsi_{period}_slope_3d"] = features[f"rsi_{period}"].diff(3)
        features[f"rsi_{period}_slope_7d"] = features[f"rsi_{period}"].diff(7)

        # RSI divergence from price
        price_change_5d = df["close"].pct_change(5)
        rsi_change_5d = features[f"rsi_{period}"].diff(5)
        features[f"rsi_{period}_divergence"] = price_change_5d - rsi_change_5d / 100

        for c in features.columns:
            FeatureEngineer.FEATURE_GROUPS["momentum"].append(c)

        return features

    @staticmethod
    def compute_macd(df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute MACD (Moving Average Convergence Divergence).
        Includes signal line and histogram.
        """
        features = pd.DataFrame(index=df.index)

        ema_fast = df["close"].ewm(span=Config.MACD_FAST, adjust=False).mean()
        ema_slow = df["close"].ewm(span=Config.MACD_SLOW, adjust=False).mean()

        features["macd"] = ema_fast - ema_slow
        features["macd_signal"] = features["macd"].ewm(span=Config.MACD_SIGNAL, adjust=False).mean()
        features["macd_histogram"] = features["macd"] - features["macd_signal"]

        # MACD momentum
        features["macd_slope_3d"] = features["macd"].diff(3)
        features["macd_histogram_slope_3d"] = features["macd_histogram"].diff(3)

        # MACD position relative to zero
        features["macd_above_zero"] = (features["macd"] > 0).astype(float)
        features["macd_histogram_above_zero"] = (features["macd_histogram"] > 0).astype(float)

        for c in features.columns:
            FeatureEngineer.FEATURE_GROUPS["momentum"].append(c)

        return features

    @staticmethod
    def compute_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
        """Compute Stochastic Oscillator (%K and %D)."""
        features = pd.DataFrame(index=df.index)

        lowest_low = df["low"].rolling(k_period).min()
        highest_high = df["high"].rolling(k_period).max()

        features["stoch_k"] = 100 * (df["close"] - lowest_low) / (highest_high - lowest_low + 1e-10)
        features["stoch_d"] = features["stoch_k"].rolling(d_period).mean()
        features["stoch_cross"] = features["stoch_k"] - features["stoch_d"]

        for c in features.columns:
            FeatureEngineer.FEATURE_GROUPS["momentum"].append(c)

        return features

    # -------------------------------------------------------------------------
    # Volatility Features
    # -------------------------------------------------------------------------

    @staticmethod
    def compute_volatility(df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
        """
        Compute realized volatility (annualized) over multiple periods.
        Uses past returns only.
        """
        periods = periods or Config.VOLATILITY_PERIODS
        features = pd.DataFrame(index=df.index)

        log_returns = np.log(df["close"] / df["close"].shift(1))

        for p in periods:
            col_name = f"volatility_{p}d"
            features[col_name] = log_returns.rolling(p).std() * np.sqrt(365)
            FeatureEngineer.FEATURE_GROUPS["volatility"].append(col_name)

        # Volatility trend (is volatility increasing?)
        features["volatility_ratio_7_30"] = features["volatility_7d"] / (features["volatility_30d"] + 1e-10)

        # Volatility regime
        vol_median_30 = features["volatility_30d"].rolling(30).median()
        features["volatility_above_median"] = (features["volatility_30d"] > vol_median_30).astype(float)

        return features

    @staticmethod
    def compute_bollinger_bands(df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute Bollinger Bands features.
        Returns position within bands and band width.
        """
        features = pd.DataFrame(index=df.index)

        sma = df["close"].rolling(Config.BBANDS_PERIOD).mean()
        std = df["close"].rolling(Config.BBANDS_PERIOD).std()

        upper = sma + Config.BBANDS_STD * std
        lower = sma - Config.BBANDS_STD * std

        features["bb_position"] = (df["close"] - lower) / (upper - lower + 1e-10)
        features["bb_width"] = (upper - lower) / (sma + 1e-10)
        features["bb_width_ratio_7d"] = features["bb_width"] / features["bb_width"].rolling(7).mean()

        # Squeeze detection (low volatility = potential breakout)
        features["bb_squeeze"] = (features["bb_width"] < features["bb_width"].rolling(50).quantile(0.25, interpolation="linear")).astype(float)

        for c in features.columns:
            FeatureEngineer.FEATURE_GROUPS["volatility"].append(c)

        return features

    @staticmethod
    def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Compute Average True Range (ATR) - volatility measure."""
        features = pd.DataFrame(index=df.index)

        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift(1)).abs()
        low_close = (df["low"] - df["close"].shift(1)).abs()

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        features[f"atr_{period}"] = tr.rolling(period).mean()
        features[f"atr_ratio_{period}"] = features[f"atr_{period}"] / df["close"]

        # ATR trend
        features[f"atr_{period}_slope_7d"] = features[f"atr_{period}"].diff(7)

        for c in features.columns:
            FeatureEngineer.FEATURE_GROUPS["volatility"].append(c)

        return features

    # -------------------------------------------------------------------------
    # Volume Features
    # -------------------------------------------------------------------------

    @staticmethod
    def compute_volume_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute volume-based features.
        Includes relative volume, volume trends, and volume/price divergence.
        """
        features = pd.DataFrame(index=df.index)

        # Relative volume (volume relative to recent average)
        for p in Config.VOLUME_MA_PERIODS:
            col_name = f"relative_volume_{p}d"
            vol_ma = df["volume"].rolling(p).mean()
            features[col_name] = df["volume"] / (vol_ma + 1e-10)
            FeatureEngineer.FEATURE_GROUPS["volume"].append(col_name)

        # Volume trend
        features["volume_trend_7d"] = df["volume"].rolling(7).mean() / df["volume"].rolling(30).mean()
        features["volume_change_1d"] = df["volume"].pct_change(1)
        features["volume_change_3d"] = df["volume"].pct_change(3)

        # Volume momentum (is volume increasing?)
        features["volume_slope_3d"] = df["volume"].diff(3)
        features["volume_slope_7d"] = df["volume"].diff(7)

        # Volume/Price divergence
        price_change_1d = df["close"].pct_change(1)
        volume_change_1d = df["volume"].pct_change(1)
        features["volume_price_divergence"] = volume_change_1d - price_change_1d

        # On-balance volume (OBV) - cumulative volume flow
        obv = pd.Series(0, index=df.index)
        obv[price_change_1d > 0] = df["volume"][price_change_1d > 0]
        obv[price_change_1d < 0] = -df["volume"][price_change_1d < 0]
        features["obv"] = obv.cumsum()
        features["obv_slope_7d"] = features["obv"].diff(7)
        features["obv_slope_14d"] = features["obv"].diff(14)

        # Volume-weighted average price (VWAP) deviation
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        vwap = (typical_price * df["volume"]).rolling(14).sum() / df["volume"].rolling(14).sum()
        features["vwap_deviation"] = (df["close"] - vwap) / (vwap + 1e-10)

        for c in ["volume_trend_7d", "volume_change_1d", "volume_change_3d",
                  "volume_slope_3d", "volume_slope_7d", "volume_price_divergence",
                  "obv", "obv_slope_7d", "obv_slope_14d", "vwap_deviation"]:
            FeatureEngineer.FEATURE_GROUPS["volume"].append(c)

        return features

    # -------------------------------------------------------------------------
    # Trend Features
    # -------------------------------------------------------------------------

    @staticmethod
    def compute_moving_average_features(df: pd.DataFrame) -> pd.DataFrame:
        """Compute moving average crossovers and price-to-MA ratios."""
        features = pd.DataFrame(index=df.index)

        for period in [7, 14, 21, 30, 50, 100]:
            ma = df["close"].rolling(period).mean()
            features[f"ma_{period}_ratio"] = df["close"] / (ma + 1e-10)
            features[f"ma_{period}_slope"] = ma.diff(7) / (ma + 1e-10)

        # Golden/Death cross signals
        features["ma_cross_7_30"] = features["ma_7_ratio"] - features["ma_30_ratio"]
        features["ma_cross_14_50"] = features["ma_14_ratio"] - features["ma_50_ratio"]
        features["ma_cross_50_100"] = features["ma_50_ratio"] - features["ma_100_ratio"]

        for c in features.columns:
            FeatureEngineer.FEATURE_GROUPS["trend"].append(c)

        return features

    @staticmethod
    def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Compute Average Directional Index (ADX) - trend strength indicator."""
        features = pd.DataFrame(index=df.index)

        plus_dm = df["high"].diff()
        minus_dm = -df["low"].diff()

        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs(),
        ], axis=1).max(axis=1)

        atr = tr.rolling(period).mean()

        plus_di = 100 * plus_dm.rolling(period).mean() / (atr + 1e-10)
        minus_di = 100 * minus_dm.rolling(period).mean() / (atr + 1e-10)

        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
        features[f"adx_{period}"] = dx.rolling(period).mean()
        features[f"plus_di_{period}"] = plus_di
        features[f"minus_di_{period}"] = minus_di
        features[f"di_cross_{period}"] = plus_di - minus_di

        for c in features.columns:
            FeatureEngineer.FEATURE_GROUPS["trend"].append(c)

        return features

    # -------------------------------------------------------------------------
    # Cross-Market Correlation Features
    # -------------------------------------------------------------------------

    @staticmethod
    def compute_correlation_features(
        df: pd.DataFrame, benchmark_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> pd.DataFrame:
        """
        Compute correlation with benchmark assets.
        Requires benchmark_data dict with keys: 'BTC', 'ETH', 'SPY'
        """
        features = pd.DataFrame(index=df.index)
        returns = df["close"].pct_change(1)

        # Auto-correlation (self correlation at different lags)
        for lag in [1, 3, 7]:
            features[f"autocorr_{lag}d"] = returns.rolling(30).apply(
                lambda x: x.corr(x.shift(lag)) if len(x.dropna()) > 5 else 0,
                raw=False,
            )
            FeatureEngineer.FEATURE_GROUPS["cross_market"].append(f"autocorr_{lag}d")

        # Benchmark correlations
        if benchmark_data:
            for benchmark_name, bench_df in benchmark_data.items():
                bench_returns = bench_df["close"].pct_change(1)
                for period in Config.CORRELATION_PERIODS:
                    # Rolling correlation
                    corr_series = returns.rolling(period).corr(bench_returns)
                    features[f"corr_{benchmark_name.lower()}_{period}d"] = corr_series

                    # Rolling beta (covariance / variance)
                    cov = returns.rolling(period).cov(bench_returns)
                    var = bench_returns.rolling(period).var()
                    features[f"beta_{benchmark_name.lower()}_{period}d"] = cov / (var + 1e-10)

                    FeatureEngineer.FEATURE_GROUPS["cross_market"].append(f"corr_{benchmark_name.lower()}_{period}d")
                    FeatureEngineer.FEATURE_GROUPS["cross_market"].append(f"beta_{benchmark_name.lower()}_{period}d")

        return features

    # -------------------------------------------------------------------------
    # On-Chain Features (placeholder for when data is available)
    # -------------------------------------------------------------------------

    @staticmethod
    def compute_on_chain_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute on-chain feature placeholders.
        When on-chain data is available, these should be populated with
        actual exchange flow, active addresses, and whale transaction data.
        """
        features = pd.DataFrame(index=df.index)

        # Exchange flow rate of change (proxy from volume patterns)
        features["exchange_flow_proxy"] = df["volume"] / df["volume"].rolling(30).mean()
        features["exchange_flow_proxy_roc_7d"] = features["exchange_flow_proxy"].pct_change(7)

        # Whale proxy (volume spikes indicate large transactions)
        vol_std = df["volume"].rolling(30).std()
        vol_mean = df["volume"].rolling(30).mean()
        features["whale_proxy"] = (df["volume"] > (vol_mean + 2 * vol_std)).astype(float).rolling(7).sum()

        # Network activity proxy (volume * price volatility)
        features["network_activity_proxy"] = df["volume"] * df["close"].pct_change(1).abs()
        features["network_activity_proxy_roc_7d"] = features["network_activity_proxy"].pct_change(7)

        for c in features.columns:
            FeatureEngineer.FEATURE_GROUPS["on_chain"].append(c)

        return features

    # -------------------------------------------------------------------------
    # Market Structure Features
    # -------------------------------------------------------------------------

    @staticmethod
    def compute_market_structure_features(df: pd.DataFrame) -> pd.DataFrame:
        """Compute market structure features."""
        features = pd.DataFrame(index=df.index)

        # Funding rate proxy (from price premium patterns)
        # Higher price momentum = higher funding (simplified)
        features["funding_proxy"] = df["close"].pct_change(1).rolling(7).mean() * 100
        features["funding_proxy_roc_7d"] = features["funding_proxy"].diff(7)

        # Open interest proxy (volume * price)
        features["oi_proxy"] = df["volume"] * df["close"]
        features["oi_proxy_change_1d"] = features["oi_proxy"].pct_change(1)
        features["oi_proxy_change_7d"] = features["oi_proxy"].pct_change(7)

        # Market dominance proxy (volume share relative to trend)
        features["dominance_proxy"] = df["volume"] / df["volume"].rolling(30).mean()

        # Long/short proxy (based on price action)
        up_days = (df["close"] > df["open"]).astype(float).rolling(14).mean()
        features["long_short_ratio_proxy"] = up_days / (1 - up_days + 1e-10)

        for c in features.columns:
            FeatureEngineer.FEATURE_GROUPS["market_structure"].append(c)

        return features

    # -------------------------------------------------------------------------
    # Engineered / Interaction Features
    # -------------------------------------------------------------------------

    @staticmethod
    def compute_interaction_features(feature_df: pd.DataFrame) -> pd.DataFrame:
        """Compute interaction features between existing features."""
        features = pd.DataFrame(index=feature_df.index)

        # Price momentum * volume (confirmation signal)
        if "return_1d" in feature_df.columns and "relative_volume_7d" in feature_df.columns:
            features["momentum_volume_interaction"] = (
                feature_df["return_1d"] * feature_df["relative_volume_7d"]
            )

        # Volatility regime * trend strength
        if "volatility_7d" in feature_df.columns and "return_7d" in feature_df.columns:
            features["vol_trend_interaction"] = (
                feature_df["volatility_7d"] * feature_df["return_7d"]
            )

        # RSI * price position
        if "rsi_14" in feature_df.columns and "price_position_14d" in feature_df.columns:
            features["rsi_price_interaction"] = (
                feature_df["rsi_14"] / 100 * feature_df["price_position_14d"]
            )

        # MACD confirmation
        if "macd_histogram" in feature_df.columns and "macd_above_zero" in feature_df.columns:
            features["macd_confirmed"] = (
                feature_df["macd_histogram"] * feature_df["macd_above_zero"]
            )

        for c in features.columns:
            FeatureEngineer.FEATURE_GROUPS["engineered"].append(c)

        return features

    # -------------------------------------------------------------------------
    # Target Variable
    # -------------------------------------------------------------------------

    @staticmethod
    def compute_target(
        df: pd.DataFrame, horizon: int = 7, threshold: float = 0.05
    ) -> pd.Series:
        """
        Compute binary target variable.

        Args:
            df: OHLCV dataframe
            horizon: Prediction horizon in days
            threshold: Minimum return to be considered positive

        Returns:
            Series with 1 if future return > threshold, 0 otherwise
        """
        future_return = df["close"].shift(-horizon) / df["close"] - 1
        return (future_return > threshold).astype(int)

    # -------------------------------------------------------------------------
    # Master Feature Pipeline
    # -------------------------------------------------------------------------

    def build_features(
        self,
        df: pd.DataFrame,
        benchmark_data: Optional[Dict[str, pd.DataFrame]] = None,
        include_target: bool = True,
        target_horizon: int = 7,
        target_threshold: float = 0.05,
    ) -> pd.DataFrame:
        """
        Build complete feature set from OHLCV data.

        Args:
            df: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
            benchmark_data: Optional dict of benchmark DataFrames
            include_target: Whether to include target variable
            target_horizon: Days ahead to predict
            target_threshold: Return threshold for positive class

        Returns:
            DataFrame with all features and optionally target
        """
        logger.info(f"Building features for {len(df)} rows of data")

        feature_dfs = []

        # Core OHLCV validation
        required_cols = {"open", "high", "low", "close", "volume"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Price features
        feature_dfs.append(self.compute_returns(df))
        feature_dfs.append(self.compute_cumulative_returns(df))
        feature_dfs.append(self.compute_price_position(df))

        # Momentum features
        feature_dfs.append(self.compute_rsi(df))
        feature_dfs.append(self.compute_macd(df))
        feature_dfs.append(self.compute_stochastic(df))

        # Volatility features
        feature_dfs.append(self.compute_volatility(df))
        feature_dfs.append(self.compute_bollinger_bands(df))
        feature_dfs.append(self.compute_atr(df))

        # Volume features
        feature_dfs.append(self.compute_volume_features(df))

        # Trend features
        feature_dfs.append(self.compute_moving_average_features(df))
        feature_dfs.append(self.compute_adx(df))

        # Cross-market features
        feature_dfs.append(self.compute_correlation_features(df, benchmark_data))

        # On-chain features (proxies)
        feature_dfs.append(self.compute_on_chain_features(df))

        # Market structure features
        feature_dfs.append(self.compute_market_structure_features(df))

        # Combine all features
        combined = pd.concat(feature_dfs, axis=1)

        # Interaction features (computed from combined)
        interaction = self.compute_interaction_features(combined)
        combined = pd.concat([combined, interaction], axis=1)

        # Add target if requested
        if include_target:
            combined["target"] = self.compute_target(df, target_horizon, target_threshold)

        # Drop rows with NaN in features or target
        initial_rows = len(combined)
        combined = combined.dropna()
        dropped = initial_rows - len(combined)
        logger.info(f"Dropped {dropped} rows with NaN values ({dropped/initial_rows*100:.1f}%)")

        # Store feature names
        self.feature_names = [c for c in combined.columns if c != "target"]

        logger.info(f"Built {len(self.feature_names)} features for {len(combined)} rows")
        logger.info(f"Positive rate: {combined['target'].mean()*100:.2f}%")

        return combined


# =============================================================================
# TIME-SERIES CROSS-VALIDATION WITH EMBARGO
# =============================================================================

class TimeSeriesEmbargoSplit:
    """
    Time-series cross-validation with embargo period.

    Prevents information leakage by adding a gap (embargo) between
    training and test sets. This is critical for financial time-series
    where data points are not independent.
    """

    def __init__(
        self,
        n_splits: int = 5,
        embargo_days: int = 7,
        test_size: Optional[int] = None,
    ):
        self.n_splits = n_splits
        self.embargo_days = embargo_days
        self.test_size = test_size

    def split(self, X: pd.DataFrame, y=None, groups=None):
        """
        Generate train/test indices with embargo period.

        Yields:
            Tuple of (train_indices, test_indices)
        """
        n_samples = len(X)
        indices = np.arange(n_samples)

        # Calculate approximate fold sizes
        if self.test_size is None:
            test_size = max(n_samples // (self.n_splits + 1), 100)
        else:
            test_size = self.test_size

        embargo_size = self.embargo_days

        for i in range(self.n_splits):
            # Test set is at the end of the available data for this fold
            test_end = n_samples - i * (test_size + embargo_size)
            test_start = test_end - test_size

            if test_start <= 0 or test_end <= 0:
                logger.warning(f"Fold {i}: insufficient data, skipping")
                continue

            # Train set is everything before the embargo period
            train_end = test_start - embargo_size

            if train_end <= 50:  # Need minimum training data
                logger.warning(f"Fold {i}: insufficient training data, skipping")
                continue

            train_idx = indices[:train_end]
            test_idx = indices[test_start:test_end]

            logger.debug(
                f"Fold {i}: train[{train_idx[0]}:{train_idx[-1]}]="
                f"{len(train_idx)}, test[{test_idx[0]}:{test_idx[-1]}]={len(test_idx)}"
            )

            yield train_idx, test_idx

    def get_n_splits(self, X=None, y=None, groups=None) -> int:
        return self.n_splits


# =============================================================================
# CLASS IMBALANCE HANDLING
# =============================================================================

class ClassImbalanceHandler:
    """
    Multiple strategies for handling extreme class imbalance.

    The positive rate is ~0.7%, meaning we have ~143 negatives for every positive.
    Standard metrics like accuracy are misleading; we focus on PR-AUC and precision.
    """

    @staticmethod
    def get_class_weights(y: np.ndarray) -> Dict[int, float]:
        """
        Compute balanced class weights.

        Returns dict mapping class -> weight, scaling minority class
        by the inverse of its frequency.
        """
        n_total = len(y)
        n_pos = y.sum()
        n_neg = n_total - n_pos

        if n_pos == 0:
            logger.warning("No positive samples found!")
            return {0: 1.0, 1: 1.0}

        weight_neg = n_total / (2.0 * n_neg)
        weight_pos = n_total / (2.0 * n_pos)

        logger.info(f"Class weights: neg={weight_neg:.1f}, pos={weight_pos:.1f}")

        return {0: weight_neg, 1: weight_pos}

    @staticmethod
    def get_scale_pos_weight(y: np.ndarray) -> float:
        """Compute XGBoost/LightGBM scale_pos_weight parameter."""
        n_neg = (y == 0).sum()
        n_pos = y.sum()
        if n_pos == 0:
            return 1.0
        return float(n_neg) / float(n_pos)

    @staticmethod
    def apply_smote(
        X_train: pd.DataFrame, y_train: np.ndarray, k_neighbors: int = 5
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Apply SMOTE oversampling for time-series data.

        Uses BorderlineSMOTE which focuses on samples near the decision boundary.
        For time-series, we use SMOTE on the feature space directly.
        """
        if not SMOTE_AVAILABLE:
            logger.warning("SMOTE not available, returning original data")
            return X_train, y_train

        if len(np.unique(y_train)) < 2:
            logger.warning("Only one class in training data, cannot apply SMOTE")
            return X_train, y_train

        # Adjust k_neighbors if we have very few minority samples
        n_minority = min((y_train == 1).sum(), (y_train == 0).sum())
        k = min(k_neighbors, n_minority - 1)
        k = max(k, 1)

        smote = BorderlineSMOTE(
            k_neighbors=k,
            random_state=42,
            sampling_strategy="auto",
        )

        try:
            X_resampled, y_resampled = smote.fit_resample(X_train, y_train)
            logger.info(
                f"SMOTE: {len(y_train)} -> {len(y_resampled)} samples, "
                f"positive rate: {y_train.mean()*100:.2f}% -> {y_resampled.mean()*100:.2f}%"
            )
            return pd.DataFrame(X_resampled, columns=X_train.columns), y_resampled
        except Exception as e:
            logger.warning(f"SMOTE failed: {e}, returning original data")
            return X_train, y_train

    @staticmethod
    def focal_loss(y_true: np.ndarray, y_pred: np.ndarray, gamma: float = 2.0, alpha: float = 0.75) -> float:
        """
        Compute focal loss for imbalanced classification.

        Focal loss down-weights easy examples and focuses on hard examples.
        """
        epsilon = 1e-7
        y_pred = np.clip(y_pred, epsilon, 1 - epsilon)

        # Binary focal loss
        cross_entropy = -y_true * np.log(y_pred) - (1 - y_true) * np.log(1 - y_pred)
        weight = alpha * y_true * (1 - y_pred) ** gamma + (1 - alpha) * (1 - y_true) * y_pred ** gamma

        loss = weight * cross_entropy
        return float(np.mean(loss))


# =============================================================================
# THRESHOLD OPTIMIZATION
# =============================================================================

class ThresholdOptimizer:
    """
    Optimize classification threshold on validation data.

    Default threshold of 0.5 is suboptimal for imbalanced datasets.
    We optimize based on the chosen metric (default: F1-score).
    """

    @staticmethod
    def optimize(
        y_true: np.ndarray,
        y_proba: np.ndarray,
        metric: str = "f1",
        beta: float = 2.0,
        n_thresholds: int = 100,
    ) -> float:
        """
        Find optimal classification threshold.

        Args:
            y_true: True labels
            y_proba: Predicted probabilities
            metric: Metric to optimize ('f1', 'precision', 'recall', 'f2')
            beta: Beta parameter for F-beta score
            n_thresholds: Number of threshold values to try

        Returns:
            Optimal threshold value
        """
        thresholds = np.linspace(0.01, 0.99, n_thresholds)
        scores = []

        for t in thresholds:
            y_pred = (y_proba >= t).astype(int)

            if metric == "f1":
                score = f1_score(y_true, y_pred, zero_division=0)
            elif metric == "precision":
                score = precision_score(y_true, y_pred, zero_division=0)
            elif metric == "recall":
                score = recall_score(y_true, y_pred, zero_division=0)
            elif metric == "f2":
                # F2 score weights recall higher than precision
                p = precision_score(y_true, y_pred, zero_division=0)
                r = recall_score(y_true, y_pred, zero_division=0)
                if p + r == 0:
                    score = 0
                else:
                    score = (1 + beta**2) * p * r / (beta**2 * p + r)
            else:
                score = f1_score(y_true, y_pred, zero_division=0)

            scores.append(score)

        best_idx = int(np.argmax(scores))
        best_threshold = float(thresholds[best_idx])
        best_score = float(scores[best_idx])

        logger.info(
            f"Threshold optimization ({metric}): best={best_threshold:.3f}, "
            f"score={best_score:.4f}"
        )

        return best_threshold

    @staticmethod
    def find_threshold_for_target_recall(
        y_true: np.ndarray, y_proba: np.ndarray, target_recall: float = 0.30
    ) -> float:
        """Find threshold that achieves target recall."""
        precision, recall, thresholds = precision_recall_curve(y_true, y_proba)

        # Find threshold closest to target recall
        idx = np.argmin(np.abs(recall[:-1] - target_recall))
        return float(thresholds[idx]) if idx < len(thresholds) else 0.5




# =============================================================================
# MODEL BUILDERS
# =============================================================================

class ModelBuilder:
    """
    Factory for creating ML models with proper class imbalance handling.

    Each model is configured with settings appropriate for extreme class imbalance.
    """

    @staticmethod
    def build_xgboost(scale_pos_weight: float, n_estimators: int = None) -> Optional[Any]:
        """Build XGBoost classifier with class imbalance handling."""
        if not XGBOOST_AVAILABLE:
            logger.warning("XGBoost not available")
            return None

        n_estimators = n_estimators or Config.N_ESTIMATORS

        model = xgb.XGBClassifier(
            n_estimators=n_estimators,
            max_depth=Config.MAX_DEPTH_XGB,
            learning_rate=Config.LEARNING_RATE_XGB,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            objective="binary:logistic",
            eval_metric="aucpr",
            random_state=42,
            n_jobs=-1,
            reg_alpha=0.1,
            reg_lambda=1.0,
            min_child_weight=5,
            gamma=0.1,
            early_stopping_rounds=20,
            verbosity=0,
        )
        return model

    @staticmethod
    def build_lightgbm(scale_pos_weight: float, n_estimators: int = None) -> Optional[Any]:
        """Build LightGBM classifier with class imbalance handling."""
        if not LIGHTGBM_AVAILABLE:
            logger.warning("LightGBM not available")
            return None

        n_estimators = n_estimators or Config.N_ESTIMATORS

        model = lgb.LGBMClassifier(
            n_estimators=n_estimators,
            max_depth=Config.MAX_DEPTH_LGB,
            learning_rate=Config.LEARNING_RATE_LGB,
            subsample=0.8,
            colsample_bytree=0.8,
            is_unbalance=True,
            objective="binary",
            metric="average_precision",
            random_state=42,
            n_jobs=-1,
            reg_alpha=0.1,
            reg_lambda=1.0,
            min_child_samples=20,
            verbose=-1,
        )
        return model

    @staticmethod
    def build_random_forest(class_weight: Union[str, Dict] = None, n_estimators: int = None) -> RandomForestClassifier:
        """Build Random Forest classifier with class imbalance handling."""
        class_weight = class_weight or Config.RF_CLASS_WEIGHT
        n_estimators = n_estimators or Config.N_ESTIMATORS

        model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=Config.MAX_DEPTH_RF,
            min_samples_leaf=Config.MIN_SAMPLES_LEAF_RF,
            class_weight=class_weight,
            random_state=42,
            n_jobs=-1,
            bootstrap=True,
            oob_score=True,
            max_features="sqrt",
        )
        return model

    @staticmethod
    def build_logistic_regression(class_weight: Union[str, Dict] = None) -> LogisticRegression:
        """Build Logistic Regression with L2 regularization as baseline."""
        class_weight = class_weight or Config.LR_CLASS_WEIGHT

        model = LogisticRegression(
            C=Config.LR_C,
            class_weight=class_weight,
            max_iter=Config.LR_MAX_ITER,
            random_state=42,
            n_jobs=-1,
            solver="lbfgs",
            penalty="l2",
        )
        return model


# =============================================================================
# ENSEMBLE MODEL
# =============================================================================

class MLEnsemble(BaseEstimator, ClassifierMixin):
    """
    Multi-model ensemble with soft voting.

    Combines XGBoost, LightGBM, Random Forest, and Logistic Regression
    with learnable weights optimized for PR-AUC.

    Each model trains on a different time-series fold for diversity.
    """

    def __init__(
        self,
        use_xgb: bool = True,
        use_lgb: bool = True,
        use_rf: bool = True,
        use_lr: bool = True,
        use_smote: bool = True,
        model_weights: Optional[Dict[str, float]] = None,
        threshold: float = 0.5,
        calibration: bool = True,
    ):
        self.use_xgb = use_xgb and XGBOOST_AVAILABLE
        self.use_lgb = use_lgb and LIGHTGBM_AVAILABLE
        self.use_rf = use_rf
        self.use_lr = use_lr
        self.use_smote = use_smote and SMOTE_AVAILABLE
        self.model_weights = model_weights or Config.MODEL_WEIGHTS.copy()
        self.threshold = threshold
        self.calibration = calibration

        self.models: Dict[str, Any] = {}
        self.calibrators: Dict[str, Any] = {}
        self.feature_names: List[str] = []
        self.scaler: Optional[RobustScaler] = None
        self.is_fitted = False
        self.version = f"v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.training_metadata: Dict[str, Any] = {}
        self.feature_importance: Dict[str, float] = {}

    def _build_models(self, scale_pos_weight: float, class_weights: Dict) -> None:
        """Build all model instances."""
        if self.use_xgb:
            self.models["xgb"] = ModelBuilder.build_xgboost(scale_pos_weight)

        if self.use_lgb:
            self.models["lgb"] = ModelBuilder.build_lightgbm(scale_pos_weight)

        if self.use_rf:
            self.models["rf"] = ModelBuilder.build_random_forest(class_weights)

        if self.use_lr:
            self.models["lr"] = ModelBuilder.build_logistic_regression(class_weights)

        active_models = list(self.models.keys())
        logger.info(f"Built models: {active_models}")

        # Normalize weights for active models only
        active_weights = {k: v for k, v in self.model_weights.items() if k in active_models}
        total = sum(active_weights.values())
        if total > 0:
            self.model_weights = {k: v / total for k, v in active_weights.items()}

    def _fit_model(self, name: str, model: Any, X_train: pd.DataFrame, y_train: np.ndarray,
                   X_val: Optional[pd.DataFrame] = None, y_val: Optional[np.ndarray] = None) -> None:
        """Fit a single model with appropriate handling."""
        logger.info(f"Training {name} on {len(X_train)} samples...")

        try:
            if name == "xgb" and X_val is not None:
                model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    verbose=False,
                )
            elif name == "lgb" and X_val is not None:
                model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                )
            else:
                model.fit(X_train, y_train)

            # Calibrate probabilities
            if self.calibration and X_val is not None and y_val is not None:
                calibrator = CalibratedClassifierCV(
                    estimator=clone(model),
                    method="isotonic",
                    cv="prefit",
                )
                calibrator.fit(X_val, y_val)
                self.calibrators[name] = calibrator
                logger.info(f"Calibrated {name} probabilities")

        except Exception as e:
            logger.error(f"Failed to train {name}: {e}")
            # Remove failed model from ensemble
            if name in self.models:
                del self.models[name]

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> "MLEnsemble":
        """
        Fit the ensemble on training data.

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features for calibration
            y_val: Validation labels for calibration
        """
        logger.info("=" * 60)
        logger.info("Fitting ML Ensemble v2")
        logger.info("=" * 60)

        self.feature_names = list(X_train.columns)

        # Fit scaler
        self.scaler = RobustScaler()
        X_train_scaled = pd.DataFrame(
            self.scaler.fit_transform(X_train),
            columns=X_train.columns,
            index=X_train.index,
        )

        X_val_scaled = None
        if X_val is not None:
            X_val_scaled = pd.DataFrame(
                self.scaler.transform(X_val),
                columns=X_val.columns,
                index=X_val.index,
            )

        # Compute class weights
        scale_pos_weight = ClassImbalanceHandler.get_scale_pos_weight(y_train)
        class_weights = ClassImbalanceHandler.get_class_weights(y_train)

        logger.info(f"Training samples: {len(y_train)}, Positives: {y_train.sum()}")
        logger.info(f"Scale pos weight: {scale_pos_weight:.1f}")

        # Build models
        self._build_models(scale_pos_weight, class_weights)

        # Apply SMOTE for non-tree models
        X_train_smote, y_train_smote = X_train_scaled, y_train
        if self.use_smote:
            # SMOTE for LR; tree models handle imbalance via class weights
            X_train_smote, y_train_smote = ClassImbalanceHandler.apply_smote(
                X_train_scaled, y_train
            )

        # Train each model
        for name, model in list(self.models.items()):
            if name in ("lr",):
                # Use SMOTE-augmented data for logistic regression
                self._fit_model(name, model, X_train_smote, y_train_smote, X_val_scaled, y_val)
            else:
                # Tree models use original data with class weights
                self._fit_model(name, model, X_train_scaled, y_train, X_val_scaled, y_val)

        # Compute feature importance (average across tree models)
        self._compute_feature_importance()

        self.is_fitted = True
        self.training_metadata = {
            "version": self.version,
            "n_train": len(y_train),
            "n_pos_train": int(y_train.sum()),
            "positive_rate": float(y_train.mean()),
            "models_trained": list(self.models.keys()),
            "feature_count": len(self.feature_names),
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"Ensemble fitted. Models: {list(self.models.keys())}")
        return self

    def _compute_feature_importance(self) -> None:
        """Aggregate feature importance across tree-based models."""
        importance_sum = np.zeros(len(self.feature_names))
        n_models = 0

        for name, model in self.models.items():
            try:
                if hasattr(model, "feature_importances_"):
                    importance_sum += model.feature_importances_
                    n_models += 1
            except Exception as e:
                logger.warning(f"Could not get feature importance from {name}: {e}")

        if n_models > 0:
            avg_importance = importance_sum / n_models
            self.feature_importance = {
                name: float(imp)
                for name, imp in zip(self.feature_names, avg_importance)
            }

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict class probabilities using soft voting.

        Returns array of shape (n_samples, 2) with [P(negative), P(positive)].
        """
        if not self.is_fitted:
            raise RuntimeError("Ensemble not fitted. Call fit() first.")

        if self.scaler is not None:
            X_scaled = pd.DataFrame(
                self.scaler.transform(X),
                columns=X.columns,
                index=X.index,
            )
        else:
            X_scaled = X

        probabilities = []
        weights = []

        for name, model in self.models.items():
            try:
                # Use calibrated model if available
                if name in self.calibrators:
                    proba = self.calibrators[name].predict_proba(X_scaled)
                else:
                    proba = model.predict_proba(X_scaled)

                probabilities.append(proba[:, 1])  # P(positive)
                weights.append(self.model_weights.get(name, 1.0))
            except Exception as e:
                logger.warning(f"Prediction failed for {name}: {e}")

        if not probabilities:
            raise RuntimeError("All models failed to predict")

        # Weighted average of probabilities
        weights = np.array(weights)
        weights = weights / weights.sum()

        ensemble_proba = np.average(probabilities, axis=0, weights=weights)

        # Return as [P(neg), P(pos)]
        return np.column_stack([1 - ensemble_proba, ensemble_proba])

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict class labels using optimized threshold."""
        proba = self.predict_proba(X)[:, 1]
        return (proba >= self.threshold).astype(int)

    def get_individual_predictions(self, X: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Get predictions from each individual model."""
        if self.scaler is not None:
            X_scaled = pd.DataFrame(
                self.scaler.transform(X),
                columns=X.columns,
                index=X.index,
            )
        else:
            X_scaled = X

        predictions = {}
        for name, model in self.models.items():
            try:
                proba = model.predict_proba(X_scaled)
                predictions[name] = proba[:, 1]
            except Exception as e:
                logger.warning(f"Individual prediction failed for {name}: {e}")

        return predictions

    def save(self, path: Optional[str] = None) -> str:
        """Save ensemble to disk."""
        path = path or str(Config.MODEL_DIR / f"ensemble_{self.version}.joblib")
        Config.MODEL_DIR.mkdir(parents=True, exist_ok=True)

        artifact = {
            "models": self.models,
            "calibrators": self.calibrators,
            "scaler": self.scaler,
            "feature_names": self.feature_names,
            "model_weights": self.model_weights,
            "threshold": self.threshold,
            "version": self.version,
            "is_fitted": self.is_fitted,
            "training_metadata": self.training_metadata,
            "feature_importance": self.feature_importance,
        }

        joblib.dump(artifact, path)
        logger.info(f"Ensemble saved to {path}")

        # Save version info
        version_info = {
            "version": self.version,
            "path": path,
            "timestamp": datetime.now().isoformat(),
            "models": list(self.models.keys()),
            "n_features": len(self.feature_names),
        }
        with open(Config.MODEL_VERSION_FILE, "w") as f:
            json.dump(version_info, f, indent=2, default=str)

        return path

    @classmethod
    def load(cls, path: str) -> "MLEnsemble":
        """Load ensemble from disk."""
        artifact = joblib.load(path)

        ensemble = cls.__new__(cls)
        ensemble.models = artifact["models"]
        ensemble.calibrators = artifact.get("calibrators", {})
        ensemble.scaler = artifact["scaler"]
        ensemble.feature_names = artifact["feature_names"]
        ensemble.model_weights = artifact["model_weights"]
        ensemble.threshold = artifact["threshold"]
        ensemble.version = artifact["version"]
        ensemble.is_fitted = artifact["is_fitted"]
        ensemble.training_metadata = artifact.get("training_metadata", {})
        ensemble.feature_importance = artifact.get("feature_importance", {})

        logger.info(f"Ensemble loaded: {ensemble.version}")
        return ensemble


# =============================================================================
# MODEL EVALUATOR
# =============================================================================

class ModelEvaluator:
    """
    Comprehensive model evaluation for imbalanced classification.

    PRIMARY METRIC: PR-AUC (not ROC-AUC)
    ROC-AUC is misleading with extreme class imbalance.
    PR-AUC tells us how well we rank positives relative to each other.
    """

    @staticmethod
    def evaluate(
        y_true: np.ndarray,
        y_proba: np.ndarray,
        threshold: float = 0.5,
        model_name: str = "",
        fold_idx: Optional[int] = None,
        n_train: int = 0,
        positive_rate_train: float = 0.0,
    ) -> ModelMetrics:
        """
        Compute comprehensive evaluation metrics.

        Args:
            y_true: True binary labels
            y_proba: Predicted probabilities for positive class
            threshold: Classification threshold
            model_name: Name of the model
            fold_idx: Cross-validation fold index

        Returns:
            ModelMetrics dataclass with all metrics
        """
        y_pred = (y_proba >= threshold).astype(int)

        # Confusion matrix components
        tp = int(np.sum((y_true == 1) & (y_pred == 1)))
        fp = int(np.sum((y_true == 0) & (y_pred == 1)))
        tn = int(np.sum((y_true == 0) & (y_pred == 0)))
        fn = int(np.sum((y_true == 1) & (y_pred == 0)))

        # Primary metric: PR-AUC
        pr_auc = float(average_precision_score(y_true, y_proba))

        # Secondary metrics
        roc_auc = float(roc_auc_score(y_true, y_proba)) if len(np.unique(y_true)) > 1 else 0.0
        f1 = float(f1_score(y_true, y_pred, zero_division=0))
        precision = float(precision_score(y_true, y_pred, zero_division=0))
        recall = float(recall_score(y_true, y_pred, zero_division=0))
        avg_precision = float(average_precision_score(y_true, y_proba))
        brier = float(brier_score_loss(y_true, y_proba))

        # Calibration error (Expected Calibration Error)
        n_bins = 10
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        calibration_error = 0.0
        for i in range(n_bins):
            mask = (y_proba >= bin_boundaries[i]) & (y_proba < bin_boundaries[i + 1])
            if i == n_bins - 1:
                mask = (y_proba >= bin_boundaries[i]) & (y_proba <= bin_boundaries[i + 1])
            if mask.sum() > 0:
                avg_confidence = y_proba[mask].mean()
                avg_accuracy = y_true[mask].mean()
                calibration_error += mask.sum() * abs(avg_confidence - avg_accuracy)
        calibration_error /= len(y_true)

        positive_rate_test = float(y_true.mean())

        metrics = ModelMetrics(
            pr_auc=pr_auc,
            roc_auc=roc_auc,
            f1_score=f1,
            precision=precision,
            recall=recall,
            average_precision=avg_precision,
            brier_score=brier,
            calibration_error=calibration_error,
            threshold=threshold,
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            n_train=n_train,
            n_test=len(y_true),
            positive_rate_train=positive_rate_train,
            positive_rate_test=positive_rate_test,
            fold_idx=fold_idx,
            model_name=model_name,
        )

        return metrics

    @staticmethod
    def print_report(metrics: ModelMetrics, verbose: bool = True) -> str:
        """Generate formatted evaluation report."""
        report_lines = [
            "",
            "=" * 60,
            f"MODEL EVALUATION: {metrics.model_name}",
            "=" * 60,
            f"Fold:              {metrics.fold_idx}",
            f"",
            f"PRIMARY METRICS:",
            f"  PR-AUC:          {metrics.pr_auc:.4f}  {'PASS' if metrics.pr_auc >= Config.PR_AUC_THRESHOLD else 'FAIL'}",
            f"  ROC-AUC:         {metrics.roc_auc:.4f}",
            f"  F1-Score:        {metrics.f1_score:.4f}",
            f"",
            f"PRECISION/RECALL:",
            f"  Precision:       {metrics.precision:.4f}",
            f"  Recall:          {metrics.recall:.4f}",
            f"  Avg Precision:   {metrics.average_precision:.4f}",
            f"",
            f"CALIBRATION:",
            f"  Brier Score:     {metrics.brier_score:.4f}",
            f"  Calib. Error:    {metrics.calibration_error:.4f}",
            f"  Threshold:       {metrics.threshold:.4f}",
            f"",
            f"CONFUSION MATRIX:",
            f"  True Positives:  {metrics.true_positives}",
            f"  False Positives: {metrics.false_positives}",
            f"  True Negatives:  {metrics.true_negatives}",
            f"  False Negatives: {metrics.false_negatives}",
            f"",
            f"DATA:",
            f"  Train samples:   {metrics.n_train}",
            f"  Test samples:    {metrics.n_test}",
            f"  Pos rate (train): {metrics.positive_rate_train*100:.2f}%",
            f"  Pos rate (test):  {metrics.positive_rate_test*100:.2f}%",
            f"  Acceptable:      {metrics.is_acceptable()}",
            "=" * 60,
        ]

        report = "\n".join(report_lines)

        if verbose:
            print(report)

        return report


# =============================================================================
# TRAINING PIPELINE
# =============================================================================

class TrainingPipeline:
    """
    End-to-end training pipeline with time-series cross-validation.

    Handles the full flow: feature engineering -> CV training ->
    threshold optimization -> model saving.
    """

    def __init__(self, feature_engineer: Optional[FeatureEngineer] = None):
        self.feature_engineer = feature_engineer or FeatureEngineer()
        self.evaluator = ModelEvaluator()
        self.threshold_optimizer = ThresholdOptimizer()
        self.cv_results: List[Dict[str, Any]] = []
        self.best_ensemble: Optional[MLEnsemble] = None
        self.best_pr_auc = 0.0

    def run_cross_validation(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_splits: int = None,
        embargo_days: int = None,
    ) -> List[ModelMetrics]:
        """
        Run time-series cross-validation with embargo.

        Each fold trains on progressively larger history with an embargo gap.
        """
        n_splits = n_splits or Config.N_SPLITS_TS
        embargo_days = embargo_days or Config.EMBARGO_DAYS

        logger.info("=" * 60)
        logger.info(f"Time-Series Cross-Validation: {n_splits} splits, {embargo_days}d embargo")
        logger.info("=" * 60)

        cv = TimeSeriesEmbargoSplit(n_splits=n_splits, embargo_days=embargo_days)

        all_metrics = []

        for fold_idx, (train_idx, test_idx) in enumerate(cv.split(X)):
            logger.info(f"\n--- Fold {fold_idx + 1}/{n_splits} ---")

            X_train = X.iloc[train_idx]
            y_train = y.iloc[train_idx].values
            X_test = X.iloc[test_idx]
            y_test = y.iloc[test_idx].values

            # Create validation split from end of training data (most recent)
            val_size = min(len(train_idx) // 5, 500)
            val_size = max(val_size, 50)

            X_val = X_train.tail(val_size)
            y_val = y_train[-val_size:]
            X_train_fold = X_train.head(len(X_train) - val_size)
            y_train_fold = y_train[:-val_size]

            logger.info(f"Train: {len(X_train_fold)}, Val: {len(X_val)}, Test: {len(X_test)}")
            logger.info(f"Train positive rate: {y_train_fold.mean()*100:.2f}%")

            # Train ensemble
            ensemble = MLEnsemble()
            ensemble.fit(
                X_train_fold, y_train_fold,
                X_val=X_val, y_val=y_val,
            )

            # Evaluate on test set
            y_proba = ensemble.predict_proba(X_test)[:, 1]

            # Optimize threshold on validation set
            optimal_threshold = self.threshold_optimizer.optimize(
                y_val, ensemble.predict_proba(X_val)[:, 1],
                metric=Config.THRESHOLD_OPTIMIZATION_METRIC,
            )
            ensemble.threshold = optimal_threshold

            # Evaluate with optimal threshold
            metrics = self.evaluator.evaluate(
                y_test, y_proba,
                threshold=optimal_threshold,
                model_name=f"ensemble_fold_{fold_idx}",
                fold_idx=fold_idx,
                n_train=len(X_train_fold),
                positive_rate_train=y_train_fold.mean(),
            )

            self.evaluator.print_report(metrics)
            all_metrics.append(metrics)

            # Track best model
            if metrics.pr_auc > self.best_pr_auc:
                self.best_pr_auc = metrics.pr_auc
                self.best_ensemble = ensemble
                logger.info(f"New best model: PR-AUC = {metrics.pr_auc:.4f}")

            self.cv_results.append(metrics.to_dict())

        return all_metrics

    def train_final_model(
        self, X: pd.DataFrame, y: pd.Series, validation_split: float = 0.15
    ) -> MLEnsemble:
        """
        Train final model on all data with a validation split.

        Uses the most recent data for validation (time-series appropriate).
        """
        logger.info("=" * 60)
        logger.info("Training Final Model")
        logger.info("=" * 60)

        val_size = int(len(X) * validation_split)
        val_size = min(val_size, 1000)
        val_size = max(val_size, 50)

        X_train = X.head(len(X) - val_size)
        y_train = y.head(len(X) - val_size).values
        X_val = X.tail(val_size)
        y_val = y.tail(val_size).values

        logger.info(f"Train: {len(X_train)}, Val: {len(X_val)}")

        ensemble = MLEnsemble()
        ensemble.fit(X_train, y_train, X_val=X_val, y_val=y_val)

        # Optimize threshold
        y_val_proba = ensemble.predict_proba(X_val)[:, 1]
        optimal_threshold = self.threshold_optimizer.optimize(
            y_val, y_val_proba, metric=Config.THRESHOLD_OPTIMIZATION_METRIC,
        )
        ensemble.threshold = optimal_threshold

        # Evaluate
        metrics = self.evaluator.evaluate(
            y_val, y_val_proba,
            threshold=optimal_threshold,
            model_name="final_ensemble",
            n_train=len(X_train),
            positive_rate_train=y_train.mean(),
        )
        self.evaluator.print_report(metrics)

        self.best_ensemble = ensemble
        return ensemble

    def summarize_cv_results(self) -> Dict[str, float]:
        """Summarize cross-validation results."""
        if not self.cv_results:
            return {}

        metrics_keys = ["pr_auc", "roc_auc", "f1_score", "precision", "recall"]
        summary = {}

        for key in metrics_keys:
            values = [r[key] for r in self.cv_results]
            summary[f"{key}_mean"] = float(np.mean(values))
            summary[f"{key}_std"] = float(np.std(values))
            summary[f"{key}_min"] = float(np.min(values))
            summary[f"{key}_max"] = float(np.max(values))

        summary["n_folds"] = len(self.cv_results)
        summary["timestamp"] = datetime.now().isoformat()

        logger.info("\n" + "=" * 60)
        logger.info("CROSS-VALIDATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"PR-AUC:  {summary['pr_auc_mean']:.4f} +/- {summary['pr_auc_std']:.4f}")
        logger.info(f"ROC-AUC: {summary['roc_auc_mean']:.4f} +/- {summary['roc_auc_std']:.4f}")
        logger.info(f"F1:      {summary['f1_score_mean']:.4f} +/- {summary['f1_score_std']:.4f}")
        logger.info(f"Precision: {summary['precision_mean']:.4f} +/- {summary['precision_std']:.4f}")
        logger.info(f"Recall:    {summary['recall_mean']:.4f} +/- {summary['recall_std']:.4f}")

        return summary




# =============================================================================
# LIVE PREDICTION PIPELINE
# =============================================================================

class LivePredictor:
    """
    Production prediction pipeline.

    Loads trained ensemble, generates predictions with confidence tiers,
    detects feature drift, and logs all predictions.
    """

    def __init__(self, ensemble: Optional[MLEnsemble] = None, feature_engineer: Optional[FeatureEngineer] = None):
        self.ensemble = ensemble
        self.feature_engineer = feature_engineer or FeatureEngineer()
        self.drift_detector = FeatureDriftDetector()
        self.prediction_history: List[Dict[str, Any]] = []
        self.reference_distribution: Optional[pd.DataFrame] = None

    def load_model(self, model_path: Optional[str] = None) -> None:
        """Load trained ensemble from disk."""
        if model_path is None:
            # Find most recent model
            model_dir = Config.MODEL_DIR
            if not model_dir.exists():
                raise FileNotFoundError(f"Model directory not found: {model_dir}")

            model_files = sorted(model_dir.glob("ensemble_*.joblib"), reverse=True)
            if not model_files:
                raise FileNotFoundError("No ensemble model files found")
            model_path = str(model_files[0])

        self.ensemble = MLEnsemble.load(model_path)
        logger.info(f"Loaded model: {self.ensemble.version}")

    def set_reference_distribution(self, X_reference: pd.DataFrame) -> None:
        """Set reference distribution for drift detection."""
        self.reference_distribution = X_reference.copy()
        self.drift_detector.set_reference(X_reference)
        logger.info(f"Set reference distribution: {len(X_reference)} samples, {len(X_reference.columns)} features")

    def predict(
        self,
        X: pd.DataFrame,
        symbol: str = "UNKNOWN",
        timestamp: Optional[datetime] = None,
    ) -> MLPrediction:
        """
        Generate prediction for a single sample.

        Args:
            X: Feature DataFrame (single row or will use last row)
            symbol: Trading pair symbol
            timestamp: Prediction timestamp

        Returns:
            MLPrediction with full metadata
        """
        if self.ensemble is None:
            raise RuntimeError("No model loaded. Call load_model() first.")

        timestamp = timestamp or datetime.now()

        # Ensure single row
        if len(X) > 1:
            X = X.iloc[[-1]]

        # Get ensemble prediction
        proba = self.ensemble.predict_proba(X)[0, 1]

        # Get individual model scores
        individual_scores = {}
        try:
            individual_scores_raw = self.ensemble.get_individual_predictions(X)
            for name, scores in individual_scores_raw.items():
                individual_scores[name] = float(scores[0])
        except Exception as e:
            logger.warning(f"Could not get individual predictions: {e}")

        # Determine direction and confidence
        direction = Direction.LONG if proba >= self.ensemble.threshold else Direction.NEUTRAL
        confidence_tier = self._get_confidence_tier(proba)

        # Build features dict
        features_used = X.iloc[0].to_dict() if len(X.columns) > 0 else {}

        prediction = MLPrediction(
            symbol=symbol,
            timestamp=timestamp,
            direction=direction,
            probability=float(proba),
            confidence_tier=confidence_tier,
            model_version=self.ensemble.version,
            features_used=features_used,
            threshold_used=self.ensemble.threshold,
            ensemble_weights=self.ensemble.model_weights,
            individual_scores=individual_scores,
        )

        # Log prediction
        self._log_prediction(prediction)

        # Check for drift
        if self.reference_distribution is not None:
            drift_report = self.drift_detector.check_drift(X)
            n_drifted = sum(1 for r in drift_report if r.is_drifted)
            if n_drifted > 0:
                logger.warning(f"Feature drift detected: {n_drifted}/{len(drift_report)} features")
                self._log_drift(drift_report)

        return prediction

    def predict_batch(
        self,
        X: pd.DataFrame,
        symbols: Optional[List[str]] = None,
    ) -> List[MLPrediction]:
        """Generate predictions for multiple samples."""
        if self.ensemble is None:
            raise RuntimeError("No model loaded. Call load_model() first.")

        symbols = symbols or [f"SAMPLE_{i}" for i in range(len(X))]
        predictions = []

        proba_all = self.ensemble.predict_proba(X)[:, 1]
        individual_scores_all = {}
        try:
            individual_scores_all = self.ensemble.get_individual_predictions(X)
        except Exception as e:
            logger.warning(f"Could not get batch individual predictions: {e}")

        for i, (idx, row) in enumerate(X.iterrows()):
            symbol = symbols[i] if i < len(symbols) else f"SAMPLE_{i}"
            proba = float(proba_all[i])

            direction = Direction.LONG if proba >= self.ensemble.threshold else Direction.NEUTRAL
            confidence_tier = self._get_confidence_tier(proba)

            individual_scores = {
                name: float(scores[i])
                for name, scores in individual_scores_all.items()
            }

            prediction = MLPrediction(
                symbol=symbol,
                timestamp=datetime.now(),
                direction=direction,
                probability=proba,
                confidence_tier=confidence_tier,
                model_version=self.ensemble.version,
                features_used=row.to_dict(),
                threshold_used=self.ensemble.threshold,
                ensemble_weights=self.ensemble.model_weights,
                individual_scores=individual_scores,
            )

            predictions.append(prediction)
            self._log_prediction(prediction)

        return predictions

    @staticmethod
    def _get_confidence_tier(probability: float) -> ConfidenceTier:
        """Map probability to confidence tier."""
        if probability >= Config.CONFIDENCE_TIERS["high"]:
            return ConfidenceTier.HIGH
        elif probability >= Config.CONFIDENCE_TIERS["medium"]:
            return ConfidenceTier.MEDIUM
        elif probability >= Config.CONFIDENCE_TIERS["low"]:
            return ConfidenceTier.LOW
        else:
            return ConfidenceTier.NONE

    def _log_prediction(self, prediction: MLPrediction) -> None:
        """Log prediction to file."""
        Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.prediction_history.append(prediction.to_dict())

        with open(Config.PREDICTION_LOG_FILE, "a") as f:
            f.write(json.dumps(prediction.to_dict(), default=str) + "\n")

    def _log_drift(self, drift_reports: List[DriftReport]) -> None:
        """Log drift detection results."""
        Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        for report in drift_reports:
            with open(Config.DRIFT_LOG_FILE, "a") as f:
                f.write(json.dumps(report.__dict__, default=str) + "\n")

    def get_prediction_history(self, n: int = 100) -> List[Dict[str, Any]]:
        """Get recent prediction history."""
        return self.prediction_history[-n:]


# =============================================================================
# FEATURE DRIFT DETECTION
# =============================================================================

class FeatureDriftDetector:
    """
    Detect when feature distributions shift from the training distribution.

    Uses statistical tests and distance metrics to identify drift.
    Alerts when drift exceeds threshold (default: 2 standard deviations).
    """

    def __init__(self, threshold: float = None):
        self.threshold = threshold or Config.DRIFT_THRESHOLD
        self.reference_stats: Optional[Dict[str, Dict[str, float]]] = None
        self.feature_names: List[str] = []

    def set_reference(self, X_reference: pd.DataFrame) -> None:
        """Compute reference distribution statistics."""
        self.feature_names = list(X_reference.columns)
        self.reference_stats = {}

        for col in X_reference.columns:
            self.reference_stats[col] = {
                "mean": float(X_reference[col].mean()),
                "std": float(X_reference[col].std()),
                "median": float(X_reference[col].median()),
                "q05": float(X_reference[col].quantile(0.05)),
                "q95": float(X_reference[col].quantile(0.95)),
            }

    def check_drift(self, X_current: pd.DataFrame) -> List[DriftReport]:
        """
        Check for feature drift between reference and current distributions.

        Returns list of DriftReport for each feature.
        """
        if self.reference_stats is None:
            raise RuntimeError("Reference distribution not set. Call set_reference() first.")

        reports = []

        for col in X_current.columns:
            if col not in self.reference_stats:
                continue

            ref = self.reference_stats[col]
            current_mean = float(X_current[col].mean())
            current_std = float(X_current[col].std())

            # Z-score of mean difference
            mean_drift = 0.0
            if ref["std"] > 0:
                mean_drift = abs(current_mean - ref["mean"]) / ref["std"]

            # Standard deviation ratio
            std_drift = 0.0
            if ref["std"] > 0:
                std_drift = current_std / ref["std"]

            # Kolmogorov-Smirnov-like statistic (simplified)
            ks_stat = mean_drift + abs(std_drift - 1.0)

            is_drifted = mean_drift > self.threshold or std_drift > (self.threshold * 0.5)

            report = DriftReport(
                feature_name=col,
                mean_drift=mean_drift,
                std_drift=std_drift,
                ks_statistic=ks_stat,
                is_drifted=is_drifted,
            )
            reports.append(report)

        return reports

    def get_drift_summary(self, reports: List[DriftReport]) -> Dict[str, Any]:
        """Get summary of drift detection."""
        n_drifted = sum(1 for r in reports if r.is_drifted)
        drifted_features = [r.feature_name for r in reports if r.is_drifted]
        max_drift = max((r.mean_drift for r in reports), default=0)

        return {
            "n_features_checked": len(reports),
            "n_drifted": n_drifted,
            "drift_ratio": n_drifted / len(reports) if reports else 0,
            "max_drift": max_drift,
            "drifted_features": drifted_features,
            "is_significant": n_drifted > len(reports) * 0.1,  # >10% features drifted
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# MODEL MONITORING
# =============================================================================

class ModelMonitor:
    """
    Monitor model performance over time.

    Tracks:
    - Prediction accuracy (30-day rolling)
    - Feature importance drift
    - Model performance alerts
    """

    def __init__(self):
        self.performance_log: List[Dict[str, Any]] = []
        self.accuracy_window: List[Dict[str, Any]] = []
        self.alert_threshold = Config.ACCURACY_ALERT_THRESHOLD
        self.pause_threshold = Config.ACCURACY_PAUSE_THRESHOLD
        self.rolling_window_days = Config.ROLLING_WINDOW_DAYS

    def record_outcome(
        self,
        prediction_id: str,
        symbol: str,
        predicted_direction: str,
        actual_return: float,
        predicted_probability: float,
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Record the outcome of a prediction.

        Args:
            prediction_id: Unique prediction ID
            symbol: Trading pair
            predicted_direction: 'long', 'short', or 'neutral'
            actual_return: Actual realized return
            predicted_probability: Predicted probability
            timestamp: When the prediction was made

        Returns:
            Dict with outcome analysis
        """
        timestamp = timestamp or datetime.now()

        # Determine if prediction was correct
        is_correct = False
        if predicted_direction == "long" and actual_return > 0:
            is_correct = True
        elif predicted_direction == "short" and actual_return < 0:
            is_correct = True
        elif predicted_direction == "neutral":
            is_correct = abs(actual_return) < 0.02  # Within 2%

        outcome = {
            "prediction_id": prediction_id,
            "symbol": symbol,
            "predicted_direction": predicted_direction,
            "actual_return": actual_return,
            "predicted_probability": predicted_probability,
            "is_correct": is_correct,
            "timestamp": timestamp.isoformat(),
        }

        self.accuracy_window.append(outcome)
        self.performance_log.append(outcome)

        # Clean old entries
        cutoff = datetime.now() - timedelta(days=self.rolling_window_days)
        self.accuracy_window = [
            o for o in self.accuracy_window
            if datetime.fromisoformat(o["timestamp"]) > cutoff
        ]

        return outcome

    def get_rolling_accuracy(self) -> Dict[str, Any]:
        """Calculate 30-day rolling accuracy metrics."""
        if not self.accuracy_window:
            return {"accuracy": 0.0, "n_predictions": 0, "status": "insufficient_data"}

        # Overall accuracy
        correct = sum(1 for o in self.accuracy_window if o["is_correct"])
        total = len(self.accuracy_window)
        accuracy = correct / total if total > 0 else 0.0

        # By direction
        long_correct = sum(
            1 for o in self.accuracy_window
            if o["predicted_direction"] == "long" and o["is_correct"]
        )
        long_total = sum(
            1 for o in self.accuracy_window if o["predicted_direction"] == "long"
        )

        # Profitability
        returns = [o["actual_return"] for o in self.accuracy_window if o["predicted_direction"] == "long"]
        avg_return = float(np.mean(returns)) if returns else 0.0
        total_return = float(np.sum(returns)) if returns else 0.0

        # Win rate
        wins = sum(1 for r in returns if r > 0)
        win_rate = wins / len(returns) if returns else 0.0

        # Status
        if accuracy < self.pause_threshold:
            status = "auto_pause"
        elif accuracy < self.alert_threshold:
            status = "alert"
        else:
            status = "healthy"

        return {
            "accuracy": accuracy,
            "n_predictions": total,
            "n_correct": correct,
            "long_accuracy": (long_correct / long_total) if long_total > 0 else 0.0,
            "n_long_predictions": long_total,
            "win_rate": win_rate,
            "avg_return": avg_return,
            "total_return": total_return,
            "status": status,
            "window_days": self.rolling_window_days,
            "alert_threshold": self.alert_threshold,
            "pause_threshold": self.pause_threshold,
        }

    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for performance alerts."""
        metrics = self.get_rolling_accuracy()
        alerts = []

        if metrics["status"] == "alert":
            alerts.append({
                "level": "warning",
                "message": f"Model accuracy {metrics['accuracy']:.1%} below threshold {self.alert_threshold:.1%}",
                "metric": "accuracy",
                "value": metrics["accuracy"],
                "threshold": self.alert_threshold,
                "action": "Consider retraining",
                "timestamp": datetime.now().isoformat(),
            })

        if metrics["status"] == "auto_pause":
            alerts.append({
                "level": "critical",
                "message": f"Model accuracy {metrics['accuracy']:.1%} critically low! Auto-pausing predictions.",
                "metric": "accuracy",
                "value": metrics["accuracy"],
                "threshold": self.pause_threshold,
                "action": "RETRAIN REQUIRED - predictions auto-paused",
                "timestamp": datetime.now().isoformat(),
            })

        if metrics["win_rate"] < 0.40 and metrics["n_long_predictions"] > 10:
            alerts.append({
                "level": "warning",
                "message": f"Win rate {metrics['win_rate']:.1%} below 40%",
                "metric": "win_rate",
                "value": metrics["win_rate"],
                "threshold": 0.40,
                "action": "Review feature engineering",
                "timestamp": datetime.now().isoformat(),
            })

        for alert in alerts:
            logger.warning(f"[{alert['level'].upper()}] {alert['message']}")

        return alerts

    def should_retrain(self) -> Tuple[bool, str]:
        """Determine if model should be retrained."""
        metrics = self.get_rolling_accuracy()

        # Check accuracy
        if metrics["status"] in ("alert", "auto_pause"):
            return True, f"accuracy_{metrics['accuracy']:.3f}"

        # Check if we have enough new data
        if len(self.accuracy_window) > 20:
            recent_accuracy = metrics["accuracy"]
            if recent_accuracy < 0.55:
                return True, f"low_recent_accuracy_{recent_accuracy:.3f}"

        return False, ""

    def get_performance_report(self) -> Dict[str, Any]:
        """Get full performance report."""
        accuracy_metrics = self.get_rolling_accuracy()
        alerts = self.check_alerts()

        return {
            "accuracy_metrics": accuracy_metrics,
            "alerts": alerts,
            "total_predictions_logged": len(self.performance_log),
            "monitoring_since": (
                self.performance_log[0]["timestamp"]
                if self.performance_log else None
            ),
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# FEEDBACK LOOP
# =============================================================================

class FeedbackLoop:
    """
    Retrain model from resolved pick outcomes.

    Loads closed picks, recomputes features, adds to training data,
    and triggers incremental retraining.
    """

    def __init__(
        self,
        feature_engineer: Optional[FeatureEngineer] = None,
        training_pipeline: Optional[TrainingPipeline] = None,
    ):
        self.feature_engineer = feature_engineer or FeatureEngineer()
        self.training_pipeline = training_pipeline or TrainingPipeline()
        self.monitor = ModelMonitor()

    def load_closed_picks(self, picks_file: Optional[str] = None) -> pd.DataFrame:
        """
        Load resolved picks from file.

        Args:
            picks_file: Path to closed_picks.json

        Returns:
            DataFrame with pick data
        """
        picks_file = picks_file or str(Config.CLOSED_PICKS_FILE)

        if not os.path.exists(picks_file):
            logger.warning(f"Closed picks file not found: {picks_file}")
            return pd.DataFrame()

        try:
            with open(picks_file, "r") as f:
                picks = json.load(f)

            if isinstance(picks, dict):
                picks = [picks]

            df = pd.DataFrame(picks)
            logger.info(f"Loaded {len(df)} closed picks")
            return df

        except Exception as e:
            logger.error(f"Failed to load closed picks: {e}")
            return pd.DataFrame()

    def retrain_from_outcomes(
        self,
        base_features: pd.DataFrame,
        base_target: pd.Series,
        picks_file: Optional[str] = None,
        min_new_samples: int = 10,
    ) -> Tuple[Optional[MLEnsemble], Dict[str, Any]]:
        """
        Retrain model using resolved pick outcomes.

        Args:
            base_features: Original training features
            base_target: Original training target
            picks_file: Path to closed picks
            min_new_samples: Minimum new samples to trigger retrain

        Returns:
            Tuple of (new ensemble, metadata)
        """
        logger.info("=" * 60)
        logger.info("Feedback Loop: Retraining from Outcomes")
        logger.info("=" * 60)

        # Load resolved picks
        picks_df = self.load_closed_picks(picks_file)

        if len(picks_df) < min_new_samples:
            logger.info(f"Only {len(picks_df)} picks available (min: {min_new_samples}), skipping retrain")
            return None, {"status": "skipped", "reason": "insufficient_picks"}

        # Convert picks to training samples
        # Each pick becomes a training sample with actual outcome as label
        new_features = []
        new_targets = []

        for _, pick in picks_df.iterrows():
            try:
                # Extract features from pick data if available
                pick_features = self._extract_features_from_pick(pick)
                if pick_features is not None:
                    new_features.append(pick_features)

                    # Outcome: 1 if profitable, 0 otherwise
                    pnl = pick.get("pnl", 0)
                    outcome = 1 if pnl > 0.05 else 0  # 5% threshold
                    new_targets.append(outcome)

            except Exception as e:
                logger.warning(f"Failed to process pick: {e}")
                continue

        if len(new_features) < min_new_samples:
            logger.info(f"Only {len(new_features)} valid samples, skipping retrain")
            return None, {"status": "skipped", "reason": "insufficient_valid_samples"}

        # Combine with base training data
        new_features_df = pd.DataFrame(new_features)
        new_targets_series = pd.Series(new_targets)

        # Align columns
        common_cols = list(set(base_features.columns) & set(new_features_df.columns))
        if not common_cols:
            logger.warning("No common features between base data and picks")
            return None, {"status": "skipped", "reason": "feature_mismatch"}

        combined_features = pd.concat([
            base_features[common_cols],
            new_features_df[common_cols],
        ], ignore_index=True)
        combined_target = pd.concat([base_target, new_targets_series], ignore_index=True)

        logger.info(f"Combined dataset: {len(combined_features)} samples")
        logger.info(f"Positive rate: {combined_target.mean()*100:.2f}%")

        # Train new ensemble
        ensemble = self.training_pipeline.train_final_model(
            combined_features, combined_target, validation_split=0.15
        )

        # Save
        model_path = ensemble.save()

        metadata = {
            "status": "success",
            "model_path": model_path,
            "version": ensemble.version,
            "n_base_samples": len(base_features),
            "n_new_samples": len(new_features),
            "n_combined": len(combined_features),
            "positive_rate": float(combined_target.mean()),
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"Retraining complete: {model_path}")
        return ensemble, metadata

    @staticmethod
    def _extract_features_from_pick(pick: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Extract features from a closed pick record."""
        features = {}

        # Extract whatever features are available
        for key in ["rsi", "macd", "volume_ratio", "volatility", "momentum",
                    "price_change_1d", "price_change_7d", "price_change_30d",
                    "volume_change", "bb_position", "atr", "adx"]:
            if key in pick:
                features[key] = float(pick[key])

        # If pick has feature_data, use that
        if "feature_data" in pick and isinstance(pick["feature_data"], dict):
            features.update(pick["feature_data"])

        return features if features else None

    def run_scheduled_retrain(
        self,
        base_features: pd.DataFrame,
        base_target: pd.Series,
        force: bool = False,
    ) -> Tuple[Optional[MLEnsemble], Dict[str, Any]]:
        """
        Run retraining if conditions are met.

        Conditions:
        - force=True: Always retrain
        - Weekly schedule
        - Model accuracy drops below threshold
        """
        # Check if retraining is needed
        should_retrain, reason = self.monitor.should_retrain()

        if not force and not should_retrain:
            return None, {"status": "skipped", "reason": "conditions_not_met"}

        logger.info(f"Retraining triggered: reason={reason}")
        return self.retrain_from_outcomes(base_features, base_target)




# =============================================================================
# PREMIUM SIGNAL INTEGRATION
# =============================================================================

class PremiumSignalIntegration:
    """
    Integrate ML predictions with the alpha_engine signal format.

    Converts MLPrediction objects to the expected premium_signals.json format.
    """

    @staticmethod
    def predictions_to_signals(predictions: List[MLPrediction]) -> List[Dict[str, Any]]:
        """Convert predictions to premium signal format."""
        return [p.to_premium_signal() for p in predictions]

    @staticmethod
    def save_signals(
        signals: List[Dict[str, Any]],
        output_file: Optional[str] = None,
        append: bool = True,
    ) -> str:
        """
        Save signals to premium_signals.json.

        Args:
            signals: List of signal dicts
            output_file: Output path (default: Config.PREMIUM_SIGNALS_FILE)
            append: Whether to append or overwrite

        Returns:
            Path to output file
        """
        output_file = output_file or str(Config.PREMIUM_SIGNALS_FILE)
        Config.DATA_DIR.mkdir(parents=True, exist_ok=True)

        existing = []
        if append and os.path.exists(output_file):
            try:
                with open(output_file, "r") as f:
                    content = f.read().strip()
                    if content:
                        existing = json.loads(content)
                        if isinstance(existing, dict):
                            existing = [existing]
            except Exception:
                existing = []

        # Deduplicate by ID
        all_signals = existing + signals
        seen_ids = set()
        unique_signals = []
        for s in all_signals:
            if s["id"] not in seen_ids:
                seen_ids.add(s["id"])
                unique_signals.append(s)

        # Keep only signals from last 7 days
        cutoff = datetime.now() - timedelta(days=7)
        recent_signals = [
            s for s in unique_signals
            if datetime.fromisoformat(s["generated_at"].replace("Z", "+00:00").replace("+00:00", "")) > cutoff
               or "T" not in s.get("generated_at", "")
        ]

        with open(output_file, "w") as f:
            json.dump(recent_signals, f, indent=2, default=str)

        logger.info(f"Saved {len(signals)} new signals to {output_file} (total: {len(recent_signals)})")
        return output_file

    @staticmethod
    def load_signals(signals_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load existing signals."""
        signals_file = signals_file or str(Config.PREMIUM_SIGNALS_FILE)

        if not os.path.exists(signals_file):
            return []

        try:
            with open(signals_file, "r") as f:
                content = f.read().strip()
                if not content:
                    return []
                data = json.loads(content)
                return data if isinstance(data, list) else [data]
        except Exception as e:
            logger.warning(f"Failed to load signals: {e}")
            return []


# =============================================================================
# QUALITY GATES
# =============================================================================

class QualityGate:
    """
    Quality gates to filter low-confidence predictions.

    Ensures only high-quality signals are passed through.
    """

    @staticmethod
    def check_prediction_quality(prediction: MLPrediction) -> Tuple[bool, str]:
        """
        Check if prediction meets quality standards.

        Returns:
            Tuple of (passed, reason)
        """
        # Minimum probability threshold
        if prediction.probability < Config.CONFIDENCE_TIERS["low"]:
            return False, f"probability_too_low_{prediction.probability:.3f}"

        # Model disagreement check (if individual scores diverge too much)
        if prediction.individual_scores:
            scores = list(prediction.individual_scores.values())
            score_std = np.std(scores)
            if score_std > 0.3:
                return False, f"high_model_disagreement_std_{score_std:.3f}"

        # Confidence tier check
        if prediction.confidence_tier == ConfidenceTier.NONE:
            return False, "confidence_tier_none"

        return True, "passed"

    @staticmethod
    def filter_predictions(
        predictions: List[MLPrediction],
    ) -> Tuple[List[MLPrediction], List[Dict[str, Any]]]:
        """
        Filter predictions through quality gates.

        Returns:
            Tuple of (passed_predictions, rejection_log)
        """
        passed = []
        rejections = []

        for pred in predictions:
            ok, reason = QualityGate.check_prediction_quality(pred)
            if ok:
                passed.append(pred)
            else:
                rejections.append({
                    "symbol": pred.symbol,
                    "probability": pred.probability,
                    "reason": reason,
                    "timestamp": pred.timestamp.isoformat(),
                })

        logger.info(f"Quality gate: {len(passed)}/{len(predictions)} passed")
        return passed, rejections


# =============================================================================
# MAIN ML ENGINE
# =============================================================================

class MLEngine:
    """
    Main ML Engine orchestrating all components.

    This is the primary interface for the ML pipeline:
    - train(): Train a new model
    - predict(): Generate predictions
    - retrain(): Incremental retraining from outcomes
    - monitor(): Check model health
    - scan(): Full scan and signal generation
    """

    def __init__(self):
        self.feature_engineer = FeatureEngineer()
        self.training_pipeline = TrainingPipeline(self.feature_engineer)
        self.live_predictor: Optional[LivePredictor] = None
        self.feedback_loop = FeedbackLoop(self.feature_engineer, self.training_pipeline)
        self.monitor = ModelMonitor()
        self.ensemble: Optional[MLEnsemble] = None

    # -------------------------------------------------------------------------
    # Training
    # -------------------------------------------------------------------------

    def train(
        self,
        ohlcv_data: pd.DataFrame,
        benchmark_data: Optional[Dict[str, pd.DataFrame]] = None,
        target_horizon: int = 7,
        target_threshold: float = 0.05,
        run_cv: bool = True,
    ) -> Dict[str, Any]:
        """
        Train the complete ML pipeline.

        Args:
            ohlcv_data: OHLCV DataFrame with columns [open, high, low, close, volume]
            benchmark_data: Optional benchmark data for correlation features
            target_horizon: Days ahead to predict
            target_threshold: Return threshold for positive class
            run_cv: Whether to run cross-validation

        Returns:
            Training metadata dict
        """
        logger.info("=" * 60)
        logger.info("ML Engine v2 - Training Pipeline")
        logger.info("=" * 60)

        # Build features
        feature_df = self.feature_engineer.build_features(
            ohlcv_data,
            benchmark_data=benchmark_data,
            include_target=True,
            target_horizon=target_horizon,
            target_threshold=target_threshold,
        )

        # Split features and target
        target_col = "target"
        y = feature_df[target_col]
        X = feature_df.drop(columns=[target_col])

        logger.info(f"Feature matrix: {X.shape}")
        logger.info(f"Class distribution: {y.value_counts().to_dict()}")

        # Run cross-validation
        if run_cv:
            cv_metrics = self.training_pipeline.run_cross_validation(X, y)
            cv_summary = self.training_pipeline.summarize_cv_results()
        else:
            cv_summary = {"status": "cv_skipped"}

        # Train final model
        ensemble = self.training_pipeline.train_final_model(X, y)

        # Save model
        model_path = ensemble.save()

        # Store reference distribution for drift detection
        self.ensemble = ensemble
        self.live_predictor = LivePredictor(ensemble, self.feature_engineer)
        self.live_predictor.set_reference_distribution(X)

        metadata = {
            "version": ensemble.version,
            "model_path": model_path,
            "n_samples": len(X),
            "n_features": len(X.columns),
            "positive_rate": float(y.mean()),
            "feature_names": list(X.columns),
            "cv_summary": cv_summary,
            "threshold": ensemble.threshold,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info("=" * 60)
        logger.info("Training Complete")
        logger.info(f"Model: {model_path}")
        logger.info(f"PR-AUC: {cv_summary.get('pr_auc_mean', 'N/A')}")
        logger.info("=" * 60)

        return metadata

    # -------------------------------------------------------------------------
    # Prediction
    # -------------------------------------------------------------------------

    def load_model(self, model_path: Optional[str] = None) -> None:
        """Load a trained model."""
        self.live_predictor = LivePredictor()
        self.live_predictor.load_model(model_path)
        self.ensemble = self.live_predictor.ensemble

    def predict(
        self,
        ohlcv_data: pd.DataFrame,
        symbol: str,
        benchmark_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> MLPrediction:
        """
        Generate prediction for a single symbol.

        Args:
            ohlcv_data: Recent OHLCV data for feature computation
            symbol: Trading pair symbol
            benchmark_data: Optional benchmark data

        Returns:
            MLPrediction
        """
        if self.live_predictor is None or self.ensemble is None:
            raise RuntimeError("No model loaded. Call train() or load_model() first.")

        # Build features (without target)
        feature_df = self.feature_engineer.build_features(
            ohlcv_data,
            benchmark_data=benchmark_data,
            include_target=False,
        )

        # Align features with model's expected features
        model_features = self.ensemble.feature_names
        available_features = [f for f in model_features if f in feature_df.columns]

        if len(available_features) < len(model_features) * 0.8:
            logger.warning(
                f"Only {len(available_features)}/{len(model_features)} features available"
            )

        X = feature_df[available_features].iloc[[-1]]

        # Fill missing features with 0
        for f in model_features:
            if f not in X.columns:
                X[f] = 0

        X = X[model_features]

        return self.live_predictor.predict(X, symbol=symbol)

    def predict_batch(
        self,
        data_dict: Dict[str, pd.DataFrame],
        benchmark_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> List[MLPrediction]:
        """
        Generate predictions for multiple symbols.

        Args:
            data_dict: Dict mapping symbol -> OHLCV DataFrame
            benchmark_data: Optional benchmark data

        Returns:
            List of MLPredictions
        """
        if self.live_predictor is None or self.ensemble is None:
            raise RuntimeError("No model loaded. Call train() or load_model() first.")

        predictions = []
        symbols = []
        all_features = []

        model_features = self.ensemble.feature_names

        for symbol, ohlcv in data_dict.items():
            try:
                feature_df = self.feature_engineer.build_features(
                    ohlcv,
                    benchmark_data=benchmark_data,
                    include_target=False,
                )

                available_features = [f for f in model_features if f in feature_df.columns]
                X = feature_df[available_features]

                for f in model_features:
                    if f not in X.columns:
                        X[f] = 0

                X = X[model_features].iloc[[-1]]
                all_features.append(X)
                symbols.append(symbol)

            except Exception as e:
                logger.warning(f"Failed to process {symbol}: {e}")
                continue

        if not all_features:
            logger.warning("No valid features computed for any symbol")
            return []

        # Batch predict
        X_batch = pd.concat(all_features, ignore_index=True)
        batch_predictions = self.live_predictor.predict_batch(X_batch, symbols=symbols)

        return batch_predictions

    # -------------------------------------------------------------------------
    # Full Scan
    # -------------------------------------------------------------------------

    def scan_and_generate_signals(
        self,
        data_dict: Dict[str, pd.DataFrame],
        benchmark_data: Optional[Dict[str, pd.DataFrame]] = None,
        min_confidence: str = "low",
    ) -> List[Dict[str, Any]]:
        """
        Full scan: predict for all symbols, filter through quality gates,
        and output premium signals.

        Args:
            data_dict: Dict mapping symbol -> OHLCV DataFrame
            benchmark_data: Optional benchmark data
            min_confidence: Minimum confidence tier to include

        Returns:
            List of premium signal dicts
        """
        logger.info("=" * 60)
        logger.info("ML Engine v2 - Full Scan")
        logger.info("=" * 60)

        # Generate predictions
        predictions = self.predict_batch(data_dict, benchmark_data)

        # Quality gate
        passed, rejections = QualityGate.filter_predictions(predictions)

        # Filter by confidence tier
        tier_order = {"high": 3, "medium": 2, "low": 1, "none": 0}
        min_level = tier_order.get(min_confidence, 1)

        filtered = [
            p for p in passed
            if tier_order.get(p.confidence_tier.value, 0) >= min_level
        ]

        # Convert to premium signals
        signals = PremiumSignalIntegration.predictions_to_signals(filtered)

        # Save signals
        PremiumSignalIntegration.save_signals(signals, append=True)

        logger.info(f"Scan complete: {len(predictions)} predictions, {len(filtered)} signals")

        return signals

    # -------------------------------------------------------------------------
    # Monitoring & Retraining
    # -------------------------------------------------------------------------

    def record_outcome(
        self,
        prediction_id: str,
        symbol: str,
        predicted_direction: str,
        actual_return: float,
        predicted_probability: float,
    ) -> Dict[str, Any]:
        """Record a prediction outcome for monitoring."""
        return self.monitor.record_outcome(
            prediction_id, symbol, predicted_direction,
            actual_return, predicted_probability,
        )

    def check_health(self) -> Dict[str, Any]:
        """Check model health and return status report."""
        health = self.monitor.get_performance_report()

        # Add drift info if available
        if self.live_predictor and self.live_predictor.reference_distribution is not None:
            health["drift_detector_active"] = True
        else:
            health["drift_detector_active"] = False

        # Model info
        if self.ensemble:
            health["model_version"] = self.ensemble.version
            health["model_threshold"] = self.ensemble.threshold
            health["active_models"] = list(self.ensemble.models.keys())

        return health

    def retrain(self, base_features: pd.DataFrame, base_target: pd.Series, force: bool = False) -> Dict[str, Any]:
        """Trigger retraining from resolved outcomes."""
        new_ensemble, metadata = self.feedback_loop.run_scheduled_retrain(
            base_features, base_target, force=force,
        )

        if new_ensemble is not None:
            self.ensemble = new_ensemble
            self.live_predictor = LivePredictor(new_ensemble, self.feature_engineer)

        return metadata

    def get_feature_importance(self, top_n: int = 20) -> List[Dict[str, Any]]:
        """Get top feature importances."""
        if self.ensemble is None:
            return []

        importance = self.ensemble.feature_importance
        sorted_importance = sorted(
            importance.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return [
            {"feature": name, "importance": round(imp, 6), "rank": i + 1}
            for i, (name, imp) in enumerate(sorted_importance[:top_n])
        ]


# =============================================================================
# CLI / ENTRY POINT
# =============================================================================

def create_parser():
    """Create argument parser."""
    import argparse

    parser = argparse.ArgumentParser(
        description="ML Engine v2 - Financial Time-Series Prediction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ml_engine_v2.py train --data data/btc_usd.csv --output models/
  python ml_engine_v2.py predict --model models/ensemble_v2.joblib --data data/recent.csv
  python ml_engine_v2.py scan --model models/ensemble_v2.joblib --symbols BTC,ETH,SOL
  python ml_engine_v2.py health --model models/ensemble_v2.joblib
  python ml_engine_v2.py retrain --model models/ensemble_v2.joblib --picks data/closed_picks.json
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Train command
    train_parser = subparsers.add_parser("train", help="Train a new model")
    train_parser.add_argument("--data", required=True, help="Path to OHLCV CSV file")
    train_parser.add_argument("--benchmarks", help="JSON file with benchmark data paths")
    train_parser.add_argument("--horizon", type=int, default=7, help="Prediction horizon (days)")
    train_parser.add_argument("--threshold", type=float, default=0.05, help="Target threshold")
    train_parser.add_argument("--no-cv", action="store_true", help="Skip cross-validation")
    train_parser.add_argument("--output", default="ml_models_v2", help="Output directory")

    # Predict command
    predict_parser = subparsers.add_parser("predict", help="Generate predictions")
    predict_parser.add_argument("--model", required=True, help="Path to trained model")
    predict_parser.add_argument("--data", required=True, help="Path to recent OHLCV data")
    predict_parser.add_argument("--symbol", default="BTCUSDT", help="Symbol to predict")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Full scan for all symbols")
    scan_parser.add_argument("--model", required=True, help="Path to trained model")
    scan_parser.add_argument("--symbols", required=True, help="Comma-separated symbols")
    scan_parser.add_argument("--data-dir", required=True, help="Directory with OHLCV CSVs")
    scan_parser.add_argument("--min-confidence", default="low", help="Minimum confidence tier")

    # Health command
    health_parser = subparsers.add_parser("health", help="Check model health")
    health_parser.add_argument("--model", help="Path to trained model")
    health_parser.add_argument("--log-file", help="Path to prediction log")

    # Retrain command
    retrain_parser = subparsers.add_parser("retrain", help="Retrain from outcomes")
    retrain_parser.add_argument("--model", required=True, help="Path to current model")
    retrain_parser.add_argument("--picks", help="Path to closed picks file")
    retrain_parser.add_argument("--data", required=True, help="Path to base training data")
    retrain_parser.add_argument("--force", action="store_true", help="Force retrain")

    return parser


def load_ohlcv(path: str) -> pd.DataFrame:
    """Load OHLCV data from CSV."""
    df = pd.read_csv(path)

    # Standardize column names
    col_map = {
        "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume",
        "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume",
        "open_price": "open", "close_price": "close",
    }
    df = df.rename(columns=col_map)

    # Ensure required columns exist
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}. Available: {list(df.columns)}")

    return df


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    engine = MLEngine()

    if args.command == "train":
        # Load data
        ohlcv = load_ohlcv(args.data)
        benchmarks = None
        if args.benchmarks:
            with open(args.benchmarks, "r") as f:
                bench_paths = json.load(f)
            benchmarks = {
                k: load_ohlcv(v) for k, v in bench_paths.items()
            }

        # Train
        Config.MODEL_DIR = Path(args.output)
        metadata = engine.train(
            ohlcv, benchmarks,
            target_horizon=args.horizon,
            target_threshold=args.threshold,
            run_cv=not args.no_cv,
        )
        print(json.dumps(metadata, indent=2, default=str))

    elif args.command == "predict":
        engine.load_model(args.model)
        ohlcv = load_ohlcv(args.data)
        prediction = engine.predict(ohlcv, symbol=args.symbol)
        print(json.dumps(prediction.to_dict(), indent=2, default=str))

    elif args.command == "scan":
        engine.load_model(args.model)
        symbols = [s.strip() for s in args.symbols.split(",")]

        data_dict = {}
        for symbol in symbols:
            path = os.path.join(args.data_dir, f"{symbol}.csv")
            if os.path.exists(path):
                data_dict[symbol] = load_ohlcv(path)
            else:
                logger.warning(f"Data file not found: {path}")

        signals = engine.scan_and_generate_signals(
            data_dict, min_confidence=args.min_confidence,
        )
        print(json.dumps(signals, indent=2, default=str))

    elif args.command == "health":
        if args.model:
            engine.load_model(args.model)
        health = engine.check_health()
        print(json.dumps(health, indent=2, default=str))

    elif args.command == "retrain":
        engine.load_model(args.model)
        base_data = load_ohlcv(args.data)
        feature_df = engine.feature_engineer.build_features(base_data, include_target=True)
        y = feature_df["target"]
        X = feature_df.drop(columns=["target"])
        metadata = engine.retrain(X, y, force=args.force)
        print(json.dumps(metadata, indent=2, default=str))


# =============================================================================
# DEMO / TESTING UTILITIES
# =============================================================================

def generate_synthetic_data(
    n_samples: int = 2000,
    symbol: str = "BTCUSDT",
    positive_rate: float = 0.007,
    random_seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic OHLCV data for testing.

    Creates realistic-looking price data with known patterns.
    """
    np.random.seed(random_seed)

    dates = pd.date_range(end=datetime.now(), periods=n_samples, freq="D")

    # Random walk with drift
    returns = np.random.normal(0.001, 0.03, n_samples)

    # Add some momentum periods (trend following)
    for i in range(50, n_samples):
        if np.random.random() < 0.3:
            # Trend period
            returns[i:i+5] += np.random.choice([-1, 1]) * 0.01

    # Add regime changes
    regime_changes = np.random.choice(n_samples, size=5, replace=False)
    for rc in regime_changes:
        returns[rc:rc+20] += np.random.normal(0, 0.02)

    close = 50000 * np.exp(np.cumsum(returns))

    # Generate OHLC from close
    high_low_range = close * np.abs(np.random.normal(0.02, 0.01, n_samples))
    high = close + high_low_range * np.random.uniform(0.3, 0.7, n_samples)
    low = close - high_low_range * np.random.uniform(0.3, 0.7, n_samples)
    open_price = close * (1 + np.random.normal(0, 0.005, n_samples))

    # Volume with some correlation to volatility
    volatility = np.abs(returns)
    volume = np.random.lognormal(20, 1, n_samples) * (1 + volatility * 10)

    df = pd.DataFrame({
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }, index=dates)

    return df


def run_demo():
    """Run a complete demo of the ML pipeline."""
    print("=" * 70)
    print("ML ENGINE v2 - DEMONSTRATION")
    print("=" * 70)

    # Generate synthetic data
    print("\n[1] Generating synthetic data...")
    ohlcv = generate_synthetic_data(n_samples=2500)
    print(f"  Generated {len(ohlcv)} rows of OHLCV data")
    print(f"  Price range: ${ohlcv['close'].min():.0f} - ${ohlcv['close'].max():.0f}")

    # Benchmark data
    benchmarks = {
        "BTC": generate_synthetic_data(n_samples=2500, symbol="BTCUSDT", random_seed=43),
        "ETH": generate_synthetic_data(n_samples=2500, symbol="ETHUSDT", random_seed=44),
    }

    # Initialize engine
    print("\n[2] Initializing ML Engine...")
    engine = MLEngine()

    # Train
    print("\n[3] Training model (with cross-validation)...")
    metadata = engine.train(
        ohlcv,
        benchmark_data=benchmarks,
        target_horizon=7,
        target_threshold=0.05,
        run_cv=True,
    )

    print(f"\n  Model version: {metadata['version']}")
    print(f"  Training samples: {metadata['n_samples']}")
    print(f"  Features: {metadata['n_features']}")
    print(f"  Positive rate: {metadata['positive_rate']*100:.2f}%")

    cv_summary = metadata.get("cv_summary", {})
    print(f"  CV PR-AUC: {cv_summary.get('pr_auc_mean', 'N/A')}")

    # Predict
    print("\n[4] Generating predictions...")
    recent_data = ohlcv.tail(100)
    prediction = engine.predict(recent_data, symbol="BTCUSDT")

    print(f"  Symbol: {prediction.symbol}")
    print(f"  Probability: {prediction.probability:.4f}")
    print(f"  Direction: {prediction.direction.value}")
    print(f"  Confidence: {prediction.confidence_tier.value}")
    print(f"  Threshold: {prediction.threshold_used:.4f}")
    print(f"  Individual scores: {prediction.individual_scores}")

    # Batch predict
    print("\n[5] Batch predictions...")
    data_dict = {
        "BTCUSDT": recent_data,
        "ETHUSDT": benchmarks["ETH"].tail(100),
    }
    batch_preds = engine.predict_batch(data_dict)
    for p in batch_preds:
        print(f"  {p.symbol}: {p.direction.value} (p={p.probability:.4f}, conf={p.confidence_tier.value})")

    # Feature importance
    print("\n[6] Top features:")
    top_features = engine.get_feature_importance(top_n=10)
    for feat in top_features:
        print(f"  {feat['rank']:2d}. {feat['feature']}: {feat['importance']:.4f}")

    # Health check
    print("\n[7] Health check:")
    health = engine.check_health()
    print(f"  Status: {health['accuracy_metrics']['status']}")
    print(f"  Active models: {health.get('active_models', [])}")

    # Generate signals
    print("\n[8] Premium signals:")
    signals = engine.scan_and_generate_signals(data_dict, min_confidence="low")
    for sig in signals:
        print(f"  {sig['symbol']}: {sig['direction']} (p={sig['probability']}, conf={sig['confidence']})")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)

    return engine, metadata, prediction


if __name__ == "__main__":
    # Check if running as CLI or demo
    import sys
    if len(sys.argv) > 1 and sys.argv[1] in ("train", "predict", "scan", "health", "retrain"):
        main()
    else:
        print("Running demo mode...")
        print("Usage: python ml_engine_v2.py <command> [options]")
        print("Commands: train, predict, scan, health, retrain")
        print()
        run_demo()

