"""
Strategy 097: Price Volume Trend
PVT cumulative volume
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class PVTStrategy:
    """Price Volume Trend cumulative indicator."""
    
    def __init__(self, ma_period: int = 21):
        self.ma_period = ma_period
    
    def analyze(self, closes: List[float], volumes: List[float]) -> Signal:
        if len(closes) < 2:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate PVT
        pvt = [volumes[0]]
        for i in range(1, len(closes)):
            change = (closes[i] - closes[i-1]) / closes[i-1]
            pvt.append(pvt[-1] + volumes[i] * change)
        
        # PVT vs MA
        pvt_ma = np.mean(pvt[-self.ma_period:])
        
        metadata = {"pvt": pvt[-1], "pvt_ma": pvt_ma}
        
        if pvt[-1] > pvt_ma and closes[-1] > closes[-2]:
            return Signal("buy", 0.65, metadata)
        if pvt[-1] < pvt_ma and closes[-1] < closes[-2]:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*50 for i in range(25)]
    volumes = [1000]*25
    s = PVTStrategy()
    sig = s.analyze(closes, volumes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
