"""
Profitable-but-Filtered Observational Lane (starter)

Addresses the P0 incident:
"Profitable-but-filtered picks are not surfaced anywhere"
(OVERALL P0 in incidents/enhancements dashboard + EAGLE QUICK_WINS).

This is deliberately *observational only*. It never weakens live gates,
never changes scoring, and never promotes anything into active/smart feeds.

Usage (to be wired from dashboard_generator.py filtered_out path):
    from audit_trail.profitable_filtered_observer import record_if_later_profitable

    for rejected in filtered_out:
        record_if_later_profitable(rejected, closed_picks_lookup)

The first implementation writes a daily JSONL artifact under
audit_dashboard/data/profitable_but_filtered_YYYY-MM-DD.jsonl
(one line per later-profitable reject with first_failed_gate + eventual PnL).

This gives the first durable false-negative signal for gate calibration
without any production behavior change.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

DATA_DIR = Path("audit_dashboard/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def record_if_later_profitable(
    rejected_pick: Dict[str, Any],
    closed_lookup: Dict[str, Dict[str, Any]],
    *,
    min_pnl_pct: float = 0.5,
) -> bool:
    """
    If a previously gate-rejected pick later closed with positive PnL,
    append a one-line observation.

    Returns True if a record was written.
    """
    key = _pick_key(rejected_pick)
    if not key or key not in closed_lookup:
        return False

    closed = closed_lookup[key]
    pnl = float(closed.get("pnl_pct") or 0.0)
    if pnl < min_pnl_pct:
        return False

    first_failed = rejected_pick.get("_first_failed_gate") or rejected_pick.get("failed_gate") or "unknown_gate"

    record = {
        "signal_ts": rejected_pick.get("signal_time") or rejected_pick.get("created_at"),
        "strategy": rejected_pick.get("strategy"),
        "symbol": rejected_pick.get("symbol"),
        "direction": rejected_pick.get("direction"),
        "first_failed_gate": first_failed,
        "gate_score_at_reject": rejected_pick.get("score"),
        "later_pnl_pct": round(pnl, 4),
        "later_exit_reason": closed.get("exit_reason"),
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }

    path = DATA_DIR / f"profitable_but_filtered_{_today()}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")

    return True


def _pick_key(p: Dict[str, Any]) -> Optional[str]:
    """Stable key for joining a rejected pick to its later closed outcome."""
    sym = (p.get("symbol") or "").upper().strip()
    strat = (p.get("strategy") or "").strip()
    direction = (p.get("direction") or "").upper().strip()
    if not (sym and strat and direction):
        return None
    # Best-effort: many systems already carry a stable signal_id / pick_id
    if p.get("signal_id"):
        return f"id:{p['signal_id']}"
    return f"{sym}|{strat}|{direction}"


# Convenience batch helper for callers that already have the filtered_out list
def record_batch_if_later_profitable(
    filtered_out: Iterable[Dict[str, Any]],
    closed_lookup: Dict[str, Dict[str, Any]],
) -> int:
    count = 0
    for p in filtered_out:
        if record_if_later_profitable(p, closed_lookup):
            count += 1
    return count
