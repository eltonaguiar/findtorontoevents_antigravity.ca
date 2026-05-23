"""
Strategy 098: Negative Volume Index
NVI smart money tracker
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class NVIStrategy:
    """Negative Volume Index smart money indicator."""
    
    def __init__(self, ma_period: int = 255):
        self.ma_period = ma_period
    
    def analyze(self, closes: List[float], volumes: List[float]) -> Signal:
        if len(closes) < 2:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate NVI
        nvi = [1000]
        for i in range(1, len(closes)):
            if volumes[i] < volumes[i-1]:
                nvi.append(nvi[-1] + (closes[i] - closes[i-1]) / closes[i-1] * nvi[-1])
            else:
                nvi.append(nvi[-1])
        
        # NVI vs its MA
        if len(nvi) >= self.ma_period:
            nvi_ma = np.mean(nvi[-self.ma_period:])
        else:
            nvi_ma = np.mean(nvi)
        
        metadata = {"nvi": nvi[-1], "nvi_ma": nvi_ma}
        
        if nvi[-1] > nvi_ma:
            return Signal("buy", 0.6, metadata)
        if nvi[-1] < nvi_ma:
            return Signal("sell", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*40 for i in range(30)]
    volumes = [1000 - (i%5)*50 for i in range(30)]
    s = NVIStrategy()
    sig = s.analyze(closes, volumes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
