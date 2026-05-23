"""
Strategy 052: Gamma Exposure Wall
Options gamma exposure analysis
"""
from dataclasses import dataclass
from typing import List, Dict
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class GammaExposureStrategy:
    """
    Analyzes gamma exposure to predict price magnet levels.
    High positive gamma = price stability near strike
    High negative gamma = volatility near strike
    """
    
    def __init__(
        self,
        gamma_threshold: float = 1000000,
        spot_proximity: float = 0.02,
        lookback: int = 5
    ):
        self.gamma_threshold = gamma_threshold
        self.spot_proximity = spot_proximity
        self.lookback = lookback
    
    def analyze(
        self,
        current_price: float,
        gamma_by_strike: Dict[float, float],  # {strike: gamma, ...}
        net_gamma: float,
        prices: List[float]
    ) -> Signal:
        if not gamma_by_strike:
            return Signal("hold", 0.0, {"error": "No gamma data"})
        
        # Find strikes near current price
        nearby_strikes = {k: v for k, v in gamma_by_strike.items() 
                         if abs(k - current_price) / current_price < self.spot_proximity}
        
        if not nearby_strikes:
            return Signal("hold", 0.1, {"error": "No strikes near spot"})
        
        # Largest gamma walls
        max_gamma_strike = max(nearby_strikes.items(), key=lambda x: abs(x[1]))
        
        # Total gamma sign
        gamma_sign = "positive" if net_gamma > 0 else "negative"
        
        # Distance to largest wall
        distance_to_wall = (max_gamma_strike[0] - current_price) / current_price
        
        # Gamma flip point (where net gamma = 0)
        # Simplified: assume it's between largest positive and negative
        positive_gamma = sum(v for v in gamma_by_strike.values() if v > 0)
        negative_gamma = sum(v for v in gamma_by_strike.values() if v < 0)
        
        metadata = {
            "net_gamma": net_gamma,
            "gamma_sign": gamma_sign,
            "max_gamma_strike": max_gamma_strike[0],
            "max_gamma_value": max_gamma_strike[1],
            "distance_to_wall": distance_to_wall,
            "positive_gamma": positive_gamma,
            "negative_gamma": negative_gamma
        }
        
        # Large positive gamma wall above price = resistance
        if max_gamma_strike[1] > self.gamma_threshold and distance_to_wall > 0:
            confidence = min(0.75, 0.5 + max_gamma_strike[1] / self.gamma_threshold * 0.2)
            return Signal("sell", confidence, {**metadata, "reason": "Gamma wall above"})
        
        # Large positive gamma wall below price = support
        if max_gamma_strike[1] > self.gamma_threshold and distance_to_wall < 0:
            confidence = min(0.75, 0.5 + max_gamma_strike[1] / self.gamma_threshold * 0.2)
            return Signal("buy", confidence, {**metadata, "reason": "Gamma wall below"})
        
        # Negative gamma environment = expect volatility
        if net_gamma < -self.gamma_threshold:
            recent_vol = np.std(prices[-self.lookback:]) / np.mean(prices[-self.lookback:])
            if recent_vol < 0.01:
                return Signal("buy", 0.6, {**metadata, "reason": "Negative gamma, vol expansion expected"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    current_price = 40000
    
    # Gamma distribution around strikes
    strikes = [38000, 39000, 40000, 41000, 42000]
    gamma_by_strike = {
        38000: 500000,
        39000: 1200000,  # Support wall
        40000: 800000,
        41000: 2000000,  # Resistance wall
        42000: 600000
    }
    
    net_gamma = sum(gamma_by_strike.values())
    prices = [40000 + np.random.randn() * 100 for _ in range(10)]
    
    strategy = GammaExposureStrategy()
    signal = strategy.analyze(current_price, gamma_by_strike, net_gamma, prices)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
