"""
Strategy 036: ATR Regime Detection
Volatility regime strategy using ATR
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ATRRegimeStrategy:
    """
    Detects volatility regimes using Average True Range.
    Adjusts strategy based on high/low volatility environments.
    """
    
    def __init__(
        self,
        atr_period: int = 14,
        regime_lookback: int = 50,
        high_vol_threshold: float = 1.5,
        low_vol_threshold: float = 0.7
    ):
        self.atr_period = atr_period
        self.regime_lookback = regime_lookback
        self.high_vol_threshold = high_vol_threshold
        self.low_vol_threshold = low_vol_threshold
    
    def _calculate_atr(self, highs: List[float], lows: List[float], closes: List[float]) -> List[float]:
        atr_values = []
        for i in range(1, len(highs)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            tr = max(tr1, tr2, tr3)
            atr_values.append(tr)
        return atr_values
    
    def analyze(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(highs) < self.regime_lookback + self.atr_period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate ATR
        tr_values = self._calculate_atr(highs, lows, closes)
        atr = np.mean(tr_values[-self.atr_period:])
        
        # Historical ATR for regime classification
        historical_atr = []
        for i in range(self.regime_lookback, len(tr_values)):
            historical_atr.append(np.mean(tr_values[i-self.atr_period:i]))
        
        atr_median = np.median(historical_atr)
        atr_percentile = sum(1 for a in historical_atr if a < atr) / len(historical_atr)
        
        # Regime classification
        atr_ratio = atr / atr_median if atr_median > 0 else 1
        
        if atr_ratio > self.high_vol_threshold:
            regime = "high_volatility"
        elif atr_ratio < self.low_vol_threshold:
            regime = "low_volatility"
        else:
            regime = "normal"
        
        # Price momentum
        price_change = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 else 0
        
        # Volume confirmation
        vol_ma = np.mean(volumes[-10:])
        vol_surge = volumes[-1] / vol_ma if vol_ma > 0 else 1
        
        metadata = {
            "atr": atr,
            "atr_ratio": atr_ratio,
            "atr_percentile": atr_percentile,
            "regime": regime,
            "price_change": price_change,
            "vol_surge": vol_surge
        }
        
        # High volatility regime - trend following
        if regime == "high_volatility":
            if price_change > 0.02 and vol_surge > 1.3:
                return Signal("buy", 0.7, {**metadata, "reason": "High vol breakout up"})
            if price_change < -0.02 and vol_surge > 1.3:
                return Signal("sell", 0.7, {**metadata, "reason": "High vol breakout down"})
        
        # Low volatility regime - mean reversion or breakout anticipation
        if regime == "low_volatility":
            if atr_percentile < 0.2 and vol_surge > 1.5:
                # Volatility expansion coming
                if price_change > 0:
                    return Signal("buy", 0.6, {**metadata, "reason": "Low vol compression breaking up"})
                else:
                    return Signal("sell", 0.6, {**metadata, "reason": "Low vol compression breaking down"})
            
            # Range trading
            mid = (max(highs[-10:]) + min(lows[-10:])) / 2
            if closes[-1] < mid * 0.995:
                return Signal("buy", 0.55, {**metadata, "reason": "Low vol range low"})
            if closes[-1] > mid * 1.005:
                return Signal("sell", 0.55, {**metadata, "reason": "Low vol range high"})
        
        # Normal regime - standard momentum
        if price_change > 0.015:
            return Signal("buy", 0.6, {**metadata, "reason": "Normal regime momentum"})
        if price_change < -0.015:
            return Signal("sell", 0.6, {**metadata, "reason": "Normal regime momentum"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 70
    base = 40000
    
    # Generate price data with varying volatility
    closes = [base]
    highs = [base + 100]
    lows = [base - 100]
    volumes = [1000]
    
    for i in range(1, n):
        vol = 50 if i < 50 else 200  # Low vol then high vol
        change = np.random.randn() * vol
        close = closes[-1] + change
        closes.append(close)
        highs.append(close + abs(np.random.randn() * vol * 0.5))
        lows.append(close - abs(np.random.randn() * vol * 0.5))
        volumes.append(1000 + np.random.randn() * 200)
    
    strategy = ATRRegimeStrategy()
    signal = strategy.analyze(highs, lows, closes, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
