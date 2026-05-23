"""ML Battleground (Systems A-F) — Audit Trail Push (SQLite + MySQL dual-write)."""
import json, logging, os, sys

log = logging.getLogger("battleground.audit_push")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# Each sub-system gets its own source ID in the audit trail
SYSTEMS = [
    {"id": "Battleground_A", "name": "System A: The Filter",
     "data": os.path.join(os.path.dirname(__file__), "system_a_filter", "data", "active_picks.json")},
    {"id": "Battleground_B", "name": "System B: Regime",
     "data": os.path.join(os.path.dirname(__file__), "system_b_regime", "data", "active_picks.json")},
    {"id": "Battleground_C", "name": "System C: DeepLearn",
     "data": os.path.join(os.path.dirname(__file__), "system_c_deeplearn", "data", "active_picks.json")},
    {"id": "Battleground_D", "name": "System D: Carry",
     "data": os.path.join(os.path.dirname(__file__), "system_d_carry", "data", "active_picks.json")},
    {"id": "Battleground_E", "name": "System E: Momentum",
     "data": os.path.join(os.path.dirname(__file__), "system_e_momentum", "data", "active_picks.json")},
    {"id": "Battleground_F", "name": "System F: Claws of Doom",
     "data": os.path.join(os.path.dirname(__file__), "system_f_clawsofdoom", "data", "active_picks.json")},
]

# Also check the main battleground active_picks
BG_MAIN = os.path.join(os.path.dirname(os.path.dirname(__file__)), "battleground", "data", "active_picks.json")


def load_picks(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
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
        "confidence": p.get("confidence", p.get("ml_score", 0.5)),
        "strategy": p.get("strategy", "battleground"),
        "timestamp": p.get("timestamp", ""),
    }


def main():
    try:
        from audit_trail import start_run, finish_run, record_raw_pick, record_event
    except ImportError as e:
        log.error("audit_trail not available: %s", e)
        return

    total_ok = 0
    total_picks = 0

    # Push each sub-system independently
    for sys_info in SYSTEMS:
        picks = load_picks(sys_info["data"])
        if not picks:
            continue

        source = sys_info["id"]
        run_id = start_run(regime_data={"source": source})
        ok = 0
        for p in picks:
            if record_raw_pick(source, normalize(p), run_id):
                ok += 1

        finish_run(run_id, consensus_count=ok, systems_loaded=1, raw_count=len(picks))
        record_event("BATTLEGROUND_AUDIT_PUSH", run_id=run_id,
                     payload={"system": source, "recorded": ok, "total": len(picks)}, origin=source)
        log.info("%s: %d/%d picks pushed", source, ok, len(picks))
        total_ok += ok
        total_picks += len(picks)

    # Also push main battleground picks
    main_picks = load_picks(BG_MAIN)
    if main_picks:
        source = "Battleground_Main"
        run_id = start_run(regime_data={"source": source})
        ok = 0
        for p in main_picks:
            if record_raw_pick(source, normalize(p), run_id):
                ok += 1
        finish_run(run_id, consensus_count=ok, systems_loaded=1, raw_count=len(main_picks))
        log.info("%s: %d/%d picks pushed", source, ok, len(main_picks))
        total_ok += ok
        total_picks += len(main_picks)

    # WAL checkpoint
    try:
        from audit_trail.db import get_connection, close as audit_close
        get_connection().execute("PRAGMA wal_checkpoint(TRUNCATE)")
        audit_close()
    except Exception:
        pass

    log.info("Battleground total: %d/%d picks pushed to audit trail", total_ok, total_picks)


if __name__ == "__main__":
    main()
