"""
Strategy 026: Asian Session Breakout
Session-based trading strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class AsianSessionBreakoutStrategy:
    """
    Trades breakouts of the Asian session range.
    Asian session: 00:00 - 09:00 UTC
    """
    
    def __init__(
        self,
        session_start_hour: int = 0,
        session_end_hour: int = 9,
        breakout_threshold: float = 0.005,
        min_range_pct: float = 0.003
    ):
        self.start_hour = session_start_hour
        self.end_hour = session_end_hour
        self.breakout_threshold = breakout_threshold
        self.min_range = min_range_pct
    
    def analyze(
        self,
        hourly_prices: List[float],
        hourly_volumes: List[float],
        hours: List[int]  # Hour of day for each price
    ) -> Signal:
        if len(hourly_prices) < 24:
            return Signal("hold", 0.0, {"error": "Insufficient hourly data"})
        
        # Identify Asian session candles
        asian_indices = [i for i, h in enumerate(hours) 
                        if self.start_hour <= h < self.end_hour]
        
        if len(asian_indices) < 5:
            return Signal("hold", 0.0, {"error": "Insufficient Asian session data"})
        
        # Asian session range
        asian_prices = [hourly_prices[i] for i in asian_indices]
        asian_high = max(asian_prices)
        asian_low = min(asian_prices)
        asian_range = (asian_high - asian_low) / asian_low
        
        # Current price (post-Asian session)
        current_price = hourly_prices[-1]
        
        # Breakout detection
        breakout_up = current_price > asian_high * (1 + self.breakout_threshold)
        breakout_down = current_price < asian_low * (1 - self.breakout_threshold)
        
        # Volume confirmation
        asian_volume = sum(hourly_volumes[i] for i in asian_indices)
        recent_volume = sum(hourly_volumes[-3:])
        volume_confirm = recent_volume > asian_volume / len(asian_indices) * 1.5
        
        metadata = {
            "asian_high": asian_high,
            "asian_low": asian_low,
            "asian_range_pct": asian_range * 100,
            "current_price": current_price,
            "breakout_up": breakout_up,
            "breakout_down": breakout_down,
            "volume_confirm": volume_confirm
        }
        
        # Range too small - avoid false breakouts
        if asian_range < self.min_range:
            return Signal("hold", 0.1, {**metadata, "reason": "Asian range too small"})
        
        # Breakout up
        if breakout_up and volume_confirm:
            confidence = min(0.8, 0.6 + (current_price - asian_high) / asian_high * 50)
            return Signal("buy", confidence, {**metadata, "reason": "Asian session breakout up"})
        
        # Breakout down
        if breakout_down and volume_confirm:
            confidence = min(0.8, 0.6 + (asian_low - current_price) / asian_low * 50)
            return Signal("sell", confidence, {**metadata, "reason": "Asian session breakout down"})
        
        # Inside range - mean reversion potential
        if asian_low < current_price < asian_high:
            mid = (asian_high + asian_low) / 2
            if current_price < mid * 0.995:
                return Signal("buy", 0.5, {**metadata, "reason": "Price near Asian low"})
            if current_price > mid * 1.005:
                return Signal("sell", 0.5, {**metadata, "reason": "Price near Asian high"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    # Generate 24 hours of data
    hours = list(range(24))
    base_price = 40000
    
    # Asian session (0-9) with range
    prices = []
    for h in hours:
        if h < 9:
            prices.append(base_price + np.random.randn() * 50)
        elif h == 9:
            prices.append(max(prices) + 200)  # Breakout
        else:
            prices.append(prices[-1] + np.random.randn() * 30)
    
    volumes = [100 + np.random.randn() * 20 for _ in range(24)]
    volumes[9] = 300  # High volume on breakout
    
    strategy = AsianSessionBreakoutStrategy()
    signal = strategy.analyze(prices, volumes, hours)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
