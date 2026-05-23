"""
KalmanMeanReversionStrategy - Baby Strat
========================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: Price deviates significantly from Kalman filter trend estimate
- Exit when: Price returns to Kalman estimate or SL hit
- Risk management: Dynamic position sizing based on prediction error

Unique Value Proposition:
Uses Kalman filter to adaptively estimate the "true" price trend, filtering out noise.
Mean reversion is calculated against this adaptive estimate rather than static MA.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]

@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class KalmanMeanReversionStrategy:
    """
    Kalman Filter Mean Reversion Strategy
    
    Applies Kalman filtering to estimate the underlying price trend,
    then trades mean reversion when price deviates from this estimate.
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.process_variance = self.params.get('process_variance', 1e-5)
        self.measurement_variance = self.params.get('measurement_variance', 1e-3)
        self.deviation_threshold = self.params.get('deviation_threshold', 2.0)
        self.min_deviation_pct = self.params.get('min_deviation_pct', 0.015)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_mult = self.params.get('tp_mult', 1.0)
        self.sl_mult = self.params.get('sl_mult', 1.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < 50:
            return []

        # Calculate Kalman filter estimate
        kalman_estimate = self._kalman_filter(data['close'].values)
        kalman_series = pd.Series(kalman_estimate, index=data.index)
        
        # Calculate ATR
        atr = self._calculate_atr(data, self.atr_period)
        
        current_price = data['close'].iloc[-1]
        current_kalman = kalman_series.iloc[-1]
        current_atr = atr.iloc[-1]
        
        # Calculate deviation as percentage
        deviation_pct = (current_price - current_kalman) / current_kalman
        
        # Calculate standard deviation of recent deviations
        recent_prices = data['close'].iloc[-30:]
        recent_kalman = kalman_series.iloc[-30:]
        deviations = (recent_prices - recent_kalman) / recent_kalman
        deviation_std = deviations.std()
        
        # Z-score of deviation
        z_score = deviation_pct / deviation_std if deviation_std > 0 else 0
        
        signals = []
        
        # Long signal: Price below Kalman estimate by threshold
        if deviation_pct < -self.min_deviation_pct and z_score < -self.deviation_threshold:
            confidence = min(abs(z_score) / 4, 0.95)
            
            tp = current_kalman  # Target: return to estimate
            sl = current_price - (current_atr * self.sl_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Kalman deviation: {deviation_pct:.2%} (z: {z_score:.2f})"
            ))
        
        # Short signal: Price above Kalman estimate by threshold
        elif deviation_pct > self.min_deviation_pct and z_score > self.deviation_threshold:
            confidence = min(abs(z_score) / 4, 0.95)
            
            tp = current_kalman
            sl = current_price + (current_atr * self.sl_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Kalman deviation: {deviation_pct:.2%} (z: {z_score:.2f})"
            ))
        
        return signals

    def _kalman_filter(self, prices: np.ndarray) -> np.ndarray:
        """
        Apply Kalman filter to price series.
        
        State: current price level
        Measurement: observed price
        """
        n = len(prices)
        estimates = np.zeros(n)
        
        # Initial estimates
        estimate = prices[0]
        error_estimate = 1.0
        
        for i in range(n):
            # Prediction (state stays same, uncertainty grows)
            error_estimate += self.process_variance
            
            # Update
            kalman_gain = error_estimate / (error_estimate + self.measurement_variance)
            estimate = estimate + kalman_gain * (prices[i] - estimate)
            error_estimate = (1 - kalman_gain) * error_estimate
            
            estimates[i] = estimate
        
        return estimates

    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        high = data['high']
        low = data['low']
        close = data['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period, min_periods=1).mean()
        return atr


# ==============================================================================
# TESTING
# ==============================================================================

if __name__ == "__main__":
    """Quick test with synthetic data."""
    
    np.random.seed(42)
    n = 200
    returns = np.random.normal(0.0001, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    
    test_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.random.uniform(100, 1000, n)
    })
    
    strategy = KalmanMeanReversionStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
