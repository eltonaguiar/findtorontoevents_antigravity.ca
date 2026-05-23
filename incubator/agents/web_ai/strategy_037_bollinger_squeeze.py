"""
Strategy 037: Bollinger Squeeze Breakout
Volatility compression strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class BollingerSqueezeStrategy:
    """
    Trades breakouts from Bollinger Band squeezes.
    Low volatility periods often precede high volatility moves.
    """
    
    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        squeeze_threshold: float = 0.1,
        breakout_threshold: float = 0.02
    ):
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.squeeze_threshold = squeeze_threshold
        self.breakout_threshold = breakout_threshold
    
    def analyze(
        self,
        prices: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(prices) < self.bb_period + 10:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate Bollinger Bands
        recent_prices = prices[-self.bb_period:]
        sma = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        upper_band = sma + self.bb_std * std
        lower_band = sma - self.bb_std * std
        bandwidth = (upper_band - lower_band) / sma
        
        # Historical bandwidth for squeeze detection
        historical_bandwidth = []
        for i in range(self.bb_period + 10, len(prices)):
            window = prices[i-self.bb_period:i]
            w_sma = np.mean(window)
            w_std = np.std(window)
            w_bandwidth = (2 * self.bb_std * w_std) / w_sma
            historical_bandwidth.append(w_bandwidth)
        
        # Squeeze detection
        bandwidth_percentile = sum(1 for b in historical_bandwidth if b < bandwidth) / len(historical_bandwidth) if historical_bandwidth else 0.5
        in_squeeze = bandwidth_percentile < self.squeeze_threshold
        
        # Current position
        current_price = prices[-1]
        position_in_band = (current_price - lower_band) / (upper_band - lower_band) if upper_band != lower_band else 0.5
        
        # Breakout detection
        breakout_up = current_price > upper_band * (1 + self.breakout_threshold * 0.1)
        breakout_down = current_price < lower_band * (1 - self.breakout_threshold * 0.1)
        
        # Volume
        vol_ma = np.mean(volumes[-5:])
        vol_surge = volumes[-1] / vol_ma if vol_ma > 0 else 1
        
        metadata = {
            "sma": sma,
            "upper_band": upper_band,
            "lower_band": lower_band,
            "bandwidth": bandwidth,
            "bandwidth_percentile": bandwidth_percentile,
            "in_squeeze": in_squeeze,
            "position_in_band": position_in_band,
            "breakout_up": breakout_up,
            "breakout_down": breakout_down,
            "vol_surge": vol_surge
        }
        
        # Squeeze breakout up
        if in_squeeze and breakout_up and vol_surge > 1.3:
            confidence = min(0.85, 0.65 + (1 - bandwidth_percentile) * 0.2)
            return Signal("buy", confidence, {**metadata, "reason": "Bollinger squeeze breakout up"})
        
        # Squeeze breakout down
        if in_squeeze and breakout_down and vol_surge > 1.3:
            confidence = min(0.85, 0.65 + (1 - bandwidth_percentile) * 0.2)
            return Signal("sell", confidence, {**metadata, "reason": "Bollinger squeeze breakout down"})
        
        # Regular breakout
        if breakout_up and not in_squeeze:
            return Signal("buy", 0.6, {**metadata, "reason": "Upper band breakout"})
        
        if breakout_down and not in_squeeze:
            return Signal("sell", 0.6, {**metadata, "reason": "Lower band breakdown"})
        
        # Squeeze anticipation
        if in_squeeze and bandwidth_percentile < 0.05:
            return Signal("hold", 0.4, {**metadata, "reason": "Extreme squeeze - awaiting breakout"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 40
    base = 40000
    
    # Low volatility squeeze period
    prices = [base + np.random.randn() * 30 for _ in range(30)]
    # Breakout
    for i in range(10):
        prices.append(prices[-1] + 100 + i * 20 + np.random.randn() * 20)
    
    volumes = [800 + np.random.randn() * 100 for _ in range(30)]
    volumes.extend([1500 + np.random.randn() * 200 for _ in range(10)])
    
    strategy = BollingerSqueezeStrategy()
    signal = strategy.analyze(prices, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
