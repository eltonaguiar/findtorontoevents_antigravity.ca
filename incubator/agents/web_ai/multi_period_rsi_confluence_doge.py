"""
MultiPeriodRSIConfluence DOGE - Baby Strat
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


class MultiPeriodRSIConfluenceDOGEStrategy:
    """Short + long RSI alignment for DOGE."""

    TARGET_PAIR = "DOGE/USDT"
    TARGET_SYMBOL = "DOGEUSDT"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rsi_short = self.params.get("rsi_short", 14)
        self.rsi_long = self.params.get("rsi_long", 50)
        self.rsi_short_th = self.params.get("rsi_short_th", 30)
        self.rsi_long_th = self.params.get("rsi_long_th", 35)
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr = self.params.get("tp_atr", 2.8)
        self.sl_atr = self.params.get("sl_atr", 1.2)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "DOGEUSDT") -> List[Signal]:
        min_len = self.rsi_long + 20
        if len(data) < min_len:
            return []
        rsi_s = self._calculate_rsi(data["close"], self.rsi_short)
        rsi_l = self._calculate_rsi(data["close"], self.rsi_long)
        atr = self._calculate_atr(data)
        current_rsi_s = rsi_s.iloc[-1]
        current_rsi_l = rsi_l.iloc[-1]
        current_price = data["close"].iloc[-1]
        current_atr = atr.iloc[-1]
        if current_rsi_s < self.rsi_short_th and current_rsi_l < self.rsi_long_th:
            conf = 0.6 + (self.rsi_long_th - current_rsi_l) / self.rsi_long_th * 0.3
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
        high, low, close = data["high"], data["low"], data["close"]
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()
