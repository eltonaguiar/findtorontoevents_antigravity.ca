"""
QuanEngine Audit Push — Records active signals into the central audit trail.

Follows the same pattern as cross_aggregation/aggregator.py:
  1. start_run()
  2. record_raw_pick() for each signal
  3. finish_run()
  4. WAL checkpoint so git picks up the SQLite changes
"""

import argparse
import json
import logging
import os
import pathlib
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("quan_engine.audit_push")

# Ensure repo root is on sys.path for audit_trail package
_REPO_ROOT = str(pathlib.Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Path to active signals output
SIGNALS_PATH = os.path.join(
    os.path.dirname(__file__), "data", "active_signals.json"
)

SOURCE_SYSTEM = "QuanEngine"


def refresh_active_signals() -> dict:
    """Validate active signals and re-export the source ledger before pushing."""
    try:
        from quan_engine.forward_tracker import ForwardTracker
    except ImportError:
        from forward_tracker import ForwardTracker

    tracker = ForwardTracker()
    try:
        closed = tracker.validate_active_signals()
        output_path = tracker.export_active_json()
        active = tracker.get_active_signals()
        summary = {
            "closed": len(closed),
            "active": len(active),
            "output_path": output_path,
        }
        log.info(
            "Refreshed QuanEngine source ledger: closed=%d active=%d output=%s",
            summary["closed"],
            summary["active"],
            summary["output_path"],
        )
        return summary
    except Exception as exc:
        log.warning("QuanEngine refresh failed: %s", exc)
        return {}
    finally:
        tracker.close()


def load_signals(refresh: bool = True) -> list:
    """Load active_signals.json, handling both list and dict formats."""
    if refresh:
        refresh_active_signals()

    if not os.path.exists(SIGNALS_PATH):
        log.warning("No active_signals.json found at %s", SIGNALS_PATH)
        return []

    with open(SIGNALS_PATH, "r") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("active_picks", data.get("signals", data.get("picks", [])))
    return []


def push_to_audit(signals: list) -> dict:
    """Push signals to the central audit trail SQLite + MySQL dual-write."""
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

    for sig in signals:
        # Normalize the pick dict for the recorder's field extractors
        _conf = float(sig.get("confidence", sig.get("ml_score", 0.5)) or 0.5)
        pick = {
            "symbol": sig.get("symbol", ""),
            "direction": sig.get("direction", sig.get("signal_type", "BUY")),
            "entry_price": sig.get("entry_price", sig.get("entry", 0)),
            "take_profit": sig.get("tp", sig.get("take_profit", sig.get("tp_price", 0))),
            "stop_loss": sig.get("sl", sig.get("stop_loss", sig.get("sl_price", 0))),
            "confidence": _conf,
            "strategy": sig.get("strategy", sig.get("mode", "quan_engine")),
            "timestamp": sig.get("timestamp", sig.get("generated_at", "")),
            # Propagate source score; fall back to confidence*100 so the dashboard
            # doesn't treat quan_engine picks as unscored (avoids elite_scorer backfill)
            "score": sig.get("score") or sig.get("elite_score") or round(_conf * 100),
        }

        pick_id = record_raw_pick(SOURCE_SYSTEM, pick, run_id)
        if pick_id:
            recorded += 1
        else:
            skipped += 1

    finish_run(run_id, consensus_count=recorded, systems_loaded=1, raw_count=len(signals))

    record_event(
        "QUAN_ENGINE_SCAN_COMPLETE",
        run_id=run_id,
        payload={
            "total_signals": len(signals),
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
    parser = argparse.ArgumentParser(description="Push QuanEngine signals into the central audit trail")
    parser.add_argument(
        "--refresh-only",
        action="store_true",
        help="Refresh active_signals.json without pushing anything to audit_trail",
    )
    args = parser.parse_args()

    refresh_active_signals()
    if args.refresh_only:
        return

    signals = load_signals(refresh=False)
    if not signals:
        log.info("No active signals to push to audit trail")
        return

    log.info("Pushing %d signals to audit trail...", len(signals))
    result = push_to_audit(signals)
    log.info("Result: %s", result)


if __name__ == "__main__":
    main()
