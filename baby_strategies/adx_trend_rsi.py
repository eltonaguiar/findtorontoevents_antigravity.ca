"""
ADXTrendStrengthRSIStrategy - Baby Strat
=======================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: RSI signals in strong trending markets (ADX filter)
- Exit when: TP/SL hit or trend weakens
- Risk management: ATR-based SL/TP

Unique Value Proposition:
Combines RSI mean reversion with ADX trend strength filter to trade with the trend.
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


class ADXTrendStrengthRSIStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.adx_period = self.params.get('adx_period', 14)
        self.adx_threshold = self.params.get('adx_threshold', 25)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_oversold = self.params.get('rsi_oversold', 30)
        self.rsi_overbought = self.params.get('rsi_overbought', 70)
        self.ema_trend = self.params.get('ema_trend', 50)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.adx_period, self.rsi_period, self.ema_trend, self.atr_period) + 10:
            return []

        # Calculate indicators
        adx, di_plus, di_minus = self._calculate_adx(data, self.adx_period)
        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        ema_trend = data['close'].ewm(span=self.ema_trend).mean()
        trend_slope = (ema_trend - ema_trend.shift(1)) / ema_trend.shift(1)
        atr = self._calculate_atr(data, self.atr_period)

        current_price = data['close'].iloc[-1]
        current_adx = adx.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_trend = trend_slope.iloc[-1]
        current_atr = atr.iloc[-1]

        signals = []

        # Strong uptrend + RSI oversold
        if current_adx > self.adx_threshold and current_trend > 0 and current_rsi < self.rsi_oversold:
            confidence = (self.rsi_oversold - current_rsi) / self.rsi_oversold
            confidence = confidence * (current_adx / 50)  # Boost with trend strength
            confidence = min(confidence, 0.95)

            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"ADX strong uptrend ({current_adx:.1f}) + RSI oversold ({current_rsi:.1f})"
            ))

        # Strong downtrend + RSI overbought
        elif current_adx > self.adx_threshold and current_trend < 0 and current_rsi > self.rsi_overbought:
            confidence = (current_rsi - self.rsi_overbought) / (100 - self.rsi_overbought)
            confidence = confidence * (current_adx / 50)
            confidence = min(confidence, 0.95)

            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = current_price + (current_atr * self.sl_atr_mult)

            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"ADX strong downtrend ({current_adx:.1f}) + RSI overbought ({current_rsi:.1f})"
            ))

        return signals

    def _calculate_adx(self, data: pd.DataFrame, period: int = 14):
        high = data['high']
        low = data['low']
        close = data['close']

        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        # Calculate Directional Movement
        dm_plus = pd.Series(np.where((high - high.shift()) > (low.shift() - low), 
                                   np.maximum(high - high.shift(), 0), 0), index=data.index)
        dm_minus = pd.Series(np.where((low.shift() - low) > (high - high.shift()), 
                                    np.maximum(low.shift() - low, 0), 0), index=data.index)

        # Calculate Directional Indicators
        di_plus = 100 * (dm_plus.rolling(window=period).mean() / atr)
        di_minus = 100 * (dm_minus.rolling(window=period).mean() / atr)

        # Calculate ADX
        dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
        adx = dx.rolling(window=period).mean()

        return adx, di_plus, di_minus

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = (-delta.where(delta < 0, 0))
        avg_gains = gains.rolling(window=period, min_periods=1).mean()
        avg_losses = losses.rolling(window=period, min_periods=1).mean()
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        return rsi

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
