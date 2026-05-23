"""Regression tests for dashboard_data.json strict-JSON output.

Background: 2026-04-27, the live findtorontoevents.ca/audit page rendered
"No data loaded" because the external dashboard_data.json contained
``"profit_factor": Infinity``. Browser ``JSON.parse()`` rejects the entire
payload on the first non-spec literal, so the dashboard fell through to
its empty fallback. Root cause: ``profit_factor = gross_wins / gross_losses``
produces ``inf`` when a cohort has zero losses, and Python's default
``json.dumps`` emits ``Infinity`` (allow_nan=True default).

These tests guard the fix:
1. The ``_sanitize_for_json`` helper recursively replaces inf/-inf/nan
   with None across dicts/lists/tuples.
2. The writers in ``audit_trail.dashboard_generator`` emit STRICT JSON
   (``allow_nan=False``) so any future regression that bypasses the
   sanitizer fails loudly at write time rather than silently corrupting
   the production payload.
"""
from __future__ import annotations

import json
import math

import pytest

from audit_trail.dashboard_generator import _sanitize_for_json


class TestSanitizer:
    def test_replaces_infinity_with_none(self):
        assert _sanitize_for_json(float("inf")) is None

    def test_replaces_negative_infinity_with_none(self):
        assert _sanitize_for_json(float("-inf")) is None

    def test_replaces_nan_with_none(self):
        assert _sanitize_for_json(float("nan")) is None

    def test_preserves_finite_floats(self):
        assert _sanitize_for_json(0.5) == 0.5
        assert _sanitize_for_json(-1e6) == -1e6
        assert _sanitize_for_json(0.0) == 0.0

    def test_preserves_non_float_types(self):
        assert _sanitize_for_json("hello") == "hello"
        assert _sanitize_for_json(42) == 42
        assert _sanitize_for_json(None) is None
        assert _sanitize_for_json(True) is True

    def test_recurses_into_dicts(self):
        result = _sanitize_for_json({
            "profit_factor": float("inf"),
            "win_rate": 0.5,
            "label": "ok",
        })
        assert result == {
            "profit_factor": None,
            "win_rate": 0.5,
            "label": "ok",
        }

    def test_recurses_into_lists(self):
        result = _sanitize_for_json([1.0, float("nan"), 2.0, float("-inf")])
        assert result == [1.0, None, 2.0, None]

    def test_handles_nested_structures(self):
        payload = {
            "systems": [
                {"name": "A", "pf": float("inf")},
                {"name": "B", "pf": 1.5},
            ],
            "summary": {
                "expectancy": float("nan"),
                "wr": 0.42,
            },
        }
        result = _sanitize_for_json(payload)
        assert result["systems"][0]["pf"] is None
        assert result["systems"][1]["pf"] == 1.5
        assert result["summary"]["expectancy"] is None
        assert result["summary"]["wr"] == 0.42

    def test_tuples_become_lists_with_inf_replaced(self):
        result = _sanitize_for_json((1.0, float("inf"), 2.0))
        assert result == [1.0, None, 2.0]


class TestStrictJsonOutput:
    """The shipped JSON must parse with browser-strict semantics (no inf/nan)."""

    def test_sanitized_payload_dumps_with_allow_nan_false(self):
        payload = {
            "metric": float("inf"),
            "ratio": float("nan"),
            "value": 3.14,
        }
        clean = _sanitize_for_json(payload)
        out = json.dumps(clean, allow_nan=False)
        parsed = json.loads(out)
        assert parsed["metric"] is None
        assert parsed["ratio"] is None
        assert parsed["value"] == 3.14

    def test_unsanitized_payload_with_strict_dumps_raises(self):
        """Sanity: without sanitization, allow_nan=False raises.

        Documents the failure mode that bricked the live dashboard 2026-04-27.
        """
        payload = {"profit_factor": float("inf")}
        with pytest.raises(ValueError):
            json.dumps(payload, allow_nan=False)

    def test_default_dumps_emits_invalid_json(self):
        """Document why default json.dumps is unsafe: it emits 'Infinity'."""
        payload = {"profit_factor": float("inf")}
        out = json.dumps(payload)  # default allow_nan=True
        assert "Infinity" in out  # the spec violation
