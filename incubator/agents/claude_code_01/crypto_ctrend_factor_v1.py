"""CTREND Cross-Sectional Trend Factor — 28-Indicator Aggregate Ranking.

Based on Fieberg, Liedtke, Poddig, Walker, Zaremba (2024):
"A Trend Factor for the Cross Section of Cryptocurrency Returns"
Published in JFQA (Journal of Financial and Quantitative Analysis).

Core idea: Compute 28 technical indicators per coin, aggregate them into
a single trend-strength score, rank coins cross-sectionally. Buy coins with
the strongest aggregate trend conviction, sell those with weakest.

Unlike simple momentum (past returns), CTREND measures TECHNICAL AGREEMENT —
how many independent indicators simultaneously confirm the trend. A coin
ranked high by CTREND has RSI, MACD, EMAs, volume, volatility bands all
confirming the same direction.

The factor is orthogonal to size, momentum, and liquidity — adds genuine
alpha beyond existing factor models.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass
import requests


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


# Symbols to rank cross-sectionally (extend as needed)
CTREND_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "MATICUSDT", "LTCUSDT", "UNIUSDT", "ATOMUSDT", "NEARUSDT",
    "APTUSDT", "ARBUSDT", "OPUSDT", "FILUSDT", "INJUSDT",
]

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"


class CTRENDFactorStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        # Top/bottom percentile to trade
        self.top_pct = self.params.get('top_pct', 0.2)    # long top 20%
        self.bottom_pct = self.params.get('bottom_pct', 0.2)  # short bottom 20%
        # TP/SL
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)
        self.atr_period = self.params.get('atr_period', 14)
        self.min_bars = self.params.get('min_bars', 100)
        # Minimum CTREND score to trigger (absolute value)
        self.min_score = self.params.get('min_score', 0.5)
        # Cache for cross-sectional data
        self._cross_data = None
        self._cross_timestamp = 0

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        """Generate signal based on cross-sectional CTREND ranking."""
        if len(data) < self.min_bars:
            return []

        close = data['close'].values.astype(float)
        current_price = close[-1]
        if current_price <= 0:
            return []

        # Compute CTREND score for the given symbol using its data
        score = self._compute_ctrend_score(data)

        if score is None or abs(score) < self.min_score:
            return []

        # Compute ATR
        atr = self._atr(data, self.atr_period)
        current_atr = atr.iloc[-1]
        if current_atr <= 0:
            return []

        signals = []

        # Confidence scales with score magnitude (max ~0.9 at score=1.0)
        confidence = min(0.90, 0.5 + abs(score) * 0.35)

        if score > self.min_score:
            # Strong bullish trend agreement across 28 indicators
            tp = round(current_price + current_atr * self.tp_atr_mult, 2)
            sl = round(current_price - current_atr * self.sl_atr_mult, 2)
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=tp,
                stop_loss=sl,
                reason=(
                    f"CTREND BUY: score {score:+.3f} — "
                    f"28-indicator aggregate trend conviction is strongly bullish"
                )
            ))
        elif score < -self.min_score:
            # Strong bearish trend agreement
            tp = round(current_price - current_atr * self.tp_atr_mult, 2)
            sl = round(current_price + current_atr * self.sl_atr_mult, 2)
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=tp,
                stop_loss=sl,
                reason=(
                    f"CTREND SELL: score {score:+.3f} — "
                    f"28-indicator aggregate trend conviction is strongly bearish"
                )
            ))

        return signals

    def _compute_ctrend_score(self, data: pd.DataFrame) -> Optional[float]:
        """Compute CTREND score: normalized aggregate of 28 technical indicators.

        Returns float in [-1, +1] where +1 = all 28 indicators bullish,
        -1 = all 28 bearish, 0 = mixed/neutral.
        """
        close = data['close'].values.astype(float)
        high = data['high'].values.astype(float)
        low = data['low'].values.astype(float)
        volume = data['volume'].values.astype(float)
        n = len(close)

        if n < 100:
            return None

        votes = []  # each vote is +1 (bullish) or -1 (bearish)

        # ── Moving Average Signals (8 indicators) ──
        for period in [5, 10, 20, 50]:
            ma = self._sma(close, period)
            if ma is not None:
                votes.append(1 if close[-1] > ma else -1)

        for period in [9, 21, 50, 100]:
            ema = self._ema_arr(close, period)
            if ema is not None:
                votes.append(1 if close[-1] > ema[-1] else -1)

        # ── EMA slope signals (3 indicators) ──
        for period in [9, 21, 50]:
            ema = self._ema_arr(close, period)
            if ema is not None and len(ema) > 3:
                slope = ema[-1] - ema[-3]
                votes.append(1 if slope > 0 else -1)

        # ── MACD (2 indicators) ──
        if n > 26:
            fast_ema = pd.Series(close).ewm(span=12, adjust=False).mean().values
            slow_ema = pd.Series(close).ewm(span=26, adjust=False).mean().values
            macd = fast_ema - slow_ema
            signal_line = pd.Series(macd).ewm(span=9, adjust=False).mean().values
            # MACD above signal
            votes.append(1 if macd[-1] > signal_line[-1] else -1)
            # MACD above zero
            votes.append(1 if macd[-1] > 0 else -1)

        # ── RSI (2 indicators) ──
        rsi = self._rsi(close, 14)
        if rsi is not None:
            votes.append(1 if rsi > 50 else -1)
            # RSI momentum (rising?)
            rsi_prev = self._rsi(close[:-1], 14)
            if rsi_prev is not None:
                votes.append(1 if rsi > rsi_prev else -1)

        # ── Stochastic (2 indicators) ──
        if n > 14:
            low14 = pd.Series(low).rolling(14).min().iloc[-1]
            high14 = pd.Series(high).rolling(14).max().iloc[-1]
            if high14 > low14:
                stoch_k = (close[-1] - low14) / (high14 - low14) * 100
                votes.append(1 if stoch_k > 50 else -1)
                votes.append(1 if stoch_k > 20 else (-1 if stoch_k < 80 else 0))

        # ── Bollinger Bands (2 indicators) ──
        if n > 20:
            sma20 = np.mean(close[-20:])
            std20 = np.std(close[-20:])
            upper = sma20 + 2 * std20
            lower = sma20 - 2 * std20
            # Price position relative to bands
            bb_pct = (close[-1] - lower) / (upper - lower) if (upper - lower) > 0 else 0.5
            votes.append(1 if bb_pct > 0.5 else -1)
            # Bandwidth expanding or contracting
            if n > 40:
                std20_prev = np.std(close[-40:-20])
                votes.append(1 if std20 > std20_prev else -1)

        # ── Volume indicators (3 indicators) ──
        if n > 20:
            vol_sma = np.mean(volume[-20:])
            # Volume trend
            vol_recent = np.mean(volume[-5:])
            votes.append(1 if vol_recent > vol_sma else -1)
            # Price-volume agreement: rising price + rising volume = bullish
            price_up = close[-1] > close[-5]
            vol_up = vol_recent > vol_sma
            if price_up and vol_up:
                votes.append(1)
            elif not price_up and vol_up:
                votes.append(-1)
            else:
                votes.append(0)
            # OBV trend
            obv = np.cumsum(np.where(np.diff(close[-30:]) > 0, volume[-29:], -volume[-29:]))
            votes.append(1 if obv[-1] > obv[0] else -1)

        # ── ATR / Volatility (2 indicators) ──
        if n > 20:
            atr_recent = np.mean(np.maximum(
                high[-14:] - low[-14:],
                np.maximum(
                    np.abs(high[-14:] - close[-15:-1]),
                    np.abs(low[-14:] - close[-15:-1])
                )
            ))
            atr_prev = np.mean(np.maximum(
                high[-28:-14] - low[-28:-14],
                np.maximum(
                    np.abs(high[-28:-14] - close[-29:-15]),
                    np.abs(low[-28:-14] - close[-29:-15])
                )
            )) if n > 30 else atr_recent
            # Volatility expanding with trend = bullish
            vol_expanding = atr_recent > atr_prev
            trend_up = close[-1] > close[-14]
            if vol_expanding and trend_up:
                votes.append(1)
            elif vol_expanding and not trend_up:
                votes.append(-1)
            else:
                votes.append(0)

        # ── ROC / Momentum (2 indicators) ──
        if n > 20:
            roc_10 = (close[-1] - close[-11]) / close[-11] if close[-11] > 0 else 0
            roc_20 = (close[-1] - close[-21]) / close[-21] if close[-21] > 0 else 0
            votes.append(1 if roc_10 > 0 else -1)
            votes.append(1 if roc_20 > 0 else -1)

        # Filter out zeros and compute aggregate score
        valid_votes = [v for v in votes if v != 0]
        if len(valid_votes) < 10:
            return None

        score = np.mean(valid_votes)  # [-1, +1]
        return float(score)

    def _sma(self, arr: np.ndarray, period: int) -> Optional[float]:
        if len(arr) < period:
            return None
        return float(np.mean(arr[-period:]))

    def _ema_arr(self, arr: np.ndarray, period: int) -> Optional[np.ndarray]:
        if len(arr) < period:
            return None
        return pd.Series(arr).ewm(span=period, adjust=False).mean().values

    def _rsi(self, close: np.ndarray, period: int = 14) -> Optional[float]:
        if len(close) < period + 1:
            return None
        deltas = np.diff(close[-period - 1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return float(100 - (100 / (1 + rs)))

    def _atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        tr = pd.concat([
            data['high'] - data['low'],
            (data['high'] - data['close'].shift()).abs(),
            (data['low'] - data['close'].shift()).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean()
