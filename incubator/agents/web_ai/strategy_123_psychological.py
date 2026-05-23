"""
Strategy 123: Psychological Line
Psychological line sentiment
"""
from dataclasses import dataclass
from typing import List

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class PsychologicalLineStrategy:
    """Psychological Line sentiment indicator."""
    
    def __init__(self, period: int = 12):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period + 1:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Count up days
        up_days = sum(1 for i in range(-self.period, 0) if closes[i] > closes[i-1])
        psy = 100 * up_days / self.period
        
        metadata = {"psy": psy}
        
        if psy > 75:
            return Signal("sell", 0.7, metadata)
        if psy < 25:
            return Signal("buy", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + (i%3)*100 for i in range(15)]
    s = PsychologicalLineStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
