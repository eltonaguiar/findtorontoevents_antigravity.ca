#!/usr/bin/env python3
"""Virtual forward book for B_flip_PriceRocMeanReversion (bootstrap-approved).

PR #482: n=157 IS PF~35.9, pf_lo_95=21.2 — forward-test only; no production scanner flag.
Inverts PriceRoc mean-reversion entries (SHORT when base strategy would LONG).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT_DIR = Path(__file__).resolve().parent
LOG_PATH = PILOT_DIR / "b_flip_price_roc_paper_log.jsonl"
STATE_PATH = PILOT_DIR / "b_flip_price_roc_state.json"
STRATEGY_ID = "B_flip_PriceRocMeanReversion"
UNIVERSE = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "FETUSDT",
]
INTERVAL = "1h"
TP_ATR = 2.0
SL_ATR = 1.5
MAX_HOLD_DAYS = 15
LAB_OOS_PF = 35.91


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {"strategy_id": STRATEGY_ID, "open_position": None, "day_count": 0}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"strategy_id": STRATEGY_ID, "open_position": None, "day_count": 0}


def _save_state(state: dict) -> None:
    state["last_update_utc"] = datetime.now(timezone.utc).isoformat()
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _append_log(row: dict) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def _klines_df(symbol: str, interval: str, limit: int = 260) -> pd.DataFrame | None:
    from alpha_engine.ml_strategy_reviver import fetch_klines

    rows = fetch_klines(symbol, interval, limit)
    if not rows:
        return None
    df = pd.DataFrame(rows)
    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"])
    if df.empty or len(df) < 220:
        return None
    return df


def _indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["roc_5"] = out["close"].pct_change(periods=5)
    out["ema_20"] = out["close"].ewm(span=20, adjust=False).mean()
    high_low = out["high"] - out["low"]
    high_close = np.abs(out["high"] - out["close"].shift())
    low_close = np.abs(out["low"] - out["close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    out["atr_14"] = tr.rolling(window=14).mean()
    out["median_vol_50"] = out["volume"].rolling(window=50).median()
    return out


def _short_entry_on_last_bar(df: pd.DataFrame, symbol: str) -> dict | None:
    df = _indicators(df)
    row = df.iloc[-2]
    if any(pd.isna(row[c]) for c in ("roc_5", "ema_20", "atr_14", "median_vol_50")):
        return None
    if not (
        row["roc_5"] < -0.02
        and row["close"] < row["ema_20"]
        and row["volume"] > 1.5 * row["median_vol_50"]
    ):
        return None
    entry = float(row["close"])
    atr = float(row["atr_14"])
    return {
        "symbol": SYMBOL,
        "direction": "SELL",
        "entry_price": entry,
        "take_profit": entry - atr * TP_ATR,
        "stop_loss": entry + atr * SL_ATR,
        "atr": atr,
    }


def _resolve_short(open_pos: dict, last_px: float, today: str) -> str | None:
    tp = float(open_pos["take_profit"])
    sl = float(open_pos["stop_loss"])
    if last_px <= tp:
        return "TP_HIT"
    if last_px >= sl:
        return "SL_HIT"
    entry_date = open_pos.get("entry_date", today)
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


def run_daily_tick() -> dict:
    today = _utc_today()
    state = _load_state()
    state["day_count"] = int(state.get("day_count") or 0) + 1

    df = _klines_df(SYMBOL, INTERVAL)
    if df is None:
        state["note"] = "klines_unavailable"
        _save_state(state)
        return state

    last_px = float(df["close"].iloc[-1])
    open_pos = state.get("open_position")

    if open_pos and open_pos.get("status") == "OPEN":
        outcome = _resolve_short(open_pos, last_px, today)
        if outcome:
            entry = float(open_pos["entry_price"])
            pnl_pct = (entry - last_px) / entry if entry else 0.0
            _append_log(
                {
                    "event": "CLOSE",
                    "strategy": STRATEGY_ID,
                    "symbol": SYMBOL,
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
        sig = _short_entry_on_last_bar(df)
        if sig:
            state["open_position"] = {
                **sig,
                "strategy": STRATEGY_ID,
                "status": "OPEN",
                "entry_date": today,
            }
            _append_log({"event": "OPEN", "strategy": STRATEGY_ID, **sig, "opened_at": today})

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
        f"[b_flip pilot] n_closed={fwd.get('n_closed')} pf={fwd.get('pf')} "
        f"open={bool(state.get('open_position'))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())