"""HF Quality Gate telemetry — guardrails required by external-AI consensus.

Implements the 4 mandatory guardrails the 4-of-5 external AI review
required before flipping ``HF_QUALITY_GATE_ENABLED`` default-on (see
``reports/external_ai_review_hf_gate_default_on_2026_04_28.md``):

1. **50-pick rolling circuit-breaker** — if HF reject rate exceeds
   ``HF_GATE_CIRCUIT_BREAKER_THRESHOLD`` (default 0.50) on the most recent
   50 picks, the next gate evaluation auto-bypasses (logs
   ``circuit_breaker_tripped``).
2. **200-pick attribution audit** — rolling window of the last 200
   ``record_hf_gate_decision`` entries with
   ``(pick_id, hf_reject_reason, source_system, asset_class,
     ml_composite_pre_gate, ml_composite_post_gate)``.
3. **Per-asset-class reject counters** — running counters
   broken down by ``asset_class``.
4. **Pre-flip re-smoke gate** — see ``tools/run_hf_gate_smoke.py``.

The module is import-safe and never raises in normal use; all I/O is
soft-failed so that callers (notably ``audit_trail.quality_gates``) can
treat telemetry as best-effort.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from collections import Counter, deque
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ───────────────── tunables ─────────────────

CIRCUIT_BREAKER_WINDOW = 50
CIRCUIT_BREAKER_THRESHOLD = float(
    os.environ.get("HF_GATE_CIRCUIT_BREAKER_THRESHOLD", "0.50")
)
ATTRIBUTION_WINDOW = 200

# ───────────────── module-level state ─────────────────
# Guarded by ``_LOCK``; all mutators take the lock for thread-safety in the
# pick-load cycle which fans out across asset classes.

_LOCK = threading.RLock()
# Each entry is True for accept, False for reject. Used for the rolling
# circuit-breaker reject-rate calculation.
_RECENT_DECISIONS: deque[bool] = deque(maxlen=CIRCUIT_BREAKER_WINDOW)
# Last N attribution records.
_ATTRIBUTION_LOG: deque[dict[str, Any]] = deque(maxlen=ATTRIBUTION_WINDOW)
# Per-asset-class reject counter.
_REJECT_BY_AC: Counter[str] = Counter()
# Per-asset-class accept counter (helps reason about reject rate per-AC).
_ACCEPT_BY_AC: Counter[str] = Counter()
# Number of times the circuit breaker has tripped this process lifetime.
_CIRCUIT_TRIPS = 0
# Whether the breaker is currently tripped (auto-clears once the window
# rolls back under threshold, since we recompute on every call).

_TELEMETRY_PATH = (
    Path(__file__).resolve().parent / "data" / "hf_gate_telemetry.json"
)


def _coerce_str(val: Any) -> str:
    return str(val) if val is not None else ""


def _ac_key(pick: dict[str, Any]) -> str:
    """Normalize asset_class to a non-empty string key."""
    ac = _coerce_str(pick.get("asset_class") or pick.get("assetClass") or "").upper()
    return ac or "UNKNOWN"


def _should_circuit_break_hf_gate() -> bool:
    """Return True if the rolling reject rate exceeds the threshold.

    Window only counts once we have a full 50-sample buffer — until
    then the breaker stays open (gate runs normally). This keeps cold
    starts from falsely tripping on the first few rejects.
    """
    with _LOCK:
        if len(_RECENT_DECISIONS) < CIRCUIT_BREAKER_WINDOW:
            return False
        rejects = sum(1 for accept in _RECENT_DECISIONS if not accept)
        rate = rejects / float(CIRCUIT_BREAKER_WINDOW)
        return rate > CIRCUIT_BREAKER_THRESHOLD


def record_hf_gate_decision(
    pick: dict[str, Any],
    decision: bool,
    reason: str | None,
) -> None:
    """Append a gate evaluation to the rolling 200-pick attribution log,
    increment the per-AC counter, and record the boolean for the circuit
    breaker window.

    ``decision`` is True for "accepted" (gate passed), False for
    "rejected". ``reason`` is the rejection reason string (may be None
    for an accept). All exceptions are swallowed and logged at debug —
    telemetry must never break the gate.
    """
    global _CIRCUIT_TRIPS
    try:
        ac = _ac_key(pick)
        record = {
            "pick_id": _coerce_str(pick.get("id") or pick.get("pick_id")),
            "hf_reject_reason": reason if not decision else None,
            "source_system": _coerce_str(pick.get("source_system")),
            "asset_class": ac,
            "ml_composite_pre_gate": pick.get(
                "ml_composite_pre_gate", pick.get("ml_composite")
            ),
            "ml_composite_post_gate": pick.get("ml_composite_post_gate"),
            "decision": "ACCEPT" if decision else "REJECT",
        }
        with _LOCK:
            _RECENT_DECISIONS.append(bool(decision))
            _ATTRIBUTION_LOG.append(record)
            if decision:
                _ACCEPT_BY_AC[ac] += 1
            else:
                _REJECT_BY_AC[ac] += 1
    except Exception as exc:  # pragma: no cover — best effort only
        logger.debug(f"HF gate telemetry: record_hf_gate_decision swallowed {exc!r}")


def record_circuit_breaker_trip(reason: str = "rolling_reject_rate_exceeded") -> None:
    """Bump the lifetime trip counter when the breaker fires."""
    global _CIRCUIT_TRIPS
    with _LOCK:
        _CIRCUIT_TRIPS += 1
    logger.warning(
        "HF gate: circuit_breaker_tripped (%s, lifetime trips=%d)",
        reason,
        _CIRCUIT_TRIPS,
    )


def get_telemetry_snapshot() -> dict[str, Any]:
    """Return a JSON-safe snapshot of the current telemetry state."""
    with _LOCK:
        recent = list(_RECENT_DECISIONS)
        rejects = sum(1 for a in recent if not a)
        accepts = len(recent) - rejects
        rate = (rejects / float(len(recent))) if recent else 0.0
        per_ac = {}
        for ac in set(list(_REJECT_BY_AC.keys()) + list(_ACCEPT_BY_AC.keys())):
            r = _REJECT_BY_AC.get(ac, 0)
            a = _ACCEPT_BY_AC.get(ac, 0)
            tot = r + a
            per_ac[ac] = {
                "rejects": r,
                "accepts": a,
                "total": tot,
                "reject_rate": (r / float(tot)) if tot else 0.0,
            }
        return {
            "circuit_breaker": {
                "window": CIRCUIT_BREAKER_WINDOW,
                "threshold": CIRCUIT_BREAKER_THRESHOLD,
                "current_window_size": len(recent),
                "current_window_rejects": rejects,
                "current_window_accepts": accepts,
                "current_reject_rate": rate,
                "tripped": _should_circuit_break_hf_gate(),
                "lifetime_trips": _CIRCUIT_TRIPS,
            },
            "per_asset_class": per_ac,
            "attribution_log_recent": list(_ATTRIBUTION_LOG),
        }


def _flush_telemetry_to_disk(path: Path | None = None) -> bool:
    """Write the telemetry snapshot to ``audit_trail/data/hf_gate_telemetry.json``.

    Returns True on success, False on any I/O error. Writes are atomic
    via ``.tmp`` + replace so partial files never appear on disk.
    """
    target = Path(path) if path else _TELEMETRY_PATH
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        snap = get_telemetry_snapshot()
        tmp = target.with_suffix(target.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(snap, fh, indent=2, default=str)
        os.replace(tmp, target)
        return True
    except Exception as exc:  # pragma: no cover — best effort only
        logger.debug(f"HF gate telemetry: _flush_telemetry_to_disk failed: {exc!r}")
        return False


def _reset_for_tests() -> None:
    """Reset all module state. Test-only helper."""
    global _CIRCUIT_TRIPS
    with _LOCK:
        _RECENT_DECISIONS.clear()
        _ATTRIBUTION_LOG.clear()
        _REJECT_BY_AC.clear()
        _ACCEPT_BY_AC.clear()
        _CIRCUIT_TRIPS = 0
