"""
Strategy 007: NUPL Sentiment Tracker
On-chain metric using Net Unrealized Profit/Loss
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class NUPLStrategy:
    """
    Net Unrealized Profit/Loss indicates market sentiment.
    NUPL > 0.5 = Euphoria/Greed (take profits)
    NUPL < 0 = Capitulation (accumulate)
    -0.25 to 0 = Hope/Fear (watch for reversal)
    """
    
    def __init__(
        self,
        euphoria_threshold: float = 0.5,
        belief_threshold: float = 0.25,
        hope_threshold: float = 0.0,
        fear_threshold: float = -0.25,
        capitulation_threshold: float = -0.5
    ):
        self.euphoria = euphoria_threshold
        self.belief = belief_threshold
        self.hope = hope_threshold
        self.fear = fear_threshold
        self.capitulation = capitulation_threshold
    
    def analyze(
        self,
        nupl: List[float],
        prices: List[float]
    ) -> Signal:
        if len(nupl) < 7:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        current_nupl = nupl[-1]
        nupl_ma = np.mean(nupl[-7:])
        nupl_trend = current_nupl - nupl[-7]
        
        # Determine sentiment zone
        if current_nupl > self.euphoria:
            zone = "euphoria"
        elif current_nupl > self.belief:
            zone = "belief"
        elif current_nupl > self.hope:
            zone = "optimism"
        elif current_nupl > self.fear:
            zone = "hope"
        elif current_nupl > self.capitulation:
            zone = "fear"
        else:
            zone = "capitulation"
        
        metadata = {
            "nupl": current_nupl,
            "nupl_ma": nupl_ma,
            "trend": nupl_trend,
            "zone": zone
        }
        
        # Extreme fear/capitulation - strong buy
        if current_nupl < self.fear and nupl_trend > 0:
            confidence = min(0.9, 0.6 + abs(current_nupl) * 0.3)
            return Signal("buy", confidence, {**metadata, "reason": "Capitulation reversal"})
        
        # Deep capitulation
        if current_nupl < self.capitulation:
            return Signal("buy", 0.85, {**metadata, "reason": "Maximum fear zone"})
        
        # Euphoria - take profits
        if current_nupl > self.euphoria and nupl_trend < 0:
            confidence = min(0.85, 0.5 + current_nupl * 0.3)
            return Signal("sell", confidence, {**metadata, "reason": "Euphoria peaking"})
        
        # Entering belief zone with momentum
        if current_nupl > self.belief and nupl_trend > 0.05:
            return Signal("buy", 0.6, {**metadata, "reason": "Belief building"})
        
        return Signal("hold", 0.25, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n_days = 30
    # NUPL recovering from negative
    nupl = [-0.3 + i * 0.015 + np.random.randn() * 0.02 for i in range(n_days)]
    prices = [40000 + i * 150 + np.random.randn() * 300 for i in range(n_days)]
    
    strategy = NUPLStrategy()
    signal = strategy.analyze(nupl, prices)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
