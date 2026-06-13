#!/usr/bin/env python3
"""build_picks_now_track_record.py — honest forward-tested performance for /audit/picks-now.html.

Reads ONLY the deduped tracking view `vw_picks_now_dedup` (one row per symbol per
UTC day; created 2026-06-09 alongside the per-symbol-day writer guards) and emits
`audit_dashboard/data/picks_now_track_record.json` for the page's
"Forward-Tested Performance" panel.

Honesty rules baked in:
- Deduped n only (no double-counting from the pre-guard duplicate rows).
- WR is reported with an early-resolution-bias caveat while unresolved picks
  remain: TP/SL touches resolve in days, TIME_EXIT losers take the full horizon,
  so early WR skews high. The panel must show resolved AND still-active counts.
- No annualized/extrapolated numbers. Raw pnl only.

Read-only against the DB; writes one additive JSON. Never run dashboard
generators from here. Usage: python3 tools/build_picks_now_track_record.py [--out PATH] [--stdout]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pymysql  # noqa: E402
from tools.db_env import get_stocks_creds  # noqa: E402

OUT_DEFAULT = os.path.join(REPO_ROOT, "audit_dashboard", "data", "picks_now_track_record.json")
_KEEP = ("host", "user", "password", "database", "port", "connect_timeout")


def _f(x):
    return float(x) if x is not None else None


def build() -> dict:
    creds = {k: v for k, v in get_stocks_creds().items() if k in _KEEP}
    conn = pymysql.connect(**creds, cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()

    # Totals over the deduped view.
    cur.execute(
        """
        SELECT COUNT(*) AS tracked,
               SUM(exit_pnl_pct IS NOT NULL) AS resolved,
               SUM(exit_pnl_pct > 0) AS won,
               SUM(exit_pnl_pct <= 0 AND exit_pnl_pct IS NOT NULL) AS lost,
               MIN(generated_at) AS first_tracked,
               MAX(generated_at) AS last_tracked,
               AVG(CASE WHEN exit_pnl_pct IS NOT NULL THEN exit_pnl_pct END) AS avg_pnl,
               SUM(CASE WHEN exit_pnl_pct IS NOT NULL THEN exit_pnl_pct ELSE 0 END) AS cum_pnl
        FROM vw_picks_now_dedup
        """
    )
    t = cur.fetchone()
    resolved = int(t["resolved"] or 0)
    won = int(t["won"] or 0)

    # Resolved rows (the actual forward track record).
    cur.execute(
        """
        SELECT symbol, asset_class, direction,
               DATE(generated_at) AS pick_date,
               entry_price, exit_price,
               ROUND(exit_pnl_pct, 2) AS pnl_pct,
               exit_reason, resolved_at,
               DATEDIFF(resolved_at, generated_at) AS days_held
        FROM vw_picks_now_dedup
        WHERE exit_pnl_pct IS NOT NULL
        ORDER BY resolved_at DESC, symbol
        LIMIT 200
        """
    )
    resolved_rows = []
    for r in cur.fetchall():
        resolved_rows.append({
            "symbol": r["symbol"],
            "asset_class": r["asset_class"],
            "direction": r["direction"],
            "pick_date": str(r["pick_date"]),
            "entry": _f(r["entry_price"]),
            "exit": _f(r["exit_price"]),
            "pnl_pct": _f(r["pnl_pct"]),
            "exit_reason": r["exit_reason"],
            "resolved_at": str(r["resolved_at"]),
            "days_held": int(r["days_held"] or 0),
        })

    # Maturity pipeline: unresolved picks by age bucket (so the page can show
    # how much of the cohort hasn't had time to prove itself yet).
    cur.execute(
        """
        SELECT CASE
                 WHEN DATEDIFF(UTC_DATE(), DATE(generated_at)) <= 2 THEN '0-2d'
                 WHEN DATEDIFF(UTC_DATE(), DATE(generated_at)) <= 5 THEN '3-5d'
                 WHEN DATEDIFF(UTC_DATE(), DATE(generated_at)) <= 9 THEN '6-9d'
                 ELSE '10d+ (TIME_EXIT due)'
               END AS age_bucket,
               COUNT(*) AS n
        FROM vw_picks_now_dedup
        WHERE exit_pnl_pct IS NULL
        GROUP BY age_bucket
        ORDER BY MIN(DATEDIFF(UTC_DATE(), DATE(generated_at)))
        """
    )
    pipeline = {r["age_bucket"]: int(r["n"]) for r in cur.fetchall()}

    # Per-asset-class split of the resolved cohort.
    cur.execute(
        """
        SELECT asset_class,
               COUNT(*) AS n,
               SUM(exit_pnl_pct > 0) AS won,
               ROUND(AVG(exit_pnl_pct), 2) AS avg_pnl
        FROM vw_picks_now_dedup
        WHERE exit_pnl_pct IS NOT NULL
        GROUP BY asset_class
        ORDER BY n DESC
        """
    )
    by_class = [
        {"asset_class": r["asset_class"], "n": int(r["n"]),
         "won": int(r["won"] or 0), "avg_pnl_pct": _f(r["avg_pnl"])}
        for r in cur.fetchall()
    ]

    # 2026-06-13: UNIQUE-SYMBOL track record. The symbol-day view re-picks the
    # same name up to 7 consecutive days, so one real decline books as up to 6
    # "losses" (ORCL x6, GOOGL x5 in the 21.1% panel — 21 of 28 dedup losses
    # came from 5 underlying decisions). This block reports each symbol ONCE
    # (its picked-cohort net outcome) so the page can show decision-level truth
    # alongside symbol-day rows. Additive keys only — existing consumers unchanged.
    cur.execute(
        """
        SELECT symbol,
               COUNT(*) AS picks,
               SUM(exit_pnl_pct) AS sum_pnl,
               AVG(exit_pnl_pct) AS avg_pnl,
               SUM(exit_pnl_pct > 0) AS won_days
        FROM vw_picks_now_dedup
        WHERE exit_pnl_pct IS NOT NULL
        GROUP BY symbol
        ORDER BY sum_pnl DESC
        """
    )
    sym_rows = cur.fetchall()
    uniq_n = len(sym_rows)
    uniq_pos = sum(1 for r in sym_rows if (r["sum_pnl"] or 0) > 0)
    unique_symbols = {
        "n_symbols": uniq_n,
        "n_net_positive": uniq_pos,
        "wr_pct_by_symbol": round(100 * uniq_pos / uniq_n, 1) if uniq_n else None,
        "note": ("each symbol counted ONCE (net of all its symbol-day picks). "
                 "Decision-level WR; the headline WR above is symbol-day rows."),
        "best": [{"symbol": r["symbol"], "picks": int(r["picks"]),
                  "net_pnl_pct": _f(r["sum_pnl"])} for r in sym_rows[:5]],
        "worst": [{"symbol": r["symbol"], "picks": int(r["picks"]),
                   "net_pnl_pct": _f(r["sum_pnl"])} for r in sym_rows[-5:]],
    }
    conn.close()

    return {
        "unique_symbols": unique_symbols,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "vw_picks_now_dedup (one row per symbol per UTC day; resolver = tools/resolve_picks_now.py first-touch TP/SL, 10d TIME_EXIT)",
        "totals": {
            "symbol_days_tracked": int(t["tracked"] or 0),
            "resolved": resolved,
            "won": won,
            "lost": int(t["lost"] or 0),
            "wr_pct": round(100.0 * won / resolved, 1) if resolved else None,
            "avg_pnl_pct": round(_f(t["avg_pnl"]), 2) if t["avg_pnl"] is not None else None,
            "cum_pnl_pct": round(_f(t["cum_pnl"]), 2) if t["cum_pnl"] is not None else None,
            "first_tracked": str(t["first_tracked"]),
            "last_tracked": str(t["last_tracked"]),
        },
        "by_class": by_class,
        "resolved_picks": resolved_rows,
        "maturity_pipeline": pipeline,
        "caveats": [
            "Forward test started 2026-06-06; n is TINY — treat WR as provisional, not edge.",
            "Early-resolution bias: TP/SL touches resolve within days while TIME_EXIT losers take the full 10-day horizon, so early WR skews HIGH until the pipeline matures.",
            "Deduped: one pick per symbol per UTC day (pre-2026-06-09 duplicate rows are excluded by the view).",
            "Consecutive-day picks of the same symbol share one underlying move (e.g. one decline can resolve 3-4 symbol-days at once) — outcomes are correlated, so effective independent n is LOWER than the row count.",
            "No backtest data in this panel — every row was published on the live page BEFORE its outcome was known.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()
    payload = build()
    if args.stdout:
        print(json.dumps(payload, indent=2, default=str))
    else:
        with open(args.out, "w") as f:
            json.dump(payload, f, indent=2, default=str)
        t = payload["totals"]
        print(f"wrote {args.out}: {t['resolved']}/{t['symbol_days_tracked']} resolved, WR={t['wr_pct']}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
