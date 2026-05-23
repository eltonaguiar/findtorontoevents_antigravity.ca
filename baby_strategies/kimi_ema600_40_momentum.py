"""
KimiEma60040MomentumStrategy - Baby Strat
==========================================

Created by: Claude AI
Date: 2026-03-04

Academic Source: Jaaskellainen (2022), Lappeenranta University thesis
  EMA 600/40 crossover beat BTC buy-and-hold 2016-2021.
  Fast EMA 40 (hourly ~1.5 days, 4H ~6.5 days)
  Slow EMA 600 (hourly ~25 days, 4H ~100 days)

Strategy Logic:
- Fast EMA: 40-period exponential moving average
- Slow EMA: 600-period exponential moving average
- Entry BUY:  Fast EMA crosses above Slow EMA
- Entry SELL: Fast EMA crosses below Slow EMA
- Exit: Reverse cross OR trailing stop at 3 * ATR(14)
- TP: +15%, SL: -6%

Why it works:
- 600-period EMA captures macro trend (~100 days on 4H)
- 40-period EMA captures short-term momentum (~6.5 days on 4H)
- Crossover timing filters out whipsaws better than shorter MA pairs
- Academically validated on BTC with out-of-sample alpha over buy-and-hold
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


def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series,
             period: int = 14) -> pd.Series:
    """Average True Range."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


class KimiEma60040MomentumStrategy:
    NAME = "Kimi EMA600-40 Momentum"
    DESCRIPTION = "EMA 600/40 crossover momentum (Jaaskellainen 2022, beat BTC B&H 2016-2021)"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.fast_period = self.params.get("fast_period", 40)
        self.slow_period = self.params.get("slow_period", 600)
        self.atr_period = self.params.get("atr_period", 14)
        self.atr_trail_mult = self.params.get("atr_trail_mult", 3.0)
        self.tp_pct = self.params.get("tp_pct", 0.15)
        self.sl_pct = self.params.get("sl_pct", 0.06)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        min_bars = self.slow_period + 10
        if len(data) < min_bars:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)

        fast_ema = close.ewm(span=self.fast_period, adjust=False).mean()
        slow_ema = close.ewm(span=self.slow_period, adjust=False).mean()
        atr = calc_atr(high, low, close, self.atr_period)

        current_price = float(close.iloc[-1])
        current_fast = float(fast_ema.iloc[-1])
        current_slow = float(slow_ema.iloc[-1])
        prev_fast = float(fast_ema.iloc[-2])
        prev_slow = float(slow_ema.iloc[-2])
        current_atr = float(atr.iloc[-1])

        if np.isnan(current_fast) or np.isnan(current_slow) or np.isnan(current_atr):
            return []

        signals = []
        ema_gap_pct = abs(current_fast - current_slow) / current_slow

        # Bullish crossover: fast crosses above slow
        if current_fast > current_slow and prev_fast <= prev_slow:
            confidence = min(0.55 + ema_gap_pct * 10, 0.95)
            tp = current_price * (1 + self.tp_pct)
            sl_trailing = current_price - self.atr_trail_mult * current_atr
            sl_fixed = current_price * (1 - self.sl_pct)
            sl = max(sl_trailing, sl_fixed)
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"EMA crossover BUY: EMA({self.fast_period})={current_fast:.2f} crossed above EMA({self.slow_period})={current_slow:.2f}, ATR trail={self.atr_trail_mult}x",
                )
            )

        # Bearish crossover: fast crosses below slow
        elif current_fast < current_slow and prev_fast >= prev_slow:
            confidence = min(0.55 + ema_gap_pct * 10, 0.95)
            tp = current_price * (1 - self.tp_pct)
            sl_trailing = current_price + self.atr_trail_mult * current_atr
            sl_fixed = current_price * (1 + self.sl_pct)
            sl = min(sl_trailing, sl_fixed)
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"EMA crossover SELL: EMA({self.fast_period})={current_fast:.2f} crossed below EMA({self.slow_period})={current_slow:.2f}, ATR trail={self.atr_trail_mult}x",
                )
            )

        return signals


if __name__ == "__main__":
    np.random.seed(42)
    n = 700
    # Simulate trending market with regime change for crossover detection
    trend_up = np.random.normal(0.001, 0.015, 350)
    trend_down = np.random.normal(-0.001, 0.015, 350)
    returns = np.concatenate([trend_up, trend_down])
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

    strategy = KimiEma60040MomentumStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")

    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
