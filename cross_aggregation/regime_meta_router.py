#!/usr/bin/env python3
"""
Regime Meta-Router — Unified Consensus Regime + Strategy-Level Alignment
========================================================================
Unifies all 5+ regime detectors into a single consensus regime and applies
strategy-level scoring adjustments to picks.

Detectors consumed:
  1. cross_aggregation/regime_router.py     — F&G + EMA + ADX + RSI (binary gate)
  2. regime_terminal/data/regime_state.json  — 7-state GaussianHMM (per-ticker)
  3. ml_battleground/system_b_regime/        — XGBoost 4-state classifier
  4. risk_management/regime_detector.py      — HMM 3-state (CRASH/RANGE/TREND)
  5. regime_terminal/hierarchical_regime.py  — 3-level macro/sector/micro weights

Consensus regimes:
  TRENDING_UP, TRENDING_DOWN, RANGING, HIGH_VOLATILITY, CRASH

Strategy alignment scoring:
  +15% confidence boost for regime-aligned strategies
  -30% confidence penalty for misaligned strategies

Usage:
    from cross_aggregation.regime_meta_router import (
        get_consensus_regime, score_picks_by_regime
    )

    regime = get_consensus_regime()
    scored_picks = score_picks_by_regime(picks, regime)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Repository root ──
REPO_ROOT = Path(__file__).resolve().parent.parent

# ── Import regime detectors with graceful fallbacks ──

# Detector 0 (HIGHEST WEIGHT): Regime Sentinel — 4-state on-chain cycle classifier
_HAS_SENTINEL = False
try:
    sys.path.insert(0, str(REPO_ROOT / "alpha_engine"))
    from regime_sentinel import get_regime_sentinel as _get_sentinel
    _HAS_SENTINEL = True
except ImportError:
    pass

# Detector 1: cross_aggregation regime_router (F&G + EMA + ADX + RSI)
_HAS_REGIME_ROUTER = False
try:
    from cross_aggregation.regime_router import get_current_regime as _get_router_regime
    _HAS_REGIME_ROUTER = True
except ImportError:
    pass

# Detector 5: hierarchical regime (macro/sector/micro)
_HAS_HIERARCHICAL = False
try:
    from regime_terminal.hierarchical_regime import get_regime_weights as _get_hier_weights
    _HAS_HIERARCHICAL = True
except ImportError:
    pass


# ── Regime label normalization ──────────────────────────────────────
# Each detector uses different labels. Normalize them all to our 5 canonical regimes.

# Detector 1: regime_router.py
_ROUTER_REGIME_MAP = {
    "TRENDING_UP":   "TRENDING_UP",
    "TRENDING_DOWN": "TRENDING_DOWN",
    "RANGE_BOUND":   "RANGING",
    "UNKNOWN":       None,  # no vote
}

# Detector 2: regime_terminal (7-state HMM)
_TERMINAL_REGIME_MAP = {
    "Strong Bull":   "TRENDING_UP",
    "Mild Bull":     "TRENDING_UP",
    "Accumulation":  "RANGING",
    "Neutral":       "RANGING",
    "Mild Bear":     "TRENDING_DOWN",
    "Strong Bear":   "TRENDING_DOWN",
    "Crash":         "CRASH",
    "Distribution":  "TRENDING_DOWN",
}

# Detector 3: ml_battleground system_b (XGBoost 4-state)
_SYSTEM_B_REGIME_MAP = {
    "trending_up":     "TRENDING_UP",
    "trending_down":   "TRENDING_DOWN",
    "range_bound":     "RANGING",
    "high_volatility": "HIGH_VOLATILITY",
}

# Detector 4: risk_management HMM (3-state)
_RISK_REGIME_MAP = {
    "CRASH": "CRASH",
    "RANGE": "RANGING",
    "TREND": "TRENDING_UP",  # TREND is directional — needs F&G to disambiguate
}

# Canonical regimes with weights (higher = stronger vote)
CANONICAL_REGIMES = ["TRENDING_UP", "TRENDING_DOWN", "RANGING", "HIGH_VOLATILITY", "CRASH"]

# Detector vote weights — tuned by reliability
DETECTOR_WEIGHTS = {
    "regime_sentinel":     3.0,  # 4-state on-chain cycle (MVRV + F&G + funding) — HIGHEST WEIGHT
    "regime_router":       2.0,  # Live data, battle-tested in aggregator
    "regime_terminal":     1.5,  # HMM with 730d lookback, per-ticker
    "system_b_classifier": 1.0,  # XGBoost, good but needs retraining
    "risk_hmm":            0.8,  # 3-state only, coarse
    "hierarchical":        1.2,  # 3-level, good for macro context
}


# ── Strategy-Regime alignment table ────────────────────────────────
# Maps each canonical regime to the strategy categories that are appropriate.
# Uses the same categories as alpha_engine STRATEGY_REGIME_MAP but unified.

REGIME_STRATEGY_ALIGNMENT = {
    "TRENDING_UP": {
        "aligned": [
            "trending", "momentum", "breakout", "trend-following",
            # Specific strategies
            "btc_ichimoku_cloud", "crypto_breakout_volume", "altcoin_season_rotation",
            "break_of_structure", "multi_timeframe_ema_stack", "cross_sectional_momentum",
            "atr_volatility_breakout", "obv_divergence_breakout", "ema_stack",
            "supertrend_follow", "rsi_macd_confluence", "fibonacci_retracement",
            "tsmom_28d", "momentum_factor_12m", "penny_volume_breakout",
            "carry_trade_momentum", "session_momentum_continuation",
            "dynamic_momentum_scaling", "sector_momentum_7d", "pentoshi_htf_structure",
            "spike_momentum_ignition", "spike_squeeze_breakout", "spike_volume_explosion",
            "community_ema_9_21_rsi_crypto", "community_momentum_breakout_volume_crypto",
            "community_bb_squeeze_breakout_crypto", "profit_taking_reentry",
            "adx_volatility_breakout", "market_structure_break", "hurst_regime_momentum",
        ],
        "misaligned": [
            "mean-reversion", "short", "bear",
            "ema_crossover_short", "sell_the_rally", "bear_trend_short",
            "connors_rsi2_crypto", "connors_rsi2", "connors_rsi2_scanner",
            "ornstein_uhlenbeck", "hurst_mean_reversion", "cointegrated_pairs",
            "bb_rsi_mean_reversion", "connors_r3_survivor",
            "keltner_mean_reversion_survivor", "bollinger_mean_reversion_survivor",
        ],
    },
    "TRENDING_DOWN": {
        "aligned": [
            "short", "mean-reversion", "fear-contrarian", "bear",
            "ema_crossover_short", "sell_the_rally", "bear_trend_short",
            "swing_failure_pattern", "crypto_fear_greed_contrarian",
            "fear_greed_extreme_dca", "liquidation_cascade_bottom",
            "liquidation_cascade_buy", "dead_cat_bounce_momentum",
            "momentum_crash_hedge", "vix_spike_reversal_scanner",
            "token_unlock_short", "fast_rsi2_short",
        ],
        "misaligned": [
            "momentum", "breakout", "trend-following",
            "btc_ichimoku_cloud", "crypto_breakout_volume", "altcoin_season_rotation",
            "multi_timeframe_ema_stack", "cross_sectional_momentum",
            "spike_momentum_ignition", "spike_volume_explosion",
            "carry_trade_momentum", "penny_volume_breakout",
            "dynamic_momentum_scaling", "sector_momentum_7d",
            "profit_taking_reentry", "adx_volatility_breakout",
        ],
    },
    "RANGING": {
        "aligned": [
            "mean-reversion", "ranging", "bollinger", "rsi",
            "connors_rsi2_crypto", "connors_rsi2", "connors_rsi2_scanner",
            "rsi_hidden_divergence", "stochrsi_oversold_bounce",
            "hurst_mean_reversion", "vwap_sd_mean_reversion",
            "rsi_macd_confluence", "volume_climax_reversal",
            "cmf_zero_line_cross", "ornstein_uhlenbeck",
            "bollinger_keltner_squeeze", "swing_failure_pattern",
            "entropy_adaptive_rsi", "liquidity_sweep_reversal",
            "cointegrated_pairs", "support_resistance_bounce",
            "triple_rsi_scanner", "fast_rsi2_relaxed", "fast_rsi2_extended",
            "fast_rsi2_aggressive", "fast_triple_confirm",
            "bb_rsi_mean_reversion", "connors_r3_survivor",
            "keltner_mean_reversion_survivor", "bollinger_mean_reversion_survivor",
            "lw_vwap_mean_reversion", "iv_skew_reversion",
            "cointegration_pair_trade", "volume_acceleration_reversion",
            "spread_of_candles_gap", "vix_correlation_divergence",
            "forex_mean_reversion_200d", "dxy_rsi_mean_reversion",
            "community_rsi_extreme_reversal_crypto", "community_vwap_bounce_crypto",
            "spike_rsi_extreme", "spike_macd_divergence", "spike_zscore_extreme",
            "sopr_dip_buy_proxy", "btc_200d_sma_bounce",
            "earnings_gap_reversal_scanner", "gap_reversal_tech_stocks",
            "altcoin_dip_amplifier", "dvol_extreme_buy",
            "community_forex_zscore_mean_reversion",
        ],
        "misaligned": [
            "breakout", "trend-following",
            "spike_momentum_ignition", "spike_volume_explosion",
            "adx_volatility_breakout", "market_structure_break",
        ],
    },
    "HIGH_VOLATILITY": {
        "aligned": [
            "volatility-breakout", "squeeze", "keltner",
            "bollinger_keltner_squeeze", "atr_volatility_breakout",
            "swing_failure_pattern", "ema_crossover_short",
            "sell_the_rally", "spike_squeeze_breakout",
            "session_volatility_expansion", "forex_bollinger_squeeze",
            "vol_risk_premium", "whale_accumulation_detector",
            "adx_volatility_breakout", "fast_vix_moderate",
        ],
        "misaligned": [
            "mean-reversion",
            "ornstein_uhlenbeck", "connors_rsi2", "connors_rsi2_crypto",
            "hurst_mean_reversion", "cointegrated_pairs",
            "cointegration_pair_trade",
        ],
    },
    "CRASH": {
        "aligned": [
            "fear-contrarian", "dca", "liquidation-cascade",
            "crypto_fear_greed_contrarian", "fear_greed_extreme_dca",
            "liquidation_cascade_bottom", "liquidation_cascade_buy",
            "dead_cat_bounce_momentum", "momentum_crash_hedge",
            "vix_spike_reversal_scanner", "whale_accumulation_detector",
            "sopr_dip_buy_proxy", "onchain_composite_score",
            "hayes_liquidity_index",
        ],
        "misaligned": [
            "momentum", "breakout", "trend-following", "mean-reversion",
            "btc_ichimoku_cloud", "crypto_breakout_volume",
            "multi_timeframe_ema_stack", "ornstein_uhlenbeck",
            "connors_rsi2", "connors_rsi2_crypto", "hurst_mean_reversion",
            "carry_trade_momentum", "penny_volume_breakout",
            "cointegrated_pairs", "cointegration_pair_trade",
        ],
    },
}

# Score adjustments
ALIGNED_BOOST = 0.15      # +15% confidence for regime-aligned strategies
MISALIGNED_PENALTY = -0.30  # -30% confidence for misaligned strategies


# ── Detector data loaders ──────────────────────────────────────────

def _load_regime_terminal() -> Optional[dict]:
    """Load regime_terminal/data/regime_state.json for market overview + per-ticker regimes."""
    path = REPO_ROOT / "regime_terminal" / "data" / "regime_state.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        # Check freshness (< 2 hours old)
        gen = data.get("generated_at", "")
        if gen:
            try:
                ts = datetime.fromisoformat(gen.replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
                if age_hours > 2:
                    print(f"  [META-ROUTER] regime_terminal data stale ({age_hours:.1f}h old)", file=sys.stderr)
                    return None
            except Exception:
                pass
        return data
    except Exception as e:
        print(f"  [META-ROUTER] Failed to load regime_terminal: {e}", file=sys.stderr)
        return None


def _load_system_b_regime() -> Optional[dict]:
    """Load ml_battleground/system_b_regime/data/regime_history.json for latest regime."""
    path = REPO_ROOT / "ml_battleground" / "system_b_regime" / "data" / "regime_history.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            history = json.load(f)
        if history and isinstance(history, list):
            latest = history[-1]
            return {
                "regime": latest.get("regime", "range_bound"),
                "confidence": latest.get("confidence", 0.5),
            }
        return None
    except Exception as e:
        print(f"  [META-ROUTER] Failed to load system_b regime: {e}", file=sys.stderr)
        return None


def _load_risk_hmm() -> Optional[dict]:
    """Load risk_management HMM regime if a model exists and can predict."""
    # This detector requires a trained model + live price data.
    # We check for cached output first.
    path = REPO_ROOT / "risk_management" / "data" / "regime_prediction.json"
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
            return data
        except Exception:
            pass
    return None


# ── Consensus computation ──────────────────────────────────────────

def _collect_votes() -> list[dict]:
    """
    Collect regime votes from all available detectors.

    Returns list of:
        {"detector": name, "regime": canonical_regime, "confidence": 0-1, "weight": float, "raw": ...}
    """
    votes = []

    # ── Detector 0: Regime Sentinel (4-state on-chain cycle classifier) ──
    if _HAS_SENTINEL:
        try:
            sentinel = _get_sentinel()
            canonical = sentinel.get("canonical_regime", "RANGING")
            conf = sentinel.get("confidence", 0.5)
            votes.append({
                "detector": "regime_sentinel",
                "regime": canonical,
                "confidence": conf,
                "weight": DETECTOR_WEIGHTS["regime_sentinel"],
                "raw": {
                    "sentinel_regime": sentinel.get("regime"),
                    "risk_multiplier": sentinel.get("risk_multiplier"),
                    "action_bias": sentinel.get("action_bias"),
                    "inputs": sentinel.get("inputs"),
                    "reasoning": sentinel.get("reasoning"),
                },
            })
        except Exception as e:
            print(f"  [META-ROUTER] regime_sentinel failed: {e}", file=sys.stderr)

    # ── Detector 1: regime_router (live API — F&G + BTC technicals) ──
    if _HAS_REGIME_ROUTER:
        try:
            router_data = _get_router_regime()
            raw_regime = router_data.get("regime", "UNKNOWN")
            canonical = _ROUTER_REGIME_MAP.get(raw_regime)

            # Enhance with F&G context: extreme fear overrides to CRASH
            fng = router_data.get("fng")
            if fng is not None and fng <= 10:
                canonical = "CRASH"
            elif fng is not None and fng <= 20 and raw_regime == "TRENDING_DOWN":
                canonical = "CRASH"

            if canonical:
                # Confidence from ADX strength + F&G certainty
                adx = router_data.get("adx")
                conf = 0.6
                if adx and adx > 25:
                    conf = 0.8
                elif adx and adx > 15:
                    conf = 0.7
                votes.append({
                    "detector": "regime_router",
                    "regime": canonical,
                    "confidence": conf,
                    "weight": DETECTOR_WEIGHTS["regime_router"],
                    "raw": router_data,
                })
        except Exception as e:
            print(f"  [META-ROUTER] regime_router failed: {e}", file=sys.stderr)

    # ── Detector 2: regime_terminal (7-state HMM) ──
    terminal_data = _load_regime_terminal()
    if terminal_data:
        # Use market_overview for aggregate vote
        overview = terminal_data.get("market_overview", {})
        bull = overview.get("bull_count", 0)
        bear = overview.get("bear_count", 0)
        neutral = overview.get("neutral_count", 0)
        total = overview.get("total_scanned", 1) or 1

        # Determine aggregate regime from the balance
        bull_pct = bull / total
        bear_pct = bear / total
        neutral_pct = neutral / total

        if bear_pct > 0.5:
            regime = "TRENDING_DOWN"
            conf = min(0.9, bear_pct)
        elif bull_pct > 0.4:
            regime = "TRENDING_UP"
            conf = min(0.9, bull_pct)
        elif neutral_pct > 0.4:
            regime = "RANGING"
            conf = min(0.8, neutral_pct)
        else:
            regime = "RANGING"
            conf = 0.5

        votes.append({
            "detector": "regime_terminal",
            "regime": regime,
            "confidence": conf,
            "weight": DETECTOR_WEIGHTS["regime_terminal"],
            "raw": {"bull_pct": round(bull_pct, 2), "bear_pct": round(bear_pct, 2),
                     "neutral_pct": round(neutral_pct, 2)},
        })

    # ── Detector 3: system_b classifier (XGBoost 4-state) ──
    sys_b = _load_system_b_regime()
    if sys_b:
        raw_regime = sys_b.get("regime", "range_bound")
        canonical = _SYSTEM_B_REGIME_MAP.get(raw_regime, "RANGING")
        conf = sys_b.get("confidence", 0.5)
        votes.append({
            "detector": "system_b_classifier",
            "regime": canonical,
            "confidence": conf,
            "weight": DETECTOR_WEIGHTS["system_b_classifier"],
            "raw": sys_b,
        })

    # ── Detector 4: risk_management HMM ──
    risk_data = _load_risk_hmm()
    if risk_data:
        raw_regime = risk_data.get("regime", "RANGE")
        canonical = _RISK_REGIME_MAP.get(raw_regime, "RANGING")

        # If risk_management says TREND, use F&G from detector 1 to determine direction
        if canonical == "TRENDING_UP" and _HAS_REGIME_ROUTER:
            try:
                router = _get_router_regime()
                if router.get("regime") == "TRENDING_DOWN":
                    canonical = "TRENDING_DOWN"
            except Exception:
                pass

        conf = risk_data.get("confidence", 0.5)
        votes.append({
            "detector": "risk_hmm",
            "regime": canonical,
            "confidence": conf,
            "weight": DETECTOR_WEIGHTS["risk_hmm"],
            "raw": risk_data,
        })

    return votes


def _weighted_vote(votes: list[dict]) -> tuple[str, float, dict]:
    """
    Compute weighted consensus regime from detector votes.

    Returns:
        (consensus_regime, consensus_confidence, vote_breakdown)
    """
    if not votes:
        return "RANGING", 0.3, {"no_votes": True}

    # Accumulate weighted scores per regime
    scores: dict[str, float] = {r: 0.0 for r in CANONICAL_REGIMES}
    total_weight = 0.0

    for v in votes:
        regime = v["regime"]
        w = v["weight"] * v["confidence"]
        if regime in scores:
            scores[regime] += w
        total_weight += w

    if total_weight == 0:
        return "RANGING", 0.3, {"zero_weight": True}

    # Normalize
    for r in scores:
        scores[r] /= total_weight

    # Winner
    winner = max(scores, key=scores.get)
    confidence = scores[winner]

    # CRASH override: if ANY detector says CRASH with confidence > 0.6, force CRASH
    for v in votes:
        if v["regime"] == "CRASH" and v["confidence"] > 0.6:
            winner = "CRASH"
            confidence = max(confidence, v["confidence"])
            break

    breakdown = {
        "scores": {r: round(s, 4) for r, s in scores.items()},
        "votes": [
            {"detector": v["detector"], "regime": v["regime"],
             "confidence": round(v["confidence"], 3), "weight": v["weight"]}
            for v in votes
        ],
        "winner": winner,
        "consensus_confidence": round(confidence, 4),
    }

    return winner, confidence, breakdown


# ── Public API ─────────────────────────────────────────────────────

def get_consensus_regime() -> dict:
    """
    Fetch regime data from all detectors and compute consensus.

    Returns:
        {
            "consensus_regime": "TRENDING_DOWN",
            "confidence": 0.72,
            "detectors_available": 3,
            "detectors_total": 5,
            "vote_breakdown": {...},
            "strategy_alignment": {...},
            "timestamp": "2026-03-15T12:00:00Z"
        }
    """
    votes = _collect_votes()
    regime, confidence, breakdown = _weighted_vote(votes)

    result = {
        "consensus_regime": regime,
        "confidence": round(confidence, 4),
        "detectors_available": len(votes),
        "detectors_total": 6,
        "vote_breakdown": breakdown,
        "strategy_alignment": REGIME_STRATEGY_ALIGNMENT.get(regime, {}),
        "aligned_boost": ALIGNED_BOOST,
        "misaligned_penalty": MISALIGNED_PENALTY,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return result


def score_pick_by_regime(pick: dict, consensus: dict) -> dict:
    """
    Score a single pick based on regime alignment.

    Modifies pick in-place, adding:
      - regime_alignment: 'aligned' | 'misaligned' | 'neutral'
      - regime_score_adj: float (the confidence adjustment applied)
      - consensus_regime: str
      - original_confidence: float (before adjustment)

    Returns the modified pick.
    """
    regime = consensus.get("consensus_regime", "RANGING")
    alignment_info = REGIME_STRATEGY_ALIGNMENT.get(regime, {})
    aligned_strategies = set(alignment_info.get("aligned", []))
    misaligned_strategies = set(alignment_info.get("misaligned", []))

    # Get strategy name(s) from pick
    strategy = pick.get("strategy", pick.get("strategy_name", ""))
    strategies = pick.get("source_strategies", [strategy] if strategy else [])

    # Also check direction alignment
    direction = pick.get("direction", "").upper()
    direction_aligned = _check_direction_alignment(direction, regime)

    # Check strategy alignment
    alignment = "neutral"
    for s in strategies:
        s_lower = s.lower() if isinstance(s, str) else ""
        if s_lower in aligned_strategies or s in aligned_strategies:
            alignment = "aligned"
            break
        if s_lower in misaligned_strategies or s in misaligned_strategies:
            alignment = "misaligned"
            break

    # Direction override: even if strategy is neutral, direction matters
    if alignment == "neutral" and not direction_aligned:
        alignment = "misaligned"
    elif alignment == "neutral" and direction_aligned:
        alignment = "aligned"

    # Apply score adjustment
    original_conf = pick.get("confidence", 0.5)
    if alignment == "aligned":
        adj = ALIGNED_BOOST
    elif alignment == "misaligned":
        adj = MISALIGNED_PENALTY
    else:
        adj = 0.0

    new_conf = max(0.05, min(0.95, original_conf + adj))

    # Annotate pick
    pick["regime_alignment"] = alignment
    pick["regime_score_adj"] = round(adj, 4)
    pick["consensus_regime"] = regime
    pick["original_confidence"] = round(original_conf, 4)
    pick["confidence"] = round(new_conf, 4)

    return pick


def _check_direction_alignment(direction: str, regime: str) -> bool:
    """Check if trade direction aligns with regime."""
    if regime == "TRENDING_UP":
        return direction == "LONG"
    elif regime == "TRENDING_DOWN":
        return direction == "SHORT"
    elif regime == "CRASH":
        # During crashes, contrarian LONG at extreme fear is valid
        return direction == "LONG"
    elif regime in ("RANGING", "HIGH_VOLATILITY"):
        return True  # Both directions valid
    return True


def score_picks_by_regime(picks: list[dict],
                          consensus: dict | None = None) -> tuple[list[dict], dict]:
    """
    Score all picks through the regime meta-router.

    Args:
        picks: list of pick dicts
        consensus: pre-fetched consensus (if None, will fetch)

    Returns:
        (scored_picks, regime_summary) where regime_summary includes stats
    """
    if consensus is None:
        consensus = get_consensus_regime()

    regime = consensus.get("consensus_regime", "RANGING")
    aligned_count = 0
    misaligned_count = 0
    neutral_count = 0

    scored = []
    for pick in picks:
        scored_pick = score_pick_by_regime(pick, consensus)
        scored.append(scored_pick)

        a = scored_pick.get("regime_alignment", "neutral")
        if a == "aligned":
            aligned_count += 1
        elif a == "misaligned":
            misaligned_count += 1
        else:
            neutral_count += 1

    summary = {
        "consensus_regime": regime,
        "confidence": consensus.get("confidence", 0.0),
        "detectors_available": consensus.get("detectors_available", 0),
        "total_picks": len(picks),
        "aligned": aligned_count,
        "misaligned": misaligned_count,
        "neutral": neutral_count,
        "timestamp": consensus.get("timestamp"),
    }

    return scored, summary


def get_per_ticker_regime(symbol: str) -> Optional[dict]:
    """
    Get regime for a specific ticker from regime_terminal signals.

    Returns dict with normalized regime label or None.
    """
    path = REPO_ROOT / "regime_terminal" / "data" / "active_signals.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        for sig in data.get("signals", []):
            # Normalize ticker: BTCUSDT -> BTC-USD, etc.
            ticker = sig.get("ticker", "")
            if _symbols_match(symbol, ticker):
                raw_regime = sig.get("regime", "")
                canonical = _TERMINAL_REGIME_MAP.get(raw_regime, "RANGING")
                return {
                    "regime": canonical,
                    "raw_regime": raw_regime,
                    "confidence": sig.get("confidence", 0.5),
                    "signal": sig.get("signal", ""),
                    "rsi": sig.get("rsi"),
                }
    except Exception:
        pass
    return None


def _symbols_match(sym1: str, sym2: str) -> bool:
    """Check if two symbols refer to the same asset (fuzzy matching)."""
    # Normalize: remove -USD, USDT, =X suffixes, uppercase
    def _norm(s):
        s = s.upper().replace("-USD", "").replace("USDT", "").replace("=X", "").replace("/", "")
        return s
    return _norm(sym1) == _norm(sym2)


# ── CLI ────────────────────────────────────────────────────────────

def main():
    """Print consensus regime status."""
    print("=" * 70)
    print("REGIME META-ROUTER — Consensus from All Detectors")
    print("=" * 70)

    consensus = get_consensus_regime()

    print(f"\n  Consensus Regime:   {consensus['consensus_regime']}")
    print(f"  Confidence:         {consensus['confidence']:.1%}")
    print(f"  Detectors Online:   {consensus['detectors_available']}/{consensus['detectors_total']}")
    print(f"  Timestamp:          {consensus['timestamp']}")

    breakdown = consensus.get("vote_breakdown", {})
    scores = breakdown.get("scores", {})
    votes = breakdown.get("votes", [])

    print(f"\n  Regime Scores:")
    for regime, score in sorted(scores.items(), key=lambda x: -x[1]):
        bar = "#" * int(score * 40)
        print(f"    {regime:20s} {score:6.1%}  {bar}")

    print(f"\n  Individual Votes:")
    for v in votes:
        print(f"    {v['detector']:25s} -> {v['regime']:20s} (conf={v['confidence']:.1%}, w={v['weight']})")

    alignment = consensus.get("strategy_alignment", {})
    aligned = alignment.get("aligned", [])
    misaligned = alignment.get("misaligned", [])
    print(f"\n  Aligned strategies:    {len(aligned)} types")
    print(f"  Misaligned strategies: {len(misaligned)} types")
    print(f"  Boost for aligned:     +{ALIGNED_BOOST:.0%}")
    print(f"  Penalty for misaligned: {MISALIGNED_PENALTY:.0%}")

    print(f"\n{'=' * 70}")
    return consensus


if __name__ == "__main__":
    main()
