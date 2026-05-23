"""
Strategy 164: Recovery Factor
Recovery factor analysis
"""
from dataclasses import dataclass
from typing import List

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class RecoveryFactorStrategy:
    """Trade recovery from drawdown."""
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < 10:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Find max drawdown
        peak = closes[0]
        max_dd = 0
        
        for c in closes:
            if c > peak:
                peak = c
            dd = (peak - c) / peak
            max_dd = max(max_dd, dd)
        
        # Recovery
        total_return = (closes[-1] - closes[0]) / closes[0]
        recovery = total_return / max_dd if max_dd > 0 else total_return
        
        metadata = {"recovery": recovery, "max_dd": max_dd}
        
        if recovery > 3:
            return Signal("buy", 0.7, metadata)
        if recovery < 1 and max_dd > 0.1:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000, 38000, 37000, 39000, 42000, 45000]
    s = RecoveryFactorStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
