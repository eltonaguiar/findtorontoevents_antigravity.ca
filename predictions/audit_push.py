"""
Social Media Predictions Audit Push — Records active predictions into the central audit trail.

Reads active predictions from predictions/data/predictions.db (SQLite)
and predictions/data/active_predictions.json, then pushes them to the
audit_trail SQLite + MySQL dual-write system.
"""

import argparse
import json
import logging
import os
import pathlib
import sqlite3
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("predictions.audit_push")

# Ensure repo root is on sys.path for audit_trail package
_REPO_ROOT = str(pathlib.Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

SOURCE_SYSTEM = "Predictions"

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "predictions.db")
ACTIVE_JSON_PATH = os.path.join(os.path.dirname(__file__), "data", "active_predictions.json")


def refresh_active_predictions() -> dict:
    """Run the source validator so stale ACTIVE rows are closed before export."""
    try:
        from predictions.validation.price_validator import validate_all
    except ImportError:
        from validation.price_validator import validate_all

    try:
        summary = validate_all() or {}
        log.info(
            "Refreshed predictions source ledger: validated=%s closed=%s active=%s",
            summary.get("validated", 0),
            summary.get("closed", 0),
            summary.get("still_active", 0),
        )
        return summary
    except Exception as exc:
        log.warning("Prediction refresh failed: %s", exc)
        return {}


def load_picks(refresh: bool = True) -> list:
    """Load active predictions from SQLite, falling back to JSON export."""
    if refresh:
        refresh_active_predictions()

    picks = []

    # Primary: read directly from SQLite
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM predictions WHERE status = 'ACTIVE' ORDER BY scraped_at DESC"
            ).fetchall()
            picks = [dict(r) for r in rows]
            conn.close()
            log.info("Loaded %d active predictions from SQLite", len(picks))
        except Exception as e:
            log.warning("Failed to read predictions.db: %s", e)

    # Fallback: active_predictions.json
    if not picks and os.path.exists(ACTIVE_JSON_PATH):
        try:
            with open(ACTIVE_JSON_PATH, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                picks = data
            elif isinstance(data, dict):
                picks = data.get("active_predictions", data.get("predictions", []))
            log.info("Loaded %d active predictions from JSON fallback", len(picks))
        except Exception as e:
            log.warning("Failed to load active_predictions.json: %s", e)

    return picks


def normalize(pred: dict) -> dict:
    """Normalize a prediction row to the audit trail schema.

    Predictions DB columns:
      predictor_id, platform, symbol, direction, entry_price, take_profit,
      stop_loss, sentiment_score, source_url, scraped_at, status
    """
    # Build strategy string from predictor + platform
    predictor = pred.get("predictor_id", "unknown")
    platform = pred.get("platform", "social")
    strategy = f"{platform}/{predictor}"

    return {
        "symbol": pred.get("symbol", ""),
        "direction": pred.get("direction", "LONG"),
        "entry_price": pred.get("entry_price", 0) or 0,
        "take_profit": pred.get("take_profit", 0) or 0,
        "stop_loss": pred.get("stop_loss", 0) or 0,
        "confidence": pred.get("sentiment_score", 0.5) or 0.5,
        "strategy": strategy,
        "timestamp": pred.get("scraped_at", ""),
    }


def push_to_audit(picks: list) -> dict:
    """Push predictions to the central audit trail SQLite + MySQL dual-write."""
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

    for pred in picks:
        pick_id = record_raw_pick(SOURCE_SYSTEM, normalize(pred), run_id)
        if pick_id:
            recorded += 1
        else:
            skipped += 1

    finish_run(run_id, consensus_count=recorded, systems_loaded=1, raw_count=len(picks))

    # Count unique platforms and predictors for the event payload
    platforms = set(p.get("platform", "") for p in picks)
    predictors = set(p.get("predictor_id", "") for p in picks)

    record_event(
        "PREDICTIONS_AUDIT_PUSH",
        run_id=run_id,
        payload={
            "total_predictions": len(picks),
            "recorded": recorded,
            "skipped": skipped,
            "unique_platforms": len(platforms),
            "unique_predictors": len(predictors),
        },
        origin=SOURCE_SYSTEM,
    )

    log.info(
        "Audit push complete: %d recorded, %d skipped from %d platforms (run_id=%s)",
        recorded, skipped, len(platforms), run_id,
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
    parser = argparse.ArgumentParser(description="Push predictions into the central audit trail")
    parser.add_argument(
        "--refresh-only",
        action="store_true",
        help="Refresh the predictions source ledger without pushing anything to audit_trail",
    )
    args = parser.parse_args()

    refresh_active_predictions()
    if args.refresh_only:
        return

    picks = load_picks(refresh=False)
    if not picks:
        log.info("No active predictions to push to audit trail")
        return

    log.info("Pushing %d predictions to audit trail...", len(picks))
    result = push_to_audit(picks)
    log.info("Result: %s", result)


if __name__ == "__main__":
    main()
