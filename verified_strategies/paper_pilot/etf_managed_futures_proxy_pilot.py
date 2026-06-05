#!/usr/bin/env python3
"""Virtual forward book for ETF managed-futures proxy (DBMF + KMLM).

Commodity beta substitute while COMMODITY futures class stays frozen.
Signals from alpha_engine.etf_managed_futures_proxy (3m momentum > 0, VIX < 25).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT_DIR = Path(__file__).resolve().parent
LOG_PATH = PILOT_DIR / "etf_managed_futures_proxy_paper_log.jsonl"
STATE_PATH = PILOT_DIR / "etf_managed_futures_proxy_state.json"
STRATEGY_ID = "etf_managed_futures_proxy"
SYMBOLS = ("DBMF", "KMLM")


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_state(state: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _append_log(row: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def _last_close(symbol: str) -> float:
    import yfinance as yf

    px = yf.download(symbol, period="10d", progress=False, auto_adjust=True)
    if px is None or px.empty:
        return 0.0
    col = "Close" if "Close" in px.columns else px.columns[0]
    val = px[col].dropna().iloc[-1]
    return float(val.item() if hasattr(val, "item") else val)


def _target_long_symbols() -> dict[str, dict]:
    from alpha_engine.etf_managed_futures_proxy import generate_etf_managed_futures_picks

    out: dict[str, dict] = {}
    for pick in generate_etf_managed_futures_picks():
        sym = str(pick.get("symbol") or "").upper()
        if sym in SYMBOLS:
            out[sym] = pick
    return out


def run_one_shot() -> dict:
    today = _utc_today()
    state = _load_state()
    if "open_positions" not in state:
        state["open_positions"] = {}
    if "strategy_id" not in state:
        state["strategy_id"] = STRATEGY_ID
        state["started_at"] = datetime.now(timezone.utc).isoformat()
        state["n_closed"] = int(state.get("n_closed") or 0)

    targets = _target_long_symbols()
    open_pos: dict = state["open_positions"]
    closed_events: list[dict] = []

    for sym in SYMBOLS:
        held = open_pos.get(sym)
        want = sym in targets

        if held and held.get("status") == "OPEN" and not want:
            entry = float(held.get("entry_price") or 0.0)
            exit_px = _last_close(sym)
            pnl_pct = (exit_px / entry - 1.0) if entry else 0.0
            row = {
                "date": today,
                "event": "CLOSE",
                "strategy": STRATEGY_ID,
                "symbol": sym,
                "direction": "LONG",
                "entry_price": entry,
                "exit_price": exit_px,
                "pnl_pct": round(pnl_pct, 6),
                "outcome": "WIN" if pnl_pct > 0 else "LOSS",
                "reason": "flat_signal",
            }
            _append_log(row)
            closed_events.append(row)
            open_pos.pop(sym, None)
            state["n_closed"] = int(state.get("n_closed") or 0) + 1

        if want and (not held or held.get("status") != "OPEN"):
            pick = targets[sym]
            entry_px = float(
                (pick.get("extra") or {}).get("entry_price") or _last_close(sym)
            )
            open_pos[sym] = {
                "symbol": sym,
                "direction": "LONG",
                "entry_price": entry_px,
                "entry_date": today,
                "strategy": STRATEGY_ID,
                "status": "OPEN",
                "momentum_3m_pct": (pick.get("extra") or {}).get("momentum_3m_pct"),
                "vix": (pick.get("extra") or {}).get("vix"),
            }
            _append_log(
                {
                    "date": today,
                    "event": "OPEN",
                    "strategy": STRATEGY_ID,
                    "symbol": sym,
                    "direction": "LONG",
                    "entry_price": entry_px,
                    "reason": pick.get("reason"),
                }
            )

    state["open_positions"] = open_pos
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    state["target_symbols"] = sorted(targets.keys())
    _save_state(state)

    return {
        "date": today,
        "target_symbols": sorted(targets.keys()),
        "open_positions": open_pos,
        "n_closed": state.get("n_closed", 0),
        "closed_today": closed_events,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--one-shot", action="store_true", help="Run single daily tick")
    args = ap.parse_args(argv)
    if not args.one_shot:
        ap.print_help()
        return 0
    print(json.dumps(run_one_shot(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())