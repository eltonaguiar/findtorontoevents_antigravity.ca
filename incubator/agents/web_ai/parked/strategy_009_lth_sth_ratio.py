"""
Strategy 009: LTH/STH Ratio Cycle
On-chain metric comparing Long-Term to Short-Term Holders
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class LTHSTHStrategy:
    """
    Analyzes Long-Term Holder (LTH) vs Short-Term Holder (STH) supply ratio.
    High LTH ratio = strong hands holding (bullish)
    Declining LTH ratio = distribution to weak hands (bearish)
    """
    
    def __init__(
        self,
        lth_dominance_threshold: float = 0.7,
        sth_dominance_threshold: float = 0.5,
        trend_window: int = 14,
        min_history: int = 30
    ):
        self.lth_threshold = lth_dominance_threshold
        self.sth_threshold = sth_dominance_threshold
        self.trend_window = trend_window
        self.min_history = min_history
    
    def analyze(
        self,
        lth_supply: List[float],
        sth_supply: List[float],
        prices: List[float]
    ) -> Signal:
        if len(lth_supply) < self.min_history:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate ratio
        total_supply = [l + s for l, s in zip(lth_supply, sth_supply)]
        lth_ratio = [l / (t + 1e-8) for l, t in zip(lth_supply, total_supply)]
        
        current_ratio = lth_ratio[-1]
        prev_ratio = lth_ratio[-self.trend_window]
        
        # Trends
        ratio_change = current_ratio - prev_ratio
        short_ma = np.mean(lth_ratio[-7:])
        long_ma = np.mean(lth_ratio[-self.trend_window:])
        
        metadata = {
            "lth_ratio": current_ratio,
            "sth_ratio": 1 - current_ratio,
            "ratio_change": ratio_change,
            "short_ma": short_ma,
            "long_ma": long_ma
        }
        
        # LTH accumulation phase - ratio increasing
        if ratio_change > 0.05 and current_ratio > self.lth_threshold:
            confidence = min(0.85, 0.5 + ratio_change * 3)
            return Signal("buy", confidence, {**metadata, "reason": "Strong hands accumulating"})
        
        # LTH distribution - ratio declining from high levels
        if ratio_change < -0.03 and current_ratio > 0.6:
            confidence = min(0.8, 0.5 + abs(ratio_change) * 5)
            return Signal("sell", confidence, {**metadata, "reason": "Long-term holders distributing"})
        
        # STH dominance - potential bottom (weak hands exhausted)
        if current_ratio < self.sth_threshold and ratio_change > 0:
            return Signal("buy", 0.7, {**metadata, "reason": "Short-term holders dominant, reversal likely"})
        
        # Golden cross of LTH ratio
        if short_ma > long_ma * 1.02 and ratio_change > 0.02:
            return Signal("buy", 0.6, {**metadata, "reason": "LTH ratio trend turning up"})
        
        return Signal("hold", 0.25, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n_days = 45
    # LTH increasing their share
    lth = [12e6 + i * 50000 + np.random.randn() * 100000 for i in range(n_days)]
    sth = [6e6 - i * 20000 + np.random.randn() * 50000 for i in range(n_days)]
    prices = [40000 + i * 120 + np.random.randn() * 300 for i in range(n_days)]
    
    strategy = LTHSTHStrategy()
    signal = strategy.analyze(lth, sth, prices)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
