"""
crypto_whale_social_divergence_v1 - Baby Strat
==============================================

Created by: cursor_ai
Date: 2026-02-27

Strategy Logic:
- Entry when: whale accumulation diverges from social hype and trend confirms
- Exit when: ATR-based TP/SL or time-based backtest exit
- Risk management: symmetric ATR envelope

Unique Value Proposition:
Trades accumulation-vs-crowd divergence rather than pure price indicators.
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


class CryptoWhaleSocialDivergenceStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get("lookback", 96)
        self.atr_period = self.params.get("atr_period", 14)
        self.div_threshold = self.params.get("div_threshold", 1.0)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.1)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.3)

    def generate_signals(
        self,
        data: pd.DataFrame,
        whale_inflow: Optional[pd.Series] = None,
        social_data: Optional[pd.Series] = None,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        if len(data) < self.lookback + self.atr_period:
            return []
        if whale_inflow is None or social_data is None:
            return []

        ts = pd.to_datetime(data["timestamp"], utc=True)
        whale = pd.to_numeric(whale_inflow, errors="coerce").reindex(ts, method="ffill").fillna(0.0)
        social = pd.to_numeric(social_data, errors="coerce").reindex(ts, method="ffill").fillna(0.0)
        close = pd.to_numeric(data["close"], errors="coerce")
        ema = close.ewm(span=34, adjust=False).mean()
        atr = self._atr(data, self.atr_period)

        whale_z = self._zscore(whale, self.lookback)
        social_z = self._zscore(social, self.lookback)
        divergence = whale_z - social_z
        trend_bias = (close / ema - 1.0).fillna(0.0)

        if atr.isna().iloc[-1] or atr.iloc[-1] <= 0:
            return []
        px = float(close.iloc[-1])
        a = float(atr.iloc[-1])
        div = float(divergence.iloc[-1])
        tb = float(trend_bias.iloc[-1])

        signals: List[Signal] = []
        if div > (self.div_threshold + 0.25) and tb > 0.001:
            conf = min(0.95, 0.56 + 0.12 * max(0.0, div) + 2.0 * max(0.0, tb))
            signals.append(
                Signal(symbol, "BUY", round(float(conf), 3), round(px, 4), round(px + a * self.tp_atr_mult, 4), round(px - a * self.sl_atr_mult, 4),
                       f"Whale-social divergence {div:.2f} with bullish trend")
            )
        elif div < -(self.div_threshold + 0.25) and tb < -0.001:
            conf = min(0.95, 0.56 + 0.12 * max(0.0, -div) + 2.0 * max(0.0, -tb))
            signals.append(
                Signal(symbol, "SELL", round(float(conf), 3), round(px, 4), round(px - a * self.tp_atr_mult, 4), round(px + a * self.sl_atr_mult, 4),
                       f"Whale-social divergence {div:.2f} with bearish trend")
            )
        return signals

    @staticmethod
    def _zscore(series: pd.Series, window: int) -> pd.Series:
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
