#!/usr/bin/env python3
"""Edge-stability scan: per asset class, find filters that produce edge
across MULTIPLE rolling windows (30d/60d/90d/180d).

Definition of "verified edge": PF >= 1.5 AND WR >= 55% AND n >= 30 in
EVERY window tested. Filters that survive all 4 windows = repeatable.

Backward-looking only — no forward validation. This is a "what worked
when we ran it" stability test.

Output: reports/edge_stability_2026-05-09/{class}.csv + a SUMMARY.md.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import pymysql

if sys.platform == "win32":
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            try:
                s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "reports" / "edge_stability_2026-05-09"
OUT.mkdir(parents=True, exist_ok=True)

DB = pymysql.connect(
    host=os.getenv("AUDIT_DB_HOST", "mysql.50webs.com"),
    user=os.getenv("AUDIT_DB_USER", "ejaguiar1_stocks"),
    password=os.getenv("AUDIT_DB_PASS", "stocks"),
    db=os.getenv("AUDIT_DB_NAME", "ejaguiar1_stocks"),
    connect_timeout=20, read_timeout=180, charset="utf8mb4",
)

CLOSED = "('WON','LOST','WIN','LOSS','TP_HIT','SL_HIT','CLOSED_TP','CLOSED_SL','CLOSED','EXPIRED','TIME_EXIT','FLAT','STALE')"
WIN = "('WON','WIN','TP_HIT','CLOSED_TP')"
WINDOWS = [30, 60, 90, 180]

ASSET_CLASSES = ['crypto', 'commodity', 'equity', 'forex', 'futures', 'etf']

THRESHOLDS = dict(min_n=30, min_wr=55.0, min_pf=1.5)

# Filter dimensions to test
FILTERS = {
    "confidence_band": [
        ("conf_lt_50", "AND confidence < 0.50"),
        ("conf_50_60", "AND confidence >= 0.50 AND confidence < 0.60"),
        ("conf_60_70", "AND confidence >= 0.60 AND confidence < 0.70"),
        ("conf_70_80", "AND confidence >= 0.70 AND confidence < 0.80"),
        ("conf_80_90", "AND confidence >= 0.80 AND confidence < 0.90"),
        ("conf_gte_90", "AND confidence >= 0.90"),
    ],
    "elite_score": [
        ("elite_lt_30",  "AND elite_score < 30"),
        ("elite_30_50",  "AND elite_score >= 30 AND elite_score < 50"),
        ("elite_50_70",  "AND elite_score >= 50 AND elite_score < 70"),
        ("elite_gte_70", "AND elite_score >= 70"),
    ],
    "trust_score": [
        ("trust_lt_5",  "AND trust_score < 5"),
        ("trust_5",     "AND trust_score = 5"),
        ("trust_6",     "AND trust_score = 6"),
        ("trust_7",     "AND trust_score = 7"),
        ("trust_8plus", "AND trust_score >= 8"),
    ],
    "direction": [
        ("LONG",  "AND direction IN ('LONG','BUY')"),
        ("SHORT", "AND direction IN ('SHORT','SELL')"),
    ],
    "hour_of_day_utc": [
        (f"h{h:02d}", f"AND HOUR(created_at) = {h}") for h in (0, 4, 8, 12, 14, 16, 18, 20, 22)
    ],
    "hold_bucket": [
        ("h_lt_2",   "AND TIMESTAMPDIFF(HOUR,created_at,closed_at) BETWEEN 1 AND 2"),
        ("h_2_8",    "AND TIMESTAMPDIFF(HOUR,created_at,closed_at) > 2 AND TIMESTAMPDIFF(HOUR,created_at,closed_at) <= 8"),
        ("h_8_24",   "AND TIMESTAMPDIFF(HOUR,created_at,closed_at) > 8 AND TIMESTAMPDIFF(HOUR,created_at,closed_at) <= 24"),
        ("h_24_72",  "AND TIMESTAMPDIFF(HOUR,created_at,closed_at) > 24 AND TIMESTAMPDIFF(HOUR,created_at,closed_at) <= 72"),
        ("h_72plus", "AND TIMESTAMPDIFF(HOUR,created_at,closed_at) > 72"),
    ],
}


def query_filter_window(asset_class: str, days: int, filter_clause: str):
    """Return (n, wr, pf, sum_pnl) for one filter+window+class."""
    cur = DB.cursor()
    sql = f"""
        SELECT
          COUNT(*) AS n,
          SUM(CASE WHEN status IN {WIN} THEN 1 ELSE 0 END) AS wins,
          SUM(GREATEST(pnl_pct, 0))                       AS gross_w,
          SUM(GREATEST(-pnl_pct, 0))                      AS gross_l,
          SUM(pnl_pct)                                    AS sum_pnl
        FROM trading_picks
        WHERE status IN {CLOSED}
          AND closed_at >= NOW() - INTERVAL {days} DAY
          AND category = '{asset_class}'
          AND pnl_pct IS NOT NULL
          AND pnl_pct BETWEEN -50 AND 50
          {filter_clause}
    """
    cur.execute(sql)
    row = cur.fetchone()
    cur.close()
    n, wins, gw, gl, sum_pnl = row
    if not n or n == 0:
        return None
    wr = (wins or 0) / n * 100
    pf = (float(gw or 0) / float(gl)) if gl and float(gl) > 0 else 999.0
    return {"n": n, "wins": wins or 0, "wr": round(wr, 2),
            "pf": round(pf, 2), "sum_pnl": round(float(sum_pnl or 0), 2)}


def stable_edge(results: dict) -> bool:
    """All windows must pass thresholds."""
    for w in WINDOWS:
        r = results.get(w)
        if not r:
            return False
        if r["n"] < THRESHOLDS["min_n"]:
            return False
        if r["wr"] < THRESHOLDS["min_wr"]:
            return False
        if r["pf"] < THRESHOLDS["min_pf"]:
            return False
    return True


def main():
    summary_rows = []
    for ac in ASSET_CLASSES:
        print(f"\n=== {ac.upper()} edge-stability scan ===")
        ac_rows = []

        # Baseline (no filter, just class)
        print(f"  baseline (no filter):")
        baseline = {}
        for w in WINDOWS:
            r = query_filter_window(ac, w, "")
            baseline[w] = r
            if r:
                print(f"    {w:>3}d: n={r['n']:>5} WR={r['wr']:>5.1f}% PF={r['pf']:>5.2f} sum={r['sum_pnl']:>+8.1f}")
        ac_rows.append({
            "filter_dim": "baseline", "filter_value": "all",
            **{f"{w}d_n": baseline[w]["n"] if baseline[w] else 0 for w in WINDOWS},
            **{f"{w}d_wr": baseline[w]["wr"] if baseline[w] else 0 for w in WINDOWS},
            **{f"{w}d_pf": baseline[w]["pf"] if baseline[w] else 0 for w in WINDOWS},
            "stable_edge": stable_edge(baseline),
        })

        # Each filter
        for dim_name, filter_list in FILTERS.items():
            for fname, fclause in filter_list:
                results = {}
                for w in WINDOWS:
                    r = query_filter_window(ac, w, fclause)
                    results[w] = r
                stable = stable_edge(results)
                row = {
                    "filter_dim": dim_name, "filter_value": fname,
                    **{f"{w}d_n": results[w]["n"] if results[w] else 0 for w in WINDOWS},
                    **{f"{w}d_wr": results[w]["wr"] if results[w] else 0 for w in WINDOWS},
                    **{f"{w}d_pf": results[w]["pf"] if results[w] else 0 for w in WINDOWS},
                    "stable_edge": stable,
                }
                ac_rows.append(row)
                if stable:
                    print(f"  ✓ STABLE  {dim_name}={fname}  "
                          + ", ".join(f"{w}d:n={results[w]['n']}/WR={results[w]['wr']}/PF={results[w]['pf']}" for w in WINDOWS))

        # Save per-class CSV
        csv_path = OUT / f"{ac}_filter_stability.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            cols = ["filter_dim", "filter_value"]
            for w in WINDOWS:
                cols += [f"{w}d_n", f"{w}d_wr", f"{w}d_pf"]
            cols.append("stable_edge")
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for r in ac_rows:
                w.writerow(r)
        # Add stable edges to summary
        for r in ac_rows:
            if r["stable_edge"]:
                summary_rows.append({"asset_class": ac, **r})

    # Source-system edge per class (fan-out separately because too many to enum)
    print("\n=== SOURCE-SYSTEM PER-CLASS EDGE ===")
    cur = DB.cursor()
    for ac in ASSET_CLASSES:
        for w in WINDOWS:
            cur.execute(f"""
              SELECT source_system, COUNT(*) n,
                ROUND(SUM(CASE WHEN status IN {WIN} THEN 1 ELSE 0 END)/COUNT(*)*100,1) wr,
                ROUND(SUM(GREATEST(pnl_pct,0))/NULLIF(SUM(GREATEST(-pnl_pct,0)),0),2) pf,
                ROUND(SUM(pnl_pct),1) sum_pnl
              FROM trading_picks
              WHERE status IN {CLOSED}
                AND closed_at >= NOW() - INTERVAL {w} DAY
                AND category='{ac}'
                AND pnl_pct BETWEEN -50 AND 50
              GROUP BY source_system HAVING n >= {THRESHOLDS['min_n']}
                AND wr >= {THRESHOLDS['min_wr']} AND pf >= {THRESHOLDS['min_pf']}
              ORDER BY pf DESC
            """)
            for r in cur.fetchall():
                src, n, wr, pf, sum_pnl = r
                summary_rows.append({
                    "asset_class": ac, "filter_dim": "source_system",
                    "filter_value": src, f"{w}d_n": n, f"{w}d_wr": float(wr),
                    f"{w}d_pf": float(pf or 0), "stable_edge": "single_window",
                    "window": w, "sum_pnl": float(sum_pnl or 0),
                })
    cur.close()

    # Save summary JSON
    with open(OUT / "_stable_edges.json", "w", encoding="utf-8") as fh:
        json.dump(summary_rows, fh, indent=2, default=str)
    print(f"\nDone. Output: {OUT}")
    DB.close()


if __name__ == "__main__":
    main()
