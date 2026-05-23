"""
KIMI_FEB172026 - ML Signal Ranker
Machine Learning ranking system for signal quality prediction
Uses RandomForest to predict win probability of each signal
"""

import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

# ML imports
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SignalFeatures:
    """24 features used for ML ranking"""
    # Algorithm features
    algo_id_encoded: int
    category_encoded: int  # 0=crypto, 1=forex, 2=stock, 3=meme
    symbol_encoded: int
    
    # Time features
    hour_of_day: int
    day_of_week: int
    
    # Market regime features
    regime_encoded: int  # -1=bear, 0=neutral, 1=bull
    crypto_regime: int  # -1=defensive, 0=neutral, 1=risk_on
    vix_proxy: float  # volatility proxy
    
    # Market context
    hmm_confidence: float
    breadth_pct: float  # % above 50d SMA
    vol_20d: float  # 20-day realized volatility
    btc_eth_ratio: float
    fear_greed_crypto: float
    fear_greed_stock: float
    
    # Algorithm performance
    algo_current_wr: float  # win rate
    algo_current_sharpe: float
    algo_drought_scans: int  # consecutive scans without signal
    algo_total_closed: int
    
    # Price/technical features
    price_vs_52w_high: float
    volume_ratio: float
    rsi_value: float
    
    # Tier and convergence
    tier_encoded: int  # 1=TIER_1, 0=SCOUT
    signal_convergence: int  # how many algos fired same symbol
    
    # Position sizing
    kelly_fraction: float


class MLSignalRanker:
    """
    Machine Learning signal quality ranker
    Trains on historical signal outcomes to predict future win probability
    """
    
    MIN_TRAINING_SAMPLES = 50
    MODEL_VERSION = "1.0.0"
    
    def __init__(self, data_dir: str = "KIMI_FEB172026/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Model paths
        self.model_path = self.data_dir / "rf_model.pkl"
        self.scaler_path = self.data_dir / "scaler.pkl"
        self.encoders_path = self.data_dir / "encoders.pkl"
        self.weights_path = self.data_dir / "ml_weights.json"
        self.stats_path = self.data_dir / "ml_training_stats.json"
        
        # Initialize components
        self.model: Optional[RandomForestClassifier] = None
        self.scaler = StandardScaler()
        self.encoders: Dict[str, LabelEncoder] = {}
        self.is_trained = False
        
        # Feature names (must match SignalFeatures order)
        self.feature_names = [
            'algo_id_encoded', 'category_encoded', 'symbol_encoded',
            'hour_of_day', 'day_of_week',
            'regime_encoded', 'crypto_regime', 'vix_proxy',
            'hmm_confidence', 'breadth_pct', 'vol_20d', 'btc_eth_ratio',
            'fear_greed_crypto', 'fear_greed_stock',
            'algo_current_wr', 'algo_current_sharpe', 'algo_drought_scans',
            'algo_total_closed', 'price_vs_52w_high', 'volume_ratio',
            'rsi_value', 'tier_encoded', 'signal_convergence', 'kelly_fraction'
        ]
        
        # Try to load existing model
        self._load_model()
    
    def _load_model(self):
        """Load pre-trained model if exists"""
        try:
            if self.model_path.exists():
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                
                if self.scaler_path.exists():
                    with open(self.scaler_path, 'rb') as f:
                        self.scaler = pickle.load(f)
                
                if self.encoders_path.exists():
                    with open(self.encoders_path, 'rb') as f:
                        self.encoders = pickle.load(f)
                
                self.is_trained = True
                logger.info("Loaded existing ML model")
        except Exception as e:
            logger.warning(f"Could not load model: {e}")
            self.model = None
    
    def _save_model(self):
        """Save trained model"""
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.model, f)
            
            with open(self.scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            
            with open(self.encoders_path, 'wb') as f:
                pickle.dump(self.encoders, f)
            
            logger.info("Saved ML model to disk")
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def _encode_categorical(self, values: List[str], name: str) -> np.ndarray:
        """Encode categorical variables"""
        if name not in self.encoders:
            self.encoders[name] = LabelEncoder()
            self.encoders[name].fit(values)
        
        encoder = self.encoders[name]
        # Handle unseen values
        encoded = []
        for v in values:
            if v in encoder.classes_:
                encoded.append(encoder.transform([v])[0])
            else:
                encoded.append(len(encoder.classes_))  # Unknown class
        
        return np.array(encoded)
    
    def extract_features_from_signal(self, signal: Dict, market_data: Dict, 
                                     algo_stats: Dict) -> SignalFeatures:
        """
        Extract 24 features from signal + market context
        """
        now = datetime.now()
        
        # Symbol encoding (top 50 + OTHER)
        top_symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'DOT', 
                      'MATIC', 'LINK', 'AVAX', 'ATOM', 'NEAR', 'FIL', 'INJ',
                      'TIA', 'SUI', 'APT', 'ARB', 'OP', 'SEI', 'JUP', 'PYTH',
                      'WIF', 'BONK', 'PEPE', 'SHIB', 'LTC', 'BCH', 'ALGO']
        symbol = signal.get('symbol', 'OTHER').split('-')[0]
        symbol_encoded = top_symbols.index(symbol) if symbol in top_symbols else 50
        
        # Category encoding
        categories = {'crypto': 0, 'forex': 1, 'stock': 2, 'meme': 3, 'penny': 4}
        category = signal.get('category', 'crypto')
        category_encoded = categories.get(category, 0)
        
        # Algo ID encoding
        algo_id = signal.get('signal_type', 'unknown')
        
        return SignalFeatures(
            algo_id_encoded=hash(algo_id) % 1000,
            category_encoded=category_encoded,
            symbol_encoded=symbol_encoded,
            hour_of_day=now.hour,
            day_of_week=now.weekday(),
            regime_encoded=market_data.get('regime', 0),
            crypto_regime=market_data.get('crypto_regime', 0),
            vix_proxy=market_data.get('vix_proxy', 20),
            hmm_confidence=market_data.get('hmm_confidence', 0.5),
            breadth_pct=market_data.get('breadth_pct', 50),
            vol_20d=market_data.get('vol_20d', 0.02),
            btc_eth_ratio=market_data.get('btc_eth_ratio', 15),
            fear_greed_crypto=market_data.get('fear_greed_crypto', 50),
            fear_greed_stock=market_data.get('fear_greed_stock', 50),
            algo_current_wr=algo_stats.get('win_rate', 0.5),
            algo_current_sharpe=algo_stats.get('sharpe', 1.0),
            algo_drought_scans=algo_stats.get('drought_scans', 0),
            algo_total_closed=algo_stats.get('total_closed', 10),
            price_vs_52w_high=market_data.get('price_vs_52w_high', 0.5),
            volume_ratio=signal.get('metadata', {}).get('volume_ratio', 1.0),
            rsi_value=signal.get('metadata', {}).get('rsi', 50),
            tier_encoded=1 if signal.get('tier') == 'TIER_1' else 0,
            signal_convergence=signal.get('convergence_count', 0),
            kelly_fraction=self._calculate_kelly(algo_stats)
        )
    
    def _calculate_kelly(self, algo_stats: Dict) -> float:
        """Calculate Kelly Criterion fraction for position sizing"""
        win_rate = algo_stats.get('win_rate', 0.5)
        avg_win = algo_stats.get('avg_win_pct', 0.02)
        avg_loss = algo_stats.get('avg_loss_pct', 0.01)
        
        if avg_loss == 0:
            return 0.01  # Minimum position
        
        win_loss_ratio = avg_win / avg_loss
        kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
        
        # Use half-Kelly for safety
        return max(0.01, min(0.25, kelly / 2))
    
    def features_to_array(self, features: SignalFeatures) -> np.ndarray:
        """Convert features dataclass to numpy array"""
        return np.array([
            features.algo_id_encoded,
            features.category_encoded,
            features.symbol_encoded,
            features.hour_of_day,
            features.day_of_week,
            features.regime_encoded,
            features.crypto_regime,
            features.vix_proxy,
            features.hmm_confidence,
            features.breadth_pct,
            features.vol_20d,
            features.btc_eth_ratio,
            features.fear_greed_crypto,
            features.fear_greed_stock,
            features.algo_current_wr,
            features.algo_current_sharpe,
            features.algo_drought_scans,
            features.algo_total_closed,
            features.price_vs_52w_high,
            features.volume_ratio,
            features.rsi_value,
            features.tier_encoded,
            features.signal_convergence,
            features.kelly_fraction
        ]).reshape(1, -1)
    
    def train_if_ready(self, picks_data: List[Dict]) -> Dict:
        """
        Train model if we have enough closed picks
        Returns training statistics
        """
        if len(picks_data) < self.MIN_TRAINING_SAMPLES:
            logger.info(f"Not enough samples for training. Have {len(picks_data)}, need {self.MIN_TRAINING_SAMPLES}")
            return {"status": "insufficient_data", "n_samples": len(picks_data)}
        
        try:
            # Prepare training data
            X = []
            y = []
            
            for pick in picks_data:
                features = pick.get('features')
                outcome = pick.get('status')  # 'WON', 'LOST', 'EXPIRED'
                
                if features and outcome:
                    X.append([
                        features.get(f, 0) for f in self.feature_names
                    ])
                    # Binary: 1 = WIN, 0 = LOSS/EXPIRE
                    y.append(1 if outcome == 'WON' else 0)
            
            if len(X) < self.MIN_TRAINING_SAMPLES:
                return {"status": "insufficient_valid_samples", "n_samples": len(X)}
            
            X = np.array(X)
            y = np.array(y)
            
            # Temporal split: train on earlier data, test on later (no data leakage)
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train Random Forest
            self.model = RandomForestClassifier(
                n_estimators=200,
                max_depth=8,
                min_samples_split=10,
                min_samples_leaf=5,
                class_weight='balanced',
                random_state=42,
                n_jobs=-1
            )
            
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = self.model.predict(X_test_scaled)
            y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]
            
            # Calculate metrics
            stats = {
                "status": "trained",
                "timestamp": datetime.now().isoformat(),
                "model_version": self.MODEL_VERSION,
                "n_samples": len(X),
                "n_features": len(self.feature_names),
                "accuracy": round(accuracy_score(y_test, y_pred), 4),
                "precision": round(precision_score(y_test, y_pred), 4),
                "recall": round(recall_score(y_test, y_pred), 4),
                "f1_score": round(f1_score(y_test, y_pred), 4),
                "roc_auc": round(roc_auc_score(y_test, y_pred_proba), 4),
                "win_rate_train": round(np.mean(y), 4),
                "class_distribution": {
                    "wins": int(np.sum(y)),
                    "losses": int(len(y) - np.sum(y))
                }
            }
            
            # Feature importance
            importance = self.model.feature_importances_
            stats["feature_importance"] = {
                name: round(imp, 4) 
                for name, imp in sorted(
                    zip(self.feature_names, importance),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]  # Top 10
            }
            
            self.is_trained = True
            
            # Save everything
            self._save_model()
            self._save_stats(stats)
            
            logger.info(f"Model trained successfully! Accuracy: {stats['accuracy']:.2%}")
            return stats
            
        except Exception as e:
            logger.error(f"Training error: {e}")
            return {"status": "error", "message": str(e)}
    
    def _save_stats(self, stats: Dict):
        """Save training statistics"""
        with open(self.stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
    
    def score_signal(self, features: SignalFeatures) -> float:
        """
        Predict win probability for a signal
        Returns value 0.0-1.0
        """
        if not self.is_trained or self.model is None:
            # Fallback to heuristic scoring
            return self._heuristic_score(features)
        
        try:
            X = self.features_to_array(features)
            X_scaled = self.scaler.transform(X)
            
            # Get probability of win (class 1)
            proba = self.model.predict_proba(X_scaled)[0][1]
            return float(proba)
            
        except Exception as e:
            logger.error(f"Scoring error: {e}")
            return self._heuristic_score(features)
    
    def _heuristic_score(self, features: SignalFeatures) -> float:
        """
        Heuristic scoring when ML model not available
        Uses weighted combination of key features
        """
        score = 0.5  # Base score
        
        # Algorithm performance (30% weight)
        score += (features.algo_current_wr - 0.5) * 0.3
        score += (features.algo_current_sharpe - 1.0) * 0.05
        
        # Market regime (20% weight)
        score += features.regime_encoded * 0.05
        score += features.crypto_regime * 0.05
        
        # Technical factors (20% weight)
        score += (0.7 - features.price_vs_52w_high) * 0.1  # Prefer not at highs
        score += (features.volume_ratio - 1) * 0.05  # Volume confirmation
        
        # Tier bonus (15% weight)
        score += features.tier_encoded * 0.15
        
        # Convergence bonus (15% weight)
        score += min(features.signal_convergence * 0.03, 0.15)
        
        return max(0.1, min(0.95, score))
    
    def get_weights(self) -> Dict[str, Dict[str, float]]:
        """Get per-algo, per-symbol win probabilities"""
        # This would query database for actual weights
        # For now, return structure
        return {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "model_trained": self.is_trained,
                "version": self.MODEL_VERSION
            },
            "default_weight": 0.5,
            "algo_weights": {},
            "symbol_weights": {}
        }
    
    def get_algo_ranking(self, algo_stats: List[Dict]) -> List[Dict]:
        """
        Rank algorithms by expected win probability
        """
        ranked = []
        
        for stats in algo_stats:
            algo_id = stats.get('algorithm', 'unknown')
            
            # Create mock features for ranking
            features = SignalFeatures(
                algo_id_encoded=hash(algo_id) % 1000,
                category_encoded=0,
                symbol_encoded=0,
                hour_of_day=12,
                day_of_week=1,
                regime_encoded=1,
                crypto_regime=1,
                vix_proxy=20,
                hmm_confidence=0.6,
                breadth_pct=60,
                vol_20d=0.02,
                btc_eth_ratio=15,
                fear_greed_crypto=55,
                fear_greed_stock=50,
                algo_current_wr=stats.get('win_rate', 0.5),
                algo_current_sharpe=stats.get('sharpe', 1.0),
                algo_drought_scans=0,
                algo_total_closed=stats.get('total_closed', 10),
                price_vs_52w_high=0.6,
                volume_ratio=1.5,
                rsi_value=50,
                tier_encoded=1 if stats.get('tier') == 'TIER_1' else 0,
                signal_convergence=0,
                kelly_fraction=self._calculate_kelly(stats)
            )
            
            win_prob = self.score_signal(features)
            
            ranked.append({
                'algorithm': algo_id,
                'expected_win_prob': round(win_prob, 4),
                'current_win_rate': stats.get('win_rate', 0),
                'sharpe': stats.get('sharpe', 0),
                'total_picks': stats.get('total_closed', 0),
                'tier': stats.get('tier', 'SCOUT')
            })
        
        # Sort by expected win probability
        ranked.sort(key=lambda x: x['expected_win_prob'], reverse=True)
        
        return ranked
    
    def recommend_position_size(self, signal_score: float, 
                               max_position: float = 10000) -> float:
        """
        Recommend position size based on signal confidence
        Uses Kelly criterion adjustment
        """
        if signal_score < 0.35:
            return 0  # Don't trade
        elif signal_score < 0.5:
            return max_position * 0.25
        elif signal_score < 0.65:
            return max_position * 0.5
        elif signal_score < 0.8:
            return max_position * 0.75
        else:
            return max_position


# =============================================================================
# Signal Quality Validator
# =============================================================================
class SignalQualityValidator:
    """
    Post-signal validation and outcome tracking
    For continuous model improvement
    """
    
    def __init__(self, db_path: str = "KIMI_FEB172026/data/kimi_trading.db"):
        self.db_path = db_path
    
    def validate_outcome(self, signal_id: str, exit_price: float, 
                        exit_reason: str) -> Dict:
        """
        Validate signal outcome and update model training data
        """
        # This would update database with outcome
        # For use in next training cycle
        return {
            "signal_id": signal_id,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "validated_at": datetime.now().isoformat()
        }
    
    def calculate_realized_performance(self, signals: List[Dict]) -> Dict:
        """Calculate actual performance of signals"""
        if not signals:
            return {"error": "No signals"}
        
        total = len(signals)
        wins = sum(1 for s in signals if s.get('outcome') == 'WIN')
        losses = sum(1 for s in signals if s.get('outcome') == 'LOSS')
        
        total_pnl = sum(s.get('pnl_pct', 0) for s in signals)
        
        return {
            "total_signals": total,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / total, 4) if total > 0 else 0,
            "total_pnl_pct": round(total_pnl, 4),
            "avg_pnl_pct": round(total_pnl / total, 4) if total > 0 else 0
        }


# =============================================================================
# Main Entry Point
# =============================================================================
def main():
    """Test the ML signal ranker"""
    print("=" * 80)
    print("KIMI_FEB172026 - ML Signal Ranker")
    print("Machine Learning Signal Quality Prediction")
    print("=" * 80)
    
    ranker = MLSignalRanker()
    
    # Example signal
    test_signal = {
        "symbol": "BTC-USD",
        "signal_type": "pump-detector-scout",
        "category": "crypto",
        "tier": "TIER_1",
        "metadata": {
            "volume_ratio": 5.5,
            "rsi": 55,
            "price_change_4h": 12
        }
    }
    
    market_data = {
        "regime": 1,
        "crypto_regime": 1,
        "vix_proxy": 18,
        "hmm_confidence": 0.75,
        "breadth_pct": 65,
        "vol_20d": 0.025,
        "btc_eth_ratio": 16.5,
        "fear_greed_crypto": 65,
        "fear_greed_stock": 55,
        "price_vs_52w_high": 0.75
    }
    
    algo_stats = {
        "win_rate": 0.68,
        "sharpe": 1.45,
        "total_closed": 125,
        "avg_win_pct": 0.035,
        "avg_loss_pct": 0.018
    }
    
    # Extract features
    features = ranker.extract_features_from_signal(
        test_signal, market_data, algo_stats
    )
    
    print("\nExtracted Features:")
    for key, value in asdict(features).items():
        print(f"  {key}: {value}")
    
    # Score signal
    score = ranker.score_signal(features)
    
    print(f"\n{'='*80}")
    print(f"Signal: {test_signal['symbol']} - {test_signal['signal_type']}")
    print(f"Win Probability: {score:.1%}")
    print(f"Recommended Position: ${ranker.recommend_position_size(score):,.2f}")
    print(f"Model Status: {'Trained' if ranker.is_trained else 'Heuristic Mode'}")
    
    # Test ranking
    test_algos = [
        {"algorithm": "pump-detector", "win_rate": 0.72, "sharpe": 1.6, "total_closed": 200, "tier": "TIER_1"},
        {"algorithm": "liquidation-cascade", "win_rate": 0.65, "sharpe": 1.3, "total_closed": 150, "tier": "TIER_1"},
        {"algorithm": "order-book-imbalance", "win_rate": 0.58, "sharpe": 1.1, "total_closed": 80, "tier": "SCOUT"},
        {"algorithm": "smc-order-block", "win_rate": 0.61, "sharpe": 1.2, "total_closed": 95, "tier": "SCOUT"},
    ]
    
    print("\n" + "=" * 80)
    print("Algorithm Rankings by Expected Win Probability:")
    print("=" * 80)
    
    rankings = ranker.get_algo_ranking(test_algos)
    for i, r in enumerate(rankings, 1):
        print(f"{i}. {r['algorithm']}")
        print(f"   Expected Win Prob: {r['expected_win_prob']:.1%}")
        print(f"   Current Win Rate: {r['current_win_rate']:.1%}")
        print(f"   Sharpe: {r['sharpe']:.2f}")
        print(f"   Total Picks: {r['total_picks']}")
        print()
    
    print("\nML Ranker ready for live trading!")


if __name__ == "__main__":
    main()
