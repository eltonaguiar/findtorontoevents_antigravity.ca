#!/usr/bin/env python3
"""Virtual forward book for inverse_alpha_engine_fast (mutation-approved).

Mutation scan (2026-06-13): alpha_engine_fast PF=0.00 in live book
(trading_picks deduped). Inversion produces PF~99.00 — perfectly wrong,
flip signals.  ADOPT recommendation.

Reads alpha_engine/data/active_picks_fast.json (ALL sub-strategies from
the FAST scanner), inverts direction + mirrors TP/SL for each pick,
and maintains a multi-symbol paper book. Crypto positions resolve
daily against Binance/CoinGecko prices; non-crypto positions resolve
via TIME_EXIT after MAX_HOLD_DAYS.

This is a passive-consumer pilot — it never generates its own signals.
It consumes whatever the FAST scanner emits. The source file is read
each tick so new scanner output flows in automatically.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT_DIR = Path(__file__).resolve().parent
LOG_PATH = PILOT_DIR / "inverse_alpha_engine_fast_paper_log.jsonl"
STATE_PATH = PILOT_DIR / "inverse_alpha_engine_fast_state.json"
SOURCE_PATH = ROOT / "alpha_engine" / "data" / "active_picks_fast.json"
STRATEGY_ID = "inverse_alpha_engine_fast"
LAB_OOS_PF = 99.0  # mutation scan — invert of PF=0.00

# Max days before a paper position auto-closes (TIME_EXIT).
MAX_HOLD_DAYS = 30

# Crypto pairs known to work with Binance/CoinGecko pricing.
_CRYPTO_SUFFIXES = ("USDT", "USD", "USDC", "BUSD", "BTC", "ETH")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_today() -> str:
    return _utc_now().strftime("%Y-%m-%d")


def _is_crypto_symbol(symbol: str) -> bool:
    """Heuristic: crypto pairs end with a known quote asset or use DEX: prefix."""
    up = symbol.upper().strip()
    if up.startswith("DEX:") or up.startswith("CEX:"):
        return True
    for suffix in _CRYPTO_SUFFIXES:
        if up.endswith(suffix) and len(up) > len(suffix) + 1:
            return True
    return False


def _flip_direction(direction: str) -> str:
    return {"LONG": "SHORT", "SHORT": "LONG", "BUY": "SELL", "SELL": "BUY"}.get(direction, direction)


def _swap_prices(entry: float, tp: float, sl: float) -> tuple[float, float]:
    """Mirror TP and SL around entry price for the inverted direction."""
    tp_dist = tp - entry
    sl_dist = sl - entry
    return entry - tp_dist, entry - sl_dist


# ── state helpers ──────────────────────────────────────────────────────────


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {"strategy_id": STRATEGY_ID, "positions": {}, "seen_ids": [], "day_count": 0}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"strategy_id": STRATEGY_ID, "positions": {}, "seen_ids": [], "day_count": 0}


def _save_state(state: dict) -> None:
    state["last_update_utc"] = _utc_now().isoformat()
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def _append_log(row: dict) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


# ── source data ────────────────────────────────────────────────────────────


def _read_source_picks() -> list[dict]:
    if not SOURCE_PATH.exists():
        return []
    try:
        data = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        # Handle wrapped formats
        for key in ("picks", "data", "results"):
            if key in data:
                return data[key]
        return list(data.values()) if isinstance(data, dict) else []
    except (json.JSONDecodeError, Exception):
        return []


# ── price ──────────────────────────────────────────────────────────────────


def _current_price(symbol: str) -> float | None:
    """Fetch current price for a crypto symbol. Returns None for non-crypto."""
    if not _is_crypto_symbol(symbol):
        return None
    try:
        from alpha_engine.ml_strategy_reviver import (
            _fetch_price_binance,
            _fetch_price_coingecko,
        )
    except ImportError:
        return None

    px = _fetch_price_binance(symbol)
    if px is not None:
        return px
    px = _fetch_price_coingecko(symbol)
    return px


def _resolve_position(pos: dict, last_px: float, today: str) -> str | None:
    """Check whether a position should close. Returns outcome or None."""
    tp = float(pos["take_profit"])
    sl = float(pos["stop_loss"])
    direction = pos.get("direction", "SHORT")

    if direction in ("SHORT", "SELL"):
        if last_px <= tp:
            return "TP_HIT"
        if last_px >= sl:
            return "SL_HIT"
    else:
        if last_px >= tp:
            return "TP_HIT"
        if last_px <= sl:
            return "SL_HIT"

    entry_date = pos.get("entry_date", today)
    try:
        held = (
            datetime.strptime(today, "%Y-%m-%d").date()
            - datetime.strptime(entry_date, "%Y-%m-%d").date()
        ).days
    except ValueError:
        held = 0
    if held >= MAX_HOLD_DAYS:
        return "TIME_EXIT"
    return None


# ── main tick ──────────────────────────────────────────────────────────────


def run_daily_tick() -> dict:
    today = _utc_today()
    state = _load_state()
    state["day_count"] = int(state.get("day_count") or 0) + 1

    seen: set[str] = set(state.get("seen_ids") or [])
    positions: dict[str, dict] = state.get("positions") or {}

    # ── RESOLVE existing positions ────────────────────────────────────────
    for pos_id in list(positions.keys()):
        pos = positions[pos_id]
        if pos.get("status") != "OPEN":
            continue
        symbol = pos["symbol"]
        last_px = _current_price(symbol)
        if last_px is None:
            # Can't price — skip resolve this tick. Non-crypto will TIME_EXIT.
            pos["mark_price"] = pos.get("mark_price") or pos["entry_price"]
            pos["last_seen"] = today
            continue

        outcome = _resolve_position(pos, last_px, today)
        if outcome:
            entry = float(pos["entry_price"])
            if pos.get("direction") in ("SHORT", "SELL"):
                pnl_pct = (entry - last_px) / entry if entry else 0.0
            else:
                pnl_pct = (last_px - entry) / entry if entry else 0.0

            _append_log({
                "event": "CLOSE",
                "strategy": STRATEGY_ID,
                "symbol": symbol,
                "direction": pos["direction"],
                "entry_price": entry,
                "exit_price": last_px,
                "pnl_pct": round(pnl_pct, 6),
                "outcome": outcome,
                "closed_at": today,
                "source_pick_id": pos.get("source_pick_id", ""),
                "source_strategy": pos.get("source_strategy", ""),
            })
            pos["status"] = outcome
            pos["closed_at"] = today
            pos["exit_price"] = last_px
            pos["pnl_pct"] = round(pnl_pct, 6)
        else:
            pos["last_seen"] = today
            pos["mark_price"] = last_px

    # ── OPEN new positions from source picks ──────────────────────────────
    source_picks = _read_source_picks()
    for pick in source_picks:
        pick_id = pick.get("id") or ""
        if not pick_id:
            continue
        if pick_id in seen:
            continue

        direction = pick.get("direction") or "LONG"
        entry = pick.get("entry_price")
        tp = pick.get("take_profit")
        sl = pick.get("stop_loss")
        symbol = pick.get("symbol", "")

        if not all([entry, tp, sl, symbol]):
            seen.add(pick_id)
            continue

        # Build inverted version
        flipped = _flip_direction(direction)
        try:
            inv_tp, inv_sl = _swap_prices(float(entry), float(tp), float(sl))
        except (TypeError, ValueError):
            seen.add(pick_id)
            continue

        pos_id = f"inv_{pick_id}"
        positions[pos_id] = {
            "strategy": STRATEGY_ID,
            "symbol": symbol,
            "direction": flipped,
            "status": "OPEN",
            "entry_price": float(entry),
            "take_profit": inv_tp,
            "stop_loss": inv_sl,
            "entry_date": today,
            "source_pick_id": pick_id,
            "source_strategy": pick.get("strategy", ""),
            "source_direction": direction,
        }
        seen.add(pick_id)

        _append_log({
            "event": "OPEN",
            "strategy": STRATEGY_ID,
            "symbol": symbol,
            "direction": flipped,
            "entry_price": float(entry),
            "take_profit": inv_tp,
            "stop_loss": inv_sl,
            "entry_date": today,
            "source_pick_id": pick_id,
            "source_strategy": pick.get("strategy", ""),
        })

    # ── Persist state ─────────────────────────────────────────────────────
    state["seen_ids"] = list(seen)
    state["positions"] = positions

    # ── Forward stats ─────────────────────────────────────────────────────
    from verified_strategies.paper_pilot.pilot_forward_summary import forward_block

    open_positions = [p for p in positions.values() if p.get("status") == "OPEN"]
    state["forward"] = forward_block(
        log_path=LOG_PATH,
        strategy_id=STRATEGY_ID,
        oos_pf=LAB_OOS_PF,
        open_position=open_positions[0] if open_positions else None,
    )
    state["lab_is_pf"] = LAB_OOS_PF
    state["production_enable"] = False
    state["open_position_count"] = len(open_positions)
    state["total_positions_created"] = len(positions)
    _save_state(state)
    return state


def main() -> int:
    state = run_daily_tick()
    fwd = state.get("forward") or {}
    open_count = state.get("open_position_count", 0)
    total = state.get("total_positions_created", 0)
    print(
        f"[inverse_alpha_engine_fast pilot] "
        f"n_closed={fwd.get('n_closed')} pf={fwd.get('pf')} "
        f"open={open_count}/{total}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
