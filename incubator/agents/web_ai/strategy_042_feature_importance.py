"""
Strategy 042: Feature Importance Ranker
ML feature selection strategy
"""
from dataclasses import dataclass
from typing import List, Dict
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class FeatureImportanceStrategy:
    """
    Dynamically ranks features by their predictive power.
    Adapts signal weights based on current market regime.
    """
    
    def __init__(
        self,
        lookback: int = 30,
        top_n_features: int = 3,
        min_importance: float = 0.1
    ):
        self.lookback = lookback
        self.top_n = top_n_features
        self.min_importance = min_importance
    
    def _calculate_feature_performance(self, feature_values: List[float], forward_returns: List[float]) -> float:
        """Calculate correlation between feature and forward returns"""
        if len(feature_values) != len(forward_returns) or len(feature_values) < 5:
            return 0
        
        correlation = np.corrcoef(feature_values, forward_returns)[0, 1]
        return abs(correlation) if not np.isnan(correlation) else 0
    
    def analyze(
        self,
        prices: List[float],
        features: Dict[str, List[float]],  # Feature name to historical values
        volumes: List[float]
    ) -> Signal:
        if len(prices) < self.lookback + 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate forward returns
        forward_returns = [(prices[i+1] - prices[i]) / prices[i] 
                          for i in range(len(prices)-1)]
        
        # Rank features by predictive power
        feature_scores = {}
        for name, values in features.items():
            if len(values) >= len(forward_returns):
                score = self._calculate_feature_performance(
                    values[-len(forward_returns):], 
                    forward_returns
                )
                feature_scores[name] = score
        
        if not feature_scores:
            return Signal("hold", 0.1, {"error": "No valid features"})
        
        # Select top features
        sorted_features = sorted(feature_scores.items(), key=lambda x: x[1], reverse=True)
        top_features = sorted_features[:self.top_n]
        
        # Get current values of top features
        current_signals = {}
        for name, score in top_features:
            if name in features and features[name]:
                # Normalize to -1 to 1
                recent = features[name][-self.lookback:]
                current = features[name][-1]
                mean = np.mean(recent)
                std = np.std(recent) if np.std(recent) > 0 else 1
                normalized = (current - mean) / std
                current_signals[name] = normalized
        
        # Weighted consensus
        total_weight = sum(score for _, score in top_features)
        weighted_signal = sum(current_signals.get(name, 0) * score 
                             for name, score in top_features) / (total_weight + 1e-8)
        
        metadata = {
            "feature_scores": feature_scores,
            "top_features": [n for n, _ in top_features],
            "weighted_signal": weighted_signal,
            "current_signals": current_signals
        }
        
        # Signal generation
        if weighted_signal > 0.5:
            confidence = min(0.8, 0.5 + weighted_signal * 0.3)
            return Signal("buy", confidence, {**metadata, "reason": "Top features bullish"})
        
        if weighted_signal < -0.5:
            confidence = min(0.8, 0.5 + abs(weighted_signal) * 0.3)
            return Signal("sell", confidence, {**metadata, "reason": "Top features bearish"})
        
        return Signal("hold", 0.25, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 40
    prices = [40000 + i * 80 + np.random.randn() * 150 for i in range(n)]
    volumes = [1000 + np.random.randn() * 200 for _ in range(n)]
    
    # Generate features
    features = {
        "rsi": [50 + np.sin(i * 0.3) * 20 + np.random.randn() * 5 for i in range(n)],
        "macd": [np.sin(i * 0.2) * 5 + np.random.randn() for i in range(n)],
        "bb_position": [0.5 + np.sin(i * 0.25) * 0.3 + np.random.randn() * 0.1 for i in range(n)],
        "volume_ratio": [1 + np.random.randn() * 0.3 for _ in range(n)]
    }
    
    strategy = FeatureImportanceStrategy()
    signal = strategy.analyze(prices, features, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
