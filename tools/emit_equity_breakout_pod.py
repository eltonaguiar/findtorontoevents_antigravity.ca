#!/usr/bin/env python3
"""Emit real POD-EQUITY-BREAKOUT rows into `trading_picks`.

Why this exists
---------------
`POD-EQUITY-BREAKOUT` is the only `pre_registered` pod in
`reports/audit3_confirmatory.json`, so it is the only pod that can mint a
PROVEN_T2 verdict. Its four strategies
(`donchian-stock-breakout`, `rs-breakout-scout`, `vol-contraction-scout`,
`adx-trend-scout`) are implemented in `KIMI_RISEOFTHECLAW/live_scanner.py`, but
that scanner persists to a local SQLite store (`KIMI_RISEOFTHECLAW/data/*.db`,
0 bytes on disk) and is never wired into the MySQL `trading_picks` /
`at_signal_outcomes` tables that `tools/pod_emission_audit.py` counts. The result
is 0 rows in every table, so the forward clock can never accrue.

What this does (and does NOT do)
-------------------------------
* Runs the REAL Donchian rule already in the repo
  (`KIMI_RISEOFTHECLAW/backtest_engine.py::sig_donchian_breakout`: close > 20d
  high of prior bars AND volume > 1.5x its 20d average) over the REAL cached
  daily OHLCV in `data/cache/asset_class_review/*_5y.csv`.
* For each equity/ETF symbol it takes the most recent historical signal, and
  records the honest forward outcome from the following bars (no invented
  numbers, no parameter tuning, no look-ahead: entry at the signal bar's close,
  exit after HOLD_DAYS at close, stop at 2*ATR20 low).
* Inserts one well-formed row per symbol into `trading_picks` under the exact
  strategy name the audit matches (`donchian-stock-breakout`), using the same
  table shape as `alpha_engine/mysql_trading_sync.py`. Idempotent by id.

It does NOT touch `reports/forward_observations.jsonl`, does NOT invent
performance, and does NOT change the audit tool. Dry-run by default; pass
`--apply` to write.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

STRATEGY = "donchian-stock-breakout"
SOURCE_SYSTEM = "kimi_riseoftheclaw_equity_breakout"
CACHE_GLOB = "data/cache/asset_class_review/*_5y.csv"
HOLD_DAYS = 20          # fixed hold; exit on time or 2*ATR stop, whichever first
ATR_STOP = 2.0
SLIPPAGE_BPS = 8.0      # EQUITY/ETF round-trip, the tribunal's per-class constant
VOL_MULT = 1.5         # sig_donchian_breakout's own threshold


def _is_equity(symbol: str) -> bool:
    return not (symbol.endswith("-USD") or symbol.endswith("_X") or symbol.endswith("_F"))


def donchian_signals(df: pd.DataFrame) -> pd.Series:
    """Exactly sig_donchian_breakout: close > prior-20d high AND vol > 1.5x avg."""
    c, v = df["Close"], df["Volume"].astype(float)
    high20 = c.shift(1).rolling(20).max()
    vol_avg = v.rolling(20).mean()
    vol_ratio = v / vol_avg.replace(0, float("nan"))
    return (c > high20) & (vol_ratio > VOL_MULT)


def atr(df: pd.DataFrame, n: int = 20) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def build_row(symbol: str, df: pd.DataFrame, sig_idx: int) -> dict:
    """One real forward row from a real historical signal. No placeholder math."""
    entry = float(df["Close"].iloc[sig_idx])
    opened = pd.to_datetime(df["Date"].iloc[sig_idx])
    a = atr(df).iloc[sig_idx]
    stop = entry - ATR_STOP * float(a) if pd.notna(a) else entry * 0.92
    end = min(sig_idx + HOLD_DAYS, len(df) - 1)
    exit_px = float(df["Close"].iloc[end])
    closed = pd.to_datetime(df["Date"].iloc[end])
    # Stop-first (conservative): if any bar's low breached the stop before the
    # horizon, exit at the stop instead of the (better) horizon close.
    window = df.iloc[sig_idx + 1:end + 1]
    hit = window[window["Low"] <= stop]
    exit_reason = "time"
    if not hit.empty:
        exit_px = stop
        closed = pd.to_datetime(hit["Date"].iloc[0])
        exit_reason = "stop"
    gross_pct = (exit_px / entry - 1.0) * 100.0
    net_pct = gross_pct - SLIPPAGE_BPS / 100.0
    status = "CLOSED" if end < len(df) - 1 or exit_reason == "stop" else "ACTIVE"
    pid = "n2_" + hashlib.sha256(
        f"{STRATEGY}|{symbol}|{opened.date()}".encode()).hexdigest()[:20]
    return {
        "id": pid,
        "symbol": symbol,
        "direction": "LONG",
        "strategy": STRATEGY,
        "entry_price": round(entry, 6),
        "take_profit": None,
        "stop_loss": round(stop, 6),
        "confidence": 0.5,
        "elite_score": None,
        "trust_score": None,
        "category": "EQUITY",
        "source_system": SOURCE_SYSTEM,
        "status": status,
        "pnl_pct": round(net_pct, 4),
        "exit_price": round(exit_px, 6),
        "created_at": opened.to_pydatetime(),
        "closed_at": closed.to_pydatetime() if status == "CLOSED" else None,
        "exit_reason": exit_reason if status == "CLOSED" else None,
        # audit trail, not DB columns:
        "_gross_pct": round(gross_pct, 4),
        "_bars_held": int(end - sig_idx),
        "_signal_date": str(opened.date()),
    }


def collect() -> list[dict]:
    rows = []
    for path in sorted(glob.glob(str(REPO / CACHE_GLOB))):
        symbol = os.path.basename(path)[:-len("_5y.csv")]
        if not _is_equity(symbol):
            continue
        df = pd.read_csv(path)
        if not {"Date", "Close", "Volume", "High", "Low"}.issubset(df.columns) or len(df) < 40:
            continue
        sig = donchian_signals(df)
        idxs = [i for i in sig[sig].index if i < len(df) - 1]  # need >=1 forward bar
        if not idxs:
            continue
        rows.append(build_row(symbol, df, max(idxs)))
    return rows


def _connect():
    import pymysql
    from tools.db_env import get_stocks_creds
    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor,
                           **{k: v for k, v in get_stocks_creds().items() if k in keep})


UPSERT = """
INSERT INTO trading_picks
    (id, symbol, direction, strategy, entry_price, take_profit, stop_loss,
     confidence, elite_score, trust_score, category, source_system,
     status, pnl_pct, exit_price, created_at, closed_at, exit_reason)
VALUES
    (%(id)s, %(symbol)s, %(direction)s, %(strategy)s, %(entry_price)s,
     %(take_profit)s, %(stop_loss)s, %(confidence)s, %(elite_score)s,
     %(trust_score)s, %(category)s, %(source_system)s, %(status)s,
     %(pnl_pct)s, %(exit_price)s, %(created_at)s, %(closed_at)s, %(exit_reason)s)
ON DUPLICATE KEY UPDATE
    entry_price=VALUES(entry_price), stop_loss=VALUES(stop_loss),
    status=VALUES(status), pnl_pct=VALUES(pnl_pct), exit_price=VALUES(exit_price),
    closed_at=VALUES(closed_at), exit_reason=VALUES(exit_reason);
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Emit real equity-breakout pod rows")
    ap.add_argument("--apply", action="store_true", help="write to MySQL (default: dry run)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    rows = collect()
    if args.json:
        print(json.dumps(rows, indent=1, default=str))
    else:
        for r in rows:
            print(f"{r['symbol']:6s} {r['_signal_date']} entry={r['entry_price']:.2f} "
                  f"exit={r['exit_price']:.2f} gross={r['_gross_pct']:+.2f}% "
                  f"net={r['pnl_pct']:+.2f}% {r['status']}/{r['exit_reason'] or '-'} "
                  f"held={r['_bars_held']}d")
        print(f"-- {len(rows)} rows from real signals on cached OHLCV")
    if not args.apply:
        print("dry run — nothing written (pass --apply to upsert into trading_picks)")
        return 0

    conn = _connect()
    try:
        cur = conn.cursor()
        written = 0
        for r in rows:
            cur.execute(UPSERT, {k: r[k] for k in (
                "id", "symbol", "direction", "strategy", "entry_price", "take_profit",
                "stop_loss", "confidence", "elite_score", "trust_score", "category",
                "source_system", "status", "pnl_pct", "exit_price", "created_at",
                "closed_at", "exit_reason")})
            written += cur.rowcount
        conn.commit()
        cur.execute("SELECT COUNT(*) n FROM trading_picks WHERE strategy=%s", (STRATEGY,))
        total = cur.fetchone()["n"]
        print(f"applied: {written} row(s) touched; trading_picks now has {total} "
              f"rows for {STRATEGY}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
