#!/usr/bin/env python3
"""
EMA Retracement Mean Reversion Strategy
=========================================
From r/algotrading: Use EMA as dynamic support/resistance. When price retraces
TO the EMA in a trend, enter expecting a bounce. Tight SL (just below EMA)
gives favorable R:R because the stop is close.

Our data confirms this works: winners have LOWER R:R (1.81 vs 1.99 losers)
and enter at LOWER volume (calm pullback, not FOMO spike). Mean reversion
is our best crypto approach (60.3% WR in backtest).

Three sub-strategies:
  A) ema21_retracement   — retracement to EMA(21), fastest signals
  B) ema50_retracement   — retracement to EMA(50), deeper pullback
  C) ema_stack_retracement — EMA(21) retracement + perfect stack (21>50>200)

References:
  - Kavajecz & Odders-White (2004): Moving averages as S/R proxies
  - Nison (1991): Dynamic support at short-term MAs
  - Our own forward-test data: mean reversion Portfolio D = 60.3% WR

Exports:
  EMA_RETRACEMENT_STRATEGIES  — dict for scanner.py
  run_backtest()              — standalone backtester (90d 4H data)

Pure Python + numpy. No pandas required at runtime.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

try:
    from api_failover import fetch_klines
except ImportError:
    fetch_klines = None

try:
    from fast_regime_detector import get_fast_regime
except ImportError:
    get_fast_regime = None

try:
    from config import DATA_DIR
except ImportError:
    DATA_DIR = _THIS_DIR / "data"

_log = logging.getLogger("alpha_engine.ema_retracement")

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


# ===========================================================================
# Indicator helpers (pure numpy — no pandas dependency)
# ===========================================================================

def _ema_np(arr: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average using numpy."""
    alpha = 2.0 / (period + 1)
    out = np.empty_like(arr, dtype=np.float64)
    out[0] = arr[0]
    for i in range(1, len(arr)):
        out[i] = alpha * arr[i] + (1 - alpha) * out[i - 1]
    return out


def _sma_np(arr: np.ndarray, period: int) -> np.ndarray:
    """Simple Moving Average using numpy."""
    out = np.full_like(arr, np.nan, dtype=np.float64)
    cumsum = np.cumsum(arr)
    out[period - 1:] = (cumsum[period - 1:] - np.concatenate(([0], cumsum[:-period]))) / period
    return out


def _atr_np(high: np.ndarray, low: np.ndarray, close: np.ndarray,
            period: int = 14) -> np.ndarray:
    """Average True Range (Wilder smoothing)."""
    n = len(close)
    tr = np.empty(n, dtype=np.float64)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i],
                     abs(high[i] - close[i - 1]),
                     abs(low[i] - close[i - 1]))
    return _ema_np(tr, period)


def _rsi_np(close: np.ndarray, period: int = 14) -> np.ndarray:
    """RSI using Wilder smoothing."""
    n = len(close)
    out = np.full(n, 50.0, dtype=np.float64)
    if n < period + 1:
        return out
    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            out[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i + 1] = 100.0 - (100.0 / (1.0 + rs))
    return out


def _volume_ratio_np(volume: np.ndarray, period: int = 20) -> np.ndarray:
    """Current volume / SMA(volume, period)."""
    avg = _sma_np(volume, period)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(avg > 0, volume / avg, 1.0)
    return ratio


def _swing_high(high: np.ndarray, lookback: int = 20) -> float:
    """Most recent swing high in last `lookback` bars."""
    return float(np.max(high[-lookback:]))


def _swing_low(low: np.ndarray, lookback: int = 20) -> float:
    """Most recent swing low in last `lookback` bars."""
    return float(np.min(low[-lookback:]))


def _ema_slope(ema_vals: np.ndarray, bars: int = 5) -> float:
    """Average per-bar change of EMA over last `bars` bars."""
    if len(ema_vals) < bars + 1:
        return 0.0
    segment = ema_vals[-(bars + 1):]
    return float(np.mean(np.diff(segment)))


def _smart_round(value: float) -> float:
    """Round to appropriate precision based on magnitude."""
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    else:
        return round(value, 10)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ===========================================================================
# Core detection logic
# ===========================================================================

def _detect_uptrend(ema_vals: np.ndarray, bars: int = 5) -> bool:
    """EMA slope positive for `bars` consecutive bars = uptrend."""
    if len(ema_vals) < bars + 2:
        return False
    diffs = np.diff(ema_vals[-(bars + 1):])
    return bool(np.all(diffs > 0))


def _detect_downtrend(ema_vals: np.ndarray, bars: int = 5) -> bool:
    """EMA slope negative for `bars` consecutive bars = downtrend."""
    if len(ema_vals) < bars + 2:
        return False
    diffs = np.diff(ema_vals[-(bars + 1):])
    return bool(np.all(diffs < 0))


def _retracement_to_ema(close: np.ndarray, ema_vals: np.ndarray,
                         atr_vals: np.ndarray,
                         min_distance_atr: float = 1.0,
                         touch_threshold_atr: float = 0.3,
                         lookback: int = 10) -> str:
    """Detect if price retraced TO the EMA.

    Returns:
        'LONG'  — price was above EMA, pulled back to touch it (uptrend retracement)
        'SHORT' — price was below EMA, rallied back to touch it (downtrend retracement)
        ''      — no retracement detected
    """
    if len(close) < lookback + 1 or len(ema_vals) < lookback + 1:
        return ""

    current_close = close[-1]
    current_ema = ema_vals[-1]
    current_atr = atr_vals[-1]

    if current_atr <= 0:
        return ""

    # Current distance from EMA (normalized by ATR)
    dist_now = abs(current_close - current_ema) / current_atr

    # Price must be NEAR the EMA now (within touch_threshold)
    if dist_now > touch_threshold_atr:
        return ""

    # Check if price was AWAY from EMA recently (at least min_distance_atr away)
    recent_close = close[-(lookback + 1):-1]
    recent_ema = ema_vals[-(lookback + 1):-1]
    dists = (recent_close - recent_ema) / current_atr

    # Was price above EMA by enough? -> LONG (pullback from above)
    if np.any(dists >= min_distance_atr):
        return "LONG"

    # Was price below EMA by enough? -> SHORT (rally from below)
    if np.any(dists <= -min_distance_atr):
        return "SHORT"

    return ""


def _check_entry_conditions(direction: str, rsi_val: float,
                             vol_ratio: float) -> bool:
    """Confirm entry with RSI and volume filters.

    LONG:  RSI 35-55 (not overbought) + volume < 1.5x avg (calm pullback)
    SHORT: RSI 45-65 (not oversold)   + volume < 1.5x avg (calm pullback)
    """
    if vol_ratio >= 1.5:
        return False  # Volume filter: reject spikes (FOMO/panic)

    if direction == "LONG":
        return 35.0 <= rsi_val <= 55.0
    elif direction == "SHORT":
        return 45.0 <= rsi_val <= 65.0
    return False


def _compute_tp_sl(direction: str, price: float, ema_val: float,
                    atr_val: float, high: np.ndarray, low: np.ndarray,
                    lookback: int = 20) -> tuple:
    """Compute TP/SL with tight EMA-based stop.

    SL: Just beyond EMA + 0.5x ATR buffer (~1-2% tight stop)
    TP: Max of (previous swing high/low, 2x distance to SL) -> R:R >= 2.0
    """
    if direction == "LONG":
        sl = ema_val - 0.5 * atr_val
        swing_target = _swing_high(high, lookback)
        min_tp = price + 2.0 * (price - sl)  # Guarantee R:R >= 2.0
        tp = max(swing_target, min_tp)
        # Sanity: TP must be above price
        if tp <= price:
            tp = price + 2.0 * atr_val
    else:  # SHORT
        sl = ema_val + 0.5 * atr_val
        swing_target = _swing_low(low, lookback)
        min_tp = price - 2.0 * (sl - price)  # Guarantee R:R >= 2.0
        tp = min(swing_target, min_tp)
        # Sanity: TP must be below price
        if tp >= price:
            tp = price - 2.0 * atr_val

    return _smart_round(tp), _smart_round(sl)


def _get_regime(symbol: str = "BTCUSDT") -> str:
    """Get market regime. Uses fast_regime_detector if available, else 'UNKNOWN'."""
    if get_fast_regime is not None:
        try:
            result = get_fast_regime(symbol)
            return result.get("regime", "UNKNOWN")
        except Exception:
            pass
    return "UNKNOWN"


def _regime_allows(direction: str, regime: str) -> bool:
    """Check if regime allows the direction.

    LONG: allowed in BULL, STRONG_BULL, CHOPPY, RANGING, UNKNOWN
    SHORT: allowed in BEAR, STRONG_BEAR, UNKNOWN
    """
    regime_upper = regime.upper()
    if direction == "LONG":
        return regime_upper not in ("BEAR", "STRONG_BEAR")
    elif direction == "SHORT":
        return regime_upper in ("BEAR", "STRONG_BEAR", "UNKNOWN")
    return False


# ===========================================================================
# Strategy A: EMA(21) Retracement
# ===========================================================================

def ema21_retracement(data: "dict | pd.DataFrame", context: dict = None) -> list:
    """EMA(21) retracement — fastest signals, most trades."""
    return _run_ema_retracement(
        data=data,
        context=context,
        strategy_name="ema21_retracement",
        ema_period=21,
        min_distance_atr=1.0,
        touch_threshold_atr=0.3,
        trend_bars=5,
    )


# ===========================================================================
# Strategy B: EMA(50) Retracement
# ===========================================================================

def ema50_retracement(data: "dict | pd.DataFrame", context: dict = None) -> list:
    """EMA(50) retracement — deeper pullback, higher WR expected."""
    return _run_ema_retracement(
        data=data,
        context=context,
        strategy_name="ema50_retracement",
        ema_period=50,
        min_distance_atr=1.5,
        touch_threshold_atr=0.4,
        trend_bars=8,
    )


# ===========================================================================
# Strategy C: EMA Stack Retracement (21 > 50 > 200 alignment)
# ===========================================================================

def ema_stack_retracement(data: "dict | pd.DataFrame", context: dict = None) -> list:
    """EMA stack retracement — perfect EMA alignment (21>50>200), highest conviction."""
    return _run_ema_retracement(
        data=data,
        context=context,
        strategy_name="ema_stack_retracement",
        ema_period=21,
        min_distance_atr=1.0,
        touch_threshold_atr=0.3,
        trend_bars=5,
        require_stack=True,
    )


# ===========================================================================
# Shared engine for all 3 strategies
# ===========================================================================

def _run_ema_retracement(data, context: dict = None,
                          strategy_name: str = "ema21_retracement",
                          ema_period: int = 21,
                          min_distance_atr: float = 1.0,
                          touch_threshold_atr: float = 0.3,
                          trend_bars: int = 5,
                          require_stack: bool = False) -> list:
    """Core EMA retracement engine.

    Accepts either:
      - pandas DataFrame (from scanner.py via data dict)
      - dict with numpy arrays (from standalone backtest)
    """
    signals = []

    # --- Extract OHLCV arrays ---
    try:
        import pandas as pd
        _has_pandas = True
    except ImportError:
        _has_pandas = False

    if _has_pandas and hasattr(data, "items") and not isinstance(data, np.ndarray):
        # data is dict[symbol -> DataFrame] from scanner
        for symbol, df in data.items():
            if not hasattr(df, "columns"):
                continue
            try:
                close = df["Close"].values.astype(np.float64)
                high = df["High"].values.astype(np.float64)
                low = df["Low"].values.astype(np.float64)
                volume = df["Volume"].values.astype(np.float64)
            except (KeyError, AttributeError):
                continue
            if len(close) < max(200, ema_period + 30):
                continue
            sig = _analyze_symbol(
                symbol=symbol, close=close, high=high, low=low, volume=volume,
                strategy_name=strategy_name, ema_period=ema_period,
                min_distance_atr=min_distance_atr,
                touch_threshold_atr=touch_threshold_atr,
                trend_bars=trend_bars, require_stack=require_stack,
                context=context,
            )
            if sig:
                signals.append(sig)
    elif isinstance(data, dict) and "close" in data:
        # Raw numpy dict from backtest
        sig = _analyze_symbol(
            symbol=data.get("symbol", "UNKNOWN"),
            close=data["close"], high=data["high"],
            low=data["low"], volume=data["volume"],
            strategy_name=strategy_name, ema_period=ema_period,
            min_distance_atr=min_distance_atr,
            touch_threshold_atr=touch_threshold_atr,
            trend_bars=trend_bars, require_stack=require_stack,
            context=context,
        )
        if sig:
            signals.append(sig)

    return signals


def _analyze_symbol(symbol: str, close: np.ndarray, high: np.ndarray,
                     low: np.ndarray, volume: np.ndarray,
                     strategy_name: str, ema_period: int,
                     min_distance_atr: float, touch_threshold_atr: float,
                     trend_bars: int, require_stack: bool,
                     context: dict = None) -> Optional[dict]:
    """Run EMA retracement analysis on a single symbol."""

    n = len(close)
    if n < 210:  # Need 200 for EMA(200) + buffer
        return None

    # Compute indicators
    ema_main = _ema_np(close, ema_period)
    atr_vals = _atr_np(high, low, close, 14)
    rsi_vals = _rsi_np(close, 14)
    vol_ratio = _volume_ratio_np(volume, 20)

    current_atr = atr_vals[-1]
    current_rsi = rsi_vals[-1]
    current_vol_ratio = vol_ratio[-1]
    current_price = close[-1]

    if current_atr <= 0 or math.isnan(current_atr):
        return None

    # Step 1: Detect trend on the target EMA
    is_uptrend = _detect_uptrend(ema_main, trend_bars)
    is_downtrend = _detect_downtrend(ema_main, trend_bars)

    if not is_uptrend and not is_downtrend:
        return None  # No clear trend

    # Step 2: Detect retracement to EMA
    direction = _retracement_to_ema(
        close, ema_main, atr_vals,
        min_distance_atr=min_distance_atr,
        touch_threshold_atr=touch_threshold_atr,
        lookback=10,
    )

    if not direction:
        return None

    # Trend-direction alignment
    if direction == "LONG" and not is_uptrend:
        return None
    if direction == "SHORT" and not is_downtrend:
        return None

    # Step 3: Stack alignment check (Strategy C)
    if require_stack:
        ema50 = _ema_np(close, 50)
        ema200 = _ema_np(close, 200)
        if direction == "LONG":
            if not (ema_main[-1] > ema50[-1] > ema200[-1]):
                return None
        else:  # SHORT
            if not (ema_main[-1] < ema50[-1] < ema200[-1]):
                return None

    # Step 4: Entry confirmation (RSI + volume filter)
    if not _check_entry_conditions(direction, current_rsi, current_vol_ratio):
        return None

    # Step 5: Regime filter
    regime = "UNKNOWN"
    if context and "regime" in context:
        regime = context.get("regime", "UNKNOWN")
    elif context and "fear_greed" in context:
        fg = context.get("fear_greed", 50)
        if fg >= 70:
            regime = "BULL"
        elif fg <= 30:
            regime = "BEAR"
        else:
            regime = "RANGING"
    else:
        regime = _get_regime(symbol)

    if not _regime_allows(direction, regime):
        return None

    # Step 6: TP/SL calculation
    tp, sl = _compute_tp_sl(direction, current_price, ema_main[-1],
                             current_atr, high, low, lookback=20)

    # Compute R:R
    risk = abs(current_price - sl)
    reward = abs(tp - current_price)
    rr = reward / risk if risk > 0 else 0

    # Confidence scoring
    confidence = 0.60
    # Bonus for calm volume (verified edge: +10pp WR)
    if current_vol_ratio < 1.0:
        confidence += 0.05
    # Bonus for strong trend
    slope = _ema_slope(ema_main, trend_bars)
    slope_pct = abs(slope) / current_price * 100 if current_price > 0 else 0
    if slope_pct > 0.1:
        confidence += 0.05
    # Bonus for stack alignment
    if require_stack:
        confidence += 0.05
    # Bonus for good R:R
    if rr >= 2.5:
        confidence += 0.05
    confidence = min(confidence, 0.85)

    signal_type = "BUY" if direction == "LONG" else "SELL"

    return {
        "symbol": symbol,
        "signal_type": signal_type,
        "direction": direction,
        "strategy": strategy_name,
        "entry_price": _smart_round(current_price),
        "take_profit": tp,
        "stop_loss": sl,
        "confidence": round(confidence, 3),
        "rr_ratio": round(rr, 2),
        "atr": _smart_round(current_atr),
        "rsi": round(current_rsi, 1),
        "volume_ratio": round(current_vol_ratio, 2),
        "ema_period": ema_period,
        "ema_value": _smart_round(ema_main[-1]),
        "regime": regime,
        "trailing_stop_ema": 9,  # After +1 ATR profit, trail at EMA(9)
        "trail_activate_atr": 1.0,  # Activate trailing after +1 ATR
        "max_hold_hours": 120,  # 5 days max hold
        "timestamp": _now_iso(),
        "source": "ema_retracement_strategy",
    }


# ===========================================================================
# Strategy dict for scanner.py
# ===========================================================================

EMA_RETRACEMENT_STRATEGIES = {
    "ema21_retracement": ema21_retracement,
    "ema50_retracement": ema50_retracement,
    "ema_stack_retracement": ema_stack_retracement,
}


# ===========================================================================
# Backtester
# ===========================================================================

BACKTEST_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT",
    "AVAXUSDT", "DOTUSDT", "LINKUSDT", "NEARUSDT", "FETUSDT",
    "RENDERUSDT", "PAXGUSDT",
]


def _fetch_4h_data(symbol: str, limit: int = 540) -> Optional[dict]:
    """Fetch 90 days of 4H klines (540 bars) via api_failover."""
    if fetch_klines is None:
        _log.warning("api_failover not available, skipping %s", symbol)
        return None

    klines = fetch_klines(symbol, interval="4h", limit=limit)
    if not klines or len(klines) < 210:
        _log.warning("Insufficient data for %s: got %d bars",
                     symbol, len(klines) if klines else 0)
        return None

    # Parse Binance kline format: [open_time, open, high, low, close, volume, ...]
    opens = np.array([float(k[1]) for k in klines], dtype=np.float64)
    highs = np.array([float(k[2]) for k in klines], dtype=np.float64)
    lows = np.array([float(k[3]) for k in klines], dtype=np.float64)
    closes = np.array([float(k[4]) for k in klines], dtype=np.float64)
    volumes = np.array([float(k[5]) for k in klines], dtype=np.float64)
    timestamps = [int(k[0]) for k in klines]

    return {
        "symbol": symbol,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "timestamps": timestamps,
    }


def _backtest_strategy_on_symbol(
    ohlcv: dict,
    strategy_name: str,
    ema_period: int,
    min_distance_atr: float,
    touch_threshold_atr: float,
    trend_bars: int,
    require_stack: bool,
) -> list:
    """Walk-forward backtest of a single strategy on a single symbol.

    Simulates bar-by-bar: at each bar, check for entry signal. If in a trade,
    check TP/SL/trailing/time-stop. Track all trades.
    """
    close = ohlcv["close"]
    high = ohlcv["high"]
    low = ohlcv["low"]
    volume = ohlcv["volume"]
    symbol = ohlcv["symbol"]
    n = len(close)

    if n < 210:
        return []

    # Pre-compute all indicators
    ema_main = _ema_np(close, ema_period)
    ema9 = _ema_np(close, 9)  # For trailing stop
    atr_vals = _atr_np(high, low, close, 14)
    rsi_vals = _rsi_np(close, 14)
    vol_ratio = _volume_ratio_np(volume, 20)

    if require_stack:
        ema50 = _ema_np(close, 50)
        ema200 = _ema_np(close, 200)

    trades = []
    in_trade = False
    trade = {}
    # Start from bar 210 to have enough history
    start_bar = 210

    for i in range(start_bar, n):
        if in_trade:
            # Check exit conditions
            entry = trade["entry_price"]
            tp = trade["tp"]
            sl = trade["sl"]
            direction = trade["direction"]
            bars_held = i - trade["entry_bar"]

            # Trailing stop update (after +1 ATR profit, trail at EMA(9))
            if direction == "LONG":
                profit_atr = (close[i] - entry) / atr_vals[trade["entry_bar"]]
                if profit_atr >= 1.0 and trade.get("trailing_active", False):
                    # Trail SL up to EMA(9)
                    new_sl = ema9[i] - 0.2 * atr_vals[i]
                    if new_sl > sl:
                        sl = new_sl
                        trade["sl"] = sl
                elif profit_atr >= 1.0:
                    trade["trailing_active"] = True

                # Check SL hit (use low of bar)
                if low[i] <= sl:
                    pnl_pct = ((sl - entry) / entry) * 100
                    trade["exit_price"] = sl
                    trade["exit_bar"] = i
                    trade["pnl_pct"] = pnl_pct
                    trade["exit_reason"] = "SL_HIT"
                    trades.append(trade)
                    in_trade = False
                    continue

                # Check TP hit (use high of bar)
                if high[i] >= tp:
                    pnl_pct = ((tp - entry) / entry) * 100
                    trade["exit_price"] = tp
                    trade["exit_bar"] = i
                    trade["pnl_pct"] = pnl_pct
                    trade["exit_reason"] = "TP_HIT"
                    trades.append(trade)
                    in_trade = False
                    continue

            else:  # SHORT
                profit_atr = (entry - close[i]) / atr_vals[trade["entry_bar"]]
                if profit_atr >= 1.0 and trade.get("trailing_active", False):
                    new_sl = ema9[i] + 0.2 * atr_vals[i]
                    if new_sl < sl:
                        sl = new_sl
                        trade["sl"] = sl
                elif profit_atr >= 1.0:
                    trade["trailing_active"] = True

                if high[i] >= sl:
                    pnl_pct = ((entry - sl) / entry) * 100
                    trade["exit_price"] = sl
                    trade["exit_bar"] = i
                    trade["pnl_pct"] = pnl_pct
                    trade["exit_reason"] = "SL_HIT"
                    trades.append(trade)
                    in_trade = False
                    continue

                if low[i] <= tp:
                    pnl_pct = ((entry - tp) / entry) * 100
                    trade["exit_price"] = tp
                    trade["exit_bar"] = i
                    trade["pnl_pct"] = pnl_pct
                    trade["exit_reason"] = "TP_HIT"
                    trades.append(trade)
                    in_trade = False
                    continue

            # Max hold: 30 bars = 5 days on 4H
            if bars_held >= 30:
                exit_price = close[i]
                if direction == "LONG":
                    pnl_pct = ((exit_price - entry) / entry) * 100
                else:
                    pnl_pct = ((entry - exit_price) / entry) * 100
                trade["exit_price"] = exit_price
                trade["exit_bar"] = i
                trade["pnl_pct"] = pnl_pct
                trade["exit_reason"] = "TIME_STOP"
                trades.append(trade)
                in_trade = False
                continue

        else:
            # Look for entry signal
            if atr_vals[i] <= 0 or math.isnan(atr_vals[i]):
                continue

            # Trend detection
            is_up = _detect_uptrend(ema_main[:i + 1], trend_bars)
            is_down = _detect_downtrend(ema_main[:i + 1], trend_bars)
            if not is_up and not is_down:
                continue

            # Retracement detection
            direction = _retracement_to_ema(
                close[:i + 1], ema_main[:i + 1], atr_vals[:i + 1],
                min_distance_atr=min_distance_atr,
                touch_threshold_atr=touch_threshold_atr,
                lookback=10,
            )
            if not direction:
                continue
            if direction == "LONG" and not is_up:
                continue
            if direction == "SHORT" and not is_down:
                continue

            # Stack check
            if require_stack:
                if direction == "LONG":
                    if not (ema_main[i] > ema50[i] > ema200[i]):
                        continue
                else:
                    if not (ema_main[i] < ema50[i] < ema200[i]):
                        continue

            # Entry confirmation
            if not _check_entry_conditions(direction, rsi_vals[i], vol_ratio[i]):
                continue

            # Compute TP/SL
            entry_price = close[i]
            ema_at_entry = ema_main[i]
            current_atr = atr_vals[i]

            if direction == "LONG":
                sl = ema_at_entry - 0.5 * current_atr
                swing_target = float(np.max(high[max(0, i - 20):i + 1]))
                min_tp = entry_price + 2.0 * (entry_price - sl)
                tp = max(swing_target, min_tp)
                if tp <= entry_price:
                    tp = entry_price + 2.0 * current_atr
            else:
                sl = ema_at_entry + 0.5 * current_atr
                swing_target = float(np.min(low[max(0, i - 20):i + 1]))
                min_tp = entry_price - 2.0 * (sl - entry_price)
                tp = min(swing_target, min_tp)
                if tp >= entry_price:
                    tp = entry_price - 2.0 * current_atr

            in_trade = True
            trade = {
                "symbol": symbol,
                "strategy": strategy_name,
                "direction": direction,
                "entry_price": entry_price,
                "entry_bar": i,
                "tp": tp,
                "sl": sl,
                "rsi_at_entry": rsi_vals[i],
                "vol_ratio_at_entry": vol_ratio[i],
                "atr_at_entry": current_atr,
                "trailing_active": False,
            }

    # Close any open trade at end
    if in_trade:
        exit_price = close[-1]
        direction = trade["direction"]
        entry = trade["entry_price"]
        if direction == "LONG":
            pnl_pct = ((exit_price - entry) / entry) * 100
        else:
            pnl_pct = ((entry - exit_price) / entry) * 100
        trade["exit_price"] = exit_price
        trade["exit_bar"] = n - 1
        trade["pnl_pct"] = pnl_pct
        trade["exit_reason"] = "OPEN_AT_END"
        trades.append(trade)

    return trades


def _compute_metrics(trades: list) -> dict:
    """Compute strategy metrics from trade list."""
    if not trades:
        return {
            "trade_count": 0, "win_rate": 0.0, "profit_factor": 0.0,
            "sharpe": 0.0, "avg_win_pct": 0.0, "avg_loss_pct": 0.0,
            "max_drawdown_pct": 0.0, "total_pnl_pct": 0.0,
        }

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    trade_count = len(trades)
    win_rate = len(wins) / trade_count if trade_count > 0 else 0
    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    total_pnl = sum(pnls)

    # Sharpe (annualized, assuming 4H bars ~ 6 trades/day)
    if len(pnls) >= 2:
        pnl_arr = np.array(pnls)
        mean_ret = np.mean(pnl_arr)
        std_ret = np.std(pnl_arr, ddof=1)
        sharpe = (mean_ret / std_ret) * np.sqrt(252 * 6) if std_ret > 0 else 0
    else:
        sharpe = 0

    # Max drawdown
    equity = np.cumsum([0] + pnls)
    peak = np.maximum.accumulate(equity)
    drawdown = equity - peak
    max_dd = float(np.min(drawdown))

    # Exit reason breakdown
    exit_reasons = {}
    for t in trades:
        reason = t.get("exit_reason", "UNKNOWN")
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

    return {
        "trade_count": trade_count,
        "win_rate": round(win_rate * 100, 1),
        "profit_factor": round(profit_factor, 2),
        "sharpe": round(sharpe, 2),
        "avg_win_pct": round(avg_win, 2),
        "avg_loss_pct": round(avg_loss, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "total_pnl_pct": round(total_pnl, 2),
        "exit_reasons": exit_reasons,
    }


def run_backtest(symbols: list = None) -> dict:
    """Run full backtest across all symbols and strategies.

    Fetches 90 days of 4H data, runs all 3 strategies, reports metrics.
    """
    if symbols is None:
        symbols = BACKTEST_SYMBOLS

    strategies_config = {
        "ema21_retracement": {
            "ema_period": 21, "min_distance_atr": 1.0,
            "touch_threshold_atr": 0.3, "trend_bars": 5,
            "require_stack": False,
        },
        "ema50_retracement": {
            "ema_period": 50, "min_distance_atr": 1.5,
            "touch_threshold_atr": 0.4, "trend_bars": 8,
            "require_stack": False,
        },
        "ema_stack_retracement": {
            "ema_period": 21, "min_distance_atr": 1.0,
            "touch_threshold_atr": 0.3, "trend_bars": 5,
            "require_stack": True,
        },
    }

    results = {
        "backtest_date": _now_iso(),
        "data_interval": "4h",
        "data_bars_requested": 540,
        "symbols_tested": [],
        "symbols_failed": [],
        "strategies": {},
        "comparison": {},
    }

    # Fetch data for all symbols
    all_data = {}
    for sym in symbols:
        print(f"  Fetching 4H data for {sym}...")
        ohlcv = _fetch_4h_data(sym, limit=540)
        if ohlcv is not None:
            all_data[sym] = ohlcv
            results["symbols_tested"].append(sym)
        else:
            results["symbols_failed"].append(sym)
        time.sleep(0.3)  # Rate limit

    print(f"  Data fetched: {len(all_data)}/{len(symbols)} symbols")

    # Run backtest for each strategy
    for strat_name, config in strategies_config.items():
        print(f"\n  Backtesting {strat_name}...")
        all_trades = []
        per_symbol = {}

        for sym, ohlcv in all_data.items():
            trades = _backtest_strategy_on_symbol(
                ohlcv=ohlcv,
                strategy_name=strat_name,
                **config,
            )
            all_trades.extend(trades)
            if trades:
                per_symbol[sym] = _compute_metrics(trades)
                print(f"    {sym}: {len(trades)} trades, "
                      f"WR={per_symbol[sym]['win_rate']}%, "
                      f"PF={per_symbol[sym]['profit_factor']}")

        overall = _compute_metrics(all_trades)
        results["strategies"][strat_name] = {
            "overall": overall,
            "per_symbol": per_symbol,
            "config": config,
        }
        print(f"  {strat_name} OVERALL: {overall['trade_count']} trades, "
              f"WR={overall['win_rate']}%, PF={overall['profit_factor']}, "
              f"Sharpe={overall['sharpe']}")

    # A/B Comparison
    strat_names = list(results["strategies"].keys())
    for sn in strat_names:
        s = results["strategies"][sn]["overall"]
        results["comparison"][sn] = {
            "trades": s["trade_count"],
            "win_rate": s["win_rate"],
            "profit_factor": s["profit_factor"],
            "sharpe": s["sharpe"],
            "avg_win": s["avg_win_pct"],
            "avg_loss": s["avg_loss_pct"],
            "max_dd": s["max_drawdown_pct"],
            "total_pnl": s["total_pnl_pct"],
        }

    # Benchmark comparison
    results["benchmarks"] = {
        "gamma_portfolio": {"win_rate": 68.3, "note": "Best existing portfolio"},
        "mean_reversion_D": {"win_rate": 60.3, "note": "Our backtest leader"},
    }

    return results


# ===========================================================================
# CLI entry point
# ===========================================================================

def main():
    """Run backtest and save results."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("=" * 60)
    print("EMA Retracement Mean Reversion — Backtest")
    print("=" * 60)
    print(f"Symbols: {len(BACKTEST_SYMBOLS)}")
    print(f"Interval: 4H | Bars: 540 (~90 days)")
    print(f"Strategies: ema21_retracement, ema50_retracement, ema_stack_retracement")
    print()

    results = run_backtest()

    # Save results
    out_path = DATA_DIR / "ema_retracement_backtest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Sanitize NaN/Inf for JSON
    def sanitize(obj):
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [sanitize(v) for v in obj]
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        if hasattr(obj, "item"):
            return sanitize(obj.item())
        return obj

    with open(out_path, "w") as f:
        json.dump(sanitize(results), f, indent=2)

    print(f"\nResults saved to {out_path}")

    # Print comparison table
    print("\n" + "=" * 60)
    print("A/B COMPARISON")
    print("=" * 60)
    print(f"{'Strategy':<25} {'Trades':>7} {'WR%':>7} {'PF':>7} {'Sharpe':>7} {'PnL%':>8}")
    print("-" * 60)
    for name, m in results["comparison"].items():
        print(f"{name:<25} {m['trades']:>7} {m['win_rate']:>7.1f} "
              f"{m['profit_factor']:>7.2f} {m['sharpe']:>7.2f} {m['total_pnl']:>8.2f}")
    print("-" * 60)
    print(f"{'GAMMA (benchmark)':<25} {'':>7} {'68.3':>7} {'':>7} {'':>7} {'':>8}")
    print(f"{'MeanRev-D (benchmark)':<25} {'':>7} {'60.3':>7} {'':>7} {'':>7} {'':>8}")

    return results


if __name__ == "__main__":
    main()
