"""
VWAPDeviationRSIStrategy - Baby Strat
====================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: Price deviates from VWAP with RSI confirmation
- Exit when: TP/SL hit or returns to VWAP
- Risk management: ATR-based SL/TP

Unique Value Proposition:
Uses VWAP as fair value anchor with RSI timing for mean reversion trades.
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


class VWAPDeviationRSIStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.vwap_lookback = self.params.get('vwap_lookback', 100)
        self.deviation_threshold = self.params.get('deviation_threshold', 0.02)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_oversold = self.params.get('rsi_oversold', 35)
        self.rsi_overbought = self.params.get('rsi_overbought', 65)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.vwap_lookback, self.rsi_period, self.atr_period) + 10:
            return []

        # Calculate indicators
        vwap = self._calculate_vwap(data, self.vwap_lookback)
        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        atr = self._calculate_atr(data, self.atr_period)

        current_price = data['close'].iloc[-1]
        current_vwap = vwap.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_atr = atr.iloc[-1]

        deviation = (current_price - current_vwap) / current_vwap

        signals = []

        # Buy signal: below VWAP + oversold RSI
        if deviation < -self.deviation_threshold and current_rsi < self.rsi_oversold:
            confidence = (self.deviation_threshold + deviation) / self.deviation_threshold
            confidence = confidence * ((self.rsi_oversold - current_rsi) / self.rsi_oversold)
            confidence = min(confidence, 0.95)

            tp = current_vwap + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"VWAP deviation ({deviation:.3f}) + RSI oversold ({current_rsi:.1f})"
            ))

        # Sell signal: above VWAP + overbought RSI
        elif deviation > self.deviation_threshold and current_rsi > self.rsi_overbought:
            confidence = (deviation - self.deviation_threshold) / self.deviation_threshold
            confidence = confidence * ((current_rsi - self.rsi_overbought) / (100 - self.rsi_overbought))
            confidence = min(confidence, 0.95)

            tp = current_vwap - (current_atr * self.tp_atr_mult)
            sl = current_price + (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"VWAP deviation ({deviation:.3f}) + RSI overbought ({current_rsi:.1f})"
            ))

        return signals

    def _calculate_vwap(self, data: pd.DataFrame, lookback: int) -> pd.Series:
        typical_price = (data['high'] + data['low'] + data['close']) / 3
        vwap = (typical_price * data['volume']).rolling(window=lookback).sum() / data['volume'].rolling(window=lookback).sum()
        return vwap

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
