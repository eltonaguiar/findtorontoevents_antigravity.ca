#!/usr/bin/env python3
"""Virtual forward book for inverse_ml_enhanced_ADAUSDT_15m_D (bootstrap FORWARD_TRACK).

Strongest bootstrap sleeve per pilot_forward_dashboard (PF~1.73, WR~56%, n=36 DB).
Virtual log + daily mark; production enable stays False until forward n>=100.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT_DIR = Path(__file__).resolve().parent
LOG_PATH = PILOT_DIR / "inverse_ml_ada_paper_log.jsonl"
STATE_PATH = PILOT_DIR / "inverse_ml_ada_state.json"
STRATEGY_ID = "inverse_ml_enhanced_ADAUSDT_15m_D"
LAB_OOS_PF = 1.73
LAB_WR = 0.556
LAB_N = 36


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_today() -> str:
    return _utc_now().strftime("%Y-%m-%d")


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {"strategy_id": STRATEGY_ID, "open_position": None, "day_count": 0}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"strategy_id": STRATEGY_ID, "open_position": None, "day_count": 0}


def _save_state(state: dict) -> None:
    state["last_update_utc"] = _utc_now().isoformat()
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _append_log(row: dict) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def _current_price(symbol: str) -> float | None:
    from alpha_engine.ml_strategy_reviver import (
        _fetch_price_binance,
        _fetch_price_coingecko,
    )

    px = _fetch_price_binance(symbol)
    if px is None:
        px = _fetch_price_coingecko(symbol)
    return px


def _resolve_short(open_pos: dict, last_px: float, now: datetime) -> str | None:
    tp = float(open_pos["take_profit"])
    sl = float(open_pos["stop_loss"])
    if last_px <= tp:
        return "TP_HIT"
    if last_px >= sl:
        return "SL_HIT"
    expires = open_pos.get("expires_at")
    if expires:
        try:
            exp = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            if now >= exp:
                return "TIME_EXIT"
        except ValueError:
            pass
    entry_date = open_pos.get("entry_date")
    if entry_date:
        try:
            held = (now.date() - datetime.strptime(entry_date, "%Y-%m-%d").date()).days
            if held >= 3:
                return "TIME_EXIT"
        except ValueError:
            pass
    return None


def _db_forward_deduped() -> dict | None:
    """Policy-forward stats from trading_picks (deduped)."""
    try:
        import pymysql
        from tools.db_env import get_stocks_creds

        creds = get_stocks_creds()
        conn = pymysql.connect(**creds, cursorclass=pymysql.cursors.DictCursor)
        cutoff = (_utc_now() - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT symbol, direction, entry_price, pnl_pct, closed_at
                FROM trading_picks
                WHERE strategy = %s AND closed_at >= %s AND pnl_pct IS NOT NULL
                ORDER BY closed_at DESC LIMIT 3000
                """,
                (STRATEGY_ID, cutoff),
            )
            raw = cur.fetchall()
        conn.close()
        if not raw:
            return None
        seen: set[str] = set()
        pnls: list[float] = []
        missing_pnl = 0
        for r in raw:
            ts = str(r.get("closed_at") or "")
            key = ts
            if key in seen:
                continue
            seen.add(key)
            if r.get("pnl_pct") is None:
                missing_pnl += 1
                continue
            pnls.append(float(r["pnl_pct"]))
        if not pnls:
            return None
        wins = sum(1 for x in pnls if x > 0)
        n = len(pnls)
        gw = sum(x for x in pnls if x > 0)
        gl = abs(sum(x for x in pnls if x < 0))
        pf = (gw / gl) if gl > 0 else (999.0 if gw > 0 else 0.0)
        return {
            "n_closed": n,
            "wr": round(wins / n, 4),
            "pf": round(pf, 4),
            "rolling_pnls": pnls[:100],
            "source": "mysql_deduped_90d",
            "rows_seen": len(raw),
            "pnl_null_skipped": missing_pnl,
        }
    except Exception:
        return None


def run_daily_tick() -> dict:
    today = _utc_today()
    now = _utc_now()
    state = _load_state()
    state["day_count"] = int(state.get("day_count") or 0) + 1

    from alpha_engine.ml_strategy_reviver import INVERSE_STRATEGIES, _generate_inverse_pick

    cfg = INVERSE_STRATEGIES[STRATEGY_ID]
    symbol = cfg["symbol"]
    last_px = _current_price(symbol)
    if last_px is None:
        state["note"] = "price_unavailable"
        _save_state(state)
        return state

    open_pos = state.get("open_position")
    if open_pos and open_pos.get("status") == "OPEN":
        outcome = _resolve_short(open_pos, last_px, now)
        if outcome:
            entry = float(open_pos["entry_price"])
            pnl_pct = (entry - last_px) / entry if entry else 0.0
            _append_log(
                {
                    "event": "CLOSE",
                    "strategy": STRATEGY_ID,
                    "symbol": symbol,
                    "direction": "SELL",
                    "entry_price": entry,
                    "exit_price": last_px,
                    "pnl_pct": round(pnl_pct, 6),
                    "outcome": outcome,
                    "closed_at": today,
                }
            )
            state["open_position"] = None
        else:
            open_pos["last_seen"] = today
            open_pos["mark_price"] = last_px
            state["open_position"] = open_pos
    elif not open_pos:
        pick = _generate_inverse_pick(STRATEGY_ID, cfg)
        if pick:
            expires = pick.get("expires_at") or (
                now + timedelta(hours=cfg.get("expiry_hours", 2))
            ).isoformat()
            state["open_position"] = {
                "strategy": STRATEGY_ID,
                "symbol": symbol,
                "direction": "SELL",
                "status": "OPEN",
                "entry_price": float(pick["entry_price"]),
                "take_profit": float(pick["take_profit"]),
                "stop_loss": float(pick["stop_loss"]),
                "entry_date": today,
                "expires_at": expires,
            }
            _append_log({"event": "OPEN", "strategy": STRATEGY_ID, "opened_at": today, **state["open_position"]})

    from verified_strategies.paper_pilot.pilot_forward_summary import forward_block

    state["forward_virtual"] = forward_block(
        log_path=LOG_PATH,
        strategy_id=STRATEGY_ID,
        oos_pf=LAB_OOS_PF,
        open_position=state.get("open_position"),
    )
    state["forward_db"] = _db_forward_deduped()
    try:
        from audit_trail.promotion_gate import evaluate_forward_tier2

        pnls = (state.get("forward_db") or {}).get("rolling_pnls") or []
        state["tier2_db"] = evaluate_forward_tier2(pnls, oos_pf=(state["forward_db"] or {}).get("pf"), is_pf=LAB_OOS_PF)
        v_pnls = [
            float(r.get("pnl_pct") or 0)
            for r in (state.get("forward_virtual") or {}).get("closed_rows") or []
        ]
        if not v_pnls:
            from verified_strategies.paper_pilot.pilot_forward_summary import closed_rows_from_log
            closed = closed_rows_from_log(LOG_PATH, STRATEGY_ID)
            v_pnls = [float(r.get("pnl_pct") or 0) for r in closed]
        state["tier2_virtual"] = evaluate_forward_tier2(v_pnls, oos_pf=LAB_OOS_PF, is_pf=LAB_OOS_PF)
    except Exception as exc:
        state["tier2_error"] = str(exc)
    state["lab_reference"] = {"pf": LAB_OOS_PF, "wr": LAB_WR, "n": LAB_N}
    state["production_enable"] = False
    _save_state(state)
    return state


def main() -> int:
    state = run_daily_tick()
    v = state.get("forward_virtual") or {}
    db = state.get("forward_db") or {}
    print(
        f"[inverse_ml_ada pilot] virtual n={v.get('n_closed')} pf={v.get('pf')} | "
        f"db n={db.get('n_closed')} wr={db.get('wr')} pf={db.get('pf')}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())