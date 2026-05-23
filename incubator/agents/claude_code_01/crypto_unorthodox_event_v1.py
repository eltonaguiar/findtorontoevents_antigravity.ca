"""
Unorthodox Event-Driven Crypto Strategies v1
=============================================

Eight event-driven strategies that exploit structural patterns in crypto markets:
anomalous price events, candlestick formations, and behavioral biases that create
predictable short-term dislocations.

Strategies:
  1. ATHBreakoutStrategy        - All-time high breakout momentum
  2. ATLBounceStrategy          - All-time low mean reversion bounce
  3. BTCATHAltRotationStrategy  - BTC strength -> alt rotation lag
  4. WeekendDipBuyStrategy      - Consecutive lower lows dip buy
  5. PostCrashRecoveryStrategy  - First green candle after >10% crash
  6. LongWickReversalStrategy   - Lower wick rejection buy
  7. GapFillStrategy            - Gap fill mean reversion (up/down)
  8. ThreeWhiteSoldiersStrategy - Classic 3 bullish soldiers pattern

Each strategy implements generate_signals(data, symbol) -> List[Signal].

Dependencies: numpy, pandas only.
"""

import os
import sys

if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class Signal:
    symbol: str
    direction: str          # "BUY" or "SELL"
    entry_price: float
    take_profit: float
    stop_loss: float
    confidence: float       # 0.0 to 1.0
    strategy_name: str
    metadata: dict = field(default_factory=dict)
    reason: str = ""        # populated from metadata for scanner compatibility


# ---------------------------------------------------------------------------
#  Shared indicator helpers (numpy-only, no external deps)
# ---------------------------------------------------------------------------

def _rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """RSI using Wilder exponential smoothing."""
    deltas = np.diff(close, prepend=close[0])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    alpha = 1.0 / period
    avg_gain = np.zeros_like(close)
    avg_loss = np.zeros_like(close)

    if len(close) > period:
        avg_gain[period] = np.mean(gains[1:period + 1])
        avg_loss[period] = np.mean(losses[1:period + 1])

        for i in range(period + 1, len(close)):
            avg_gain[i] = avg_gain[i - 1] * (1 - alpha) + gains[i] * alpha
            avg_loss[i] = avg_loss[i - 1] * (1 - alpha) + losses[i] * alpha

    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi[:period + 1] = 50.0
    return rsi


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
         period: int = 14) -> np.ndarray:
    """Average True Range using Wilder smoothing."""
    tr = np.zeros_like(close)
    tr[0] = high[0] - low[0]
    for i in range(1, len(close)):
        tr[i] = max(high[i] - low[i],
                     abs(high[i] - close[i - 1]),
                     abs(low[i] - close[i - 1]))

    atr = np.zeros_like(close)
    atr[:period] = np.nan
    if len(close) > period:
        atr[period] = np.mean(tr[:period])
        for i in range(period + 1, len(close)):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def _sma(arr: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average."""
    out = np.full_like(arr, np.nan)
    if len(arr) >= period:
        cumsum = np.cumsum(arr)
        out[period - 1:] = (cumsum[period - 1:] - np.concatenate(([0], cumsum[:-period]))) / period
    return out


# ===================================================================
# Strategy 1: ATH Breakout
# ===================================================================

class ATHBreakoutStrategy:
    """Buy when price breaks to a new all-time high (200+ bar lookback).

    Historical basis: ATH breakouts in crypto tend to cascade as short sellers
    cover and FOMO buyers pile in. Bitcoin's largest rallies began at ATH breaks.

    Filters:
      - close > max(high[-200:])
      - volume > 1.5x 20-bar average volume
    Targets:
      - TP = 3.0 * ATR(14), SL = 1.5 * ATR(14)
    """

    NAME = "ATHBreakout"
    VERSION = "1.0"

    def __init__(self, params: Optional[Dict] = None):
        p = params or {}
        self.lookback = p.get('lookback', 200)
        self.vol_mult = p.get('vol_mult', 1.5)
        self.vol_avg_period = p.get('vol_avg_period', 20)
        self.atr_period = p.get('atr_period', 14)
        self.tp_atr_mult = p.get('tp_atr_mult', 3.0)
        self.sl_atr_mult = p.get('sl_atr_mult', 1.5)
        self.min_bars = p.get('min_bars', 210)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data['close'].values.astype(float)
        high = data['high'].values.astype(float)
        low = data['low'].values.astype(float)
        volume = data['volume'].values.astype(float)

        i = len(close) - 1
        atr = _atr(high, low, close, self.atr_period)
        if np.isnan(atr[i]) or atr[i] <= 0:
            return []

        # ATH detection: current close > highest high over lookback period (excluding current bar)
        lookback_start = max(0, i - self.lookback)
        prior_high = np.max(high[lookback_start:i])
        if close[i] <= prior_high:
            return []

        # Volume confirmation
        vol_start = max(0, i - self.vol_avg_period)
        avg_vol = np.mean(volume[vol_start:i]) if i > 0 else volume[i]
        if avg_vol <= 0 or volume[i] < avg_vol * self.vol_mult:
            return []

        entry = close[i]
        tp = entry + self.tp_atr_mult * atr[i]
        sl = entry - self.sl_atr_mult * atr[i]
        vol_ratio = volume[i] / avg_vol

        confidence = min(0.60 + 0.10 * (vol_ratio - self.vol_mult), 0.90)

        reason = (
            f"ATHBreakout: close={entry:.6f} > prior_ATH={prior_high:.6f} | "
            f"vol_ratio={vol_ratio:.2f}x | ATR={atr[i]:.6f}"
        )

        return [Signal(
            symbol=symbol,
            direction="BUY",
            entry_price=round(entry, 8),
            take_profit=round(tp, 8),
            stop_loss=round(sl, 8),
            confidence=round(confidence, 4),
            strategy_name=self.NAME,
            metadata={
                'prior_ath': round(prior_high, 8),
                'vol_ratio': round(vol_ratio, 4),
                'atr': round(atr[i], 8),
                'lookback': self.lookback,
            },
            reason=reason,
        )]


# ===================================================================
# Strategy 2: ATL Bounce
# ===================================================================

class ATLBounceStrategy:
    """Mean reversion buy when price hits all-time low (200+ bar lookback).

    Rationale: crypto rarely stays at absolute bottoms -- panic selling overshoots
    fair value, and bargain hunters eventually step in. Confirmed by extreme RSI.

    Filters:
      - close < min(low[-200:])
      - RSI(14) < 25
    Targets:
      - TP = 2.5 * ATR(14), SL = 1.0 * ATR(14)
    """

    NAME = "ATLBounce"
    VERSION = "1.0"

    def __init__(self, params: Optional[Dict] = None):
        p = params or {}
        self.lookback = p.get('lookback', 200)
        self.rsi_period = p.get('rsi_period', 14)
        self.rsi_threshold = p.get('rsi_threshold', 25)
        self.atr_period = p.get('atr_period', 14)
        self.tp_atr_mult = p.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = p.get('sl_atr_mult', 1.0)
        self.min_bars = p.get('min_bars', 210)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data['close'].values.astype(float)
        high = data['high'].values.astype(float)
        low = data['low'].values.astype(float)
        volume = data['volume'].values.astype(float)

        i = len(close) - 1
        atr = _atr(high, low, close, self.atr_period)
        if np.isnan(atr[i]) or atr[i] <= 0:
            return []

        # ATL detection: current close < lowest low over lookback (excluding current bar)
        lookback_start = max(0, i - self.lookback)
        prior_low = np.min(low[lookback_start:i])
        if close[i] >= prior_low:
            return []

        # RSI confirmation
        rsi = _rsi(close, self.rsi_period)
        if rsi[i] >= self.rsi_threshold:
            return []

        entry = close[i]
        tp = entry + self.tp_atr_mult * atr[i]
        sl = entry - self.sl_atr_mult * atr[i]

        confidence = min(0.55 + 0.15 * ((self.rsi_threshold - rsi[i]) / self.rsi_threshold), 0.85)

        reason = (
            f"ATLBounce: close={entry:.6f} < prior_ATL={prior_low:.6f} | "
            f"RSI={rsi[i]:.1f} < {self.rsi_threshold} | ATR={atr[i]:.6f}"
        )

        return [Signal(
            symbol=symbol,
            direction="BUY",
            entry_price=round(entry, 8),
            take_profit=round(tp, 8),
            stop_loss=round(sl, 8),
            confidence=round(confidence, 4),
            strategy_name=self.NAME,
            metadata={
                'prior_atl': round(prior_low, 8),
                'rsi': round(rsi[i], 2),
                'atr': round(atr[i], 8),
            },
            reason=reason,
        )]


# ===================================================================
# Strategy 3: BTC ATH Alt Rotation
# ===================================================================

class BTCATHAltRotationStrategy:
    """When BTC is near its recent highs, alts tend to follow with a lag.

    Rationale: capital flows from BTC into alts after BTC rallies stall.
    This is a single-symbol strategy that checks if the asset itself is near
    recent highs with momentum, anticipating continued rotation.

    Filters:
      - close > 0.95 * max(high[-90:])
      - RSI(14) > 60
    Targets:
      - TP = 4.0 * ATR(14), SL = 2.0 * ATR(14)
    """

    NAME = "BTCATHAltRotation"
    VERSION = "1.0"

    def __init__(self, params: Optional[Dict] = None):
        p = params or {}
        self.lookback = p.get('lookback', 90)
        self.proximity_pct = p.get('proximity_pct', 0.95)
        self.rsi_period = p.get('rsi_period', 14)
        self.rsi_min = p.get('rsi_min', 60)
        self.atr_period = p.get('atr_period', 14)
        self.tp_atr_mult = p.get('tp_atr_mult', 4.0)
        self.sl_atr_mult = p.get('sl_atr_mult', 2.0)
        self.min_bars = p.get('min_bars', 100)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data['close'].values.astype(float)
        high = data['high'].values.astype(float)
        low = data['low'].values.astype(float)

        i = len(close) - 1
        atr = _atr(high, low, close, self.atr_period)
        if np.isnan(atr[i]) or atr[i] <= 0:
            return []

        # Check if near recent highs
        lookback_start = max(0, i - self.lookback)
        recent_high = np.max(high[lookback_start:i + 1])
        threshold = self.proximity_pct * recent_high

        if close[i] < threshold:
            return []

        # RSI momentum confirmation
        rsi = _rsi(close, self.rsi_period)
        if rsi[i] < self.rsi_min:
            return []

        entry = close[i]
        tp = entry + self.tp_atr_mult * atr[i]
        sl = entry - self.sl_atr_mult * atr[i]

        proximity = close[i] / recent_high
        confidence = min(0.55 + 0.20 * (proximity - self.proximity_pct) / (1.0 - self.proximity_pct), 0.85)

        reason = (
            f"BTCATHAltRotation: close={entry:.6f} at {proximity:.1%} of "
            f"90d high={recent_high:.6f} | RSI={rsi[i]:.1f} | ATR={atr[i]:.6f}"
        )

        return [Signal(
            symbol=symbol,
            direction="BUY",
            entry_price=round(entry, 8),
            take_profit=round(tp, 8),
            stop_loss=round(sl, 8),
            confidence=round(confidence, 4),
            strategy_name=self.NAME,
            metadata={
                'recent_high': round(recent_high, 8),
                'proximity': round(proximity, 4),
                'rsi': round(rsi[i], 2),
                'atr': round(atr[i], 8),
            },
            reason=reason,
        )]


# ===================================================================
# Strategy 4: Weekend Dip Buy (Consecutive Lower Lows)
# ===================================================================

class WeekendDipBuyStrategy:
    """Buy the dip after 3 consecutive lower lows with RSI < 40.

    Robust version of the weekend-dip hypothesis: rather than relying on
    calendar day detection (unreliable with bar data), we detect the structural
    pattern that weekend dips create -- 3+ consecutive lower lows with
    oversold RSI indicating exhausted sellers.

    Filters:
      - 3 consecutive lower lows: low[i] < low[i-1] < low[i-2]
      - RSI(14) < 40
    Targets:
      - TP = 2.0 * ATR(14), SL = 1.0 * ATR(14)
    """

    NAME = "WeekendDipBuy"
    VERSION = "1.0"

    def __init__(self, params: Optional[Dict] = None):
        p = params or {}
        self.consecutive_lows = p.get('consecutive_lows', 3)
        self.rsi_period = p.get('rsi_period', 14)
        self.rsi_threshold = p.get('rsi_threshold', 40)
        self.atr_period = p.get('atr_period', 14)
        self.tp_atr_mult = p.get('tp_atr_mult', 2.0)
        self.sl_atr_mult = p.get('sl_atr_mult', 1.0)
        self.min_bars = p.get('min_bars', 50)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data['close'].values.astype(float)
        high = data['high'].values.astype(float)
        low = data['low'].values.astype(float)

        i = len(close) - 1
        atr = _atr(high, low, close, self.atr_period)
        if np.isnan(atr[i]) or atr[i] <= 0:
            return []

        # Check for N consecutive lower lows
        if i < self.consecutive_lows:
            return []

        for k in range(1, self.consecutive_lows):
            if low[i - k + 1] >= low[i - k]:
                return []

        # RSI confirmation
        rsi = _rsi(close, self.rsi_period)
        if rsi[i] >= self.rsi_threshold:
            return []

        entry = close[i]
        tp = entry + self.tp_atr_mult * atr[i]
        sl = entry - self.sl_atr_mult * atr[i]

        confidence = min(0.55 + 0.10 * ((self.rsi_threshold - rsi[i]) / self.rsi_threshold), 0.80)

        reason = (
            f"WeekendDipBuy: {self.consecutive_lows} consecutive lower lows | "
            f"RSI={rsi[i]:.1f} < {self.rsi_threshold} | ATR={atr[i]:.6f}"
        )

        return [Signal(
            symbol=symbol,
            direction="BUY",
            entry_price=round(entry, 8),
            take_profit=round(tp, 8),
            stop_loss=round(sl, 8),
            confidence=round(confidence, 4),
            strategy_name=self.NAME,
            metadata={
                'consecutive_lows': self.consecutive_lows,
                'rsi': round(rsi[i], 2),
                'atr': round(atr[i], 8),
                'low_sequence': [round(low[i - k], 8) for k in range(self.consecutive_lows - 1, -1, -1)],
            },
            reason=reason,
        )]


# ===================================================================
# Strategy 5: Post-Crash Recovery
# ===================================================================

class PostCrashRecoveryStrategy:
    """Buy the first green candle after a crash (>10% drop in 3 bars).

    Rationale: panic selling overshoots fair value. The first green candle
    after a sharp decline signals that selling pressure is exhausted and
    bargain hunters are stepping in. Historically, crypto V-bounces after
    crashes produce 5-15% recoveries within days.

    Filters:
      - close dropped > 10% from close[3 bars ago]
      - Current candle is green: close > open
    Targets:
      - TP = 3.0 * ATR(14), SL = 1.5 * ATR(14)
    """

    NAME = "PostCrashRecovery"
    VERSION = "1.0"

    def __init__(self, params: Optional[Dict] = None):
        p = params or {}
        self.crash_pct = p.get('crash_pct', 0.10)
        self.crash_bars = p.get('crash_bars', 3)
        self.atr_period = p.get('atr_period', 14)
        self.tp_atr_mult = p.get('tp_atr_mult', 3.0)
        self.sl_atr_mult = p.get('sl_atr_mult', 1.5)
        self.min_bars = p.get('min_bars', 50)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data['close'].values.astype(float)
        high = data['high'].values.astype(float)
        low = data['low'].values.astype(float)
        opn = data['open'].values.astype(float)

        i = len(close) - 1
        atr = _atr(high, low, close, self.atr_period)
        if np.isnan(atr[i]) or atr[i] <= 0:
            return []

        if i < self.crash_bars:
            return []

        # Detect crash: close dropped > crash_pct from close N bars ago
        ref_close = close[i - self.crash_bars]
        if ref_close <= 0:
            return []
        drop_pct = (ref_close - close[i]) / ref_close

        if drop_pct < self.crash_pct:
            return []

        # First green candle after crash
        if close[i] <= opn[i]:
            return []

        entry = close[i]
        tp = entry + self.tp_atr_mult * atr[i]
        sl = entry - self.sl_atr_mult * atr[i]

        confidence = min(0.60 + 0.15 * (drop_pct - self.crash_pct), 0.90)

        reason = (
            f"PostCrashRecovery: {drop_pct:.1%} drop in {self.crash_bars} bars | "
            f"first green candle | ATR={atr[i]:.6f}"
        )

        return [Signal(
            symbol=symbol,
            direction="BUY",
            entry_price=round(entry, 8),
            take_profit=round(tp, 8),
            stop_loss=round(sl, 8),
            confidence=round(confidence, 4),
            strategy_name=self.NAME,
            metadata={
                'drop_pct': round(drop_pct, 4),
                'crash_bars': self.crash_bars,
                'ref_close': round(ref_close, 8),
                'atr': round(atr[i], 8),
            },
            reason=reason,
        )]


# ===================================================================
# Strategy 6: Long Wick Reversal
# ===================================================================

class LongWickReversalStrategy:
    """Buy on candles with very long lower wicks signaling rejection.

    Rationale: a long lower wick means price was pushed down but buyers
    aggressively rejected the move. This is a classic rejection/hammer
    pattern that precedes reversals, especially with above-average volume.

    Filters:
      - Lower wick > 3x body size
      - Volume > 20-bar average
      - RSI(14) < 45 (not already overbought)
    Targets:
      - TP = 2.0 * ATR(14), SL = 0.75 * ATR(14)
    """

    NAME = "LongWickReversal"
    VERSION = "1.0"

    def __init__(self, params: Optional[Dict] = None):
        p = params or {}
        self.wick_body_ratio = p.get('wick_body_ratio', 3.0)
        self.rsi_period = p.get('rsi_period', 14)
        self.rsi_max = p.get('rsi_max', 45)
        self.vol_avg_period = p.get('vol_avg_period', 20)
        self.atr_period = p.get('atr_period', 14)
        self.tp_atr_mult = p.get('tp_atr_mult', 2.0)
        self.sl_atr_mult = p.get('sl_atr_mult', 0.75)
        self.min_bars = p.get('min_bars', 50)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data['close'].values.astype(float)
        high = data['high'].values.astype(float)
        low = data['low'].values.astype(float)
        opn = data['open'].values.astype(float)
        volume = data['volume'].values.astype(float)

        i = len(close) - 1
        atr = _atr(high, low, close, self.atr_period)
        if np.isnan(atr[i]) or atr[i] <= 0:
            return []

        # Body and wick calculation
        body = abs(close[i] - opn[i])
        lower_wick = min(close[i], opn[i]) - low[i]

        # Avoid division by zero: treat tiny bodies as doji (body ~ 0 means wick dominates)
        if body <= 0:
            body = atr[i] * 0.001  # negligible body

        if lower_wick < body * self.wick_body_ratio:
            return []

        # Volume above average
        vol_start = max(0, i - self.vol_avg_period)
        avg_vol = np.mean(volume[vol_start:i]) if i > 0 else volume[i]
        if avg_vol <= 0 or volume[i] <= avg_vol:
            return []

        # RSI not overbought
        rsi = _rsi(close, self.rsi_period)
        if rsi[i] >= self.rsi_max:
            return []

        entry = close[i]
        tp = entry + self.tp_atr_mult * atr[i]
        sl = entry - self.sl_atr_mult * atr[i]

        wick_ratio = lower_wick / body
        vol_ratio = volume[i] / avg_vol
        confidence = min(0.55 + 0.05 * (wick_ratio - self.wick_body_ratio), 0.85)

        reason = (
            f"LongWickReversal: wick/body={wick_ratio:.1f}x | "
            f"vol={vol_ratio:.2f}x avg | RSI={rsi[i]:.1f} | ATR={atr[i]:.6f}"
        )

        return [Signal(
            symbol=symbol,
            direction="BUY",
            entry_price=round(entry, 8),
            take_profit=round(tp, 8),
            stop_loss=round(sl, 8),
            confidence=round(confidence, 4),
            strategy_name=self.NAME,
            metadata={
                'wick_body_ratio': round(wick_ratio, 2),
                'vol_ratio': round(vol_ratio, 4),
                'rsi': round(rsi[i], 2),
                'atr': round(atr[i], 8),
                'lower_wick': round(lower_wick, 8),
                'body': round(abs(close[i] - opn[i]), 8),
            },
            reason=reason,
        )]


# ===================================================================
# Strategy 7: Gap Fill
# ===================================================================

class GapFillStrategy:
    """Mean reversion on significant price gaps (>2% from prior close).

    Rationale: gaps in crypto (especially on lower-liquidity pairs) tend to
    fill as market makers and arbitrageurs close the dislocation. Gap-ups
    get sold, gap-downs get bought.

    Logic:
      - Gap up > 2%:  SELL (expect gap fill down)
      - Gap down > 2%: BUY  (expect gap fill up)
    Targets:
      - TP = distance to gap fill (prior close), SL = 1.5 * ATR(14)
    """

    NAME = "GapFill"
    VERSION = "1.0"

    def __init__(self, params: Optional[Dict] = None):
        p = params or {}
        self.gap_pct = p.get('gap_pct', 0.02)
        self.atr_period = p.get('atr_period', 14)
        self.sl_atr_mult = p.get('sl_atr_mult', 1.5)
        self.min_bars = p.get('min_bars', 50)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data['close'].values.astype(float)
        high = data['high'].values.astype(float)
        low = data['low'].values.astype(float)
        opn = data['open'].values.astype(float)

        i = len(close) - 1
        if i < 1:
            return []

        atr = _atr(high, low, close, self.atr_period)
        if np.isnan(atr[i]) or atr[i] <= 0:
            return []

        prev_close = close[i - 1]
        if prev_close <= 0:
            return []

        gap = (opn[i] - prev_close) / prev_close

        if abs(gap) < self.gap_pct:
            return []

        entry = close[i]
        sl_dist = self.sl_atr_mult * atr[i]

        if gap > self.gap_pct:
            # Gap up -> SELL to fill
            direction = "SELL"
            tp_dist = abs(entry - prev_close)
            if tp_dist < atr[i] * 0.5:
                return []  # gap already mostly filled
            tp = entry - tp_dist
            sl = entry + sl_dist
        else:
            # Gap down -> BUY to fill
            direction = "BUY"
            tp_dist = abs(prev_close - entry)
            if tp_dist < atr[i] * 0.5:
                return []  # gap already mostly filled
            tp = entry + tp_dist
            sl = entry - sl_dist

        confidence = min(0.55 + 0.10 * (abs(gap) - self.gap_pct) / self.gap_pct, 0.85)

        reason = (
            f"GapFill: {direction} gap={gap:+.2%} | prev_close={prev_close:.6f} "
            f"open={opn[i]:.6f} | ATR={atr[i]:.6f}"
        )

        return [Signal(
            symbol=symbol,
            direction=direction,
            entry_price=round(entry, 8),
            take_profit=round(tp, 8),
            stop_loss=round(sl, 8),
            confidence=round(confidence, 4),
            strategy_name=self.NAME,
            metadata={
                'gap_pct': round(gap, 6),
                'prev_close': round(prev_close, 8),
                'open': round(opn[i], 8),
                'gap_fill_target': round(prev_close, 8),
                'atr': round(atr[i], 8),
            },
            reason=reason,
        )]


# ===================================================================
# Strategy 8: Three White Soldiers
# ===================================================================

class ThreeWhiteSoldiersStrategy:
    """Classic bullish candlestick pattern: 3 consecutive strong bullish candles.

    Each candle:
      - Closes higher than the previous close
      - Has a body > 0.6 * total range (strong body, small wicks)

    This is one of the most reliable bullish continuation patterns in technical
    analysis, signaling sustained buying pressure with conviction.

    Targets:
      - TP = 2.5 * ATR(14)
      - SL = low of the 3-candle pattern
    """

    NAME = "ThreeWhiteSoldiers"
    VERSION = "1.0"

    def __init__(self, params: Optional[Dict] = None):
        p = params or {}
        self.body_ratio_min = p.get('body_ratio_min', 0.6)
        self.atr_period = p.get('atr_period', 14)
        self.tp_atr_mult = p.get('tp_atr_mult', 2.5)
        self.min_bars = p.get('min_bars', 50)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data['close'].values.astype(float)
        high = data['high'].values.astype(float)
        low = data['low'].values.astype(float)
        opn = data['open'].values.astype(float)

        i = len(close) - 1
        if i < 2:
            return []

        atr = _atr(high, low, close, self.atr_period)
        if np.isnan(atr[i]) or atr[i] <= 0:
            return []

        # Check 3 consecutive bullish candles with strong bodies
        for k in range(3):
            idx = i - 2 + k
            # Must be bullish
            if close[idx] <= opn[idx]:
                return []
            # Each close must be higher than prior close (except first)
            if k > 0 and close[idx] <= close[idx - 1]:
                return []
            # Body > body_ratio_min * total range
            candle_range = high[idx] - low[idx]
            if candle_range <= 0:
                return []
            body = close[idx] - opn[idx]
            if body / candle_range < self.body_ratio_min:
                return []

        entry = close[i]
        pattern_low = min(low[i - 2], low[i - 1], low[i])
        tp = entry + self.tp_atr_mult * atr[i]
        sl = pattern_low

        # If stop is too far, cap at 2x ATR below entry
        if entry - sl > 2.0 * atr[i]:
            sl = entry - 2.0 * atr[i]

        # Ensure stop is below entry
        if sl >= entry:
            return []

        avg_body_ratio = 0.0
        for k in range(3):
            idx = i - 2 + k
            candle_range = high[idx] - low[idx]
            body = close[idx] - opn[idx]
            avg_body_ratio += body / candle_range
        avg_body_ratio /= 3.0

        confidence = min(0.60 + 0.15 * (avg_body_ratio - self.body_ratio_min), 0.90)

        reason = (
            f"ThreeWhiteSoldiers: 3 bullish candles | avg_body_ratio={avg_body_ratio:.2f} | "
            f"pattern_low={pattern_low:.6f} | ATR={atr[i]:.6f}"
        )

        return [Signal(
            symbol=symbol,
            direction="BUY",
            entry_price=round(entry, 8),
            take_profit=round(tp, 8),
            stop_loss=round(sl, 8),
            confidence=round(confidence, 4),
            strategy_name=self.NAME,
            metadata={
                'avg_body_ratio': round(avg_body_ratio, 4),
                'pattern_low': round(pattern_low, 8),
                'closes': [round(close[i - 2], 8), round(close[i - 1], 8), round(close[i], 8)],
                'atr': round(atr[i], 8),
            },
            reason=reason,
        )]


# ===================================================================
# Convenience: all strategies in one list
# ===================================================================

ALL_STRATEGIES = [
    ATHBreakoutStrategy,
    ATLBounceStrategy,
    BTCATHAltRotationStrategy,
    WeekendDipBuyStrategy,
    PostCrashRecoveryStrategy,
    LongWickReversalStrategy,
    GapFillStrategy,
    ThreeWhiteSoldiersStrategy,
]


def get_all_strategies(params: Optional[Dict] = None) -> list:
    """Instantiate all 8 strategies with optional shared params."""
    return [cls(params) for cls in ALL_STRATEGIES]
