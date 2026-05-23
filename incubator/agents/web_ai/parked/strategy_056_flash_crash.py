"""
Strategy 056: Flash Crash Reversal
Flash crash detection and reversal
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class FlashCrashReversalStrategy:
    """
    Detects flash crashes and trades the reversal.
    Flash crashes often recover quickly.
    """
    
    def __init__(
        self,
        crash_threshold: float = 0.1,
        recovery_threshold: float = 0.02,
        time_window: int = 6,
        volume_multiplier: float = 3.0
    ):
        self.crash_threshold = crash_threshold
        self.recovery_threshold = recovery_threshold
        self.time_window = time_window
        self.volume_mult = volume_multiplier
    
    def analyze(
        self,
        prices: List[float],
        volumes: List[float],
        lows: List[float]
    ) -> Signal:
        if len(prices) < self.time_window + 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Detect flash crash
        recent_low = min(lows[-self.time_window:])
        recent_high = max(prices[-self.time_window:])
        
        crash_magnitude = (recent_high - recent_low) / recent_high
        
        # Time since crash low
        bars_since_low = len(lows) - lows.index(recent_low) - 1 if recent_low in lows[-self.time_window:] else self.time_window
        
        # Recovery detection
        current_price = prices[-1]
        recovery_from_low = (current_price - recent_low) / recent_low
        
        # Volume analysis
        avg_volume = np.mean(volumes[-self.time_window*2:-self.time_window])
        crash_volume = np.mean(volumes[-self.time_window:])
        volume_surge = crash_volume / avg_volume if avg_volume > 0 else 1
        
        # Velocity of drop
        if bars_since_low < self.time_window:
            velocity = crash_magnitude / (bars_since_low + 1)
        else:
            velocity = 0
        
        metadata = {
            "crash_magnitude": crash_magnitude,
            "bars_since_low": bars_since_low,
            "recovery_from_low": recovery_from_low,
            "volume_surge": volume_surge,
            "velocity": velocity,
            "recent_low": recent_low
        }
        
        # Flash crash detected with recovery starting
        if crash_magnitude > self.crash_threshold and volume_surge > self.volume_mult:
            if recovery_from_low > self.recovery_threshold and bars_since_low <= 3:
                confidence = min(0.85, 0.6 + recovery_from_low * 5)
                return Signal("buy", confidence, {**metadata, "reason": "Flash crash recovery"})
            elif bars_since_low <= 2:
                return Signal("hold", 0.4, {**metadata, "reason": "Flash crash ongoing"})
        
        # Moderate crash
        if crash_magnitude > self.crash_threshold * 0.6 and recovery_from_low > 0.01:
            return Signal("buy", 0.6, {**metadata, "reason": "Moderate crash recovery"})
        
        # False breakdown recovery
        if crash_magnitude > 0.05 and current_price > recent_high * 0.98:
            return Signal("buy", 0.65, {**metadata, "reason": "V-bottom formation"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    # Flash crash pattern
    prices = [40000, 39900, 39800, 39500, 38000, 37000, 36500, 37200, 37800, 38500]
    lows = [39800, 39700, 39600, 39200, 37500, 36000, 36200, 36800, 37400, 38000]
    volumes = [1000, 1100, 1200, 1500, 5000, 8000, 6000, 4000, 3000, 2500]
    
    strategy = FlashCrashReversalStrategy()
    signal = strategy.analyze(prices, volumes, lows)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
