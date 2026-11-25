"""Offline tests for tools/stock_picks_writer.py.

The writer exists because `stock_picks` had 11 readers and zero writers, so the
live PHP surfaces reading it served data frozen at ~5,047 hours. These tests pin
the row mapping and the idempotency contract without touching MySQL.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import stock_picks_writer as w  # noqa: E402


GOOD_PICK = {
    "symbol": "PG",
    "strategy": "stocksunify2_volatility_adjusted_momentum_v2",
    "entry_price": 169.485,
    "simulated_entry_price": 0,
    "stop_loss": 161.01,
    "score": 100.0,
    "rating": "STRONG BUY",
    "risk": "Low",
    "timeframe": "1m",
    "pick_hash": "7be6a495e40d1aa7027e5be6e8789b671fe7d8a55442e6bdfae439e0d0f9e6e9",
    "indicators": {"rsi": 61.2},
    "generated_at": "2026-11-20T21:09:43.564Z",
}


class FakeCursor:
    """Records executed SQL; answers the hashes SELECT from a preset set."""

    def __init__(self, existing=()):
        self.existing = set(existing)
        self.calls = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))

    def fetchall(self):
        return [(h,) for h in self.existing]

    @property
    def insert_calls(self):
        return [c for c in self.calls if c[0].lstrip().upper().startswith("INSERT")]

    @property
    def select_calls(self):
        return [c for c in self.calls if c[0].lstrip().upper().startswith("SELECT")]


def test_maps_canonical_pick_to_row():
    row = w.to_row(GOOD_PICK)
    assert row is not None
    assert row["ticker"] == "PG"
    assert row["algorithm_name"] == "stocksunify2_volatility_adjusted_momentum_v2"
    assert row["pick_date"] == "2026-11-20"
    assert row["pick_time"] == "2026-11-20 21:09:43"
    assert row["entry_price"] == pytest.approx(169.485)
    assert row["stop_loss_price"] == pytest.approx(161.01)
    assert row["rating"] == "STRONG BUY"
    assert row["risk_level"] == "Low"
    assert row["pick_hash"] == GOOD_PICK["pick_hash"]
    assert row["verified"] == 0


def test_score_float_is_stored_as_int():
    row = w.to_row(GOOD_PICK)
    assert row["score"] == 100
    assert isinstance(row["score"], int)


def test_simulated_entry_falls_back_to_entry_price():
    row = w.to_row(GOOD_PICK)  # simulated_entry_price is 0
    assert row["simulated_entry_price"] == pytest.approx(169.485)


def test_zulu_timestamp_is_parsed_as_utc():
    row = w.to_row({**GOOD_PICK, "generated_at": "2026-11-20T23:09:43.564+02:00"})
    # 23:09 at +02:00 is 21:09 UTC
    assert row["pick_time"] == "2026-11-20 21:09:43"


def test_indicators_become_json():
    row = w.to_row(GOOD_PICK)
    assert json.loads(row["indicators_json"]) == {"rsi": 61.2}


def test_missing_symbol_is_unusable():
    assert w.to_row({**GOOD_PICK, "symbol": "   "}) is None


def test_missing_timestamp_is_unusable():
    assert w.to_row({**GOOD_PICK, "generated_at": None}) is None


def test_absent_hash_is_derived_deterministically():
    pick = {**GOOD_PICK}
    pick.pop("pick_hash")
    first = w.to_row(pick)["pick_hash"]
    second = w.to_row(pick)["pick_hash"]
    assert first == second
    assert w._HASH_RE.match(first)
    assert first != GOOD_PICK["pick_hash"]


def test_short_or_uppercase_hash_is_replaced_by_derived_hash():
    row = w.to_row({**GOOD_PICK, "pick_hash": "DEADBEEF"})
    assert w._HASH_RE.match(row["pick_hash"])
    assert row["pick_hash"] != "DEADBEEF"


def test_duplicate_hash_is_not_reinserted():
    rows, skipped = w.plan_inserts([GOOD_PICK], {GOOD_PICK["pick_hash"]})
    assert rows == []
    assert skipped and skipped[0][0] == "duplicate"


def test_in_batch_duplicates_collapse():
    rows, skipped = w.plan_inserts([GOOD_PICK, dict(GOOD_PICK)], set())
    assert len(rows) == 1
    assert skipped and skipped[0][0] == "duplicate"


def test_limit_caps_rows():
    second = {**GOOD_PICK, "symbol": "MSFT",
              "pick_hash": "a" * 64}
    rows, _ = w.plan_inserts([GOOD_PICK, second], set(), limit=1)
    assert len(rows) == 1


def test_insert_uses_full_column_list():
    cur = FakeCursor()
    w.insert_rows(cur, [w.to_row(GOOD_PICK)])
    sql, params = cur.insert_calls[0]
    for col in w.COLUMNS:
        assert col in sql
    assert len(params) == len(w.COLUMNS)


def test_insert_of_nothing_is_a_noop():
    cur = FakeCursor()
    assert w.insert_rows(cur, []) == 0
    assert cur.insert_calls == []


def test_fetch_existing_hashes_parses_rows():
    cur = FakeCursor(existing={"a" * 64})
    got = w.fetch_existing_hashes(cur, ["a" * 64, "b" * 64])
    assert got == {"a" * 64}


def test_fetch_existing_hashes_short_circuits_on_empty():
    cur = FakeCursor()
    assert w.fetch_existing_hashes(cur, []) == set()
    assert cur.select_calls == []


def test_dry_run_never_connects(tmp_path, monkeypatch):
    src = tmp_path / "picks.json"
    src.write_text(json.dumps({"active_picks": [GOOD_PICK]}), encoding="utf-8")

    def boom():
        raise AssertionError("dry run must not open a database connection")

    monkeypatch.setattr(w, "connect", boom)
    rc = w.main(["--input", str(src), "--quiet"])
    assert rc == 0


def test_missing_input_file_returns_2(tmp_path):
    rc = w.main(["--input", str(tmp_path / "nope.json"), "--quiet"])
    assert rc == 2


def test_commit_is_idempotent_against_existing_rows(tmp_path, monkeypatch):
    """A --commit run whose hashes already exist inserts nothing."""
    src = tmp_path / "picks.json"
    src.write_text(json.dumps({"active_picks": [GOOD_PICK]}), encoding="utf-8")

    cur = FakeCursor(existing={GOOD_PICK["pick_hash"]})

    class FakeConn:
        def cursor(self):
            return cur

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(w, "connect", lambda: FakeConn())
    rc = w.main(["--input", str(src), "--commit", "--quiet"])
    assert rc == 0
    assert cur.insert_calls == []


def test_commit_inserts_new_rows(tmp_path, monkeypatch):
    src = tmp_path / "picks.json"
    src.write_text(json.dumps({"active_picks": [GOOD_PICK]}), encoding="utf-8")

    cur = FakeCursor(existing=set())

    class FakeConn:
        def cursor(self):
            return cur

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(w, "connect", lambda: FakeConn())
    rc = w.main(["--input", str(src), "--commit", "--quiet"])
    assert rc == 0
    assert len(cur.insert_calls) == 1
