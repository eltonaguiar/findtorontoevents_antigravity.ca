"""Task 11: DB freshness gate tests for audit_trail.dashboard_generator.

Covers the fail-soft freshness check added as a gate input to the
``measurement_hygiene`` payload block:

1. Fresh data (timestamps within 24 h) -> ``freshness_ok`` True, no warning.
2. Stale data (mocked timestamp older than 24 h) -> ``freshness_ok`` False,
   warning present, ``measurement_hygiene.enabled`` forced False.
3. The guard does not affect any other payload fields.

The tests exercise the helper and the payload attachment directly (they do not
run the full dashboard generator, matching the project rule that dashboard
generators are never run locally).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import audit_trail.dashboard_generator as dg  # noqa: E402

FIXED_NOW = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _stamp_mtime(path: Path, dt: datetime) -> None:
    ts = dt.timestamp()
    os.utime(path, (ts, ts))


# ── Helper: _check_data_freshness() ──


def test_fresh_data_returns_ok_without_warning(tmp_path):
    src = tmp_path / "source.json"
    _write_json(src, {"generated_utc": (FIXED_NOW - timedelta(hours=1)).isoformat()})

    ok, warning = dg._check_data_freshness([src], now=FIXED_NOW)

    assert ok is True
    assert warning == ""


def test_fresh_data_via_mtime_returns_ok(tmp_path):
    src = tmp_path / "source.json"
    _write_json(src, {"payload_only": 1})
    _stamp_mtime(src, FIXED_NOW - timedelta(hours=2))

    ok, warning = dg._check_data_freshness([src], now=FIXED_NOW)

    assert ok is True
    assert warning == ""


def test_stale_content_timestamp_flagged(tmp_path):
    src = tmp_path / "source.json"
    _write_json(src, {"generated_utc": (FIXED_NOW - timedelta(hours=48)).isoformat()})

    ok, warning = dg._check_data_freshness([src], now=FIXED_NOW)

    assert ok is False
    assert warning and "stale" in warning.lower()


def test_stale_mtime_flagged(tmp_path):
    # No parseable content timestamp -> helper must fall back to file mtime.
    src = tmp_path / "source.json"
    _write_json(src, {"payload_only": 1})
    _stamp_mtime(src, FIXED_NOW - timedelta(hours=72))

    ok, warning = dg._check_data_freshness([src], now=FIXED_NOW)

    assert ok is False
    assert warning and "stale" in warning.lower()


def test_missing_source_fails_open(tmp_path):
    missing = tmp_path / "does_not_exist.json"

    ok, warning = dg._check_data_freshness([missing], now=FIXED_NOW)

    assert ok is True
    assert warning == ""


def test_any_stale_source_among_fresh_flags(tmp_path):
    fresh = tmp_path / "fresh.json"
    stale = tmp_path / "stale.json"
    _write_json(fresh, {"generated_utc": (FIXED_NOW - timedelta(hours=1)).isoformat()})
    _write_json(stale, {"generated_utc": (FIXED_NOW - timedelta(hours=30)).isoformat()})

    ok, warning = dg._check_data_freshness([fresh, stale], now=FIXED_NOW)

    assert ok is False
    assert "stale.json" in warning


# ── Integration: _attach_measurement_payload_keys() ──


def _base_payload() -> dict:
    return {
        "summary": {"total_pnl_pct": 1.23},
        "picks": {"active": [{"symbol": "X"}]},
        "generated_at": FIXED_NOW.isoformat(),
    }


def test_stale_forces_enabled_false_and_adds_warning():
    payload = _base_payload()
    block = {"total_ledgers": 1, "n_verified": 5, "ledgers": []}

    out = dg._attach_measurement_payload_keys(
        payload,
        measurement_block=block,
        ledger_gate_results={"s|A": {"verdict": "OK"}},
        overlap_aware_return=None,
        freshness_check=(False, "Data source source.json is stale (48.0h old)."),
    )

    mh = out["measurement_hygiene"]
    assert mh["enabled"] is False
    assert mh["freshness_ok"] is False
    assert "freshness_warning" in mh
    assert "source.json" in mh["freshness_warning"]

    summary_mh = out["summary"]["measurement_hygiene"]
    assert summary_mh["freshness_ok"] is False
    assert "freshness_warning" in summary_mh


def test_fresh_preserves_enabled_true_and_no_warning():
    payload = _base_payload()

    out = dg._attach_measurement_payload_keys(
        payload,
        measurement_block=None,
        ledger_gate_results={"s|A": {"verdict": "OK"}},
        overlap_aware_return=None,
        freshness_check=(True, ""),
    )

    mh = out["measurement_hygiene"]
    assert mh["enabled"] is True
    assert mh["freshness_ok"] is True
    assert "freshness_warning" not in mh


def test_guard_does_not_affect_other_payload_fields():
    payload = _base_payload()
    block = {"total_ledgers": 1, "n_verified": 5, "ledgers": []}

    out = dg._attach_measurement_payload_keys(
        payload,
        measurement_block=block,
        ledger_gate_results={"s|A": {"verdict": "OK"}},
        overlap_aware_return=None,
        freshness_check=(False, "stale source"),
    )

    # Non-hygiene fields are byte-identical to the input.
    assert out["summary"]["total_pnl_pct"] == 1.23
    assert out["picks"] == {"active": [{"symbol": "X"}]}
    assert out["generated_at"] == FIXED_NOW.isoformat()
    # The measurement block's pre-existing fields are preserved.
    assert out["measurement_hygiene"]["excluded_ledgers"] == []
    assert out["summary"]["measurement_hygiene"]["n_verified"] == 5
