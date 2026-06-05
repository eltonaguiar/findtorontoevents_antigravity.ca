#!/usr/bin/env python3
"""PMC (prediction_market_consensus) paper-pilot monitor.

Queries at_pick_outcomes for NEW resolved picks since the last update,
appends them to the JSONL log, recalculates forward stats, checks kill
switches, and prints a dashboard-friendly summary.

Typical cron usage (daily at 06:05 UTC):
    5 6 * * * cd /home/eaguiar2015/findtorontoevents_antigravity.ca && python3 tools/pmc_pilot_monitor.py >> logs/pmc_monitor.log 2>&1
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root is on path so we can import shared helpers if needed
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT_DIR = ROOT / "verified_strategies" / "paper_pilot"
LOG_PATH = PILOT_DIR / "prediction_market_consensus_paper_log.jsonl"
STATE_PATH = PILOT_DIR / "prediction_market_consensus_state.json"
STRATEGY = "prediction_market_consensus"


def _db_connection():
    import pymysql
    from tools.db_env import get_stocks_creds

    return pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)


def _load_state() -> dict:
    if not STATE_PATH.exists():
        raise FileNotFoundError(f"State file missing: {STATE_PATH}")
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def _save_state(state: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _load_log_ids() -> set[str]:
    """Return the set of pick_ids already present in the JSONL log."""
    ids: set[str] = set()
    if not LOG_PATH.exists():
        return ids
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        pid = row.get("pick_id")
        if pid:
            ids.add(pid)
    return ids


def _append_log(row: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def _fetch_new_picks(since_date: str) -> list[dict]:
    """Pull resolved picks for this strategy resolved on or after since_date."""
    conn = _db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  po.pick_id,
                  po.symbol,
                  po.status,
                  po.resolution_method,
                  po.pnl_pct,
                  po.resolved_at,
                  po.resolver_version
                FROM at_pick_outcomes po
                WHERE po.strategy = %s
                  AND po.status IN ('WON','LOST','FLAT')
                  AND DATE(po.resolved_at) >= %s
                ORDER BY po.resolved_at ASC
                """,
                (STRATEGY, since_date),
            )
            return cur.fetchall()
    finally:
        conn.close()


def _infer_direction(pick_id: str) -> str:
    if "_S_" in pick_id:
        return "SHORT"
    if "_L_" in pick_id:
        return "LONG"
    return "LONG"


def _outcome_from_row(row: dict) -> str:
    status = row["status"]
    method = row.get("resolution_method")
    if status == "WON":
        return method or "TP_HIT"
    if status == "LOST":
        return method or "SL_HIT"
    if status == "FLAT":
        return method or "MANUAL"
    return status


def _row_to_log_entry(row: dict) -> dict:
    return {
        "timestamp": row["resolved_at"].isoformat() if row.get("resolved_at") else None,
        "pick_id": row["pick_id"],
        "symbol": row["symbol"],
        "direction": _infer_direction(row["pick_id"]),
        "entry_price": None,
        "tp": None,
        "sl": None,
        "predicted_confidence": None,
        "outcome": _outcome_from_row(row),
        "pnl_pct": float(row["pnl_pct"]) if row["pnl_pct"] is not None else 0.0,
        "resolver_version": row.get("resolver_version"),
    }


def _recalc_stats() -> dict:
    """Recompute forward stats from the full JSONL log."""
    pnls: list[float] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "pick_id" not in row:
            continue
        pnls.append(float(row.get("pnl_pct") or 0))

    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    gross_win = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    pf = gross_win / gross_loss if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0)
    wr = (wins / n * 100) if n else 0.0
    avg_pnl = sum(pnls) / n if n else 0.0
    total_pnl = sum(pnls)

    return {
        "forward_n": n,
        "forward_wr": round(wr, 2),
        "forward_pf": round(pf, 3),
        "forward_avg_pnl": round(avg_pnl, 2),
        "forward_total_pnl": round(total_pnl, 2),
        "wins": wins,
        "losses": losses,
        "flats": sum(1 for p in pnls if p == 0),
    }


def _check_kill_switch(stats: dict, state: dict) -> dict:
    """Evaluate kill-switch conditions and return status block."""
    ks = state.get("kill_switch", {})
    wr_floor = state.get("kill_switch_wr_floor", 55.0)
    n_min = state.get("kill_switch_n_min", 50)

    active = False
    reasons: list[str] = []

    n = stats["forward_n"]
    wr = stats["forward_wr"]

    if n >= n_min and wr < wr_floor:
        active = True
        reasons.append(f"WR {wr:.1f}% < floor {wr_floor}% (n={n})")

    ks["active"] = active
    ks["reasons"] = reasons
    ks["last_checked"] = datetime.now(timezone.utc).isoformat()
    state["kill_switch"] = ks
    return state


def _recent_picks(limit: int = 10) -> list[dict]:
    """Return the most recent *closed* picks from the log."""
    rows: list[dict] = []
    if not LOG_PATH.exists():
        return rows
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "pick_id" in row:
            rows.append(row)
    rows.sort(key=lambda r: r.get("timestamp") or "", reverse=True)
    return rows[:limit]


def _dashboard_json(state: dict, stats: dict, recent: list[dict]) -> dict:
    ks = state.get("kill_switch", {})
    return {
        "strategy": STRATEGY,
        "asset_class": state.get("asset_class", "CRYPTO"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "forward": {
            "n": stats["forward_n"],
            "wr": stats["forward_wr"],
            "pf": stats["forward_pf"],
            "avg_pnl": stats["forward_avg_pnl"],
            "total_pnl": stats["forward_total_pnl"],
        },
        "promotion_ready": state.get("promotion_ready", False),
        "shadow_mode": state.get("shadow_mode", True),
        "kill_switch": {
            "active": ks.get("active", False),
            "reasons": ks.get("reasons", []),
            "wr_floor": state.get("kill_switch_wr_floor", 55.0),
            "n_min": state.get("kill_switch_n_min", 50),
        },
        "recent_picks": recent,
    }


def main() -> int:
    state = _load_state()
    last_updated = state.get("last_updated", state.get("started_date", "2026-06-05"))

    existing_ids = _load_log_ids()
    new_rows = _fetch_new_picks(last_updated)

    added = 0
    for row in new_rows:
        if row["pick_id"] in existing_ids:
            continue
        entry = _row_to_log_entry(row)
        _append_log(entry)
        existing_ids.add(row["pick_id"])
        added += 1

    stats = _recalc_stats()
    state.update(stats)
    state["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    state = _check_kill_switch(stats, state)
    _save_state(state)

    recent = _recent_picks(10)
    dash = _dashboard_json(state, stats, recent)

    # Console summary
    print("=" * 60)
    print(f"  PMC Paper Pilot — {STRATEGY}")
    print("=" * 60)
    print(f"  Forward N      : {stats['forward_n']}")
    print(f"  Forward WR     : {stats['forward_wr']:.2f}%")
    print(f"  Forward PF     : {stats['forward_pf']:.3f}")
    print(f"  Avg PnL        : {stats['forward_avg_pnl']:+.2f}%")
    print(f"  Total PnL      : {stats['forward_total_pnl']:+.2f}%")
    print(f"  New picks today: {added}")
    print(f"  Kill switch    : {'TRIPPED — ' + ', '.join(dash['kill_switch']['reasons']) if dash['kill_switch']['active'] else 'OK'}")
    print("-" * 60)
    print("  Recent 10 picks:")
    for p in recent:
        ts = (p.get("timestamp") or "")[:10]
        print(f"    {ts}  {p['symbol']:10s}  {p['direction']:5s}  {p['outcome']:12s}  {p['pnl_pct']:+.2f}%")
    print("=" * 60)

    # Also write a dashboard payload next to the state file
    dash_path = PILOT_DIR / "prediction_market_consensus_dashboard.json"
    dash_path.write_text(json.dumps(dash, indent=2, default=str), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
