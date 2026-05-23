"""
Strategy 176: Consecutive Wins
Consecutive wins/losses
"""
from dataclasses import dataclass
from typing import List

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ConsecutiveStrategy:
    """Consecutive wins/losses streak."""
    
    def __init__(self, threshold: int = 3):
        self.threshold = threshold
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Count consecutive
        streak = 0
        direction = 1 if returns[-1] > 0 else -1
        
        for r in reversed(returns):
            if (r > 0 and direction == 1) or (r <= 0 and direction == -1):
                streak += 1
            else:
                break
        
        metadata = {"streak": streak, "direction": direction}
        
        if streak >= self.threshold and direction == 1:
            return Signal("sell", 0.65, metadata)
        if streak >= self.threshold and direction == -1:
            return Signal("buy", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.01, 0.02, 0.015, 0.01, -0.005]
    s = ConsecutiveStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
