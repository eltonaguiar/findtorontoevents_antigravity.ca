"""
CorrHmaTrendStrategy - Baby Strat
==================================

Created by: Claude AI
Date: 2026-03-04

Academic Source: Alan Hull (2005), "Hull Moving Average"
  HMA = WMA(2*WMA(close, n/2) - WMA(close, n), sqrt(n))
  +0.978 correlation with close price

Strategy Logic:
- Entry BUY: Close > HMA (price trending above smoothed average)
- Entry SELL: Close < HMA (price trending below smoothed average)
- TP: +8%, SL: -4%
- Confidence based on distance from HMA as percentage

Why it works:
- HMA eliminates lag almost entirely while maintaining smoothness
- Traditional MAs lag badly; HMA uses weighted difference trick to project direction
- High correlation (+0.978) means it tracks price closely but smooths noise
- Ideal for trend-following on crypto where momentum is king
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]

@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


def _wma(series: pd.Series, period: int) -> pd.Series:
    """Weighted Moving Average: heavier weight on recent bars."""
    weights = np.arange(1, period + 1, dtype=float)
    return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)


def calc_hma(close: pd.Series, period: int = 16) -> pd.Series:
    """Hull Moving Average = WMA(2*WMA(n/2) - WMA(n), sqrt(n))."""
    half_period = max(int(period / 2), 1)
    sqrt_period = max(int(np.sqrt(period)), 1)
    wma_half = _wma(close, half_period)
    wma_full = _wma(close, period)
    diff = 2 * wma_half - wma_full
    return _wma(diff, sqrt_period)


class CorrHmaTrendStrategy:
    NAME = "Correlation - HMA Trend"
    DESCRIPTION = "Hull Moving Average trend following with +0.978 correlation to close"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.hma_period = self.params.get("hma_period", 16)
        self.tp_pct = self.params.get("tp_pct", 0.08)
        self.sl_pct = self.params.get("sl_pct", 0.04)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.hma_period + 10:
            return []

        close = data["close"].astype(float)
        hma = calc_hma(close, self.hma_period)

        current_price = float(close.iloc[-1])
        current_hma = float(hma.iloc[-1])

        if np.isnan(current_hma) or current_hma <= 0:
            return []

        distance_pct = (current_price - current_hma) / current_hma
        signals = []

        if current_price > current_hma:
            confidence = min(0.5 + abs(distance_pct) * 5, 0.95)
            tp = current_price * (1 + self.tp_pct)
            sl = current_price * (1 - self.sl_pct)
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"HMA trend BUY: price {current_price:.2f} > HMA({self.hma_period}) {current_hma:.2f}, dist={distance_pct:+.2%}",
                )
            )
        elif current_price < current_hma:
            confidence = min(0.5 + abs(distance_pct) * 5, 0.95)
            tp = current_price * (1 - self.tp_pct)
            sl = current_price * (1 + self.sl_pct)
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"HMA trend SELL: price {current_price:.2f} < HMA({self.hma_period}) {current_hma:.2f}, dist={distance_pct:+.2%}",
                )
            )

        return signals


if __name__ == "__main__":
    np.random.seed(42)
    n = 300
    returns = np.random.normal(0.0001, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))

    test_data = pd.DataFrame(
        {
            "open": prices * (1 + np.random.normal(0, 0.001, n)),
            "high": prices * (1 + abs(np.random.normal(0, 0.01, n))),
            "low": prices * (1 - abs(np.random.normal(0, 0.01, n))),
            "close": prices,
            "volume": np.random.uniform(100, 1000, n),
        }
    )

    strategy = CorrHmaTrendStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")

    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
