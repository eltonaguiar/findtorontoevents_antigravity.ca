"""
Coinglass DNA Bundle Audit Push — Records active picks into the central audit trail.

Reads picks from coinglass_strategies/data/active_picks.json (written by signal_engine.scan_all)
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
log = logging.getLogger("coinglass_strategies.audit_push")

# Ensure repo root is on sys.path for audit_trail package
_REPO_ROOT = str(pathlib.Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

SOURCE_SYSTEM = "CoinglassDNA"

ACTIVE_PICKS_PATH = os.path.join(os.path.dirname(__file__), "data", "active_picks.json")


def load_picks() -> list:
    """Load active picks from active_picks.json."""
    if not os.path.exists(ACTIVE_PICKS_PATH):
        log.warning("No active_picks.json found at %s", ACTIVE_PICKS_PATH)
        return []

    try:
        with open(ACTIVE_PICKS_PATH, "r") as f:
            data = json.load(f)
    except Exception as e:
        log.error("Failed to parse active_picks.json: %s", e)
        return []

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("picks", data.get("active_picks", data.get("signals", [])))
    return []


def normalize(pick: dict) -> dict:
    """Normalize a Coinglass pick dict to the audit trail schema.

    Coinglass signal_engine outputs dicts with keys like:
      symbol, direction, strategy, confidence, entry_price, take_profit, stop_loss, timestamp
    """
    return {
        "symbol": pick.get("symbol", ""),
        "direction": pick.get("direction", "LONG"),
        "entry_price": pick.get("entry_price", 0),
        "take_profit": pick.get("take_profit", pick.get("tp", 0)),
        "stop_loss": pick.get("stop_loss", pick.get("sl", 0)),
        "confidence": pick.get("confidence", 0.5),
        "strategy": pick.get("strategy", "coinglass_dna"),
        "timestamp": pick.get("timestamp", pick.get("generated_at", "")),
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
        "COINGLASS_DNA_AUDIT_PUSH",
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


def reconcile_closed_trades() -> dict:
    """Read closed positions from coinglass.db and push resolutions to audit trail.

    This ensures the audit trail reflects final outcomes (TP hit, SL hit, etc.)
    for trades that were opened by the Coinglass DNA system.
    """
    try:
        from . import ratio_store
    except ImportError:
        try:
            import ratio_store
        except ImportError:
            log.warning("ratio_store not importable, skipping closed trade reconciliation")
            return {"status": "skip", "reason": "ratio_store not importable"}

    try:
        from audit_trail import record_event
    except ImportError:
        log.warning("audit_trail not importable, skipping reconciliation")
        return {"status": "skip", "reason": "audit_trail not importable"}

    closed = ratio_store.get_closed_positions(limit=100)
    if not closed:
        log.info("No closed positions to reconcile")
        return {"status": "ok", "reconciled": 0}

    # Track which signal_ids we've already reconciled (stored in a local JSON file)
    reconciled_path = os.path.join(os.path.dirname(__file__), "data", "reconciled_ids.json")
    already_reconciled = set()
    if os.path.exists(reconciled_path):
        try:
            with open(reconciled_path, "r") as f:
                already_reconciled = set(json.load(f))
        except Exception:
            already_reconciled = set()

    new_reconciled = 0
    for pos in closed:
        sig_id = pos.get("signal_id", "")
        if not sig_id or sig_id in already_reconciled:
            continue

        # Push resolution event to audit trail
        record_event(
            "COINGLASS_DNA_TRADE_CLOSED",
            payload={
                "signal_id": sig_id,
                "symbol": pos.get("symbol", ""),
                "direction": pos.get("direction", ""),
                "entry_price": pos.get("entry_price"),
                "exit_price": pos.get("exit_price"),
                "exit_reason": pos.get("exit_reason", ""),
                "pnl_pct": pos.get("pnl_pct"),
                "pnl_dollar": pos.get("pnl_dollar"),
                "opened_at": pos.get("opened_at", ""),
                "closed_at": pos.get("closed_at", ""),
            },
            origin=SOURCE_SYSTEM,
        )
        already_reconciled.add(sig_id)
        new_reconciled += 1

    # Persist reconciled IDs so we don't double-push
    try:
        os.makedirs(os.path.dirname(reconciled_path), exist_ok=True)
        with open(reconciled_path, "w") as f:
            json.dump(sorted(already_reconciled), f)
    except Exception as e:
        log.warning("Failed to save reconciled IDs: %s", e)

    log.info("Reconciled %d closed trades to audit trail", new_reconciled)
    return {"status": "ok", "reconciled": new_reconciled}


def main():
    picks = load_picks()
    if not picks:
        log.info("No active Coinglass DNA picks to push to audit trail")
    else:
        log.info("Pushing %d Coinglass DNA picks to audit trail...", len(picks))
        result = push_to_audit(picks)
        log.info("Active picks result: %s", result)

    # Reconcile closed trades from coinglass.db to audit trail
    reconcile_result = reconcile_closed_trades()
    log.info("Reconciliation result: %s", reconcile_result)


if __name__ == "__main__":
    main()
