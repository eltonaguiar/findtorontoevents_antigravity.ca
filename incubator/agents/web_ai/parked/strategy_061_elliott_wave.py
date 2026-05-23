"""
Strategy 061: Elliott Wave
Elliott wave pattern detection
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ElliottWaveStrategy:
    """
    Simplified Elliott Wave pattern detection.
    Identifies impulse and corrective waves.
    """
    
    def __init__(
        self,
        wave_tolerance: float = 0.15,
        min_wave_size: float = 0.02,
        lookback: int = 30
    ):
        self.tolerance = wave_tolerance
        self.min_size = min_wave_size
        self.lookback = lookback
    
    def _find_waves(self, prices: List[float]) -> List[dict]:
        """Find potential Elliott waves"""
        waves = []
        
        # Simple wave detection based on direction changes
        direction = 1 if prices[1] > prices[0] else -1
        wave_start = 0
        
        for i in range(2, len(prices)):
            new_direction = 1 if prices[i] > prices[i-1] else -1
            
            if new_direction != direction:
                wave_size = abs(prices[i-1] - prices[wave_start]) / prices[wave_start]
                if wave_size >= self.min_size:
                    waves.append({
                        "start": wave_start,
                        "end": i-1,
                        "direction": direction,
                        "size": wave_size,
                        "start_price": prices[wave_start],
                        "end_price": prices[i-1]
                    })
                wave_start = i-1
                direction = new_direction
        
        return waves
    
    def analyze(
        self,
        prices: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(prices) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        waves = self._find_waves(prices[-self.lookback:])
        
        if len(waves) < 3:
            return Signal("hold", 0.1, {"error": "Insufficient waves detected"})
        
        # Check for 5-wave impulse pattern
        recent_waves = waves[-5:] if len(waves) >= 5 else waves
        
        # Wave 1, 3, 5 should be in same direction (impulse)
        # Wave 2, 4 should be corrections
        if len(recent_waves) >= 5:
            w1, w2, w3, w4, w5 = recent_waves[0], recent_waves[1], recent_waves[2], recent_waves[3], recent_waves[4]
            
            # Check impulse pattern
            impulse_up = w1["direction"] == 1 and w3["direction"] == 1 and w5["direction"] == 1
            impulse_down = w1["direction"] == -1 and w3["direction"] == -1 and w5["direction"] == -1
            
            # Wave 3 should be longest
            w3_longest = w3["size"] > w1["size"] and w3["size"] > w5["size"]
            
            # Wave 4 should not enter wave 1 territory
            if impulse_up:
                w4_valid = w4["end_price"] > w1["end_price"]
            else:
                w4_valid = w4["end_price"] < w1["end_price"]
            
            impulse_pattern = (impulse_up or impulse_down) and w3_longest and w4_valid
        else:
            impulse_pattern = False
            impulse_up = False
        
        # Volume confirmation
        recent_vol = np.mean(volumes[-5:])
        avg_vol = np.mean(volumes[-self.lookback:])
        vol_confirm = recent_vol > avg_vol
        
        metadata = {
            "wave_count": len(waves),
            "impulse_pattern": impulse_pattern,
            "impulse_up": impulse_up,
            "recent_waves": len(recent_waves),
            "vol_confirm": vol_confirm
        }
        
        if impulse_pattern and impulse_up and vol_confirm:
            return Signal("buy", 0.75, {**metadata, "reason": "Elliott Wave 5-up complete"})
        
        if impulse_pattern and not impulse_up and vol_confirm:
            return Signal("sell", 0.75, {**metadata, "reason": "Elliott Wave 5-down complete"})
        
        # Wave 3 detection
        if len(recent_waves) >= 3 and recent_waves[2]["size"] > recent_waves[0]["size"] * 1.2:
            if recent_waves[0]["direction"] == 1:
                return Signal("buy", 0.6, {**metadata, "reason": "Wave 3 up detected"})
            else:
                return Signal("sell", 0.6, {**metadata, "reason": "Wave 3 down detected"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    # Create 5-wave up pattern
    base = 40000
    prices = [
        base,          # 0 - start
        base + 500,    # 1 - wave 1 up
        base + 300,    # 2 - wave 2 down
        base + 1200,   # 3 - wave 3 up (longest)
        base + 900,    # 4 - wave 4 down
        base + 1500,   # 5 - wave 5 up
    ]
    
    # Add more data
    for i in range(25):
        prices.append(prices[-1] + np.random.randn() * 50)
    
    volumes = [1000 + np.random.randn() * 200 for _ in range(len(prices))]
    volumes[3] = 2000  # High volume on wave 3
    
    strategy = ElliottWaveStrategy()
    signal = strategy.analyze(prices, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
