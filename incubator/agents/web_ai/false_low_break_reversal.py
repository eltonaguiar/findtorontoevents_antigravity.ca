"""
FalseLowBreakReversal - Baby Strat
====================================

Created by: web_ai
Date: 2026-02-26

Strategy Logic:
- Entry when: Low breaks 25-period low (sweep) AND close > prev close (recovery)
- Exit when: TP = 2.3 x ATR, SL = 1.3 x ATR

Unique Value Proposition:
False-break reversal (sweep + recovery) is completely missing from inventory.
Pure microstructure/orderflow play.

Expected Regime: Ranging or bottoming markets with stop-hunting wicks.
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


class FalseLowBreakReversalStrategy:
    """False low break + immediate recovery."""

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get('lookback', 25)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr = self.params.get('tp_atr', 2.3)
        self.sl_atr = self.params.get('sl_atr', 1.3)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = self.lookback + 10
        if len(data) < min_len:
            return []

        rolling_low = data['low'].rolling(self.lookback).min()
        atr = self._calculate_atr(data)

        current_low = data['low'].iloc[-1]
        current_close = data['close'].iloc[-1]
        prev_close = data['close'].iloc[-2]
        current_atr = atr.iloc[-1]
        recent_low = rolling_low.iloc[-1]

        is_sweep = current_low < recent_low
        is_recovery = current_close > prev_close

        if is_sweep and is_recovery:
            return [Signal(
                symbol=symbol, direction="BUY",
                confidence=0.80,
                entry_price=round(current_close, 2),
                take_profit=round(current_close + current_atr * self.tp_atr, 2),
                stop_loss=round(current_close - current_atr * self.sl_atr, 2),
                reason=f"SweepLow + Recov"
            )]
        return []

    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()


if __name__ == "__main__":
    np.random.seed(42)
    n = 300
    returns = np.random.normal(-0.0002, 0.022, n)
    prices = 49800 * np.exp(np.cumsum(returns))
    test_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices, 'volume': np.random.uniform(100, 1000, n)
    })
    strategy = FalseLowBreakReversalStrategy()
    signals = strategy.generate_signals(test_data)
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%} | Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f} | {sig.reason}")
