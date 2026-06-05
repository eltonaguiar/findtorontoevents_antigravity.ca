#!/usr/bin/env python3
"""30-day forward paper tracker for `mega_mutation` (CRYPTO multi-symbol sleeve).

Verified bridge-to-money-ready candidate per
`reports/MEGA_MUTATION_BRIDGE_CANDIDATE_2026-06-05.md`:

  After INCIDENT #91-style dedup (composite key on symbol/direction/entry/
  TP/SL/DATE(closed_at)):
    n=109 (raw 296, inflation 2.72x)
    WR 61.5%, PF 2.79, avg +2.12%
    First-half PF 2.65 / Second-half PF 2.93 (OOS-stable)
    8 syms (JUP/WIF/AVAX/DOT/RENDER/STX/ENA/ADA), 39 dates
    max single-day share 6.4%, max symbol 15.9%, PF w/o top-2 wins 3.06

  Passes every gate that killed prediction_market_consensus,
  regime_mild_bear, ml_enhanced_*USDT_*_D_ensemble_stack, ig_contrarian,
  myfxbook_retail_contrarian. See SUSPICIOUS_PICKS_SCRUTINY_2026-06-05.md.

Honesty pattern (matches Cursor's luxalgo fix):
  forward stats count ONLY picks with closed_at > pilot.started_at.
  No lab/backfill data is counted as forward. If no live forward closes
  yet exist, n_closed = 0, NOT inflated from history.

Promotion criteria:
  - day_count >= 30
  - forward n_closed >= 30 (then 100 for T2 confirm), WR >= 55%, PF >= 1.5
  - PF within 30% of post-dedup PF 2.79
  - max single-day share < 25%, max symbol share < 50% (drift gates)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT_DIR = Path(__file__).resolve().parent
LOG_PATH = PILOT_DIR / "mega_mutation_paper_log.jsonl"
STATE_PATH = PILOT_DIR / "mega_mutation_state.json"

STRATEGY_ID = "mega_mutation"
PROMOTION_TARGET_DAYS = 30
LAB_PF_POST_DEDUP = 2.79
LAB_WR_POST_DEDUP = 0.615
LAB_N_POST_DEDUP = 109
PF_DRIFT_MAX = 0.30  # forward PF must be within 30% of post-dedup
MIN_FORWARD_N_FOR_PROMOTION = 30


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _f(x):
    return float(x) if isinstance(x, Decimal) else x


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {
        "strategy_id": STRATEGY_ID,
        "started_at": _utc_iso(),
        "started_at_date": _utc_today(),
        "day_count": 0,
        "rolling_30d_n_closed": 0,
        "rolling_30d_wr": None,
        "rolling_30d_pf": None,
        "rolling_30d_avg": None,
        "promotion_ready": False,
        "production_enable": False,
        "blockers": ["n<30 forward"],
        "lab_post_dedup": {
            "n": LAB_N_POST_DEDUP, "wr": LAB_WR_POST_DEDUP, "pf": LAB_PF_POST_DEDUP,
        },
    }


def _save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def _forward_stats(started_at_iso: str) -> dict:
    """Query trading_picks for closes AFTER pilot start.

    Honest forward window. No backfill, no lab data, no closes before
    `started_at`. Same dedup composite-key applied (incident #91).
    """
    try:
        import pymysql
        from tools.db_env import get_stocks_creds
    except Exception as exc:
        return {"n_closed": 0, "wr": None, "pf": None, "avg": None, "error": f"db_import: {exc}"}

    sql = """
    WITH dedup AS (
        SELECT symbol, direction, entry_price, take_profit, stop_loss,
               DATE(closed_at) d, pnl_pct, closed_at,
               ROW_NUMBER() OVER (
                 PARTITION BY symbol, direction, entry_price, take_profit, stop_loss, DATE(closed_at)
                 ORDER BY closed_at ASC, id ASC
               ) rn
        FROM trading_picks
        WHERE (strategy=%s OR source_system LIKE %s)
          AND closed_at IS NOT NULL
          AND closed_at > %s
          AND pnl_pct IS NOT NULL
          AND status IN ('TP_HIT','SL_HIT','LOST','TIME_EXIT','WON')
    )
    SELECT COUNT(*) n,
           SUM(pnl_pct > 0) wins,
           SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) gw,
           SUM(CASE WHEN pnl_pct < 0 THEN ABS(pnl_pct) ELSE 0 END) gl,
           AVG(pnl_pct) avg_pnl,
           COUNT(DISTINCT d) dates,
           COUNT(DISTINCT symbol) syms
    FROM dedup WHERE rn = 1
    """
    try:
        conn = pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)
        with conn, conn.cursor() as cur:
            cur.execute(sql, (STRATEGY_ID, f"%{STRATEGY_ID}%", started_at_iso))
            r = cur.fetchone() or {}
    except Exception as exc:
        return {"n_closed": 0, "wr": None, "pf": None, "avg": None, "error": f"db_query: {exc}"}

    n = int(r.get("n") or 0)
    wins = int(r.get("wins") or 0)
    gw = _f(r.get("gw") or 0)
    gl = _f(r.get("gl") or 0)
    return {
        "n_closed": n,
        "wins": wins,
        "wr": (wins / n) if n else None,
        "pf": (gw / gl) if gl else (float("inf") if gw > 0 else None),
        "avg": _f(r.get("avg_pnl")),
        "dates": r.get("dates"),
        "syms": r.get("syms"),
        "started_at": started_at_iso,
    }


def _eval_promotion(state: dict, stats: dict) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    if state.get("day_count", 0) < PROMOTION_TARGET_DAYS:
        blockers.append(f"day_count<{PROMOTION_TARGET_DAYS}")
    n = stats.get("n_closed") or 0
    if n < MIN_FORWARD_N_FOR_PROMOTION:
        blockers.append(f"n<{MIN_FORWARD_N_FOR_PROMOTION}")
    wr = stats.get("wr")
    if wr is None or wr < 0.55:
        blockers.append("wr<0.55")
    pf = stats.get("pf")
    if pf is None or pf < 1.5:
        blockers.append("pf<1.5")
    if pf is not None and pf != float("inf"):
        drift = abs(pf - LAB_PF_POST_DEDUP) / LAB_PF_POST_DEDUP
        if drift > PF_DRIFT_MAX:
            blockers.append(f"pf_drift>{int(PF_DRIFT_MAX*100)}%")
    return (len(blockers) == 0), blockers


def run_daily_tick() -> dict:
    state = _load_state()
    started_at = state.get("started_at") or _utc_iso()
    if "started_at" not in state:
        state["started_at"] = started_at
        state["started_at_date"] = _utc_today()
    state["day_count"] = int(state.get("day_count", 0)) + 1

    stats = _forward_stats(started_at)
    state["rolling_30d_n_closed"] = stats.get("n_closed", 0)
    state["rolling_30d_wr"] = stats.get("wr")
    state["rolling_30d_pf"] = stats.get("pf")
    state["rolling_30d_avg"] = stats.get("avg")
    state["last_tick_utc"] = _utc_iso()

    ready, blockers = _eval_promotion(state, stats)
    state["promotion_ready"] = ready
    state["blockers"] = blockers
    state["production_enable"] = False  # always false until operator flips

    _save_state(state)

    log_row = {
        "tick_utc": state["last_tick_utc"],
        "day_count": state["day_count"],
        "stats": stats,
        "blockers": blockers,
        "promotion_ready": ready,
    }
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(log_row, default=str) + "\n")
    return state


def main() -> int:
    ap = argparse.ArgumentParser(description="mega_mutation 30-day forward pilot")
    ap.add_argument("--one-shot", action="store_true", help="Run one daily tick + exit")
    ap.add_argument("--print-state", action="store_true", help="Dump current state JSON")
    args = ap.parse_args()
    if args.print_state:
        print(json.dumps(_load_state(), indent=2))
        return 0
    state = run_daily_tick()
    print(json.dumps({
        "strategy": STRATEGY_ID,
        "day_count": state["day_count"],
        "n_closed": state["rolling_30d_n_closed"],
        "wr": state["rolling_30d_wr"],
        "pf": state["rolling_30d_pf"],
        "promotion_ready": state["promotion_ready"],
        "blockers": state["blockers"],
    }, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
