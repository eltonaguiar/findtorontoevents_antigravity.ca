"""
Unit tests for tools/mysql_prediction_anomaly_scanner.py

All DB calls are mocked — no live MySQL connection required.
"""
from __future__ import annotations

import importlib
import json
import sys
import types
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# Ensure repo root is on the path so we can import tools.*
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ---------------------------------------------------------------------------
# Helpers to import the module under test without a real pymysql
# ---------------------------------------------------------------------------

def _load_scanner(monkeypatch_env: dict | None = None, env: dict | None = None):
    """Import (or re-import) the scanner module with optional env overrides."""
    # Clear cached import so env changes take effect
    sys.modules.pop("tools.mysql_prediction_anomaly_scanner", None)

    # Build a fake pymysql so the import doesn't fail on machines without it
    fake_pymysql = types.ModuleType("pymysql")
    fake_pymysql.connect = MagicMock()
    fake_cursors = types.ModuleType("pymysql.cursors")
    fake_cursors.DictCursor = dict
    fake_pymysql.cursors = fake_cursors
    sys.modules.setdefault("pymysql", fake_pymysql)
    sys.modules.setdefault("pymysql.cursors", fake_cursors)

    with patch.dict("os.environ", env or {}, clear=False):
        import tools.mysql_prediction_anomaly_scanner as m
        importlib.reload(m)
    return m


# ---------------------------------------------------------------------------
# 1. Inverted confidence detector
# ---------------------------------------------------------------------------

class TestScanInvertedConfidence:
    def _make_cursor(self, rows):
        cur = MagicMock()
        cur.fetchall.return_value = rows
        return cur

    def test_returns_empty_when_no_rows(self):
        m = _load_scanner()
        cur = self._make_cursor([])
        result = m.scan_inverted_confidence(cur, "trading_picks")
        assert result == []
        cur.execute.assert_called_once()

    def test_returns_rows_normalised(self):
        m = _load_scanner()
        row = {
            "symbol": "BTCUSDT",
            "source_system": "quan_engine",
            "confidence": 0.91,
            "direction": "LONG",
            "created_at": datetime(2026, 5, 16, 1, 0, 0),
        }
        cur = self._make_cursor([row])
        result = m.scan_inverted_confidence(cur, "trading_picks")
        assert len(result) == 1
        # datetime should be serialised to ISO string
        assert isinstance(result[0]["created_at"], str)
        assert "2026-05-16" in result[0]["created_at"]

    def test_sql_uses_threshold_and_sources(self):
        m = _load_scanner()
        cur = self._make_cursor([])
        m.scan_inverted_confidence(cur, "trading_picks")
        sql_called = cur.execute.call_args[0][0]
        assert "confidence" in sql_called
        assert "CRYPTO" in sql_called
        assert "OPEN" in sql_called
        # Parameters include threshold + all anti-correlated sources
        params = cur.execute.call_args[0][1]
        assert params[0] == m.INVERTED_CONFIDENCE_THRESHOLD
        for src in m.ANTI_CORRELATED_SOURCES:
            assert src in params

    def test_anti_correlated_sources_contains_expected(self):
        m = _load_scanner()
        for src in ("super_signals", "luxalgo_filters", "quan_engine"):
            assert src in m.ANTI_CORRELATED_SOURCES


# ---------------------------------------------------------------------------
# 2. Direction conflict detector
# ---------------------------------------------------------------------------

class TestScanDirectionConflicts:
    def _make_cursor(self, rows):
        cur = MagicMock()
        cur.fetchall.return_value = rows
        return cur

    def test_returns_empty_when_no_conflicts(self):
        m = _load_scanner()
        cur = self._make_cursor([])
        result = m.scan_direction_conflicts(cur, "trading_picks")
        assert result == []

    def test_returns_conflict_rows(self):
        m = _load_scanner()
        conflict = {
            "symbol": "SOLUSDT",
            "directions": "LONG,SHORT",
            "pick_count": 2,
            "sources": "super_signals,quan_engine",
        }
        cur = self._make_cursor([conflict])
        result = m.scan_direction_conflicts(cur, "trading_picks")
        assert len(result) == 1
        assert result[0]["symbol"] == "SOLUSDT"
        assert "LONG" in result[0]["directions"]
        assert "SHORT" in result[0]["directions"]

    def test_sql_uses_having_count_distinct(self):
        m = _load_scanner()
        cur = self._make_cursor([])
        m.scan_direction_conflicts(cur, "trading_picks")
        sql = cur.execute.call_args[0][0]
        # Must group by symbol and filter for more than 1 distinct direction
        assert "GROUP BY symbol" in sql or "GROUP BY" in sql
        assert "HAVING" in sql
        assert "COUNT(DISTINCT direction)" in sql or "COUNT(DISTINCT" in sql

    def test_multiple_symbols_returned(self):
        m = _load_scanner()
        rows = [
            {"symbol": "BTCUSDT", "directions": "LONG,SHORT", "pick_count": 3, "sources": "a,b"},
            {"symbol": "ETHUSDT", "directions": "LONG,SHORT", "pick_count": 2, "sources": "c,d"},
        ]
        cur = self._make_cursor(rows)
        result = m.scan_direction_conflicts(cur, "trading_picks")
        assert len(result) == 2


# ---------------------------------------------------------------------------
# 3. Silent-dead strategy detector
# ---------------------------------------------------------------------------

class TestScanSilentDeadStrategies:
    def _make_cursor(self, rows):
        cur = MagicMock()
        cur.fetchall.return_value = rows
        return cur

    def test_returns_empty_when_all_strategies_active(self):
        m = _load_scanner()
        cur = self._make_cursor([])
        result = m.scan_silent_dead_strategies(cur, "trading_picks")
        assert result == []

    def test_returns_dead_strategies(self):
        m = _load_scanner()
        row = {
            "source_system": "hl_funding_fade",
            "last_pick": datetime(2026, 5, 8, 12, 0, 0),
            "total_picks": 11,
        }
        cur = self._make_cursor([row])
        result = m.scan_silent_dead_strategies(cur, "trading_picks")
        assert len(result) == 1
        assert result[0]["source_system"] == "hl_funding_fade"
        # datetime normalised
        assert isinstance(result[0]["last_pick"], str)

    def test_sql_has_7_day_having_clause(self):
        m = _load_scanner()
        cur = self._make_cursor([])
        m.scan_silent_dead_strategies(cur, "trading_picks")
        sql = cur.execute.call_args[0][0]
        assert "INTERVAL" in sql
        # 7-day gap and 30-day lookback
        assert "7" in sql
        assert "30" in sql

    def test_multiple_dead_strategies(self):
        m = _load_scanner()
        rows = [
            {"source_system": "strat_a", "last_pick": datetime(2026, 5, 1), "total_picks": 5},
            {"source_system": "strat_b", "last_pick": datetime(2026, 5, 3), "total_picks": 20},
        ]
        cur = self._make_cursor(rows)
        result = m.scan_silent_dead_strategies(cur, "trading_picks")
        assert len(result) == 2
        names = [r["source_system"] for r in result]
        assert "strat_a" in names and "strat_b" in names


# ---------------------------------------------------------------------------
# 4. run_scan — missing DB_PASS_STOCKS → sample data
# ---------------------------------------------------------------------------

class TestRunScanNoDB:
    def test_returns_sample_data_when_no_password(self, monkeypatch):
        # Remove password env vars
        for key in ("DB_PASS_STOCKS", "DB_STOCKS_PASSWORD", "MYSQL_PASSWORD"):
            monkeypatch.delenv(key, raising=False)

        m = _load_scanner(env={})
        # Patch _get_password to return None to simulate missing creds
        with patch.object(m, "_get_password", return_value=None):
            result = m.run_scan()

        assert result["mode"] == "SAMPLE_DATA"
        assert "warning" in result
        assert result["verdict"] == "ANOMALIES_FOUND"
        assert "inverted_confidence" in result["anomalies"]
        assert "direction_conflicts" in result["anomalies"]
        assert "silent_dead_strategies" in result["anomalies"]

    def test_sample_data_total_matches_counts(self, monkeypatch):
        m = _load_scanner(env={})
        with patch.object(m, "_get_password", return_value=None):
            result = m.run_scan()
        expected_total = (
            result["anomalies"]["inverted_confidence"]["count"]
            + result["anomalies"]["direction_conflicts"]["count"]
            + result["anomalies"]["silent_dead_strategies"]["count"]
        )
        assert result["total_anomalies"] == expected_total

    def test_sample_data_is_json_serialisable(self, monkeypatch):
        m = _load_scanner(env={})
        with patch.object(m, "_get_password", return_value=None):
            result = m.run_scan()
        # Should not raise
        serialised = json.dumps(result, default=str)
        parsed = json.loads(serialised)
        assert parsed["verdict"] == "ANOMALIES_FOUND"


# ---------------------------------------------------------------------------
# 5. run_scan — live DB path (mocked connection)
# ---------------------------------------------------------------------------

class TestRunScanLiveDB:
    def _mock_conn_ctx(self, inv_rows, dc_rows, sd_rows, table="trading_picks"):
        """Return a mock connection context manager + cursor."""
        cur = MagicMock()

        def fetchall_side_effect():
            # Called in order: resolve_table, inverted, conflicts, silent
            if not hasattr(fetchall_side_effect, "_call_n"):
                fetchall_side_effect._call_n = 0
            n = fetchall_side_effect._call_n
            fetchall_side_effect._call_n += 1
            return [inv_rows, dc_rows, sd_rows][n % 3]

        # resolve_table calls execute then fetchall is not used — execute returns None
        # We simulate: first execute succeeds (table found), then 3 fetchalls
        execute_call_count = [0]

        def execute_side(sql, params=None):
            execute_call_count[0] += 1

        cur.execute.side_effect = execute_side
        cur.fetchall.side_effect = [
            inv_rows,  # inverted_confidence
            dc_rows,   # direction_conflicts
            sd_rows,   # silent_dead_strategies
        ]

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur
        return conn, cur

    def test_clean_verdict_when_no_anomalies(self):
        m = _load_scanner(env={})
        conn, cur = self._mock_conn_ctx([], [], [])
        with patch.object(m, "_get_password", return_value="secret"), \
             patch.object(m, "connect", return_value=conn), \
             patch.object(m, "_resolve_table", return_value="trading_picks"):
            result = m.run_scan()
        assert result["verdict"] == "CLEAN"
        assert result["total_anomalies"] == 0

    def test_anomalies_found_verdict(self):
        m = _load_scanner(env={})
        inv_row = {
            "symbol": "BTCUSDT", "source_system": "quan_engine",
            "confidence": 0.93, "direction": "LONG",
            "created_at": datetime(2026, 5, 16),
        }
        conn, cur = self._mock_conn_ctx([inv_row], [], [])
        with patch.object(m, "_get_password", return_value="secret"), \
             patch.object(m, "connect", return_value=conn), \
             patch.object(m, "_resolve_table", return_value="trading_picks"):
            result = m.run_scan()
        assert result["verdict"] == "ANOMALIES_FOUND"
        assert result["total_anomalies"] == 1

    def test_error_path_on_connect_failure(self):
        m = _load_scanner(env={})
        with patch.object(m, "_get_password", return_value="secret"), \
             patch.object(m, "connect", side_effect=Exception("timeout")):
            result = m.run_scan()
        assert result["mode"] == "ERROR"
        assert "timeout" in result["error"]
        assert result["verdict"] == "ERROR"

    def test_result_is_json_serialisable_live_path(self):
        m = _load_scanner(env={})
        sd_row = {
            "source_system": "dead_strat",
            "last_pick": datetime(2026, 5, 8),
            "total_picks": 3,
        }
        conn, cur = self._mock_conn_ctx([], [], [sd_row])
        with patch.object(m, "_get_password", return_value="secret"), \
             patch.object(m, "connect", return_value=conn), \
             patch.object(m, "_resolve_table", return_value="trading_picks"):
            result = m.run_scan()
        serialised = json.dumps(result, default=str)
        parsed = json.loads(serialised)
        assert parsed["anomalies"]["silent_dead_strategies"]["count"] == 1


# ---------------------------------------------------------------------------
# 6. CLI flags
# ---------------------------------------------------------------------------

class TestCLI:
    def test_json_flag_outputs_valid_json(self, capsys):
        m = _load_scanner(env={})
        with patch.object(m, "_get_password", return_value=None):
            ret = m.main(["--json"])
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert "verdict" in parsed

    def test_check_flag_exits_1_on_anomalies(self):
        m = _load_scanner(env={})
        with patch.object(m, "_get_password", return_value=None):
            ret = m.main(["--check"])
        # Sample data has anomalies → exit code 1
        assert ret == 1

    def test_check_flag_exits_0_when_clean(self):
        m = _load_scanner(env={})
        clean_result = {
            "generated_at": "2026-05-16T00:00:00+00:00",
            "mode": "LIVE_DB",
            "table": "trading_picks",
            "anomalies": {
                "inverted_confidence": {"count": 0, "picks": []},
                "direction_conflicts": {"count": 0, "symbols": []},
                "silent_dead_strategies": {"count": 0, "strategies": []},
            },
            "total_anomalies": 0,
            "verdict": "CLEAN",
        }
        with patch.object(m, "run_scan", return_value=clean_result):
            ret = m.main(["--check"])
        assert ret == 0

    def test_no_flags_prints_report(self, capsys):
        m = _load_scanner(env={})
        with patch.object(m, "_get_password", return_value=None):
            m.main([])
        captured = capsys.readouterr()
        assert "MySQL Prediction Anomaly Scanner" in captured.out
        assert "INVERTED_CONFIDENCE" in captured.out
        assert "DIRECTION_CONFLICT" in captured.out
        assert "SILENT_DEAD_STRATEGY" in captured.out
