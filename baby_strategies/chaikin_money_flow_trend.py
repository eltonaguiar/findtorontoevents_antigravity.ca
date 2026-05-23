"""
ChaikinMoneyFlowTrend - Baby Strat
=====================================

Created by: Claude Opus
Date: 2026-02-27

Strategy Logic:
- Uses Chaikin Money Flow (CMF) to measure institutional buying/selling pressure
- Entry when CMF crosses above/below zero with EMA trend alignment
- Confirmation: CMF must sustain direction for N bars (no flickering)

Unique Value Proposition:
CMF measures the accumulation/distribution over a window (unlike OBV which is cumulative).
It captures WHERE the close is within the bar range weighted by volume — institutional
footprint. The sustained-cross filter eliminates the noise of single-bar CMF flips.
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


class ChaikinMoneyFlowTrendStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.cmf_period = self.params.get('cmf_period', 20)
        self.sustain_bars = self.params.get('sustain_bars', 3)
        self.ema_period = self.params.get('ema_period', 50)
        self.cmf_threshold = self.params.get('cmf_threshold', 0.05)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.cmf_period, self.ema_period, self.atr_period) + self.sustain_bars + 10
        if len(data) < min_bars:
            return []

        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']

        # Money Flow Multiplier: ((close - low) - (high - close)) / (high - low)
        mf_mult = ((close - low) - (high - close)) / (high - low + 1e-10)
        mf_volume = mf_mult * volume

        # CMF = sum(mf_volume, period) / sum(volume, period)
        cmf = mf_volume.rolling(self.cmf_period).sum() / (volume.rolling(self.cmf_period).sum() + 1e-10)

        ema = close.ewm(span=self.ema_period).mean()
        atr = self._atr(data, self.atr_period)

        current_price = close.iloc[-1]
        current_atr = atr.iloc[-1]
        current_cmf = cmf.iloc[-1]
        current_ema = ema.iloc[-1]

        if np.isnan(current_atr) or current_atr <= 0 or np.isnan(current_cmf):
            return []

        signals = []

        # Check sustained CMF above threshold
        recent_cmf = cmf.iloc[-self.sustain_bars:]
        all_positive = (recent_cmf > self.cmf_threshold).all()
        all_negative = (recent_cmf < -self.cmf_threshold).all()

        # CMF just crossed above threshold and sustained + price above EMA (uptrend)
        prev_cmf = cmf.iloc[-(self.sustain_bars + 1)]
        if all_positive and prev_cmf <= self.cmf_threshold and current_price > current_ema:
            confidence = min(0.6 + abs(current_cmf) * 2, 0.95)
            tp = current_price + current_atr * self.tp_atr_mult
            sl = current_price - current_atr * self.sl_atr_mult
            signals.append(Signal(
                symbol=symbol, direction="BUY", confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2), stop_loss=round(sl, 2),
                reason=f"CMF sustained positive ({current_cmf:.3f}), above EMA"
            ))

        elif all_negative and prev_cmf >= -self.cmf_threshold and current_price < current_ema:
            confidence = min(0.6 + abs(current_cmf) * 2, 0.95)
            tp = current_price - current_atr * self.tp_atr_mult
            sl = current_price + current_atr * self.sl_atr_mult
            signals.append(Signal(
                symbol=symbol, direction="SELL", confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2), stop_loss=round(sl, 2),
                reason=f"CMF sustained negative ({current_cmf:.3f}), below EMA"
            ))

        return signals

    def _atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift())
        tr3 = abs(data['low'] - data['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean()
