#!/usr/bin/env python3
"""Dedup INCIDENT #91-style row inflation on `ejaguiar1_stocks.trading_picks`.

Background
----------
INCIDENT #91 first surfaced on `at_signal_outcomes` (Cursor's 2026-06-05 session
dedup'd 242,427 -> 2,467 rows). The same inflation pattern was confirmed on
`trading_picks` for `mega_mutation` (2.72x ratio: 296 raw -> 109 deduped).
See reports/MEGA_MUTATION_BRIDGE_CANDIDATE_2026-06-05.md.

Signature of an inflated row group
-----------------------------------
  (symbol, direction, entry_price, take_profit, stop_loss, DATE(closed_at))
  is the natural composite key. Within a group, multiple rows share identical
  entry/TP/SL/pnl but differ only by `id` + `closed_at` minute. `created_at` is
  often NULL on the dupes -- a strong synthetic-replay signal.

Safety
------
Dry-run by default. `--apply` requires `--confirm INCIDENT_91_TRADING_PICKS`.
Archive of to-be-deleted rows is written to a local JSON slice under
reports/db_archive_slices/ before any DELETE. (50webs ejaguiar1_stocks lacks
CREATE on ejaguiar1_backups so cross-DB archive is unreliable -- the local
JSON is the rollback source of truth.) See pr-reviewer finding on PR #537.

Author: claude-opus-4-7 /loop blitz 2026-06-05
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import pymysql  # noqa: E402
from tools.db_env import get_stocks_creds  # noqa: E402

ARCHIVE_DIR = REPO / "reports" / "db_archive_slices"
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

DEDUP_KEY_SQL = "symbol, direction, entry_price, take_profit, stop_loss, DATE(closed_at)"

# Hard cap: refuse to delete > N rows without an explicit second confirmation
MAX_DELETE_HARD_CAP = 200_000


def _dec(x):
    return float(x) if isinstance(x, Decimal) else x


def _connect():
    return pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)


def survey(strategy: str | None) -> dict:
    """Count inflation per strategy (or whole table if strategy is None)."""
    where = "closed_at IS NOT NULL AND pnl_pct IS NOT NULL"
    params: tuple = ()
    if strategy:
        where += " AND (strategy=%s OR source_system=%s)"
        params = (strategy, strategy)

    with _connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT COUNT(*) raw_n,
                   COUNT(DISTINCT {DEDUP_KEY_SQL}) uniq_n
            FROM trading_picks WHERE {where}
        """, params)
        r = cur.fetchone()
        raw_n = int(r["raw_n"])
        uniq_n = int(r["uniq_n"])
        ratio = raw_n / uniq_n if uniq_n else 0
        to_delete = raw_n - uniq_n

        # Top 10 inflation groups
        cur.execute(f"""
            SELECT symbol, direction, entry_price, take_profit, stop_loss,
                   DATE(closed_at) d, COUNT(*) c
            FROM trading_picks WHERE {where}
            GROUP BY {DEDUP_KEY_SQL}
            HAVING c > 1
            ORDER BY c DESC
            LIMIT 10
        """, params)
        top_groups = []
        for row in cur.fetchall():
            top_groups.append({
                "symbol": row["symbol"],
                "direction": row["direction"],
                "entry_price": _dec(row["entry_price"]),
                "take_profit": _dec(row["take_profit"]),
                "stop_loss": _dec(row["stop_loss"]),
                "date": str(row["d"]),
                "row_count": int(row["c"]),
            })

    return {
        "scope": strategy or "ALL strategies",
        "raw_n": raw_n,
        "uniq_n": uniq_n,
        "to_delete": to_delete,
        "inflation_ratio": round(ratio, 3),
        "top_inflation_groups": top_groups,
    }


def archive_slice(strategy: str | None) -> Path:
    """Snapshot all rows that would be deleted (rn>1) to a local JSON archive."""
    where = "closed_at IS NOT NULL AND pnl_pct IS NOT NULL"
    params: tuple = ()
    if strategy:
        where += " AND (strategy=%s OR source_system=%s)"
        params = (strategy, strategy)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = (strategy or "ALL").replace("/", "_")
    out = ARCHIVE_DIR / f"trading_picks_dedup_incident_91__{safe}__{ts}.json"

    with _connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT * FROM (
              SELECT *, ROW_NUMBER() OVER (
                PARTITION BY symbol, direction, entry_price, take_profit, stop_loss, DATE(closed_at)
                ORDER BY closed_at ASC, id ASC
              ) rn
              FROM trading_picks WHERE {where}
            ) t WHERE rn > 1
        """, params)
        rows = []
        for r in cur.fetchall():
            rows.append({k: (_dec(v) if isinstance(v, Decimal) else str(v) if hasattr(v, "isoformat") else v) for k, v in r.items()})

    out.write_text(json.dumps({"generated_at": ts, "scope": strategy or "ALL", "row_count": len(rows), "rows": rows}, indent=2, default=str))
    return out


def apply_delete(strategy: str | None) -> int:
    """Delete rn>1 rows. Returns affected count."""
    where = "closed_at IS NOT NULL AND pnl_pct IS NOT NULL"
    params: tuple = ()
    if strategy:
        where += " AND (strategy=%s OR source_system=%s)"
        params = (strategy, strategy)

    with _connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            DELETE FROM trading_picks WHERE id IN (
              SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (
                  PARTITION BY symbol, direction, entry_price, take_profit, stop_loss, DATE(closed_at)
                  ORDER BY closed_at ASC, id ASC
                ) rn
                FROM trading_picks WHERE {where}
              ) t WHERE rn > 1
            )
        """, params)
        n = cur.rowcount
        conn.commit()
        return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Dedup INCIDENT #91-style inflation on trading_picks")
    ap.add_argument("--strategy", help="Limit to one strategy/source_system (default: ALL)")
    ap.add_argument("--apply", action="store_true", help="Execute the DELETE (default: dry-run survey only)")
    ap.add_argument("--confirm", help="Required with --apply. Must equal INCIDENT_91_TRADING_PICKS")
    args = ap.parse_args()

    survey_out = survey(args.strategy)
    print(json.dumps({"phase": "survey", **survey_out}, indent=2))

    if not args.apply:
        print("\nDry-run only. Re-run with --apply --confirm INCIDENT_91_TRADING_PICKS to execute.")
        return 0

    if args.confirm != "INCIDENT_91_TRADING_PICKS":
        print("\nERROR: --apply requires --confirm INCIDENT_91_TRADING_PICKS", file=sys.stderr)
        return 2

    if survey_out["to_delete"] > MAX_DELETE_HARD_CAP:
        print(f"\nERROR: to_delete={survey_out['to_delete']} exceeds hard cap {MAX_DELETE_HARD_CAP}. "
              f"Re-run scoped to --strategy <name> or raise the cap manually.", file=sys.stderr)
        return 3

    archive = archive_slice(args.strategy)
    print(f"\nArchived to-be-deleted rows -> {archive}")

    n = apply_delete(args.strategy)
    print(f"\nDeleted {n} duplicate rows from trading_picks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
