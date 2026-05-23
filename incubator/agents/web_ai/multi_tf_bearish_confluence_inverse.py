"""
Multi-Timeframe Bearish Confluence — INVERSE MUTATION
======================================================
DNA Mutation C: Flip direction (SELL -> BUY)
- Original: SHORT when 1h downtrend + 4h RSI overbought
- Inverse: LONG when 1h uptrend + 4h RSI oversold (buy the dip in uptrend)
Parent: multi_tf_bearish_confluence.py (PF 3.39, 62.3% WR, 61 trades)
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional
import requests
import time


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT",
    "ALGOUSDT", "SUIUSDT", "FETUSDT", "AVAXUSDT", "DOTUSDT",
    "LINKUSDT", "MATICUSDT"
]


class MultiTFBearishConfluenceInverseStrategy:
    """Inverse mutation: BUY when uptrend + RSI oversold (buy the dip)."""

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema_fast = self.params.get('ema_fast', 8)
        self.ema_slow = self.params.get('ema_slow', 21)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_os = self.params.get('rsi_oversold', 40)  # MUTATED: mirror of 60
        self.atr_period = self.params.get('atr_period', 14)
        self.atr_sma_period = self.params.get('atr_sma_period', 20)
        self.tp_atr = self.params.get('tp_atr', 2.0)
        self.sl_atr = self.params.get('sl_atr', 1.0)
        self.cooldown = self.params.get('cooldown', 6)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = max(self.ema_slow, self.rsi_period, self.atr_period, self.atr_sma_period) + 20
        if len(data) < min_len:
            return []

        ema_fast = data['close'].ewm(span=self.ema_fast, adjust=False).mean()
        ema_slow = data['close'].ewm(span=self.ema_slow, adjust=False).mean()
        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        atr = self._calculate_atr(data)
        atr_sma = atr.rolling(self.atr_sma_period).mean()

        signals: List[Signal] = []
        last_signal_bar = -self.cooldown

        for i in range(min_len, len(data)):
            if i - last_signal_bar < self.cooldown:
                continue

            cur_rsi = rsi.iloc[i]
            cur_atr = atr.iloc[i]
            cur_atr_sma = atr_sma.iloc[i]
            cur_close = data['close'].iloc[i]

            if any(pd.isna(v) for v in [cur_rsi, cur_atr, cur_atr_sma]):
                continue
            if cur_atr <= 0:
                continue

            # INVERSE: uptrend (EMA fast > EMA slow)
            trend_up = ema_fast.iloc[i] > ema_slow.iloc[i]
            # INVERSE: RSI oversold (dip in uptrend)
            rsi_os = cur_rsi < self.rsi_os
            atr_expanding = cur_atr > cur_atr_sma

            if trend_up and rsi_os and atr_expanding:
                conf = min(0.60 + 0.01 * (self.rsi_os - cur_rsi), 0.90)
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",  # INVERSE: was SELL
                    confidence=round(conf, 2),
                    entry_price=cur_close,
                    take_profit=round(cur_close + cur_atr * self.tp_atr, 2),  # INVERSE
                    stop_loss=round(cur_close - cur_atr * self.sl_atr, 2),    # INVERSE
                    reason=f"MTF_BULL_INV EMA8>21 RSI={cur_rsi:.1f} ATR_exp={cur_atr/cur_atr_sma:.2f}"
                ))
                last_signal_bar = i

        return signals

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()
