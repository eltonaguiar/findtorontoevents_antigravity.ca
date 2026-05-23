"""
Strategy 057: Wyckoff Accumulation
Wyckoff accumulation pattern
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class WyckoffAccumulationStrategy:
    """
    Identifies Wyckoff accumulation phases.
    Trades the markup phase after accumulation.
    """
    
    def __init__(
        self,
        phase_lookback: int = 30,
        spring_threshold: float = 0.03,
        volume_confirm: float = 1.5
    ):
        self.phase_lookback = phase_lookback
        self.spring_threshold = spring_threshold
        self.volume_confirm = volume_confirm
    
    def analyze(
        self,
        prices: List[float],
        volumes: List[float],
        highs: List[float],
        lows: List[float]
    ) -> Signal:
        if len(prices) < self.phase_lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Trading range analysis
        range_high = max(highs[-self.phase_lookback:])
        range_low = min(lows[-self.phase_lookback:])
        range_size = (range_high - range_low) / range_low
        
        # Current position in range
        current = prices[-1]
        position = (current - range_low) / (range_high - range_low)
        
        # Volume analysis
        vol_ma = np.mean(volumes[-self.phase_lookback:])
        recent_vol = np.mean(volumes[-5:])
        vol_ratio = recent_vol / vol_ma
        
        # Spring detection (false breakdown below support)
        recent_lows = lows[-5:]
        spring_low = min(recent_lows)
        prior_lows = lows[-self.phase_lookback:-5]
        prior_support = min(prior_lows) if prior_lows else spring_low
        
        spring = spring_low < prior_support * (1 - self.spring_threshold) and current > prior_support
        
        # Test of support with low volume (no supply)
        near_support = current < range_low + range_size * range_low * 0.2
        low_vol_near_support = near_support and vol_ratio < 0.8
        
        # Breaking out of range
        breakout = current > range_high * 0.995 and vol_ratio > self.volume_confirm
        
        # PS (Preliminary Support) and SC (Selling Climax) detection
        # Simplified: large volume capitulation followed by lower volume
        if len(volumes) >= 10:
            vol_spike_ago = max(volumes[-10:-5]) > vol_ma * 2
            recent_quiet = recent_vol < vol_ma * 0.9
            ps_sc_pattern = vol_spike_ago and recent_quiet
        else:
            ps_sc_pattern = False
        
        metadata = {
            "range_high": range_high,
            "range_low": range_low,
            "position_in_range": position,
            "spring": spring,
            "breakout": breakout,
            "vol_ratio": vol_ratio,
            "ps_sc_pattern": ps_sc_pattern
        }
        
        # Spring pattern - strong buy
        if spring and current > prior_support:
            confidence = min(0.85, 0.6 + (prior_support - spring_low) / prior_support * 10)
            return Signal("buy", confidence, {**metadata, "reason": "Wyckoff spring"})
        
        # Breakout from accumulation
        if breakout and position > 0.9:
            return Signal("buy", 0.8, {**metadata, "reason": "Wyckoff breakout"})
        
        # No supply near support
        if low_vol_near_support and ps_sc_pattern:
            return Signal("buy", 0.7, {**metadata, "reason": "Wyckoff no supply"})
        
        # Early accumulation phase
        if position < 0.3 and vol_ratio > 1.2:
            return Signal("buy", 0.55, {**metadata, "reason": "Potential accumulation zone"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 35
    base = 40000
    
    # Accumulation range
    prices = []
    highs = []
    lows = []
    volumes = []
    
    for i in range(25):
        p = base + np.random.randn() * 300
        prices.append(p)
        highs.append(p + 150)
        lows.append(p - 150)
        volumes.append(1000 + np.random.randn() * 200)
    
    # Spring (false breakdown)
    lows[-3] = base - 1500
    prices[-3] = base - 1200
    volumes[-3] = 2500
    
    # Recovery
    for i in range(10):
        prices.append(prices[-1] + 100 + i * 30)
        highs.append(prices[-1] + 200)
        lows.append(prices[-1] - 100)
        volumes.append(1800 + i * 50)
    
    strategy = WyckoffAccumulationStrategy()
    signal = strategy.analyze(prices, volumes, highs, lows)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
