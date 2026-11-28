#!/usr/bin/env python3
"""Fill missing / contradicted asset-class labels across the ledger tables.

2026-11-28 — extends the original UNKNOWN-category scrub (INCP2) into the
label-drift repair the class audit asked for:

  1. MISSING label — `category`/`asset_class` is NULL, '' or 'UNKNOWN'.
     trading_picks carried 2,667 of these; 91% are `etf_all_strategies` ETF
     rows whose emitter never set a class.
  2. CONTRADICTED label — a `*-USDT/USDC/BUSD` pair filed under EQUITY,
     COMMODITY or FOREX (40 rows). The symbol alone proves the class is wrong.

Both passes are DETERMINISTIC — a source-system rule where the emitter is
unambiguous, otherwise `alpha_engine.config.detect_asset_class(symbol)`. Rows
the detector cannot classify are REPORTED and left untouched; nothing is
guessed.

2026-11-28: the detector returns 'unknown' for dash-separated ISO pairs such as
`USD-JPY` / `USD-CHF` (a bare X-Y shape is genuinely ambiguous), so this tool
now applies the SAME rule the sync uses at ingest
(`alpha_engine/mysql_trading_sync.py::_FX_ISO`): both halves must be real ISO
currency codes, in which case the row is FOREX. Repeating the sync's rule here
is what stops those rows being reported as unclassifiable on every run.

Column compatibility: `at_raw_picks.asset_class` and
`at_signal_outcomes.asset_class` are ENUMs that do not contain INDEX or
PREDICTION_MARKET, so a detected class outside the column's enum is clamped to
'UNKNOWN' rather than silently writing the enum's empty/invalid value.

Safety:
  * Dry-run by DEFAULT.
  * --apply snapshots every affected full row to a timestamped table in
    ejaguiar1_backups (tools/db_env.get_backups_creds — mandatory per project
    rule) BEFORE any UPDATE, then writes set-based, PK-keyed chunks.
  * PK is discovered per table (at_raw_picks has no `id` column).

Usage:
  python3 tools/backfill_unknown_category.py                  # dry-run, all tables
  python3 tools/backfill_unknown_category.py --table trading_picks
  python3 tools/backfill_unknown_category.py --apply
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pymysql

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.config import detect_asset_class  # noqa: E402
from tools.db_env import get_backups_creds, get_stocks_creds  # noqa: E402

# Exact enum members each target column can store. trading_picks is a
# varchar(20) so it takes the full canonical enum; the two at_* columns are
# narrower ENUMs and must be clamped.
_CANON_TRADING_PICKS = {
    "CRYPTO", "EQUITY", "FOREX", "ETF", "BOND", "COMMODITY", "FUTURES",
    "INDEX", "PREDICTION_MARKET", "MEMECOIN", "PENNY_STOCK",
}
_AT_ENUM = {
    "CRYPTO", "FOREX", "EQUITY", "PENNY_STOCK", "MEMECOIN", "SPORTS",
    "FUTURES", "ETF", "COMMODITY", "BOND", "UNKNOWN",
}

TABLES: dict[str, dict] = {
    "trading_picks": {"col": "category", "allowed": _CANON_TRADING_PICKS},
    "at_raw_picks": {"col": "asset_class", "allowed": _AT_ENUM},
    "at_signal_outcomes": {"col": "asset_class", "allowed": _AT_ENUM},
}

# Source systems whose class is unambiguous regardless of symbol.
SOURCE_FORCE = {
    "polymarket_bts_consensus_v1": "PREDICTION_MARKET",
    "polymarket_bts_consensus": "PREDICTION_MARKET",
    "pm_macro_expansion": "PREDICTION_MARKET",
    "goldmine_meme": "MEMECOIN",
    "etf_all_strategies": "ETF",
}

_CRYPTO_PAIR_RE = r"(USDT|USDC|BUSD|TUSD|FDUSD)$"

# Mirror of alpha_engine/mysql_trading_sync.py::_FX_ISO. Kept as a literal copy
# on purpose: the sync set is private to a module-level function scope and
# importing the sync module from a backfill tool would pull its DB writers in.
# tests/test_backfill_unknown_category.py asserts the two stay identical.
_FX_ISO = frozenset({
    "USD", "EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD", "CNY",
    "HKD", "SGD", "SEK", "NOK", "DKK", "MXN", "ZAR", "TRY", "INR",
    "BRL", "KRW", "PLN", "CZK", "HUF", "ILS", "THB", "PHP", "MYR",
})
_DETECTED_TO_CANON = {
    "crypto": "CRYPTO",
    "equity": "EQUITY",
    "forex": "FOREX",
    "etf": "ETF",
    "bond": "BOND",
    "commodity": "COMMODITY",
    "futures": "FUTURES",
    "index": "INDEX",
    "memecoin": "MEMECOIN",
    "meme": "MEMECOIN",
    "penny_stock": "PENNY_STOCK",
    "mutual_fund": "UNKNOWN",
    "sports": "SPORTS",
    "unknown": None,
}


def _conn(creds: dict):
    keep = ("host", "user", "password", "database", "port",
            "connect_timeout", "read_timeout")
    kwargs = {k: v for k, v in creds.items() if k in keep}
    kwargs.setdefault("read_timeout", 600)
    return pymysql.connect(**kwargs, cursorclass=pymysql.cursors.DictCursor)


def primary_key(cur, table: str) -> str:
    cur.execute(f"SHOW KEYS FROM {table} WHERE Key_name = 'PRIMARY'")
    rows = cur.fetchall()
    if not rows:
        raise SystemExit(f"{table} has no PRIMARY KEY — refusing to update it")
    # Single-column PKs only; a composite key would need a compound WHERE.
    cols = [r["Column_name"] for r in rows]
    if len(cols) != 1:
        raise SystemExit(f"{table} has a composite PK {cols} — unsupported")
    return cols[0]


def candidates(cur, table: str) -> list[dict]:
    """Rows needing a label: missing first, then symbol-contradicted."""
    meta = TABLES[table]
    col, pk = meta["col"], primary_key(cur, table)
    cur.execute(
        f"""
        SELECT {pk} AS pk, symbol, source_system, {col} AS current_label,
               'missing' AS reason
        FROM {table}
        WHERE {col} IS NULL OR {col} = '' OR UPPER({col}) = 'UNKNOWN'
        """
    )
    rows = list(cur.fetchall())
    cur.execute(
        f"""
        SELECT {pk} AS pk, symbol, source_system, {col} AS current_label,
               'contradicted' AS reason
        FROM {table}
        WHERE UPPER(symbol) REGEXP %s
          AND {col} IS NOT NULL AND {col} <> ''
          AND UPPER({col}) NOT IN ('CRYPTO', 'MEMECOIN')
        """,
        (_CRYPTO_PAIR_RE,),
    )
    rows.extend(cur.fetchall())
    return rows


def iso_fx_pair(symbol: str) -> bool:
    """True for a dash-separated pair whose halves are BOTH ISO currency codes.

    `USD-JPY` / `USD-CHF` yes; `BTC-USD` no (BTC is not an ISO code). This is
    the sync's rule verbatim, so a row the sync would label FOREX at ingest is
    never reported as unclassifiable by the backfill.
    """
    sym = str(symbol or "").strip().upper()
    if sym.count("-") != 1:
        return False
    return all(part in _FX_ISO for part in sym.split("-"))


def resolve(row: dict, allowed: set[str]) -> tuple[str | None, str]:
    """Return (target, why). target=None means 'cannot classify, leave it'."""
    src = str(row.get("source_system") or "").strip().lower()
    if src in SOURCE_FORCE:
        target, why = SOURCE_FORCE[src], f"source:{src}"
    elif iso_fx_pair(str(row.get("symbol") or "")):
        target, why = "FOREX", "iso_pair"
    else:
        detected = detect_asset_class(str(row.get("symbol") or ""))
        target = _DETECTED_TO_CANON.get(str(detected).strip().lower())
        why = f"detect:{detected}"
    if not target:
        return None, why
    if target not in allowed:
        # Column cannot store it (e.g. INDEX in the at_* ENUMs).
        return ("UNKNOWN" if "UNKNOWN" in allowed else None), f"{why}->clamped"
    return target, why


def plan(cur, table: str) -> tuple[list[dict], list[dict]]:
    meta = TABLES[table]
    updates: list[dict] = []
    skipped: list[dict] = []
    for row in candidates(cur, table):
        target, why = resolve(row, meta["allowed"])
        current = str(row.get("current_label") or "")
        if not target or target == current:
            skipped.append({**row, "why": why})
            continue
        updates.append({**row, "target": target, "why": why})
    return updates, skipped


def clean_ddl(ddl: str, source: str, dest: str, suffix: str) -> str:
    """Make a SHOW CREATE TABLE clone safe to create in the archive schema.

    Two MySQL-8 schema rules bite here:
      * FOREIGN KEY: the referenced table does not exist in ejaguiar1_backups
        (at_raw_picks -> at_aggregation_runs), so the clone fails with errno
        1824. Snapshots don't need referential integrity — strip the FK.
      * named CHECK/UNIQUE constraints must be unique per SCHEMA, so a second
        snapshot of the same table collides on the constraint name — suffix it.
    """
    ddl = ddl.replace(f"CREATE TABLE `{source}`", f"CREATE TABLE `{dest}`", 1)
    ddl = re.sub(
        r",?\s*CONSTRAINT `[^`]+` FOREIGN KEY \([^)]*\)"
        r" REFERENCES `[^`]+` \([^)]*\)[^,\n]*",
        "",
        ddl,
    )
    # Unique per snapshot table, not per run: two snapshots in one run share the
    # timestamp and collided on 'chk_pnl_sign_coherence_<stamp>' (errno 3822).
    tag = hashlib.md5(dest.encode()).hexdigest()[:10]
    ddl = re.sub(
        r"CONSTRAINT `([^`]+)`",
        lambda m: "CONSTRAINT `" + (m.group(1) + "_" + tag)[:60] + "`",
        ddl,
    )
    return ddl


def snapshot(cur, table: str, rows: list[dict], stamp: str) -> str | None:
    """Full-row snapshot of the affected rows into ejaguiar1_backups."""
    if not rows:
        return None
    pk = primary_key(cur, table)
    name = f"{table}_label_fill_{stamp}"[:64]
    ids = [r["pk"] for r in rows]
    bconn = _conn(get_backups_creds())
    try:
        bcur = bconn.cursor()
        cur.execute(f"SHOW CREATE TABLE {table}")
        ddl = clean_ddl(cur.fetchone()["Create Table"], table, name, stamp)
        bcur.execute(f"DROP TABLE IF EXISTS `{name}`")
        bcur.execute(ddl)
        placeholders = ",".join(["%s"] * len(ids))
        cur.execute(f"SELECT * FROM {table} WHERE {pk} IN ({placeholders})", ids)
        cols = [d[0] for d in cur.description]
        payload = cur.fetchall()
        ins = (f"INSERT INTO `{name}` (`" + "`,`".join(cols) + "`) VALUES ("
               + ",".join(["%s"] * len(cols)) + ")")
        for i in range(0, len(payload), 500):
            bcur.executemany(ins, [tuple(r[c] for c in cols)
                                   for r in payload[i:i + 500]])
            bconn.commit()
        bcur.execute(f"SELECT COUNT(*) AS n FROM `{name}`")
        got = int(bcur.fetchone()["n"])
        print(f"  backup: {got:,} rows -> ejaguiar1_backups.{name} "
              f"(expected {len(ids):,}) {'OK' if got == len(ids) else 'MISMATCH'}")
        return name
    finally:
        bconn.close()


def apply(conn, cur, table: str, updates: list[dict]) -> int:
    meta = TABLES[table]
    col, pk = meta["col"], primary_key(cur, table)
    by_target: dict[str, list] = {}
    for u in updates:
        by_target.setdefault(u["target"], []).append(u["pk"])
    touched = 0
    for target, ids in sorted(by_target.items()):
        for i in range(0, len(ids), 200):
            chunk = ids[i:i + 200]
            ph = ",".join(["%s"] * len(chunk))
            cur.execute(
                f"UPDATE {table} SET {col} = %s "
                f"WHERE {pk} IN ({ph}) AND ({col} IS NULL OR {col} = '' "
                f"OR UPPER({col}) = 'UNKNOWN' OR UPPER({col}) NOT IN ('CRYPTO','MEMECOIN'))",
                [target, *chunk],
            )
            conn.commit()
            touched += cur.rowcount or 0
        print(f"  {table}.{col} -> {target:<18} {len(ids):>6,} planned")
    return touched


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Fill missing/contradicted asset-class labels (dry-run default).")
    ap.add_argument("--table", action="append", choices=sorted(TABLES),
                    help="table to fix (repeatable; default: all)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    tables = args.table or sorted(TABLES)

    conn = _conn(get_stocks_creds())
    cur = conn.cursor()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    totals: dict[str, dict] = {}
    grand = 0
    for table in tables:
        updates, skipped = plan(cur, table)
        grand += len(updates)
        by_target: dict[str, int] = {}
        by_reason: dict[str, int] = {}
        for u in updates:
            by_target[u["target"]] = by_target.get(u["target"], 0) + 1
            by_reason[u["reason"]] = by_reason.get(u["reason"], 0) + 1
        print(f"\n=== {table} ===")
        print(f"  updatable: {len(updates):,}   unclassifiable/skipped: {len(skipped):,}")
        for t, n in sorted(by_target.items(), key=lambda kv: -kv[1]):
            print(f"    -> {t:<20} {n:>6,}")
        for r, n in sorted(by_reason.items(), key=lambda kv: -kv[1]):
            print(f"    via {r:<28} {n:>6,}")
        if skipped:
            sample = ", ".join(
                f"{s.get('symbol')}({s['why']})" for s in skipped[:8])
            print(f"    left alone (no deterministic class): {sample}"
                  f"{' ...' if len(skipped) > 8 else ''}")
        totals[table] = {
            "updatable": len(updates),
            "skipped": len(skipped),
            "by_target": by_target,
            "backup_table": None,
            "touched": 0,
        }

    if not grand:
        print("\nnothing to fill")
        return 0

    if not args.apply:
        print(f"\nDRY-RUN (default): {grand:,} rows would be relabelled."
              " Re-run with --apply to write.")
        return 0

    print("\n=== APPLY ===")
    for table in tables:
        updates, _ = plan(cur, table)
        if not updates:
            continue
        print(f"\n[{table}]")
        name = snapshot(cur, table, updates, stamp)
        touched = apply(conn, cur, table, updates)
        totals[table]["backup_table"] = name
        totals[table]["touched"] = touched
        print(f"  updated {touched:,} rows")

    out = REPO_ROOT / "reports" / f"label_fill_{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"generated_at": stamp, "tables": totals},
                              indent=2, default=str), encoding="utf-8")
    print(f"\nreport: {out}")

    print("\n=== POST-STATE ===")
    leftover = 0
    for table in tables:
        updates, skipped = plan(cur, table)
        leftover += len(updates)
        print(f"  {table}: {len(updates):,} still updatable, "
              f"{len(skipped):,} unclassifiable")
    print("  OK: no deterministic relabel left" if not leftover
          else f"  WARNING: {leftover:,} rows still updatable")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
