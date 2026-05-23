"""
Strategy 180: Out of Sample
Out of sample validation
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class OutOfSampleStrategy:
    """Out of sample performance."""
    
    def __init__(self, in_sample: int = 60, out_sample: int = 20):
        self.in_sample = in_sample
        self.out_sample = out_sample
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < self.in_sample + self.out_sample:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        is_ret = np.mean(returns[-self.in_sample-self.out_sample:-self.out_sample])
        oos_ret = np.mean(returns[-self.out_sample:])
        
        degradation = (is_ret - oos_ret) / is_ret if is_ret != 0 else 0
        
        metadata = {"is_ret": is_ret, "oos_ret": oos_ret, "degradation": degradation}
        
        if oos_ret > 0 and degradation < 0.5:
            return Signal("buy", 0.7, metadata)
        if oos_ret < 0:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.002]*80 + [0.001]*20
    s = OutOfSampleStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
