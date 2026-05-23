"""Trend Reversal Emoji — 1-hour timeframe baby strategy.

EMA(21/55/200) crossover + RSI(14) momentum + ATR(14) volatility gate.
Standard timeframe for swing entries.

Literature:
  - Brock, Lakonishok & LeBaron (1992): MA crossover profitability
  - Hsu & Kuan (2005): intraday 10-30m optimal for MA rules
  - Elder Triple Screen (1985): multi-timeframe confirmation
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class Signal:
    """A trading signal — required return type."""
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class TrendReversalEmoji1hStrategy:
    """EMA crossover trend reversal — 1h timeframe."""

    INTERVAL = "1h"
    MAX_PICKS = 5
    EMA_FAST = 21
    EMA_SLOW = 55
    EMA_TREND = 200
    RSI_PERIOD = 14
    ATR_PERIOD = 14
    RSI_LONG = 55
    RSI_SHORT = 45
    TP_ATR = 2.5
    SL_ATR = 1.5

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.min_bars = self.EMA_TREND + 10

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)

        ema21 = close.ewm(span=self.EMA_FAST, adjust=False).mean()
        ema55 = close.ewm(span=self.EMA_SLOW, adjust=False).mean()
        ema200 = close.ewm(span=self.EMA_TREND, adjust=False).mean()

        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(com=self.RSI_PERIOD - 1, min_periods=self.RSI_PERIOD).mean()
        avg_loss = loss.ewm(com=self.RSI_PERIOD - 1, min_periods=self.RSI_PERIOD).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        rsi = 100 - (100 / (1 + rs))

        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr = tr.ewm(com=self.ATR_PERIOD - 1, min_periods=self.ATR_PERIOD).mean()

        price = close.iloc[-1]
        atr_now = atr.iloc[-1]
        rsi_now = rsi.iloc[-1]
        tr_now = tr.iloc[-1]

        if atr_now <= 0:
            return []

        cross_up = ema21.iloc[-1] > ema55.iloc[-1] and ema21.iloc[-2] <= ema55.iloc[-2]
        cross_down = ema21.iloc[-1] < ema55.iloc[-1] and ema21.iloc[-2] >= ema55.iloc[-2]
        vol_ok = tr_now > atr_now

        direction = None
        if cross_up and price > ema200.iloc[-1] and rsi_now > self.RSI_LONG and vol_ok:
            direction = "BUY"
        elif cross_down and price < ema200.iloc[-1] and rsi_now < self.RSI_SHORT and vol_ok:
            direction = "SELL"

        if direction is None:
            return []

        if direction == "BUY":
            tp = round(price + self.TP_ATR * atr_now, 6)
            sl = round(price - self.SL_ATR * atr_now, 6)
        else:
            tp = round(price - self.TP_ATR * atr_now, 6)
            sl = round(price + self.SL_ATR * atr_now, 6)

        ema_gap = abs(ema21.iloc[-1] - ema55.iloc[-1]) / price if price > 0 else 0
        rsi_dist = abs(rsi_now - 50) / 50
        confidence = round(min(0.90, 0.50 + ema_gap * 10 + rsi_dist * 0.15), 3)

        return [Signal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            entry_price=round(price, 6),
            take_profit=tp,
            stop_loss=sl,
            reason=(
                f"EMA(21)x EMA(55) {direction} [1h] | "
                f"{'>' if direction == 'BUY' else '<'} EMA(200) | "
                f"RSI={rsi_now:.1f} | TR/ATR={tr_now / atr_now:.2f}"
            ),
        )]


if __name__ == "__main__":
    import numpy as np
    np.random.seed(42)
    n = 250
    prices = 100 + np.cumsum(np.random.randn(n) * 0.5)
    df = pd.DataFrame({
        "open": prices,
        "high": prices + np.random.rand(n) * 2,
        "low": prices - np.random.rand(n) * 2,
        "close": prices + np.random.randn(n) * 0.3,
        "volume": np.random.rand(n) * 1000,
    })
    strat = TrendReversalEmoji1hStrategy()
    sigs = strat.generate_signals(df, "BTCUSDT")
    print(f"Signals: {len(sigs)}")
    for s in sigs:
        print(f"  {s.direction} {s.symbol} @ {s.entry_price} conf={s.confidence}")
