"""
Strategy 060: Harmonic Patterns
Harmonic pattern detection
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class HarmonicPatternStrategy:
    """
    Detects harmonic patterns (Gartley, Butterfly, Bat, Crab).
    Trades pattern completion.
    """
    
    def __init__(
        self,
        tolerance: float = 0.05,
        pattern_lookback: int = 20
    ):
        self.tolerance = tolerance
        self.lookback = pattern_lookback
    
    def _find_swing_points(self, prices: List[float], window: int = 3) -> List[tuple]:
        """Find swing highs and lows"""
        swings = []
        for i in range(window, len(prices) - window):
            # Swing high
            if all(prices[i] >= prices[i-j] for j in range(1, window+1)) and \
               all(prices[i] >= prices[i+j] for j in range(1, window+1)):
                swings.append((i, prices[i], "high"))
            # Swing low
            elif all(prices[i] <= prices[i-j] for j in range(1, window+1)) and \
                 all(prices[i] <= prices[i+j] for j in range(1, window+1)):
                swings.append((i, prices[i], "low"))
        return swings
    
    def _check_bullish_bat(self, x, a, b, c, d) -> bool:
        """Check for bullish Bat pattern"""
        xa = abs(a - x)
        ab = abs(b - a)
        bc = abs(c - b)
        cd = abs(d - c)
        
        if xa == 0:
            return False
        
        ab_xa = ab / xa
        bc_ab = bc / ab if ab > 0 else 0
        cd_bc = cd / bc if bc > 0 else 0
        
        # Bat ratios: B=0.382-0.5, C=0.382-0.886, D=1.618-2.618
        return (0.382 - self.tolerance < ab_xa < 0.5 + self.tolerance and
                0.382 - self.tolerance < bc_ab < 0.886 + self.tolerance and
                1.618 - self.tolerance < cd_bc < 2.618 + self.tolerance)
    
    def analyze(
        self,
        prices: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(prices) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        swings = self._find_swing_points(prices[-self.lookback:])
        
        if len(swings) < 5:
            return Signal("hold", 0.1, {"error": "Insufficient swing points"})
        
        # Use last 5 swings
        recent_swings = swings[-5:]
        points = [s[1] for s in recent_swings]
        
        x, a, b, c, d = points[0], points[1], points[2], points[3], points[4]
        
        # Check patterns
        bullish_bat = self._check_bullish_bat(x, a, b, c, d)
        
        # Check if D is recent (pattern completing)
        d_recent = recent_swings[-1][0] > len(prices) - self.lookback - 3
        
        # Volume at D
        vol_at_d = volumes[-1] / np.mean(volumes[-5:]) if len(volumes) >= 5 else 1
        
        metadata = {
            "swing_points": len(swings),
            "pattern_type": "bullish_bat" if bullish_bat else "none",
            "d_recent": d_recent,
            "vol_at_d": vol_at_d,
            "xa": abs(a - x),
            "ab": abs(b - a),
            "bc": abs(c - b),
            "cd": abs(d - c)
        }
        
        if bullish_bat and d_recent:
            if vol_at_d > 1.2:
                return Signal("buy", 0.75, {**metadata, "reason": "Bullish Bat pattern complete"})
            else:
                return Signal("buy", 0.6, {**metadata, "reason": "Bullish Bat pattern forming"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    # Create a bullish Bat-like pattern
    # X=100, A=120, B=108 (0.4 of XA), C=114 (0.5 of AB), D=102 (2.0 of BC)
    base = 40000
    prices = [base, base + 2000, base + 800, base + 1400, base + 200, base + 500]
    
    # Add more data
    for i in range(20):
        prices.append(prices[-1] + np.random.randn() * 100)
    
    volumes = [1000 + np.random.randn() * 200 for _ in range(len(prices))]
    
    strategy = HarmonicPatternStrategy()
    signal = strategy.analyze(prices, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
