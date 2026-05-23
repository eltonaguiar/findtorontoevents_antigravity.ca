"""
Unified forward win-rate reads for dashboard / bundle payloads.

Legacy `forward_win_rate` is often unset on audit picks; live strategy-level
`strat_fwd_wr` and baby-dashboard `forward_metrics.win_rate` carry the signal.
"""

from __future__ import annotations

from typing import Any, Mapping


def forward_win_rate_percent(record: Mapping[str, Any]) -> float:
    """
    Return forward win rate on a 0-100 percent scale.

    Priority:
      1. strat_fwd_wr (strategy-level field aligned with audit stamping)
      2. forward_metrics.win_rate (nested baby-strats / battleground window)
      3. forward_win_rate (legacy flat field)

    Values <= 1 are treated as a ratio (0.52 -> 52%); values > 1 as percent.
    """
    raw: Any = record.get("strat_fwd_wr")
    if raw is None:
        fm = record.get("forward_metrics")
        if isinstance(fm, Mapping):
            raw = fm.get("win_rate")
    if raw is None:
        raw = record.get("forward_win_rate")
    if raw is None:
        return 0.0
    try:
        x = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if x <= 1.0:
        return x * 100.0
    return x
