"""
MultiPeriodRSIConfluence - Baby Strat
======================================

Created by: web_ai
Date: 2026-02-26

Strategy Logic:
- Entry when: RSI14 < 35 AND RSI50 < 40 (dual-period alignment)
- Exit when: TP = 2.0 x ATR, SL = 1.5 x ATR
- Risk management: Dual-timeframe RSI confirmation only

Unique Value Proposition:
Uses different RSI lengths as 1h/4h proxy. Zero overlap with existing
single-RSI bots — requires BOTH short and long momentum oversold.

Expected Regime: Deep ranging or bottoming markets.
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


class MultiPeriodRSIConfluenceStrategy:
    """Short + long RSI alignment (multi-TF proxy)."""

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rsi_short = self.params.get('rsi_short', 14)
        self.rsi_long = self.params.get('rsi_long', 50)
        self.rsi_short_th = self.params.get('rsi_short_th', 35)
        self.rsi_long_th = self.params.get('rsi_long_th', 40)
        self.atr_period = self.params.get('atr_period', 14)
        # R:R widened 2026-03-16: was 2.0, now 3.2 (target R:R >= 2.0; was 1.33, now 2.13)
        self.tp_atr = self.params.get('tp_atr', 3.2)
        self.sl_atr = self.params.get('sl_atr', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = self.rsi_long + 20
        if len(data) < min_len:
            return []

        rsi_s = self._calculate_rsi(data['close'], self.rsi_short)
        rsi_l = self._calculate_rsi(data['close'], self.rsi_long)
        atr = self._calculate_atr(data)

        current_rsi_s = rsi_s.iloc[-1]
        current_rsi_l = rsi_l.iloc[-1]
        current_price = data['close'].iloc[-1]
        current_atr = atr.iloc[-1]

        if current_rsi_s < self.rsi_short_th and current_rsi_l < self.rsi_long_th:
            conf = 0.6 + (40 - current_rsi_l) / 40 * 0.3
            return [Signal(
                symbol=symbol, direction="BUY",
                confidence=round(min(conf, 0.9), 2),
                entry_price=round(current_price, 2),
                take_profit=round(current_price + current_atr * self.tp_atr, 2),
                stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                reason=f"RSI14={current_rsi_s:.1f} RSI50={current_rsi_l:.1f}"
            )]
        return []

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()


if __name__ == "__main__":
    np.random.seed(42)
    n = 400
    returns = np.random.normal(-0.0003, 0.02, n)
    prices = 51000 * np.exp(np.cumsum(returns))
    test_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices, 'volume': np.random.uniform(100, 1000, n)
    })
    strategy = MultiPeriodRSIConfluenceStrategy()
    signals = strategy.generate_signals(test_data)
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%} | Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f} | {sig.reason}")
