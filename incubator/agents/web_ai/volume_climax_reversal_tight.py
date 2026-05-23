"""
Volume Climax Reversal — TIGHT MUTATION
========================================
DNA Mutation A: Tighter TP/SL
- TP: 2.5 -> 1.75 ATR (-30%)
- SL: 1.5 -> 1.2 ATR (-20%)
Parent: volume_climax_reversal.py (PF 26.02, 94.7% WR, 19 trades)
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


class VolumeClimaxReversalTightStrategy:
    """Tight mutation: TP=1.75x ATR, SL=1.2x ATR."""

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.vol_sma_period = self.params.get('vol_sma_period', 20)
        self.vol_multiplier = self.params.get('vol_multiplier', 3.0)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr = self.params.get('tp_atr', 1.75)  # MUTATED: 2.5 -> 1.75
        self.sl_atr = self.params.get('sl_atr', 1.2)    # MUTATED: 1.5 -> 1.2
        self.cooldown = self.params.get('cooldown', 4)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = max(self.vol_sma_period, self.rsi_period, self.atr_period) + 20
        if len(data) < min_len:
            return []

        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        atr = self._calculate_atr(data)
        vol_sma = data['volume'].rolling(self.vol_sma_period).mean()

        signals: List[Signal] = []
        last_signal_bar = -self.cooldown

        for i in range(min_len, len(data)):
            if i - last_signal_bar < self.cooldown:
                continue

            cur_rsi = rsi.iloc[i]
            cur_atr = atr.iloc[i]
            cur_close = data['close'].iloc[i]
            cur_open = data['open'].iloc[i]
            cur_vol = data['volume'].iloc[i]
            cur_vol_sma = vol_sma.iloc[i]

            if any(pd.isna(v) for v in [cur_rsi, cur_atr, cur_vol_sma]):
                continue
            if cur_atr <= 0 or cur_vol_sma <= 0:
                continue

            vol_ratio = cur_vol / cur_vol_sma
            if vol_ratio < self.vol_multiplier:
                continue

            if cur_close < cur_open and cur_rsi > 50:
                conf = min(0.60 + 0.05 * (vol_ratio - self.vol_multiplier), 0.92)
                signals.append(Signal(
                    symbol=symbol, direction="SELL", confidence=round(conf, 2),
                    entry_price=cur_close,
                    take_profit=round(cur_close - cur_atr * self.tp_atr, 2),
                    stop_loss=round(cur_close + cur_atr * self.sl_atr, 2),
                    reason=f"VOL_CLIMAX_SHORT_TIGHT vol={vol_ratio:.1f}x RSI={cur_rsi:.1f}"
                ))
                last_signal_bar = i
            elif cur_close > cur_open and cur_rsi < 50:
                conf = min(0.55 + 0.05 * (vol_ratio - self.vol_multiplier), 0.88)
                signals.append(Signal(
                    symbol=symbol, direction="BUY", confidence=round(conf, 2),
                    entry_price=cur_close,
                    take_profit=round(cur_close + cur_atr * self.tp_atr, 2),
                    stop_loss=round(cur_close - cur_atr * self.sl_atr, 2),
                    reason=f"VOL_CLIMAX_LONG_TIGHT vol={vol_ratio:.1f}x RSI={cur_rsi:.1f}"
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
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()
