"""Tests for tools/audit3_db_sync.py — plan building, idempotency, dry-run safety.

No database is touched: every test either builds a plan from fixtures or injects a
recording fake connection.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import audit3_db_sync as sync  # noqa: E402


LEDGER = {
    "schema": "audit3.v1",
    "generated_at": "2026-11-19T16:53:50.651880+00:00",
    "source_generated_at": "2026-11-19T16:05:18.497265+00:00",
    "summary": {
        "n_rows": 8613, "n_cells_total": 359, "n_cells_tested": 67,
        "n_proven": 0, "n_candidate": 0, "n_weak": 59, "n_kill": 8, "n_insufficient": 292,
    },
    "selection_alpha": {"available": False},
    "forward_gate": {
        "n_rows": 430, "fingerprint": "5771c6fac172ca46",
        "pods": {
            "POD-CRYPTO-POSITION": {
                "status": "observe", "hypothesis_id": "H-144", "n_forward": 0,
                "min_n": 100, "eligible": False, "promotion_blocked_by_status": "observe",
                "reasons": ["observe pods cannot promote"], "pf_ci_lb": None, "ir": None,
            }
        },
    },
    "classes": [
        {"asset_class": "CRYPTO", "n": 6740, "verdict": "KILL", "wr": 0.39,
         "net_expectancy_pct": -0.13, "net_ci_pct": [-0.4, 0.1], "q_value": 0.01},
    ],
    "cells": [
        {"asset_class": "CRYPTO", "strategy": "luxalgo_confluence", "direction": "LONG",
         "namespace": "discovery", "n": 2066, "wins": 824, "wr": 0.3988, "pf": 0.904,
         "net_expectancy_pct": -0.1377, "net_ci_pct": [-0.473, 0.1797],
         "net_ci_pct_2x": [-0.573, 0.0797], "mean_cost_pct": 0.1, "q_value": 1.0,
         "harm_q": None, "dsr": 0.0, "required_n": 4069, "verdict": "WEAK",
         "raw_verdict": "WEAK", "reasons": ["no claim"], "recent_ok": False,
         "stress_2x_ok": False},
        {"asset_class": "ETF", "strategy": "fabers_taa", "direction": "LONG",
         "namespace": "confirmatory", "n": 261, "wins": 140, "wr": 0.536,
         "net_expectancy_pct": 0.21, "net_ci_pct": [0.05, 0.37],
         "verdict": "INSUFFICIENT_N", "alpha_gate": {"status": "unmeasured"}},
    ],
    "provenance": {
        "git_sha": "23659ecdc825", "input_sha256": "d0107055", "generator_version": "audit3.v2",
    },
}

FORWARD_LINES = [
    {"id": "fwd_1", "hypothesis_id": "H-119", "symbol": "SOLUSDT", "asset_class": "CRYPTO",
     "side": "LONG", "opened_at": "2026-11-17T19:02:27+00:00",
     "closed_at": "2026-11-18T01:10:27+00:00", "entry_px": 72.62, "exit_px": 74.798,
     "gross_mismatch_pp": 0.1809, "slippage_bps": 16.0, "intrabar_first_touch": True,
     "regime_ok": True, "resolver_version": "at_signal_outcomes.intrabar.v1"},
    {"id": "fwd_2", "hypothesis_id": "H-119", "symbol": "BTCUSDT", "asset_class": "CRYPTO",
     "side": "SHORT", "opened_at": "2026-11-17T20:00:00+00:00", "closed_at": None,
     "entry_px": 91000.0, "exit_px": None, "intrabar_first_touch": False},
]

REGISTRY = {
    "schema_version": "1.0",
    "hypotheses": [
        {"id": "H-144", "asset_class": "CRYPTO", "family": "position_pod",
         "status": "PRE_REGISTERED", "registered_at": "2026-11-19",
         "description": "position pod", "acceptance_criteria": {"min_n": 100},
         "result": None},
        {"id": "H-145", "asset_class": "ETF", "family": "exit_geometry_time_exit",
         "status": "PRE_REGISTERED", "registered_at": "2026-11-19",
         "acceptance_criteria": {"bonferroni": {"alpha_corrected": 0.005556}}, "result": None},
    ],
}


@pytest.fixture()
def inputs(tmp_path: Path) -> dict:
    ledger = tmp_path / "audit3_ledger.json"
    ledger.write_text(json.dumps(LEDGER), encoding="utf-8")
    forward = tmp_path / "forward_observations.jsonl"
    forward.write_text("\n".join(json.dumps(x) for x in FORWARD_LINES) + "\n", encoding="utf-8")
    registry = tmp_path / "hypothesis_registry.json"
    registry.write_text(json.dumps(REGISTRY), encoding="utf-8")
    return {"ledger": ledger, "forward": forward, "registry": registry}


def _plan(inputs: dict) -> dict:
    return sync.plan(inputs["ledger"], inputs["forward"], inputs["registry"],
                     synced_at="2026-11-19 17:00:00")


def test_snapshot_id_is_stable_and_content_addressed(inputs):
    first = _plan(inputs)["snapshot_id"]
    second = _plan(inputs)["snapshot_id"]
    assert first == second
    assert first.startswith("snap_") and len(first) == 25
    changed = json.loads(json.dumps(LEDGER))
    changed["generated_at"] = "2026-11-19T17:53:00+00:00"
    path = inputs["ledger"]
    path.write_text(json.dumps(changed), encoding="utf-8")
    assert _plan(inputs)["snapshot_id"] != first


def test_counts_cover_cells_classes_pods_forward_hypotheses(inputs):
    plan = _plan(inputs)
    assert sync.counts(plan) == {
        "snapshot": 1, "cells": 3, "pods": 1, "forward": 2, "hypotheses": 2,
    }


def test_plan_never_opens_a_connection(inputs, monkeypatch):
    def boom():
        raise AssertionError("plan() must not connect")

    monkeypatch.setattr(sync, "apply_plan", boom)
    _plan(inputs)


def test_dry_run_main_writes_no_database(inputs, monkeypatch, tmp_path):
    called = {"n": 0}

    def boom(*args, **kwargs):
        called["n"] += 1
        raise AssertionError("--apply absent must not write")

    monkeypatch.setattr(sync, "apply_plan", boom)
    out = tmp_path / "plan.json"
    rc = sync.main(["--ledger", str(inputs["ledger"]), "--forward", str(inputs["forward"]),
                    "--registry", str(inputs["registry"]), "--json-out", str(out)])
    assert rc == 0 and called["n"] == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["dry_run"] is True and payload["counts"]["forward"] == 2


def test_placeholder_count_matches_row_width(inputs):
    plan = _plan(inputs)
    for key in sync.ORDER:
        section = plan[key]
        if not section["rows"]:
            continue
        expected = section["rows"][0].__len__()
        assert section["sql"].count("%s") == expected, key


def test_no_values_are_string_interpolated_into_sql(inputs):
    plan = _plan(inputs)
    for key in sync.ORDER:
        sql = plan[key]["sql"]
        assert "SOLUSDT" not in sql and "CRYPTO" not in sql and "H-145" not in sql


def test_pk_columns_are_never_null(inputs):
    plan = _plan(inputs)
    for row in plan["cells"]["rows"]:
        assert row[0] and row[1] and row[2] is not None
        assert row[3] is not None and row[4] is not None
    for row in plan["pods"]["rows"]:
        assert row[0] and row[1]


def test_unmeasured_alpha_status_is_carried(inputs):
    plan = _plan(inputs)
    statuses = {row[2] + ":" + row[3]: row[21] for row in plan["cells"]["rows"]}
    assert statuses["ETF:fabers_taa"] == "unmeasured"
    assert statuses["CRYPTO:luxalgo_confluence"] is None


def test_forward_dedupes_ids_and_skips_bad_lines(inputs, tmp_path):
    forward = tmp_path / "fwd.jsonl"
    forward.write_text(
        json.dumps(FORWARD_LINES[0]) + "\n"
        + json.dumps(FORWARD_LINES[0]) + "\n"
        + "{not json}\n"
        + json.dumps({"symbol": "NOPE"}) + "\n",
        encoding="utf-8",
    )
    plan = sync.plan(inputs["ledger"], forward, inputs["registry"],
                     synced_at="2026-11-19 17:00:00")
    assert len(plan["forward"]["rows"]) == 1
    assert any("not JSON" in e for e in plan["errors"])
    assert any("missing id" in e for e in plan["errors"])


def test_open_forward_row_keeps_null_exit(inputs):
    plan = _plan(inputs)
    rows = {row[0]: row for row in plan["forward"]["rows"]}
    # layout: 0 id, 1 snapshot, 2 hyp, 3 symbol, 4 class, 5 side, 6 opened, 7 closed,
    #         8 entry_px, 9 exit_px
    assert rows["fwd_2"][9] is None and rows["fwd_2"][7] is None
    assert rows["fwd_2"][8] == pytest.approx(91000.0)
    assert rows["fwd_1"][9] == pytest.approx(74.798)
    assert rows["fwd_1"][7] == "2026-11-18 01:10:27"


def test_apply_plan_uses_injected_connection_and_commits(inputs):
    class Cursor:
        def __init__(self):
            self.calls = []

        def execute(self, sql, params=None):
            self.calls.append(sql.split()[0])
            return 0

        def executemany(self, sql, rows):
            self.calls.append(f"many:{len(rows)}")
            return len(rows)

        @property
        def rowcount(self):
            return 0

    class Conn:
        def __init__(self):
            self.cur = Cursor()
            self.committed = False
            self.rolled = False

        def cursor(self):
            return self.cur

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled = True

        def close(self):
            pass

    conn = Conn()
    written = sync.apply_plan(_plan(inputs), connector=lambda: conn)
    assert conn.committed and not conn.rolled
    # one CREATE per table, then one batched upsert per table that has rows
    assert conn.cur.calls.count("CREATE") == len(sync.ORDER)
    assert "many:3" in conn.cur.calls  # 2 cells + 1 class
    assert "many:1" in conn.cur.calls  # single snapshot row
    assert set(written) == set(sync.TABLE_NAMES.values())


def test_apply_plan_rolls_back_on_failure(inputs):
    class Conn:
        def __init__(self):
            self.rolled = False

        def cursor(self):
            class C:
                def execute(self, sql, params=None):
                    raise RuntimeError("boom")

            return C()

        def rollback(self):
            self.rolled = True

        def close(self):
            pass

    conn = Conn()
    with pytest.raises(RuntimeError):
        sync.apply_plan(_plan(inputs), connector=lambda: conn)
    assert conn.rolled


def test_ddl_is_create_upsert_only(inputs):
    plan = _plan(inputs)
    for key in sync.ORDER:
        ddl = plan[key]["ddl"].upper()
        assert "CREATE TABLE IF NOT EXISTS" in ddl
        assert "DELETE" not in ddl and "TRUNCATE" not in ddl and "DROP" not in ddl
    for key in sync.ORDER:
        sql = plan[key]["sql"].upper()
        assert "ON DUPLICATE KEY UPDATE" in sql


def test_datetime_normalisation():
    assert sync._dt("2026-11-19T16:53:50.651880+00:00") == "2026-11-19 16:53:50"
    assert sync._dt("2026-11-19") == "2026-11-19 00:00:00"
    assert sync._dt(None) is None
    assert sync._dt("not a date") is None


def test_missing_registry_is_reported_not_fatal(inputs, tmp_path):
    plan = sync.plan(inputs["ledger"], inputs["forward"], tmp_path / "absent.json",
                     synced_at="2026-11-19 17:00:00")
    assert plan["hypotheses"]["rows"] == []
    assert any("absent.json" in e for e in plan["errors"])
