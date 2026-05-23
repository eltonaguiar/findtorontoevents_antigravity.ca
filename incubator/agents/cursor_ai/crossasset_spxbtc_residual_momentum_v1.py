"""
crossasset_spxbtc_residual_momentum_v1 - Baby Strat
===================================================

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


class CrossassetSpxBtcResidualMomentumStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get("lookback", 100)
        self.beta_window = self.params.get("beta_window", 48)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.2)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.4)

    def generate_signals(
        self,
        data: pd.DataFrame,
        spx_data: Optional[pd.DataFrame] = None,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        if len(data) < self.lookback + self.atr_period:
            return []
        if spx_data is None or spx_data.empty:
            return []

        ts = pd.to_datetime(data["timestamp"], utc=True)
        btc = pd.to_numeric(data["close"], errors="coerce")
        btc.index = ts
        spx = pd.to_numeric(spx_data.set_index(pd.to_datetime(spx_data["timestamp"], utc=True))["close"], errors="coerce").reindex(ts, method="ffill")
        atr = self._atr(data, self.atr_period)
        if atr.isna().iloc[-1] or atr.iloc[-1] <= 0:
            return []

        rb = np.log(btc / btc.shift(1)).fillna(0.0)
        rs = np.log(spx / spx.shift(1)).fillna(0.0)

        cov = rb.rolling(self.beta_window, min_periods=20).cov(rs)
        var = rs.rolling(self.beta_window, min_periods=20).var().replace(0, np.nan)
        beta = (cov / var).fillna(0.0).clip(-3, 3)
        residual = rb - beta * rs

        res_mu = residual.rolling(self.lookback, min_periods=30).mean()
        res_sd = residual.rolling(self.lookback, min_periods=30).std().replace(0, np.nan)
        res_z = ((residual - res_mu) / res_sd).fillna(0.0)
        slope = residual.rolling(6, min_periods=3).mean().diff().fillna(0.0)

        px = float(btc.iloc[-1])
        a = float(atr.iloc[-1])
        z = float(res_z.iloc[-1])
        slp = float(slope.iloc[-1])

        signals: List[Signal] = []
        if z > 0.8 and slp > 0:
            conf = min(0.95, 0.58 + 0.13 * z + 0.4 * min(0.5, slp * 1000))
            signals.append(Signal(symbol, "BUY", round(float(conf), 3), round(px, 4), round(px + a * self.tp_atr_mult, 4), round(px - a * self.sl_atr_mult, 4),
                                  f"Positive residual z={z:.2f} with rising slope"))
        elif z < -0.8 and slp < 0:
            conf = min(0.95, 0.58 + 0.13 * abs(z) + 0.4 * min(0.5, abs(slp) * 1000))
            signals.append(Signal(symbol, "SELL", round(float(conf), 3), round(px, 4), round(px - a * self.tp_atr_mult, 4), round(px + a * self.sl_atr_mult, 4),
                                  f"Negative residual z={z:.2f} with falling slope"))
        return signals

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        high = pd.to_numeric(data["high"], errors="coerce")
        low = pd.to_numeric(data["low"], errors="coerce")
        close = pd.to_numeric(data["close"], errors="coerce")
        tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=period).mean()
