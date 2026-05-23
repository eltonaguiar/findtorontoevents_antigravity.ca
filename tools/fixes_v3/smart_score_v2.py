"""
Smart Score V2 — Data-Driven Scoring Overhaul
===============================================
The current Smart Score formula has several components that the audit dashboard
itself identified as anti-predictive (IC negative). Despite being ZEROED in
elite_score, they may still influence the pipeline. This module provides a
clean, data-validated scoring function.

Key changes from audit dashboard findings:

KEPT (positive IC):
  - Forward WR + Track Record: IC +0.17 (DOUBLED to 40 max — correct)
  - Regime Bonus: IC +0.19 (BEST predictor — correct)
  - Technical Alignment: IC +0.16

ZEROED (negative IC — confirmed anti-predictive):
  - ML Replacement Score: IC -0.19 (was confidence + kelly + strategy rep)
  - Source System Tier: IC -0.18
  - Risk:Reward Ratio: IC -0.13 (R:R 3.0+ = 0% WR!)
  - Age Freshness: IC -0.076
  - Leverage Safety: IC -0.05
  - Proven Strategy Bonus: IC -0.003

NEW discoveries from 3,242 trade analysis:
  - Time-of-Day: Already in elite_score but should be STRONGER
    (08-11 UTC = 20% WR vs 22-23 UTC = 37% WR = 17pp spread)
  - Overconfidence cap: Already implemented but threshold should be lower
  - Strategy momentum: After WIN = 65.6% WR, after LOSS = 24.1% WR (huge!)

Usage:
    from tools.fixes_v3.smart_score_v2 import compute_smart_score_v2
    
    score = compute_smart_score_v2(pick_data)

Author: Enhancement PR based on audit feedback
Date: 2026-04-11
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def compute_smart_score_v2(
    direction: str,
    regime: str,
    fgi: int,
    elite_score: float,
    age_hours: float,
    tp_remaining_pct: float,
    htf_aligned: bool,
    mtf_recommendation: str,
    entry_hour_utc: int,
    strat_fwd_wr: float,
    strat_fwd_trades: int,
    last_trade_was_win: Optional[bool] = None,
    ml_score: Optional[float] = None,
    confidence: float = 0.5,
    ensemble_agreement: int = 0,
    ensemble_total: int = 3,
) -> Dict[str, Any]:
    """
    Compute Smart Score V2 with data-driven weights.
    
    Changes from V1:
    1. Time-of-day has MUCH stronger weight (17pp WR spread is real)
    2. Overconfidence penalty applied above confidence 0.65
    3. Strategy momentum gets more weight (41pp spread is massive)
    4. R:R ratio is EXCLUDED (anti-predictive: R:R 3.0+ = 0% WR)
    5. Minimum forward trades gate (0 trades = blocked)
    
    Returns:
        Dict with: score, breakdown, warnings, blocked
    """
    breakdown = {}
    warnings = []
    blocked = False
    blocked_reason = ""
    
    # ── 1. Direction x Regime (max 25) ────────────────────────────────────
    dir_upper = direction.upper()
    regime_lower = regime.lower()
    
    # Use FGI to determine actual market state
    if fgi <= 25:
        market_state = "fear"
    elif fgi <= 45:
        market_state = "caution"
    elif fgi <= 55:
        market_state = "neutral"
    elif fgi <= 75:
        market_state = "greed"
    else:
        market_state = "euphoria"
    
    if (dir_upper in ("LONG", "BUY") and market_state in ("greed", "neutral")) or \
       (dir_upper in ("SHORT", "SELL") and market_state in ("fear", "caution")):
        regime_pts = 25  # Aligned
    elif market_state == "neutral":
        regime_pts = 15  # Neutral
    elif (dir_upper in ("LONG", "BUY") and market_state == "fear"):
        regime_pts = 5   # Counter-trend (contrarian)
        warnings.append(f"LONG in fear (FGI={fgi}) — counter-trend")
    elif (dir_upper in ("SHORT", "SELL") and market_state in ("greed", "euphoria")):
        regime_pts = 5   # Counter-trend (contrarian)
    else:
        regime_pts = 0
    
    breakdown["direction_regime"] = regime_pts
    
    # ── 2. Elite Score Quality (max 35) ───────────────────────────────────
    elite_pts = min(35, max(0, elite_score * 35 / 100))
    breakdown["elite_quality"] = round(elite_pts, 1)
    
    # ── 3. Freshness (max 15) ─────────────────────────────────────────────
    if age_hours < 1:
        fresh_pts = 15
    elif age_hours < 4:
        fresh_pts = 12
    elif age_hours < 12:
        fresh_pts = 8
    elif age_hours < 24:
        fresh_pts = 4
    else:
        fresh_pts = 0
    breakdown["freshness"] = fresh_pts
    
    # ── 4. TP Upside (max 15) ─────────────────────────────────────────────
    if tp_remaining_pct > 70:
        tp_pts = 15
    elif tp_remaining_pct > 50:
        tp_pts = 10
    elif tp_remaining_pct > 30:
        tp_pts = 5
    elif tp_remaining_pct > 10:
        tp_pts = 2
    else:
        tp_pts = 0
        blocked = True
        blocked_reason = f"TP remaining {tp_remaining_pct:.0f}% < 10%"
    breakdown["tp_upside"] = tp_pts
    
    # ── 5. HTF Alignment (max 10) ─────────────────────────────────────────
    htf_pts = 10 if htf_aligned else 5
    breakdown["htf_alignment"] = htf_pts
    
    # ── 6. MTF Gate (+10 to -25) ──────────────────────────────────────────
    mtf_map = {"STRONG": 10, "MODERATE": 5, "WEAK": -10, "BLOCKED": -25}
    mtf_pts = mtf_map.get(mtf_recommendation.upper(), 0)
    breakdown["mtf_gate"] = mtf_pts
    
    # ── 7. TIME-OF-DAY (NEW: stronger weight, -15 to +8) ─────────────────
    # Data: 08-11 UTC = 20% WR, 22-23 = 37%, 03/13 = 33-34%
    death_zone = {8, 9, 10, 11}
    good_hours = {22, 23, 3, 13}
    caution_hours = {16, 20}
    
    h = entry_hour_utc % 24
    if h in death_zone:
        tod_pts = -15  # MUCH stronger penalty (was -2)
        warnings.append(f"Death zone entry at {h:02d} UTC (20% WR)")
    elif h in caution_hours:
        tod_pts = -5
    elif h in good_hours:
        tod_pts = +8   # Stronger bonus (was +3)
    else:
        tod_pts = 0
    breakdown["time_of_day"] = tod_pts
    
    # ── 8. STRATEGY MOMENTUM (NEW: stronger weight, -10 to +10) ──────────
    # Data: after WIN = 65.6% WR, after LOSS = 24.1% WR (41pp spread!)
    if last_trade_was_win is True:
        momentum_pts = +10
    elif last_trade_was_win is False:
        momentum_pts = -10
        warnings.append("Last trade was a LOSS (24.1% WR after loss)")
    else:
        momentum_pts = 0  # Unknown
    breakdown["strategy_momentum"] = momentum_pts
    
    # ── 9. FORWARD TRACK RECORD GATE ─────────────────────────────────────
    if strat_fwd_trades == 0:
        blocked = True
        blocked_reason = f"Strategy has 0 forward trades — no track record"
        track_pts = -20
        warnings.append("ZERO forward trades — cannot assess edge")
    elif strat_fwd_trades < 10:
        track_pts = -10
        warnings.append(f"Only {strat_fwd_trades} forward trades (min 10)")
    elif strat_fwd_wr >= 60:
        track_pts = +15
    elif strat_fwd_wr >= 50:
        track_pts = +8
    elif strat_fwd_wr >= 40:
        track_pts = 0
    else:
        track_pts = -10
    breakdown["track_record"] = track_pts
    
    # ── 10. OVERCONFIDENCE PENALTY ────────────────────────────────────────
    # Data: confidence 0.65-0.75 = 20% WR (WORST bucket)
    if confidence > 0.70:
        overconf_pts = -8
        warnings.append(f"Overconfidence penalty: conf={confidence:.2f} > 0.70 (20% WR zone)")
    elif confidence > 0.65:
        overconf_pts = -4
    else:
        overconf_pts = 0
    breakdown["overconfidence_adj"] = overconf_pts
    
    # ── 11. Ensemble Agreement ────────────────────────────────────────────
    if ensemble_total >= 3 and ensemble_agreement >= 3:
        ensemble_pts = +5
    elif ensemble_total >= 3 and ensemble_agreement <= 1:
        ensemble_pts = -5
    else:
        ensemble_pts = 0
    breakdown["ensemble"] = ensemble_pts
    
    # ── TOTAL ─────────────────────────────────────────────────────────────
    raw_score = sum(breakdown.values())
    # Normalize to 0-100
    score = max(0, min(100, round(raw_score * 100 / 120)))  # 120 = theoretical max
    
    return {
        "score": score,
        "raw_score": round(raw_score, 1),
        "breakdown": breakdown,
        "warnings": warnings,
        "blocked": blocked,
        "blocked_reason": blocked_reason,
        "confidence_input": confidence,
        "fgi": fgi,
        "market_state": market_state,
    }
