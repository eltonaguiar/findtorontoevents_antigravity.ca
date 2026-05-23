"""
crypto_fng_funding_regime_router_v1
===================================

Regime router using sentiment proxy + funding state:
- Contrarian mode in fear/greed extremes with aligned funding
- Trend mode in neutral states
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


class CryptoFngFundingRegimeRouterStrategy:
    """Switches between contrarian and trend-following playbooks."""

    def __init__(self, params: Optional[Dict] = None):
        self.p = params or {}
        self.proxy_window = self.p.get("proxy_window", 48)
        self.fear_level = self.p.get("fear_level", 35.0)
        self.greed_level = self.p.get("greed_level", 65.0)
        self.funding_extreme = self.p.get("funding_extreme", 0.0025)
        self.rsi_period = self.p.get("rsi_period", 14)
        self.ema_fast = self.p.get("ema_fast", 21)
        self.ema_slow = self.p.get("ema_slow", 55)
        self.adx_period = self.p.get("adx_period", 14)
        self.atr_period = self.p.get("atr_period", 14)
        self.tp_atr = self.p.get("tp_atr", 2.2)
        self.sl_atr = self.p.get("sl_atr", 1.3)

    def generate_signals(
        self,
        data: pd.DataFrame,
        funding_rate: float,
        social_data: pd.Series,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        min_len = max(self.ema_slow, self.proxy_window, self.adx_period) + 12
        if data is None or social_data is None or len(data) < min_len or len(social_data) < min_len:
            return []

        close = data["close"].astype(float)
        atr = self._atr(data, self.atr_period)
        ema_f = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_s = close.ewm(span=self.ema_slow, adjust=False).mean()
        rsi = self._rsi(close, self.rsi_period)
        adx = self._adx(data, self.adx_period)

        current_price = float(close.iloc[-1])
        current_atr = float(atr.iloc[-1])
        if np.isnan(current_atr) or current_atr <= 0:
            return []

        social = pd.Series(social_data).astype(float).reset_index(drop=True)
        z = (social - social.rolling(self.proxy_window).mean()) / social.rolling(self.proxy_window).std(ddof=0).replace(0, np.nan)
        proxy_fng = float(np.clip(50 + 18 * z.iloc[-1], 0, 100)) if not np.isnan(z.iloc[-1]) else 50.0

        fr = float(0.0 if funding_rate is None else funding_rate)
        current_rsi = float(rsi.iloc[-1])

        contrarian_fear = proxy_fng <= self.fear_level and fr <= -self.funding_extreme and current_rsi < 45
        contrarian_greed = proxy_fng >= self.greed_level and fr >= self.funding_extreme and current_rsi > 55
        neutral = self.fear_level < proxy_fng < self.greed_level

        trend_up = ema_f.iloc[-1] > ema_s.iloc[-1] and adx.iloc[-1] >= 18
        trend_down = ema_f.iloc[-1] < ema_s.iloc[-1] and adx.iloc[-1] >= 18

        signals: List[Signal] = []
        if contrarian_fear:
            confidence = min(0.93, 0.62 + (self.fear_level - proxy_fng) / 100 + abs(fr) * 35)
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price + current_atr * self.tp_atr, 2),
                    stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                    reason=f"ContrarianFear fng={proxy_fng:.1f} funding={fr:.4%}",
                )
            )
        elif contrarian_greed:
            confidence = min(0.93, 0.62 + (proxy_fng - self.greed_level) / 100 + abs(fr) * 35)
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price - current_atr * self.tp_atr, 2),
                    stop_loss=round(current_price + current_atr * self.sl_atr, 2),
                    reason=f"ContrarianGreed fng={proxy_fng:.1f} funding={fr:.4%}",
                )
            )
        elif neutral and trend_up and current_rsi > 50:
            confidence = min(0.9, 0.56 + min(float(adx.iloc[-1]) / 100, 0.2))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price + current_atr * (self.tp_atr + 0.3), 2),
                    stop_loss=round(current_price - current_atr * (self.sl_atr + 0.2), 2),
                    reason=f"TrendModeUP fng={proxy_fng:.1f} adx={adx.iloc[-1]:.1f}",
                )
            )
        elif neutral and trend_down and current_rsi < 50:
            confidence = min(0.9, 0.56 + min(float(adx.iloc[-1]) / 100, 0.2))
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price - current_atr * (self.tp_atr + 0.3), 2),
                    stop_loss=round(current_price + current_atr * (self.sl_atr + 0.2), 2),
                    reason=f"TrendModeDN fng={proxy_fng:.1f} adx={adx.iloc[-1]:.1f}",
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

