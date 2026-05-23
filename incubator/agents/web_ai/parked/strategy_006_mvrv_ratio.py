"""
Strategy 006: MVRV Ratio Reversion
On-chain metric using Market Value to Realized Value ratio
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class MVRVStrategy:
    """
    Uses MVRV ratio to identify market tops and bottoms.
    MVRV > 3.5 = overvalued (sell zone)
    MVRV < 1.0 = undervalued (buy zone)
    """
    
    def __init__(
        self,
        overvalued_threshold: float = 3.5,
        undervalued_threshold: float = 1.0,
        neutral_high: float = 2.5,
        neutral_low: float = 1.5,
        lookback: int = 30
    ):
        self.overvalued = overvalued_threshold
        self.undervalued = undervalued_threshold
        self.neutral_high = neutral_high
        self.neutral_low = neutral_low
        self.lookback = lookback
    
    def analyze(
        self,
        mvrv_ratio: List[float],
        prices: List[float]
    ) -> Signal:
        if len(mvrv_ratio) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        current_mvrv = mvrv_ratio[-1]
        previous_mvrv = mvrv_ratio[-2]
        
        # Trend
        mvrv_ma = np.mean(mvrv_ratio[-self.lookback:])
        trend = current_mvrv - mvrv_ma
        
        # Rate of change
        roc = (current_mvrv - previous_mvrv) / previous_mvrv
        
        metadata = {
            "mvrv": current_mvrv,
            "mvrv_ma": mvrv_ma,
            "trend": trend,
            "roc": roc,
            "zone": "neutral"
        }
        
        # Determine zone
        if current_mvrv > self.overvalued:
            metadata["zone"] = "overvalued"
        elif current_mvrv < self.undervalued:
            metadata["zone"] = "undervalued"
        elif current_mvrv > self.neutral_high:
            metadata["zone"] = "high"
        elif current_mvrv < self.neutral_low:
            metadata["zone"] = "low"
        
        # Strong buy signal - deeply undervalued
        if current_mvrv < self.undervalued and trend > 0:
            confidence = min(0.95, 0.6 + (self.undervalued - current_mvrv) * 0.2)
            return Signal("buy", confidence, {**metadata, "reason": "Deep value zone"})
        
        # Strong sell signal - extremely overvalued
        if current_mvrv > self.overvalued and trend < 0:
            confidence = min(0.95, 0.6 + (current_mvrv - self.overvalued) * 0.15)
            return Signal("sell", confidence, {**metadata, "reason": "Extreme overvaluation"})
        
        # Moderate buy - entering value zone
        if current_mvrv < self.neutral_low and roc < 0:
            return Signal("buy", 0.55, {**metadata, "reason": "Approaching value"})
        
        # Moderate sell - entering overvalue zone
        if current_mvrv > self.neutral_high and roc > 0:
            return Signal("sell", 0.55, {**metadata, "reason": "Approaching overvalue"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n_days = 60
    # Simulate MVRV in undervalued zone recovering
    mvrv = [0.8 + i * 0.02 + np.random.randn() * 0.05 for i in range(n_days)]
    prices = [35000 + i * 100 + np.random.randn() * 200 for i in range(n_days)]
    
    strategy = MVRVStrategy()
    signal = strategy.analyze(mvrv, prices)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
