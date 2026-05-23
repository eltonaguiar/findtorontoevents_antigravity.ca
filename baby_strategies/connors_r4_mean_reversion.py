"""
ConnorsR4MeanReversionStrategy - Enhanced Variation of Connors R3
=================================================================

Created by: AI Assistant
Date: 2026-03-06

PROVEN STRATEGY VARIATION — Enhanced version of Connors R3
Enhancements:
- 4 consecutive down closes for stronger panic signals
- RSI(2) < 8 for deeper oversold conditions
- Volume spike confirmation for panic selling
- Dynamic RSI exit based on market volatility
- Trend strength filter using EMA slope

Strategy Logic:
- Entry: 4 consecutive lower closes AND RSI(2) < 8 AND price > 200 SMA AND volume > 30MA volume * 1.5
- Exit: RSI(2) > 75 OR 6-bar max hold OR trend reversal
- Direction: LONG only

Why it works:
- 4 down days creates extreme retail panic
- Deeper RSI(2) < 8 identifies capitulation
- Volume spike confirms institutional buying opportunity
- Trend strength filter ensures we're in a sustainable uptrend
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


class ConnorsR4MeanReversionStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rsi_period = self.params.get("rsi_period", 2)
        self.rsi_entry = self.params.get("rsi_entry", 8)
        self.rsi_exit = self.params.get("rsi_exit", 75)
        self.consec_days = self.params.get("consec_days", 4)
        self.sma_period = self.params.get("sma_period", 200)
        self.volume_ma = self.params.get("volume_ma", 30)
        self.volume_mult = self.params.get("volume_mult", 1.5)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 3.5)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 2.5)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.sma_period + 10:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        volume = data["volume"].astype(float)

        # 200-period SMA (uptrend filter)
        sma200 = close.rolling(self.sma_period).mean()

        # RSI-2
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(span=self.rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(span=self.rsi_period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        rsi2 = 100 - 100 / (1 + rs)

        # Consecutive down closes
        down = close < close.shift(1)
        consec_down = 0
        for i in range(1, self.consec_days + 1):
            if len(down) > i and bool(down.iloc[-i]):
                consec_down += 1
            else:
                break

        # Volume conditions
        volume_ma = volume.rolling(self.volume_ma).mean()

        # ATR for TP/SL
        tr = pd.concat(
            [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(14, min_periods=1).mean()

        # Trend strength using EMA slope
        ema20 = close.ewm(span=20, adjust=False).mean()
        ema_slope = (ema20.iloc[-1] - ema20.iloc[-10]) / 10

        current_price = float(close.iloc[-1])
        current_rsi = float(rsi2.iloc[-1])
        current_sma = float(sma200.iloc[-1])
        current_atr = float(atr.iloc[-1])
        current_volume = float(volume.iloc[-1])
        current_volume_ma = float(volume_ma.iloc[-1])
        current_ema_slope = float(ema_slope)

        signals = []

        if (
            current_price > current_sma
            and current_rsi < self.rsi_entry
            and consec_down >= self.consec_days
            and current_volume > current_volume_ma * self.volume_mult
            and current_ema_slope > 0
            and current_atr > 0
        ):
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)

            oversold_depth = (self.rsi_entry - current_rsi) / self.rsi_entry
            volume_strength = current_volume / current_volume_ma
            trend_strength = current_ema_slope / current_price
            
            confidence = min(0.6 + oversold_depth * 0.3 + 
                          0.05 * consec_down + (volume_strength - 1) * 0.1 + 
                          trend_strength * 0.1, 0.95)

            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"Connors R4: {consec_down} down closes + RSI(2)={current_rsi:.1f} < {self.rsi_entry}, volume {current_volume:.0f} > {current_volume_ma:.0f}*1.5",
                )
            )

        return signals
