"""
crypto_mark_spot_premium_meanrevert_v1
======================================

Mean-reversion of perp premium proxy:
- premium proxy from funding + deviation from fast EMA
- liquidation spike filter to avoid weak fades
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


class CryptoMarkSpotPremiumMeanrevertStrategy:
    """Fades extreme premium/discount states with liquidation confirmation."""

    def __init__(self, params: Optional[Dict] = None):
        self.p = params or {}
        self.ema_period = self.p.get("ema_period", 21)
        self.premium_weight = self.p.get("premium_weight", 0.6)
        self.hist_window = self.p.get("hist_window", 48)
        self.z_entry = self.p.get("z_entry", 1.8)
        self.liq_mult = self.p.get("liq_mult", 1.6)
        self.rsi_period = self.p.get("rsi_period", 14)
        self.atr_period = self.p.get("atr_period", 14)
        self.tp_atr = self.p.get("tp_atr", 2.0)
        self.sl_atr = self.p.get("sl_atr", 1.25)
        self._premium_hist: List[float] = []

    def generate_signals(
        self,
        data: pd.DataFrame,
        funding_rate: float,
        liquidation_data: pd.DataFrame,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        min_len = max(self.ema_period, self.hist_window, self.rsi_period) + 10
        if data is None or len(data) < min_len:
            return []

        close = data["close"].astype(float)
        ema = close.ewm(span=self.ema_period, adjust=False).mean()
        premium_px = (close.iloc[-1] - ema.iloc[-1]) / max(abs(ema.iloc[-1]), 1e-9)
        fr = float(0.0 if funding_rate is None else funding_rate)
        premium_proxy = self.premium_weight * fr + (1.0 - self.premium_weight) * float(premium_px)

        self._premium_hist.append(float(premium_proxy))
        if len(self._premium_hist) > self.hist_window:
            self._premium_hist = self._premium_hist[-self.hist_window :]

        z = self._zscore(self._premium_hist)
        if np.isnan(z):
            return []

        liq_ratio = self._liquidation_ratio(liquidation_data)
        if liq_ratio < self.liq_mult:
            return []

        rsi = self._rsi(close, self.rsi_period)
        atr = self._atr(data, self.atr_period)
        curr_price = float(close.iloc[-1])
        curr_atr = float(atr.iloc[-1])
        curr_rsi = float(rsi.iloc[-1])
        if np.isnan(curr_atr) or curr_atr <= 0:
            return []

        signals: List[Signal] = []
        if z >= self.z_entry and curr_rsi >= 50:
            confidence = min(0.95, 0.60 + min(z / 4.0, 0.2) + min((liq_ratio - 1.0) / 3.0, 0.15))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(curr_price, 2),
                    take_profit=round(curr_price - curr_atr * self.tp_atr, 2),
                    stop_loss=round(curr_price + curr_atr * self.sl_atr, 2),
                    reason=f"PremiumZ={z:.2f} liqRatio={liq_ratio:.2f} funding={fr:.4%}",
                )
            )
        elif z <= -self.z_entry and curr_rsi <= 50:
            confidence = min(0.95, 0.60 + min(abs(z) / 4.0, 0.2) + min((liq_ratio - 1.0) / 3.0, 0.15))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(curr_price, 2),
                    take_profit=round(curr_price + curr_atr * self.tp_atr, 2),
                    stop_loss=round(curr_price - curr_atr * self.sl_atr, 2),
                    reason=f"PremiumZ={z:.2f} liqRatio={liq_ratio:.2f} funding={fr:.4%}",
                )
            )
        return signals

    @staticmethod
    def _zscore(vals: List[float]) -> float:
        if len(vals) < 12:
            return float("nan")
        s = pd.Series(vals, dtype=float)
        mu = s.mean()
        sd = s.std(ddof=0)
        if sd <= 0 or np.isnan(sd):
            return float("nan")
        return float((s.iloc[-1] - mu) / sd)

    @staticmethod
    def _liquidation_ratio(liquidation_data: pd.DataFrame) -> float:
        if liquidation_data is None or len(liquidation_data) < 20 or "usd_value" not in liquidation_data.columns:
            return 1.0
        vals = liquidation_data["usd_value"].astype(float)
        baseline = vals.rolling(20, min_periods=5).mean().iloc[-1]
        current = vals.iloc[-1]
        if baseline <= 0 or np.isnan(baseline):
            return 1.0
        return float(current / baseline)

    @staticmethod
    def _rsi(prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gains = delta.clip(lower=0)
        losses = (-delta).clip(lower=0)
        rs = gains.rolling(period, min_periods=1).mean() / losses.rolling(period, min_periods=1).mean().replace(0, np.nan)
        return 100 - (100 / (1 + rs))

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

