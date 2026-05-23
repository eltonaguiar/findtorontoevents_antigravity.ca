"""
MeanReversionZScore - Baby Strat
==================================

Created by: Claude Opus
Date: 2026-02-27

Strategy Logic:
- Computes z-score of close price relative to its rolling mean
- Entry at extreme z-scores (±2σ) with mean reversion expectation
- Filters: volume must be declining (exhaustion), RSI confirms extreme

Unique Value Proposition:
Pure statistical mean reversion based on z-score — the most mathematically grounded
approach. The volume-declining filter ensures we're buying into exhaustion (not catching
a falling knife with rising sell volume). Existing Kalman strat uses Kalman filter;
this uses classical z-score which is simpler, more robust, and has clearer statistical
properties.
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


class MeanReversionZScoreStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.zscore_period = self.params.get('zscore_period', 20)
        self.zscore_entry = self.params.get('zscore_entry', 2.0)
        self.zscore_extreme = self.params.get('zscore_extreme', 3.0)
        self.volume_decline_bars = self.params.get('volume_decline_bars', 3)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.zscore_period, self.rsi_period, self.atr_period) + self.volume_decline_bars + 10
        if len(data) < min_bars:
            return []

        close = data['close']
        volume = data['volume']

        # Z-Score
        rolling_mean = close.rolling(self.zscore_period).mean()
        rolling_std = close.rolling(self.zscore_period).std()
        zscore = (close - rolling_mean) / (rolling_std + 1e-10)

        # RSI
        rsi = self._rsi(close, self.rsi_period)

        # Volume declining
        vol_declining = True
        for i in range(1, self.volume_decline_bars + 1):
            if volume.iloc[-i] >= volume.iloc[-i-1]:
                vol_declining = False
                break

        atr = self._atr(data, self.atr_period)
        current_price = close.iloc[-1]
        current_atr = atr.iloc[-1]
        current_zscore = zscore.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_mean = rolling_mean.iloc[-1]

        if any(np.isnan(v) for v in [current_atr, current_zscore, current_rsi, current_mean]):
            return []
        if current_atr <= 0:
            return []

        signals = []

        # Bullish: extreme negative z-score + RSI oversold + volume declining
        if current_zscore <= -self.zscore_entry and current_rsi < 35:
            if vol_declining or current_zscore <= -self.zscore_extreme:
                strength = min(abs(current_zscore) / self.zscore_extreme, 1.0)
                confidence = min(0.55 + strength * 0.35, 0.95)
                # TP targets the mean
                tp_to_mean = current_mean - current_price
                tp = current_price + max(tp_to_mean * 0.6, current_atr * self.tp_atr_mult)
                sl = current_price - current_atr * self.sl_atr_mult
                signals.append(Signal(
                    symbol=symbol, direction="BUY", confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2), stop_loss=round(sl, 2),
                    reason=f"Z-score={current_zscore:.2f}, RSI={current_rsi:.0f}, vol declining={vol_declining}"
                ))

        # Bearish: extreme positive z-score + RSI overbought + volume declining
        elif current_zscore >= self.zscore_entry and current_rsi > 65:
            if vol_declining or current_zscore >= self.zscore_extreme:
                strength = min(abs(current_zscore) / self.zscore_extreme, 1.0)
                confidence = min(0.55 + strength * 0.35, 0.95)
                tp_to_mean = current_price - current_mean
                tp = current_price - max(tp_to_mean * 0.6, current_atr * self.tp_atr_mult)
                sl = current_price + current_atr * self.sl_atr_mult
                signals.append(Signal(
                    symbol=symbol, direction="SELL", confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2), stop_loss=round(sl, 2),
                    reason=f"Z-score={current_zscore:.2f}, RSI={current_rsi:.0f}, vol declining={vol_declining}"
                ))

        return signals

    def _rsi(self, prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / (loss + 1e-10)
        return 100 - (100 / (1 + rs))

    def _atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift())
        tr3 = abs(data['low'] - data['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean()
