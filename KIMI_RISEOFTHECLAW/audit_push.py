"""KIMI Rise of the Claw — Audit Trail Push (SQLite + MySQL dual-write)."""
import json, logging, os, sys

log = logging.getLogger("kimi.audit_push")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

SOURCE = "KIMI_RiseOfTheClaw"
DATA = os.path.join(os.path.dirname(__file__), "data", "live_signals_now.json")


def load_picks():
    if not os.path.exists(DATA):
        return []
    with open(DATA) as f:
        data = json.load(f)
    picks = []
    for key in ("crypto_signals", "forex_signals", "stock_signals"):
        picks.extend(data.get(key, []))
    return picks


def normalize(p):
    return {
        "symbol": p.get("symbol", ""),
        "direction": p.get("signal", "BUY"),
        "entry_price": p.get("entryPrice", p.get("price", 0)),
        "take_profit": p.get("take_profit", p.get("targetPrice", 0)),
        "stop_loss": p.get("stop_loss", p.get("stopPrice", 0)),
        "confidence": (p.get("confidence", 50) or 50) / 100.0 if (p.get("confidence", 50) or 50) > 1 else p.get("confidence", 0.5),
        "strategy": p.get("algorithm", "kimi"),
        "timestamp": p.get("timestamp", ""),
    }


def main():
    try:
        from audit_trail import start_run, finish_run, record_raw_pick, record_event
    except ImportError as e:
        log.error("audit_trail not available: %s", e)
        return

    picks = load_picks()
    if not picks:
        log.info("No KIMI picks to push")
        return

    run_id = start_run(regime_data={"source": SOURCE})
    ok = 0
    for p in picks:
        if record_raw_pick(SOURCE, normalize(p), run_id):
            ok += 1

    finish_run(run_id, consensus_count=ok, systems_loaded=1, raw_count=len(picks))
    record_event("KIMI_AUDIT_PUSH", run_id=run_id,
                 payload={"recorded": ok, "total": len(picks)}, origin=SOURCE)

    try:
        from audit_trail.db import get_connection, close as audit_close
        get_connection().execute("PRAGMA wal_checkpoint(TRUNCATE)")
        audit_close()
    except Exception:
        pass

    log.info("KIMI: %d/%d picks pushed to audit trail", ok, len(picks))


if __name__ == "__main__":
    main()
