"""
Regression tests for tools/audit_pick_funnel/cli_track.py upsert logic.

Specifically guards against FINDING_OVERALL#2: argparse defaults for
--severity / --status (and similar fields on incident/enhancement) being
written into the UPDATE clause when the user did NOT pass them, which
silently flipped resolved P0s to INFO.

We monkeypatch pymysql.connect with a fake connection so the tests never
touch the live ejaguiar1_stocks DB. The fake records all executed SQL +
params, and lets us seed a "row already exists" response for the
SELECT-by-title lookup so we can exercise the UPDATE branch.
"""
from __future__ import annotations
import importlib
import os
import sys
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)


# --------------------------------------------------------------------------- #
# Fake pymysql                                                                #
# --------------------------------------------------------------------------- #
class _FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.lastrowid = None
        self.rowcount = 0
        self._last_result = None

    def execute(self, sql, params=None):
        self.conn.executed.append((sql, tuple(params) if params else ()))
        sql_strip = sql.strip().upper()
        if sql_strip.startswith("SELECT"):
            # Caller seeded a fixed response for the next SELECT.
            self._last_result = self.conn.select_response
        elif sql_strip.startswith("INSERT"):
            self.conn.inserted_rows += 1
            self.lastrowid = 100 + self.conn.inserted_rows
            self.rowcount = 1
        elif sql_strip.startswith("UPDATE"):
            self.conn.updated_rows += 1
            self.rowcount = 1

    def fetchone(self):
        return self._last_result

    def fetchall(self):
        return [self._last_result] if self._last_result else []

    def __enter__(self): return self
    def __exit__(self, *a): pass


class _FakeConn:
    def __init__(self):
        self.executed = []
        self.committed = 0
        self.closed = False
        self.select_response = None
        self.inserted_rows = 0
        self.updated_rows = 0

    def cursor(self): return _FakeCursor(self)
    def commit(self): self.committed += 1
    def close(self): self.closed = True


@pytest.fixture
def cli(monkeypatch):
    """Import cli_track with pymysql.connect monkeypatched."""
    # ensure DB_PASS_STOCKS env is set so module import doesn't choke
    monkeypatch.setenv("DB_PASS_STOCKS", "test-not-used")
    # Force a fresh import so our monkeypatch sticks
    mod_name = "tools.audit_pick_funnel.cli_track"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    cli_track = importlib.import_module(mod_name)

    conns = []

    def fake_connect(*a, **kw):
        c = _FakeConn()
        conns.append(c)
        return c

    monkeypatch.setattr(cli_track.pymysql, "connect", fake_connect)
    cli_track._conns = conns  # type: ignore[attr-defined]
    return cli_track


def _run(cli_track, argv):
    """Invoke main() with the given argv."""
    old = sys.argv
    sys.argv = ["cli_track.py"] + argv
    try:
        cli_track.main()
    finally:
        sys.argv = old


def _last_insert(conn):
    for sql, params in reversed(conn.executed):
        if sql.strip().upper().startswith("INSERT"):
            return sql, params
    return None, None


def _last_update(conn):
    for sql, params in reversed(conn.executed):
        if sql.strip().upper().startswith("UPDATE"):
            return sql, params
    return None, None


# --------------------------------------------------------------------------- #
# FINDING tests                                                               #
# --------------------------------------------------------------------------- #
def test_finding_insert_full_args(cli):
    _run(cli, [
        "finding", "--class", "OVERALL", "--title", "new-thing",
        "--description", "desc", "--severity", "P1", "--status", "CONFIRMED",
        "--agent", "claude-opus-4-7", "--evidence", "file:42",
        "--linked-incident-id", "7", "--linked-enhancement-id", "9",
    ])
    conn = cli._conns[-1]
    sql, params = _last_insert(conn)
    assert "FINDING_OVERALL" in sql
    assert "description" in sql and "severity" in sql and "status" in sql
    # title is first column, then field_map columns in order
    assert params == ("new-thing", "desc", "P1", "CONFIRMED",
                      "claude-opus-4-7", "file:42", 7, 9)


def test_finding_insert_only_required_uses_documented_defaults(cli):
    _run(cli, ["finding", "--class", "OVERALL", "--title", "bare"])
    conn = cli._conns[-1]
    sql, params = _last_insert(conn)
    # title + (description=None, severity=INFO, status=OPEN, agent=None,
    # evidence=None, linked_incident_id=None, linked_enhancement_id=None)
    assert params == ("bare", None, "INFO", "OPEN", None, None, None, None)


def test_finding_update_without_severity_preserves_existing_severity_REGRESSION(cli):
    """The exact FINDING_OVERALL#2 regression: marking RESOLVED must NOT clobber P0->INFO."""
    cli._conns  # noqa
    # Monkeypatch _connect to seed a SELECT response
    orig_connect = cli.pymysql.connect

    def seeded(*a, **kw):
        c = orig_connect()
        c.select_response = {"id": 42, "severity": "P0"}
        return c
    cli.pymysql.connect = seeded

    _run(cli, [
        "finding", "--class", "OVERALL", "--title", "existing",
        "--status", "RESOLVED",
    ])
    conn = cli._conns[-1]
    sql, params = _last_update(conn)
    assert sql is not None, "should have hit UPDATE branch"
    # The UPDATE SET clause must NOT contain severity (we didn't pass it)
    assert "severity=" not in sql, f"severity must not be in UPDATE SET when omitted; got: {sql}"
    assert "status=%s" in sql
    # params: [status, id]
    assert params == ("RESOLVED", 42)


def test_finding_update_only_description(cli):
    orig_connect = cli.pymysql.connect

    def seeded(*a, **kw):
        c = orig_connect()
        c.select_response = {"id": 7, "severity": "P1"}
        return c
    cli.pymysql.connect = seeded

    _run(cli, [
        "finding", "--class", "OVERALL", "--title", "x",
        "--description", "new desc",
    ])
    conn = cli._conns[-1]
    sql, params = _last_update(conn)
    assert sql is not None
    assert "description=%s" in sql
    assert "severity=" not in sql
    assert "status=" not in sql
    assert "agent=" not in sql
    assert params == ("new desc", 7)


def test_finding_update_only_linked_incident(cli):
    orig_connect = cli.pymysql.connect

    def seeded(*a, **kw):
        c = orig_connect()
        c.select_response = {"id": 11, "severity": "INFO"}
        return c
    cli.pymysql.connect = seeded

    _run(cli, [
        "finding", "--class", "OVERALL", "--title", "x",
        "--linked-incident-id", "55",
    ])
    conn = cli._conns[-1]
    sql, params = _last_update(conn)
    assert "linked_incident_id=%s" in sql
    assert "severity=" not in sql and "status=" not in sql
    assert params == (55, 11)


def test_finding_invalid_class(cli):
    with pytest.raises(SystemExit):
        _run(cli, ["finding", "--class", "BOGUS", "--title", "x"])


def test_finding_invalid_severity(cli):
    with pytest.raises(SystemExit):
        _run(cli, ["finding", "--class", "OVERALL", "--title", "x", "--severity", "NUKE"])


def test_finding_invalid_status(cli):
    with pytest.raises(SystemExit):
        _run(cli, ["finding", "--class", "OVERALL", "--title", "x", "--status", "WHATEVER"])


def test_finding_idempotent_same_insert_twice_updates_not_duplicates(cli):
    """Second call with same title hits UPDATE path (no second INSERT)."""
    # First call: row does not exist -> INSERT
    _run(cli, ["finding", "--class", "OVERALL", "--title", "dupe-test"])
    first_conn = cli._conns[-1]
    assert first_conn.inserted_rows == 1
    assert first_conn.updated_rows == 0

    # Second call: seed the SELECT to return an existing row -> UPDATE
    orig_connect = cli.pymysql.connect

    def seeded(*a, **kw):
        c = orig_connect()
        c.select_response = {"id": 101, "severity": "INFO"}
        return c
    cli.pymysql.connect = seeded

    _run(cli, ["finding", "--class", "OVERALL", "--title", "dupe-test",
               "--description", "second time"])
    second_conn = cli._conns[-1]
    assert second_conn.inserted_rows == 0, "must not INSERT a duplicate"
    assert second_conn.updated_rows == 1


# --------------------------------------------------------------------------- #
# INCIDENT + ENHANCEMENT regression tests (same null-overwrite bug)           #
# --------------------------------------------------------------------------- #
def test_incident_update_without_severity_preserves_existing(cli):
    orig_connect = cli.pymysql.connect

    def seeded(*a, **kw):
        c = orig_connect()
        c.select_response = {"incident_id": 4}
        return c
    cli.pymysql.connect = seeded

    _run(cli, [
        "incident", "--class", "OVERALL", "--title", "old-inc",
        "--status", "RESOLVED",
    ])
    conn = cli._conns[-1]
    sql, params = _last_update(conn)
    assert sql is not None
    assert "severity=" not in sql, \
        f"severity must not be in incident UPDATE SET when omitted; got: {sql}"
    assert "status=%s" in sql
    # status=RESOLVED triggers resolved_at auto-stamp
    assert "resolved_at=IFNULL" in sql


def test_enhancement_update_without_status_preserves_existing(cli):
    orig_connect = cli.pymysql.connect

    def seeded(*a, **kw):
        c = orig_connect()
        c.select_response = {"enhancement_id": 9}
        return c
    cli.pymysql.connect = seeded

    _run(cli, [
        "enhancement", "--class", "OVERALL", "--title", "old-enh",
        "--description", "tweak",
    ])
    conn = cli._conns[-1]
    sql, params = _last_update(conn)
    assert sql is not None
    # User passed only --description, so status/category/impact/effort must NOT
    # be in the SET clause (would clobber existing with BACKLOG/OTHER/UNKNOWN/M).
    for clobber_risk in ("status=", "category=", "expected_impact=", "effort="):
        assert clobber_risk not in sql, \
            f"{clobber_risk} must not appear in enhancement UPDATE SET when omitted"
    assert "description=%s" in sql
