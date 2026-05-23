"""
Strategy 169: Expectancy
Trade expectancy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ExpectancyStrategy:
    """Trade expectancy."""
    
    def __init__(self, period: int = 30):
        self.period = period
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        r = returns[-self.period:]
        
        wins = [ri for ri in r if ri > 0]
        win_rate = len(wins) / len(r) if r else 0
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean([ri for ri in r if ri <= 0])) if any(ri <= 0 for ri in r) else 1
        
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        metadata = {"expectancy": expectancy}
        
        if expectancy > 0.001:
            return Signal("buy", 0.7, metadata)
        if expectancy < -0.001:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.002 if i%3==0 else -0.0005 for i in range(35)]
    s = ExpectancyStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
