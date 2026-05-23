"""
crypto_adx_pullback_sortino_guard_v1
====================================

Trend-resume pullback entries gated by rolling Sortino quality.
Targets smoother risk-adjusted returns than raw ADX pullback.
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


class CryptoAdxPullbackSortinoGuardStrategy:
    """ADX pullback with downside-volatility quality gating."""

    def __init__(self, params: Optional[Dict] = None):
        self.p = params or {}
        self.adx_period = self.p.get("adx_period", 14)
        self.adx_min = self.p.get("adx_min", 20.0)
        self.ema_fast = self.p.get("ema_fast", 21)
        self.ema_slow = self.p.get("ema_slow", 55)
        self.rsi_period = self.p.get("rsi_period", 14)
        self.rsi_buy_max = self.p.get("rsi_buy_max", 45)
        self.rsi_sell_min = self.p.get("rsi_sell_min", 55)
        self.sortino_window = self.p.get("sortino_window", 48)
        self.sortino_min = self.p.get("sortino_min", 0.4)
        self.pullback_atr = self.p.get("pullback_atr", 0.8)
        self.atr_period = self.p.get("atr_period", 14)
        self.tp_atr = self.p.get("tp_atr", 2.4)
        self.sl_atr = self.p.get("sl_atr", 1.3)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = max(self.ema_slow, self.sortino_window, self.adx_period) + 12
        if data is None or len(data) < min_len:
            return []

        close = data["close"].astype(float)
        ema_f = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_s = close.ewm(span=self.ema_slow, adjust=False).mean()
        atr = self._atr(data, self.atr_period)
        adx = self._adx(data, self.adx_period)
        rsi = self._rsi(close, self.rsi_period)
        sortino = self._sortino(close.pct_change().fillna(0.0), self.sortino_window)

        current_price = float(close.iloc[-1])
        current_atr = float(atr.iloc[-1])
        if np.isnan(current_atr) or current_atr <= 0:
            return []

        trend_up = ema_f.iloc[-1] > ema_s.iloc[-1]
        trend_down = ema_f.iloc[-1] < ema_s.iloc[-1]
        strong_trend = float(adx.iloc[-1]) >= self.adx_min
        pullback_distance = abs(current_price - float(ema_f.iloc[-1])) / current_atr
        in_pullback_zone = pullback_distance <= self.pullback_atr
        srt = float(sortino.iloc[-1]) if not np.isnan(sortino.iloc[-1]) else 0.0

        signals: List[Signal] = []
        if (
            strong_trend
            and trend_up
            and in_pullback_zone
            and float(rsi.iloc[-1]) <= self.rsi_buy_max
            and srt >= self.sortino_min
        ):
            confidence = min(0.95, 0.58 + min(srt / 3.0, 0.22) + min(float(adx.iloc[-1]) / 100.0, 0.15))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price + current_atr * self.tp_atr, 2),
                    stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                    reason=f"ADX={adx.iloc[-1]:.1f} Sortino={srt:.2f} pullbackATR={pullback_distance:.2f}",
                )
            )
        elif (
            strong_trend
            and trend_down
            and in_pullback_zone
            and float(rsi.iloc[-1]) >= self.rsi_sell_min
            and srt <= -self.sortino_min
        ):
            confidence = min(0.95, 0.58 + min(abs(srt) / 3.0, 0.22) + min(float(adx.iloc[-1]) / 100.0, 0.15))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price - current_atr * self.tp_atr, 2),
                    stop_loss=round(current_price + current_atr * self.sl_atr, 2),
                    reason=f"ADX={adx.iloc[-1]:.1f} Sortino={srt:.2f} pullbackATR={pullback_distance:.2f}",
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

    @staticmethod
    def _adx(data: pd.DataFrame, period: int) -> pd.Series:
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        close = data["close"].astype(float)
        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        tr = pd.concat(
            [(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(period, min_periods=1).mean().replace(0, np.nan)
        plus_di = 100 * pd.Series(plus_dm, index=data.index).rolling(period, min_periods=1).mean() / atr
        minus_di = 100 * pd.Series(minus_dm, index=data.index).rolling(period, min_periods=1).mean() / atr
        dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)).fillna(0.0)
        return dx.rolling(period, min_periods=1).mean()

    @staticmethod
    def _sortino(rets: pd.Series, window: int) -> pd.Series:
        mean_r = rets.rolling(window, min_periods=5).mean()
        downside = rets.where(rets < 0, 0.0)
        downside_dev = np.sqrt((downside.pow(2)).rolling(window, min_periods=5).mean()).replace(0, np.nan)
        return (mean_r / downside_dev) * np.sqrt(window)

