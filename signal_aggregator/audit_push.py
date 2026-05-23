"""
Signal Aggregator Audit Push — Records master-picks into the central audit trail.

Reads active picks from signal_aggregator/data/master_picks_tracker.json
and pushes them to the audit_trail SQLite + MySQL dual-write system.
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
log = logging.getLogger("signal_aggregator.audit_push")

# Ensure repo root is on sys.path for audit_trail package
_REPO_ROOT = str(pathlib.Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

SOURCE_SYSTEM = "SignalAggregator"

# Data files to read picks from (in priority order)
TRACKER_PATH = os.path.join(os.path.dirname(__file__), "data", "master_picks_tracker.json")
CONSENSUS_PATH = os.path.join(os.path.dirname(__file__), "data", "consensus_output.json")


def load_picks() -> list:
    """Load active picks from master_picks_tracker.json."""
    picks = []

    # Primary: master_picks_tracker.json (active picks with full metadata)
    if os.path.exists(TRACKER_PATH):
        try:
            with open(TRACKER_PATH, "r") as f:
                data = json.load(f)
            active = data.get("active_picks", [])
            for p in active:
                if p.get("status", "active") == "active":
                    picks.append(p)
            log.info("Loaded %d active picks from master_picks_tracker.json", len(picks))
        except Exception as e:
            log.warning("Failed to load master_picks_tracker.json: %s", e)

    # Supplement: consensus_output.json (latest consensus signals)
    if not picks and os.path.exists(CONSENSUS_PATH):
        try:
            with open(CONSENSUS_PATH, "r") as f:
                data = json.load(f)
            signals = data.get("signals", {})
            for symbol, sig_data in signals.items():
                for sig in sig_data.get("signals", []):
                    picks.append({
                        "symbol": symbol,
                        "direction": sig.get("direction", "LONG"),
                        "entry_price": sig.get("entry_price", sig.get("current_price", 0)),
                        "tp_price": sig.get("tp_price", 0),
                        "sl_price": sig.get("sl_price", 0),
                        "confidence": sig.get("confidence", sig.get("consensus_score", 0.5)),
                        "strategy": sig.get("strategy", sig.get("system", "consensus")),
                        "timestamp": sig.get("timestamp", ""),
                        "systems": sig.get("systems", []),
                    })
            log.info("Loaded %d picks from consensus_output.json", len(picks))
        except Exception as e:
            log.warning("Failed to load consensus_output.json: %s", e)

    return picks


def normalize(pick: dict) -> dict:
    """Normalize a master-pick dict to the audit trail schema."""
    return {
        "symbol": pick.get("symbol", ""),
        "direction": pick.get("direction", "LONG"),
        "entry_price": pick.get("entry_price", 0),
        "take_profit": pick.get("tp_price", pick.get("take_profit", 0)),
        "stop_loss": pick.get("sl_price", pick.get("stop_loss", 0)),
        "confidence": pick.get("confidence", pick.get("consensus_score", 0.5)),
        "strategy": pick.get("strategy", ", ".join(pick.get("systems", ["signal_aggregator"]))),
        "timestamp": pick.get("timestamp", ""),
    }


def push_to_audit(picks: list) -> dict:
    """Push picks to the central audit trail SQLite + MySQL dual-write."""
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

    run_id = start_run(regime_data={"source": SOURCE_SYSTEM})
    recorded = 0
    skipped = 0

    for pick in picks:
        pick_id = record_raw_pick(SOURCE_SYSTEM, normalize(pick), run_id)
        if pick_id:
            recorded += 1
        else:
            skipped += 1

    finish_run(run_id, consensus_count=recorded, systems_loaded=1, raw_count=len(picks))

    record_event(
        "SIGNAL_AGGREGATOR_AUDIT_PUSH",
        run_id=run_id,
        payload={
            "total_picks": len(picks),
            "recorded": recorded,
            "skipped": skipped,
        },
        origin=SOURCE_SYSTEM,
    )

    log.info(
        "Audit push complete: %d recorded, %d skipped (run_id=%s)",
        recorded, skipped, run_id,
    )

    # Flush WAL so git can pick up changes
    try:
        from audit_trail.db import get_connection, close as audit_close
        conn = get_connection()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        audit_close()
        log.info("WAL checkpoint complete")
    except Exception as e:
        log.warning("WAL checkpoint failed (non-fatal): %s", e)

    return {"status": "ok", "recorded": recorded, "skipped": skipped, "run_id": run_id}


def main():
    picks = load_picks()
    if not picks:
        log.info("No active Signal Aggregator picks to push to audit trail")
        return

    log.info("Pushing %d Signal Aggregator picks to audit trail...", len(picks))
    result = push_to_audit(picks)
    log.info("Result: %s", result)


if __name__ == "__main__":
    main()
