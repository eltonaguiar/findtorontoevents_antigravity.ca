"""pnl_pct NULL aggregate semantics for tools/sync_summary_picks_json.py.

Contract under test (2026-11-16 fleet fix):
  * NULL (unmeasurable close) is excluded from avg/sum
  * NULL-pnl closed rows still count as resolved-unknown
  * a measured 0.0 remains a legitimate flat trade in the averages
  * the MySQL aggregate keeps the AVG(CASE WHEN pnl_pct IS NOT NULL...) guard
"""
from __future__ import annotations

import sys
import types

from tools import sync_summary_picks_json as spj


def _stats() -> dict:
    return {
        "total_picks": 0, "resolved": 0, "resolved_unknown": 0,
        "wins": 0, "losses": 0,
        "pnl_sum": 0.0, "pnl_n": 0, "last_pick": "",
    }


# ---------------------------------------------------------------------------
# aggregate exclusion (local-JSON accumulation path)
# ---------------------------------------------------------------------------

def test_null_excluded_from_avg_sum_but_counted_resolved_unknown() -> None:
    s = _stats()
    spj._accumulate_pick(s, {"status": "TIME_EXIT", "pnl_pct": None})
    spj._accumulate_pick(s, {"status": "ABANDONED", "pnl_pct": None})
    spj._accumulate_pick(s, {"status": "WON", "pnl_pct": 2.0})

    assert s["total_picks"] == 3
    assert s["resolved"] == 3
    assert s["resolved_unknown"] == 2
    assert s["pnl_n"] == 1
    assert s["pnl_sum"] == 2.0
    assert s["wins"] == 1
    assert s["losses"] == 0


def test_measured_zero_stays_in_average() -> None:
    s = _stats()
    spj._accumulate_pick(s, {"status": "CLOSED", "pnl_pct": 0.0})
    spj._accumulate_pick(s, {"status": "WON", "pnl_pct": 2.0})

    assert s["resolved_unknown"] == 0
    assert s["pnl_n"] == 2
    assert s["pnl_sum"] == 2.0  # avg 1.0 — measured flat trade, not unknown


def test_resolver_close_statuses_count_as_resolved() -> None:
    s = _stats()
    spj._accumulate_pick(s, {"status": "TIME_EXIT", "pnl_pct": None})
    spj._accumulate_pick(s, {"status": "ABANDONED", "pnl_pct": None})
    spj._accumulate_pick(s, {"status": "EXPIRED", "pnl_pct": None})

    assert s["resolved"] == 3
    assert s["resolved_unknown"] == 3
    assert s["wins"] == 0 and s["losses"] == 0


def test_open_pick_without_pnl_not_resolved() -> None:
    s = _stats()
    spj._accumulate_pick(s, {"status": "OPEN", "pnl_pct": None})
    assert s["resolved"] == 0
    assert s["resolved_unknown"] == 0


def test_payload_avg_excludes_nulls_and_surfaces_unknown() -> None:
    stats = {"CRYPTO": _stats()}
    s = stats["CRYPTO"]
    spj._accumulate_pick(s, {"status": "TIME_EXIT", "pnl_pct": None})
    spj._accumulate_pick(s, {"status": "TIME_EXIT", "pnl_pct": None})
    spj._accumulate_pick(s, {"status": "WON", "pnl_pct": 2.0})

    payload = spj._format_payload(stats, source="test")
    cls = payload["asset_classes"][0]
    assert cls["resolved"] == 3
    assert cls["resolved_unknown"] == 2
    assert cls["avg_pnl_pct"] == 2.0  # NOT 0.67 — NULLs excluded from avg
    assert payload["n_resolved_unknown"] == 2


def test_payload_null_only_class_avg_is_none() -> None:
    stats = {"CRYPTO": _stats()}
    spj._accumulate_pick(stats["CRYPTO"], {"status": "TIME_EXIT", "pnl_pct": None})
    payload = spj._format_payload(stats, source="test")
    assert payload["asset_classes"][0]["avg_pnl_pct"] is None
    assert payload["asset_classes"][0]["resolved_unknown"] == 1


def test_zero_to_null_semantics_change_averages() -> None:
    # BEFORE the fix the resolver wrote 0.0: closes (-2, 0 fake, +4) -> avg 0.67
    legacy = _stats()
    for pnl in (-2.0, 0.0, 4.0):
        spj._accumulate_pick(legacy, {"status": "TIME_EXIT", "pnl_pct": pnl})
    assert legacy["pnl_n"] == 3
    assert round(legacy["pnl_sum"] / legacy["pnl_n"], 2) == 0.67

    # AFTER: the unmeasurable close is NULL -> avg over measured only (-2, +4)
    fixed = _stats()
    for pnl in (-2.0, None, 4.0):
        spj._accumulate_pick(fixed, {"status": "TIME_EXIT", "pnl_pct": pnl})
    assert fixed["resolved"] == 3
    assert fixed["resolved_unknown"] == 1
    assert fixed["pnl_n"] == 2
    assert round(fixed["pnl_sum"] / fixed["pnl_n"], 2) == 1.0


# ---------------------------------------------------------------------------
# MySQL aggregate path: NULL guard + resolved-unknown CASE
# ---------------------------------------------------------------------------

class _FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.executed_sql = ""

    def execute(self, sql, params=None):
        self.executed_sql = sql

    def fetchall(self):
        return self.rows


class _FakeConn:
    def __init__(self, rows):
        self._cur = _FakeCursor(rows)

    def cursor(self):
        return self._cur

    def close(self):
        pass


def _run_mysql(monkeypatch, rows):
    conn = _FakeConn(rows)
    monkeypatch.setenv("DB_PASS_STOCKS", "test-only")
    monkeypatch.setitem(
        sys.modules,
        "pymysql",
        types.SimpleNamespace(
            connect=lambda **kw: conn,
            cursors=types.SimpleNamespace(DictCursor=object),
        ),
    )
    payload = spj._from_mysql()
    return payload, conn._cur.executed_sql


def test_mysql_aggregate_sql_excludes_null_and_counts_unknown(monkeypatch) -> None:
    rows = [{
        "category": "CRYPTO",
        "total_picks": 3,
        "resolved": 3,
        "resolved_unknown": 2,
        "wins": 1,
        "losses": 0,
        "avg_pnl_pct": 2.0,
        "last_pick": None,
    }]
    payload, sql = _run_mysql(monkeypatch, rows)

    assert "AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct ELSE NULL END)" in sql
    assert "pnl_pct IS NULL" in sql  # resolved_unknown CASE
    assert payload["n_resolved_unknown"] == 2
    cls = payload["asset_classes"][0]
    assert cls["resolved_unknown"] == 2
    assert cls["avg_pnl_pct"] == 2.0


def test_mysql_null_avg_maps_to_none(monkeypatch) -> None:
    rows = [{
        "category": "FOREX",
        "total_picks": 2,
        "resolved": 2,
        "resolved_unknown": 2,
        "wins": 0,
        "losses": 0,
        "avg_pnl_pct": None,  # all-NULL cohort -> SQL AVG returns NULL
        "last_pick": None,
    }]
    payload, _ = _run_mysql(monkeypatch, rows)
    assert payload["asset_classes"][0]["avg_pnl_pct"] is None
    assert payload["n_resolved_unknown"] == 2
