"""
Regime-FGI Synchronizer
========================
Current problem: Fear & Greed Index = 11 (EXTREME FEAR) but regime = "NEUTRAL".
The regime detector and FGI are out of sync, leading to:
- LONG trades being generated in extreme fear
- No defensive position sizing being applied
- Strategies with SHORT bias not being prioritized

This module ensures regime and FGI are consistent. When FGI says extreme fear
but regime says neutral, we override to the more conservative assessment.

From the audit:
- "Regime Bonus" has IC = +0.19 (BEST IC predictor in Elite Score)
- "SHORT in bull = -30 penalty" is correctly implemented
- But regime itself is miscalibrated when FGI diverges

Usage:
    from tools.fixes_v3.regime_fgi_sync import sync_regime_fgi
    
    corrected = sync_regime_fgi(regime="neutral", fgi=11)
    # Returns: {"regime": "extreme_fear", "source": "fgi_override", ...}

Author: Enhancement PR based on audit feedback
Date: 2026-04-11
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# FGI ranges and their regime implications
FGI_TO_REGIME = {
    # FGI 0-10: Extreme Fear → regime should be extreme_fear/panic
    (0, 10): {
        "regime": "extreme_fear",
        "position_scalar": 0.15,
        "preferred_direction": "SHORT",
        "contrarian_long": True,  # Extreme fear CAN be contrarian LONG opportunity
        "description": "FGI 0-10: Market capitulation. Contrarian opportunities exist but high risk.",
    },
    # FGI 11-25: Fear → regime should be panic/fear
    (11, 25): {
        "regime": "fear",
        "position_scalar": 0.25,
        "preferred_direction": "SHORT",
        "contrarian_long": True,
        "description": "FGI 11-25: Elevated fear. SHORT-biased, selective contrarian LONG.",
    },
    # FGI 26-45: Caution → regime should be caution
    (26, 45): {
        "regime": "caution",
        "position_scalar": 0.50,
        "preferred_direction": "BOTH",
        "contrarian_long": False,
        "description": "FGI 26-45: Below-average sentiment. Cautious trading.",
    },
    # FGI 46-55: Neutral
    (46, 55): {
        "regime": "neutral",
        "position_scalar": 1.00,
        "preferred_direction": "BOTH",
        "contrarian_long": False,
        "description": "FGI 46-55: Balanced sentiment. Normal operations.",
    },
    # FGI 56-75: Greed
    (56, 75): {
        "regime": "greed",
        "position_scalar": 0.75,
        "preferred_direction": "LONG",
        "contrarian_long": False,
        "description": "FGI 56-75: Greedy. Ride momentum but reduce size.",
    },
    # FGI 76-90: Extreme Greed
    (76, 90): {
        "regime": "extreme_greed",
        "position_scalar": 0.50,
        "preferred_direction": "SHORT",
        "contrarian_long": False,
        "description": "FGI 76-90: Extreme greed. Contrarian SHORT opportunities.",
    },
    # FGI 91-100: Euphoria
    (91, 100): {
        "regime": "euphoria",
        "position_scalar": 0.25,
        "preferred_direction": "SHORT",
        "contrarian_long": False,
        "description": "FGI 91-100: Euphoria/mania. Strong SHORT bias.",
    },
}


def sync_regime_fgi(
    regime: str,
    fgi: int,
    override_threshold: int = 15,
) -> Dict[str, Any]:
    """
    Synchronize regime classification with Fear & Greed Index.
    
    When FGI and regime disagree by more than 1 category, use the more
    conservative (more fearful/cautious) assessment.
    
    Args:
        regime: Current regime from system ("neutral", "panic", etc.)
        fgi: Fear & Greed Index value (0-100)
        override_threshold: FGI deviation that triggers override
        
    Returns:
        Dict with corrected regime info
    """
    # Get FGI-implied regime
    fgi_regime_info = None
    for (lo, hi), info in FGI_TO_REGIME.items():
        if lo <= fgi <= hi:
            fgi_regime_info = info
            break
    
    if fgi_regime_info is None:
        fgi_regime_info = FGI_TO_REGIME[(46, 55)]  # Default neutral
    
    fgi_regime = fgi_regime_info["regime"]
    
    # Regime severity ordering (lower = more fearful)
    severity = {
        "extreme_fear": 0, "panic": 1, "fear": 2, "caution": 3,
        "warning": 3, "neutral": 4, "greed": 5, "extreme_greed": 6,
        "euphoria": 7, "risk_on": 5, "risk_off": 2, "crisis": 0,
    }
    
    regime_sev = severity.get(regime.lower(), 4)  # Default neutral
    fgi_sev = severity.get(fgi_regime, 4)
    
    # Use the MORE CONSERVATIVE (lower severity) assessment
    if abs(regime_sev - fgi_sev) >= 2:
        # Significant disagreement — override to more conservative
        if fgi_sev < regime_sev:
            # FGI says more fearful than regime → trust FGI
            final_regime = fgi_regime
            source = "fgi_override"
            reason = (
                f"FGI={fgi} implies '{fgi_regime}' but system says '{regime}'. "
                f"Using FGI (more conservative). Disagreement: {abs(regime_sev - fgi_sev)} levels."
            )
        else:
            # Regime says more fearful than FGI → trust regime
            final_regime = regime.lower()
            source = "system_regime"
            reason = (
                f"System regime '{regime}' is more conservative than FGI={fgi} "
                f"(implies '{fgi_regime}'). Keeping system regime."
            )
        
        logger.warning(f"Regime-FGI sync: {reason}")
    else:
        # Agreement or minor difference
        final_regime = fgi_regime if fgi_sev <= regime_sev else regime.lower()
        source = "consensus"
        reason = f"FGI={fgi} and regime='{regime}' are in agreement."
    
    return {
        "regime": final_regime,
        "fgi": fgi,
        "original_regime": regime,
        "fgi_implied_regime": fgi_regime,
        "source": source,
        "reason": reason,
        "position_scalar": fgi_regime_info["position_scalar"],
        "preferred_direction": fgi_regime_info["preferred_direction"],
        "contrarian_long_allowed": fgi_regime_info["contrarian_long"],
        "description": fgi_regime_info["description"],
    }


def apply_regime_to_pick(
    pick: Dict,
    regime_info: Dict,
) -> Dict[str, Any]:
    """
    Apply regime assessment to a pick. Modifies the pick in-place and
    returns a gate result.
    
    Rules:
    1. If pick direction conflicts with preferred_direction → penalize or block
    2. Apply position_scalar to any position sizing
    3. Add regime metadata to pick
    """
    direction = pick.get("direction", "LONG").upper()
    preferred = regime_info["preferred_direction"]
    score = pick.get("smart_score", 0)
    
    result = {
        "pick_symbol": pick.get("symbol"),
        "pick_direction": direction,
        "regime": regime_info["regime"],
        "fgi": regime_info["fgi"],
    }
    
    # Check direction alignment
    if preferred == "BOTH":
        result["direction_check"] = "PASS"
        result["score_adjustment"] = 0
    elif preferred == "SHORT" and direction in ("LONG", "BUY"):
        if regime_info.get("contrarian_long_allowed") and score >= 85:
            result["direction_check"] = "CONTRARIAN_ALLOWED"
            result["score_adjustment"] = -15  # Penalize but allow
            result["reason"] = (
                f"LONG in {regime_info['regime']} regime (FGI={regime_info['fgi']}). "
                f"Allowed as contrarian (score {score} >= 85) but penalized -15."
            )
        else:
            result["direction_check"] = "BLOCKED"
            result["score_adjustment"] = -100
            result["reason"] = (
                f"BLOCKED: LONG in {regime_info['regime']} regime (FGI={regime_info['fgi']}). "
                f"Only SHORT or contrarian LONG with score >= 85 allowed."
            )
    elif preferred == "LONG" and direction in ("SHORT", "SELL"):
        result["direction_check"] = "PENALIZED"
        result["score_adjustment"] = -10
        result["reason"] = f"SHORT in {regime_info['regime']} (greedy) → -10 penalty"
    else:
        result["direction_check"] = "ALIGNED"
        result["score_adjustment"] = +5  # Bonus for regime alignment
    
    result["position_scalar"] = regime_info["position_scalar"]
    
    return result
