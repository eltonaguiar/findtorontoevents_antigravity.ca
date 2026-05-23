"""
Strategy 099: Positive Volume Index
PVI crowd tracker
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class PVIStrategy:
    """Positive Volume Index crowd indicator."""
    
    def __init__(self, ma_period: int = 255):
        self.ma_period = ma_period
    
    def analyze(self, closes: List[float], volumes: List[float]) -> Signal:
        if len(closes) < 2:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate PVI
        pvi = [1000]
        for i in range(1, len(closes)):
            if volumes[i] > volumes[i-1]:
                pvi.append(pvi[-1] + (closes[i] - closes[i-1]) / closes[i-1] * pvi[-1])
            else:
                pvi.append(pvi[-1])
        
        # PVI vs its MA
        if len(pvi) >= self.ma_period:
            pvi_ma = np.mean(pvi[-self.ma_period:])
        else:
            pvi_ma = np.mean(pvi)
        
        metadata = {"pvi": pvi[-1], "pvi_ma": pvi_ma}
        
        if pvi[-1] > pvi_ma:
            return Signal("buy", 0.6, metadata)
        if pvi[-1] < pvi_ma:
            return Signal("sell", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*40 for i in range(30)]
    volumes = [1000 + (i%5)*50 for i in range(30)]
    s = PVIStrategy()
    sig = s.analyze(closes, volumes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
