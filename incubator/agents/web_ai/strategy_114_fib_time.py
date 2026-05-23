"""
Strategy 114: Fibonacci Time
Fibonacci time zones
"""
from dataclasses import dataclass
from typing import List

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class FibonacciTimeStrategy:
    """Fibonacci time zone analysis."""
    
    def __init__(self):
        self.fib_numbers = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
    
    def analyze(self, significant_low_idx: int, current_idx: int, closes: List[float]) -> Signal:
        bars_since_low = current_idx - significant_low_idx
        
        # Check if near fib time zone
        near_fib = any(abs(bars_since_low - f) <= 1 for f in self.fib_numbers)
        
        metadata = {"bars_since_low": bars_since_low, "near_fib": near_fib}
        
        if near_fib and closes[-1] > closes[-3]:
            return Signal("buy", 0.6, metadata)
        if near_fib and closes[-1] < closes[-3]:
            return Signal("sell", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*100 for i in range(15)]
    s = FibonacciTimeStrategy()
    sig = s.analyze(0, 13, closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
