"""Regression guard tests for Task 10 (byte-identical OFF output).

Verifies the MEASUREMENT_HYGIENE_V1 regression guard in
``audit_trail/dashboard_generator.py``:

1. The ON-generation payload JSON string can be generated and captured.
2. The OFF-generation payload JSON string is byte-identical to the ON
   generation except for the omitted ``measurement_hygiene`` block(s).
3. When a non-guarded field drifts, the guard logs a warning and falls back to
   the previous-generation JSON (fail-soft, byte-identical guarantee).

Note: these are unit tests against the pure guard helpers — they do not invoke
the full heavy ``generate()`` (which touches MySQL/network and rewrites live
files). The ON/OFF payload shapes are produced with the same wire helpers that
``generate()`` uses when the flag is enabled/disabled.
"""

from __future__ import annotations

import copy
import json
import logging

import pytest

from audit_trail import dashboard_generator as dg


def _sample_measurement_block():
    return {
        "ledgers": [
            {
                "strategy": "alpha_engine",
                "asset_class": "EQUITY",
                "direction": "LONG",
                "n": 120,
                "pf_gross": 1.8,
                "pf_net": 1.62,
                "pf_net_ci_lower": 1.31,
                "mdd": 0.14,
                "ledger_gate_pass": True,
            }
        ],
        "n_unverified": 0,
        "n_verified": 120,
        "total_ledgers": 1,
    }


def _sample_ledger_gate_results():
    return {
        ("alpha_engine", "EQUITY", "LONG"): {"verdict": "OK"},
        ("baby_strat", "CRYPTO", "LONG"): {"verdict": "UNVERIFIED: n=21<100"},
    }


def _sample_base_payload():
    return {
        "generated_at": "2026-10-23T00:00:00Z",
        "summary": {
            "total_pnl": 12.34,
            "overall_wr": 55.5,
            "active_picks": 42,
            "quality_stats": {"feature_rows_persisted": 3},
        },
        "picks": {
            "active": [{"symbol": "AAPL", "direction": "LONG"}],
            "recent_closed": [{"symbol": "TSLA", "pnl_pct": 1.25}],
        },
        "systems": [{"name": "alpha_engine", "wr_pct": 60.0}],
    }


def _serialize(payload):
    return json.dumps(payload, indent=2, default=str, allow_nan=False)


# ── 1 & 2: ON vs OFF payload JSON strings ──────────────────────


def test_on_vs_off_payload_json_identical_except_measurement_block():
    """Generating ON and OFF payloads yields identical JSON minus the block."""
    # OFF generation = base payload with NO measurement_hygiene keys.
    off_payload = _sample_base_payload()
    off_json = _serialize(off_payload)

    # ON generation = base payload + measurement_hygiene keys, via the same
    # wire helper production uses when the flag is enabled.
    on_payload = dg._attach_measurement_payload_keys(
        _sample_base_payload(),
        measurement_block=_sample_measurement_block(),
        ledger_gate_results=_sample_ledger_gate_results(),
        overlap_aware_return=0.0123,
    )
    on_json = _serialize(on_payload)

    # ON must actually carry the measurement blocks.
    assert "measurement_hygiene" in on_payload
    assert on_payload["measurement_hygiene"]["enabled"] is True
    assert "measurement_hygiene" in on_payload["summary"]

    # OFF must not carry them (omission).
    assert "measurement_hygiene" not in off_payload
    assert "measurement_hygiene" not in off_payload["summary"]

    # Stripping the ON generation yields exactly the OFF generation, byte for
    # byte (same serialization settings as generate()).
    stripped_on = dg._strip_measurement_hygiene_keys(on_payload)
    assert stripped_on == off_payload
    assert _serialize(stripped_on) == off_json


def test_strip_removes_both_full_and_legacy_enabled_false_blocks():
    payload = {
        "a": 1,
        # Legacy OFF-era emission that the guard must also normalize away.
        "measurement_hygiene": {"enabled": False},
        "summary": {"x": 2, "measurement_hygiene": {"foo": "bar"}},
    }
    out = dg._strip_measurement_hygiene_keys(payload)
    assert "measurement_hygiene" not in out
    assert "measurement_hygiene" not in out["summary"]
    assert out == {"a": 1, "summary": {"x": 2}}


# ── 3: guard logs warning + falls back on mismatch ─────────────


def test_guard_logs_warning_and_falls_back_on_mismatch(tmp_path, caplog):
    prev_obj = _sample_base_payload()
    out_path = tmp_path / "dashboard_data.json"
    prev_path = dg._regression_prev_gen_path(out_path)
    prev_path.parent.mkdir(parents=True, exist_ok=True)
    prev_path.write_text(_serialize(prev_obj), encoding="utf-8")

    # Simulate drift in a NON-guarded field while still being an OFF payload.
    off_payload = copy.deepcopy(prev_obj)
    off_payload["summary"]["total_pnl"] = 9999.0
    off_json = _serialize(off_payload)

    with caplog.at_level(logging.WARNING, logger="audit_dashboard"):
        out_text, used_fallback = dg.run_measurement_regression_guard(
            off_payload, off_json, out_path
        )

    assert used_fallback is True
    # Falls back to the stored previous generation -> byte-identical output.
    assert json.loads(out_text) == prev_obj
    assert any("Regression guard" in r.message for r in caplog.records)


def test_guard_noop_when_identical_and_refreshes_baseline(tmp_path, caplog):
    base = _sample_base_payload()
    out_path = tmp_path / "dashboard_data.json"
    prev_path = dg._regression_prev_gen_path(out_path)
    prev_path.parent.mkdir(parents=True, exist_ok=True)
    prev_path.write_text(_serialize(base), encoding="utf-8")

    off_json = _serialize(copy.deepcopy(base))
    with caplog.at_level(logging.WARNING, logger="audit_dashboard"):
        out_text, used_fallback = dg.run_measurement_regression_guard(
            copy.deepcopy(base), off_json, out_path
        )

    assert used_fallback is False
    assert out_text == off_json
    assert not any("Regression guard" in r.message for r in caplog.records)
    # Baseline refreshed for the next run.
    assert prev_path.read_text(encoding="utf-8") == off_json


def test_guard_seeds_baseline_when_no_previous(tmp_path):
    off_payload = _sample_base_payload()
    off_json = _serialize(off_payload)
    out_path = tmp_path / "dashboard_data.json"

    out_text, used_fallback = dg.run_measurement_regression_guard(
        off_payload, off_json, out_path
    )
    assert out_text == off_json
    assert used_fallback is False
    assert dg._regression_prev_gen_path(out_path).exists()


def test_guard_is_fail_soft_on_corrupt_previous(tmp_path, caplog):
    off_payload = _sample_base_payload()
    off_json = _serialize(off_payload)
    out_path = tmp_path / "dashboard_data.json"
    prev_path = dg._regression_prev_gen_path(out_path)
    prev_path.parent.mkdir(parents=True, exist_ok=True)
    prev_path.write_text("{not valid json", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="audit_dashboard"):
        out_text, used_fallback = dg.run_measurement_regression_guard(
            off_payload, off_json, out_path
        )
    assert out_text == off_json
    assert used_fallback is False
