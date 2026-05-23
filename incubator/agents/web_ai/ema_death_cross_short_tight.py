"""
EMA Death Cross Short — TIGHT MUTATION
========================================
DNA Mutation A: Tighter TP/SL
- TP: 2.5 -> 1.75 ATR (-30%)
- SL: 1.5 -> 1.2 ATR (-20%)
Parent: ema_death_cross_short.py (PF 1.52, 57.1% WR, 49 trades)
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


class EMADeathCrossShortTightStrategy:
    """Tight mutation: TP=1.75x ATR, SL=1.2x ATR."""

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema_fast = self.params.get('ema_fast', 9)
        self.ema_slow = self.params.get('ema_slow', 21)
        self.adx_period = self.params.get('adx_period', 14)
        self.adx_threshold = self.params.get('adx_threshold', 20)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr = self.params.get('tp_atr', 1.75)  # MUTATED: 2.5 -> 1.75
        self.sl_atr = self.params.get('sl_atr', 1.2)    # MUTATED: 1.5 -> 1.2
        self.cooldown = self.params.get('cooldown', 4)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = max(self.ema_slow, self.adx_period * 3, self.atr_period) + 20
        if len(data) < min_len:
            return []

        ema_fast = data['close'].ewm(span=self.ema_fast, adjust=False).mean()
        ema_slow = data['close'].ewm(span=self.ema_slow, adjust=False).mean()
        adx = self._calculate_adx(data)
        atr = self._calculate_atr(data)

        signals: List[Signal] = []
        last_signal_bar = -self.cooldown

        for i in range(min_len, len(data)):
            if i - last_signal_bar < self.cooldown:
                continue

            cur_adx = adx.iloc[i]
            cur_atr = atr.iloc[i]
            cur_close = data['close'].iloc[i]
            prev_ema_fast = ema_fast.iloc[i - 1]
            prev_ema_slow = ema_slow.iloc[i - 1]
            cur_ema_fast = ema_fast.iloc[i]
            cur_ema_slow = ema_slow.iloc[i]

            if any(pd.isna(v) for v in [cur_adx, cur_atr, cur_ema_fast, cur_ema_slow,
                                         prev_ema_fast, prev_ema_slow]):
                continue
            if cur_atr <= 0:
                continue

            cross_down = prev_ema_fast >= prev_ema_slow and cur_ema_fast < cur_ema_slow

            if cross_down and cur_adx > self.adx_threshold:
                conf = min(0.60 + 0.01 * (cur_adx - self.adx_threshold), 0.90)
                signals.append(Signal(
                    symbol=symbol, direction="SELL", confidence=round(conf, 2),
                    entry_price=cur_close,
                    take_profit=round(cur_close - cur_atr * self.tp_atr, 2),
                    stop_loss=round(cur_close + cur_atr * self.sl_atr, 2),
                    reason=f"DEATH_CROSS_TIGHT EMA9<EMA21 ADX={cur_adx:.1f}"
                ))
                last_signal_bar = i

        return signals

    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def _calculate_adx(self, data: pd.DataFrame) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        n = self.adx_period
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        atr_smooth = tr.ewm(alpha=1/n, min_periods=n, adjust=False).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1/n, min_periods=n, adjust=False).mean() / atr_smooth
        minus_di = 100 * minus_dm.ewm(alpha=1/n, min_periods=n, adjust=False).mean() / atr_smooth
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1e-10)
        return dx.ewm(alpha=1/n, min_periods=n, adjust=False).mean()
