"""
Volatility Cone Breakout Strategy
=================================

Created by: cursor_ai
Date: 2026-02-27
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class VolatilityConeBreakoutStrategy:
    """Trade when realized volatility expands beyond its cone."""

    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.rv_period = self.p.get("rv_period", 20)
        self.cone_period = self.p.get("cone_period", 60)
        self.z_threshold = self.p.get("z_threshold", 1.8)
        self.sma_period = self.p.get("sma_period", 20)
        self.atr_period = self.p.get("atr_period", 14)
        self.tp_atr_mult = self.p.get("tp_atr_mult", 2.5)
        self.sl_atr_mult = self.p.get("sl_atr_mult", 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.cone_period + self.rv_period + 5:
            return []

        close = data["close"]
        returns = close.pct_change()
        rv = returns.rolling(self.rv_period).std()
        rv_mean = rv.rolling(self.cone_period).mean()
        rv_std = rv.rolling(self.cone_period).std()
        rv_z = (rv - rv_mean) / rv_std.replace(0, np.nan)

        sma = close.rolling(self.sma_period).mean()
        atr = self._calculate_atr(data)

        price = close.iloc[-1]
        z = float(rv_z.iloc[-1]) if pd.notna(rv_z.iloc[-1]) else 0.0
        atr_now = float(atr.iloc[-1]) if pd.notna(atr.iloc[-1]) else 0.0

        if atr_now <= 0:
            return []

        signals: List[Signal] = []
        if z > self.z_threshold and price > sma.iloc[-1]:
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(min(0.95, 0.55 + (z - self.z_threshold) * 0.12), 3),
                    entry_price=round(price, 2),
                    take_profit=round(price + atr_now * self.tp_atr_mult, 2),
                    stop_loss=round(price - atr_now * self.sl_atr_mult, 2),
                    reason=f"RV z-score {z:.2f} > {self.z_threshold} with bullish trend",
                )
            )
        elif z > self.z_threshold and price < sma.iloc[-1]:
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(min(0.95, 0.55 + (z - self.z_threshold) * 0.12), 3),
                    entry_price=round(price, 2),
                    take_profit=round(price - atr_now * self.tp_atr_mult, 2),
                    stop_loss=round(price + atr_now * self.sl_atr_mult, 2),
                    reason=f"RV z-score {z:.2f} > {self.z_threshold} with bearish trend",
                )
            )
        return signals

    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]
        tr = pd.concat(
            [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        return tr.rolling(self.atr_period).mean()


if __name__ == "__main__":
    np.random.seed(42)
    n = 400
    rets = np.random.normal(0.0002, 0.015, n)
    prices = 50000 * np.exp(np.cumsum(rets))
    df = pd.DataFrame(
        {
            "open": prices * (1 + np.random.normal(0, 0.001, n)),
            "high": prices * (1 + np.abs(np.random.normal(0, 0.008, n))),
            "low": prices * (1 - np.abs(np.random.normal(0, 0.008, n))),
            "close": prices,
            "volume": np.random.uniform(200, 2000, n),
        }
    )
    s = VolatilityConeBreakoutStrategy()
    out = s.generate_signals(df, "BTCUSDT")
    print(f"Generated {len(out)} signals")
    for sig in out:
        print(sig)
