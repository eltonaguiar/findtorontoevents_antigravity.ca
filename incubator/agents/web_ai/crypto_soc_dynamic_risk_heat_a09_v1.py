"""
crypto_soc_dynamic_risk_heat_a09_v1 - Social-Inspired High-Sharpe Baby Strat
====================================================

Created by: web_ai
Date: 2026-02-26
Archetype: dynamic_risk_heat

Inspired by recurring community themes:
- regime filtering and volatility-state gating
- orderflow/delta confirmation
- time-slice confluence and breakout hygiene
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional, Dict


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class CryptoSoc090DynamicRiskHeatStrategy:
    """Composite social-theme strategy: dynamic_risk_heat."""

    def __init__(self, params: Optional[Dict] = None):
        self.p = params or {}
        self.fast_ema = self.p.get('fast_ema', 16)
        self.slow_ema = self.p.get('slow_ema', 46)
        self.z_window = self.p.get('z_window', 34)
        self.breakout_window = self.p.get('breakout_window', 24)
        self.vol_window = self.p.get('vol_window', 38)
        self.atr_short = self.p.get('atr_short', 9)
        self.atr_long = self.p.get('atr_long', 42)
        self.atr_gate = self.p.get('atr_gate', 1.120)
        self.vol_ratio_gate = self.p.get('vol_ratio_gate', 1.200)
        self.tp_atr = self.p.get('tp_atr', 2.90)
        self.sl_atr = self.p.get('sl_atr', 1.30)
        self.cooldown = self.p.get('cooldown', 1)

        self.trend_w = self.p.get('trend_w', 0.2675)
        self.meanrev_w = self.p.get('meanrev_w', 0.1031)
        self.breakout_w = self.p.get('breakout_w', 0.1488)
        self.volstate_w = self.p.get('volstate_w', 0.2048)
        self.flow_w = self.p.get('flow_w', 0.1819)
        self.session_w = self.p.get('session_w', 0.0939)

        self.long_threshold = self.p.get('long_threshold', 0.460)
        self.short_threshold = self.p.get('short_threshold', 0.460)

    def generate_signals(self, data: pd.DataFrame, symbol: str = 'BTCUSDT') -> List[Signal]:
        req = {'open', 'high', 'low', 'close', 'volume'}
        if not req.issubset(set(data.columns)):
            return []

        min_len = max(self.slow_ema, self.z_window, self.breakout_window, self.vol_window, self.atr_long) + 10
        if len(data) < min_len:
            return []

        close = data['close']
        high = data['high']
        low = data['low']
        open_ = data['open']
        volume = data['volume']

        ema_fast = close.ewm(span=self.fast_ema, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow_ema, adjust=False).mean()
        atr_s = self._atr(data, self.atr_short)
        atr_l = self._atr(data, self.atr_long)

        # Volatility Expansion Index (community-discussed concept)
        vei = atr_s / (atr_l + 1e-12)
        vol_state = float(np.clip((vei.iloc[-1] - self.atr_gate) / 0.7, -1.0, 1.0))

        # Trend score
        trend_raw = (ema_fast.iloc[-1] - ema_slow.iloc[-1]) / (atr_s.iloc[-1] + 1e-12)
        trend_score = float(np.tanh(trend_raw))

        # Mean-reversion score (zscore)
        z = (close - close.rolling(self.z_window).mean()) / (close.rolling(self.z_window).std() + 1e-12)
        meanrev_score = float(np.clip(-z.iloc[-1] / 3.0, -1.0, 1.0))

        # Breakout score with volume filter
        hi = high.rolling(self.breakout_window).max().shift(1)
        lo = low.rolling(self.breakout_window).min().shift(1)
        vol_ma = volume.rolling(self.vol_window).mean()
        vol_ratio = volume.iloc[-1] / (vol_ma.iloc[-1] + 1e-12)
        breakout_score = 0.0
        if close.iloc[-1] > hi.iloc[-1] and vol_ratio > self.vol_ratio_gate:
            breakout_score = 1.0
        elif close.iloc[-1] < lo.iloc[-1] and vol_ratio > self.vol_ratio_gate:
            breakout_score = -1.0

        # Orderflow-like proxy score (delta/absorption proxy)
        rng = (high - low).replace(0, np.nan).ffill().fillna(1e-6)
        delta_proxy = ((close - open_) / rng) * volume
        flow = delta_proxy.rolling(self.vol_window).sum()
        flow_norm = flow.iloc[-1] / (volume.rolling(self.vol_window).mean().iloc[-1] + 1e-12)
        flow_score = float(np.clip(flow_norm / 4.0, -1.0, 1.0))

        # Session score (time-slice confluence)
        session_score = 0.0
        if isinstance(data.index, pd.DatetimeIndex):
            h = int(data.index[-1].hour)
            if h in (8, 9, 10, 13, 14, 15):
                session_score = 1.0
            elif h in (0, 1, 2, 3):
                session_score = -0.3

        # Cooldown-like micro-noise filter: require bar range > median recent micro range
        micro_range = (high - low)
        micro_ok = micro_range.iloc[-1] > micro_range.rolling(self.cooldown * 5).median().iloc[-1]
        if not micro_ok:
            return []

        composite = (
            self.trend_w * trend_score +
            self.meanrev_w * meanrev_score +
            self.breakout_w * breakout_score +
            self.volstate_w * vol_state +
            self.flow_w * flow_score +
            self.session_w * session_score
        )

        # Regime guard: avoid dead volatility
        if vei.iloc[-1] < (self.atr_gate - 0.2):
            return []

        px = close.iloc[-1]
        a = atr_s.iloc[-1]
        if pd.isna(px) or pd.isna(a) or a <= 0:
            return []

        signals: List[Signal] = []
        if composite > self.long_threshold:
            conf = min(0.95, max(0.1, 0.52 + (composite - self.long_threshold) * 0.55))
            signals.append(self._mk(symbol, 'BUY', px, a, conf, f'dynamic_risk_heat comp={composite:.2f} vei={vei.iloc[-1]:.2f}'))
        elif composite < -self.short_threshold:
            conf = min(0.95, max(0.1, 0.52 + ((-composite) - self.short_threshold) * 0.55))
            signals.append(self._mk(symbol, 'SELL', px, a, conf, f'dynamic_risk_heat comp={composite:.2f} vei={vei.iloc[-1]:.2f}'))

        return signals

    def _mk(self, symbol: str, direction: str, px: float, atr: float, conf: float, reason: str) -> Signal:
        if direction == 'BUY':
            tp = px + self.tp_atr * atr
            sl = px - self.sl_atr * atr
        else:
            tp = px - self.tp_atr * atr
            sl = px + self.sl_atr * atr
        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=float(round(conf, 3)),
            entry_price=float(round(px, 2)),
            take_profit=float(round(tp, 2)),
            stop_loss=float(round(sl, 2)),
            reason=reason,
        )

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        h, l, c = data['high'], data['low'], data['close']
        tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period).mean()


if __name__ == '__main__':
    np.random.seed(700 + 90)
    n = 340
    returns = np.random.normal(0.00025, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    test = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.random.lognormal(7.0, 0.6, n)
    })
    s = CryptoSoc090DynamicRiskHeatStrategy()
    total = 0
    for i in range(130, len(test)):
        total += len(s.generate_signals(test.iloc[:i+1], 'BTCUSDT'))
    print(total)
