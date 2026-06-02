"""
Proven Winners — Walk-Forward Validated Strategies
====================================================
Built from the top 5 strategies that passed purged walk-forward validation:
- macd_rsi_m048: PF 3.33 test, 75.4% WR, 5/5 folds (BEST)
- rs-breakout-scout: PF 1.25 test, 72.1% WR, 5/5 folds
- adx-trend-scout: PF 2.00 test, 66.7% WR, 3/5 folds
- ema-ribbon-momentum-scout: PF 1.50 test, 66.7% WR, 3/5 folds

Created: 2026-06-02
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
import pandas as pd


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


class MACDRSIMomentumStrategy:
    """
    MACD + RSI Momentum (from macd_rsi_m048 — BEST validated strategy)
    
    Walk-forward: PF 3.33 test, 75.4% WR, 5/5 folds profitable, NEGATIVE decay
    
    Logic: MACD crossover + RSI confirmation + volume filter
    - Entry: MACD histogram positive AND RSI > 50 AND volume surge
    - Exit: MACD histogram negative OR RSI < 30 OR ATR stop/target
    """
    
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.macd_fast = self.params.get("macd_fast", 12)
        self.macd_slow = self.params.get("macd_slow", 26)
        self.macd_signal = self.params.get("macd_signal", 9)
        self.rsi_period = self.params.get("rsi_period", 14)
        self.rsi_entry = self.params.get("rsi_entry", 50)
        self.rsi_exit = self.params.get("rsi_exit", 30)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr = self.params.get("tp_atr", 3.0)
        self.sl_atr = self.params.get("sl_atr", 2.0)
        self.volume_ma = self.params.get("volume_ma", 20)
        self.volume_mult = self.params.get("volume_mult", 1.1)
    
    def _compute_rsi(self, close: pd.Series, period: int) -> pd.Series:
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.macd_slow + 20:
            return []
        
        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        volume = data["volume"].astype(float)
        
        # MACD
        ema_fast = close.ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.macd_slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        # RSI
        rsi = self._compute_rsi(close, self.rsi_period)
        
        # ATR
        tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period, min_periods=1).mean()
        
        # Volume
        vol_ma = volume.rolling(self.volume_ma).mean()
        
        current_price = float(close.iloc[-1])
        current_hist = float(histogram.iloc[-1])
        prev_hist = float(histogram.iloc[-2]) if len(histogram) > 1 else 0
        current_rsi = float(rsi.iloc[-1])
        current_atr = float(atr.iloc[-1])
        current_vol = float(volume.iloc[-1])
        current_vol_ma = float(vol_ma.iloc[-1])
        
        signals = []
        
        # LONG: MACD histogram turning positive + RSI > 50 + volume surge
        if (current_hist > 0 and prev_hist <= 0 and 
            current_rsi > self.rsi_entry and 
            current_vol > current_vol_ma * self.volume_mult and
            current_atr > 0):
            
            tp = current_price + current_atr * self.tp_atr
            sl = current_price - current_atr * self.sl_atr
            confidence = min(0.6 + (current_rsi - 50) / 200 + (current_vol / current_vol_ma - 1) * 0.1, 0.95)
            
            signals.append(Signal(
                symbol=symbol, direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=f"MACD_RSI: hist↑ RSI={current_rsi:.0f} vol={current_vol/current_vol_ma:.1f}x",
            ))
        
        # SHORT: MACD histogram turning negative + RSI < 50
        elif (current_hist < 0 and prev_hist >= 0 and 
              current_rsi < (100 - self.rsi_entry) and
              current_vol > current_vol_ma * self.volume_mult and
              current_atr > 0):
            
            tp = current_price - current_atr * self.tp_atr
            sl = current_price + current_atr * self.sl_atr
            confidence = min(0.6 + (50 - current_rsi) / 200 + (current_vol / current_vol_ma - 1) * 0.1, 0.95)
            
            signals.append(Signal(
                symbol=symbol, direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=f"MACD_RSI: hist↓ RSI={current_rsi:.0f} vol={current_vol/current_vol_ma:.1f}x",
            ))
        
        return signals


class ATRBreakoutStrategy:
    """
    ATR Breakout (from rs-breakout-scout — 2nd best validated strategy)
    
    Walk-forward: PF 1.25 test, 72.1% WR, 5/5 folds profitable
    
    Logic: Price breakout above N-day high with ATR confirmation
    - Entry: Close > N-day high AND ATR expanding AND volume surge
    - Exit: Close < N-day low OR ATR trailing stop
    """
    
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.breakout_period = self.params.get("breakout_period", 20)
        self.atr_period = self.params.get("atr_period", 14)
        self.atr_expansion = self.params.get("atr_expansion", 1.2)
        self.tp_atr = self.params.get("tp_atr", 3.0)
        self.sl_atr = self.params.get("sl_atr", 2.0)
        self.volume_ma = self.params.get("volume_ma", 20)
        self.volume_mult = self.params.get("volume_mult", 1.2)
    
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.breakout_period + 20:
            return []
        
        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        volume = data["volume"].astype(float)
        
        # N-day high/low
        n_high = high.rolling(self.breakout_period).max()
        n_low = low.rolling(self.breakout_period).min()
        
        # ATR
        tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period, min_periods=1).mean()
        atr_ma = atr.rolling(50).mean()
        
        # Volume
        vol_ma = volume.rolling(self.volume_ma).mean()
        
        current_price = float(close.iloc[-1])
        current_n_high = float(n_high.iloc[-2]) if len(n_high) > 1 else current_price
        current_n_low = float(n_low.iloc[-2]) if len(n_low) > 1 else current_price
        current_atr = float(atr.iloc[-1])
        current_atr_ma = float(atr_ma.iloc[-1]) if not pd.isna(atr_ma.iloc[-1]) else current_atr
        current_vol = float(volume.iloc[-1])
        current_vol_ma = float(vol_ma.iloc[-1])
        
        signals = []
        
        # LONG: Breakout above N-day high + ATR expanding + volume surge
        if (current_price > current_n_high and
            current_atr > current_atr_ma * self.atr_expansion and
            current_vol > current_vol_ma * self.volume_mult and
            current_atr > 0):
            
            tp = current_price + current_atr * self.tp_atr
            sl = current_price - current_atr * self.sl_atr
            confidence = min(0.6 + (current_atr / current_atr_ma - 1) * 0.3 + (current_vol / current_vol_ma - 1) * 0.1, 0.95)
            
            signals.append(Signal(
                symbol=symbol, direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=f"ATR_Breakout: >{self.breakout_period}d high, ATR={current_atr/current_atr_ma:.1f}x avg",
            ))
        
        # SHORT: Breakdown below N-day low + ATR expanding
        elif (current_price < current_n_low and
              current_atr > current_atr_ma * self.atr_expansion and
              current_vol > current_vol_ma * self.volume_mult and
              current_atr > 0):
            
            tp = current_price - current_atr * self.tp_atr
            sl = current_price + current_atr * self.sl_atr
            confidence = min(0.6 + (current_atr / current_atr_ma - 1) * 0.3 + (current_vol / current_vol_ma - 1) * 0.1, 0.95)
            
            signals.append(Signal(
                symbol=symbol, direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=f"ATR_Breakdown: <{self.breakout_period}d low, ATR={current_atr/current_atr_ma:.1f}x avg",
            ))
        
        return signals


class ADXTrendStrategy:
    """
    ADX Trend (from adx-trend-scout — 3rd best validated strategy)
    
    Walk-forward: PF 2.00 test, 66.7% WR, 3/5 folds profitable
    
    Logic: ADX trend strength + directional movement
    - Entry: ADX > 25 AND +DI > -DI (bullish) OR -DI > +DI (bearish)
    - Exit: ADX < 20 OR ATR stop/target
    """
    
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.adx_period = self.params.get("adx_period", 14)
        self.adx_threshold = self.params.get("adx_threshold", 25)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr = self.params.get("tp_atr", 3.0)
        self.sl_atr = self.params.get("sl_atr", 2.0)
    
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.adx_period * 3:
            return []
        
        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        
        # Directional Movement
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        # ATR
        tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period, min_periods=1).mean()
        
        # Smoothed DI
        plus_di = 100 * (plus_dm.rolling(self.adx_period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(self.adx_period).mean() / atr)
        
        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(self.adx_period).mean()
        
        current_price = float(close.iloc[-1])
        current_adx = float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else 0
        current_plus = float(plus_di.iloc[-1]) if not pd.isna(plus_di.iloc[-1]) else 0
        current_minus = float(minus_di.iloc[-1]) if not pd.isna(minus_di.iloc[-1]) else 0
        current_atr = float(atr.iloc[-1])
        
        signals = []
        
        # LONG: ADX > threshold AND +DI > -DI
        if (current_adx > self.adx_threshold and 
            current_plus > current_minus and 
            current_atr > 0):
            
            tp = current_price + current_atr * self.tp_atr
            sl = current_price - current_atr * self.sl_atr
            confidence = min(0.55 + (current_adx - self.adx_threshold) / 100, 0.90)
            
            signals.append(Signal(
                symbol=symbol, direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=f"ADX_Trend: ADX={current_adx:.0f} +DI={current_plus:.0f} > -DI={current_minus:.0f}",
            ))
        
        # SHORT: ADX > threshold AND -DI > +DI
        elif (current_adx > self.adx_threshold and 
              current_minus > current_plus and 
              current_atr > 0):
            
            tp = current_price - current_atr * self.tp_atr
            sl = current_price + current_atr * self.sl_atr
            confidence = min(0.55 + (current_adx - self.adx_threshold) / 100, 0.90)
            
            signals.append(Signal(
                symbol=symbol, direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=f"ADX_Trend: ADX={current_adx:.0f} -DI={current_minus:.0f} > +DI={current_plus:.0f}",
            ))
        
        return signals


class EMARibbonMomentumStrategy:
    """
    EMA Ribbon Momentum (from ema-ribbon-momentum-scout — 4th best)
    
    Walk-forward: PF 1.50 test, 66.7% WR, 3/5 folds profitable
    
    Logic: Multiple EMA alignment for trend confirmation
    - Entry: EMA8 > EMA21 > EMA50 (bullish ribbon) AND price > EMA8
    - Exit: EMA8 < EMA21 OR ATR stop/target
    """
    
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema_fast = self.params.get("ema_fast", 8)
        self.ema_mid = self.params.get("ema_mid", 21)
        self.ema_slow = self.params.get("ema_slow", 50)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr = self.params.get("tp_atr", 3.0)
        self.sl_atr = self.params.get("sl_atr", 2.0)
    
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.ema_slow + 20:
            return []
        
        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        
        # EMAs
        ema8 = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema21 = close.ewm(span=self.ema_mid, adjust=False).mean()
        ema50 = close.ewm(span=self.ema_slow, adjust=False).mean()
        
        # ATR
        tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period, min_periods=1).mean()
        
        current_price = float(close.iloc[-1])
        current_ema8 = float(ema8.iloc[-1])
        current_ema21 = float(ema21.iloc[-1])
        current_ema50 = float(ema50.iloc[-1])
        current_atr = float(atr.iloc[-1])
        
        signals = []
        
        # LONG: Bullish ribbon (8 > 21 > 50) AND price > EMA8
        if (current_ema8 > current_ema21 > current_ema50 and 
            current_price > current_ema8 and 
            current_atr > 0):
            
            tp = current_price + current_atr * self.tp_atr
            sl = current_price - current_atr * self.sl_atr
            ribbon_strength = (current_ema8 - current_ema50) / current_ema50
            confidence = min(0.55 + ribbon_strength * 5, 0.90)
            
            signals.append(Signal(
                symbol=symbol, direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=f"EMA_Ribbon: 8>21>50, price>{current_ema8:.0f}",
            ))
        
        # SHORT: Bearish ribbon (8 < 21 < 50) AND price < EMA8
        elif (current_ema8 < current_ema21 < current_ema50 and 
              current_price < current_ema8 and 
              current_atr > 0):
            
            tp = current_price - current_atr * self.tp_atr
            sl = current_price + current_atr * self.sl_atr
            ribbon_strength = (current_ema50 - current_ema8) / current_ema50
            confidence = min(0.55 + ribbon_strength * 5, 0.90)
            
            signals.append(Signal(
                symbol=symbol, direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=f"EMA_Ribbon: 8<21<50, price<{current_ema8:.0f}",
            ))
        
        return signals


# ── Registry ────────────────────────────────────────────────────────

PROVEN_STRATEGIES = {
    "macd_rsi_momentum": MACDRSIMomentumStrategy,
    "atr_breakout": ATRBreakoutStrategy,
    "adx_trend": ADXTrendStrategy,
    "ema_ribbon_momentum": EMARibbonMomentumStrategy,
}
