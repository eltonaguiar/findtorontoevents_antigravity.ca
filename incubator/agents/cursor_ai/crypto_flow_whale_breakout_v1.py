"""
crypto_flow_whale_breakout_v1 - Baby Strat
==========================================

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


class CryptoFlowWhaleBreakoutStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get("lookback", 80)
        self.range_window = self.params.get("range_window", 24)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.2)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.4)

    def generate_signals(
        self,
        data: pd.DataFrame,
        flow_data: Optional[pd.Series] = None,
        whale_inflow: Optional[pd.Series] = None,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        if len(data) < self.lookback + self.atr_period:
            return []
        if flow_data is None or whale_inflow is None:
            return []

        ts = pd.to_datetime(data["timestamp"], utc=True)
        close = pd.to_numeric(data["close"], errors="coerce")
        high = pd.to_numeric(data["high"], errors="coerce")
        low = pd.to_numeric(data["low"], errors="coerce")
        flow = pd.to_numeric(flow_data, errors="coerce").reindex(ts, method="ffill").fillna(0.0)
        whale = pd.to_numeric(whale_inflow, errors="coerce").reindex(ts, method="ffill").fillna(0.0)
        atr = self._atr(data, self.atr_period)
        if atr.isna().iloc[-1] or atr.iloc[-1] <= 0:
            return []

        upper = high.shift(1).rolling(self.range_window, min_periods=10).max()
        lower = low.shift(1).rolling(self.range_window, min_periods=10).min()
        ema_fast = close.ewm(span=15, adjust=False).mean()
        ema_slow = close.ewm(span=50, adjust=False).mean()
        trend = (ema_fast - ema_slow) / close.replace(0, pd.NA)
        flow_bias = flow.rolling(10, min_periods=5).mean() - flow.rolling(30, min_periods=10).mean()
        whale_bias = whale.rolling(8, min_periods=4).mean() - whale.rolling(24, min_periods=8).mean()

        px = float(close.iloc[-1])
        a = float(atr.iloc[-1])
        ub = float(upper.iloc[-1]) if pd.notna(upper.iloc[-1]) else px
        lb = float(lower.iloc[-1]) if pd.notna(lower.iloc[-1]) else px
        fb = float(flow_bias.iloc[-1])
        wb = float(whale_bias.iloc[-1])

        signals: List[Signal] = []
        if px > ub and fb > 0 and wb > 0 and float(trend.iloc[-1]) > 0:
            conf = min(0.95, 0.57 + min(0.2, (px / max(ub, 1e-9) - 1.0) * 80) + 0.08)
            signals.append(Signal(symbol, "BUY", round(float(conf), 3), round(px, 4), round(px + a * self.tp_atr_mult, 4), round(px - a * self.sl_atr_mult, 4),
                                  f"Breakout above {ub:.2f} with positive flow/whale bias"))
        elif px < lb and fb < 0 and wb < 0 and float(trend.iloc[-1]) < 0:
            conf = min(0.95, 0.57 + min(0.2, (1.0 - px / max(lb, 1e-9)) * 80) + 0.08)
            signals.append(Signal(symbol, "SELL", round(float(conf), 3), round(px, 4), round(px - a * self.tp_atr_mult, 4), round(px + a * self.sl_atr_mult, 4),
                                  f"Breakdown below {lb:.2f} with negative flow/whale bias"))
        return signals

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        high = pd.to_numeric(data["high"], errors="coerce")
        low = pd.to_numeric(data["low"], errors="coerce")
        close = pd.to_numeric(data["close"], errors="coerce")
        tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=period).mean()
