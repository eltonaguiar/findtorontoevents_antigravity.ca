"""
Strategy 151: Kelly Criterion
Kelly optimal sizing
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class KellyCriterionStrategy:
    """Kelly criterion optimal position sizing."""
    
    def __init__(self, period: int = 50):
        self.period = period
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        r = returns[-self.period:]
        
        wins = [ri for ri in r if ri > 0]
        losses = [ri for ri in r if ri <= 0]
        
        w = len(wins) / len(r) if r else 0
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 1
        
        kelly = w - (1 - w) / (avg_win / avg_loss) if avg_loss > 0 else 0
        
        metadata = {"kelly": kelly}
        
        if kelly > 0.2:
            return Signal("buy", min(0.9, 0.5 + kelly), metadata)
        if kelly < -0.1:
            return Signal("sell", min(0.9, 0.5 - kelly), metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.001 + np.random.randn()*0.015 for _ in range(60)]
    s = KellyCriterionStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
