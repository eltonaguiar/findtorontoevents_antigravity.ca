"""
Strategy 047: Cointegration Trading
Cointegration-based statistical arbitrage
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class CointegrationStrategy:
    """
    Uses cointegration relationship for mean reversion trading.
    More robust than correlation for non-stationary series.
    """
    
    def __init__(
        self,
        lookback: int = 60,
        entry_threshold: float = 2.0,
        exit_threshold: float = 0.5,
        half_life_max: int = 10
    ):
        self.lookback = lookback
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.half_life_max = half_life_max
    
    def _estimate_half_life(self, spread: List[float]) -> float:
        """Estimate half-life of mean reversion using AR(1)"""
        if len(spread) < 10:
            return float('inf')
        
        # Lagged spread
        spread_lag = spread[:-1]
        spread_diff = [spread[i+1] - spread[i] for i in range(len(spread)-1)]
        
        # Regression: delta_spread = alpha + beta * spread_lag
        x = np.array(spread_lag)
        y = np.array(spread_diff)
        
        if np.var(x) == 0:
            return float('inf')
        
        beta = np.cov(x, y)[0, 1] / np.var(x)
        
        if beta >= 0:
            return float('inf')
        
        half_life = -np.log(2) / beta
        return half_life
    
    def analyze(
        self,
        asset1_prices: List[float],
        asset2_prices: List[float]
    ) -> Signal:
        if len(asset1_prices) < self.lookback or len(asset2_prices) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate spread (simplified cointegration)
        # Use log prices for better statistical properties
        log_p1 = [np.log(p) for p in asset1_prices[-self.lookback:]]
        log_p2 = [np.log(p) for p in asset2_prices[-self.lookback:]]
        
        # Estimate beta via regression
        x = np.array(log_p2)
        y = np.array(log_p1)
        beta = np.cov(x, y)[0, 1] / np.var(x) if np.var(x) > 0 else 1
        
        # Calculate spread
        spread = [y[i] - beta * x[i] for i in range(len(x))]
        
        # Z-score
        spread_mean = np.mean(spread)
        spread_std = np.std(spread)
        current_spread = spread[-1]
        zscore = (current_spread - spread_mean) / (spread_std + 1e-8)
        
        # Half-life estimation
        half_life = self._estimate_half_life(spread)
        
        # Stationarity check (simplified)
        is_mean_reverting = half_life < self.half_life_max and half_life > 0
        
        metadata = {
            "beta": beta,
            "spread": current_spread,
            "zscore": zscore,
            "half_life": half_life,
            "is_mean_reverting": is_mean_reverting,
            "spread_mean": spread_mean
        }
        
        if not is_mean_reverting:
            return Signal("hold", 0.1, {**metadata, "reason": "Not mean-reverting"})
        
        # Entry signals
        if zscore > self.entry_threshold:
            confidence = min(0.8, 0.5 + (zscore - self.entry_threshold) * 0.15)
            return Signal("sell", confidence, {**metadata, "reason": "Cointegration spread high"})
        
        if zscore < -self.entry_threshold:
            confidence = min(0.8, 0.5 + (abs(zscore) - self.entry_threshold) * 0.15)
            return Signal("buy", confidence, {**metadata, "reason": "Cointegration spread low"})
        
        # Exit signal
        if abs(zscore) < self.exit_threshold:
            return Signal("hold", 0.3, {**metadata, "reason": "Spread normalized"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 70
    # Cointegrated series
    t = np.linspace(0, 10, n)
    asset2 = 2000 + 100 * t + np.random.randn(n) * 50
    asset1 = 4000 + 200 * t + np.random.randn(n) * 80 + 0.5 * (asset2 - 2000)
    
    # Create temporary divergence
    asset1[-10:] = [a + 300 for a in asset1[-10:]]
    
    strategy = CointegrationStrategy()
    signal = strategy.analyze(asset1.tolist(), asset2.tolist())
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
