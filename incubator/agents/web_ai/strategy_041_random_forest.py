"""
Strategy 041: Random Forest Ensemble
ML ensemble strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class RandomForestEnsembleStrategy:
    """
    Simulates Random Forest predictions using feature importance weighting.
    Combines multiple technical signals as an ensemble.
    """
    
    def __init__(
        self,
        n_estimators: int = 10,
        feature_weights: dict = None,
        threshold: float = 0.55
    ):
        self.n_estimators = n_estimators
        self.threshold = threshold
        self.feature_weights = feature_weights or {
            "trend": 0.25,
            "momentum": 0.20,
            "volatility": 0.15,
            "volume": 0.20,
            "mean_reversion": 0.20
        }
    
    def _calculate_features(self, prices: List[float], volumes: List[float]) -> dict:
        """Calculate feature values"""
        if len(prices) < 20:
            return {}
        
        # Trend feature
        ma5 = np.mean(prices[-5:])
        ma20 = np.mean(prices[-20:])
        trend = 1 if ma5 > ma20 else 0
        
        # Momentum feature
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        momentum = 1 if np.mean(returns[-5:]) > 0 else 0
        
        # Volatility feature
        volatility = np.std(returns[-10:])
        vol_feature = 1 if volatility > np.mean([np.std(returns[i:i+10]) for i in range(len(returns)-10)]) else 0
        
        # Volume feature
        vol_ma = np.mean(volumes[-5:])
        volume = 1 if volumes[-1] > vol_ma else 0
        
        # Mean reversion feature
        price_vs_ma = (prices[-1] - ma20) / ma20
        mean_rev = 1 if abs(price_vs_ma) > 0.05 and price_vs_ma < 0 else 0
        
        return {
            "trend": trend,
            "momentum": momentum,
            "volatility": vol_feature,
            "volume": volume,
            "mean_reversion": mean_rev
        }
    
    def analyze(
        self,
        prices: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(prices) < 20:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        features = self._calculate_features(prices, volumes)
        if not features:
            return Signal("hold", 0.0, {"error": "Feature calculation failed"})
        
        # Weighted vote
        bullish_score = 0
        total_weight = 0
        
        for feature, value in features.items():
            weight = self.feature_weights.get(feature, 0.2)
            bullish_score += value * weight
            total_weight += weight
        
        prediction = bullish_score / total_weight if total_weight > 0 else 0.5
        
        # Confidence based on consensus
        feature_values = list(features.values())
        consensus = 1 - np.std(feature_values)
        
        metadata = {
            "features": features,
            "prediction": prediction,
            "consensus": consensus,
            "bullish_score": bullish_score
        }
        
        # Strong bullish consensus
        if prediction > self.threshold and consensus > 0.6:
            confidence = min(0.85, prediction + consensus * 0.2)
            return Signal("buy", confidence, {**metadata, "reason": "RF ensemble bullish"})
        
        # Strong bearish consensus
        if prediction < (1 - self.threshold) and consensus > 0.6:
            confidence = min(0.85, (1 - prediction) + consensus * 0.2)
            return Signal("sell", confidence, {**metadata, "reason": "RF ensemble bearish"})
        
        # Moderate signals
        if prediction > 0.6:
            return Signal("buy", 0.55, {**metadata, "reason": "RF weak bullish"})
        if prediction < 0.4:
            return Signal("sell", 0.55, {**metadata, "reason": "RF weak bearish"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 30
    prices = [40000 + i * 100 + np.random.randn() * 200 for i in range(n)]
    volumes = [1000 + np.random.randn() * 200 for _ in range(n)]
    
    strategy = RandomForestEnsembleStrategy()
    signal = strategy.analyze(prices, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
