"""
crypto_liquidation_flow_exhaustion_v1 - Baby Strat
==================================================

Created by: cursor_ai
Date: 2026-02-27

Strategy Logic:
- Entry when: liquidation spike + aggressive flow exhaustion + short-term momentum turn
- Exit when: ATR-based TP/SL or time-based backtest exit
- Risk management: ATR-normalized stop and target

Unique Value Proposition:
Combines liquidation pressure with flow exhaustion to catch post-cascade reversals.
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


class CryptoLiquidationFlowExhaustionStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get("lookback", 72)
        self.atr_period = self.params.get("atr_period", 14)
        self.liq_z = self.params.get("liq_z", 2.0)
        self.flow_z = self.params.get("flow_z", 1.5)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.3)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.4)

    def generate_signals(
        self,
        data: pd.DataFrame,
        liquidation_data: Optional[pd.DataFrame] = None,
        flow_data: Optional[pd.Series] = None,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        if len(data) < self.lookback + self.atr_period:
            return []
        if liquidation_data is None or liquidation_data.empty or flow_data is None or len(flow_data) < self.lookback:
            return []

        close = pd.to_numeric(data["close"], errors="coerce")
        atr = self._atr(data, self.atr_period)
        if atr.isna().iloc[-1] or atr.iloc[-1] <= 0:
            return []

        liq = liquidation_data.copy()
        liq["timestamp"] = pd.to_datetime(liq["timestamp"], utc=True, errors="coerce")
        liq = liq.dropna(subset=["timestamp", "usd_value"])
        liq["usd_value"] = pd.to_numeric(liq["usd_value"], errors="coerce").fillna(0.0)
        liq_series = liq.set_index("timestamp")["usd_value"].sort_index().reindex(pd.to_datetime(data["timestamp"], utc=True), method="ffill").fillna(0.0)

        flow = pd.to_numeric(flow_data, errors="coerce").fillna(0.0)
        flow = flow.reindex(pd.to_datetime(data["timestamp"], utc=True), method="ffill").fillna(0.0)

        liq_mu = liq_series.rolling(self.lookback, min_periods=20).mean()
        liq_sd = liq_series.rolling(self.lookback, min_periods=20).std().replace(0, np.nan)
        flow_mu = flow.rolling(self.lookback, min_periods=20).mean()
        flow_sd = flow.rolling(self.lookback, min_periods=20).std().replace(0, np.nan)

        liq_score = (liq_series - liq_mu) / liq_sd
        flow_score = (flow - flow_mu) / flow_sd
        mom_fast = close.pct_change(3).fillna(0.0)
        mom_slow = close.pct_change(12).fillna(0.0)

        px = float(close.iloc[-1])
        a = float(atr.iloc[-1])
        signals: List[Signal] = []

        bullish = liq_score.iloc[-1] > self.liq_z and flow_score.iloc[-1] < -self.flow_z and mom_fast.iloc[-1] > mom_fast.iloc[-2] and mom_slow.iloc[-1] > -0.01
        bearish = liq_score.iloc[-1] > self.liq_z and flow_score.iloc[-1] > self.flow_z and mom_fast.iloc[-1] < mom_fast.iloc[-2] and mom_slow.iloc[-1] < 0.01

        if bullish:
            conf = float(min(0.95, 0.55 + 0.08 * max(0.0, liq_score.iloc[-1]) + 0.06 * max(0.0, -flow_score.iloc[-1])))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(conf, 3),
                    entry_price=round(px, 4),
                    take_profit=round(px + a * self.tp_atr_mult, 4),
                    stop_loss=round(px - a * self.sl_atr_mult, 4),
                    reason=f"Liq z={liq_score.iloc[-1]:.2f}, flow z={flow_score.iloc[-1]:.2f}, momentum turn up",
                )
            )
        elif bearish:
            conf = float(min(0.95, 0.55 + 0.08 * max(0.0, liq_score.iloc[-1]) + 0.06 * max(0.0, flow_score.iloc[-1])))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(conf, 3),
                    entry_price=round(px, 4),
                    take_profit=round(px - a * self.tp_atr_mult, 4),
                    stop_loss=round(px + a * self.sl_atr_mult, 4),
                    reason=f"Liq z={liq_score.iloc[-1]:.2f}, flow z={flow_score.iloc[-1]:.2f}, momentum turn down",
                )
            )
        return signals

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        high = pd.to_numeric(data["high"], errors="coerce")
        low = pd.to_numeric(data["low"], errors="coerce")
        close = pd.to_numeric(data["close"], errors="coerce")
        tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=period).mean()
