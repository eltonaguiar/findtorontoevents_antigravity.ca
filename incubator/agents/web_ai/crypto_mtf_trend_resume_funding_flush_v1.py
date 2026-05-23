"""
crypto_mtf_trend_resume_funding_flush_v1
========================================

Multi-timeframe trend resume:
- 4h defines dominant trend
- 1h waits for funding flush + pullback alignment
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class CryptoMtfTrendResumeFundingFlushStrategy:
    """Uses 4h trend context with 1h execution timing."""

    def __init__(self, params: Optional[Dict] = None):
        self.p = params or {}
        self.trend_fast_4h = self.p.get("trend_fast_4h", 50)
        self.trend_slow_4h = self.p.get("trend_slow_4h", 200)
        self.pullback_ema_1h = self.p.get("pullback_ema_1h", 20)
        self.rsi_period_1h = self.p.get("rsi_period_1h", 14)
        self.rsi_pullback_buy = self.p.get("rsi_pullback_buy", 42)
        self.rsi_pullback_sell = self.p.get("rsi_pullback_sell", 58)
        self.funding_flush = self.p.get("funding_flush", 0.0028)
        self.atr_period = self.p.get("atr_period", 14)
        self.tp_atr = self.p.get("tp_atr", 2.5)
        self.sl_atr = self.p.get("sl_atr", 1.35)

    def generate_signals(
        self,
        data_1h: pd.DataFrame,
        data_4h: pd.DataFrame,
        funding_rate: float,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        min_1h = self.pullback_ema_1h + self.rsi_period_1h + 10
        min_4h = self.trend_slow_4h + 5
        if (
            data_1h is None
            or data_4h is None
            or len(data_1h) < min_1h
            or len(data_4h) < min_4h
        ):
            return []

        c1 = data_1h["close"].astype(float)
        c4 = data_4h["close"].astype(float)
        ema4_fast = c4.ewm(span=self.trend_fast_4h, adjust=False).mean()
        ema4_slow = c4.ewm(span=self.trend_slow_4h, adjust=False).mean()
        trend_up = ema4_fast.iloc[-1] > ema4_slow.iloc[-1]
        trend_down = ema4_fast.iloc[-1] < ema4_slow.iloc[-1]

        ema1 = c1.ewm(span=self.pullback_ema_1h, adjust=False).mean()
        rsi1 = self._rsi(c1, self.rsi_period_1h)
        atr1 = self._atr(data_1h, self.atr_period)

        curr_price = float(c1.iloc[-1])
        curr_atr = float(atr1.iloc[-1])
        if np.isnan(curr_atr) or curr_atr <= 0:
            return []

        fr = float(0.0 if funding_rate is None else funding_rate)
        pullback_dist = abs(curr_price - float(ema1.iloc[-1])) / max(curr_atr, 1e-9)
        in_pullback = pullback_dist <= 1.0

        signals: List[Signal] = []
        if trend_up and in_pullback and fr <= -self.funding_flush and float(rsi1.iloc[-1]) <= self.rsi_pullback_buy:
            confidence = min(0.94, 0.60 + min(abs(fr) * 30, 0.2) + min((self.rsi_pullback_buy - float(rsi1.iloc[-1])) / 40, 0.12))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(curr_price, 2),
                    take_profit=round(curr_price + curr_atr * self.tp_atr, 2),
                    stop_loss=round(curr_price - curr_atr * self.sl_atr, 2),
                    reason=f"4hTrendUP fundingFlush={fr:.4%} RSI1h={rsi1.iloc[-1]:.1f}",
                )
            )
        elif trend_down and in_pullback and fr >= self.funding_flush and float(rsi1.iloc[-1]) >= self.rsi_pullback_sell:
            confidence = min(0.94, 0.60 + min(abs(fr) * 30, 0.2) + min((float(rsi1.iloc[-1]) - self.rsi_pullback_sell) / 40, 0.12))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(curr_price, 2),
                    take_profit=round(curr_price - curr_atr * self.tp_atr, 2),
                    stop_loss=round(curr_price + curr_atr * self.sl_atr, 2),
                    reason=f"4hTrendDN fundingFlush={fr:.4%} RSI1h={rsi1.iloc[-1]:.1f}",
                )
            )
        return signals

    @staticmethod
    def _rsi(prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gains = delta.clip(lower=0)
        losses = (-delta).clip(lower=0)
        rs = gains.rolling(period, min_periods=1).mean() / losses.rolling(period, min_periods=1).mean().replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]
        tr = pd.concat(
            [(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()

