#!/usr/bin/env python3
"""Re-run mutation scan on real closed picks with corrected compute_pf.

Outputs: reports/mutation_scan_honest_latest.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pymysql

from verified_strategies.mutation_framework import MutationAxis, run_full_mutation_scan


def _db_password() -> str:
    pw = os.environ.get("DB_PASS_STOCKS") or os.environ.get("AUDIT_DB_PASS")
    if pw:
        return pw.strip()
    lines = Path("/home/eaguiar2015/dbpasses.txt").read_text().splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "ejaguiar1_stocks" and i + 1 < len(lines):
            return lines[i + 1].strip()
    import os
    return os.environ.get("DB_PASS_STOCKS", "") or os.environ.get("MYSQL_PASSWORD", "")


def load_closed_trades(days: int = 180, limit: int = 50000) -> dict[str, list[dict]]:
    conn = pymysql.connect(
        host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
        user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
        password=_db_password(),
        database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
        port=3306,
        connect_timeout=30,
        cursorclass=pymysql.cursors.DictCursor,
    )
    sql = """
        SELECT
            COALESCE(NULLIF(source_system, ''), strategy, 'unknown') AS strat_key,
            symbol, direction, pnl_pct, status, created_at
        FROM trading_picks
        WHERE status IN ('WON', 'LOST', 'EXPIRED')
          AND pnl_pct IS NOT NULL AND closed_at IS NOT NULL
          AND created_at >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL %s DAY)
        ORDER BY created_at DESC
        LIMIT %s
    """
    by_strat: dict[str, list[dict]] = defaultdict(list)
    with conn.cursor() as cur:
        cur.execute(sql, (days, limit))
        for row in cur.fetchall():
            pnl = float(row["pnl_pct"] or 0)
            by_strat[row["strat_key"]].append({
                "symbol": row["symbol"],
                "direction": row.get("direction") or "LONG",
                "pnl": pnl,
                "pnl_pct": pnl,
                "status": row["status"],
            })
    conn.close()
    return dict(by_strat)


def main() -> int:
    print("[mutation-scan] loading closed trades from MySQL...")
    trades_by_strat = load_closed_trades()
    n_trades = sum(len(v) for v in trades_by_strat.values())
    print(f"[mutation-scan] {len(trades_by_strat)} strategies, {n_trades} closed rows")

    results = run_full_mutation_scan(trades_by_strat)
    invert = [r for r in results if r.axis == MutationAxis.INVERT]
    adopt = [r for r in invert if r.verdict in ("ADOPT", "CONSIDER")]

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "compute_pf": "gross_profit/gross_loss capped 99; zero-loss=0; ADOPT requires >=3 losses",
        "n_strategies_scanned": len(trades_by_strat),
        "n_trades": n_trades,
        "n_mutation_results": len(results),
        "invert_adopt_or_consider": len(adopt),
        "top_invert": [
            {
                "strategy": r.strategy_name,
                "original_pf": round(r.original_pf, 3),
                "mutated_pf": round(r.mutated_pf, 3),
                "mutated_wr": round(r.mutated_wr, 3),
                "n": r.mutated_n,
                "verdict": r.verdict,
            }
            for r in sorted(adopt, key=lambda x: x.mutated_pf, reverse=True)[:15]
        ],
        "note": "Do not ship INVERT until promotion_gate allowlist + forward proof.",
    }

    out = REPO / "reports" / "mutation_scan_honest_latest.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[mutation-scan] wrote {out}")
    print(f"[mutation-scan] INVERT adopt/consider (honest): {len(adopt)}")
    for row in payload["top_invert"][:8]:
        print(
            f"  {row['strategy'][:40]:40s} "
            f"PF {row['original_pf']:.2f} -> {row['mutated_pf']:.2f}  {row['verdict']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
