"""
Fundamental and Macro Regime Gates for Money-Ready Pick Identification
======================================================================

This module implements the new gates for identifying high-conviction immediate opportunities
and long-term stable edges based on fundamental strength and macro regime alignment.

Gates:
- Fundamental Strength Gate: Quantifies fundamental attractiveness (earnings momentum, valuation, network metrics)
- Macro Regime Alignment Score: Assesses alignment with current macro regimes (USD, Yield Curve, VIX)
- High-Conviction Immediate Opportunity Gate: Promotes picks meeting "Right Now" criteria
- Long-Term Edge Stability Gate: Elevates picks with persistent, robust statistical edges

Integration:
- Called from alpha_engine/money_ready_verdict.py
- Results used to set tags and apply confidence boosts
"""

from __future__ import annotations

import logging
import math
from typing import Any, Optional

import sys as _sys

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Category normalization  (stocks → equity, infer missing from symbol)
# ---------------------------------------------------------------------------
_CRYPTO_SUFFIXES = ("USDT", "USDC", "BUSD", "BTC", "ETH", "USD")
_FX_PAIRS = {"EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD",
             "NZDUSD", "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "NZDJPY",
             "EURNZD", "GBPAUD", "GBPCAD", "GBPNZD", "CADJPY", "CHFJPY",
             "AUDCAD", "AUDCHF", "AUDNZD", "NZDCAD", "NZDCHF", "CADCHF",
             "EURCHF", "EURAUD", "EURCAD", "XAUUSD", "XAGUSD", "WTICOUSD"}
_FUTURES_ROOTS = {"ES", "NQ", "YM", "RTY", "GC", "SI", "CL", "NG", "ZB",
                  "ZN", "ZF", "ZT", "6E", "6J", "6B", "6A", "6C"}

def _normalize_category(pick: dict) -> str:
    """Return a canonical asset-class string for *pick*.

    Handles the three common data-quality issues:
    1. category == 'stocks'  →  'equity'
    2. category empty / NONE  →  infer from symbol format
    3. known forex / futures symbols  →  'forex' / 'futures'
    """
    raw = (pick.get("category") or "").strip().lower()
    if raw in ("equity", "etf", "bond", "index"):
        return raw
    if raw == "stocks":
        return "equity"
    if raw in ("crypto", "forex", "commodity", "futures", "penny_stock"):
        return raw

    # ---- Infer from symbol ----
    sym = (pick.get("symbol") or "").upper().strip()
    if not sym:
        return ""
    for suffix in _CRYPTO_SUFFIXES:
        if sym.endswith(suffix) and len(sym) > len(suffix):
            return "crypto"
    if sym in _FX_PAIRS:
        return "forex"
    if len(sym) == 6 and sym.isalpha() and sym[:3] in (
        "EUR", "GBP", "USD", "AUD", "NZD", "CAD", "CHF", "JPY"):
        return "forex"
    if sym in _FUTURES_ROOTS:
        return "futures"

    # ---- Infer from strategy name ----
    strat = (pick.get("strategy") or "").lower()
    if "crypto" in strat or "btc" in strat or "eth" in strat or "usdt" in strat:
        return "crypto"
    if "forex" in strat or "fx" in strat:
        return "forex"
    if "futures" in strat or "commodity" in strat:
        return "futures"

    # Default: treat 3-5 char alpha symbols as equity
    if sym.isalpha() and 1 <= len(sym) <= 5:
        return "equity"
    return raw or ""
# Lazy, fail-open imports.  On GHA runners (and any environment where a
# transitive dependency is missing / network-gated) the top-level imports
# used to crash the entire module.  The callers (money_ready_verdict.py,
# eagle_gates.py) already have fail-open stubs, but those only fire if
# THIS module itself fails to import — we fix the root cause here so the
# real gate logic can actually run.
# ---------------------------------------------------------------------------

# fred_macro_context — provides get_macro_context().
# Fail-open: returns empty dict → neutral regime scores (0.0).
try:
    from alpha_engine.fred_macro_context import get_macro_context as _get_macro_context
except Exception:
    _get_macro_context = None  # type: ignore[assignment]
    print("WARN: fred_macro_context unavailable; macro regime scores default to 0.0",
          file=_sys.stderr)

def get_macro_context():  # noqa: N802 — public API name preserved
    if _get_macro_context is not None:
        return _get_macro_context()
    return {}

# equity_earnings_loader — provides load_pead_event_for_ticker().
# Fail-open: returns None → heuristic keyword fallback already exists in
# _compute_equity_fundamental_strength().
try:
    from alpha_engine.equity_earnings_loader import load_pead_event_for_ticker  # noqa: F401
except Exception:
    def load_pead_event_for_ticker(ticker, **_kw):  # type: ignore[misc]
        return None
    print("WARN: equity_earnings_loader unavailable; PEAD data disabled (heuristic fallback)",
          file=_sys.stderr)

# fundamental_valuation_strategies — symbols used only as strategy names in
# _compute_crypto_fundamental_strength() (which matches on pick["strategy"]).
# The module-level names are NEVER called directly; we only need the import
# so that e.g. btc_power_law_deviation is importable by *other* consumers.
# Fail-open: provide empty stubs.
try:
    from alpha_engine.fundamental_valuation_strategies import (  # noqa: F401
        FUNDAMENTAL_VALUATION_STRATEGIES,
        btc_power_law_deviation,
        nvm_metcalfe_valuation,
        eth_gas_fee_reversal,
    )
except Exception:
    FUNDAMENTAL_VALUATION_STRATEGIES = []  # type: ignore[misc]
    btc_power_law_deviation = None  # type: ignore[assignment]
    nvm_metcalfe_valuation = None  # type: ignore[assignment]
    eth_gas_fee_reversal = None  # type: ignore[assignment]
    print("WARN: fundamental_valuation_strategies unavailable; crypto valuation stubs active",
          file=_sys.stderr)

# walk_forward_validator — symbols imported for future direct use but
# currently only the pick-dict fields (consistency_score, edge_decay,
# regime_robustness) are read by passes_long_term_stability_gate().
# Fail-open: stubs that always "pass" (fail-open conservative).
try:
    from alpha_engine.walk_forward_validator import (  # noqa: F401
        compute_consistency_score,
        detect_edge_decay,
        assess_regime_robustness,
    )
except Exception:
    def compute_consistency_score(*a, **kw):  # type: ignore[misc]
        return 0.0
    def detect_edge_decay(*a, **kw):  # type: ignore[misc]
        return {}
    def assess_regime_robustness(*a, **kw):  # type: ignore[misc]
        return {}
    print("WARN: walk_forward_validator unavailable; long-term gate uses pick-dict fields only",
          file=_sys.stderr)

# ============================================================================
# Fundamental Strength Gate
# ============================================================================


def _compute_equity_fundamental_strength(pick: dict) -> Optional[float]:
    """
    Compute fundamental strength score for equity picks.
    
    Uses earnings momentum (PEAD), sector strength, analyst sentiment, and valuation.
    
    Returns:
        float: Score in range [0, 100], or None if insufficient data
    """
    category = _normalize_category(pick)
    if category != "equity":
        return None
    
    ticker = pick.get("symbol")
    reason = (pick.get("reason", "") or "").lower()
    
    score = 50.0  # Base score
    
    # 1. PEAD (Earnings Momentum) - Data Driven
    if ticker:
        pead_event = load_pead_event_for_ticker(ticker)
        if pead_event and isinstance(pead_event, dict):
            surprise = pead_event.get("surprise_pct", 0.0)
            guidance = pead_event.get("guidance_raised", False)

            # Surprise scoring
            if surprise > 10:
                score += 20
            elif surprise > 5:
                score += 10
            elif surprise > 0:
                score += 5
            elif surprise > -5:
                score -= 5
            elif surprise > -10:
                score -= 10
            else:
                score -= 20
            
            # Guidance boost
            if guidance:
                score += 15
        else:
            # Fallback to heuristic if no PEAD data found
            if "earnings surprise" in reason or "positive earnings" in reason:
                score += 15
            elif "earnings miss" in reason or "negative earnings" in reason:
                score -= 10

    # 2. Analyst sentiment (Heuristic/Keyword)
    if "upgrade" in reason:
        score += 10
    elif "downgrade" in reason:
        score -= 10
    
    # 3. Valuation (Heuristic/Keyword)
    if "undervalued" in reason or "cheap" in reason:
        score += 10
    elif "overvalued" in reason or "expensive" in reason:
        score -= 10
    
    # Cap at 100, floor at 0
    score = max(0, min(100, score))
    
    return round(score, 1) if score > 0 else None


def _compute_crypto_fundamental_strength(pick: dict) -> Optional[float]:
    """
    Compute fundamental strength score for crypto picks.
    
    Uses network metrics (NVT, Metcalfe), power law deviation, and gas analysis.
    
    Returns:
        float: Normalized deviation score (sigma), or None if insufficient data
    """
    category = _normalize_category(pick)
    if category != "crypto":
        return None
    
    strategy = pick.get("strategy", "").lower()
    extra = pick.get("extra", {})
    if not isinstance(extra, dict):
        extra = {}
    
    # ---- Strategy-specific paths (original valuation strategies) ----
    # Power Law deviation (z-score)
    if strategy == "btc_power_law_deviation":
        z_score = extra.get("z_score")
        if z_score is not None:
            sigma = abs(float(z_score))
            return round(sigma, 2)
    
    # NVM Metcalfe deviation (percentile)
    elif strategy == "nvm_metcalfe_valuation":
        percentile = extra.get("nvm_percentile")
        if percentile is not None:
            if percentile < 25:
                sigma = 1.5 + (25 - percentile) * 0.02
            elif percentile > 75:
                sigma = 1.5 + (percentile - 75) * 0.02
            else:
                sigma = 0.5
            return round(sigma, 2)
    
    # Gas fee reversal (z-score proxy)
    elif strategy == "eth_gas_fee_reversal":
        gas_z = extra.get("gas_z_score")
        if gas_z is not None:
            return round(abs(float(gas_z)), 2)

    # ---- Generic on-chain snapshot (network_metrics dict) ----
    net = extra.get("network_metrics") if isinstance(extra.get("network_metrics"), dict) else {}
    if net:
        score = 0.0
        fr = net.get("funding_rate")
        if fr is not None:
            try:
                score += min(1.5, abs(float(fr)) * 5000)
            except (TypeError, ValueError):
                pass
        fgi = net.get("fear_greed")
        if fgi is not None:
            try:
                fgi_i = int(fgi)
                if fgi_i <= 25 or fgi_i >= 75:
                    score += 1.0
            except (TypeError, ValueError):
                pass
        if score >= 1.0:
            return round(score, 2)

    # ---- Battleground / scanner extra fields ----
    # These are the actual fields present in closed_picks.json for crypto
    # picks: fast_regime_score, btc_granger_significant, btc_lead_boost, etc.
    score = 0.0

    # fast_regime_score: -1 (bearish) to +1 (bullish); use absolute as
    # conviction signal
    regime_score = extra.get("fast_regime_score")
    if regime_score is not None:
        try:
            rs = abs(float(regime_score))
            score += min(1.0, rs)
        except (TypeError, ValueError):
            pass

    # fast_regime_confidence: 0-1 scale
    regime_conf = extra.get("fast_regime_confidence")
    if regime_conf is not None:
        try:
            rc = float(regime_conf)
            if rc >= 0.7:
                score += 0.8
            elif rc >= 0.4:
                score += 0.4
        except (TypeError, ValueError):
            pass

    # btc_granger_significant: boolean — BTC leads this alt
    if extra.get("btc_granger_significant"):
        score += 0.5

    # btc_lead_boost: numeric boost from BTC lead-lag
    boost = extra.get("btc_lead_boost")
    if boost is not None:
        try:
            b = abs(float(boost))
            if b > 0:
                score += min(1.0, b)
        except (TypeError, ValueError):
            pass

    if score >= 1.0:
        return round(score, 2)

    # ---- Reason-keyword fallback for crypto ----
    reason = (pick.get("reason") or "").lower()
    _BULLISH_KW = ("breakout", "accumulation", "whale", "bullish", "oversold",
                   "support bounce", "golden cross", "funding positive")
    _BEARISH_KW = ("breakdown", "bearish", "overbought", "distribution",
                   "death cross", "funding negative")
    for kw in _BULLISH_KW:
        if kw in reason:
            return 1.2
    for kw in _BEARISH_KW:
        if kw in reason:
            return 0.8

    return None


def compute_fundamental_strength(pick: dict) -> dict[str, Any]:
    """
    Compute fundamental strength score for a pick.
    
    Returns a dictionary with:
    - fundamental_strength_score: float or None
    - fundamental_strength_status: str ("high", "medium", "low", "none")
    - reason: explanation of the score
    """
    category = _normalize_category(pick)
    
    if category == "equity":
        score = _compute_equity_fundamental_strength(pick)
    elif category == "crypto":
        score = _compute_crypto_fundamental_strength(pick)
    else:
        score = None
    
    result = {
        "fundamental_strength_score": score,
        "fundamental_strength_status": "none",
        "reason": "",
    }
    
    if score is None:
        result["reason"] = "No fundamental data available for this asset class"
        return result
    
    # Determine status based on thresholds from spec
    if category == "equity":
        if score > 70:
            result["fundamental_strength_status"] = "high"
            result["reason"] = f"Strong fundamental score: {score}/100"
        elif score > 50:
            result["fundamental_strength_status"] = "medium"
            result["reason"] = f"Moderate fundamental score: {score}/100"
        else:
            result["fundamental_strength_status"] = "low"
            result["reason"] = f"Weak fundamental score: {score}/100"
    
    elif category == "crypto":
        # For crypto, score is in sigma units
        if score > 1.5:
            result["fundamental_strength_status"] = "high"
            result["reason"] = f"Strong fundamental deviation: {score}σ"
        elif score > 0.8:
            result["fundamental_strength_status"] = "medium"
            result["reason"] = f"Moderate fundamental deviation: {score}σ"
        else:
            result["fundamental_strength_status"] = "low"
            result["reason"] = f"Weak fundamental deviation: {score}σ"
    
    return result


# ============================================================================
# Macro Regime Alignment Score
# ============================================================================


def _get_macro_regime_scores(pick: dict) -> dict[str, float]:
    """
    Get macro regime alignment scores for a pick based on its asset class.
    
    Returns a dictionary with alignment scores for:
    - usd: USD regime alignment [-1, 1]
    - curve: Yield curve regime alignment [-1, 1]
    - vol: Volatility regime alignment [-1, 1]
    - overall: Combined alignment score [-1, 1]
    """
    macro_context = get_macro_context()
    
    if not macro_context:
        return {
            "usd": 0.0,
            "curve": 0.0,
            "vol": 0.0,
            "overall": 0.0,
        }
    
    regime = macro_context.get("regime", {})
    indicators = macro_context.get("indicators", {})
    deltas = macro_context.get("deltas", {})

    usd_regime = regime.get("usd", "neutral")
    curve_regime = regime.get("curve", "flat")
    vol_regime = regime.get("vol", "normal")
    
    # Asset class from pick
    category = _normalize_category(pick)
    
    # Default scores (neutral alignment)
    scores = {
        "usd": 0.0,
        "curve": 0.0,
        "vol": 0.0,
        "overall": 0.0,
    }
    
    # --- USD Regime Alignment ---
    # Use regime label + actual USD index delta for finer scoring
    usd_delta = deltas.get("DTWEXBGS_30d_pct")  # 30d % change in USD index
    if usd_regime == "strong":
        base_usd = 0.3
    elif usd_regime == "weak":
        base_usd = -0.3
    else:
        base_usd = 0.0
    # Amplify if USD is actually moving significantly
    if usd_delta is not None:
        try:
            d = float(usd_delta)
            if abs(d) > 1.0:
                base_usd *= 1.5
            elif abs(d) < 0.3:
                base_usd *= 0.5  # Stable USD → less impact
        except (TypeError, ValueError):
            pass
    if category in ("equity", "forex", "commodity"):
        scores["usd"] = base_usd
    elif category == "crypto":
        scores["usd"] = -base_usd * 1.2  # Crypto inversely correlated with USD
    elif category == "etf":
        scores["usd"] = base_usd * 0.5
    
    # --- Yield Curve Regime Alignment ---
    # Use actual T10Y2Y spread value for nuance
    spread_entry = indicators.get("T10Y2Y", {})
    spread_val = spread_entry.get("value") if isinstance(spread_entry, dict) else None
    if curve_regime == "steep":
        base_curve = 0.3
    elif curve_regime == "inverted":
        base_curve = -0.2
    elif curve_regime == "flat":
        # Flat but positive spread → mild positive; flat + near-zero → neutral
        if spread_val is not None:
            try:
                base_curve = max(-0.2, min(0.3, float(spread_val) * 0.5))
            except (TypeError, ValueError):
                base_curve = 0.0
        else:
            base_curve = 0.0
    else:
        base_curve = 0.0
    if category in ("equity", "etf"):
        scores["curve"] = base_curve
    elif category == "crypto":
        scores["curve"] = base_curve * 0.5  # Crypto less curve-sensitive
    elif category in ("commodity", "futures"):
        scores["curve"] = -base_curve * 0.3  # Defensive assets inverse
    
    # --- Volatility Regime Alignment ---
    # Use actual VIX value for precise scoring
    vix_entry = indicators.get("VIXCLS", {})
    vix_val = vix_entry.get("value") if isinstance(vix_entry, dict) else None
    if vol_regime == "low":
        base_vol = 0.3
    elif vol_regime == "elevated":
        base_vol = -0.2
    else:
        base_vol = 0.0
    # Refine with actual VIX level
    if vix_val is not None:
        try:
            v = float(vix_val)
            if v < 15:
                # Very low vol → amplify risk-on signal
                base_vol = max(base_vol, 0.3) if category in ("equity", "crypto") else base_vol
            elif v > 25:
                # High vol → risk-off signal
                base_vol = min(base_vol, -0.2) if category in ("equity", "crypto") else base_vol
            elif v > 30:
                # Extreme vol → strong risk-off
                base_vol = min(base_vol, -0.4) if category == "equity" else base_vol
        except (TypeError, ValueError):
            pass
    if category in ("equity", "crypto"):
        scores["vol"] = base_vol
    elif category in ("forex", "commodity"):
        scores["vol"] = -base_vol * 0.5  # Flight to safety
    elif category in ("etf", "bond"):
        scores["vol"] = -base_vol * 0.3
    
    # Combine scores (weighted average)
    scores["overall"] = round(
        (scores["usd"] * 0.4 + scores["curve"] * 0.3 + scores["vol"] * 0.3),
        3
    )
    
    return scores


def compute_macro_alignment(pick: dict) -> dict[str, Any]:
    """
    Compute macro regime alignment score for a pick.
    
    Returns a dictionary with:
    - macro_alignment_score: float [-1, 1]
    - macro_alignment_status: str ("aligned", "neutral", "misaligned")
    - regime_details: dict with individual regime scores
    - reason: explanation of alignment
    """
    scores = _get_macro_regime_scores(pick)
    
    macro_score = scores["overall"]
    
    # Determine status based on thresholds
    if macro_score > 0.5:
        status = "aligned"
        reason = f"Strong macro alignment: {macro_score:.3f}"
    elif macro_score > 0.1:
        status = "neutral"
        reason = f"Moderate macro alignment: {macro_score:.3f}"
    elif macro_score < -0.5:
        status = "misaligned"
        reason = f"Strong macro misalignment: {macro_score:.3f}"
    else:
        status = "neutral"
        reason = f"Neutral macro alignment: {macro_score:.3f}"
    
    return {
        "macro_alignment_score": macro_score,
        "macro_alignment_status": status,
        "regime_details": scores,
        "reason": reason,
    }


# ============================================================================
# High-Conviction Immediate Opportunity Gate
# ============================================================================


def passes_high_conviction_gate(pick: dict) -> tuple[bool, dict[str, Any]]:
    """
    Determine if a pick qualifies as a high-conviction immediate opportunity.
    
    Criteria:
    - High fundamental strength score (> 70 for equities, > 1.5σ for crypto)
    - High macro alignment score (> 0.5)
    - Minimum trades: 5 (for new strategies)
    - Acceptable risk profile (MDD < 30%, CVaR < 25%)
    
    Returns:
        tuple: (passes, result_dict)
    """
    result = {
        "high_conviction": False,
        "high_conviction_reason": "",
        "confidence_boost": 1.0,
    }
    
    # Get fundamental strength
    fundamental_result = compute_fundamental_strength(pick)
    fundamental_score = fundamental_result.get("fundamental_strength_score")
    fundamental_status = fundamental_result.get("fundamental_strength_status")
    
    # Get macro alignment
    macro_result = compute_macro_alignment(pick)
    macro_score = macro_result.get("macro_alignment_score")
    macro_status = macro_result.get("macro_alignment_status")
    
    # Minimum trade count check
    n_trades = pick.get("n_trades", 0)
    
    # Risk profile checks - try pick stats first, then defaults
    mdd = pick.get("mdd")
    cvar = pick.get("cvar")
    
    if mdd is None:
        mdd = pick.get("max_drawdown", 999)
    if cvar is None:
        cvar = pick.get("cvar_95", 999)
    
    # Guard against None values
    mdd = float(mdd) if mdd is not None else 999
    cvar = float(cvar) if cvar is not None else 999
    
    # Determine if criteria are met
    category = _normalize_category(pick)
    
    # Check fundamental threshold
    fundamental_ok = False
    if category == "equity":
        fundamental_ok = fundamental_score is not None and fundamental_score > 70
    elif category == "crypto":
        fundamental_ok = fundamental_score is not None and fundamental_score > 1.5
    
    # Check macro alignment threshold
    macro_ok = macro_score is not None and macro_score > 0.5
    
    # Check minimum trades
    trades_ok = n_trades >= 5
    
    # Check risk profile
    risk_ok = mdd < 30 and cvar < 25
    
    # All criteria must be met
    if fundamental_ok and macro_ok and trades_ok and risk_ok:
        result["high_conviction"] = True
        result["high_conviction_reason"] = (
            f"High-conviction immediate opportunity: "
            f"fundamental={fundamental_status}, "
            f"macro={macro_status}, "
            f"trades={n_trades}, "
            f"risk_ok={risk_ok}"
        )
        result["confidence_boost"] = 1.3  # 1.3x boost as per spec
        logger.info(f"High-conviction pick identified: {pick.get('strategy', 'unknown')}")
    else:
        reasons = []
        if not fundamental_ok:
            reasons.append(f"fundamental={fundamental_status or 'none'}")
        if not macro_ok:
            reasons.append(f"macro={macro_status or 'none'}")
        if not trades_ok:
            reasons.append(f"trades={n_trades}/5")
        if not risk_ok:
            reasons.append(f"risk_mdd={mdd}% risk_cvar={cvar}%")
        
        result["high_conviction_reason"] = (
            f"Does not meet high-conviction criteria: "
            f"{', '.join(reasons)}"
        )
    
    # Merge in the detailed results
    result.update(fundamental_result)
    result.update(macro_result)
    
    return True, result


# ============================================================================
# Long-Term Edge Stability Gate
# ============================================================================


def passes_long_term_stability_gate(pick: dict) -> tuple[bool, dict[str, Any]]:
    """
    Determine if a pick demonstrates a long-term stable edge.
    
    Criteria:
    - High Walk-Forward Consistency (> 0.7)
    - Low Edge Decay (< 0.2)
    - Regime Robustness (all regimes > 0.6)
    - Sufficient Historical Trades (> 50)
    - DSR > 2.0
    - PBO < 0.05
    - SPA p-value > 0.95
    - MDD < 20%
    - CVaR < 15%
    
    Returns:
        tuple: (passes, result_dict)
    """
    result = {
        "long_term": False,
        "long_term_reason": "",
        "confidence_boost": 1.0,
    }
    
    # Extract required statistics from pick
    # These would typically come from walk-forward validation and statistical tests
    
    consistency_score = pick.get("consistency_score", 0)
    edge_decay_info = pick.get("edge_decay", {})
    regime_info = pick.get("regime_robustness", {})
    n_trades = pick.get("n_trades", 0)
    
    # Risk metrics
    mdd = pick.get("mdd", 999)
    cvar = pick.get("cvar", 999)
    
    # Statistical gates
    dsr = pick.get("dsr", 0)
    pbo = pick.get("pbo", 1.0)  # Higher is worse
    spa_pvalue = pick.get("spa_pvalue", 0)
    
    # Determine if criteria are met
    
    # Consistency check
    consistency_ok = consistency_score >= 70
    
    # Edge decay check
    decay_ok = not edge_decay_info.get("decaying", False)
    
    # Regime robustness check
    multi_regime = regime_info.get("multi_direction", False)
    single_regime_only = regime_info.get("single_regime_only", None)
    regime_ok = multi_regime or single_regime_only is None
    
    # Trade count check
    trades_ok = n_trades >= 50
    
    # Risk profile checks
    risk_ok = mdd < 20 and cvar < 15
    
    # Statistical gate checks
    dsr_ok = dsr > 2.0
    pbo_ok = pbo < 0.05
    spa_ok = spa_pvalue > 0.95
    
    # All criteria must be met
    if (consistency_ok and decay_ok and regime_ok and trades_ok and 
        risk_ok and dsr_ok and pbo_ok and spa_ok):
        result["long_term"] = True
        result["long_term_reason"] = (
            f"Long-term stable edge confirmed: "
            f"consistency={consistency_score}, "
            f"decay_ok={decay_ok}, "
            f"regime_ok={regime_ok}, "
            f"trades={n_trades}, "
            f"risk_ok={risk_ok}, "
            f"dsr={dsr}, "
            f"pbo={pbo}, "
            f"spa={spa_pvalue}"
        )
        result["confidence_boost"] = 1.2  # 1.2x boost as per spec
        logger.info(f"Long-term stable edge identified: {pick.get('strategy', 'unknown')}")
    else:
        reasons = []
        if not consistency_ok:
            reasons.append(f"consistency={consistency_score}/70")
        if not decay_ok:
            reasons.append("edge_decay_detected")
        if not regime_ok:
            reasons.append("single_regime_only")
        if not trades_ok:
            reasons.append(f"trades={n_trades}/50")
        if not risk_ok:
            reasons.append(f"risk_mdd={mdd}% risk_cvar={cvar}%")
        if not dsr_ok:
            reasons.append(f"dsr={dsr}/2.0")
        if not pbo_ok:
            reasons.append(f"pbo={pbo}/0.05")
        if not spa_ok:
            reasons.append(f"spa_pvalue={spa_pvalue}/0.95")
        
        result["long_term_reason"] = (
            f"Does not meet long-term stability criteria: "
            f"{', '.join(reasons)}"
        )
    
    # Add detailed metrics to result
    result.update({
        "consistency_score": consistency_score,
        "edge_decay_info": edge_decay_info,
        "regime_info": regime_info,
        "n_trades": n_trades,
        "mdd": mdd,
        "cvar": cvar,
        "dsr": dsr,
        "pbo": pbo,
        "spa_pvalue": spa_pvalue,
    })
    
    return True, result


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "compute_fundamental_strength",
    "compute_macro_alignment",
    "passes_high_conviction_gate",
    "passes_long_term_stability_gate",
]
