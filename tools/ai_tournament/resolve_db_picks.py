#!/usr/bin/env python3
"""
DB-native resolver for the AI tournament `tournament_picks` table.

WHY THIS EXISTS (INCIDENT_OVERALL #43):
The existing resolution path is JSON-bound: `price_tracker.py` only resolves
OPEN picks that are still present in the recent `data/ai_tournament/submissions/*.json`
glob, and `ingest_to_db.py` propagates those resolutions back to MySQL via
`ON DUPLICATE KEY UPDATE`. Any OPEN pick that ages out of the submissions glob
window can therefore NEVER be resolved in the DB. As of 2026-05-31 this left
2,693 OPEN rows (1,479 aged >5d) stranded — DB resolution throughput went
1,725 (2026-05-24) -> 1 (05-25) -> 0, starving every model of resolved sample
and blocking the top tournament models from reaching n>=100.

This resolver reads OPEN picks DIRECTLY from the DB (independent of the JSON
glob), reuses the exact tested TP/SL/expiry logic from price_tracker.resolve_pick
(+ its price-failover fetch_price), and writes resolutions straight back to the
DB. Dry-run by default; --apply commits.

USAGE:
  python tools/ai_tournament/resolve_db_picks.py                 # dry-run, all OPEN
  python tools/ai_tournament/resolve_db_picks.py --expired-only  # only past resolution window (deterministic, no TP/SL ambiguity)
  python tools/ai_tournament/resolve_db_picks.py --limit 50      # cap work
  python tools/ai_tournament/resolve_db_picks.py --apply         # commit UPDATEs

READ-ONLY unless --apply is passed. Never prints credentials.
"""
from __future__ import annotations
import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- import the tested resolve/fetch logic from price_tracker (works from /tmp or in-repo) ---
_REPO = Path(__file__).resolve()
for _p in list(_REPO.parents) + [Path("/home/eaguiar2015/findtorontoevents_antigravity.ca")]:
    if (_p / "tools" / "ai_tournament" / "price_tracker.py").exists():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break
from tools.ai_tournament.price_tracker import (  # noqa: E402
    resolve_pick, fetch_price, RESOLUTION_WINDOWS_DAYS,
)
from tools.db_env import get_stocks_creds  # noqa: E402
import pymysql  # noqa: E402


def _iso_aware(v) -> str:
    """Return an ISO-8601 string that is always timezone-aware (UTC).

    pymysql returns DATETIME columns as naive datetimes; submitted_at may also
    arrive as a string. resolve_pick compares submitted_at+window against an
    aware `datetime.now(timezone.utc)`, so a naive value would TypeError. Normalize.
    """
    if hasattr(v, "isoformat"):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
    s = str(v)
    # only append UTC offset if the string carries no tz info already
    # (Z, or a +HH:MM / -HH:MM offset after the date portion at index 10)
    if "Z" not in s and "+" not in s[10:] and "-" not in s[10:]:
        s += "+00:00"
    return s


def _fetch_price(pick):
    """Direct yfinance fetch for COMMODITY/FUTURES =F symbols; tested path otherwise.

    price_tracker.fetch_price_equity historically stripped '=F' before querying
    yfinance (which needs the suffix for futures/commodities, e.g. 'GC=F'). That
    bug was fixed in PR #135's price_tracker.py change, but we keep COMMODITY/FUTURES
    on the direct yfinance path here to skip the Alpha Vantage fallback for symbols
    that reliably exist in yfinance with their '=F' suffix. Redundant-but-harmless
    once the price_tracker fix lands; safe to collapse in a future refactor.
    """
    ac = (pick.get("asset_class") or "EQUITY").upper()
    sym = pick.get("symbol", "")
    if ac in ("COMMODITY", "FUTURES") and sym.endswith("=F"):
        try:
            import yfinance as yf
            h = yf.Ticker(sym).history(period="2d")
            if len(h):
                return float(h["Close"].iloc[-1])
        except Exception:
            pass
        return None
    return fetch_price(pick)

RESOLVE_COLS = ["id", "symbol", "asset_class", "direction",
                "entry_price", "take_profit", "stop_loss", "submitted_at", "status"]


def _is_expired(asset_class: str, submitted_at) -> bool:
    if not submitted_at:
        return False
    if isinstance(submitted_at, str):
        try:
            submitted_at = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
        except ValueError:
            return False
    if submitted_at.tzinfo is None:
        submitted_at = submitted_at.replace(tzinfo=timezone.utc)
    window = RESOLUTION_WINDOWS_DAYS.get((asset_class or "EQUITY").upper(), 30)
    return datetime.now(timezone.utc) >= submitted_at + timedelta(days=window)


def main() -> int:
    ap = argparse.ArgumentParser(description="DB-native tournament_picks resolver")
    ap.add_argument("--apply", action="store_true", help="commit UPDATEs (default: dry-run)")
    ap.add_argument("--expired-only", action="store_true",
                    help="only resolve picks past their resolution window (deterministic)")
    ap.add_argument("--asset-class", default=None, help="restrict to one asset class")
    ap.add_argument("--limit", type=int, default=0, help="max picks to process (0 = all)")
    args = ap.parse_args()

    conn = pymysql.connect(**get_stocks_creds())
    cur = conn.cursor(pymysql.cursors.DictCursor)
    sql = f"SELECT {', '.join(RESOLVE_COLS)} FROM tournament_picks WHERE status='OPEN' " \
          "AND entry_price IS NOT NULL AND take_profit IS NOT NULL AND stop_loss IS NOT NULL"
    params: list = []
    if args.asset_class:
        sql += " AND asset_class=%s"
        params.append(args.asset_class.upper())
    sql += " ORDER BY submitted_at ASC"
    if args.limit:
        sql += " LIMIT %s"
        params.append(args.limit)
    cur.execute(sql, params)
    rows = cur.fetchall()
    print(f"[resolve-db] {len(rows)} OPEN candidate picks loaded "
          f"({'expired-only' if args.expired_only else 'all'}; "
          f"{'APPLY' if args.apply else 'DRY-RUN'})")

    counts = {"WIN": 0, "LOSS": 0, "still_open": 0, "skip_expired_filter": 0,
              "price_fail": 0}
    updates: list[tuple] = []
    for r in rows:
        if args.expired_only and not _is_expired(r["asset_class"], r["submitted_at"]):
            counts["skip_expired_filter"] += 1
            continue
        pick = {
            "entry_price": r["entry_price"], "take_profit": r["take_profit"],
            "stop_loss": r["stop_loss"], "direction": r.get("direction") or "LONG",
            "asset_class": r.get("asset_class") or "EQUITY", "symbol": r["symbol"],
            "submitted_at": _iso_aware(r["submitted_at"]),
            "status": "OPEN",
        }
        price = _fetch_price(pick)
        if price is None:
            counts["price_fail"] += 1
            continue
        out = resolve_pick(pick, price)
        st = out.get("status", "OPEN")
        if st in ("WIN", "LOSS"):
            counts[st] += 1
            updates.append((st, out.get("exit_price"), out.get("pnl_pct"),
                            out.get("exit_reason"), out.get("resolved_at"), r["id"]))
        else:
            counts["still_open"] += 1

    print(f"[resolve-db] would resolve: WIN={counts['WIN']} LOSS={counts['LOSS']} "
          f"| still_open={counts['still_open']} price_fail={counts['price_fail']} "
          f"skipped_not_expired={counts['skip_expired_filter']}")

    if args.apply and updates:
        cur2 = conn.cursor()
        cur2.executemany(
            "UPDATE tournament_picks SET status=%s, exit_price=%s, pnl_pct=%s, "
            "exit_reason=%s, resolved_at=%s WHERE id=%s AND status='OPEN'", updates)
        conn.commit()
        print(f"[resolve-db] APPLIED {cur2.rowcount} DB updates.")
    elif updates:
        print(f"[resolve-db] DRY-RUN: {len(updates)} picks would be UPDATEd "
              f"(pass --apply to commit). Sample:")
        for u in updates[:5]:
            print(f"    id={u[5]} -> {u[0]} pnl={u[2]}% ({u[3]})")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
