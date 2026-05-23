#!/usr/bin/env python3
"""
sports_arbitrage_scanner.py
===========================
Scans lm_sports_odds for pure arbitrage opportunities across all
bookmakers — including OLG ProLine+ and Betway — and emits a JSON
alert file that can be consumed by the dashboard or CI notifications.

Arbitrage definition:
    For a given event + market, if the sum of 1/best_odds for each
    outcome across *different* books is < 1.0, a risk-free profit exists.

Usage:
    python3 alpha_engine/sports_arbitrage_scanner.py
    python3 alpha_engine/sports_arbitrage_scanner.py --output backfill/sports_arbitrage_alerts.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    import pymysql
    _HAS_PYMYSQL = True
except Exception:
    pymysql = None  # type: ignore
    _HAS_PYMYSQL = False

DEFAULT_OUTPUT = "backfill/sports_arbitrage_alerts.json"

# DB credentials mirror live-monitor/api/db_config.php
DB_DEFAULTS = {
    "host": os.environ.get("SPORTS_DB_HOST", "mysql.50webs.com"),
    "user": os.environ.get("SPORTS_DB_USER", "ejaguiar1_sportsbet"),
    "password": os.environ.get("SPORTS_DB_PASSWORD", "eltonsportsbets"),
    "database": os.environ.get("SPORTS_DB_NAME", "ejaguiar1_sportsbet"),
    "port": int(os.environ.get("SPORTS_DB_PORT", "3306")),
}


def _connect() -> Optional[Any]:
    if not _HAS_PYMYSQL:
        print("[arb] pymysql not installed; cannot query DB", file=sys.stderr)
        return None
    try:
        return pymysql.connect(
            host=DB_DEFAULTS["host"],
            user=DB_DEFAULTS["user"],
            password=DB_DEFAULTS["password"],
            database=DB_DEFAULTS["database"],
            port=DB_DEFAULTS["port"],
            connect_timeout=10,
            read_timeout=15,
            write_timeout=15,
            cursorclass=pymysql.cursors.DictCursor,
        )
    except Exception as e:
        print(f"[arb] DB connection failed: {e}", file=sys.stderr)
        return None


def fetch_active_odds(conn: Any, hours_ahead: int = 48) -> List[Dict[str, Any]]:
    sql = (
        "SELECT sport, event_id, home_team, away_team, commence_time, "
        "bookmaker, bookmaker_key, market, outcome_name, outcome_price "
        "FROM lm_sports_odds "
        "WHERE commence_time >= NOW() AND commence_time <= DATE_ADD(NOW(), INTERVAL %s HOUR) "
        "AND outcome_price > 1.01 AND outcome_price < 80.0 "
        "ORDER BY event_id, market, outcome_name, outcome_price DESC"
    )
    with conn.cursor() as cur:
        cur.execute(sql, (hours_ahead,))
        return list(cur.fetchall())


def find_arbitrages(rows: List[Dict[str, Any]], min_profit_pct: float = 1.5) -> List[Dict[str, Any]]:
    """Group rows by (event_id, market, outcome_name) and find arb opportunities.

    2026-04-27 fixes (sports-C9, see docs/CODE_REVIEW_2026_04_27.md):
      - Default ``min_profit_pct`` raised 0.5 -> 1.5 to absorb slippage and
        the latency between snapshot read and bet placement.
      - Distinct-bookmaker enforcement: a candidate is only an arb when at
        least two *different* bookmakers contribute legs. Same-book "arbs"
        are non-actionable (the book just runs a balanced market).
      - Same-book candidates are still computed for visibility but flagged
        and excluded from the actionable list.
    """
    # Bucket by event+market
    buckets: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for r in rows:
        bk = f"{r['event_id']}\x1f{r['market']}"
        ok = r["outcome_name"]
        buckets.setdefault(bk, {}).setdefault(ok, []).append(r)

    arbs: List[Dict[str, Any]] = []
    for bk, outcomes in buckets.items():
        eid, market = bk.split("\x1f", 1)
        if len(outcomes) < 2:
            continue
        # For each outcome, pick the best price across *different* books
        best_for_outcome: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        for ok, quotes in outcomes.items():
            if not quotes:
                continue
            # Sort by price descending
            quotes_sorted = sorted(quotes, key=lambda x: float(x["outcome_price"]), reverse=True)
            best = quotes_sorted[0]
            best_for_outcome[ok] = (float(best["outcome_price"]), best)

        # Calculate implied prob sum using best prices
        inv_sum = 0.0
        legs: List[Dict[str, Any]] = []
        for ok, (price, best_row) in best_for_outcome.items():
            inv = 1.0 / price
            inv_sum += inv
            legs.append({
                "outcome_name": ok,
                "best_price": round(price, 4),
                "implied_prob": round(inv, 4),
                "bookmaker": best_row["bookmaker"],
                "bookmaker_key": best_row["bookmaker_key"],
                "sport": best_row["sport"],
                "home_team": best_row["home_team"],
                "away_team": best_row["away_team"],
                "commence_time": str(best_row["commence_time"]),
            })

        # 2026-04-27 (sports-C9): require at least 2 distinct bookmakers
        # contributing legs. A "best price" arb assembled entirely from one
        # book is the book's natural margin, not an exploitable spread.
        _distinct_books = {l["bookmaker_key"] for l in legs}
        if len(_distinct_books) < 2:
            continue

        if inv_sum < 1.0:
            profit_pct = round((1.0 - inv_sum) * 100.0, 3)
            if profit_pct >= min_profit_pct:
                # Determine if OLG or Betway is involved
                ca_books = [l for l in legs if l["bookmaker_key"] in ("olg_prolineplus", "betway")]
                arbs.append({
                    "event_id": eid,
                    "market": market,
                    "profit_pct": profit_pct,
                    "implied_prob_sum": round(inv_sum, 4),
                    "legs": legs,
                    "ca_legal_involved": len(ca_books) > 0,
                    "ca_legal_books": [l["bookmaker"] for l in ca_books],
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                })

    # Sort by profit desc
    arbs.sort(key=lambda x: x["profit_pct"], reverse=True)
    return arbs


def main() -> int:
    parser = argparse.ArgumentParser(description="Sports arbitrage scanner")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--min-profit", type=float, default=1.5, help="Minimum arb profit %% (default 1.5; absorbs slippage/latency)")
    parser.add_argument("--hours-ahead", type=int, default=48)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    print("[arb] Connecting to sports DB...")
    conn = _connect()
    if not conn:
        # Degrade gracefully: write empty alert file so downstream doesn't crash
        payload = {
            "ok": True,
            "arbitrages": [],
            "note": "DB connection unavailable",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        return 0

    try:
        print(f"[arb] Fetching odds ({args.hours_ahead}h window)...")
        rows = fetch_active_odds(conn, args.hours_ahead)
        print(f"[arb] Rows fetched: {len(rows)}")

        arbs = find_arbitrages(rows, min_profit_pct=args.min_profit)
        print(f"[arb] Opportunities found: {len(arbs)}")

        if args.verbose:
            for a in arbs[:5]:
                teams = f"{a['legs'][0]['away_team']} @ {a['legs'][0]['home_team']}"
                print(f"  PROFIT {a['profit_pct']}% | {teams} | {a['market']}")
                for leg in a["legs"]:
                    print(f"    -> {leg['outcome_name']} {leg['best_price']} @ {leg['bookmaker']}")

        payload = {
            "ok": True,
            "arbitrage_count": len(arbs),
            "min_profit_pct": args.min_profit,
            "hours_ahead": args.hours_ahead,
            "arbitrages": arbs,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str)
        print(f"[arb] Wrote {len(arbs)} alerts to {args.output}")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
