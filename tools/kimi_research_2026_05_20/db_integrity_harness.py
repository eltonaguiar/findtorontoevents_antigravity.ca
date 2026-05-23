#!/usr/bin/env python3
"""
================================================================================
DB Integrity Harness — Schema, Referential & Data-Quality Guardian
================================================================================
Continuously validates the findtorontoevents.ca/audit SQLite (or Postgres)
database, detects corruption / drift, repairs common issues automatically,
and reports an integrity score.

Target integrity score:  > 95 %
Current integrity score: ~61 %

Checks
------
1. Schema validation      — expected tables / columns / types / indexes
2. Referential consistency — FK-like relationships across tables
3. Stale-data detection    — picks with no updates in 48 h
4. Orphan cleanup          — dangling references (resolutions without picks, etc.)
5. Automated repair        — missing asset_class, corrupted pnl_pct, etc.
6. Integrity score         — weighted composite 0-100

Usage
-----
    python db_integrity_harness.py --db-path ./alpha_engine.db
    # or inside Python:
    from db_integrity_harness import IntegrityHarness
    harness = IntegrityHarness("./alpha_engine.db")
    report = harness.run_full_check()
    print(report.score, report.issues)

Author: Alpha Engine Team
Date: 2026-05-20
================================================================================
"""
from __future__ import annotations

import json
import logging
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

import numpy as np
import pandas as pd

logger = logging.getLogger("db_integrity_harness")


def _setup_logging(level: int = logging.INFO) -> None:
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(level)


_setup_logging()

__version__ = "2.0.0"
__date__ = "2026-05-20"

# ---------------------------------------------------------------------------
# Expected schema contract
# ---------------------------------------------------------------------------

class ColumnSpec:
    """Description of a column that MUST exist."""

    def __init__(
        self,
        name: str,
        dtype: str,
        nullable: bool = True,
        default: Any = None,
    ) -> None:
        self.name = name
        self.dtype = dtype.upper()
        self.nullable = nullable
        self.default = default


EXPECTED_SCHEMA: Dict[str, List[ColumnSpec]] = {
    "picks": [
        ColumnSpec("pick_id", "INTEGER", nullable=False),
        ColumnSpec("symbol", "TEXT", nullable=False),
        ColumnSpec("asset_class", "TEXT", nullable=False, default="EQUITY"),
        ColumnSpec("direction", "TEXT", nullable=False, default="LONG"),
        ColumnSpec("entry_price", "REAL"),
        ColumnSpec("exit_price", "REAL"),
        ColumnSpec("entry_time", "TEXT", nullable=False),
        ColumnSpec("exit_time", "TEXT"),
        ColumnSpec("stop_loss", "REAL"),
        ColumnSpec("take_profit", "REAL"),
        ColumnSpec("confidence", "REAL", default=0.5),
        ColumnSpec("status", "TEXT", default="unresolved"),
        ColumnSpec("pnl_pct", "REAL"),
        ColumnSpec("resolved_at", "TEXT"),
        ColumnSpec("outcome", "TEXT"),
        ColumnSpec("metadata", "TEXT", default="{}"),
        ColumnSpec("resolution_version", "TEXT"),
        ColumnSpec("created_at", "TEXT"),
        ColumnSpec("updated_at", "TEXT"),
    ],
    "resolution_audit": [
        ColumnSpec("audit_id", "INTEGER", nullable=False),
        ColumnSpec("pick_id", "INTEGER", nullable=False),
        ColumnSpec("status", "TEXT", nullable=False),
        ColumnSpec("outcome", "TEXT"),
        ColumnSpec("pnl_pct", "REAL"),
        ColumnSpec("exit_price", "REAL"),
        ColumnSpec("resolution_time_ms", "REAL"),
        ColumnSpec("slippage_estimate", "REAL"),
        ColumnSpec("market_impact_estimate", "REAL"),
        ColumnSpec("error_message", "TEXT"),
        ColumnSpec("resolver_version", "TEXT"),
        ColumnSpec("resolved_at", "TEXT", nullable=False),
    ],
    "strategies": [
        ColumnSpec("strategy_id", "INTEGER", nullable=False),
        ColumnSpec("strategy_name", "TEXT", nullable=False),
        ColumnSpec("category", "TEXT"),
        ColumnSpec("asset_class", "TEXT"),
        ColumnSpec("is_active", "INTEGER", default=1),
        ColumnSpec("created_at", "TEXT"),
        ColumnSpec("updated_at", "TEXT"),
    ],
    "strategy_performance": [
        ColumnSpec("perf_id", "INTEGER", nullable=False),
        ColumnSpec("strategy_id", "INTEGER", nullable=False),
        ColumnSpec("sharpe_30d", "REAL"),
        ColumnSpec("sharpe_90d", "REAL"),
        ColumnSpec("total_return", "REAL"),
        ColumnSpec("max_drawdown", "REAL"),
        ColumnSpec("n_trades", "INTEGER"),
        ColumnSpec("win_rate", "REAL"),
        ColumnSpec("computed_at", "TEXT"),
    ],
}

# Indexes that should exist
EXPECTED_INDEXES: Dict[str, List[str]] = {
    "picks": [
        "idx_picks_symbol",
        "idx_picks_status",
        "idx_picks_entry_time",
        "idx_picks_asset_class",
    ],
    "resolution_audit": [
        "idx_audit_pick_id",
        "idx_audit_resolved_at",
    ],
    "strategies": [
        "idx_strategies_name",
        "idx_strategies_active",
    ],
    "strategy_performance": [
        "idx_perf_strategy_id",
        "idx_perf_computed_at",
    ],
}

# Cross-table referential rules: (table, column) -> (parent_table, parent_column)
REFERENTIAL_RULES: List[Tuple[str, str, str, str]] = [
    ("resolution_audit", "pick_id", "picks", "pick_id"),
    ("strategy_performance", "strategy_id", "strategies", "strategy_id"),
]

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Severity(Enum):
    CRITICAL = "critical"    # data loss / corruption risk
    WARNING = "warning"      # sub-optimal but functional
    INFO = "info"            # cosmetic / best-practice


class CheckCategory(Enum):
    SCHEMA = "schema"
    REFERENTIAL = "referential"
    STALE_DATA = "stale_data"
    ORPHAN = "orphan"
    REPAIR = "repair"
    STATISTICS = "statistics"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class IntegrityIssue:
    category: CheckCategory
    severity: Severity
    table: str
    description: str
    count: int = 1
    sql_fix: str = ""
    auto_fixed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "table": self.table,
            "description": self.description,
            "count": self.count,
            "sql_fix": self.sql_fix,
            "auto_fixed": self.auto_fixed,
        }


@dataclass
class IntegrityReport:
    run_at: datetime
    db_path: str
    score: float                    # 0.0 - 100.0
    total_issues: int
    critical_count: int
    warning_count: int
    info_count: int
    auto_fixed_count: int
    issues: List[IntegrityIssue] = field(default_factory=list)
    table_row_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_at": self.run_at.isoformat(),
            "db_path": self.db_path,
            "integrity_score": round(self.score, 2),
            "total_issues": self.total_issues,
            "critical": self.critical_count,
            "warning": self.warning_count,
            "info": self.info_count,
            "auto_fixed": self.auto_fixed_count,
            "table_row_counts": self.table_row_counts,
            "issues": [i.to_dict() for i in self.issues],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------
class IntegrityHarness:
    """Full-spectrum database integrity checker with auto-repair."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.issues: List[IntegrityIssue] = []
        self._auto_fixed = 0
        self._row_counts: Dict[str, int] = {}

    # -- helpers -----------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _tables(self) -> Set[str]:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            return {r[0] for r in cur.fetchall()}

    def _columns(self, table: str) -> Dict[str, str]:
        try:
            with self._conn() as conn:
                cur = conn.execute(f"PRAGMA table_info({table})")
                return {r[1]: r[2].upper() for r in cur.fetchall()}
        except Exception:
            return {}

    def _indexes(self, table: str) -> Set[str]:
        try:
            with self._conn() as conn:
                cur = conn.execute(f"PRAGMA index_list({table})")
                return {r[1] for r in cur.fetchall()}
        except Exception:
            return set()

    def _row_count(self, table: str) -> int:
        try:
            with self._conn() as conn:
                cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
                return cur.fetchone()[0]
        except Exception:
            return -1

    def _add_issue(
        self,
        category: CheckCategory,
        severity: Severity,
        table: str,
        description: str,
        count: int = 1,
        sql_fix: str = "",
        auto_fixed: bool = False,
    ) -> None:
        self.issues.append(
            IntegrityIssue(
                category=category,
                severity=severity,
                table=table,
                description=description,
                count=count,
                sql_fix=sql_fix,
                auto_fixed=auto_fixed,
            )
        )
        if auto_fixed:
            self._auto_fixed += 1

    def _execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        try:
            with self._conn() as conn:
                cur = conn.execute(sql, params)
                conn.commit()
                return cur.rowcount
        except Exception as exc:
            logger.error("SQL execution failed: %s | %s", sql, exc)
            return 0

    # -- 1. Schema validation ----------------------------------------------

    def check_schema(self) -> None:
        """Validate tables, columns, and indexes against EXPECTED_SCHEMA."""
        logger.info("--- Schema Validation ---")
        existing_tables = self._tables()

        for expected_table, expected_cols in EXPECTED_SCHEMA.items():
            if expected_table not in existing_tables:
                self._add_issue(
                    CheckCategory.SCHEMA,
                    Severity.CRITICAL,
                    expected_table,
                    f"Missing table: {expected_table}",
                    sql_fix=f"CREATE TABLE {expected_table} (...); -- see EXPECTED_SCHEMA",
                )
                continue

            # row count for statistics
            self._row_counts[expected_table] = self._row_count(expected_table)

            actual_cols = self._columns(expected_table)
            for col in expected_cols:
                if col.name not in actual_cols:
                    self._add_issue(
                        CheckCategory.SCHEMA,
                        Severity.WARNING,
                        expected_table,
                        f"Missing column: {col.name} ({col.dtype})",
                        sql_fix=f"ALTER TABLE {expected_table} ADD COLUMN {col.name} {col.dtype}",
                    )
                elif actual_cols[col.name] != col.dtype:
                    self._add_issue(
                        CheckCategory.SCHEMA,
                        Severity.INFO,
                        expected_table,
                        f"Type mismatch for {col.name}: expected {col.dtype}, got {actual_cols[col.name]}",
                    )

            # index checks
            actual_indexes = self._indexes(expected_table)
            for idx_name in EXPECTED_INDEXES.get(expected_table, []):
                if idx_name not in actual_indexes:
                    self._add_issue(
                        CheckCategory.SCHEMA,
                        Severity.WARNING,
                        expected_table,
                        f"Missing index: {idx_name}",
                    )

        logger.info("Schema check complete: %d issues", len(self.issues))

    # -- 2. Referential consistency -----------------------------------------

    def check_referential(self) -> None:
        """FK-like checks across tables."""
        logger.info("--- Referential Consistency ---")
        for child_table, child_col, parent_table, parent_col in REFERENTIAL_RULES:
            # check child -> parent orphans
            try:
                with self._conn() as conn:
                    sql = f"""
                        SELECT COUNT(*) FROM {child_table} c
                        LEFT JOIN {parent_table} p ON c.{child_col} = p.{parent_col}
                        WHERE p.{parent_col} IS NULL AND c.{child_col} IS NOT NULL
                    """
                    orphan_count = conn.execute(sql).fetchone()[0]
                    if orphan_count > 0:
                        self._add_issue(
                            CheckCategory.REFERENTIAL,
                            Severity.CRITICAL,
                            child_table,
                            f"{orphan_count} rows in {child_table} reference non-existent {parent_table}.{parent_col}",
                            count=orphan_count,
                            sql_fix=f"DELETE FROM {child_table} WHERE {child_col} NOT IN (SELECT {parent_col} FROM {parent_table});",
                        )
            except Exception as exc:
                self._add_issue(
                    CheckCategory.REFERENTIAL,
                    Severity.WARNING,
                    child_table,
                    f"Referential check error: {exc}",
                )

    # -- 3. Stale data detection -------------------------------------------

    def check_stale_data(self, hours: int = 48) -> None:
        """Find picks with no update in *hours*."""
        logger.info("--- Stale Data Detection (%dh) ---", hours)
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        tables_to_check = [
            ("picks", "updated_at", "entry_time"),
            ("strategies", "updated_at", "created_at"),
        ]
        for table, ts_col, fallback_col in tables_to_check:
            # First check if the timestamp column exists
            cols = self._columns(table)
            check_col = ts_col if ts_col in cols else fallback_col
            if check_col not in cols:
                continue
            try:
                with self._conn() as conn:
                    sql = f"""
                        SELECT COUNT(*) FROM {table}
                        WHERE {check_col} < ?
                        AND (status != 'resolved' OR status IS NULL)
                    """
                    stale_count = conn.execute(sql, (cutoff,)).fetchone()[0]
                    if stale_count > 0:
                        self._add_issue(
                            CheckCategory.STALE_DATA,
                            Severity.WARNING,
                            table,
                            f"{stale_count} rows not updated in {hours}h",
                            count=stale_count,
                        )
            except Exception as exc:
                self._add_issue(
                    CheckCategory.STALE_DATA,
                    Severity.INFO,
                    table,
                    f"Stale check skipped: {exc}",
                )

    # -- 4. Orphan cleanup --------------------------------------------------

    def check_orphans(self) -> None:
        """Detect and optionally remove dangling rows."""
        logger.info("--- Orphan Check ---")
        checks: List[Tuple[str, str, str]] = [
            # (description, table, condition_sql)
            (
                "Resolution audit rows referencing deleted picks",
                "resolution_audit",
                "pick_id NOT IN (SELECT pick_id FROM picks)",
            ),
            (
                "Strategy performance rows referencing deleted strategies",
                "strategy_performance",
                "strategy_id NOT IN (SELECT strategy_id FROM strategies)",
            ),
            (
                "Picks with NULL symbol",
                "picks",
                "symbol IS NULL OR TRIM(symbol) = ''",
            ),
            (
                "Picks with invalid entry_price <= 0",
                "picks",
                "entry_price IS NOT NULL AND entry_price <= 0",
            ),
        ]
        for desc, table, condition in checks:
            try:
                with self._conn() as conn:
                    sql = f"SELECT COUNT(*) FROM {table} WHERE {condition}"
                    count = conn.execute(sql).fetchone()[0]
                    if count > 0:
                        self._add_issue(
                            CheckCategory.ORPHAN,
                            Severity.WARNING,
                            table,
                            f"{count} {desc}",
                            count=count,
                            sql_fix=f"DELETE FROM {table} WHERE {condition}",
                        )
            except Exception as exc:
                self._add_issue(
                    CheckCategory.ORPHAN, Severity.INFO, table, f"Orphan check error: {exc}"
                )

    # -- 5. Automated repair ------------------------------------------------

    def run_repair(self, dry_run: bool = True) -> int:
        """Fix common issues automatically.  Returns number of fixes applied."""
        logger.info("--- Automated Repair (dry_run=%s) ---", dry_run)
        fixes_applied = 0

        # 5a. missing asset_class
        try:
            with self._conn() as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM picks WHERE asset_class IS NULL OR TRIM(asset_class) = ''"
                ).fetchone()[0]
                if count > 0:
                    fix_sql = "UPDATE picks SET asset_class = 'EQUITY' WHERE asset_class IS NULL OR TRIM(asset_class) = ''"
                    if dry_run:
                        self._add_issue(
                            CheckCategory.REPAIR,
                            Severity.INFO,
                            "picks",
                            f"Would fix {count} rows with missing asset_class -> 'EQUITY'",
                            count=count,
                            sql_fix=fix_sql,
                            auto_fixed=False,
                        )
                    else:
                        applied = self._execute(fix_sql)
                        self._add_issue(
                            CheckCategory.REPAIR,
                            Severity.INFO,
                            "picks",
                            f"Fixed {applied} rows with missing asset_class",
                            count=applied,
                            auto_fixed=True,
                        )
                        fixes_applied += applied
        except Exception as exc:
            logger.error("Repair asset_class error: %s", exc)

        # 5b. corrupted pnl_pct (NaN, Inf, > 500%, < -100%)
        try:
            with self._conn() as conn:
                count = conn.execute(
                    """SELECT COUNT(*) FROM picks
                    WHERE pnl_pct IS NOT NULL
                    AND (pnl_pct != pnl_pct  -- NaN check
                         OR pnl_pct > 5.0
                         OR pnl_pct < -1.0)"""
                ).fetchone()[0]
                if count > 0:
                    fix_sql = "UPDATE picks SET pnl_pct = NULL WHERE pnl_pct IS NOT NULL AND (pnl_pct != pnl_pct OR pnl_pct > 5.0 OR pnl_pct < -1.0)"
                    if dry_run:
                        self._add_issue(
                            CheckCategory.REPAIR,
                            Severity.INFO,
                            "picks",
                            f"Would clear {count} corrupted pnl_pct values",
                            count=count,
                            sql_fix=fix_sql,
                            auto_fixed=False,
                        )
                    else:
                        applied = self._execute(fix_sql)
                        self._add_issue(
                            CheckCategory.REPAIR,
                            Severity.INFO,
                            "picks",
                            f"Cleared {applied} corrupted pnl_pct values",
                            count=applied,
                            auto_fixed=True,
                        )
                        fixes_applied += applied
        except Exception as exc:
            logger.error("Repair pnl_pct error: %s", exc)

        # 5c. missing status
        try:
            with self._conn() as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM picks WHERE status IS NULL OR TRIM(status) = ''"
                ).fetchone()[0]
                if count > 0:
                    fix_sql = "UPDATE picks SET status = 'unresolved' WHERE status IS NULL OR TRIM(status) = ''"
                    if dry_run:
                        self._add_issue(
                            CheckCategory.REPAIR,
                            Severity.INFO,
                            "picks",
                            f"Would fix {count} rows with missing status -> 'unresolved'",
                            count=count,
                            sql_fix=fix_sql,
                            auto_fixed=False,
                        )
                    else:
                        applied = self._execute(fix_sql)
                        self._add_issue(
                            CheckCategory.REPAIR,
                            Severity.INFO,
                            "picks",
                            f"Fixed {applied} rows with missing status",
                            count=applied,
                            auto_fixed=True,
                        )
                        fixes_applied += applied
        except Exception as exc:
            logger.error("Repair status error: %s", exc)

        # 5d. picks with exit_time but no exit_price (stuck)
        try:
            with self._conn() as conn:
                count = conn.execute(
                    """SELECT COUNT(*) FROM picks
                    WHERE exit_time IS NOT NULL AND exit_price IS NULL AND status != 'resolved'"""
                ).fetchone()[0]
                if count > 0:
                    fix_sql = "UPDATE picks SET status = 'stale' WHERE exit_time IS NOT NULL AND exit_price IS NULL AND status != 'resolved'"
                    if dry_run:
                        self._add_issue(
                            CheckCategory.REPAIR,
                            Severity.INFO,
                            "picks",
                            f"Would mark {count} stuck picks as 'stale'",
                            count=count,
                            sql_fix=fix_sql,
                            auto_fixed=False,
                        )
                    else:
                        applied = self._execute(fix_sql)
                        self._add_issue(
                            CheckCategory.REPAIR,
                            Severity.INFO,
                            "picks",
                            f"Marked {applied} stuck picks as 'stale'",
                            count=applied,
                            auto_fixed=True,
                        )
                        fixes_applied += applied
        except Exception as exc:
            logger.error("Repair stuck picks error: %s", exc)

        # 5e. duplicate symbol+entry_time combinations
        try:
            with self._conn() as conn:
                sql = """
                    SELECT symbol, entry_time, COUNT(*) as cnt
                    FROM picks
                    GROUP BY symbol, entry_time
                    HAVING cnt > 1
                """
                dups = conn.execute(sql).fetchall()
                if dups:
                    total_dups = sum(r[2] - 1 for r in dups)
                    self._add_issue(
                        CheckCategory.REPAIR,
                        Severity.WARNING,
                        "picks",
                        f"{total_dups} duplicate pick rows detected (same symbol+entry_time)",
                        count=total_dups,
                        sql_fix="DELETE FROM picks WHERE rowid NOT IN (SELECT MIN(rowid) FROM picks GROUP BY symbol, entry_time);",
                    )
        except Exception as exc:
            logger.error("Duplicate check error: %s", exc)

        logger.info("Repair pass complete: %d fixes applied", fixes_applied)
        return fixes_applied

    # -- 6. Score computation -----------------------------------------------

    @staticmethod
    def _compute_score(issues: List[IntegrityIssue]) -> float:
        """Weighted score 0-100 based on issue severity."""
        if not issues:
            return 100.0
        weights = {
            Severity.CRITICAL: 15.0,
            Severity.WARNING: 5.0,
            Severity.INFO: 0.5,
        }
        penalty = sum(
            weights[i.severity] * max(1, np.log1p(i.count))
            for i in issues
        )
        return max(0.0, 100.0 - penalty)

    # -- Main entry point ---------------------------------------------------

    def run_full_check(
        self,
        auto_repair: bool = False,
        stale_hours: int = 48,
    ) -> IntegrityReport:
        """Run all checks and return a report."""
        self.issues = []
        self._auto_fixed = 0
        self._row_counts = {}

        logger.info("=== DB Integrity Harness V%s starting ===", __version__)

        self.check_schema()
        self.check_referential()
        self.check_stale_data(hours=stale_hours)
        self.check_orphans()
        self.run_repair(dry_run=not auto_repair)

        # Compute row counts for all tables
        for t in self._tables():
            if t not in self._row_counts:
                self._row_counts[t] = self._row_count(t)

        score = self._compute_score(self.issues)

        critical = sum(1 for i in self.issues if i.severity == Severity.CRITICAL)
        warning = sum(1 for i in self.issues if i.severity == Severity.WARNING)
        info = sum(1 for i in self.issues if i.severity == Severity.INFO)

        report = IntegrityReport(
            run_at=datetime.utcnow(),
            db_path=self.db_path,
            score=score,
            total_issues=len(self.issues),
            critical_count=critical,
            warning_count=warning,
            info_count=info,
            auto_fixed_count=self._auto_fixed,
            issues=self.issues,
            table_row_counts=self._row_counts,
        )

        logger.info(
            "=== Integrity Score: %.1f / 100 | Issues: %d (C:%d W:%d I:%d) ===",
            score, len(self.issues), critical, warning, info,
        )
        return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="DB Integrity Harness")
    parser.add_argument("--db-path", required=True, help="Path to SQLite DB")
    parser.add_argument("--auto-repair", action="store_true", help="Apply fixes")
    parser.add_argument("--stale-hours", type=int, default=48)
    parser.add_argument("--json-out", default=None, help="Write JSON report to file")
    args = parser.parse_args()

    harness = IntegrityHarness(args.db_path)
    report = harness.run_full_check(
        auto_repair=args.auto_repair, stale_hours=args.stale_hours
    )

    print(report.to_json())

    if args.json_out:
        Path(args.json_out).write_text(report.to_json())
        logger.info("Report written to %s", args.json_out)


if __name__ == "__main__":
    main()
