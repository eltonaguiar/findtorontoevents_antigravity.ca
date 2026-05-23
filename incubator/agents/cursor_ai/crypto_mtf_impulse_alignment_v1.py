"""
crypto_mtf_impulse_alignment_v1 - Baby Strat
============================================

Created by: cursor_ai
Date: 2026-02-27
"""

import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class CryptoMtfImpulseAlignmentStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get("lookback", 80)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.0)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.3)

    def generate_signals(
        self,
        data: pd.DataFrame,
        data_15m: Optional[pd.DataFrame] = None,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        if len(data) < self.lookback + self.atr_period:
            return []
        if data_15m is None or len(data_15m) < 100:
            return []

        close_1h = pd.to_numeric(data["close"], errors="coerce")
        close_15 = pd.to_numeric(data_15m["close"], errors="coerce")
        atr = self._atr(data, self.atr_period)
        if atr.isna().iloc[-1] or atr.iloc[-1] <= 0:
            return []

        trend_1h = close_1h.ewm(span=20, adjust=False).mean() - close_1h.ewm(span=60, adjust=False).mean()
        trend_1h = (trend_1h / close_1h.replace(0, pd.NA)).fillna(0.0)

        impulse_15 = close_15.pct_change(4).rolling(4, min_periods=2).mean().fillna(0.0)
        accel_15 = impulse_15.diff().fillna(0.0)

        i = float(impulse_15.iloc[-1])
        a15 = float(accel_15.iloc[-1])
        t1 = float(trend_1h.iloc[-1])
        px = float(close_1h.iloc[-1])
        atr_now = float(atr.iloc[-1])

        signals: List[Signal] = []
        if t1 > 0.001 and i > 0.003 and a15 > 0:
            conf = min(0.95, 0.56 + min(0.2, t1 * 200) + min(0.18, i * 35))
            signals.append(Signal(symbol, "BUY", round(float(conf), 3), round(px, 4), round(px + atr_now * self.tp_atr_mult, 4), round(px - atr_now * self.sl_atr_mult, 4),
                                  f"1h trend {t1:.4f}, 15m impulse {i:.4f}, accel {a15:.4f}"))
        elif t1 < -0.001 and i < -0.003 and a15 < 0:
            conf = min(0.95, 0.56 + min(0.2, abs(t1) * 200) + min(0.18, abs(i) * 35))
            signals.append(Signal(symbol, "SELL", round(float(conf), 3), round(px, 4), round(px - atr_now * self.tp_atr_mult, 4), round(px + atr_now * self.sl_atr_mult, 4),
                                  f"1h trend {t1:.4f}, 15m impulse {i:.4f}, accel {a15:.4f}"))
        return signals

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        high = pd.to_numeric(data["high"], errors="coerce")
        low = pd.to_numeric(data["low"], errors="coerce")
        close = pd.to_numeric(data["close"], errors="coerce")
        tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=period).mean()
