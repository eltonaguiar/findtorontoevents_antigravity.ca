"""
Strategy 058: Open Interest Delta
Open interest change analysis
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class OpenInterestDeltaStrategy:
    """
    Analyzes open interest changes for directional signals.
    OI + Price up = new longs (trend continuation)
    OI + Price down = new shorts (trend continuation)
    OI - Price up = short squeeze
    OI - Price down = long capitulation
    """
    
    def __init__(
        self,
        oi_change_threshold: float = 0.05,
        price_change_threshold: float = 0.02,
        lookback: int = 5
    ):
        self.oi_threshold = oi_change_threshold
        self.price_threshold = price_change_threshold
        self.lookback = lookback
    
    def analyze(
        self,
        open_interest: List[float],
        prices: List[float],
        funding_rates: List[float]
    ) -> Signal:
        if len(open_interest) < self.lookback + 1:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate changes
        oi_change = (open_interest[-1] - open_interest[-self.lookback]) / open_interest[-self.lookback]
        price_change = (prices[-1] - prices[-self.lookback]) / prices[-self.lookback]
        
        # CVD-like calculation
        oi_delta = open_interest[-1] - open_interest[-2]
        price_delta = prices[-1] - prices[-2]
        
        # Classification
        if oi_change > 0 and price_change > 0:
            regime = "long_buildup"
        elif oi_change > 0 and price_change < 0:
            regime = "short_buildup"
        elif oi_change < 0 and price_change > 0:
            regime = "short_squeeze"
        elif oi_change < 0 and price_change < 0:
            regime = "long_liquidation"
        else:
            regime = "neutral"
        
        # Funding context
        avg_funding = np.mean(funding_rates[-3:]) if funding_rates else 0
        
        metadata = {
            "oi_change": oi_change,
            "price_change": price_change,
            "regime": regime,
            "avg_funding": avg_funding
        }
        
        # Long buildup with positive funding = strong trend
        if regime == "long_buildup" and oi_change > self.oi_threshold:
            if avg_funding > 0:
                confidence = min(0.8, 0.55 + oi_change)
                return Signal("buy", confidence, {**metadata, "reason": "Long buildup"})
        
        # Short buildup with negative funding = strong downtrend
        if regime == "short_buildup" and oi_change > self.oi_threshold:
            if avg_funding < 0:
                confidence = min(0.8, 0.55 + oi_change)
                return Signal("sell", confidence, {**metadata, "reason": "Short buildup"})
        
        # Short squeeze
        if regime == "short_squeeze" and abs(oi_change) > self.oi_threshold * 0.5:
            confidence = min(0.75, 0.5 + abs(oi_change) * 2)
            return Signal("buy", confidence, {**metadata, "reason": "Short squeeze"})
        
        # Long liquidation
        if regime == "long_liquidation" and abs(oi_change) > self.oi_threshold * 0.5:
            confidence = min(0.75, 0.5 + abs(oi_change) * 2)
            return Signal("sell", confidence, {**metadata, "reason": "Long liquidation"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 10
    oi = [1000000 + i * 50000 for i in range(n)]
    prices = [40000 + i * 200 for i in range(n)]
    funding = [0.01] * n
    
    strategy = OpenInterestDeltaStrategy()
    signal = strategy.analyze(oi, prices, funding)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
