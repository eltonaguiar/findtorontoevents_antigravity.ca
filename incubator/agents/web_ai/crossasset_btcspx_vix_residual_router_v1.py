"""
crossasset_btcspx_vix_residual_router_v1
========================================

Residual router:
- Model BTC returns from SPX + VIX betas
- Trade residual z-score only when VIX regime is elevated
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


class CrossassetBTCSPXVixResidualRouterStrategy:
    """Cross-asset residual mean reversion with risk-regime gating."""

    def __init__(self, params: Optional[Dict] = None):
        self.p = params or {}
        self.beta_window = self.p.get("beta_window", 72)
        self.resid_window = self.p.get("resid_window", 40)
        self.resid_z_entry = self.p.get("resid_z_entry", 1.7)
        self.vix_window = self.p.get("vix_window", 40)
        self.vix_z_gate = self.p.get("vix_z_gate", 0.8)
        self.atr_period = self.p.get("atr_period", 14)
        self.tp_atr = self.p.get("tp_atr", 2.1)
        self.sl_atr = self.p.get("sl_atr", 1.3)

    def generate_signals(
        self,
        btc_data: pd.DataFrame,
        spx_data: pd.DataFrame,
        vix_data: pd.DataFrame,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        min_len = max(self.beta_window, self.resid_window, self.vix_window) + 12
        if (
            btc_data is None
            or spx_data is None
            or vix_data is None
            or len(btc_data) < min_len
            or len(spx_data) < min_len
            or len(vix_data) < min_len
        ):
            return []

        btc = btc_data["close"].astype(float).reset_index(drop=True)
        spx = spx_data["close"].astype(float).reset_index(drop=True)
        vix = vix_data["close"].astype(float).reset_index(drop=True)
        n = min(len(btc), len(spx), len(vix))
        btc = btc.iloc[-n:]
        spx = spx.iloc[-n:]
        vix = vix.iloc[-n:]

        r_btc = btc.pct_change()
        r_spx = spx.pct_change()
        r_vix = vix.pct_change()

        beta_spx = r_btc.rolling(self.beta_window).cov(r_spx) / r_spx.rolling(self.beta_window).var().replace(0, np.nan)
        beta_vix = r_btc.rolling(self.beta_window).cov(r_vix) / r_vix.rolling(self.beta_window).var().replace(0, np.nan)
        beta_spx = beta_spx.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        beta_vix = beta_vix.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        pred = beta_spx * r_spx + beta_vix * r_vix
        resid = r_btc - pred
        resid_mu = resid.rolling(self.resid_window).mean()
        resid_sd = resid.rolling(self.resid_window).std(ddof=0).replace(0, np.nan)
        resid_z = (resid - resid_mu) / resid_sd

        vix_mu = vix.rolling(self.vix_window).mean()
        vix_sd = vix.rolling(self.vix_window).std(ddof=0).replace(0, np.nan)
        vix_z = (vix - vix_mu) / vix_sd

        rz = float(resid_z.iloc[-1]) if not np.isnan(resid_z.iloc[-1]) else 0.0
        vz = float(vix_z.iloc[-1]) if not np.isnan(vix_z.iloc[-1]) else 0.0
        risk_on_high_vol = vz >= self.vix_z_gate
        if not risk_on_high_vol:
            return []

        atr = self._atr(btc_data, self.atr_period)
        curr_price = float(btc.iloc[-1])
        curr_atr = float(atr.iloc[-1])
        if np.isnan(curr_atr) or curr_atr <= 0:
            return []

        signals: List[Signal] = []
        if rz <= -self.resid_z_entry:
            confidence = min(0.95, 0.60 + min(abs(rz) / 4.0, 0.2) + min(vz / 3.0, 0.15))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(curr_price, 2),
                    take_profit=round(curr_price + curr_atr * self.tp_atr, 2),
                    stop_loss=round(curr_price - curr_atr * self.sl_atr, 2),
                    reason=f"ResidZ={rz:.2f} VIXz={vz:.2f} betaSPX={beta_spx.iloc[-1]:.2f}",
                )
            )
        elif rz >= self.resid_z_entry:
            confidence = min(0.95, 0.60 + min(abs(rz) / 4.0, 0.2) + min(vz / 3.0, 0.15))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(curr_price, 2),
                    take_profit=round(curr_price - curr_atr * self.tp_atr, 2),
                    stop_loss=round(curr_price + curr_atr * self.sl_atr, 2),
                    reason=f"ResidZ={rz:.2f} VIXz={vz:.2f} betaSPX={beta_spx.iloc[-1]:.2f}",
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

