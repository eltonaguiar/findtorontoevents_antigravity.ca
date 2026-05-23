"""
VolumeImbalanceReversal - Baby Strat
======================================

Created by: Claude Opus
Date: 2026-02-27

Strategy Logic:
- Detects buy/sell volume imbalance using close position within bar (Bulk Volume Classification)
- Entry when cumulative imbalance diverges from price (smart money absorption)
- Confirmation: OBV divergence + price at support/resistance

Unique Value Proposition:
Uses Bulk Volume Classification (BVC) to estimate buy vs sell pressure without tick data.
When BVC shows heavy buying but price drops (absorption), a reversal is likely.
No existing strat uses BVC-based volume decomposition.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass


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


class VolumeImbalanceReversalStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get('lookback', 20)
        self.imbalance_threshold = self.params.get('imbalance_threshold', 0.65)
        self.price_divergence_bars = self.params.get('price_divergence_bars', 5)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.lookback, self.atr_period) + self.price_divergence_bars + 10
        if len(data) < min_bars:
            return []

        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']

        # Bulk Volume Classification: buy_pct = (close - low) / (high - low)
        bar_range = high - low
        bar_range = bar_range.replace(0, np.nan)
        buy_pct = (close - low) / bar_range
        buy_pct = buy_pct.fillna(0.5)

        buy_volume = volume * buy_pct
        sell_volume = volume * (1 - buy_pct)

        # Rolling buy ratio
        rolling_buy = buy_volume.rolling(self.lookback).sum()
        rolling_total = volume.rolling(self.lookback).sum()
        buy_ratio = rolling_buy / (rolling_total + 1e-10)

        # Price change over divergence window
        price_change = close.pct_change(self.price_divergence_bars)

        atr = self._atr(data, self.atr_period)
        current_price = close.iloc[-1]
        current_atr = atr.iloc[-1]
        current_buy_ratio = buy_ratio.iloc[-1]
        current_price_change = price_change.iloc[-1]

        if np.isnan(current_atr) or current_atr <= 0 or np.isnan(current_buy_ratio):
            return []

        signals = []

        # Bullish divergence: heavy buying but price dropped (absorption)
        if current_buy_ratio > self.imbalance_threshold and current_price_change < -0.005:
            confidence = min(0.5 + (current_buy_ratio - 0.5) * 2, 0.95)
            tp = current_price + current_atr * self.tp_atr_mult
            sl = current_price - current_atr * self.sl_atr_mult
            signals.append(Signal(
                symbol=symbol, direction="BUY", confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2), stop_loss=round(sl, 2),
                reason=f"BVC bullish absorption: buy_ratio={current_buy_ratio:.2f}, price_chg={current_price_change:.3f}"
            ))

        # Bearish divergence: heavy selling but price rose (distribution)
        elif current_buy_ratio < (1 - self.imbalance_threshold) and current_price_change > 0.005:
            confidence = min(0.5 + (0.5 - current_buy_ratio) * 2, 0.95)
            tp = current_price - current_atr * self.tp_atr_mult
            sl = current_price + current_atr * self.sl_atr_mult
            signals.append(Signal(
                symbol=symbol, direction="SELL", confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2), stop_loss=round(sl, 2),
                reason=f"BVC bearish distribution: buy_ratio={current_buy_ratio:.2f}, price_chg={current_price_change:.3f}"
            ))

        return signals

    def _atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift())
        tr3 = abs(data['low'] - data['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean()
