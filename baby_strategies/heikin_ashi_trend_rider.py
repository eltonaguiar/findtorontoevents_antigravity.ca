"""
HeikinAshiTrendRider - Baby Strat
==================================

Created by: Claude Opus
Date: 2026-02-27

Strategy Logic:
- Converts price to Heikin-Ashi candles to filter noise
- Entry on HA trend confirmation (3+ consecutive same-color candles) + ADX strength
- Exit when HA candle reverses color or TP/SL hit

Unique Value Proposition:
Heikin-Ashi smooths noise better than MA crossovers. Combined with ADX trend
strength filter, this avoids whipsaws in ranging markets. No existing baby strat
uses HA candle patterns.
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


class HeikinAshiTrendRiderStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ha_consecutive = self.params.get('ha_consecutive', 3)
        self.adx_period = self.params.get('adx_period', 14)
        self.adx_threshold = self.params.get('adx_threshold', 25)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 3.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.adx_period * 2, self.atr_period, 30) + self.ha_consecutive
        if len(data) < min_bars:
            return []

        ha = self._heikin_ashi(data)
        adx = self._adx(data, self.adx_period)
        atr = self._atr(data, self.atr_period)

        current_price = data['close'].iloc[-1]
        current_adx = adx.iloc[-1]
        current_atr = atr.iloc[-1]

        if np.isnan(current_adx) or np.isnan(current_atr) or current_atr <= 0:
            return []

        # Check HA candle colors (True = bullish)
        ha_bullish = ha['close'] > ha['open']
        recent = ha_bullish.iloc[-(self.ha_consecutive + 1):]

        signals = []

        if current_adx >= self.adx_threshold:
            # All recent HA candles bullish
            if recent.iloc[-self.ha_consecutive:].all() and not recent.iloc[0]:
                # Trend just started (prev was bearish)
                confidence = min(0.5 + (current_adx - self.adx_threshold) / 50, 0.95)
                tp = current_price + current_atr * self.tp_atr_mult
                sl = current_price - current_atr * self.sl_atr_mult
                signals.append(Signal(
                    symbol=symbol, direction="BUY", confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2), stop_loss=round(sl, 2),
                    reason=f"HA bullish trend ({self.ha_consecutive} bars), ADX={current_adx:.1f}"
                ))

            # All recent HA candles bearish
            elif not recent.iloc[-self.ha_consecutive:].any() and recent.iloc[0]:
                confidence = min(0.5 + (current_adx - self.adx_threshold) / 50, 0.95)
                tp = current_price - current_atr * self.tp_atr_mult
                sl = current_price + current_atr * self.sl_atr_mult
                signals.append(Signal(
                    symbol=symbol, direction="SELL", confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2), stop_loss=round(sl, 2),
                    reason=f"HA bearish trend ({self.ha_consecutive} bars), ADX={current_adx:.1f}"
                ))

        return signals

    def _heikin_ashi(self, data: pd.DataFrame) -> pd.DataFrame:
        ha_close = (data['open'].values + data['high'].values + data['low'].values + data['close'].values) / 4
        ha_open = np.empty_like(ha_close)
        ha_open[0] = (data['open'].values[0] + data['close'].values[0]) / 2
        for i in range(1, len(ha_close)):
            ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2
        ha = pd.DataFrame({
            'open': ha_open, 'close': ha_close,
            'high': np.maximum(np.maximum(data['high'].values, ha_open), ha_close),
            'low': np.minimum(np.minimum(data['low'].values, ha_open), ha_close),
        }, index=data.index)
        return ha

    def _adx(self, data: pd.DataFrame, period: int) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        plus_dm = high.diff().clip(lower=0)
        minus_dm = (-low.diff()).clip(lower=0)
        # Zero out where the other is larger
        plus_dm[plus_dm < minus_dm] = 0
        minus_dm[minus_dm < plus_dm] = 0
        tr = self._true_range(data)
        atr = tr.rolling(window=period, min_periods=1).mean()
        plus_di = 100 * (plus_dm.rolling(window=period, min_periods=1).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period, min_periods=1).mean() / atr)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.rolling(window=period, min_periods=1).mean()
        return adx

    def _atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        tr = self._true_range(data)
        return tr.rolling(window=period, min_periods=1).mean()

    def _true_range(self, data: pd.DataFrame) -> pd.Series:
        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift())
        tr3 = abs(data['low'] - data['close'].shift())
        return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
