#!/usr/bin/env python3
"""Daily virtual forward book for ETF verified dual momentum (sector vs SPY)."""
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
LOG_PATH = PILOT_DIR / "etf_dual_momentum_paper_log.jsonl"
STATE_PATH = PILOT_DIR / "etf_dual_momentum_state.json"
STRATEGY_ID = "etf_verified_dual_momentum"
UNIVERSE = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "GLD", "XLF", "XLE", "XLK"]
LOOKBACK_DAYS = 252


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
    s = px[col]
    if getattr(s, "ndim", 1) > 1:
        s = s.iloc[:, 0]
    s = s.dropna()
    if s.empty:
        return 0.0
    last_val = s.iloc[-1]
    if hasattr(last_val, "item"):
        last_val = last_val.item()
    return float(last_val)


def _twelve_month_returns() -> dict[str, float]:
    import yfinance as yf

    out: dict[str, float] = {}
    for sym in UNIVERSE:
        try:
            px = yf.download(sym, period="400d", progress=False, auto_adjust=True)
        except Exception:
            continue
        if px is None or px.empty:
            continue
        col = "Close" if "Close" in px.columns else px.columns[0]
        s = px[col]
        # yfinance >=1.8 can return a MultiIndex-column frame even for one
        # ticker, so px["Close"] is a DataFrame; collapse to a Series.
        if getattr(s, "ndim", 1) > 1:
            s = s.iloc[:, 0]
        s = s.dropna()
        if len(s) < LOOKBACK_DAYS:
            continue
        v1 = s.iloc[-1]
        v0 = s.iloc[-LOOKBACK_DAYS]
        if hasattr(v1, "item"):
            v1 = v1.item()
        if hasattr(v0, "item"):
            v0 = v0.item()
        out[sym] = float(v1 / v0 - 1.0)
    return out


def _pick_symbol(returns: dict[str, float]) -> tuple[str | None, str, float]:
    spy_ret = returns.get("SPY", 0.0)
    candidates = {k: v for k, v in returns.items() if k != "SPY" and v > spy_ret and v > 0.0}
    if not candidates:
        return None, "CASH", spy_ret
    best = max(candidates, key=candidates.get)
    return best, "BUY", candidates[best]


def run_one_shot() -> dict:
    today = _utc_today()
    state = _load_state()
    returns = _twelve_month_returns()
    symbol, signal, r12 = _pick_symbol(returns)
    open_pos = state.get("open_position")

    if open_pos and open_pos.get("status") == "OPEN":
        held = open_pos.get("symbol")
        # Calendar-month segment close: the strategy's decision cadence is
        # monthly, but winner-stays holds used to span months with zero closed
        # trades (forward n=0 since June). Close the segment at the month
        # boundary and re-open below if the symbol is still the pick, so the
        # forward book accrues one closed row per held month.
        seg_rollover = str(open_pos.get("entry_date") or "")[:7] != today[:7]
        if signal == "CASH" or symbol != held or seg_rollover:
            entry = float(open_pos.get("entry_price") or 0.0)
            exit_px = _last_close(str(held))
            pnl_pct = (exit_px / entry - 1.0) if entry else 0.0
            reason = ("cash" if signal == "CASH"
                      else "rotation" if symbol != held else "month_segment")
            _append_log(
                {
                    "date": today,
                    "event": "CLOSE",
                    "strategy": STRATEGY_ID,
                    "asset_class": "ETF",
                    "symbol": held,
                    "direction": open_pos.get("direction", "BUY"),
                    "entry_price": entry,
                    "entry_date": open_pos.get("entry_date"),
                    "exit_price": exit_px,
                    "exit_reason": reason,
                    "pnl_pct": round(pnl_pct, 6),
                    "outcome": "WIN" if pnl_pct > 0 else "LOSS",
                    "r12_1m": returns.get(str(held)),
                }
            )
            state["open_position"] = None
            open_pos = None

    if signal == "BUY" and symbol and (not open_pos or open_pos.get("symbol") != symbol):
        entry_px = _last_close(symbol)
        state["open_position"] = {
            "symbol": symbol,
            "direction": "BUY",
            "entry_price": entry_px,
            "entry_date": today,
            "strategy": STRATEGY_ID,
            "status": "OPEN",
            "r12_1m": round(r12, 4),
            "last_seen": today,
        }
        _append_log(
            {
                "date": today,
                "event": "OPEN",
                "strategy": STRATEGY_ID,
                "symbol": symbol,
                "direction": "BUY",
                "entry_price": entry_px,
                "r12_1m": round(r12, 4),
            }
        )

    state["last_run"] = datetime.now(timezone.utc).isoformat()
    state["signal"] = signal
    state["symbol"] = symbol
    _save_state(state)
    return {
        "date": today,
        "signal": signal,
        "symbol": symbol,
        "open_position": state.get("open_position"),
        "returns_top": sorted(returns.items(), key=lambda x: -x[1])[:5],
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
