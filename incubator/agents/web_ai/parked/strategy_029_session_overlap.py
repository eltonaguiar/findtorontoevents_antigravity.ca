"""
Strategy 029: Session Overlap Momentum
Trading the London-NY overlap
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class SessionOverlapStrategy:
    """
    Trades the London-NY overlap (13:00 - 17:00 UTC).
    Highest liquidity period of the day.
    """
    
    def __init__(
        self,
        overlap_start: int = 13,
        overlap_end: int = 17,
        breakout_threshold: float = 0.004,
        volume_confirm: float = 1.5
    ):
        self.overlap_start = overlap_start
        self.overlap_end = overlap_end
        self.breakout_threshold = breakout_threshold
        self.volume_confirm = volume_confirm
    
    def analyze(
        self,
        hourly_prices: List[float],
        hourly_volumes: List[float],
        hours: List[int]
    ) -> Signal:
        if len(hourly_prices) < 24:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Pre-overlap range (London morning)
        pre_indices = [i for i, h in enumerate(hours) 
                      if 8 <= h < self.overlap_start]
        overlap_indices = [i for i, h in enumerate(hours) 
                          if self.overlap_start <= h <= self.overlap_end]
        
        if len(pre_indices) < 3 or len(overlap_indices) < 2:
            return Signal("hold", 0.0, {"error": "Insufficient session data"})
        
        # Pre-overlap range
        pre_prices = [hourly_prices[i] for i in pre_indices]
        pre_high = max(pre_prices)
        pre_low = min(pre_prices)
        pre_range = pre_high - pre_low
        
        # Overlap session
        overlap_prices = [hourly_prices[i] for i in overlap_indices]
        overlap_volumes = [hourly_volumes[i] for i in overlap_indices]
        overlap_high = max(overlap_prices)
        overlap_low = min(overlap_prices)
        overlap_current = overlap_prices[-1]
        
        # Volume check
        pre_avg_vol = np.mean([hourly_volumes[i] for i in pre_indices])
        overlap_avg_vol = np.mean(overlap_volumes)
        volume_surge = overlap_avg_vol / pre_avg_vol
        
        # Breakout detection
        breakout_up = overlap_high > pre_high * (1 + self.breakout_threshold)
        breakout_down = overlap_low < pre_low * (1 - self.breakout_threshold)
        
        # Momentum
        overlap_open = overlap_prices[0]
        momentum = (overlap_current - overlap_open) / overlap_open
        
        metadata = {
            "pre_high": pre_high,
            "pre_low": pre_low,
            "overlap_high": overlap_high,
            "overlap_low": overlap_low,
            "overlap_current": overlap_current,
            "breakout_up": breakout_up,
            "breakout_down": breakout_down,
            "momentum": momentum,
            "volume_surge": volume_surge
        }
        
        # Breakout up with volume
        if breakout_up and volume_surge > self.volume_confirm:
            confidence = min(0.9, 0.65 + momentum * 20)
            return Signal("buy", confidence, {**metadata, "reason": "Overlap breakout up"})
        
        # Breakout down with volume
        if breakout_down and volume_surge > self.volume_confirm:
            confidence = min(0.9, 0.65 + abs(momentum) * 20)
            return Signal("sell", confidence, {**metadata, "reason": "Overlap breakout down"})
        
        # Strong momentum within range
        if abs(momentum) > self.breakout_threshold and volume_surge > 1.3:
            if momentum > 0:
                return Signal("buy", 0.65, {**metadata, "reason": "Overlap bullish momentum"})
            else:
                return Signal("sell", 0.65, {**metadata, "reason": "Overlap bearish momentum"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    hours = list(range(24))
    base = 40000
    
    # London morning range
    prices = [base + np.random.randn() * 40 for _ in range(13)]
    volumes = [100 + np.random.randn() * 15 for _ in range(13)]
    
    # Overlap breakout
    pre_high = max(prices)
    for h in range(13, 18):
        prices.append(pre_high + 200 + (h - 13) * 50 + np.random.randn() * 30)
        volumes.append(200 + np.random.randn() * 30)
    
    # Post overlap
    for h in range(18, 24):
        prices.append(prices[-1] + np.random.randn() * 40)
        volumes.append(120 + np.random.randn() * 20)
    
    strategy = SessionOverlapStrategy()
    signal = strategy.analyze(prices, volumes, hours)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
