"""Alpha Engine -- institutional-grade trading strategy infrastructure.

Modules:
- track_calculator: per-(strategy,symbol,direction) forward WR%
- statistical_rigor: PSR, DSR, bootstrap CI, MTRL
- decay_tracker: auto-demotion based on rolling Sharpe decline
- hedge_fund_quality_gate: per-asset-class quality gates
- outcome_resolver: trade outcome resolution engine

DecayTracker imports numpy; it is lazily exported so lightweight tools
(`python -m alpha_engine.continuous_improvement_monitor`, CI smoke, etc.)
do not pull numpy transitively unless those symbols are referenced.
"""

from __future__ import annotations

from typing import Any

from alpha_engine.track_calculator import TrackCalculator, get_track_wr, find_asymmetries

__version__ = "2.0.0"


def __getattr__(name: str) -> Any:
    if name == "DecayTracker":
        from alpha_engine.decay_tracker import DecayTracker

        return DecayTracker
    if name == "StrategyStatus":
        from alpha_engine.decay_tracker import StrategyStatus

        return StrategyStatus
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "TrackCalculator",
    "get_track_wr",
    "find_asymmetries",
    "DecayTracker",
    "StrategyStatus",
]
