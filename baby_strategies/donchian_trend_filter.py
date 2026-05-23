"""
DonchianTrendFilter - Baby Strat
===================================

Created by: Claude Opus
Date: 2026-02-27

Strategy Logic:
- Uses Donchian Channel breakout (turtle trading) with an ATR volatility filter
- Only enters breakouts when ATR is expanding (confirms real momentum, not just noise)
- Trailing stop based on opposite Donchian band

Unique Value Proposition:
The original Turtle Trading system is the most famous trend-following strategy in history.
This modernizes it with an ATR expansion filter — the turtles' biggest weakness was
false breakouts in low-vol environments. The ATR filter eliminates those. Existing
codex_gpt5 has a Donchian+ADX version; this uses ATR expansion which is more responsive.
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


class DonchianTrendFilterStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.dc_period = self.params.get('dc_period', 20)
        self.atr_period = self.params.get('atr_period', 14)
        self.atr_expansion_mult = self.params.get('atr_expansion_mult', 1.2)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 3.5)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.dc_period, self.atr_period * 2) + 10
        if len(data) < min_bars:
            return []

        high = data['high']
        low = data['low']
        close = data['close']

        # Donchian Channel
        dc_upper = high.rolling(self.dc_period).max()
        dc_lower = low.rolling(self.dc_period).min()
        dc_mid = (dc_upper + dc_lower) / 2

        # ATR and its moving average (for expansion detection)
        atr = self._atr(data, self.atr_period)
        atr_ma = atr.rolling(self.atr_period).mean()

        current_price = close.iloc[-1]
        prev_price = close.iloc[-2]
        current_atr = atr.iloc[-1]
        current_atr_ma = atr_ma.iloc[-1]
        current_dc_upper = dc_upper.iloc[-2]  # Use previous bar's channel (avoid look-ahead)
        current_dc_lower = dc_lower.iloc[-2]

        if any(np.isnan(v) for v in [current_atr, current_atr_ma, current_dc_upper, current_dc_lower]):
            return []
        if current_atr <= 0:
            return []

        # ATR expansion: current ATR > its average * multiplier
        atr_expanding = current_atr > current_atr_ma * self.atr_expansion_mult

        signals = []

        # Bullish breakout: price breaks above upper Donchian + ATR expanding
        if current_price > current_dc_upper and prev_price <= current_dc_upper and atr_expanding:
            confidence = min(0.6 + (current_atr / current_atr_ma - 1) * 0.5, 0.95)
            tp = current_price + current_atr * self.tp_atr_mult
            sl = current_dc_lower  # Opposite band as stop
            if current_price - sl > current_atr * self.sl_atr_mult * 3:
                sl = current_price - current_atr * self.sl_atr_mult  # Tighten if too wide
            signals.append(Signal(
                symbol=symbol, direction="BUY", confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2), stop_loss=round(sl, 2),
                reason=f"Donchian breakout UP, ATR expanding {current_atr:.2f}>{current_atr_ma:.2f}"
            ))

        # Bearish breakout: price breaks below lower Donchian + ATR expanding
        elif current_price < current_dc_lower and prev_price >= current_dc_lower and atr_expanding:
            confidence = min(0.6 + (current_atr / current_atr_ma - 1) * 0.5, 0.95)
            tp = current_price - current_atr * self.tp_atr_mult
            sl = current_dc_upper
            if sl - current_price > current_atr * self.sl_atr_mult * 3:
                sl = current_price + current_atr * self.sl_atr_mult
            signals.append(Signal(
                symbol=symbol, direction="SELL", confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2), stop_loss=round(sl, 2),
                reason=f"Donchian breakout DOWN, ATR expanding {current_atr:.2f}>{current_atr_ma:.2f}"
            ))

        return signals

    def _atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift())
        tr3 = abs(data['low'] - data['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean()
