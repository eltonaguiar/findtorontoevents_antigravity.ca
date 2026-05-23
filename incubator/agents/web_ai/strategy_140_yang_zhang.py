"""
Strategy 140: Yang-Zhang Vol
Yang-Zhang volatility
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class YangZhangStrategy:
    """Yang-Zhang overnight volatility."""
    
    def __init__(self, period: int = 20):
        self.period = period
    
    def analyze(self, opens: List[float], highs: List[float], lows: List[float], closes: List[float]) -> Signal:
        if len(closes) < self.period + 1:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Overnight volatility
        overnight = [np.log(o / closes[i-1]) ** 2 for i, o in enumerate(opens[-self.period:], -self.period)]
        
        # Rogers-Satchell
        rs = []
        for i in range(-self.period, 0):
            h, l, o, c = highs[i], lows[i], opens[i], closes[i]
            term = np.log(h / c) * np.log(h / o) + np.log(l / c) * np.log(l / o)
            rs.append(term)
        
        # Open-to-close
        oc = [np.log(c / o) ** 2 for o, c in zip(opens[-self.period:], closes[-self.period:])]
        
        k = 0.34 / (1.34 + (self.period + 1) / (self.period - 1))
        
        yz_vol = np.sqrt(np.mean(overnight) + k * np.mean(oc) + (1 - k) * np.mean(rs))
        
        metadata = {"yz_vol": yz_vol}
        
        if yz_vol > 0.03:
            return Signal("sell", 0.6, metadata)
        if yz_vol < 0.01:
            return Signal("buy", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    opens = [40000]*25
    highs = [40200]*25
    lows = [39800]*25
    closes = [40100]*25
    s = YangZhangStrategy()
    sig = s.analyze(opens, highs, lows, closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
