"""Provenance/signal_ts backfill proposer — synthetic-fixture tests (report-only)."""
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import backfill_provenance as bp  # noqa: E402


def test_propose_signal_ts_fallback_chain():
    assert bp.propose_signal_ts({"signal_ts": "s"}) == "s"
    assert bp.propose_signal_ts({"entry_date": "2026-06-01"}) == "2026-06-01"
    assert bp.propose_signal_ts({"timestamp": "t"}) == "t"
    assert bp.propose_signal_ts({"nothing": 1}) is None


def test_propose_source_chain_and_inference():
    assert bp.propose_source({"source_system": "luxalgo"}) == "luxalgo"
    assert bp.propose_source({"original_source": "okx"}) == "okx"
    assert bp.propose_source({"strategy": "quan_engine_scalp"}) == "inferred:quan"
    assert bp.propose_source({}) is None


def test_report_counts_present_recovered_unrepairable():
    rows = [
        {"signal_ts": "x", "source_system": "a"},               # both present
        {"entry_date": "d", "strategy": "luxalgo_conf"},        # ts recoverable, src inferred
        {"timestamp": "t", "original_source": "okx"},           # ts recoverable, src recovered
        {"symbol": "X"},                                        # both unrepairable
    ]
    r = bp.backfill_report(rows)
    assert r["n_total"] == 4
    assert r["signal_ts"]["present"] == 1
    assert r["signal_ts"]["recoverable"] == 2
    assert r["signal_ts"]["unrepairable"] == 1
    assert r["source"]["present"] == 1
    assert r["source"]["recoverable"] == 1
    assert r["source"]["inferred"] == 1
    assert r["source"]["unrepairable"] == 1


def test_report_is_read_only():
    rows = [{"entry_date": "d", "strategy": "s"}]
    before = copy.deepcopy(rows)
    r = bp.backfill_report(rows)
    assert rows == before
    assert r["_mutated_ledger"] is False


def test_coverage_after_backfill_pct():
    rows = [{"timestamp": "t", "source_system": "a"}] * 4
    r = bp.backfill_report(rows)
    assert r["signal_ts"]["coverage_after_backfill_pct"] == 100.0
    assert r["source"]["coverage_after_backfill_pct"] == 100.0
