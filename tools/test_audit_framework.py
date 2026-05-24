"""Unit tests for the audit test framework.

Uses mocked file reads to test each AuditTest subclass in isolation.

Run with:
    python3 tools/test_audit_framework.py
    pytest tools/test_audit_framework.py
"""

import json
import os
import sys
import unittest
from unittest.mock import patch, mock_open, MagicMock

# Ensure project root is on sys.path so we can import tools.audit_test_framework
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from tools.audit_test_framework.base import AuditTest
from tools.audit_test_framework.tests import (
    AssetClassificationCheck,
    BacktestTableCheck,
    DataFreshnessCheck,
    DbHealthCheck,
    GhostRowCount,
    OpenBloatCheck,
    PnLIntegrityCheck,
    SignalOutcomesCheck,
    WonPnlContradiction,
)

# ── Shared fixture helpers ──────────────────────────────────────────────


def _make_db_health(red_checks=None):
    """Build a minimal db_health.json structure."""
    red_checks = red_checks or []
    checks = {
        "pnl_integrity": {
            "data": {"mismatch_pct": 2.0, "gt1pct_mismatch": 100, "gt001pct_mismatch": 200, "sampled": 5000, "tier": "green"},
        },
        "won_pnl_contradiction": {
            "data": {"contradiction_detected": False, "by_status": [], "tier": "green"},
        },
        "ghost_rows": {
            "data": {"total_ghost_rows": 500, "top_cohorts": [], "tier": "green"},
        },
        "open_bloat": {
            "data": {"open_count": 50000, "info_schema_estimate": 10000, "hours_since_last_close": 2, "validator_frozen": False, "tier": "green"},
        },
    }
    for name in red_checks:
        if name in checks:
            checks[name]["data"]["tier"] = "red"
            # For specific checks, set additional red fields
            if name == "pnl_integrity":
                checks[name]["data"]["mismatch_pct"] = 10.0
            elif name == "ghost_rows":
                checks[name]["data"]["total_ghost_rows"] = 5000
            elif name == "open_bloat":
                checks[name]["data"]["open_count"] = 5_000_000

    return {"checks": checks, "overall": {"checks_run": 4, "checks_passed": 4 - len(red_checks), "checks_failed": len(red_checks), "any_red": len(red_checks) > 0}}


def _make_db_freshness(signal_minutes_stale=200, backtest_minutes_stale=1000, backtest_error=None, backtest_n_total=50):
    """Build a minimal db_freshness.json structure."""
    checks = [
        {"check": "live_picks", "status": "GREEN", "minutes_stale": 30, "n_active": 100},
        {"check": "resolver_outputs", "status": "GREEN", "minutes_stale": 20, "n_resolved_today": 5},
        {
            "check": "signal_outcomes",
            "status": "GREEN" if signal_minutes_stale <= 1440 else "RED",
            "minutes_stale": signal_minutes_stale,
            "last_resolved_at": "2026-05-23 12:00:00",
            "n_total": 121,
        },
        {
            "check": "backtests",
            "status": "RED" if backtest_error else ("YELLOW" if (backtest_minutes_stale or 0) > 10080 else "GREEN"),
            "minutes_stale": backtest_minutes_stale,
            "n_total": backtest_n_total,
            "error": backtest_error,
        },
    ]
    return {"checks": checks, "overall": "GREEN"}


def _make_tournament_picks(misclassified=None):
    """Build a minimal ai_tournament_picks_latest.json list."""
    picks = [
        {"symbol": "BTCUSDT", "asset_class": "CRYPTO", "direction": "LONG"},
        {"symbol": "AAPL", "asset_class": "EQUITY", "direction": "LONG"},
    ]
    # Add some proper ETFs
    for sym in ["SPY", "QQQ"]:
        picks.append({"symbol": sym, "asset_class": "ETF", "direction": "LONG"})

    if misclassified:
        for sym, wrong_class in misclassified:
            picks.append({"symbol": sym, "asset_class": wrong_class, "direction": "LONG"})

    return picks


def _patch_load_json(return_value):
    """Patch _load_json to return a specific value."""
    return patch("tools.audit_test_framework.tests._load_json", return_value=return_value)


# ── Tests ────────────────────────────────────────────────────────────────


class TestAuditTestBase(unittest.TestCase):
    """Base class should have proper interface."""

    def test_base_raises_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            AuditTest().run()

    def test_base_repr(self):
        t = AuditTest()
        t.name = "TestName"
        t.severity = "high"
        self.assertIn("TestName", repr(t))
        self.assertIn("high", repr(t))


class TestDbHealthCheck(unittest.TestCase):

    def test_all_green(self):
        data = _make_db_health()
        with _patch_load_json(data):
            result = DbHealthCheck().run()
        self.assertTrue(result["passed"])
        self.assertIn("green", result["message"].lower())

    def test_red_tier_fails(self):
        data = _make_db_health(red_checks=["pnl_integrity", "ghost_rows"])
        with _patch_load_json(data):
            result = DbHealthCheck().run()
        self.assertFalse(result["passed"])
        self.assertIn("pnl_integrity", result["message"])
        self.assertIn("ghost_rows", result["message"])

    def test_file_not_found(self):
        with patch("tools.audit_test_framework.tests._load_json", side_effect=FileNotFoundError):
            result = DbHealthCheck().run()
        self.assertFalse(result["passed"])
        self.assertIn("not found", result["message"])

    def test_severity(self):
        self.assertEqual(DbHealthCheck().severity, "critical")


class TestGhostRowCount(unittest.TestCase):

    def test_within_threshold(self):
        data = _make_db_health()
        with _patch_load_json(data):
            result = GhostRowCount().run()
        self.assertTrue(result["passed"])

    def test_exceeds_threshold(self):
        data = _make_db_health(red_checks=["ghost_rows"])
        with _patch_load_json(data):
            result = GhostRowCount().run()
        self.assertFalse(result["passed"])
        self.assertIn("5,000", result["message"])

    def test_file_not_found(self):
        with patch("tools.audit_test_framework.tests._load_json", side_effect=FileNotFoundError):
            result = GhostRowCount().run()
        self.assertFalse(result["passed"])

    def test_severity(self):
        self.assertEqual(GhostRowCount().severity, "high")


class TestOpenBloatCheck(unittest.TestCase):

    def test_within_threshold(self):
        data = _make_db_health()
        with _patch_load_json(data):
            result = OpenBloatCheck().run()
        self.assertTrue(result["passed"])

    def test_exceeds_threshold(self):
        data = _make_db_health(red_checks=["open_bloat"])
        with _patch_load_json(data):
            result = OpenBloatCheck().run()
        self.assertFalse(result["passed"])
        self.assertIn("5,000,000", result["message"])

    def test_file_not_found(self):
        with patch("tools.audit_test_framework.tests._load_json", side_effect=FileNotFoundError):
            result = OpenBloatCheck().run()
        self.assertFalse(result["passed"])

    def test_severity(self):
        self.assertEqual(OpenBloatCheck().severity, "high")


class TestPnLIntegrityCheck(unittest.TestCase):

    def test_within_threshold(self):
        data = _make_db_health()
        with _patch_load_json(data):
            result = PnLIntegrityCheck().run()
        self.assertTrue(result["passed"])

    def test_exceeds_threshold(self):
        data = _make_db_health(red_checks=["pnl_integrity"])
        with _patch_load_json(data):
            result = PnLIntegrityCheck().run()
        self.assertFalse(result["passed"])
        self.assertIn("10.0%", result["message"])

    def test_file_not_found(self):
        with patch("tools.audit_test_framework.tests._load_json", side_effect=FileNotFoundError):
            result = PnLIntegrityCheck().run()
        self.assertFalse(result["passed"])

    def test_severity(self):
        self.assertEqual(PnLIntegrityCheck().severity, "critical")


class TestWonPnlContradiction(unittest.TestCase):

    def test_no_contradiction(self):
        data = _make_db_health()
        with _patch_load_json(data):
            result = WonPnlContradiction().run()
        self.assertTrue(result["passed"])

    def test_contradiction_detected(self):
        data = _make_db_health()
        data["checks"]["won_pnl_contradiction"]["data"]["contradiction_detected"] = True
        with _patch_load_json(data):
            result = WonPnlContradiction().run()
        self.assertFalse(result["passed"])
        self.assertIn("contradiction", result["message"].lower())

    def test_severity(self):
        self.assertEqual(WonPnlContradiction().severity, "critical")


class TestDataFreshnessCheck(unittest.TestCase):

    @patch("tools.audit_test_framework.tests.glob.glob")
    @patch("tools.audit_test_framework.tests._file_age_days")
    def test_all_fresh(self, mock_age, mock_glob):
        mock_glob.return_value = ["/data/a.json", "/data/b.json"]
        mock_age.return_value = 1.0  # 1 day old
        result = DataFreshnessCheck().run()
        self.assertTrue(result["passed"])

    @patch("tools.audit_test_framework.tests.glob.glob")
    @patch("tools.audit_test_framework.tests._file_age_days")
    def test_stale_files(self, mock_age, mock_glob):
        mock_glob.return_value = ["/data/a.json", "/data/b.json"]
        # Simulate age: first file is stale, second is fresh
        mock_age.side_effect = [10.0, 1.0]
        result = DataFreshnessCheck().run()
        self.assertFalse(result["passed"])
        self.assertIn("older than", result["message"].lower())

    def test_severity(self):
        self.assertEqual(DataFreshnessCheck().severity, "high")


class TestAssetClassificationCheck(unittest.TestCase):

    def test_all_correct(self):
        picks = _make_tournament_picks()
        with _patch_load_json(picks):
            result = AssetClassificationCheck().run()
        self.assertTrue(result["passed"])

    def test_misclassified(self):
        picks = _make_tournament_picks(misclassified=[("SPY", "CRYPTO"), ("XLK", "EQUITY")])
        with _patch_load_json(picks):
            result = AssetClassificationCheck().run()
        self.assertFalse(result["passed"])
        self.assertIn("SPY", result["message"])
        self.assertIn("XLK", result["message"])

    def test_not_a_list(self):
        with _patch_load_json({"key": "value"}):
            result = AssetClassificationCheck().run()
        self.assertFalse(result["passed"])

    def test_file_not_found(self):
        with patch("tools.audit_test_framework.tests._load_json", side_effect=FileNotFoundError):
            result = AssetClassificationCheck().run()
        self.assertFalse(result["passed"])

    def test_severity(self):
        self.assertEqual(AssetClassificationCheck().severity, "high")


class TestSignalOutcomesCheck(unittest.TestCase):

    def test_within_threshold(self):
        data = _make_db_freshness(signal_minutes_stale=200)
        with _patch_load_json(data):
            result = SignalOutcomesCheck().run()
        self.assertTrue(result["passed"])

    def test_exceeds_threshold(self):
        data = _make_db_freshness(signal_minutes_stale=2000)
        with _patch_load_json(data):
            result = SignalOutcomesCheck().run()
        self.assertFalse(result["passed"])
        self.assertIn("2,000", result["message"])

    def test_missing_check(self):
        data = _make_db_freshness()
        data["checks"] = [{"check": "live_picks"}]
        with _patch_load_json(data):
            result = SignalOutcomesCheck().run()
        self.assertFalse(result["passed"])
        self.assertIn("not found", result["message"])

    def test_severity(self):
        self.assertEqual(SignalOutcomesCheck().severity, "high")


class TestBacktestTableCheck(unittest.TestCase):

    def test_healthy(self):
        data = _make_db_freshness(backtest_minutes_stale=1000)
        with _patch_load_json(data):
            result = BacktestTableCheck().run()
        self.assertTrue(result["passed"])

    def test_stale(self):
        data = _make_db_freshness(backtest_minutes_stale=20000)
        with _patch_load_json(data):
            result = BacktestTableCheck().run()
        self.assertFalse(result["passed"])

    def test_error(self):
        data = _make_db_freshness(backtest_error="no timestamp column")
        with _patch_load_json(data):
            result = BacktestTableCheck().run()
        self.assertFalse(result["passed"])
        self.assertIn("error", result["message"].lower())

    def test_severity(self):
        self.assertEqual(BacktestTableCheck().severity, "medium")


class TestRunner(unittest.TestCase):

    @patch("tools.audit_test_framework.tests._load_json")
    @patch("tools.audit_test_framework.tests.glob.glob")
    @patch("tools.audit_test_framework.tests._file_age_days")
    def test_run_all_tests(self, mock_age, mock_glob, mock_load):
        """Runner should execute all tests without error."""
        # Set up all mocked file reads
        mock_load.side_effect = lambda name: {
            "db_health.json": _make_db_health(),
            "db_freshness.json": _make_db_freshness(),
            "ai_tournament_picks_latest.json": _make_tournament_picks(),
        }.get(name, {})
        mock_glob.return_value = []
        mock_age.return_value = 1.0

        from tools.audit_test_framework.runner import run_audit_tests
        report = run_audit_tests(mode="all")

        self.assertIn("summary", report)
        self.assertIn("results", report)
        self.assertIn("timestamp", report)
        self.assertEqual(report["summary"]["total"], len(report["results"]))

    @patch("tools.audit_test_framework.tests._load_json")
    def test_run_critical_only(self, mock_load):
        mock_load.side_effect = lambda name: {
            "db_health.json": _make_db_health(),
        }.get(name, {})

        from tools.audit_test_framework.runner import run_audit_tests
        report = run_audit_tests(mode="critical")

        for r in report["results"]:
            self.assertEqual(r["severity"], "critical")

    @patch("tools.audit_test_framework.tests._load_json")
    def test_critical_failure_exit_code(self, mock_load):
        mock_load.side_effect = lambda name: {
            "db_health.json": _make_db_health(red_checks=["pnl_integrity"]),
        }.get(name, {})

        from tools.audit_test_framework.runner import run_audit_tests
        report = run_audit_tests(mode="critical")

        self.assertTrue(report["summary"]["critical_failed"])


if __name__ == "__main__":
    unittest.main()
