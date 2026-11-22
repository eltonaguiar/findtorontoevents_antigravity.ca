"""Idempotency + faithfulness tests for tools/emit_equity_breakout_pod.py.

Proves:
  (a) upserting the same rows twice inserts no duplicates (id is the PRIMARY KEY),
  (b) ids are deterministic (strategy|symbol|signal-date) and unique per symbol,
  (c) every strategy in STRATEGIES emits at least one real row on cached OHLCV,
  (d) the re-implemented rules agree with the live_scanner functions they mirror.

No MySQL is touched: upsert_rows() is exercised against an in-memory fake that
enforces PRIMARY KEY id semantics, exactly like trading_picks.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import emit_equity_breakout_pod as E  # noqa: E402


class _FakeCursor:
    def __init__(self, store):
        self._store = store
        self.rowcount = 0

    def execute(self, sql, params):
        if "INSERT INTO trading_picks" in sql:
            exists = params["id"] in self._store
            self._store[params["id"]] = dict(params)
            self.rowcount = 2 if exists else 1  # MySQL ON DUPLICATE KEY semantics
        else:
            raise AssertionError(f"unexpected SQL in test: {sql[:40]}")


class _FakeConn:
    def __init__(self):
        self.store = {}
        self.commits = 0

    def cursor(self):
        return _FakeCursor(self.store)

    def commit(self):
        self.commits += 1


def test_upsert_twice_no_duplicates():
    rows = E.collect("adx-trend")
    assert rows, "expected real adx-trend signals on cached OHLCV"
    conn = _FakeConn()
    E.upsert_rows(conn, rows)
    n_first = len(conn.store)
    E.upsert_rows(conn, rows)          # re-run, identical rows
    assert len(conn.store) == n_first == len(rows)
    assert n_first > 0


def test_ids_deterministic_and_unique():
    rows = E.collect("vol-contraction")
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "one id per symbol"
    again = [r["id"] for r in E.collect("vol-contraction")]
    assert ids == again, "ids are deterministic across runs"


def test_every_strategy_produces_rows():
    for key in E.STRATEGIES:
        rows = E.collect(key)
        assert rows, f"{key} produced no real signals on cached OHLCV"
        assert all(r["strategy"] == E.STRATEGIES[key][0] for r in rows)
        assert all(r["direction"] == "LONG" for r in rows)
        # net = gross - 8bp, and stop-first never exits above the stop
        for r in rows:
            assert abs((r["_gross_pct"] - r["pnl_pct"]) - E.SLIPPAGE_BPS / 100.0) < 1e-6
            if r["exit_reason"] == "stop":
                assert r["exit_price"] == r["stop_loss"]


def test_rules_match_live_scanner():
    """Spot-check the adx rule against the real function on a truncated frame."""
    import importlib.util
    import pandas as pd

    path = "KIMI_RISEOFTHECLAW/live_scanner.py"
    spec = importlib.util.spec_from_file_location("live_scanner", path)
    ls = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ls)
    df = pd.read_csv("data/cache/asset_class_review/AAPL_5y.csv")
    mine = E.adx_trend_signals(df)
    for i in range(200, len(df), 97):
        got, _ = ls.signal_adx_trend_filter("AAPL", df.iloc[: i + 1], {}, 0)
        assert (got == "BUY") == bool(mine.iloc[i]), f"ADX mismatch at bar {i}"


if __name__ == "__main__":
    sys.exit(__import__("pytest").main([__file__, "-q"]))
