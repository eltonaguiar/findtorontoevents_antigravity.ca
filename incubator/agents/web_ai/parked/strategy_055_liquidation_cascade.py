"""
Strategy 055: Liquidation Cascade Detector
Liquidation cascade detection
"""
from dataclasses import dataclass
from typing import List, Dict
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class LiquidationCascadeStrategy:
    """
    Detects liquidation cascades and trades the aftermath.
    Cascades often create temporary price dislocations.
    """
    
    def __init__(
        self,
        liquidation_threshold: float = 10000000,  # $10M
        cascade_window: int = 6,  # hours
        price_change_threshold: float = 0.05,
        recovery_lookback: int = 3
    ):
        self.liq_threshold = liquidation_threshold
        self.cascade_window = cascade_window
        self.price_threshold = price_change_threshold
        self.recovery_lookback = recovery_lookback
    
    def analyze(
        self,
        liquidations_long: List[float],
        liquidations_short: List[float],
        prices: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(liquidations_long) < self.cascade_window:
            return Signal("hold", 0.0, {"error": "Insufficient liquidation data"})
        
        # Recent liquidation volumes
        recent_long_liq = sum(liquidations_long[-self.cascade_window:])
        recent_short_liq = sum(liquidations_short[-self.cascade_window:])
        total_liq = recent_long_liq + recent_short_liq
        
        # Price change during liquidation period
        price_change = (prices[-1] - prices[-self.cascade_window]) / prices[-self.cascade_window]
        
        # Detect cascade type
        if recent_long_liq > recent_short_liq * 3 and price_change < -self.price_threshold:
            cascade_type = "long_liquidation"
        elif recent_short_liq > recent_long_liq * 3 and price_change > self.price_threshold:
            cascade_type = "short_liquidation"
        else:
            cascade_type = "none"
        
        # Recovery signals
        if len(prices) >= self.recovery_lookback + 1:
            recent_price_change = (prices[-1] - prices[-self.recovery_lookback]) / prices[-self.recovery_lookback]
        else:
            recent_price_change = 0
        
        # Volume during cascade
        avg_volume = np.mean(volumes[-self.cascade_window*2:-self.cascade_window])
        cascade_volume = np.mean(volumes[-self.cascade_window:])
        volume_ratio = cascade_volume / avg_volume if avg_volume > 0 else 1
        
        metadata = {
            "total_liquidations": total_liq,
            "long_liquidations": recent_long_liq,
            "short_liquidations": recent_short_liq,
            "price_change": price_change,
            "cascade_type": cascade_type,
            "volume_ratio": volume_ratio,
            "recent_price_change": recent_price_change
        }
        
        # Major long liquidation cascade - potential bottom
        if cascade_type == "long_liquidation" and total_liq > self.liq_threshold:
            if recent_price_change > 0.01:  # Bouncing
                confidence = min(0.85, 0.5 + total_liq / self.liq_threshold * 0.1)
                return Signal("buy", confidence, {**metadata, "reason": "Long cascade bounce"})
            else:
                return Signal("hold", 0.4, {**metadata, "reason": "Long cascade ongoing"})
        
        # Major short liquidation cascade - potential top
        if cascade_type == "short_liquidation" and total_liq > self.liq_threshold:
            if recent_price_change < -0.01:  # Pulling back
                confidence = min(0.85, 0.5 + total_liq / self.liq_threshold * 0.1)
                return Signal("sell", confidence, {**metadata, "reason": "Short cascade pullback"})
            else:
                return Signal("hold", 0.4, {**metadata, "reason": "Short cascade ongoing"})
        
        # Elevated liquidations but not cascade
        if total_liq > self.liq_threshold * 0.5:
            return Signal("hold", 0.35, {**metadata, "reason": "Elevated liquidations"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 12
    # Normal liquidations then cascade
    long_liq = [1e6, 1.2e6, 0.8e6, 1.5e6, 2e6, 1e6, 5e6, 15e6, 20e6, 8e6, 3e6, 2e6]
    short_liq = [0.5e6, 0.8e6, 1e6, 0.6e6, 0.9e6, 1.2e6, 1e6, 2e6, 3e6, 1.5e6, 1e6, 0.8e6]
    
    # Price drops during cascade then recovers
    prices = [40000, 39900, 39850, 39700, 39500, 39200, 38500, 37500, 
              36500, 37000, 37500, 37800]
    volumes = [1000 + np.random.randn() * 200 for _ in range(n)]
    volumes[7:9] = [5000, 6000]  # High volume during cascade
    
    strategy = LiquidationCascadeStrategy()
    signal = strategy.analyze(long_liq, short_liq, prices, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
