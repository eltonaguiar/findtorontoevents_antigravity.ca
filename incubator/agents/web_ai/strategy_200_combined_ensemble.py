"""
Strategy 200: Combined Ensemble
Meta ensemble strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class CombinedEnsembleStrategy:
    """Meta ensemble of multiple signals."""
    
    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
    
    def analyze(self, signals: List[str], confidences: List[float]) -> Signal:
        if not signals or not confidences:
            return Signal("hold", 0.0, {"error": "No signals"})
        
        # Weighted vote
        buy_score = sum(c for s, c in zip(signals, confidences) if s == "buy")
        sell_score = sum(c for s, c in zip(signals, confidences) if s == "sell")
        
        total = sum(confidences)
        
        buy_pct = buy_score / total if total > 0 else 0
        sell_pct = sell_score / total if total > 0 else 0
        
        metadata = {"buy_pct": buy_pct, "sell_pct": sell_pct, "count": len(signals)}
        
        if buy_pct > self.threshold:
            return Signal("buy", buy_pct, metadata)
        if sell_pct > self.threshold:
            return Signal("sell", sell_pct, metadata)
        return Signal("hold", 0.3, metadata)

if __name__ == "__main__":
    signals = ["buy", "buy", "hold", "buy", "sell"]
    confidences = [0.7, 0.6, 0.5, 0.8, 0.4]
    s = CombinedEnsembleStrategy()
    sig = s.analyze(signals, confidences)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
