"""
Strategy 027: London Session Momentum
Session-based momentum strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class LondonSessionMomentumStrategy:
    """
    Captures momentum during London session (08:00 - 17:00 UTC).
    London session often sets the trend for the day.
    """
    
    def __init__(
        self,
        session_start: int = 8,
        session_end: int = 17,
        momentum_threshold: float = 0.003,
        volume_multiplier: float = 1.3
    ):
        self.start_hour = session_start
        self.end_hour = session_end
        self.momentum_threshold = momentum_threshold
        self.volume_mult = volume_multiplier
    
    def analyze(
        self,
        hourly_prices: List[float],
        hourly_volumes: List[float],
        hours: List[int]
    ) -> Signal:
        if len(hourly_prices) < self.end_hour + 1:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # London session data
        london_indices = [i for i, h in enumerate(hours) 
                         if self.start_hour <= h <= self.end_hour]
        
        if len(london_indices) < 3:
            return Signal("hold", 0.0, {"error": "Insufficient London session data"})
        
        london_prices = [hourly_prices[i] for i in london_indices]
        london_volumes = [hourly_volumes[i] for i in london_indices]
        
        # Session momentum
        session_open = london_prices[0]
        session_high = max(london_prices)
        session_low = min(london_prices)
        current = london_prices[-1]
        
        momentum = (current - session_open) / session_open
        
        # Volume analysis
        avg_volume = np.mean(hourly_volumes)
        london_avg_volume = np.mean(london_volumes)
        volume_surge = london_avg_volume / avg_volume
        
        # Trend strength
        up_move = session_high - session_open
        down_move = session_open - session_low
        
        metadata = {
            "session_open": session_open,
            "session_high": session_high,
            "session_low": session_low,
            "current": current,
            "momentum": momentum,
            "volume_surge": volume_surge,
            "up_move": up_move,
            "down_move": down_move
        }
        
        # Strong bullish momentum with volume
        if momentum > self.momentum_threshold and volume_surge > self.volume_mult:
            confidence = min(0.85, 0.6 + momentum * 50)
            return Signal("buy", confidence, {**metadata, "reason": "London bullish momentum"})
        
        # Strong bearish momentum with volume
        if momentum < -self.momentum_threshold and volume_surge > self.volume_mult:
            confidence = min(0.85, 0.6 + abs(momentum) * 50)
            return Signal("sell", confidence, {**metadata, "reason": "London bearish momentum"})
        
        # Moderate momentum
        if momentum > self.momentum_threshold * 0.7:
            return Signal("buy", 0.55, {**metadata, "reason": "Positive London momentum"})
        
        if momentum < -self.momentum_threshold * 0.7:
            return Signal("sell", 0.55, {**metadata, "reason": "Negative London momentum"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    hours = list(range(24))
    base = 40000
    
    # London session bullish
    prices = [base + np.random.randn() * 30 for _ in range(8)]  # Pre-London
    for h in range(8, 18):
        prices.append(prices[-1] + 50 + np.random.randn() * 20)
    for h in range(18, 24):
        prices.append(prices[-1] + np.random.randn() * 30)
    
    volumes = [80 + np.random.randn() * 10 for _ in range(8)]
    volumes.extend([150 + np.random.randn() * 20 for _ in range(10)])  # London
    volumes.extend([100 + np.random.randn() * 15 for _ in range(6)])
    
    strategy = LondonSessionMomentumStrategy()
    signal = strategy.analyze(prices, volumes, hours)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
