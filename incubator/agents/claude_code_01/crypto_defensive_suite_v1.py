"""Crypto Defensive Strategy Suite v1 — REWRITTEN with practical entry conditions.

Previous version produced 0 trades across 128 backtest combos because it required
5-6 simultaneous conditions. This rewrite uses 2-3 conditions max per strategy
with relaxed thresholds, targeting ~10-50+ trades per 500 bars.

Still smarter than going blindly long — every strategy uses trend awareness,
mean-reversion logic, or regime detection.

NOTE: numpy-only build (no pandas) for Python 3.14 compatibility.
"""

import sys
import os
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass, field

if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


@dataclass
class Signal:
    symbol: str
    direction: str  # "BUY" or "SELL"
    entry_price: float
    take_profit: float
    stop_loss: float
    confidence: float
    strategy_name: str
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Shared indicator helpers (numpy only)
# ---------------------------------------------------------------------------

def _calculate_ema(series: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average."""
    ema = np.full_like(series, np.nan, dtype=float)
    if len(series) < period:
        return ema
    ema[period - 1] = np.mean(series[:period])
    mult = 2.0 / (period + 1)
    for j in range(period, len(series)):
        ema[j] = series[j] * mult + ema[j - 1] * (1.0 - mult)
    return ema


def _calculate_rsi(series: np.ndarray, period: int = 14) -> np.ndarray:
    """Wilder RSI."""
    rsi = np.full_like(series, np.nan, dtype=float)
    if len(series) < period + 1:
        return rsi
    deltas = np.diff(series)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rsi[period] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    for j in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[j]) / period
        avg_loss = (avg_loss * (period - 1) + losses[j]) / period
        if avg_loss == 0:
            rsi[j + 1] = 100.0
        else:
            rsi[j + 1] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return rsi


def _calculate_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Average True Range (Wilder smoothing)."""
    atr = np.full_like(close, np.nan, dtype=float)
    if len(close) < period + 1:
        return atr
    tr = np.empty(len(close), dtype=float)
    tr[0] = high[0] - low[0]
    for j in range(1, len(close)):
        tr[j] = max(high[j] - low[j], abs(high[j] - close[j - 1]), abs(low[j] - close[j - 1]))
    atr[period] = np.mean(tr[1:period + 1])
    for j in range(period + 1, len(close)):
        atr[j] = (atr[j - 1] * (period - 1) + tr[j]) / period
    return atr


def _calculate_adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """ADX indicator."""
    n = len(close)
    adx = np.full(n, np.nan, dtype=float)
    if n < 2 * period + 1:
        return adx
    tr = np.empty(n, dtype=float)
    plus_dm = np.empty(n, dtype=float)
    minus_dm = np.empty(n, dtype=float)
    tr[0] = high[0] - low[0]
    plus_dm[0] = 0.0
    minus_dm[0] = 0.0
    for j in range(1, n):
        tr[j] = max(high[j] - low[j], abs(high[j] - close[j - 1]), abs(low[j] - close[j - 1]))
        up = high[j] - high[j - 1]
        down = low[j - 1] - low[j]
        plus_dm[j] = up if (up > down and up > 0) else 0.0
        minus_dm[j] = down if (down > up and down > 0) else 0.0
    atr_s = np.mean(tr[1:period + 1])
    plus_dm_s = np.mean(plus_dm[1:period + 1])
    minus_dm_s = np.mean(minus_dm[1:period + 1])
    dx_arr = np.full(n, np.nan, dtype=float)
    for j in range(period, n):
        if j > period:
            atr_s = (atr_s * (period - 1) + tr[j]) / period
            plus_dm_s = (plus_dm_s * (period - 1) + plus_dm[j]) / period
            minus_dm_s = (minus_dm_s * (period - 1) + minus_dm[j]) / period
        if atr_s == 0:
            continue
        plus_di = 100.0 * plus_dm_s / atr_s
        minus_di = 100.0 * minus_dm_s / atr_s
        denom = plus_di + minus_di
        if denom == 0:
            dx_arr[j] = 0.0
        else:
            dx_arr[j] = 100.0 * abs(plus_di - minus_di) / denom
    start = period
    while start < n and np.isnan(dx_arr[start]):
        start += 1
    if start + period > n:
        return adx
    adx[start + period - 1] = np.nanmean(dx_arr[start:start + period])
    for j in range(start + period, n):
        if not np.isnan(dx_arr[j]):
            adx[j] = (adx[j - 1] * (period - 1) + dx_arr[j]) / period
    return adx


def _calculate_bb(close: np.ndarray, period: int = 20, num_std: float = 2.0):
    """Bollinger Bands. Returns (upper, middle, lower)."""
    mid = np.full_like(close, np.nan, dtype=float)
    upper = np.full_like(close, np.nan, dtype=float)
    lower = np.full_like(close, np.nan, dtype=float)
    for j in range(period - 1, len(close)):
        window = close[j - period + 1:j + 1]
        m = np.mean(window)
        s = np.std(window)
        mid[j] = m
        upper[j] = m + num_std * s
        lower[j] = m - num_std * s
    return upper, mid, lower


def _calculate_macd(close: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD line, signal line, histogram."""
    ema_fast = _calculate_ema(close, fast)
    ema_slow = _calculate_ema(close, slow)
    macd_line = ema_fast - ema_slow
    sig_line = _calculate_ema(macd_line[~np.isnan(macd_line)], signal)
    # Align signal line back to full array
    full_sig = np.full_like(close, np.nan, dtype=float)
    offset = len(close) - len(sig_line)
    full_sig[offset:] = sig_line
    hist = macd_line - full_sig
    return macd_line, full_sig, hist


def _extract_arrays(data):
    """Extract OHLCV arrays from data (dict, NpDataFrame, or pandas DataFrame)."""
    if hasattr(data, 'columns') and hasattr(data, 'iloc'):
        # pandas DataFrame
        return (data["open"].values.astype(float), data["high"].values.astype(float),
                data["low"].values.astype(float), data["close"].values.astype(float),
                data["volume"].values.astype(float))
    # dict of arrays or NpDataFrame-like wrapper
    def _to_arr(v):
        if hasattr(v, 'values'):
            return np.asarray(v.values, dtype=float)
        return np.asarray(v, dtype=float)
    return (_to_arr(data["open"]), _to_arr(data["high"]),
            _to_arr(data["low"]), _to_arr(data["close"]),
            _to_arr(data["volume"]))


def _data_len(data) -> int:
    if hasattr(data, '__len__'):
        return len(data)
    v = data.get("close", data.get("Close", []))
    if hasattr(v, 'values'):
        return len(v.values)
    return len(v)


def _volume_avg(volume: np.ndarray, period: int = 20) -> np.ndarray:
    """Simple moving average of volume."""
    avg = np.full_like(volume, np.nan, dtype=float)
    for j in range(period - 1, len(volume)):
        avg[j] = np.mean(volume[j - period + 1:j + 1])
    return avg


# ---------------------------------------------------------------------------
# Strategy 1: TrendGuard Long
# ---------------------------------------------------------------------------

class TrendGuardLongStrategy:
    """Go long in uptrends when not overbought, on a bullish candle.

    3 conditions:
      - EMA(20) > EMA(50)  -- uptrend
      - RSI(14) < 55       -- not overbought
      - close > open        -- bullish candle
    """

    strategy_name = "TrendGuard_Long_v1"

    def generate_signals(self, data: dict, symbol: str) -> List[Signal]:
        if _data_len(data) < 60:
            return []
        op, hi, lo, cl, vol = _extract_arrays(data)
        i = len(cl) - 1

        ema20 = _calculate_ema(cl, 20)
        ema50 = _calculate_ema(cl, 50)
        rsi = _calculate_rsi(cl, 14)
        atr = _calculate_atr(hi, lo, cl, 14)

        if np.isnan(ema20[i]) or np.isnan(ema50[i]) or np.isnan(rsi[i]) or np.isnan(atr[i]):
            return []
        if atr[i] <= 0:
            return []

        # 3 conditions
        uptrend = ema20[i] > ema50[i]
        not_overbought = rsi[i] < 55
        bullish_candle = cl[i] > op[i]

        if uptrend and not_overbought and bullish_candle:
            entry = cl[i]
            tp = entry + 2.0 * atr[i]
            sl = entry - 1.0 * atr[i]
            conf = 0.55 + 0.15 * (55 - rsi[i]) / 55  # higher conf when RSI lower
            return [Signal(
                symbol=symbol, direction="BUY", entry_price=entry,
                take_profit=tp, stop_loss=sl,
                confidence=round(min(conf, 0.80), 2),
                strategy_name=self.strategy_name,
                metadata={"ema20": round(ema20[i], 2), "ema50": round(ema50[i], 2),
                          "rsi": round(rsi[i], 1), "atr": round(atr[i], 4)}
            )]
        return []


# ---------------------------------------------------------------------------
# Strategy 2: TrendGuard Short
# ---------------------------------------------------------------------------

class TrendGuardShortStrategy:
    """Go short in downtrends when not oversold, on a bearish candle.

    3 conditions:
      - EMA(20) < EMA(50)  -- downtrend
      - RSI(14) > 45       -- not oversold
      - close < open        -- bearish candle
    """

    strategy_name = "TrendGuard_Short_v1"

    def generate_signals(self, data: dict, symbol: str) -> List[Signal]:
        if _data_len(data) < 60:
            return []
        op, hi, lo, cl, vol = _extract_arrays(data)
        i = len(cl) - 1

        ema20 = _calculate_ema(cl, 20)
        ema50 = _calculate_ema(cl, 50)
        rsi = _calculate_rsi(cl, 14)
        atr = _calculate_atr(hi, lo, cl, 14)

        if np.isnan(ema20[i]) or np.isnan(ema50[i]) or np.isnan(rsi[i]) or np.isnan(atr[i]):
            return []
        if atr[i] <= 0:
            return []

        downtrend = ema20[i] < ema50[i]
        not_oversold = rsi[i] > 45
        bearish_candle = cl[i] < op[i]

        if downtrend and not_oversold and bearish_candle:
            entry = cl[i]
            tp = entry - 2.0 * atr[i]
            sl = entry + 1.0 * atr[i]
            conf = 0.55 + 0.15 * (rsi[i] - 45) / 55
            return [Signal(
                symbol=symbol, direction="SELL", entry_price=entry,
                take_profit=tp, stop_loss=sl,
                confidence=round(min(conf, 0.80), 2),
                strategy_name=self.strategy_name,
                metadata={"ema20": round(ema20[i], 2), "ema50": round(ema50[i], 2),
                          "rsi": round(rsi[i], 1), "atr": round(atr[i], 4)}
            )]
        return []


# ---------------------------------------------------------------------------
# Strategy 3: Volatility Regime Filter
# ---------------------------------------------------------------------------

class VolatilityRegimeFilterStrategy:
    """Long in calm uptrends — avoid high-volatility cascades.

    3 conditions:
      - ATR(14)/close < 0.04  -- normalized vol under 4%
      - EMA(20) > EMA(50)     -- uptrend
      - RSI(14) < 60           -- room to run
    """

    strategy_name = "VolRegime_Filter_v1"

    def generate_signals(self, data: dict, symbol: str) -> List[Signal]:
        if _data_len(data) < 60:
            return []
        op, hi, lo, cl, vol = _extract_arrays(data)
        i = len(cl) - 1

        ema20 = _calculate_ema(cl, 20)
        ema50 = _calculate_ema(cl, 50)
        rsi = _calculate_rsi(cl, 14)
        atr = _calculate_atr(hi, lo, cl, 14)

        if np.isnan(ema20[i]) or np.isnan(ema50[i]) or np.isnan(rsi[i]) or np.isnan(atr[i]):
            return []
        if atr[i] <= 0 or cl[i] <= 0:
            return []

        norm_vol = atr[i] / cl[i]
        calm = norm_vol < 0.04
        uptrend = ema20[i] > ema50[i]
        not_extended = rsi[i] < 60

        if calm and uptrend and not_extended:
            entry = cl[i]
            tp = entry + 1.5 * atr[i]
            sl = entry - 1.0 * atr[i]
            conf = 0.55 + 0.15 * (0.04 - norm_vol) / 0.04
            return [Signal(
                symbol=symbol, direction="BUY", entry_price=entry,
                take_profit=tp, stop_loss=sl,
                confidence=round(min(conf, 0.80), 2),
                strategy_name=self.strategy_name,
                metadata={"norm_vol": round(norm_vol, 4), "rsi": round(rsi[i], 1),
                          "atr": round(atr[i], 4)}
            )]
        return []


# ---------------------------------------------------------------------------
# Strategy 4: Multi-Timeframe Trend (EMA Stack)
# ---------------------------------------------------------------------------

class MultiTimeframeTrendStrategy:
    """Trade with triple EMA alignment. Bull stack = BUY, bear stack = SELL.

    3 conditions (bull):
      - EMA(9) > EMA(21) > EMA(50)  -- 3-level alignment
      - Close within 2.0 * ATR of EMA(21)  -- not too extended
    Bear is the mirror.
    """

    strategy_name = "MTF_Trend_v1"

    def generate_signals(self, data: dict, symbol: str) -> List[Signal]:
        if _data_len(data) < 60:
            return []
        op, hi, lo, cl, vol = _extract_arrays(data)
        i = len(cl) - 1

        ema9 = _calculate_ema(cl, 9)
        ema21 = _calculate_ema(cl, 21)
        ema50 = _calculate_ema(cl, 50)
        atr = _calculate_atr(hi, lo, cl, 14)

        if np.isnan(ema9[i]) or np.isnan(ema21[i]) or np.isnan(ema50[i]) or np.isnan(atr[i]):
            return []
        if atr[i] <= 0:
            return []

        bull_stack = ema9[i] > ema21[i] > ema50[i]
        bear_stack = ema9[i] < ema21[i] < ema50[i]
        dist_from_ema21 = abs(cl[i] - ema21[i])
        not_extended = dist_from_ema21 < 2.0 * atr[i]

        if bull_stack and not_extended:
            entry = cl[i]
            tp = entry + 2.0 * atr[i]
            sl = entry - 1.0 * atr[i]
            # Confidence based on how tight the stack is
            stack_spread = (ema9[i] - ema50[i]) / cl[i]
            conf = 0.55 + min(0.20, stack_spread * 10)
            return [Signal(
                symbol=symbol, direction="BUY", entry_price=entry,
                take_profit=tp, stop_loss=sl,
                confidence=round(min(conf, 0.80), 2),
                strategy_name=self.strategy_name,
                metadata={"ema9": round(ema9[i], 2), "ema21": round(ema21[i], 2),
                          "ema50": round(ema50[i], 2), "dist_atr": round(dist_from_ema21 / atr[i], 2)}
            )]

        if bear_stack and not_extended:
            entry = cl[i]
            tp = entry - 2.0 * atr[i]
            sl = entry + 1.0 * atr[i]
            stack_spread = (ema50[i] - ema9[i]) / cl[i]
            conf = 0.55 + min(0.20, stack_spread * 10)
            return [Signal(
                symbol=symbol, direction="SELL", entry_price=entry,
                take_profit=tp, stop_loss=sl,
                confidence=round(min(conf, 0.80), 2),
                strategy_name=self.strategy_name,
                metadata={"ema9": round(ema9[i], 2), "ema21": round(ema21[i], 2),
                          "ema50": round(ema50[i], 2), "dist_atr": round(dist_from_ema21 / atr[i], 2)}
            )]
        return []


# ---------------------------------------------------------------------------
# Strategy 5: Mean Reversion Timing
# ---------------------------------------------------------------------------

class MeanReversionTimingStrategy:
    """Buy oversold bounces. Just 2 conditions.

    2 conditions:
      - RSI(14) < 35       -- oversold
      - close > open        -- bullish reversal candle
    """

    strategy_name = "MeanRev_Timing_v1"

    def generate_signals(self, data: dict, symbol: str) -> List[Signal]:
        if _data_len(data) < 20:
            return []
        op, hi, lo, cl, vol = _extract_arrays(data)
        i = len(cl) - 1

        rsi = _calculate_rsi(cl, 14)
        atr = _calculate_atr(hi, lo, cl, 14)

        if np.isnan(rsi[i]) or np.isnan(atr[i]):
            return []
        if atr[i] <= 0:
            return []

        oversold = rsi[i] < 35
        bullish_candle = cl[i] > op[i]

        if oversold and bullish_candle:
            entry = cl[i]
            tp = entry + 2.0 * atr[i]
            sl = entry - 1.0 * atr[i]
            conf = 0.60 + 0.20 * (35 - rsi[i]) / 35  # deeper oversold = higher conf
            return [Signal(
                symbol=symbol, direction="BUY", entry_price=entry,
                take_profit=tp, stop_loss=sl,
                confidence=round(min(conf, 0.85), 2),
                strategy_name=self.strategy_name,
                metadata={"rsi": round(rsi[i], 1), "atr": round(atr[i], 4)}
            )]
        return []


# ---------------------------------------------------------------------------
# Strategy 6: Adaptive Regime
# ---------------------------------------------------------------------------

class AdaptiveRegimeStrategy:
    """Switch between trend-following and mean-reversion based on ADX.

    Trending (ADX > 20): trade EMA(20) vs EMA(50) direction
    Ranging  (ADX <= 20): buy RSI < 35, sell RSI > 65
    """

    strategy_name = "Adaptive_Regime_v1"

    def generate_signals(self, data: dict, symbol: str) -> List[Signal]:
        if _data_len(data) < 60:
            return []
        op, hi, lo, cl, vol = _extract_arrays(data)
        i = len(cl) - 1

        ema20 = _calculate_ema(cl, 20)
        ema50 = _calculate_ema(cl, 50)
        rsi = _calculate_rsi(cl, 14)
        atr = _calculate_atr(hi, lo, cl, 14)
        adx = _calculate_adx(hi, lo, cl, 14)

        if np.isnan(adx[i]) or np.isnan(rsi[i]) or np.isnan(atr[i]):
            return []
        if np.isnan(ema20[i]) or np.isnan(ema50[i]):
            return []
        if atr[i] <= 0:
            return []

        entry = cl[i]
        regime = "trending" if adx[i] > 20 else "ranging"

        if regime == "trending":
            if ema20[i] > ema50[i]:
                tp = entry + 2.0 * atr[i]
                sl = entry - 1.0 * atr[i]
                conf = 0.55 + 0.15 * min(adx[i] / 50, 1.0)
                return [Signal(
                    symbol=symbol, direction="BUY", entry_price=entry,
                    take_profit=tp, stop_loss=sl,
                    confidence=round(min(conf, 0.80), 2),
                    strategy_name=self.strategy_name,
                    metadata={"regime": regime, "adx": round(adx[i], 1), "rsi": round(rsi[i], 1)}
                )]
            else:
                tp = entry - 2.0 * atr[i]
                sl = entry + 1.0 * atr[i]
                conf = 0.55 + 0.15 * min(adx[i] / 50, 1.0)
                return [Signal(
                    symbol=symbol, direction="SELL", entry_price=entry,
                    take_profit=tp, stop_loss=sl,
                    confidence=round(min(conf, 0.80), 2),
                    strategy_name=self.strategy_name,
                    metadata={"regime": regime, "adx": round(adx[i], 1), "rsi": round(rsi[i], 1)}
                )]
        else:
            # Ranging — mean reversion
            if rsi[i] < 35:
                tp = entry + 2.0 * atr[i]
                sl = entry - 1.0 * atr[i]
                return [Signal(
                    symbol=symbol, direction="BUY", entry_price=entry,
                    take_profit=tp, stop_loss=sl,
                    confidence=round(0.60, 2),
                    strategy_name=self.strategy_name,
                    metadata={"regime": regime, "adx": round(adx[i], 1), "rsi": round(rsi[i], 1)}
                )]
            elif rsi[i] > 65:
                tp = entry - 2.0 * atr[i]
                sl = entry + 1.0 * atr[i]
                return [Signal(
                    symbol=symbol, direction="SELL", entry_price=entry,
                    take_profit=tp, stop_loss=sl,
                    confidence=round(0.60, 2),
                    strategy_name=self.strategy_name,
                    metadata={"regime": regime, "adx": round(adx[i], 1), "rsi": round(rsi[i], 1)}
                )]
        return []


# ---------------------------------------------------------------------------
# Strategy 7: Cascade Sell Recovery
# ---------------------------------------------------------------------------

class CascadeSellRecoveryStrategy:
    """Buy after a cascade of selling shows reversal signs.

    2 conditions:
      - At least 2 of last 3 candles are red (recent selling pressure)
      - Current candle shows buying: lower wick > 40% of range OR close > open
    """

    strategy_name = "Cascade_Recovery_v1"

    def generate_signals(self, data: dict, symbol: str) -> List[Signal]:
        if _data_len(data) < 20:
            return []
        op, hi, lo, cl, vol = _extract_arrays(data)
        i = len(cl) - 1
        if i < 3:
            return []

        atr = _calculate_atr(hi, lo, cl, 14)
        if np.isnan(atr[i]) or atr[i] <= 0:
            return []

        # Count red candles in last 3 (excluding current)
        red_count = 0
        for k in range(i - 3, i):
            if cl[k] < op[k]:
                red_count += 1

        if red_count < 2:
            return []

        # Current candle shows buying
        candle_range = hi[i] - lo[i]
        if candle_range <= 0:
            return []

        lower_wick = min(op[i], cl[i]) - lo[i]
        buying_tail = lower_wick / candle_range > 0.40
        bullish_close = cl[i] > op[i]

        if buying_tail or bullish_close:
            entry = cl[i]
            tp = entry + 1.5 * atr[i]
            sl = entry - 0.75 * atr[i]
            conf = 0.55 + 0.10 * (red_count / 3)
            if buying_tail and bullish_close:
                conf += 0.05  # both signals = stronger
            return [Signal(
                symbol=symbol, direction="BUY", entry_price=entry,
                take_profit=tp, stop_loss=sl,
                confidence=round(min(conf, 0.80), 2),
                strategy_name=self.strategy_name,
                metadata={"red_candles_3": red_count, "buying_tail": buying_tail,
                          "bullish_close": bullish_close, "atr": round(atr[i], 4)}
            )]
        return []


# ---------------------------------------------------------------------------
# Strategy 8: Divergence Entry
# ---------------------------------------------------------------------------

class DivergenceEntryStrategy:
    """Simple RSI divergence detection.

    Bullish divergence (BUY):
      - Price made lower low vs 10 bars ago window
      - RSI did NOT make lower low (higher RSI at lower price)

    Bearish divergence (SELL):
      - Price made higher high vs 10 bars ago window
      - RSI did NOT make higher high
    """

    strategy_name = "Divergence_Entry_v1"

    def generate_signals(self, data: dict, symbol: str) -> List[Signal]:
        if _data_len(data) < 30:
            return []
        op, hi, lo, cl, vol = _extract_arrays(data)
        i = len(cl) - 1

        rsi = _calculate_rsi(cl, 14)
        atr = _calculate_atr(hi, lo, cl, 14)

        if np.isnan(rsi[i]) or np.isnan(atr[i]) or atr[i] <= 0:
            return []

        # Need enough RSI history
        lookback_start = max(0, i - 15)
        lookback_end = max(0, i - 5)
        if lookback_end <= lookback_start:
            return []

        # Check for NaN in lookback window
        rsi_window = rsi[lookback_start:lookback_end]
        cl_window = cl[lookback_start:lookback_end]
        if np.any(np.isnan(rsi_window)) or len(rsi_window) == 0:
            return []

        price_prev_low = np.min(cl_window)
        price_prev_high = np.max(cl_window)
        rsi_prev_low = np.min(rsi_window)
        rsi_prev_high = np.max(rsi_window)

        entry = cl[i]

        # Bullish divergence: price lower low, RSI higher low
        if cl[i] < price_prev_low and rsi[i] > rsi_prev_low:
            tp = entry + 2.0 * atr[i]
            sl = entry - 1.0 * atr[i]
            # Stronger divergence = bigger gap between price direction and RSI direction
            rsi_diff = rsi[i] - rsi_prev_low
            conf = 0.55 + min(0.20, rsi_diff / 30)
            return [Signal(
                symbol=symbol, direction="BUY", entry_price=entry,
                take_profit=tp, stop_loss=sl,
                confidence=round(min(conf, 0.80), 2),
                strategy_name=self.strategy_name,
                metadata={"type": "bullish_div", "rsi": round(rsi[i], 1),
                          "rsi_prev_low": round(rsi_prev_low, 1),
                          "price_prev_low": round(price_prev_low, 2)}
            )]

        # Bearish divergence: price higher high, RSI lower high
        if cl[i] > price_prev_high and rsi[i] < rsi_prev_high:
            tp = entry - 2.0 * atr[i]
            sl = entry + 1.0 * atr[i]
            rsi_diff = rsi_prev_high - rsi[i]
            conf = 0.55 + min(0.20, rsi_diff / 30)
            return [Signal(
                symbol=symbol, direction="SELL", entry_price=entry,
                take_profit=tp, stop_loss=sl,
                confidence=round(min(conf, 0.80), 2),
                strategy_name=self.strategy_name,
                metadata={"type": "bearish_div", "rsi": round(rsi[i], 1),
                          "rsi_prev_high": round(rsi_prev_high, 1),
                          "price_prev_high": round(price_prev_high, 2)}
            )]

        return []


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_STRATEGIES = [
    TrendGuardLongStrategy,
    TrendGuardShortStrategy,
    VolatilityRegimeFilterStrategy,
    MultiTimeframeTrendStrategy,
    MeanReversionTimingStrategy,
    AdaptiveRegimeStrategy,
    CascadeSellRecoveryStrategy,
    DivergenceEntryStrategy,
]


# ---------------------------------------------------------------------------
# Live test harness
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import requests
    import time

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    for sym in symbols:
        url = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1h&limit=500"
        r = requests.get(url, timeout=30)
        klines = r.json()
        data = {
            "open": np.array([float(k[1]) for k in klines]),
            "high": np.array([float(k[2]) for k in klines]),
            "low": np.array([float(k[3]) for k in klines]),
            "close": np.array([float(k[4]) for k in klines]),
            "volume": np.array([float(k[5]) for k in klines]),
        }

        print(f"\n{'=' * 60}")
        print(f"  {sym} -- 500 x 1h bars")
        print(f"{'=' * 60}")

        # Walk through last 200 bars
        total_trades = 0
        for strat_cls in ALL_STRATEGIES:
            strat = strat_cls()
            count = 0
            for j in range(300, 500):
                sliced = {k: v[:j] for k, v in data.items()}
                sigs = strat.generate_signals(sliced, sym)
                count += len(sigs)
            total_trades += count

            # Also get the latest signal
            last_sig = None
            sigs = strat.generate_signals(data, sym)
            if sigs:
                last_sig = sigs[0]

            status = f"{count} trades"
            if last_sig:
                status += f" | LIVE: {last_sig.direction} @ {last_sig.entry_price:.2f} conf={last_sig.confidence:.2f}"
            print(f"  {strat.strategy_name:30s} {status}")

        print(f"  {'TOTAL':30s} {total_trades} trades")
        time.sleep(0.5)
