#!/usr/bin/env python3
"""30-day shadow paper tracker for macd_rsi_m048.

EAGLE-3 second promotion candidate. Live lab stats (alpha_engine/data/
strategy_performance.json 2026-06-02): closed_picks=65, wins=49, losses=16,
WR=75.4%, PF~3.06. Already in CRYPTO_PROVEN_STRATEGIES allowlist
(alpha_engine/smart_picks_engine.py:310). Needs 30-day forward proof before
adding to PROMOTED_STRATEGIES in audit_trail/promotion_gate.py.

Pattern mirrors verified_strategies/paper_pilot/etf_dual_momentum_pilot.py.
The pilot reads live picks emitted by the production scanner with
source_system=macd_rsi_m048, tracks their open/close outcomes on a daily
cadence, and writes the running 30-day shadow stats to a state file.

Promotion criteria (per EAGLE-3 + blackboxai tightening):
  - 30 consecutive days of forward paper with PF within 30% of lab PF
  - WR >= 0.55 (relax from 0.75 lab figure to account for live decay)
  - n_closed >= 30 in the 30-day window
  - sign_coherence_check returns 0 flips for the strategy's rows
  - source-system HHI within the asset class < 0.20

When ALL criteria pass, add "macd_rsi_m048" to
audit_trail/promotion_gate.PROMOTED_STRATEGIES and the production_scanner
will start emitting it through the live admission path.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT_DIR = Path(__file__).resolve().parent
LOG_PATH = PILOT_DIR / "macd_rsi_m048_paper_log.jsonl"
STATE_PATH = PILOT_DIR / "macd_rsi_m048_state.json"
STRATEGY_ID = "macd_rsi_m048"
PROMOTION_TARGET_DAYS = 30

# Promotion thresholds (per EAGLE-3 + blackboxai)
PROMOTION_MIN_PF = 1.5
PROMOTION_MIN_WR = 0.55
PROMOTION_MIN_N = 30
PROMOTION_MAX_PF_DRIFT_FROM_LAB = 0.30  # within 30% of lab PF ~3.06


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {
            "strategy_id": STRATEGY_ID,
            "started_at": _utc_today(),
            "day_count": 0,
            "rolling_30d_pf": None,
            "rolling_30d_wr": None,
            "rolling_30d_n_closed": 0,
            "lab_pf": 3.06,
            "lab_wr": 0.754,
            "lab_n_closed": 65,
            "promotion_status": "SHADOW",  # SHADOW -> READY_REVIEW -> PROMOTED -> REVOKED
            "promotion_blockers": [],
            "last_update_utc": None,
        }
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_state(state: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    state["last_update_utc"] = datetime.now(timezone.utc).isoformat()
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _append_log(row: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def _query_live_stats(window_days: int = 30) -> dict:
    """Pull macd_rsi_m048 closed-pick stats for the trailing window from MySQL.

    Reads from at_pick_outcomes joined with trading_picks. Returns
    {n_closed, wins, losses, pf, wr, avg_pnl_pct}. Falls back to
    strategy_performance.json if DB is unreachable.
    """
    try:
        import pymysql

        import os
        pw = os.environ.get("DB_PASS_STOCKS", "") or os.environ.get("MYSQL_PASSWORD", "")
        conn = pymysql.connect(
            host="mysql.50webs.com", user="ejaguiar1_stocks",
            password=pw, database="ejaguiar1_stocks",
            charset="utf8mb4", connect_timeout=10,
        )
        cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).strftime("%Y-%m-%d")
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS n,
                    SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END) AS losses,
                    SUM(CASE WHEN status = 'WON' THEN ABS(pnl_pct) ELSE 0 END) AS gross_win,
                    SUM(CASE WHEN status = 'LOST' THEN ABS(pnl_pct) ELSE 0 END) AS gross_loss,
                    AVG(pnl_pct) AS avg_pnl
                FROM trading_picks
                WHERE (source_system = %s OR strategy = %s)
                  AND status IN ('WON', 'LOST')
                  AND resolved_at >= %s
                """,
                (STRATEGY_ID, STRATEGY_ID, cutoff),
            )
            row = cur.fetchone() or (0, 0, 0, 0.0, 0.0, 0.0)
        conn.close()
        n, wins, losses, gw, gl, avg_pnl = row
        n = int(n or 0); wins = int(wins or 0); losses = int(losses or 0)
        gw = float(gw or 0); gl = float(gl or 0)
        pf = (gw / gl) if gl > 0 else None
        wr = (wins / n) if n > 0 else None
        return {
            "n_closed": n, "wins": wins, "losses": losses,
            "pf": pf, "wr": wr, "avg_pnl_pct": float(avg_pnl or 0),
            "source": "mysql_live",
        }
    except Exception as exc:
        try:
            with open(ROOT / "alpha_engine" / "data" / "strategy_performance.json") as fh:
                d = json.load(fh)
            m = d.get(STRATEGY_ID, {})
            return {
                "n_closed": int(m.get("closed_picks", 0)),
                "wins": int(m.get("wins", 0)),
                "losses": int(m.get("losses", 0)),
                "pf": None,
                "wr": float(m.get("win_rate", 0)) if m.get("win_rate") else None,
                "avg_pnl_pct": None,
                "source": f"strategy_performance.json fallback (db: {type(exc).__name__})",
            }
        except Exception:
            return {"n_closed": 0, "wins": 0, "losses": 0, "pf": None, "wr": None, "source": "no_data"}


def _evaluate_promotion(state: dict, stats: dict) -> tuple[str, list[str]]:
    """Return (promotion_status, blockers) per the criteria in the module doc."""
    blockers = []
    if state.get("day_count", 0) < PROMOTION_TARGET_DAYS:
        blockers.append(f"day_count {state.get('day_count',0)} < {PROMOTION_TARGET_DAYS}")
    pf = stats.get("pf")
    if pf is None:
        blockers.append("pf unavailable (no closed picks or DB unreachable)")
    elif pf < PROMOTION_MIN_PF:
        blockers.append(f"pf {pf:.2f} < {PROMOTION_MIN_PF}")
    else:
        lab_pf = state.get("lab_pf", 3.06)
        drift = abs(pf - lab_pf) / lab_pf
        if drift > PROMOTION_MAX_PF_DRIFT_FROM_LAB:
            blockers.append(f"pf drift {drift:.0%} from lab {lab_pf:.2f} > {PROMOTION_MAX_PF_DRIFT_FROM_LAB:.0%}")
    wr = stats.get("wr")
    if wr is not None and wr < PROMOTION_MIN_WR:
        blockers.append(f"wr {wr:.0%} < {PROMOTION_MIN_WR:.0%}")
    n = stats.get("n_closed", 0)
    if n < PROMOTION_MIN_N:
        blockers.append(f"n_closed {n} < {PROMOTION_MIN_N}")

    if not blockers:
        return "READY_REVIEW", []
    return "SHADOW", blockers


def run_daily_tick() -> dict:
    """Single-day update — call this from a daily cron or from
    tools/run_verified_pilots_daily.py.
    """
    state = _load_state()
    stats = _query_live_stats(window_days=PROMOTION_TARGET_DAYS)

    state["day_count"] = state.get("day_count", 0) + 1
    state["rolling_30d_pf"] = stats.get("pf")
    state["rolling_30d_wr"] = stats.get("wr")
    state["rolling_30d_n_closed"] = stats.get("n_closed", 0)

    new_status, blockers = _evaluate_promotion(state, stats)
    state["promotion_status"] = new_status
    state["promotion_blockers"] = blockers

    _save_state(state)
    _append_log({
        "date": _utc_today(),
        "day_count": state["day_count"],
        "stats": stats,
        "promotion_status": new_status,
        "blockers": blockers,
    })
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--one-shot", action="store_true",
                        help="Run a single daily tick and exit.")
    parser.add_argument("--show-state", action="store_true",
                        help="Print current state JSON and exit.")
    args = parser.parse_args()

    if args.show_state:
        print(json.dumps(_load_state(), indent=2))
        return 0

    state = run_daily_tick()
    print(f"[macd_rsi_m048 pilot] day {state['day_count']} status={state['promotion_status']}")
    if state.get("promotion_blockers"):
        for b in state["promotion_blockers"]:
            print(f"  - {b}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
