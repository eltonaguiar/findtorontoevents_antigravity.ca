"""
SuperTrendATRStrategy - Baby Strat
=================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: SuperTrend trend change
- Exit when: TP/SL hit or trend reversal
- Risk management: ATR-based SL/TP

Unique Value Proposition:
Uses SuperTrend for trend following with ATR for dynamic position sizing and risk management.
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


class SuperTrendATRStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.atr_period = self.params.get('atr_period', 10)
        self.multiplier = self.params.get('multiplier', 3.0)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 4.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 2.0)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.atr_period + 10:
            return []

        # Calculate SuperTrend
        supertrend, direction = self._calculate_supertrend(data, self.atr_period, self.multiplier)
        atr = self._calculate_atr(data, self.atr_period)

        current_price = data['close'].iloc[-1]
        prev_price = data['close'].iloc[-2]
        current_supertrend = supertrend.iloc[-1]
        prev_supertrend = supertrend.iloc[-2]
        current_direction = direction.iloc[-1]
        prev_direction = direction.iloc[-2]
        current_atr = atr.iloc[-1]

        signals = []

        # Bullish trend change
        if prev_direction < 0 and current_direction > 0:
            confidence = min(abs(current_price - prev_supertrend) / current_atr, 0.95)

            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_supertrend - (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"SuperTrend bullish trend change from {prev_supertrend:.2f} to {current_supertrend:.2f}"
            ))

        # Bearish trend change
        elif prev_direction > 0 and current_direction < 0:
            confidence = min(abs(current_price - prev_supertrend) / current_atr, 0.95)

            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = current_supertrend + (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"SuperTrend bearish trend change from {prev_supertrend:.2f} to {current_supertrend:.2f}"
            ))

        return signals

    def _calculate_supertrend(self, data: pd.DataFrame, atr_period: int = 10, multiplier: float = 3.0):
        high = data['high']
        low = data['low']
        close = data['close']

        # Calculate ATR
        atr = self._calculate_atr(data, atr_period)

        # Calculate basic upper and lower bands
        hl2 = (high + low) / 2
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)

        # Initialize SuperTrend
        supertrend = pd.Series(index=data.index, dtype=float)
        direction = pd.Series(index=data.index, dtype=int)

        for i in range(len(data)):
            if i == 0:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = 1
            else:
                if close.iloc[i-1] <= supertrend.iloc[i-1]:
                    # Bearish trend
                    supertrend.iloc[i] = max(upper_band.iloc[i], supertrend.iloc[i-1])
                    direction.iloc[i] = -1 if close.iloc[i] <= supertrend.iloc[i] else 1
                else:
                    # Bullish trend
                    supertrend.iloc[i] = min(lower_band.iloc[i], supertrend.iloc[i-1])
                    direction.iloc[i] = 1 if close.iloc[i] >= supertrend.iloc[i] else -1

        return supertrend, direction

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
