"""
HMM-Based Regime Detector with Volatility + Sentiment
=====================================================
Detects market regimes using Hidden Markov Model with:
- Realized volatility
- Macro sentiment (Fear & Greed, Google Trends)
- Returns momentum

Outputs probabilistic regime estimates: P(CRASH), P(RANGE), P(TREND)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import joblib

# HMM import with fallback
try:
    from hmmlearn.hmm import GaussianHMM
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False
    logging.warning("hmmlearn not available, HMM will not function")

from sklearn.preprocessing import StandardScaler
from sklearn.isotonic import IsotonicRegression

logger = logging.getLogger(__name__)


@dataclass
class RegimePrediction:
    """Container for regime prediction results."""
    regime: str  # 'CRASH', 'RANGE', 'TREND'
    regime_id: int  # 0, 1, 2
    probabilities: Dict[str, float]  # {'CRASH': 0.1, 'RANGE': 0.3, 'TREND': 0.6}
    confidence: float  # Probability of predicted regime
    features: Dict[str, float]  # Input features used
    timestamp: datetime


class HMMRegimeDetector:
    """
    Hidden Markov Model regime detector.
    
    States:
        CRASH (0): High volatility, negative sentiment
        RANGE (1): Low volatility, neutral sentiment
        TREND (2): Moderate volatility, directional momentum
    """
    
    REGIME_LABELS = {0: 'CRASH', 1: 'RANGE', 2: 'TREND'}
    
    def __init__(
        self,
        n_states: int = 3,
        lookback_window: int = 30,
        retrain_frequency: int = 7  # days
    ):
        self.n_states = n_states
        self.lookback_window = lookback_window
        self.retrain_frequency = retrain_frequency
        
        self.model: Optional[GaussianHMM] = None
        self.scaler = StandardScaler()
        self.calibrator: Optional[IsotonicRegression] = None
        self._last_training_date: Optional[datetime] = None
        self._feature_cols: List[str] = []
        
        if not HMM_AVAILABLE:
            raise ImportError("hmmlearn is required for HMMRegimeDetector")
    
    def _compute_features(
        self,
        price_df: pd.DataFrame,
        macro_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Compute regime detection features.
        
        Features:
            - vol_forecast: Realized volatility (20-period)
            - returns_1d: 1-day returns
            - returns_5d: 5-day returns
            - sentiment: Normalized sentiment score (0-100)
            - volume_anomaly: Volume vs average ratio
        """
        df = price_df.copy()
        
        # Returns
        df['returns_1d'] = df['close'].pct_change(1)
        df['returns_5d'] = df['close'].pct_change(5)
        df['returns_20d'] = df['close'].pct_change(20)
        
        # Realized volatility (20-period, annualized)
        df['vol_forecast'] = df['returns_1d'].rolling(20).std() * np.sqrt(365) * 100
        
        # Volume anomaly
        df['volume_sma_20'] = df['volume'].rolling(20).mean()
        df['volume_anomaly'] = df['volume'] / df['volume_sma_20']
        
        # Price distance from moving averages
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        df['dist_sma20'] = (df['close'] - df['sma_20']) / df['sma_20']
        df['dist_sma50'] = (df['close'] - df['sma_50']) / df['sma_50']
        
        # Merge macro features if available
        if macro_df is not None and not macro_df.empty:
            # Align by timestamp
            macro_aligned = macro_df.reindex(df.index, method='ffill')
            
            # Fear & Greed as sentiment (0-100 scale)
            if 'fear_greed_index' in macro_aligned.columns:
                df['sentiment'] = macro_aligned['fear_greed_index']
            
            # BTC dominance
            if 'btc_dominance' in macro_aligned.columns:
                df['btc_dominance'] = macro_aligned['btc_dominance']
            
            # Market cap change as broad sentiment
            if 'market_cap_change_24h' in macro_aligned.columns:
                df['market_change'] = macro_aligned['market_cap_change_24h']
        
        # Fill missing sentiment with neutral (50)
        if 'sentiment' not in df.columns:
            df['sentiment'] = 50.0
        else:
            df['sentiment'] = df['sentiment'].fillna(50.0)
        
        # Select feature columns
        feature_cols = [
            'vol_forecast', 'returns_1d', 'returns_5d',
            'sentiment', 'volume_anomaly',
            'dist_sma20', 'dist_sma50'
        ]
        
        # Add optional features if available
        for col in ['btc_dominance', 'market_change']:
            if col in df.columns:
                feature_cols.append(col)
        
        self._feature_cols = feature_cols
        return df[feature_cols].dropna()
    
    def fit(
        self,
        price_df: pd.DataFrame,
        macro_df: Optional[pd.DataFrame] = None,
        calibrate: bool = True
    ):
        """
        Train HMM on historical data.
        
        Args:
            price_df: OHLCV data
            macro_df: Optional macro factors
            calibrate: Whether to fit probability calibrator
        """
        features = self._compute_features(price_df, macro_df)
        
        if len(features) < 100:
            raise ValueError(f"Insufficient data: {len(features)} samples, need 100+")
        
        # Scale features
        X = self.scaler.fit_transform(features.values)
        
        # Fit HMM
        self.model = GaussianHMM(
            n_components=self.n_states,
            covariance_type="full",
            n_iter=1000,
            random_state=42,
            verbose=False
        )
        
        self.model.fit(X)
        
        # Assign regime labels based on state characteristics
        self._assign_regime_labels(features, X)
        
        # Fit probability calibrator
        if calibrate:
            self._fit_calibrator(X)
        
        self._last_training_date = datetime.utcnow()
        
        logger.info(
            f"HMM trained: log-likelihood={self.model.score(X):.1f}, "
            f"converged={self.model.monitor_.converged}"
        )
        self._print_transition_matrix()
    
    def _assign_regime_labels(
        self,
        features: pd.DataFrame,
        X_scaled: np.ndarray
    ):
        """
        Assign semantic labels to HMM states based on feature characteristics.
        """
        hidden_states = self.model.predict(X_scaled)
        
        # Compute mean features per state
        state_profiles = {}
        for state in range(self.n_states):
            mask = hidden_states == state
            if mask.sum() > 0:
                state_data = features.iloc[mask]
                state_profiles[state] = {
                    'volatility': state_data['vol_forecast'].mean(),
                    'returns': state_data['returns_5d'].mean(),
                    'sentiment': state_data['sentiment'].mean(),
                    'count': mask.sum()
                }
        
        # Assign labels based on characteristics
        # CRASH: High vol, negative returns, low sentiment
        # RANGE: Low vol, near-zero returns, neutral sentiment
        # TREND: Moderate vol, directional returns, varying sentiment
        
        # Sort by volatility (highest first)
        sorted_by_vol = sorted(
            state_profiles.items(),
            key=lambda x: x[1]['volatility'],
            reverse=True
        )
        
        # Highest vol = CRASH
        crash_state = sorted_by_vol[0][0]
        
        # Of remaining, lowest vol = RANGE
        remaining = [s for s, _ in sorted_by_vol[1:]]
        range_candidates = {s: state_profiles[s] for s in remaining}
        range_state = min(range_candidates.items(), key=lambda x: x[1]['volatility'])[0]
        
        # Last one = TREND
        trend_state = [s for s in remaining if s != range_state][0]
        
        self._state_label_map = {
            crash_state: 'CRASH',
            range_state: 'RANGE',
            trend_state: 'TREND'
        }
        
        self._state_id_map = {v: k for k, v in self._state_label_map.items()}
        
        logger.info("Regime state mapping:")
        for state, label in self._state_label_map.items():
            p = state_profiles[state]
            logger.info(
                f"  State {state} [{label:>5}]: "
                f"vol={p['volatility']:.1f}%, ret={p['returns']:.1%}, "
                f"sent={p['sentiment']:.0f}, n={p['count']}"
            )
    
    def _fit_calibrator(self, X: np.ndarray):
        """Fit isotonic regression for probability calibration."""
        # Use recent data to calibrate probabilities
        hidden_states = self.model.predict(X)
        posteriors = self.model.predict_proba(X)
        
        # For each state, calibrate the probability outputs
        # This ensures P(predicted) matches actual frequency
        self.calibrator = IsotonicRegression(out_of_bounds='clip')
        
        # Use max posterior as confidence, check if correct
        max_probs = posteriors.max(axis=1)
        correct = (posteriors.argmax(axis=1) == hidden_states).astype(int)
        
        self.calibrator.fit(max_probs, correct)
    
    def predict(
        self,
        price_df: pd.DataFrame,
        macro_df: Optional[pd.DataFrame] = None
    ) -> RegimePrediction:
        """
        Predict current regime.
        
        Returns:
            RegimePrediction with probabilities and confidence
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call fit() first.")
        
        features = self._compute_features(price_df, macro_df)
        
        if features.empty:
            return RegimePrediction(
                regime='UNKNOWN',
                regime_id=-1,
                probabilities={},
                confidence=0.0,
                features={},
                timestamp=datetime.utcnow()
            )
        
        # Get latest features
        latest = features.iloc[-1:]
        X = self.scaler.transform(latest.values)
        
        # Predict
        state = self.model.predict(X)[0]
        posteriors = self.model.predict_proba(X)[0]
        
        # Build probability dict
        probabilities = {
            self._state_label_map.get(i, f'STATE_{i}'): float(p)
            for i, p in enumerate(posteriors)
        }
        
        # Get predicted regime
        regime = self._state_label_map.get(state, 'UNKNOWN')
        confidence = float(posteriors[state])
        
        # Calibrate confidence if calibrator available
        if self.calibrator is not None:
            confidence = float(self.calibrator.predict([confidence])[0])
        
        # Get transition probabilities
        trans = self.model.transmat_[state]
        
        return RegimePrediction(
            regime=regime,
            regime_id=state,
            probabilities=probabilities,
            confidence=confidence,
            features=latest.iloc[0].to_dict(),
            timestamp=datetime.utcnow()
        )
    
    def predict_proba(
        self,
        price_df: pd.DataFrame,
        macro_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Predict regime probabilities for entire series.
        
        Returns:
            DataFrame with columns [regime_0, regime_1, regime_2, predicted_regime]
        """
        features = self._compute_features(price_df, macro_df)
        
        if features.empty:
            return pd.DataFrame()
        
        X = self.scaler.transform(features.values)
        posteriors = self.model.predict_proba(X)
        
        # Build DataFrame
        df = pd.DataFrame(
            posteriors,
            index=features.index,
            columns=[f'regime_{self._state_label_map.get(i, i)}' for i in range(self.n_states)]
        )
        
        df['predicted_regime'] = [
            self._state_label_map.get(s, f'STATE_{s}')
            for s in posteriors.argmax(axis=1)
        ]
        df['confidence'] = posteriors.max(axis=1)
        
        return df
    
    def get_transition_matrix(self) -> pd.DataFrame:
        """Get regime transition probability matrix."""
        if self.model is None:
            return pd.DataFrame()
        
        T = self.model.transmat_
        labels = [self._state_label_map.get(i, f'STATE_{i}') for i in range(self.n_states)]
        
        return pd.DataFrame(T, index=labels, columns=labels)
    
    def _print_transition_matrix(self):
        """Log transition matrix."""
        if self.model is None:
            return
        
        T = self.model.transmat_
        labels = [self._state_label_map.get(i, f'S{i}') for i in range(self.n_states)]
        
        logger.info("Transition Matrix (row -> col):")
        header = "       " + " ".join(f"{l:>7}" for l in labels)
        logger.info(header)
        for i, row in enumerate(T):
            vals = " ".join(f"{v:7.3f}" for v in row)
            logger.info(f"{labels[i]:>7} {vals}")
    
    def save(self, path: Path):
        """Save model to disk."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'calibrator': self.calibrator,
            'state_label_map': self._state_label_map,
            'feature_cols': self._feature_cols,
            'last_training_date': self._last_training_date
        }, path / 'hmm_regime_detector.joblib')
        
        logger.info(f"Model saved to {path}")
    
    def load(self, path: Path):
        """Load model from disk."""
        path = Path(path)
        model_path = path / 'hmm_regime_detector.joblib'
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path}")
        
        data = joblib.load(model_path)
        
        self.model = data['model']
        self.scaler = data['scaler']
        self.calibrator = data.get('calibrator')
        self._state_label_map = data['state_label_map']
        self._state_id_map = {v: k for k, v in self._state_label_map.items()}
        self._feature_cols = data.get('feature_cols', [])
        self._last_training_date = data.get('last_training_date')
        
        logger.info(f"Model loaded from {path}")


class RegimeAwareRiskManager:
    """
    Risk manager that uses regime predictions to adjust position sizing.
    """
    
    def __init__(self, detector: HMMRegimeDetector):
        self.detector = detector
    
    def get_position_size_multiplier(
        self,
        prediction: RegimePrediction,
        base_size: float = 1.0
    ) -> float:
        """
        Get position size multiplier based on regime.
        
        Multipliers:
            CRASH: 0.0 (no new positions)
            RANGE: 0.7 (reduced size for chop)
            TREND: 1.2 (increased size for directional moves)
        """
        multipliers = {
            'CRASH': 0.0,
            'RANGE': 0.7,
            'TREND': 1.2
        }
        
        base_mult = multipliers.get(prediction.regime, 0.5)
        
        # Scale by confidence
        confidence_scale = 0.5 + prediction.confidence * 0.5
        
        return base_size * base_mult * confidence_scale
    
    def should_trade(
        self,
        prediction: RegimePrediction,
        direction: str = 'LONG'
    ) -> Tuple[bool, str]:
        """
        Determine if trading should be allowed based on regime.
        """
        if prediction.regime == 'CRASH':
            return False, "CRASH regime - no new positions"
        
        if prediction.confidence < 0.5:
            return False, f"Low confidence ({prediction.confidence:.0%}) - wait"
        
        if prediction.regime == 'RANGE':
            # In range regimes, both directions OK but caution
            return True, f"RANGE regime - mean reversion OK with reduced size"
        
        if prediction.regime == 'TREND':
            # In trend, follow the trend
            # Could add logic to check trend direction
            return True, f"TREND regime - trend following OK"
        
        return True, "Unknown regime - proceed with caution"


def train_regime_detector(
    price_data: pd.DataFrame,
    macro_data: Optional[pd.DataFrame] = None,
    model_path: Path = Path("models/regime_detector")
) -> HMMRegimeDetector:
    """
    Train and save regime detector.
    """
    detector = HMMRegimeDetector()
    detector.fit(price_data, macro_data)
    detector.save(model_path)
    return detector


def load_regime_detector(
    model_path: Path = Path("models/regime_detector")
) -> HMMRegimeDetector:
    """
    Load trained regime detector.
    """
    detector = HMMRegimeDetector()
    detector.load(model_path)
    return detector
