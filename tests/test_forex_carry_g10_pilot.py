"""Tests for `verified_strategies.paper_pilot.forex_carry_g10_pilot`."""
from __future__ import annotations

import json
import sys
import types
from types import SimpleNamespace

import verified_strategies.paper_pilot.forex_carry_g10_pilot as fx


def test_one_shot_and_write_db_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fx, "PILOT_DIR", tmp_path)
    monkeypatch.setattr(fx, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(fx, "LOG_PATH", tmp_path / "log.jsonl")

    fake_carry_mod = types.ModuleType("tools.research.forex_carry")
    fake_carry_mod.fetch_current_rates = lambda: {"AUD": 4.35, "JPY": 0.25}
    fake_carry_mod.build_signals = lambda rates: [
        {"ccy": "AUD", "direction": "LONG", "carry_bps": 435},
        {"ccy": "JPY", "direction": "SHORT", "carry_bps": 25},
    ]
    monkeypatch.setitem(sys.modules, "tools.research.forex_carry", fake_carry_mod)

    executed = []

    class FakeCursor:
        def execute(self, sql, params):
            executed.append((sql, params))

    class FakeConn:
        def __init__(self):
            self.committed = False
            self.closed = False

        def cursor(self):
            return FakeCursor()

        def commit(self):
            self.committed = True

        def close(self):
            self.closed = True

    fake_conn = FakeConn()
    connect_kwargs = {}

    def fake_connect(**kwargs):
        connect_kwargs.update(kwargs)
        return fake_conn

    fake_pymysql = types.ModuleType("pymysql")
    fake_pymysql.connect = fake_connect
    fake_pymysql.cursors = SimpleNamespace(DictCursor="DictCursor")
    monkeypatch.setitem(sys.modules, "pymysql", fake_pymysql)

    fake_db_env = types.ModuleType("tools.db_env")
    fake_db_env.get_stocks_creds = lambda: {
        "host": "localhost",
        "user": "u",
        "password": "p",
        "database": "d",
        "extra_diag_key": "must_be_filtered",
    }
    monkeypatch.setitem(sys.modules, "tools.db_env", fake_db_env)

    class FakeHist:
        empty = False
        def __getitem__(self, col):
            return SimpleNamespace(iloc=SimpleNamespace(__getitem__=lambda _self, _idx: 0.65))

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda pair: SimpleNamespace(history=lambda period="1d": FakeHist())
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    rc = fx.main(["--one-shot", "--write-db"])
    assert rc == 0

    out = json.loads(capsys.readouterr().out)
    assert out["open_legs"] == 2
    assert len(out["basket"]) == 2
    assert out["basket"][0]["pair"] == "AUDUSD=X"

    assert "extra_diag_key" not in connect_kwargs
    assert fake_conn.committed is True
    assert fake_conn.closed is True
    assert len(executed) == 2
