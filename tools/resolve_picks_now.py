#!/usr/bin/env python3
"""Resolve picks_now_tracker outcomes — so /audit/picks-now.html picks get a
verifiable right/wrong track record (the operator's core ask: "see historical
picks and whether we were right or wrong").

picks_now_tracker has 500+ picks ENTERED but 0 RESOLVED (exit_pnl_pct NULL on
all). This tool replays each unresolved pick's intrabar path from generated_at
forward and fills exit_price / exit_pnl_pct / exit_reason / resolved_at by
FIRST-TOUCH of suggested_tp vs suggested_sl (the same intrabar discipline as
reresolve_intrabar.py — SL-first on same-bar ties, conservative).

OHLC sources: stock_ohlcv (EQUITY/ETF, 1h), crypto_ohlcv (CRYPTO, 1h),
fx_prices (FOREX, daily). Symbols without bars are left OPEN (no_data).

Resolution rules per pick (direction STRONG_BUY/BUY = long; SELL/SHORT = short):
  - TP touched first within horizon -> WON  (exit=tp)
  - SL touched first               -> LOST (exit=sl)
  - neither, AND pick older than --max-hold-days -> TIME_EXIT (exit=last close)
  - neither, still within horizon  -> leave OPEN (too recent)

SAFETY: DRY-RUN by default (read-only, prints the right/wrong split). --apply
fills ONLY the NULL exit_* columns (never overwrites a resolved row, never
touches entry data). This is the tracking table's own purpose-built outcome
columns — lower stakes than canonical trading_picks — but still gated.

Usage:
  python3 tools/resolve_picks_now.py                 # dry-run
  python3 tools/resolve_picks_now.py --apply         # write outcomes
  python3 tools/resolve_picks_now.py --max-hold-days 10
"""
from __future__ import annotations
import argparse, sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import pymysql
from tools.db_env import get_stocks_creds


def _to_ms(dt):
    if dt is None:
        return None
    if isinstance(dt, (int, float)):
        return int(dt)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def fetch_bars(cur, asset_class, symbol, start_ms, end_ms):
    """Return list of (high, low, close) bars in time order, or [] if none."""
    ac = (asset_class or "").upper()
    if ac in ("CRYPTO", "MEME"):
        cur.execute("SELECT high,low,close FROM crypto_ohlcv WHERE symbol=%s AND timeframe='1h' "
                    "AND timestamp>=%s AND timestamp<=%s ORDER BY timestamp", (symbol, start_ms, end_ms))
    elif ac in ("FOREX",):
        # fx_prices is daily; pair like EURUSD (strip =X)
        pair = symbol.replace("=X", "")
        cur.execute("SELECT high_price high, low_price low, close_price close FROM fx_prices "
                    "WHERE pair=%s AND UNIX_TIMESTAMP(trade_date)*1000>=%s AND UNIX_TIMESTAMP(trade_date)*1000<=%s "
                    "ORDER BY trade_date", (pair, start_ms, end_ms))
    else:  # EQUITY / ETF / others -> stock_ohlcv
        cur.execute("SELECT high,low,close FROM stock_ohlcv WHERE symbol=%s AND timeframe='1h' "
                    "AND timestamp>=%s AND timestamp<=%s ORDER BY timestamp", (symbol, start_ms, end_ms))
    return [(float(r[0]), float(r[1]), float(r[2])) for r in cur.fetchall()]


def resolve(entry, tp, sl, direction, bars, max_bars):
    """First-touch resolution. Returns (status, exit_price, pnl_pct, reason) or None if OPEN/no-data."""
    if not bars:
        return None  # no data -> stay OPEN
    is_long = str(direction or "BUY").upper() in ("LONG", "BUY", "STRONG_BUY")
    for i, (h, l, c) in enumerate(bars):
        if is_long:
            sl_hit, tp_hit = l <= sl, h >= tp
        else:
            sl_hit, tp_hit = h >= sl, l <= tp
        if sl_hit:  # SL-first on same-bar tie (conservative)
            pnl = (sl - entry) / entry * 100 if is_long else (entry - sl) / entry * 100
            return ("LOST", sl, round(pnl, 4), "SL_HIT")
        if tp_hit:
            pnl = (tp - entry) / entry * 100 if is_long else (entry - tp) / entry * 100
            return ("WON", tp, round(pnl, 4), "TP_HIT")
    # neither touched within available bars
    if len(bars) >= max_bars:  # horizon fully elapsed -> time exit at last close
        last = bars[-1][2]
        pnl = (last - entry) / entry * 100 if is_long else (entry - last) / entry * 100
        return ("EXPIRED", last, round(pnl, 4), "TIME_EXIT")
    return None  # still within horizon, too recent -> OPEN


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--max-hold-days", type=int, default=10)
    args = ap.parse_args()
    max_bars = args.max_hold_days * 24  # 1h bars

    conn = pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    cur.execute("SELECT id, symbol, asset_class, direction, entry_price, suggested_tp, suggested_sl, generated_at "
                "FROM picks_now_tracker WHERE exit_pnl_pct IS NULL AND entry_price>0 AND suggested_tp>0 AND suggested_sl>0")
    picks = cur.fetchall()
    print(f"[resolve_picks_now] {len(picks)} unresolved picks with TP/SL")

    from collections import Counter
    outcomes = Counter()
    won = lost = 0
    updates = []
    for p in picks:
        start = _to_ms(p["generated_at"])
        if not start:
            outcomes["no_ts"] += 1
            continue
        end = start + max_bars * 3600 * 1000
        bars = fetch_bars(cur, p["asset_class"], p["symbol"], start, end)
        r = resolve(float(p["entry_price"]), float(p["suggested_tp"]), float(p["suggested_sl"]),
                    p["direction"], bars, max_bars)
        if r is None:
            outcomes["OPEN/no_data"] += 1
            continue
        status, exit_px, pnl, reason = r
        outcomes[reason] += 1
        if pnl > 0:
            won += 1
        else:
            lost += 1
        updates.append((p["id"], status, exit_px, pnl, reason))

    print("\n=== RESOLUTION OUTCOMES (would-be) ===")
    for k, v in outcomes.most_common():
        print(f"  {k}: {v}")
    decisive = won + lost
    if decisive:
        print(f"\n  RIGHT/WRONG: {won} won / {lost} lost = {won/decisive*100:.1f}% WR on {decisive} resolved")
    print(f"  (resolvable now: {len(updates)} of {len(picks)})")

    if args.apply and updates:
        for pid, status, exit_px, pnl, reason in updates:
            cur.execute("UPDATE picks_now_tracker SET exit_price=%s, exit_pnl_pct=%s, exit_reason=%s, "
                        "resolved_at=NOW() WHERE id=%s AND exit_pnl_pct IS NULL",
                        (round(exit_px, 6), pnl, reason, pid))
        conn.commit()
        print(f"\n[APPLY] wrote {len(updates)} resolutions (only filled NULL exit_* rows)")
    elif updates:
        print(f"\n[DRY-RUN] {len(updates)} picks would be resolved. Re-run with --apply to write.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
