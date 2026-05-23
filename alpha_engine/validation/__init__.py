"""Validation engine - the 'truth machine' for strategy evaluation."""
from .walk_forward import WalkForwardValidator, TradeWalkForwardValidator
from .purged_cv import PurgedKFoldCV
from .monte_carlo import MonteCarloSimulator
from .stress_test import StressTester
from .metrics import PerformanceMetrics

try:
    from .sharpe_metrics import (
        compute_sharpe,
        deflated_sharpe_ratio,
        probabilistic_sharpe_ratio,
        compute_tail_risk_metrics,
    )
except ImportError:
    # scipy not installed — sharpe_metrics functions unavailable
    compute_sharpe = None
    deflated_sharpe_ratio = None
    probabilistic_sharpe_ratio = None
    compute_tail_risk_metrics = None

# Layer 4 statistical gates (numpy-only, no scipy)
from .statistical_gates import (
    benjamini_hochberg,
    deflated_sharpe_ratio as dsr_gate,
    newey_west_tstat,
    power_analysis,
    run_all_gates,
)
