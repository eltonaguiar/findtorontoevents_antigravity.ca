"""Publish-boundary guard: the /audit deploy must never ship non-strict JSON.

Observed live 2026-11-16: `strategy_ic_analysis.json` and `money_ready_verdict.json`
both returned HTTP 200 with fresh timestamps, yet their panels read "no data".
Python's `json` accepts and re-emits bare `NaN` / `Infinity`; browser `JSON.parse`
rejects the entire document. No server-side check could see the difference, so the
guard now lives where the bytes leave the repo.

Pure/offline: no FTP, no network.
"""

import json

import pytest

from tools.deploy_audit_files import _sanitize_json_bytes, _strict_json_problem


def test_flags_bare_nan():
    assert _strict_json_problem(b'{"dsr_score": NaN}') is not None


def test_flags_bare_infinity():
    # The exact live Strategy-IC failure shape.
    assert _strict_json_problem(b'{"pf": Infinity}') is not None
    assert _strict_json_problem(b'{"pf": -Infinity}') is not None


def test_accepts_valid_json_and_the_string_form():
    assert _strict_json_problem(b'{"a": null, "b": 1.5}') is None
    # A quoted sentinel parses fine -- it is a data-quality wart, not invalid JSON.
    assert _strict_json_problem(b'{"pf": "Infinity"}') is None


def test_flags_non_utf8():
    assert _strict_json_problem(b"\xff\xfe{}") is not None


def test_sanitize_produces_parseable_json_with_nulls():
    out = _sanitize_json_bytes(b'{"a": NaN, "b": [Infinity, -Infinity, 1.0]}')

    def _reject(tok):
        raise AssertionError(f"non-finite token leaked: {tok}")

    parsed = json.loads(out.decode("utf-8"), parse_constant=_reject)
    assert parsed == {"a": None, "b": [None, None, 1.0]}
    assert b"NaN" not in out and b"Infinity" not in out


def test_sanitize_preserves_finite_values():
    raw = b'{"generated_at": "2026-11-16T03:00:00Z", "n": 42, "wr": 0.412}'
    parsed = json.loads(_sanitize_json_bytes(raw).decode("utf-8"))
    assert parsed["n"] == 42 and parsed["wr"] == 0.412
    assert parsed["generated_at"] == "2026-11-16T03:00:00Z"
