#!/usr/bin/env python3
"""Isolated forward paper pilot for EQUITY MeanReversionBB.

Resolver stats (2026-06-06): n=175 WON+LOST, WR=54.9%, PF=1.82.
Policy: EQUITY pair unblocked in BLOCKED_ASSET_STRATEGY_PAIRS; CRYPTO stays blocked.
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
LOG_PATH = PILOT_DIR / "equity_bb_paper_log.jsonl"
STATE_PATH = PILOT_DIR / "equity_bb_state.json"
STRATEGY_ID = "MeanReversionBB"

UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "JPM", "V", "UNH", "HD",
    "SPY", "QQQ", "IWM", "XLK", "XLF", "XLE",
]


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
        "last_run": None,
    }


def _save_state(state: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _append_log(row: dict) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def _ueps_long_symbols() -> set[str]:
    path = ROOT / "audit_dashboard" / "data" / "ueps_picks.json"
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        longs = data.get("long_picks") or data.get("picks") or []
        return {str(p.get("symbol", "")).upper() for p in longs if p.get("symbol")}
    except Exception:
        return set()


def _scan_signals() -> list[dict]:
    import pandas as pd
    import yfinance as yf

    from multi_asset.scanner import STOCKS, ETFS, mean_reversion_bollinger

    symbol_info = {**STOCKS, **ETFS}
    ueps = _ueps_long_symbols()
    out: list[dict] = []
    for sym in UNIVERSE:
        info = symbol_info.get(sym, {"name": sym, "cat": "stock"})
        if info.get("cat") not in ("stock", "etf"):
            continue
        try:
            df = yf.download(sym, period="6mo", progress=False, auto_adjust=True)
        except Exception:
            continue
        if df is None or df.empty or len(df) < 50:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df = df.rename(columns=str.title)
        if "Close" not in df.columns:
            continue
        for sig in mean_reversion_bollinger(df, sym, info):
            if sig.get("direction") != "LONG" and sig.get("signal_type") != "BUY":
                continue
            sig["asset_class"] = "EQUITY"
            sig["strategy"] = STRATEGY_ID
            sig["source_system"] = "equity_bb_pilot"
            sig["ueps_overlay"] = sym.upper() in ueps if ueps else None
            out.append(sig)
    out.sort(key=lambda s: float(s.get("confidence") or 0), reverse=True)
    return out[:3]


def run_one_shot() -> dict:
    today = _utc_today()
    state = _load_state()
    state["day_count"] = int(state.get("day_count", 0)) + 1
    signals = _scan_signals()
    state["last_signals"] = [
        {"symbol": s["symbol"], "confidence": s.get("confidence"), "ueps_overlay": s.get("ueps_overlay")}
        for s in signals
    ]
    state["last_run"] = _utc_iso()
    _save_state(state)
    for s in signals:
        _append_log({"date": today, "event": "SIGNAL", "strategy": STRATEGY_ID, **s})
    return {
        "date": today,
        "strategy": STRATEGY_ID,
        "signals": len(signals),
        "picks": state["last_signals"],
        "day_count": state["day_count"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--one-shot", action="store_true")
    args = ap.parse_args(argv)
    if not args.one_shot:
        ap.print_help()
        return 0
    print(json.dumps(run_one_shot(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
