"""
MeanReversionMomentum - Baby Strat
==================================

Created by: web_ai
Date: 2026-02-26

Strategy Logic:
- Buy when close breaches lower Bollinger Band and RSI > 30
- Sell when close breaches upper Bollinger Band and RSI < 70
- Exit via ATR-scaled TP/SL

Unique Value Proposition:
Hybrid mean-reversion + momentum confirmation. A BB breach alone can be a
trap in trend markets; RSI gating attempts to filter weaker reversals.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional, Dict


@dataclass
class Signal:
    symbol: str
    direction: str          # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class MeanReversionMomentumStrategy:
    """Combines mean reversion (Bollinger) with momentum (RSI)."""

    def __init__(self, params: Optional[Dict] = None):
        self.p = params or {}
        self.lookback = self.p.get("lookback", 20)       # generic data guard
        self.bb_window = self.p.get("bb_window", 20)     # Bollinger period
        self.rsi_period = self.p.get("rsi_period", 14)   # RSI period
        self.atr_period = self.p.get("atr_period", 14)   # ATR period
        self.tp_atr = self.p.get("tp_atr", 2.0)          # TP = entry +/- ATR*tp_atr
        self.sl_atr = self.p.get("sl_atr", 1.5)          # SL = entry -/+ ATR*sl_atr

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        """Return a list with 0 or 1 Signal for the latest bar."""
        required_cols = {"close", "high", "low"}
        if not required_cols.issubset(set(data.columns)):
            return []

        min_len = max(self.lookback, self.bb_window, self.rsi_period, self.atr_period) + 5
        if len(data) < min_len:
            return []

        bb = self._bollinger_bands(data["close"], self.bb_window)
        rsi = self._rsi(data["close"], self.rsi_period)
        atr = self._atr(data, self.atr_period)

        price = data["close"].iloc[-1]
        cur_upper = bb["upper"].iloc[-1]
        cur_lower = bb["lower"].iloc[-1]
        cur_rsi = rsi.iloc[-1]
        cur_atr = atr.iloc[-1]

        if any(pd.isna(v) for v in [cur_upper, cur_lower, cur_rsi, cur_atr]):
            return []

        # BUY: lower-band breach + momentum recovering above weak-oversold zone.
        if price < cur_lower and cur_rsi > 30:
            band_dist = max(0.0, (cur_lower - price) / max(cur_lower, 1e-12))
            rsi_edge = min(max((cur_rsi - 30) / 30, 0.0), 1.0)
            confidence = float(round(min(0.95, max(0.1, 0.55 + 0.25 * band_dist + 0.1 * rsi_edge)), 2))
            return [Signal(
                symbol=symbol,
                direction="BUY",
                confidence=confidence,
                entry_price=float(round(price, 2)),
                take_profit=float(round(price + cur_atr * self.tp_atr, 2)),
                stop_loss=float(round(price - cur_atr * self.sl_atr, 2)),
                reason=f"BB lower breach + RSI {cur_rsi:.1f}",
            )]

        # SELL: upper-band breach + momentum rolling over below strong-overbought zone.
        if price > cur_upper and cur_rsi < 70:
            band_dist = max(0.0, (price - cur_upper) / max(cur_upper, 1e-12))
            rsi_edge = min(max((70 - cur_rsi) / 70, 0.0), 1.0)
            confidence = float(round(min(0.95, max(0.1, 0.55 + 0.25 * band_dist + 0.1 * rsi_edge)), 2))
            return [Signal(
                symbol=symbol,
                direction="SELL",
                confidence=confidence,
                entry_price=float(round(price, 2)),
                take_profit=float(round(price - cur_atr * self.tp_atr, 2)),
                stop_loss=float(round(price + cur_atr * self.sl_atr, 2)),
                reason=f"BB upper breach + RSI {cur_rsi:.1f}",
            )]

        return []

    def _bollinger_bands(self, prices: pd.Series, window: int) -> pd.DataFrame:
        """Upper / lower Bollinger bands (2 sigma)."""
        ma = prices.rolling(window).mean()
        std = prices.rolling(window).std()
        upper = ma + 2 * std
        lower = ma - 2 * std
        return pd.DataFrame({"upper": upper, "lower": lower})

    def _rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Classic 0-100 RSI."""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / (loss + 1e-12)
        return 100 - (100 / (1 + rs))

    def _atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average True Range."""
        high, low, close = data["high"], data["low"], data["close"]
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()


if __name__ == "__main__":
    # Minimal sanity-check with synthetic data.
    np.random.seed(0)
    n = 320
    close = np.random.randn(n).cumsum() + 50000
    high = close + np.random.rand(n) * 15
    low = close - np.random.rand(n) * 15
    data = pd.DataFrame({"close": close, "high": high, "low": low})

    strat = MeanReversionMomentumStrategy()
    all_sigs = []
    for i in range(60, len(data)):
        all_sigs.extend(strat.generate_signals(data.iloc[: i + 1], "BTCUSDT"))
    print(f"Generated {len(all_sigs)} signal(s).")
    for s in all_sigs[:3]:
        print(f"{s.direction} {s.symbol} @ {s.entry_price:.2f} - {s.reason}")
