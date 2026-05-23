"""
ALPHA_ENGINE -- Regime-Specialist Strategy Router
===================================================
Two layers of regime routing:

LAYER 1 -- Composite Market Regime (stdlib-only, JSON-based)
  Combines regime_report.json + Fear & Greed + Hurst to produce a
  market-wide composite: RISK_ON / RISK_OFF / NEUTRAL / VOLATILE.
  Maps each strategy *family* (from config.STRATEGY_FAMILIES) to a
  sizing_multiplier boost/penalty [0.3, 1.5].
  Applied in production_scanner.py AFTER feature population, BEFORE quality gates.

LAYER 2 -- 2D Per-Symbol Regime Matrix (pandas/numpy, OHLCV-based)
  Classifies each symbol on two axes (trend + volatility) into a 3x3
  matrix (BULL/BEAR/NEUTRAL x EXPANSION/COMPRESSION/NORMAL).
  Maps each strategy *type* to recommended regime cells.
  Used by scanner.py for per-symbol signal filtering.

References:
  - Hamilton (1989): Markov-switching models for regime detection
  - Ang & Bekaert (2002): Regime switches in interest rates
  - Bollinger (2001): Squeeze detection via BB inside Keltner
  - Wilder (1978): ATR-based volatility measurement
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Layer 2 dependencies (pandas/numpy/indicators) -- deferred import
# Layer 1 functions (detect_current_regime, apply_regime_routing) are stdlib-only.
# Layer 2 (RegimeRouter class) requires numpy + pandas + indicators.
try:
    import numpy as np
    import pandas as pd
    from indicators import (
        rsi, ema, sma, atr, adx, bollinger_bands, keltner_channels,
        bollinger_squeeze, macd,
    )
    _HAS_LAYER2_DEPS = True
except ImportError:
    np = None  # type: ignore[assignment]
    pd = None  # type: ignore[assignment]
    _HAS_LAYER2_DEPS = False

# ---------------------------------------------------------------------------
# Paths (Layer 1)
# ---------------------------------------------------------------------------
_ENGINE_DIR = Path(__file__).resolve().parent
_DATA_DIR = _ENGINE_DIR / "data"
_REGIME_REPORT_PATH = _DATA_DIR / "regime_report.json"

# ---------------------------------------------------------------------------
# Composite regime constants (Layer 1)
# ---------------------------------------------------------------------------
RISK_ON = "RISK_ON"
RISK_OFF = "RISK_OFF"
COMPOSITE_NEUTRAL = "NEUTRAL"     # prefixed to avoid clash with per-symbol "NEUTRAL"
COMPOSITE_VOLATILE = "VOLATILE"

# ---------------------------------------------------------------------------
# Strategy family -> regime affinity mapping (Layer 1)
# ---------------------------------------------------------------------------
# Families from config.STRATEGY_FAMILIES values:
#   trend, momentum, sentiment, structure, volume, volatility,
#   on_chain, carry

FAMILY_REGIME_AFFINITY: dict[str, dict[str, Any]] = {
    "trend": {
        "best_regime": RISK_ON,
        "worst_regime": RISK_OFF,
        "neutral_performance": 1.0,
        "description": "Trend-following works in persistent directional markets",
    },
    "momentum": {
        "best_regime": RISK_ON,
        "worst_regime": COMPOSITE_NEUTRAL,
        "neutral_performance": 0.9,
        "description": "Momentum thrives in bull markets with strong trends",
    },
    "sentiment": {
        "best_regime": RISK_OFF,
        "worst_regime": COMPOSITE_NEUTRAL,
        "neutral_performance": 0.85,
        "description": "Sentiment-contrarian signals strongest at fear/greed extremes",
    },
    "structure": {
        "best_regime": COMPOSITE_VOLATILE,
        "worst_regime": RISK_ON,
        "neutral_performance": 1.0,
        "description": "Market structure (SFP, BOS) works in volatile/ranging markets",
    },
    "volume": {
        "best_regime": COMPOSITE_VOLATILE,
        "worst_regime": COMPOSITE_NEUTRAL,
        "neutral_performance": 0.95,
        "description": "Volume signals strongest during high-activity regimes",
    },
    "volatility": {
        "best_regime": COMPOSITE_VOLATILE,
        "worst_regime": RISK_ON,
        "neutral_performance": 1.0,
        "description": "Mean-reversion and squeeze strategies need volatility",
    },
    "on_chain": {
        "best_regime": RISK_OFF,
        "worst_regime": RISK_ON,
        "neutral_performance": 0.9,
        "description": "On-chain metrics best at cycle extremes (accumulation zones)",
    },
    "carry": {
        "best_regime": COMPOSITE_NEUTRAL,
        "worst_regime": COMPOSITE_VOLATILE,
        "neutral_performance": 1.1,
        "description": "Carry/basis trades need stable funding rate differentials",
    },
}

# ---------------------------------------------------------------------------
# Regime boost matrix (Layer 1): (family, composite_regime) -> multiplier
# Range: [0.3, 1.5]
# ---------------------------------------------------------------------------
_FAMILY_BOOST_MATRIX: dict[tuple[str, str], float] = {
    # -- trend family --
    ("trend", RISK_ON):            1.4,
    ("trend", COMPOSITE_NEUTRAL):  1.0,
    ("trend", COMPOSITE_VOLATILE): 0.8,
    ("trend", RISK_OFF):           0.5,

    # -- momentum family --
    ("momentum", RISK_ON):            1.5,
    ("momentum", COMPOSITE_NEUTRAL):  0.8,
    ("momentum", COMPOSITE_VOLATILE): 0.9,
    ("momentum", RISK_OFF):           0.4,

    # -- sentiment family (contrarian -- loves extremes) --
    ("sentiment", RISK_OFF):           1.4,
    ("sentiment", RISK_ON):            0.7,
    ("sentiment", COMPOSITE_VOLATILE): 1.2,
    ("sentiment", COMPOSITE_NEUTRAL):  0.7,

    # -- structure family --
    ("structure", COMPOSITE_VOLATILE): 1.3,
    ("structure", RISK_OFF):           1.1,
    ("structure", COMPOSITE_NEUTRAL):  1.0,
    ("structure", RISK_ON):            0.7,

    # -- volume family --
    ("volume", COMPOSITE_VOLATILE): 1.3,
    ("volume", RISK_ON):            1.1,
    ("volume", RISK_OFF):           0.9,
    ("volume", COMPOSITE_NEUTRAL):  0.7,

    # -- volatility family (mean-reversion, squeezes) --
    ("volatility", COMPOSITE_VOLATILE): 1.4,
    ("volatility", RISK_OFF):           1.1,
    ("volatility", COMPOSITE_NEUTRAL):  0.9,
    ("volatility", RISK_ON):            0.6,

    # -- on_chain family --
    ("on_chain", RISK_OFF):           1.3,
    ("on_chain", COMPOSITE_NEUTRAL):  1.0,
    ("on_chain", COMPOSITE_VOLATILE): 1.0,
    ("on_chain", RISK_ON):            0.7,

    # -- carry family --
    ("carry", COMPOSITE_NEUTRAL):  1.3,
    ("carry", RISK_ON):            1.0,
    ("carry", RISK_OFF):           0.7,
    ("carry", COMPOSITE_VOLATILE): 0.3,
}


# ===================================================================
# LAYER 1 -- Composite Market Regime (stdlib-only, production_scanner)
# ===================================================================

def _load_regime_report() -> dict | None:
    """Load regime_report.json from data directory."""
    try:
        if _REGIME_REPORT_PATH.exists():
            with open(_REGIME_REPORT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _load_strategy_families() -> dict[str, str]:
    """Load STRATEGY_FAMILIES from config.py with graceful fallback."""
    try:
        from config import STRATEGY_FAMILIES
        return STRATEGY_FAMILIES
    except ImportError:
        pass
    try:
        from alpha_engine.config import STRATEGY_FAMILIES
        return STRATEGY_FAMILIES
    except ImportError:
        pass
    return {}


def detect_current_regime(market_ctx: dict | None = None) -> dict[str, Any]:
    """Detect composite market regime from multiple signals.

    Sources:
      - regime_report.json: BTC macro regime (BULLISH/BEARISH/NEUTRAL)
      - market_ctx['fear_greed']: Fear & Greed Index
      - regime_report volatility_pct and ADX

    Returns:
        {
            "regime": RISK_ON | RISK_OFF | NEUTRAL | VOLATILE,
            "confidence": float [0, 1],
            "components": {
                "btc_regime": str,
                "fear_greed_value": int | None,
                "fear_greed_label": str | None,
                "volatility_pct": float | None,
                "rsi": float | None,
                "adx": float | None,
                "fast_regime": str | None,
            },
            "votes": dict,
            "timestamp": str (ISO),
        }
    """
    market_ctx = market_ctx or {}

    # -- Component 1: BTC macro regime from regime_report.json --
    btc_regime = "NEUTRAL"
    volatility_pct = None
    rsi_val = None
    adx_val = None
    report = _load_regime_report()
    if report:
        btc_regime = (report.get("regime") or report.get("regime_raw") or "NEUTRAL").upper()
        volatility_pct = report.get("volatility_pct")
        rsi_val = report.get("rsi_4h") or report.get("btc_rsi")
        adx_val = report.get("adx")

    # -- Component 2: Fear & Greed --
    fg = market_ctx.get("fear_greed") or {}
    fg_value = fg.get("value") if isinstance(fg, dict) else None
    fg_label = fg.get("label") if isinstance(fg, dict) else None

    # -- Component 3: Fast regime --
    fast_regime = (market_ctx.get("fast_regime") or "").upper()

    # -- Scoring: map each component to a regime vote --
    votes: dict[str, float] = {
        RISK_ON: 0.0,
        RISK_OFF: 0.0,
        COMPOSITE_NEUTRAL: 0.0,
        COMPOSITE_VOLATILE: 0.0,
    }

    # BTC regime vote (weight: 0.35)
    if btc_regime in ("BULLISH", "STRONG_BULL"):
        votes[RISK_ON] += 0.35
    elif btc_regime in ("BEARISH", "STRONG_BEAR"):
        votes[RISK_OFF] += 0.35
    elif btc_regime == "VOLATILE":
        votes[COMPOSITE_VOLATILE] += 0.35
    else:
        votes[COMPOSITE_NEUTRAL] += 0.35

    # Fear & Greed vote (weight: 0.30)
    if fg_value is not None:
        try:
            fgv = int(fg_value)
        except (TypeError, ValueError):
            fgv = 50
        if fgv >= 75:
            votes[RISK_ON] += 0.30
        elif fgv >= 55:
            votes[RISK_ON] += 0.15
            votes[COMPOSITE_NEUTRAL] += 0.15
        elif fgv <= 25:
            votes[RISK_OFF] += 0.30
        elif fgv <= 45:
            votes[RISK_OFF] += 0.15
            votes[COMPOSITE_NEUTRAL] += 0.15
        else:
            votes[COMPOSITE_NEUTRAL] += 0.30
    else:
        votes[COMPOSITE_NEUTRAL] += 0.15
        if btc_regime in ("BULLISH", "STRONG_BULL"):
            votes[RISK_ON] += 0.15
        elif btc_regime in ("BEARISH", "STRONG_BEAR"):
            votes[RISK_OFF] += 0.15
        else:
            votes[COMPOSITE_NEUTRAL] += 0.15

    # Volatility vote (weight: 0.20)
    if volatility_pct is not None:
        try:
            vol = float(volatility_pct)
        except (TypeError, ValueError):
            vol = 1.5
        if vol > 3.0:
            votes[COMPOSITE_VOLATILE] += 0.20
        elif vol > 2.0:
            votes[COMPOSITE_VOLATILE] += 0.10
            votes[COMPOSITE_NEUTRAL] += 0.10
        else:
            votes[COMPOSITE_NEUTRAL] += 0.10
            if btc_regime in ("BULLISH", "STRONG_BULL"):
                votes[RISK_ON] += 0.10
            elif btc_regime in ("BEARISH", "STRONG_BEAR"):
                votes[RISK_OFF] += 0.10
            else:
                votes[COMPOSITE_NEUTRAL] += 0.10
    else:
        votes[COMPOSITE_NEUTRAL] += 0.20

    # ADX tiebreaker (weight: 0.15)
    if adx_val is not None:
        try:
            adx_f = float(adx_val)
        except (TypeError, ValueError):
            adx_f = 20.0
        if adx_f > 40:
            if btc_regime in ("BULLISH", "STRONG_BULL"):
                votes[RISK_ON] += 0.15
            elif btc_regime in ("BEARISH", "STRONG_BEAR"):
                votes[RISK_OFF] += 0.15
            else:
                votes[COMPOSITE_VOLATILE] += 0.15
        elif adx_f > 25:
            if btc_regime in ("BULLISH", "STRONG_BULL"):
                votes[RISK_ON] += 0.10
                votes[COMPOSITE_NEUTRAL] += 0.05
            elif btc_regime in ("BEARISH", "STRONG_BEAR"):
                votes[RISK_OFF] += 0.10
                votes[COMPOSITE_NEUTRAL] += 0.05
            else:
                votes[COMPOSITE_NEUTRAL] += 0.15
        else:
            votes[COMPOSITE_NEUTRAL] += 0.10
            votes[COMPOSITE_VOLATILE] += 0.05
    else:
        votes[COMPOSITE_NEUTRAL] += 0.15

    # -- Determine winner --
    composite = max(votes, key=lambda k: votes[k])
    total_weight = sum(votes.values())
    confidence = votes[composite] / total_weight if total_weight > 0 else 0.0

    return {
        "regime": composite,
        "confidence": round(confidence, 4),
        "components": {
            "btc_regime": btc_regime,
            "fear_greed_value": fg_value,
            "fear_greed_label": fg_label,
            "volatility_pct": volatility_pct,
            "rsi": rsi_val,
            "adx": adx_val,
            "fast_regime": fast_regime or None,
        },
        "votes": {k: round(v, 4) for k, v in votes.items()},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_strategy_regime_affinity() -> dict[str, dict[str, Any]]:
    """Return the regime affinity map for all strategy families.

    Returns:
        {family: {best_regime, worst_regime, neutral_performance, description}}
    """
    return dict(FAMILY_REGIME_AFFINITY)


def compute_regime_boost(strategy_family: str, current_regime: str) -> float:
    """Compute sizing multiplier boost/penalty for a strategy in current regime.

    Args:
        strategy_family: One of: trend, momentum, sentiment, structure,
                        volume, volatility, on_chain, carry
        current_regime: One of: RISK_ON, RISK_OFF, NEUTRAL, VOLATILE

    Returns:
        Multiplier in [0.3, 1.5].
    """
    family = strategy_family.lower().strip()
    regime = current_regime.upper().strip()

    key = (family, regime)
    if key in _FAMILY_BOOST_MATRIX:
        return _FAMILY_BOOST_MATRIX[key]

    return 1.0


def apply_regime_routing(
    picks: list[dict],
    market_ctx: dict | None = None,
    strategy_families: dict[str, str] | None = None,
) -> list[dict]:
    """Apply regime-based sizing boost/penalty to all picks.

    For each pick:
      1. Look up its strategy family from STRATEGY_FAMILIES
      2. Compute regime boost based on family-regime alignment
      3. Apply to sizing_multiplier (NOT confidence -- per C1 fix)
      4. Tag with regime_alignment metadata for dashboard

    Args:
        picks: List of pick dicts (must have 'strategy' key).
        market_ctx: Market context dict (passed to detect_current_regime).
        strategy_families: Strategy->family mapping (defaults to config.STRATEGY_FAMILIES).

    Returns:
        The same picks list, mutated with regime routing metadata.
    """
    if not picks:
        return picks

    if strategy_families is None:
        strategy_families = _load_strategy_families()

    regime_info = detect_current_regime(market_ctx)
    current_regime = regime_info["regime"]
    regime_confidence = regime_info["confidence"]

    boosted = 0
    penalized = 0
    unchanged = 0

    for pick in picks:
        strategy_name = pick.get("strategy", "")
        family = strategy_families.get(strategy_name, "unknown")

        raw_boost = compute_regime_boost(family, current_regime)

        # Scale boost by regime confidence -- low confidence dampens toward 1.0
        if regime_confidence < 0.5:
            dampen_factor = regime_confidence / 0.5
            effective_boost = 1.0 + (raw_boost - 1.0) * dampen_factor
        else:
            effective_boost = raw_boost

        effective_boost = max(0.3, min(1.5, effective_boost))

        # C1 fix: apply to sizing_multiplier, never confidence
        existing_mult = float(pick.get("sizing_multiplier", 1.0) or 1.0)
        new_mult = round(existing_mult * effective_boost, 4)
        new_mult = max(0.1, min(2.0, new_mult))
        pick["sizing_multiplier"] = new_mult

        # Tag with regime metadata for dashboard
        pick["regime_alignment"] = round(effective_boost, 4)
        pick["regime_current"] = current_regime
        pick["regime_family"] = family
        pick["regime_confidence"] = regime_confidence

        if effective_boost >= 1.2:
            pick["regime_alignment_label"] = "STRONG_MATCH"
            boosted += 1
        elif effective_boost >= 0.9:
            pick["regime_alignment_label"] = "NEUTRAL"
            unchanged += 1
        else:
            pick["regime_alignment_label"] = "MISMATCH"
            penalized += 1

    print(f"  [REGIME ROUTER] Regime={current_regime} (confidence={regime_confidence:.2f})")
    print(f"  [REGIME ROUTER] Boosted={boosted}, Neutral={unchanged}, "
          f"Penalized={penalized} / {len(picks)} picks")
    if regime_info.get("components"):
        comps = regime_info["components"]
        print(f"  [REGIME ROUTER] Components: BTC={comps.get('btc_regime')}, "
              f"F&G={comps.get('fear_greed_value')}, "
              f"Vol={comps.get('volatility_pct')}, ADX={comps.get('adx')}")

    return picks


# ===================================================================
# LAYER 2 -- 2D Per-Symbol Regime Matrix (requires pandas/numpy)
# ===================================================================

# ---------------------------------------------------------------------------
# Strategy type classification
# ---------------------------------------------------------------------------

STRATEGY_TYPES: dict[str, str] = {
    # Trend following
    "alpha_trend": "trend_following",
    "multi_timeframe_ema_stack": "trend_following",
    "adaptive_supertrend": "trend_following",
    "pentoshi_htf_structure": "trend_following",

    # Momentum
    "wavetrend_oscillator": "momentum",
    "true_strength_index": "momentum",
    "rsi_macd_confluence": "momentum",
    "cross_sectional_momentum": "momentum",

    # Mean reversion
    "nadaraya_watson_envelope": "mean_reversion",
    "vwap_sd_mean_reversion": "mean_reversion",
    "stochastic_momentum_index": "mean_reversion",
    "connors_rsi2": "mean_reversion",

    # Bottom detection
    "williams_vix_fix": "bottom_detection",
    "liquidation_cascade_bottom": "bottom_detection",
    "fear_greed_extreme_dca": "bottom_detection",
    "cryptopanic_news_sentiment": "bottom_detection",
    "sopr_dip_buy_proxy": "bottom_detection",

    # Breakout
    "ttm_squeeze": "breakout",
    "entropy_regime_breakout": "breakout",
    "atr_volatility_breakout": "breakout",

    # Smart money
    "smc_confluence_score": "smart_money",
    "ict_three_chain": "smart_money",
    "volume_delta_divergence": "smart_money",
    "swing_failure_pattern": "smart_money",
    "break_of_structure": "smart_money",
    "whale_accumulation_detector": "smart_money",

    # On-chain
    "mvrv_sma_proxy": "on_chain",
    "hash_ribbon_buy": "on_chain",
    "nvt_overvaluation": "on_chain",
    "onchain_composite_score": "on_chain",
    "hayes_liquidity_index": "on_chain",

    # ML / Classification
    "lorentzian_classification": "ml_classification",

    # Regime (self-referential -- always allowed)
    "hmm_regime_filter": "regime",

    # Carry / Arbitrage
    "funding_rate_carry": "carry",
    "funding_rate_arbitrage": "carry",
    "cross_exchange_basis_carry": "carry",
    "oi_funding_squeeze": "carry",

    # Cointegration Pairs (mean reversion on spread)
    "cointegration_pair_zscore": "mean_reversion",
    "cointegration_half_life_trade": "mean_reversion",

    # Candlestick Patterns (reversal detection)
    "hammer_reversal": "mean_reversion",
    "engulfing_reversal": "mean_reversion",
    "doji_reversal": "mean_reversion",
    "morning_evening_star": "bottom_detection",
    "three_white_soldiers_black_crows": "momentum",

    # Hoffman Strategy (trend following)
    "hoffman_inventory_retracement": "trend_following",
    "hoffman_continuation": "trend_following",

    # Session Breakout (intraday momentum)
    "london_session_breakout": "breakout",
    "ny_session_breakout": "breakout",
    "asian_session_breakout": "breakout",

    # Range Breakout (consolidation breakout)
    "consolidation_range_breakout": "breakout",
    "volatility_contraction_breakout": "breakout",
    "opening_range_breakout": "breakout",

    # Hybrid Confluence (multi-indicator confluence)
    "hurst_volume_profile_confluence": "mean_reversion",
    "adaptive_hurst_markov_gated": "mean_reversion",
    "multi_sigma_ema_stack": "mean_reversion",
    "cross_system_regime_arbitrage": "momentum",
    "widened_tp_momentum_carry": "momentum",
    "vwap_rsi_confluence": "mean_reversion",
    "hoffman_keltner_expansion": "trend_following",
    "ai_ema_pullback": "trend_following",
    # Antigravity (Google Gemini) strategies
    "ag_vwap_rsi_institutional": "mean_reversion",
    "ag_liquidation_cascade_contrarian": "momentum",
    "ag_regime_sentinel_composite": "regime_filter",
    "ag_rsi_pairs_arbitrage": "mean_reversion",

    # Cross-Sectional Reversal (contrarian -- profits when momentum fails)
    "cross_sectional_reversal": "mean_reversion",
}

# Which strategy types work best in each regime cell
REGIME_STRATEGY_MAP: dict[str, list[str]] = {
    "BULL_EXPANSION":    ["trend_following", "momentum"],
    "BULL_COMPRESSION":  ["breakout"],
    "BULL_NORMAL":       ["trend_following", "momentum", "smart_money"],
    "BEAR_EXPANSION":    ["momentum"],          # overbought sells / short setups
    "BEAR_COMPRESSION":  ["bottom_detection", "mean_reversion"],
    "BEAR_NORMAL":       ["mean_reversion", "smart_money"],
    "NEUTRAL_EXPANSION": ["breakout"],
    "NEUTRAL_COMPRESSION": ["mean_reversion"],
    "NEUTRAL_NORMAL":    [],                    # low-conviction -- reduce exposure
}

# Human-readable descriptions for each regime cell
REGIME_DESCRIPTIONS: dict[str, str] = {
    "BULL_EXPANSION":    "Aggressive trending with expanding volatility -- ride momentum",
    "BULL_COMPRESSION":  "Bullish squeeze building -- anticipate breakout continuation",
    "BULL_NORMAL":       "Steady uptrend with normal volatility -- classic trend following",
    "BEAR_EXPANSION":    "High-volatility selloff -- caution, short setups only",
    "BEAR_COMPRESSION":  "Bearish compression -- watch for capitulation reversal",
    "BEAR_NORMAL":       "Grinding downtrend -- mean reversion and SMC opportunities",
    "NEUTRAL_EXPANSION": "Directionless but volatile -- breakout plays only",
    "NEUTRAL_COMPRESSION": "Dead market -- tight range, mean reversion scalps",
    "NEUTRAL_NORMAL":    "Low-conviction chop -- reduce position size or skip",
}

# Confidence modifiers
_BOOST_ALIGNED = 1.15       # strategy type matches recommended: +15%
_PENALTY_COUNTER = 0.75     # strategy type counter to regime: -25%
_PENALTY_NEUTRAL = 0.85     # NEUTRAL_NORMAL blanket penalty: -15%

# Types that are always allowed regardless of regime
_ALWAYS_ALLOWED = {"regime", "on_chain", "carry"}


# ---------------------------------------------------------------------------
# Trend classification
# ---------------------------------------------------------------------------

def _classify_trend(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    lookback: int = 100,
) -> str:
    """
    Classify trend state using smoothed returns, EMA displacement, momentum.

    Returns: 'BULL', 'BEAR', or 'NEUTRAL'
    """
    if len(close) < lookback:
        return "NEUTRAL"

    # Smoothed log returns (14-bar average)
    log_ret = np.log(close / close.shift(1))
    smoothed_ret = log_ret.rolling(14, min_periods=1).mean()
    current_ret = float(smoothed_ret.iloc[-1]) if not np.isnan(smoothed_ret.iloc[-1]) else 0.0

    # EMA displacement: EMA9 vs EMA21 relative to ATR
    ema9 = ema(close, 9)
    ema21 = ema(close, 21)
    atr_val = atr(high, low, close, 14)
    atr_safe = max(float(atr_val.iloc[-1]), 1e-10)
    displacement = float(ema9.iloc[-1] - ema21.iloc[-1]) / atr_safe

    # RSI momentum
    rsi_val = rsi(close, 14)
    current_rsi = float(rsi_val.iloc[-1]) if not np.isnan(rsi_val.iloc[-1]) else 50.0

    # ADX for trend strength
    adx_val = adx(high, low, close, 14)
    current_adx = float(adx_val.iloc[-1]) if not np.isnan(adx_val.iloc[-1]) else 20.0

    # Scoring
    # Returns score: positive = bullish, negative = bearish
    ret_score = np.clip(current_ret / 0.005, -1.0, 1.0)  # normalize to ~[-1,1]

    # Displacement score
    disp_score = np.clip(displacement / 2.0, -1.0, 1.0)

    # RSI score: map [0,100] to [-1,1]
    rsi_score = (current_rsi - 50.0) / 50.0

    # Composite trend score [-1, 1]
    trend_score = ret_score * 0.30 + disp_score * 0.35 + rsi_score * 0.35

    # ADX gate: if ADX < 20, trend is weak regardless of direction
    if current_adx < 20:
        trend_score *= 0.5  # dampen weak trends

    # Classification thresholds
    if trend_score > 0.15:
        return "BULL"
    elif trend_score < -0.15:
        return "BEAR"
    else:
        return "NEUTRAL"


# ---------------------------------------------------------------------------
# Volatility classification
# ---------------------------------------------------------------------------

def _classify_volatility(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    atr_lookback: int = 100,
    atr_period: int = 14,
) -> str:
    """
    Classify volatility state using ATR percentile rank and Bollinger Squeeze.

    Returns: 'EXPANSION', 'COMPRESSION', or 'NORMAL'
    """
    if len(close) < atr_lookback:
        return "NORMAL"

    # ATR percentile over lookback window
    atr_series = atr(high, low, close, atr_period)
    atr_window = atr_series.iloc[-atr_lookback:]
    current_atr = float(atr_series.iloc[-1])

    if np.isnan(current_atr) or atr_window.isna().all():
        return "NORMAL"

    pct_rank = float((atr_window < current_atr).sum()) / len(atr_window)

    # Bollinger Squeeze detection (BB inside Keltner)
    squeeze = bollinger_squeeze(close, high, low)
    is_squeezed = bool(squeeze.iloc[-1]) if not squeeze.empty else False

    # Bollinger bandwidth trend
    bb = bollinger_bands(close, 20)
    bw = bb["bandwidth"]
    bw_sma = sma(bw, 20)
    bw_expanding = False
    if not bw.empty and not bw_sma.empty:
        curr_bw = float(bw.iloc[-1]) if not np.isnan(bw.iloc[-1]) else 0
        avg_bw = float(bw_sma.iloc[-1]) if not np.isnan(bw_sma.iloc[-1]) else 0
        bw_expanding = curr_bw > avg_bw * 1.2

    # Classification
    if is_squeezed or pct_rank < 0.25:
        return "COMPRESSION"
    elif pct_rank > 0.75 or bw_expanding:
        return "EXPANSION"
    else:
        return "NORMAL"


# ---------------------------------------------------------------------------
# RegimeRouter
# ---------------------------------------------------------------------------

class RegimeRouter:
    """
    2D market regime classifier that routes signals to optimal strategy types.

    Classifies the market on two independent axes:
      - Trend:      BULL / BEAR / NEUTRAL
      - Volatility: EXPANSION / COMPRESSION / NORMAL

    The 3x3 matrix maps each cell to recommended strategy types, with
    confidence modifiers applied to incoming signals.

    Usage:
        router = RegimeRouter()
        regime = router.classify(df)  # Returns regime dict

        # Filter signals by regime
        filtered = router.filter_by_regime(signals, data)

        # Get recommended strategy types
        recommended = router.get_recommended_strategies(df)
    """

    def __init__(
        self,
        trend_lookback: int = 100,
        vol_lookback: int = 100,
        atr_period: int = 14,
        boost_aligned: float = _BOOST_ALIGNED,
        penalty_counter: float = _PENALTY_COUNTER,
        penalty_neutral: float = _PENALTY_NEUTRAL,
    ):
        self.trend_lookback = trend_lookback
        self.vol_lookback = vol_lookback
        self.atr_period = atr_period
        self.boost_aligned = boost_aligned
        self.penalty_counter = penalty_counter
        self.penalty_neutral = penalty_neutral

    # ----- Core classification -----

    def classify(self, df: pd.DataFrame) -> dict:
        """
        Classify market into 2D regime.

        Parameters
        ----------
        df : pd.DataFrame
            OHLCV DataFrame with columns: open, high, low, close, volume.

        Returns
        -------
        dict with keys:
            trend: str              -- 'BULL', 'BEAR', or 'NEUTRAL'
            volatility: str         -- 'EXPANSION', 'COMPRESSION', or 'NORMAL'
            cell: str               -- combined key e.g. 'BULL_EXPANSION'
            recommended_types: list -- strategy types suited for this regime
            confidence_modifier: float -- default modifier for aligned signals
            description: str        -- human-readable regime summary
        """
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        trend = _classify_trend(close, high, low, self.trend_lookback)
        volatility = _classify_volatility(
            close, high, low, self.vol_lookback, self.atr_period
        )

        cell = f"{trend}_{volatility}"
        recommended = REGIME_STRATEGY_MAP.get(cell, [])

        # Default confidence modifier for the cell
        if cell == "NEUTRAL_NORMAL":
            conf_mod = self.penalty_neutral
        elif recommended:
            conf_mod = self.boost_aligned
        else:
            conf_mod = 1.0

        return {
            "trend": trend,
            "volatility": volatility,
            "cell": cell,
            "recommended_types": recommended,
            "confidence_modifier": conf_mod,
            "description": REGIME_DESCRIPTIONS.get(cell, "Unknown regime"),
        }

    # ----- Signal filtering -----

    def filter_by_regime(
        self,
        signals: list[dict],
        data: dict[str, pd.DataFrame],
    ) -> list[dict]:
        """
        Adjust signal confidence based on regime alignment.

        For each signal, classifies the regime of its symbol's data, then:
        - Signals with strategy type matching recommended types: boost confidence
        - Signals with strategy type not in recommended: reduce confidence
        - NEUTRAL_NORMAL regime: blanket reduction on all signals
        - 'regime', 'on_chain', 'carry' types are always allowed (no penalty)

        Parameters
        ----------
        signals : list[dict]
            Each signal dict must have at minimum:
                'strategy': str  -- strategy name
                'confidence': float  -- base confidence (0-100)
                'symbol': str  -- trading symbol
        data : dict[str, pd.DataFrame]
            Map of symbol -> OHLCV DataFrame

        Returns
        -------
        list[dict]
            Signals with adjusted 'confidence' and added 'regime_cell',
            'regime_modifier' fields.
        """
        # Cache regime per symbol to avoid recomputation
        regime_cache: dict[str, dict] = {}
        filtered: list[dict] = []

        for sig in signals:
            symbol = sig.get("symbol", "")
            strategy_name = sig.get("strategy", "")
            base_confidence = float(sig.get("confidence", 50))

            # Get or compute regime for this symbol
            if symbol not in regime_cache:
                df = data.get(symbol)
                if df is not None and len(df) >= 50:
                    regime_cache[symbol] = self.classify(df)
                else:
                    # Not enough data -- neutral assumption
                    regime_cache[symbol] = {
                        "trend": "NEUTRAL",
                        "volatility": "NORMAL",
                        "cell": "NEUTRAL_NORMAL",
                        "recommended_types": [],
                        "confidence_modifier": self.penalty_neutral,
                        "description": REGIME_DESCRIPTIONS["NEUTRAL_NORMAL"],
                    }

            regime = regime_cache[symbol]
            cell = regime["cell"]
            recommended = regime["recommended_types"]
            strategy_type = STRATEGY_TYPES.get(strategy_name, "unknown")

            # Determine confidence modifier
            if strategy_type in _ALWAYS_ALLOWED:
                modifier = 1.0
            elif cell == "NEUTRAL_NORMAL":
                # Blanket penalty for low-conviction environment
                modifier = self.penalty_neutral
            elif strategy_type in recommended:
                modifier = self.boost_aligned
            elif recommended:
                # Recommended types exist but this strategy is not one of them
                modifier = self.penalty_counter
            else:
                modifier = 1.0

            adjusted_confidence = round(
                min(100.0, max(0.0, base_confidence * modifier)), 1
            )

            out = dict(sig)
            out["confidence"] = adjusted_confidence
            out["regime_cell"] = cell
            out["regime_modifier"] = modifier
            out["regime_description"] = regime["description"]
            filtered.append(out)

        return filtered

    # ----- Strategy recommendations -----

    def get_recommended_strategies(self, df: pd.DataFrame) -> list[str]:
        """
        Return list of strategy names best suited for the current regime.

        Parameters
        ----------
        df : pd.DataFrame
            OHLCV DataFrame

        Returns
        -------
        list[str]
            Concrete strategy names (not types) that match the current regime.
        """
        regime = self.classify(df)
        recommended_types = set(regime["recommended_types"])

        if not recommended_types:
            return []

        return [
            name
            for name, stype in STRATEGY_TYPES.items()
            if stype in recommended_types
        ]

    # ----- Utility -----

    def classify_multi(
        self, data: dict[str, pd.DataFrame]
    ) -> dict[str, dict]:
        """
        Classify regimes for multiple symbols at once.

        Parameters
        ----------
        data : dict[str, pd.DataFrame]
            Map of symbol -> OHLCV DataFrame

        Returns
        -------
        dict[str, dict]
            Map of symbol -> regime classification dict
        """
        results: dict[str, dict] = {}
        for symbol, df in data.items():
            if len(df) >= 50:
                results[symbol] = self.classify(df)
            else:
                results[symbol] = {
                    "trend": "NEUTRAL",
                    "volatility": "NORMAL",
                    "cell": "NEUTRAL_NORMAL",
                    "recommended_types": [],
                    "confidence_modifier": self.penalty_neutral,
                    "description": REGIME_DESCRIPTIONS["NEUTRAL_NORMAL"],
                }
        return results

    def summarize(self, df: pd.DataFrame) -> str:
        """One-line regime summary for logging/dashboards."""
        r = self.classify(df)
        types = ", ".join(r["recommended_types"]) if r["recommended_types"] else "none"
        return (
            f"Regime: {r['cell']} (mod={r['confidence_modifier']:.2f}) "
            f"| Recommended: {types} | {r['description']}"
        )
