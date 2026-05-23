"""
ALPHA_ENGINE -- Session-Based Breakout Strategies for Forex
============================================================
Improved session breakout and VWAP mean-reversion strategies
with ATR filtering and false breakout detection.

Replaces/improves upon community_london_breakout_v2_forex which
shows weak performance (-0.65% NZDUSD, -0.29% GBPUSD).

Key improvements over v2:
  1. ATR filter rejects noise breakouts (range must exceed 0.7x ATR)
  2. Volume confirmation (1.2x 10-period average)
  3. Anti-chase filter (skip if previous day was also a breakout)
  4. Tighter SL via range-based placement instead of fixed ATR multiple

References:
  - Lui & Mole (1998), "Role of Technical Analysis in FX Market"
  - Menkhoff & Taylor (2007), "Obstinate passion of FX professionals"
  - Chaboud et al. (2014), "Rise of the machines: HFT in FX"
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Internal indicator calculations (self-contained, no external imports)
# ---------------------------------------------------------------------------

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series,
         period: int = 14) -> pd.Series:
    """Average True Range -- Wilder smoothing."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def _volume_ratio(volume: pd.Series, period: int = 10) -> pd.Series:
    """Current volume relative to rolling average."""
    avg = volume.rolling(window=period, min_periods=period).mean()
    return volume / avg.replace(0, np.nan)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# STRATEGY 1: Asian-London Session Breakout (ATR-filtered)
# ---------------------------------------------------------------------------
# Approximation for daily bars: Asian session range is estimated as
# 60% of the previous day's total range, centered on the previous close.
# This captures the typical compression during Asian hours before the
# London open drives directional moves.
#
# Three-filter system eliminates the false breakouts that plagued v2:
#   F1: ATR expansion confirms genuine volatility
#   F2: Volume surge confirms institutional participation
#   F3: Anti-chase rejects consecutive breakout days
# ---------------------------------------------------------------------------

def asian_london_breakout_filtered(symbol: str, df: pd.DataFrame,
                                   market_data: Optional[dict] = None) -> list[dict]:
    """ATR-filtered session breakout -- improvement over basic London breakout.

    Uses previous day's range as Asian session proxy, applies three filters
    to reject noise breakouts, and uses range-based SL for tighter risk.

    Returns list of pick dicts (0 or 1 element).
    """
    try:
        if df is None or len(df) < 30:
            return []

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df.get("Volume")

        # --- Compute indicators ---
        atr_series = _atr(high, low, close, 14)
        atr_val = float(atr_series.iloc[-1])
        if np.isnan(atr_val) or atr_val <= 0:
            return []

        # --- Asian session range proxy (previous bar) ---
        prev_close = float(close.iloc[-2])
        prev_range = float(high.iloc[-2] - low.iloc[-2])
        session_range = prev_range * 0.6

        if session_range <= 0:
            return []

        upper_boundary = prev_close + session_range / 2.0
        lower_boundary = prev_close - session_range / 2.0

        # --- Current bar values ---
        cur_close = float(close.iloc[-1])
        cur_range = float(high.iloc[-1] - low.iloc[-1])

        # --- FILTER 1: ATR expansion (real volatility, not noise) ---
        if cur_range < 0.7 * atr_val:
            return []

        # --- FILTER 2: Volume confirmation ---
        vol_ratio = 1.0
        if volume is not None and len(volume) >= 10:
            vr_series = _volume_ratio(volume, 10)
            vr_val = float(vr_series.iloc[-1])
            if not np.isnan(vr_val):
                vol_ratio = vr_val
        if vol_ratio < 1.2:
            return []

        # --- FILTER 3: Anti-chase (previous day must not be a breakout) ---
        if len(df) >= 4:
            prev2_close = float(close.iloc[-3])
            prev2_range = float(high.iloc[-3] - low.iloc[-3])
            prev2_session = prev2_range * 0.6
            prev2_upper = prev2_close + prev2_session / 2.0
            prev2_lower = prev2_close - prev2_session / 2.0
            if prev_close > prev2_upper or prev_close < prev2_lower:
                return []

        # --- Determine direction ---
        direction = None
        if cur_close > upper_boundary:
            direction = "long"
        elif cur_close < lower_boundary:
            direction = "short"

        if direction is None:
            return []

        # --- Risk management ---
        if direction == "long":
            entry = cur_close
            sl = lower_boundary - 0.3 * atr_val
            tp = entry + 1.5 * session_range

            # Maximum risk check: SL distance > 2x ATR = range too wide
            if (entry - sl) > 2.0 * atr_val:
                return []
        else:
            entry = cur_close
            sl = upper_boundary + 0.3 * atr_val
            tp = entry - 1.5 * session_range

            if (sl - entry) > 2.0 * atr_val:
                return []

        # --- Risk/reward check ---
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = reward / risk if risk > 0 else 0
        if rr < 1.0:
            return []

        # --- Confidence: base 0.55, boost for strong volume and clean range ---
        confidence = 0.55
        if vol_ratio >= 1.5:
            confidence += 0.05
        if cur_range > 1.0 * atr_val:
            confidence += 0.05
        confidence = min(confidence, 0.75)

        rsi_val = float(_rsi(close, 14).iloc[-1])

        return [{
            "symbol": symbol,
            "direction": direction,
            "signal_type": "BUY" if direction == "long" else "SELL",
            "confidence": round(confidence, 2),
            "entry_price": round(entry, 5),
            "take_profit": round(tp, 5),
            "stop_loss": round(sl, 5),
            "risk_reward": round(rr, 2),
            "reason": (
                f"Session breakout {'above' if direction == 'long' else 'below'} "
                f"{'upper' if direction == 'long' else 'lower'} boundary "
                f"{upper_boundary if direction == 'long' else lower_boundary:.5f}, "
                f"ATR={atr_val:.5f}, vol={vol_ratio:.1f}x, "
                f"range={session_range:.5f}"
            ),
            "strategy": "asian_london_breakout_filtered",
            "category": "forex",
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "timestamp": _now_iso(),
            "extra": {
                "session_range": round(session_range, 6),
                "atr": round(atr_val, 6),
                "volume_ratio": round(vol_ratio, 2),
                "upper_boundary": round(upper_boundary, 5),
                "lower_boundary": round(lower_boundary, 5),
                "prev_range": round(prev_range, 6),
            },
        }]

    except Exception:
        return []


# ---------------------------------------------------------------------------
# STRATEGY 2: VWAP Session Mean Reversion
# ---------------------------------------------------------------------------
# Intraday VWAP bounce adapted for daily bars using a 5-period rolling VWAP
# proxy. Institutional traders anchor to VWAP; prices that deviate tend to
# revert. Combined with trend confirmation (SMA slope + 20-bar momentum)
# to only enter in the trend direction.
#
# Reference:
#   - Berkowitz et al. (1988), "VWAP strategies in practice"
#   - Almgren & Chriss (2001), "Optimal execution of portfolio transactions"
# ---------------------------------------------------------------------------

def vwap_session_mean_reversion(symbol: str, df: pd.DataFrame,
                                market_data: Optional[dict] = None) -> list[dict]:
    """VWAP bounce in trending market -- institutional mean reversion.

    Calculates a rolling 5-bar VWAP proxy. Signals when price pulls back
    to within 0.3% of VWAP in the direction of the prevailing trend,
    confirmed by SMA slope, RSI neutrality, and 20-bar momentum.

    Returns list of pick dicts (0 or 1 element).
    """
    try:
        if df is None or len(df) < 30:
            return []

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        opn = df["Open"]
        volume = df.get("Volume")

        if volume is None or volume.iloc[-1] == 0:
            return []

        # --- Rolling VWAP proxy (5-bar) ---
        typical_price = (high + low + close) / 3.0
        tp_vol = typical_price * volume
        vwap = tp_vol.rolling(5, min_periods=5).sum() / volume.rolling(5, min_periods=5).sum()

        cur_vwap = float(vwap.iloc[-1])
        if np.isnan(cur_vwap) or cur_vwap <= 0:
            return []

        cur_close = float(close.iloc[-1])
        cur_open = float(opn.iloc[-1])

        # --- Price deviation from VWAP ---
        deviation = (cur_close - cur_vwap) / cur_vwap
        if abs(deviation) > 0.003:  # Must be within 0.3% of VWAP
            return []

        # --- Trend direction: 5-bar SMA slope ---
        sma_5 = close.rolling(5, min_periods=5).mean()
        sma_slope = float(sma_5.iloc[-1] - sma_5.iloc[-2])

        # --- 20-bar momentum confirmation ---
        if len(close) < 21:
            return []
        momentum_20 = float(close.iloc[-1] - close.iloc[-21])

        # --- RSI neutrality check (40-60 range) ---
        rsi_series = _rsi(close, 14)
        rsi_val = float(rsi_series.iloc[-1])
        if np.isnan(rsi_val):
            return []
        if rsi_val < 40 or rsi_val > 60:
            return []

        # --- ATR for TP/SL ---
        atr_series = _atr(high, low, close, 14)
        atr_val = float(atr_series.iloc[-1])
        if np.isnan(atr_val) or atr_val <= 0:
            return []

        # --- Determine direction ---
        direction = None
        is_bullish_bar = cur_close > cur_open
        is_bearish_bar = cur_close < cur_open

        if sma_slope > 0 and momentum_20 > 0 and is_bullish_bar:
            direction = "long"
        elif sma_slope < 0 and momentum_20 < 0 and is_bearish_bar:
            direction = "short"

        if direction is None:
            return []

        # --- Risk management: ATR-based TP/SL ---
        entry = cur_close
        if direction == "long":
            sl = entry - 1.5 * atr_val
            tp = entry + 2.0 * atr_val
        else:
            sl = entry + 1.5 * atr_val
            tp = entry - 2.0 * atr_val

        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = reward / risk if risk > 0 else 0
        if rr < 1.0:
            return []

        # --- Confidence: base 0.55, boost for tight deviation and strong RSI ---
        confidence = 0.55
        if abs(deviation) < 0.001:
            confidence += 0.05  # Very close to VWAP
        if 45 <= rsi_val <= 55:
            confidence += 0.05  # RSI perfectly neutral
        confidence = min(confidence, 0.70)

        vol_ratio = 1.0
        if volume is not None and len(volume) >= 10:
            vr_series = _volume_ratio(volume, 10)
            vr_val = float(vr_series.iloc[-1])
            if not np.isnan(vr_val):
                vol_ratio = vr_val

        return [{
            "symbol": symbol,
            "direction": direction,
            "signal_type": "BUY" if direction == "long" else "SELL",
            "confidence": round(confidence, 2),
            "entry_price": round(entry, 5),
            "take_profit": round(tp, 5),
            "stop_loss": round(sl, 5),
            "risk_reward": round(rr, 2),
            "reason": (
                f"VWAP mean reversion: price at {deviation:+.3%} from VWAP "
                f"{cur_vwap:.5f}, {'uptrend' if direction == 'long' else 'downtrend'} "
                f"confirmed (SMA slope={sma_slope:.6f}, 20d mom={momentum_20:.5f}), "
                f"RSI={rsi_val:.1f}"
            ),
            "strategy": "vwap_session_mean_reversion",
            "category": "forex",
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "timestamp": _now_iso(),
            "extra": {
                "vwap": round(cur_vwap, 5),
                "deviation_pct": round(deviation * 100, 4),
                "sma_slope": round(sma_slope, 6),
                "momentum_20": round(momentum_20, 5),
                "atr": round(atr_val, 6),
                "volume_ratio": round(vol_ratio, 2),
            },
        }]

    except Exception:
        return []


# ---------------------------------------------------------------------------
# Exported strategy registry
# ---------------------------------------------------------------------------

SESSION_STRATEGIES = {
    "asian_london_breakout_filtered": asian_london_breakout_filtered,
    "vwap_session_mean_reversion": vwap_session_mean_reversion,
}
