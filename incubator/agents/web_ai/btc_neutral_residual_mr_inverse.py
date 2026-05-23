"""
BTC-Neutral Residual Mean Reversion — INVERSE MUTATION
========================================================
DNA Mutation C: Flip direction (momentum instead of mean-reversion)
- Original: LONG when z < -2.0 (cheap), SHORT when z > 2.0 (expensive)
- Inverse: SHORT when z < -2.0 (momentum down), LONG when z > 2.0 (momentum up)
Parent: btc_neutral_residual_mr.py (PF 1.18, 48.1% WR, 264 trades)
"""

import time
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


BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]


class BtcNeutralResidualMRInverseStrategy:
    """Inverse mutation: trade WITH the z-score direction (momentum)."""

    def __init__(self, params: Optional[Dict] = None):
        self.p = params or {}
        self.reg_window = self.p.get("regression_window", 30)
        self.z_window = self.p.get("zscore_window", 20)
        self.z_entry = self.p.get("z_entry", 2.0)
        self.atr_period = self.p.get("atr_period", 14)
        self.tp_atr = self.p.get("tp_atr", 2.0)
        self.sl_atr = self.p.get("sl_atr", 1.5)

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        h, l, c = data["high"], data["low"], data["close"]
        tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()

    @staticmethod
    def _rolling_ols_residual(alt_ret, btc_ret, window):
        residuals = pd.Series(np.nan, index=alt_ret.index)
        for i in range(window, len(alt_ret)):
            y = alt_ret.iloc[i - window:i].values.astype(float)
            x = btc_ret.iloc[i - window:i].values.astype(float)
            if np.any(~np.isfinite(y)) or np.any(~np.isfinite(x)):
                continue
            x_mat = np.column_stack([np.ones(window), x])
            try:
                coeffs = np.linalg.lstsq(x_mat, y, rcond=None)[0]
            except Exception:
                continue
            predicted = coeffs[0] + coeffs[1] * float(btc_ret.iloc[i])
            alt_val = float(alt_ret.iloc[i])
            if np.isfinite(predicted) and np.isfinite(alt_val):
                residuals.iloc[i] = alt_val - predicted
        return residuals

    @staticmethod
    def _rolling_zscore(series, window):
        mu = series.rolling(window, min_periods=window).mean()
        sd = series.rolling(window, min_periods=window).std(ddof=0).replace(0, np.nan)
        return (series - mu) / sd

    def generate_signals(self, data, symbol="ETHUSDT", btc_data=None):
        min_bars = self.reg_window + self.z_window + 10
        if data is None or len(data) < min_bars:
            return []

        if btc_data is None:
            return []

        n = min(len(data), len(btc_data))
        alt = data.iloc[-n:].reset_index(drop=True)
        btc = btc_data.iloc[-n:].reset_index(drop=True)

        alt_ret = alt["close"].pct_change()
        btc_ret = btc["close"].pct_change()

        residuals = self._rolling_ols_residual(alt_ret, btc_ret, self.reg_window)
        z = self._rolling_zscore(residuals, self.z_window)

        current_z = z.iloc[-1]
        if np.isnan(current_z):
            return []

        current_price = float(alt["close"].iloc[-1])
        atr = self._atr(alt, self.atr_period)
        current_atr = float(atr.iloc[-1])
        if np.isnan(current_atr) or current_atr <= 0:
            return []

        signals = []

        # INVERSE: z < -2.0 -> SHORT (momentum down, not mean-rev long)
        if current_z < -self.z_entry:
            conf = round(min(0.55 + min(abs(current_z) - self.z_entry, 2.0) * 0.15, 0.85), 3)
            signals.append(Signal(
                symbol=symbol, direction="SELL",  # INVERSE: was BUY
                confidence=conf,
                entry_price=round(current_price, 6),
                take_profit=round(current_price - current_atr * self.tp_atr, 6),  # INVERSE
                stop_loss=round(current_price + current_atr * self.sl_atr, 6),    # INVERSE
                reason=f"BTC-Neutral ResidZ={current_z:.2f} SHORT_INV",
            ))

        # INVERSE: z > 2.0 -> LONG (momentum up, not mean-rev short)
        if current_z > self.z_entry:
            conf = round(min(0.55 + min(abs(current_z) - self.z_entry, 2.0) * 0.15, 0.85), 3)
            signals.append(Signal(
                symbol=symbol, direction="BUY",  # INVERSE: was SELL
                confidence=conf,
                entry_price=round(current_price, 6),
                take_profit=round(current_price + current_atr * self.tp_atr, 6),  # INVERSE
                stop_loss=round(current_price - current_atr * self.sl_atr, 6),    # INVERSE
                reason=f"BTC-Neutral ResidZ={current_z:.2f} LONG_INV",
            ))

        return signals
