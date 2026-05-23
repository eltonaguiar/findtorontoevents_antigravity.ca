"""
WilliamsRVolumeStrategy - Baby Strat
===================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: Williams %R extreme levels with volume confirmation
- Exit when: TP/SL hit or Williams %R normalizes
- Risk management: ATR-based SL/TP

Unique Value Proposition:
Combines Williams %R oscillator with volume spikes for stronger reversal signals.
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


class WilliamsRVolumeStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.williams_period = self.params.get('williams_period', 14)
        self.oversold = self.params.get('oversold', -80)
        self.overbought = self.params.get('overbought', -20)
        self.volume_period = self.params.get('volume_period', 20)
        self.volume_mult = self.params.get('volume_mult', 1.8)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.williams_period, self.volume_period, self.atr_period) + 10:
            return []

        # Calculate indicators
        williams_r = self._calculate_williams_r(data, self.williams_period)
        volume_ma = data['volume'].rolling(window=self.volume_period).mean()
        atr = self._calculate_atr(data, self.atr_period)

        current_price = data['close'].iloc[-1]
        current_williams = williams_r.iloc[-1]
        current_volume = data['volume'].iloc[-1]
        current_volume_ma = volume_ma.iloc[-1]
        current_atr = atr.iloc[-1]

        signals = []

        # Buy signal: oversold Williams %R + high volume
        if current_williams < self.oversold and current_volume > current_volume_ma * self.volume_mult:
            confidence = (self.oversold - current_williams) / (self.oversold - (-100))
            confidence = confidence * (current_volume / current_volume_ma)
            confidence = min(confidence, 0.95)

            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Williams %R oversold ({current_williams:.1f}) + volume spike ({current_volume/current_volume_ma:.1f}x)"
            ))

        # Sell signal: overbought Williams %R + high volume
        elif current_williams > self.overbought and current_volume > current_volume_ma * self.volume_mult:
            confidence = (current_williams - self.overbought) / (0 - self.overbought)
            confidence = confidence * (current_volume / current_volume_ma)
            confidence = min(confidence, 0.95)

            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = current_price + (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Williams %R overbought ({current_williams:.1f}) + volume spike ({current_volume/current_volume_ma:.1f}x)"
            ))

        return signals

    def _calculate_williams_r(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        high = data['high'].rolling(window=period).max()
        low = data['low'].rolling(window=period).min()
        close = data['close']
        williams_r = -100 * ((high - close) / (high - low))
        return williams_r

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
