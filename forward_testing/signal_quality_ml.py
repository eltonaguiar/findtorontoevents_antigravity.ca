"""
Signal Quality ML Predictor

Predicts which signals are likely to succeed BEFORE execution.
Uses historical forward test results to train quality classifiers.
Filters out low-quality signals to improve overall win rate.
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignalQualityPredictor:
    """
    ML-based signal quality prediction.
    
    Trains on forward test outcomes to predict signal success
    before the trade is executed. Can filter out poor-quality signals.
    """
    
    def __init__(self, db_path: str = "forward_tracking.db", 
                 quality_threshold: float = 0.6):
        """
        Initialize quality predictor.
        
        Args:
            db_path: Path to forward testing database
            quality_threshold: Minimum quality score to accept signal (0-1)
        """
        self.db_path = db_path
        self.quality_threshold = quality_threshold
        
        # Models for different aspects
        self.tp_hit_model = None  # Predict probability of TP hit
        self.sl_avoidance_model = None  # Predict probability of avoiding SL
        self.expiration_model = None  # Predict probability of expiration
        
        self.min_samples = 100
        self.feature_columns = None
        self.model_stats = {}
        
        logger.info(f"Signal Quality Predictor initialized (threshold: {quality_threshold})")
    
    def _load_historical_signals(self) -> pd.DataFrame:
        """Load historical signals with outcomes."""
        if not os.path.exists(self.db_path):
            logger.warning(f"Database not found: {self.db_path}")
            return pd.DataFrame()
        
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT 
            s.*,
            CASE 
                WHEN s.status = 'tp_hit' THEN 1 
                WHEN s.status = 'sl_hit' THEN 0
                WHEN s.status = 'expired' THEN 0
                ELSE NULL
            END as success,
            CASE
                WHEN s.status = 'expired' THEN 1
                ELSE 0
            END as expired,
            julianday(s.resolved_at) - julianday(s.timestamp) as duration_days
        FROM signals s
        WHERE s.status IN ('tp_hit', 'sl_hit', 'expired')
        ORDER BY s.timestamp DESC
        LIMIT 5000
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        logger.info(f"Loaded {len(df)} historical signals")
        return df
    
    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer features for quality prediction."""
        if df.empty:
            return df
        
        f = df.copy()
        
        # Price structure features
        f['rr_ratio'] = np.where(
            f['direction'] == 'LONG',
            (f['tp_price'] - f['entry_price']) / (f['entry_price'] - f['sl_price']),
            (f['entry_price'] - f['tp_price']) / (f['sl_price'] - f['entry_price'])
        )
        
        # Handle division by zero
        f['rr_ratio'] = f['rr_ratio'].replace([np.inf, -np.inf], 10).fillna(2)

        # ATR-normalized distances
        f['tp_dist_atr'] = np.abs(f['tp_price'] - f['entry_price']) / f['atr'].clip(lower=0.001)
        f['sl_dist_atr'] = np.abs(f['entry_price'] - f['sl_price']) / f['atr'].clip(lower=0.001)

        # Signal characteristics
        f['direction_long'] = (f['direction'] == 'LONG').astype(int)
        f['high_confidence'] = (f['confidence'] > 0.7).astype(int)
        f['very_high_confidence'] = (f['confidence'] > 0.85).astype(int)

        # Time features
        f['timestamp'] = pd.to_datetime(f['timestamp'])
        f['hour'] = f['timestamp'].dt.hour
        f['is_weekend'] = f['timestamp'].dt.dayofweek.isin([5, 6]).astype(int)

        # Session encoding
        f['is_asian_session'] = ((f['hour'] >= 0) & (f['hour'] < 8)).astype(int)
        f['is_london_session'] = ((f['hour'] >= 8) & (f['hour'] < 16)).astype(int)
        f['is_ny_session'] = ((f['hour'] >= 13) & (f['hour'] < 21)).astype(int)

        # Symbol category
        f['is_btc'] = f['symbol'].str.contains('BTC', case=False).astype(int)
        f['is_eth'] = f['symbol'].str.contains('ETH', case=False).astype(int)
        f['is_major'] = f['symbol'].str.contains('BTC|ETH', case=False).astype(int)

        # TP/SL tightness (tighter = more aggressive)
        f['tight_tp'] = (f['tp_dist_atr'] < 2.5).astype(int)
        f['tight_sl'] = (f['sl_dist_atr'] < 1.5).astype(int)
        f['wide_tp'] = (f['tp_dist_atr'] > 5).astype(int)

        # ── New quality features ───────────────────────────────────────────

        # R:R quality tiers (better granularity than raw ratio alone)
        f['rr_below_min'] = (f['rr_ratio'] < 1.2).astype(int)    # sub-commission edge
        f['rr_good'] = (f['rr_ratio'] >= 1.5).astype(int)         # solid edge
        f['rr_excellent'] = (f['rr_ratio'] >= 2.0).astype(int)    # strong edge

        # Hull Moving Avg (HMA) trend alignment — stored in metadata when available.
        # hma_slope: +1 = uptrend, -1 = downtrend, 0 = flat/unknown.
        # A LONG signal against a bearish HMA slope is a counter-trend entry (higher risk).
        # Sentinel -1 used when hma_slope is not provided so the model can distinguish
        # "not aligned" (0) from "data unavailable" (-1) without biasing toward alignment.
        if 'hma_slope' in f.columns:
            f['hma_aligned'] = np.where(
                (f['direction'] == 'LONG') & (f['hma_slope'] > 0), 1,
                np.where((f['direction'] == 'SHORT') & (f['hma_slope'] < 0), 1, 0)
            )
            # counter_trend = explicitly opposed to HMA; unknown = -1 treated as neutral
            f['hma_counter_trend'] = np.where(
                (f['direction'] == 'LONG') & (f['hma_slope'] < 0), 1,
                np.where((f['direction'] == 'SHORT') & (f['hma_slope'] > 0), 1, 0)
            )
        else:
            f['hma_aligned'] = -1      # sentinel: data not available — model treats as neutral
            f['hma_counter_trend'] = -1

        # Volume expansion — current bar volume vs 20-bar average.
        # volume_ratio > 1.2 means volume expanded at entry → higher conviction.
        if 'volume_ratio' in f.columns:
            f['volume_confirmed'] = (f['volume_ratio'] >= 1.2).astype(int)
            f['volume_weak'] = (f['volume_ratio'] < 0.8).astype(int)
        else:
            f['volume_confirmed'] = 0
            f['volume_weak'] = 0

        # Multi-timeframe RSI alignment (1h + 4h).
        # Both timeframes agreeing on direction reduces false signals.
        if 'rsi_1h' in f.columns and 'rsi_4h' in f.columns:
            long_aligned = (
                (f['direction'] == 'LONG') &
                (f['rsi_1h'] > 45) & (f['rsi_1h'] < 70) &
                (f['rsi_4h'] > 45)
            )
            short_aligned = (
                (f['direction'] == 'SHORT') &
                (f['rsi_1h'] < 55) & (f['rsi_1h'] > 30) &
                (f['rsi_4h'] < 55)
            )
            f['mtf_rsi_aligned'] = (long_aligned | short_aligned).astype(int)
            # Overbought LONG entry or oversold SHORT entry — fading potential
            f['rsi_overbought_long'] = (
                (f['direction'] == 'LONG') & (f['rsi_1h'] > 70)
            ).astype(int)
            f['rsi_oversold_short'] = (
                (f['direction'] == 'SHORT') & (f['rsi_1h'] < 30)
            ).astype(int)
        else:
            f['mtf_rsi_aligned'] = 0
            f['rsi_overbought_long'] = 0
            f['rsi_oversold_short'] = 0

        # System performance (if available)
        if 'system' in f.columns:
            system_success = f.groupby('system')['success'].mean()
            f['system_historical_wr'] = f['system'].map(system_success).fillna(0.5)
        else:
            f['system_historical_wr'] = 0.5

        self.feature_columns = [
            'rr_ratio', 'tp_dist_atr', 'sl_dist_atr', 'direction_long',
            'high_confidence', 'very_high_confidence', 'hour', 'is_weekend',
            'is_asian_session', 'is_london_session', 'is_ny_session',
            'is_btc', 'is_eth', 'is_major', 'tight_tp', 'tight_sl', 'wide_tp',
            'system_historical_wr',
            # Quality enhancement features
            'rr_below_min', 'rr_good', 'rr_excellent',
            'hma_aligned', 'hma_counter_trend',
            'volume_confirmed', 'volume_weak',
            'mtf_rsi_aligned', 'rsi_overbought_long', 'rsi_oversold_short',
        ]

        return f
    
    def train_models(self) -> bool:
        """Train all quality prediction models."""
        df = self._load_historical_signals()
        
        if len(df) < self.min_samples:
            logger.warning(f"Insufficient data: {len(df)} samples (need {self.min_samples})")
            return False
        
        f = self._engineer_features(df)
        
        X = f[self.feature_columns].fillna(0)
        
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import cross_val_score
            
            # Model 1: TP Hit Prediction
            y_tp = f['success'].fillna(0)
            self.tp_hit_model = RandomForestClassifier(
                n_estimators=100, max_depth=6, random_state=42
            )
            self.tp_hit_model.fit(X, y_tp)
            
            tp_scores = cross_val_score(self.tp_hit_model, X, y_tp, cv=5, scoring='roc_auc')
            logger.info(f"TP Hit Model - ROC-AUC: {tp_scores.mean():.3f} (+/- {tp_scores.std()*2:.3f})")
            
            # Model 2: Expiration Prediction (we want to avoid expiration)
            y_exp = f['expired'].fillna(0)
            self.expiration_model = RandomForestClassifier(
                n_estimators=100, max_depth=6, random_state=43
            )
            self.expiration_model.fit(X, y_exp)
            
            exp_scores = cross_val_score(self.expiration_model, X, y_exp, cv=5, scoring='roc_auc')
            logger.info(f"Expiration Model - ROC-AUC: {exp_scores.mean():.3f} (+/- {exp_scores.std()*2:.3f})")
            
            # Store stats
            self.model_stats = {
                'trained_at': datetime.now().isoformat(),
                'n_samples': len(df),
                'tp_hit_roc_auc': float(tp_scores.mean()),
                'expiration_roc_auc': float(exp_scores.mean()),
                'win_rate_improvement': self._estimate_improvement(f, X)
            }
            
            self._save_models()
            
            return True
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return False
    
    def _estimate_improvement(self, df: pd.DataFrame, X: pd.DataFrame) -> float:
        """Estimate win rate improvement from quality filtering."""
        if self.tp_hit_model is None:
            return 0.0
        
        # Get predictions
        prob_tp = self.tp_hit_model.predict_proba(X)[:, 1]
        prob_exp = self.expiration_model.predict_proba(X)[:, 1]
        
        # Calculate quality score
        quality = prob_tp * (1 - prob_exp)
        
        # Compare win rate above/below threshold
        baseline_wr = df['success'].mean()
        
        high_quality_mask = quality >= self.quality_threshold
        if high_quality_mask.sum() < 10:
            return 0.0
        
        filtered_wr = df.loc[high_quality_mask, 'success'].mean()
        improvement = (filtered_wr - baseline_wr) * 100
        
        retention_rate = high_quality_mask.mean()
        
        logger.info(f"Quality filtering: Baseline WR {baseline_wr:.1%} -> Filtered WR {filtered_wr:.1%} "
                   f"(Improvement: +{improvement:.1f}pp, Retention: {retention_rate:.1%})")
        
        return improvement
    
    def predict_quality(self, signal: Dict) -> Dict:
        """
        Predict quality of a new signal.
        
        Returns quality score and recommendation.
        """
        if self.tp_hit_model is None:
            self.load_models()
        
        if self.tp_hit_model is None:
            return {
                'quality_score': 0.5,
                'prob_tp_hit': 0.5,
                'prob_expiration': 0.3,
                'recommendation': 'PASS',
                'reason': 'No model available',
                'confidence': 'low'
            }
        
        try:
            # Extract features from signal
            entry = signal.get('entry_price', 0)
            tp = signal.get('tp_price', entry)
            sl = signal.get('sl_price', entry)
            atr = signal.get('atr', abs(tp - sl) / 3)
            direction = signal.get('direction', 'LONG')
            confidence = signal.get('confidence', 0.5)
            symbol = signal.get('symbol', 'UNKNOWN')

            # Calculate features
            rr_ratio = abs(tp - entry) / abs(entry - sl) if sl != entry else 2.0
            tp_dist_atr = abs(tp - entry) / max(atr, 0.001)
            sl_dist_atr = abs(entry - sl) / max(atr, 0.001)

            now = datetime.now()
            hour = now.hour

            hma_slope = signal.get('hma_slope', None)
            volume_ratio = signal.get('volume_ratio', None)
            rsi_1h = signal.get('rsi_1h', None)
            rsi_4h = signal.get('rsi_4h', None)

            # Derive HMA features
            if hma_slope is not None:
                hma_aligned = 1 if (
                    (direction == 'LONG' and hma_slope > 0) or
                    (direction == 'SHORT' and hma_slope < 0)
                ) else 0
                hma_counter_trend = 1 if (
                    (direction == 'LONG' and hma_slope < 0) or
                    (direction == 'SHORT' and hma_slope > 0)
                ) else 0
            else:
                hma_aligned = -1
                hma_counter_trend = -1

            # Derive volume features
            if volume_ratio is not None:
                volume_confirmed = 1 if volume_ratio >= 1.2 else 0
                volume_weak = 1 if volume_ratio < 0.8 else 0
            else:
                volume_confirmed = 0
                volume_weak = 0

            # Derive MTF RSI features
            if rsi_1h is not None and rsi_4h is not None:
                if direction == 'LONG':
                    mtf_rsi_aligned = 1 if (45 < rsi_1h < 70 and rsi_4h > 45) else 0
                    rsi_overbought_long = 1 if rsi_1h > 70 else 0
                    rsi_oversold_short = 0
                else:
                    mtf_rsi_aligned = 1 if (30 < rsi_1h < 55 and rsi_4h < 55) else 0
                    rsi_overbought_long = 0
                    rsi_oversold_short = 1 if rsi_1h < 30 else 0
            else:
                mtf_rsi_aligned = 0
                rsi_overbought_long = 0
                rsi_oversold_short = 0

            # Build a row dict with all known features, then select via self.feature_columns
            # so predict_quality() always stays aligned with whatever train_models() uses.
            row = {
                'rr_ratio': min(rr_ratio, 10),
                'tp_dist_atr': tp_dist_atr,
                'sl_dist_atr': sl_dist_atr,
                'direction_long': 1 if direction == 'LONG' else 0,
                'high_confidence': 1 if confidence > 0.7 else 0,
                'very_high_confidence': 1 if confidence > 0.85 else 0,
                'hour': hour,
                'is_weekend': 1 if now.weekday() >= 5 else 0,
                'is_asian_session': 1 if 0 <= hour < 8 else 0,
                'is_london_session': 1 if 8 <= hour < 16 else 0,
                'is_ny_session': 1 if 13 <= hour < 21 else 0,
                'is_btc': 1 if 'BTC' in symbol else 0,
                'is_eth': 1 if 'ETH' in symbol else 0,
                'is_major': 1 if any(x in symbol for x in ['BTC', 'ETH']) else 0,
                'tight_tp': 1 if tp_dist_atr < 2.5 else 0,
                'tight_sl': 1 if sl_dist_atr < 1.5 else 0,
                'wide_tp': 1 if tp_dist_atr > 5 else 0,
                'system_historical_wr': 0.5,
                # Quality enhancement features (aligned with _engineer_features)
                'rr_below_min': 1 if rr_ratio < 1.2 else 0,
                'rr_good': 1 if rr_ratio >= 1.5 else 0,
                'rr_excellent': 1 if rr_ratio >= 2.0 else 0,
                'hma_aligned': hma_aligned,
                'hma_counter_trend': hma_counter_trend,
                'volume_confirmed': volume_confirmed,
                'volume_weak': volume_weak,
                'mtf_rsi_aligned': mtf_rsi_aligned,
                'rsi_overbought_long': rsi_overbought_long,
                'rsi_oversold_short': rsi_oversold_short,
            }

            # Use self.feature_columns when available (set after training) so that
            # the feature matrix always matches the trained model's expectations.
            # Fall back to all keys in row if feature_columns not yet populated.
            feature_cols = self.feature_columns if self.feature_columns else list(row.keys())
            X = pd.DataFrame([row]).reindex(columns=feature_cols).fillna(0)
            
            # Get predictions
            prob_tp = self.tp_hit_model.predict_proba(X)[0, 1]
            prob_exp = self.expiration_model.predict_proba(X)[0, 1]
            
            # Calculate quality score
            quality_score = prob_tp * (1 - prob_exp)
            
            # Determine recommendation
            if quality_score >= self.quality_threshold + 0.1:
                recommendation = 'STRONG_BUY'
                reason = f'High quality ({quality_score:.1%}): Strong TP probability, low expiration risk'
            elif quality_score >= self.quality_threshold:
                recommendation = 'BUY'
                reason = f'Acceptable quality ({quality_score:.1%}): Meets minimum threshold'
            elif quality_score >= self.quality_threshold - 0.1:
                recommendation = 'CAUTION'
                reason = f'Marginal quality ({quality_score:.1%}): Consider reducing position size'
            else:
                recommendation = 'REJECT'
                reason = f'Low quality ({quality_score:.1%}): High expiration risk or low TP probability'
            
            return {
                'quality_score': float(quality_score),
                'prob_tp_hit': float(prob_tp),
                'prob_sl_hit': float(1 - prob_tp - prob_exp),
                'prob_expiration': float(prob_exp),
                'recommendation': recommendation,
                'reason': reason,
                'confidence': 'high' if self.model_stats.get('n_samples', 0) > 200 else 'medium',
                'model_samples': self.model_stats.get('n_samples', 0)
            }
            
        except Exception as e:
            logger.error(f"Quality prediction failed: {e}")
            return {
                'quality_score': 0.5,
                'prob_tp_hit': 0.5,
                'prob_expiration': 0.3,
                'recommendation': 'PASS',
                'reason': f'Error: {str(e)}',
                'confidence': 'none'
            }
    
    def filter_signals(self, signals: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Filter signals into accepted and rejected lists.
        
        Returns:
            Tuple of (accepted_signals, rejected_signals)
        """
        accepted = []
        rejected = []
        
        for signal in signals:
            quality = self.predict_quality(signal)
            signal['ml_quality'] = quality
            
            if quality['recommendation'] in ['STRONG_BUY', 'BUY']:
                accepted.append(signal)
            else:
                rejected.append(signal)
        
        logger.info(f"Signal filtering: {len(accepted)} accepted, {len(rejected)} rejected "
                   f"({len(accepted)/max(len(signals),1)*100:.1f}% pass rate)")
        
        return accepted, rejected
    
    def _save_models(self):
        """Save trained models."""
        try:
            import joblib
            
            model_dir = Path("forward_testing/models")
            model_dir.mkdir(parents=True, exist_ok=True)
            
            joblib.dump(self.tp_hit_model, model_dir / "tp_hit_model.pkl")
            joblib.dump(self.expiration_model, model_dir / "expiration_model.pkl")
            
            with open(model_dir / "quality_model_stats.json", 'w') as f:
                json.dump(self.model_stats, f, indent=2)
            
            logger.info("Models saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save models: {e}")
    
    def load_models(self) -> bool:
        """Load trained models."""
        try:
            import joblib
            
            model_dir = Path("forward_testing/models")
            
            tp_model_path = model_dir / "tp_hit_model.pkl"
            exp_model_path = model_dir / "expiration_model.pkl"
            
            if not tp_model_path.exists():
                return False
            
            self.tp_hit_model = joblib.load(tp_model_path)
            self.expiration_model = joblib.load(exp_model_path)
            
            stats_path = model_dir / "quality_model_stats.json"
            if stats_path.exists():
                with open(stats_path) as f:
                    self.model_stats = json.load(f)
            
            logger.info("Models loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            return False
    
    def get_quality_report(self) -> Dict:
        """Get report on model performance and recommendations."""
        return {
            'model_status': 'trained' if self.tp_hit_model else 'untrained',
            'training_stats': self.model_stats,
            'quality_threshold': self.quality_threshold,
            'feature_importance': self._get_feature_importance() if self.tp_hit_model else {}
        }
    
    def _get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from models."""
        if self.tp_hit_model is None or self.feature_columns is None:
            return {}
        
        importance = dict(zip(
            self.feature_columns,
            self.tp_hit_model.feature_importances_.tolist()
        ))
        
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))


class SignalQualityFilter:
    """
    Wrapper class for easy integration with existing signal flow.
    """
    
    def __init__(self, db_path: str = "forward_tracking.db",
                 auto_filter: bool = True):
        """
        Initialize quality filter.
        
        Args:
            db_path: Path to forward testing database
            auto_filter: Whether to automatically filter signals
        """
        self.predictor = SignalQualityPredictor(db_path)
        self.auto_filter = auto_filter
        
        # Try to load models
        if not self.predictor.load_models():
            logger.info("No quality models found, training new ones...")
            self.predictor.train_models()
    
    def evaluate_signal(self, signal: Dict) -> Dict:
        """Evaluate a single signal's quality."""
        return self.predictor.predict_quality(signal)
    
    def evaluate_batch(self, signals: List[Dict]) -> List[Dict]:
        """Evaluate multiple signals."""
        results = []
        for signal in signals:
            quality = self.evaluate_signal(signal)
            signal_with_quality = {**signal, 'quality_ml': quality}
            results.append(signal_with_quality)
        return results
    
    def get_accepted_signals(self, signals: List[Dict]) -> List[Dict]:
        """Get only signals that pass quality filter."""
        accepted, _ = self.predictor.filter_signals(signals)
        return accepted


def test_quality_predictor():
    """Test signal quality predictor."""
    print("Testing Signal Quality Predictor...")
    
    predictor = SignalQualityPredictor(db_path="test_forward.db")
    
    # Test signals
    test_signals = [
        {
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'entry_price': 85000,
            'tp_price': 90000,
            'sl_price': 82000,
            'atr': 2000,
            'confidence': 0.75
        },
        {
            'symbol': 'ETHUSDT',
            'direction': 'SHORT',
            'entry_price': 2500,
            'tp_price': 2300,
            'sl_price': 2600,
            'atr': 50,
            'confidence': 0.55
        }
    ]
    
    for signal in test_signals:
        quality = predictor.predict_quality(signal)
        print(f"\n{signal['symbol']} {signal['direction']}:")
        print(f"  Quality Score: {quality['quality_score']:.2%}")
        print(f"  TP Prob: {quality['prob_tp_hit']:.2%}")
        print(f"  Expiration Prob: {quality['prob_expiration']:.2%}")
        print(f"  Recommendation: {quality['recommendation']}")
    
    print("\nTest complete!")


if __name__ == "__main__":
    test_quality_predictor()
