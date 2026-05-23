"""
Leverage Safety Gate — Tags each pick with a max recommended leverage based on risk factors.

Scoring system (each factor 0-5 points, total 30):
  - Volatility (ATR-based)
  - Correlation risk (same-direction active picks)
  - Entry quality (proximity to stop loss / support)
  - Market regime (fear & greed index)
  - R:R quality (reward-to-risk ratio)
  - Beta score (confluence quality)

Leverage mapping:
  total >= 25  -> max 20x
  total >= 20  -> max 10x
  total >= 15  -> max 5x
  total < 15   -> max 2x (avoid leveraged trading)
"""

import json
import os
from typing import Any, Dict, List, Optional

# ── Warning thresholds ──
WARNING_THRESHOLDS = {
    "single_factor_low": {
        "threshold": 1,
        "message": "At least one risk factor scored critically low"
    },
    "total_high_risk": {
        "threshold": 15,
        "message": "HIGH RISK — not suitable for leveraged trading"
    },
    "bear_correlated_longs": {
        "regime_max": 1,
        "correlation_max": 2,
        "message": "DANGER — correlated longs in bear market"
    },
}


def _float(val) -> float:
    """Safely convert a value to float."""
    try:
        return float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def _load_aggregated_picks() -> List[Dict]:
    """Load active aggregated picks from disk for correlation analysis."""
    try:
        agg_path = os.path.join(os.path.dirname(__file__), "data", "aggregated_picks.json")
        if os.path.exists(agg_path):
            with open(agg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for key in ("consensus_picks", "active_picks", "picks", "active"):
                    if key in data and isinstance(data[key], list):
                        return data[key]
        return []
    except Exception:
        return []


def _score_volatility(pick: Dict) -> Dict[str, Any]:
    """Score volatility based on ATR proxy (0-5 points)."""
    atr_pct = _float(pick.get("atr_pct", 0))

    # If no explicit atr_pct, try to compute from high/low/entry
    if atr_pct <= 0:
        high = _float(pick.get("high", 0))
        low = _float(pick.get("low", 0))
        entry = _float(pick.get("entry", pick.get("entry_price", 0)))
        if high > 0 and low > 0 and entry > 0:
            atr_pct = abs(high - low) / entry * 100

    # If still no data, estimate from TP/SL spread as a proxy
    if atr_pct <= 0:
        entry = _float(pick.get("entry", pick.get("entry_price", 0)))
        tp = _float(pick.get("tp", pick.get("take_profit", pick.get("targetPrice", 0))))
        sl = _float(pick.get("sl", pick.get("stop_loss", pick.get("stopPrice", 0))))
        if entry > 0 and tp > 0 and sl > 0:
            spread = abs(tp - sl) / entry * 100
            atr_pct = spread / 3.0  # rough approximation

    if atr_pct <= 0:
        # No data at all — assume moderate volatility
        return {"score": 3, "max": 5, "detail": "No volatility data, assuming moderate"}

    if atr_pct < 1:
        score = 5
        detail = f"ATR/entry={atr_pct:.1f}%, very low vol"
    elif atr_pct < 2:
        score = 4
        detail = f"ATR/entry={atr_pct:.1f}%, low vol"
    elif atr_pct < 3:
        score = 3
        detail = f"ATR/entry={atr_pct:.1f}%, moderate vol"
    elif atr_pct < 5:
        score = 2
        detail = f"ATR/entry={atr_pct:.1f}%, high vol"
    else:
        score = 1
        detail = f"ATR/entry={atr_pct:.1f}%, extreme vol"

    return {"score": score, "max": 5, "detail": detail}


def _score_correlation(pick: Dict, aggregated_picks: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Score correlation risk based on same-direction active picks (0-5 points)."""
    if aggregated_picks is None:
        aggregated_picks = _load_aggregated_picks()

    direction = str(pick.get("direction", "LONG")).upper()
    symbol = str(pick.get("symbol", ""))

    # Count OTHER active picks with same direction (exclude this pick's own symbol)
    same_dir_count = 0
    for p in aggregated_picks:
        p_dir = str(p.get("direction", "")).upper()
        p_sym = str(p.get("symbol", ""))
        if p_dir == direction and p_sym != symbol:
            same_dir_count += 1

    if same_dir_count <= 1:
        score = 5
        detail = f"{same_dir_count} same-direction positions, low correlation"
    elif same_dir_count <= 3:
        score = 4
        detail = f"{same_dir_count} same-direction positions"
    elif same_dir_count <= 5:
        score = 3
        detail = f"{same_dir_count} same-direction positions, moderate"
    elif same_dir_count <= 7:
        score = 2
        detail = f"{same_dir_count} same-direction positions, high"
    else:
        score = 1
        detail = f"{same_dir_count} same-direction positions, very high"

    return {"score": score, "max": 5, "detail": detail}


def _score_entry_quality(pick: Dict) -> Dict[str, Any]:
    """Score entry quality based on proximity to stop loss / support (0-5 points)."""
    entry = _float(pick.get("entry", pick.get("entry_price", 0)))
    sl = _float(pick.get("sl", pick.get("stop_loss", pick.get("stopPrice", 0))))

    if entry <= 0 or sl <= 0:
        return {"score": 3, "max": 5, "detail": "Missing entry/SL data, assuming moderate"}

    entry_to_sl_pct = abs(entry - sl) / entry * 100

    if entry_to_sl_pct < 1.5:
        score = 5
        detail = f"Entry-to-SL={entry_to_sl_pct:.1f}%, tight stop (near support)"
    elif entry_to_sl_pct < 3:
        score = 4
        detail = f"Entry-to-SL={entry_to_sl_pct:.1f}%, good"
    elif entry_to_sl_pct < 5:
        score = 3
        detail = f"Entry-to-SL={entry_to_sl_pct:.1f}%, moderate"
    elif entry_to_sl_pct < 7:
        score = 2
        detail = f"Entry-to-SL={entry_to_sl_pct:.1f}%, wide stop"
    else:
        score = 1
        detail = f"Entry-to-SL={entry_to_sl_pct:.1f}%, very wide stop"

    return {"score": score, "max": 5, "detail": detail}


def _score_regime(pick: Dict, market_context: Optional[Dict] = None) -> Dict[str, Any]:
    """Score market regime based on Fear & Greed index (0-5 points)."""
    if market_context is None:
        market_context = {}

    # Support both field names (fear_greed and fear_greed_index)
    fg = market_context.get("fear_greed", market_context.get("fear_greed_index", 50))
    fg = _float(fg)
    direction = str(pick.get("direction", "LONG")).upper()
    is_long = direction in ("LONG", "BUY")

    if is_long:
        # For longs: greed = good, fear = bad
        if fg > 60:
            score = 5
            detail = f"F&G={fg:.0f} (greed), favorable for longs"
        elif fg >= 40:
            score = 3
            detail = f"F&G={fg:.0f} (neutral)"
        elif fg >= 25:
            score = 1
            detail = f"F&G={fg:.0f} (fear), longs risky"
        else:
            score = 0
            detail = f"F&G={fg:.0f} (extreme fear), longs very risky"
    else:
        # For shorts: fear = good, greed = bad
        if fg < 25:
            score = 5
            detail = f"F&G={fg:.0f} (extreme fear), favorable for shorts"
        elif fg < 40:
            score = 4
            detail = f"F&G={fg:.0f} (fear), good for shorts"
        elif fg <= 60:
            score = 3
            detail = f"F&G={fg:.0f} (neutral)"
        elif fg <= 75:
            score = 2
            detail = f"F&G={fg:.0f} (greed), shorts risky"
        else:
            score = 1
            detail = f"F&G={fg:.0f} (extreme greed), shorts very risky"

    return {"score": score, "max": 5, "detail": detail}


def _score_rr_quality(pick: Dict) -> Dict[str, Any]:
    """Score reward-to-risk ratio (0-5 points)."""
    entry = _float(pick.get("entry", pick.get("entry_price", 0)))
    tp = _float(pick.get("tp", pick.get("take_profit", pick.get("targetPrice", 0))))
    sl = _float(pick.get("sl", pick.get("stop_loss", pick.get("stopPrice", 0))))

    if entry <= 0 or tp <= 0 or sl <= 0:
        # Try rr_ratio if already computed
        rr = _float(pick.get("rr_ratio", 0))
        if rr > 0:
            pass
        else:
            return {"score": 3, "max": 5, "detail": "Missing price data, assuming moderate R:R"}
    else:
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = reward / risk if risk > 0 else 0

    if rr >= 3.0:
        score = 5
        detail = f"R:R={rr:.1f}:1, excellent"
    elif rr >= 2.5:
        score = 4
        detail = f"R:R={rr:.1f}:1, very good"
    elif rr >= 2.0:
        score = 3
        detail = f"R:R={rr:.1f}:1, good"
    elif rr >= 1.5:
        score = 2
        detail = f"R:R={rr:.1f}:1, marginal"
    else:
        score = 1
        detail = f"R:R={rr:.1f}:1, poor"

    return {"score": score, "max": 5, "detail": detail}


def _score_beta(pick: Dict) -> Dict[str, Any]:
    """Score beta confluence quality (0-5 points)."""
    beta = _float(pick.get("beta_score", 0))

    if beta <= 0:
        return {"score": 3, "max": 5, "detail": "No beta score available"}

    if beta >= 80:
        score = 5
        detail = f"beta={beta:.0f}, excellent confluence"
    elif beta >= 70:
        score = 4
        detail = f"beta={beta:.0f}, strong confluence"
    elif beta >= 60:
        score = 3
        detail = f"beta={beta:.0f}, moderate confluence"
    elif beta >= 50:
        score = 2
        detail = f"beta={beta:.0f}, weak confluence"
    else:
        score = 1
        detail = f"beta={beta:.0f}, very weak confluence"

    return {"score": score, "max": 5, "detail": detail}


def _compute_leverage(total_score: int) -> int:
    """Map total score to max safe leverage."""
    if total_score >= 25:
        return 20
    elif total_score >= 20:
        return 10
    elif total_score >= 15:
        return 5
    else:
        return 2


def _build_warnings(factors: Dict[str, Dict], total_score: int) -> str:
    """Build warning string from factor scores and thresholds."""
    warnings = []

    # Check individual factor critical scores (0-1)
    low_factors = []
    for name, f in factors.items():
        if f["score"] <= WARNING_THRESHOLDS["single_factor_low"]["threshold"]:
            low_factors.append(name)

    if low_factors:
        warnings.append(f"Critical risk in: {', '.join(low_factors)}")

    # Total score high risk
    if total_score < WARNING_THRESHOLDS["total_high_risk"]["threshold"]:
        warnings.append(WARNING_THRESHOLDS["total_high_risk"]["message"])

    # Bear regime + high correlation (correlated longs in bear market)
    regime_score = factors.get("regime", {}).get("score", 3)
    corr_score = factors.get("correlation", {}).get("score", 3)
    bear_thresh = WARNING_THRESHOLDS["bear_correlated_longs"]
    if regime_score <= bear_thresh["regime_max"] and corr_score <= bear_thresh["correlation_max"]:
        warnings.append(bear_thresh["message"])

    return " | ".join(warnings) if warnings else ""


def assess_leverage_safety(pick: Dict, market_context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Assess the maximum safe leverage for a given pick based on multiple risk factors.

    Args:
        pick: Dict with pick data (symbol, direction, entry, tp, sl, beta_score, etc.)
        market_context: Optional dict with market data (fear_greed / fear_greed_index, etc.)

    Returns:
        Dict with max_safe_leverage, leverage_factors, total_score, and optional warning.
    """
    # Load aggregated picks once for correlation scoring
    aggregated_picks = _load_aggregated_picks()

    # Score each factor
    factors = {
        "volatility": _score_volatility(pick),
        "correlation": _score_correlation(pick, aggregated_picks),
        "entry_quality": _score_entry_quality(pick),
        "regime": _score_regime(pick, market_context),
        "rr_quality": _score_rr_quality(pick),
        "beta_score": _score_beta(pick),
    }

    total_score = sum(f["score"] for f in factors.values())
    max_leverage = _compute_leverage(total_score)
    warning = _build_warnings(factors, total_score)

    result = {
        "max_safe_leverage": max_leverage,
        "leverage_factors": factors,
        "total_score": total_score,
    }

    if warning:
        result["warning"] = warning

    return result
