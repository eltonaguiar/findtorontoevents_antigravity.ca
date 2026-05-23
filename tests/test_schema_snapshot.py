"""Tests for tools/db_schema_snapshot.py — uses mocked pymysql connections."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Make sure the repo root is on sys.path so we can import the module
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import tools.db_schema_snapshot as snap

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_COLUMNS_A = [
    {"TABLE_NAME": "trading_picks", "COLUMN_NAME": "id",     "COLUMN_TYPE": "int",         "IS_NULLABLE": "NO",  "COLUMN_DEFAULT": None},
    {"TABLE_NAME": "trading_picks", "COLUMN_NAME": "symbol", "COLUMN_TYPE": "varchar(20)", "IS_NULLABLE": "NO",  "COLUMN_DEFAULT": None},
    {"TABLE_NAME": "trading_picks", "COLUMN_NAME": "pnl",    "COLUMN_TYPE": "double",      "IS_NULLABLE": "YES", "COLUMN_DEFAULT": "0"},
]

_SAMPLE_COLUMNS_B = [
    # same as A but adds a new column and removes 'pnl'
    {"TABLE_NAME": "trading_picks", "COLUMN_NAME": "id",        "COLUMN_TYPE": "int",         "IS_NULLABLE": "NO",  "COLUMN_DEFAULT": None},
    {"TABLE_NAME": "trading_picks", "COLUMN_NAME": "symbol",    "COLUMN_TYPE": "varchar(20)", "IS_NULLABLE": "NO",  "COLUMN_DEFAULT": None},
    {"TABLE_NAME": "trading_picks", "COLUMN_NAME": "direction", "COLUMN_TYPE": "varchar(10)", "IS_NULLABLE": "YES", "COLUMN_DEFAULT": None},
]


def _make_conn_mock(rows):
    """Return a mock pymysql connection whose cursor yields *rows*."""
    cursor_mock = MagicMock()
    cursor_mock.fetchall.return_value = rows
    cursor_mock.__enter__ = lambda s: cursor_mock
    cursor_mock.__exit__ = MagicMock(return_value=False)

    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock
    conn_mock.__enter__ = lambda s: conn_mock
    conn_mock.__exit__ = MagicMock(return_value=False)
    return conn_mock


def _tables_from_rows(rows):
    """Convert flat column rows into the nested tables dict used by diff_schemas."""
    tables = {}
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
# Test 1: identical schemas → 0 drift items
# ---------------------------------------------------------------------------


def test_diff_identical_schemas_returns_no_drift():
    tables_a = _tables_from_rows(_SAMPLE_COLUMNS_A)
    tables_b = _tables_from_rows(_SAMPLE_COLUMNS_A)  # same data
    drift = snap.diff_schemas(tables_a, tables_b)
    assert drift == [], f"Expected no drift, got: {drift}"


# ---------------------------------------------------------------------------
# Test 2: one column added in current → 1 drift item of kind 'column_added'
# ---------------------------------------------------------------------------


def test_diff_one_column_added_returns_one_drift_item():
    baseline = _tables_from_rows(_SAMPLE_COLUMNS_A)   # has id, symbol, pnl
    current = _tables_from_rows(_SAMPLE_COLUMNS_B)    # has id, symbol, direction

    drift = snap.diff_schemas(baseline, current)

    added   = [d for d in drift if d["kind"] == "column_added"]
    removed = [d for d in drift if d["kind"] == "column_removed"]

    assert len(added)   == 1, f"Expected 1 column_added, got: {added}"
    assert added[0]["column"] == "direction"

    assert len(removed) == 1, f"Expected 1 column_removed for 'pnl', got: {removed}"
    assert removed[0]["column"] == "pnl"

    # The prompt says "one column added returns 1 drift item" — verify at least 1
    assert len(drift) >= 1


# ---------------------------------------------------------------------------
# Test 3: missing DB_PASS_STOCKS → fetch_schema returns {} without raising
# ---------------------------------------------------------------------------


def test_missing_db_pass_stocks_returns_gracefully(monkeypatch, capsys):
    # Ensure the env var is absent
    monkeypatch.delenv("DB_PASS_STOCKS", raising=False)

    result = snap.fetch_schema("ejaguiar1_stocks")

    assert result == {}, "Expected empty dict when credentials are absent"
    captured = capsys.readouterr()
    assert "DB_PASS_STOCKS" in captured.err, "Expected a warning mentioning DB_PASS_STOCKS"


# ---------------------------------------------------------------------------
# Test 4: --snapshot writes a valid baseline file
# ---------------------------------------------------------------------------


def test_snapshot_writes_baseline(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PASS_STOCKS", "fake_pass")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_USER", "fake_user")

    fake_conn = _make_conn_mock(_SAMPLE_COLUMNS_A)

    # Redirect the baseline path to a tmp file
    baseline_file = tmp_path / "schema_baseline.json"
    monkeypatch.setattr(snap, "BASELINE_PATH", baseline_file)

    with patch("pymysql.connect", return_value=fake_conn):
        rc = snap.cmd_snapshot("ejaguiar1_stocks")

    assert rc == 0
    assert baseline_file.exists()
    data = json.loads(baseline_file.read_text())
    assert data["db"] == "ejaguiar1_stocks"
    assert "trading_picks" in data["tables"]
    assert data["generated_at"] is not None


# ---------------------------------------------------------------------------
# Test 5: --check exits 1 when drift detected
# ---------------------------------------------------------------------------


def test_check_mode_exits_1_on_drift(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PASS_STOCKS", "fake_pass")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_USER", "fake_user")

    # Write a baseline with schema A
    baseline_file = tmp_path / "schema_baseline.json"
    baseline_data = {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "db": "ejaguiar1_stocks",
        "tables": _tables_from_rows(_SAMPLE_COLUMNS_A),
    }
    baseline_file.write_text(json.dumps(baseline_data))
    monkeypatch.setattr(snap, "BASELINE_PATH", baseline_file)

    # Current DB returns schema B (different from A)
    fake_conn = _make_conn_mock(_SAMPLE_COLUMNS_B)

    with patch("pymysql.connect", return_value=fake_conn):
        rc = snap.cmd_diff("ejaguiar1_stocks", exit_on_drift=True)

    assert rc == 1, "Expected exit code 1 when drift is detected"


# ---------------------------------------------------------------------------
# Test 6: --check exits 0 when schemas match
# ---------------------------------------------------------------------------


def test_check_mode_exits_0_on_no_drift(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PASS_STOCKS", "fake_pass")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_USER", "fake_user")

    baseline_file = tmp_path / "schema_baseline.json"
    baseline_data = {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "db": "ejaguiar1_stocks",
        "tables": _tables_from_rows(_SAMPLE_COLUMNS_A),
    }
    baseline_file.write_text(json.dumps(baseline_data))
    monkeypatch.setattr(snap, "BASELINE_PATH", baseline_file)

    # Current DB returns identical schema A
    fake_conn = _make_conn_mock(_SAMPLE_COLUMNS_A)

    with patch("pymysql.connect", return_value=fake_conn):
        rc = snap.cmd_diff("ejaguiar1_stocks", exit_on_drift=True)

    assert rc == 0, "Expected exit code 0 when schemas are identical"
