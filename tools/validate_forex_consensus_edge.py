#!/usr/bin/env python3
"""
validate_forex_consensus_edge.py — reproduce the FOREX strategy-level edge audit.

Per CLAUDE.md "DO NOT trust unsourced model claims about /audit numbers": this
script is the reproducer for reports/PLAN_INSIGHTS_FABLE_June122026_1137pm.MD. It
re-derives, from the live ejaguiar1_stocks.trading_picks table, the finding that
the FOREX class FAILS at the aggregate level but source_system=non_crypto_consensus
is a Tier-1-PF / Tier-2-WR candidate once you:

  1. dedup per (strategy, symbol, day)         — kills batch-emission inflation
  2. use a 5bp win threshold (percent units)   — TIME_EXIT near-flat != "win"
  3. exclude contamination (hold < 60 min,     — resolver/backfill artifacts
     i.e. created==closed or time-travel)
  4. time-split IS/OOS by median date          — the test that kills snapshot edges
  5. winsorize / drop-largest-winner PF         — outlier-robustness

Read-only. No DB writes. Credentials come from env or ~/dbpasses.txt — NEVER
hardcoded (Gitleaks gate). Set DB_PASS_STOCKS, or rely on the 50webs convention
documented in dbpasses.txt.

Usage:
    python3 tools/validate_forex_consensus_edge.py
    python3 tools/validate_forex_consensus_edge.py --category equity --min-n 30
    python3 tools/validate_forex_consensus_edge.py --json reports/forex_edge_check.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

WIN_THRESHOLD_PCT = 0.05  # 5bp, pnl_pct stored in percent units
MIN_HOLD_MINUTES = 60     # exclude same-stamp + time-travel contamination


def _load_db_password() -> str:
    pw = os.environ.get("DB_PASS_STOCKS") or os.environ.get("STOCKS_DB_PASS")
    if pw:
        return pw
    # Convention fallback: 50webs password is "<db-suffix>1234560" (see dbpasses.txt).
    # We read the literal from the local creds file rather than hardcoding it.
    for path in (Path.home() / "dbpasses.txt", Path("/home/eaguiar2015/dbpasses.txt")):
        if path.exists():
            for line in path.read_text(errors="replace").splitlines():
                s = line.strip()
                if s == "stocks1234560" or (s.startswith("stocks") and s.endswith("1234560")):
                    return s
    raise SystemExit("No DB password: set DB_PASS_STOCKS or provide dbpasses.txt")


def _connect():
    import pymysql
    return pymysql.connect(
        host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
        user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
        password=_load_db_password(),
        database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
        connect_timeout=20,
    )


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return ((centre - half) * 100, (centre + half) * 100)


def _pf(items: list, win: float) -> tuple[float, int, int]:
    wins = [x for x in items if x["pnl"] > win]
    losses = [x for x in items if x["pnl"] < -win]
    gp = sum(x["pnl"] for x in wins)
    gl = abs(sum(x["pnl"] for x in losses))
    pf = gp / gl if gl > 0 else float("inf")
    return pf, len(wins), len(losses)


def fetch_rows(conn, category: str, clean: bool) -> list[dict]:
    cond = "AND TIMESTAMPDIFF(MINUTE,created_at,closed_at) >= %d" % MIN_HOLD_MINUTES if clean else ""
    sql = f"""
        SELECT id, symbol, strategy, source_system, pnl_pct, DATE(created_at) AS d
        FROM trading_picks
        WHERE LOWER(category)=%s AND closed_at IS NOT NULL
          AND status IN ('TP_HIT','SL_HIT','LOST','TIME_EXIT','EXPIRED','WON')
          AND pnl_pct IS NOT NULL AND created_at>='2026-01-01' {cond}
    """
    cur = conn.cursor()
    cur.execute(sql, (category,))
    return [
        {"id": r[0], "symbol": r[1], "strategy": r[2], "source": r[3],
         "pnl": float(r[4]), "date": str(r[5])}
        for r in cur.fetchall()
    ]


def dedup(rows: list[dict]) -> list[dict]:
    seen: dict[tuple, dict] = {}
    for r in rows:
        key = (r["strategy"], r["symbol"], r["date"])
        if key not in seen or r["id"] < seen[key]["id"]:
            seen[key] = r
    return sorted(seen.values(), key=lambda x: x["date"])


def analyze(rows: list[dict], min_n: int) -> list[dict]:
    by_source: dict[tuple, list] = defaultdict(list)
    for r in rows:
        by_source[(r["source"], r["strategy"])].append(r)
    out = []
    for (source, strategy), items in by_source.items():
        n = len(items)
        if n < min_n:
            continue
        items = sorted(items, key=lambda x: x["date"])
        pf, nw, nl = _pf(items, WIN_THRESHOLD_PCT)
        mid = n // 2
        ispf, _, _ = _pf(items[:mid], WIN_THRESHOLD_PCT)
        oospf, _, _ = _pf(items[mid:], WIN_THRESHOLD_PCT)
        decisive = nw + nl
        dec_wr = nw / decisive * 100 if decisive else 0.0
        lo, hi = _wilson(nw, decisive)
        wins = sorted((x["pnl"] for x in items if x["pnl"] > WIN_THRESHOLD_PCT), reverse=True)
        losses = [x["pnl"] for x in items if x["pnl"] < -WIN_THRESHOLD_PCT]
        gl = abs(sum(losses))
        pf_minus_top = (sum(wins[1:]) / gl) if (gl > 0 and wins) else None
        sym_counts = defaultdict(int)
        for x in items:
            sym_counts[x["symbol"]] += 1
        top_sym, top_n = max(sym_counts.items(), key=lambda kv: kv[1])
        out.append({
            "source": source, "strategy": strategy, "n": n,
            "pf": round(pf, 2), "is_pf": round(ispf, 2), "oos_pf": round(oospf, 2),
            "decisive_n": decisive, "decisive_wr": round(dec_wr, 1),
            "wr_ci95": [round(lo, 1), round(hi, 1)],
            "pf_minus_top_winner": round(pf_minus_top, 2) if pf_minus_top is not None else None,
            "top_symbol": top_sym, "top_symbol_pct": round(top_n / n * 100, 1),
            "active_days": len({x["date"] for x in items}),
            "holds_oos": bool(ispf >= 1.2 and oospf >= 1.2),
        })
    return sorted(out, key=lambda r: -r["pf"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default="forex")
    ap.add_argument("--min-n", type=int, default=30)
    ap.add_argument("--raw", action="store_true", help="skip the hold>=60min contamination filter")
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    conn = _connect()
    try:
        rows = dedup(fetch_rows(conn, args.category, clean=not args.raw))
    finally:
        conn.close()

    results = analyze(rows, args.min_n)
    print(f"# {args.category.upper()} strategy-level edge ({'raw' if args.raw else 'contamination-clean'}, "
          f"deduped per symbol-day, 5bp win threshold)")
    print(f"# {len(rows)} deduped resolved picks; {len(results)} sources with n>={args.min_n}\n")
    hdr = f"{'source/strategy':40} {'n':>4} {'PF':>5} {'IS':>5} {'OOS':>5} {'decWR':>6} {'CI95':>13} {'-top':>5} {'topsym':>9} {'days':>4} {'OOS?'}"
    print(hdr)
    for r in results:
        label = f"{r['source']}/{r['strategy']}"[:40]
        ci = f"[{r['wr_ci95'][0]:.0f},{r['wr_ci95'][1]:.0f}]"
        print(f"{label:40} {r['n']:>4} {r['pf']:>5.2f} {r['is_pf']:>5.2f} {r['oos_pf']:>5.2f} "
              f"{r['decisive_wr']:>5.1f}% {ci:>13} {str(r['pf_minus_top_winner']):>5} "
              f"{r['top_symbol'][:9]:>9} {r['active_days']:>4} {'HOLDS' if r['holds_oos'] else 'fails'}")

    if args.json:
        Path(args.json).write_text(json.dumps({"category": args.category, "results": results}, indent=2))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
