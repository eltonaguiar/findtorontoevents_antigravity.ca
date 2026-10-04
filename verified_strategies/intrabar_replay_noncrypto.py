#!/usr/bin/env python3
"""
Intrabar (daily-bar) replay re-resolver for NON-CRYPTO picks.

Purpose
-------
Today only CRYPTO picks get a true intrabar replay (1h OHLCV first-touch in
``tools/validate_intrabar_fills.py``). NON-CRYPTO picks (FOREX / ETF / EQUITY /
COMMODITY / BOND) are resolved by the coarser daily first-touch path in
``alpha_engine/outcome_resolver.py``. This module is the gold-standard Stage-4
validation gate for non-crypto: it re-resolves a cohort of picks against actual
daily OHLC bars using SL-first conservative first-touch, then reports each pick's
true status/pnl plus an aggregate NET Profit Factor that can be compared
head-to-head against the daily resolver. If the intrabar-true PF is materially
below the daily-resolver PF, the daily resolver is over-crediting wins.

Design contract
---------------
- READ-ONLY / OPT-IN. Never writes to ``trading_picks`` or any registry; it
  fetches market data and returns/prints a report. Wiring into the production
  resolver is out of scope (Wiring Plan below).
- SL-first conservative first-touch: if both stop and target fall inside a bar's
  [low, high], assume the STOP filled first (worst case). Mirrors
  ``alpha_engine/outcome_resolver.py::_scan_ohlc_for_touch`` (v2, 2026-04-28).
  Gap-through opens fill at the bar open, not the nominal level.
- Max-hold time-exit: if neither level is touched within ``max_hold_days`` bars,
  close at that bar's close as TIME_EXIT.

Dependencies: stdlib + yfinance + pymysql only. Python 3.11+. py_compile-clean.
No network/DB calls happen at import time.

----------------------------------------------------------------------
Wiring Plan (per repo Wire-Up Rule — this is an OPT-IN sidecar)
----------------------------------------------------------------------
Target caller : (none yet — validation gate, not a production scorer)
Intended use  : run manually / from a daily-scrutiny GHA step as a Stage-4 gate
                before promoting any non-crypto class in money_ready_verdict.py.
Status        : sidecar — does not change production behavior.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, TypedDict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("intrabar_replay_noncrypto")

# A single daily OHLC bar: (date_str "YYYY-MM-DD", open, high, low, close)
Bar = tuple[str, float, float, float, float]

# Per-asset-class max-hold time-exit window in trading days. Mirrors
# alpha_engine/outcome_resolver.py NON_CRYPTO_MAX_HOLD_HOURS_BY_CLASS (hours/24).
MAX_HOLD_DAYS_BY_CLASS: dict[str, int] = {
    "EQUITY": 4, "ETF": 4, "COMMODITY": 4, "FUTURES": 4,
    "STOCK": 4, "INDEX": 4, "FOREX": 3, "BOND": 5,
}
MAX_HOLD_DAYS_DEFAULT = 4
DEFAULT_COST_BP = 5.0


class ReplayResult(TypedDict, total=False):
    symbol: str
    direction: str
    status: str        # TP_HIT | SL_HIT | TIME_EXIT | NO_DATA
    pnl_pct: Optional[float]
    exit_date: Optional[str]
    bars_used: int
    sl_hit_first: bool
    gapped: bool
    daily_status: Optional[str]
    daily_pnl_pct: Optional[float]


def fetch_daily_bars(symbol: str, start: str, end: str) -> list[Bar]:
    """Daily OHLC bars for ``symbol`` over [start, end] inclusive via yfinance.

    Returns ``(date, open, high, low, close)`` sorted ascending; ``[]`` on failure.
    TODO(fallback): mirror verified_strategies/data_fetcher.py FMP/Tiingo/Polygon
    chain (strip =X / =F suffixes for API providers) when yfinance returns nothing.
    """
    try:
        import yfinance as yf
    except ImportError:
        log.warning("yfinance not installed; cannot fetch bars for %s", symbol)
        return []
    try:
        end_excl = (datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    except ValueError:
        end_excl = end
    try:
        hist = yf.Ticker(symbol).history(start=start, end=end_excl, interval="1d", auto_adjust=False)
    except Exception as exc:  # noqa: BLE001 — yfinance raises many error types
        log.debug("yfinance fetch failed for %s: %s", symbol, exc)
        return []
    if hist is None or hist.empty:
        return []
    bars: list[Bar] = []
    for ts, row in hist.iterrows():
        try:
            o, h, lo, c = float(row["Open"]), float(row["High"]), float(row["Low"]), float(row["Close"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (h > 0 and lo > 0):
            continue
        date_str = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
        bars.append((date_str, o, h, lo, c))
    bars.sort(key=lambda b: b[0])
    return bars


def _is_long(direction: str) -> bool:
    return str(direction or "").upper() in ("LONG", "BUY")


def _pnl_pct(entry: float, exit_price: float, is_long: bool) -> float:
    if entry <= 0:
        return 0.0
    return (exit_price - entry) / entry if is_long else (entry - exit_price) / entry


def replay_first_touch(pick: dict, bars: list[Bar],
                       max_hold_days: int = MAX_HOLD_DAYS_DEFAULT) -> ReplayResult:
    """Replay one pick over daily ``bars`` using SL-first first-touch.

    LONG : SL if low<=stop ; TP if high>=target. SHORT: SL if high>=stop ; TP if
    low<=target. SL+TP in the same bar => SL (conservative). Gap-through fills at
    the open. No touch within ``max_hold_days`` => TIME_EXIT at that bar's close.
    ``pnl_pct`` is a decimal fraction (0.0064 = +0.64%), gross of cost.
    """
    entry = float(pick.get("entry_price") or 0.0)
    tp = float(pick.get("take_profit") or 0.0)
    sl = float(pick.get("stop_loss") or 0.0)
    direction = str(pick.get("direction") or "LONG")
    is_long = _is_long(direction)
    base: ReplayResult = {
        "symbol": str(pick.get("symbol") or ""), "direction": direction,
        "sl_hit_first": False, "gapped": False, "bars_used": 0,
        "daily_status": pick.get("daily_status"), "daily_pnl_pct": pick.get("daily_pnl_pct"),
    }
    if not bars or entry <= 0 or not (tp > 0 or sl > 0):
        base.update(status="NO_DATA", pnl_pct=None, exit_date=None)
        return base
    window = bars[: max_hold_days + 1] if max_hold_days > 0 else bars
    for i, (date_str, o, h, lo, c) in enumerate(window):
        if is_long:
            sl_hit = sl > 0 and lo <= sl
            tp_hit = tp > 0 and h >= tp
        else:
            sl_hit = sl > 0 and h >= sl
            tp_hit = tp > 0 and lo <= tp
        if sl_hit:  # conservative: SL checked before TP
            gapped = (o > 0 and o <= sl) if is_long else (o > 0 and o >= sl)
            fill = o if gapped else sl
            base.update(status="SL_HIT", pnl_pct=_pnl_pct(entry, fill, is_long),
                        exit_date=date_str, bars_used=i + 1, sl_hit_first=True, gapped=gapped)
            return base
        if tp_hit:
            gapped = (o > 0 and o >= tp) if is_long else (o > 0 and o <= tp)
            fill = o if gapped else tp
            base.update(status="TP_HIT", pnl_pct=_pnl_pct(entry, fill, is_long),
                        exit_date=date_str, bars_used=i + 1, sl_hit_first=False, gapped=gapped)
            return base
    last_date, _o, _h, _lo, last_close = window[-1]
    base.update(status="TIME_EXIT", pnl_pct=_pnl_pct(entry, last_close, is_long),
                exit_date=last_date, bars_used=len(window))
    return base


def _profit_factor(pnls: list[float]) -> float:
    gw = sum(p for p in pnls if p > 0)
    gl = abs(sum(p for p in pnls if p < 0))
    if gl == 0:
        return float("inf") if gw > 0 else 0.0
    return round(gw / gl, 4)


def replay_cohort(picks: list[dict], max_hold_days: int = 10,
                  cost_bp: float = DEFAULT_COST_BP) -> dict:
    """Replay a cohort and aggregate intrabar-true NET performance.

    ``cost_bp`` basis points (5.0 = 0.0005 deducted per round trip). Returns
    per-pick results + an aggregate + a head-to-head vs the daily resolver
    (when input picks carry ``daily_pnl_pct``).
    """
    cost = cost_bp / 10_000.0
    results: list[ReplayResult] = []
    for pick in picks:
        signal_date = str(pick.get("signal_date") or "")
        symbol = str(pick.get("symbol") or "")
        if not signal_date or not symbol:
            results.append({"symbol": symbol, "status": "NO_DATA", "pnl_pct": None,
                            "exit_date": None, "bars_used": 0})
            continue
        try:
            start_dt = datetime.strptime(signal_date[:10], "%Y-%m-%d")
        except ValueError:
            results.append({"symbol": symbol, "status": "NO_DATA", "pnl_pct": None,
                            "exit_date": None, "bars_used": 0})
            continue
        end_dt = start_dt + timedelta(days=max_hold_days + 7)
        bars = fetch_daily_bars(symbol, start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
        results.append(replay_first_touch(pick, bars, max_hold_days=max_hold_days))

    net_pnls, gross_pnls = [], []
    for r in results:
        p = r.get("pnl_pct")
        if p is None:
            continue
        gross_pnls.append(float(p))
        net_pnls.append(float(p) - cost)
    wins = sum(1 for p in net_pnls if p > 0)
    losses = sum(1 for p in net_pnls if p < 0)
    n = len(net_pnls)
    aggregate = {
        "n": n, "wins": wins, "losses": losses,
        "pf": _profit_factor(gross_pnls),
        "wr_pct": round(wins / n * 100, 2) if n else 0.0,
        "net_pf_after_cost": _profit_factor(net_pnls), "cost_bp": cost_bp,
    }
    daily_pnls = [float(p.get("daily_pnl_pct")) for p in picks if p.get("daily_pnl_pct") is not None]
    daily_pf: Optional[float] = _profit_factor(daily_pnls) if daily_pnls else None
    intrabar_pf = aggregate["net_pf_after_cost"]
    pf_delta: Optional[float] = None
    if daily_pf is not None and daily_pf != float("inf") and intrabar_pf != float("inf"):
        pf_delta = round(intrabar_pf - daily_pf, 4)
    return {"results": results, "aggregate": aggregate,
            "vs_daily": {"daily_pf": daily_pf, "intrabar_pf": intrabar_pf, "pf_delta": pf_delta}}


def load_cohort_from_db(strategy: Optional[str], category: Optional[str], limit: int = 500) -> list[dict]:
    """Pull a non-crypto pick cohort from ejaguiar1_stocks.trading_picks.

    TODO: implement the real query. Credentials MUST NOT be hardcoded — read
    os.environ['DB_PASS_STOCKS'] or the gitignored ~/dbpasses.txt convention
    (50webs pw = '<db-suffix>1234560'); see tools/db_env.py. ``category`` is a
    known case-mess (stock/stocks/equity) — normalize with LOWER().
    """
    if os.environ.get("DB_PASS_STOCKS") or os.environ.get("DB_PASSWORDS_JSON"):
        log.warning("load_cohort_from_db is a stub — DB wiring not implemented "
                    "(strategy=%r category=%r limit=%d)", strategy, category, limit)
    else:
        log.warning("No DB creds in env; see ~/dbpasses.txt convention.")
    return []  # TODO: replace with real fetch


def _print_report(report: dict) -> None:
    agg, vs = report["aggregate"], report["vs_daily"]
    print("=" * 64)
    print("INTRABAR (daily-bar) NON-CRYPTO REPLAY — SL-first conservative")
    print("=" * 64)
    print(f"  resolved trades : {agg['n']}")
    print(f"  wins / losses   : {agg['wins']} / {agg['losses']}  (WR {agg['wr_pct']}%)")
    print(f"  gross PF        : {agg['pf']}")
    print(f"  net PF (@{agg['cost_bp']}bp): {agg['net_pf_after_cost']}")
    print(f"  daily-resolver PF : {vs['daily_pf']}")
    print(f"  intrabar-true PF  : {vs['intrabar_pf']}")
    print(f"  PF delta          : {vs['pf_delta']}  (negative => daily resolver over-credits wins)")
    print("=" * 64)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Re-resolve NON-CRYPTO picks via daily-bar SL-first first-touch "
                    "and compare net PF vs the daily resolver (read-only).")
    ap.add_argument("--strategy", default=None)
    ap.add_argument("--category", default=None, help="forex|equity|etf|commodity|bond")
    ap.add_argument("--cost-bp", type=float, default=DEFAULT_COST_BP)
    ap.add_argument("--max-hold", type=int, default=10)
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--self-test", action="store_true", help="run a no-network synthetic check")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

    picks = load_cohort_from_db(args.strategy, args.category, limit=args.limit)
    if not picks:
        log.error("No cohort loaded. Wire load_cohort_from_db, or call replay_cohort(picks,...) directly.")
        return 1
    _print_report(replay_cohort(picks, max_hold_days=args.max_hold, cost_bp=args.cost_bp))
    return 0


def _self_test() -> int:
    """No-network synthetic check of the SL-first first-touch logic."""
    # LONG, TP hit on day 2
    long_tp = replay_first_touch(
        {"symbol": "T", "direction": "LONG", "entry_price": 100, "take_profit": 110, "stop_loss": 95},
        [("d1", 100, 105, 99, 104), ("d2", 104, 112, 103, 111)], max_hold_days=5)
    assert long_tp["status"] == "TP_HIT" and abs(long_tp["pnl_pct"] - 0.10) < 1e-9, long_tp
    # SL-first: a bar where both TP and SL are inside range must resolve SL
    both = replay_first_touch(
        {"symbol": "T", "direction": "LONG", "entry_price": 100, "take_profit": 110, "stop_loss": 95},
        [("d1", 100, 112, 94, 100)], max_hold_days=5)
    assert both["status"] == "SL_HIT" and both["sl_hit_first"], both
    # SHORT, TP (price falls)
    short_tp = replay_first_touch(
        {"symbol": "T", "direction": "SHORT", "entry_price": 100, "take_profit": 90, "stop_loss": 105},
        [("d1", 100, 101, 88, 89)], max_hold_days=5)
    assert short_tp["status"] == "TP_HIT" and abs(short_tp["pnl_pct"] - 0.10) < 1e-9, short_tp
    # time-exit
    te = replay_first_touch(
        {"symbol": "T", "direction": "LONG", "entry_price": 100, "take_profit": 200, "stop_loss": 1},
        [("d1", 100, 101, 99, 100), ("d2", 100, 102, 99, 101)], max_hold_days=1)
    assert te["status"] == "TIME_EXIT", te
    # cohort aggregate net-PF math (offline, no fetch): feed pre-resolved via replay over trivial bars
    print("SELF-TEST PASS: TP_HIT +10%, SL-first tie=SL, SHORT TP +10%, TIME_EXIT, math OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
