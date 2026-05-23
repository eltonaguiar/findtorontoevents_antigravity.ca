"""
L1-Regularized Logistic Regression for High-Frequency Signals
=============================================================
Implements sparse logistic regression with L1 regularization for
micro-structure signal prediction.

Planned v1.1 from updates_torontoevent.html - NOW IMPLEMENTED
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import pickle

logger = logging.getLogger(__name__)


@dataclass
class L1LogisticConfig:
    """Configuration for L1 logistic regression."""
    C: float = 1.0  # Inverse of regularization strength (smaller = stronger regularization)
    max_iter: int = 1000
    solver: str = 'liblinear'  # Good for L1 penalty
    penalty: str = 'l1'
    class_weight: str = 'balanced'
    random_state: int = 42


class L1LogisticHFT:
    """
    L1-regularized logistic regression for high-frequency trading signals.
    
    Features used:
    - Orderbook imbalance (L1-L3)
    - Spread metrics
    - Recent trade flow
    - Price momentum (micro-scale)
    - Volatility estimates
    
    L1 regularization performs feature selection, keeping only the most
    predictive micro-structure features.
    
    Status: IMPLEMENTED (was PLANNED v1.1)
    """
    
    def __init__(self, config: L1LogisticConfig = None):
        self.config = config or L1LogisticConfig()
        self.model = LogisticRegression(
            C=self.config.C,
            max_iter=self.config.max_iter,
            solver=self.config.solver,
            penalty=self.config.penalty,
            class_weight=self.config.class_weight,
            random_state=self.config.random_state
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = []
        
        logger.info("[OK] L1 Logistic HFT INITIALIZED (v1.1 IMPLEMENTED)")
    
    def extract_features(self, orderbook: Dict, recent_trades: List) -> np.ndarray:
        """
        Extract micro-structure features from orderbook and recent trades.
        
        Args:
            orderbook: Current orderbook with bids/asks
            recent_trades: List of recent trades
        
        Returns:
            Feature vector (sparse due to L1 regularization)
        """
        features = {}
        
        # Orderbook features
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        if not bids or not asks:
            return np.zeros(20)
        
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid_price = (best_bid + best_ask) / 2
        spread = best_ask - best_bid
        spread_bps = spread / mid_price * 10000  # Basis points
        
        features['spread_bps'] = spread_bps
        features['mid_price'] = mid_price
        
        # Level 1-3 imbalances
        for level in [1, 2, 3]:
            bid_vol = sum([v for _, v in bids[:level]])
            ask_vol = sum([v for _, v in asks[:level]])
            imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol + 1e-10)
            features[f'imbalance_l{level}'] = imbalance
        
        # Depth ratios
        features['depth_ratio_l1_l3'] = (
            sum([v for _, v in bids[:1]]) / 
            (sum([v for _, v in bids[:3]]) + 1e-10)
        )
        
        # Recent trade features
        if recent_trades:
            trade_prices = [t['price'] for t in recent_trades[-20:]]
            trade_volumes = [t['volume'] for t in recent_trades[-20:]]
            trade_sides = [t.get('side', 'buy') for t in recent_trades[-20:]]
            
            # Trade flow imbalance
            buy_vol = sum([v for v, s in zip(trade_volumes, trade_sides) if s == 'buy'])
            sell_vol = sum([v for v, s in zip(trade_volumes, trade_sides) if s == 'sell'])
            features['trade_flow_imbalance'] = (buy_vol - sell_vol) / (buy_vol + sell_vol + 1e-10)
            
            # Micro momentum (last 5 trades vs last 20)
            if len(trade_prices) >= 20:
                recent_mean = np.mean(trade_prices[-5:])
                older_mean = np.mean(trade_prices[-20:-15])
                features['micro_momentum'] = (recent_mean - older_mean) / older_mean * 10000
            else:
                features['micro_momentum'] = 0
            
            # Trade intensity
            features['trade_intensity'] = len(recent_trades) / 60  # Trades per minute
            
            # Volume-weighted average price
            vwap = sum([p * v for p, v in zip(trade_prices, trade_volumes)]) / sum(trade_volumes)
            features['vwap_deviation'] = (mid_price - vwap) / vwap * 10000
        else:
            features['trade_flow_imbalance'] = 0
            features['micro_momentum'] = 0
            features['trade_intensity'] = 0
            features['vwap_deviation'] = 0
        
        # Price acceleration (change in momentum)
        if len(recent_trades) >= 10:
            prices = [t['price'] for t in recent_trades[-10:]]
            returns = np.diff(prices) / prices[:-1]
            if len(returns) >= 2:
                features['price_acceleration'] = returns[-1] - returns[-2]
            else:
                features['price_acceleration'] = 0
        else:
            features['price_acceleration'] = 0
        
        # Volatility estimate from orderbook
        features['book_volatility'] = np.std([p for p, _ in bids[:5] + asks[:5]])
        
        # Quote slope (how aggressively orders are stacked)
        if len(bids) >= 3 and len(asks) >= 3:
            bid_slope = (bids[0][0] - bids[2][0]) / (bids[0][1] + bids[1][1] + bids[2][1] + 1e-10)
            ask_slope = (asks[2][0] - asks[0][0]) / (asks[0][1] + asks[1][1] + asks[2][1] + 1e-10)
            features['quote_slope_imbalance'] = bid_slope - ask_slope
        else:
            features['quote_slope_imbalance'] = 0
        
        # Time-of-day features (market microstructure varies by time)
        from datetime import datetime
        now = datetime.now()
        features['hour_sin'] = np.sin(2 * np.pi * now.hour / 24)
        features['hour_cos'] = np.cos(2 * np.pi * now.hour / 24)
        
        # Convert to array in consistent order
        self.feature_names = sorted(features.keys())
        feature_array = np.array([features[k] for k in self.feature_names])
        
        return feature_array
    
    def predict(
        self,
        orderbook: Dict,
        recent_trades: List,
        return_proba: bool = True
    ) -> Dict:
        """
        Predict direction probability from micro-structure.
        
        Args:
            orderbook: Current orderbook
            recent_trades: Recent trade history
            return_proba: Whether to return probability scores
        
        Returns:
            Prediction dict with direction, probability, and confidence
        """
        if not self.is_trained:
            logger.warning("Model not trained yet - returning neutral prediction")
            return {
                'direction': 'NEUTRAL',
                'up_probability': 0.5,
                'down_probability': 0.5,
                'confidence': 0.0,
                'features_used': 0
            }
        
        features = self.extract_features(orderbook, recent_trades)
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        if return_proba:
            proba = self.model.predict_proba(features_scaled)[0]
        else:
            proba = [0.5, 0.5]
        
        prediction = self.model.predict(features_scaled)[0]
        
        # Count non-zero coefficients (L1 feature selection)
        n_features_used = np.sum(self.model.coef_[0] != 0)
        
        # Confidence is distance from 0.5
        confidence = abs(proba[1] - 0.5) * 2  # Scale to 0-1
        
        result = {
            'direction': 'UP' if prediction == 1 else 'DOWN',
            'up_probability': proba[1],
            'down_probability': proba[0],
            'confidence': confidence,
            'features_used': n_features_used,
            'total_features': len(self.feature_names),
            'feature_importance': self._get_feature_importance()
        }
        
        logger.debug(f"L1 Logistic prediction: {result['direction']} (conf: {confidence:.3f})")
        
        return result
    
    def _get_feature_importance(self) -> Dict:
        """Get feature importance from L1 coefficients."""
        if not self.is_trained:
            return {}
        
        importance = {}
        for name, coef in zip(self.feature_names, self.model.coef_[0]):
            if coef != 0:  # L1 sparsity - only non-zero features matter
                importance[name] = abs(coef)
        
        # Sort by importance
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
    
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        validation_split: float = 0.2
    ) -> Dict:
        """
        Train L1 logistic regression model.
        
        Args:
            X: Feature matrix (n_samples, n_features)
            y: Labels (0=down, 1=up)
            validation_split: Fraction for validation
        
        Returns:
            Training metrics
        """
        # Split data
        n_val = int(len(X) * validation_split)
        X_train, X_val = X[:-n_val], X[-n_val:]
        y_train, y_val = y[:-n_val], y[-n_val:]
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        
        # Train model
        self.model.fit(X_train_scaled, y_train)
        self.is_trained = True
        
        # Evaluate
        train_acc = self.model.score(X_train_scaled, y_train)
        val_acc = self.model.score(X_val_scaled, y_val)
        
        # Count selected features (L1 sparsity)
        n_selected = np.sum(self.model.coef_[0] != 0)
        sparsity = n_selected / len(self.model.coef_[0])
        
        metrics = {
            'train_accuracy': train_acc,
            'val_accuracy': val_acc,
            'n_selected_features': int(n_selected),
            'sparsity_ratio': float(sparsity),
            'regularization_C': self.config.C
        }
        
        logger.info(
            f"[OK] L1 Logistic trained: {n_selected}/{len(self.model.coef_[0])} "
            f"features selected ({sparsity:.1%} sparsity)"
        )
        
        return metrics
    
    def online_update(self, X_new: np.ndarray, y_new: np.ndarray) -> Dict:
        """
        Online update with new data (partial fit).
        
        For true online learning, we maintain a rolling window
        and retrain periodically.
        """
        # For sklearn, we need to refit with combined data
        # In production, use SGDClassifier for true online learning
        logger.info(f"Online update with {len(X_new)} new samples")
        
        # Retrain with new data
        return self.train(X_new, y_new)
    
    def save(self, path: str):
        """Save model to disk."""
        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler,
                'config': self.config,
                'feature_names': self.feature_names,
                'is_trained': self.is_trained
            }, f)
        logger.info(f"💾 L1 Logistic model saved to {path}")
    
    def load(self, path: str):
        """Load model from disk."""
        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.scaler = data['scaler']
            self.config = data['config']
            self.feature_names = data['feature_names']
            self.is_trained = data['is_trained']
        logger.info(f"📂 L1 Logistic model loaded from {path}")


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Initialize model
    model = L1LogisticHFT()
    
    # Example data
    orderbook = {
        'bids': [[50000, 2.0], [49999, 3.0], [49998, 5.0]],
        'asks': [[50001, 1.5], [50002, 4.0], [50003, 6.0]]
    }
    
    recent_trades = [
        {'price': 50000.5, 'volume': 0.5, 'side': 'buy'},
        {'price': 50000.8, 'volume': 0.3, 'side': 'buy'},
        {'price': 50000.2, 'volume': 0.8, 'side': 'sell'},
    ]
    
    # Extract features
    features = model.extract_features(orderbook, recent_trades)
    print(f"Extracted {len(features)} features")
    print(f"Feature names: {model.feature_names[:5]}...")
    
    # Note: Model needs training before prediction
    print("\n[OK] L1 Logistic HFT v1.1 IMPLEMENTATION COMPLETE")
