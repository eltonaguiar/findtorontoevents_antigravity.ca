"""
crypto_funding_curvature_wick_absorption_v1
===========================================

Funding extreme + funding curvature turn + wick absorption confirmation.
Designed to catch crowded perp positioning unwind/reversal zones.
"""

import math
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


class CryptoFundingCurvatureWickAbsorptionStrategy:
    """Mean-reversion entries when funding and candles agree on exhaustion."""

    def __init__(self, params: Optional[Dict] = None):
        self.p = params or {}
        self.atr_period = self.p.get("atr_period", 14)
        self.ema_period = self.p.get("ema_period", 34)
        self.funding_hist_window = self.p.get("funding_hist_window", 36)
        self.funding_extreme = self.p.get("funding_extreme", 0.0035)
        self.curve_turn_min = self.p.get("curve_turn_min", 0.00008)
        self.wick_ratio_min = self.p.get("wick_ratio_min", 0.45)
        self.tp_atr = self.p.get("tp_atr", 2.2)
        self.sl_atr = self.p.get("sl_atr", 1.3)
        self._funding_hist: List[float] = []

    def generate_signals(
        self,
        data: pd.DataFrame,
        funding_rate: float,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        if data is None or len(data) < self.ema_period + self.atr_period + 8:
            return []

        try:
            fr = float(0.0 if funding_rate is None else funding_rate)
        except (TypeError, ValueError):
            fr = 0.0

        self._funding_hist.append(fr)
        if len(self._funding_hist) > self.funding_hist_window:
            self._funding_hist = self._funding_hist[-self.funding_hist_window :]

        atr = self._atr(data, self.atr_period)
        ema = data["close"].ewm(span=self.ema_period, adjust=False).mean()

        current_price = float(data["close"].iloc[-1])
        current_atr = float(atr.iloc[-1])
        if current_atr <= 0 or math.isnan(current_atr):
            return []

        last = data.iloc[-1]
        upper_wick = float(last["high"] - max(last["open"], last["close"]))
        lower_wick = float(min(last["open"], last["close"]) - last["low"])
        candle_range = float(max(last["high"] - last["low"], 1e-9))
        lower_wick_ratio = lower_wick / candle_range
        upper_wick_ratio = upper_wick / candle_range

        funding_curve = self._funding_curvature(self._funding_hist)
        above_ema = current_price > float(ema.iloc[-1])
        below_ema = current_price < float(ema.iloc[-1])

        signals: List[Signal] = []

        long_cond = (
            fr <= -self.funding_extreme
            and funding_curve >= self.curve_turn_min
            and lower_wick_ratio >= self.wick_ratio_min
            and above_ema
        )
        short_cond = (
            fr >= self.funding_extreme
            and funding_curve <= -self.curve_turn_min
            and upper_wick_ratio >= self.wick_ratio_min
            and below_ema
        )

        if long_cond:
            confidence = min(0.95, 0.62 + abs(fr) * 40 + min(funding_curve * 2000, 0.15))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price + current_atr * self.tp_atr, 2),
                    stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                    reason=(
                        f"Funding={fr:.4%} curve={funding_curve:.5f} "
                        f"lowerWick={lower_wick_ratio:.2f}"
                    ),
                )
            )
        elif short_cond:
            confidence = min(0.95, 0.62 + abs(fr) * 40 + min(abs(funding_curve) * 2000, 0.15))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price - current_atr * self.tp_atr, 2),
                    stop_loss=round(current_price + current_atr * self.sl_atr, 2),
                    reason=(
                        f"Funding={fr:.4%} curve={funding_curve:.5f} "
                        f"upperWick={upper_wick_ratio:.2f}"
                    ),
                )
            )

        return signals

    @staticmethod
    def _funding_curvature(hist: List[float]) -> float:
        if len(hist) < 3:
            return 0.0
        s = pd.Series(hist, dtype=float)
        first_diff = s.diff()
        second_diff = first_diff.diff()
        val = second_diff.iloc[-1]
        return float(0.0 if pd.isna(val) else val)

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

