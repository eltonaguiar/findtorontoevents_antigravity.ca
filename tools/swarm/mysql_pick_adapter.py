"""
MySQL Pick Adapter — Production-grade MySQL adapter for the swarm edge engine.

Provides:
- Connection pooling via context managers (pymysql + DictCursor)
- CRUD-style querying against ``trading_picks`` (with ``picks`` fallback)
- Graceful JSON-file fallback when the DB is unreachable
- Full type hints, structured logging, and environment-driven configuration

Environment Variables
---------------------
DB_HOST      : MySQL host (default: mysql.50webs.com)
DB_USER      : MySQL username
DB_PASSWORD  : MySQL password
DB_NAME      : Database name (default: ejaguiar1_stocks)
DB_PORT      : MySQL port (default: 3306)

Typical usage::

    from mysql_pick_adapter import MySQLPickAdapter

    adapter = MySQLPickAdapter()
    active_picks = adapter.fetch_all_active()
    adapter.sync_to_json_store("/tmp/picks_cache.json")
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union

try:
    import pymysql
    from pymysql.cursors import DictCursor
    from pymysql.err import MySQLError, OperationalError
except ImportError as _exc:  # pragma: no cover
    raise ImportError(
        "pymysql is required. Install with: pip install pymysql"
    ) from _exc

logger = logging.getLogger("swarm.mysql")


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _load_db_env_config(db_name: Optional[str] = None) -> Dict[str, Any]:
    """Assemble connection kwargs from environment variables.

    Parameters
    ----------
    db_name:
        Optional override for the database name. When *None* the value is
        read from ``DB_NAME`` env var (falls back to ``ejaguiar1_stocks``).

    Returns
    -------
    dict
        Keyword arguments compatible with ``pymysql.connect``.
    """
    host: str = os.getenv("DB_HOST", "mysql.50webs.com")
    user: str = os.getenv("DB_USER", "")
    password: str = os.getenv("DB_PASSWORD", "")
    name: str = db_name or os.getenv("DB_NAME", "ejaguiar1_stocks")
    port_raw: str = os.getenv("DB_PORT", "3306")
    try:
        port: int = int(port_raw)
    except ValueError:
        logger.warning(
            "Invalid DB_PORT value %r — falling back to 3306", port_raw
        )
        port = 3306

    if not user:
        logger.warning("DB_USER environment variable is not set")
    if not password:
        logger.warning("DB_PASSWORD environment variable is not set")

    return {
        "host": host,
        "user": user,
        "password": password,
        "database": name,
        "port": port,
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "connect_timeout": 10,
    }


# ---------------------------------------------------------------------------
# Row model
# ---------------------------------------------------------------------------

@dataclass
class PickRow:
    """Typed representation of a single trading-pick row."""

    id: int
    ticker: str
    asset_class: str
    direction: str
    entry_time: Optional[str] = None
    entry_price: Optional[float] = None
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    status: str = "active"
    tp: Optional[float] = None
    sl: Optional[float] = None
    qty: Optional[float] = None
    timeframe: Optional[str] = None
    consensus_tier: Optional[str] = None
    regime_at_entry: Optional[Dict[str, Any]] = None
    models_consulted: Optional[Dict[str, Any]] = None
    outcome: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, row: Dict[str, Any]) -> "PickRow":
        """Hydrate a *PickRow* from a raw dictionary (e.g. DictCursor row).

        JSON columns are parsed automatically when they arrive as strings.
        """
        # Parse JSON columns that may still be strings
        for json_col in ("regime_at_entry", "models_consulted", "outcome"):
            val = row.get(json_col)
            if isinstance(val, str):
                try:
                    row[json_col] = json.loads(val)
                except json.JSONDecodeError:
                    row[json_col] = None
        return cls(**{k: v for k, v in row.items() if k in cls.__dataclass_fields__})

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the row back to a plain dictionary."""
        result: Dict[str, Any] = {}
        for key in self.__dataclass_fields__:
            result[key] = getattr(self, key)
        return result


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class MySQLPickAdapter:
    """Production MySQL adapter for trading-pick queries.

    The adapter attempts to connect to the configured MySQL host.  If the
    connection fails on *any* public method call, it transparently falls
    back to reading from a local JSON cache file (``json_store_path``).

    Parameters
    ----------
    db_name:
        Override the default database name.
    json_store_path:
        Path to the JSON fallback / cache file.  Defaults to
        ``/tmp/swarm_picks_cache.json``.
    """

    # Ordered list of table names to try when probing the schema.
    _TABLE_CANDIDATES: List[str] = ["trading_picks", "picks"]

    def __init__(
        self,
        db_name: Optional[str] = None,
        json_store_path: Union[str, Path] = "/tmp/swarm_picks_cache.json",
    ) -> None:
        self._conn_kwargs = _load_db_env_config(db_name=db_name)
        self._json_store_path = Path(json_store_path)
        self._resolved_table: Optional[str] = None

    # -- internal helpers --------------------------------------------------

    @contextmanager
    def _connect(self) -> Generator[pymysql.Connection, None, None]:
        """Yield a live pymysql connection, properly closing it on exit.

        Raises
        ------
        OperationalError
            If the connection cannot be established.
        """
        conn: Optional[pymysql.Connection] = None
        try:
            conn = pymysql.connect(**self._conn_kwargs)
            logger.debug(
                "Connected to %s:%s/%s",
                self._conn_kwargs["host"],
                self._conn_kwargs["port"],
                self._conn_kwargs["database"],
            )
            yield conn
        except OperationalError as exc:
            logger.error("MySQL connection failed: %s", exc)
            raise
        finally:
            if conn is not None:
                conn.close()
                logger.debug("MySQL connection closed.")

    def _resolve_table(self, conn: pymysql.Connection) -> str:
        """Probe the database and return the first existing table candidate.

        The result is cached in ``self._resolved_table`` so the probe only
        runs once per adapter instance.
        """
        if self._resolved_table is not None:
            return self._resolved_table

        with conn.cursor() as cur:
            for table in self._TABLE_CANDIDATES:
                cur.execute(
                    "SHOW TABLES LIKE %s",
                    (table,),
                )
                if cur.fetchone() is not None:
                    logger.info("Resolved table: %s", table)
                    self._resolved_table = table
                    return table

        raise RuntimeError(
            f"None of the expected tables exist: {self._TABLE_CANDIDATES}"
        )

    def _run_query(
        self, sql: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Execute *sql* and return the full result set as a list of dicts."""
        with self._connect() as conn:
            table = self._resolve_table(conn)
            # Inject resolved table name if placeholder present
            if "{table}" in sql:
                sql = sql.replace("{table}", f"`{table}`")
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows: List[Dict[str, Any]] = cur.fetchall()
                logger.debug("Query returned %d row(s)", len(rows))
                return rows

    # -- JSON fallback -----------------------------------------------------

    def _read_json_fallback(self) -> List[Dict[str, Any]]:
        """Load cached picks from the local JSON file.

        Returns
        -------
        list
            The parsed JSON content.  Returns an empty list when the file
            does not exist or cannot be parsed.
        """
        path = self._json_store_path
        if not path.exists():
            logger.warning("JSON fallback file not found: %s", path)
            return []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data: List[Dict[str, Any]] = json.load(fh)
            logger.info(
                "JSON fallback loaded: %d pick(s) from %s", len(data), path
            )
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to read JSON fallback %s: %s", path, exc)
            return []

    def _execute_with_fallback(
        self, sql: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Run *sql* against MySQL, falling back to JSON on failure."""
        try:
            return self._run_query(sql, params)
        except (OperationalError, MySQLError, RuntimeError) as exc:
            logger.warning(
                "DB query failed (%s) — falling back to JSON store", exc
            )
            # Apply client-side filtering on the fallback data when possible
            return self._filter_fallback(sql, params)

    def _filter_fallback(
        self, sql: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Naïve client-side filtering for the most common query patterns.

        This is **not** a SQL engine — it handles the simple ``WHERE``
        clauses generated by this adapter so that fallback behaviour remains
        useful.
        """
        all_picks = self._read_json_fallback()
        status_filter: Optional[str] = None
        asset_filter: Optional[str] = None

        # Extract simple equality predicates from the SQL we generate
        if params and "%s" in sql:
            # Status filter
            if "status =" in sql or "status = " in sql:
                status_filter = params[0] if params else None
            # Asset-class filter
            if "asset_class =" in sql or "asset_class = " in sql:
                asset_filter = params[-1] if params else None

        filtered: List[Dict[str, Any]] = []
        for pick in all_picks:
            if status_filter and pick.get("status") != status_filter:
                continue
            if asset_filter and pick.get("asset_class") != asset_filter:
                continue
            filtered.append(pick)
        return filtered

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_picks(
        self,
        status: Optional[str] = None,
        asset_class: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch trading picks with optional filters.

        Parameters
        ----------
        status:
            Filter by pick status, e.g. ``'active'`` or ``'closed'``.
        asset_class:
            Filter by asset class, e.g. ``'crypto'``, ``'equity'``.

        Returns
        -------
        list[dict]
            Raw dictionary rows (compatible with the statistical engine).
        """
        conditions: List[str] = []
        params: List[Any] = []

        if status is not None:
            conditions.append("status = %s")
            params.append(status)
        if asset_class is not None:
            conditions.append("asset_class = %s")
            params.append(asset_class)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = (
            f"SELECT * FROM {{table}} WHERE {where_clause} "
            "ORDER BY entry_time DESC"
        )

        logger.info(
            "fetch_picks(status=%s, asset_class=%s)", status, asset_class
        )
        rows = self._execute_with_fallback(sql, tuple(params) if params else None)
        return rows

    def fetch_all_active(self) -> List[Dict[str, Any]]:
        """Return every pick whose *status* equals ``'active'``."""
        logger.info("fetch_all_active()")
        return self.fetch_picks(status="active")

    def fetch_all_closed(self) -> List[Dict[str, Any]]:
        """Return every pick whose *status* equals ``'closed'``."""
        logger.info("fetch_all_closed()")
        return self.fetch_picks(status="closed")

    def sync_to_json_store(self, json_path: Optional[Union[str, Path]] = None) -> Path:
        """Dump the full *trading_picks* table to a JSON file.

        Parameters
        ----------
        json_path:
            Destination path.  When *None* the instance default
            ``json_store_path`` is used.

        Returns
        -------
        pathlib.Path
            The path to the written file.
        """
        dest = Path(json_path) if json_path else self._json_store_path
        logger.info("sync_to_json_store → %s", dest)

        rows = self._execute_with_fallback("SELECT * FROM {table} ORDER BY id")
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=2, default=str)

        logger.info("Synced %d pick(s) to %s", len(rows), dest)
        return dest

    # -- introspection helpers -------------------------------------------

    def health_check(self) -> Dict[str, Union[bool, str]]:
        """Quick connectivity check.

        Returns
        -------
        dict
            ``{'ok': bool, 'host': str, 'database': str, 'error': str|None}``
        """
        result: Dict[str, Union[bool, str]] = {
            "ok": False,
            "host": str(self._conn_kwargs["host"]),
            "database": str(self._conn_kwargs["database"]),
            "error": None,
        }
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result["ok"] = True
        except Exception as exc:  # noqa: BLE001
            result["error"] = str(exc)
        return result

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"host={self._conn_kwargs['host']!r}, "
            f"db={self._conn_kwargs['database']!r})"
        )
