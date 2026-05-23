"""
Heuristic tier lifecycle suggestions from aggregate stats (not automatic promotion).

Input shape matches `tools/tier_significance.py` tier rows or a simple dict:
  tier, n, win_rate, profit_factor (optional), p_value_two_sided_z (optional)
"""
from __future__ import annotations

from typing import Any

PROMOTION_HINTS = {
    "B_to_A": {"min_n": 30, "min_wr": 0.60, "min_pf": 1.5},
    "A_to_S": {"min_n": 50, "min_wr": 0.65, "min_pf": 2.0},
}

DEMOTION_HINTS = {
    "low_wr": {"min_n": 10, "max_wr": 0.45},
}


def evaluate_tier_row(stats: dict[str, Any]) -> dict[str, Any]:
    tier = str(stats.get("tier") or "?")
    n = int(stats.get("n") or 0)
    wr = float(stats.get("win_rate") or 0)
    pf = stats.get("profit_factor")
    pf_f = float(pf) if pf is not None else None

    if tier == "B":
        r = PROMOTION_HINTS["B_to_A"]
        if n >= r["min_n"] and wr >= r["min_wr"] and (pf_f is None or pf_f >= r["min_pf"]):
            return {
                "action": "CONSIDER_PROMOTION_REVIEW",
                "target": "A",
                "reason": "meets B_to_A heuristic thresholds",
            }

    if tier == "A":
        r = PROMOTION_HINTS["A_to_S"]
        if n >= r["min_n"] and wr >= r["min_wr"] and (pf_f is None or pf_f >= r["min_pf"]):
            return {
                "action": "CONSIDER_PROMOTION_REVIEW",
                "target": "S",
                "reason": "meets A_to_S heuristic thresholds",
            }

    d = DEMOTION_HINTS["low_wr"]
    if n >= d["min_n"] and wr < d["max_wr"]:
        return {
            "action": "CONSIDER_DEMOTION_OR_RETIRE",
            "reason": "win_rate below %.0f%% with n=%s" % (100 * d["max_wr"], n),
        }

    return {"action": "HOLD", "reason": "no heuristic trigger"}
