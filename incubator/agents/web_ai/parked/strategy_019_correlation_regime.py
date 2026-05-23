"""
Strategy 019: Correlation Regime Detection
Dynamic correlation regime strategy
"""
from dataclasses import dataclass
from typing import List, Dict
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class CorrelationRegimeStrategy:
    """
    Detects changes in correlation regimes between assets.
    Adapts strategy based on current correlation environment.
    """
    
    def __init__(
        self,
        short_window: int = 7,
        long_window: int = 30,
        regime_threshold: float = 0.3
    ):
        self.short_window = short_window
        self.long_window = long_window
        self.regime_threshold = regime_threshold
    
    def _calculate_returns(self, prices: List[float]) -> List[float]:
        return [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
    
    def _correlation(self, x: List[float], y: List[float]) -> float:
        if len(x) != len(y) or len(x) < 2:
            return 0
        return np.corrcoef(x, y)[0, 1]
    
    def analyze(
        self,
        btc_prices: List[float],
        correlations: Dict[str, List[float]],  # Pre-calculated correlations with various assets
        btc_volumes: List[float]
    ) -> Signal:
        if len(btc_prices) < self.long_window:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate BTC momentum
        btc_returns = self._calculate_returns(btc_prices)
        short_momentum = sum(btc_returns[-self.short_window:])
        long_momentum = sum(btc_returns[-self.long_window:])
        
        # Average correlation across assets
        avg_correlations = {}
        for asset, corr_series in correlations.items():
            if len(corr_series) >= self.short_window:
                avg_correlations[asset] = np.mean(corr_series[-self.short_window:])
        
        if not avg_correlations:
            return Signal("hold", 0.1, {"error": "No correlation data"})
        
        avg_corr = np.mean(list(avg_correlations.values()))
        
        # Regime detection
        if avg_corr > self.regime_threshold:
            regime = "high_correlation"
        elif avg_corr < -self.regime_threshold:
            regime = "inverse_correlation"
        else:
            regime = "low_correlation"
        
        metadata = {
            "avg_correlation": avg_corr,
            "regime": regime,
            "short_momentum": short_momentum,
            "long_momentum": long_momentum,
            "asset_correlations": avg_correlations
        }
        
        # High correlation regime - follow the leader
        if regime == "high_correlation" and short_momentum > 0.03:
            return Signal("buy", 0.7, {**metadata, "reason": "High correlation, positive momentum"})
        
        if regime == "high_correlation" and short_momentum < -0.03:
            return Signal("sell", 0.7, {**metadata, "reason": "High correlation, negative momentum"})
        
        # Low correlation regime - mean reversion favored
        if regime == "low_correlation":
            if short_momentum < -0.05 and long_momentum > 0:
                return Signal("buy", 0.65, {**metadata, "reason": "Low correlation, mean reversion setup"})
            if short_momentum > 0.05 and long_momentum < 0:
                return Signal("sell", 0.65, {**metadata, "reason": "Low correlation, mean reversion setup"})
        
        # Inverse correlation - contrarian signals
        if regime == "inverse_correlation":
            if short_momentum > 0.04:
                return Signal("sell", 0.6, {**metadata, "reason": "Inverse regime, take profits"})
        
        return Signal("hold", 0.25, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 40
    btc = [40000 + i * 100 + np.random.randn() * 300 for i in range(n)]
    volumes = [1000 + np.random.randn() * 200 for _ in range(n)]
    
    # Simulated correlations
    correlations = {
        "SPX": [0.6 + np.random.randn() * 0.1 for _ in range(n)],
        "DXY": [-0.4 + np.random.randn() * 0.1 for _ in range(n)],
        "GOLD": [0.2 + np.random.randn() * 0.1 for _ in range(n)]
    }
    
    strategy = CorrelationRegimeStrategy()
    signal = strategy.analyze(btc, correlations, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
