"""
Strategy 043: Anomaly Detection
Outlier-based trading strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class AnomalyDetectionStrategy:
    """
    Detects anomalous price movements using statistical methods.
    Trades mean reversion after extreme moves.
    """
    
    def __init__(
        self,
        lookback: int = 50,
        zscore_threshold: float = 2.5,
        isolation_threshold: float = 0.1
    ):
        self.lookback = lookback
        self.zscore_threshold = zscore_threshold
        self.isolation_threshold = isolation_threshold
    
    def _calculate_zscore(self, value: float, historical: List[float]) -> float:
        mean = np.mean(historical)
        std = np.std(historical)
        return (value - mean) / (std + 1e-8)
    
    def _isolation_score(self, returns: List[float]) -> float:
        """Simple isolation score based on distance from neighbors"""
        if len(returns) < 3:
            return 0.5
        
        current = returns[-1]
        distances = [abs(current - r) for r in returns[:-1]]
        avg_distance = np.mean(distances)
        max_distance = max(distances) if distances else 1
        
        return avg_distance / (max_distance + 1e-8)
    
    def analyze(
        self,
        prices: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(prices) < self.lookback + 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate returns
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        current_return = returns[-1]
        historical_returns = returns[-self.lookback:-1]
        
        # Z-score of current return
        zscore = self._calculate_zscore(current_return, historical_returns)
        
        # Isolation score
        isolation = self._isolation_score(returns[-10:])
        
        # Volume anomaly
        vol_zscore = self._calculate_zscore(volumes[-1], volumes[-self.lookback:-1])
        
        # Price level anomaly
        price_ma = np.mean(prices[-self.lookback:])
        price_zscore = (prices[-1] - price_ma) / (np.std(prices[-self.lookback:]) + 1e-8)
        
        metadata = {
            "return_zscore": zscore,
            "isolation_score": isolation,
            "volume_zscore": vol_zscore,
            "price_zscore": price_zscore,
            "current_return": current_return
        }
        
        # Extreme positive anomaly - mean reversion sell
        if zscore > self.zscore_threshold and isolation > self.isolation_threshold:
            confidence = min(0.8, 0.5 + (zscore - self.zscore_threshold) * 0.15)
            return Signal("sell", confidence, {**metadata, "reason": "Positive anomaly detected"})
        
        # Extreme negative anomaly - mean reversion buy
        if zscore < -self.zscore_threshold and isolation > self.isolation_threshold:
            confidence = min(0.8, 0.5 + (abs(zscore) - self.zscore_threshold) * 0.15)
            return Signal("buy", confidence, {**metadata, "reason": "Negative anomaly detected"})
        
        # Volume anomaly with price move
        if abs(vol_zscore) > 3 and abs(zscore) > 2:
            if zscore > 0:
                return Signal("sell", 0.7, {**metadata, "reason": "Volume-price anomaly up"})
            else:
                return Signal("buy", 0.7, {**metadata, "reason": "Volume-price anomaly down"})
        
        # Price far from mean
        if abs(price_zscore) > 2.5:
            if price_zscore > 0:
                return Signal("sell", 0.6, {**metadata, "reason": "Price far above mean"})
            else:
                return Signal("buy", 0.6, {**metadata, "reason": "Price far below mean"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 60
    # Normal returns
    returns = [np.random.randn() * 0.01 for _ in range(n-1)]
    # Extreme positive return
    returns[-1] = 0.08
    
    prices = [40000]
    for r in returns:
        prices.append(prices[-1] * (1 + r))
    
    volumes = [1000 + np.random.randn() * 150 for _ in range(n-1)]
    volumes.append(2500)  # Volume spike
    
    strategy = AnomalyDetectionStrategy()
    signal = strategy.analyze(prices, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
