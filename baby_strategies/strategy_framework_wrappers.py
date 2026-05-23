"""
Strategy Framework Wrappers
===========================

Wraps the new strategy variations to work with the backtest framework's Strategy base class.
"""

from backtest_framework import Strategy, Signal as BTSignal, PositionSide
import pandas as pd
import numpy as np

# Import new strategy variations
from keltner_rsi_confluence import KeltnerRSIConfluenceStrategy
from connors_r4_mean_reversion import ConnorsR4MeanReversionStrategy
from supertrend_multi_timeframe import SuperTrendMultiTimeframeStrategy
from vol_scaled_keltner import VolScaledKeltnerStrategy


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]

class KeltnerRSIConfluenceWrapper(Strategy):
    """Wrapper for KeltnerRSIConfluenceStrategy"""
    
    def __init__(self, name: str = "KeltnerRSIConfluence"):
        super().__init__(name)
        self.baby_strategy = KeltnerRSIConfluenceStrategy()
        self.last_signal = None
    
    def _calculate_indicators(self):
        """Calculate indicators"""
        # Indicators are calculated within the baby strategy
        pass
    
    def on_bar(self, idx: int, bar: pd.Series) -> BTSignal:
        """Generate signals on each bar"""
        # Get historical data up to current index
        if idx < 200:  # Need at least 200 bars for 200MA
            return None
        
        window_data = self.data.iloc[:idx+1]
        
        try:
            baby_signals = self.baby_strategy.generate_signals(window_data, "BTCUSDT")
            
            if baby_signals:
                self.last_signal = baby_signals[0].direction
                return BTSignal.BUY if self.last_signal == "BUY" else BTSignal.SELL
            else:
                # If in position, check for exit conditions
                if self.last_signal == "BUY":
                    # Exit if price reaches middle band or RSI > 50
                    ema20 = window_data['close'].ewm(span=20, adjust=False).mean()
                    rsi14 = self._calculate_rsi(window_data['close'], 14)
                    
                    if (window_data['close'].iloc[-1] >= ema20.iloc[-1] or 
                        rsi14.iloc[-1] > 50):
                        self.last_signal = None
                        return BTSignal.SELL
            
            return None
            
        except Exception as e:
            return None
    
    def _calculate_rsi(self, close: pd.Series, period: int) -> pd.Series:
        """Calculate RSI indicator"""
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        rsi = 100 - 100 / (1 + rs)
        return rsi


class ConnorsR4MeanReversionWrapper(Strategy):
    """Wrapper for ConnorsR4MeanReversionStrategy"""
    
    def __init__(self, name: str = "ConnorsR4MeanReversion"):
        super().__init__(name)
        self.baby_strategy = ConnorsR4MeanReversionStrategy()
        self.last_signal = None
    
    def _calculate_indicators(self):
        """Calculate indicators"""
        pass
    
    def on_bar(self, idx: int, bar: pd.Series) -> BTSignal:
        """Generate signals on each bar"""
        if idx < 200:  # Need at least 200 bars for 200MA
            return None
        
        window_data = self.data.iloc[:idx+1]
        
        try:
            baby_signals = self.baby_strategy.generate_signals(window_data, "BTCUSDT")
            
            if baby_signals:
                self.last_signal = baby_signals[0].direction
                return BTSignal.BUY
            
            else:
                # Exit if RSI(2) > 75 or 6 bars after entry
                if self.last_signal == "BUY":
                    rsi2 = self._calculate_rsi(window_data['close'], 2)
                    if rsi2.iloc[-1] > 75:
                        self.last_signal = None
                        return BTSignal.SELL
            
            return None
            
        except Exception as e:
            return None
    
    def _calculate_rsi(self, close: pd.Series, period: int) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        rsi = 100 - 100 / (1 + rs)
        return rsi


class SuperTrendMultiTimeframeWrapper(Strategy):
    """Wrapper for SuperTrendMultiTimeframeStrategy"""
    
    def __init__(self, name: str = "SuperTrendMultiTimeframe"):
        super().__init__(name)
        self.baby_strategy = SuperTrendMultiTimeframeStrategy()
        self.last_signal = None
    
    def _calculate_indicators(self):
        """Calculate indicators"""
        pass
    
    def on_bar(self, idx: int, bar: pd.Series) -> BTSignal:
        """Generate signals on each bar"""
        if idx < 400:  # Need enough data for multi-timeframe analysis
            return None
        
        window_data = self.data.iloc[:idx+1]
        
        try:
            baby_signals = self.baby_strategy.generate_signals(window_data, "BTCUSDT")
            
            if baby_signals:
                new_signal = BTSignal.BUY if baby_signals[0].direction == "BUY" else BTSignal.SELL
                self.last_signal = new_signal
                return new_signal
            
            return None
            
        except Exception as e:
            return None


class VolScaledKeltnerWrapper(Strategy):
    """Wrapper for VolScaledKeltnerStrategy"""
    
    def __init__(self, name: str = "VolScaledKeltner"):
        super().__init__(name)
        self.baby_strategy = VolScaledKeltnerStrategy()
        self.last_signal = None
    
    def _calculate_indicators(self):
        """Calculate indicators"""
        pass
    
    def on_bar(self, idx: int, bar: pd.Series) -> BTSignal:
        """Generate signals on each bar"""
        if idx < 200:  # Need at least 200 bars for 200EMA
            return None
        
        window_data = self.data.iloc[:idx+1]
        
        try:
            baby_signals = self.baby_strategy.generate_signals(window_data, "BTCUSDT")
            
            if baby_signals:
                self.last_signal = baby_signals[0].direction
                return BTSignal.BUY
            
            else:
                # Exit if price closes below EMA(20)
                if self.last_signal == "BUY":
                    ema20 = window_data['close'].ewm(span=20, adjust=False).mean()
                    if window_data['close'].iloc[-1] < ema20.iloc[-1]:
                        self.last_signal = None
                        return BTSignal.SELL
            
            return None
            
        except Exception as e:
            return None
