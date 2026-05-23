"""
IchimokuCloudBreakoutStrategy - Baby Strat
=========================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: Price breaks cloud boundaries
- Exit when: TP/SL hit or enters opposite cloud
- Risk management: ATR-based SL/TP

Unique Value Proposition:
Uses Ichimoku cloud for support/resistance levels with trend confirmation.
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


class IchimokuCloudBreakoutStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.tenkan_period = self.params.get('tenkan_period', 9)
        self.kijun_period = self.params.get('kijun_period', 26)
        self.senkou_span_b_period = self.params.get('senkou_span_b_period', 52)
        self.chikou_shift = self.params.get('chikou_shift', 26)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 3.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 2.0)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.senkou_span_b_period + self.chikou_shift + 10:
            return []

        # Calculate Ichimoku components
        tenkan_sen = self._calculate_tenkan_sen(data, self.tenkan_period)
        kijun_sen = self._calculate_kijun_sen(data, self.kijun_period)
        senkou_span_a = self._calculate_senkou_span_a(tenkan_sen, kijun_sen)
        senkou_span_b = self._calculate_senkou_span_b(data, self.senkou_span_b_period)
        chikou_span = data['close'].shift(-self.chikou_shift)

        atr = self._calculate_atr(data, self.atr_period)

        current_price = data['close'].iloc[-1]
        prev_price = data['close'].iloc[-2]
        current_span_a = senkou_span_a.iloc[-1]
        current_span_b = senkou_span_b.iloc[-1]
        prev_span_a = senkou_span_a.iloc[-2]
        prev_span_b = senkou_span_b.iloc[-2]
        current_atr = atr.iloc[-1]

        # Cloud boundaries
        cloud_top = max(current_span_a, current_span_b)
        cloud_bottom = min(current_span_a, current_span_b)

        signals = []

        # Bullish breakout above cloud
        if prev_price <= cloud_top and current_price > cloud_top and current_price > current_span_a:
            confidence = (current_price - cloud_top) / current_atr
            confidence = min(confidence, 0.95)

            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = cloud_top - (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Ichimoku cloud breakout above {cloud_top:.2f}"
            ))

        # Bearish breakout below cloud
        elif prev_price >= cloud_bottom and current_price < cloud_bottom and current_price < current_span_a:
            confidence = (cloud_bottom - current_price) / current_atr
            confidence = min(confidence, 0.95)

            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = cloud_bottom + (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Ichimoku cloud breakout below {cloud_bottom:.2f}"
            ))

        return signals

    def _calculate_tenkan_sen(self, data: pd.DataFrame, period: int) -> pd.Series:
        high = data['high'].rolling(window=period).max()
        low = data['low'].rolling(window=period).min()
        return (high + low) / 2

    def _calculate_kijun_sen(self, data: pd.DataFrame, period: int) -> pd.Series:
        high = data['high'].rolling(window=period).max()
        low = data['low'].rolling(window=period).min()
        return (high + low) / 2

    def _calculate_senkou_span_a(self, tenkan_sen: pd.Series, kijun_sen: pd.Series) -> pd.Series:
        return ((tenkan_sen + kijun_sen) / 2).shift(26)

    def _calculate_senkou_span_b(self, data: pd.DataFrame, period: int) -> pd.Series:
        high = data['high'].rolling(window=period).max()
        low = data['low'].rolling(window=period).min()
        return ((high + low) / 2).shift(26)

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
