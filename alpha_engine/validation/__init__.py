"""Validation engine - the 'truth machine' for strategy evaluation."""
from .walk_forward import WalkForwardValidator
from .purged_cv import PurgedKFoldCV
from .monte_carlo import MonteCarloSimulator
from .stress_test import StressTester
from .metrics import PerformanceMetrics
