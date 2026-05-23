"""
crypto_corrshock_dispersion_reversion_v1
========================================

Trades BTC mean reversion after abrupt BTC-SPX correlation breakdowns combined
with return dispersion spikes.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class CryptoCorrshockDispersionReversionStrategy:
    """Fade temporary dislocations after correlation shocks."""

    def __init__(self, params: Optional[Dict] = None):
        self.p = params or {}
        self.short_corr = self.p.get("short_corr", 18)
        self.long_corr = self.p.get("long_corr", 72)
        self.shock_threshold = self.p.get("shock_threshold", 0.35)
        self.disp_window = self.p.get("disp_window", 40)
        self.disp_z_entry = self.p.get("disp_z_entry", 1.5)
        self.rsi_period = self.p.get("rsi_period", 14)
        self.atr_period = self.p.get("atr_period", 14)
        self.tp_atr = self.p.get("tp_atr", 2.0)
        self.sl_atr = self.p.get("sl_atr", 1.25)

    def generate_signals(
        self,
        data: pd.DataFrame,
        spx_data: pd.DataFrame,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        min_len = max(self.long_corr, self.disp_window) + self.rsi_period + 8
        if data is None or spx_data is None or len(data) < min_len or len(spx_data) < min_len:
            return []

        btc = data["close"].astype(float).reset_index(drop=True)
        spx = spx_data["close"].astype(float).reset_index(drop=True)
        n = min(len(btc), len(spx))
        btc = btc.iloc[-n:]
        spx = spx.iloc[-n:]

        btc_ret = btc.pct_change()
        spx_ret = spx.pct_change()

        corr_short = btc_ret.rolling(self.short_corr).corr(spx_ret)
        corr_long = btc_ret.rolling(self.long_corr).corr(spx_ret)
        corr_shock = corr_long - corr_short

        gap = btc_ret - spx_ret
        disp = gap.abs().rolling(self.disp_window).mean()
        disp_mu = disp.rolling(self.disp_window).mean()
        disp_sd = disp.rolling(self.disp_window).std(ddof=0).replace(0, np.nan)
        disp_z = (disp - disp_mu) / disp_sd

        current_price = float(btc.iloc[-1])
        atr = self._atr(data, self.atr_period)
        current_atr = float(atr.iloc[-1])
        rsi = self._rsi(btc, self.rsi_period).iloc[-1]

        if np.isnan(current_atr) or current_atr <= 0:
            return []

        c_shock = float(corr_shock.iloc[-1]) if not np.isnan(corr_shock.iloc[-1]) else 0.0
        d_z = float(disp_z.iloc[-1]) if not np.isnan(disp_z.iloc[-1]) else 0.0
        g = float(gap.iloc[-1]) if not np.isnan(gap.iloc[-1]) else 0.0

        shock = c_shock >= self.shock_threshold
        dislocated = d_z >= self.disp_z_entry

        if not (shock and dislocated):
            return []

        signals: List[Signal] = []
        if g < 0 and rsi < 48:
            confidence = min(0.93, 0.58 + min(d_z / 4.0, 0.2) + min(c_shock / 1.5, 0.15))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price + current_atr * self.tp_atr, 2),
                    stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                    reason=f"CorrShock={c_shock:.2f} DispZ={d_z:.2f} gap={g:.4f}",
                )
            )
        elif g > 0 and rsi > 52:
            confidence = min(0.93, 0.58 + min(d_z / 4.0, 0.2) + min(c_shock / 1.5, 0.15))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price - current_atr * self.tp_atr, 2),
                    stop_loss=round(current_price + current_atr * self.sl_atr, 2),
                    reason=f"CorrShock={c_shock:.2f} DispZ={d_z:.2f} gap={g:.4f}",
                )
            )

        return signals

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]
        tr = pd.concat(
            [(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()

    @staticmethod
    def _rsi(prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        up = delta.clip(lower=0)
        down = (-delta).clip(lower=0)
        rs = up.rolling(period, min_periods=1).mean() / down.rolling(period, min_periods=1).mean().replace(0, np.nan)
        return 100 - (100 / (1 + rs))

