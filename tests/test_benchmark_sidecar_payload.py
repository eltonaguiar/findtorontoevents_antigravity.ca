"""Task 5: benchmark sidecar merge into the measurement-hygiene payload block.

These tests exercise the small, testable helper ``_build_benchmark_sidecar``
in ``audit_trail.dashboard_generator``. That helper makes the in-memory output
of ``alpha_engine.benchmark_closed_ledger.build_report`` available as
``benchmark_sidecar`` on the ``measurement_hygiene`` payload block, independent
of whether the on-disk sidecar file ``audit_dashboard/data/benchmark_ledger_proof.json``
exists (it currently does not).

Per the TDD brief, ``build_report`` is always monkeypatched — no network calls,
no file IO, no real benchmark computation in these tests.
"""
from __future__ import annotations

import pytest

from audit_trail.dashboard_generator import _build_benchmark_sidecar

SENTINEL_REPORT = {
    "ledgers": [{"strategy": "s1", "asset_class": "CRYPTO", "n": 10}],
    "summary": {
        "n_ledgers": 1,
        "n_full_proof": 0,
        "n_pass_95": 0,
        "n_mc_top_decile": 0,
    },
    "generated_at": "2026-10-22T00:00:00Z",
    "source": "test",
    "n_boot": 10000,
    "n_perm": 10000,
    "seed": 42,
    "conventions": {},
}

ROWS = [{"strategy": "s1", "asset_class": "CRYPTO", "pnl_pct": 1.0}]


def test_benchmark_sidecar_key_present_when_flag_on(monkeypatch):
    """Helper surfaces build_report()["ledgers"] as benchmark_sidecar."""
    # Note 1: monkeypatch the attribute on the module object, because the helper
    # performs `from alpha_engine.benchmark_closed_ledger import build_report`
    # inside the function body at call time.
    monkeypatch.setattr(
        "alpha_engine.benchmark_closed_ledger.build_report",
        lambda *a, **k: SENTINEL_REPORT,
    )
    result = _build_benchmark_sidecar(ROWS)
    assert result["benchmark_sidecar"] == SENTINEL_REPORT["ledgers"]
    # No error key on the happy path.
    assert "benchmark_error" not in result


def test_benchmark_sidecar_none_when_build_report_raises(monkeypatch):
    """Fail-soft: a build_report crash must NOT raise; it yields None + error."""

    def _boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "alpha_engine.benchmark_closed_ledger.build_report", _boom
    )
    result = _build_benchmark_sidecar(ROWS)  # must not raise
    assert result["benchmark_sidecar"] is None
    assert "boom" in result["benchmark_error"]


def test_benchmark_sidecar_none_when_ledgers_missing(monkeypatch):
    """A report without a leadinggers`` key yields None (not [])."""
    monkeypatch.setattr(
        "alpha_engine.benchmark_closed_ledger.build_report",
        lambda *a, **k: {},
    )
    result = _build_benchmark_sidecar(ROWS)
    assert result["benchmark_sidecar"] is None


def test_benchmark_sidecar_empty_rows_returns_none(monkeypatch):
    """Empty rows => None, and build_report must NOT be called."""
    calls = []

    def _recorder(*a, **k):
        calls.append(a)
        return SENTINEL_REPORT

    monkeypatch.setattr(
        "alpha_engine.benchmark_closed_ledger.build_report", _recorder
    )
    result = _build_benchmark_sidecar([])
    assert result["benchmark_sidecar"] is None
    assert calls == [], "build_report must not be called with empty rows"
