"""
Strategy 166: Profit Factor
Profit factor analysis
"""
from dataclasses import dataclass
from typing import List

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ProfitFactorStrategy:
    """Profit factor (gross profit / gross loss)."""
    
    def __init__(self, period: int = 30):
        self.period = period
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        r = returns[-self.period:]
        
        gross_profit = sum(ri for ri in r if ri > 0)
        gross_loss = sum(abs(ri) for ri in r if ri < 0)
        
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        metadata = {"pf": pf}
        
        if pf > 2:
            return Signal("buy", 0.7, metadata)
        if pf < 0.8:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.002 if i%3==0 else -0.001 for i in range(35)]
    s = ProfitFactorStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
