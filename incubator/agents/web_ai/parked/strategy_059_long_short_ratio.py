"""
Strategy 059: Long Short Ratio
Long/short position ratio analysis
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class LongShortRatioStrategy:
    """
    Analyzes long/short ratio for contrarian signals.
    Extreme ratios often mark turning points.
    """
    
    def __init__(
        self,
        extreme_long: float = 3.0,
        extreme_short: float = 0.5,
        lookback: int = 20,
        threshold: float = 0.1
    ):
        self.extreme_long = extreme_long
        self.extreme_short = extreme_short
        self.lookback = lookback
        self.threshold = threshold
    
    def analyze(
        self,
        long_short_ratio: List[float],
        prices: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(long_short_ratio) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        current_ratio = long_short_ratio[-1]
        ratio_ma = np.mean(long_short_ratio[-self.lookback:])
        
        # Ratio trend
        ratio_change = current_ratio - long_short_ratio[-self.lookback]
        
        # Percentiles
        sorted_ratios = sorted(long_short_ratio[-self.lookback:])
        percentile = sum(1 for r in sorted_ratios if r < current_ratio) / len(sorted_ratios)
        
        # Price context
        price_change = (prices[-1] - prices[-5]) / prices[-5] if len(prices) >= 5 else 0
        
        metadata = {
            "current_ratio": current_ratio,
            "ratio_ma": ratio_ma,
            "ratio_change": ratio_change,
            "percentile": percentile,
            "price_change": price_change
        }
        
        # Extreme long ratio - contrarian sell
        if current_ratio > self.extreme_long and percentile > 0.9:
            if ratio_change < 0:  # Starting to decline
                confidence = min(0.8, 0.5 + (current_ratio - self.extreme_long) * 0.2)
                return Signal("sell", confidence, {**metadata, "reason": "Extreme long ratio declining"})
        
        # Extreme short ratio - contrarian buy
        if current_ratio < self.extreme_short and percentile < 0.1:
            if ratio_change > 0:  # Starting to rise
                confidence = min(0.8, 0.5 + (self.extreme_short - current_ratio) * 0.4)
                return Signal("buy", confidence, {**metadata, "reason": "Extreme short ratio recovering"})
        
        # Ratio diverging from price
        if current_ratio > ratio_ma * 1.2 and price_change < 0:
            return Signal("sell", 0.65, {**metadata, "reason": "Long ratio up, price down"})
        
        if current_ratio < ratio_ma * 0.8 and price_change > 0:
            return Signal("buy", 0.65, {**metadata, "reason": "Short ratio up, price up"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 25
    # Ratio declining from extreme long
    ls_ratio = [3.5 - i * 0.1 + np.random.randn() * 0.1 for i in range(n)]
    prices = [40000 + i * 50 for i in range(n)]
    volumes = [1000 + np.random.randn() * 200 for _ in range(n)]
    
    strategy = LongShortRatioStrategy()
    signal = strategy.analyze(ls_ratio, prices, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
