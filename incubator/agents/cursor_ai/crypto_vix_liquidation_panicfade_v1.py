"""
crypto_vix_liquidation_panicfade_v1 - Baby Strat
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


class CryptoVixLiquidationPanicfadeStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get("lookback", 100)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.5)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.4)

    def generate_signals(
        self,
        data: pd.DataFrame,
        vix_data: Optional[pd.DataFrame] = None,
        liquidation_data: Optional[pd.DataFrame] = None,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        if len(data) < self.lookback + self.atr_period:
            return []
        if vix_data is None or liquidation_data is None or liquidation_data.empty:
            return []

        btc = pd.to_numeric(data["close"], errors="coerce")
        ts = pd.to_datetime(data["timestamp"], utc=True)
        vix = pd.to_numeric(vix_data.set_index(pd.to_datetime(vix_data["timestamp"], utc=True))["close"], errors="coerce").reindex(ts, method="ffill")
        atr = self._atr(data, self.atr_period)
        if atr.isna().iloc[-1] or atr.iloc[-1] <= 0:
            return []

        liq = liquidation_data.copy()
        liq["timestamp"] = pd.to_datetime(liq["timestamp"], utc=True, errors="coerce")
        liq["usd_value"] = pd.to_numeric(liq["usd_value"], errors="coerce").fillna(0.0)
        liq_series = liq.dropna(subset=["timestamp"]).set_index("timestamp")["usd_value"].sort_index().reindex(ts, method="ffill").fillna(0.0)

        vix_z = self._z(vix, self.lookback)
        liq_z = self._z(liq_series, self.lookback)
        ret3 = btc.pct_change(3).fillna(0.0)
        ret1 = btc.pct_change(1).fillna(0.0)

        px = float(btc.iloc[-1])
        a = float(atr.iloc[-1])
        vz = float(vix_z.iloc[-1])
        lz = float(liq_z.iloc[-1])
        r3 = float(ret3.iloc[-1])
        r1 = float(ret1.iloc[-1])

        signals: List[Signal] = []
        if vz > 0.8 and lz > 0.9 and r3 < -0.006 and r1 > -0.003:
            conf = min(0.95, 0.58 + 0.1 * vz + 0.1 * lz)
            signals.append(Signal(symbol, "BUY", round(float(conf), 3), round(px, 4), round(px + a * self.tp_atr_mult, 4), round(px - a * self.sl_atr_mult, 4),
                                  f"Panic fade: VIX z={vz:.2f}, liq z={lz:.2f}"))
        elif vz < -0.6 and lz < -0.4 and r3 > 0.006 and r1 < 0.003:
            conf = min(0.95, 0.57 + 0.08 * abs(vz) + 0.08 * abs(lz))
            signals.append(Signal(symbol, "SELL", round(float(conf), 3), round(px, 4), round(px - a * self.tp_atr_mult, 4), round(px + a * self.sl_atr_mult, 4),
                                  f"Euphoria fade: VIX z={vz:.2f}, liq z={lz:.2f}"))
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
