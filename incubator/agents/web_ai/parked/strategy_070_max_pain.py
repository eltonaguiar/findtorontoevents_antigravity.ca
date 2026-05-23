"""
Strategy 070: Max Pain Theory
Options max pain strategy
"""
from dataclasses import dataclass
from typing import List, Dict
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class MaxPainStrategy:
    """
    Uses max pain theory - price tends to move toward max pain strike.
    Max pain = strike where option writers lose least.
    """
    
    def __init__(
        self,
        proximity_threshold: float = 0.03,
        lookback: int = 5
    ):
        self.proximity = proximity_threshold
        self.lookback = lookback
    
    def _calculate_max_pain(self, strikes: List[float], 
                           call_oi: Dict[float, float],
                           put_oi: Dict[float, float]) -> float:
        """Calculate max pain strike"""
        min_pain = float('inf')
        max_pain_strike = strikes[0]
        
        for strike in strikes:
            # Pain at this strike
            pain = 0
            for s in strikes:
                if s in call_oi:
                    pain += call_oi[s] * max(0, strike - s)
                if s in put_oi:
                    pain += put_oi[s] * max(0, s - strike)
            
            if pain < min_pain:
                min_pain = pain
                max_pain_strike = strike
        
        return max_pain_strike
    
    def analyze(
        self,
        current_price: float,
        strikes: List[float],
        call_oi: Dict[float, float],
        put_oi: Dict[float, float],
        prices: List[float]
    ) -> Signal:
        if not strikes or not call_oi or not put_oi:
            return Signal("hold", 0.0, {"error": "Insufficient options data"})
        
        max_pain = self._calculate_max_pain(strikes, call_oi, put_oi)
        
        # Distance to max pain
        distance = (max_pain - current_price) / current_price
        
        # Price trend
        price_trend = (prices[-1] - prices[-self.lookback]) / prices[-self.lookback] if len(prices) >= self.lookback else 0
        
        metadata = {
            "max_pain": max_pain,
            "current_price": current_price,
            "distance": distance,
            "price_trend": price_trend
        }
        
        # Price below max pain - expect upward pressure
        if distance > self.proximity and price_trend >= 0:
            confidence = min(0.7, 0.5 + distance * 5)
            return Signal("buy", confidence, {**metadata, "reason": "Below max pain"})
        
        # Price above max pain - expect downward pressure
        if distance < -self.proximity and price_trend <= 0:
            confidence = min(0.7, 0.5 + abs(distance) * 5)
            return Signal("sell", confidence, {**metadata, "reason": "Above max pain"})
        
        return Signal("hold", 0.25, metadata)


if __name__ == "__main__":
    current_price = 40000
    strikes = [38000, 39000, 40000, 41000, 42000]
    
    call_oi = {38000: 100, 39000: 200, 40000: 500, 41000: 300, 42000: 150}
    put_oi = {38000: 200, 39000: 300, 40000: 400, 41000: 200, 42000: 100}
    
    prices = [39500, 39600, 39700, 39800, 39900]
    
    strategy = MaxPainStrategy()
    signal = strategy.analyze(current_price, strikes, call_oi, put_oi, prices)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
