"""
Strategy 045: PCA Dimension Reduction
Principal component analysis strategy
"""
from dataclasses import dataclass
from typing import List, Dict
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class PCAStrategy:
    """
    Uses PCA-inspired dimension reduction to identify dominant market factors.
    Trades when primary factor aligns with secondary factors.
    """
    
    def __init__(
        self,
        lookback: int = 20,
        n_components: int = 3,
        alignment_threshold: float = 0.7
    ):
        self.lookback = lookback
        self.n_components = n_components
        self.alignment_threshold = alignment_threshold
    
    def _calculate_factors(self, prices: List[float], features: Dict[str, List[float]]) -> List[float]:
        """Calculate simplified principal components"""
        if len(prices) < self.lookback:
            return [0, 0, 0]
        
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        # Factor 1: Price momentum (dominant)
        momentum = np.mean(returns[-5:]) * 100
        
        # Factor 2: Volatility
        volatility = np.std(returns[-10:]) * 100
        
        # Factor 3: Volume-weighted trend
        if "volume" in features and len(features["volume"]) >= len(returns):
            vw_returns = [r * (features["volume"][-(len(returns)-i)] / np.mean(list(features["volume"])[-10:]))
                         for i, r in enumerate(returns[-5:])]
            vw_trend = np.mean(vw_returns) * 100
        else:
            vw_trend = momentum * 0.8
        
        return [momentum, volatility, vw_trend]
    
    def analyze(
        self,
        prices: List[float],
        features: Dict[str, List[float]],
        market_data: Dict[str, List[float]]
    ) -> Signal:
        if len(prices) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate current factors
        current_factors = self._calculate_factors(prices, features)
        
        # Calculate historical factor variance
        factor_history = []
        for i in range(self.lookback, len(prices)):
            hist_features = {k: v[:i] for k, v in features.items()}
            f = self._calculate_factors(prices[:i], hist_features)
            factor_history.append(f)
        
        # Explained variance (simplified)
        if factor_history:
            variances = [np.std([f[i] for f in factor_history]) for i in range(3)]
            total_var = sum(variances) + 1e-8
            explained_var = [v / total_var for v in variances]
        else:
            explained_var = [0.5, 0.3, 0.2]
        
        # Factor alignment
        signs = [np.sign(f) for f in current_factors]
        alignment = sum(1 for s in signs if s == signs[0]) / len(signs)
        
        # Factor momentum
        if len(factor_history) >= 2:
            factor_change = [current_factors[i] - factor_history[-2][i] for i in range(3)]
        else:
            factor_change = [0, 0, 0]
        
        metadata = {
            "factors": current_factors,
            "explained_variance": explained_var,
            "alignment": alignment,
            "factor_change": factor_change,
            "dominant_factor": explained_var.index(max(explained_var))
        }
        
        # Strong factor alignment bullish
        if alignment >= self.alignment_threshold and signs[0] > 0:
            if explained_var[0] > 0.4:  # Dominant momentum factor
                confidence = min(0.85, 0.5 + alignment * 0.3 + explained_var[0] * 0.2)
                return Signal("buy", confidence, {**metadata, "reason": "Factors aligned bullish"})
        
        # Strong factor alignment bearish
        if alignment >= self.alignment_threshold and signs[0] < 0:
            if explained_var[0] > 0.4:
                confidence = min(0.85, 0.5 + alignment * 0.3 + explained_var[0] * 0.2)
                return Signal("sell", confidence, {**metadata, "reason": "Factors aligned bearish"})
        
        # Primary factor signal
        if explained_var[0] > 0.5 and abs(current_factors[0]) > 1:
            if current_factors[0] > 0:
                return Signal("buy", 0.6, {**metadata, "reason": "Primary factor bullish"})
            else:
                return Signal("sell", 0.6, {**metadata, "reason": "Primary factor bearish"})
        
        # Factor divergence
        if alignment < 0.5:
            return Signal("hold", 0.3, {**metadata, "reason": "Factor divergence - caution"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 35
    prices = [40000 + i * 90 + np.random.randn() * 120 for i in range(n)]
    
    features = {
        "volume": [1000 + np.random.randn() * 200 for _ in range(n)],
        "rsi": [55 + np.sin(i * 0.2) * 15 for i in range(n)]
    }
    
    market_data = {"btc_dominance": [0.4 + np.random.randn() * 0.02 for _ in range(n)]}
    
    strategy = PCAStrategy()
    signal = strategy.analyze(prices, features, market_data)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
