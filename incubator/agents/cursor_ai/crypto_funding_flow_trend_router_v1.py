"""
crypto_funding_flow_trend_router_v1 - Baby Strat
================================================

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


class CryptoFundingFlowTrendRouterStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get("lookback", 80)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.4)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        funding_rate: Optional[float] = None,
        flow_data: Optional[pd.Series] = None,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        if len(data) < self.lookback + self.atr_period:
            return []
        if funding_rate is None or flow_data is None:
            return []

        close = pd.to_numeric(data["close"], errors="coerce")
        ema_fast = close.ewm(span=21, adjust=False).mean()
        ema_slow = close.ewm(span=55, adjust=False).mean()
        trend = (ema_fast - ema_slow) / ema_slow.replace(0, np.nan)
        atr = self._atr(data, self.atr_period)
        if atr.isna().iloc[-1] or atr.iloc[-1] <= 0:
            return []

        ts = pd.to_datetime(data["timestamp"], utc=True)
        flow = pd.to_numeric(flow_data, errors="coerce").reindex(ts, method="ffill").fillna(0.0)
        flow_m = flow.rolling(10, min_periods=5).mean()
        flow_s = flow.rolling(30, min_periods=10).mean()
        flow_delta = (flow_m - flow_s).fillna(0.0)

        px = float(close.iloc[-1])
        a = float(atr.iloc[-1])
        tr = float(trend.iloc[-1]) if pd.notna(trend.iloc[-1]) else 0.0
        fd = float(flow_delta.iloc[-1])
        fr = float(funding_rate)

        long_setup = tr > 0 and ((fr < -0.002 and fd > 0) or (fr > 0 and fd > abs(flow_delta.iloc[-20:]).median()))
        short_setup = tr < 0 and ((fr > 0.002 and fd < 0) or (fr < 0 and fd < -abs(flow_delta.iloc[-20:]).median()))

        signals: List[Signal] = []
        if long_setup:
            conf = min(0.95, 0.55 + min(0.2, abs(fr) * 12) + min(0.2, abs(fd) / (abs(flow).rolling(40, min_periods=15).std().iloc[-1] + 1e-9)))
            signals.append(
                Signal(symbol, "BUY", round(float(conf), 3), round(px, 4), round(px + a * self.tp_atr_mult, 4), round(px - a * self.sl_atr_mult, 4),
                       f"Trend up {tr:.4f}, funding {fr:.4f}, flow delta {fd:.2f}")
            )
        elif short_setup:
            conf = min(0.95, 0.55 + min(0.2, abs(fr) * 12) + min(0.2, abs(fd) / (abs(flow).rolling(40, min_periods=15).std().iloc[-1] + 1e-9)))
            signals.append(
                Signal(symbol, "SELL", round(float(conf), 3), round(px, 4), round(px - a * self.tp_atr_mult, 4), round(px + a * self.sl_atr_mult, 4),
                       f"Trend down {tr:.4f}, funding {fr:.4f}, flow delta {fd:.2f}")
            )
        return signals

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        high = pd.to_numeric(data["high"], errors="coerce")
        low = pd.to_numeric(data["low"], errors="coerce")
        close = pd.to_numeric(data["close"], errors="coerce")
        tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=period).mean()
