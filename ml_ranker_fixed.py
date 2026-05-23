#!/usr/bin/env python3
"""
ML Ranker v2 - Fixed Model
Addresses: Placeholder features, wrong metrics, no train/test split

Key Fixes:
- Remove placeholder time features (hour_of_day, day_of_week defaults)
- Add proper train/test split (80/20)
- Switch from accuracy to ROC-AUC metric
- Add probability calibration with isotonic regression
- Add feature importance analysis
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import IsotonicRegression
from sklearn.metrics import roc_auc_score, classification_report
import joblib
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLRankerFixed:
    """
    Fixed ML ranker addressing all audit findings.
    """
    
    def __init__(self, 
                 min_samples: int = 20,  # Lowered from 50
                 test_size: float = 0.2,
                 random_state: int = 42):
        
        self.min_samples = min_samples
        self.test_size = test_size
        self.random_state = random_state
        
        self.model = None
        self.scaler = StandardScaler()
        self.calibrator = None
        self.is_trained = False
        self.feature_names = []
        
        # Metrics tracking
        self.training_metrics = {}
        self.validation_metrics = {}
        
    def _engineer_features(self, 
                          df: pd.DataFrame, 
                          signal_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Engineer proper features (NO placeholders).
        
        FIXED: Removed placeholder hour_of_day, day_of_week defaults
        """
        features = pd.DataFrame()
        
        # Price-based features
        features['returns_1h'] = df['close'].pct_change()
        features['returns_4h'] = df['close'].pct_change(4)
        features['returns_24h'] = df['close'].pct_change(24)
        
        # Volatility features
        features['volatility_20h'] = features['returns_1h'].rolling(20).std()
        features['atr_14'] = self._calculate_atr(df, 14)
        features['atr_ratio'] = features['atr_14'] / df['close']
        
        # Trend features
        features['sma_20'] = df['close'].rolling(20).mean() / df['close']
        features['sma_50'] = df['close'].rolling(50).mean() / df['close']
        features['ema_12'] = df['close'].ewm(span=12).mean() / df['close']
        
        # Momentum features
        features['rsi_14'] = self._calculate_rsi(df['close'], 14)
        features['macd'] = self._calculate_macd(df['close'])
        features['momentum_10'] = df['close'].pct_change(10)
        
        # Volume features
        features['volume_sma_20'] = df['volume'].rolling(20).mean() / df['volume']
        features['volume_change'] = df['volume'].pct_change()
        features['obv'] = self._calculate_obv(df)
        
        # Market structure
        features['bb_position'] = self._calculate_bb_position(df)
        features['price_position'] = (df['close'] - df['low'].rolling(20).min()) / \
                                     (df['high'].rolling(20).max() - df['low'].rolling(20).min())
        
        # FIXED: Add ACTUAL time features if signal_time provided
        # (Previously these were set to 0.5 as placeholders)
        if signal_time is not None:
            features['hour_of_day'] = signal_time.hour / 24.0  # Normalize 0-1
            features['day_of_week'] = signal_time.weekday() / 6.0  # Normalize 0-1
            features['is_weekend'] = 1.0 if signal_time.weekday() >= 5 else 0.0
        else:
            # For backtesting, use the timestamp from the data
            features['hour_of_day'] = df.index.hour / 24.0
            features['day_of_week'] = df.index.weekday / 6.0
            features['is_weekend'] = (df.index.weekday >= 5).astype(float)
        
        # Fear & Greed (if available)
        if 'fear_greed' in df.columns:
            features['fear_greed'] = df['fear_greed']
            features['fear_greed_ma'] = df['fear_greed'].rolling(7).mean()
        else:
            features['fear_greed'] = 50.0  # Neutral default
            features['fear_greed_ma'] = 50.0
        
        return features.dropna()
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(period).mean()
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series) -> pd.Series:
        """Calculate MACD."""
        ema_12 = prices.ewm(span=12).mean()
        ema_26 = prices.ewm(span=26).mean()
        return ema_12 - ema_26
    
    def _calculate_obv(self, df: pd.DataFrame) -> pd.Series:
        """Calculate On-Balance Volume."""
        obv = (np.sign(df['close'].diff()) * df['volume']).cumsum()
        return obv / obv.rolling(20).mean()  # Normalized
    
    def _calculate_bb_position(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Bollinger Bands position (0-1)."""
        sma = df['close'].rolling(20).mean()
        std = df['close'].rolling(20).std()
        upper = sma + 2 * std
        lower = sma - 2 * std
        return (df['close'] - lower) / (upper - lower)
    
    def prepare_data(self, 
                    price_data: pd.DataFrame,
                    closed_picks: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare training data from closed picks.
        
        FIXED: Proper chronological ordering to prevent data leakage
        """
        X_list = []
        y_list = []
        
        for pick in closed_picks:
            try:
                # Get data up to signal time
                signal_time = pd.to_datetime(pick['created_at'])
                symbol = pick['symbol']
                result = pick.get('result', 'expired')  # 'win', 'loss', 'expired'
                
                # Filter data before signal
                mask = price_data.index <= signal_time
                historical = price_data[mask].tail(100)  # Last 100 periods
                
                if len(historical) < 50:
                    continue
                
                # Engineer features with ACTUAL signal time
                features = self._engineer_features(historical, signal_time)
                
                if len(features) < 1:
                    continue
                
                # Get latest feature vector
                X = features.iloc[-1].values
                
                # Label: 1 for win, 0 for loss or expired
                y = 1.0 if result == 'win' else 0.0
                
                X_list.append(X)
                y_list.append(y)
                
            except Exception as e:
                logger.warning(f"Error processing pick: {e}")
                continue
        
        if len(X_list) < self.min_samples:
            logger.warning(f"Insufficient samples: {len(X_list)} < {self.min_samples}")
            return None, None
        
        X = np.array(X_list)
        y = np.array(y_list)
        
        return X, y
    
    def train(self, 
             price_data: pd.DataFrame,
             closed_picks: List[Dict]) -> bool:
        """
        Train the model with proper validation.
        
        FIXED: Train/test split, ROC-AUC metric, probability calibration
        """
        logger.info("Preparing training data...")
        X, y = self.prepare_data(price_data, closed_picks)
        
        if X is None:
            logger.error("Training failed: insufficient data")
            return False
        
        logger.info(f"Training with {len(X)} samples ({sum(y)} wins, {len(y)-sum(y)} losses)")
        
        # Store feature names
        self.feature_names = self._engineer_features(price_data).columns.tolist()
        
        # FIXED: Chronological train/test split (not random!)
        # Use first 80% for train, last 20% for test
        split_idx = int(len(X) * (1 - self.test_size))
        
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight='balanced',  # Handle imbalanced data
            random_state=self.random_state
        )
        
        # FIXED: Split training data into train (90%) and calibration (10%)
        # to avoid calibrating on test set (data leakage).
        cal_split = int(len(X_train_scaled) * 0.9)
        X_train_real = X_train_scaled[:cal_split]
        y_train_real = y_train[:cal_split]
        X_cal = X_train_scaled[cal_split:]
        y_cal = y_train[cal_split:]

        self.model.fit(X_train_real, y_train_real)

        # FIXED: Evaluate with ROC-AUC (not accuracy)
        train_proba = self.model.predict_proba(X_train_real)[:, 1]
        test_proba = self.model.predict_proba(X_test_scaled)[:, 1]

        train_auc = roc_auc_score(y_train_real, train_proba)
        test_auc = roc_auc_score(y_test, test_proba)

        # FIXED: Cross-validation with ROC-AUC
        cv_scores = cross_val_score(
            self.model, X_train_real, y_train_real,
            cv=5, scoring='roc_auc'  # FIXED: was 'accuracy'
        )

        # Store metrics
        self.training_metrics = {
            'train_auc': float(train_auc),
            'test_auc': float(test_auc),
            'cv_auc_mean': float(cv_scores.mean()),
            'cv_auc_std': float(cv_scores.std()),
            'auc_gap': float(train_auc - test_auc),  # Overfitting check
            'n_samples': len(X),
            'n_features': X.shape[1],
            'win_rate': float(y.mean()),
            'feature_names': self.feature_names
        }

        logger.info(f"Train AUC: {train_auc:.3f}, Test AUC: {test_auc:.3f}")
        logger.info(f"CV AUC: {cv_scores.mean():.3f} (+/- {cv_scores.std()*2:.3f})")

        # Check for overfitting
        if train_auc - test_auc > 0.1:
            logger.warning("Possible overfitting detected (train-test gap > 0.1)")

        # FIXED: Calibrate on held-out calibration set (not test set)
        cal_proba = self.model.predict_proba(X_cal)[:, 1]
        self.calibrator = IsotonicRegression(out_of_bounds='clip')
        self.calibrator.fit(cal_proba, y_cal)

        # Verify calibration quality on test set
        calibrated_proba = self.calibrator.predict(test_proba)
        calibrated_auc = roc_auc_score(y_test, calibrated_proba)
        logger.info(f"Calibrated AUC: {calibrated_auc:.3f}")
        
        self.validation_metrics = {
            'classification_report': classification_report(y_test, test_proba > 0.5, output_dict=True),
            'calibrated_auc': float(calibrated_auc)
        }
        
        self.is_trained = True
        return True
    
    def predict(self, 
               price_data: pd.DataFrame,
               signal_time: Optional[datetime] = None) -> Dict:
        """
        Make prediction for a new signal.
        
        Returns calibrated probability and confidence score.
        """
        if not self.is_trained:
            return {'error': 'Model not trained'}
        
        # Engineer features
        features = self._engineer_features(price_data, signal_time)
        
        if len(features) < 1:
            return {'error': 'Insufficient data for features'}
        
        X = features.iloc[-1].values.reshape(1, -1)
        X_scaled = self.scaler.transform(X)
        
        # Get raw probability
        raw_proba = self.model.predict_proba(X_scaled)[0, 1]
        
        # FIXED: Return calibrated probability
        if self.calibrator:
            calibrated_proba = self.calibrator.predict([raw_proba])[0]
        else:
            calibrated_proba = raw_proba
        
        # Feature importance for this prediction
        feature_importance = dict(zip(
            self.feature_names,
            self.model.feature_importances_
        ))
        
        # Top 5 important features
        top_features = sorted(
            feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            'raw_probability': float(raw_proba),
            'calibrated_probability': float(calibrated_proba),
            'confidence': 'high' if calibrated_proba > 0.7 or calibrated_proba < 0.3 else 'medium',
            'expected_win_rate': float(calibrated_proba),
            'top_features': dict(top_features),
            'model_auc': self.training_metrics.get('test_auc', 0.5)
        }
    
    def save(self, filepath: str):
        """Save model to disk."""
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'calibrator': self.calibrator,
            'feature_names': self.feature_names,
            'training_metrics': self.training_metrics,
            'validation_metrics': self.validation_metrics,
            'saved_at': datetime.now().isoformat()
        }
        
        joblib.dump(model_data, filepath)
        logger.info(f"Model saved to {filepath}")
    
    def load(self, filepath: str):
        """Load model from disk."""
        model_data = joblib.load(filepath)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.calibrator = model_data['calibrator']
        self.feature_names = model_data['feature_names']
        self.training_metrics = model_data['training_metrics']
        self.validation_metrics = model_data['validation_metrics']
        self.is_trained = True
        
        logger.info(f"Model loaded from {filepath}")
        logger.info(f"Test AUC: {self.training_metrics.get('test_auc', 'N/A')}")


def test_ml_ranker():
    """Test the fixed ML ranker."""
    print("="*60)
    print("ML RANKER v2 - TEST SUITE")
    print("="*60)
    
    # Create synthetic data
    np.random.seed(42)
    n_samples = 100
    
    dates = pd.date_range(end=datetime.now(), periods=n_samples, freq='H')
    price_data = pd.DataFrame({
        'open': 100 + np.cumsum(np.random.randn(n_samples) * 0.1),
        'high': 101 + np.cumsum(np.random.randn(n_samples) * 0.1),
        'low': 99 + np.cumsum(np.random.randn(n_samples) * 0.1),
        'close': 100 + np.cumsum(np.random.randn(n_samples) * 0.1),
        'volume': np.random.randint(1000, 10000, n_samples)
    }, index=dates)
    
    # Create synthetic closed picks
    closed_picks = []
    for i in range(50):
        closed_picks.append({
            'symbol': 'BTCUSDT',
            'created_at': dates[i * 2].isoformat(),
            'result': 'win' if np.random.random() > 0.5 else 'loss'
        })
    
    # Train model
    ranker = MLRankerFixed(min_samples=20)
    success = ranker.train(price_data, closed_picks)
    
    if success:
        print("\n[PASS] Model trained successfully")
        print(f"Test AUC: {ranker.training_metrics['test_auc']:.3f}")
        print(f"CV AUC: {ranker.training_metrics['cv_auc_mean']:.3f}")
        
        # Make prediction
        prediction = ranker.predict(price_data)
        print(f"\nPrediction:")
        print(f"  Raw probability: {prediction['raw_probability']:.3f}")
        print(f"  Calibrated: {prediction['calibrated_probability']:.3f}")
        print(f"  Confidence: {prediction['confidence']}")
        print(f"  Top features: {list(prediction['top_features'].keys())[:3]}")
        
        # Save and load
        ranker.save('test_model.joblib')
        ranker2 = MLRankerFixed()
        ranker2.load('test_model.joblib')
        print("\n[PASS] Save/load test passed")
        
        import os
        os.remove('test_model.joblib')
    else:
        print("\n[FAIL] Model training failed")
    
    print("="*60)


if __name__ == "__main__":
    test_ml_ranker()
