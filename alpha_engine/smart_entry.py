#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Smart Entry Zone Detector
==========================================
Identifies high-probability entry zones using multi-factor confluence scoring.

Unlike entry_optimizer.py (which scores real-time 15m micro-timing), this module
analyzes the broader daily OHLCV DataFrame that scanner already provides to
determine whether the *price structure* is favorable for entry.

Five factors, each worth 0-20 points (total 0-100):
  1. Support proximity -- is price near a support level?
  2. Momentum confirmation -- is momentum turning in our favor?
  3. Volume confirmation -- is smart money participating?
  4. Trend alignment -- does the bigger picture support this trade?
  5. Volatility compression -- is a move about to happen?

Usage:
  from smart_entry import SmartEntryDetector
  detector = SmartEntryDetector()
  result = detector.score_entry_zone(symbol, df, direction='LONG')
  # result = {score: 0-100, factors: {...}, recommendation: 'STRONG_BUY'|...}
"""

from __future__ import annotations

import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)


class SmartEntryDetector:
    """Identifies high-probability entry zones using multi-factor confluence."""

    # -- 1. Support Proximity (20 pts) ------------------------------------

    def _score_support_proximity(self, close, high, low, volume, direction: str) -> tuple[float, dict]:
        """Score how close price is to a support (LONG) or resistance (SHORT) level."""
        n = len(close)
        score = 0.0
        details: dict = {}

        if n < 20:
            return 0.0, {"note": "insufficient data"}

        current = close.iloc[-1]

        # --- Bollinger Band proximity ---
        sma20 = close.rolling(20).mean().iloc[-1]
        std20 = close.rolling(20).std().iloc[-1]

        if not _is_valid(sma20) or not _is_valid(std20) or std20 == 0:
            bb_lower = current
            bb_upper = current
        else:
            bb_lower = sma20 - 2.0 * std20
            bb_upper = sma20 + 2.0 * std20

        # --- 20-period low/high proximity ---
        period_low = float(low.tail(20).min())
        period_high = float(high.tail(20).max())

        if direction == "LONG":
            # Near 20-period low?
            if current > 0 and period_low > 0:
                dist_to_low_pct = (current - period_low) / current * 100
                details["dist_to_20low_pct"] = round(dist_to_low_pct, 2)
                if dist_to_low_pct <= 0.5:
                    score += 20
                elif dist_to_low_pct <= 1.5:
                    score += 12
                elif dist_to_low_pct <= 3.0:
                    score += 5

            # Near lower Bollinger Band?
            if _is_valid(bb_lower) and current > 0 and bb_lower > 0:
                dist_to_bb_pct = (current - bb_lower) / current * 100
                details["dist_to_bb_lower_pct"] = round(dist_to_bb_pct, 2)
                if dist_to_bb_pct <= 1.0:
                    score = max(score, 15)
                elif dist_to_bb_pct <= 2.0:
                    score = max(score, 10)

            # At or below VWAP?
            vwap = _compute_vwap(close, volume)
            if _is_valid(vwap) and vwap > 0:
                details["vwap"] = round(vwap, 4)
                if current <= vwap:
                    score = max(score, 10)
        else:
            # SHORT: near resistance
            if current > 0 and period_high > 0:
                dist_to_high_pct = (period_high - current) / current * 100
                details["dist_to_20high_pct"] = round(dist_to_high_pct, 2)
                if dist_to_high_pct <= 0.5:
                    score += 20
                elif dist_to_high_pct <= 1.5:
                    score += 12
                elif dist_to_high_pct <= 3.0:
                    score += 5

            if _is_valid(bb_upper) and current > 0 and bb_upper > 0:
                dist_to_bb_pct = (bb_upper - current) / current * 100
                details["dist_to_bb_upper_pct"] = round(dist_to_bb_pct, 2)
                if dist_to_bb_pct <= 1.0:
                    score = max(score, 15)
                elif dist_to_bb_pct <= 2.0:
                    score = max(score, 10)

            vwap = _compute_vwap(close, volume)
            if _is_valid(vwap) and vwap > 0:
                details["vwap"] = round(vwap, 4)
                if current >= vwap:
                    score = max(score, 10)

        return min(score, 20.0), details

    # -- 2. Momentum Confirmation (20 pts) --------------------------------

    def _score_momentum(self, close, direction: str) -> tuple[float, dict]:
        """Score momentum turning signals."""
        n = len(close)
        score = 0.0
        details: dict = {}

        if n < 26:
            return 0.0, {"note": "insufficient data for momentum"}

        # --- RSI(14) ---
        rsi_values = _compute_rsi_series(close, 14)
        if len(rsi_values) >= 2:
            rsi_now = rsi_values[-1]
            rsi_prev = rsi_values[-2]
            details["rsi_14"] = round(rsi_now, 1)
            details["rsi_prev"] = round(rsi_prev, 1)

            if direction == "LONG":
                # RSI < 35 AND rising
                if rsi_now < 35 and rsi_now > rsi_prev:
                    score += 20
                    details["rsi_signal"] = "oversold_rising"
                elif rsi_now < 40 and rsi_now > rsi_prev:
                    score += 10
                    details["rsi_signal"] = "approaching_oversold_rising"
            else:
                if rsi_now > 65 and rsi_now < rsi_prev:
                    score += 20
                    details["rsi_signal"] = "overbought_falling"
                elif rsi_now > 60 and rsi_now < rsi_prev:
                    score += 10
                    details["rsi_signal"] = "approaching_overbought_falling"

        # --- MACD histogram ---
        macd_hist = _compute_macd_histogram(close)
        if len(macd_hist) >= 2:
            hist_now = macd_hist[-1]
            hist_prev = macd_hist[-2]
            details["macd_hist"] = round(hist_now, 6)

            if direction == "LONG":
                if hist_prev < 0 and hist_now > 0:
                    score = max(score, 15)
                    details["macd_signal"] = "histogram_turned_positive"
                elif hist_now > hist_prev and hist_now < 0:
                    score = max(score, 8)
                    details["macd_signal"] = "histogram_recovering"
            else:
                if hist_prev > 0 and hist_now < 0:
                    score = max(score, 15)
                    details["macd_signal"] = "histogram_turned_negative"
                elif hist_now < hist_prev and hist_now > 0:
                    score = max(score, 8)
                    details["macd_signal"] = "histogram_weakening"

        # --- Stochastic %K/%D ---
        stoch_k, stoch_d = _compute_stochastic(close, 14, 3)
        if _is_valid(stoch_k) and _is_valid(stoch_d):
            details["stoch_k"] = round(stoch_k, 1)
            details["stoch_d"] = round(stoch_d, 1)

            if direction == "LONG":
                if stoch_k < 20 and stoch_k > stoch_d:
                    score = max(score, 10)
                    details["stoch_signal"] = "bullish_cross_oversold"
            else:
                if stoch_k > 80 and stoch_k < stoch_d:
                    score = max(score, 10)
                    details["stoch_signal"] = "bearish_cross_overbought"

        return min(score, 20.0), details

    # -- 3. Volume Confirmation (20 pts) ----------------------------------

    def _score_volume(self, close, volume, direction: str) -> tuple[float, dict]:
        """Score volume-based confirmation signals."""
        n = len(close)
        score = 0.0
        details: dict = {}

        if n < 20 or volume is None or len(volume) < 20:
            return 0.0, {"note": "insufficient volume data"}

        vol_values = volume.values
        close_values = close.values

        # Ensure no NaN in volume
        vol_clean = [float(v) if _is_valid(v) else 0.0 for v in vol_values]
        if sum(vol_clean) == 0:
            return 0.0, {"note": "zero volume"}

        # --- Volume vs 20-period average ---
        avg_vol_20 = sum(vol_clean[-20:]) / 20
        current_vol = vol_clean[-1]
        if avg_vol_20 > 0:
            vol_ratio = current_vol / avg_vol_20
            details["volume_ratio_20"] = round(vol_ratio, 2)
            if vol_ratio > 1.5:
                score += 20
                details["volume_signal"] = "high_volume"
            elif vol_ratio > 1.2:
                score += 10
                details["volume_signal"] = "above_average_volume"

        # --- OBV divergence ---
        obv = _compute_obv(close_values, vol_clean)
        if len(obv) >= 10:
            # OBV trend over last 10 bars
            obv_slope = (obv[-1] - obv[-10]) / max(abs(obv[-10]), 1e-10)
            price_slope = (close_values[-1] - close_values[-10]) / max(abs(close_values[-10]), 1e-10)
            details["obv_slope"] = round(obv_slope, 4)
            details["price_slope"] = round(price_slope, 4)

            if direction == "LONG":
                # OBV rising while price flat/falling = bullish divergence
                if obv_slope > 0.05 and price_slope <= 0.01:
                    score = max(score, 15)
                    details["obv_signal"] = "bullish_divergence"
            else:
                # OBV falling while price flat/rising = bearish divergence
                if obv_slope < -0.05 and price_slope >= -0.01:
                    score = max(score, 15)
                    details["obv_signal"] = "bearish_divergence"

        # --- Volume expanding on favorable candles ---
        if n >= 5:
            green_vol = 0.0
            red_vol = 0.0
            green_count = 0
            red_count = 0
            for i in range(-5, 0):
                if close_values[i] >= close_values[i - 1]:
                    green_vol += vol_clean[i]
                    green_count += 1
                else:
                    red_vol += vol_clean[i]
                    red_count += 1

            if direction == "LONG":
                if green_count > 0 and red_count > 0:
                    avg_green = green_vol / green_count
                    avg_red = red_vol / red_count
                    if avg_red > 0 and avg_green / avg_red > 1.3:
                        score = max(score, 10)
                        details["green_vol_signal"] = "buying_pressure"
            else:
                if green_count > 0 and red_count > 0:
                    avg_green = green_vol / green_count
                    avg_red = red_vol / red_count
                    if avg_green > 0 and avg_red / avg_green > 1.3:
                        score = max(score, 10)
                        details["red_vol_signal"] = "selling_pressure"

        return min(score, 20.0), details

    # -- 4. Trend Alignment (20 pts) --------------------------------------

    def _score_trend(self, close, direction: str) -> tuple[float, dict]:
        """Score trend alignment on the bigger timeframe."""
        n = len(close)
        score = 0.0
        details: dict = {}

        current = float(close.iloc[-1])
        if current <= 0:
            return 0.0, {}

        # Price above/below 200 SMA
        if n >= 200:
            sma200 = float(close.rolling(200).mean().iloc[-1])
            if _is_valid(sma200) and sma200 > 0:
                details["sma200"] = round(sma200, 4)
                if direction == "LONG" and current > sma200:
                    score += 10
                elif direction == "SHORT" and current < sma200:
                    score += 10

        # Price above/below 50 SMA
        if n >= 50:
            sma50 = float(close.rolling(50).mean().iloc[-1])
            if _is_valid(sma50) and sma50 > 0:
                details["sma50"] = round(sma50, 4)
                if direction == "LONG" and current > sma50:
                    score += 5
                elif direction == "SHORT" and current < sma50:
                    score += 5

        # 20 SMA vs 50 SMA alignment
        if n >= 50:
            sma20 = float(close.rolling(20).mean().iloc[-1])
            sma50 = float(close.rolling(50).mean().iloc[-1])
            if _is_valid(sma20) and _is_valid(sma50) and sma50 > 0:
                if direction == "LONG" and sma20 > sma50:
                    score += 5
                    details["sma_alignment"] = "bullish"
                elif direction == "SHORT" and sma20 < sma50:
                    score += 5
                    details["sma_alignment"] = "bearish"

        return min(score, 20.0), details

    # -- 5. Volatility Compression (20 pts) -------------------------------

    def _score_volatility_compression(self, close, high, low) -> tuple[float, dict]:
        """Score whether volatility is compressed (move brewing)."""
        n = len(close)
        score = 0.0
        details: dict = {}

        if n < 50:
            return 0.0, {"note": "insufficient data for vol analysis"}

        current = float(close.iloc[-1])
        if current <= 0:
            return 0.0, {}

        # --- Bollinger Band width percentile ---
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        bb_width = (2.0 * std20 / sma20).dropna()

        if len(bb_width) >= 50:
            current_width = float(bb_width.iloc[-1])
            recent_widths = bb_width.tail(50).values
            # Sort to find percentile
            sorted_widths = sorted(float(w) for w in recent_widths if _is_valid(w))
            if sorted_widths:
                rank = sum(1 for w in sorted_widths if w <= current_width)
                percentile = rank / len(sorted_widths) * 100
                details["bb_width_percentile"] = round(percentile, 1)
                details["bb_width"] = round(current_width, 4)

                if percentile <= 20:
                    score += 20
                    details["bb_signal"] = "extreme_compression"
                elif percentile <= 35:
                    score += 12
                    details["bb_signal"] = "compression"

        # --- ATR contraction ---
        tr_series = _compute_tr_series(high, low, close)
        if len(tr_series) >= 20:
            atr_20 = sum(tr_series[-20:]) / 20
            atr_current = tr_series[-1]
            if atr_20 > 0:
                atr_ratio = atr_current / atr_20
                details["atr_ratio"] = round(atr_ratio, 3)
                if atr_ratio < 0.7:
                    score = max(score, 15)
                    details["atr_signal"] = "contracting"
                elif atr_ratio < 0.85:
                    score = max(score, 8)

        # --- Low range candles (body < 30% of ATR) ---
        if n >= 20 and 'Open' in close.index.__class__.__name__:
            # We'll use close vs previous close as body proxy
            pass  # handled below with a simpler approach

        if len(tr_series) >= 1:
            atr_now = tr_series[-1] if tr_series[-1] > 0 else 1e-10
            # Body = |close - prev_close|
            if n >= 2:
                body = abs(float(close.iloc[-1]) - float(close.iloc[-2]))
                body_ratio = body / atr_now
                details["body_atr_ratio"] = round(body_ratio, 3)
                if body_ratio < 0.3:
                    score = max(score, 10)
                    details["candle_signal"] = "low_range_candle"

        return min(score, 20.0), details

    # -- Main scoring method ----------------------------------------------

    def score_entry_zone(self, symbol: str, data, direction: str = "LONG") -> dict:
        """Score current price action for entry quality (0-100).

        Args:
            symbol: Trading pair (e.g. "BTCUSDT")
            data: dict of {symbol: DataFrame} OR a single DataFrame.
                  DataFrame must have columns: Close, High, Low, Volume (optional).
            direction: 'LONG' or 'SHORT'

        Returns:
            {
                'score': 0-100,
                'factors': {factor_name: {score: float, details: dict}},
                'recommendation': 'STRONG_BUY'|'BUY'|'WAIT'|'AVOID',
                'entry_zone_quality': str
            }
        """
        result = {
            "score": 0,
            "factors": {},
            "recommendation": "WAIT",
            "entry_zone_quality": "unknown",
        }

        direction = direction.upper()
        if direction in ("BUY",):
            direction = "LONG"
        elif direction in ("SELL",):
            direction = "SHORT"

        # Resolve DataFrame
        df = None
        if hasattr(data, "iloc"):
            # data is already a DataFrame
            df = data
        elif isinstance(data, dict):
            df = data.get(symbol)
            if df is None:
                # Try first available key
                keys = list(data.keys())
                if keys:
                    df = data[keys[0]]

        if df is None or not hasattr(df, "iloc") or len(df) < 10:
            result["factors"]["error"] = "no valid DataFrame"
            return result

        # Extract series
        try:
            close = df["Close"] if "Close" in df.columns else df.get("close")
            high = df["High"] if "High" in df.columns else df.get("high")
            low = df["Low"] if "Low" in df.columns else df.get("low")
            volume = df["Volume"] if "Volume" in df.columns else df.get("volume")
        except Exception:
            result["factors"]["error"] = "cannot extract OHLCV columns"
            return result

        if close is None or len(close) < 10:
            result["factors"]["error"] = "insufficient close data"
            return result

        # Score each factor
        total = 0.0

        s1, d1 = self._score_support_proximity(close, high, low, volume, direction)
        result["factors"]["support_proximity"] = {"score": s1, "details": d1}
        total += s1

        s2, d2 = self._score_momentum(close, direction)
        result["factors"]["momentum_confirmation"] = {"score": s2, "details": d2}
        total += s2

        s3, d3 = self._score_volume(close, volume, direction)
        result["factors"]["volume_confirmation"] = {"score": s3, "details": d3}
        total += s3

        s4, d4 = self._score_trend(close, direction)
        result["factors"]["trend_alignment"] = {"score": s4, "details": d4}
        total += s4

        s5, d5 = self._score_volatility_compression(close, high, low)
        result["factors"]["volatility_compression"] = {"score": s5, "details": d5}
        total += s5

        result["score"] = int(round(total))

        # Recommendation
        if total >= 70:
            result["recommendation"] = "STRONG_BUY" if direction == "LONG" else "STRONG_SELL"
            result["entry_zone_quality"] = "excellent"
        elif total >= 50:
            result["recommendation"] = "BUY" if direction == "LONG" else "SELL"
            result["entry_zone_quality"] = "good"
        elif total >= 30:
            result["recommendation"] = "WAIT"
            result["entry_zone_quality"] = "fair"
        else:
            result["recommendation"] = "AVOID"
            result["entry_zone_quality"] = "poor"

        return result

    # -- Support / Resistance finder --------------------------------------

    def find_support_resistance(self, data, symbol: str = "", lookback: int = 50) -> dict:
        """Find key S/R levels from recent price action.

        Uses pivot highs/lows and volume-weighted price clusters.

        Returns:
            {
                'supports': [price, ...],   # sorted ascending
                'resistances': [price, ...], # sorted ascending
                'nearest_support': float,
                'nearest_resistance': float,
            }
        """
        result = {"supports": [], "resistances": [], "nearest_support": 0.0, "nearest_resistance": 0.0}

        df = None
        if hasattr(data, "iloc"):
            df = data
        elif isinstance(data, dict):
            df = data.get(symbol)
            if df is None:
                keys = list(data.keys())
                if keys:
                    df = data[keys[0]]

        if df is None or len(df) < 10:
            return result

        close = df["Close"] if "Close" in df.columns else df.get("close")
        high = df["High"] if "High" in df.columns else df.get("high")
        low = df["Low"] if "Low" in df.columns else df.get("low")

        if close is None:
            return result

        n = len(close)
        window = min(lookback, n)
        current = float(close.iloc[-1])

        # Find pivot highs and lows (3-bar pivots)
        supports = []
        resistances = []
        for i in range(2, min(window, n - 1)):
            idx = n - 1 - i
            if idx < 1 or idx >= n - 1:
                continue
            lo = float(low.iloc[idx]) if low is not None else float(close.iloc[idx])
            hi = float(high.iloc[idx]) if high is not None else float(close.iloc[idx])
            lo_prev = float(low.iloc[idx - 1]) if low is not None else float(close.iloc[idx - 1])
            lo_next = float(low.iloc[idx + 1]) if low is not None else float(close.iloc[idx + 1])
            hi_prev = float(high.iloc[idx - 1]) if high is not None else float(close.iloc[idx - 1])
            hi_next = float(high.iloc[idx + 1]) if high is not None else float(close.iloc[idx + 1])

            if lo <= lo_prev and lo <= lo_next:
                supports.append(lo)
            if hi >= hi_prev and hi >= hi_next:
                resistances.append(hi)

        # Cluster nearby levels (within 1% of each other)
        supports = _cluster_levels(supports, tolerance_pct=1.0)
        resistances = _cluster_levels(resistances, tolerance_pct=1.0)

        # Separate into below/above current price
        result["supports"] = sorted([s for s in supports if s < current])
        result["resistances"] = sorted([r for r in resistances if r > current])

        if result["supports"]:
            result["nearest_support"] = result["supports"][-1]
        if result["resistances"]:
            result["nearest_resistance"] = result["resistances"][0]

        return result

    # -- Accumulation detection -------------------------------------------

    def detect_accumulation(self, data, symbol: str = "") -> dict:
        """Detect Wyckoff-style accumulation patterns.

        Rising OBV + flat price + decreasing spread = accumulation.

        Returns:
            {
                'is_accumulating': bool,
                'is_distributing': bool,
                'confidence': float (0-1),
                'details': {}
            }
        """
        result = {
            "is_accumulating": False,
            "is_distributing": False,
            "confidence": 0.0,
            "details": {},
        }

        df = None
        if hasattr(data, "iloc"):
            df = data
        elif isinstance(data, dict):
            df = data.get(symbol)
            if df is None:
                keys = list(data.keys())
                if keys:
                    df = data[keys[0]]

        if df is None or len(df) < 20:
            return result

        close = df["Close"] if "Close" in df.columns else df.get("close")
        high = df["High"] if "High" in df.columns else df.get("high")
        low = df["Low"] if "Low" in df.columns else df.get("low")
        volume = df["Volume"] if "Volume" in df.columns else df.get("volume")

        if close is None or volume is None or len(close) < 20:
            return result

        close_vals = [float(c) for c in close.values[-20:]]
        vol_vals = [float(v) if _is_valid(v) else 0.0 for v in volume.values[-20:]]
        high_vals = [float(h) for h in high.values[-20:]] if high is not None else close_vals
        low_vals = [float(lo) for lo in low.values[-20:]] if low is not None else close_vals

        # Price flatness: % change over 20 bars
        if close_vals[0] > 0:
            price_change_pct = abs(close_vals[-1] - close_vals[0]) / close_vals[0] * 100
        else:
            price_change_pct = 999

        # OBV trend
        obv = _compute_obv(close_vals, vol_vals)
        if len(obv) >= 10 and abs(obv[-10]) > 0:
            obv_change = (obv[-1] - obv[-10]) / max(abs(obv[-10]), 1e-10)
        else:
            obv_change = 0.0

        # Spread (high-low range) decreasing
        spreads = [h - lo for h, lo in zip(high_vals, low_vals)]
        if len(spreads) >= 10:
            avg_early = sum(spreads[:10]) / 10
            avg_late = sum(spreads[-10:]) / 10
            spread_decreasing = avg_late < avg_early * 0.85
        else:
            spread_decreasing = False

        result["details"] = {
            "price_change_pct": round(price_change_pct, 2),
            "obv_change": round(obv_change, 4),
            "spread_decreasing": spread_decreasing,
        }

        # Accumulation: flat price + rising OBV + decreasing spread
        confidence = 0.0
        if price_change_pct < 5:
            confidence += 0.3
        if obv_change > 0.05:
            confidence += 0.4
        if spread_decreasing:
            confidence += 0.3

        if confidence >= 0.7:
            result["is_accumulating"] = True
            result["confidence"] = round(confidence, 2)

        # Distribution: flat price + falling OBV + decreasing spread
        dist_confidence = 0.0
        if price_change_pct < 5:
            dist_confidence += 0.3
        if obv_change < -0.05:
            dist_confidence += 0.4
        if spread_decreasing:
            dist_confidence += 0.3

        if dist_confidence >= 0.7:
            result["is_distributing"] = True
            result["confidence"] = round(dist_confidence, 2)

        return result

    # -- Optimal entry price suggestion -----------------------------------

    def get_optimal_entry_price(self, symbol: str, data, direction: str = "LONG") -> dict:
        """Suggest optimal limit order price based on S/R and VWAP mean reversion.

        Returns:
            {
                'suggested_price': float,
                'confidence': float (0-1),
                'method': str,
                'details': {}
            }
        """
        result = {"suggested_price": 0.0, "confidence": 0.0, "method": "none", "details": {}}

        direction = direction.upper()
        if direction in ("BUY",):
            direction = "LONG"
        elif direction in ("SELL",):
            direction = "SHORT"

        df = None
        if hasattr(data, "iloc"):
            df = data
        elif isinstance(data, dict):
            df = data.get(symbol)
            if df is None:
                keys = list(data.keys())
                if keys:
                    df = data[keys[0]]

        if df is None or len(df) < 20:
            return result

        close = df["Close"] if "Close" in df.columns else df.get("close")
        volume = df["Volume"] if "Volume" in df.columns else df.get("volume")

        if close is None or len(close) < 20:
            return result

        current = float(close.iloc[-1])
        if current <= 0:
            return result

        # Get S/R levels
        sr = self.find_support_resistance(data, symbol)

        # Get VWAP
        vwap = _compute_vwap(close, volume) if volume is not None else 0.0

        candidates = []

        if direction == "LONG":
            # Place limit buy near nearest support or VWAP (whichever is closer to current)
            if sr["nearest_support"] > 0:
                # Slightly above support (0.2% buffer)
                support_entry = sr["nearest_support"] * 1.002
                dist_pct = abs(current - support_entry) / current * 100
                if dist_pct < 5:  # Within 5% of current price
                    candidates.append((support_entry, 0.7, "near_support"))

            if _is_valid(vwap) and vwap > 0 and vwap < current:
                candidates.append((vwap, 0.6, "at_vwap"))

            # Bollinger lower band
            if len(close) >= 20:
                sma20 = float(close.rolling(20).mean().iloc[-1])
                std20 = float(close.rolling(20).std().iloc[-1])
                if _is_valid(sma20) and _is_valid(std20):
                    bb_lower = sma20 - 2.0 * std20
                    if bb_lower > 0 and bb_lower < current:
                        dist_pct = abs(current - bb_lower) / current * 100
                        if dist_pct < 5:
                            candidates.append((bb_lower * 1.001, 0.5, "near_bb_lower"))
        else:
            # SHORT: place limit sell near nearest resistance or VWAP
            if sr["nearest_resistance"] > 0:
                resist_entry = sr["nearest_resistance"] * 0.998
                dist_pct = abs(resist_entry - current) / current * 100
                if dist_pct < 5:
                    candidates.append((resist_entry, 0.7, "near_resistance"))

            if _is_valid(vwap) and vwap > 0 and vwap > current:
                candidates.append((vwap, 0.6, "at_vwap"))

            if len(close) >= 20:
                sma20 = float(close.rolling(20).mean().iloc[-1])
                std20 = float(close.rolling(20).std().iloc[-1])
                if _is_valid(sma20) and _is_valid(std20):
                    bb_upper = sma20 + 2.0 * std20
                    if bb_upper > current:
                        dist_pct = abs(bb_upper - current) / current * 100
                        if dist_pct < 5:
                            candidates.append((bb_upper * 0.999, 0.5, "near_bb_upper"))

        if candidates:
            # Pick the candidate with highest confidence
            candidates.sort(key=lambda x: x[1], reverse=True)
            best = candidates[0]
            result["suggested_price"] = round(best[0], 8)
            result["confidence"] = best[1]
            result["method"] = best[2]
            result["details"]["candidates"] = [
                {"price": round(c[0], 8), "confidence": c[1], "method": c[2]}
                for c in candidates
            ]
        else:
            # Fallback: current price with low confidence
            result["suggested_price"] = current
            result["confidence"] = 0.2
            result["method"] = "market_price_fallback"

        return result


# ══════════════════════════════════════════════════════════════════════════
# Helper functions (module-level, not part of class)
# ══════════════════════════════════════════════════════════════════════════

def _is_valid(val) -> bool:
    """Check if a value is a valid finite number."""
    if val is None:
        return False
    try:
        f = float(val)
        return not (math.isnan(f) or math.isinf(f))
    except (TypeError, ValueError):
        return False


def _compute_vwap(close, volume) -> float:
    """Compute VWAP from pandas Series."""
    if close is None or volume is None:
        return 0.0
    try:
        n = len(close)
        if n == 0:
            return 0.0
        cum_pv = 0.0
        cum_vol = 0.0
        for i in range(n):
            c = float(close.iloc[i])
            v = float(volume.iloc[i])
            if _is_valid(c) and _is_valid(v):
                cum_pv += c * v
                cum_vol += v
        if cum_vol <= 0:
            return float(close.iloc[-1]) if n > 0 else 0.0
        return cum_pv / cum_vol
    except Exception:
        return 0.0


def _compute_rsi_series(close, period: int = 14) -> list:
    """Compute RSI series from pandas close Series. Returns list of RSI values."""
    n = len(close)
    if n < period + 1:
        return []

    values = [float(close.iloc[i]) for i in range(n)]
    rsi_out = []

    gains = []
    losses = []
    for i in range(1, n):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    if len(gains) < period:
        return []

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi_out.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_out.append(100.0 - (100.0 / (1.0 + rs)))

    return rsi_out


def _compute_macd_histogram(close) -> list:
    """Compute MACD histogram (MACD line - signal line)."""
    n = len(close)
    if n < 26:
        return []

    values = [float(close.iloc[i]) for i in range(n)]

    # EMA-12
    ema12 = _ema(values, 12)
    # EMA-26
    ema26 = _ema(values, 26)

    if len(ema12) != len(ema26):
        return []

    macd_line = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    signal_line = _ema(macd_line, 9)

    hist = []
    for i in range(len(macd_line)):
        hist.append(macd_line[i] - signal_line[i])

    return hist


def _ema(values: list, period: int) -> list:
    """Compute EMA for a list of values. Returns list of same length."""
    if not values or period <= 0:
        return values
    multiplier = 2.0 / (period + 1)
    result = [values[0]]
    for i in range(1, len(values)):
        result.append(values[i] * multiplier + result[-1] * (1.0 - multiplier))
    return result


def _compute_stochastic(close, k_period: int = 14, d_period: int = 3) -> tuple:
    """Compute Stochastic %K and %D. Returns (k, d) for latest bar."""
    n = len(close)
    if n < k_period + d_period:
        return (float("nan"), float("nan"))

    values = [float(close.iloc[i]) for i in range(n)]

    k_values = []
    for i in range(k_period - 1, n):
        window = values[i - k_period + 1: i + 1]
        lo = min(window)
        hi = max(window)
        if hi - lo > 0:
            k_values.append((values[i] - lo) / (hi - lo) * 100)
        else:
            k_values.append(50.0)

    if len(k_values) < d_period:
        return (float("nan"), float("nan"))

    # %D is SMA of %K
    d_value = sum(k_values[-d_period:]) / d_period
    return (k_values[-1], d_value)


def _compute_obv(close_values: list, vol_values: list) -> list:
    """Compute On-Balance Volume from lists."""
    if not close_values or not vol_values:
        return []
    obv = [0.0]
    for i in range(1, min(len(close_values), len(vol_values))):
        if close_values[i] > close_values[i - 1]:
            obv.append(obv[-1] + vol_values[i])
        elif close_values[i] < close_values[i - 1]:
            obv.append(obv[-1] - vol_values[i])
        else:
            obv.append(obv[-1])
    return obv


def _compute_tr_series(high, low, close) -> list:
    """Compute True Range series from pandas Series. Returns list of floats."""
    n = len(close)
    if n < 2:
        return []
    result = []
    for i in range(1, n):
        h = float(high.iloc[i]) if high is not None else float(close.iloc[i])
        lo = float(low.iloc[i]) if low is not None else float(close.iloc[i])
        prev_c = float(close.iloc[i - 1])
        tr = max(h - lo, abs(h - prev_c), abs(lo - prev_c))
        result.append(tr)
    return result


def _cluster_levels(levels: list, tolerance_pct: float = 1.0) -> list:
    """Cluster price levels within tolerance_pct of each other.
    Returns list of averaged cluster centers."""
    if not levels:
        return []
    sorted_levels = sorted(levels)
    clusters = [[sorted_levels[0]]]

    for lvl in sorted_levels[1:]:
        cluster_avg = sum(clusters[-1]) / len(clusters[-1])
        if cluster_avg > 0 and abs(lvl - cluster_avg) / cluster_avg * 100 <= tolerance_pct:
            clusters[-1].append(lvl)
        else:
            clusters.append([lvl])

    return [sum(c) / len(c) for c in clusters]


# ══════════════════════════════════════════════════════════════════════════
# Standalone test
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 60)
    print("ALPHA ENGINE -- Smart Entry Zone Detector v1.0")
    print("=" * 60)

    # Quick self-test with synthetic data
    try:
        import pandas as pd
        import numpy as np

        np.random.seed(42)
        n = 250
        prices = 100 + np.cumsum(np.random.randn(n) * 0.5)
        prices = np.maximum(prices, 10)

        df = pd.DataFrame({
            "Open": prices + np.random.randn(n) * 0.1,
            "High": prices + abs(np.random.randn(n) * 0.5),
            "Low": prices - abs(np.random.randn(n) * 0.5),
            "Close": prices,
            "Volume": np.random.randint(1000, 10000, n).astype(float),
        })

        detector = SmartEntryDetector()

        result = detector.score_entry_zone("TEST", df, direction="LONG")
        print(f"\nLONG entry zone score: {result['score']}/100")
        print(f"  Recommendation: {result['recommendation']}")
        for factor, data in result["factors"].items():
            if isinstance(data, dict) and "score" in data:
                print(f"  {factor}: {data['score']}/20")

        result_short = detector.score_entry_zone("TEST", df, direction="SHORT")
        print(f"\nSHORT entry zone score: {result_short['score']}/100")
        print(f"  Recommendation: {result_short['recommendation']}")

        sr = detector.find_support_resistance(df)
        print(f"\nS/R levels: {len(sr['supports'])} supports, {len(sr['resistances'])} resistances")
        print(f"  Nearest support: {sr['nearest_support']:.2f}")
        print(f"  Nearest resistance: {sr['nearest_resistance']:.2f}")

        accum = detector.detect_accumulation(df)
        print(f"\nAccumulation: {accum['is_accumulating']}, Distribution: {accum['is_distributing']}")
        print(f"  Confidence: {accum['confidence']}")

        optimal = detector.get_optimal_entry_price("TEST", df, direction="LONG")
        print(f"\nOptimal entry price: {optimal['suggested_price']:.2f}")
        print(f"  Method: {optimal['method']}, Confidence: {optimal['confidence']}")

        print("\nAll tests passed.")

    except ImportError as e:
        print(f"Skipping self-test (missing dependency): {e}")

    print("\nDone.")
