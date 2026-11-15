"""Tests for batched MySQL inserts in `audit_trail.backfill_local_sources`."""
from __future__ import annotations

import json
import sqlite3

import audit_trail.backfill_local_sources as bls


class _FakeConn:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


class _FakeCursor:
    def __init__(self, fail_batch_once=False):
        self.connection = _FakeConn()
        self.executemany_calls = []
        self.execute_calls = []
        self.rowcount = 0
        self._fail_batch_once = fail_batch_once

    def executemany(self, sql, rows):
        if self._fail_batch_once:
            self._fail_batch_once = False
            raise RuntimeError("simulated chunk error")
        self.executemany_calls.append((sql, list(rows)))
        self.rowcount = len(rows)

    def execute(self, sql, row=None):
        self.execute_calls.append((sql, row))
        self.rowcount = 1


def test_flush_batch_chunks_500_rows():
    cur = _FakeCursor()
    rows = [("BTC-USD",) * 15 for _ in range(1205)]
    inserted = bls._flush_batch(cur, bls._PICK_SQL, rows, batch_size=500)
    assert inserted == 1205
    assert [len(c[1]) for c in cur.executemany_calls] == [500, 500, 205]
    assert cur.connection.commits == 3
    assert cur.execute_calls == []


def test_flush_batch_falls_back_per_row_on_chunk_error():
    cur = _FakeCursor(fail_batch_once=True)
    rows = [("ETH-USD",) * 15, ("SOL-USD",) * 15]
    inserted = bls._flush_batch(cur, bls._PICK_SQL, rows, batch_size=500)
    assert inserted == 2
    assert len(cur.execute_calls) == 2
    assert cur.connection.commits == 1


def test_load_json_and_sqlite_preserve_gates_and_batch(tmp_path, monkeypatch):
    monkeypatch.setattr(bls, "REPO", tmp_path)
    monkeypatch.setattr(
        bls, "is_emission_allowed",
        lambda strategy, source_system: (strategy != "KILLED_STRAT", "test"),
    )

    picks_json = tmp_path / "closed.json"
    picks_json.write_text(
        json.dumps([
            {
                "symbol": "BTCUSDT", "direction": "BUY", "strategy": "VALID_STRAT",
                "entry_price": 60000, "take_profit": 63000, "stop_loss": 58000,
                "exit_price": 63000, "status": "WON", "exit_reason": "TP_HIT",
                "pnl_pct": 5.0, "timestamp": "2026-11-10T10:00:00Z",
                "closed_at": "2026-11-10T12:00:00Z",
            },
            {
                "symbol": "DOGEUSDT", "direction": "BUY", "strategy": "KILLED_STRAT",
                "entry_price": 0.1, "status": "LOST", "pnl_pct": -5.0,
                "timestamp": "2026-11-10T10:00:00Z",
            },
            {
                "symbol": "ADAUSDT", "direction": "BUY", "strategy": "VALID_STRAT",
                "entry_price": 0.5, "status": "WON", "pnl_pct": 2.0,
                # No timestamp/closed_at -> must be skipped from at_signal_outcomes
            },
        ]),
        encoding="utf-8",
    )

    cur = _FakeCursor()
    p_cnt, o_cnt = bls.load_json_picks(cur, "closed.json", "test_sys", is_closed=True)
    assert p_cnt == 2
    assert o_cnt == 1
    assert len(cur.executemany_calls) == 2

    db_path = tmp_path / "sample.db"
    db = sqlite3.connect(str(db_path))
    db.execute("CREATE TABLE picks (symbol TEXT, strategy TEXT, status TEXT, timestamp TEXT, closed_at TEXT, pnl_pct REAL)")
    db.execute("INSERT INTO picks VALUES ('AAPL', 'VALID_STRAT', 'WON', '2026-11-10 10:00:00', '2026-11-10 16:00:00', 3.0)")
    db.execute("INSERT INTO picks VALUES ('NVDA', 'KILLED_STRAT', 'LOST', '2026-11-10 10:00:00', '2026-11-10 16:00:00', -2.0)")
    db.commit()
    db.close()

    cur2 = _FakeCursor()
    sp, so = bls.load_sqlite_table(cur2, "sample.db", "picks", "test_sqlite")
    assert sp == 1
    assert so == 1
    assert len(cur2.executemany_calls) == 2
