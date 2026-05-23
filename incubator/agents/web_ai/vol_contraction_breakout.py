"""
VolContractionBreakout - Baby Strat
====================================

Created by: web_ai
Date: 2026-02-26

Strategy Logic:
- Entry when: ATR ratio (current / 50-period avg) < 0.75 AND close breaks 20-period high
- Exit when: TP = 2.5 x ATR, SL = 1.5 x ATR
- Risk management: Strict vol contraction gate before any breakout signal

Unique Value Proposition:
Basic breakout arena exists, but pure contraction-filtered VCP-style entry
(white-space volatility regime) is missing. No RSI, no MACD, no crossovers
— just clean vol squeeze → expansion.

Expected Regime: Low-vol → expansion (quiet consolidation → violent moves).
Crypto ranging-to-trending transitions.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class Signal:
    """A trading signal - required return type."""
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class VolContractionBreakoutStrategy:
    """Vol contraction → breakout (VCP style)."""

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.atr_period = self.params.get('atr_period', 14)
        self.regime_lookback = self.params.get('regime_lookback', 50)
        self.contraction_threshold = self.params.get('contraction_threshold', 0.75)
        self.breakout_lookback = self.params.get('breakout_lookback', 20)
        self.tp_atr = self.params.get('tp_atr', 2.5)
        self.sl_atr = self.params.get('sl_atr', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = self.regime_lookback + self.atr_period + self.breakout_lookback + 10
        if len(data) < min_len:
            return []

        atr = self._calculate_atr(data)
        atr_ma = atr.rolling(self.regime_lookback).mean()
        rolling_high = data['high'].rolling(self.breakout_lookback).max()

        current_atr = atr.iloc[-1]
        current_atr_ma = atr_ma.iloc[-1] if not pd.isna(atr_ma.iloc[-1]) else current_atr
        current_close = data['close'].iloc[-1]
        current_high = rolling_high.iloc[-1]

        ratio = current_atr / current_atr_ma if current_atr_ma > 0 else 1.0
        is_contracting = ratio < self.contraction_threshold
        is_breakout = current_close > current_high

        if is_contracting and is_breakout:
            confidence = 0.75 + (1.0 - ratio) * 0.2
            return [Signal(
                symbol=symbol, direction="BUY",
                confidence=round(min(confidence, 0.95), 2),
                entry_price=round(current_close, 2),
                take_profit=round(current_close + current_atr * self.tp_atr, 2),
                stop_loss=round(current_close - current_atr * self.sl_atr, 2),
                reason=f"ContrRatio={ratio:.2f} Break>High"
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
    prices = 52000 * np.exp(np.cumsum(returns))
    test_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices, 'volume': np.random.uniform(100, 1000, n)
    })
    strategy = VolContractionBreakoutStrategy()
    signals = strategy.generate_signals(test_data)
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%} | Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f} | {sig.reason}")
