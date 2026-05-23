"""
HurstRegimeFilterStrategy - Baby Strat
========================================

Created by: Claude Code (Deep Research Round 14)
Date: 2026-03-02

Academic Basis:
- H.E. Hurst (1951) "Long-term storage capacity of reservoirs"
- Mandelbrot & Van Ness (1968) "Fractional Brownian Motions"
- Qian & Rasheed (2004, 2007) "Hurst Exponent and Financial Market Predictability"
- H > 0.5: trending (persistent) → use trend-following
- H < 0.5: mean-reverting (anti-persistent) → use mean reversion
- H ≈ 0.5: random walk → don't trade

Strategy Logic:
- Compute Hurst exponent using R/S analysis on rolling window
- H > 0.55: regime is TRENDING → BUY if price > EMA, SELL if below
- H < 0.45: regime is MEAN-REVERTING → BUY if RSI < 30, SELL if RSI > 70
- 0.45 ≤ H ≤ 0.55: regime is RANDOM → no trade (edge is minimal)
- This is a META-STRATEGY that adapts behavior to current regime

Why It Works:
- Markets alternate between trending and mean-reverting regimes
- Using the wrong strategy type in the wrong regime is the #1 reason for losses
- Hurst exponent objectively measures which regime we're in
- Avoids random-walk periods where no strategy has edge
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Dict
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


class HurstRegimeFilterStrategy:
    NAME = "hurst_regime_filter"
    DESCRIPTION = "Hurst exponent regime detection — trend-follow or mean-revert adaptively"
    ACADEMIC_SOURCE = "Hurst 1951, Mandelbrot 1968, Qian & Rasheed 2004: H>0.5=trend, H<0.5=MR"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.hurst_window = self.params.get('hurst_window', 200)
        self.trend_threshold = self.params.get('trend_threshold', 0.55)
        self.mr_threshold = self.params.get('mr_threshold', 0.45)
        self.ema_fast = self.params.get('ema_fast', 20)
        self.ema_slow = self.params.get('ema_slow', 50)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.tp_pct = self.params.get('tp_pct', 3.0)
        self.sl_pct = self.params.get('sl_pct', 2.0)

    def _compute_hurst(self, prices: np.ndarray) -> float:
        """Compute Hurst exponent using R/S analysis."""
        n = len(prices)
        if n < 20:
            return 0.5

        log_returns = np.diff(np.log(prices))
        if len(log_returns) < 20:
            return 0.5

        # R/S analysis with multiple sub-periods
        max_k = min(int(n / 4), 50)
        min_k = 10

        rs_list = []
        n_list = []

        for k in range(min_k, max_k + 1, max(1, (max_k - min_k) // 8)):
            num_segments = len(log_returns) // k
            if num_segments < 1:
                continue

            rs_values = []
            for seg in range(num_segments):
                segment = log_returns[seg * k:(seg + 1) * k]
                if len(segment) < 2:
                    continue

                mean_seg = np.mean(segment)
                deviations = np.cumsum(segment - mean_seg)
                R = np.max(deviations) - np.min(deviations)
                S = np.std(segment, ddof=1)

                if S > 1e-10:
                    rs_values.append(R / S)

            if rs_values:
                rs_list.append(np.mean(rs_values))
                n_list.append(k)

        if len(rs_list) < 3:
            return 0.5

        # Linear regression of log(R/S) vs log(n) → slope = H
        log_n = np.log(n_list)
        log_rs = np.log(rs_list)

        # Simple OLS
        n_pts = len(log_n)
        sum_x = np.sum(log_n)
        sum_y = np.sum(log_rs)
        sum_xy = np.sum(log_n * log_rs)
        sum_x2 = np.sum(log_n ** 2)

        denom = n_pts * sum_x2 - sum_x ** 2
        if abs(denom) < 1e-10:
            return 0.5

        H = (n_pts * sum_xy - sum_x * sum_y) / denom
        return max(0.0, min(1.0, H))

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        min_bars = max(self.hurst_window + 10, self.ema_slow + 10, 100)
        if len(data) < min_bars:
            return []

        close = data['close'].values
        n = len(close)
        current_price = close[-1]

        # Compute Hurst exponent
        H = self._compute_hurst(close[-self.hurst_window:])

        # Determine regime
        if self.mr_threshold <= H <= self.trend_threshold:
            return []  # Random walk — no edge

        signals = []

        if H > self.trend_threshold:
            # TRENDING regime → use trend-following
            ema_fast = self._ema(close, self.ema_fast)
            ema_slow = self._ema(close, self.ema_slow)

            if ema_fast[-1] > ema_slow[-1] and current_price > ema_fast[-1]:
                # Uptrend confirmed
                confidence = min(0.3 + (H - 0.5) * 2, 0.80)
                tp = current_price * (1 + self.tp_pct / 100)
                sl = current_price * (1 - self.sl_pct / 100)

                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"Hurst TREND BUY (H={H:.3f}, EMA cross UP, regime=PERSISTENT)"
                ))

            elif ema_fast[-1] < ema_slow[-1] and current_price < ema_fast[-1]:
                # Downtrend confirmed
                confidence = min(0.3 + (H - 0.5) * 2, 0.80)
                tp = current_price * (1 - self.tp_pct / 100)
                sl = current_price * (1 + self.sl_pct / 100)

                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"Hurst TREND SELL (H={H:.3f}, EMA cross DOWN, regime=PERSISTENT)"
                ))

        elif H < self.mr_threshold:
            # MEAN-REVERTING regime → use RSI extremes
            rsi = self._rsi(close, self.rsi_period)
            current_rsi = rsi[-1]

            # Mean price
            mean_price = np.mean(close[-self.hurst_window:])

            if current_rsi < 30 and current_price < mean_price:
                confidence = min(0.3 + (0.5 - H) * 2, 0.80)
                tp = current_price * (1 + self.tp_pct / 100)
                sl = current_price * (1 - self.sl_pct / 100)

                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"Hurst MR BUY (H={H:.3f}, RSI={current_rsi:.1f}, below mean, regime=ANTI-PERSISTENT)"
                ))

            elif current_rsi > 70 and current_price > mean_price:
                confidence = min(0.3 + (0.5 - H) * 2, 0.80)
                tp = current_price * (1 - self.tp_pct / 100)
                sl = current_price * (1 + self.sl_pct / 100)

                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"Hurst MR SELL (H={H:.3f}, RSI={current_rsi:.1f}, above mean, regime=ANTI-PERSISTENT)"
                ))

        return signals

    def _rsi(self, close: np.ndarray, period: int) -> np.ndarray:
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.zeros(len(close))
        avg_loss = np.zeros(len(close))
        if len(gains) < period:
            return np.full(len(close), 50.0)
        avg_gain[period] = np.mean(gains[:period])
        avg_loss[period] = np.mean(losses[:period])
        for i in range(period + 1, len(close)):
            avg_gain[i] = (avg_gain[i-1] * (period - 1) + gains[i-1]) / period
            avg_loss[i] = (avg_loss[i-1] * (period - 1) + losses[i-1]) / period
        rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100)
        return 100 - (100 / (1 + rs))

    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        result = np.zeros(len(data))
        k = 2.0 / (period + 1)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = data[i] * k + result[i - 1] * (1 - k)
        return result
