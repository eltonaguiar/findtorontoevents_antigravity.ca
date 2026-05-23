"""
crypto_dxy_funding_squeeze_v1 - Baby Strat
==========================================

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


class CryptoDxyFundingSqueezeStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get("lookback", 96)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.25)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.45)

    def generate_signals(
        self,
        data: pd.DataFrame,
        dxy_data: Optional[pd.DataFrame] = None,
        funding_rate: Optional[float] = None,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        if len(data) < self.lookback + self.atr_period:
            return []
        if dxy_data is None or funding_rate is None:
            return []

        btc = pd.to_numeric(data["close"], errors="coerce")
        ts = pd.to_datetime(data["timestamp"], utc=True)
        dxy = pd.to_numeric(dxy_data.set_index(pd.to_datetime(dxy_data["timestamp"], utc=True))["close"], errors="coerce").reindex(ts, method="ffill")
        atr = self._atr(data, self.atr_period)
        if atr.isna().iloc[-1] or atr.iloc[-1] <= 0:
            return []

        rb = btc.pct_change(8).fillna(0.0)
        rd = dxy.pct_change(8).fillna(0.0)
        spread = (rb + rd).fillna(0.0)  # inverse correlation squeeze proxy
        mu = spread.rolling(self.lookback, min_periods=30).mean()
        sd = spread.rolling(self.lookback, min_periods=30).std().replace(0, np.nan)
        z = ((spread - mu) / sd).fillna(0.0)
        trend = (btc.ewm(span=20, adjust=False).mean() - btc.ewm(span=50, adjust=False).mean()) / btc.replace(0, np.nan)
        trend = trend.fillna(0.0)

        fr = float(funding_rate)
        zz = float(z.iloc[-1])
        tr = float(trend.iloc[-1])
        px = float(btc.iloc[-1])
        a = float(atr.iloc[-1])

        signals: List[Signal] = []
        long_setup = zz < -0.65 and ((fr < -0.0008) or tr > 0)
        short_setup = zz > 0.65 and ((fr > 0.0008) or tr < 0)

        if long_setup:
            conf = min(0.95, 0.56 + 0.12 * abs(zz) + min(0.16, abs(fr) * 20))
            signals.append(Signal(symbol, "BUY", round(float(conf), 3), round(px, 4), round(px + a * self.tp_atr_mult, 4), round(px - a * self.sl_atr_mult, 4),
                                  f"DXY/BTC squeeze z={zz:.2f}, negative funding {fr:.4f}"))
        elif short_setup:
            conf = min(0.95, 0.56 + 0.12 * abs(zz) + min(0.16, abs(fr) * 20))
            signals.append(Signal(symbol, "SELL", round(float(conf), 3), round(px, 4), round(px - a * self.tp_atr_mult, 4), round(px + a * self.sl_atr_mult, 4),
                                  f"DXY/BTC squeeze z={zz:.2f}, positive funding {fr:.4f}"))
        return signals

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        high = pd.to_numeric(data["high"], errors="coerce")
        low = pd.to_numeric(data["low"], errors="coerce")
        close = pd.to_numeric(data["close"], errors="coerce")
        tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=period).mean()
