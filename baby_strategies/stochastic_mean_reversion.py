"""
StochasticMeanReversionStrategy - Baby Strat
===========================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: Stochastic oversold/overbought with divergence
- Exit when: TP/SL hit or stochastic normalization
- Risk management: ATR-based SL/TP

Unique Value Proposition:
Uses Stochastic oscillator for mean reversion with price divergence confirmation.
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


class StochasticMeanReversionStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.k_period = self.params.get('k_period', 14)
        self.d_period = self.params.get('d_period', 3)
        self.oversold = self.params.get('oversold', 20)
        self.overbought = self.params.get('overbought', 80)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.k_period + self.d_period + self.atr_period + 10:
            return []

        # Calculate indicators
        k, d = self._calculate_stochastic(data, self.k_period, self.d_period)
        atr = self._calculate_atr(data, self.atr_period)

        current_price = data['close'].iloc[-1]
        current_k = k.iloc[-1]
        current_d = d.iloc[-1]
        prev_k = k.iloc[-2]
        prev_d = d.iloc[-2]
        current_atr = atr.iloc[-1]

        signals = []

        # Buy signal: oversold + K crosses above D
        if (current_k < self.oversold and prev_k <= prev_d and current_k > current_d):
            confidence = (self.oversold - current_k) / self.oversold
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
                reason=f"Stochastic oversold crossover K:{current_k:.1f} D:{current_d:.1f}"
            ))

        # Sell signal: overbought + K crosses below D
        elif (current_k > self.overbought and prev_k >= prev_d and current_k < current_d):
            confidence = (current_k - self.overbought) / (100 - self.overbought)
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
                reason=f"Stochastic overbought crossover K:{current_k:.1f} D:{current_d:.1f}"
            ))

        return signals

    def _calculate_stochastic(self, data: pd.DataFrame, k_period: int = 14, d_period: int = 3):
        high = data['high']
        low = data['low']
        close = data['close']

        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d = k.rolling(window=d_period).mean()

        return k, d

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
