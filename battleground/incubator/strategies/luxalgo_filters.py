#!/usr/bin/env python3
"""
Probabilistic Breakout Forecaster — Python Port
=================================================

Ported from: LuxAlgo Probabilistic Breakout Forecaster (Pine Script v6)
License: CC BY-NC-SA 4.0 — adapted for non-commercial research
Date: 2026-03-13

Core Math (Log-Normal Random Walk):
  σ = std_dev(log_returns, lookback)
  Z_upper = ln(range_high / price) / (σ × √horizon)
  Z_lower = ln(range_low / price) / (σ × √horizon)
  P(breakout_up)   = 1 - Φ(Z_upper)   where Φ = normal CDF
  P(breakout_down)  = Φ(Z_lower)
  Squeeze = max(0, 1 - ATR/avg_ATR) × 100

Also includes:
  - Consecutive Candle Streak Analyzer (from LuxAlgo Streak Analysis)
  - Multi-Horizon Volatility Waterfall (from LuxAlgo Volatility Waterfall)
  - Structural SVM Ranker concepts for break quality scoring
"""

from __future__ import annotations

import math
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Normal CDF — Abramowitz & Stegun approximation (same as LuxAlgo)
# ══════════════════════════════════════════════════════════════════════

def _normal_cdf(x: float) -> float:
    """Normal cumulative distribution function (Abramowitz & Stegun)."""
    t = 1.0 / (1.0 + 0.2316419 * abs(x))
    d = 0.3989423 * math.exp(-x * x / 2.0)
    p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.7814779 + t * (-1.821256 + t * 1.3302744))))
    return 1.0 - p if x > 0 else p


# ══════════════════════════════════════════════════════════════════════
# 1. PROBABILISTIC BREAKOUT FORECASTER
# ══════════════════════════════════════════════════════════════════════

class BreakoutForecaster:
    """
    LuxAlgo Probabilistic Breakout Forecaster — Python port.

    Calculates the statistical probability of price breaking above the
    recent range high or below the range low within a specified time horizon,
    using a log-normal random walk model.

    Usage:
        bf = BreakoutForecaster(range_len=20, horizon=10, vol_lookback=50)
        result = bf.forecast(closes, highs, lows)
        # result["bull_prob"] = 62.3  (% chance of upside breakout)
        # result["bear_prob"] = 18.7  (% chance of downside breakdown)
        # result["squeeze"]  = 45.2  (volatility compression %)
    """

    def __init__(self, range_len: int = 20, horizon: int = 10, vol_lookback: int = 50):
        self.range_len = range_len
        self.horizon = horizon
        self.vol_lookback = vol_lookback

    def forecast(self, closes: List[float], highs: List[float], lows: List[float]) -> dict:
        """
        Compute breakout probabilities.

        Returns dict with:
          - bull_prob: % probability of breaking above range high
          - bear_prob: % probability of breaking below range low
          - squeeze: volatility squeeze intensity (0-100%)
          - upper_range: the range high
          - lower_range: the range low
          - sigma: volatility (std dev of log returns)
        """
        n = len(closes)
        min_required = max(self.range_len, self.vol_lookback) + 2
        if n < min_required:
            return {"bull_prob": 50.0, "bear_prob": 50.0, "squeeze": 0.0,
                    "upper_range": 0, "lower_range": 0, "sigma": 0}

        current = closes[-1]
        upper = max(highs[-self.range_len:])
        lower = min(lows[-self.range_len:])

        # Log returns standard deviation
        log_returns = []
        for i in range(n - self.vol_lookback, n):
            if i > 0 and closes[i - 1] > 0:
                log_returns.append(math.log(closes[i] / closes[i - 1]))

        if not log_returns:
            return {"bull_prob": 50.0, "bear_prob": 50.0, "squeeze": 0.0,
                    "upper_range": upper, "lower_range": lower, "sigma": 0}

        mean_lr = sum(log_returns) / len(log_returns)
        variance = sum((lr - mean_lr) ** 2 for lr in log_returns) / len(log_returns)
        sigma = math.sqrt(variance)

        denominator = sigma * math.sqrt(self.horizon)

        if denominator <= 1e-10:
            return {"bull_prob": 50.0, "bear_prob": 50.0, "squeeze": 0.0,
                    "upper_range": upper, "lower_range": lower, "sigma": sigma}

        # Z-scores
        z_upper = math.log(upper / current) / denominator if current > 0 else 0
        z_lower = math.log(lower / current) / denominator if current > 0 else 0

        bull_prob = (1.0 - _normal_cdf(z_upper)) * 100
        bear_prob = _normal_cdf(z_lower) * 100

        # Squeeze intensity
        squeeze = self._calc_squeeze(highs, lows, closes)

        return {
            "bull_prob": round(bull_prob, 2),
            "bear_prob": round(bear_prob, 2),
            "squeeze": round(squeeze, 2),
            "upper_range": round(upper, 6),
            "lower_range": round(lower, 6),
            "sigma": round(sigma, 6),
        }

    def _calc_squeeze(self, highs: List[float], lows: List[float], closes: List[float]) -> float:
        """Calculate volatility squeeze intensity (ATR vs avg ATR)."""
        n = len(closes)
        if n < 15:
            return 0.0

        # Current ATR (14-period)
        trs = []
        for i in range(max(1, n - 14), n):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            trs.append(tr)
        current_atr = sum(trs) / len(trs) if trs else 0

        # Average ATR (100-period)
        all_trs = []
        for i in range(max(1, n - 100), n):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            all_trs.append(tr)
        avg_atr = sum(all_trs) / len(all_trs) if all_trs else current_atr

        if avg_atr <= 0:
            return 0.0

        return max(0, (1 - current_atr / avg_atr)) * 100

    def should_enter(self, closes, highs, lows, direction: str = "LONG") -> Tuple[bool, dict]:
        """
        Check if breakout probability supports the trade direction.

        Returns (should_enter, forecast_data).
        """
        result = self.forecast(closes, highs, lows)

        if direction in ("BUY", "LONG"):
            enter = result["bull_prob"] > 40 and result["bull_prob"] > result["bear_prob"]
        else:
            enter = result["bear_prob"] > 40 and result["bear_prob"] > result["bull_prob"]

        return enter, result


# ══════════════════════════════════════════════════════════════════════
# 2. CONSECUTIVE CANDLE STREAK ANALYZER
# ══════════════════════════════════════════════════════════════════════

class StreakAnalyzer:
    """
    LuxAlgo Consecutive Candle Streak Analysis — Python port.

    Tracks consecutive bullish/bearish candle streaks and computes
    the historical probability of reversal at the current streak length.
    """

    def analyze(self, closes: List[float]) -> dict:
        """
        Analyze current streak and historical reversal probability.

        Returns:
          - direction: "BULL" or "BEAR"
          - length: current streak length
          - reversal_probability: 0.0-1.0
          - pct_change: % change during current streak
          - historical_matches: how many historical streaks of same length+
          - max_observed: longest streak ever seen in this direction
          - unprecedented: True if current streak exceeds all historical
        """
        if len(closes) < 3:
            return {"direction": "NEUTRAL", "length": 0, "reversal_probability": 0.5,
                    "pct_change": 0, "historical_matches": 0, "max_observed": 0,
                    "unprecedented": False}

        # Build streak history
        streaks = []  # (direction, length, start_idx)
        current_dir = None
        current_len = 0
        current_start = 0

        for i in range(1, len(closes)):
            d = "BULL" if closes[i] > closes[i - 1] else "BEAR"
            if d == current_dir:
                current_len += 1
            else:
                if current_dir and current_len > 0:
                    streaks.append((current_dir, current_len, current_start))
                current_dir = d
                current_len = 1
                current_start = i

        # Current active streak
        active_dir = current_dir or "NEUTRAL"
        active_len = current_len
        active_pct = ((closes[-1] - closes[-(active_len + 1)]) / closes[-(active_len + 1)] * 100
                      if active_len < len(closes) else 0)

        # Historical reversal probability at this streak length
        matching = [s for s in streaks if s[0] == active_dir and s[1] >= active_len]
        continued = [s for s in streaks if s[0] == active_dir and s[1] > active_len]

        if matching:
            reversal_prob = 1 - (len(continued) / len(matching))
        else:
            reversal_prob = 0.5

        max_obs = max((s[1] for s in streaks if s[0] == active_dir), default=active_len)

        return {
            "direction": active_dir,
            "length": active_len,
            "reversal_probability": round(reversal_prob, 4),
            "pct_change": round(active_pct, 4),
            "historical_matches": len(matching),
            "max_observed": max_obs,
            "unprecedented": active_len > max_obs,
        }

    def should_enter(self, closes: List[float], trade_direction: str) -> Tuple[bool, dict]:
        """
        Check if the current streak supports entering.

        Blocks entry if:
          1. Reversal probability > 75% in the trade direction
          2. Streak is "unprecedented" (longer than any historical)
        """
        result = self.analyze(closes)

        # If going LONG during a BULL streak with high reversal prob → skip
        if trade_direction in ("BUY", "LONG") and result["direction"] == "BULL":
            if result["reversal_probability"] > 0.75:
                return False, result

        if trade_direction in ("SELL", "SHORT") and result["direction"] == "BEAR":
            if result["reversal_probability"] > 0.75:
                return False, result

        if result["unprecedented"]:
            return False, result  # never seen this streak length before

        return True, result


# ══════════════════════════════════════════════════════════════════════
# 3. STRUCTURAL SVM RANKER (simplified)
# ══════════════════════════════════════════════════════════════════════

class StructuralSVMRanker:
    """
    Score structural breaks (BOS/CHoCH) 0-100 using weighted features.

    Features:
      1. Relative volume (current vs 20-period avg)
      2. RSI momentum (distance from 50, normalized)
      3. Break distance (how far price closed past pivot, normalized by ATR)

    Combined through sigmoid for 0-100 score.
    High score (>70) = high-conviction break, low (<30) = likely fakeout.
    """

    def __init__(self, w_volume: float = 1.0, w_rsi: float = 0.8, w_distance: float = 1.2):
        self.w_vol = w_volume
        self.w_rsi = w_rsi
        self.w_dist = w_distance

    def score_break(
        self,
        current_volume: float,
        avg_volume_20: float,
        rsi: float,
        pivot_level: float,
        close_price: float,
        atr: float,
    ) -> float:
        """
        Score a structural break 0-100.

        Args:
            current_volume: volume of the breakout candle
            avg_volume_20: 20-period average volume
            rsi: current RSI value (0-100)
            pivot_level: the swing high/low that was broken
            close_price: where price closed
            atr: current ATR for normalization
        """
        # Feature 1: Relative volume
        rel_vol = (current_volume / avg_volume_20) if avg_volume_20 > 0 else 1.0

        # Feature 2: RSI momentum (how far from neutral 50)
        rsi_momentum = abs(rsi - 50) / 50  # normalized 0-1

        # Feature 3: Break distance (normalized by ATR)
        break_dist = abs(close_price - pivot_level) / atr if atr > 0 else 0

        # Weighted sum
        raw = self.w_vol * rel_vol + self.w_rsi * rsi_momentum + self.w_dist * break_dist

        # Sigmoid normalization → 0-100
        score = (1.0 / (1.0 + math.exp(-raw))) * 100

        return round(score, 1)

    def is_high_conviction(self, score: float, threshold: float = 60.0) -> bool:
        """Check if the break score exceeds the conviction threshold."""
        return score >= threshold


# ══════════════════════════════════════════════════════════════════════
# 4. MULTI-HORIZON VOLATILITY WATERFALL
# ══════════════════════════════════════════════════════════════════════

class VolatilityWaterfall:
    """
    LuxAlgo Multi-Horizon Volatility Waterfall — Python port.

    Ranks ATR percentile across 10 different timeframes.
    Returns aggregate "heat" (0-100) and regime classification.

    Heat > 70: EXPANSION (volatility breakout — trend likely)
    Heat < 30: COMPRESSION (squeeze — breakout imminent)
    30-70:     NEUTRAL
    """

    def __init__(self, base_step: int = 10, percentile_lookback: int = 200):
        self.horizons = [base_step * (i + 1) for i in range(10)]
        self.lookback = percentile_lookback

    def compute(self, highs: List[float], lows: List[float], closes: List[float]) -> dict:
        """
        Compute volatility heat across all horizons.

        Returns:
          - aggregate_heat: 0-100 (average heat across all horizons)
          - regime: "EXPANSION" | "COMPRESSION" | "NEUTRAL"
          - per_horizon: list of heat values per horizon
          - all_hot: True if all horizons > 70 (cluster signal)
          - all_cold: True if all horizons < 30 (squeeze)
        """
        n = len(closes)
        if n < 15:
            return {"aggregate_heat": 50, "regime": "NEUTRAL",
                    "per_horizon": [50] * 10, "all_hot": False, "all_cold": False}

        # Calculate all true ranges
        all_trs = []
        for i in range(1, n):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            all_trs.append(tr)

        heats = []
        for horizon in self.horizons:
            if len(all_trs) < horizon:
                heats.append(50.0)
                continue

            # Current ATR for this horizon
            current_atr = sum(all_trs[-horizon:]) / horizon

            # Historical ATR values for percentile ranking
            history = []
            for j in range(len(all_trs) - horizon):
                avg = sum(all_trs[j:j + horizon]) / horizon
                history.append(avg)

            if not history:
                heats.append(50.0)
                continue

            # Percentile rank
            rank = sum(1 for h in history if h <= current_atr) / len(history) * 100
            heats.append(rank)

        aggregate = sum(heats) / len(heats)

        if aggregate > 70:
            regime = "EXPANSION"
        elif aggregate < 30:
            regime = "COMPRESSION"
        else:
            regime = "NEUTRAL"

        return {
            "aggregate_heat": round(aggregate, 1),
            "regime": regime,
            "per_horizon": [round(h, 1) for h in heats],
            "all_hot": all(h > 70 for h in heats),
            "all_cold": all(h < 30 for h in heats),
        }

    def should_enter(self, highs, lows, closes) -> Tuple[bool, dict]:
        """Check if volatility regime supports entry."""
        result = self.compute(highs, lows, closes)

        # Best to enter during NEUTRAL or early EXPANSION
        # Avoid deep COMPRESSION (waiting) or extreme EXPANSION (overheated)
        if result["regime"] == "COMPRESSION" and result["aggregate_heat"] < 15:
            return False, result  # deep squeeze — wait for breakout

        if result["all_hot"]:
            return False, result  # all horizons screaming — market overheated

        return True, result


# ══════════════════════════════════════════════════════════════════════
# Combined Filter Pipeline
# ══════════════════════════════════════════════════════════════════════

class LuxAlgoFilterPipeline:
    """
    Combines all LuxAlgo-inspired filters into a single pipeline.

    Usage:
        pipeline = LuxAlgoFilterPipeline()
        pipeline.train(closes, highs, lows)  # feed 500+ bars
        result = pipeline.evaluate("LONG", current_rsi=55.0)
        # result["should_enter"] = True/False
        # result["confidence_boost"] = 0.12
        # result["filters"] = {each filter's output}
    """

    def __init__(self):
        from rsi_range_predictor import RSIRangePredictor
        self.rsi_pred = RSIRangePredictor(segments=10, forecast_len=50)
        self.breakout = BreakoutForecaster(range_len=20, horizon=10, vol_lookback=50)
        self.streak = StreakAnalyzer()
        self.waterfall = VolatilityWaterfall(base_step=10)
        self._trained = False

    def train(self, closes: List[float], highs: List[float], lows: List[float]):
        """Train all sub-models."""
        self.rsi_pred.train_from_closes(closes)
        self._closes = closes
        self._highs = highs
        self._lows = lows
        self._trained = True

    def evaluate(self, direction: str, current_rsi: float) -> dict:
        """
        Run all filters. Returns combined decision.
        """
        if not self._trained:
            return {"should_enter": True, "confidence_boost": 0.0, "filters": {}}

        filters = {}
        should_enter = True
        confidence_boost = 0.0

        # 1. RSI Prediction
        rsi_ok, rsi_boost = self.rsi_pred.should_enter(current_rsi, direction)
        filters["rsi_prediction"] = self.rsi_pred.predict(current_rsi)
        if not rsi_ok:
            should_enter = False
            filters["rsi_prediction"]["blocked"] = True
        confidence_boost += rsi_boost

        # 2. Breakout Probability
        bo_ok, bo_data = self.breakout.should_enter(
            self._closes, self._highs, self._lows, direction
        )
        filters["breakout_forecast"] = bo_data
        if not bo_ok:
            # Don't block but reduce confidence
            confidence_boost -= 0.05

        # 3. Streak Analysis
        str_ok, str_data = self.streak.should_enter(self._closes, direction)
        filters["streak"] = str_data
        if not str_ok:
            should_enter = False
            filters["streak"]["blocked"] = True

        # 4. Volatility Waterfall
        vol_ok, vol_data = self.waterfall.should_enter(
            self._highs, self._lows, self._closes
        )
        filters["volatility"] = vol_data
        if not vol_ok:
            should_enter = False
            filters["volatility"]["blocked"] = True

        return {
            "should_enter": should_enter,
            "confidence_boost": round(max(0, confidence_boost), 4),
            "filters": filters,
            "filters_passed": sum([rsi_ok, bo_ok, str_ok, vol_ok]),
            "filters_total": 4,
        }


# ══════════════════════════════════════════════════════════════════════
# Standalone Test
# ══════════════════════════════════════════════════════════════════════

def main():
    """Test all modules with live Binance data."""
    try:
        import requests
    except ImportError:
        print("requests not available")
        return

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "ENAUSDT", "NEARUSDT"]

    print("=" * 70)
    print("  LUXALGO-INSPIRED FILTER PIPELINE TEST")
    print("=" * 70)

    bf = BreakoutForecaster()
    sa = StreakAnalyzer()
    vw = VolatilityWaterfall()

    for sym in symbols:
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1h&limit=500"
            resp = requests.get(url, timeout=10)
            data = resp.json()

            closes = [float(k[4]) for k in data]
            highs = [float(k[2]) for k in data]
            lows = [float(k[3]) for k in data]

            # Breakout Forecast
            bo = bf.forecast(closes, highs, lows)

            # Streak
            streak = sa.analyze(closes)

            # Volatility
            vol = vw.compute(highs, lows, closes)

            print(f"\n  {sym}")
            print(f"  {'─' * 50}")
            print(f"  Breakout:  Bull {bo['bull_prob']:.1f}% | Bear {bo['bear_prob']:.1f}% | Squeeze {bo['squeeze']:.1f}%")
            print(f"  Streak:    {streak['direction']} x{streak['length']} (reversal prob: {streak['reversal_probability']:.1%})")
            print(f"  Volatility: {vol['regime']} (heat: {vol['aggregate_heat']:.0f}/100)")

            if streak["unprecedented"]:
                print(f"  ⚠️ UNPRECEDENTED streak — longest ever!")

        except Exception as e:
            print(f"  {sym}: Error — {e}")

    print(f"\n{'=' * 70}")


if __name__ == "__main__":
    main()
