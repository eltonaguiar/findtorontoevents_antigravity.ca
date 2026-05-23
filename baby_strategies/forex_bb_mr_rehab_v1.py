"""
ForexBbMrRehabV1Strategy — Rehabilitation candidate (FOREX)
============================================================
TESTING_PROTOCOL.MD §7: FOREX showed weak aggregate WR in historical audit; Bollinger
mean-reversion was the standout positive style in that narrative review.

This module applies the same *mechanism* as `bollinger_mean_reversion.py` to liquid
USDT-quoted FX proxies on Binance (EUR/GBP/AUD). It is **not** survivor-validated yet —
run bundle backtests, walk-forward, and `tools/mimo_strategy_validation_smoke.py`
before promoting.

Direction: LONG only at lower band in structural uptrend (price > 0.9 × 200 SMA).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


# USDT-margined FX proxies (spot). Same pipeline as other baby strats (Binance klines).
SYMBOLS = ["EURUSDT", "GBPUSDT", "AUDUSDT"]


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class ForexBbMrRehabV1Strategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.bb_period = self.params.get("bb_period", 20)
        self.bb_std = self.params.get("bb_std", 2.0)
        self.sma_period = self.params.get("sma_period", 200)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.5)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.5)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "EURUSDT"
    ) -> List[Signal]:
        min_bars = max(self.bb_period, self.sma_period) + 10
        if len(data) < min_bars:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)

        sma = close.rolling(self.bb_period).mean()
        std = close.rolling(self.bb_period).std()
        lower_band = sma - self.bb_std * std
        sma200 = close.rolling(self.sma_period).mean()

        tr = pd.concat(
            [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(14, min_periods=1).mean()

        current_price = float(close.iloc[-1])
        prev_price = float(close.iloc[-2])
        current_lower = float(lower_band.iloc[-1])
        current_middle = float(sma.iloc[-1])
        current_sma200 = float(sma200.iloc[-1])
        current_atr = float(atr.iloc[-1])

        signals: List[Signal] = []

        if (
            current_price <= current_lower
            and current_price > current_sma200 * 0.9
            and prev_price > current_lower
            and current_atr > 0
        ):
            tp = current_middle
            sl = current_price - (current_atr * self.sl_atr_mult)
            band_depth = (current_lower - current_price) / current_atr if current_atr > 0 else 0.0
            confidence = min(0.5 + band_depth * 0.15 + 0.1, 0.90)
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(float(confidence), 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=(
                        f"forex_bb_mr_rehab_v1 price {current_price:.6f} at lower BB, "
                        f"target mid {current_middle:.6f}"
                    ),
                )
            )
        return signals
