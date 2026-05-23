"""
Pick Lifecycle Logger (M-110 / PR-T1).

Assigns stable pick_ids and tracks each pick from scan → filter/score → active → closed.
Wires into passes_active_gate() via tag_futures_monitor() already; full decorator
integration planned in PR-T2.

Storage: SQLite (audit_trail/audit_trail.db) — zero new infrastructure dependency.
Upgrade path: swap _conn() for MySQL when at_pick_features table is provisioned.

Kimi spec reference: reports/PICK_TRACEABILITY_SPEC_2026-05-18.md §3, §4.3.1
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DB_PATH = _REPO_ROOT / "audit_trail" / "audit_trail.db"

# ---------------------------------------------------------------------------
# Schema (idempotent CREATE IF NOT EXISTS)
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS pick_lifecycle_log (
    pick_id          TEXT    NOT NULL PRIMARY KEY,
    scan_timestamp   TEXT    NOT NULL,
    symbol           TEXT    NOT NULL,
    asset_class      TEXT    NOT NULL,
    strategy         TEXT    NOT NULL,
    source_system    TEXT    NOT NULL DEFAULT '',
    direction        TEXT    NOT NULL DEFAULT '',
    entry_price      REAL,
    exit_price       REAL,
    pnl_pct          REAL,
    confidence       REAL,
    current_stage    TEXT    NOT NULL DEFAULT 'scanned',
    stage_timestamp  TEXT    NOT NULL,
    scan_metadata    TEXT,
    created_at       TEXT    NOT NULL,
    updated_at       TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pll_scan_ts  ON pick_lifecycle_log(scan_timestamp);
CREATE INDEX IF NOT EXISTS idx_pll_ac_stage ON pick_lifecycle_log(asset_class, current_stage);
CREATE INDEX IF NOT EXISTS idx_pll_symbol   ON pick_lifecycle_log(symbol, strategy);

CREATE TABLE IF NOT EXISTS filter_event_log (
    filter_event_id  TEXT    NOT NULL PRIMARY KEY,
    pick_id          TEXT    NOT NULL REFERENCES pick_lifecycle_log(pick_id),
    gate_name        TEXT    NOT NULL,
    rule_id          TEXT    NOT NULL DEFAULT '',
    rule_type        TEXT    NOT NULL DEFAULT 'CUSTOM',
    filter_reason    TEXT    NOT NULL,
    filter_context   TEXT    NOT NULL DEFAULT '{}',
    filter_timestamp TEXT    NOT NULL,
    pick_values      TEXT,
    created_at       TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fel_pick_id   ON filter_event_log(pick_id);
CREATE INDEX IF NOT EXISTS idx_fel_gate_name ON filter_event_log(gate_name);
CREATE INDEX IF NOT EXISTS idx_fel_ts        ON filter_event_log(filter_timestamp);

CREATE TABLE IF NOT EXISTS gate_pass_log (
    pass_id        INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    pick_id        TEXT    NOT NULL REFERENCES pick_lifecycle_log(pick_id),
    gate_name      TEXT    NOT NULL,
    gate_order     INTEGER NOT NULL DEFAULT 0,
    score_at_gate  REAL,
    gate_params    TEXT,
    passed_at      TEXT    NOT NULL,
    created_at     TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gpl_pick_id   ON gate_pass_log(pick_id);
CREATE INDEX IF NOT EXISTS idx_gpl_gate_name ON gate_pass_log(gate_name);
"""

# Gate evaluation order (lower = evaluated first)
_GATE_ORDER: dict[str, int] = {
    "format_validation": 1,
    "symbol_blocklist": 2,
    "strategy_blocklist": 3,
    "asset_strategy_pairs": 4,
    "asset_strategy_symbol_triples": 5,
    "direction_triples": 6,
    "source_system_blocklist": 7,
    "confidence_threshold": 8,
    "score_booster": 9,
    "regime_gate": 10,
    "tier_gate": 11,
    "meta_label": 12,
}

_RULE_TYPES: dict[str, str] = {
    "RULE-BLOCK": "BLOCKLIST",
    "RULE-THRESH": "THRESHOLD",
    "RULE-REGIME": "REGIME",
    "RULE-TIER": "TIER",
    "RULE-FMT": "FORMAT",
    "RULE-CUST": "CUSTOM",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PickEvent:
    symbol: str
    asset_class: str
    strategy: str
    source_system: str = ""
    direction: str = ""
    confidence: Optional[float] = None
    entry_price: Optional[float] = None
    metadata: Optional[dict] = None


@dataclass
class CloseEvent:
    pick_id: str
    exit_price: float
    pnl_pct: float
    exit_reason: str = "unknown"


@dataclass
class FilterTraceback:
    pick_id: str
    scan_timestamp: str
    symbol: str
    asset_class: str
    strategy: str
    direction: str
    final_stage: str
    total_gates_evaluated: int
    gate_evaluations: list
    filter_summary: dict


# ---------------------------------------------------------------------------
# Core logger (singleton, thread-safe, batch writes)
# ---------------------------------------------------------------------------

class PickLifecycleLogger:
    """Singleton lifecycle logger. Fail-soft — never crashes the pick pipeline."""

    _instance: Optional["PickLifecycleLogger"] = None
    _lock = threading.Lock()
    _BATCH_SIZE = 50
    _FLUSH_INTERVAL = 5.0  # seconds

    def __new__(cls) -> "PickLifecycleLogger":
        with cls._lock:
            if cls._instance is None:
                inst = object.__new__(cls)
                inst._init()
                cls._instance = inst
        return cls._instance

    @classmethod
    def get_instance(cls) -> "PickLifecycleLogger":
        return cls()

    def _init(self) -> None:
        self._db_path = _DB_PATH
        self._write_lock = threading.Lock()
        self._batch: list[tuple] = []
        self._last_flush = time.monotonic()
        try:
            self._ensure_schema()
        except Exception as exc:
            logger.warning("pick_lifecycle_logger: schema init failed: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_scan(self, event: PickEvent) -> str:
        """Log a new pick scan; returns a stable pick_id (UUID4)."""
        pick_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO pick_lifecycle_log
                       (pick_id, scan_timestamp, symbol, asset_class, strategy,
                        source_system, direction, confidence, entry_price,
                        current_stage, stage_timestamp, scan_metadata, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,'scanned',?,?,?,?)""",
                    (
                        pick_id, now, event.symbol, event.asset_class, event.strategy,
                        event.source_system or "", event.direction or "",
                        event.confidence, event.entry_price,
                        now,
                        json.dumps(event.metadata) if event.metadata else None,
                        now, now,
                    ),
                )
        except Exception as exc:
            logger.debug("pick_lifecycle_logger.log_scan failed: %s", exc)
        return pick_id

    def transition_stage(self, pick_id: str, new_stage: str) -> None:
        """Move pick to a new lifecycle stage."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self._conn() as conn:
                conn.execute(
                    "UPDATE pick_lifecycle_log SET current_stage=?, stage_timestamp=?, updated_at=? WHERE pick_id=?",
                    (new_stage, now, now, pick_id),
                )
        except Exception as exc:
            logger.debug("pick_lifecycle_logger.transition_stage failed: %s", exc)

    def log_gate_pass(
        self,
        pick_id: str,
        gate_name: str,
        score_at_gate: Optional[float] = None,
        gate_params: Optional[dict] = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        order = _GATE_ORDER.get(gate_name, 99)
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO gate_pass_log
                       (pick_id, gate_name, gate_order, score_at_gate, gate_params, passed_at, created_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (pick_id, gate_name, order, score_at_gate,
                     json.dumps(gate_params) if gate_params else None, now, now),
                )
        except Exception as exc:
            logger.debug("pick_lifecycle_logger.log_gate_pass failed: %s", exc)

    def update_confidence(self, pick_id: str, confidence: float) -> None:
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self._conn() as conn:
                conn.execute(
                    "UPDATE pick_lifecycle_log SET confidence=?, updated_at=? WHERE pick_id=?",
                    (confidence, now, pick_id),
                )
        except Exception as exc:
            logger.debug("pick_lifecycle_logger.update_confidence failed: %s", exc)

    def log_active(self, pick_id: str, entry_price: float) -> None:
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self._conn() as conn:
                conn.execute(
                    """UPDATE pick_lifecycle_log
                       SET current_stage='active', entry_price=?, stage_timestamp=?, updated_at=?
                       WHERE pick_id=?""",
                    (entry_price, now, now, pick_id),
                )
        except Exception as exc:
            logger.debug("pick_lifecycle_logger.log_active failed: %s", exc)

    def log_close(self, event: CloseEvent) -> None:
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self._conn() as conn:
                conn.execute(
                    """UPDATE pick_lifecycle_log
                       SET current_stage='closed', exit_price=?, pnl_pct=?,
                           stage_timestamp=?, updated_at=?
                       WHERE pick_id=?""",
                    (event.exit_price, event.pnl_pct, now, now, event.pick_id),
                )
        except Exception as exc:
            logger.debug("pick_lifecycle_logger.log_close failed: %s", exc)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(_DDL)


# ---------------------------------------------------------------------------
# Filter traceback engine (singleton)
# ---------------------------------------------------------------------------

class FilterTracebackEngine:
    """Logs gate rejections and reconstructs full filter traceback per pick."""

    _instance: Optional["FilterTracebackEngine"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "FilterTracebackEngine":
        with cls._lock:
            if cls._instance is None:
                inst = object.__new__(cls)
                inst._db_path = _DB_PATH
                cls._instance = inst
        return cls._instance

    @classmethod
    def get_instance(cls) -> "FilterTracebackEngine":
        return cls()

    def log_filter(
        self,
        pick_id: str,
        gate_name: str,
        reason: str,
        rule_id: str = "",
        context: Optional[dict] = None,
        pick_values: Optional[dict] = None,
    ) -> None:
        """Record a gate rejection for this pick."""
        now = datetime.now(timezone.utc).isoformat()
        rule_type = _RULE_TYPES.get(
            next((k for k in _RULE_TYPES if rule_id.startswith(k)), "RULE-CUST"),
            "CUSTOM",
        )
        try:
            conn = sqlite3.connect(str(self._db_path), timeout=5.0)
            with conn:
                conn.execute(
                    """INSERT INTO filter_event_log
                       (filter_event_id, pick_id, gate_name, rule_id, rule_type,
                        filter_reason, filter_context, filter_timestamp, pick_values, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        str(uuid.uuid4()), pick_id, gate_name, rule_id or "", rule_type,
                        reason,
                        json.dumps(context or {}),
                        now,
                        json.dumps(pick_values) if pick_values else None,
                        now,
                    ),
                )
        except Exception as exc:
            logger.debug("filter_traceback_engine.log_filter failed: %s", exc)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def get_traceback(self, pick_id: str) -> Optional[FilterTraceback]:
        """Reconstruct full gate-by-gate evaluation history for a pick."""
        try:
            conn = sqlite3.connect(str(self._db_path), timeout=5.0)
            conn.row_factory = sqlite3.Row
            with conn:
                row = conn.execute(
                    "SELECT * FROM pick_lifecycle_log WHERE pick_id=?", (pick_id,)
                ).fetchone()
                if not row:
                    return None

                filters = conn.execute(
                    "SELECT * FROM filter_event_log WHERE pick_id=? ORDER BY filter_timestamp",
                    (pick_id,),
                ).fetchall()

                passes = conn.execute(
                    "SELECT * FROM gate_pass_log WHERE pick_id=? ORDER BY gate_order",
                    (pick_id,),
                ).fetchall()

            gate_evals = [
                {
                    "gate_name": r["gate_name"],
                    "result": "PASS",
                    "gate_order": r["gate_order"],
                    "score_at_gate": r["score_at_gate"],
                    "timestamp": r["passed_at"],
                }
                for r in passes
            ] + [
                {
                    "gate_name": r["gate_name"],
                    "result": "FAIL",
                    "rule_id": r["rule_id"],
                    "rule_type": r["rule_type"],
                    "reason": r["filter_reason"],
                    "timestamp": r["filter_timestamp"],
                }
                for r in filters
            ]
            gate_evals.sort(key=lambda e: e.get("timestamp", ""))

            filter_summary: dict[str, int] = {}
            for f in filters:
                filter_summary[f["gate_name"]] = filter_summary.get(f["gate_name"], 0) + 1

            return FilterTraceback(
                pick_id=pick_id,
                scan_timestamp=row["scan_timestamp"],
                symbol=row["symbol"],
                asset_class=row["asset_class"],
                strategy=row["strategy"],
                direction=row["direction"],
                final_stage=row["current_stage"],
                total_gates_evaluated=len(gate_evals),
                gate_evaluations=gate_evals,
                filter_summary=filter_summary,
            )
        except Exception as exc:
            logger.debug("filter_traceback_engine.get_traceback failed: %s", exc)
            return None

    def get_filter_distribution(self, days: int = 7, asset_class: Optional[str] = None) -> dict[str, int]:
        """Count filter rejections per gate over the last N days."""
        cutoff = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        try:
            conn = sqlite3.connect(str(self._db_path), timeout=5.0)
            with conn:
                if asset_class:
                    rows = conn.execute(
                        """SELECT f.gate_name, COUNT(*) as cnt
                           FROM filter_event_log f
                           JOIN pick_lifecycle_log p ON f.pick_id = p.pick_id
                           WHERE f.filter_timestamp >= ? AND p.asset_class = ?
                           GROUP BY f.gate_name ORDER BY cnt DESC""",
                        (cutoff, asset_class),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """SELECT gate_name, COUNT(*) as cnt
                           FROM filter_event_log WHERE filter_timestamp >= ?
                           GROUP BY gate_name ORDER BY cnt DESC""",
                        (cutoff,),
                    ).fetchall()
            return {r[0]: r[1] for r in rows}
        except Exception as exc:
            logger.debug("filter_traceback_engine.get_filter_distribution failed: %s", exc)
            return {}


# ---------------------------------------------------------------------------
# Module-level singletons (lazy init — never fail on import)
# ---------------------------------------------------------------------------

def get_logger() -> PickLifecycleLogger:
    """Get (or create) the singleton PickLifecycleLogger. Fail-soft."""
    try:
        return PickLifecycleLogger.get_instance()
    except Exception:
        return _NullLogger()  # type: ignore[return-value]


def get_tracer() -> FilterTracebackEngine:
    """Get (or create) the singleton FilterTracebackEngine. Fail-soft."""
    try:
        return FilterTracebackEngine.get_instance()
    except Exception:
        return _NullTracer()  # type: ignore[return-value]


class _NullLogger:
    """No-op fallback when DB is unavailable."""
    def log_scan(self, event: Any) -> str: return ""
    def transition_stage(self, *a: Any) -> None: pass
    def log_gate_pass(self, *a: Any, **kw: Any) -> None: pass
    def update_confidence(self, *a: Any) -> None: pass
    def log_active(self, *a: Any) -> None: pass
    def log_close(self, *a: Any) -> None: pass


class _NullTracer:
    def log_filter(self, *a: Any, **kw: Any) -> None: pass
    def get_traceback(self, *a: Any) -> None: return None
    def get_filter_distribution(self, *a: Any) -> dict: return {}
