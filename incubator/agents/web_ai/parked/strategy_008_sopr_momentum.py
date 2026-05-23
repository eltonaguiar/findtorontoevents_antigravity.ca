"""
Strategy 008: SOPR Momentum
On-chain metric using Spent Output Profit Ratio
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class SOPRStrategy:
    """
    SOPR > 1 = coins moved at profit (distribution possible)
    SOPR < 1 = coins moved at loss (capitulation/accumulation)
    SOPR resetting to 1 and bouncing = bullish continuation
    """
    
    def __init__(
        self,
        profit_threshold: float = 1.05,
        loss_threshold: float = 0.95,
        reset_band: float = 0.02,
        ma_period: int = 7
    ):
        self.profit_threshold = profit_threshold
        self.loss_threshold = loss_threshold
        self.reset_band = reset_band
        self.ma_period = ma_period
    
    def analyze(
        self,
        sopr: List[float],
        prices: List[float]
    ) -> Signal:
        if len(sopr) < self.ma_period + 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        current_sopr = sopr[-1]
        sopr_ma = np.mean(sopr[-self.ma_period:])
        
        # Check for reset pattern (crossing below 1 and back up)
        recent_sopr = sopr[-5:]
        crossed_below = any(s < 1 - self.reset_band for s in sopr[-10:-5])
        crossed_above = current_sopr > 1 + self.reset_band
        reset_pattern = crossed_below and crossed_above
        
        # Trend
        trend = current_sopr - sopr_ma
        
        metadata = {
            "sopr": current_sopr,
            "sopr_ma": sopr_ma,
            "trend": trend,
            "reset_pattern": reset_pattern,
            "in_profit": current_sopr > 1
        }
        
        # Bullish reset - SOPR dipped below 1 and recovered
        if reset_pattern and trend > 0:
            return Signal("buy", 0.75, {**metadata, "reason": "SOPR reset complete"})
        
        # Capitulation - selling at loss
        if current_sopr < self.loss_threshold and trend < 0:
            confidence = min(0.8, 0.5 + (self.loss_threshold - current_sopr) * 2)
            return Signal("buy", confidence, {**metadata, "reason": "Loss selling"})
        
        # Distribution - heavy profit taking
        if current_sopr > self.profit_threshold and trend < -0.02:
            confidence = min(0.75, 0.5 + (current_sopr - self.profit_threshold) * 3)
            return Signal("sell", confidence, {**metadata, "reason": "Profit taking"})
        
        # Sustained profit taking
        if sopr_ma > 1.02 and current_sopr < sopr_ma * 0.98:
            return Signal("sell", 0.6, {**metadata, "reason": "SOPR declining from profit zone"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n_days = 20
    # SOPR recovering from below 1
    sopr = [0.98, 0.97, 0.96, 0.98, 0.99, 1.0, 1.01, 1.02, 1.01, 1.03,
            1.02, 1.01, 1.0, 0.99, 1.0, 1.01, 1.02, 1.03, 1.04, 1.05]
    prices = [40000 + i * 100 for i in range(n_days)]
    
    strategy = SOPRStrategy()
    signal = strategy.analyze(sopr, prices)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
