#!/usr/bin/env python3
"""Virtual forward book for inverse_ml_enhanced_BTCUSDT_15m_D (bootstrap-approved).

PR #482: n=65 IS PF~34.5, pf_lo_95=15.97 — forward-test only.
Uses ml_strategy_reviver inverse SHORT logic; daily mark checks TP/SL.
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
LOG_PATH = PILOT_DIR / "inverse_ml_btc_paper_log.jsonl"
STATE_PATH = PILOT_DIR / "inverse_ml_btc_state.json"
STRATEGY_ID = "inverse_ml_enhanced_BTCUSDT_15m_D"
LAB_OOS_PF = 34.46


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
            expires = pick.get("expires_at")
            if not expires:
                expires = (now + timedelta(hours=cfg.get("expiry_hours", 2))).isoformat()
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
            _append_log(
                {
                    "event": "OPEN",
                    "strategy": STRATEGY_ID,
                    "opened_at": today,
                    **state["open_position"],
                }
            )

    from verified_strategies.paper_pilot.pilot_forward_summary import forward_block

    state["forward"] = forward_block(
        log_path=LOG_PATH,
        strategy_id=STRATEGY_ID,
        oos_pf=LAB_OOS_PF,
        open_position=state.get("open_position"),
    )
    state["lab_is_pf"] = LAB_OOS_PF
    state["production_enable"] = False
    _save_state(state)
    return state


def main() -> int:
    state = run_daily_tick()
    fwd = state.get("forward") or {}
    print(
        f"[inverse_ml_btc pilot] n_closed={fwd.get('n_closed')} pf={fwd.get('pf')} "
        f"open={bool(state.get('open_position'))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())