"""INCIDENT_CRYPTO #8 resolver-hygiene checker — synthetic-fixture tests."""
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import resolver_hygiene_check as rh  # noqa: E402


def test_clean_ledger_has_no_suspects():
    picks = [
        {"symbol": "BTCUSDT", "signal_ts": "t1", "strategy": "s", "status": "CLOSED",
         "outcome": "WON", "pnl_pct": 1.2, "close_ts": "t2", "source_system": "lux"},
        {"symbol": "ETHUSDT", "signal_ts": "t1", "strategy": "s", "status": "CLOSED",
         "outcome": "LOST", "pnl_pct": -0.8, "close_ts": "t2", "source_system": "lux"},
    ]
    r = rh.scan_ledger(picks)
    assert r["never_closed"] == 0 and r["mislabels"] == 0
    assert r["missing_provenance"] == 0 and r["duplicate_groups"] == 0


def test_expired_won_mislabel_flagged():
    picks = [{"symbol": "X", "signal_ts": "t", "strategy": "s", "status": "EXPIRED",
              "outcome": "WON", "pnl_pct": 0.0, "source_system": "src"}]
    r = rh.scan_ledger(picks)
    assert r["mislabels"] == 1
    assert r["never_closed"] == 1  # terminal-nonwin + outcome WON


def test_pnl_sign_mismatch_flagged():
    picks = [{"symbol": "X", "signal_ts": "t", "strategy": "s", "status": "CLOSED",
              "outcome": "WON", "pnl_pct": -2.0, "close_ts": "c", "source_system": "src"}]
    assert rh.scan_ledger(picks)["mislabels"] == 1


def test_duplicates_counted():
    row = {"symbol": "MATICUSDT", "signal_ts": "ts", "strategy": "quan",
           "status": "CLOSED", "outcome": "WON", "pnl_pct": 2.5, "close_ts": "c",
           "source_system": "q"}
    picks = [copy.deepcopy(row) for _ in range(3)]
    r = rh.scan_ledger(picks)
    assert r["duplicate_groups"] == 1
    assert r["duplicate_rows"] == 3


def test_no_signal_ts_not_counted_as_duplicate():
    # 5 separate signals for same symbol/strategy but NO signal_ts -> must NOT
    # be flagged as duplicates (real-ledger false-positive fix).
    picks = [{"symbol": "JUPUSDT", "strategy": "luxalgo_confluence", "status": "CLOSED",
              "outcome": "WON", "pnl_pct": 1.0, "close_ts": "c", "source_system": "lux"}
             for _ in range(5)]
    r = rh.scan_ledger(picks)
    assert r["duplicate_groups"] == 0
    assert r["duplicate_rows"] == 0
    assert r["rows_without_signal_ts"] == 5


def test_missing_provenance_flagged():
    picks = [{"symbol": "X", "signal_ts": "t", "strategy": "s", "status": "CLOSED",
              "outcome": "WON", "pnl_pct": 1.0, "close_ts": "c"}]  # no source_*
    assert rh.scan_ledger(picks)["missing_provenance"] == 1


def test_report_only_never_mutates_input():
    picks = [{"symbol": "X", "signal_ts": "t", "strategy": "s", "status": "EXPIRED",
              "outcome": "WON", "pnl_pct": 0.0}]
    before = copy.deepcopy(picks)
    r = rh.scan_ledger(picks)
    assert picks == before              # input untouched
    assert r["_mutated_ledger"] is False
