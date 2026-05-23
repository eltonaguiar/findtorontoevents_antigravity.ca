"""
crossasset_risk_triad_rotation_v1 - Baby Strat
==============================================

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


class CrossassetRiskTriadRotationStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get("lookback", 120)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.0)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.2)

    def generate_signals(
        self,
        data: pd.DataFrame,
        spx_data: Optional[pd.DataFrame] = None,
        dxy_data: Optional[pd.DataFrame] = None,
        vix_data: Optional[pd.DataFrame] = None,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        if len(data) < self.lookback + self.atr_period:
            return []
        if spx_data is None or dxy_data is None or vix_data is None:
            return []

        btc = pd.to_numeric(data["close"], errors="coerce")
        ts = pd.to_datetime(data["timestamp"], utc=True)
        spx = pd.to_numeric(spx_data.set_index(pd.to_datetime(spx_data["timestamp"], utc=True))["close"], errors="coerce").reindex(ts, method="ffill")
        dxy = pd.to_numeric(dxy_data.set_index(pd.to_datetime(dxy_data["timestamp"], utc=True))["close"], errors="coerce").reindex(ts, method="ffill")
        vix = pd.to_numeric(vix_data.set_index(pd.to_datetime(vix_data["timestamp"], utc=True))["close"], errors="coerce").reindex(ts, method="ffill")
        atr = self._atr(data, self.atr_period)
        if atr.isna().iloc[-1] or atr.iloc[-1] <= 0:
            return []

        rb = btc.pct_change(8)
        rs = spx.pct_change(8)
        rd = dxy.pct_change(8)
        rv = vix.pct_change(8)

        risk_score = (1.2 * rs - 1.0 * rd - 0.8 * rv).fillna(0.0)
        basis = risk_score.rolling(self.lookback, min_periods=30).mean()
        sigma = risk_score.rolling(self.lookback, min_periods=30).std().replace(0, np.nan)
        z = ((risk_score - basis) / sigma).fillna(0.0)
        btc_mom = rb.fillna(0.0)

        px = float(btc.iloc[-1])
        a = float(atr.iloc[-1])
        z_last = float(z.iloc[-1])
        mom = float(btc_mom.iloc[-1])

        signals: List[Signal] = []
        if z_last > 1.2 and mom > 0.003:
            conf = min(0.95, 0.55 + 0.14 * z_last + 0.08 * min(2.0, mom * 100))
            signals.append(Signal(symbol, "BUY", round(float(conf), 3), round(px, 4), round(px + a * self.tp_atr_mult, 4), round(px - a * self.sl_atr_mult, 4),
                                  f"Risk-on triad z={z_last:.2f}, BTC momentum {mom:.3f}"))
        elif z_last < -1.2 and mom < -0.003:
            conf = min(0.95, 0.55 + 0.14 * abs(z_last) + 0.08 * min(2.0, abs(mom) * 100))
            signals.append(Signal(symbol, "SELL", round(float(conf), 3), round(px, 4), round(px - a * self.tp_atr_mult, 4), round(px + a * self.sl_atr_mult, 4),
                                  f"Risk-off triad z={z_last:.2f}, BTC momentum {mom:.3f}"))
        return signals

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        high = pd.to_numeric(data["high"], errors="coerce")
        low = pd.to_numeric(data["low"], errors="coerce")
        close = pd.to_numeric(data["close"], errors="coerce")
        tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=period).mean()
