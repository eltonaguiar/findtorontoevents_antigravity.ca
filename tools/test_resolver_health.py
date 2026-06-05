#!/usr/bin/env python3
"""
tools/test_resolver_health.py -- Unit tests for resolver health checks
======================================================================

Tests the core functions in check_resolver_health.py and resolve_stale_open_picks.py
with mocked DB connections and filesystem access.

Usage
-----
    python tools/test_resolver_health.py
    python -m pytest tools/test_resolver_health.py -v
"""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Import the modules under test
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import check_resolver_health as crh
from tools import resolve_stale_open_picks as rsop


class MockCursor:
    """Mock pymysql cursor for testing."""

    def __init__(self, results=None):
        self.results = results or []
        self.executed_sql = None
        self.executed_params = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, sql, params=None):
        self.executed_sql = sql
        self.executed_params = params

    def fetchone(self):
        return self.results[0] if self.results else None

    def fetchall(self):
        return self.results


# ---------------------------------------------------------------------------
# Test: MAX_HOLD_HOURS_BY_CLASS constants (from resolve_stale_open_picks)
# ---------------------------------------------------------------------------

class TestMaxHoldHours(unittest.TestCase):
    """Verify hold window constants match universal_pick_resolver.py."""

    def test_crypto_48h(self):
        self.assertEqual(rsop.MAX_HOLD_HOURS_BY_CLASS["CRYPTO"], 48)

    def test_equity_96h(self):
        self.assertEqual(rsop.MAX_HOLD_HOURS_BY_CLASS["EQUITY"], 96)

    def test_etf_96h(self):
        self.assertEqual(rsop.MAX_HOLD_HOURS_BY_CLASS["ETF"], 96)

    def test_commodity_96h(self):
        self.assertEqual(rsop.MAX_HOLD_HOURS_BY_CLASS["COMMODITY"], 96)

    def test_futures_96h(self):
        self.assertEqual(rsop.MAX_HOLD_HOURS_BY_CLASS["FUTURES"], 96)

    def test_forex_72h(self):
        self.assertEqual(rsop.MAX_HOLD_HOURS_BY_CLASS["FOREX"], 72)

    def test_bond_120h(self):
        self.assertEqual(rsop.MAX_HOLD_HOURS_BY_CLASS["BOND"], 120)

    def test_unknown_defaults_to_48(self):
        self.assertEqual(rsop._hold_hours_for("UNKNOWN"), 48)
        self.assertEqual(rsop._hold_hours_for(""), 48)
        self.assertEqual(rsop._hold_hours_for("MEMECOIN"), 48)


# ---------------------------------------------------------------------------
# Test: pick age calculation (from resolve_stale_open_picks)
# ---------------------------------------------------------------------------

class TestPickAgeCalculation(unittest.TestCase):
    """Test _pick_age_hours function."""

    def test_datetime_timestamp(self):
        """Age calculation from datetime object."""
        two_days_ago = datetime.now(timezone.utc) - timedelta(hours=50)
        pick = {"created_at": two_days_ago}
        age = rsop._pick_age_hours(pick)
        self.assertIsNotNone(age)
        self.assertGreater(age, 49)

    def test_string_timestamp(self):
        """Age calculation from string timestamp."""
        two_days_ago = (datetime.now(timezone.utc) - timedelta(hours=50)).strftime("%Y-%m-%d %H:%M:%S")
        pick = {"created_at": two_days_ago}
        age = rsop._pick_age_hours(pick)
        self.assertIsNotNone(age)
        self.assertGreater(age, 49)

    def test_submitted_at_preferred(self):
        """submitted_at should be preferred over created_at."""
        old_ts = datetime.now(timezone.utc) - timedelta(hours=100)
        new_ts = datetime.now(timezone.utc) - timedelta(hours=10)
        pick = {
            "submitted_at": new_ts,
            "created_at": old_ts,
        }
        age = rsop._pick_age_hours(pick)
        self.assertIsNotNone(age)
        self.assertLess(age, 15)

    def test_missing_timestamp(self):
        """Returns None when no timestamp fields exist."""
        pick = {"symbol": "BTCUSDT"}
        age = rsop._pick_age_hours(pick)
        self.assertIsNone(age)


# ---------------------------------------------------------------------------
# Test: staleness detection (from resolve_stale_open_picks)
# ---------------------------------------------------------------------------

class TestStalenessDetection(unittest.TestCase):
    """Test is_stale function."""

    def test_crypto_stale_50h(self):
        """CRYPTO pick > 48h is stale."""
        pick = {
            "asset_class": "CRYPTO",
            "created_at": datetime.now(timezone.utc) - timedelta(hours=50),
        }
        self.assertTrue(rsop.is_stale(pick))

    def test_crypto_not_stale_24h(self):
        """CRYPTO pick < 48h is not stale."""
        pick = {
            "asset_class": "CRYPTO",
            "created_at": datetime.now(timezone.utc) - timedelta(hours=24),
        }
        self.assertFalse(rsop.is_stale(pick))

    def test_equity_stale_100h(self):
        """EQUITY pick > 96h is stale."""
        pick = {
            "asset_class": "EQUITY",
            "created_at": datetime.now(timezone.utc) - timedelta(hours=100),
        }
        self.assertTrue(rsop.is_stale(pick))

    def test_equity_not_stale_48h(self):
        """EQUITY pick < 96h is not stale."""
        pick = {
            "asset_class": "EQUITY",
            "created_at": datetime.now(timezone.utc) - timedelta(hours=48),
        }
        self.assertFalse(rsop.is_stale(pick))

    def test_forex_stale_130h(self):
        """FOREX pick > 120h is stale."""
        pick = {
            "asset_class": "FOREX",
            "created_at": datetime.now(timezone.utc) - timedelta(hours=130),
        }
        self.assertTrue(rsop.is_stale(pick))

    def test_forex_not_stale_100h(self):
        """FOREX pick < 120h is not stale."""
        pick = {
            "asset_class": "FOREX",
            "created_at": datetime.now(timezone.utc) - timedelta(hours=100),
        }
        self.assertFalse(rsop.is_stale(pick))

    def test_no_timestamp_not_stale(self):
        """Pick without timestamp is not considered stale."""
        pick = {"asset_class": "CRYPTO", "symbol": "BTCUSDT"}
        self.assertFalse(rsop.is_stale(pick))


# ---------------------------------------------------------------------------
# Test: PnL computation (from resolve_stale_open_picks)
# ---------------------------------------------------------------------------

class TestPnLComputation(unittest.TestCase):
    """Test _compute_pnl function."""

    def test_long_flat(self):
        pick = {"entry_price": 100.0, "direction": "LONG"}
        pnl = rsop._compute_pnl(pick, current_price=100.0)
        self.assertEqual(pnl, 0.0)

    def test_long_profit(self):
        pick = {"entry_price": 100.0, "direction": "LONG"}
        pnl = rsop._compute_pnl(pick, current_price=105.0)
        self.assertEqual(pnl, 5.0)

    def test_long_loss(self):
        pick = {"entry_price": 100.0, "direction": "LONG"}
        pnl = rsop._compute_pnl(pick, current_price=95.0)
        self.assertEqual(pnl, -5.0)

    def test_short_profit(self):
        pick = {"entry_price": 100.0, "direction": "SHORT"}
        pnl = rsop._compute_pnl(pick, current_price=95.0)
        self.assertEqual(pnl, 5.0)

    def test_short_loss(self):
        pick = {"entry_price": 100.0, "direction": "SHORT"}
        pnl = rsop._compute_pnl(pick, current_price=105.0)
        self.assertEqual(pnl, -5.0)

    def test_no_entry_price(self):
        pick = {"entry_price": 0, "direction": "LONG"}
        pnl = rsop._compute_pnl(pick, current_price=100.0)
        self.assertEqual(pnl, 0.0)

    def test_no_current_price_flat(self):
        pick = {"entry_price": 100.0, "direction": "LONG"}
        pnl = rsop._compute_pnl(pick, current_price=None)
        self.assertEqual(pnl, 0.0)


# ---------------------------------------------------------------------------
# Test: DB connectivity check (from check_resolver_health)
# ---------------------------------------------------------------------------

class TestDBConnectivity(unittest.TestCase):
    """Test check_db_connectivity function."""

    @patch.object(crh, "_connect")
    def test_db_connected(self, mock_connect):
        """Successful DB connection returns GREEN."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"ok": 1}
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = crh.check_db_connectivity()
        self.assertEqual(result["status"], "GREEN")
        mock_conn.close.assert_called_once()

    @patch.object(crh, "_connect")
    def test_db_connection_fails(self, mock_connect):
        """Failed DB connection returns RED."""
        mock_connect.side_effect = Exception("Connection refused")

        result = crh.check_db_connectivity()
        self.assertEqual(result["status"], "RED")
        self.assertIn("Connection refused", result["message"])


# ---------------------------------------------------------------------------
# Test: Open picks count check (from check_resolver_health)
# ---------------------------------------------------------------------------

class TestOpenPicksCount(unittest.TestCase):
    """Test check_open_picks_count function."""

    def test_below_threshold(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"cnt": 500_000}
        mock_conn.cursor.return_value = mock_cursor

        result = crh.check_open_picks_count(mock_conn)
        self.assertEqual(result["status"], "GREEN")
        self.assertEqual(result["value"], 500_000)

    def test_above_threshold(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"cnt": 5_000_000}
        mock_conn.cursor.return_value = mock_cursor

        result = crh.check_open_picks_count(mock_conn)
        self.assertEqual(result["status"], "RED")
        self.assertEqual(result["value"], 5_000_000)
        self.assertIn("EXCEEDS", result["message"])


# ---------------------------------------------------------------------------
# Test: Stale by asset class check (from check_resolver_health)
# ---------------------------------------------------------------------------

class TestStaleByAssetClass(unittest.TestCase):
    """Test check_stale_by_asset_class function."""

    def test_returns_counts_by_class(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {"asset_class": "CRYPTO", "cnt": 1_000, "oldest": "2026-05-01", "newest": "2026-05-20"},
            {"asset_class": "FOREX", "cnt": 500, "oldest": "2026-05-01", "newest": "2026-05-18"},
        ]
        mock_conn.cursor.return_value = mock_cursor

        result = crh.check_stale_by_asset_class(mock_conn)
        self.assertIn("CRYPTO", result["by_class"])
        self.assertIn("FOREX", result["by_class"])
        self.assertEqual(result["by_class"]["CRYPTO"]["total_open"], 1_000)
        self.assertEqual(result["by_class"]["FOREX"]["total_open"], 500)
        self.assertEqual(result["by_class"]["CRYPTO"]["max_hold_hours"], 48)
        self.assertEqual(result["by_class"]["FOREX"]["max_hold_hours"], 120)


# ---------------------------------------------------------------------------
# Test: Last resolver run check (from check_resolver_health)
# ---------------------------------------------------------------------------

class TestLastResolverRun(unittest.TestCase):
    """Test check_last_resolver_run function."""

    @patch("tools.check_resolver_health.RESOLVED_FILE")
    def test_file_not_exists(self, mock_file):
        """Missing resolved file returns RED."""
        mock_file.exists.return_value = False

        result = crh.check_last_resolver_run()
        self.assertEqual(result["status"], "RED")
        self.assertFalse(result["resolved_file_exists"])

    @patch("tools.check_resolver_health.RESOLVED_FILE")
    def test_recent_file(self, mock_file):
        """Recent resolved file returns GREEN."""
        mock_file.exists.return_value = True
        now = datetime.now(timezone.utc)
        mock_file.stat.return_value = MagicMock(st_mtime=now.timestamp())
        mock_file.read_text.return_value = json.dumps([
            {"resolved_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "symbol": "BTCUSDT"}
        ])

        result = crh.check_last_resolver_run()
        self.assertEqual(result["status"], "GREEN")
        self.assertTrue(result["resolved_file_exists"])

    @patch("tools.check_resolver_health.RESOLVED_FILE")
    def test_stale_file(self, mock_file):
        """Old resolved file returns RED."""
        mock_file.exists.return_value = True
        old_time = (datetime.now(timezone.utc) - timedelta(hours=72)).timestamp()
        mock_file.stat.return_value = MagicMock(st_mtime=old_time)
        mock_file.read_text.return_value = json.dumps([
            {"resolved_at": "2026-05-12T00:00:00Z", "symbol": "BTCUSDT"}
        ])

        result = crh.check_last_resolver_run()
        self.assertEqual(result["status"], "RED")


# ---------------------------------------------------------------------------
# Test: Full health report (from check_resolver_health)
# ---------------------------------------------------------------------------

class TestFullHealthReport(unittest.TestCase):
    """Test run_health_check function."""

    @patch.object(crh, "_connect")
    @patch.object(crh, "check_last_resolver_run")
    def test_green_report(self, mock_resolver, mock_connect):
        """Green report when all checks pass (no stale picks, count below threshold)."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.side_effect = [
            {"ok": 1},
            {"cnt": 100},  # Below threshold
        ]
        mock_cursor.fetchall.return_value = []  # No stale picks by asset class
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_resolver.return_value = {
            "status": "GREEN",
            "resolved_file_exists": True,
            "message": "Resolver appears active",
        }

        report = crh.run_health_check(alert_threshold=1_000_000)

        self.assertEqual(report["overall"]["status"], "GREEN")
        self.assertGreater(report["overall"]["checks_run"], 0)

    @patch.object(crh, "_connect")
    def test_red_report_on_high_count(self, mock_connect):
        """Red report when OPEN count exceeds threshold."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.side_effect = [
            {"ok": 1},
            {"cnt": 2_000_000},
        ]
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        with patch.object(crh, "check_last_resolver_run", return_value={"status": "GREEN"}):
            report = crh.run_health_check(alert_threshold=1_000_000)

        self.assertEqual(report["overall"]["status"], "RED")
        self.assertGreater(report["overall"]["checks_red"], 0)


# ---------------------------------------------------------------------------
# Test: resolve_stale_open_picks module functions
# ---------------------------------------------------------------------------

class TestResolveStaleOpenPicks(unittest.TestCase):
    """Test functions in resolve_stale_open_picks.py."""

    def test_hold_hours_mapping(self):
        """Verify hold hours match expected values."""
        self.assertEqual(rsop._hold_hours_for("CRYPTO"), 48)
        self.assertEqual(rsop._hold_hours_for("EQUITY"), 96)
        self.assertEqual(rsop._hold_hours_for("FOREX"), 72)
        self.assertEqual(rsop._hold_hours_for("BOND"), 120)
        self.assertEqual(rsop._hold_hours_for("UNKNOWN"), 48)

    def test_pnl_long_flat(self):
        pick = {"entry_price": 100.0, "direction": "LONG"}
        pnl = rsop._compute_pnl(pick, 100.0)
        self.assertEqual(pnl, 0.0)

    def test_pnl_short_flat(self):
        pick = {"entry_price": 100.0, "direction": "SHORT"}
        pnl = rsop._compute_pnl(pick, 100.0)
        self.assertEqual(pnl, 0.0)

    @patch("tools.resolve_stale_open_picks._connect")
    def test_dry_run_summary(self, mock_connect):
        """Dry run returns summary without DB writes."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"cnt": 0}
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        summary = rsop.resolve_stale_open_picks(execute=False, batch_size=100)

        self.assertEqual(summary["mode"], "DRY_RUN")
        self.assertEqual(summary["total_open_picks"], 0)
        self.assertEqual(summary["total_resolved"], 0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
