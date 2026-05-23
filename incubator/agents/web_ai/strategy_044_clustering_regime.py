"""
Strategy 044: Clustering Regime Detection
Unsupervised learning regime strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ClusteringRegimeStrategy:
    """
    Uses k-means-like clustering to identify market regimes.
    Trades based on regime characteristics.
    """
    
    def __init__(
        self,
        n_clusters: int = 3,
        lookback: int = 30,
        feature_window: int = 10
    ):
        self.n_clusters = n_clusters
        self.lookback = lookback
        self.feature_window = feature_window
    
    def _extract_features(self, prices: List[float], volumes: List[float]) -> List[float]:
        """Extract regime features"""
        if len(prices) < self.feature_window:
            return [0, 0, 0]
        
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        # Feature 1: Return volatility
        volatility = np.std(returns[-self.feature_window:])
        
        # Feature 2: Trend strength
        ma_short = np.mean(prices[-5:])
        ma_long = np.mean(prices[-self.feature_window:])
        trend = (ma_short - ma_long) / ma_long
        
        # Feature 3: Volume intensity
        vol_ratio = volumes[-1] / np.mean(volumes[-self.feature_window:]) if len(volumes) >= self.feature_window else 1
        
        return [volatility * 100, trend * 100, vol_ratio]
    
    def _simple_cluster(self, features_list: List[List[float]]) -> int:
        """Simple clustering based on feature centroids"""
        if not features_list:
            return 0
        
        # Define cluster centroids (trending up, trending down, ranging)
        centroids = [
            [0.5, 2.0, 1.2],   # Bullish trending
            [0.5, -2.0, 1.2],  # Bearish trending
            [0.3, 0.0, 0.8]    # Low vol ranging
        ]
        
        current = features_list[-1]
        distances = [np.sqrt(sum((c - f) ** 2 for c, f in zip(centroid, current))) 
                    for centroid in centroids]
        
        return distances.index(min(distances))
    
    def analyze(
        self,
        prices: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(prices) < self.lookback + self.feature_window:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Build feature history
        features_history = []
        for i in range(self.lookback, len(prices)):
            feat = self._extract_features(prices[:i], volumes[:i])
            features_history.append(feat)
        
        # Current cluster
        current_cluster = self._simple_cluster(features_history)
        
        # Cluster stability
        recent_clusters = [self._simple_cluster(features_history[:i+1]) 
                          for i in range(max(0, len(features_history)-5), len(features_history))]
        cluster_stability = sum(1 for c in recent_clusters if c == current_cluster) / len(recent_clusters)
        
        # Current features
        current_features = features_history[-1]
        
        metadata = {
            "current_cluster": current_cluster,
            "cluster_stability": cluster_stability,
            "features": current_features,
            "volatility": current_features[0],
            "trend": current_features[1],
            "volume_intensity": current_features[2]
        }
        
        # Bullish trending regime
        if current_cluster == 0 and cluster_stability > 0.6:
            if current_features[1] > 1:
                return Signal("buy", 0.75, {**metadata, "reason": "Bullish regime confirmed"})
        
        # Bearish trending regime
        if current_cluster == 1 and cluster_stability > 0.6:
            if current_features[1] < -1:
                return Signal("sell", 0.75, {**metadata, "reason": "Bearish regime confirmed"})
        
        # Ranging regime - mean reversion
        if current_cluster == 2:
            if current_features[1] > 0.5:
                return Signal("sell", 0.55, {**metadata, "reason": "Ranging regime, near resistance"})
            if current_features[1] < -0.5:
                return Signal("buy", 0.55, {**metadata, "reason": "Ranging regime, near support"})
        
        # Regime transition
        if len(recent_clusters) >= 2 and recent_clusters[-2] != current_cluster:
            if current_cluster == 0:
                return Signal("buy", 0.65, {**metadata, "reason": "Transition to bullish regime"})
            if current_cluster == 1:
                return Signal("sell", 0.65, {**metadata, "reason": "Transition to bearish regime"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 50
    # Bullish trending data
    prices = [40000 + i * 100 + np.random.randn() * 150 for i in range(n)]
    volumes = [1200 + np.random.randn() * 200 for _ in range(n)]
    
    strategy = ClusteringRegimeStrategy()
    signal = strategy.analyze(prices, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
