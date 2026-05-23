"""
StochPullbackTrendLongRehabStrategy — trend pullback entries (CRYPTO rehab)
===========================================================================
**Uptrend** (close > SMA200) + Stochastic **K** rising from oversold (<30) with K crossing
above D — classic pullback long. Targets symbols with low standalone WR when traded
counter-trend; here we require trend filter.

Not survivor-validated — register for bundle / forward tests only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd


SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "DOTUSDT",
    "LINKUSDT",
    "NEARUSDT",
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


def _stoch_k_d(
    high: pd.Series, low: pd.Series, close: pd.Series, k_p: int, d_p: int
) -> Tuple[pd.Series, pd.Series]:
    lowest = low.rolling(k_p, min_periods=1).min()
    highest = high.rolling(k_p, min_periods=1).max()
    num = close - lowest
    den = (highest - lowest).replace(0, pd.NA)
    k = (num / den) * 100
    d = k.rolling(d_p, min_periods=1).mean()
    return k, d


class StochPullbackTrendLongRehabStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.sma_period = self.params.get("sma_period", 200)
        self.k_period = self.params.get("k_period", 14)
        self.d_period = self.params.get("d_period", 3)
        self.oversold = self.params.get("oversold", 30)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.5)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.5)
        self.atr_period = self.params.get("atr_period", 14)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.sma_period + self.k_period + 10:
            return []

        high = data["high"].astype(float)
        low = data["low"].astype(float)
        close = data["close"].astype(float)
        sma = close.rolling(self.sma_period, min_periods=1).mean()
        k, d = _stoch_k_d(high, low, close, self.k_period, self.d_period)

        tr = pd.concat(
            [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(self.atr_period, min_periods=1).mean()

        c = float(close.iloc[-1])
        pk, pd_ = float(k.iloc[-1]), float(d.iloc[-1])
        pk1, pd1 = float(k.iloc[-2]), float(d.iloc[-2])
        sma_v = float(sma.iloc[-1])
        atr_v = float(atr.iloc[-1])

        if atr_v <= 0 or c <= sma_v:
            return []
        # Pullback: was oversold recently, now K crosses up through D
        if pk1 > self.oversold:
            return []
        if not (pk > pd_ and pk1 < pd1):
            return []

        tp = c + self.tp_atr_mult * atr_v
        sl = c - self.sl_atr_mult * atr_v
        conf = min(0.5 + (self.oversold - min(pk1, pk)) / 100.0, 0.9)

        return [
            Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(conf, 3),
                entry_price=round(c, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason="stoch_pullback_trend_long_rehab sma200+stoch_oversold_cross",
            )
        ]
