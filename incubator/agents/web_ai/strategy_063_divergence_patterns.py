"""
Strategy 063: Divergence Patterns
Price-indicator divergence strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class DivergencePatternStrategy:
    """
    Detects divergences between price and indicators.
    Bullish divergence: price lower low, indicator higher low
    Bearish divergence: price higher high, indicator lower high
    """
    
    def __init__(
        self,
        lookback: int = 20,
        divergence_threshold: float = 0.02,
        confirmation_bars: int = 3
    ):
        self.lookback = lookback
        self.threshold = divergence_threshold
        self.confirmation = confirmation_bars
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """Calculate RSI values"""
        if len(prices) < period + 1:
            return [50] * len(prices)
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        rsi_values = [50]
        
        for i in range(period, len(deltas)):
            gains = [max(d, 0) for d in deltas[i-period:i]]
            losses = [abs(min(d, 0)) for d in deltas[i-period:i]]
            avg_gain = np.mean(gains)
            avg_loss = np.mean(losses)
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            rsi_values.append(rsi)
        
        # Pad with initial value
        while len(rsi_values) < len(prices):
            rsi_values.insert(0, rsi_values[0])
        
        return rsi_values
    
    def _find_divergence(self, prices: List[float], indicator: List[float]) -> str:
        """Find divergence pattern"""
        if len(prices) < self.lookback or len(indicator) < self.lookback:
            return "none"
        
        # Find recent highs and lows
        price_highs = []
        price_lows = []
        
        for i in range(2, len(prices) - 2):
            if prices[i] > prices[i-1] and prices[i] > prices[i-2] and \
               prices[i] > prices[i+1] and prices[i] > prices[i+2]:
                price_highs.append((i, prices[i]))
            if prices[i] < prices[i-1] and prices[i] < prices[i-2] and \
               prices[i] < prices[i+1] and prices[i] < prices[i+2]:
                price_lows.append((i, prices[i]))
        
        if len(price_highs) < 2 or len(price_lows) < 2:
            return "none"
        
        # Check for bearish divergence (price HH, indicator LH)
        if len(price_highs) >= 2:
            ph1, ph2 = price_highs[-2], price_highs[-1]
            ih1, ih2 = indicator[ph1[0]], indicator[ph2[0]]
            
            if ph2[1] > ph1[1] * (1 + self.threshold) and ih2 < ih1:
                return "bearish"
        
        # Check for bullish divergence (price LL, indicator HL)
        if len(price_lows) >= 2:
            pl1, pl2 = price_lows[-2], price_lows[-1]
            il1, il2 = indicator[pl1[0]], indicator[pl2[0]]
            
            if pl2[1] < pl1[1] * (1 - self.threshold) and il2 > il1:
                return "bullish"
        
        return "none"
    
    def analyze(
        self,
        prices: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(prices) < self.lookback + 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        rsi = self._calculate_rsi(prices)
        divergence = self._find_divergence(prices, rsi)
        
        current_price = prices[-1]
        current_rsi = rsi[-1]
        
        # Volume confirmation
        vol_ma = np.mean(volumes[-5:])
        vol_surge = volumes[-1] / vol_ma if vol_ma > 0 else 1
        
        metadata = {
            "divergence": divergence,
            "current_rsi": current_rsi,
            "vol_surge": vol_surge
        }
        
        if divergence == "bullish":
            if current_rsi < 40:  # Oversold
                confidence = min(0.8, 0.6 + (40 - current_rsi) / 100)
                return Signal("buy", confidence, {**metadata, "reason": "Bullish divergence + oversold"})
            else:
                return Signal("buy", 0.65, {**metadata, "reason": "Bullish divergence"})
        
        if divergence == "bearish":
            if current_rsi > 60:  # Overbought
                confidence = min(0.8, 0.6 + (current_rsi - 60) / 100)
                return Signal("sell", confidence, {**metadata, "reason": "Bearish divergence + overbought"})
            else:
                return Signal("sell", 0.65, {**metadata, "reason": "Bearish divergence"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    # Create bullish divergence: price lower low, RSI higher low
    prices = [40000, 40500, 40000, 39500, 39000, 39200, 38800, 38500, 38700, 38200]
    volumes = [1000 + np.random.randn() * 200 for _ in range(len(prices))]
    
    strategy = DivergencePatternStrategy()
    signal = strategy.analyze(prices, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
