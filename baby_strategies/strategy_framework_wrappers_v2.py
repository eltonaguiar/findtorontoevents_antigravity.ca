"""
Strategy Framework Wrappers Version 2
=====================================

Wraps additional strategy variations to work with the backtest framework.
These include advanced strategies based on quantitative and technical algorithms.
"""

from backtest_framework import Strategy, Signal, PositionSide
import pandas as pd
import numpy as np

# Import new strategy variations
from adaptive_bollinger_momentum import AdaptiveBollingerMomentumStrategy
from volatility_regime_breakout import VolatilityRegimeBreakoutStrategy
from kama_volatility_adaptive import KamaVolatilityAdaptiveStrategy
from multi_timeframe_ema_cloud import MultiTimeframeEMACloudStrategy
from moving_average_slope_momentum import MovingAverageSlopeMomentumStrategy


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]

class AdaptiveBollingerMomentumWrapper(Strategy):
    """Wrapper for AdaptiveBollingerMomentumStrategy"""
    
    def __init__(self, name: str = "AdaptiveBollingerMomentum"):
        super().__init__(name)
        self.baby_strategy = AdaptiveBollingerMomentumStrategy()
        self.last_signal = None
    
    def _calculate_indicators(self):
        """Calculate indicators"""
        pass
    
    def on_bar(self, idx: int, bar: pd.Series):
        """Generate signals on each bar"""
        if idx < 40:  # Need sufficient data for calculations
            return None
        
        window_data = self.data.iloc[:idx+1]
        
        try:
            baby_signals = self.baby_strategy.generate_signals(window_data, "BTCUSDT")
            
            if baby_signals:
                direction = Signal.BUY if baby_signals[0].direction == "BUY" else Signal.SELL
                self.last_signal = direction
                return direction
            
            # Exit logic for open positions
            if self.last_signal == Signal.BUY:
                ema = window_data['close'].ewm(span=20, adjust=False).mean().iloc[-1]
                if window_data['close'].iloc[-1] >= ema:
                    self.last_signal = None
                    return Signal.SELL
            elif self.last_signal == Signal.SELL:
                ema = window_data['close'].ewm(span=20, adjust=False).mean().iloc[-1]
                if window_data['close'].iloc[-1] <= ema:
                    self.last_signal = None
                    return Signal.BUY
            
            return None
            
        except Exception as e:
            return None


class VolatilityRegimeBreakoutWrapper(Strategy):
    """Wrapper for VolatilityRegimeBreakoutStrategy"""
    
    def __init__(self, name: str = "VolatilityRegimeBreakout"):
        super().__init__(name)
        self.baby_strategy = VolatilityRegimeBreakoutStrategy()
        self.last_signal = None
    
    def _calculate_indicators(self):
        """Calculate indicators"""
        pass
    
    def on_bar(self, idx: int, bar: pd.Series):
        """Generate signals on each bar"""
        if idx < 120:  # Need sufficient data for volatility calculations
            return None
        
        window_data = self.data.iloc[:idx+1]
        
        try:
            baby_signals = self.baby_strategy.generate_signals(window_data, "BTCUSDT")
            
            if baby_signals:
                direction = Signal.BUY if baby_signals[0].direction == "BUY" else Signal.SELL
                self.last_signal = direction
                return direction
            
            return None
            
        except Exception as e:
            return None


class KamaVolatilityAdaptiveWrapper(Strategy):
    """Wrapper for KamaVolatilityAdaptiveStrategy"""
    
    def __init__(self, name: str = "KamaVolatilityAdaptive"):
        super().__init__(name)
        self.baby_strategy = KamaVolatilityAdaptiveStrategy()
        self.last_signal = None
    
    def _calculate_indicators(self):
        """Calculate indicators"""
        pass
    
    def on_bar(self, idx: int, bar: pd.Series):
        """Generate signals on each bar"""
        if idx < 30:  # Need sufficient data for KAMA
            return None
        
        window_data = self.data.iloc[:idx+1]
        
        try:
            baby_signals = self.baby_strategy.generate_signals(window_data, "BTCUSDT")
            
            if baby_signals:
                direction = Signal.BUY if baby_signals[0].direction == "BUY" else Signal.SELL
                self.last_signal = direction
                return direction
            
            # Exit logic based on KAMA
            if self.last_signal == Signal.BUY:
                kama = self.baby_strategy._calculate_kama(
                    window_data['close'], 10, 0.666, 0.0645
                ).iloc[-1]
                if window_data['close'].iloc[-1] < kama - (self._calculate_atr(window_data, 14).iloc[-1] * 1.5):
                    self.last_signal = None
                    return Signal.SELL
            elif self.last_signal == Signal.SELL:
                kama = self.baby_strategy._calculate_kama(
                    window_data['close'], 10, 0.666, 0.0645
                ).iloc[-1]
                if window_data['close'].iloc[-1] > kama + (self._calculate_atr(window_data, 14).iloc[-1] * 1.5):
                    self.last_signal = None
                    return Signal.BUY
            
            return None
            
        except Exception as e:
            return None
    
    def _calculate_atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        high = data['high']
        low = data['low']
        close = data['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period, min_periods=1).mean()
        return atr


class MultiTimeframeEMACloudWrapper(Strategy):
    """Wrapper for MultiTimeframeEMACloudStrategy"""
    
    def __init__(self, name: str = "MultiTimeframeEMACloud"):
        super().__init__(name)
        self.baby_strategy = MultiTimeframeEMACloudStrategy()
        self.last_signal = None
    
    def _calculate_indicators(self):
        """Calculate indicators"""
        pass
    
    def on_bar(self, idx: int, bar: pd.Series):
        """Generate signals on each bar"""
        if idx < 220:  # Need sufficient data for 200-period EMA
            return None
        
        window_data = self.data.iloc[:idx+1]
        
        try:
            baby_signals = self.baby_strategy.generate_signals(window_data, "BTCUSDT")
            
            if baby_signals:
                direction = Signal.BUY if baby_signals[0].direction == "BUY" else Signal.SELL
                self.last_signal = direction
                return direction
            
            return None
            
        except Exception as e:
            return None


class MovingAverageSlopeMomentumWrapper(Strategy):
    """Wrapper for MovingAverageSlopeMomentumStrategy"""
    
    def __init__(self, name: str = "MovingAverageSlopeMomentum"):
        super().__init__(name)
        self.baby_strategy = MovingAverageSlopeMomentumStrategy()
        self.last_signal = None
    
    def _calculate_indicators(self):
        """Calculate indicators"""
        pass
    
    def on_bar(self, idx: int, bar: pd.Series):
        """Generate signals on each bar"""
        if idx < 50:  # Need sufficient data for 34-period EMA
            return None
        
        window_data = self.data.iloc[:idx+1]
        
        try:
            baby_signals = self.baby_strategy.generate_signals(window_data, "BTCUSDT")
            
            if baby_signals:
                direction = Signal.BUY if baby_signals[0].direction == "BUY" else Signal.SELL
                self.last_signal = direction
                return direction
            
            # Exit logic based on slope crossing
            if self.last_signal == Signal.BUY:
                close = window_data['close']
                ema5 = close.ewm(span=5, adjust=False).mean()
                ema13 = close.ewm(span=13, adjust=False).mean()
                if ema5.iloc[-1] < ema13.iloc[-1]:
                    self.last_signal = None
                    return Signal.SELL
            elif self.last_signal == Signal.SELL:
                close = window_data['close']
                ema5 = close.ewm(span=5, adjust=False).mean()
                ema13 = close.ewm(span=13, adjust=False).mean()
                if ema5.iloc[-1] > ema13.iloc[-1]:
                    self.last_signal = None
                    return Signal.BUY
            
            return None
            
        except Exception as e:
            return None
