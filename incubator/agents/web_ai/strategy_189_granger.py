"""
Strategy 189: Granger Causality
Granger causality test
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class GrangerStrategy:
    """Granger causality with market."""
    
    def __init__(self, lag: int = 2):
        self.lag = lag
    
    def analyze(self, asset: List[float], market: List[float]) -> Signal:
        if len(asset) < 20 or len(market) < 20:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Simple correlation-based causality proxy
        corr = np.corrcoef(asset[-20:], market[-20:])[0, 1]
        
        # Lead-lag
        lead_corr = np.corrcoef(asset[-19:], market[-20:-1])[0, 1] if len(asset) > 20 else 0
        
        metadata = {"corr": corr, "lead_corr": lead_corr}
        
        if lead_corr > corr and corr > 0.5:
            return Signal("buy", 0.65, metadata)
        if lead_corr < corr and corr < -0.3:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    asset = [40000 + i*100 for i in range(25)]
    market = [40000 + (i-1)*100 for i in range(25)]
    s = GrangerStrategy()
    sig = s.analyze(asset, market)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
