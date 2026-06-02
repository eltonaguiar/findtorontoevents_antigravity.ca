"""Fold-level promotion decision (EAGLE2 §3.6)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class PromotionThresholds:
    oos_min_pf: float = 0.50
    oos_min_wr: float = 0.55
    max_drawdown_cap: float = -0.20
    mc_p_max: float = 0.10
    min_fold_pass_ratio: float = 0.70


def promote_from_folds(
    metrics_by_fold: List[Dict],
    thresholds: PromotionThresholds | None = None,
) -> bool:
    """Pass when >=70% of folds meet PF/WR/DD/MC gates."""
    thresholds = thresholds or PromotionThresholds()
    if not metrics_by_fold:
        return False

    passed = 0
    for m in metrics_by_fold:
        if (
            m.get("pf", 0) >= thresholds.oos_min_pf
            and m.get("wr", 0) >= thresholds.oos_min_wr
            and m.get("max_dd", -1) >= thresholds.max_drawdown_cap
            and m.get("mc_p", 1) <= thresholds.mc_p_max
        ):
            passed += 1

    return passed >= int(thresholds.min_fold_pass_ratio * len(metrics_by_fold))
