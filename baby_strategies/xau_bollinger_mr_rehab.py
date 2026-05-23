"""
XauBollingerMrRehabStrategy - COMMODITY / Gold expansion
=========================================================
Historical closed-trade data showed COMMODITY (gold proxy) as a standout positive
in the rehabilitation pipeline. This strategy applies Bollinger mean-reversion
to XAU (Gold) on Binance.

TESTING_PROTOCOL.MD: Run Layers 1-5 before production.

Direction: LONG only at lower band in structural uptrend (price > 0.9 × 200 SMA).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


# Gold pairs on Binance (USDT-margined)
SYMBOLS = ["XAUTUSDT", "PAXGUSDT"]


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class XauBollingerMrRehabStrategy:
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.bb_period = self.params.get("bb_period", 20)
        self.bb_std = self.params.get("bb_std", 2.0)
        self.sma_period = self.params.get("sma_period", 200)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.5)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.5)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "XAUTUSDT"
    ) -> List[Signal]:
        min_bars = max(self.bb_period, self.sma_period) + 10
        if len(data) < min_bars:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)

        # Bollinger Bands
        sma = close.rolling(self.bb_period).mean()
        std = close.rolling(self.bb_period).std()
        lower_band = sma - self.bb_std * std
        middle_band = sma
        sma200 = close.rolling(self.sma_period).mean()

        # ATR for stops
        tr = pd.concat(
            [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(14, min_periods=1).mean()

        # Current values
        current_price = float(close.iloc[-1])
        prev_price = float(close.iloc[-2])
        current_lower = float(lower_band.iloc[-1])
        current_middle = float(middle_band.iloc[-1])
        current_sma200 = float(sma200.iloc[-1])
        current_atr = float(atr.iloc[-1])

        signals: List[Signal] = []

        # Entry: price at lower band in broader uptrend
        if (
            current_price <= current_lower
            and current_price > current_sma200 * 0.9
            and prev_price > current_lower
            and current_atr > 0
        ):
            tp = current_middle  # Target middle band
            sl = current_price - (current_atr * self.sl_atr_mult)
            
            # Confidence based on how deep we are in the band
            band_depth = (current_lower - current_price) / current_atr if current_atr > 0 else 0.0
            confidence = min(0.5 + band_depth * 0.15 + 0.1, 0.90)

            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(float(confidence), 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"xau_bollinger_mr_rehab price {current_price:.4f} at lower BB, target mid {current_middle:.4f}",
                )
            )
        return signals