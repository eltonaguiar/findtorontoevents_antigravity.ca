#!/usr/bin/env python3
"""Verify multi_asset_cot PF/WR claim against raw DB.

Dashboard payload claims multi_asset_cot system: PF 21.86, WR 94.1%, n=102
(per audit_dashboard/data/dashboard_data.json::systems[name=multi_asset_cot]).

This number is implausibly high. Similar pattern to kimi_signal_tracking
PF reversal earlier in session (resolver-denominator quirk: 1174 closed vs
18 resolved-valid).

Goal: query ejaguiar1_stocks.picks joined to outcomes directly, compute
raw PF/WR/MDD from CLOSED rows with EXIT_REASON in (TP, SL, TIME). Compare
to dashboard payload. Identify any resolver-induced inflation.

Spawned 2026-05-13 per swarm 4/4 consensus: Option C (standalone verifier
bypasses cron concurrency issues, gives immediate DB truth without touching
production workflow).

Requires DB_PASS_STOCKS env var. Run:
  DB_PASS_STOCKS=<pwd> python tools/verify_multi_asset_cot_db.py
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import pymysql
except ImportError:
    print("ERROR: pymysql not installed. Run: pip install pymysql", file=sys.stderr)
    sys.exit(2)

from tools.db_env import get_stocks_creds


def query_multi_asset_cot(conn) -> dict:
    """Run multi-query forensic on multi_asset_cot picks."""
    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "queries": {},
    }
    with conn.cursor() as cur:
        # Q1: Total row count by status
        try:
            cur.execute("""
                SELECT status, COUNT(*) AS n
                FROM picks
                WHERE source_system = 'multi_asset_cot'
                GROUP BY status
                ORDER BY n DESC
            """)
            rows = cur.fetchall()
            results["queries"]["status_breakdown"] = [
                {"status": r[0], "n": r[1]} for r in rows
            ]
        except pymysql.Error as exc:
            results["queries"]["status_breakdown"] = {"error": str(exc)}

        # Q2: PnL distribution for closed picks (terminal status only)
        try:
            cur.execute("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN pnl_pct < 0 THEN 1 ELSE 0 END) AS losses,
                    SUM(CASE WHEN pnl_pct = 0 OR pnl_pct IS NULL THEN 1 ELSE 0 END) AS zero_flat,
                    SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) AS gross_win,
                    SUM(CASE WHEN pnl_pct < 0 THEN ABS(pnl_pct) ELSE 0 END) AS gross_loss,
                    AVG(pnl_pct) AS avg_pnl,
                    MAX(pnl_pct) AS max_pnl,
                    MIN(pnl_pct) AS min_pnl
                FROM picks
                WHERE source_system = 'multi_asset_cot'
                  AND status IN ('CLOSED', 'TP', 'SL', 'TIME_EXIT', 'STOPPED_OUT')
            """)
            row = cur.fetchone()
            if row:
                total, wins, losses, zero_flat, gw, gl, avg, mx, mn = row
                results["queries"]["raw_outcome"] = {
                    "total": int(total or 0),
                    "wins": int(wins or 0),
                    "losses": int(losses or 0),
                    "zero_flat": int(zero_flat or 0),
                    "gross_win_pct": float(gw or 0),
                    "gross_loss_pct": float(gl or 0),
                    "avg_pnl_pct": float(avg) if avg else None,
                    "max_pnl_pct": float(mx) if mx else None,
                    "min_pnl_pct": float(mn) if mn else None,
                }
                if (wins or 0) + (losses or 0) > 0:
                    results["queries"]["raw_outcome"]["wr_pct"] = round(
                        int(wins) / (int(wins) + int(losses)) * 100, 2
                    )
                if (gl or 0) > 0:
                    results["queries"]["raw_outcome"]["pf"] = round(
                        float(gw) / float(gl), 4
                    )
        except pymysql.Error as exc:
            results["queries"]["raw_outcome"] = {"error": str(exc)}

        # Q3: Per-symbol breakdown to spot concentration / placeholder patterns
        try:
            cur.execute("""
                SELECT
                    symbol,
                    COUNT(*) AS n,
                    SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN pnl_pct < 0 THEN 1 ELSE 0 END) AS losses,
                    AVG(pnl_pct) AS avg_pnl,
                    STDDEV(pnl_pct) AS std_pnl,
                    COUNT(DISTINCT pnl_pct) AS distinct_pnl_values
                FROM picks
                WHERE source_system = 'multi_asset_cot'
                  AND status IN ('CLOSED', 'TP', 'SL', 'TIME_EXIT', 'STOPPED_OUT')
                GROUP BY symbol
                ORDER BY n DESC
                LIMIT 30
            """)
            rows = cur.fetchall()
            results["queries"]["per_symbol"] = [
                {
                    "symbol": r[0], "n": int(r[1]),
                    "wins": int(r[2] or 0), "losses": int(r[3] or 0),
                    "avg_pnl_pct": float(r[4]) if r[4] is not None else None,
                    "std_pnl_pct": float(r[5]) if r[5] is not None else None,
                    "distinct_pnl_values": int(r[6] or 0),
                }
                for r in rows
            ]
        except pymysql.Error as exc:
            results["queries"]["per_symbol"] = {"error": str(exc)}

        # Q4: Ghost-row detection (constant pnl_pct = placeholder signature)
        try:
            cur.execute("""
                SELECT
                    symbol, ROUND(pnl_pct, 4) AS rounded_pnl,
                    COUNT(*) AS n
                FROM picks
                WHERE source_system = 'multi_asset_cot'
                  AND status IN ('CLOSED', 'TP', 'SL', 'TIME_EXIT', 'STOPPED_OUT')
                  AND pnl_pct IS NOT NULL
                GROUP BY symbol, ROUND(pnl_pct, 4)
                HAVING COUNT(*) >= 5
                ORDER BY n DESC
                LIMIT 20
            """)
            rows = cur.fetchall()
            results["queries"]["potential_ghosts"] = [
                {"symbol": r[0], "pnl_pct": float(r[1]), "n_identical": int(r[2])}
                for r in rows
            ]
        except pymysql.Error as exc:
            results["queries"]["potential_ghosts"] = {"error": str(exc)}

        # Q5: Date range
        try:
            cur.execute("""
                SELECT MIN(created_at), MAX(created_at), COUNT(*)
                FROM picks
                WHERE source_system = 'multi_asset_cot'
            """)
            row = cur.fetchone()
            if row:
                results["queries"]["date_range"] = {
                    "earliest": str(row[0]) if row[0] else None,
                    "latest": str(row[1]) if row[1] else None,
                    "total": int(row[2] or 0),
                }
        except pymysql.Error as exc:
            results["queries"]["date_range"] = {"error": str(exc)}

    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default="reports/multi_asset_cot_db_verify.json")
    p.add_argument("--dry-run", action="store_true",
                   help="Print SQL queries only, do not connect")
    args = p.parse_args()

    if args.dry_run:
        print("# DRY RUN — would query:")
        print("# Q1: status breakdown for source_system=multi_asset_cot")
        print("# Q2: aggregate PF/WR from CLOSED rows")
        print("# Q3: per-symbol breakdown (concentration check)")
        print("# Q4: ghost-row detection (constant pnl_pct signatures)")
        print("# Q5: date range")
        print("\n# Run without --dry-run + DB_PASS_STOCKS env to execute.")
        return

    try:
        creds = get_stocks_creds()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("\nSet DB_PASS_STOCKS env var (or one of the legacy fallbacks).",
              file=sys.stderr)
        sys.exit(3)

    print(f"# connecting to {creds['host']}:{creds['port']} db={creds['database']}",
          file=sys.stderr)
    try:
        conn = pymysql.connect(**creds)
    except pymysql.Error as exc:
        print(f"ERROR: connection failed: {exc}", file=sys.stderr)
        sys.exit(4)

    try:
        results = query_multi_asset_cot(conn)
    finally:
        conn.close()

    # Compare to dashboard payload claim
    try:
        dash = json.load(open("audit_dashboard/data/dashboard_data.json", encoding="utf-8"))
        for s in dash.get("systems", []):
            if s.get("name") == "multi_asset_cot":
                results["dashboard_payload_claim"] = {
                    "closed_picks": s.get("closed_picks"),
                    "resolved_picks": s.get("resolved_picks"),
                    "win_rate": s.get("win_rate"),
                    "profit_factor": s.get("profit_factor"),
                    "total_pnl_pct": s.get("total_pnl_pct"),
                }
                break
    except Exception:
        pass

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"# wrote {out_path}", file=sys.stderr)
    raw = results["queries"].get("raw_outcome", {})
    if isinstance(raw, dict) and "wr_pct" in raw:
        print(f"\n## DB RAW: total={raw.get('total')} wins={raw.get('wins')} "
              f"losses={raw.get('losses')} zero_flat={raw.get('zero_flat')}")
        print(f"## DB RAW WR={raw.get('wr_pct')}% PF={raw.get('pf')}")
        print(f"## DASH CLAIM: WR={results.get('dashboard_payload_claim', {}).get('win_rate')}% "
              f"PF={results.get('dashboard_payload_claim', {}).get('profit_factor')}")


if __name__ == "__main__":
    main()
