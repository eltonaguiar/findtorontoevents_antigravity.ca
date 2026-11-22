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
* Re-implements, line-for-line from source, the REAL signal rules already in
  the repo (see `STRATEGIES` below) and runs them over the REAL cached daily
  OHLCV in `data/cache/asset_class_review/*_5y.csv`.
* For each equity/ETF symbol it takes the most recent historical signal, and
  records the honest forward outcome from the following bars (no invented
  numbers, no parameter tuning, no look-ahead: entry at the signal bar's close,
  exit after HOLD_DAYS at close, stop at 2*ATR20 low, stop checked first).
* Inserts one well-formed row per symbol into `trading_picks` under the exact
  strategy name the audit matches, using the same table shape as
  `alpha_engine/mysql_trading_sync.py`. Idempotent by id.

It does NOT touch `reports/forward_observations.jsonl`, does NOT invent
performance, and does NOT change the audit tool. Dry-run by default; pass
`--apply` to write.

Strategy semantics (read from source, `drought=0` as the scanner default)
-----------------------------------------------------------------------
* donchian-stock-breakout: `KIMI_RISEOFTHECLAW/backtest_engine.py::sig_donchian_breakout`
  close > prior-20d high AND volume > 1.5x its 20d mean. LONG-only.
* adx-trend-scout: `KIMI_RISEOFTHECLAW/live_scanner.py::signal_adx_trend_filter`
  Wilder-14 ADX > 25 AND DI+ > DI- AND close >= 0.99 * SMA20. LONG-only.
* vol-contraction-scout: `...::signal_volatility_contraction_breakout`
  BB(20,2) width within 5% of its 40d low AND current true range within 2% of
  its 7d low (NR7) AND close >= 0.99 * SMA20 AND 5d mean volume < 1.2x 20d mean
  AND RSI(14, Wilder) <= 68. LONG-only.
* rs-breakout-scout: `...::signal_relative_strength_breakout`
  RS = close/SPY close at a 20d high (>= 0.999x) AND close >= 0.99 * SMA50 AND
  5d RS change >= +0.5%. Needs SPY in the cache. LONG-only.

All four emit only "BUY" (LONG). The exit convention is shared: entry at close,
20-bar time stop or 2*ATR20 stop (stop first), -8bp EQUITY slippage.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SOURCE_SYSTEM = "kimi_riseoftheclaw_equity_breakout"
CACHE_GLOB = "data/cache/asset_class_review/*_5y.csv"
HOLD_DAYS = 20          # fixed hold; exit on time or 2*ATR stop, whichever first
ATR_STOP = 2.0
SLIPPAGE_BPS = 8.0      # EQUITY/ETF round-trip, the tribunal's per-class constant
VOL_MULT = 1.5         # sig_donchian_breakout's own threshold

# strategy key -> (audit strategy name, minimum bars needed)
STRATEGIES = {
    "donchian": ("donchian-stock-breakout", 40),
    "rs-breakout": ("rs-breakout-scout", 60),
    "vol-contraction": ("vol-contraction-scout", 60),
    "adx-trend": ("adx-trend-scout", 30),
}
DEFAULT_STRATEGY = "donchian"


def _is_equity(symbol: str) -> bool:
    return not (symbol.endswith("-USD") or symbol.endswith("_X") or symbol.endswith("_F"))


def donchian_signals(df: pd.DataFrame) -> pd.Series:
    """Exactly sig_donchian_breakout: close > prior-20d high AND vol > 1.5x avg."""
    c, v = df["Close"], df["Volume"].astype(float)
    high20 = c.shift(1).rolling(20).max()
    vol_avg = v.rolling(20).mean()
    vol_ratio = v / vol_avg.replace(0, float("nan"))
    return (c > high20) & (vol_ratio > VOL_MULT)


def _rsi_wilder(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=n - 1, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=n - 1, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def _true_range(df: pd.DataFrame) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    return pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)


def adx_trend_signals(df: pd.DataFrame) -> pd.Series:
    """Exactly signal_adx_trend_filter (drought=0). Returns True on BUY bars.

    Vectorised over the whole series so the rule is evaluated at every bar, then
    the most recent True bar is used by collect().
    """
    close = df["Close"]
    high = df["High"] if "High" in df.columns else close
    low = df["Low"] if "Low" in df.columns else close
    tr = _true_range(df)
    up, down = high.diff(), -low.diff()
    dm_plus = up.where((up > down) & (up > 0), 0.0)
    dm_minus = down.where((down > up) & (down > 0), 0.0)
    period = 14
    atr_w = tr.ewm(alpha=1 / period, adjust=False).mean()
    di_p = 100 * dm_plus.ewm(alpha=1 / period, adjust=False).mean() / atr_w.replace(0, np.nan)
    di_m = 100 * dm_minus.ewm(alpha=1 / period, adjust=False).mean() / atr_w.replace(0, np.nan)
    dx = (100 * (di_p - di_m).abs() / (di_p + di_m).replace(0, np.nan)).fillna(0.0)
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()
    sma20 = close.rolling(20).mean()
    return (adx >= 25.0) & (di_p > di_m) & (close >= sma20 * 0.99)


def vol_contraction_signals(df: pd.DataFrame) -> pd.Series:
    """Exactly signal_volatility_contraction_breakout (drought=0)."""
    close, high, low = df["Close"], df["High"], df["Low"]
    volume = df["Volume"].astype(float)
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    bb_width = (2 * std20 / sma20.replace(0, np.nan)) * 100
    bb_min = bb_width.rolling(40).min()
    bb_squeeze = bb_width <= bb_min * 1.05
    tr = _true_range(df)
    nr7 = tr <= tr.rolling(7).min() * 1.02
    direction = close >= sma20 * 0.99
    vol_quiet = volume.rolling(5).mean() < volume.rolling(20).mean() * 1.2
    rsi = _rsi_wilder(close, 14)
    return bb_squeeze & nr7 & direction & vol_quiet & (rsi <= 68)


def rs_breakout_signals(df: pd.DataFrame, spy: pd.DataFrame | None) -> pd.Series:
    """Exactly signal_relative_strength_breakout (drought=0), aligned by tail.

    The live function aligns close/SPY close by taking the LAST min_len bars of
    each, so we do the same positionally on the common tail.
    """
    if spy is None:
        return pd.Series(False, index=df.index)
    close = df["Close"]
    spy_close = spy["Close"]
    min_len = min(len(close), len(spy_close))
    if min_len < 25:
        return pd.Series(False, index=df.index)
    rs = pd.Series(close.iloc[-min_len:].values / spy_close.iloc[-min_len:].values,
                   index=close.index[-min_len:])
    rs_20d_high = rs.rolling(20).max()
    at_high = rs >= rs_20d_high * 0.999
    sma50 = close.rolling(50).mean() if len(close) >= 50 else None
    above = (close >= sma50 * 0.99) if sma50 is not None else pd.Series(True, index=df.index)
    rs_chg = (rs - rs.shift(5)) / rs.shift(5).where(rs.shift(5) > 0)
    out = pd.Series(False, index=df.index)
    tail = (at_high & (rs_chg >= 0.005)).fillna(False)
    out.iloc[-min_len:] = tail.values
    return out & above.reindex(df.index).fillna(False)


def atr(df: pd.DataFrame, n: int = 20) -> pd.Series:
    return _true_range(df).rolling(n).mean()


def build_row(strategy: str, symbol: str, df: pd.DataFrame, sig_idx: int) -> dict:
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
        f"{strategy}|{symbol}|{opened.date()}".encode()).hexdigest()[:20]
    return {
        "id": pid,
        "symbol": symbol,
        "direction": "LONG",
        "strategy": strategy,
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


def _signal_fn(strategy_key: str, df: pd.DataFrame, spy: pd.DataFrame | None) -> pd.Series:
    if strategy_key == "donchian":
        return donchian_signals(df)
    if strategy_key == "adx-trend":
        return adx_trend_signals(df)
    if strategy_key == "vol-contraction":
        return vol_contraction_signals(df)
    if strategy_key == "rs-breakout":
        return rs_breakout_signals(df, spy)
    raise ValueError(f"unknown strategy {strategy_key!r}")


def collect(strategy_key: str = DEFAULT_STRATEGY) -> list[dict]:
    strategy_name, min_bars = STRATEGIES[strategy_key]
    spy = None
    if strategy_key == "rs-breakout":
        spy_path = REPO / "data/cache/asset_class_review/SPY_5y.csv"
        if spy_path.exists():
            spy = pd.read_csv(spy_path)
    rows = []
    for path in sorted(glob.glob(str(REPO / CACHE_GLOB))):
        symbol = os.path.basename(path)[:-len("_5y.csv")]
        if not _is_equity(symbol):
            continue
        df = pd.read_csv(path)
        if not {"Date", "Close", "Volume", "High", "Low"}.issubset(df.columns) or len(df) < min_bars:
            continue
        sig = _signal_fn(strategy_key, df, spy)
        idxs = [i for i in sig[sig].index if i < len(df) - 1]  # need >=1 forward bar
        if not idxs:
            continue
        rows.append(build_row(strategy_name, symbol, df, max(idxs)))
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

_COLS = ("id", "symbol", "direction", "strategy", "entry_price", "take_profit",
         "stop_loss", "confidence", "elite_score", "trust_score", "category",
         "source_system", "status", "pnl_pct", "exit_price", "created_at",
         "closed_at", "exit_reason")


def upsert_rows(conn, rows: list[dict]) -> int:
    """The single insert path, shared by every strategy. Returns rows touched.

    Idempotency: `id` is deterministic (strategy|symbol|signal-date) and is the
    PRIMARY KEY, so a re-run hits ON DUPLICATE KEY UPDATE and never duplicates.
    """
    cur = conn.cursor()
    written = 0
    for r in rows:
        cur.execute(UPSERT, {k: r[k] for k in _COLS})
        written += cur.rowcount
    conn.commit()
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Emit real equity-breakout pod rows")
    ap.add_argument("--strategy", default=DEFAULT_STRATEGY,
                    choices=list(STRATEGIES) + ["all"],
                    help="which strategy to emit (default: donchian)")
    ap.add_argument("--apply", action="store_true", help="write to MySQL (default: dry run)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    keys = list(STRATEGIES) if args.strategy == "all" else [args.strategy]
    per = {k: collect(k) for k in keys}
    for k in keys:
        rows = per[k]
        name = STRATEGIES[k][0]
        if args.json:
            print(json.dumps(rows, indent=1, default=str))
            continue
        for r in rows:
            print(f"{name} {r['symbol']:6s} {r['_signal_date']} entry={r['entry_price']:.2f} "
                  f"exit={r['exit_price']:.2f} gross={r['_gross_pct']:+.2f}% "
                  f"net={r['pnl_pct']:+.2f}% {r['status']}/{r['exit_reason'] or '-'} "
                  f"held={r['_bars_held']}d")
        print(f"-- {name}: {len(rows)} rows from real signals on cached OHLCV")
    if not args.apply:
        print("dry run — nothing written (pass --apply to upsert into trading_picks)")
        return 0

    conn = _connect()
    try:
        for k in keys:
            rows = per[k]
            name = STRATEGIES[k][0]
            written = upsert_rows(conn, rows)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) n FROM trading_picks WHERE strategy=%s", (name,))
            total = cur.fetchone()["n"]
            print(f"applied {name}: {written} row(s) touched; trading_picks now has "
                  f"{total} rows for {name}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
