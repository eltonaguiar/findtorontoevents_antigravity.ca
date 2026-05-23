"""
Strategy 116: Fibonacci Fans
Fibonacci fan lines
"""
from dataclasses import dataclass
from typing import List

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class FibonacciFanStrategy:
    """Fibonacci fan trend lines."""
    
    def analyze(self, start_price: float, end_price: float, current: float, bars: int) -> Signal:
        range_size = end_price - start_price
        
        # Fan levels
        fan_382 = start_price + range_size * 0.382
        fan_50 = start_price + range_size * 0.5
        fan_618 = start_price + range_size * 0.618
        
        metadata = {"fan_382": fan_382, "fan_50": fan_50, "fan_618": fan_618}
        
        if current > fan_618:
            return Signal("buy", 0.7, metadata)
        if current < fan_382:
            return Signal("sell", 0.7, metadata)
        if current > fan_50:
            return Signal("buy", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    s = FibonacciFanStrategy()
    sig = s.analyze(40000, 45000, 43000, 20)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
