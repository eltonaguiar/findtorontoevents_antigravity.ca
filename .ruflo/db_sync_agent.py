"""
DB Sync Agent — synchronizes MySQL DB data with the local JSON pick store.

This agent adds database awareness to the .ruflo orchestrator pipeline,
enabling bidirectional sync between MySQL tables (stocks, backtests, backups)
and the local JSON pick store used by the audit swarm.
"""

from __future__ import annotations

import copy
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

logger = logging.getLogger("ruflo.db_sync")


class DBSyncAgent:
    """Agent that synchronizes MySQL DB data with the local JSON pick store.

    The orchestrator runs continuous swarms for audit, GitHub hygiene, strategy
    ideation, and bug hunting. This agent provides DB awareness by keeping the
    local JSON pick store in sync with the remote MySQL databases.

    Unique key for records: ``(ticker, entry_time)``.
    """

    # Expected schema for compatibility checks
    EXPECTED_SCHEMA: dict[str, dict[str, str]] = {
        "swarm_picks": {
            "ticker": "VARCHAR(10)",
            "entry_time": "DATETIME",
            "exit_time": "DATETIME",
            "direction": "VARCHAR(4)",
            "entry_price": "DECIMAL(12,4)",
            "exit_price": "DECIMAL(12,4)",
            "pnl": "DECIMAL(12,4)",
            "status": "VARCHAR(20)",
            "created_at": "TIMESTAMP",
            "updated_at": "TIMESTAMP",
        },
    }

    def __init__(
        self,
        db_config: dict[str, Any] | None = None,
        json_store_path: str = "audit_dashboard/data/swarm_picks.json",
    ) -> None:
        """Initialize the DB sync agent.

        Parameters
        ----------
        db_config:
            Override for DB connection parameters. Keys understood:
            ``host``, ``user``, ``password``, ``database``, ``port``.
            Missing keys are read from environment variables.
        json_store_path:
            Path to the local JSON file that acts as the pick store.
        """
        self._cfg: dict[str, Any] = db_config or {}
        self._json_store_path: str = json_store_path
        self._conn: pymysql.Connection | None = None

        # Connection parameters (env fallback)
        self._host: str = self._cfg.get("host") or os.getenv("DB_HOST", "mysql.50webs.com")
        self._user: str = self._cfg.get("user") or os.getenv("DB_USER", "")
        self._password: str = self._cfg.get("password") or os.getenv("DB_PASSWORD", "")
        self._databases: list[str] = [
            self._cfg.get("database") or os.getenv("DB_NAME", "ejaguiar1_stocks"),
            "ejaguiar1_backtests",
            "ejaguiar1_backups",
        ]
        self._port: int = int(self._cfg.get("port", 3306))

        logger.info("DBSyncAgent initialized — host=%s, json=%s", self._host, self._json_store_path)

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _connect(self, database: str | None = None) -> pymysql.Connection:
        """Open (or re-use) a pymysql connection.

        Parameters
        ----------
        database:
            Database name to connect to. Uses the primary DB if *None*.

        Returns
        -------
        pymysql.Connection
            Live connection using ``DictCursor``.
        """
        if self._conn is not None and self._conn.open:
            return self._conn

        db = database or self._databases[0]
        self._conn = pymysql.connect(
            host=self._host,
            user=self._user,
            password=self._password,
            database=db,
            port=self._port,
            cursorclass=DictCursor,
            connect_timeout=10,
        )
        logger.debug("DB connection opened — db=%s", db)
        return self._conn

    def _close(self) -> None:
        """Close the cached connection if open."""
        if self._conn is not None and self._conn.open:
            self._conn.close()
            logger.debug("DB connection closed")
        self._conn = None

    def _fetch_db_records(self, database: str | None = None) -> dict[tuple[str, str], dict[str, Any]]:
        """Pull all records from the primary ``swarm_picks`` table as a dict.

        Returns
        -------
        dict
            Mapping of ``(ticker, entry_time)`` → row.
        """
        conn = self._connect(database)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM swarm_picks WHERE ticker IS NOT NULL AND entry_time IS NOT NULL"
                )
                rows = cur.fetchall()
        except pymysql.MySQLError as exc:
            logger.error("DB fetch failed (%s): %s", database or self._databases[0], exc)
            rows = []

        result: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            key = (str(row.get("ticker", "")), str(row.get("entry_time", "")))
            if key[0] and key[1]:
                result[key] = dict(row)
        logger.debug("Fetched %d rows from DB (%s)", len(result), database or self._databases[0])
        return result

    def _fetch_json_records(self) -> dict[tuple[str, str], dict[str, Any]]:
        """Load the JSON store into a ``(ticker, entry_time)`` → record map.

        Returns
        -------
        dict
            Empty dict if the file does not exist.
        """
        if not os.path.exists(self._json_store_path):
            logger.warning("JSON store not found at %s — treating as empty", self._json_store_path)
            return {}

        with open(self._json_store_path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)

        records: list[dict[str, Any]] = raw if isinstance(raw, list) else raw.get("records", [])
        result: dict[tuple[str, str], dict[str, Any]] = {}
        for rec in records:
            key = (str(rec.get("ticker", "")), str(rec.get("entry_time", "")))
            if key[0] and key[1]:
                result[key] = rec
        logger.debug("Loaded %d rows from JSON store", len(result))
        return result

    def _write_json_records(self, records: dict[tuple[str, str], dict[str, Any]]) -> None:
        """Persist the merged record map back to the JSON store."""
        os.makedirs(os.path.dirname(self._json_store_path) or ".", exist_ok=True)
        serializable = list(records.values())
        with open(self._json_store_path, "w", encoding="utf-8") as fh:
            json.dump(serializable, fh, indent=2, default=str)
        logger.debug("Wrote %d records to JSON store", len(serializable))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sync_mysql_to_json(self) -> int:
        """Sync records from MySQL → JSON.

        Adds missing records and updates records that differ.

        Returns
        -------
        int
            Number of rows synced.
        """
        db_records = self._fetch_db_records()
        json_records = self._fetch_json_records()

        synced = 0
        for key, db_row in db_records.items():
            json_row = json_records.get(key)
            if json_row is None:
                json_records[key] = copy.deepcopy(db_row)
                synced += 1
                logger.debug("Inserted %s into JSON store", key)
            elif json_row != db_row:
                json_records[key] = copy.deepcopy(db_row)
                synced += 1
                logger.debug("Updated %s in JSON store", key)

        self._write_json_records(json_records)
        logger.info("sync_mysql_to_json complete — %d rows synced", synced)
        self._close()
        return synced

    def sync_json_to_mysql(self) -> int:
        """Sync records from JSON → MySQL.

        Inserts missing records and updates existing rows that differ.

        Returns
        -------
        int
            Number of rows synced.
        """
        db_records = self._fetch_db_records()
        json_records = self._fetch_json_records()

        conn = self._connect()
        synced = 0

        with conn.cursor() as cur:
            for key, json_row in json_records.items():
                if key not in db_records:
                    # Insert
                    columns = list(json_row.keys())
                    placeholders = ", ".join(["%s"] * len(columns))
                    col_names = ", ".join(f"`{c}`" for c in columns)
                    sql = f"INSERT INTO swarm_picks ({col_names}) VALUES ({placeholders})"
                    try:
                        cur.execute(sql, tuple(json_row.values()))
                        synced += 1
                        logger.debug("Inserted %s into DB", key)
                    except pymysql.MySQLError as exc:
                        logger.error("Insert failed for %s: %s", key, exc)
                elif db_records[key] != json_row:
                    # Update
                    columns = [k for k in json_row.keys() if k not in ("ticker", "entry_time")]
                    if not columns:
                        continue
                    set_clause = ", ".join(f"`{c}`=%s" for c in columns)
                    sql = (
                        f"UPDATE swarm_picks SET {set_clause} "
                        f"WHERE ticker=%s AND entry_time=%s"
                    )
                    try:
                        cur.execute(sql, tuple(json_row[c] for c in columns) + key)
                        synced += 1
                        logger.debug("Updated %s in DB", key)
                    except pymysql.MySQLError as exc:
                        logger.error("Update failed for %s: %s", key, exc)

        conn.commit()
        logger.info("sync_json_to_mysql complete — %d rows synced", synced)
        self._close()
        return synced

    def detect_sync_conflicts(self) -> list[dict]:
        """Detect records that differ between DB and JSON.

        Returns
        -------
        list[dict]
            Each dict contains:
            ``unique_key`` (tuple), ``db_record``, ``json_record``,
            ``diff_fields`` (list of differing column names).
        """
        db_records = self._fetch_db_records()
        json_records = self._fetch_json_records()

        conflicts: list[dict] = []
        all_keys = set(db_records.keys()) | set(json_records.keys())

        for key in all_keys:
            db_row = db_records.get(key)
            json_row = json_records.get(key)

            if db_row is None or json_row is None:
                conflicts.append({
                    "unique_key": key,
                    "db_record": db_row,
                    "json_record": json_row,
                    "diff_fields": ["<missing>"],
                })
                continue

            diff_fields = [
                col for col in set(db_row.keys()) | set(json_row.keys())
                if db_row.get(col) != json_row.get(col)
            ]
            if diff_fields:
                conflicts.append({
                    "unique_key": key,
                    "db_record": db_row,
                    "json_record": json_row,
                    "diff_fields": diff_fields,
                })

        logger.info("Detected %d conflicts", len(conflicts))
        self._close()
        return conflicts

    def resolve_conflicts(self, strategy: str = "latest_wins") -> int:
        """Resolve detected conflicts using the chosen strategy.

        Parameters
        ----------
        strategy:
            One of ``latest_wins``, ``db_wins``, ``json_wins``, ``manual``.

        Returns
        -------
        int
            Number of conflicts resolved.
        """
        conflicts = self.detect_sync_conflicts()
        if not conflicts:
            return 0

        if strategy not in {"latest_wins", "db_wins", "json_wins", "manual"}:
            raise ValueError(f"Unknown conflict strategy: {strategy}")

        db_records = self._fetch_db_records()
        json_records = self._fetch_json_records()
        resolved = 0

        for conflict in conflicts:
            key = conflict["unique_key"]
            db_row = conflict["db_record"]
            json_row = conflict["json_record"]

            if strategy == "manual":
                logger.info("Manual resolution required for %s — skipping auto-resolve", key)
                continue

            if strategy == "db_wins":
                if db_row is not None:
                    json_records[key] = copy.deepcopy(db_row)
                    resolved += 1
            elif strategy == "json_wins":
                if json_row is not None:
                    db_records[key] = copy.deepcopy(json_row)
            elif strategy == "latest_wins":
                # Compare updated_at if present, else fall back to db winning
                db_ts = self._parse_ts(db_row.get("updated_at") if db_row else None)
                json_ts = self._parse_ts(json_row.get("updated_at") if json_row else None)

                if db_ts is not None and (json_ts is None or db_ts >= json_ts):
                    json_records[key] = copy.deepcopy(db_row) if db_row else json_records.pop(key, None)  # type: ignore[assignment]
                    resolved += 1
                elif json_ts is not None:
                    db_records[key] = copy.deepcopy(json_row) if json_row else db_records.pop(key, None)  # type: ignore[assignment]
                    resolved += 1

        # Persist JSON side
        self._write_json_records(json_records)

        # Persist DB side (upsert for any json_wins / latest_wins where JSON was newer)
        if strategy in ("json_wins", "latest_wins"):
            conn = self._connect()
            with conn.cursor() as cur:
                for key, rec in db_records.items():
                    columns = list(rec.keys())
                    placeholders = ", ".join(["%s"] * len(columns))
                    col_names = ", ".join(f"`{c}`" for c in columns)
                    update_clause = ", ".join(f"`{c}`=VALUES(`{c}`)" for c in columns)
                    sql = (
                        f"INSERT INTO swarm_picks ({col_names}) VALUES ({placeholders}) "
                        f"ON DUPLICATE KEY UPDATE {update_clause}"
                    )
                    try:
                        cur.execute(sql, tuple(rec.values()))
                    except pymysql.MySQLError as exc:
                        logger.error("Conflict resolution upsert failed for %s: %s", key, exc)
            conn.commit()
            logger.info("Persisted resolved records to DB")

        logger.info("Resolved %d/%d conflicts using '%s'", resolved, len(conflicts), strategy)
        self._close()
        return resolved

    @staticmethod
    def _parse_ts(value: Any) -> datetime | None:
        """Best-effort parse a value into a timezone-aware datetime."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
        try:
            # Try ISO format first, then common MySQL datetime
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None

    def validate_schema_compatibility(self) -> dict[str, Any]:
        """Check whether the remote DB schema matches expectations.

        Returns
        -------
        dict
            ``is_compatible`` (bool), ``missing_tables`` (list),
            ``missing_columns`` (dict), ``type_mismatches`` (list),
            ``extra_columns`` (dict).
        """
        result: dict[str, Any] = {
            "is_compatible": True,
            "missing_tables": [],
            "missing_columns": {},
            "type_mismatches": [],
            "extra_columns": {},
        }

        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SHOW TABLES")
                tables = {row[f"Tables_in_{self._databases[0]}"] for row in cur.fetchall()}
        except pymysql.MySQLError as exc:
            logger.error("Schema validation — could not list tables: %s", exc)
            result["is_compatible"] = False
            self._close()
            return result

        for expected_table in self.EXPECTED_SCHEMA:
            if expected_table not in tables:
                result["missing_tables"].append(expected_table)
                result["is_compatible"] = False
                continue

            with conn.cursor() as cur:
                cur.execute(f"SHOW COLUMNS FROM `{expected_table}`")
                db_cols = {row["Field"]: row["Type"] for row in cur.fetchall()}

            expected_cols = self.EXPECTED_SCHEMA[expected_table]
            missing = [c for c in expected_cols if c not in db_cols]
            if missing:
                result["missing_columns"][expected_table] = missing
                result["is_compatible"] = False

            extra = [c for c in db_cols if c not in expected_cols]
            if extra:
                result["extra_columns"][expected_table] = extra

            for col, expected_type in expected_cols.items():
                if col in db_cols and db_cols[col].upper() != expected_type.upper():
                    result["type_mismatches"].append(
                        f"{expected_table}.{col}: expected {expected_type}, got {db_cols[col]}"
                    )
                    result["is_compatible"] = False

        logger.info("Schema compatibility: %s", result["is_compatible"])
        self._close()
        return result

    def run_full_sync(self) -> dict[str, Any]:
        """Run a full bidirectional sync with conflict detection and resolution.

        The pipeline is:
        1. Validate schema compatibility.
        2. Sync MySQL → JSON.
        3. Sync JSON → MySQL.
        4. Detect remaining conflicts.
        5. Auto-resolve with ``latest_wins``.

        Returns
        -------
        dict
            Summary with ``schema_ok``, ``mysql_to_json``, ``json_to_mysql``,
            "conflicts_detected", "conflicts_resolved", "timestamp".
        """
        logger.info("Starting full sync pipeline")
        ts_start = datetime.now(timezone.utc).isoformat()

        schema_check = self.validate_schema_compatibility()
        if not schema_check["is_compatible"]:
            logger.warning("Schema compatibility issues detected: %s", schema_check)

        m2j = self.sync_mysql_to_json()
        j2m = self.sync_json_to_mysql()
        conflicts = self.detect_sync_conflicts()
        resolved = self.resolve_conflicts(strategy="latest_wins")

        summary = {
            "schema_ok": schema_check["is_compatible"],
            "schema_details": schema_check,
            "mysql_to_json": m2j,
            "json_to_mysql": j2m,
            "conflicts_detected": len(conflicts),
            "conflicts_resolved": resolved,
            "timestamp": ts_start,
        }

        logger.info("Full sync complete — %s", summary)
        return summary
