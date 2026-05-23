"""
ML Consensus Module for Signal Aggregator

Uses forward test results to train a model that predicts signal success probability.
Integrates with existing Bayesian confidence calculator.
"""

import os
import sys
import json
import sqlite3
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLConsensusEngine:
    """
    Machine Learning consensus engine for signal aggregation.
    
    Trains on forward test results to predict signal success probability.
    Combines with existing Bayesian confidence for enhanced consensus.
    """
    
    def __init__(self, db_path: str = "forward_tracking.db"):
        """
        Initialize ML consensus engine.
        
        Args:
            db_path: Path to forward testing SQLite database
        """
        self.db_path = db_path
        self.model = None
        self.feature_columns = None
        self.training_stats = {}
        
        # Model configuration
        self.min_samples = 50  # Minimum samples needed for training
        self.test_size = 0.2
        self.model_version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        logger.info(f"ML Consensus Engine initialized (db: {db_path})")
    
    def _load_training_data(self) -> pd.DataFrame:
        """
        Load historical signal data with outcomes from forward database.
        
        Returns:
            DataFrame with signal features and outcomes
        """
        if not os.path.exists(self.db_path):
            logger.warning(f"Database not found: {self.db_path}")
            return pd.DataFrame()
        
        conn = sqlite3.connect(self.db_path)
        
        # Query resolved signals with outcomes
        query = """
        SELECT 
            s.signal_id,
            s.symbol,
            s.direction,
            s.entry_price,
            s.tp_price,
            s.sl_price,
            s.atr,
            s.system,
            s.confidence,
            s.timestamp,
            s.status,
            s.pnl_pct,
            s.resolved_at,
            p.regime,
            p.volatility_regime,
            p.trend_strength
        FROM signals s
        LEFT JOIN performance_stats p ON s.system = p.system
        WHERE s.status IN ('tp_hit', 'sl_hit', 'expired')
        ORDER BY s.timestamp DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if len(df) < self.min_samples:
            logger.warning(f"Insufficient training data: {len(df)} samples (need {self.min_samples})")
            return df
        
        logger.info(f"Loaded {len(df)} historical signals for training")
        return df
    
    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer features from raw signal data.
        
        Args:
            df: Raw signal DataFrame
            
        Returns:
            DataFrame with engineered features
        """
        if df.empty:
            return df
        
        # Create copy to avoid modifying original
        features = df.copy()
        
        # Price-based features
        features['risk_reward_ratio'] = (
            (features['tp_price'] - features['entry_price']).abs() /
            (features['entry_price'] - features['sl_price']).abs()
        )
        
        # ATR-normalized distances
        features['tp_distance_atr'] = (
            (features['tp_price'] - features['entry_price']).abs() / features['atr']
        )
        features['sl_distance_atr'] = (
            (features['entry_price'] - features['sl_price']).abs() / features['atr']
        )
        
        # Direction encoding
        features['direction_long'] = (features['direction'] == 'LONG').astype(int)
        
        # Time features
        features['timestamp'] = pd.to_datetime(features['timestamp'])
        features['hour'] = features['timestamp'].dt.hour
        features['day_of_week'] = features['timestamp'].dt.dayofweek
        
        # System performance features (would need historical system stats)
        # For now, use confidence as proxy
        features['system_confidence'] = features['confidence']
        
        # Regime encoding
        regime_map = {'BULL': 1, 'SIDEWAYS': 0, 'BEAR': -1, 'HIGH_VOL': 2}
        features['regime_encoded'] = features['regime'].map(regime_map).fillna(0)
        
        # Volatility regime encoding
        vol_map = {'LOW': 0, 'NORMAL': 1, 'HIGH': 2, 'EXTREME': 3}
        features['volatility_encoded'] = features['volatility_regime'].map(vol_map).fillna(1)
        
        # Target variable: 1 for TP hit, 0 for SL hit or expired
        features['target'] = (features['status'] == 'tp_hit').astype(int)
        
        return features
    
    def train_model(self, force: bool = False) -> bool:
        """
        Train ML model on forward test results.
        
        Args:
            force: Force retraining even if model exists
            
        Returns:
            True if training successful, False otherwise
        """
        # Check if model already exists and not forced
        model_path = self._get_model_path()
        if os.path.exists(model_path) and not force:
            logger.info(f"Model already exists at {model_path}, skipping training")
            self.load_model()
            return True
        
        # Load training data
        df = self._load_training_data()
        if len(df) < self.min_samples:
            logger.warning(f"Cannot train: insufficient data ({len(df)} < {self.min_samples})")
            return False
        
        # Engineer features
        features = self._engineer_features(df)
        
        # Select feature columns
        self.feature_columns = [
            'risk_reward_ratio', 'tp_distance_atr', 'sl_distance_atr',
            'direction_long', 'hour', 'day_of_week', 'system_confidence',
            'regime_encoded', 'volatility_encoded'
        ]
        
        # Prepare training data
        X = features[self.feature_columns].fillna(0)
        y = features['target']
        
        # Train/test split (time-based to avoid leakage)
        split_idx = int(len(X) * (1 - self.test_size))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        logger.info(f"Training on {len(X_train)} samples, testing on {len(X_test)}")
        
        try:
            from sklearn.ensemble import GradientBoostingClassifier
            from sklearn.metrics import roc_auc_score, accuracy_score, classification_report
            
            # Train gradient boosting model
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                random_state=42
            )
            
            self.model.fit(X_train, y_train)
            
            # Evaluate
            y_pred = self.model.predict(X_test)
            y_pred_proba = self.model.predict_proba(X_test)[:, 1]
            
            accuracy = accuracy_score(y_test, y_pred)
            roc_auc = roc_auc_score(y_test, y_pred_proba)
            
            self.training_stats = {
                'version': self.model_version,
                'trained_at': datetime.now().isoformat(),
                'n_samples': len(df),
                'n_train': len(X_train),
                'n_test': len(X_test),
                'accuracy': float(accuracy),
                'roc_auc': float(roc_auc),
                'feature_importance': dict(zip(
                    self.feature_columns,
                    self.model.feature_importances_.tolist()
                ))
            }
            
            logger.info(f"Training complete: Accuracy={accuracy:.3f}, ROC-AUC={roc_auc:.3f}")
            
            # Save model
            self._save_model()
            
            return True
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return False
    
    def predict_signal_quality(self, signal: Dict) -> Dict:
        """
        Predict success probability for a new signal.
        
        Args:
            signal: Signal dictionary with required fields
            
        Returns:
            Dictionary with ml_confidence and metadata
        """
        if self.model is None:
            self.load_model()
        
        if self.model is None:
            logger.warning("No model available, returning neutral prediction")
            return {
                'ml_confidence': 0.5,
                'ml_prob_success': 0.5,
                'model_version': None,
                'status': 'no_model'
            }
        
        try:
            # Extract features from signal
            entry = signal.get('entry_price', 0)
            tp = signal.get('tp_price', entry)
            sl = signal.get('sl_price', entry)
            atr = signal.get('atr', abs(tp - sl) / 3)
            
            # Calculate features
            rr_ratio = abs(tp - entry) / abs(entry - sl) if sl != entry else 1.0
            tp_dist_atr = abs(tp - entry) / atr if atr > 0 else 1.0
            sl_dist_atr = abs(entry - sl) / atr if atr > 0 else 1.0
            
            direction_long = 1 if signal.get('direction') == 'LONG' else 0
            
            now = datetime.now()
            hour = now.hour
            day_of_week = now.weekday()
            
            system_confidence = signal.get('confidence', 0.5)
            
            regime = signal.get('regime', 'SIDEWAYS')
            regime_map = {'BULL': 1, 'SIDEWAYS': 0, 'BEAR': -1, 'HIGH_VOL': 2}
            regime_encoded = regime_map.get(regime, 0)
            
            volatility_encoded = 1  # Default NORMAL
            
            # Create feature vector
            X = pd.DataFrame([{
                'risk_reward_ratio': rr_ratio,
                'tp_distance_atr': tp_dist_atr,
                'sl_distance_atr': sl_dist_atr,
                'direction_long': direction_long,
                'hour': hour,
                'day_of_week': day_of_week,
                'system_confidence': system_confidence,
                'regime_encoded': regime_encoded,
                'volatility_encoded': volatility_encoded
            }])
            
            # Predict
            prob_success = self.model.predict_proba(X)[0, 1]
            
            # Calibrate to 0-1 scale
            ml_confidence = prob_success
            
            return {
                'ml_confidence': float(ml_confidence),
                'ml_prob_success': float(prob_success),
                'model_version': self.model_version,
                'training_stats': self.training_stats,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return {
                'ml_confidence': 0.5,
                'ml_prob_success': 0.5,
                'model_version': self.model_version,
                'status': f'error: {str(e)}'
            }
    
    def combine_with_bayesian(self, bayesian_confidence: float, 
                             ml_confidence: float,
                             bayesian_weight: float = 0.5) -> float:
        """
        Combine Bayesian and ML confidence scores.
        
        Args:
            bayesian_confidence: Confidence from Bayesian calculator
            ml_confidence: Confidence from ML model
            bayesian_weight: Weight for Bayesian (0-1), ML gets 1-weight
            
        Returns:
            Combined confidence score
        """
        ml_weight = 1 - bayesian_weight
        combined = (bayesian_weight * bayesian_confidence + 
                   ml_weight * ml_confidence)
        
        return combined
    
    def _get_model_path(self) -> str:
        """Get path for saving/loading model."""
        model_dir = Path("signal_aggregator/models")
        model_dir.mkdir(parents=True, exist_ok=True)
        return str(model_dir / f"ml_consensus_{self.model_version}.pkl")
    
    def _get_stats_path(self) -> str:
        """Get path for saving/loading training stats."""
        model_dir = Path("signal_aggregator/models")
        model_dir.mkdir(parents=True, exist_ok=True)
        return str(model_dir / f"ml_consensus_{self.model_version}_stats.json")
    
    def _save_model(self):
        """Save trained model and stats to disk."""
        try:
            import joblib
            
            model_path = self._get_model_path()
            joblib.dump(self.model, model_path)
            
            stats_path = self._get_stats_path()
            with open(stats_path, 'w') as f:
                json.dump(self.training_stats, f, indent=2)
            
            logger.info(f"Model saved to {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
    
    def load_model(self) -> bool:
        """
        Load latest trained model from disk.
        
        Returns:
            True if model loaded successfully
        """
        try:
            import joblib
            
            model_dir = Path("signal_aggregator/models")
            if not model_dir.exists():
                return False
            
            # Find latest model
            model_files = list(model_dir.glob("ml_consensus_*.pkl"))
            if not model_files:
                return False
            
            latest_model = max(model_files, key=lambda p: p.stat().st_mtime)
            
            self.model = joblib.load(latest_model)
            
            # Load stats
            stats_file = latest_model.with_suffix('').with_name(
                latest_model.stem + '_stats.json'
            )
            if stats_file.exists():
                with open(stats_file) as f:
                    self.training_stats = json.load(f)
                    self.model_version = self.training_stats.get('version', 'unknown')
            
            logger.info(f"Model loaded from {latest_model}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from trained model."""
        if not self.training_stats or 'feature_importance' not in self.training_stats:
            return {}
        
        return self.training_stats['feature_importance']


class EnhancedConfidenceCalculator:
    """
    Enhanced confidence calculator combining Bayesian and ML approaches.
    
    This wraps the existing BayesianConfidenceCalculator and adds
    ML-based predictions from forward test results.
    """
    
    def __init__(self, db_path: str = "forward_tracking.db"):
        """
        Initialize enhanced calculator.
        
        Args:
            db_path: Path to forward testing database
        """
        self.ml_engine = MLConsensusEngine(db_path)
        
        # Try to load or train model
        if not self.ml_engine.load_model():
            logger.info("No existing model found, attempting to train...")
            self.ml_engine.train_model()
    
    def calculate_enhanced_confidence(self, signal: Dict, 
                                     bayesian_confidence: float) -> Dict:
        """
        Calculate enhanced confidence combining Bayesian and ML.
        
        Args:
            signal: Signal data dictionary
            bayesian_confidence: Existing Bayesian confidence
            
        Returns:
            Dictionary with confidence scores and metadata
        """
        # Get ML prediction
        ml_result = self.ml_engine.predict_signal_quality(signal)
        ml_confidence = ml_result['ml_confidence']
        
        # Combine scores (weight Bayesian higher initially until ML proves itself)
        ml_weight = 0.3  # Start conservative
        
        # Increase ML weight as we get more training data
        if self.ml_engine.training_stats:
            n_samples = self.ml_engine.training_stats.get('n_samples', 0)
            if n_samples > 200:
                ml_weight = 0.4
            if n_samples > 500:
                ml_weight = 0.5
        
        bayesian_weight = 1 - ml_weight
        
        combined = self.ml_engine.combine_with_bayesian(
            bayesian_confidence, ml_confidence, bayesian_weight
        )
        
        return {
            'confidence': combined,
            'bayesian_confidence': bayesian_confidence,
            'ml_confidence': ml_confidence,
            'ml_prob_success': ml_result['ml_prob_success'],
            'ml_weight': ml_weight,
            'bayesian_weight': bayesian_weight,
            'model_version': ml_result['model_version'],
            'model_status': ml_result['status'],
            'training_samples': self.ml_engine.training_stats.get('n_samples', 0)
        }


# Test function
def test_ml_consensus():
    """Test ML consensus engine."""
    print("Testing ML Consensus Engine...")
    
    # Create test instance
    engine = MLConsensusEngine(db_path="test_forward.db")
    
    # Test with dummy signal
    test_signal = {
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'entry_price': 85000,
        'tp_price': 90000,
        'sl_price': 82000,
        'atr': 2000,
        'confidence': 0.7,
        'regime': 'BULL'
    }
    
    result = engine.predict_signal_quality(test_signal)
    print(f"ML Prediction: {result}")
    
    # Test enhanced calculator
    enhanced = EnhancedConfidenceCalculator(db_path="test_forward.db")
    result = enhanced.calculate_enhanced_confidence(test_signal, 0.65)
    print(f"Enhanced Confidence: {result}")
    
    print("Test complete!")


if __name__ == "__main__":
    test_ml_consensus()
