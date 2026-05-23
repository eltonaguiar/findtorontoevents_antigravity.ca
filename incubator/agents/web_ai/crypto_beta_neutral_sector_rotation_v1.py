"""
crypto_beta_neutral_sector_rotation_v1
======================================

Beta-neutral residual rotation:
- estimate BTC beta to SPX
- use governance/social proxies as risk rotation gauge
- trade idiosyncratic residual reversion in direction of rotation regime.
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


class CryptoBetaNeutralSectorRotationStrategy:
    """Residual-zscore entries aligned with risk-rotation proxy."""

    def __init__(self, params: Optional[Dict] = None):
        self.p = params or {}
        self.beta_window = self.p.get("beta_window", 60)
        self.resid_window = self.p.get("resid_window", 36)
        self.resid_z_entry = self.p.get("resid_z_entry", 1.6)
        self.proxy_window = self.p.get("proxy_window", 24)
        self.proxy_z_gate = self.p.get("proxy_z_gate", 0.5)
        self.atr_period = self.p.get("atr_period", 14)
        self.tp_atr = self.p.get("tp_atr", 2.0)
        self.sl_atr = self.p.get("sl_atr", 1.35)

    def generate_signals(
        self,
        data: pd.DataFrame,
        spx_data: pd.DataFrame,
        gov_data: pd.Series,
        social_data: pd.Series,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        min_len = max(self.beta_window, self.resid_window, self.proxy_window) + 10
        if (
            data is None
            or spx_data is None
            or gov_data is None
            or social_data is None
            or len(data) < min_len
            or len(spx_data) < min_len
            or len(gov_data) < min_len
            or len(social_data) < min_len
        ):
            return []

        btc = data["close"].astype(float).reset_index(drop=True)
        spx = spx_data["close"].astype(float).reset_index(drop=True)
        n = min(len(btc), len(spx))
        btc = btc.iloc[-n:]
        spx = spx.iloc[-n:]

        btc_ret = btc.pct_change()
        spx_ret = spx.pct_change()
        beta = btc_ret.rolling(self.beta_window).cov(spx_ret) / spx_ret.rolling(self.beta_window).var().replace(0, np.nan)
        beta = beta.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        resid = btc_ret - beta * spx_ret
        resid_mu = resid.rolling(self.resid_window).mean()
        resid_sd = resid.rolling(self.resid_window).std(ddof=0).replace(0, np.nan)
        resid_z = (resid - resid_mu) / resid_sd

        # Risk rotation proxy from governance + social acceleration.
        gov_s = pd.Series(gov_data).reset_index(drop=True).astype(float).tail(n)
        soc_s = pd.Series(social_data).reset_index(drop=True).astype(float).tail(n)
        rotation_raw = 0.6 * gov_s.pct_change().fillna(0.0) + 0.4 * soc_s.pct_change().fillna(0.0)
        rot_mu = rotation_raw.rolling(self.proxy_window).mean()
        rot_sd = rotation_raw.rolling(self.proxy_window).std(ddof=0).replace(0, np.nan)
        rot_z = (rotation_raw - rot_mu) / rot_sd

        rz = float(resid_z.iloc[-1]) if not np.isnan(resid_z.iloc[-1]) else 0.0
        pz = float(rot_z.iloc[-1]) if not np.isnan(rot_z.iloc[-1]) else 0.0
        current_price = float(btc.iloc[-1])

        atr = self._atr(data, self.atr_period)
        current_atr = float(atr.iloc[-1])
        if np.isnan(current_atr) or current_atr <= 0:
            return []

        signals: List[Signal] = []
        if rz <= -self.resid_z_entry and pz >= self.proxy_z_gate:
            confidence = min(0.93, 0.58 + min(abs(rz) / 4.0, 0.2) + min(pz / 3.0, 0.15))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price + current_atr * self.tp_atr, 2),
                    stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                    reason=f"ResidZ={rz:.2f} RotZ={pz:.2f} beta={beta.iloc[-1]:.2f}",
                )
            )
        elif rz >= self.resid_z_entry and pz <= -self.proxy_z_gate:
            confidence = min(0.93, 0.58 + min(abs(rz) / 4.0, 0.2) + min(abs(pz) / 3.0, 0.15))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price - current_atr * self.tp_atr, 2),
                    stop_loss=round(current_price + current_atr * self.sl_atr, 2),
                    reason=f"ResidZ={rz:.2f} RotZ={pz:.2f} beta={beta.iloc[-1]:.2f}",
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

