"""
LowerWickAbsorption - Baby Strat
=================================

Created by: web_ai
Date: 2026-02-26

Strategy Logic:
- Entry when: Close in bottom 25% of candle range + ATR in lowest 30% percentile
- Exit when: TP = 2.2 x ATR, SL = 1.4 x ATR

Unique Value Proposition:
No existing strategy uses candle-location % as primary signal.
White-space microstructure candle-location.

Expected Regime: Low-vol ranging with buyer absorption (bottoming tails).
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class LowerWickAbsorptionStrategy:
    """Lower-wick absorption in low-vol percentile."""

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.atr_period = self.params.get('atr_period', 14)
        self.percentile_lookback = self.params.get('percentile_lookback', 50)
        self.wick_threshold = self.params.get('wick_threshold', 0.25)
        self.percentile_threshold = self.params.get('percentile_threshold', 0.30)
        self.tp_atr = self.params.get('tp_atr', 2.2)
        self.sl_atr = self.params.get('sl_atr', 1.4)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = self.percentile_lookback + self.atr_period + 10
        if len(data) < min_len:
            return []

        atr = self._calculate_atr(data)
        atr_roll = atr.rolling(self.percentile_lookback)
        atr_pct = atr / atr_roll.quantile(self.percentile_threshold)

        current_close = data['close'].iloc[-1]
        current_high = data['high'].iloc[-1]
        current_low = data['low'].iloc[-1]
        current_atr = atr.iloc[-1]
        current_atr_pct = atr_pct.iloc[-1] if not pd.isna(atr_pct.iloc[-1]) else 1.0

        range_ = current_high - current_low
        if range_ == 0:
            return []
        close_pos = (current_close - current_low) / range_

        if close_pos < self.wick_threshold and current_atr_pct < 1.0:
            confidence = 0.75 + (1.0 - current_atr_pct) * 0.2
            return [Signal(
                symbol=symbol, direction="BUY",
                confidence=round(min(confidence, 0.93), 2),
                entry_price=round(current_close, 2),
                take_profit=round(current_close + current_atr * self.tp_atr, 2),
                stop_loss=round(current_close - current_atr * self.sl_atr, 2),
                reason=f"WickPos={close_pos:.2f} ATRpct={current_atr_pct:.2f}"
            )]
        return []

    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()


if __name__ == "__main__":
    np.random.seed(42)
    n = 300
    returns = np.random.normal(0.0001, 0.02, n)
    prices = 50500 * np.exp(np.cumsum(returns))
    test_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices, 'volume': np.random.uniform(100, 1000, n)
    })
    strategy = LowerWickAbsorptionStrategy()
    signals = strategy.generate_signals(test_data)
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%} | Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f} | {sig.reason}")
