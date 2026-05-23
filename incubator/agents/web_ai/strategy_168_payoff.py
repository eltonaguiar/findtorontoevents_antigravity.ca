"""
Strategy 168: Payoff Ratio
Payoff ratio analysis
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class PayoffRatioStrategy:
    """Payoff ratio (avg win / avg loss)."""
    
    def __init__(self, period: int = 30):
        self.period = period
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        r = returns[-self.period:]
        
        wins = [ri for ri in r if ri > 0]
        losses = [ri for ri in r if ri < 0]
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 1
        
        payoff = avg_win / avg_loss if avg_loss > 0 else 0
        
        metadata = {"payoff": payoff}
        
        if payoff > 1.5:
            return Signal("buy", 0.7, metadata)
        if payoff < 0.8:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.003 if i%3==0 else -0.001 for i in range(35)]
    s = PayoffRatioStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
