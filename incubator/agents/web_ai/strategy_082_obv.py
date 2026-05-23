"""
Strategy 082: OBV On Balance Volume
OBV trend confirmation
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class OBVStrategy:
    """On Balance Volume trend strategy."""
    
    def __init__(self, ma_period: int = 20):
        self.ma_period = ma_period
    
    def analyze(self, closes: List[float], volumes: List[float]) -> Signal:
        if len(closes) < 2:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate OBV
        obv = [volumes[0]]
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                obv.append(obv[-1] + volumes[i])
            elif closes[i] < closes[i-1]:
                obv.append(obv[-1] - volumes[i])
            else:
                obv.append(obv[-1])
        
        # OBV trend
        obv_ma = np.mean(obv[-self.ma_period:])
        obv_trend = obv[-1] > obv_ma
        
        # Price trend
        price_ma = np.mean(closes[-self.ma_period:])
        price_trend = closes[-1] > price_ma
        
        metadata = {"obv": obv[-1], "obv_trend": obv_trend, "price_trend": price_trend}
        
        if obv_trend and price_trend:
            return Signal("buy", 0.7, metadata)
        if not obv_trend and not price_trend:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.25, metadata)

if __name__ == "__main__":
    closes = [40000 + i*100 for i in range(25)]
    volumes = [1000 + i*50 for i in range(25)]
    s = OBVStrategy()
    sig = s.analyze(closes, volumes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
