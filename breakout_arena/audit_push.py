"""
Breakout Arena Audit Push — Records active + closed picks into the central audit trail.

Follows the same pattern as quan_engine/audit_push.py:
  1. start_run()
  2. record_raw_pick() for each active signal
  3. finish_run()
  4. WAL checkpoint so git picks up the SQLite changes
"""

import json
import logging
import os
import pathlib
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("breakout_arena.audit_push")

# Ensure repo root is on sys.path for audit_trail package
_REPO_ROOT = str(pathlib.Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Three approach data dirs
APPROACHES = [
    {
        "id": "BreakoutArena_A",
        "name": "Breakout Arena A (S/R)",
        "data_dir": os.path.join(os.path.dirname(__file__), "approach_a_sr_breakout", "data"),
    },
    {
        "id": "BreakoutArena_B",
        "name": "Breakout Arena B (ML)",
        "data_dir": os.path.join(os.path.dirname(__file__), "approach_b_ml_breakout", "data"),
    },
    {
        "id": "BreakoutArena_C",
        "name": "Breakout Arena C (Spike)",
        "data_dir": os.path.join(os.path.dirname(__file__), "approach_c_spike_reverse", "data"),
    },
]


def load_picks(data_dir: str) -> tuple[list, list]:
    """Load active and closed picks from a data directory."""
    active = []
    closed = []

    active_path = os.path.join(data_dir, "active_picks.json")
    closed_path = os.path.join(data_dir, "closed_picks.json")

    if os.path.exists(active_path):
        with open(active_path) as f:
            active = json.load(f)

    if os.path.exists(closed_path):
        with open(closed_path) as f:
            closed = json.load(f)

    return active, closed


def normalize_pick(pick: dict, source_system: str) -> dict:
    """Normalize an arena pick dict for the audit recorder's field extractors."""
    return {
        "symbol": pick.get("symbol", ""),
        "direction": pick.get("signal_type", "BUY"),
        "entry_price": pick.get("entry_price", 0),
        "take_profit": pick.get("take_profit", 0),
        "stop_loss": pick.get("stop_loss", 0),
        "confidence": pick.get("confidence", pick.get("ml_score", 0.5)),
        "strategy": pick.get("strategy", pick.get("archetype_match", source_system)),
        "timestamp": pick.get("timestamp", ""),
    }


def push_to_audit() -> dict:
    """Push all arena picks to the central audit trail (SQLite + MySQL dual-write)."""
    try:
        from audit_trail import (
            start_run,
            finish_run,
            record_raw_pick,
            record_event,
        )
    except ImportError as e:
        log.error("audit_trail package not available: %s", e)
        return {"status": "skip", "reason": "audit_trail not importable"}

    total_recorded = 0
    total_skipped = 0

    for approach in APPROACHES:
        source = approach["id"]
        data_dir = approach["data_dir"]

        active, closed = load_picks(data_dir)
        all_picks = active  # Only push active picks (closed are already recorded)

        if not all_picks:
            log.info("%s: no active picks to push", source)
            continue

        run_id = start_run(regime_data={"source": source})
        recorded = 0
        skipped = 0

        for pick in all_picks:
            normalized = normalize_pick(pick, source)
            pick_id = record_raw_pick(source, normalized, run_id)
            if pick_id:
                recorded += 1
            else:
                skipped += 1

        finish_run(run_id, consensus_count=recorded, systems_loaded=1, raw_count=len(all_picks))

        record_event(
            "ARENA_SCAN_COMPLETE",
            run_id=run_id,
            payload={
                "approach": source,
                "active_picks": len(active),
                "closed_picks": len(closed),
                "recorded": recorded,
                "skipped": skipped,
            },
            origin=source,
        )

        log.info("%s: %d recorded, %d skipped (run_id=%s)", source, recorded, skipped, run_id)
        total_recorded += recorded
        total_skipped += skipped

    # Flush WAL so git can pick up changes
    try:
        from audit_trail.db import get_connection, close as audit_close

        conn = get_connection()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        audit_close()
        log.info("WAL checkpoint complete")
    except Exception as e:
        log.warning("WAL checkpoint failed (non-fatal): %s", e)

    return {"status": "ok", "recorded": total_recorded, "skipped": total_skipped}


def main():
    log.info("Pushing Breakout Arena picks to audit trail...")
    result = push_to_audit()
    log.info("Result: %s", result)


if __name__ == "__main__":
    main()
