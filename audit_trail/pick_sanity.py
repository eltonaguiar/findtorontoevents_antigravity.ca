"""
Financial / structural sanity checks for pick dicts (audit & consensus ingest).

Used at system boundaries to drop scraper bugs and impossible economics before
scoring or consensus. Deterministic rules only — no ML.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Institutional-style bounds: wide enough for FX micro-prices & wide commodity spreads.
MIN_RISK_REWARD = 0.2
MAX_RISK_REWARD = 8.0
MAX_SCORE = 100.0
MAX_CONFIDENCE = 1.0
MAX_ML_SCORE = 1.0


def _f(x: Any) -> Optional[float]:
    if x is None or x == "":
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def pick_financial_sanity_issues(pick: Dict[str, Any]) -> List[str]:
    """Return human-readable issue codes; empty list means OK."""
    issues: List[str] = []
    if not isinstance(pick, dict):
        return ["not_a_dict"]

    ep = _f(pick.get("entry_price"))
    if ep is not None and ep <= 0:
        issues.append("entry_price_non_positive")

    tp = _f(pick.get("take_profit"))
    sl = _f(pick.get("stop_loss"))
    if tp is not None and tp <= 0:
        issues.append("take_profit_non_positive")
    if sl is not None and sl <= 0:
        issues.append("stop_loss_non_positive")

    direction = str(pick.get("direction") or pick.get("signal_type") or "").upper()
    if "SHORT" in direction or "SELL" in direction:
        d = "SHORT"
    elif "LONG" in direction or "BUY" in direction:
        d = "LONG"
    else:
        d = ""

    if ep is not None and tp is not None and sl is not None and ep > 0 and d:
        if d == "LONG":
            # Long: profit if price rises to TP; stop below entry
            if not (sl < ep and tp > ep):
                issues.append("long_tp_sl_geometry")
        elif d == "SHORT":
            if not (tp < ep and sl > ep):
                issues.append("short_tp_sl_geometry")

    rr = _f(pick.get("risk_reward"))
    if rr is not None:
        if rr < MIN_RISK_REWARD or rr > MAX_RISK_REWARD:
            issues.append("risk_reward_out_of_range")

    # Derive R:R when not supplied
    if rr is None and ep and tp and sl and ep > 0:
        if d == "LONG":
            reward = abs(tp - ep)
            risk = abs(ep - sl)
        elif d == "SHORT":
            reward = abs(ep - tp)
            risk = abs(sl - ep)
        else:
            reward = risk = 0.0
        if risk > 0 and reward > 0:
            derived = reward / risk
            if derived < MIN_RISK_REWARD or derived > MAX_RISK_REWARD:
                issues.append("derived_rr_out_of_range")

    sc = _f(pick.get("score"))
    if sc is not None and (sc < 0 or sc > MAX_SCORE):
        issues.append("score_out_of_range")

    conf = _f(pick.get("confidence"))
    if conf is not None and (conf < 0 or conf > MAX_CONFIDENCE):
        issues.append("confidence_out_of_range")

    ml = _f(pick.get("ml_score"))
    if ml is not None and (ml < 0 or ml > MAX_ML_SCORE):
        issues.append("ml_score_out_of_range")

    return issues


def passes_pick_sanity(pick: Dict[str, Any]) -> bool:
    return len(pick_financial_sanity_issues(pick)) == 0


def sanity_summary(picks: List[Dict[str, Any]]) -> Tuple[int, int, Dict[str, int]]:
    """Returns (ok_count, fail_count, issue_code_counts)."""
    ok = 0
    fail = 0
    codes: Dict[str, int] = {}
    for p in picks:
        iss = pick_financial_sanity_issues(p)
        if iss:
            fail += 1
            for c in iss:
                codes[c] = codes.get(c, 0) + 1
        else:
            ok += 1
    return ok, fail, codes
