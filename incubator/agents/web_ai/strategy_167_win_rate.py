"""
Strategy 167: Win Rate
Win rate momentum
"""
from dataclasses import dataclass
from typing import List

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class WinRateStrategy:
    """Win rate trend."""
    
    def __init__(self, period: int = 30):
        self.period = period
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        r = returns[-self.period:]
        wins = sum(1 for ri in r if ri > 0)
        win_rate = wins / len(r)
        
        metadata = {"win_rate": win_rate}
        
        if win_rate > 0.6:
            return Signal("buy", 0.7, metadata)
        if win_rate < 0.4:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.001 if i%2==0 else -0.0005 for i in range(35)]
    s = WinRateStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
