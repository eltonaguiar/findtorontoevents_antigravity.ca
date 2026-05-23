#!/usr/bin/env python3
"""Snapshot MySQL schema to JSON and diff against a stored baseline.

Usage:
    python tools/db_schema_snapshot.py --snapshot   # write current schema to baseline
    python tools/db_schema_snapshot.py --diff        # compare current schema to baseline
    python tools/db_schema_snapshot.py --check       # exit 1 if drift detected
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BASELINE_PATH = Path(__file__).parent / "data" / "schema_baseline.json"

# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------


def _get_connection(db_name: str):
    """Return a pymysql connection.  Returns None (with warning) if creds absent."""
    import pymysql  # local import so missing package gives a clear error

    host = os.environ.get("DB_HOST", "localhost")
    user = os.environ.get("DB_USER", "")
    password = os.environ.get("DB_PASS_STOCKS", "")

    if not password:
        print(
            "WARNING: DB_PASS_STOCKS is not set. "
            "Skipping schema snapshot (no DB credentials available).",
            file=sys.stderr,
        )
        return None

    return pymysql.connect(
        host=host,
        user=user,
        password=password,
        database="information_schema",
        connect_timeout=15,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


# ---------------------------------------------------------------------------
# Schema fetching
# ---------------------------------------------------------------------------


def fetch_schema(db_name: str) -> dict:
    """Query INFORMATION_SCHEMA.COLUMNS and return a structured schema dict."""
    conn = _get_connection(db_name)
    if conn is None:
        return {}

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    TABLE_NAME,
                    COLUMN_NAME,
                    COLUMN_TYPE,
                    IS_NULLABLE,
                    COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME, ORDINAL_POSITION
                """,
                (db_name,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    tables: dict = {}
    for row in rows:
        tbl = row["TABLE_NAME"]
        if tbl not in tables:
            tables[tbl] = {"columns": []}
        tables[tbl]["columns"].append(
            {
                "name": row["COLUMN_NAME"],
                "type": row["COLUMN_TYPE"],
                "nullable": row["IS_NULLABLE"].upper() == "YES",
                "default": row["COLUMN_DEFAULT"],
            }
        )
    return tables


# ---------------------------------------------------------------------------
# Snapshot command
# ---------------------------------------------------------------------------


def cmd_snapshot(db_name: str) -> int:
    print(f"Fetching schema for database '{db_name}' …")
    tables = fetch_schema(db_name)
    if tables == {} and not os.environ.get("DB_PASS_STOCKS"):
        # Graceful exit when creds absent (already warned inside fetch_schema)
        return 0

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db": db_name,
        "tables": tables,
    }
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Baseline written to {BASELINE_PATH}  ({len(tables)} tables)")
    return 0


# ---------------------------------------------------------------------------
# Diff logic
# ---------------------------------------------------------------------------


def _load_baseline() -> dict | None:
    if not BASELINE_PATH.exists():
        print(f"ERROR: Baseline file not found: {BASELINE_PATH}", file=sys.stderr)
        return None
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    if not data.get("tables"):
        print(
            "WARNING: Baseline is empty (run --snapshot first). Nothing to compare.",
            file=sys.stderr,
        )
        return data
    return data


def diff_schemas(baseline_tables: dict, current_tables: dict) -> list[dict]:
    """Return a list of drift items (added/removed/retyped columns, added/removed tables)."""
    drift = []

    all_tables = set(baseline_tables) | set(current_tables)

    for table in sorted(all_tables):
        if table not in baseline_tables:
            drift.append({"table": table, "kind": "table_added"})
            continue
        if table not in current_tables:
            drift.append({"table": table, "kind": "table_removed"})
            continue

        base_cols = {c["name"]: c for c in baseline_tables[table]["columns"]}
        curr_cols = {c["name"]: c for c in current_tables[table]["columns"]}

        for col_name in sorted(set(base_cols) | set(curr_cols)):
            if col_name not in base_cols:
                drift.append(
                    {
                        "table": table,
                        "column": col_name,
                        "kind": "column_added",
                        "current": curr_cols[col_name],
                    }
                )
            elif col_name not in curr_cols:
                drift.append(
                    {
                        "table": table,
                        "column": col_name,
                        "kind": "column_removed",
                        "baseline": base_cols[col_name],
                    }
                )
            else:
                b, c = base_cols[col_name], curr_cols[col_name]
                changes = {}
                for field in ("type", "nullable", "default"):
                    if b.get(field) != c.get(field):
                        changes[field] = {"baseline": b.get(field), "current": c.get(field)}
                if changes:
                    drift.append(
                        {
                            "table": table,
                            "column": col_name,
                            "kind": "column_changed",
                            "changes": changes,
                        }
                    )

    return drift


def _print_drift(drift: list[dict]) -> None:
    if not drift:
        print("No schema drift detected.")
        return

    print(f"Schema drift detected — {len(drift)} item(s):")
    for item in drift:
        kind = item["kind"]
        tbl = item.get("table", "?")
        if kind == "table_added":
            print(f"  [TABLE ADDED]   {tbl}")
        elif kind == "table_removed":
            print(f"  [TABLE REMOVED] {tbl}")
        elif kind == "column_added":
            col = item.get("column", "?")
            print(f"  [COL ADDED]     {tbl}.{col}  →  {item.get('current', {})}")
        elif kind == "column_removed":
            col = item.get("column", "?")
            print(f"  [COL REMOVED]   {tbl}.{col}  (was: {item.get('baseline', {})})")
        elif kind == "column_changed":
            col = item.get("column", "?")
            for field, vals in item.get("changes", {}).items():
                print(
                    f"  [COL CHANGED]   {tbl}.{col} .{field}: "
                    f"{vals['baseline']!r} → {vals['current']!r}"
                )


# ---------------------------------------------------------------------------
# Diff / Check commands
# ---------------------------------------------------------------------------


def cmd_diff(db_name: str, exit_on_drift: bool = False) -> int:
    baseline = _load_baseline()
    if baseline is None:
        return 1
    if not baseline.get("tables"):
        # Empty baseline — nothing to compare, treat as no drift
        return 0

    print(f"Fetching current schema for '{db_name}' …")
    current_tables = fetch_schema(db_name)
    if current_tables == {} and not os.environ.get("DB_PASS_STOCKS"):
        # Creds absent — skip gracefully (already warned)
        return 0

    drift = diff_schemas(baseline["tables"], current_tables)
    _print_drift(drift)

    if exit_on_drift and drift:
        return 1
    return 0


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="MySQL schema drift watchdog",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--snapshot",
        action="store_true",
        help="Write current DB schema to baseline JSON",
    )
    mode.add_argument(
        "--diff",
        action="store_true",
        help="Print differences between current schema and baseline",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="Like --diff but exit 1 if drift found (for CI)",
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("DB_NAME", "ejaguiar1_stocks"),
        help="Target database name (default: env DB_NAME or ejaguiar1_stocks)",
    )

    args = parser.parse_args()

    if args.snapshot:
        return cmd_snapshot(args.db)
    elif args.diff:
        return cmd_diff(args.db, exit_on_drift=False)
    else:  # --check
        return cmd_diff(args.db, exit_on_drift=True)


if __name__ == "__main__":
    sys.exit(main())
