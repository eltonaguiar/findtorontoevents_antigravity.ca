"""
Strategy 003: Network Velocity Divergence
On-chain metric analyzing Bitcoin network velocity
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class NetworkVelocityStrategy:
    """
    Tracks Bitcoin network velocity (how quickly coins move).
    Low velocity + rising price = strong holders (bullish)
    High velocity + falling price = distribution (bearish)
    """
    
    def __init__(
        self,
        velocity_window: int = 7,
        divergence_threshold: float = 0.3,
        min_history: int = 14
    ):
        self.velocity_window = velocity_window
        self.divergence_threshold = divergence_threshold
        self.min_history = min_history
    
    def analyze(
        self,
        velocity: List[float],
        prices: List[float],
        transaction_volume: List[float]
    ) -> Signal:
        if len(velocity) < self.min_history or len(prices) < self.min_history:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Normalize velocity and price for comparison
        vel_norm = np.array(velocity) / np.mean(velocity[-self.min_history:])
        price_norm = np.array(prices) / np.mean(prices[-self.min_history:])
        
        # Calculate rate of change
        vel_roc = (vel_norm[-1] - vel_norm[-self.velocity_window]) / vel_norm[-self.velocity_window]
        price_roc = (price_norm[-1] - price_norm[-self.velocity_window]) / price_norm[-self.velocity_window]
        
        # Divergence calculation
        divergence = price_roc - vel_roc
        
        # Moving averages
        vel_ma_short = np.mean(velocity[-7:])
        vel_ma_long = np.mean(velocity[-14:])
        
        metadata = {
            "velocity_roc": vel_roc,
            "price_roc": price_roc,
            "divergence": divergence,
            "velocity_trend": vel_ma_short - vel_ma_long,
            "current_velocity": velocity[-1]
        }
        
        # Bullish divergence: Price up, velocity down (holders not selling)
        if price_roc > 0.05 and vel_roc < -0.05 and divergence > self.divergence_threshold:
            confidence = min(0.85, 0.5 + divergence)
            return Signal("buy", confidence, metadata)
        
        # Bearish divergence: Price down, velocity up (panic selling)
        if price_roc < -0.05 and vel_roc > 0.05 and divergence < -self.divergence_threshold:
            confidence = min(0.85, 0.5 + abs(divergence))
            return Signal("sell", confidence, metadata)
        
        # Velocity trend confirmation
        if vel_ma_short < vel_ma_long * 0.95 and price_roc > 0:
            return Signal("buy", 0.6, {**metadata, "reason": "Decreasing velocity in uptrend"})
        
        if vel_ma_short > vel_ma_long * 1.05 and price_roc < 0:
            return Signal("sell", 0.6, {**metadata, "reason": "Increasing velocity in downtrend"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n_days = 30
    # Simulate decreasing velocity with increasing price (hodling)
    velocity = [2.0 - i * 0.03 + np.random.randn() * 0.1 for i in range(n_days)]
    prices = [40000 + i * 200 + np.random.randn() * 500 for i in range(n_days)]
    tx_volume = [10000 + np.random.randn() * 1000 for _ in range(n_days)]
    
    strategy = NetworkVelocityStrategy()
    signal = strategy.analyze(velocity, prices, tx_volume)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
