"""V2.1 Priority-1 blocker -- money_ready_verdict.json must be STRICT JSON.

Observed live 2026-10-19 (evidence hashes recorded in planv2_Oct19_github.MD):
the served artifact returns HTTP 200 but contains four bare ``"dsr_score": NaN``
tokens. Python's ``json.dumps`` emits ``NaN`` by default and ``json.load``
accepts it, so local tooling never noticed -- but browser ``JSON.parse`` rejects
it ("Unexpected token 'N'"), which is why the Money Ready tab showed
"No data available" despite a fresh timestamp.

Two-part contract tested here:

1. ``_dsr_gate`` fails CLOSED on non-finite input: a degenerate return series
   must yield ``dsr_score: None`` + a reason note, never NaN
   (plan measurement contract: "report null plus reason, not
   999/infinity/proven").
2. The serialization boundary sanitizes ANY non-finite float (any field) to
   null and emits with ``allow_nan=False`` so a corrupt artifact can never be
   published again, regardless of which upstream value degenerates.

Pure/offline: no DB, no network, no generator run.
"""

import json
import math
import types

import pytest

from alpha_engine.money_ready_verdict import _dsr_gate, _json_safe


# Real-world shape: a two-point binary series makes sharpe_variance degenerate
# and deflated_sharpe_ratio return NaN (empirically reproduced 2026-10-19).
DEGENERATE_RETURNS = [0.05, -0.03] * 25  # n=50


def test_dsr_gate_never_returns_nan_score():
    r = _dsr_gate(DEGENERATE_RETURNS)
    s = r.get("dsr_score")
    if s is not None:
        assert math.isfinite(float(s)), f"dsr_score must be finite or None, got {s!r}"


def test_dsr_gate_fails_closed_on_degenerate_series():
    """The reproduced NaN fixture: score None + reason, ok None (not a pass)."""
    r = _dsr_gate(DEGENERATE_RETURNS)
    if r["dsr_score"] is None or (
        isinstance(r["dsr_score"], float) and not math.isfinite(r["dsr_score"])
    ):
        # if the raw computation is non-finite the gate must fail closed
        assert r["dsr_score"] is None, "non-finite score must be null, not NaN"
        assert r["ok"] is not True, "unknown evidence must not pass"
        assert r.get("note"), "null score must carry a reason note"


def test_json_safe_converts_nonfinite_to_null():
    payload = {
        "classes": {
            "A": {"dsr_score": float("nan")},
            "B": {"dsr_score": float("inf"), "neg": float("-inf")},
        },
        "rows": [1.5, float("nan"), None, "x"],
        "ok_float": 0.75,
        "ints": 3,
    }
    safe = _json_safe(payload)
    assert safe["classes"]["A"]["dsr_score"] is None
    assert safe["classes"]["B"]["dsr_score"] is None
    assert safe["classes"]["B"]["neg"] is None
    assert safe["rows"][1] is None
    assert safe["ok_float"] == 0.75  # finite floats untouched
    assert safe["ints"] == 3


def test_sanitized_payload_is_strict_json():
    """The exact browser-level regression: strict JSON.parse must succeed."""
    out = {
        "generated_at": "2026-10-19T03:56:39Z",
        "classes": {"X": {"dsr_score": float("nan"), "pf": float("inf")}},
    }
    text = json.dumps(_json_safe(out), indent=2, allow_nan=False)
    assert "NaN" not in text and "Infinity" not in text
    # json.loads with a parse_constant that RAISES == browser strictness
    def _reject(token):
        raise AssertionError(f"non-finite token leaked into JSON: {token}")

    parsed = json.loads(text, parse_constant=_reject)
    assert parsed["classes"]["X"]["dsr_score"] is None


def test_json_safe_is_identity_for_valid_structures():
    obj = {"a": [1, 2.5, "s", None, True], "b": {"c": 0.0}}
    assert _json_safe(obj) == obj


# ---------------------------------------------------------------------------
# money_ready_snapshot.py -- the actual writer of the live
# money_ready_verdict.json (execs the verdict script, re-serializes stdout).
# Python's json.loads ACCEPTS bare NaN, so the old code silently passed the
# corruption through and re-emitted it into the served artifact.
# ---------------------------------------------------------------------------


def test_snapshot_run_verdict_fails_loud_on_nan_stdout(monkeypatch):
    """run_verdict's documented contract is 'fail LOUD'. A NaN-emitting
    verdict stdout must abort, not flow into the published artifact."""
    import tools.money_ready_snapshot as snap

    fake_proc = types.SimpleNamespace(
        returncode=0,
        stdout='{"CRYPTO": {"dsr_score": NaN, "verdict": "WATCH"}}',
        stderr="",
    )
    monkeypatch.setattr(
        snap, "subprocess", types.SimpleNamespace(run=lambda *a, **k: fake_proc)
    )
    with pytest.raises(SystemExit):
        snap.run_verdict()


def test_snapshot_local_json_safe_sanitizes():
    """The snapshot keeps its decoupling rule (never imports the verdict
    module), so it carries its own sanitizer at the write boundary."""
    import tools.money_ready_snapshot as snap

    safe = snap._json_safe({"a": float("nan"), "b": [float("inf"), 1.0]})
    assert safe["a"] is None
    assert safe["b"][0] is None
    assert safe["b"][1] == 1.0
    text = json.dumps(safe, allow_nan=False)
    assert "NaN" not in text and "Infinity" not in text


def test_snapshot_reject_constant_raises_json_error():
    """parse_constant hook must raise JSONDecodeError so run_verdict's
    existing except-clause reports it with the stdout snippet."""
    import tools.money_ready_snapshot as snap

    with pytest.raises(json.JSONDecodeError):
        snap._reject_constant("NaN")
    with pytest.raises(json.JSONDecodeError):
        snap._reject_constant("Infinity")
