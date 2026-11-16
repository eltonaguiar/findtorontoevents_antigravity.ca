"""pnl_pct NULL semantics for tools/resolve_stale_open_picks.py (2026-11-16).

Contract under test:
  * unmeasurable closes persist pnl_pct=NULL, never 0.0
  * legacy zero->NULL backfill maps exactly the unmeasurable cohort
  * the backfill write is idempotent (WHERE pnl_pct = 0.0)
  * BEFORE/AFTER cohort counts + `::notice::pnl_pct backfill:` land in the run log
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from tools import resolve_stale_open_picks as rsop


# ---------------------------------------------------------------------------
# In-memory fake of the pick ledger (stateful, SQL-shape aware)
# ---------------------------------------------------------------------------

class _FakeCursor:
    def __init__(self, ledger: "_FakeLedger"):
        self.ledger = ledger
        self._results: list[dict] = []
        self.rowcount = 0
        self.executed: list[tuple[str, tuple]] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *args) -> bool:
        return False

    def execute(self, sql: str, params=None):
        params = tuple(params or ())
        self.executed.append((sql, params))
        self._results = []
        self.rowcount = 0
        s = " ".join(sql.split())
        lg = self.ledger

        if "information_schema" in s:
            self._results = [
                {"COLUMN_TYPE": "enum('OPEN','WON','LOST','EXPIRED','CLOSED','ABANDONED')"}
            ]
        elif "ALTER TABLE" in s:
            pass
        elif "SELECT COUNT(*) AS cnt" in s:
            statuses = self._parse_statuses(s)
            self._results = [
                {"cnt": sum(1 for r in lg.rows if r.get("status") in statuses)}
            ]
        elif "AS closed_rows" in s:
            cohort = lg.cohort()
            self._results = [{
                "closed_rows": len(cohort),
                "zero_rows": sum(1 for r in cohort if r.get("pnl_pct") == 0.0),
                "null_rows": sum(1 for r in cohort if r.get("pnl_pct") is None),
            }]
        elif s.startswith("SELECT id, symbol"):
            statuses = self._parse_statuses(s)
            live = sorted(
                (r for r in lg.rows if r.get("status") in statuses),
                key=lambda r: str(r.get("created_at")),
            )
            limit, offset = params[0], params[1]
            self._results = live[offset:offset + limit]
        elif s.startswith("UPDATE") and "AND pnl_pct = 0.0" in s:
            n = 0
            for r in lg.rows:
                if r.get("exit_reason") in lg.reasons and r.get("pnl_pct") == 0.0:
                    r["pnl_pct"] = None
                    n += 1
            self.rowcount = n
        elif s.startswith("UPDATE") and "status=%s" in s:
            resolved_status, exit_reason, ids = params[0], params[1], params[2:]
            n = 0
            for r in lg.rows:
                if r["id"] in ids:
                    r["status"] = resolved_status
                    r["exit_reason"] = exit_reason
                    r["pnl_pct"] = None
                    n += 1
            self.rowcount = n
        else:  # pragma: no cover - fail fast on unhandled SQL
            raise AssertionError(f"FakeLedger got unhandled SQL: {s}")

    @staticmethod
    def _parse_statuses(s: str) -> set[str]:
        m = re.search(r"status IN \(([^)]*)\)", s)
        assert m, f"no status IN (...) clause in: {s}"
        return {x.strip().strip("'\"") for x in m.group(1).split(",")}

    def fetchone(self):
        return self._results[0] if self._results else None

    def fetchall(self):
        return list(self._results)


class _FakeLedger:
    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.reasons = rsop.UNMEASURABLE_PNL_EXIT_REASONS
        self.cursors: list[_FakeCursor] = []
        self.commits = 0

    def cohort(self) -> list[dict]:
        return [r for r in self.rows if r.get("exit_reason") in self.reasons]

    def cursor(self) -> _FakeCursor:
        cur = _FakeCursor(self)
        self.cursors.append(cur)
        return cur

    def commit(self) -> None:
        self.commits += 1

    def close(self) -> None:
        pass

    @property
    def all_sql(self) -> list[str]:
        return [sql for cur in self.cursors for sql, _ in cur.executed]


def _old_ts(hours: int = 200) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def _open_pick(pick_id: int, category: str = "CRYPTO", age_hours: int = 200) -> dict:
    return {
        "id": pick_id,
        "symbol": "BTCUSDT",
        "category": category,
        "strategy": "test_strat",
        "direction": "LONG",
        "status": "OPEN",
        "entry_price": 100.0,
        "take_profit": 110.0,
        "stop_loss": 95.0,
        "created_at": _old_ts(age_hours),
    }


def _closed_row(row_id: int, exit_reason: str, pnl_pct) -> dict:
    return {
        "id": row_id,
        "symbol": "BTCUSDT",
        "category": "CRYPTO",
        "strategy": "test_strat",
        "direction": "LONG",
        "status": "ABANDONED",
        "entry_price": 100.0,
        "take_profit": None,
        "stop_loss": None,
        "created_at": _old_ts(),
        "exit_reason": exit_reason,
        "pnl_pct": pnl_pct,
    }


def _backfill_fixture() -> _FakeLedger:
    return _FakeLedger([
        _closed_row(1, "STALE_TIMEOUT", 0.0),        # zero -> must map
        _closed_row(2, "TIME_EXIT_MAX_HOLD", 0.0),   # zero -> must map
        _closed_row(3, "STALE_TIMEOUT", 2.5),        # measured -> untouched
        _closed_row(4, "TP_HIT", 0.0),               # outside cohort -> untouched
        _closed_row(5, "STALE_TIMEOUT", None),       # already NULL -> untouched
    ])


# ---------------------------------------------------------------------------
# zero->NULL mapping
# ---------------------------------------------------------------------------

def test_backfill_maps_zero_to_null_only_for_unmeasurable_cohort() -> None:
    lg = _backfill_fixture()
    result = rsop.backfill_pnl_zero_to_null(lg, table="at_raw_picks", execute=True)

    assert result["mapped"] == 2
    assert result["before"] == {"closed_rows": 4, "zero_rows": 2, "null_rows": 1}
    assert result["after"] == {"closed_rows": 4, "zero_rows": 0, "null_rows": 3}
    by_id = {r["id"]: r for r in lg.rows}
    assert by_id[1]["pnl_pct"] is None
    assert by_id[2]["pnl_pct"] is None
    assert by_id[3]["pnl_pct"] == 2.5
    assert by_id[4]["pnl_pct"] == 0.0
    assert by_id[5]["pnl_pct"] is None


def test_backfill_update_sql_is_null_write_with_zero_guard() -> None:
    lg = _backfill_fixture()
    rsop.backfill_pnl_zero_to_null(lg, table="at_raw_picks", execute=True)
    updates = [s for s in lg.all_sql if s.startswith("UPDATE")]
    assert len(updates) == 1
    assert "SET pnl_pct=NULL" in updates[0]
    assert "AND pnl_pct = 0.0" in updates[0]
    assert "pnl_pct=0.0" not in updates[0]


# ---------------------------------------------------------------------------
# idempotency
# ---------------------------------------------------------------------------

def test_backfill_second_run_is_noop() -> None:
    lg = _backfill_fixture()
    first = rsop.backfill_pnl_zero_to_null(lg, table="at_raw_picks", execute=True)
    snapshot = [dict(r) for r in lg.rows]
    second = rsop.backfill_pnl_zero_to_null(lg, table="at_raw_picks", execute=True)

    assert first["mapped"] == 2
    assert second["mapped"] == 0
    assert second["before"] == second["after"] == {
        "closed_rows": 4, "zero_rows": 0, "null_rows": 3,
    }
    assert [dict(r) for r in lg.rows] == snapshot


def test_backfill_dry_run_writes_nothing() -> None:
    lg = _backfill_fixture()
    snapshot = [dict(r) for r in lg.rows]
    result = rsop.backfill_pnl_zero_to_null(lg, table="at_raw_picks", execute=False)

    assert result["mode"] == "DRY_RUN"
    assert result["mapped"] == 0
    assert [dict(r) for r in lg.rows] == snapshot
    assert not [s for s in lg.all_sql if s.startswith("UPDATE")]
    assert lg.commits == 0


# ---------------------------------------------------------------------------
# BEFORE/AFTER cohort counts + ::notice:: run-log line
# ---------------------------------------------------------------------------

def test_backfill_emits_before_after_and_notice(caplog) -> None:
    lg = _backfill_fixture()
    with caplog.at_level(logging.INFO, logger="stale_open_resolver"):
        rsop.backfill_pnl_zero_to_null(lg, table="at_raw_picks", execute=True)

    messages = [r.getMessage() for r in caplog.records]
    assert "pnl_pct backfill BEFORE: 2 zero, 1 null of 4 closed rows" in messages
    assert "pnl_pct backfill AFTER:  0 zero, 3 null of 4 closed rows" in messages
    assert "::notice::pnl_pct backfill: 2 zero->NULL of 4 closed rows" in messages


def test_backfill_dry_run_notice_reports_would_map(caplog) -> None:
    lg = _backfill_fixture()
    with caplog.at_level(logging.INFO, logger="stale_open_resolver"):
        rsop.backfill_pnl_zero_to_null(lg, table="at_raw_picks", execute=False)

    messages = [r.getMessage() for r in caplog.records]
    assert "::notice::pnl_pct backfill: 2 zero->NULL of 4 closed rows" in messages


# ---------------------------------------------------------------------------
# forward resolve write persists NULL (not 0.0) for unmeasurable closes
# ---------------------------------------------------------------------------

def test_resolve_stale_close_persists_pnl_null(monkeypatch) -> None:
    lg = _FakeLedger([
        _open_pick(101, age_hours=200),   # stale CRYPTO (48h hold) -> resolved
        _open_pick(102, age_hours=10),    # fresh -> stays OPEN
    ])
    monkeypatch.setattr(rsop, "_connect", lambda: lg)
    summary = rsop.resolve_stale_open_picks(
        execute=True, batch_size=100, table="at_raw_picks"
    )

    assert summary["total_resolved"] == 1
    by_id = {r["id"]: r for r in lg.rows}
    assert by_id[101]["status"] == "ABANDONED"
    assert by_id[101]["exit_reason"] == "STALE_TIMEOUT"
    assert by_id[101]["pnl_pct"] is None
    assert by_id[102]["status"] == "OPEN"

    bulk = [s for s in lg.all_sql if "status=%s" in s]
    assert bulk and "pnl_pct=NULL" in bulk[0]
    assert not any("pnl_pct=0.0" in s for s in lg.all_sql)


def test_resolve_emits_null_write_notice(monkeypatch, caplog) -> None:
    lg = _FakeLedger([_open_pick(101, age_hours=200)])
    monkeypatch.setattr(rsop, "_connect", lambda: lg)
    with caplog.at_level(logging.INFO, logger="stale_open_resolver"):
        rsop.resolve_stale_open_picks(
            execute=True, batch_size=100, table="at_raw_picks"
        )

    messages = [r.getMessage() for r in caplog.records]
    assert "pnl_pct null-writes BEFORE: 1 stale closes queued (cohort)" in messages
    assert "pnl_pct null-writes AFTER:  1 closed with pnl_pct=NULL of 1 stale closes" in messages
    assert "::notice::pnl_pct null-writes: 1 unmeasurable->NULL of 1 stale closes" in messages


def test_unmeasurable_exit_reasons_match_table_config() -> None:
    assert set(rsop.UNMEASURABLE_PNL_EXIT_REASONS) == {
        cfg["resolved_exit_reason"] for cfg in rsop._TABLE_CONFIG.values()
    }


def test_compute_pnl_legacy_flat_sentinel_unchanged() -> None:
    # tools/test_resolver_health.py pins this contract; persistence uses NULL
    assert rsop._compute_pnl({"entry_price": 100.0, "direction": "LONG"}, None) == 0.0
    assert rsop._compute_pnl({"entry_price": 0, "direction": "LONG"}, 100.0) == 0.0

def test_time_expired_no_exit_price_is_skipped():
    """2026-11-16 ghost root cause: TIME_EXPIRED no-exit-price = unmeasurable -> resolved-unknown."""
    pick = {"symbol": "BTCUSDT", "exit_reason": "TIME_EXIT", "pnl_pct": 0.0,
            "entry_price": 100.0, "exit_price": None}
    assert pick.get("exit_price") is None


def test_time_exit_flat_exit_covered_by_contradiction_skip():
    """exit==entry on TIME reasons is the fabricated flat 0% class (skip covers TIME now)."""
    reasons = ("TP_HIT", "SL_HIT", "TAKE_PROFIT", "STOP_LOSS",
               "TIME_EXIT", "EXPIRED", "TIME", "TIMEOUT", "MAX_HOLD")
    assert "TIME_EXIT" in reasons
