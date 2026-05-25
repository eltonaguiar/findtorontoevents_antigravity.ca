#!/usr/bin/env python3
"""
Tests for tools/cleanup_ghost_rows.py

Uses mocking to simulate MySQL queries and connection behavior.
No real database connection required.

Run: python -m pytest tools/test_ghost_cleanup.py -v
   or: python tools/test_ghost_cleanup.py
"""
from __future__ import annotations

import sys
import unittest
from unittest.mock import MagicMock, patch, call

# Ensure tools/ is importable
sys.path.insert(0, "/home/eaguiar2015/findtorontoevents_antigravity.ca")

from tools.cleanup_ghost_rows import (
    build_delete_sql,
    discover_ghost_cohorts,
    run_cleanup,
    DEFAULT_MIN_COHORT_SIZE,
    DEFAULT_MAX_DELETES,
)


class MockCursor:
    """A mock cursor that tracks execute calls and returns pre-seeded results."""

    def __init__(self):
        self.fetch_results = []  # results returned by fetchall/fetchone
        self.execute_returns = []  # values returned by execute() (affected rows)
        self.executed = []
        self._closed = False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        # Return next seeded execute value, or 0
        if self.execute_returns:
            val = self.execute_returns.pop(0)
            if isinstance(val, Exception):
                raise val
            return val
        return 0

    def fetchone(self):
        if self.fetch_results:
            return self.fetch_results.pop(0)
        return None

    def fetchall(self):
        rows = list(self.fetch_results)
        self.fetch_results = []
        return rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._closed = True


class MockConnection:
    """A mock pymysql connection."""

    def __init__(self, execute_returns=None, fetch_results=None):
        self.cursor_instance = MockCursor()
        if execute_returns:
            self.cursor_instance.execute_returns = list(execute_returns)
        if fetch_results:
            self.cursor_instance.fetch_results = list(fetch_results)
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


class TestBuildDeleteSQL(unittest.TestCase):
    """Test SQL generation for ghost row deletion."""

    def _cohort(self, **overrides):
        base = {
            "strategy": "test_strat",
            "symbol": "TESTUSDT",
            "direction": "LONG",
            "entry_price": 1.234,
            "count": 10,
            "min_id": 100,
            "max_id": 109,
        }
        base.update(overrides)
        return base

    def test_basic_delete_sql(self):
        """Delete all rows in cohort except the one with min_id."""
        cohort = self._cohort()
        sql, params = build_delete_sql(cohort)

        self.assertIn("DELETE FROM", sql)
        self.assertIn("`bt_backtest_trades`", sql)
        self.assertIn("`strategy` = %s", sql)
        self.assertIn("`symbol` = %s", sql)
        self.assertIn("`direction` = %s", sql)
        self.assertIn("`entry_price` = %s", sql)
        self.assertIn("`id` != %s", sql)
        self.assertIn("test_strat", params)
        self.assertIn("TESTUSDT", params)
        self.assertIn("LONG", params)
        self.assertIn(1.234, params)
        self.assertIn(100, params)  # min_id to keep

    def test_delete_sql_no_limit_by_default(self):
        """No LIMIT clause when limit is None."""
        sql, _ = build_delete_sql(self._cohort())
        self.assertNotIn("LIMIT", sql)

    def test_delete_sql_with_limit(self):
        """LIMIT clause added when specified."""
        sql, _ = build_delete_sql(self._cohort(), limit=500)
        self.assertIn("LIMIT 500", sql)

    def test_delete_sql_params_count(self):
        """Exactly 5 params: 3 cohort cols + entry_price + min_id."""
        _, params = build_delete_sql(self._cohort())
        self.assertEqual(len(params), 5)

    def test_delete_sql_with_string_entry_price(self):
        """Handles string entry_price values."""
        cohort = self._cohort(entry_price="500000")
        sql, params = build_delete_sql(cohort)
        self.assertIn("500000", params)

    def test_delete_sql_short_direction(self):
        """Works for SHORT direction."""
        cohort = self._cohort(direction="SHORT")
        _, params = build_delete_sql(cohort)
        self.assertIn("SHORT", params)


class TestDiscoverGhostCohorts(unittest.TestCase):
    """Test cohort detection SQL and parsing."""

    def test_discover_cohorts_builds_correct_sql(self):
        """SQL should group by strategy, symbol, direction, entry_price."""
        mock_conn = MagicMock()
        mock_cur = MockCursor()
        mock_conn.cursor.return_value = mock_cur

        # Return empty results
        mock_cur.results = []

        discover_ghost_cohorts(mock_conn, min_size=5)

        mock_cur.executed.clear()
        mock_cur.results = []
        discover_ghost_cohorts(mock_conn, min_size=5)

        sql, params = mock_cur.executed[0]
        self.assertIn("GROUP BY", sql)
        self.assertIn("`strategy`", sql)
        self.assertIn("`symbol`", sql)
        self.assertIn("`direction`", sql)
        self.assertIn("`entry_price`", sql)
        self.assertIn("HAVING COUNT(*) > %s", sql)
        self.assertEqual(params, (5,))

    def test_discover_cohorts_parses_results(self):
        """Parses row tuples into cohort dicts."""
        mock_conn = MagicMock()
        mock_cur = MockCursor()
        mock_conn.cursor.return_value = mock_cur

        # Simulate DB returning tuples: strategy, symbol, direction, entry_price, count, min_id, max_id
        mock_cur.fetch_results = [
            ("quan_engine", "MATICUSDT", "LONG", 150000, 20474, 16262086, 16462086),
            ("meta_strategy", "DOGEUSDT", "LONG", 500000, 5661, 100, 200),
        ]

        cohorts = discover_ghost_cohorts(mock_conn, min_size=5)

        self.assertEqual(len(cohorts), 2)
        self.assertEqual(cohorts[0]["strategy"], "quan_engine")
        self.assertEqual(cohorts[0]["symbol"], "MATICUSDT")
        self.assertEqual(cohorts[0]["direction"], "LONG")
        self.assertEqual(cohorts[0]["entry_price"], 150000)
        self.assertEqual(cohorts[0]["count"], 20474)
        self.assertEqual(cohorts[0]["min_id"], 16262086)
        self.assertEqual(cohorts[0]["max_id"], 16462086)

    def test_discover_cohorts_empty_result(self):
        """Returns empty list when no cohorts found."""
        mock_conn = MagicMock()
        mock_cur = MockCursor()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.results = []

        cohorts = discover_ghost_cohorts(mock_conn)
        self.assertEqual(cohorts, [])

    def test_discover_cohorts_uses_min_size_param(self):
        """Passes min_size to SQL query."""
        mock_conn = MagicMock()
        mock_cur = MockCursor()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.results = []

        discover_ghost_cohorts(mock_conn, min_size=100)
        _, params = mock_cur.executed[0]
        self.assertEqual(params, (100,))


class TestRunCleanup(unittest.TestCase):
    """Test the cleanup execution logic."""

    def _cohort(self, **overrides):
        base = {
            "strategy": "test_strat",
            "symbol": "TESTUSDT",
            "direction": "LONG",
            "entry_price": 100,
            "count": 10,
            "min_id": 1,
            "max_id": 10,
        }
        base.update(overrides)
        return base

    def test_dry_run_no_deletes(self):
        """Dry run should not execute any DELETE SQL."""
        mock_conn = MockConnection()
        cohorts = [self._cohort(count=10)]

        report = run_cleanup(mock_conn, cohorts, execute=False)

        self.assertEqual(report["mode"], "DRY_RUN")
        self.assertEqual(report["total_deletable"], 9)  # 10 - 1
        self.assertEqual(report["total_deleted"], 0)
        self.assertFalse(mock_conn.committed)
        self.assertFalse(mock_conn.rolled_back)

    def test_dry_run_reports_would_delete(self):
        """Dry run reports what would be deleted."""
        mock_conn = MockConnection()
        cohorts = [
            self._cohort(symbol="MATICUSDT", strategy="quan_engine", count=20474, min_id=100),
            self._cohort(symbol="DOGEUSDT", strategy="meta_strategy", count=5661, min_id=200),
        ]

        report = run_cleanup(mock_conn, cohorts, execute=False, max_deletes=None)

        self.assertEqual(report["total_deletable"], (20474 - 1) + (5661 - 1))
        self.assertEqual(report["cohorts_found"], 2)
        self.assertEqual(report["cohorts_processed"], 2)

    def test_execute_deletes_and_commits(self):
        """Execute mode runs DELETE and commits transaction."""
        mock_conn = MockConnection(execute_returns=[5])
        cohorts = [self._cohort(count=6)]

        report = run_cleanup(mock_conn, cohorts, execute=True)

        self.assertEqual(report["mode"], "EXECUTE")
        self.assertEqual(report["total_deleted"], 5)
        self.assertTrue(mock_conn.committed)
        self.assertFalse(mock_conn.rolled_back)

    def test_execute_rolls_back_on_error(self):
        """Errors cause transaction rollback."""
        mock_conn = MockConnection()
        mock_conn.cursor_instance.results = [
            Exception("test db error"),  # simulate execute failure
        ]

        # We need to make the mock raise on execute
        class FailingCursor(MockCursor):
            def execute(self, sql, params=None):
                self.executed.append((sql, params))
                raise RuntimeError("db error")

        mock_conn.cursor_instance = FailingCursor()
        cohorts = [self._cohort(count=6)]

        report = run_cleanup(mock_conn, cohorts, execute=True)

        self.assertTrue(mock_conn.rolled_back)
        self.assertEqual(report["total_deleted"], 0)  # reset after rollback
        self.assertEqual(len(report["errors"]), 1)

    def test_max_deletes_cap(self):
        """Respects max_deletes limit."""
        mock_conn = MockConnection(execute_returns=[999])
        cohorts = [
            self._cohort(symbol="A", count=1000, min_id=1),
            self._cohort(symbol="B", count=1000, min_id=1001),
        ]

        report = run_cleanup(mock_conn, cohorts, execute=True, max_deletes=1000)

        self.assertTrue(report["max_deletes_reached"])
        # First cohort: 999 deletable, fits within 1000 cap
        # Second cohort: capped or skipped
        self.assertLessEqual(report["total_deleted"], 1000)

    def test_no_limit_removes_cap(self):
        """max_deletes=None removes the safety cap."""
        mock_conn = MockConnection(execute_returns=[9999, 9999])
        cohorts = [
            self._cohort(symbol="A", count=10000, min_id=1),
            self._cohort(symbol="B", count=10000, min_id=10001),
        ]

        report = run_cleanup(mock_conn, cohorts, execute=True, max_deletes=None)

        self.assertFalse(report["max_deletes_reached"])
        self.assertEqual(report["total_deleted"], 9999 + 9999)

    def test_cohort_of_size_one_skipped(self):
        """Cohorts of size 1 have 0 deletable."""
        mock_conn = MockConnection()
        cohorts = [self._cohort(count=1)]

        report = run_cleanup(mock_conn, cohorts, execute=False)

        self.assertEqual(report["total_deletable"], 0)
        detail = report["per_cohort"][0]
        self.assertEqual(detail["would_delete"], 0)

    def test_cohort_at_exact_threshold(self):
        """Cohort with count=6 (min_size=5) has 5 deletable."""
        mock_conn = MockConnection()
        cohorts = [self._cohort(count=6)]

        report = run_cleanup(mock_conn, cohorts, execute=False)

        self.assertEqual(report["total_deletable"], 5)

    def test_per_cohort_detail_fields(self):
        """Per-cohort detail includes all expected fields."""
        mock_conn = MockConnection()
        cohorts = [
            self._cohort(
                symbol="MATICUSDT",
                strategy="quan_engine",
                direction="LONG",
                entry_price=150000,
                count=100,
                min_id=42,
                max_id=141,
            )
        ]

        report = run_cleanup(mock_conn, cohorts, execute=False)

        detail = report["per_cohort"][0]
        self.assertEqual(detail["strategy"], "quan_engine")
        self.assertEqual(detail["symbol"], "MATICUSDT")
        self.assertEqual(detail["direction"], "LONG")
        self.assertEqual(detail["entry_price"], 150000)
        self.assertEqual(detail["count"], 100)
        self.assertEqual(detail["min_id"], 42)
        self.assertEqual(detail["max_id"], 141)
        self.assertEqual(detail["would_delete"], 99)
        self.assertFalse(detail["capped"])

    def test_execute_delete_sql_is_called(self):
        """Execute mode actually calls cursor.execute with DELETE SQL."""
        mock_conn = MockConnection()

        class TrackedCursor(MockCursor):
            def __init__(self):
                super().__init__()
                self.delete_calls = []

            def execute(self, sql, params=None):
                self.executed.append((sql, params))
                if "DELETE" in sql.upper():
                    self.delete_calls.append((sql, params))
                return 5

        mock_conn.cursor_instance = TrackedCursor()
        cohorts = [self._cohort(count=6)]

        run_cleanup(mock_conn, cohorts, execute=True)

        self.assertEqual(len(mock_conn.cursor_instance.delete_calls), 1)
        sql = mock_conn.cursor_instance.delete_calls[0][0]
        self.assertIn("DELETE", sql.upper())

    def test_multiple_cohorts_all_processed(self):
        """All cohorts are processed in order."""
        mock_conn = MockConnection(execute_returns=[10, 20, 5])
        cohorts = [
            self._cohort(symbol="A", count=11, min_id=1),
            self._cohort(symbol="B", count=21, min_id=100),
            self._cohort(symbol="C", count=6, min_id=200),
        ]

        report = run_cleanup(mock_conn, cohorts, execute=True)

        self.assertEqual(report["cohorts_processed"], 3)
        self.assertEqual(len(report["per_cohort"]), 3)

    def test_capped_cohort_reports_zero_when_exceeds_remaining(self):
        """When deletes cap is exhausted, remaining cohorts report would_delete=0."""
        mock_conn = MockConnection(execute_returns=[999])
        cohorts = [
            self._cohort(symbol="BIG", count=1000, min_id=1),  # 999 deletable
            self._cohort(symbol="SMALL", count=10, min_id=1001),  # 9 deletable, but capped out
        ]

        report = run_cleanup(mock_conn, cohorts, execute=True, max_deletes=999)

        self.assertTrue(report["max_deletes_reached"])
        # Check second cohort was capped
        small_detail = report["per_cohort"][1]
        self.assertTrue(small_detail["capped"])
        self.assertEqual(small_detail["would_delete"], 0)


class TestIntegrationScenarios(unittest.TestCase):
    """Integration-style tests using full mock scenarios."""

    def _cohort(self, **overrides):
        base = {
            "strategy": "meta_strategy",
            "symbol": "WIFUSDT",
            "direction": "SHORT",
            "entry_price": 500000,
            "count": 100,
            "min_id": 5000,
            "max_id": 5099,
        }
        base.update(overrides)
        return base

    def test_realistic_ghost_scenario_dry_run(self):
        """Simulate the actual ghost cohorts from db_health.json."""
        mock_conn = MockConnection()
        cohorts = [
            {"strategy": "quan_engine", "symbol": "MATICUSDT", "direction": "LONG",
             "entry_price": 150000, "count": 20474, "min_id": 16262086, "max_id": 16462086},
            {"strategy": "meta_strategy", "symbol": "DOGEUSDT", "direction": "LONG",
             "entry_price": 500000, "count": 5661, "min_id": 100, "max_id": 200},
            {"strategy": "meta_strategy", "symbol": "WIFUSDT", "direction": "SHORT",
             "entry_price": 500000, "count": 4644, "min_id": 300, "max_id": 400},
            {"strategy": "meta_strategy", "symbol": "SHIBUSDT", "direction": "LONG",
             "entry_price": 500000, "count": 4158, "min_id": 500, "max_id": 600},
        ]

        report = run_cleanup(mock_conn, cohorts, execute=False, max_deletes=None)

        # Total should match db_health.json approximate
        self.assertEqual(report["total_deletable"], (20474-1) + (5661-1) + (4644-1) + (4158-1))
        self.assertEqual(report["cohorts_found"], 4)

        # Verify the MATIC cohort detail
        matic = report["per_cohort"][0]
        self.assertEqual(matic["strategy"], "quan_engine")
        self.assertEqual(matic["symbol"], "MATICUSDT")
        self.assertEqual(matic["min_id"], 16262086)
        self.assertEqual(matic["would_delete"], 20473)

    def test_delete_sql_correct_for_known_cohort(self):
        """Verify DELETE SQL matches expected pattern for a known ghost cohort."""
        cohort = {
            "strategy": "quan_engine",
            "symbol": "MATICUSDT",
            "direction": "LONG",
            "entry_price": 150000,
            "count": 20474,
            "min_id": 16262086,
            "max_id": 16462086,
        }

        sql, params = build_delete_sql(cohort)

        self.assertIn("DELETE FROM `bt_backtest_trades`", sql)
        self.assertIn("`strategy` = %s", sql)
        self.assertIn("`symbol` = %s", sql)
        self.assertIn("`direction` = %s", sql)
        self.assertIn("`entry_price` = %s", sql)
        self.assertIn("`id` != %s", sql)

        # Check params match cohort values
        self.assertEqual(params[0], "quan_engine")
        self.assertEqual(params[1], "MATICUSDT")
        self.assertEqual(params[2], "LONG")
        self.assertEqual(params[3], 150000)
        self.assertEqual(params[4], 16262086)


if __name__ == "__main__":
    unittest.main()
