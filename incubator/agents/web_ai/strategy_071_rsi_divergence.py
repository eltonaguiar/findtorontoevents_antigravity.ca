"""
Strategy 071: RSI Divergence
RSI divergence detection
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class RSIDivergenceStrategy:
    """Detects RSI divergences for reversal signals."""
    
    def __init__(self, period: int = 14, threshold: float = 0.02):
        self.period = period
        self.threshold = threshold
    
    def _rsi(self, prices: List[float]) -> List[float]:
        if len(prices) < self.period + 1:
            return [50] * len(prices)
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        rsi_vals = [50]
        for i in range(self.period, len(deltas)):
            gains = [max(d, 0) for d in deltas[i-self.period:i]]
            losses = [abs(min(d, 0)) for d in deltas[i-self.period:i]]
            avg_gain, avg_loss = np.mean(gains), np.mean(losses)
            rs = avg_gain / avg_loss if avg_loss > 0 else 0
            rsi_vals.append(100 - (100 / (1 + rs)))
        while len(rsi_vals) < len(prices):
            rsi_vals.insert(0, 50)
        return rsi_vals
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        if len(prices) < 20:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        rsi = self._rsi(prices)
        
        # Find price and RSI lows/highs
        price_lows = [(i, prices[i]) for i in range(5, len(prices)-5) 
                      if prices[i] <= min(prices[i-5:i]) and prices[i] <= min(prices[i+1:i+6])]
        rsi_lows = [(i, rsi[i]) for i, _ in price_lows]
        
        price_highs = [(i, prices[i]) for i in range(5, len(prices)-5)
                       if prices[i] >= max(prices[i-5:i]) and prices[i] >= max(prices[i+1:i+6])]
        rsi_highs = [(i, rsi[i]) for i, _ in price_highs]
        
        # Check divergence
        bullish_div = len(price_lows) >= 2 and len(rsi_lows) >= 2 and \
                      price_lows[-1][1] < price_lows[-2][1] and rsi_lows[-1][1] > rsi_lows[-2][1]
        
        bearish_div = len(price_highs) >= 2 and len(rsi_highs) >= 2 and \
                      price_highs[-1][1] > price_highs[-2][1] and rsi_highs[-1][1] < rsi_highs[-2][1]
        
        metadata = {"rsi": rsi[-1], "bullish_div": bullish_div, "bearish_div": bearish_div}
        
        if bullish_div and rsi[-1] < 40:
            return Signal("buy", 0.75, metadata)
        if bearish_div and rsi[-1] > 60:
            return Signal("sell", 0.75, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    np.random.seed(42)
    prices = [40000 + np.sin(i*0.1)*500 - i*10 for i in range(30)]
    volumes = [1000]*30
    s = RSIDivergenceStrategy()
    sig = s.analyze(prices, volumes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
