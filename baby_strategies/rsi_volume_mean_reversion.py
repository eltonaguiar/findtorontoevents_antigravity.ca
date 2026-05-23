"""
RSIVolumeMeanReversionStrategy - Baby Strat
===========================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: RSI < 30 and volume > volume_ma (oversold with volume confirmation)
- Exit when: TP/SL hit or RSI > 70 for longs
- Risk management: ATR-based SL/TP

Unique Value Proposition:
Combines RSI mean reversion with volume confirmation to avoid false signals in low volume periods.
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
    """Required: Do not modify this class."""
    symbol: str
    direction: str  # "BUY" or "SELL"
    confidence: float  # 0.0 to 1.0
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class RSIVolumeMeanReversionStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rsi_period = self.params.get('rsi_period', 14)
        self.volume_period = self.params.get('volume_period', 20)
        self.oversold = self.params.get('oversold', 30)
        self.overbought = self.params.get('overbought', 70)
        self.volume_mult = self.params.get('volume_mult', 1.2)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.rsi_period, self.volume_period, self.atr_period) + 10:
            return []

        # Calculate indicators
        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        volume_ma = data['volume'].rolling(window=self.volume_period).mean()
        atr = self._calculate_atr(data, self.atr_period)

        current_price = data['close'].iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_volume = data['volume'].iloc[-1]
        current_volume_ma = volume_ma.iloc[-1]
        current_atr = atr.iloc[-1]

        signals = []

        # Buy signal: oversold + high volume
        if current_rsi < self.oversold and current_volume > current_volume_ma * self.volume_mult:
            confidence = (self.oversold - current_rsi) / self.oversold
            confidence = min(confidence * (current_volume / current_volume_ma), 0.95)

            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"RSI oversold ({current_rsi:.1f}) + volume spike ({current_volume/current_volume_ma:.1f}x)"
            ))

        # Sell signal: overbought + high volume
        elif current_rsi > self.overbought and current_volume > current_volume_ma * self.volume_mult:
            confidence = (current_rsi - self.overbought) / (100 - self.overbought)
            confidence = min(confidence * (current_volume / current_volume_ma), 0.95)

            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = current_price + (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"RSI overbought ({current_rsi:.1f}) + volume spike ({current_volume/current_volume_ma:.1f}x)"
            ))

        return signals

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = (-delta.where(delta < 0, 0))
        avg_gains = gains.rolling(window=period, min_periods=1).mean()
        avg_losses = losses.rolling(window=period, min_periods=1).mean()
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        return rsi

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
