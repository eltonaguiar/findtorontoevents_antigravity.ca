"""
ALPHA_ENGINE -- Unified Confluence Pipeline
============================================
Multi-stage signal quality filter combining regime detection, SMC confluence
scoring, entropy analysis, volume confirmation, and multi-timeframe trend
alignment into a single post-filter pipeline.

Any strategy's raw signals can be passed through this pipeline to get
enhanced scoring and quality gating.

Architecture:
  Stage 1: Regime Check     -- HMM-inspired 3-state regime alignment
  Stage 2: SMC Score        -- Smart Money Concepts composite (OB+FVG+Liq+BOS+MTF)
  Stage 3: Entropy Check    -- Shannon entropy regime for "decided" markets
  Stage 4: Volume Confirm   -- Volume ratio confirmation
  Stage 5: MTF Trend        -- EMA(9)/EMA(21)/EMA(50) directional alignment

References:
  - HMM regime: Hamilton (1989), tradingview_strategies_wave4.py
  - SMC: tradingview_strategies_wave2.py smc_confluence_score
  - Entropy: Shannon (1948), PhenLabs Entropy Divergence
  - LuxAlgo pipeline pattern: battleground/incubator/strategies/luxalgo_filters.py

Usage:
    from confluence_pipeline import UnifiedConfluencePipeline, filter_signals_through_pipeline

    pipeline = UnifiedConfluencePipeline(min_score=55.0)
    enhanced = pipeline.filter_signals(raw_signals, ohlcv_data)

    # Or use the convenience function:
    enhanced = filter_signals_through_pipeline(raw_signals, ohlcv_data)
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from indicators import rsi, ema, sma, atr, volume_ratio

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regime constants (mirrored from tradingview_strategies_wave4.py)
# ---------------------------------------------------------------------------
_REGIME_BULL = 0
_REGIME_BEAR = 1
_REGIME_CHOP = 2
_REGIME_NAMES = {0: "BULL", 1: "BEAR", 2: "CHOP"}
_PERSISTENCE_BONUS = 1.5

# ---------------------------------------------------------------------------
# Stage weight defaults (how much each stage contributes to composite score)
# ---------------------------------------------------------------------------
_STAGE_WEIGHTS = {
    "regime": 0.25,
    "smc": 0.25,
    "entropy": 0.15,
    "volume": 0.15,
    "trend": 0.20,
}


# =====================================================================
# Internal helpers (reimplemented to avoid circular imports)
# =====================================================================

def _classify_regimes(close: pd.Series, high: pd.Series, low: pd.Series,
                      lookback: int = 100) -> pd.Series:
    """
    Classify each bar into BULL/BEAR/CHOP using rolling feature scoring.

    Features (all normalized to [0, 1] over lookback window):
      - log_returns: smoothed 14-period average of log(close/close[1])
      - volatility: rolling std of log returns, 20-period
      - trend_strength: abs(EMA9 - EMA21) / ATR (normalized displacement)
      - momentum: RSI(14) mapped to [0, 1]

    Scoring:
      BULL  = returns_norm*0.3 + (1-vol_norm)*0.2 + trend_norm*0.3 + mom_norm*0.2
      BEAR  = (1-returns_norm)*0.3 + vol_norm*0.2 + trend_norm*0.3 + (1-mom_norm)*0.2
      CHOP  = (1-trend_norm)*0.5 + (1-abs(mom_norm-0.5)*2)*0.3 + (1-vol_norm)*0.2
    """
    n = len(close)
    regimes = pd.Series(np.nan, index=close.index, dtype=float)

    if n < lookback:
        return regimes

    log_ret = np.log(close / close.shift(1))
    log_ret_smooth = log_ret.rolling(14, min_periods=1).mean()
    vol = log_ret.rolling(20, min_periods=5).std()

    ema9 = ema(close, 9)
    ema21 = ema(close, 21)
    atr_val = atr(high, low, close, 14)
    atr_safe = atr_val.replace(0, np.nan).ffill().fillna(1e-10)
    trend_str = (ema9 - ema21).abs() / atr_safe

    rsi_val = rsi(close, 14)

    prev_regime = _REGIME_CHOP

    for i in range(lookback, n):
        window = slice(i - lookback, i + 1)

        def _minmax(s: pd.Series, w: slice) -> float:
            chunk = s.iloc[w]
            mn, mx = chunk.min(), chunk.max()
            rng = mx - mn
            if rng == 0 or pd.isna(rng):
                return 0.5
            val = chunk.iloc[-1]
            if pd.isna(val):
                return 0.5
            return float((val - mn) / rng)

        ret_n = _minmax(log_ret_smooth, window)
        vol_n = _minmax(vol, window)
        trn_n = _minmax(trend_str, window)
        mom_n = float(rsi_val.iloc[i]) / 100.0 if not pd.isna(rsi_val.iloc[i]) else 0.5

        bull_score = ret_n * 0.3 + (1.0 - vol_n) * 0.2 + trn_n * 0.3 + mom_n * 0.2
        bear_score = (1.0 - ret_n) * 0.3 + vol_n * 0.2 + trn_n * 0.3 + (1.0 - mom_n) * 0.2
        chop_score = ((1.0 - trn_n) * 0.5
                      + (1.0 - abs(mom_n - 0.5) * 2.0) * 0.3
                      + (1.0 - vol_n) * 0.2)

        scores = [bull_score, bear_score, chop_score]
        scores[prev_regime] *= _PERSISTENCE_BONUS

        regime = int(np.argmax(scores))
        regimes.iloc[i] = regime
        prev_regime = regime

    return regimes


def _rolling_entropy(returns: pd.Series, window: int = 50,
                     n_bins: int = 10) -> pd.Series:
    """
    Calculate rolling Shannon entropy of return distribution.
    Normalized to [0, 1] where 0 = perfectly predictable, 1 = maximum randomness.
    """
    n = len(returns)
    entropy_vals = pd.Series(np.nan, index=returns.index)
    max_entropy = np.log2(n_bins)

    for i in range(window, n):
        chunk = returns.iloc[i - window:i].dropna().values
        if len(chunk) < window // 2:
            continue

        counts, _ = np.histogram(chunk, bins=n_bins)
        total = counts.sum()
        if total == 0:
            continue

        probs = counts / total
        probs = probs[probs > 0]
        h = -np.sum(probs * np.log2(probs))
        entropy_vals.iloc[i] = h / max_entropy

    return entropy_vals


def _compute_smc_composite(df: pd.DataFrame) -> tuple[float, str]:
    """
    Calculate SMC confluence composite score (0-100) for a single symbol's OHLCV data.

    Components (same weights as tradingview_strategies_wave2.py):
      - Order Block strength (volume-validated): 25%
      - Fair Value Gap (size and recency): 20%
      - Liquidity zone proximity (sweep detection): 20%
      - Market structure alignment (BOS/CHoCH): 20%
      - Multi-timeframe trend alignment (EMA stack): 15%

    Returns (score, description_string).
    """
    OB_LOOKBACK = 20
    FVG_LOOKBACK = 10
    BOS_LOOKBACK = 5
    SWING_LOOKBACK = 20

    close = df["Close"]
    high, low = df["High"], df["Low"]
    vol = df.get("Volume")

    if len(close) < 60:
        return 0.0, "insufficient_data"

    price_val = float(close.iloc[-1])
    atr_val = float(atr(high, low, close, 14).iloc[-1])
    vol_r = float(volume_ratio(vol).iloc[-1]) if vol is not None and len(vol) > 20 else 1.0

    ema9 = ema(close, 9)
    ema21 = ema(close, 21)
    ema50 = ema(close, 50)

    e9 = float(ema9.iloc[-1])
    e21 = float(ema21.iloc[-1])
    e50 = float(ema50.iloc[-1])

    bullish_bias = e9 > e21 > e50
    bearish_bias = e9 < e21 < e50

    # ---- Component 1: Order Block Score (25%) ----
    ob_score = 0.0
    if vol is not None and len(vol) > OB_LOOKBACK:
        avg_vol = float(vol.iloc[-OB_LOOKBACK:].mean())
        for j in range(max(2, len(close) - OB_LOOKBACK), len(close) - 2):
            is_swing_low = (float(low.iloc[j]) <= float(low.iloc[j - 1]) and
                            float(low.iloc[j]) <= float(low.iloc[j + 1]))
            is_swing_high = (float(high.iloc[j]) >= float(high.iloc[j - 1]) and
                             float(high.iloc[j]) >= float(high.iloc[j + 1]))

            vol_at_swing = float(vol.iloc[j])
            vol_mult = vol_at_swing / avg_vol if avg_vol > 0 else 0

            if bullish_bias and is_swing_low:
                ob_level = float(low.iloc[j])
                distance_pct = abs(price_val - ob_level) / price_val if price_val > 0 else 999
                if distance_pct < 0.03 and vol_mult > 2.0:
                    ob_score = min(100, 60 + vol_mult * 10)
                elif distance_pct < 0.05 and vol_mult > 1.5:
                    ob_score = max(ob_score, min(80, 40 + vol_mult * 10))

            elif bearish_bias and is_swing_high:
                ob_level = float(high.iloc[j])
                distance_pct = abs(price_val - ob_level) / price_val if price_val > 0 else 999
                if distance_pct < 0.03 and vol_mult > 2.0:
                    ob_score = min(100, 60 + vol_mult * 10)
                elif distance_pct < 0.05 and vol_mult > 1.5:
                    ob_score = max(ob_score, min(80, 40 + vol_mult * 10))

    # ---- Component 2: Fair Value Gap Score (20%) ----
    fvg_score = 0.0
    for j in range(max(2, len(close) - FVG_LOOKBACK), len(close)):
        if bullish_bias:
            gap = float(low.iloc[j]) - float(high.iloc[j - 2])
            if gap > 0:
                gap_pct = gap / float(high.iloc[j - 2]) if float(high.iloc[j - 2]) > 0 else 0
                recency = 1.0 - (len(close) - 1 - j) / FVG_LOOKBACK
                fvg_score = max(fvg_score,
                                min(100, (gap_pct / atr_val * price_val) * 50 * recency)
                                if atr_val > 0 else 0)
        elif bearish_bias:
            gap = float(low.iloc[j - 2]) - float(high.iloc[j])
            if gap > 0:
                gap_pct = gap / float(low.iloc[j - 2]) if float(low.iloc[j - 2]) > 0 else 0
                recency = 1.0 - (len(close) - 1 - j) / FVG_LOOKBACK
                fvg_score = max(fvg_score,
                                min(100, (gap_pct / atr_val * price_val) * 50 * recency)
                                if atr_val > 0 else 0)

    # ---- Component 3: Liquidity Score (20%) ----
    liq_score = 0.0
    swing_highs = []
    swing_lows = []
    lookback_start = max(2, len(close) - SWING_LOOKBACK - 5)
    lookback_end = max(2, len(close) - 3)

    for j in range(lookback_start, lookback_end):
        if (float(high.iloc[j]) >= float(high.iloc[j - 1]) and
                float(high.iloc[j]) >= float(high.iloc[j + 1])):
            swing_highs.append(float(high.iloc[j]))
        if (float(low.iloc[j]) <= float(low.iloc[j - 1]) and
                float(low.iloc[j]) <= float(low.iloc[j + 1])):
            swing_lows.append(float(low.iloc[j]))

    cur_high = float(high.iloc[-1])
    cur_low = float(low.iloc[-1])
    cur_close = float(close.iloc[-1])

    if bullish_bias and swing_lows:
        for sl_level in swing_lows:
            if cur_low < sl_level and cur_close > sl_level:
                sweep_depth = (sl_level - cur_low) / atr_val if atr_val > 0 else 0
                liq_score = max(liq_score, min(100, 50 + sweep_depth * 50))

    elif bearish_bias and swing_highs:
        for sh_level in swing_highs:
            if cur_high > sh_level and cur_close < sh_level:
                sweep_depth = (cur_high - sh_level) / atr_val if atr_val > 0 else 0
                liq_score = max(liq_score, min(100, 50 + sweep_depth * 50))

    # ---- Component 4: Break of Structure Score (20%) ----
    bos_score = 0.0
    pivot_highs = []
    pivot_lows = []
    pivot_start = max(2, len(close) - BOS_LOOKBACK - 10)
    pivot_end = max(2, len(close) - BOS_LOOKBACK)

    for j in range(pivot_start, pivot_end):
        if j + 1 < len(high):
            if (float(high.iloc[j]) >= float(high.iloc[j - 1]) and
                    float(high.iloc[j]) >= float(high.iloc[j + 1])):
                pivot_highs.append(float(high.iloc[j]))
            if (float(low.iloc[j]) <= float(low.iloc[j - 1]) and
                    float(low.iloc[j]) <= float(low.iloc[j + 1])):
                pivot_lows.append(float(low.iloc[j]))

    for j in range(max(1, len(close) - BOS_LOOKBACK), len(close)):
        cur_c = float(close.iloc[j])
        cur_v = float(vol.iloc[j]) if vol is not None else 0
        avg_v = float(vol.iloc[max(0, j - 20):j].mean()) if vol is not None and j > 1 else 1

        if bullish_bias and pivot_highs:
            for ph in pivot_highs:
                if cur_c > ph:
                    vol_conviction = cur_v / avg_v if avg_v > 0 else 1
                    bos_score = max(bos_score, min(100, 50 + vol_conviction * 15))

        elif bearish_bias and pivot_lows:
            for pl in pivot_lows:
                if cur_c < pl:
                    vol_conviction = cur_v / avg_v if avg_v > 0 else 1
                    bos_score = max(bos_score, min(100, 50 + vol_conviction * 15))

    # ---- Component 5: Multi-Timeframe Trend Score (15%) ----
    mtf_score = 0.0
    if bullish_bias:
        alignment_count = 0
        if e9 > e21:
            alignment_count += 1
        if e21 > e50:
            alignment_count += 1
        if price_val > e9:
            alignment_count += 1
        mtf_score = (alignment_count / 3.0) * 100
    elif bearish_bias:
        alignment_count = 0
        if e9 < e21:
            alignment_count += 1
        if e21 < e50:
            alignment_count += 1
        if price_val < e9:
            alignment_count += 1
        mtf_score = (alignment_count / 3.0) * 100

    # ---- Composite ----
    composite = (
        ob_score * 0.25 +
        fvg_score * 0.20 +
        liq_score * 0.20 +
        bos_score * 0.20 +
        mtf_score * 0.15
    )

    detail = (f"OB={ob_score:.0f} FVG={fvg_score:.0f} "
              f"LIQ={liq_score:.0f} BOS={bos_score:.0f} MTF={mtf_score:.0f}")

    return round(composite, 2), detail


# =====================================================================
# Main Pipeline Class
# =====================================================================

class UnifiedConfluencePipeline:
    """
    Multi-stage signal quality filter that combines regime detection,
    SMC confluence scoring, entropy analysis, volume confirmation,
    and multi-timeframe trend alignment.

    Each stage adjusts the signal's confidence up or down. The composite
    pipeline_score (0-100) determines whether the signal passes (>= min_score).

    Usage:
        pipeline = UnifiedConfluencePipeline()
        enhanced_signals = pipeline.filter_signals(raw_signals, data)
    """

    def __init__(self, min_score: float = 55.0):
        # HEDGE FUND SPRINT (2026-03-25): Raised from 50 to 55.
        # Score 40-59 range empirically shows 6.2% WR (inverted signal).
        # 55+ is the quality gate that filters low-confidence noise.
        self.min_score = min_score

    def filter_signals(self, signals: list[dict],
                       data: dict[str, pd.DataFrame]) -> list[dict]:
        """
        Filter and enhance a list of signals through the pipeline.

        Args:
            signals: List of signal dicts (must have 'symbol' and 'direction' keys).
            data: Dict mapping symbol -> OHLCV DataFrame.

        Returns:
            List of enhanced signal dicts that passed the pipeline (score >= min_score).
            Each signal gets pipeline_score, pipeline_passed, confidence, pipeline_stages added.
        """
        enhanced: list[dict] = []

        for signal in signals:
            symbol = signal.get("symbol", "")
            df = data.get(symbol)

            if df is None or len(df) < 60:
                # Not enough data to run pipeline -- pass through with neutral score
                signal_copy = dict(signal)
                signal_copy["pipeline_score"] = 50.0
                signal_copy["pipeline_passed"] = True
                signal_copy["pipeline_stages"] = {"note": "insufficient_data_for_pipeline"}
                enhanced.append(signal_copy)
                continue

            try:
                scored = self._score_signal(signal, df)
                if scored["pipeline_passed"]:
                    enhanced.append(scored)
                else:
                    logger.debug(
                        "Signal filtered out: %s %s (score=%.1f < %.1f)",
                        symbol, signal.get("direction", "?"),
                        scored["pipeline_score"], self.min_score,
                    )
            except Exception as exc:
                logger.warning("Pipeline error for %s: %s", symbol, exc)
                # On error, pass through unchanged
                signal_copy = dict(signal)
                signal_copy["pipeline_score"] = 50.0
                signal_copy["pipeline_passed"] = True
                signal_copy["pipeline_stages"] = {"error": str(exc)}
                enhanced.append(signal_copy)

        return enhanced

    def _score_signal(self, signal: dict, df: pd.DataFrame) -> dict:
        """
        Score a single signal through all 5 stages.

        Returns a new dict with the original signal fields plus:
          - pipeline_score: 0-100 composite score
          - pipeline_passed: True if score >= min_score
          - confidence: adjusted confidence after all stages
          - pipeline_stages: dict with each stage's contribution and detail
        """
        direction = signal.get("direction", "BUY").upper()
        base_confidence = signal.get("confidence", 0.60)

        stages: dict[str, dict] = {}
        confidence = base_confidence

        # Stage 1: Regime alignment
        regime_adj, regime_detail = self._regime_score(df, direction)
        confidence += regime_adj
        stages["regime"] = {
            "adjustment": regime_adj,
            "detail": regime_detail,
            "raw_score": _regime_to_raw(regime_detail, direction),
        }

        # Stage 2: SMC confluence
        smc_adj, smc_detail = self._smc_score(df)
        confidence += smc_adj
        stages["smc"] = {
            "adjustment": smc_adj,
            "detail": smc_detail,
        }

        # Stage 3: Entropy
        entropy_adj, entropy_detail = self._entropy_score(df)
        confidence += entropy_adj
        stages["entropy"] = {
            "adjustment": entropy_adj,
            "detail": entropy_detail,
        }

        # Stage 4: Volume confirmation
        vol_adj, vol_detail = self._volume_score(df)
        confidence += vol_adj
        stages["volume"] = {
            "adjustment": vol_adj,
            "detail": vol_detail,
        }

        # Stage 5: MTF trend alignment
        trend_adj, trend_detail = self._trend_alignment_score(df, direction)
        confidence += trend_adj
        stages["trend"] = {
            "adjustment": trend_adj,
            "detail": trend_detail,
        }

        # Clamp confidence to [0.10, 0.95]
        confidence = round(max(0.10, min(0.95, confidence)), 4)

        # Composite pipeline score (0-100) from stage contributions
        # Each stage maps its adjustment to a 0-100 sub-score, then weighted
        pipeline_score = self._compute_composite(stages)
        pipeline_passed = pipeline_score >= self.min_score

        result = dict(signal)
        result["pipeline_score"] = round(pipeline_score, 2)
        result["pipeline_passed"] = pipeline_passed
        result["confidence"] = confidence
        result["pipeline_stages"] = stages
        return result

    def _regime_score(self, df: pd.DataFrame, direction: str) -> tuple[float, str]:
        """
        Stage 1: Regime alignment score.

        Uses HMM-inspired 3-state classifier. Penalizes counter-regime signals:
          - BEAR regime + BUY direction -> -0.30 confidence
          - CHOP regime + any direction -> -0.15 confidence
          - BULL regime + BUY direction -> +0.00 (neutral, already aligned)
          - BEAR regime + SELL direction -> +0.00 (aligned)
        """
        close = df["Close"]
        high, low = df["High"], df["Low"]

        if len(close) < 120:
            return 0.0, "insufficient_bars"

        try:
            regimes = _classify_regimes(close, high, low, lookback=100)
            recent = regimes.dropna().tail(5)
            if len(recent) == 0:
                return 0.0, "no_regime_data"

            current_regime = int(recent.iloc[-1])
            regime_name = _REGIME_NAMES.get(current_regime, "UNKNOWN")

            is_buy = direction in ("BUY", "LONG")

            if current_regime == _REGIME_BEAR and is_buy:
                return -0.30, f"BEAR_counter_buy"
            elif current_regime == _REGIME_BULL and not is_buy:
                return -0.30, f"BULL_counter_sell"
            elif current_regime == _REGIME_CHOP:
                return -0.15, f"CHOP_uncertain"
            else:
                # Aligned: BULL+BUY or BEAR+SELL
                return 0.0, f"{regime_name}_aligned"

        except Exception as exc:
            logger.debug("Regime classification error: %s", exc)
            return 0.0, f"error:{exc}"

    def _smc_score(self, df: pd.DataFrame) -> tuple[float, str]:
        """
        Stage 2: SMC confluence score.

        Calculates the 5-component Smart Money Concepts composite.
          - Score < 40 -> skip signal (return large negative adjustment)
          - Score > 70 -> boost confidence by +0.15
          - Score 40-70 -> neutral (no adjustment)
        """
        try:
            composite, detail = _compute_smc_composite(df)

            if composite < 40:
                return -0.50, f"smc_weak({composite:.0f}): {detail}"
            elif composite > 70:
                return 0.15, f"smc_strong({composite:.0f}): {detail}"
            else:
                return 0.0, f"smc_neutral({composite:.0f}): {detail}"

        except Exception as exc:
            logger.debug("SMC score error: %s", exc)
            return 0.0, f"error:{exc}"

    def _entropy_score(self, df: pd.DataFrame) -> tuple[float, str]:
        """
        Stage 3: Entropy regime score.

        Calculates Shannon entropy of recent returns. Low entropy means the
        market has "decided" on a direction -- breakout is more likely to follow through.

          - Entropy < SMA - 1.5*std -> boost +0.10 (market is decided)
          - Entropy > SMA + 1.5*std -> reduce -0.05 (high noise/randomness)
          - Otherwise -> neutral
        """
        close = df["Close"]
        if len(close) < 120:
            return 0.0, "insufficient_bars"

        try:
            log_ret = np.log(close / close.shift(1))
            entropy = _rolling_entropy(log_ret, window=50, n_bins=10)

            entropy_sma_val = entropy.rolling(50, min_periods=20).mean()
            entropy_std_val = entropy.rolling(50, min_periods=20).std()

            h_curr = entropy.iloc[-1]
            h_sma = entropy_sma_val.iloc[-1]
            h_std = entropy_std_val.iloc[-1]

            if pd.isna(h_curr) or pd.isna(h_sma) or pd.isna(h_std) or h_std == 0:
                return 0.0, "entropy_na"

            low_threshold = h_sma - 1.5 * h_std
            high_threshold = h_sma + 1.5 * h_std

            if h_curr < low_threshold:
                drop_mag = (low_threshold - h_curr) / h_std
                return 0.10, f"low_entropy({h_curr:.3f}<{low_threshold:.3f}, drop={drop_mag:.1f}std)"
            elif h_curr > high_threshold:
                return -0.05, f"high_entropy({h_curr:.3f}>{high_threshold:.3f})"
            else:
                return 0.0, f"normal_entropy({h_curr:.3f})"

        except Exception as exc:
            logger.debug("Entropy score error: %s", exc)
            return 0.0, f"error:{exc}"

    def _volume_score(self, df: pd.DataFrame) -> tuple[float, str]:
        """
        Stage 4: Volume confirmation score.

        Checks current volume relative to 20-period average:
          - Volume > 1.5x average -> boost +0.05 (strong participation)
          - Volume < 0.5x average -> reduce -0.10 (weak conviction)
          - Otherwise -> neutral
        """
        vol = df.get("Volume")
        if vol is None or len(vol) < 21:
            return 0.0, "no_volume_data"

        try:
            vr = volume_ratio(vol, 20)
            vr_curr = float(vr.iloc[-1])

            if pd.isna(vr_curr):
                return 0.0, "volume_ratio_na"

            if vr_curr > 1.5:
                return 0.05, f"high_volume({vr_curr:.2f}x)"
            elif vr_curr < 0.5:
                return -0.10, f"low_volume({vr_curr:.2f}x)"
            else:
                return 0.0, f"normal_volume({vr_curr:.2f}x)"

        except Exception as exc:
            logger.debug("Volume score error: %s", exc)
            return 0.0, f"error:{exc}"

    def _trend_alignment_score(self, df: pd.DataFrame, direction: str) -> tuple[float, str]:
        """
        Stage 5: Multi-timeframe trend alignment.

        Checks EMA(9) > EMA(21) > EMA(50) alignment relative to signal direction:
          - Full alignment with direction -> boost +0.10
          - Counter-trend (full alignment against) -> reduce -0.20
          - Partial alignment -> neutral
        """
        close = df["Close"]
        if len(close) < 50:
            return 0.0, "insufficient_bars"

        try:
            ema9 = float(ema(close, 9).iloc[-1])
            ema21 = float(ema(close, 21).iloc[-1])
            ema50 = float(ema(close, 50).iloc[-1])

            bullish_aligned = ema9 > ema21 > ema50
            bearish_aligned = ema9 < ema21 < ema50

            is_buy = direction in ("BUY", "LONG")

            if is_buy and bullish_aligned:
                return 0.10, f"bullish_aligned(EMA9={ema9:.2f}>EMA21={ema21:.2f}>EMA50={ema50:.2f})"
            elif not is_buy and bearish_aligned:
                return 0.10, f"bearish_aligned(EMA9={ema9:.2f}<EMA21={ema21:.2f}<EMA50={ema50:.2f})"
            elif is_buy and bearish_aligned:
                return -0.20, f"counter_trend_buy(bearish_stack)"
            elif not is_buy and bullish_aligned:
                return -0.20, f"counter_trend_sell(bullish_stack)"
            else:
                return 0.0, f"mixed_trend(EMA9={ema9:.2f},EMA21={ema21:.2f},EMA50={ema50:.2f})"

        except Exception as exc:
            logger.debug("Trend alignment error: %s", exc)
            return 0.0, f"error:{exc}"

    def _compute_composite(self, stages: dict[str, dict]) -> float:
        """
        Compute weighted composite score (0-100) from stage results.

        Maps each stage's confidence adjustment to a 0-100 sub-score:
          - Large positive adj (+0.15) -> ~85
          - Neutral (0.0) -> 60 (baseline pass)
          - Large negative adj (-0.30) -> ~15

        Then applies stage weights to get final composite.
        """
        # Mapping: adjustment -> sub-score
        # Range of adjustments is roughly [-0.50, +0.15]
        # We map linearly: -0.50 -> 0, 0.0 -> 60, +0.15 -> 90
        sub_scores = {}
        for stage_name, stage_data in stages.items():
            adj = stage_data.get("adjustment", 0.0)
            # Linear map: score = 60 + adj * 200 (clamped to [0, 100])
            sub = 60.0 + adj * 200.0
            sub_scores[stage_name] = max(0.0, min(100.0, sub))

        # Weighted composite
        composite = 0.0
        for stage_name, weight in _STAGE_WEIGHTS.items():
            composite += sub_scores.get(stage_name, 60.0) * weight

        return composite


def _regime_to_raw(detail: str, direction: str) -> float:
    """Convert regime detail string to a raw 0-100 score for display."""
    if "aligned" in detail:
        return 80.0
    elif "CHOP" in detail:
        return 40.0
    elif "counter" in detail:
        return 10.0
    return 60.0


# =====================================================================
# Convenience function
# =====================================================================

def filter_signals_through_pipeline(
    signals: list[dict],
    data: dict[str, pd.DataFrame],
    min_score: float = 50.0,
) -> list[dict]:
    """
    Convenience function to filter signals through the unified pipeline.

    Args:
        signals: List of signal dicts from any strategy.
        data: Dict mapping symbol -> OHLCV DataFrame.
        min_score: Minimum pipeline score to pass (default 50.0).

    Returns:
        List of enhanced signal dicts that passed the pipeline.
    """
    pipeline = UnifiedConfluencePipeline(min_score=min_score)
    return pipeline.filter_signals(signals, data)


# =====================================================================
# Standalone test
# =====================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

    # Generate synthetic test data
    np.random.seed(42)
    n_bars = 200
    dates = pd.date_range("2025-01-01", periods=n_bars, freq="1h")

    # Trending-up synthetic data
    base_price = 50000.0
    returns = np.random.normal(0.001, 0.02, n_bars)
    prices = base_price * np.cumprod(1 + returns)

    df = pd.DataFrame({
        "Open": prices * (1 + np.random.uniform(-0.005, 0.005, n_bars)),
        "High": prices * (1 + np.abs(np.random.normal(0, 0.01, n_bars))),
        "Low": prices * (1 - np.abs(np.random.normal(0, 0.01, n_bars))),
        "Close": prices,
        "Volume": np.random.uniform(100, 1000, n_bars),
    }, index=dates)

    test_signals = [
        {
            "strategy": "test_strategy",
            "symbol": "BTCUSDT",
            "direction": "BUY",
            "confidence": 0.65,
            "entry": float(prices[-1]),
        },
        {
            "strategy": "test_strategy",
            "symbol": "BTCUSDT",
            "direction": "SELL",
            "confidence": 0.60,
            "entry": float(prices[-1]),
        },
    ]

    test_data = {"BTCUSDT": df}

    print("=" * 70)
    print("  UNIFIED CONFLUENCE PIPELINE TEST")
    print("=" * 70)

    pipeline = UnifiedConfluencePipeline(min_score=40.0)
    results = pipeline.filter_signals(test_signals, test_data)

    for r in results:
        print(f"\n  {r['symbol']} {r['direction']}")
        print(f"  Pipeline Score: {r['pipeline_score']:.1f}")
        print(f"  Passed: {r['pipeline_passed']}")
        print(f"  Confidence: {r.get('confidence', '?')}")
        print(f"  Stages:")
        for stage_name, stage_data in r["pipeline_stages"].items():
            adj = stage_data.get("adjustment", "?")
            detail = stage_data.get("detail", "?")
            print(f"    {stage_name:>10}: adj={adj:+.2f}  | {detail}")

    print(f"\n{'=' * 70}")
    print(f"  {len(results)}/{len(test_signals)} signals passed pipeline")
    print(f"{'=' * 70}")
