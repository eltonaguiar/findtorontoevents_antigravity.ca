"""
Strategy 054: Fear Greed Index
Fear and greed index strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class FearGreedStrategy:
    """
    Uses fear and greed index for contrarian trading.
    Extreme fear = buy opportunity
    Extreme greed = sell opportunity
    """
    
    def __init__(
        self,
        extreme_fear: float = 20,
        fear: float = 40,
        greed: float = 60,
        extreme_greed: float = 80,
        lookback: int = 7
    ):
        self.extreme_fear = extreme_fear
        self.fear = fear
        self.greed = greed
        self.extreme_greed = extreme_greed
        self.lookback = lookback
    
    def analyze(
        self,
        fg_index: List[float],  # 0-100 scale
        prices: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(fg_index) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        current_fg = fg_index[-1]
        fg_ma = np.mean(fg_index[-self.lookback:])
        
        # Trend
        fg_trend = current_fg - fg_index[-self.lookback]
        
        # Determine zone
        if current_fg <= self.extreme_fear:
            zone = "extreme_fear"
        elif current_fg <= self.fear:
            zone = "fear"
        elif current_fg >= self.extreme_greed:
            zone = "extreme_greed"
        elif current_fg >= self.greed:
            zone = "greed"
        else:
            zone = "neutral"
        
        # Price context
        price_change = (prices[-1] - prices[-self.lookback]) / prices[-self.lookback]
        
        metadata = {
            "current_fg": current_fg,
            "fg_ma": fg_ma,
            "fg_trend": fg_trend,
            "zone": zone,
            "price_change": price_change
        }
        
        # Extreme fear - strong buy
        if zone == "extreme_fear" and fg_trend > 0:
            confidence = min(0.9, 0.6 + (self.extreme_fear - current_fg) / 100)
            return Signal("buy", confidence, {**metadata, "reason": "Extreme fear reversal"})
        
        # Extreme greed - strong sell
        if zone == "extreme_greed" and fg_trend < 0:
            confidence = min(0.9, 0.6 + (current_fg - self.extreme_greed) / 100)
            return Signal("sell", confidence, {**metadata, "reason": "Extreme greed reversal"})
        
        # Fear zone - moderate buy
        if zone == "fear" and fg_trend > 5:
            return Signal("buy", 0.65, {**metadata, "reason": "Fear easing"})
        
        # Greed zone - moderate sell
        if zone == "greed" and fg_trend < -5:
            return Signal("sell", 0.65, {**metadata, "reason": "Greed easing"})
        
        # Fear increasing despite price holding
        if fg_trend < -10 and price_change > -0.05:
            return Signal("buy", 0.6, {**metadata, "reason": "Fear overreaction"})
        
        return Signal("hold", 0.25, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 15
    # Index in extreme fear, recovering
    fg = [15, 16, 18, 20, 22, 25, 28, 30, 32, 35, 38, 40, 42, 45, 48]
    prices = [35000, 35200, 35100, 35300, 35500, 35800, 36000, 36200, 36500, 
              36800, 37000, 37200, 37500, 37800, 38000]
    volumes = [2000 + np.random.randn() * 300 for _ in range(n)]
    
    strategy = FearGreedStrategy()
    signal = strategy.analyze(fg, prices, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
