"""
EhlersFisherTransform - Baby Strat
====================================

Created by: Claude Opus
Date: 2026-02-27

Strategy Logic:
- Uses John Ehlers' Fisher Transform to convert price into a Gaussian normal distribution
- Clear turning points when Fisher crosses its signal line at extremes
- Entry on Fisher reversal from extreme + RSI confirmation

Unique Value Proposition:
The Fisher Transform creates sharp, unambiguous turning points — much cleaner than
RSI or Stochastic. Ehlers' DSP-based approach is peer-reviewed and used in institutional
quant systems. No existing baby strat uses Fisher Transform.
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


class EhlersFisherTransformStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.fisher_period = self.params.get('fisher_period', 10)
        self.extreme_threshold = self.params.get('extreme_threshold', 1.5)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_oversold = self.params.get('rsi_oversold', 35)
        self.rsi_overbought = self.params.get('rsi_overbought', 65)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.fisher_period, self.rsi_period, self.atr_period) + 15
        if len(data) < min_bars:
            return []

        close = data['close']
        high = data['high']
        low = data['low']

        # Fisher Transform
        fisher, fisher_signal = self._fisher_transform(high, low, self.fisher_period)
        rsi = self._rsi(close, self.rsi_period)
        atr = self._atr(data, self.atr_period)

        current_price = close.iloc[-1]
        current_atr = atr.iloc[-1]
        f_now = fisher.iloc[-1]
        f_prev = fisher.iloc[-2]
        fs_now = fisher_signal.iloc[-1]
        fs_prev = fisher_signal.iloc[-2]
        rsi_now = rsi.iloc[-1]

        if any(np.isnan(v) for v in [current_atr, f_now, f_prev, fs_now, fs_prev, rsi_now]):
            return []
        if current_atr <= 0:
            return []

        signals = []

        # Bullish: Fisher crosses above signal from extreme low
        if f_prev < fs_prev and f_now > fs_now and f_now < -self.extreme_threshold:
            if rsi_now < self.rsi_oversold:
                confidence = min(0.6 + abs(f_now) / 5, 0.95)
                tp = current_price + current_atr * self.tp_atr_mult
                sl = current_price - current_atr * self.sl_atr_mult
                signals.append(Signal(
                    symbol=symbol, direction="BUY", confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2), stop_loss=round(sl, 2),
                    reason=f"Fisher bullish reversal ({f_now:.2f}), RSI={rsi_now:.0f}"
                ))

        # Bearish: Fisher crosses below signal from extreme high
        elif f_prev > fs_prev and f_now < fs_now and f_now > self.extreme_threshold:
            if rsi_now > self.rsi_overbought:
                confidence = min(0.6 + abs(f_now) / 5, 0.95)
                tp = current_price - current_atr * self.tp_atr_mult
                sl = current_price + current_atr * self.sl_atr_mult
                signals.append(Signal(
                    symbol=symbol, direction="SELL", confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2), stop_loss=round(sl, 2),
                    reason=f"Fisher bearish reversal ({f_now:.2f}), RSI={rsi_now:.0f}"
                ))

        return signals

    def _fisher_transform(self, high: pd.Series, low: pd.Series, period: int):
        hl2 = (high + low) / 2
        highest = hl2.rolling(period).max()
        lowest = hl2.rolling(period).min()

        raw = 2 * ((hl2 - lowest) / (highest - lowest + 1e-10)) - 1
        raw_vals = np.clip(raw.values, -0.999, 0.999)
        raw_vals = np.nan_to_num(raw_vals, nan=0.0)

        # Smooth with EMA-like recursion (vectorized via loop on numpy)
        value = np.zeros(len(raw_vals))
        for i in range(1, len(value)):
            value[i] = 0.5 * raw_vals[i] + 0.5 * value[i-1]

        # Fisher transform
        value = np.clip(value, -0.999, 0.999)
        fisher_raw = 0.5 * np.log((1 + value) / (1 - value))
        fisher = np.zeros(len(fisher_raw))
        for i in range(1, len(fisher)):
            fisher[i] = fisher_raw[i] + 0.5 * fisher[i-1]

        fisher_s = pd.Series(fisher, index=high.index)
        fisher_signal = fisher_s.shift(1)
        return fisher_s, fisher_signal

    def _rsi(self, prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / (loss + 1e-10)
        return 100 - (100 / (1 + rs))

    def _atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift())
        tr3 = abs(data['low'] - data['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean()
