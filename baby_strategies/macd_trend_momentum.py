"""
MACDTrendMomentumStrategy - Baby Strat
======================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: MACD crossover in trend direction
- Exit when: TP/SL hit or MACD divergence
- Risk management: ATR-based SL/TP

Unique Value Proposition:
Combines MACD momentum signals with trend confirmation using EMA slope to avoid counter-trend trades.
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


class MACDTrendMomentumStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.fast_period = self.params.get('fast_period', 12)
        self.slow_period = self.params.get('slow_period', 26)
        self.signal_period = self.params.get('signal_period', 9)
        self.ema_trend = self.params.get('ema_trend', 50)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.slow_period, self.ema_trend, self.atr_period) + 10:
            return []

        # Calculate indicators
        macd, signal_line, histogram = self._calculate_macd(data['close'], self.fast_period, self.slow_period, self.signal_period)
        ema_trend = data['close'].ewm(span=self.ema_trend).mean()
        trend_slope = (ema_trend - ema_trend.shift(1)) / ema_trend.shift(1)
        atr = self._calculate_atr(data, self.atr_period)

        current_price = data['close'].iloc[-1]
        current_macd = macd.iloc[-1]
        current_signal = signal_line.iloc[-1]
        prev_macd = macd.iloc[-2]
        prev_signal = signal_line.iloc[-2]
        current_trend = trend_slope.iloc[-1]
        current_atr = atr.iloc[-1]

        signals = []

        # Bullish MACD crossover with uptrend
        if (prev_macd <= prev_signal and current_macd > current_signal and current_trend > 0):
            confidence = min(abs(current_macd - current_signal) / abs(current_atr), 0.95)
            confidence = confidence * (1 + current_trend * 10)  # Boost confidence in strong trends

            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"MACD bullish crossover in uptrend (slope: {current_trend:.4f})"
            ))

        # Bearish MACD crossover with downtrend
        elif (prev_macd >= prev_signal and current_macd < current_signal and current_trend < 0):
            confidence = min(abs(current_macd - current_signal) / abs(current_atr), 0.95)
            confidence = confidence * (1 + abs(current_trend) * 10)

            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = current_price + (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"MACD bearish crossover in downtrend (slope: {current_trend:.4f})"
            ))

        return signals

    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line
        return macd, signal_line, histogram

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
