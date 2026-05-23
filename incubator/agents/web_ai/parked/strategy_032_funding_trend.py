"""
Strategy 032: Funding Trend Analysis
Funding rate momentum strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class FundingTrendStrategy:
    """
    Analyzes funding rate trends for sentiment shifts.
    Rising funding = increasing long interest (potential reversal)
    Falling funding = increasing short interest (potential reversal)
    """
    
    def __init__(
        self,
        trend_period: int = 7,
        acceleration_threshold: float = 0.002,
        neutral_zone: float = 0.001
    ):
        self.trend_period = trend_period
        self.accel_threshold = acceleration_threshold
        self.neutral_zone = neutral_zone
    
    def analyze(
        self,
        funding_rates: List[float],
        prices: List[float],
        open_interest: List[float]
    ) -> Signal:
        if len(funding_rates) < self.trend_period + 5:
            return Signal("hold", 0.0, {"error": "Insufficient funding data"})
        
        current_funding = funding_rates[-1]
        
        # Trend calculation
        short_ma = np.mean(funding_rates[-3:])
        medium_ma = np.mean(funding_rates[-7:])
        long_ma = np.mean(funding_rates[-self.trend_period:])
        
        # Acceleration
        recent_change = funding_rates[-1] - funding_rates[-3]
        previous_change = funding_rates[-4] - funding_rates[-6] if len(funding_rates) >= 7 else 0
        acceleration = recent_change - previous_change
        
        # Price vs funding divergence
        price_change = (prices[-1] - prices[-7]) / prices[-7] if len(prices) >= 7 else 0
        funding_change = current_funding - long_ma
        
        divergence = price_change - funding_change * 10  # Scale funding
        
        # OI trend
        oi_change = (open_interest[-1] - open_interest[-7]) / open_interest[-7] if len(open_interest) >= 7 else 0
        
        metadata = {
            "current_funding": current_funding,
            "short_ma": short_ma,
            "long_ma": long_ma,
            "acceleration": acceleration,
            "price_change": price_change,
            "funding_change": funding_change,
            "divergence": divergence,
            "oi_change": oi_change
        }
        
        # Funding accelerating positive with price stalling
        if acceleration > self.accel_threshold and price_change < 0.01 and current_funding > 0:
            confidence = min(0.8, 0.5 + acceleration * 100)
            return Signal("sell", confidence, {**metadata, "reason": "Funding rising, price stalling"})
        
        # Funding accelerating negative with price stalling
        if acceleration < -self.accel_threshold and price_change > -0.01 and current_funding < 0:
            confidence = min(0.8, 0.5 + abs(acceleration) * 100)
            return Signal("buy", confidence, {**metadata, "reason": "Funding falling, price holding"})
        
        # Extreme funding with OI increase = crowded trade
        if abs(current_funding) > 0.005 and oi_change > 0.1:
            if current_funding > 0:
                return Signal("sell", 0.7, {**metadata, "reason": "Crowded longs"})
            else:
                return Signal("buy", 0.7, {**metadata, "reason": "Crowded shorts"})
        
        # Funding returning to neutral
        if abs(current_funding) < self.neutral_zone and abs(long_ma) > 0.003:
            if long_ma > 0:
                return Signal("buy", 0.6, {**metadata, "reason": "Funding normalizing from positive"})
            else:
                return Signal("sell", 0.6, {**metadata, "reason": "Funding normalizing from negative"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 20
    # Funding trending more positive
    funding = [0.001 + i * 0.0008 + np.random.randn() * 0.0003 for i in range(n)]
    # Price stalling
    prices = [40000 + i * 20 + np.random.randn() * 100 for i in range(n)]
    # OI increasing
    oi = [1000000 + i * 50000 for i in range(n)]
    
    strategy = FundingTrendStrategy()
    signal = strategy.analyze(funding, prices, oi)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
