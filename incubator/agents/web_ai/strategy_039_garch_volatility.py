"""
Strategy 039: GARCH Volatility Forecast
Volatility forecasting strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class GARCHVolatilityStrategy:
    """
    Simple GARCH-inspired volatility forecasting.
    Predicts volatility changes and adjusts position sizing.
    """
    
    def __init__(
        self,
        omega: float = 0.000001,
        alpha: float = 0.1,
        beta: float = 0.85,
        vol_threshold: float = 0.02
    ):
        self.omega = omega
        self.alpha = alpha
        self.beta = beta
        self.vol_threshold = vol_threshold
    
    def _calculate_returns(self, prices: List[float]) -> List[float]:
        return [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
    
    def _forecast_volatility(self, returns: List[float]) -> float:
        """Simple EWMA volatility forecast"""
        if len(returns) < 10:
            return 0.02
        
        # Initialize with historical variance
        var = np.var(returns)
        
        # GARCH iteration
        for r in returns[-30:]:
            var = self.omega + self.alpha * (r ** 2) + self.beta * var
        
        return np.sqrt(var)
    
    def analyze(
        self,
        prices: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(prices) < 30:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        returns = self._calculate_returns(prices)
        
        # Current volatility
        current_vol = np.std(returns[-10:])
        
        # Forecast volatility
        forecast_vol = self._forecast_volatility(returns)
        
        # Volatility trend
        long_vol = np.std(returns[-30:])
        vol_trend = forecast_vol / long_vol if long_vol > 0 else 1
        
        # Price trend
        price_ma_short = np.mean(prices[-5:])
        price_ma_long = np.mean(prices[-20:])
        trend = (price_ma_short - price_ma_long) / price_ma_long
        
        metadata = {
            "current_vol": current_vol,
            "forecast_vol": forecast_vol,
            "long_vol": long_vol,
            "vol_trend": vol_trend,
            "trend": trend
        }
        
        # Forecasting volatility increase
        if forecast_vol > current_vol * 1.3 and forecast_vol > self.vol_threshold:
            if trend > 0.01:
                return Signal("buy", 0.7, {**metadata, "reason": "Vol expansion expected, trend up"})
            elif trend < -0.01:
                return Signal("sell", 0.7, {**metadata, "reason": "Vol expansion expected, trend down"})
            else:
                return Signal("hold", 0.35, {**metadata, "reason": "Vol expansion expected, no clear trend"})
        
        # Forecasting volatility decrease
        if forecast_vol < current_vol * 0.8:
            if abs(trend) > 0.02:
                # Trend continuation likely with decreasing vol
                if trend > 0:
                    return Signal("buy", 0.6, {**metadata, "reason": "Trend continuation, vol decreasing"})
                else:
                    return Signal("sell", 0.6, {**metadata, "reason": "Trend continuation, vol decreasing"})
        
        # High volatility environment - reduce exposure
        if current_vol > self.vol_threshold * 2:
            return Signal("hold", 0.15, {**metadata, "reason": "High volatility - caution"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 50
    base = 40000
    
    # Generate returns with volatility clustering
    returns = []
    vol = 0.01
    for i in range(n):
        vol = 0.00001 + 0.1 * (returns[-1] ** 2 if returns else 0.0001) + 0.85 * vol
        returns.append(np.random.randn() * np.sqrt(vol))
    
    prices = [base]
    for r in returns:
        prices.append(prices[-1] * (1 + r))
    
    volumes = [1000 + np.random.randn() * 200 for _ in range(len(prices))]
    
    strategy = GARCHVolatilityStrategy()
    signal = strategy.analyze(prices, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
