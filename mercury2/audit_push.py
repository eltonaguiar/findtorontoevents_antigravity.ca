"""Mercury2 — Audit Trail Push (SQLite + MySQL dual-write)."""
import json, logging, os, sys

log = logging.getLogger("mercury2.audit_push")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

SOURCE = "Mercury2"
DATA = os.path.join(os.path.dirname(__file__), "data", "active_picks.json")


def load_picks():
    if not os.path.exists(DATA):
        return []
    with open(DATA) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return data.get("picks", data.get("active_picks", []))


def normalize(p):
    return {
        "symbol": p.get("symbol", ""),
        "direction": p.get("direction", p.get("signal_type", "BUY")),
        "entry_price": p.get("entry_price", 0),
        "take_profit": p.get("take_profit", 0),
        "stop_loss": p.get("stop_loss", 0),
        "confidence": p.get("confidence", 0.5),
        "strategy": p.get("strategy", "mercury2_ensemble"),
        "timestamp": p.get("timestamp", ""),
    }


def main():
    try:
        from audit_trail import start_run, finish_run, record_raw_pick, record_event
    except ImportError as e:
        log.error("audit_trail not available: %s", e)
        return

    picks = [p for p in load_picks() if p.get("status", "ACTIVE").upper() == "ACTIVE"]
    if not picks:
        log.info("No Mercury2 picks to push")
        return

    run_id = start_run(regime_data={"source": SOURCE})
    ok = 0
    for p in picks:
        if record_raw_pick(SOURCE, normalize(p), run_id):
            ok += 1

    finish_run(run_id, consensus_count=ok, systems_loaded=1, raw_count=len(picks))
    record_event("MERCURY2_AUDIT_PUSH", run_id=run_id,
                 payload={"recorded": ok, "total": len(picks)}, origin=SOURCE)

    try:
        from audit_trail.db import get_connection, close as audit_close
        get_connection().execute("PRAGMA wal_checkpoint(TRUNCATE)")
        audit_close()
    except Exception:
        pass

    log.info("Mercury2: %d/%d picks pushed to audit trail", ok, len(picks))


if __name__ == "__main__":
    main()
