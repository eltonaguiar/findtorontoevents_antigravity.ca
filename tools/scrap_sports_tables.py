#!/usr/bin/env python3
"""Drop the scrapped sports-betting tables from `ejaguiar1_stocks`.

2026-11-28 — sports betting is scrapped for now, but its tables still occupied
the stocks DB (the PHP live-monitor APIs and the `sports-betting-refresh`
workflow wrote them). This tool removes them, and does it the way every other
destructive step in this repo is done: snapshot first, verify the snapshot row
count equals the source, only then DROP.

Safety
  * Dry-run by DEFAULT. `--apply` required to change anything.
  * Every table is cloned into `ejaguiar1_backups` as
    `stocks_sports_drop_<stamp>__<table>` (schemas cleaned with the same
    `clean_ddl()` the label backfill uses: FK stripped, constraint names
    suffixed so two snapshots cannot collide).
  * The DROP only runs for a table whose snapshot committed exactly
    `COUNT(*)` rows. Any mismatch aborts that table and leaves it in place.
  * Refuses to run if any table is referenced by a foreign key, so an
    unrelated table cannot be silently broken.

Not touched on purpose: `sp_*` (smart picks) and `ss_*` (smart signals) match a
"sport"-ish shape but are crypto/equity scanners — they stay. `lm_scraped_data`
is equity options / short-interest cache — it stays too.

Usage
  python3 tools/scrap_sports_tables.py            # dry-run: list + row counts
  python3 tools/scrap_sports_tables.py --apply    # snapshot, verify, drop
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pymysql

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.backfill_unknown_category import clean_ddl  # noqa: E402
from tools.db_env import get_backups_creds, get_stocks_creds  # noqa: E402

# table -> why it is sports betting
SPORTS_TABLES: dict[str, str] = {
    "lm_sports_clv": "closing-line value ledger",
    "lm_sports_odds": "bookmaker odds feed",
    "lm_sports_value_bets": "+EV bet proposals",
    "lm_sports_daily_picks": "daily sports picks",
    "lm_sports_credit_usage": "The Odds API credit meter",
    "lm_sports_ml_predictions": "sports ML predictions",
    "lm_sports_ml_metrics": "sports ML metrics",
    "lm_sports_bets": "placed paper bets",
    "lm_sports_bankroll": "paper bankroll curve",
    "lm_nba_team_stats": "NBA team stats",
    "lm_nba_games_today": "NBA schedule cache",
    "lm_nba_stats_cache": "NBA stats cache",
    "lm_nfl_stats_cache": "NFL stats cache",
    "lm_mlb_stats_cache": "MLB stats cache",
    "lm_nhl_stats_cache": "NHL stats cache",
    "lm_injury_intel_cache": "NBA/MLB/NHL injury intel",
    "lm_schedule_intel_cache": "NBA/MLB/NHL rest/schedule intel",
}

_KEEP = (
    "sp_picks", "sp_batches", "sp_daily_performance",   # smart picks (crypto/equity)
    "ss_baselines", "ss_spikes",                        # smart signals
    "lm_scraped_data",                                  # equity options cache
)


def _conn(creds: dict, dict_rows: bool = False):
    keep = ("host", "user", "password", "database", "port")
    kwargs = {k: v for k, v in creds.items() if k in keep}
    kwargs["connect_timeout"] = 30
    kwargs["read_timeout"] = 300
    if dict_rows:
        kwargs["cursorclass"] = pymysql.cursors.DictCursor
    return pymysql.connect(**kwargs)


def count(cur, table: str) -> int:
    cur.execute(f"SELECT COUNT(*) AS n FROM `{table}`")
    row = cur.fetchone()
    return int(row["n"] if isinstance(row, dict) else row[0])


def fk_refs(cur, database: str, tables: list[str]) -> list[tuple]:
    cur.execute(
        """SELECT table_name, constraint_name, referenced_table_name
           FROM information_schema.key_column_usage
           WHERE table_schema=%s AND referenced_table_name IN %s""",
        (database, tables),
    )
    return list(cur.fetchall())


def snapshot(scur, bconn, table: str, stamp: str) -> tuple[str, int, int]:
    """Clone `table` into backups. Returns (backup_name, expected, copied)."""
    name = f"stocks_sports_drop_{stamp}__{table}"[:64]
    scur.execute(f"SHOW CREATE TABLE `{table}`")
    ddl = clean_ddl(scur.fetchone()["Create Table"], table, name, stamp)

    bcur = bconn.cursor()
    bcur.execute(f"DROP TABLE IF EXISTS `{name}`")
    bcur.execute(ddl)
    bconn.commit()

    scur.execute(f"SELECT * FROM `{table}`")
    cols = [d[0] for d in scur.description]
    rows = scur.fetchall()
    if rows:
        ins = (f"INSERT INTO `{name}` (`" + "`,`".join(cols) + "`) VALUES ("
               + ",".join(["%s"] * len(cols)) + ")")
        payload = [tuple(r[c] for c in cols) for r in rows]
        for i in range(0, len(payload), 500):
            bcur.executemany(ins, payload[i:i + 500])
            bconn.commit()
    bcur.execute(f"SELECT COUNT(*) FROM `{name}`")
    copied = int(bcur.fetchone()[0])
    return name, len(rows), copied


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Drop the scrapped sports tables from ejaguiar1_stocks "
                    "(dry-run default).")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    sconn = _conn(get_stocks_creds(), dict_rows=True)
    scur = sconn.cursor()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")

    scur.execute("SELECT DATABASE() AS db")
    database = scur.fetchone()["db"]

    present: list[str] = []
    missing: list[str] = []
    counts: dict[str, int] = {}
    for table in SPORTS_TABLES:
        try:
            counts[table] = count(scur, table)
            present.append(table)
        except pymysql.Error:
            missing.append(table)

    print(f"target DB: {database}")
    print(f"present: {len(present)}   already absent: {len(missing)}")
    for t in present:
        print(f"  {t:<28} {counts[t]:>8,} rows  — {SPORTS_TABLES[t]}")
    for t in missing:
        print(f"  {t:<28} {'ABSENT':>8}      — {SPORTS_TABLES[t]}")
    print("\nkept on purpose:", ", ".join(_KEEP))

    refs = fk_refs(scur, database, present) if present else []
    if refs:
        print("\nREFUSING: foreign keys reference scrapped tables:")
        for r in refs:
            print("  ", r)
        return 2

    if not args.apply:
        total = sum(counts.values())
        print(f"\nDRY-RUN: would snapshot + drop {len(present)} tables "
              f"({total:,} rows). Re-run with --apply.")
        return 0
    if not present:
        print("\nnothing to drop")
        return 0

    bconn = _conn(get_backups_creds())
    dropped: dict[str, dict] = {}
    failed: list[str] = []
    print("\n=== APPLY ===")
    for table in present:
        try:
            name, expected, copied = snapshot(scur, bconn, table, stamp)
        except pymysql.Error as exc:
            print(f"  {table}: SNAPSHOT FAILED ({exc}) — left in place")
            failed.append(table)
            continue
        print(f"  {table}: snapshot -> ejaguiar1_backups.{name} "
              f"({copied}/{expected} rows)")
        if copied != expected:
            print(f"  {table}: COUNT MISMATCH — left in place")
            failed.append(table)
            continue
        scur.execute(f"DROP TABLE `{table}`")
        sconn.commit()
        dropped[table] = {"backup": name, "rows": expected,
                          "why": SPORTS_TABLES[table]}
        print(f"  {table}: dropped")
    bconn.close()

    print("\n=== POST-STATE ===")
    leftover = 0
    for table in present:
        try:
            n = count(scur, table)
            leftover += 1
            print(f"  {table}: STILL PRESENT ({n:,} rows)")
        except pymysql.Error:
            print(f"  {table}: gone")
    sconn.close()

    out = REPO_ROOT / "reports" / f"sports_tables_scrapped_{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"generated_at": stamp, "database": database,
         "dropped": dropped, "failed": failed, "already_absent": missing},
        indent=2), encoding="utf-8")
    print(f"\nreport: {out}")
    print("OK: all scrapped tables dropped" if not leftover
          else f"WARNING: {leftover} table(s) still present")
    return 0 if not leftover else 1


if __name__ == "__main__":
    raise SystemExit(main())
