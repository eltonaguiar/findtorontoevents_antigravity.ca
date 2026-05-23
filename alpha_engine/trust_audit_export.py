"""
TRUST AUDIT EXPORT — Entry-time trust snapshot for independent verification.

Problem: trust_score is absent from raw pick data — it's injected post-hoc by
enrich_picks_with_trust_score() using strat_fwd_wr (partial lookahead).  There
was no frozen record of what trust_score a pick had at entry time, making it
impossible to independently verify trust-based gating decisions.

Solution: This module snapshots ALL trust-relevant data the moment a pick is
enriched with trust_score, including:
  - The computed trust_score, breakdown, and label
  - All raw inputs used to compute them (fwd_wr, trades, regime, prices, etc.)
  - A snapshot of the config constants that affect trust-based gating

Audit files are append-only JSONL (one JSON object per line) written to
alpha_engine/data/trust_audit_exports/trust_audit_YYYY_MM_DD.jsonl.

Usage:
    from alpha_engine.trust_audit_export import export_trust_audit
    enrich_picks_with_trust_score(active, perf, regime)
    count = export_trust_audit(active)
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPORT_DIR = Path(__file__).parent / "data" / "trust_audit_exports"

# In-memory dedup cache: prevents re-exporting the same pick_id within a
# single runtime session.  Cleared on process restart (intentional — daily
# JSONL files are append-only so duplicate lines across sessions are harmless,
# but within a session we avoid writing the same pick twice).
# Capped at 10K entries to prevent unbounded memory growth in long-running processes.
# Once full, new pick_ids are still exported but no longer tracked for dedup
# (duplicate JSONL lines are harmless — the file is append-only).
_EXPORTED_PICK_IDS: set[str] = set()
_EXPORTED_PICK_IDS_MAX = 10_000


def _get_system_config_snapshot() -> dict[str, Any]:
    """Auto-detect current trust-gating config constants from live modules.

    Returns a dict with the current values of:
      - SMART_PICKS_CRYPTO_LONG_ONLY  (audit_trail.quality_gates)
      - TIER_MULTIPLIERS              (cross_aggregation.system_trust_registry)
      - ASSET_CLASS_TRUST_THRESHOLDS   (alpha_engine.config)

    Any import failure is silently skipped (value set to None / {}).
    """
    snap: dict[str, Any] = {
        "SMART_PICKS_CRYPTO_LONG_ONLY": None,
        "TIER_MULTIPLIERS": {},
        "ASSET_CLASS_TRUST_THRESHOLDS": {},
    }

    try:
        from audit_trail.quality_gates import SMART_PICKS_CRYPTO_LONG_ONLY
        snap["SMART_PICKS_CRYPTO_LONG_ONLY"] = SMART_PICKS_CRYPTO_LONG_ONLY
    except ImportError:
        pass

    try:
        from cross_aggregation.system_trust_registry import (
            TIER_BANNED,
            TIER_PROVEN,
            TIER_RELIABLE,
            TIER_UNTRUSTED,
            TIER_WATCH,
            TIER_MULTIPLIERS,
        )
        # Convert int-keyed dict to human-readable string keys for JSON
        snap["TIER_MULTIPLIERS"] = {
            "PROVEN": TIER_MULTIPLIERS[TIER_PROVEN],
            "RELIABLE": TIER_MULTIPLIERS[TIER_RELIABLE],
            "WATCH": TIER_MULTIPLIERS[TIER_WATCH],
            "UNTRUSTED": TIER_MULTIPLIERS[TIER_UNTRUSTED],
            "BANNED": TIER_MULTIPLIERS[TIER_BANNED],
        }
    except ImportError:
        pass

    try:
        from alpha_engine.config import ASSET_CLASS_TRUST_THRESHOLDS
        snap["ASSET_CLASS_TRUST_THRESHOLDS"] = dict(ASSET_CLASS_TRUST_THRESHOLDS)
    except ImportError:
        pass

    return snap


def _build_audit_entry(
    pick: dict,
    config_snapshot: dict[str, Any],
    export_ts: str,
) -> dict[str, Any] | None:
    """Build a single audit entry dict from a pick.  Returns None if the pick
    has not been enriched with trust_score (skip unenriched picks)."""
    trust_score = pick.get("trust_score")
    if trust_score is None:
        return None

    pick_id = pick.get("id") or pick.get("pick_id") or ""
    if not pick_id:
        return None

    # Parse extra dict (may be JSON string — same pattern as compute_trust_score)
    extra = pick.get("extra") or {}
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except Exception:
            extra = {}
    elif not isinstance(extra, dict):
        extra = {}

    # Raw inputs used by compute_trust_score — capture every source field
    # the function reads so an auditor can recompute from scratch.
    # NOTE: direction is at top level (not duplicated here).
    raw_inputs = {
        "strat_fwd_wr": pick.get("strat_fwd_wr") or pick.get("forward_wr"),
        "strat_fwd_trades": pick.get("strat_fwd_trades") or pick.get("forward_trades"),
        "regime": (
            pick.get("regime_at_entry")
            or pick.get("htf_bias")
            or extra.get("fast_regime")
            or extra.get("regime")
        ),
        "entry_price": pick.get("entry_price") or pick.get("entry"),
        "tp": pick.get("take_profit") or pick.get("tp"),
        "sl": pick.get("stop_loss") or pick.get("sl"),
        "timestamp": pick.get("timestamp") or pick.get("created_at") or pick.get("scan_timestamp"),
        "asset_class": pick.get("asset_class"),
        "rr_ratio": pick.get("rr_ratio") or pick.get("risk_reward"),
    }

    entry = {
        "export_timestamp": export_ts,
        "pick_id": pick_id,
        "symbol": pick.get("symbol"),
        "strategy": pick.get("strategy"),
        "direction": pick.get("direction") or pick.get("signal_type"),
        "trust_score": trust_score,
        "trust_label": pick.get("trust_label"),
        "trust_breakdown": pick.get("trust_breakdown", {}),
        "raw_inputs": raw_inputs,
        "config_snapshot": config_snapshot,
    }
    return entry


def export_trust_audit(
    picks: list[dict],
    config_snapshot: dict[str, Any] | None = None,
) -> int:
    """Snapshot trust-relevant data for newly enriched picks.

    Appends one JSONL line per pick to the daily audit file.
    Skips picks that:
      - Lack trust_score (not yet enriched)
      - Lack a pick_id
      - Were already exported in this runtime session

    Args:
        picks: List of pick dicts (must already be enriched with trust_score).
        config_snapshot: Optional pre-built config snapshot.  If None, it is
            auto-detected from live modules.

    Returns:
        Count of newly exported entries.
    """
    global _EXPORTED_PICK_IDS

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    if config_snapshot is None:
        config_snapshot = _get_system_config_snapshot()

    now = datetime.now(timezone.utc)
    export_ts = now.isoformat()
    filename = f"trust_audit_{now.strftime('%Y_%m_%d')}.jsonl"
    filepath = EXPORT_DIR / filename

    new_lines: list[str] = []
    exported_count = 0

    for pick in picks:
        pick_id = pick.get("id") or pick.get("pick_id") or ""

        # Skip picks without an ID or already exported this session
        if not pick_id or pick_id in _EXPORTED_PICK_IDS:
            continue

        entry = _build_audit_entry(pick, config_snapshot, export_ts)
        if entry is None:
            continue  # not enriched yet

        new_lines.append(json.dumps(entry, default=str))
        if len(_EXPORTED_PICK_IDS) < _EXPORTED_PICK_IDS_MAX:
            _EXPORTED_PICK_IDS.add(pick_id)
        # If cache is full, pick is still exported but won't be dedup-tracked.
        # This is fine: daily JSONL is append-only, duplicate lines are harmless.
        exported_count += 1

    if new_lines:
        # Append to daily JSONL file (atomic write per session)
        with open(filepath, "a", encoding="utf-8") as f:
            for line in new_lines:
                f.write(line + "\n")

    return exported_count


def reset_session_cache() -> None:
    """Clear the in-memory dedup cache.  Useful for testing."""
    global _EXPORTED_PICK_IDS
    _EXPORTED_PICK_IDS.clear()


# ---------------------------------------------------------------------------
# CLI: manual re-export of current active_picks.json
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    sys.stdout = open(
        sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False, errors="replace"
    )

    DATA_DIR = Path(__file__).parent / "data"
    active_path = DATA_DIR / "active_picks.json"
    if not active_path.exists():
        print("No active_picks.json found — nothing to export.")
        sys.exit(0)

    active = json.loads(active_path.read_text(encoding="utf-8"))

    # Enrich if not already
    from alpha_engine.trust_score import enrich_picks_with_trust_score
    enrich_picks_with_trust_score(active)

    count = export_trust_audit(active)
    print(f"Exported {count} trust audit entries.")
