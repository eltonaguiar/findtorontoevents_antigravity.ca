"""
crypto_governance_social_regime_v1 - Baby Strat
===============================================

Created by: cursor_ai
Date: 2026-02-27
"""

import numpy as np
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


class CryptoGovernanceSocialRegimeStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get("lookback", 90)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.0)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.25)

    def generate_signals(
        self,
        data: pd.DataFrame,
        gov_data: Optional[pd.Series] = None,
        social_data: Optional[pd.Series] = None,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        if len(data) < self.lookback + self.atr_period:
            return []
        if gov_data is None or social_data is None:
            return []

        ts = pd.to_datetime(data["timestamp"], utc=True)
        gov = pd.to_numeric(gov_data, errors="coerce").reindex(ts, method="ffill").fillna(0.0)
        social = pd.to_numeric(social_data, errors="coerce").reindex(ts, method="ffill").fillna(0.0)
        close = pd.to_numeric(data["close"], errors="coerce")
        atr = self._atr(data, self.atr_period)
        if atr.isna().iloc[-1] or atr.iloc[-1] <= 0:
            return []

        gov_z = self._z(gov, self.lookback)
        social_z = self._z(social, self.lookback)
        spread = (gov_z - social_z).fillna(0.0)

        trend = close.ewm(span=20, adjust=False).mean() - close.ewm(span=60, adjust=False).mean()
        trend = (trend / close.replace(0, np.nan)).fillna(0.0)

        s = float(spread.iloc[-1])
        t = float(trend.iloc[-1])
        px = float(close.iloc[-1])
        a = float(atr.iloc[-1])

        signals: List[Signal] = []
        # Governance rising faster than social often means "real participation > noise".
        if s > 1.25 and t > 0.001:
            conf = min(0.95, 0.56 + 0.1 * s + 3.0 * t)
            signals.append(Signal(symbol, "BUY", round(float(conf), 3), round(px, 4), round(px + a * self.tp_atr_mult, 4), round(px - a * self.sl_atr_mult, 4),
                                  f"Gov-social spread {s:.2f} and trend {t:.4f}"))
        elif s < -1.25 and t < -0.001:
            conf = min(0.95, 0.56 + 0.1 * abs(s) + 3.0 * abs(t))
            signals.append(Signal(symbol, "SELL", round(float(conf), 3), round(px, 4), round(px - a * self.tp_atr_mult, 4), round(px + a * self.sl_atr_mult, 4),
                                  f"Gov-social spread {s:.2f} and trend {t:.4f}"))
        return signals

    @staticmethod
    def _z(series: pd.Series, window: int) -> pd.Series:
        mu = series.rolling(window, min_periods=max(20, window // 3)).mean()
        sd = series.rolling(window, min_periods=max(20, window // 3)).std().replace(0, np.nan)
        return ((series - mu) / sd).fillna(0.0)

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        high = pd.to_numeric(data["high"], errors="coerce")
        low = pd.to_numeric(data["low"], errors="coerce")
        close = pd.to_numeric(data["close"], errors="coerce")
        tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=period).mean()
