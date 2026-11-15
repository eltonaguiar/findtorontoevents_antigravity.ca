#!/usr/bin/env python3
"""Isolated forward paper pilot for BTC SMA200 + RSI2 Mean Reversion.

Strategy: LONG-only mean reversion within a bull trend.
Entry: RSI(2) < 10 AND Close > SMA200
Exit: RSI(2) > 60 OR trailing stop 5% OR 1-day time exit (24h)

This is the ONLY wealth-beating candidate identified across all agent audits
(1.94 vs 1.67 B&H final wealth in hypothesis harness). It does NOT yet pass
all 10 proof-protocol gates; this pilot collects the forward paper record.

Outputs:
  verified_strategies/paper_pilot/btc_sma200_rsi2_paper_log.jsonl
  verified_strategies/paper_pilot/btc_sma200_rsi2_positions.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT_DIR = Path(__file__).resolve().parent
LOG_PATH = PILOT_DIR / "btc_sma200_rsi2_paper_log.jsonl"
POSITIONS_PATH = PILOT_DIR / "btc_sma200_rsi2_positions.json"
STRATEGY_ID = "btc_sma200_rsi2_paper_pilot"
SYMBOL = "BTC-USD"

# Strategy parameters (match CRYPTO_AUDIT.md Experiment E1)
RSI_PERIOD = 2
SMA_PERIOD = 200
RSI_ENTRY_LONG = 10
RSI_EXIT_LONG = 60
TRAILING_STOP_PCT = 0.05
TIME_EXIT_BARS = 1  # 1 daily bar ~= 24h


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _compute_rsi(series: pd.Series, period: int = 2) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def _load_positions() -> dict:
    if POSITIONS_PATH.exists():
        try:
            return json.loads(POSITIONS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {
        "strategy_id": STRATEGY_ID,
        "symbol": SYMBOL,
        "started_at": _utc_iso(),
        "started_at_date": _utc_today(),
        "day_count": 0,
        "last_run": None,
        "open": None,
        "closed": [],
    }


def _save_positions(pos: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    POSITIONS_PATH.write_text(json.dumps(pos, indent=2, default=str), encoding="utf-8")


def _append_log(row: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def _fetch_data() -> pd.DataFrame | None:
    try:
        df = yf.download(SYMBOL, period="3y", interval="1d", progress=False, auto_adjust=True)
    except Exception as exc:
        return None
    if df is None or df.empty or len(df) < SMA_PERIOD + 10:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df.rename(columns=str.title)
    if "Close" not in df.columns:
        return None
    df = df.dropna(subset=["Close"])
    return df


def _latest_price(df: pd.DataFrame) -> float | None:
    try:
        v = df["Close"].iloc[-1]
        if hasattr(v, "item"):
            v = v.item()
        return float(v)
    except Exception:
        return None


def _stats(pos: dict) -> dict:
    closed = pos.get("closed", [])
    pnls = [float(c.get("pnl_pct", 0.0)) for c in closed]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gw = sum(wins)
    gl = abs(sum(losses))
    return {
        "n_closed": len(pnls),
        "win_rate": round(len(wins) / len(pnls), 4) if pnls else 0.0,
        "profit_factor": round(gw / gl, 4) if gl > 0 else (float("inf") if gw > 0 else 0.0),
        "avg_pnl_pct": round(sum(pnls) / len(pnls), 4) if pnls else 0.0,
        "open_count": 1 if pos.get("open") else 0,
    }


def run_one_shot() -> dict:
    today = _utc_today()
    pos = _load_positions()
    pos["day_count"] = int(pos.get("day_count", 0)) + 1
    pos.setdefault("open", None)
    pos.setdefault("closed", [])

    df = _fetch_data()
    if df is None or df.empty:
        pos["last_run"] = _utc_iso()
        pos["last_error"] = "no price data (yfinance unreachable)"
        _save_positions(pos)
        return {"date": today, "strategy": STRATEGY_ID, "error": "no price data", "day_count": pos["day_count"]}

    close = df["Close"]
    sma200 = close.rolling(window=SMA_PERIOD).mean()
    rsi2 = _compute_rsi(close, period=RSI_PERIOD)

    # Align lengths — drop NaNs at the front
    valid = close.notna() & sma200.notna() & rsi2.notna()
    close = close[valid]
    sma200 = sma200[valid]
    rsi2 = rsi2[valid]

    if len(close) < 2:
        pos["last_run"] = _utc_iso()
        pos["last_error"] = "insufficient valid bars"
        _save_positions(pos)
        return {"date": today, "strategy": STRATEGY_ID, "error": "insufficient bars", "day_count": pos["day_count"]}

    latest_close = float(close.iloc[-1])
    latest_sma200 = float(sma200.iloc[-1])
    latest_rsi2 = float(rsi2.iloc[-1])
    prev_rsi2 = float(rsi2.iloc[-2])

    # 1) Manage open position
    opened = []
    closed_today = []
    if pos["open"] is not None:
        open_rec = pos["open"]
        entry_price = float(open_rec["entry_price"])
        highest_close = max(float(open_rec.get("highest_close", entry_price)), latest_close)
        open_rec["highest_close"] = highest_close
        bars_held = int(open_rec.get("bars_held", 0)) + 1
        open_rec["bars_held"] = bars_held

        # Trailing stop: 5% below highest close since entry
        trail_price = highest_close * (1.0 - TRAILING_STOP_PCT)
        # Time exit: 1 bar (24h)
        time_exit = bars_held >= TIME_EXIT_BARS
        # RSI exit: RSI(2) > 60
        rsi_exit = latest_rsi2 > RSI_EXIT_LONG
        # Hard stop: price below trailing stop
        stop_exit = latest_close < trail_price

        exit_reason = None
        if stop_exit:
            exit_reason = "trailing_stop"
        elif time_exit:
            exit_reason = "time_exit"
        elif rsi_exit:
            exit_reason = "rsi_exit"

        if exit_reason:
            pnl_pct = round((latest_close / entry_price - 1.0) * 100.0, 4)
            rec = {
                "symbol": SYMBOL,
                "entry_price": entry_price,
                "exit_price": round(latest_close, 4),
                "entry_date": open_rec.get("entry_date"),
                "exit_date": today,
                "pnl_pct": pnl_pct,
                "reason": exit_reason,
                "bars_held": bars_held,
                "highest_close": round(highest_close, 4),
                "exit_rsi2": round(latest_rsi2, 4),
            }
            pos["closed"].append(rec)
            closed_today.append(rec)
            _append_log({"date": today, "event": "CLOSE", "strategy": STRATEGY_ID, **rec})
            pos["open"] = None
        else:
            # Update open position with latest metrics
            open_rec["current_price"] = round(latest_close, 4)
            open_rec["current_rsi2"] = round(latest_rsi2, 4)
            open_rec["current_sma200"] = round(latest_sma200, 4)
            open_rec["unrealized_pnl_pct"] = round((latest_close / entry_price - 1.0) * 100.0, 4)

    # 2) Evaluate entry signal if no open position
    entry_signal = False
    if pos["open"] is None:
        # Entry: RSI(2) < 10 AND close > SMA200
        # We use the latest bar's values (paper trade at close)
        if latest_rsi2 < RSI_ENTRY_LONG and latest_close > latest_sma200:
            entry_signal = True
            pos["open"] = {
                "symbol": SYMBOL,
                "direction": "LONG",
                "entry_price": round(latest_close, 4),
                "entry_date": today,
                "entry_rsi2": round(latest_rsi2, 4),
                "entry_sma200": round(latest_sma200, 4),
                "highest_close": round(latest_close, 4),
                "bars_held": 0,
                "status": "OPEN",
            }
            opened.append(SYMBOL)
            _append_log({
                "date": today,
                "event": "OPEN",
                "strategy": STRATEGY_ID,
                "symbol": SYMBOL,
                "entry_price": round(latest_close, 4),
                "entry_rsi2": round(latest_rsi2, 4),
                "entry_sma200": round(latest_sma200, 4),
            })

    st = _stats(pos)
    pos.update(st)
    pos["last_run"] = _utc_iso()
    pos["last_close"] = round(latest_close, 4)
    pos["last_sma200"] = round(latest_sma200, 4)
    pos["last_rsi2"] = round(latest_rsi2, 4)
    _save_positions(pos)

    return {
        "date": today,
        "strategy": STRATEGY_ID,
        "day_count": pos["day_count"],
        "entry_signal": entry_signal,
        "opened": opened,
        "closed": closed_today,
        "open_position": pos["open"] is not None,
        "metrics": {
            "close": round(latest_close, 4),
            "sma200": round(latest_sma200, 4),
            "rsi2": round(latest_rsi2, 4),
        },
        **st,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--one-shot", action="store_true")
    args = ap.parse_args(argv)
    if not args.one_shot:
        ap.print_help()
        return 0
    print(json.dumps(run_one_shot(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
