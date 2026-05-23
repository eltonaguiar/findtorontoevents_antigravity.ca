"""
Strategy 138: Garman-Klass Vol
Garman-Klass volatility
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class GarmanKlassStrategy:
    """Garman-Klass OHLC volatility."""
    
    def __init__(self, period: int = 20):
        self.period = period
    
    def analyze(self, opens: List[float], highs: List[float], lows: List[float], closes: List[float]) -> Signal:
        if len(closes) < self.period + 1:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Garman-Klass
        gk = []
        for i in range(-self.period, 0):
            h, l, o, c = highs[i], lows[i], opens[i], closes[i]
            term1 = 0.5 * (np.log(h / l)) ** 2
            term2 = (2 * np.log(2) - 1) * (np.log(c / o)) ** 2
            gk.append(term1 - term2)
        
        gk_vol = np.sqrt(np.mean(gk))
        
        metadata = {"gk_vol": gk_vol}
        
        if gk_vol > 0.03:
            return Signal("sell", 0.6, metadata)
        if gk_vol < 0.01:
            return Signal("buy", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    opens = [40000]*25
    highs = [40200]*25
    lows = [39800]*25
    closes = [40100]*25
    s = GarmanKlassStrategy()
    sig = s.analyze(opens, highs, lows, closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
