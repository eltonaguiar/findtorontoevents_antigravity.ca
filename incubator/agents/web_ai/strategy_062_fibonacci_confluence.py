"""
Strategy 062: Fibonacci Confluence
Fibonacci retracement and extension strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class FibonacciConfluenceStrategy:
    """
    Trades Fibonacci confluence zones.
    Multiple Fib levels aligning = strong support/resistance.
    """
    
    def __init__(
        self,
        tolerance: float = 0.02,
        min_confluence: int = 2,
        lookback: int = 50
    ):
        self.tolerance = tolerance
        self.min_confluence = min_confluence
        self.lookback = lookback
        self.fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618]
    
    def _calculate_fib_levels(self, swing_low: float, swing_high: float) -> List[float]:
        """Calculate Fibonacci retracement levels"""
        diff = swing_high - swing_low
        return [swing_high - diff * level for level in self.fib_levels]
    
    def analyze(
        self,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(prices) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        current_price = prices[-1]
        
        # Find recent swing high and low
        recent_highs = highs[-self.lookback:]
        recent_lows = lows[-self.lookback:]
        
        swing_high = max(recent_highs)
        swing_low = min(recent_lows)
        
        # Calculate Fib levels
        fib_levels = self._calculate_fib_levels(swing_low, swing_high)
        
        # Find confluence (price near multiple fib levels from different swings)
        confluence_zones = []
        for level in fib_levels:
            if abs(current_price - level) / current_price < self.tolerance:
                confluence_zones.append(level)
        
        # Position in Fib range
        fib_range = swing_high - swing_low
        position = (current_price - swing_low) / fib_range if fib_range > 0 else 0.5
        
        # Find nearest support and resistance
        supports = [l for l in fib_levels if l < current_price]
        resistances = [l for l in fib_levels if l > current_price]
        
        nearest_support = max(supports) if supports else swing_low
        nearest_resistance = min(resistances) if resistances else swing_high
        
        # Distance to levels
        dist_to_support = (current_price - nearest_support) / current_price
        dist_to_resistance = (nearest_resistance - current_price) / current_price
        
        metadata = {
            "swing_high": swing_high,
            "swing_low": swing_low,
            "fib_levels": len(confluence_zones),
            "position": position,
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
            "dist_to_support": dist_to_support,
            "dist_to_resistance": dist_to_resistance
        }
        
        # Near strong confluence support
        if len(confluence_zones) >= self.min_confluence and dist_to_support < self.tolerance:
            confidence = min(0.8, 0.55 + len(confluence_zones) * 0.1)
            return Signal("buy", confidence, {**metadata, "reason": "Fib confluence support"})
        
        # Near strong confluence resistance
        if len(confluence_zones) >= self.min_confluence and dist_to_resistance < self.tolerance:
            confidence = min(0.8, 0.55 + len(confluence_zones) * 0.1)
            return Signal("sell", confidence, {**metadata, "reason": "Fib confluence resistance"})
        
        # Golden pocket (0.618-0.65)
        if 0.61 < position < 0.66 and dist_to_support < 0.01:
            return Signal("buy", 0.65, {**metadata, "reason": "Golden pocket support"})
        
        # 0.382 bounce
        if 0.37 < position < 0.42:
            if dist_to_support < 0.01:
                return Signal("buy", 0.6, {**metadata, "reason": "0.382 support"})
            if dist_to_resistance < 0.01:
                return Signal("sell", 0.6, {**metadata, "reason": "0.382 resistance"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    # Price near 0.618 Fib level
    swing_low = 35000
    swing_high = 45000
    current = swing_high - (swing_high - swing_low) * 0.618  # ~38820
    
    prices = [40000] * 20 + [current]
    highs = [swing_high - 1000] * 20 + [current + 100]
    lows = [swing_low + 1000] * 20 + [current - 100]
    volumes = [1000 + np.random.randn() * 200 for _ in range(21)]
    
    strategy = FibonacciConfluenceStrategy()
    signal = strategy.analyze(prices, highs, lows, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
