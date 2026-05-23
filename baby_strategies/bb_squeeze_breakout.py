"""
BBSqueezeBreakoutStrategy - Baby Strat
=====================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: Price breaks out of Bollinger Band squeeze
- Exit when: TP/SL hit or re-enters bands
- Risk management: ATR-based SL/TP

Unique Value Proposition:
Detects periods of low volatility (squeeze) followed by breakouts, with volume confirmation.
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


class BBSqueezeBreakoutStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.bb_period = self.params.get('bb_period', 20)
        self.bb_std = self.params.get('bb_std', 2.0)
        self.squeeze_threshold = self.params.get('squeeze_threshold', 0.8)
        self.volume_period = self.params.get('volume_period', 20)
        self.volume_mult = self.params.get('volume_mult', 1.5)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 3.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.bb_period, self.volume_period, self.atr_period) + 10:
            return []

        # Calculate indicators
        sma = data['close'].rolling(window=self.bb_period).mean()
        std = data['close'].rolling(window=self.bb_period).std()
        bb_upper = sma + (std * self.bb_std)
        bb_lower = sma - (std * self.bb_std)
        bb_width = (bb_upper - bb_lower) / sma
        bb_width_ma = bb_width.rolling(window=self.bb_period).mean()

        volume_ma = data['volume'].rolling(window=self.volume_period).mean()
        atr = self._calculate_atr(data, self.atr_period)

        current_price = data['close'].iloc[-1]
        prev_price = data['close'].iloc[-2]
        current_bb_upper = bb_upper.iloc[-1]
        current_bb_lower = bb_lower.iloc[-1]
        current_bb_width = bb_width.iloc[-1]
        current_bb_width_ma = bb_width_ma.iloc[-1]
        current_volume = data['volume'].iloc[-1]
        current_volume_ma = volume_ma.iloc[-1]
        current_atr = atr.iloc[-1]

        signals = []

        # Check for squeeze (low volatility)
        is_squeeze = current_bb_width < current_bb_width_ma * self.squeeze_threshold

        if is_squeeze and current_volume > current_volume_ma * self.volume_mult:
            # Bullish breakout
            if prev_price <= current_bb_upper and current_price > current_bb_upper:
                confidence = (current_price - current_bb_upper) / current_atr
                confidence = min(confidence, 0.95)

                tp = current_price + (current_atr * self.tp_atr_mult)
                sl = current_bb_upper - (current_atr * self.sl_atr_mult)

                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"BB upper breakout from squeeze (width: {current_bb_width:.4f})"
                ))

            # Bearish breakout
            elif prev_price >= current_bb_lower and current_price < current_bb_lower:
                confidence = (current_bb_lower - current_price) / current_atr
                confidence = min(confidence, 0.95)

                tp = current_price - (current_atr * self.tp_atr_mult)
                sl = current_bb_lower + (current_atr * self.sl_atr_mult)

                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"BB lower breakout from squeeze (width: {current_bb_width:.4f})"
                ))

        return signals

    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        high = data['high']
        low = data['low']
        close = data['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period, min_periods=1).mean()
        return atr
