#!/usr/bin/env python3
"""30-day forward paper tracker for luxalgo_confluence (CRYPTO sleeve).

Most defensible production CRYPTO edge post deep_audit (2026-06-04):
n=381 unique, WR 64.4%, PF 2.36, dup ratio 1.0x. Tracks trailing 30d
closed picks from trading_picks / closed_picks JSON — isolated sleeve,
NOT whole-class CRYPTO sizing.

Promotion criteria (EAGLE-3 pattern):
  - day_count >= 30
  - forward n_closed >= 30, WR >= 55%, PF >= 1.5
  - PF within 30% of lab PF 2.36
  - sign_coherence 0 flips (operator gate before PROMOTED_STRATEGIES)
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
LOG_PATH = PILOT_DIR / "luxalgo_confluence_paper_log.jsonl"
STATE_PATH = PILOT_DIR / "luxalgo_confluence_state.json"
STRATEGY_ID = "luxalgo_confluence"
PROMOTION_TARGET_DAYS = 30
LAB_PF = 2.36
LAB_WR = 0.644
LAB_N = 381


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {
            "strategy_id": STRATEGY_ID,
            "asset_class": "CRYPTO",
            "started_at": _utc_today(),
            "day_count": 0,
            "rolling_30d_pf": None,
            "rolling_30d_wr": None,
            "rolling_30d_n_closed": 0,
            "lab_pf": LAB_PF,
            "lab_wr": LAB_WR,
            "lab_n_closed": LAB_N,
            "promotion_status": "SHADOW",
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


def _stats_from_closed_json(window_days: int = 30) -> dict:
    """Policy-clean closed picks JSON — no MySQL required."""
    for rel in (
        "alpha_engine/data/closed_picks_enriched.json",
        "alpha_engine/data/closed_picks.json",
        "battleground/data/luxalgo_closed_picks.json",
    ):
        path = ROOT / rel
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        picks = data.get("picks", data) if isinstance(data, dict) else data
        if not isinstance(picks, list):
            continue
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

        def _match(p: dict) -> bool:
            src = str(p.get("source_system") or p.get("strategy") or "").lower()
            if STRATEGY_ID not in src and "luxalgo" not in src:
                return False
            if str(p.get("asset_class") or "CRYPTO").upper() != "CRYPTO":
                return False
            ts = p.get("closed_at") or p.get("resolved_at") or p.get("signal_timestamp")
            if not ts:
                return False
            try:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except ValueError:
                return False
            return dt >= cutoff

        closed = [
            p for p in picks
            if p.get("pnl_pct") is not None
            and str(p.get("status") or "").upper() in ("WON", "LOST", "won", "lost")
            and _match(p)
        ]
        if not closed:
            continue
        pnls = [float(p.get("pnl_pct") or 0) for p in closed]
        wins = sum(1 for x in pnls if x > 0)
        gw = sum(x for x in pnls if x > 0)
        gl = abs(sum(x for x in pnls if x < 0))
        n = len(closed)
        pf = (gw / gl) if gl > 0 else (999.0 if gw > 0 else 0.0)
        return {
            "n_closed": n,
            "wins": wins,
            "losses": n - wins,
            "pf": round(pf, 4),
            "wr": round(wins / n, 4),
            "avg_pnl_pct": round(sum(pnls) / n, 4),
            "rolling_30d_pnls": list(reversed(pnls[-100:])),
            "source": rel,
        }
    return {"n_closed": 0, "wins": 0, "losses": 0, "pf": None, "wr": None, "source": "no_data"}


def _dedupe_rows(rows: list[dict]) -> list[dict]:
    """One row per (symbol, direction, entry_price, close day) — INCIDENT dup inflation."""
    seen: set[tuple] = set()
    out: list[dict] = []
    for r in rows:
        closed = r.get("closed_at")
        day = str(closed)[:10] if closed else ""
        key = (
            str(r.get("symbol") or "").upper(),
            str(r.get("direction") or "").upper(),
            round(float(r.get("entry_price") or 0), 6),
            day,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _stats_from_mysql(window_days: int = 30) -> dict | None:
    try:
        import pymysql
        from tools.db_env import get_stocks_creds

        creds = get_stocks_creds()
        conn = pymysql.connect(**creds, cursorclass=pymysql.cursors.DictCursor)
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT symbol, direction, entry_price, pnl_pct, closed_at, status
                FROM trading_picks
                WHERE strategy = %s
                  AND LOWER(category) IN ('crypto', 'cryptocurrency')
                  AND closed_at IS NOT NULL
                  AND closed_at >= %s
                  AND pnl_pct IS NOT NULL
                  AND status NOT IN ('OPEN','ACTIVE','open','active')
                ORDER BY closed_at DESC
                LIMIT 5000
                """,
                (STRATEGY_ID, cutoff.strftime("%Y-%m-%d %H:%M:%S")),
            )
            raw = cur.fetchall()
        conn.close()
        if not raw:
            return None
        rows = _dedupe_rows(raw)
        pnls = [float(r["pnl_pct"]) for r in rows]
        wins = sum(1 for x in pnls if x > 0)
        n = len(pnls)
        gw = sum(x for x in pnls if x > 0)
        gl = abs(sum(x for x in pnls if x < 0))
        pf = (gw / gl) if gl > 0 else (999.0 if gw > 0 else 0.0)
        return {
            "n_closed": n,
            "n_raw": len(raw),
            "dup_ratio": round(len(raw) / max(n, 1), 2),
            "wins": wins,
            "losses": n - wins,
            "pf": round(pf, 4),
            "wr": round(wins / n, 4) if n else None,
            "avg_pnl_pct": round(sum(pnls) / n, 4) if n else None,
            "rolling_30d_pnls": pnls[:100],
            "source": "mysql_deduped",
        }
    except Exception:
        return None


def _query_stats(window_days: int = 30) -> dict:
    live = _stats_from_mysql(window_days)
    if live and live.get("n_closed", 0) > 0:
        return live
    return _stats_from_closed_json(window_days)


def _evaluate(state: dict, stats: dict) -> tuple[str, list[str]]:
    blockers: list[str] = []
    if state.get("day_count", 0) < PROMOTION_TARGET_DAYS:
        blockers.append(f"day_count {state.get('day_count', 0)} < {PROMOTION_TARGET_DAYS}")
    pf = stats.get("pf")
    if pf is None:
        blockers.append("pf unavailable")
    elif pf < 1.5:
        blockers.append(f"pf {pf} < 1.5")
    elif abs(pf - LAB_PF) / LAB_PF > 0.30:
        blockers.append(f"pf drift >30% from lab {LAB_PF}")
    wr = stats.get("wr")
    if wr is not None and wr < 0.55:
        blockers.append(f"wr {wr:.0%} < 55%")
    if stats.get("n_closed", 0) < 30:
        blockers.append(f"n_closed {stats.get('n_closed', 0)} < 30")
    return ("READY_REVIEW", []) if not blockers else ("SHADOW", blockers)


def run_daily_tick() -> dict:
    state = _load_state()
    stats = _query_stats(PROMOTION_TARGET_DAYS)
    state["day_count"] = state.get("day_count", 0) + 1
    state["rolling_30d_pf"] = stats.get("pf")
    state["rolling_30d_wr"] = stats.get("wr")
    state["rolling_30d_n_closed"] = stats.get("n_closed", 0)
    state["rolling_30d_pnls"] = stats.get("rolling_30d_pnls") or []
    state["forward_dup_ratio"] = stats.get("dup_ratio")
    state["forward_n_raw"] = stats.get("n_raw")
    try:
        from audit_trail.promotion_gate import evaluate_forward_tier2

        state["tier2_evaluation"] = evaluate_forward_tier2(
            state["rolling_30d_pnls"],
            oos_pf=stats.get("pf"),
            is_pf=LAB_PF,
        )
    except Exception as exc:
        state["tier2_evaluation"] = {"error": str(exc)}
    status, blockers = _evaluate(state, stats)
    state["promotion_status"] = status
    state["promotion_blockers"] = blockers
    _save_state(state)
    _append_log({
        "date": _utc_today(),
        "day_count": state["day_count"],
        "stats": stats,
        "promotion_status": status,
        "blockers": blockers,
    })
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--one-shot", action="store_true")
    parser.add_argument("--show-state", action="store_true")
    args = parser.parse_args()
    if args.show_state:
        print(json.dumps(_load_state(), indent=2))
        return 0
    state = run_daily_tick()
    print(
        f"[luxalgo_confluence pilot] day {state['day_count']} "
        f"status={state['promotion_status']} n={state.get('rolling_30d_n_closed')}"
    )
    for b in state.get("promotion_blockers") or []:
        print(f"  - {b}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
