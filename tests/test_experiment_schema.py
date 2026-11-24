"""The experiment ledger DDL is one file, it parses under sqlite3, and the
tracker does not keep a second copy of it.

Regression note: tools/experiment_tracker.py used to declare its own five-table
SCHEMA literal while docs/experiment_schema.sql (on a feature branch) declared
twelve, and docs/evaluation_harness.md asserted the two matched. Nothing failed.
test_tracker_does_not_declare_its_own_ddl is the guard against that returning.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SCHEMA_PATH = ROOT / "docs" / "experiment_schema.sql"
PG_SCHEMA_PATH = ROOT / "docs" / "experiment_schema.pg.sql"

# The twelve logical tables in the Postgres original, in its declaration order.
EXPECTED_TABLES = [
    "runs",
    "run_params",
    "market_events",
    "signals",
    "orders",
    "fills",
    "positions",
    "portfolio_snapshots",
    "risk_events",
    "metrics",
    "artifacts",
    "mc_runs",
]

# The tables the tracker actually reads and writes today. Must stay a subset of
# the contract above -- if the tracker grows a table, add it to the DDL first.
TRACKER_TABLES = {"runs", "run_params", "metrics", "artifacts", "mc_runs"}


def _table_names(cx) -> list[str]:
    return [r[0] for r in cx.execute("select name from sqlite_master where type='table'")]


def test_schema_file_exists():
    assert SCHEMA_PATH.is_file(), f"missing {SCHEMA_PATH}"


def test_schema_creates_exactly_the_twelve_contract_tables():
    cx = sqlite3.connect(":memory:")
    try:
        cx.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        assert _table_names(cx) == EXPECTED_TABLES
    finally:
        cx.close()


def test_table_count_is_twelve_without_internal_tables():
    """The user-facing check: no sqlite_sequence, so the count is the real one."""
    cx = sqlite3.connect(":memory:")
    try:
        cx.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        names = _table_names(cx)
        assert len(names) == 12, names
        assert not [n for n in names if n.startswith("sqlite_")], names
    finally:
        cx.close()


def test_schema_is_idempotent():
    """init_db() may run against an existing database."""
    cx = sqlite3.connect(":memory:")
    try:
        ddl = SCHEMA_PATH.read_text(encoding="utf-8")
        cx.executescript(ddl)
        cx.executescript(ddl)
        assert len(_table_names(cx)) == 12
    finally:
        cx.close()


@pytest.mark.parametrize("table", sorted(TRACKER_TABLES))
def test_tracker_tables_exist_in_the_contract(table):
    cx = sqlite3.connect(":memory:")
    try:
        cx.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        assert table in _table_names(cx)
    finally:
        cx.close()


def test_tracker_does_not_declare_its_own_ddl():
    """Two copies of a schema always drift; the absence of a literal is the test.

    Comments are stripped first -- prose *about* not declaring DDL is fine, an
    actual statement is not.
    """
    src = (ROOT / "tools" / "experiment_tracker.py").read_text(encoding="utf-8")
    code = "\n".join(
        line for line in src.splitlines() if not line.lstrip().startswith("#")
    ).upper()
    assert "CREATE TABLE" not in code
    assert "load_schema()" in src


def test_tracker_initialises_from_the_schema_file(tmp_path):
    from tools import experiment_tracker as et

    db = str(tmp_path / "runs.db")
    et.init_db(db)
    with sqlite3.connect(db) as cx:
        assert _table_names(cx) == EXPECTED_TABLES


def test_tracker_roundtrip_still_works(tmp_path):
    from tools import experiment_tracker as et

    db = str(tmp_path / "runs.db")
    et.init_db(db)
    rid = et.log_run(
        db,
        run_type="backtest",
        strategy_name="s",
        strategy_version="v1",
        git_commit="abc123",
        data_snapshot_id="snap1",
        start_ts="2026-01-01",
        end_ts="2026-11-24",
        params={"w": 10},
        metrics=[{"name": "cagr", "value": 0.12, "scope": "overall"}],
        artifacts=[{"type": "json", "path": "reports/x.json", "checksum": "deadbeef"}],
    )
    r = et.query_run(db, rid)
    assert r["strategy_name"] == "s"
    assert r["metrics"][0]["metric_name"] == "cagr"


def test_tracker_has_no_mutating_api():
    from tools import experiment_tracker as et

    for bad in ("update_run", "delete_run", "update_metric", "delete_artifact"):
        assert not hasattr(et, bad), bad


def test_postgres_original_is_preserved():
    """The dialect that can enforce JSONB/TIMESTAMPTZ should not be deleted."""
    assert PG_SCHEMA_PATH.is_file()
    text = PG_SCHEMA_PATH.read_text(encoding="utf-8")
    assert "JSONB" in text and "TIMESTAMPTZ" in text
    assert text.count("CREATE TABLE") == 12
