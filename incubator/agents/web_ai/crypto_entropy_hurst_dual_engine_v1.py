"""
crypto_entropy_hurst_dual_engine_v1
===================================

Adaptive dual-engine strategy:
- Mean-reversion engine in high-entropy / anti-persistent regimes
- Momentum engine in low-entropy / persistent regimes
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


class CryptoEntropyHurstDualEngineStrategy:
    """Switches signal logic based on regime statistics."""

    def __init__(self, params: Optional[Dict] = None):
        self.p = params or {}
        self.regime_window = self.p.get("regime_window", 96)
        self.entropy_bins = self.p.get("entropy_bins", 6)
        self.entropy_high = self.p.get("entropy_high", 0.78)
        self.entropy_low = self.p.get("entropy_low", 0.62)
        self.hurst_mr_max = self.p.get("hurst_mr_max", 0.47)
        self.hurst_mom_min = self.p.get("hurst_mom_min", 0.56)
        self.z_window = self.p.get("z_window", 36)
        self.z_entry = self.p.get("z_entry", 1.8)
        self.breakout_window = self.p.get("breakout_window", 20)
        self.ema_fast = self.p.get("ema_fast", 21)
        self.ema_slow = self.p.get("ema_slow", 55)
        self.atr_period = self.p.get("atr_period", 14)
        self.tp_atr = self.p.get("tp_atr", 2.2)
        self.sl_atr = self.p.get("sl_atr", 1.35)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = max(self.regime_window, self.z_window, self.breakout_window, self.ema_slow) + 10
        if data is None or len(data) < min_len:
            return []

        close = data["close"].astype(float)
        rets = close.pct_change().dropna()
        regime_slice = rets.tail(self.regime_window)
        if len(regime_slice) < 32:
            return []

        entropy = self._normalized_entropy(regime_slice.values, bins=self.entropy_bins)
        hurst = self._hurst_exponent(close.tail(self.regime_window).values)
        if np.isnan(entropy) or np.isnan(hurst):
            return []

        atr = self._atr(data, self.atr_period)
        curr_price = float(close.iloc[-1])
        curr_atr = float(atr.iloc[-1])
        if np.isnan(curr_atr) or curr_atr <= 0:
            return []

        # Mean-reversion engine signals
        ema_mid = close.ewm(span=34, adjust=False).mean()
        spread = close - ema_mid
        z = self._rolling_z(spread, self.z_window)
        z_now = float(z.iloc[-1]) if not np.isnan(z.iloc[-1]) else 0.0

        # Momentum engine signals
        ema_f = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_s = close.ewm(span=self.ema_slow, adjust=False).mean()
        breakout_hi = close.shift(1).rolling(self.breakout_window).max().iloc[-1]
        breakout_lo = close.shift(1).rolling(self.breakout_window).min().iloc[-1]

        signals: List[Signal] = []

        # Engine A: mean reversion in noisy anti-persistent regimes.
        if entropy >= self.entropy_high and hurst <= self.hurst_mr_max:
            if z_now <= -self.z_entry:
                confidence = min(0.93, 0.58 + min(abs(z_now) / 4.0, 0.2) + min((entropy - self.entropy_high), 0.12))
                signals.append(
                    Signal(
                        symbol=symbol,
                        direction="BUY",
                        confidence=round(confidence, 3),
                        entry_price=round(curr_price, 2),
                        take_profit=round(curr_price + curr_atr * self.tp_atr, 2),
                        stop_loss=round(curr_price - curr_atr * self.sl_atr, 2),
                        reason=f"MR engine entropy={entropy:.2f} hurst={hurst:.2f} z={z_now:.2f}",
                    )
                )
            elif z_now >= self.z_entry:
                confidence = min(0.93, 0.58 + min(abs(z_now) / 4.0, 0.2) + min((entropy - self.entropy_high), 0.12))
                signals.append(
                    Signal(
                        symbol=symbol,
                        direction="SELL",
                        confidence=round(confidence, 3),
                        entry_price=round(curr_price, 2),
                        take_profit=round(curr_price - curr_atr * self.tp_atr, 2),
                        stop_loss=round(curr_price + curr_atr * self.sl_atr, 2),
                        reason=f"MR engine entropy={entropy:.2f} hurst={hurst:.2f} z={z_now:.2f}",
                    )
                )
        # Engine B: momentum in persistent, lower-entropy regimes.
        elif entropy <= self.entropy_low and hurst >= self.hurst_mom_min:
            if curr_price > breakout_hi and ema_f.iloc[-1] > ema_s.iloc[-1]:
                confidence = min(0.92, 0.56 + min((self.entropy_low - entropy), 0.14) + min((hurst - self.hurst_mom_min), 0.16))
                signals.append(
                    Signal(
                        symbol=symbol,
                        direction="BUY",
                        confidence=round(confidence, 3),
                        entry_price=round(curr_price, 2),
                        take_profit=round(curr_price + curr_atr * (self.tp_atr + 0.35), 2),
                        stop_loss=round(curr_price - curr_atr * (self.sl_atr + 0.2), 2),
                        reason=f"MOM engine entropy={entropy:.2f} hurst={hurst:.2f} breakoutUP",
                    )
                )
            elif curr_price < breakout_lo and ema_f.iloc[-1] < ema_s.iloc[-1]:
                confidence = min(0.92, 0.56 + min((self.entropy_low - entropy), 0.14) + min((hurst - self.hurst_mom_min), 0.16))
                signals.append(
                    Signal(
                        symbol=symbol,
                        direction="SELL",
                        confidence=round(confidence, 3),
                        entry_price=round(curr_price, 2),
                        take_profit=round(curr_price - curr_atr * (self.tp_atr + 0.35), 2),
                        stop_loss=round(curr_price + curr_atr * (self.sl_atr + 0.2), 2),
                        reason=f"MOM engine entropy={entropy:.2f} hurst={hurst:.2f} breakoutDN",
                    )
                )
        return signals

    @staticmethod
    def _rolling_z(s: pd.Series, window: int) -> pd.Series:
        mu = s.rolling(window).mean()
        sd = s.rolling(window).std(ddof=0).replace(0, np.nan)
        return (s - mu) / sd

    @staticmethod
    def _normalized_entropy(values: np.ndarray, bins: int = 6) -> float:
        if len(values) < bins * 2:
            return float("nan")
        hist, _ = np.histogram(values, bins=bins, density=False)
        p = hist / max(hist.sum(), 1)
        p = p[p > 0]
        h = -np.sum(p * np.log(p))
        return float(h / np.log(bins))

    @staticmethod
    def _hurst_exponent(prices: np.ndarray) -> float:
        if len(prices) < 40:
            return float("nan")
        lags = np.array([2, 4, 8, 16], dtype=float)
        tau = []
        for lag in lags:
            diff = prices[int(lag) :] - prices[: -int(lag)]
            tau.append(np.sqrt(np.std(diff)))
        tau = np.array(tau, dtype=float)
        if np.any(tau <= 0):
            return float("nan")
        slope = np.polyfit(np.log(lags), np.log(tau), 1)[0]
        return float(2.0 * slope)

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

