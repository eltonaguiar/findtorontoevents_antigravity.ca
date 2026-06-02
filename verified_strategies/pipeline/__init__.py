"""Shared admissibility primitives (EAGLE2 blackboxai + alpha_engine bridge)."""

from verified_strategies.pipeline.costs import CostModel, apply_costs_to_pnls
from verified_strategies.pipeline.data_admissibility import AdmissibilityRules, enforce_data_rules
from verified_strategies.pipeline.monte_carlo import block_bootstrap_pvalue
from verified_strategies.pipeline.promote import PromotionThresholds, promote_from_folds
from verified_strategies.pipeline.regimes import assign_regimes, regime_gate
from verified_strategies.pipeline.splits import WalkForwardSpec, generate_purged_embargo_folds

__all__ = [
    "AdmissibilityRules",
    "CostModel",
    "PromotionThresholds",
    "WalkForwardSpec",
    "apply_costs_to_pnls",
    "assign_regimes",
    "block_bootstrap_pvalue",
    "enforce_data_rules",
    "generate_purged_embargo_folds",
    "promote_from_folds",
    "regime_gate",
]
