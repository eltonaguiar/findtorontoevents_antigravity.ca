"""
Strategy 040: Range Expansion Contraction Cycle
Volatility cycle strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class VolatilityCycleStrategy:
    """
    Identifies cycles of volatility expansion and contraction.
    Trades the transitions between phases.
    """
    
    def __init__(
        self,
        range_period: int = 10,
        expansion_threshold: float = 1.3,
        contraction_threshold: float = 0.7,
        cycle_lookback: int = 30
    ):
        self.range_period = range_period
        self.expansion_threshold = expansion_threshold
        self.contraction_threshold = contraction_threshold
        self.cycle_lookback = cycle_lookback
    
    def analyze(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> Signal:
        if len(highs) < self.cycle_lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate daily ranges
        ranges = [h - l for h, l in zip(highs, lows)]
        range_ma = np.mean(ranges[-self.range_period:])
        
        # Historical average range
        historical_avg = np.mean(ranges[-self.cycle_lookback:])
        
        # Current vs historical
        range_ratio = range_ma / historical_avg if historical_avg > 0 else 1
        
        # Phase detection
        if range_ratio > self.expansion_threshold:
            phase = "expansion"
        elif range_ratio < self.contraction_threshold:
            phase = "contraction"
        else:
            phase = "transition"
        
        # Phase momentum
        if len(ranges) >= self.range_period * 2:
            prev_range_ma = np.mean(ranges[-self.range_period*2:-self.range_period])
            phase_momentum = range_ma / prev_range_ma if prev_range_ma > 0 else 1
        else:
            phase_momentum = 1
        
        # Price trend during phase
        price_change = (closes[-1] - closes[-self.range_period]) / closes[-self.range_period]
        
        # Count contraction periods recently
        recent_phases = []
        for i in range(self.cycle_lookback - self.range_period):
            window_ranges = ranges[-(i+self.range_period):-i if i > 0 else len(ranges)]
            if len(window_ranges) >= self.range_period:
                window_avg = np.mean(window_ranges)
                ratio = window_avg / historical_avg
                if ratio < self.contraction_threshold:
                    recent_phases.append("contraction")
                elif ratio > self.expansion_threshold:
                    recent_phases.append("expansion")
        
        contraction_count = recent_phases.count("contraction")
        
        metadata = {
            "range_ratio": range_ratio,
            "phase": phase,
            "phase_momentum": phase_momentum,
            "price_change": price_change,
            "recent_contractions": contraction_count
        }
        
        # Contraction breaking into expansion
        if phase == "contraction" and phase_momentum > 1.1:
            if price_change > 0.005:
                return Signal("buy", 0.75, {**metadata, "reason": "Contraction breaking up"})
            elif price_change < -0.005:
                return Signal("sell", 0.75, {**metadata, "reason": "Contraction breaking down"})
        
        # Extended contraction - prepare for breakout
        if contraction_count >= 3 and phase == "contraction":
            return Signal("hold", 0.4, {**metadata, "reason": "Extended contraction - awaiting breakout"})
        
        # Expansion phase - trend following
        if phase == "expansion":
            if price_change > 0.01:
                return Signal("buy", 0.65, {**metadata, "reason": "Expansion with uptrend"})
            elif price_change < -0.01:
                return Signal("sell", 0.65, {**metadata, "reason": "Expansion with downtrend"})
        
        # Expansion exhaustion
        if phase == "expansion" and phase_momentum < 0.9 and abs(price_change) > 0.03:
            if price_change > 0:
                return Signal("sell", 0.6, {**metadata, "reason": "Expansion exhaustion"})
            else:
                return Signal("buy", 0.6, {**metadata, "reason": "Expansion exhaustion"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 50
    base = 40000
    
    # Generate data with contraction then expansion
    highs = []
    lows = []
    closes = []
    
    price = base
    for i in range(35):
        # Contraction phase - small ranges
        daily_range = 100 + np.random.randn() * 20
        high = price + daily_range / 2
        low = price - daily_range / 2
        close = price + np.random.randn() * 30
        highs.append(high)
        lows.append(low)
        closes.append(close)
        price = close + np.random.randn() * 20
    
    for i in range(15):
        # Expansion phase - large ranges
        daily_range = 400 + i * 20 + np.random.randn() * 50
        high = price + daily_range / 2
        low = price - daily_range / 2
        close = price + 50 + np.random.randn() * 60
        highs.append(high)
        lows.append(low)
        closes.append(close)
        price = close
    
    strategy = VolatilityCycleStrategy()
    signal = strategy.analyze(highs, lows, closes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
