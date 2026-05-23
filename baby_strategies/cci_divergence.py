"""
CCIDivergenceStrategy - Baby Strat
=================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: CCI shows divergence with price
- Exit when: TP/SL hit or divergence resolves
- Risk management: ATR-based SL/TP

Unique Value Proposition:
Detects bullish/bearish divergences between CCI and price for high-probability reversals.
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


class CCIDivergenceStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.cci_period = self.params.get('cci_period', 20)
        self.divergence_lookback = self.params.get('divergence_lookback', 10)
        self.oversold = self.params.get('oversold', -100)
        self.overbought = self.params.get('overbought', 100)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.cci_period, self.divergence_lookback, self.atr_period) + 10:
            return []

        # Calculate indicators
        cci = self._calculate_cci(data, self.cci_period)
        atr = self._calculate_atr(data, self.atr_period)

        current_price = data['close'].iloc[-1]
        current_cci = cci.iloc[-1]
        current_atr = atr.iloc[-1]

        # Check for divergence in recent period
        recent_prices = data['close'].iloc[-self.divergence_lookback:]
        recent_cci = cci.iloc[-self.divergence_lookback:]

        signals = []

        # Bullish divergence: price makes lower low, CCI makes higher low
        if self._check_bullish_divergence(recent_prices, recent_cci):
            confidence = min(abs(current_cci - self.oversold) / 100, 0.95)

            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"CCI bullish divergence detected (CCI: {current_cci:.1f})"
            ))

        # Bearish divergence: price makes higher high, CCI makes lower high
        elif self._check_bearish_divergence(recent_prices, recent_cci):
            confidence = min(abs(current_cci - self.overbought) / 100, 0.95)

            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = current_price + (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"CCI bearish divergence detected (CCI: {current_cci:.1f})"
            ))

        return signals

    def _calculate_cci(self, data: pd.DataFrame, period: int = 20) -> pd.Series:
        typical_price = (data['high'] + data['low'] + data['close']) / 3
        sma = typical_price.rolling(window=period).mean()
        mad = typical_price.rolling(window=period).apply(lambda x: np.mean(np.abs(x - x.mean())))
        cci = (typical_price - sma) / (0.015 * mad)
        return cci

    def _check_bullish_divergence(self, prices: pd.Series, cci: pd.Series) -> bool:
        """Check if price makes lower low but CCI makes higher low"""
        if len(prices) < 4:
            return False

        # Find local minima
        price_mins = self._find_local_mins(prices)
        cci_mins = self._find_local_mins(cci)

        if len(price_mins) >= 2 and len(cci_mins) >= 2:
            # Compare last two minima
            last_price_min = prices.iloc[price_mins[-1]]
            prev_price_min = prices.iloc[price_mins[-2]]
            last_cci_min = cci.iloc[cci_mins[-1]]
            prev_cci_min = cci.iloc[cci_mins[-2]]

            return last_price_min < prev_price_min and last_cci_min > prev_cci_min

        return False

    def _check_bearish_divergence(self, prices: pd.Series, cci: pd.Series) -> bool:
        """Check if price makes higher high but CCI makes lower high"""
        if len(prices) < 4:
            return False

        # Find local maxima
        price_maxs = self._find_local_maxs(prices)
        cci_maxs = self._find_local_maxs(cci)

        if len(price_maxs) >= 2 and len(cci_maxs) >= 2:
            # Compare last two maxima
            last_price_max = prices.iloc[price_maxs[-1]]
            prev_price_max = prices.iloc[price_maxs[-2]]
            last_cci_max = cci.iloc[cci_maxs[-1]]
            prev_cci_max = cci.iloc[cci_maxs[-2]]

            return last_price_max > prev_price_max and last_cci_max < prev_cci_max

        return False

    def _find_local_mins(self, series: pd.Series) -> List[int]:
        mins = []
        for i in range(1, len(series) - 1):
            if series.iloc[i] < series.iloc[i-1] and series.iloc[i] < series.iloc[i+1]:
                mins.append(i)
        return mins

    def _find_local_maxs(self, series: pd.Series) -> List[int]:
        maxs = []
        for i in range(1, len(series) - 1):
            if series.iloc[i] > series.iloc[i-1] and series.iloc[i] > series.iloc[i+1]:
                maxs.append(i)
        return maxs

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
