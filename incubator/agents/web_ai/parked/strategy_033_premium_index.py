"""
Strategy 033: Premium Index Divergence
Perpetual vs spot premium strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class PremiumIndexStrategy:
    """
    Trades divergences between perpetual and spot prices.
    High premium = bullish sentiment (potential short)
    Negative premium = bearish sentiment (potential long)
    """
    
    def __init__(
        self,
        premium_threshold: float = 0.005,
        extreme_premium: float = 0.015,
        ma_period: int = 20
    ):
        self.premium_threshold = premium_threshold
        self.extreme_premium = extreme_premium
        self.ma_period = ma_period
    
    def analyze(
        self,
        perp_prices: List[float],
        spot_prices: List[float],
        funding_rates: List[float]
    ) -> Signal:
        if len(perp_prices) < self.ma_period or len(spot_prices) < self.ma_period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate premium
        premiums = [(p - s) / s for p, s in zip(perp_prices, spot_prices)]
        
        current_premium = premiums[-1]
        premium_ma = np.mean(premiums[-self.ma_period:])
        premium_std = np.std(premiums[-self.ma_period:])
        
        # Z-score
        premium_zscore = (current_premium - premium_ma) / (premium_std + 1e-8)
        
        # Trend
        premium_trend = current_premium - premiums[-5] if len(premiums) >= 5 else 0
        
        # Funding context
        current_funding = funding_rates[-1] if funding_rates else 0
        
        metadata = {
            "current_premium": current_premium,
            "premium_pct": current_premium * 100,
            "premium_ma": premium_ma,
            "premium_zscore": premium_zscore,
            "premium_trend": premium_trend,
            "funding": current_funding
        }
        
        # Extreme premium - contrarian sell
        if current_premium > self.extreme_premium and premium_trend < 0:
            confidence = min(0.8, 0.5 + (current_premium - self.extreme_premium) * 30)
            return Signal("sell", confidence, {**metadata, "reason": "Extreme premium reverting"})
        
        # Extreme discount - contrarian buy
        if current_premium < -self.extreme_premium and premium_trend > 0:
            confidence = min(0.8, 0.5 + (abs(current_premium) - self.extreme_premium) * 30)
            return Signal("buy", confidence, {**metadata, "reason": "Extreme discount reverting"})
        
        # Premium expansion with funding support
        if current_premium > self.premium_threshold and current_funding > 0.001:
            if premium_trend > 0:
                return Signal("buy", 0.6, {**metadata, "reason": "Premium expanding with funding"})
        
        # Premium compression
        if current_premium < self.premium_threshold * 0.5 and premium_trend < 0:
            if current_funding > 0.005:  # High funding but premium compressing
                return Signal("sell", 0.65, {**metadata, "reason": "Premium compression with high funding"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 25
    base = 40000
    
    # Spot price
    spot = [base + i * 30 + np.random.randn() * 50 for i in range(n)]
    
    # Perp at premium, now compressing
    perp = [s * (1.012 - i * 0.0003) for i, s in enumerate(spot)]
    
    # High funding
    funding = [0.008 + np.random.randn() * 0.002 for _ in range(n)]
    
    strategy = PremiumIndexStrategy()
    signal = strategy.analyze(perp, spot, funding)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
