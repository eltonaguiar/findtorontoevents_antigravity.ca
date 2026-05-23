"""
ALPHA_ENGINE - Candlestick Pattern Strategies
==============================================
3 high-probability candlestick pattern strategies from Kimi's audit review.
Each leverages institutional behaviour (stop hunts, panic traps, accumulation)
rather than naive pattern recognition.

Strategies:
  1. bearish_engulfing_bullish    - Bearish engulfing at KEY SUPPORT = bullish
                                    reversal trap (75.76% WR, Kimi audit)
  2. three_soldiers_oversold      - Three White Soldiers with RSI < 35 = ultra-
                                    high probability long (83.33% WR)
  3. liquidity_sweep_reversal     - Price sweeps beyond swing level then closes
                                    back inside = failed breakout (70%+ WR)

References:
  - Bulkowski (2008): "Encyclopedia of Candlestick Charts"
  - Nison (1991): "Japanese Candlestick Charting Techniques"
  - Kimi audit review: institutional price action statistics
  - Market microstructure: stop-hunt mechanics at key S/R levels
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from config import CRYPTO_SYMBOLS
from indicators import rsi, atr, sma, volume_ratio


# -- Helpers ----------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_category(symbol: str) -> str:
    info = CRYPTO_SYMBOLS.get(symbol, {})
    return info.get("cat", "crypto")


def _smart_round(value: float) -> float:
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


def _rr(entry: float, tp: float, sl: float) -> float:
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    return round(reward / risk, 2) if risk > 0 else 0.0


MIN_BARS = 30


# =====================================================================
# STRATEGY: Bearish Engulfing at Support = Bullish (75.76% WR)
# =====================================================================
# Counter-intuitive: a bearish engulfing candle at KEY SUPPORT is a
# LONG signal. Market makers create panic selling at support to trap
# shorts, then reverse the price upward. The engulfing candle at
# support with high volume and oversold RSI signals institutional
# accumulation, not distribution.
#
# Conditions:
#   1. Bearish engulfing pattern (current body fully covers previous)
#   2. Price within 1% of 20-period low (at support)
#   3. RSI(14) < 35 (oversold confirmation)
#   4. Volume > 1.5x 20-period average (institutional activity)
#
# Signal: BUY | TP: +2x ATR(14) | SL: engulfing low - 0.5x ATR
# =====================================================================

def bearish_engulfing_bullish(data: dict[str, pd.DataFrame],
                              context: Optional[dict] = None) -> list[dict]:
    """Bearish engulfing at support = bullish reversal (75.76% WR)."""
    signals: list[dict] = []

    for symbol, df in data.items():
        try:
            if df is None or len(df) < MIN_BARS:
                continue

            o = df["Open"]
            h = df["High"]
            lo = df["Low"]
            c = df["Close"]
            v = df["Volume"]

            # Current and previous bar
            curr_open = float(o.iloc[-1])
            curr_close = float(c.iloc[-1])
            curr_low = float(lo.iloc[-1])
            prev_open = float(o.iloc[-2])
            prev_close = float(c.iloc[-2])

            # 1. Bearish engulfing: current candle is bearish and body
            #    fully covers previous candle's body
            curr_bearish = curr_close < curr_open
            body_engulfs = (curr_open >= prev_close and curr_close <= prev_open)

            if not (curr_bearish and body_engulfs):
                continue

            # 2. At support: price within 1% of 20-period low
            period_low = float(lo.rolling(20).min().iloc[-1])
            if period_low <= 0:
                continue
            distance_to_support = (curr_close - period_low) / period_low
            if distance_to_support > 0.01:
                continue

            # 3. RSI(14) < 35
            rsi_vals = rsi(c, 14)
            curr_rsi = float(rsi_vals.iloc[-1])
            if np.isnan(curr_rsi) or curr_rsi >= 35:
                continue

            # 4. Volume > 1.5x 20-period average
            vr = volume_ratio(v, 20)
            curr_vr = float(vr.iloc[-1])
            if np.isnan(curr_vr) or curr_vr < 1.5:
                continue

            # Compute TP / SL
            atr_vals = atr(h, lo, c, 14)
            curr_atr = float(atr_vals.iloc[-1])
            if np.isnan(curr_atr) or curr_atr <= 0:
                continue

            entry = float(c.iloc[-1])
            tp = entry + 2.0 * curr_atr
            sl = curr_low - 0.5 * curr_atr

            confidence = min(0.85, 0.60 + (35 - curr_rsi) * 0.005
                             + (curr_vr - 1.5) * 0.03)

            signals.append({
                "strategy": "bearish_engulfing_bullish",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "direction": "long",
                "entry_price": _smart_round(entry),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(confidence, 3),
                "risk_reward": _rr(entry, tp, sl),
                "reason": (
                    f"Bearish engulfing at support: price within "
                    f"{distance_to_support*100:.1f}% of 20-bar low, "
                    f"RSI={curr_rsi:.1f}, vol={curr_vr:.1f}x avg. "
                    f"Institutional stop-hunt trap pattern (75.76% WR)."
                ),
                "timestamp": _now_iso(),
                "extra": {
                    "pattern": "bearish_engulfing_at_support",
                    "rsi": round(curr_rsi, 2),
                    "volume_ratio": round(curr_vr, 2),
                    "atr": round(curr_atr, 6),
                    "distance_to_support_pct": round(distance_to_support * 100, 2),
                },
            })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY: Three White Soldiers + Oversold RSI (83.33% WR)
# =====================================================================
# Three consecutive bullish candles with strong bodies (>60% of range),
# each closing higher, each opening within the previous body, with
# increasing volume -- all starting from RSI < 35.
#
# This is one of the highest win-rate patterns when filtered by
# oversold RSI, as it captures the transition from institutional
# accumulation to markup phase.
#
# Conditions:
#   1. Three consecutive bullish candles, each closing higher
#   2. Each opens within previous candle's body
#   3. Each body >= 60% of candle range (strong bodies)
#   4. RSI(14) < 35 at first soldier
#   5. Volume increasing across all three candles
#
# Signal: BUY | TP: +3x ATR(14) | SL: below first soldier's low
# =====================================================================

def three_soldiers_oversold(data: dict[str, pd.DataFrame],
                            context: Optional[dict] = None) -> list[dict]:
    """Three White Soldiers + RSI<35 = ultra-high probability long (83.33% WR)."""
    signals: list[dict] = []

    for symbol, df in data.items():
        try:
            if df is None or len(df) < MIN_BARS:
                continue

            o = df["Open"]
            h = df["High"]
            lo = df["Low"]
            c = df["Close"]
            v = df["Volume"]

            # Need at least 3 candles to check pattern on the last 3
            # Indices: -3 (first soldier), -2 (second), -1 (third / current)
            candles = []
            for i in [-3, -2, -1]:
                candles.append({
                    "open": float(o.iloc[i]),
                    "high": float(h.iloc[i]),
                    "low": float(lo.iloc[i]),
                    "close": float(c.iloc[i]),
                    "volume": float(v.iloc[i]),
                })

            # 1. All three must be bullish and each closing higher
            all_bullish = all(cn["close"] > cn["open"] for cn in candles)
            closes_rising = (candles[1]["close"] > candles[0]["close"]
                             and candles[2]["close"] > candles[1]["close"])
            if not (all_bullish and closes_rising):
                continue

            # 2. Each candle opens within previous candle's body
            # (second opens within first's body, third within second's)
            opens_inside = True
            for j in [1, 2]:
                prev_body_lo = min(candles[j-1]["open"], candles[j-1]["close"])
                prev_body_hi = max(candles[j-1]["open"], candles[j-1]["close"])
                if not (prev_body_lo <= candles[j]["open"] <= prev_body_hi):
                    opens_inside = False
                    break
            if not opens_inside:
                continue

            # 3. Each body >= 60% of total range (strong bodies, small wicks)
            strong_bodies = True
            for cn in candles:
                total_range = cn["high"] - cn["low"]
                if total_range <= 0:
                    strong_bodies = False
                    break
                body_size = abs(cn["close"] - cn["open"])
                if body_size / total_range < 0.60:
                    strong_bodies = False
                    break
            if not strong_bodies:
                continue

            # 4. RSI(14) < 35 at the first soldier
            rsi_vals = rsi(c, 14)
            rsi_first = float(rsi_vals.iloc[-3])
            if np.isnan(rsi_first) or rsi_first >= 35:
                continue

            # 5. Volume increasing across the three candles
            vol_increasing = (candles[1]["volume"] > candles[0]["volume"]
                              and candles[2]["volume"] > candles[1]["volume"])
            if not vol_increasing:
                continue

            # Compute TP / SL
            atr_vals = atr(h, lo, c, 14)
            curr_atr = float(atr_vals.iloc[-1])
            if np.isnan(curr_atr) or curr_atr <= 0:
                continue

            entry = float(c.iloc[-1])
            tp = entry + 3.0 * curr_atr  # high WR justifies wider target
            sl = candles[0]["low"]        # below first soldier's low

            # Volume ratio of third candle
            vr = volume_ratio(v, 20)
            curr_vr = float(vr.iloc[-1])

            confidence = min(0.90, 0.70 + (35 - rsi_first) * 0.005
                             + (curr_vr - 1.0) * 0.02)

            signals.append({
                "strategy": "three_soldiers_oversold",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "direction": "long",
                "entry_price": _smart_round(entry),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(confidence, 3),
                "risk_reward": _rr(entry, tp, sl),
                "reason": (
                    f"Three White Soldiers from oversold: RSI={rsi_first:.1f} "
                    f"at first soldier, all 3 candles bullish with strong "
                    f"bodies and increasing volume (83.33% WR)."
                ),
                "timestamp": _now_iso(),
                "extra": {
                    "pattern": "three_white_soldiers_oversold",
                    "rsi": round(rsi_first, 2),
                    "volume_ratio": round(curr_vr, 2) if not np.isnan(curr_vr) else 0.0,
                    "atr": round(curr_atr, 6),
                    "body_ratios": [
                        round(abs(cn["close"] - cn["open"]) /
                              max(cn["high"] - cn["low"], 1e-10), 2)
                        for cn in candles
                    ],
                },
            })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY: Liquidity Sweep Reversal (70%+ WR)
# =====================================================================
# Price sweeps beyond a swing high/low (stop-hunt) then reverses back
# inside. This captures failed breakouts engineered by market makers
# to grab liquidity (stop losses) before reversing.
#
# Conditions:
#   1. Identify swing high/low using 10-bar lookback
#   2. Price wick extends beyond swing level by >= 0.3%
#   3. Price CLOSES back inside the swing level (failed breakout)
#   4. Volume spike on sweep candle (>1.3x average)
#
# At swing low: BUY | At swing high: SELL
# TP: 2x ATR | SL: beyond sweep wick + 0.2x ATR buffer
# =====================================================================

def liquidity_sweep_reversal(data: dict[str, pd.DataFrame],
                             context: Optional[dict] = None) -> list[dict]:
    """Liquidity sweep beyond swing level then reversal (70%+ WR)."""
    signals: list[dict] = []

    for symbol, df in data.items():
        try:
            if df is None or len(df) < MIN_BARS:
                continue

            o = df["Open"]
            h = df["High"]
            lo = df["Low"]
            c = df["Close"]
            v = df["Volume"]

            lookback = 10

            curr_high = float(h.iloc[-1])
            curr_low = float(lo.iloc[-1])
            curr_close = float(c.iloc[-1])

            atr_vals = atr(h, lo, c, 14)
            curr_atr = float(atr_vals.iloc[-1])
            if np.isnan(curr_atr) or curr_atr <= 0:
                continue

            vr = volume_ratio(v, 20)
            curr_vr = float(vr.iloc[-1])
            if np.isnan(curr_vr) or curr_vr < 1.3:
                continue

            # Find swing low: minimum of lows in the lookback window
            # (excluding the current bar)
            swing_low = float(lo.iloc[-(lookback + 1):-1].min())
            # Find swing high: maximum of highs in the lookback window
            swing_high = float(h.iloc[-(lookback + 1):-1].max())

            # Check for sweep of swing LOW (bullish reversal)
            if swing_low > 0:
                sweep_below = (swing_low - curr_low) / swing_low
                closes_above = curr_close > swing_low

                if sweep_below >= 0.003 and closes_above:
                    entry = curr_close
                    tp = entry + 2.0 * curr_atr
                    sl = curr_low - 0.2 * curr_atr

                    rsi_vals = rsi(c, 14)
                    curr_rsi = float(rsi_vals.iloc[-1])

                    confidence = min(0.80, 0.55 + sweep_below * 10
                                     + (curr_vr - 1.3) * 0.03)

                    signals.append({
                        "strategy": "liquidity_sweep_reversal",
                        "symbol": symbol,
                        "category": _get_category(symbol),
                        "signal_type": "BUY",
                        "direction": "long",
                        "entry_price": _smart_round(entry),
                        "take_profit": _smart_round(tp),
                        "stop_loss": _smart_round(sl),
                        "confidence": round(confidence, 3),
                        "risk_reward": _rr(entry, tp, sl),
                        "reason": (
                            f"Liquidity sweep below swing low: wick "
                            f"extended {sweep_below*100:.1f}% below "
                            f"${swing_low:.2f}, closed back above. "
                            f"Vol={curr_vr:.1f}x avg. Stop-hunt "
                            f"reversal (70%+ WR)."
                        ),
                        "timestamp": _now_iso(),
                        "extra": {
                            "pattern": "liquidity_sweep_low",
                            "rsi": round(curr_rsi, 2) if not np.isnan(curr_rsi) else 0.0,
                            "volume_ratio": round(curr_vr, 2),
                            "sweep_pct": round(sweep_below * 100, 2),
                            "swing_level": _smart_round(swing_low),
                        },
                    })

            # Check for sweep of swing HIGH (bearish reversal)
            if swing_high > 0:
                sweep_above = (curr_high - swing_high) / swing_high
                closes_below = curr_close < swing_high

                if sweep_above >= 0.003 and closes_below:
                    entry = curr_close
                    tp = entry - 2.0 * curr_atr
                    sl = curr_high + 0.2 * curr_atr

                    rsi_vals = rsi(c, 14)
                    curr_rsi = float(rsi_vals.iloc[-1])

                    confidence = min(0.80, 0.55 + sweep_above * 10
                                     + (curr_vr - 1.3) * 0.03)

                    signals.append({
                        "strategy": "liquidity_sweep_reversal",
                        "symbol": symbol,
                        "category": _get_category(symbol),
                        "signal_type": "SELL",
                        "direction": "short",
                        "entry_price": _smart_round(entry),
                        "take_profit": _smart_round(tp),
                        "stop_loss": _smart_round(sl),
                        "confidence": round(confidence, 3),
                        "risk_reward": _rr(entry, tp, sl),
                        "reason": (
                            f"Liquidity sweep above swing high: wick "
                            f"extended {sweep_above*100:.1f}% above "
                            f"${swing_high:.2f}, closed back below. "
                            f"Vol={curr_vr:.1f}x avg. Stop-hunt "
                            f"reversal (70%+ WR)."
                        ),
                        "timestamp": _now_iso(),
                        "extra": {
                            "pattern": "liquidity_sweep_high",
                            "rsi": round(curr_rsi, 2) if not np.isnan(curr_rsi) else 0.0,
                            "volume_ratio": round(curr_vr, 2),
                            "sweep_pct": round(sweep_above * 100, 2),
                            "swing_level": _smart_round(swing_high),
                        },
                    })

        except Exception:
            continue

    return signals


# -- Strategy registry -----------------------------------------------------

CANDLESTICK_STRATEGIES: dict[str, callable] = {
    "bearish_engulfing_bullish": bearish_engulfing_bullish,
    "three_soldiers_oversold": three_soldiers_oversold,
    "liquidity_sweep_reversal": liquidity_sweep_reversal,
}
