"""
Strategy 073: Stochastic Oscillator
Stochastic momentum strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class StochasticStrategy:
    """Stochastic oscillator with overbought/oversold signals."""
    
    def __init__(self, k_period: int = 14, d_period: int = 3, overbought: float = 80, oversold: float = 20):
        self.k_period = k_period
        self.d_period = d_period
        self.overbought = overbought
        self.oversold = oversold
    
    def analyze(self, highs: List[float], lows: List[float], closes: List[float]) -> Signal:
        if len(closes) < self.k_period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate %K
        lowest_low = min(lows[-self.k_period:])
        highest_high = max(highs[-self.k_period:])
        range_hl = highest_high - lowest_low
        
        if range_hl == 0:
            return Signal("hold", 0.0, {"error": "No range"})
        
        k_current = 100 * (closes[-1] - lowest_low) / range_hl
        
        # Calculate %D (simplified)
        k_values = []
        for i in range(self.d_period):
            ll = min(lows[-(self.k_period+i):-i if i > 0 else len(lows)])
            hh = max(highs[-(self.k_period+i):-i if i > 0 else len(highs)])
            k_values.append(100 * (closes[-(1+i)] - ll) / (hh - ll + 1e-8))
        d_current = np.mean(k_values)
        
        # Cross signals
        k_prev = k_values[1] if len(k_values) > 1 else k_current
        cross_up = k_prev < d_current and k_current > d_current
        cross_down = k_prev > d_current and k_current < d_current
        
        metadata = {"k": k_current, "d": d_current}
        
        if k_current < self.oversold and cross_up:
            return Signal("buy", 0.75, metadata)
        if k_current > self.overbought and cross_down:
            return Signal("sell", 0.75, metadata)
        if k_current < self.oversold:
            return Signal("buy", 0.6, metadata)
        if k_current > self.overbought:
            return Signal("sell", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    highs = [40200]*20
    lows = [39800]*20
    closes = [40000 - i*50 for i in range(20)]
    s = StochasticStrategy()
    sig = s.analyze(highs, lows, closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
