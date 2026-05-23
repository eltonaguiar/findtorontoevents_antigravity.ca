"""
Status Enforcer — Sequential Promotion Ladder & Demotion Triggers

Implements the TESTING_PROTOCOL.MD promotion model:
  CANDIDATE -> BACKTEST_PASS -> WF_PASS -> STATS_PASS -> FORWARD_PASS -> PRODUCTION

Demotion triggers (PRODUCTION -> PROBATION):
  - Rolling 20-trade expectancy < 0
  - Max drawdown > 15%
  - Win-rate drop > 10 percentage points below baseline

Probation -> BANNED:
  - 30 days with no recovery
  - 3 consecutive negative evaluation windows

Storage: JSON file at alpha_engine/data/strategy_status_history.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROMOTION_LADDER: List[str] = [
    "CANDIDATE",
    "BACKTEST_PASS",
    "WF_PASS",
    "STATS_PASS",
    "FORWARD_PASS",
    "PRODUCTION",
]

DEMOTION_STATUSES: List[str] = ["PROBATION", "BANNED"]

ALL_STATUSES: List[str] = PROMOTION_LADDER + DEMOTION_STATUSES

# Evidence keys required at each promotion step
REQUIRED_EVIDENCE: Dict[str, List[str]] = {
    "BACKTEST_PASS": ["backtest_sharpe", "backtest_trades", "backtest_win_rate"],
    "WF_PASS": ["wf_sharpe", "wf_profit_factor", "wf_windows"],
    "STATS_PASS": ["p_value", "correction_method", "significant"],
    "FORWARD_PASS": ["forward_trades", "forward_expectancy", "forward_days"],
    "PRODUCTION": ["gate_score", "approval_source"],
}

# Demotion thresholds
EXPECTANCY_WINDOW: int = 20
MAX_DD_THRESHOLD: float = 0.15       # 15%
WR_DROP_THRESHOLD: float = 10.0      # 10 percentage points
PROBATION_RECOVERY_DAYS: int = 30
CONSECUTIVE_NEGATIVE_WINDOWS: int = 3

# Default history file
_DEFAULT_HISTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "strategy_status_history.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_history(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or _DEFAULT_HISTORY_PATH
    if p.exists():
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"transitions": []}


def _save_history(data: Dict[str, Any], path: Optional[Path] = None) -> None:
    p = path or _DEFAULT_HISTORY_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# 1) Status transition enforcement
# ---------------------------------------------------------------------------

def validate_transition(
    strategy_id: str,
    from_status: str,
    to_status: str,
    evidence: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    """Validate whether a status transition is allowed.

    Rules:
      - Promotion must follow the ladder sequentially (no skipping).
      - Demotion from PRODUCTION -> PROBATION is always allowed with reason.
      - Demotion from PROBATION -> BANNED is always allowed with reason.
      - Re-entry from PROBATION back into the ladder requires restart at CANDIDATE.
      - BANNED strategies cannot transition (must be manually unbanned).

    Returns:
        (allowed, reason) tuple.
    """
    if evidence is None:
        evidence = {}

    # Validate statuses are known
    if from_status not in ALL_STATUSES:
        return False, f"Unknown from_status: {from_status}"
    if to_status not in ALL_STATUSES:
        return False, f"Unknown to_status: {to_status}"

    # BANNED is terminal
    if from_status == "BANNED":
        return False, "BANNED strategies cannot transition. Manual unban required."

    # Demotion paths
    if from_status == "PRODUCTION" and to_status == "PROBATION":
        return True, "Demotion from PRODUCTION to PROBATION allowed."
    if from_status == "PROBATION" and to_status == "BANNED":
        return True, "Demotion from PROBATION to BANNED allowed."
    if from_status == "PROBATION" and to_status == "CANDIDATE":
        return True, "Re-entry from PROBATION restarts at CANDIDATE."

    # Promotion: must be exactly one step up the ladder
    if from_status in PROMOTION_LADDER and to_status in PROMOTION_LADDER:
        from_idx = PROMOTION_LADDER.index(from_status)
        to_idx = PROMOTION_LADDER.index(to_status)

        if to_idx != from_idx + 1:
            if to_idx <= from_idx:
                return False, (
                    f"Cannot move backwards on the ladder: "
                    f"{from_status} -> {to_status}. "
                    f"Use demotion path instead."
                )
            skipped = PROMOTION_LADDER[from_idx + 1: to_idx]
            return False, (
                f"Cannot skip levels. {from_status} -> {to_status} skips: "
                f"{', '.join(skipped)}. Promote one step at a time."
            )

        # Check required evidence for the target status
        required_keys = REQUIRED_EVIDENCE.get(to_status, [])
        missing = [k for k in required_keys if k not in evidence]
        if missing:
            return False, (
                f"Missing required evidence for {to_status}: "
                f"{', '.join(missing)}"
            )

        return True, f"Promotion {from_status} -> {to_status} approved."

    # Any other transition is invalid
    return False, (
        f"Invalid transition: {from_status} -> {to_status}. "
        f"Only sequential promotion or defined demotion paths allowed."
    )


# ---------------------------------------------------------------------------
# 2) Demotion checker
# ---------------------------------------------------------------------------

def check_demotion_triggers(
    strategy_id: str,
    recent_trades: List[Dict[str, Any]],
    baseline_win_rate: float = 0.0,
    current_status: str = "PRODUCTION",
    probation_start_date: Optional[str] = None,
    negative_windows: int = 0,
) -> List[Dict[str, str]]:
    """Check whether demotion triggers have fired.

    Args:
        strategy_id: Strategy identifier.
        recent_trades: List of trade dicts, each with at least 'pnl_pct' key.
                       Ordered oldest-first.
        baseline_win_rate: Historical win rate (0-100 scale) for comparison.
        current_status: Current strategy status.
        probation_start_date: ISO date string when probation started (if applicable).
        negative_windows: Count of consecutive negative evaluation windows.

    Returns:
        List of triggered demotion dicts with 'trigger', 'from_status',
        'to_status', and 'reason' keys.
    """
    triggers: List[Dict[str, str]] = []

    if current_status == "PRODUCTION":
        triggers.extend(
            _check_production_triggers(
                strategy_id, recent_trades, baseline_win_rate
            )
        )
    elif current_status == "PROBATION":
        triggers.extend(
            _check_probation_triggers(
                strategy_id, probation_start_date, negative_windows
            )
        )

    return triggers


def _check_production_triggers(
    strategy_id: str,
    recent_trades: List[Dict[str, Any]],
    baseline_win_rate: float,
) -> List[Dict[str, str]]:
    """Check PRODUCTION -> PROBATION triggers."""
    triggers: List[Dict[str, str]] = []

    if len(recent_trades) < EXPECTANCY_WINDOW:
        return triggers

    # Use last N trades for rolling window
    window = recent_trades[-EXPECTANCY_WINDOW:]
    pnls = []
    wins = 0
    for t in window:
        pnl = float(t.get("pnl_pct", 0.0))
        pnls.append(pnl)
        if pnl > 0:
            wins += 1

    # Trigger 1: Rolling 20-trade expectancy < 0
    expectancy = sum(pnls) / len(pnls)
    if expectancy < 0:
        triggers.append({
            "trigger": "negative_expectancy",
            "from_status": "PRODUCTION",
            "to_status": "PROBATION",
            "reason": (
                f"Rolling {EXPECTANCY_WINDOW}-trade expectancy = "
                f"{expectancy:.4f} (< 0)"
            ),
        })

    # Trigger 2: Max drawdown > 15%
    peak = 0.0
    cumulative = 0.0
    max_dd = 0.0
    for pnl in pnls:
        cumulative += pnl
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    if max_dd > MAX_DD_THRESHOLD * 100:  # pnl_pct is in percentage
        triggers.append({
            "trigger": "max_drawdown",
            "from_status": "PRODUCTION",
            "to_status": "PROBATION",
            "reason": (
                f"Rolling drawdown = {max_dd:.2f}% "
                f"(> {MAX_DD_THRESHOLD * 100:.0f}% threshold)"
            ),
        })

    # Trigger 3: Win rate drop > 10pp below baseline
    if baseline_win_rate > 0:
        current_wr = (wins / len(window)) * 100
        wr_drop = baseline_win_rate - current_wr
        if wr_drop > WR_DROP_THRESHOLD:
            triggers.append({
                "trigger": "win_rate_drop",
                "from_status": "PRODUCTION",
                "to_status": "PROBATION",
                "reason": (
                    f"Win rate dropped {wr_drop:.1f}pp "
                    f"(baseline={baseline_win_rate:.1f}%, "
                    f"current={current_wr:.1f}%, "
                    f"threshold={WR_DROP_THRESHOLD}pp)"
                ),
            })

    return triggers


def _check_probation_triggers(
    strategy_id: str,
    probation_start_date: Optional[str],
    negative_windows: int,
) -> List[Dict[str, str]]:
    """Check PROBATION -> BANNED triggers."""
    triggers: List[Dict[str, str]] = []

    # Trigger 1: 30 days with no recovery
    if probation_start_date:
        try:
            start = datetime.fromisoformat(probation_start_date)
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            days_in_probation = (now - start).days
            if days_in_probation >= PROBATION_RECOVERY_DAYS:
                triggers.append({
                    "trigger": "probation_timeout",
                    "from_status": "PROBATION",
                    "to_status": "BANNED",
                    "reason": (
                        f"{days_in_probation} days in probation "
                        f"(>= {PROBATION_RECOVERY_DAYS} day limit)"
                    ),
                })
        except (ValueError, TypeError):
            pass

    # Trigger 2: 3 consecutive negative evaluation windows
    if negative_windows >= CONSECUTIVE_NEGATIVE_WINDOWS:
        triggers.append({
            "trigger": "consecutive_negative_windows",
            "from_status": "PROBATION",
            "to_status": "BANNED",
            "reason": (
                f"{negative_windows} consecutive negative windows "
                f"(>= {CONSECUTIVE_NEGATIVE_WINDOWS} threshold)"
            ),
        })

    return triggers


# ---------------------------------------------------------------------------
# 3) Status history logger
# ---------------------------------------------------------------------------

def log_transition(
    strategy_id: str,
    from_status: str,
    to_status: str,
    reason: str,
    evidence: Optional[Dict[str, Any]] = None,
    history_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Append a transition record to the strategy status history JSON.

    Returns the record that was appended.
    """
    record = {
        "strategy_id": strategy_id,
        "from_status": from_status,
        "to_status": to_status,
        "reason": reason,
        "timestamp": _now_iso(),
    }
    if evidence:
        record["evidence"] = evidence

    history = _load_history(history_path)
    history["transitions"].append(record)
    _save_history(history, history_path)

    return record


# ---------------------------------------------------------------------------
# 4) Convenience: promote with full validation + logging
# ---------------------------------------------------------------------------

def promote(
    strategy_id: str,
    from_status: str,
    to_status: str,
    evidence: Optional[Dict[str, Any]] = None,
    history_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Validate, log, and execute a promotion in one call.

    Returns (success, message).
    """
    allowed, reason = validate_transition(strategy_id, from_status, to_status, evidence)
    if not allowed:
        return False, reason

    log_transition(
        strategy_id=strategy_id,
        from_status=from_status,
        to_status=to_status,
        reason=reason,
        evidence=evidence,
        history_path=history_path,
    )
    return True, reason


def demote(
    strategy_id: str,
    from_status: str,
    to_status: str,
    reason: str,
    history_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Validate and log a demotion in one call.

    Returns (success, message).
    """
    allowed, validation_reason = validate_transition(
        strategy_id, from_status, to_status
    )
    if not allowed:
        return False, validation_reason

    log_transition(
        strategy_id=strategy_id,
        from_status=from_status,
        to_status=to_status,
        reason=reason,
        history_path=history_path,
    )
    return True, f"Demoted: {reason}"


def get_current_status(
    strategy_id: str,
    history_path: Optional[Path] = None,
) -> Optional[str]:
    """Get the current status of a strategy from transition history.

    Returns the to_status of the most recent transition, or None if no history.
    """
    history = _load_history(history_path)
    for record in reversed(history["transitions"]):
        if record.get("strategy_id") == strategy_id:
            return record.get("to_status")
    return None
