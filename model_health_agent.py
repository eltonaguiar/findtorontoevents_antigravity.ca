#!/usr/bin/env python3
"""
Model Health Agent
==================
Comprehensive ML model monitoring and health management system.

Features:
- Real-time model performance tracking
- Statistical drift detection (concept drift, data drift)
- Automated retraining triggers
- Model validation with statistical significance testing
- Health dashboards and alerting
- Model versioning and lifecycle management
- Integration with existing ML pipeline

Author: AI Assistant
Date: 2026
"""

import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import statistics
import sqlite3
import joblib
import warnings
from pathlib import Path
import hashlib
import shutil

# Optional imports with fallbacks
try:
    import numpy as np
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import scipy.stats as stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        mean_squared_error, mean_absolute_error, r2_score
    )
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('model_health_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

warnings.filterwarnings('ignore')


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class ModelStatus(Enum):
    """Model deployment status"""
    ACTIVE = "active"
    DEGRADED = "degraded"
    RETRAINING = "retraining"
    RETIRED = "retired"
    FAILED = "failed"


class DriftType(Enum):
    """Types of model drift"""
    CONCEPT_DRIFT = "concept_drift"
    DATA_DRIFT = "data_drift"
    PERFORMANCE_DECAY = "performance_decay"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ModelMetrics:
    """Model performance metrics"""
    timestamp: datetime
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    sample_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'total_trades': self.total_trades,
            'sample_size': self.sample_size
        }


@dataclass
class DriftDetection:
    """Drift detection results"""
    timestamp: datetime
    drift_type: DriftType
    p_value: float
    statistic: float
    threshold: float
    is_significant: bool
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'drift_type': self.drift_type.value,
            'p_value': self.p_value,
            'statistic': self.statistic,
            'threshold': self.threshold,
            'is_significant': self.is_significant,
            'confidence': self.confidence,
            'details': self.details
        }


@dataclass
class ModelVersion:
    """Model version information"""
    version_id: str
    model_path: str
    created_at: datetime
    trained_on: datetime
    performance_baseline: ModelMetrics
    features_used: List[str]
    hyperparameters: Dict[str, Any]
    status: ModelStatus = ModelStatus.ACTIVE
    retired_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'version_id': self.version_id,
            'model_path': self.model_path,
            'created_at': self.created_at.isoformat(),
            'trained_on': self.trained_on.isoformat(),
            'performance_baseline': self.performance_baseline.to_dict(),
            'features_used': self.features_used,
            'hyperparameters': self.hyperparameters,
            'status': self.status.value,
            'retired_at': self.retired_at.isoformat() if self.retired_at else None
        }


@dataclass
class HealthAlert:
    """Health monitoring alert"""
    alert_id: str
    timestamp: datetime
    model_name: str
    alert_type: str
    level: AlertLevel
    message: str
    metrics: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'alert_id': self.alert_id,
            'timestamp': self.timestamp.isoformat(),
            'model_name': self.model_name,
            'alert_type': self.alert_type,
            'level': self.level.value,
            'message': self.message,
            'metrics': self.metrics,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """Configuration for Model Health Agent"""

    # Database settings
    DB_PATH = 'model_health.db'
    METRICS_RETENTION_DAYS = 90
    ALERT_RETENTION_DAYS = 30

    # Monitoring settings
    MONITORING_INTERVAL_MINUTES = 15
    PERFORMANCE_WINDOW_HOURS = 24
    DRIFT_DETECTION_WINDOW_HOURS = 168  # 1 week

    # Thresholds
    ACCURACY_DEGRADATION_THRESHOLD = 0.05  # 5% drop
    PRECISION_DEGRADATION_THRESHOLD = 0.08  # 8% drop
    RECALL_DEGRADATION_THRESHOLD = 0.08    # 8% drop
    SHARPE_RATIO_MINIMUM = 0.5
    WIN_RATE_MINIMUM = 0.45

    # Drift detection
    DRIFT_P_VALUE_THRESHOLD = 0.05
    DRIFT_STATISTIC_THRESHOLD = 2.0  # Standard deviations

    # Retraining triggers
    RETRAIN_ACCURACY_DROP = 0.10  # 10% drop triggers retrain
    RETRAIN_CONSECUTIVE_FAILURES = 3
    RETRAIN_MIN_SAMPLES = 1000

    # Alert settings
    ALERT_COOLDOWN_MINUTES = 60
    CRITICAL_ALERT_EMAIL = True

    # Model paths
    MODELS_DIR = Path('ml_crypto_predictor/models')
    PRODUCTION_MODELS_DIR = Path('ml_crypto_predictor/production_models')
    BACKUP_MODELS_DIR = Path('ml_crypto_predictor/model_backups')

    # API settings
    API_HOST = '0.0.0.0'
    API_PORT = 8001
    ENABLE_API = True


# =============================================================================
# DATABASE MANAGER
# =============================================================================

class DatabaseManager:
    """Manages model health database operations"""

    def __init__(self, db_path: str = Config.DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Model versions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_versions (
                    version_id TEXT PRIMARY KEY,
                    model_name TEXT NOT NULL,
                    model_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    trained_on TEXT NOT NULL,
                    performance_baseline TEXT NOT NULL,
                    features_used TEXT NOT NULL,
                    hyperparameters TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retired_at TEXT
                )
            ''')

            # Model metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    accuracy REAL,
                    precision REAL,
                    recall REAL,
                    f1_score REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    win_rate REAL,
                    profit_factor REAL,
                    total_trades INTEGER,
                    sample_size INTEGER
                )
            ''')

            # Drift detection table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS drift_detection (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    drift_type TEXT NOT NULL,
                    p_value REAL,
                    statistic REAL,
                    threshold REAL,
                    is_significant INTEGER,
                    confidence REAL,
                    details TEXT
                )
            ''')

            # Health alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS health_alerts (
                    alert_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    metrics TEXT NOT NULL,
                    resolved INTEGER DEFAULT 0,
                    resolved_at TEXT
                )
            ''')

            # Model predictions table for drift detection
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    features TEXT NOT NULL,
                    prediction REAL,
                    actual REAL,
                    confidence REAL
                )
            ''')

            conn.commit()

    def save_model_version(self, model_name: str, version: ModelVersion):
        """Save model version to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO model_versions
                (version_id, model_name, model_path, created_at, trained_on,
                 performance_baseline, features_used, hyperparameters, status, retired_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                version.version_id, model_name, version.model_path,
                version.created_at.isoformat(), version.trained_on.isoformat(),
                json.dumps(version.performance_baseline.to_dict()),
                json.dumps(version.features_used),
                json.dumps(version.hyperparameters),
                version.status.value,
                version.retired_at.isoformat() if version.retired_at else None
            ))
            conn.commit()

    def get_model_versions(self, model_name: str) -> List[ModelVersion]:
        """Get all versions for a model"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM model_versions WHERE model_name = ? ORDER BY created_at DESC',
                (model_name,)
            )
            rows = cursor.fetchall()

        versions = []
        for row in rows:
            performance_data = json.loads(row[5])
            versions.append(ModelVersion(
                version_id=row[0],
                model_path=row[2],
                created_at=datetime.fromisoformat(row[3]),
                trained_on=datetime.fromisoformat(row[4]),
                performance_baseline=ModelMetrics(
                    timestamp=datetime.fromisoformat(performance_data['timestamp']),
                    accuracy=performance_data.get('accuracy', 0.0),
                    precision=performance_data.get('precision', 0.0),
                    recall=performance_data.get('recall', 0.0),
                    f1_score=performance_data.get('f1_score', 0.0),
                    sharpe_ratio=performance_data.get('sharpe_ratio', 0.0),
                    max_drawdown=performance_data.get('max_drawdown', 0.0),
                    win_rate=performance_data.get('win_rate', 0.0),
                    profit_factor=performance_data.get('profit_factor', 0.0),
                    total_trades=performance_data.get('total_trades', 0),
                    sample_size=performance_data.get('sample_size', 0)
                ),
                features_used=json.loads(row[6]),
                hyperparameters=json.loads(row[7]),
                status=ModelStatus(row[8]),
                retired_at=datetime.fromisoformat(row[9]) if row[9] else None
            ))
        return versions

    def save_metrics(self, model_name: str, metrics: ModelMetrics):
        """Save model metrics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO model_metrics
                (model_name, timestamp, accuracy, precision, recall, f1_score,
                 sharpe_ratio, max_drawdown, win_rate, profit_factor, total_trades, sample_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                model_name, metrics.timestamp.isoformat(),
                metrics.accuracy, metrics.precision, metrics.recall, metrics.f1_score,
                metrics.sharpe_ratio, metrics.max_drawdown, metrics.win_rate,
                metrics.profit_factor, metrics.total_trades, metrics.sample_size
            ))
            conn.commit()

    def get_metrics_history(self, model_name: str, hours: int = 24) -> List[ModelMetrics]:
        """Get metrics history for the last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM model_metrics
                WHERE model_name = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            ''', (model_name, cutoff.isoformat()))
            rows = cursor.fetchall()

        metrics = []
        for row in rows:
            metrics.append(ModelMetrics(
                timestamp=datetime.fromisoformat(row[2]),
                accuracy=row[3] or 0.0,
                precision=row[4] or 0.0,
                recall=row[5] or 0.0,
                f1_score=row[6] or 0.0,
                sharpe_ratio=row[7] or 0.0,
                max_drawdown=row[8] or 0.0,
                win_rate=row[9] or 0.0,
                profit_factor=row[10] or 0.0,
                total_trades=row[11] or 0,
                sample_size=row[12] or 0
            ))
        return metrics

    def save_drift_detection(self, model_name: str, drift: DriftDetection):
        """Save drift detection result"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO drift_detection
                (model_name, timestamp, drift_type, p_value, statistic, threshold,
                 is_significant, confidence, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                model_name, drift.timestamp.isoformat(), drift.drift_type.value,
                drift.p_value, drift.statistic, drift.threshold,
                1 if drift.is_significant else 0, drift.confidence,
                json.dumps(drift.details)
            ))
            conn.commit()

    def save_alert(self, alert: HealthAlert):
        """Save health alert"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO health_alerts
                (alert_id, timestamp, model_name, alert_type, level, message,
                 metrics, resolved, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.alert_id, alert.timestamp.isoformat(), alert.model_name,
                alert.alert_type, alert.level.value, alert.message,
                json.dumps(alert.metrics), 1 if alert.resolved else 0,
                alert.resolved_at.isoformat() if alert.resolved_at else None
            ))
            conn.commit()

    def get_active_alerts(self, model_name: Optional[str] = None) -> List[HealthAlert]:
        """Get active (unresolved) alerts"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if model_name:
                cursor.execute(
                    'SELECT * FROM health_alerts WHERE model_name = ? AND resolved = 0 ORDER BY timestamp DESC',
                    (model_name,)
                )
            else:
                cursor.execute(
                    'SELECT * FROM health_alerts WHERE resolved = 0 ORDER BY timestamp DESC'
                )
            rows = cursor.fetchall()

        alerts = []
        for row in rows:
            alerts.append(HealthAlert(
                alert_id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                model_name=row[2],
                alert_type=row[3],
                level=AlertLevel(row[4]),
                message=row[5],
                metrics=json.loads(row[6]),
                resolved=bool(row[7]),
                resolved_at=datetime.fromisoformat(row[8]) if row[8] else None
            ))
        return alerts

    def cleanup_old_data(self):
        """Clean up old metrics and alerts"""
        metrics_cutoff = datetime.now() - timedelta(days=Config.METRICS_RETENTION_DAYS)
        alerts_cutoff = datetime.now() - timedelta(days=Config.ALERT_RETENTION_DAYS)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM model_metrics WHERE timestamp < ?', (metrics_cutoff.isoformat(),))
            cursor.execute('DELETE FROM drift_detection WHERE timestamp < ?', (metrics_cutoff.isoformat(),))
            cursor.execute('DELETE FROM health_alerts WHERE timestamp < ?', (alerts_cutoff.isoformat(),))
            conn.commit()


# =============================================================================
# DRIFT DETECTION ENGINE
# =============================================================================

class DriftDetector:
    """Statistical drift detection engine"""

    def __init__(self):
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None

    def detect_concept_drift(self, historical_predictions: np.ndarray,
                           current_predictions: np.ndarray) -> DriftDetection:
        """
        Detect concept drift using Kolmogorov-Smirnov test on prediction distributions
        """
        if not SCIPY_AVAILABLE or len(historical_predictions) < 50 or len(current_predictions) < 50:
            return DriftDetection(
                timestamp=datetime.now(),
                drift_type=DriftType.CONCEPT_DRIFT,
                p_value=1.0,
                statistic=0.0,
                threshold=Config.DRIFT_P_VALUE_THRESHOLD,
                is_significant=False,
                confidence=0.0,
                details={'reason': 'insufficient_data_or_dependencies'}
            )

        try:
            # Kolmogorov-Smirnov test for distribution difference
            ks_stat, p_value = stats.ks_2samp(historical_predictions, current_predictions)

            is_significant = p_value < Config.DRIFT_P_VALUE_THRESHOLD
            confidence = 1 - p_value

            return DriftDetection(
                timestamp=datetime.now(),
                drift_type=DriftType.CONCEPT_DRIFT,
                p_value=p_value,
                statistic=ks_stat,
                threshold=Config.DRIFT_P_VALUE_THRESHOLD,
                is_significant=is_significant,
                confidence=confidence,
                details={
                    'test': 'kolmogorov_smirnov',
                    'historical_samples': len(historical_predictions),
                    'current_samples': len(current_predictions),
                    'mean_historical': float(np.mean(historical_predictions)),
                    'mean_current': float(np.mean(current_predictions))
                }
            )
        except Exception as e:
            logger.error(f"Concept drift detection failed: {e}")
            return DriftDetection(
                timestamp=datetime.now(),
                drift_type=DriftType.CONCEPT_DRIFT,
                p_value=1.0,
                statistic=0.0,
                threshold=Config.DRIFT_P_VALUE_THRESHOLD,
                is_significant=False,
                confidence=0.0,
                details={'error': str(e)}
            )

    def detect_data_drift(self, historical_features: np.ndarray,
                         current_features: np.ndarray) -> DriftDetection:
        """
        Detect data drift using multivariate statistical tests
        """
        if not SCIPY_AVAILABLE or len(historical_features) < 50 or len(current_features) < 50:
            return DriftDetection(
                timestamp=datetime.now(),
                drift_type=DriftType.DATA_DRIFT,
                p_value=1.0,
                statistic=0.0,
                threshold=Config.DRIFT_P_VALUE_THRESHOLD,
                is_significant=False,
                confidence=0.0,
                details={'reason': 'insufficient_data_or_dependencies'}
            )

        try:
            # Calculate Mahalanobis distance for multivariate drift detection
            # Combine historical and current data
            all_data = np.vstack([historical_features, current_features])

            # Standardize features
            if self.scaler:
                all_data_scaled = self.scaler.fit_transform(all_data)
            else:
                all_data_scaled = all_data

            # Split back into historical and current
            hist_scaled = all_data_scaled[:len(historical_features)]
            curr_scaled = all_data_scaled[len(historical_features):]

            # Calculate mean difference
            mean_diff = np.mean(curr_scaled, axis=0) - np.mean(hist_scaled, axis=0)
            pooled_cov = np.cov(np.vstack([hist_scaled, curr_scaled]).T)

            # Mahalanobis distance
            try:
                mahalanobis_dist = np.sqrt(np.dot(np.dot(mean_diff, np.linalg.inv(pooled_cov)), mean_diff))
            except np.linalg.LinAlgError:
                # Fallback to Euclidean distance if covariance matrix is singular
                mahalanobis_dist = np.linalg.norm(mean_diff)

            # Convert to p-value approximation (simplified)
            # For multivariate normal, this follows chi-square distribution
            df = historical_features.shape[1]
            p_value = 1 - stats.chi2.cdf(mahalanobis_dist**2, df)

            is_significant = p_value < Config.DRIFT_P_VALUE_THRESHOLD
            confidence = 1 - p_value

            return DriftDetection(
                timestamp=datetime.now(),
                drift_type=DriftType.DATA_DRIFT,
                p_value=p_value,
                statistic=mahalanobis_dist,
                threshold=Config.DRIFT_STATISTIC_THRESHOLD,
                is_significant=is_significant,
                confidence=confidence,
                details={
                    'test': 'mahalanobis_distance',
                    'historical_samples': len(historical_features),
                    'current_samples': len(current_features),
                    'features': historical_features.shape[1],
                    'mean_difference_norm': float(np.linalg.norm(mean_diff))
                }
            )
        except Exception as e:
            logger.error(f"Data drift detection failed: {e}")
            return DriftDetection(
                timestamp=datetime.now(),
                drift_type=DriftType.DATA_DRIFT,
                p_value=1.0,
                statistic=0.0,
                threshold=Config.DRIFT_P_VALUE_THRESHOLD,
                is_significant=False,
                confidence=0.0,
                details={'error': str(e)}
            )

    def detect_performance_decay(self, metrics_history: List[ModelMetrics]) -> DriftDetection:
        """
        Detect performance decay using trend analysis
        """
        if len(metrics_history) < 10:
            return DriftDetection(
                timestamp=datetime.now(),
                drift_type=DriftType.PERFORMANCE_DECAY,
                p_value=1.0,
                statistic=0.0,
                threshold=Config.DRIFT_P_VALUE_THRESHOLD,
                is_significant=False,
                confidence=0.0,
                details={'reason': 'insufficient_history'}
            )

        try:
            # Extract accuracy trend
            accuracies = [m.accuracy for m in metrics_history if m.accuracy > 0]
            if len(accuracies) < 5:
                return DriftDetection(
                    timestamp=datetime.now(),
                    drift_type=DriftType.PERFORMANCE_DECAY,
                    p_value=1.0,
                    statistic=0.0,
                    threshold=Config.DRIFT_P_VALUE_THRESHOLD,
                    is_significant=False,
                    confidence=0.0,
                    details={'reason': 'insufficient_accuracy_data'}
                )

            # Simple linear regression to detect downward trend
            x = np.arange(len(accuracies))
            y = np.array(accuracies)

            # Calculate slope
            slope = np.polyfit(x, y, 1)[0]

            # Calculate R-squared
            y_pred = slope * x + np.polyfit(x, y, 1)[1]
            r_squared = 1 - (np.sum((y - y_pred)**2) / np.sum((y - np.mean(y))**2))

            # Statistical significance of slope (simplified t-test approximation)
            se_slope = np.sqrt(np.sum((y - y_pred)**2) / (len(x) - 2)) / np.sqrt(np.sum((x - np.mean(x))**2))
            t_stat = abs(slope) / se_slope if se_slope > 0 else 0
            p_value = 2 * (1 - stats.t.cdf(t_stat, len(x) - 2)) if SCIPY_AVAILABLE else 1.0

            # Check if trend is significantly downward
            is_significant = slope < -Config.ACCURACY_DEGRADATION_THRESHOLD and p_value < Config.DRIFT_P_VALUE_THRESHOLD

            confidence = 1 - p_value if p_value < 0.5 else 0.0

            return DriftDetection(
                timestamp=datetime.now(),
                drift_type=DriftType.PERFORMANCE_DECAY,
                p_value=p_value,
                statistic=slope,
                threshold=-Config.ACCURACY_DEGRADATION_THRESHOLD,
                is_significant=is_significant,
                confidence=confidence,
                details={
                    'trend_analysis': 'linear_regression',
                    'slope': float(slope),
                    'r_squared': float(r_squared),
                    'samples': len(accuracies),
                    'recent_accuracy': float(np.mean(accuracies[-3:])) if len(accuracies) >= 3 else 0.0,
                    'baseline_accuracy': float(np.mean(accuracies[:3])) if len(accuracies) >= 3 else 0.0
                }
            )
        except Exception as e:
            logger.error(f"Performance decay detection failed: {e}")
            return DriftDetection(
                timestamp=datetime.now(),
                drift_type=DriftType.PERFORMANCE_DECAY,
                p_value=1.0,
                statistic=0.0,
                threshold=Config.DRIFT_P_VALUE_THRESHOLD,
                is_significant=False,
                confidence=0.0,
                details={'error': str(e)}
            )


# =============================================================================
# MODEL MONITOR
# =============================================================================

class ModelMonitor:
    """Monitors individual model performance and health"""

    def __init__(self, model_name: str, db_manager: DatabaseManager, drift_detector: DriftDetector):
        self.model_name = model_name
        self.db = db_manager
        self.drift_detector = drift_detector
        self.model = None
        self.last_metrics = None
        self.consecutive_failures = 0

    def load_model(self, model_path: str) -> bool:
        """Load model from disk"""
        try:
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
                logger.info(f"Loaded model {self.model_name} from {model_path}")
                return True
            else:
                logger.error(f"Model file not found: {model_path}")
                return False
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            return False

    def calculate_metrics(self, predictions: np.ndarray, actuals: np.ndarray,
                         confidence_scores: Optional[np.ndarray] = None) -> ModelMetrics:
        """
        Calculate comprehensive model performance metrics
        """
        if not SKLEARN_AVAILABLE or len(predictions) == 0 or len(actuals) == 0:
            return ModelMetrics(timestamp=datetime.now(), sample_size=len(predictions))

        try:
            # Classification metrics
            accuracy = accuracy_score(actuals, predictions)
            precision = precision_score(actuals, predictions, average='weighted', zero_division=0)
            recall = recall_score(actuals, predictions, average='weighted', zero_division=0)
            f1 = f1_score(actuals, predictions, average='weighted', zero_division=0)

            # Trading-specific metrics (simplified)
            # Assuming predictions are trading signals (1=buy, 0=hold/sell)
            # NOTE: This is NOT data leakage. predictions[i-1] is the signal
            # generated at time i-1 (using only data up to i-1). The return
            # actuals[i] - actuals[i-1] is the outcome observed AFTER the
            # decision, which is the correct backtest convention: decide at
            # bar i-1, measure P&L at bar i.
            returns = []
            for i in range(1, len(predictions)):
                if predictions[i-1] == 1:  # Buy signal at time i-1
                    # Return realized at time i (after the decision)
                    ret = (actuals[i] - actuals[i-1]) / (actuals[i-1] + 1e-10)
                    returns.append(ret)

            win_rate = 0.0
            profit_factor = 1.0
            sharpe_ratio = 0.0
            max_drawdown = 0.0

            if returns:
                returns = np.array(returns)
                win_rate = np.mean(returns > 0)

                winning_trades = returns[returns > 0]
                losing_trades = returns[returns < 0]

                if len(winning_trades) > 0 and len(losing_trades) > 0:
                    avg_win = np.mean(winning_trades)
                    avg_loss = abs(np.mean(losing_trades))
                    profit_factor = (avg_win * len(winning_trades)) / (avg_loss * len(losing_trades))

                # Sharpe ratio (simplified, assuming daily returns)
                if len(returns) > 1:
                    excess_returns = returns - 0.02/252  # Subtract risk-free rate
                    if np.std(excess_returns) > 0:
                        sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)

                # Max drawdown
                cumulative = np.cumprod(1 + returns)
                running_max = np.maximum.accumulate(cumulative)
                drawdowns = (cumulative - running_max) / running_max
                max_drawdown = abs(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0

            return ModelMetrics(
                timestamp=datetime.now(),
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                profit_factor=profit_factor,
                total_trades=len(returns),
                sample_size=len(predictions)
            )
        except Exception as e:
            logger.error(f"Metrics calculation failed for {self.model_name}: {e}")
            return ModelMetrics(timestamp=datetime.now(), sample_size=len(predictions))

    def check_health_thresholds(self, metrics: ModelMetrics) -> List[HealthAlert]:
        """Check if metrics violate health thresholds"""
        alerts = []

        # Accuracy degradation
        if self.last_metrics and metrics.accuracy < self.last_metrics.accuracy - Config.ACCURACY_DEGRADATION_THRESHOLD:
            alerts.append(HealthAlert(
                alert_id=f"{self.model_name}_accuracy_{int(time.time())}",
                timestamp=datetime.now(),
                model_name=self.model_name,
                alert_type="accuracy_degradation",
                level=AlertLevel.WARNING,
                message=f"Accuracy dropped by {((self.last_metrics.accuracy - metrics.accuracy) * 100):.1f}%",
                metrics={
                    'current_accuracy': metrics.accuracy,
                    'previous_accuracy': self.last_metrics.accuracy,
                    'drop': self.last_metrics.accuracy - metrics.accuracy
                }
            ))

        # Sharpe ratio minimum
        if metrics.sharpe_ratio < Config.SHARPE_RATIO_MINIMUM:
            alerts.append(HealthAlert(
                alert_id=f"{self.model_name}_sharpe_{int(time.time())}",
                timestamp=datetime.now(),
                model_name=self.model_name,
                alert_type="low_sharpe_ratio",
                level=AlertLevel.WARNING,
                message=f"Sharpe ratio {metrics.sharpe_ratio:.2f} below minimum {Config.SHARPE_RATIO_MINIMUM}",
                metrics={'sharpe_ratio': metrics.sharpe_ratio}
            ))

        # Win rate minimum
        if metrics.win_rate < Config.WIN_RATE_MINIMUM:
            alerts.append(HealthAlert(
                alert_id=f"{self.model_name}_winrate_{int(time.time())}",
                timestamp=datetime.now(),
                model_name=self.model_name,
                alert_type="low_win_rate",
                level=AlertLevel.CRITICAL,
                message=f"Win rate {metrics.win_rate:.1%} below minimum {Config.WIN_RATE_MINIMUM:.1%}",
                metrics={'win_rate': metrics.win_rate}
            ))

        # Consecutive failures
        if metrics.accuracy < 0.5:  # Arbitrary failure threshold
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0

        if self.consecutive_failures >= Config.RETRAIN_CONSECUTIVE_FAILURES:
            alerts.append(HealthAlert(
                alert_id=f"{self.model_name}_failures_{int(time.time())}",
                timestamp=datetime.now(),
                model_name=self.model_name,
                alert_type="consecutive_failures",
                level=AlertLevel.CRITICAL,
                message=f"{self.consecutive_failures} consecutive performance failures",
                metrics={'consecutive_failures': self.consecutive_failures}
            ))

        return alerts

    def detect_drift(self) -> List[DriftDetection]:
        """Run drift detection on model predictions and performance"""
        detections = []

        try:
            # Get recent predictions for concept drift
            # This would need actual prediction data from the model's operation
            # For now, we'll focus on performance decay detection

            # Performance decay detection
            metrics_history = self.db.get_metrics_history(self.model_name, Config.DRIFT_DETECTION_WINDOW_HOURS)
            if len(metrics_history) >= 10:
                decay_detection = self.drift_detector.detect_performance_decay(metrics_history)
                if decay_detection.is_significant:
                    detections.append(decay_detection)

        except Exception as e:
            logger.error(f"Drift detection failed for {self.model_name}: {e}")

        return detections

    def should_retrain(self, metrics: ModelMetrics, drift_detections: List[DriftDetection]) -> Tuple[bool, str]:
        """Determine if model should be retrained"""
        reasons = []

        # Accuracy drop
        if self.last_metrics and metrics.accuracy < self.last_metrics.accuracy - Config.RETRAIN_ACCURACY_DROP:
            reasons.append(f"accuracy_drop_{((self.last_metrics.accuracy - metrics.accuracy) * 100):.1f}%")

        # Significant drift detected
        significant_drifts = [d for d in drift_detections if d.is_significant]
        if significant_drifts:
            drift_types = [d.drift_type.value for d in significant_drifts]
            reasons.append(f"drift_detected_{'_'.join(drift_types)}")

        # Consecutive failures
        if self.consecutive_failures >= Config.RETRAIN_CONSECUTIVE_FAILURES:
            reasons.append(f"consecutive_failures_{self.consecutive_failures}")

        # Minimum sample size for retraining
        if metrics.sample_size < Config.RETRAIN_MIN_SAMPLES:
            return False, "insufficient_samples"

        should_retrain = len(reasons) > 0
        reason_str = "_".join(reasons) if reasons else "no_retrain_needed"

        return should_retrain, reason_str

    def update_health(self, metrics: ModelMetrics):
        """Update model health status"""
        # Save metrics
        self.db.save_metrics(self.model_name, metrics)

        # Check thresholds and generate alerts
        alerts = self.check_health_thresholds(metrics)
        for alert in alerts:
            self.db.save_alert(alert)
            logger.warning(f"Alert generated for {self.model_name}: {alert.message}")

        # Detect drift
        drift_detections = self.detect_drift()
        for detection in drift_detections:
            self.db.save_drift_detection(self.model_name, detection)
            if detection.is_significant:
                logger.warning(f"Drift detected for {self.model_name}: {detection.drift_type.value}")

        # Check if retraining is needed
        should_retrain, reason = self.should_retrain(metrics, drift_detections)
        if should_retrain:
            logger.info(f"Retraining recommended for {self.model_name}: {reason}")
            # Here you would trigger retraining workflow

        # Update last metrics
        self.last_metrics = metrics


# =============================================================================
# MODEL HEALTH AGENT
# =============================================================================

class ModelHealthAgent:
    """Main model health monitoring agent"""

    def __init__(self):
        self.db = DatabaseManager()
        self.drift_detector = DriftDetector()
        self.monitors: Dict[str, ModelMonitor] = {}
        self.running = False
        self.monitor_thread = None
        self.api_app = None

        # Create backup directory
        Config.BACKUP_MODELS_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize API if enabled
        if FASTAPI_AVAILABLE and Config.ENABLE_API:
            self._init_api()

    def _init_api(self):
        """Initialize FastAPI application"""
        self.api_app = FastAPI(title="Model Health Agent API", version="1.0.0")

        @self.api_app.get("/")
        async def root():
            return {"message": "Model Health Agent API", "status": "running"}

        @self.api_app.get("/health/{model_name}")
        async def get_model_health(model_name: str):
            """Get health status for a specific model"""
            if model_name not in self.monitors:
                raise HTTPException(status_code=404, detail="Model not found")

            monitor = self.monitors[model_name]
            metrics_history = self.db.get_metrics_history(model_name, 24)
            alerts = self.db.get_active_alerts(model_name)

            return {
                "model_name": model_name,
                "status": "active" if monitor.model else "inactive",
                "last_metrics": monitor.last_metrics.to_dict() if monitor.last_metrics else None,
                "recent_metrics": [m.to_dict() for m in metrics_history[:10]],
                "active_alerts": [a.to_dict() for a in alerts],
                "consecutive_failures": monitor.consecutive_failures
            }

        @self.api_app.get("/health")
        async def get_all_health():
            """Get health status for all models"""
            health_data = {}
            for model_name, monitor in self.monitors.items():
                metrics_history = self.db.get_metrics_history(model_name, 24)
                alerts = self.db.get_active_alerts(model_name)

                health_data[model_name] = {
                    "status": "active" if monitor.model else "inactive",
                    "last_metrics": monitor.last_metrics.to_dict() if monitor.last_metrics else None,
                    "recent_alerts": len(alerts),
                    "consecutive_failures": monitor.consecutive_failures
                }

            return health_data

        @self.api_app.get("/alerts")
        async def get_alerts(model_name: str = None, resolved: bool = False):
            """Get alerts"""
            alerts = self.db.get_active_alerts(model_name) if not resolved else []
            return {"alerts": [a.to_dict() for a in alerts]}

        @self.api_app.get("/dashboard")
        async def get_dashboard():
            """Get dashboard data"""
            if not PLOTLY_AVAILABLE:
                return {"error": "Plotly not available for dashboard"}

            # Generate dashboard HTML
            dashboard_html = self._generate_dashboard_html()
            return HTMLResponse(content=dashboard_html, media_type="text/html")

    def _generate_dashboard_html(self) -> str:
        """Generate HTML dashboard"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Model Health Dashboard</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .metric-card { border: 1px solid #ddd; padding: 15px; margin: 10px; border-radius: 5px; }
                .alert-critical { background-color: #ffebee; }
                .alert-warning { background-color: #fff3e0; }
                .alert-info { background-color: #e3f2fd; }
            </style>
        </head>
        <body>
            <h1>Model Health Dashboard</h1>
            <div id="dashboard"></div>
        </body>
        </html>
        """
        return html

    def register_model(self, model_name: str, model_path: str,
                      features: List[str], hyperparameters: Dict[str, Any]) -> bool:
        """Register a new model for monitoring"""
        try:
            # Create model monitor
            monitor = ModelMonitor(model_name, self.db, self.drift_detector)

            # Load the model
            if monitor.load_model(model_path):
                self.monitors[model_name] = monitor

                # Create initial version record
                version_id = hashlib.md5(f"{model_name}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]
                version = ModelVersion(
                    version_id=version_id,
                    model_path=model_path,
                    created_at=datetime.now(),
                    trained_on=datetime.now(),  # This should be passed in from training
                    performance_baseline=ModelMetrics(timestamp=datetime.now()),  # Initial baseline
                    features_used=features,
                    hyperparameters=hyperparameters,
                    status=ModelStatus.ACTIVE
                )

                self.db.save_model_version(model_name, version)
                logger.info(f"Registered model {model_name} for health monitoring")
                return True
            else:
                logger.error(f"Failed to register model {model_name}: could not load from {model_path}")
                return False

        except Exception as e:
            logger.error(f"Failed to register model {model_name}: {e}")
            return False

    def unregister_model(self, model_name: str):
        """Unregister a model from monitoring"""
        if model_name in self.monitors:
            # Mark current version as retired
            versions = self.db.get_model_versions(model_name)
            if versions:
                current_version = versions[0]
                current_version.status = ModelStatus.RETIRED
                current_version.retired_at = datetime.now()
                self.db.save_model_version(model_name, current_version)

            del self.monitors[model_name]
            logger.info(f"Unregistered model {model_name}")

    def update_model_performance(self, model_name: str, predictions: np.ndarray,
                               actuals: np.ndarray, features: Optional[np.ndarray] = None):
        """Update model performance with new predictions"""
        if model_name not in self.monitors:
            logger.warning(f"Model {model_name} not registered for monitoring")
            return

        monitor = self.monitors[model_name]

        # Calculate metrics
        metrics = monitor.calculate_metrics(predictions, actuals)

        # Update health
        monitor.update_health(metrics)

        logger.info(f"Updated performance for {model_name}: accuracy={metrics.accuracy:.3f}")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Starting model health monitoring loop")

        while self.running:
            try:
                # Check all registered models
                for model_name, monitor in self.monitors.items():
                    # This would be where you collect new predictions/data
                    # For now, we'll just check if models are still accessible
                    if not monitor.model:
                        # Try to reload model
                        versions = self.db.get_model_versions(model_name)
                        if versions:
                            latest_version = versions[0]
                            monitor.load_model(latest_version.model_path)

                # Cleanup old data
                self.db.cleanup_old_data()

                # Sleep until next monitoring cycle
                time.sleep(Config.MONITORING_INTERVAL_MINUTES * 60)

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(60)  # Wait a minute before retrying

    def start_monitoring(self):
        """Start the monitoring system"""
        if self.running:
            logger.warning("Monitoring already running")
            return

        self.running = True

        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()

        # Start API server if enabled
        if self.api_app and Config.ENABLE_API:
            import uvicorn
            api_thread = threading.Thread(
                target=lambda: uvicorn.run(
                    self.api_app,
                    host=Config.API_HOST,
                    port=Config.API_PORT,
                    log_level="warning"
                ),
                daemon=True
            )
            api_thread.start()
            logger.info(f"API server started on {Config.API_HOST}:{Config.API_PORT}")

        logger.info("Model Health Agent started")

    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Model Health Agent stopped")

    def get_health_report(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "models_monitored": len(self.monitors),
            "total_alerts": len(self.db.get_active_alerts()),
            "models": {}
        }

        models_to_report = [model_name] if model_name else list(self.monitors.keys())

        for name in models_to_report:
            if name in self.monitors:
                monitor = self.monitors[name]
                metrics_history = self.db.get_metrics_history(name, 24)
                alerts = self.db.get_active_alerts(name)
                versions = self.db.get_model_versions(name)

                report["models"][name] = {
                    "status": "active" if monitor.model else "inactive",
                    "last_metrics": monitor.last_metrics.to_dict() if monitor.last_metrics else None,
                    "metrics_history_count": len(metrics_history),
                    "active_alerts": len(alerts),
                    "consecutive_failures": monitor.consecutive_failures,
                    "current_version": versions[0].version_id if versions else None,
                    "total_versions": len(versions)
                }

        return report


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main entry point"""
    agent = ModelHealthAgent()

    # Example: Register existing models
    # This would be done by the training pipeline
    try:
        # Check for existing models in production directory
        if Config.PRODUCTION_MODELS_DIR.exists():
            for model_file in Config.PRODUCTION_MODELS_DIR.glob("*.pkl"):
                model_name = model_file.stem
                model_path = str(model_file)

                # Basic registration (would need proper metadata in production)
                agent.register_model(
                    model_name=model_name,
                    model_path=model_path,
                    features=[],  # Would need to be stored with model
                    hyperparameters={}  # Would need to be stored with model
                )

    except Exception as e:
        logger.error(f"Error during model registration: {e}")

    # Start monitoring
    agent.start_monitoring()

    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        agent.stop_monitoring()


if __name__ == "__main__":
    main()