"""
Central Audit Trail for crypto prediction picks.

Public API:
    from audit_trail import start_run, finish_run, record_raw_pick, ...
"""

from audit_trail.recorder import (
    start_run,
    finish_run,
    record_raw_pick,
    record_consensus_pick,
    record_filter,
    record_event,
    update_pick_outcome,
    refresh_strategy_stats,
    derive_asset_class,
    compute_dedup_hash,
    record_backtest_run,
    record_backtest_batch,
)

__all__ = [
    "start_run",
    "finish_run",
    "record_raw_pick",
    "record_consensus_pick",
    "record_filter",
    "record_event",
    "update_pick_outcome",
    "refresh_strategy_stats",
    "derive_asset_class",
    "compute_dedup_hash",
    "record_backtest_run",
    "record_backtest_batch",
]
