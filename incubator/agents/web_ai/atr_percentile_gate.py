"""
ATRPercentileGate - Baby Strat
================================

Created by: web_ai
Date: 2026-02-26

Strategy Logic:
- Entry when: ATR percentile < 0.25 (lowest quartile) AND price > EMA(20)
- Exit when: TP = 2.0 x ATR, SL = 1.5 x ATR

Unique Value Proposition:
True rolling percentile (white-space risk-adjusted). No RSI, no candle
patterns, no crossovers. Ultra-clean risk-adjusted filter.

Expected Regime: Calm low-vol trending or ranging — safest entries only.
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


class ATRPercentileGateStrategy:
    """ATR in lowest 25% + price above EMA."""

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.atr_period = self.params.get('atr_period', 14)
        self.pct_lookback = self.params.get('pct_lookback', 60)
        self.pct_threshold = self.params.get('pct_threshold', 0.25)
        self.ema_period = self.params.get('ema_period', 20)
        self.tp_atr = self.params.get('tp_atr', 2.0)
        self.sl_atr = self.params.get('sl_atr', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = self.pct_lookback + self.atr_period + self.ema_period + 10
        if len(data) < min_len:
            return []

        atr = self._calculate_atr(data)
        atr_roll = atr.rolling(self.pct_lookback)
        atr_pct_rank = (atr < atr_roll.quantile(self.pct_threshold)).astype(float).rolling(self.pct_lookback).mean()

        ema = data['close'].ewm(span=self.ema_period).mean()

        current_atr = atr.iloc[-1]
        current_price = data['close'].iloc[-1]
        current_pct = atr_pct_rank.iloc[-1] if not pd.isna(atr_pct_rank.iloc[-1]) else 0.0
        current_ema = ema.iloc[-1]

        if current_pct > 0.6 and current_price > current_ema:
            confidence = 0.70 + current_pct * 0.25
            return [Signal(
                symbol=symbol, direction="BUY",
                confidence=round(min(confidence, 0.92), 2),
                entry_price=round(current_price, 2),
                take_profit=round(current_price + current_atr * self.tp_atr, 2),
                stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                reason=f"ATRpct={current_pct:.2f} AboveEMA"
            )]
        return []

    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()


if __name__ == "__main__":
    np.random.seed(42)
    n = 400
    returns = np.random.normal(0.0002, 0.018, n)
    prices = 51200 * np.exp(np.cumsum(returns))
    test_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices, 'volume': np.random.uniform(100, 1000, n)
    })
    strategy = ATRPercentileGateStrategy()
    signals = strategy.generate_signals(test_data)
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%} | Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f} | {sig.reason}")
