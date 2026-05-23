"""
DrawdownRecoveryRSI XRP — Baby Strat
=================================

Created by: web_ai
Date: 2026-03-06

Strategy Logic:
- Entry when: Drawdown from 50-period high > 9.0% AND RSI < 33
- Exit when: TP = 2.3 x ATR, SL = 1.3 x ATR
- Symbol: XRP only
- XRP — moderate vol, news-driven spikes

Unique Value Proposition:
Drawdown-gated RSI recovery tuned for XRP volatility profile.
Only trades oversold AFTER real pain/drawdown — no other strategy gates on % drawdown for XRP.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class DrawdownRecoveryRSIXRPStrategy:
    """Drawdown-gated RSI recovery buys for XRP."""

    TARGET_PAIR = "XRP/USDT"
    TARGET_SYMBOL = "XRPUSDT"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_threshold = self.params.get('rsi_threshold', 33)
        self.dd_lookback = self.params.get('dd_lookback', 50)
        self.dd_threshold = self.params.get('dd_threshold', 9.0)
        self.atr_period = self.params.get('atr_period', 14)
        # R:R widened 2026-03-16: was 2.3, now 3.0 (target R:R >= 2.0; was 1.77, now 2.31)
        self.tp_atr = self.params.get('tp_atr', 3.0)
        self.sl_atr = self.params.get('sl_atr', 1.3)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "XRPUSDT") -> List[Signal]:
        min_len = self.dd_lookback + self.rsi_period + 20
        if len(data) < min_len:
            return []

        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        rolling_high = data['close'].rolling(self.dd_lookback).max()

        current_close = data['close'].iloc[-1]
        current_rsi = rsi.iloc[-1]
        recent_high = rolling_high.iloc[-1]
        drawdown = (current_close / recent_high - 1) * 100 if recent_high > 0 else 0

        atr = self._calculate_atr(data)
        current_atr = atr.iloc[-1]

        if drawdown < -self.dd_threshold and current_rsi < self.rsi_threshold:
            confidence = min((self.rsi_threshold - current_rsi) / self.rsi_threshold * 0.7 + 0.3, 0.92)
            return [Signal(
                symbol=symbol, direction="BUY",
                confidence=round(confidence, 2),
                entry_price=round(current_close, 2),
                take_profit=round(current_close + current_atr * self.tp_atr, 2),
                stop_loss=round(current_close - current_atr * self.sl_atr, 2),
                reason=f"DD={drawdown:.1f}% RSI={current_rsi:.1f}"
            )]
        return []

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()
