"""
VolSpikeCapitulationLongRehabStrategy — short-term reversal (CRYPTO rehab)
==========================================================================
Targets regimes where **single-bar volatility spikes** flush weak hands; enters **LONG**
after a **bearish spike bar** closes in the lower third of its range (capitulation-style),
with an ATR stop. Rehabilitation candidate for low PF chop — must pass walk-forward.

TESTING_PROTOCOL: Layer 1 backtest + Layer 5 Monte Carlo before promotion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "LINKUSDT",
    "SUIUSDT",
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


class VolSpikeCapitulationLongRehabStrategy:
    """Big range vs ATR + bearish close near lows → contrarian long."""

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.atr_period = self.params.get("atr_period", 14)
        self.spike_atr_mult = self.params.get("spike_atr_mult", 2.2)
        self.lower_third = self.params.get("lower_third", 0.33)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 1.8)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.2)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        need = self.atr_period + 5
        if len(data) < need:
            return []

        high = data["high"].astype(float)
        low = data["low"].astype(float)
        close = data["close"].astype(float)
        open_ = data["open"].astype(float)

        tr = pd.concat(
            [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(self.atr_period, min_periods=1).mean()

        h, lo, c, o = float(high.iloc[-1]), float(low.iloc[-1]), float(close.iloc[-1]), float(open_.iloc[-1])
        atr_v = float(atr.iloc[-1])
        if atr_v <= 0:
            return []

        rng = h - lo
        if rng < self.spike_atr_mult * atr_v:
            return []
        # Bearish bar
        if c >= o:
            return []
        pos_in_range = (c - lo) / rng if rng > 0 else 1.0
        if pos_in_range > self.lower_third:
            return []

        entry = c
        sl = entry - self.sl_atr_mult * atr_v
        tp = entry + self.tp_atr_mult * atr_v
        excess = (rng / atr_v) - self.spike_atr_mult
        conf = min(0.88, 0.52 + max(0.0, excess) * 0.12)

        return [
            Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(conf, 3),
                entry_price=round(entry, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason="vol_spike_capitulation_long_rehab bearish spike lower-third close",
            )
        ]
