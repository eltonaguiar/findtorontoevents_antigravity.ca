"""
Strategy 065: Volume Profile
Volume profile analysis strategy
"""
from dataclasses import dataclass
from typing import List, Dict
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class VolumeProfileStrategy:
    """
    Analyzes volume profile to find value areas and POC.
    Trades deviations from value area.
    """
    
    def __init__(
        self,
        lookback: int = 30,
        value_area_pct: float = 0.7,
        deviation_threshold: float = 0.02
    ):
        self.lookback = lookback
        self.va_pct = value_area_pct
        self.deviation = deviation_threshold
    
    def _build_volume_profile(self, prices: List[float], volumes: List[float], bins: int = 10) -> Dict:
        """Build simple volume profile"""
        if len(prices) < bins:
            return {}
        
        price_min = min(prices)
        price_max = max(prices)
        bin_size = (price_max - price_min) / bins
        
        profile = {}
        for i in range(bins):
            level_low = price_min + i * bin_size
            level_high = level_low + bin_size
            level_mid = (level_low + level_high) / 2
            
            vol = sum(volumes[j] for j in range(len(prices))
                     if level_low <= prices[j] <= level_high)
            profile[level_mid] = vol
        
        return profile
    
    def analyze(
        self,
        prices: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(prices) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        recent_prices = prices[-self.lookback:]
        recent_volumes = volumes[-self.lookback:]
        
        # Build volume profile
        profile = self._build_volume_profile(recent_prices, recent_volumes)
        
        if not profile:
            return Signal("hold", 0.1, {"error": "Could not build profile"})
        
        # Point of Control (POC) - highest volume level
        poc = max(profile.items(), key=lambda x: x[1])[0]
        
        # Value Area (70% of volume)
        total_vol = sum(profile.values())
        sorted_levels = sorted(profile.items(), key=lambda x: x[1], reverse=True)
        
        va_volume = 0
        value_area = []
        for level, vol in sorted_levels:
            va_volume += vol
            value_area.append(level)
            if va_volume >= total_vol * self.va_pct:
                break
        
        va_high = max(value_area)
        va_low = min(value_area)
        
        # Current position
        current = prices[-1]
        in_value_area = va_low <= current <= va_high
        
        # Distance from POC
        dist_from_poc = (current - poc) / poc
        
        metadata = {
            "poc": poc,
            "va_high": va_high,
            "va_low": va_low,
            "in_value_area": in_value_area,
            "dist_from_poc": dist_from_poc
        }
        
        # Below value area - potential buy
        if current < va_low * (1 - self.deviation):
            confidence = min(0.75, 0.5 + abs(dist_from_poc) * 10)
            return Signal("buy", confidence, {**metadata, "reason": "Below value area"})
        
        # Above value area - potential sell
        if current > va_high * (1 + self.deviation):
            confidence = min(0.75, 0.5 + abs(dist_from_poc) * 10)
            return Signal("sell", confidence, {**metadata, "reason": "Above value area"})
        
        # Near POC - fair value
        if abs(dist_from_poc) < 0.005:
            return Signal("hold", 0.3, {**metadata, "reason": "Near POC - fair value"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 30
    # Cluster prices around 40000
    prices = [40000 + np.random.randn() * 500 for _ in range(n)]
    prices[-1] = 38500  # Below value area
    
    volumes = [1000 + abs(np.random.randn()) * 300 for _ in range(n)]
    
    strategy = VolumeProfileStrategy()
    signal = strategy.analyze(prices, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
